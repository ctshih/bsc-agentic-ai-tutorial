"""
render.py — 把配色結果畫成圖（論文 Methods 步驟 1、6、7）
==========================================================
論文的第二個主張在這裡實現：把 N 個神經元合併成「單一張」影像。

    步驟 1 的重疊規則  -> 一個體素被多個神經元佔據時，只留訊號最強的那個
    步驟 6 的 HSV→RGBA -> 色相由配色決定、飽和度固定 1、明度是正規化強度、α 取自強度
    步驟 7 的合併      -> 全部寫進同一個畫布

實作上用「點雲潑濺（splatting）」而不是先建立稠密體積：
把所有神經元的非零體素排成一串，依強度**由小到大**排序後依序寫入畫布，
後寫入的自然覆蓋先寫入的 —— 一行陣列指派就同時完成了「取最大值」與論文的
重疊規則。28,823,759 個體素在幾秒內畫完，不需要 166,000,000 格的稠密陣列。

輸出：
    images/mip_<mode>_<view>.png   四種配色模式 × 三個視角
    images/zoom_<mode>.png         最擁擠區域的放大對照（論文 Fig. 2b/2c）
    images/spin_kaleido.webp       繞 Y 軸旋轉動畫
    data/render.json               尺寸與檔案大小
"""

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from matplotlib.colors import hsv_to_rgb

from kaleido import load_neurons, DATA_DIR

ROOT = Path(__file__).resolve().parent
IMG_DIR = ROOT / "images"

GAMMA = 0.5            # 提亮細突起，與 EP03 三視圖一致
BAR_VOXELS = 100       # 比例尺長度（本批資料體素間距 = 1.0）
MODES = ["kaleido", "random", "nt", "misread"]
MODE_LABEL = {
    "kaleido": "Kaleido 自動配色（color by distance）",
    "random":  "隨機配色（random color）",
    "nt":      "依神經傳導物質配色（color by file）",
    "misread": "用抄錯的公式最佳化",
}
SPIN_FRAMES = 36
SPIN_MS = 70
SPIN_MAX_PX = 700
SPIN_STRIDE = 2        # 動畫每 2 個體素取 1 個，換取速度；靜態圖仍用全部


# ------------------------------------------------------------------ 畫布工具

def splat(px, py, val, hue, W, H, gamma=GAMMA):
    """把一堆帶色相的點潑到 W×H 畫布上，強度大的蓋過強度小的。

    px, py 必須已經是畫布內的整數索引；val 是 0~1 的強度；hue 是 0~360 的色相角。
    回傳 uint8 的 RGB 影像。
    """
    order = np.argsort(val, kind="stable")          # 由暗到亮
    idx = (py[order] * W + px[order]).astype(np.intp)
    v = val[order]
    h = hue[order]

    buf_h = np.zeros(W * H, dtype=np.float32)
    buf_v = np.zeros(W * H, dtype=np.float32)
    buf_h[idx] = h                                   # 後寫入者勝 = 取最亮
    buf_v[idx] = v

    hsv = np.stack([
        (buf_h / 360.0).reshape(H, W),
        np.where(buf_v.reshape(H, W) > 0, 1.0, 0.0),  # 飽和度固定 1（空白處給 0 才是黑）
        (buf_v.reshape(H, W) ** gamma),
    ], axis=-1)
    return (hsv_to_rgb(hsv) * 255).astype(np.uint8)


def add_scalebar(rgb):
    h, w = rgb.shape[:2]
    if w > BAR_VOXELS + 20:
        rgb[h - 12:h - 9, 10:10 + BAR_VOXELS] = 255
    return rgb


# --------------------------------------------------------------------- 主流程

