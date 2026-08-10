"""
kaleido.py — 復刻 Kaleido 的自動配色演算法（Wang et al., Neuroinformatics 2018）
================================================================================
論文的核心主張只有兩句：

  1. 把「相鄰卻同色」定義成能量，用蒙地卡羅把能量壓到最低，配色就自動變得好認。
  2. 把所有神經元合併成「一張」影像，檔案大小只由標準腦解析度決定，與神經元數量脫鉤。

這支程式做第 1 件事（第 2 件在 render.py 與 scaling.py）。流程對應論文 Methods
的步驟 1~5：

    步驟 1  影像對位     -> load_neurons()：把每個 .am 的體素放進同一組標準腦座標
    步驟 2  距離矩陣     -> distance_matrix()：每個神經元隨機抽 100 個體素估距
    步驟 3  選擇配色模式 -> 這裡只做 color by distance，其餘模式在 render.py
    步驟 4  能量函數     -> total_energy()（misread_energy() 是抄錯版的反例）
    步驟 5  蒙地卡羅     -> monte_carlo()

輸出（給 render.py 與 build_page.py 用）：
    data/neurons.json    每個神經元的中繼資料與各種模式下的色相角
    data/energy.json     能量下降軌跡、參數、計時、最近鄰色相差分布

論文沒寫死、我自己補的決定，都標成「【實作決定】」寫在程式碼旁邊，
教材裡會逐條交代。
"""

import json
import math
import re
import time
from pathlib import Path

import numpy as np

from amread import read_am

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "FCdata" / "neurons100"
DATA_DIR = ROOT / "data"

SAMPLE_VOXELS = 100      # 論文明寫：每個神經元隨機抽 100 個體素來估距
CLIP_PCT = 99.5          # 正規化用的白點百分位（沿用 EP03 的慣例）
SEED = 20180401          # 固定亂數種子，讓結果可重現（論文沒提，但教材需要可複現）
N_SEEDS = 8              # 最佳化重跑幾個種子。單跑一次會被雜訊騙，見 run_multi()

# 檔名裡的 driver line -> 它標記的神經傳導物質（沿用 EP03 的對照表）
NEUROTRANSMITTER = {
    "TH":     ("多巴胺", "Dopamine"),
    "Tdc2":   ("章魚胺", "Octopamine"),
    "Trh":    ("血清素", "Serotonin"),
    "VGlut":  ("麩胺酸", "Glutamate"),
    "Gad1":   ("GABA", "GABA"),
    "Cha":    ("乙醯膽鹼", "Acetylcholine"),
    "5-HT1B": ("血清素受體", "5-HT receptor"),
    "fru":    ("fruitless（性別二型迴路）", "fruitless"),
}


# ---------------------------------------------------------------- 步驟 1：對位

class Neuron:
    """一個神經元在標準腦座標裡的稀疏點雲。"""

    __slots__ = ("nid", "driver", "sex", "cell", "gx", "gy", "gz", "val",
                 "n_voxels", "src_dims", "src_bytes")

    def __init__(self, nid, driver, sex, cell, gx, gy, gz, val, src_dims, src_bytes):
        self.nid = nid
        self.driver, self.sex, self.cell = driver, sex, cell
        self.gx, self.gy, self.gz = gx, gy, gz    # 標準腦體素座標（int32）
        self.val = val                            # 正規化後強度 0~1（float32）
        self.n_voxels = int(gx.size)
        self.src_dims = src_dims
        self.src_bytes = src_bytes

    @property
    def centroid(self):
        return (float(self.gx.mean()), float(self.gy.mean()), float(self.gz.mean()))


def parse_name(stem):
    """5-HT1B-F-100000_seg001_warp_volume -> ('5-HT1B', 'F', '100000')"""
    m = re.match(r"(.+?)-([FM])-(\d+)", stem)
    return (m.group(1), m.group(2), m.group(3)) if m else (stem, "?", "")


