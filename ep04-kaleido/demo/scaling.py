"""
scaling.py — 驗證論文的第二個主張：記憶體與檔案大小和神經元數量脫鉤
====================================================================
論文說：

  * 合併後的單一 RGBA 影像，大小「只由標準腦解析度決定」，與神經元數量幾乎無關。
  * 執行時間在 N ≤ 2000 時由檔案 I/O 主導而呈線性，更大時由蒙地卡羅主導而呈 O(N²)。
  * 若不合併，光是把 FlyCircuit 約 130,000 個神經元載入就需要 10 TB 等級記憶體。

這支程式在 N = 10, 25, 50, 100 上實際量測，把上面三句話逐條對照。

關鍵設計：**標準腦網格固定**（用全部 100 個神經元的聯集範圍），不隨 N 改變。
論文的主張正是「大小由標準腦解析度決定」，所以網格不能跟著 N 縮小，否則就是
自己餵自己想要的答案。

輸出：data/scaling.json（圖表交給 charts.py 畫）
"""

import json
import time
from pathlib import Path

import numpy as np
from matplotlib.colors import hsv_to_rgb

from kaleido import (SRC, DATA_DIR, load_neurons, distance_matrix,
                     monte_carlo, hue_table)

ROOT = Path(__file__).resolve().parent
IMG_DIR = ROOT / "images"
TMP = ROOT / "_tmp_merged"

NS = [10, 25, 50, 100]


def merged_volume_bytes(grid, hues, neurons, origin, write_to=None):
    """真的把 N 個神經元合併成一個 RGBA 體積，回傳 (位元組數, 耗時秒)。

    論文步驟 1 的重疊規則（同一體素只留最強訊號）在這裡實現：把所有體素依強度
    由小到大排序後寫入，後寫入者覆蓋先寫入者。
    """
    nx, ny, nz = grid
    ox, oy, oz = origin
    t0 = time.perf_counter()

    gx = np.concatenate([n.gx for n in neurons]) - ox
    gy = np.concatenate([n.gy for n in neurons]) - oy
    gz = np.concatenate([n.gz for n in neurons]) - oz
    val = np.concatenate([n.val for n in neurons])
    owner = np.concatenate([np.full(n.n_voxels, i, dtype=np.int32)
                            for i, n in enumerate(neurons)])

    order = np.argsort(val, kind="stable")
    idx = ((gz[order].astype(np.int64) * ny + gy[order]) * nx + gx[order])
    v = val[order]
    h = hues[owner[order]]

    buf_h = np.zeros(nx * ny * nz, dtype=np.float32)
    buf_v = np.zeros(nx * ny * nz, dtype=np.float32)
    buf_h[idx] = h
    buf_v[idx] = v

    # HSV -> RGBA：色相已定、飽和度 1、明度＝正規化強度、α 也取強度
    hsv = np.stack([buf_h / 360.0, np.where(buf_v > 0, 1.0, 0.0), buf_v], axis=-1)
    rgb = (hsv_to_rgb(hsv) * 255).astype(np.uint8)
    rgba = np.concatenate([rgb, (buf_v * 255).astype(np.uint8)[:, None]], axis=1)
    dt = time.perf_counter() - t0

    nbytes = int(rgba.nbytes)
    if write_to is not None:
        write_to.parent.mkdir(parents=True, exist_ok=True)
        rgba.tofile(write_to)
        nbytes = write_to.stat().st_size
    del buf_h, buf_v, hsv, rgb, rgba
    return nbytes, dt


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # 固定的標準腦網格：用全部 100 個神經元的聯集範圍算一次，之後都不變
    print("先用全部 100 個神經元決定標準腦網格…")
    all_neurons, origin, grid = load_neurons(verbose=False)
    nx, ny, nz = grid
    voxels = nx * ny * nz
    print(f"  網格 {nx}×{ny}×{nz} = {voxels:,} 格；"
          f"RGBA 需要 {voxels * 4 / 1e6:.0f} MB（與 N 無關）")

    rows = []
    for N in NS:
        print(f"\n=== N = {N} ===")
        t0 = time.perf_counter()
        neurons, _, _ = load_neurons(limit=N, verbose=False)
        t_load = time.perf_counter() - t0

        src_bytes = sum(n.src_bytes for n in neurons)
        dense_bytes = sum(int(np.prod(n.src_dims)) * 2 for n in neurons)  # ushort
        vox = sum(n.n_voxels for n in neurons)

        D, t_dist = distance_matrix(neurons, verbose=False)
        H, _, info = monte_carlo(D, n_steps=10 * N, verbose=False)   # 論文步數
        theta = hue_table(N)
        hues = theta[H].astype(np.float32)

        out = TMP / f"merged_{N}.raw"
        merged_bytes, t_merge = merged_volume_bytes(grid, hues, neurons, origin,
                                                    write_to=out)
        out.unlink()

        rows.append({
            "N": N,
            "src_mb": round(src_bytes / 1e6, 1),
            "dense_mb": round(dense_bytes / 1e6, 1),
            "voxels": vox,
            "merged_mb": round(merged_bytes / 1e6, 1),
            "t_load": round(t_load, 2),
            "t_dist": round(t_dist, 3),
            "t_mc": round(info["seconds"], 3),
            "t_merge": round(t_merge, 2),
        })
        r = rows[-1]
        print(f"  原始 .am 檔 {r['src_mb']} MB；若各自展開成稠密體積 {r['dense_mb']} MB")
        print(f"  合併後單一 RGBA {r['merged_mb']} MB")
        print(f"  載入 {r['t_load']}s／距離矩陣 {r['t_dist']}s／"
              f"蒙地卡羅 {r['t_mc']}s／合併 {r['t_merge']}s")

    if TMP.exists():
        TMP.rmdir()

    # --- 外推：論文說 130,000 個神經元光載入就要 10 TB 等級
    per_neuron_dense = np.mean([r["dense_mb"] / r["N"] for r in rows])
    extrapolate = {
        "per_neuron_dense_mb": round(float(per_neuron_dense), 1),
        "n_flycircuit": 130000,
        "naive_tb": round(float(per_neuron_dense * 130000 / 1e6), 2),
        "merged_mb": rows[-1]["merged_mb"],
    }
    print(f"\n外推到 FlyCircuit 全腦 130,000 個神經元：")
    print(f"  各自展開 {extrapolate['naive_tb']} TB；合併後仍是 "
          f"{extrapolate['merged_mb']} MB（同一個標準腦網格）")

    # --- 蒙地卡羅的複雜度：對 N 取對數斜率
    Ns = np.array([r["N"] for r in rows], dtype=float)
    tmc = np.array([r["t_mc"] for r in rows], dtype=float)
    slope = float(np.polyfit(np.log(Ns), np.log(tmc), 1)[0])
    print(f"  蒙地卡羅時間 ~ N^{slope:.2f}（論文預期 N²；步數 10N × 每步 O(N)）")

    result = {"grid": [nx, ny, nz], "grid_voxels": int(voxels),
              "rows": rows, "extrapolate": extrapolate,
              "mc_exponent": round(slope, 2)}
    (DATA_DIR / "scaling.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")



if __name__ == "__main__":
    main()
