"""
render_spin.py — 產生「繞 Y 軸旋轉」的 MIP 動畫（每個神經元一個 .webp）
----------------------------------------------------------------------
轉軸：Y 方向（畫面的垂直軸），通過影像檔的正中央 (nx/2, nz/2)。

為什麼用點雲而不是旋轉整個陣列：
    最直覺的做法是 scipy.ndimage.rotate(volume, angle, axes=(0,2))，但那要對
    每個體素做三維內插；最大的檔有 6200 萬個體素，乘上 36 個角度 × 20 個神經元
    根本跑不完。而這批資料非零體素只佔 0.5%~4%（約 30 萬個點），
    所以改成：取出非零點 -> 對點做旋轉 -> 投影到畫面取最大值（max splatting）。
    正交投影下這和「旋轉體積再做 MIP」在數學上等價，但快了兩個數量級。

取最大值的技巧：
    先把所有點依強度「由小到大」排序，投影時直接用陣列指派 frame[idx] = value。
    後寫入的會覆蓋先寫入的，而強度大的排在後面，所以最後留下的自然是最大值——
    比 np.maximum.at 快得多。

輸出：
    images/<id>_spin.webp   （36 格、循環播放）
    data/spin.json          （尺寸資訊，給 build_page.py 排版用）
"""

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from matplotlib import colormaps

from amread import read_am

SRC = Path(__file__).resolve().parent.parent / "FCdata" / "neurons"
OUT = Path(__file__).resolve().parent
IMG_DIR = OUT / "images"
DATA_DIR = OUT / "data"

N_FRAMES = 36          # 每 10 度一格，轉滿一圈
FRAME_MS = 60          # 每格停留毫秒 -> 一圈約 2.2 秒
GAMMA = 0.5            # 與靜態三視圖一致
CLIP_PCT = 99.5        # 與靜態三視圖一致
MARGIN = 6             # 裁掉四周空白時保留的邊界
MAX_PX = 480           # 輸出動畫的最長邊上限（控制檔案大小）
BAR_VOXELS = 100       # 比例尺長度
WEBP_QUALITY = 80

CMAP = colormaps["inferno"]


def spin_frames(vol):
    """回傳 (frames, crop_w, crop_h)。frames 為 list of 2D uint16 陣列。"""
    data = vol.data                       # (z, y, x)
    nz, ny, nx = data.shape

    zs, ys, xs = np.nonzero(data)
    vals = data[zs, ys, xs]

    # 依強度由小到大排序：後寫入者覆蓋先寫入者 => 最終留下最大值
    order = np.argsort(vals, kind="stable")
    zs, ys, xs, vals = zs[order], ys[order], xs[order], vals[order]

    # 轉軸通過影像檔中央
    cx, cz = (nx - 1) / 2.0, (nz - 1) / 2.0
    dx = xs.astype(np.float32) - cx
    dz = zs.astype(np.float32) - cz

    # 旋轉時 x 會掃過的最大範圍 = 對角線長度
    W = int(math.ceil(math.hypot(nx, nz))) + 2
    half = W / 2.0
    rows = ys.astype(np.intp)

    frames, umin, umax = [], W, 0
    for k in range(N_FRAMES):
        th = 2 * math.pi * k / N_FRAMES
        c, s = math.cos(th), math.sin(th)
        # 注意：這裡不能用 np.rint。rint 是「銀行家捨入」（.5 捨入到最近的偶數），
        # 而當 nz（或 nx）是偶數時中心點是半整數，轉到 90 度會讓所有座標剛好落在 .5，
        # 於是奇數欄永遠沒人寫入 -> 畫面出現梳狀縱條紋。
        # floor(x + 0.5) 是固定方向的四捨五入，沒有平手問題，也不會犧牲銳利度。
        u = np.floor(dx * c + dz * s + half + 0.5).astype(np.intp)
        np.clip(u, 0, W - 1, out=u)

        buf = np.zeros(ny * W, dtype=np.uint16)
        buf[rows * W + u] = vals          # 排序過，所以這一行就等於取 max
        frames.append(buf.reshape(ny, W))

        umin, umax = min(umin, int(u.min())), max(umax, int(u.max()))

    # 所有格共用同一個裁切框，動畫才不會抖動
    y0, y1 = max(int(ys.min()) - MARGIN, 0), min(int(ys.max()) + MARGIN + 1, ny)
    x0, x1 = max(umin - MARGIN, 0), min(umax + MARGIN + 1, W)
    frames = [f[y0:y1, x0:x1] for f in frames]
    return frames, x1 - x0, y1 - y0


def colorize(frame, vmax, out_size):
    v = np.clip(frame.astype(np.float32) / vmax, 0.0, 1.0) ** GAMMA
    rgb = (CMAP(v)[..., :3] * 255).astype(np.uint8)

    h, w = rgb.shape[:2]
    if w > BAR_VOXELS + 20:              # 左下角比例尺 = 100 voxel
        rgb[h - 11:h - 8, 8:8 + BAR_VOXELS] = 255

    im = Image.fromarray(rgb)
    if out_size != (w, h):
        im = im.resize(out_size, Image.LANCZOS)
    return im


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    info = {}
    for f in sorted(SRC.glob("*.am")):
        nid = f.stem.split("_")[0]
        vol = read_am(f)
        frames, cw, ch = spin_frames(vol)

        # 亮度基準取第 0 格（角度 0 就是 XY 投影），讓動畫與靜態圖亮度一致，
        # 且整段動畫共用同一個基準，不會閃爍。
        first = frames[0]
        nzv = first[first > 0]
        vmax = max(float(np.percentile(nzv, CLIP_PCT)), 1.0)

        scale = min(1.0, MAX_PX / max(cw, ch))
        out_size = (max(int(round(cw * scale)), 1), max(int(round(ch * scale)), 1))

        imgs = [colorize(fr, vmax, out_size) for fr in frames]
        path = IMG_DIR / f"{nid}_spin.webp"
        imgs[0].save(path, format="WEBP", save_all=True, append_images=imgs[1:],
                     duration=FRAME_MS, loop=0, quality=WEBP_QUALITY, method=4)

        kb = path.stat().st_size / 1024
        info[nid] = {"w": cw, "h": ch, "px": list(out_size),
                     "frames": N_FRAMES, "ms": FRAME_MS, "kb": round(kb, 1)}
        print(f"{nid:24s} 畫布 {cw}×{ch} -> {out_size[0]}×{out_size[1]} px, {kb:6.1f} KB")

    (DATA_DIR / "spin.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(v["kb"] for v in info.values())
    print(f"\n完成 {len(info)} 個動畫，合計 {total/1024:.1f} MB -> {IMG_DIR}")


if __name__ == "__main__":
    main()