def load_neurons(src=SRC, limit=None, verbose=True):
    """讀入所有 .am，回傳 (neurons, grid_origin, grid_dims)。

    論文步驟 1 是「把每個單神經元影像 warp 到同一個標準腦座標系」。這批 FlyCircuit
    資料**已經是 warp 過的**（檔名就叫 _warp_volume），每個檔的 BoundingBox 就是它
    在標準腦裡的位置，三軸體素間距都是 1.0。所以我們要做的只是「平移對齊」：
    把各自的區域座標加上自己的 bbox 原點，換算成共同的標準腦體素座標。

    【實作決定】論文說對位後若一個體素被多個神經元佔據，只保留訊號最強的那個。
    那一步屬於「合併成單一影像」，放在 render.py 做（那裡才有共用畫布）；
    這裡保持稀疏點雲，因為配色只需要位置，不需要解決重疊。
    """
    files = sorted(src.glob("*.am"))
    if limit:
        files = files[:limit]

    loaded = []
    for f in files:
        vol = read_am(f)
        x0, _x1, y0, _y1, z0, _z1 = vol.bbox
        sp = vol.spacing
        if max(abs(s - 1.0) for s in sp) > 1e-3:
            raise ValueError(f"{f.name} 的體素間距不是 1.0（{sp}），對位邏輯要改寫")

        zs, ys, xs = np.nonzero(vol.data)
        vals = vol.data[zs, ys, xs].astype(np.float32)

        # 【實作決定】各檔的動態範圍不一致（有的最大值 255、有的 4095），
        # 論文只說「明度為各體素正規化後的訊號強度」。這裡用每個神經元自己的
        # 99.5 百分位當白點，和 EP03 的三視圖一致，避免單一極亮體素壓掉整條神經元。
        vmax = max(float(np.percentile(vals, CLIP_PCT)), 1.0)
        vals = np.clip(vals / vmax, 0.0, 1.0)

        stem = f.stem
        nid = stem.split("_")[0]
        driver, sex, cell = parse_name(stem)
        loaded.append(Neuron(
            nid, driver, sex, cell,
            (xs + int(round(x0))).astype(np.int32),
            (ys + int(round(y0))).astype(np.int32),
            (zs + int(round(z0))).astype(np.int32),
            vals, list(vol.dims), f.stat().st_size,
        ))
        if verbose and len(loaded) % 20 == 0:
            print(f"  已載入 {len(loaded):3d}/{len(files)} 個")

    gx0 = min(int(n.gx.min()) for n in loaded)
    gy0 = min(int(n.gy.min()) for n in loaded)
    gz0 = min(int(n.gz.min()) for n in loaded)
    gx1 = max(int(n.gx.max()) for n in loaded)
    gy1 = max(int(n.gy.max()) for n in loaded)
    gz1 = max(int(n.gz.max()) for n in loaded)
    origin = (gx0, gy0, gz0)
    dims = (gx1 - gx0 + 1, gy1 - gy0 + 1, gz1 - gz0 + 1)

    if verbose:
        tot = sum(n.n_voxels for n in loaded)
        print(f"  共 {len(loaded)} 個神經元、{tot:,} 個非零體素")
        print(f"  標準腦聯集範圍 {dims[0]}×{dims[1]}×{dims[2]} 體素，原點 {origin}")
    return loaded, origin, dims


# ------------------------------------------------------------ 步驟 2：距離矩陣

