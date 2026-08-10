"""
render_mip.py — 把每個神經元體積畫成三視圖（最大強度投影 MIP）
--------------------------------------------------------------
為什麼用 MIP 而不是切片：神經元是稀疏的立體樹狀結構（非零 voxel 只佔 2~4%），
隨便切一刀通常只切到零星幾段，看不出形態；沿著一個軸取「每條射線上的最大值」
才能把整棵樹壓成一張看得懂的圖。這也是共軛焦顯微鏡影像最常見的呈現方式。

三個投影方向（資料索引順序是 v[z, y, x]）：
    XY = 沿 z 投影（max over axis 0）→ 影像 (y, x)
    XZ = 沿 y 投影（max over axis 1）→ 影像 (z, x)
    ZY = 沿 x 投影（max over axis 2）→ 影像 (z, y)，輸出時轉置成 (y, z)

輸出：
    images/<id>_xy.png / _xz.png / _zy.png
    data/summary.json   （給 build_page.py 組網頁用）
"""

import json
import re
from pathlib import Path

import numpy as np
from PIL import Image
from matplotlib import colormaps

from amread import read_am

SRC = Path(__file__).resolve().parent.parent / "FCdata" / "neurons"
OUT = Path(__file__).resolve().parent
IMG_DIR = OUT / "images"
DATA_DIR = OUT / "data"

CMAP = colormaps["inferno"]   # 黑底暖色，適合表現螢光強度
GAMMA = 0.5                   # < 1 會把暗的細突起提亮，否則只看得到主幹
CLIP_PCT = 99.5               # 用 99.5 百分位當白點，避免單一極亮 voxel 壓掉整張圖
MARGIN = 4                    # 裁切時四周留的 voxel 邊界
BAR_VOXELS = 100              # 比例尺長度（voxel 數；本批資料 voxel 間距 = 1.0）

# 檔名裡的 driver line（基因驅動品系）-> 它標記的神經傳導物質
NEUROTRANSMITTER = {
    "TH":    ("多巴胺", "Dopamine"),
    "Tdc2":  ("章魚胺", "Octopamine"),
    "Trh":   ("血清素", "Serotonin"),
    "VGlut": ("麩胺酸", "Glutamate"),
    "Gad1":  ("GABA", "GABA"),
    "fru":   ("fruitless（性別二型迴路）", "fruitless"),
}


def parse_name(stem):
    """Gad1-F-400376_seg001_warp_volume -> driver, sex, cell id"""
    m = re.match(r"([A-Za-z0-9]+)-([FM])-(\d+)", stem)
    if not m:
        return stem, "?", ""
    return m.group(1), m.group(2), m.group(3)


def to_png(plane, path):
    """把一張 2D 投影正規化、上色、加比例尺，存成 PNG。"""
    v = plane.astype(np.float32)
    nzv = v[v > 0]
    vmax = float(np.percentile(nzv, CLIP_PCT)) if nzv.size else 1.0
    vmax = max(vmax, 1.0)
    v = np.clip(v / vmax, 0.0, 1.0) ** GAMMA

    rgb = (CMAP(v)[..., :3] * 255).astype(np.uint8)

    # 左下角比例尺：白色實心橫棒，長度 = BAR_VOXELS 個 voxel
    h, w = rgb.shape[:2]
    if w > BAR_VOXELS + 20:
        y1, y0 = h - 8, h - 11
        x0, x1 = 8, 8 + BAR_VOXELS
        rgb[y0:y1, x0:x1] = 255

    Image.fromarray(rgb).save(path)
    return w, h


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    for f in sorted(SRC.glob("*.am")):
        vol = read_am(f)
        data = vol.data
        stem = f.stem                       # e.g. Gad1-F-400376_seg001_warp_volume
        nid = stem.split("_")[0]            # e.g. Gad1-F-400376
        driver, sex, cell = parse_name(stem)

        nonzero = data > 0
        n_nonzero = int(nonzero.sum())

        # 先在 3D 裡裁掉四周的空白，三個視圖才會是同一塊區域、看起來一致
        zs, ys, xs = np.where(nonzero)
        nz, ny, nx = data.shape
        z0, z1 = max(int(zs.min()) - MARGIN, 0), min(int(zs.max()) + MARGIN + 1, nz)
        y0, y1 = max(int(ys.min()) - MARGIN, 0), min(int(ys.max()) + MARGIN + 1, ny)
        x0, x1 = max(int(xs.min()) - MARGIN, 0), min(int(xs.max()) + MARGIN + 1, nx)
        sub = data[z0:z1, y0:y1, x0:x1]

        views = {
            "xy": sub.max(axis=0),          # 沿 z 投影
            "xz": sub.max(axis=1),          # 沿 y 投影
            "zy": sub.max(axis=2).T,        # 沿 x 投影，轉置成 (y, z) 讓縱軸維持 y
        }
        sizes = {}
        for key, plane in views.items():
            sizes[key] = to_png(plane, IMG_DIR / f"{nid}_{key}.png")

        # 質心（標準腦座標）：之後要把 20 條神經元疊在同一個空間時用得到
        bx0, _bx1, by0, _by1, bz0, _bz1 = vol.bbox
        centroid = [round(float(xs.mean()) + bx0, 1),
                    round(float(ys.mean()) + by0, 1),
                    round(float(zs.mean()) + bz0, 1)]

        records.append({
            "id": nid,
            "file": f.name,
            "driver": driver,
            "sex": sex,
            "cell": cell,
            "nt_zh": NEUROTRANSMITTER.get(driver, ("—", "—"))[0],
            "nt_en": NEUROTRANSMITTER.get(driver, ("—", "—"))[1],
            "dims": list(vol.dims),
            "bbox": [round(b, 2) for b in vol.bbox],
            "spacing": [round(s, 4) for s in vol.spacing],
            "vmax": int(data.max()),
            "nonzero": n_nonzero,
            "nonzero_pct": round(n_nonzero / data.size * 100, 3),
            "crop": [int(x1 - x0), int(y1 - y0), int(z1 - z0)],
            "centroid": centroid,
            "sizes": sizes,
        })
        print(f"{nid:24s} dims={vol.dims}  nonzero={n_nonzero:7d} "
              f"({records[-1]['nonzero_pct']:.2f}%)  crop={records[-1]['crop']}")

    (DATA_DIR / "summary.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成 {len(records)} 個神經元，共 {len(records) * 3} 張投影圖 -> {IMG_DIR}")


if __name__ == "__main__":
    main()