def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    meta = json.loads((DATA_DIR / "neurons.json").read_text(encoding="utf-8"))
    energy = json.loads((DATA_DIR / "energy.json").read_text(encoding="utf-8"))
    ox, oy, oz = meta["origin"]
    nx, ny, nz = meta["dims"]

    print("載入神經元點雲…")
    neurons, _, _ = load_neurons(verbose=False)
    assert [n.nid for n in neurons] == [r["id"] for r in meta["neurons"]]

    # 攤平成一整串點，並記住每個點屬於誰
    gx = np.concatenate([n.gx for n in neurons]) - ox
    gy = np.concatenate([n.gy for n in neurons]) - oy
    gz = np.concatenate([n.gz for n in neurons]) - oz
    val = np.concatenate([n.val for n in neurons])
    owner = np.concatenate([np.full(n.n_voxels, i, dtype=np.int32)
                            for i, n in enumerate(neurons)])
    print(f"  合計 {val.size:,} 個體素，畫布 {nx}×{ny}×{nz}")

    hues = {m: np.array([r[f"hue_{m}"] for r in meta["neurons"]], dtype=np.float32)
            for m in MODES}

    info = {"dims": [nx, ny, nz], "voxels": int(val.size), "images": {}}

    # --- 三視圖 × 四種模式
    views = {
        "xy": (gx, gy, nx, ny),        # 沿 z 投影
        "xz": (gx, gz, nx, nz),        # 沿 y 投影
        "zy": (gz, gy, nz, ny),        # 沿 x 投影
    }
    for mode in MODES:
        hue_pt = hues[mode][owner]
        for vname, (a, b, W, H) in views.items():
            rgb = add_scalebar(splat(a, b, val, hue_pt, W, H))
            p = IMG_DIR / f"mip_{mode}_{vname}.png"
            Image.fromarray(rgb).save(p, optimize=True)
            info["images"][p.name] = {"px": [W, H], "kb": round(p.stat().st_size / 1024, 1)}
        print(f"  {mode:8s} 三視圖完成")

    # --- 最擁擠區域放大（論文 Fig. 2b/2c）
    #
    # 論文挑的是 calyx 尖端 —— Kenyon cells 的**細胞本體**擠成一團的地方。
    # 先替每條神經元定位它的細胞本體：取最亮的那一小撮體素的中位數位置。
    # （細胞本體是實心的一團，訊號最強；細突起再細再暗也不會贏過它。）
    soma = []
    for i, nu in enumerate(neurons):
        thr = np.quantile(nu.val, 0.999)
        m = nu.val >= thr
        soma.append((float(np.median(nu.gx[m])) - ox,
                     float(np.median(nu.gy[m])) - oy,
                     float(np.median(nu.gz[m])) - oz))
    soma = np.array(soma)

    # 只在 x-y 找窗格是不夠的：XY 投影會把整個 238 體素深度的細突起全疊上來，
    # 疊出來就是一片彩色雜訊。論文看的 calyx 尖端是薄薄一層，所以這裡也要
    # 限制一個 z 方向的薄片（slab），只畫落在薄片裡的體素。
    ZW = ZH = 200
    SLAB = 40
    STEP = 10
    best, best_box = -1, (0, 0, 0)
    for wy in range(0, ny - ZH, STEP):
        m0 = (soma[:, 1] >= wy) & (soma[:, 1] < wy + ZH)
        if not m0.any():
            continue
        for wx in range(0, nx - ZW, STEP):
            m1 = m0 & (soma[:, 0] >= wx) & (soma[:, 0] < wx + ZW)
            if not m1.any():
                continue
            for wz in range(0, nz - SLAB, STEP):
                c = int((m1 & (soma[:, 2] >= wz) & (soma[:, 2] < wz + SLAB)).sum())
                if c > best:
                    best, best_box = c, (wx, wy, wz)
    cx0, cy0, cz0 = best_box
    cx1, cy1, cz1 = cx0 + ZW - 1, cy0 + ZH - 1, cz0 + SLAB - 1
    print(f"  細胞本體最密集的薄片：x{cx0}-{cx1} y{cy0}-{cy1} z{cz0}-{cz1}，"
          f"含 {best} 顆細胞本體")

    # 放大圖只畫夠亮的體素：把糾纏成雜訊的細突起濾掉，留下細胞本體與粗主幹，
    # 才對得上論文 Fig. 2b/2c 那種「一顆一顆看得出來」的比較。
    ZTHR = 0.35
    zsel = ((gx >= cx0) & (gx <= cx1) & (gy >= cy0) & (gy <= cy1)
            & (gz >= cz0) & (gz <= cz1) & (val >= ZTHR))
    zx, zy, zv, zo = gx[zsel] - cx0, gy[zsel] - cy0, val[zsel], owner[zsel]
    # 論文 Fig. 2c 用箭頭標出「隨機配色下不巧撞色」的相鄰細胞本體。這裡把那些
    # 位置自動找出來：薄片內距離夠近、而且在隨機配色下色相差夠小的細胞本體對。
    in_box = np.where((soma[:, 0] >= cx0) & (soma[:, 0] <= cx1)
                      & (soma[:, 1] >= cy0) & (soma[:, 1] <= cy1)
                      & (soma[:, 2] >= cz0) & (soma[:, 2] <= cz1))[0]
    NEAR, SAME = 30.0, 30.0
    clashes = []
    for a_i in range(len(in_box)):
        for b_i in range(a_i + 1, len(in_box)):
            a, b = int(in_box[a_i]), int(in_box[b_i])
            dist = float(np.hypot(*(soma[a, :2] - soma[b, :2])))
            if dist > NEAR:
                continue
            dh_r = abs(hues["random"][a] - hues["random"][b])
            dh_r = min(dh_r, 360 - dh_r)
            if dh_r > SAME:
                continue
            dh_k = abs(hues["kaleido"][a] - hues["kaleido"][b])
            dh_k = min(dh_k, 360 - dh_k)
            clashes.append({"pair": [neurons[a].nid, neurons[b].nid],
                            "dist": round(dist, 1),
                            "hue_gap_random": round(float(dh_r), 1),
                            "hue_gap_kaleido": round(float(dh_k), 1),
                            "xy": [float((soma[a, 0] + soma[b, 0]) / 2 - cx0),
                                   float((soma[a, 1] + soma[b, 1]) / 2 - cy0)]})
    print(f"  隨機配色在這個薄片裡有 {len(clashes)} 對「近又同色」的細胞本體：")
    for c in clashes:
        print(f"    {c['pair'][0]} / {c['pair'][1]}  相距 {c['dist']} 體素，"
              f"色相差 隨機 {c['hue_gap_random']}° -> Kaleido {c['hue_gap_kaleido']}°")
    info["clashes"] = clashes

    ZOOM = 3                       # 放大倍率，讓細節在網頁上看得清楚
    for mode in ("kaleido", "random", "misread"):
        rgb = splat(zx, zy, zv, hues[mode][zo], ZW, ZH, gamma=0.7)
        im = Image.fromarray(rgb).resize((ZW * ZOOM, ZH * ZOOM), Image.LANCZOS)
        if mode in ("kaleido", "random"):
            dr = ImageDraw.Draw(im)
            for c in clashes:
                cxp, cyp = c["xy"][0] * ZOOM, c["xy"][1] * ZOOM
                r = 26
                dr.ellipse([cxp - r, cyp - r, cxp + r, cyp + r],
                           outline=(255, 255, 255), width=3)
        p = IMG_DIR / f"zoom_{mode}.png"
        im.save(p, optimize=True)
        info["images"][p.name] = {"px": [ZW * ZOOM, ZH * ZOOM],
                                  "kb": round(p.stat().st_size / 1024, 1)}
    info["zoom"] = {"box": [cx0, cy0, cz0, cx1, cy1, cz1], "n_somas": int(best),
                    "threshold": ZTHR, "zoom": ZOOM, "size": [ZW, ZH], "slab": SLAB}
    print(f"  放大對照完成（{ZW}×{ZH} -> {ZW * ZOOM}×{ZH * ZOOM}）")

    # --- 旋轉動畫（繞 Y 軸）
    print("  產生旋轉動畫…")
    sx = gx[::SPIN_STRIDE].astype(np.float32)
    sz = gz[::SPIN_STRIDE].astype(np.float32)
    sy = gy[::SPIN_STRIDE].astype(np.intp)
    sv = val[::SPIN_STRIDE]
    sh = hues["kaleido"][owner[::SPIN_STRIDE]]
    ccx, ccz = (nx - 1) / 2.0, (nz - 1) / 2.0
    dx, dz = sx - ccx, sz - ccz
    W = int(math.ceil(math.hypot(nx, nz))) + 2
    half = W / 2.0

    frames = []
    for k in range(SPIN_FRAMES):
        th = 2 * math.pi * k / SPIN_FRAMES
        c, s = math.cos(th), math.sin(th)
        # floor(x+0.5) 而不是 np.rint：rint 的銀行家捨入會在 90 度產生梳狀條紋
        u = np.floor(dx * c + dz * s + half + 0.5).astype(np.intp)
        np.clip(u, 0, W - 1, out=u)
        rgb = splat(u, sy, sv, sh, W, ny)
        frames.append(rgb)
    stack = np.stack(frames)
    nzc = np.any(stack.sum(-1) > 0, axis=0)
    cols = np.where(nzc.any(axis=0))[0]
    rows = np.where(nzc.any(axis=1))[0]
    x0, x1 = max(cols.min() - 6, 0), min(cols.max() + 7, W)
    y0, y1 = max(rows.min() - 6, 0), min(rows.max() + 7, ny)
    scale = min(1.0, SPIN_MAX_PX / max(x1 - x0, y1 - y0))
    size = (max(int((x1 - x0) * scale), 1), max(int((y1 - y0) * scale), 1))
    imgs = [Image.fromarray(add_scalebar(f[y0:y1, x0:x1].copy())).resize(size, Image.LANCZOS)
            for f in frames]
    spin = IMG_DIR / "spin_kaleido.webp"
    imgs[0].save(spin, format="WEBP", save_all=True, append_images=imgs[1:],
                 duration=SPIN_MS, loop=0, quality=80, method=4)
    info["images"][spin.name] = {"px": list(size), "frames": SPIN_FRAMES,
                                 "kb": round(spin.stat().st_size / 1024, 1)}
    print(f"  動畫 {size[0]}×{size[1]}，{spin.stat().st_size / 1024:.0f} KB")

    (DATA_DIR / "render.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(v["kb"] for v in info["images"].values())
    print(f"\n完成 {len(info['images'])} 張圖，合計 {total / 1024:.1f} MB -> {IMG_DIR}")


if __name__ == "__main__":
    main()