def distance_matrix(neurons, n_sample=SAMPLE_VOXELS, seed=SEED, verbose=True):
    """論文步驟 2：每個神經元隨機抽 n_sample 個體素，兩兩估算距離。

    論文原文：對第一個神經元被選的每個體素，找出第二個神經元被選體素中最近的一個，
    兩者距離即「最短體素到神經元距離」；d_ij 是這些最短距離的平均。

    【實作決定】這個定義是**不對稱**的（從 i 看 j、從 j 看 i 會得到不同的值），
    論文沒說要用哪一邊。能量函數 E 的求和是對「無序的神經元對」做的，需要單一個
    d_ij，所以這裡取兩個方向的平均把它對稱化，並在教材裡標明這是我補的決定。
    """
    rng = np.random.default_rng(seed)
    n = len(neurons)

    pts = []
    for nu in neurons:
        idx = rng.choice(nu.n_voxels, size=min(n_sample, nu.n_voxels), replace=False)
        pts.append(np.stack([nu.gx[idx], nu.gy[idx], nu.gz[idx]], axis=1).astype(np.float32))

    D = np.zeros((n, n), dtype=np.float64)
    t0 = time.perf_counter()
    for i in range(n):
        for j in range(i + 1, n):
            # (100, 1, 3) - (1, 100, 3) -> (100, 100) 的兩兩距離
            d = np.sqrt(((pts[i][:, None, :] - pts[j][None, :, :]) ** 2).sum(-1))
            dij = 0.5 * (d.min(axis=1).mean() + d.min(axis=0).mean())   # 對稱化
            D[i, j] = D[j, i] = max(float(dij), 1e-6)
        if verbose and (i + 1) % 25 == 0:
            print(f"  距離矩陣 {i + 1}/{n} 列")
    dt = time.perf_counter() - t0
    if verbose:
        print(f"  距離矩陣完成，{dt:.2f} 秒；"
              f"距離範圍 {D[D > 0].min():.1f} ~ {D.max():.1f} 體素")
    return D, dt


# ------------------------------------------------- 步驟 4：色相組態與能量函數

def hue_table(n):
    """論文：色相角在色相環上均勻分布，theta(i) = 360 * i / n。"""
    return np.arange(1, n + 1, dtype=np.float64) * 360.0 / n


def total_energy(D, theta, H):
    """論文 Methods 步驟 4 的能量函數。

        E(H) = Σ_{i=2}^{N} Σ_{j=1}^{i-1}  1 / ( d_ij × min(Δ_ij, 360° − Δ_ij) )

    整個 d_ij × min(...) 都在**分母**裡。所以：兩條神經元靠得近（d 小）又被指派
    了相近的色相（Δ 小），分母就小、這一項的能量就大 —— 正是論文正文說的「難以
    分辨的組態要付出較高能量成本」。把總能量最小化，就會把擠在一起的神經元推開
    到色相環的兩端。公式與正文完全自洽，不需要任何修補。

    （我們自己的知識庫把這個分數抄成了 (1/d_ij)·min(Δ_ij, 360−Δ_ij)，分母的 min
    項被搬到分子，意義正好相反。misread_energy() 保留那個版本當反例，
    教材裡會拿兩者的結果對照。）

    不需要防除以零：H 是 1..N 的排列、色相角互不相同，所以 Δ_ij 最小就是 360/N
    度（N=100 時是 3.6 度），不可能為 0。
    """
    h = theta[H]
    d = np.abs(h[:, None] - h[None, :])
    ang = np.minimum(d, 360.0 - d)
    with np.errstate(divide="ignore"):
        M = 1.0 / (D * ang)
    np.fill_diagonal(M, 0.0)
    return float(M.sum()) / 2.0, M


def misread_energy(D, theta, H):
    """知識庫抄錯的版本：E = Σ (1/d_ij) · min(Δ_ij, 360−Δ_ij)。

    分母的 min 項被搬到分子後，「相鄰又同色」變成能量**最低**的組態，最小化它
    會把鄰居塗成同一種顏色 —— 與 Kaleido 的目的完全相反。只用來產生反例圖。
    """
    h = theta[H]
    d = np.abs(h[:, None] - h[None, :])
    ang = np.minimum(d, 360.0 - d)
    with np.errstate(divide="ignore", invalid="ignore"):
        M = ang / D
    np.fill_diagonal(M, 0.0)
    return float(M.sum()) / 2.0, M


def _rows(D, theta, H, S, kind):
    """只算 S 這幾個神經元對「所有神經元」的逐對能量（增量更新用）。"""
    h = theta[H]
    d = np.abs(h[S][:, None] - h[None, :])
    ang = np.minimum(d, 360.0 - d)
    with np.errstate(divide="ignore", invalid="ignore"):
        R = ang / D[S] if kind == "misread" else 1.0 / (D[S] * ang)
    R[np.arange(len(S)), S] = 0.0
    return R


# ------------------------------------------------------- 步驟 5：蒙地卡羅最佳化

def monte_carlo(D, n_steps=None, beta=None, anneal=None, seed=SEED, kind="paper",
                verbose=True, n_trace=400):
    """論文步驟 5 的蒙地卡羅。回傳 (best_H, trace, info)。

    論文的動作定義（照抄）：找出目前能量最高的神經元對 (p, q)，隨機選兩個神經元
    a、b，分別與 p、q 交換色相角；接受機率 P = min(1, exp(−β ΔE))；取整個過程中
    能量最低的組態。

    參數 beta / anneal 二選一：
      beta=x      固定溫度（論文的寫法，β 是「可調參數」）
      anneal=(a,b) 幾何降溫，β 從 a/|ΔE|典型值 升到 b/|ΔE|典型值

    【實作決定 1】β 論文沒給值。這裡先跑 300 次試探測出典型 |ΔE|，再用它當尺度，
    這樣同一組參數換到別的資料上也還適用。
    【實作決定 2】增量更新。一次換色只動到 ≤4 個神經元的色相，所以只需重算那幾
    列的逐對能量（O(N)），不必重算整個 N×N 矩陣。論文的複雜度分析（每次換色更新
    2(N−2) 對、總計 O(N²)）講的就是這件事；照字面每步重算全矩陣會變成 O(N³)，
    scaling.py 的計時就會失真。
    """
    n = D.shape[0]
    theta = hue_table(n)
    rng = np.random.default_rng(seed)
    energy_fn = misread_energy if kind == "misread" else total_energy

    H = rng.permutation(n)
    E, M = energy_fn(D, theta, H)
    E0 = E

    def propose(H_cur, M_cur):
        """論文的動作：能量最高的那一對，各自跟一個隨機神經元換色。"""
        flat = int(np.argmax(M_cur))
        p, q = flat // n, flat % n
        a, b = rng.integers(0, n, size=2)
        H_new = H_cur.copy()
        H_new[[a, p]] = H_new[[p, a]]
        H_new[[b, q]] = H_new[[q, b]]
        return H_new, sorted({int(a), int(b), int(p), int(q)})

    def apply_incremental(H_new, S, M_cur, E_cur):
        """只重算 S 這幾列，回傳 (E_new, M_new)。"""
        S = np.asarray(S)
        old_rows = M_cur[S]
        old_touch = old_rows.sum() - M_cur[np.ix_(S, S)].sum() / 2.0
        new_rows = _rows(D, theta, H_new, S, kind)
        new_touch = new_rows.sum() - new_rows[:, S].sum() / 2.0
        M_new = M_cur.copy()
        M_new[S, :] = new_rows
        M_new[:, S] = new_rows.T
        return E_cur - old_touch + new_touch, M_new

    # --- 溫度尺度校準
    deltas = []
    for _ in range(300):
        H_try, S = propose(H, M)
        E_try, _ = apply_incremental(H_try, S, M, E)
        deltas.append(abs(E_try - E))
    scale = float(np.mean(deltas)) or 1.0

    if anneal is not None:
        b_lo, b_hi = anneal[0] / scale, anneal[1] / scale
    else:
        beta = beta if beta is not None else 2.0 / scale
        b_lo = b_hi = beta
    if n_steps is None:
        n_steps = 10 * n                      # 論文設定
    if verbose:
        print(f"  典型 |ΔE| = {scale:.4g}；β {b_lo:.4g} -> {b_hi:.4g}，{n_steps} 步")

    best_H, best_E = H.copy(), E
    stride = max(n_steps // n_trace, 1)
    trace = [E]
    t0 = time.perf_counter()
    n_accept = 0
    for step in range(n_steps):
        b = b_lo * (b_hi / b_lo) ** (step / max(n_steps - 1, 1)) if b_hi != b_lo else b_lo
        H_new, S = propose(H, M)
        E_new, M_new = apply_incremental(H_new, S, M, E)
        dE = E_new - E
        if dE <= 0 or rng.random() <= math.exp(-min(b * dE, 700.0)):
            H, E, M = H_new, E_new, M_new
            n_accept += 1
            if E < best_E:
                best_H, best_E = H.copy(), E
        if (step + 1) % stride == 0:
            trace.append(E)
    dt = time.perf_counter() - t0

    info = {
        "n": n, "n_steps": n_steps, "kind": kind,
        "beta_lo": b_lo, "beta_hi": b_hi, "delta_scale": scale,
        "E_start": E0, "E_best": best_E,
        "drop_pct": (E0 - best_E) / E0 * 100 if E0 else 0.0,
        "accept_rate": n_accept / n_steps,
        "seconds": dt,
        "trace_stride": stride,
    }
    if verbose:
        print(f"  {n_steps} 步、{dt:.2f} 秒，接受率 {info['accept_rate']:.1%}；"
              f"能量 {E0:.4g} -> {best_E:.4g}（下降 {info['drop_pct']:.1f}%）")
    return best_H, trace, info


# ------------------------------------------------------------------ 評估指標

def nearest_neighbour_hue_gap(D, theta, H):
    """每個神經元與它「最近的鄰居」之間的色相差（度）。

    能量是抽象的；這個指標才是人眼真正在意的：擠在一起的兩條神經元，顏色差多少。
    完美的配色會讓每個神經元的最近鄰都是對比色（接近 180 度）。
    """
    n = len(H)
    h = theta[H]
    gaps = []
    for i in range(n):
        d = D[i].copy()
        d[i] = np.inf
        j = int(np.argmin(d))
        dh = abs(h[i] - h[j])
        gaps.append(min(dh, 360.0 - dh))
    return np.array(gaps)


def closest_pairs_hue_gap(D, theta, H, k):
    """全體「最近的 k 對」神經元，各自的色相差（度）。

    和 nearest_neighbour_hue_gap 互補：那個是「每個神經元對它的最近鄰」，
    這個是「整份資料裡最擠的那 k 對」。論文 Fig. 2 比較的其實是後者
    —— 擠在 calyx 尖端的那些細胞。
    """
    n = len(H)
    iu = np.triu_indices(n, 1)
    order = np.argsort(D[iu])[:k]
    h = theta[H]
    dh = np.abs(h[iu[0][order]] - h[iu[1][order]])
    return np.minimum(dh, 360.0 - dh)


def random_baseline(D, theta, n_draw=200, seed=SEED, k=50):
    """隨機配色的基準分布：跑 n_draw 次，看兩個指標的中位數會落在哪。

    只跑一次隨機配色是不夠的 —— 單次抽樣的中位數標準差有 10 度以上，
    很容易誤判成「最佳化有效／無效」。這一步是我在除錯時吃過虧才補上的。

    回傳 (統計, 代表性的隨機組態)。代表性 = 指標中位數最接近整體平均的那一次。
    拿它當「隨機配色」的對照組，比隨手抽一次公平：隨手抽有可能抽到分布上緣，
    讓最佳化看起來毫無進步（我第一次就是這樣被騙的）。
    """
    rng = np.random.default_rng(seed)
    n = D.shape[0]
    draws, nn, cp = [], [], []
    for _ in range(n_draw):
        H = rng.permutation(n)
        draws.append(H)
        nn.append(float(np.median(nearest_neighbour_hue_gap(D, theta, H))))
        cp.append(float(np.median(closest_pairs_hue_gap(D, theta, H, k))))
    nn = np.array(nn)
    rep = int(np.argmin(np.abs(nn - nn.mean())))
    return {
        "n_draw": n_draw,
        "nn_mean": round(float(nn.mean()), 1), "nn_sd": round(float(nn.std()), 1),
        "nn_lo": round(float(nn.min()), 1), "nn_hi": round(float(nn.max()), 1),
        "cp_mean": round(float(np.mean(cp)), 1), "cp_sd": round(float(np.std(cp)), 1),
        "representative_nn": round(float(nn[rep]), 1),
    }, draws[rep]


# ----------------------------------------------------------------------- main

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    print("[步驟 1] 對位：把 100 個神經元放進同一組標準腦座標")
    neurons, origin, dims = load_neurons()
    n = len(neurons)
    theta = hue_table(n)

    print("[步驟 2] 距離矩陣：每個神經元抽 100 個體素")
    D, t_dist = distance_matrix(neurons)

    print("[基準] 隨機配色跑 200 次，先量出「什麼叫沒有進步」")
    base, H_random = random_baseline(D, theta)
    print(f"  每元最近鄰色相差中位數 {base['nn_mean']}° ± {base['nn_sd']}°"
          f"（{base['nn_lo']}~{base['nn_hi']}）；"
          f"取中位數 {base['representative_nn']}° 的那次當代表")

    def run_multi(tag, seeds=range(N_SEEDS), **kw):
        """跑多個種子，回傳 (最低能量的組態, 那次的軌跡, 那次的 info, 統計)。

        單跑一次就下結論會被雜訊騙 —— 隨機基準的中位數標準差有 10 度以上。
        論文說「取整個過程中能量最低的組態」，這裡把它延伸成「跨重啟取最低」。
        """
        runs = [monte_carlo(D, seed=s, verbose=False, **kw) for s in seeds]
        meds = [float(np.median(nearest_neighbour_hue_gap(D, theta, H)))
                for H, _, _ in runs]
        best = int(np.argmin([inf["E_best"] for _, _, inf in runs]))
        stat = {
            "seeds": len(runs),
            "E_mean": float(np.mean([i["E_best"] for _, _, i in runs])),
            "drop_mean": float(np.mean([i["drop_pct"] for _, _, i in runs])),
            "nn_mean": round(float(np.mean(meds)), 1),
            "nn_sd": round(float(np.std(meds)), 1),
            "seconds_mean": float(np.mean([i["seconds"] for _, _, i in runs])),
        }
        print(f"  {tag}：{len(runs)} 個種子，能量降幅 {stat['drop_mean']:.1f}%，"
              f"最近鄰色相差 {stat['nn_mean']}° ± {stat['nn_sd']}°")
        H, tr, inf = runs[best]
        return H, tr, inf, stat

    print(f"[步驟 5a] 照論文設定：固定溫度、10N = {10 * n} 步")
    H_paper, trace_paper, info_paper, stat_paper = run_multi("論文設定", n_steps=10 * n)

    print(f"[步驟 5b] 改成退火、加長到 2000N = {2000 * n} 步")
    H_long, trace_long, info_long, stat_long = run_multi(
        "退火加長", n_steps=2000 * n, anneal=(1, 1000))

    print("[反例] 用知識庫抄錯的公式跑一次，看會得到什麼")
    H_misread, trace_misread, info_misread, stat_misread = run_multi(
        "抄錯公式", seeds=range(3), n_steps=2000 * n, anneal=(1, 1000), kind="misread")

    # --- 四種配色模式（論文步驟 3）
    # H_random 已經由 random_baseline() 挑出代表性的那一次
    H_kaleido = H_long                                # color by distance
    # color by file：依神經傳導物質分組上色（論文的「依生物意義配色」）
    drivers = sorted({nu.driver for nu in neurons})
    by_driver = {d: i for i, d in enumerate(drivers)}
    hue_by_nt = np.array([by_driver[nu.driver] * 360.0 / len(drivers)
                          for nu in neurons])

    gap_random = nearest_neighbour_hue_gap(D, theta, H_random)
    gap_paper = nearest_neighbour_hue_gap(D, theta, H_paper)
    gap_kaleido = nearest_neighbour_hue_gap(D, theta, H_kaleido)
    gap_misread = nearest_neighbour_hue_gap(D, theta, H_misread)
    cp = {k: {name: round(float(np.median(closest_pairs_hue_gap(D, theta, Hx, k))), 1)
              for name, Hx in (("random", H_random), ("paper10N", H_paper),
                               ("kaleido", H_kaleido), ("misread", H_misread))}
          for k in (50, 200, 1000)}

    print(f"\n  每元最近鄰色相差中位數：隨機 {np.median(gap_random):.1f}°"
          f" -> 論文10N {np.median(gap_paper):.1f}°"
          f" -> 退火 {np.median(gap_kaleido):.1f}°"
          f"（抄錯版 {np.median(gap_misread):.1f}°）")
    print(f"  最近 50 對色相差中位數：{cp[50]}")

    records = []
    for i, nu in enumerate(neurons):
        cx, cy, cz = nu.centroid
        records.append({
            "idx": i,
            "id": nu.nid,
            "driver": nu.driver,
            "sex": nu.sex,
            "cell": nu.cell,
            "nt_zh": NEUROTRANSMITTER.get(nu.driver, ("—", "—"))[0],
            "nt_en": NEUROTRANSMITTER.get(nu.driver, ("—", "—"))[1],
            "voxels": nu.n_voxels,
            "src_dims": nu.src_dims,
            "src_bytes": nu.src_bytes,
            "centroid": [round(cx, 1), round(cy, 1), round(cz, 1)],
            "hue_kaleido": round(float(theta[H_kaleido[i]]), 2),
            "hue_random": round(float(theta[H_random[i]]), 2),
            "hue_nt": round(float(hue_by_nt[i]), 2),
            "hue_paper10N": round(float(theta[H_paper[i]]), 2),
            "hue_misread": round(float(theta[H_misread[i]]), 2),
            "gap_kaleido": round(float(gap_kaleido[i]), 1),
            "gap_random": round(float(gap_random[i]), 1),
        })

    (DATA_DIR / "neurons.json").write_text(json.dumps({
        "origin": list(origin), "dims": list(dims),
        "drivers": drivers,
        "neurons": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (DATA_DIR / "energy.json").write_text(json.dumps({
        "seed": SEED, "sample_voxels": SAMPLE_VOXELS,
        "t_distance_matrix": round(t_dist, 3),
        "random_baseline": base,
        "paper_10N": {"info": info_paper, "trace": trace_paper, "stat": stat_paper},
        "annealed": {"info": info_long, "trace": trace_long, "stat": stat_long},
        "misread": {"info": info_misread, "trace": trace_misread, "stat": stat_misread},
        "closest_pairs_median": cp,
        "gap": {
            "random": [round(float(x), 1) for x in gap_random],
            "paper10N": [round(float(x), 1) for x in gap_paper],
            "kaleido": [round(float(x), 1) for x in gap_kaleido],
            "misread": [round(float(x), 1) for x in gap_misread],
            "median_random": round(float(np.median(gap_random)), 1),
            "median_paper10N": round(float(np.median(gap_paper)), 1),
            "median_kaleido": round(float(np.median(gap_kaleido)), 1),
            "median_misread": round(float(np.median(gap_misread)), 1),
        },
        "distance_stats": {
            "min": round(float(D[D > 0].min()), 2),
            "max": round(float(D.max()), 2),
            "median": round(float(np.median(D[D > 0])), 2),
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    np.save(DATA_DIR / "distance.npy", D)
    print(f"\n完成 -> {DATA_DIR}")


if __name__ == "__main__":
    main()
