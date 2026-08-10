"""
view3d.py — 在 napari 裡互動檢視果蠅神經元（旋轉、縮放、平移）
--------------------------------------------------------------
用法：
    python view3d.py                      # 預設：每個 driver line 各一條，共 6 條
    python view3d.py --all                # 全部 20 條（載入較久、較吃記憶體）
    python view3d.py TH-F-000020          # 指定神經元（可給多個）
    python view3d.py --all --down 2       # 每 2 個 voxel 取 1 個，載入更快

重點：所有檔案共用同一個標準腦座標系（voxel 間距都是 1.0），
      所以用各自 BoundingBox 的原點當 translate，多條神經元就會落在
      真實的相對位置上，而不是全部疊在原點。

滑鼠操作（napari 3D 模式）：
      左鍵拖曳 = 旋轉    滾輪 = 縮放    右鍵拖曳（或 Shift+左鍵）= 平移
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from amread import read_am

SRC = Path(__file__).resolve().parent.parent / "FCdata" / "neurons"

# 每個 driver line 給一個顏色；blending='additive' 之下重疊處會自然混色
DRIVER_COLOR = {
    "TH": "magenta", "Tdc2": "yellow", "Trh": "green",
    "VGlut": "cyan", "Gad1": "red", "fru": "bop blue",
}
DRIVER_ORDER = ["TH", "Tdc2", "Trh", "VGlut", "Gad1", "fru"]
GAMMA = 0.5          # 與靜態圖一致：提亮暗部，才看得到細突起
CLIP_PCT = 99.5


def all_files():
    return sorted(SRC.glob("*.am"))


def pick_files(args):
    files = all_files()
    if args.ids:
        want = set(args.ids)
        sel = [f for f in files if f.stem.split("_")[0] in want]
        missing = want - {f.stem.split("_")[0] for f in sel}
        if missing:
            sys.exit(f"找不到這些神經元：{', '.join(sorted(missing))}")
        return sel
    if args.all:
        return files
    # 預設：每個 driver line 挑第一條，用最少的載入量呈現最多樣的形態
    seen, sel = set(), []
    for d in DRIVER_ORDER:
        for f in files:
            if f.stem.split("-")[0] == d and d not in seen:
                seen.add(d)
                sel.append(f)
                break
    return sel


def main():
    ap = argparse.ArgumentParser(description="在 napari 裡互動檢視果蠅神經元")
    ap.add_argument("ids", nargs="*", help="神經元 id，例如 TH-F-000020")
    ap.add_argument("--all", action="store_true", help="載入全部 20 條")
    ap.add_argument("--down", type=int, default=1, help="降取樣倍率（預設 1 = 原解析度）")
    args = ap.parse_args()

    files = pick_files(args)
    n = max(args.down, 1)

    import napari      # 放在這裡才 import：參數錯誤時不必等 napari 啟動
    viewer = napari.Viewer(ndisplay=3, title="果蠅神經元 3D 檢視（FlyCircuit）")
    viewer.theme = "dark"

    print(f"載入 {len(files)} 條神經元" + (f"（降取樣 {n}×）" if n > 1 else "") + " …")
    for f in files:
        nid = f.stem.split("_")[0]
        driver = nid.split("-")[0]
        vol = read_am(f)
        data = vol.data[::n, ::n, ::n]

        # 亮度上限取非零值的 99.5 百分位（資料很稀疏，用全體會太暗）
        nzv = vol.data[vol.data > 0]
        vmax = max(float(np.percentile(nzv, CLIP_PCT)), 1.0)

        # BoundingBox 給的是 (x0,x1,y0,y1,z0,z1)，napari 的軸順序是 (z,y,x)
        x0, _, y0, _, z0, _ = vol.bbox
        viewer.add_image(
            data,
            name=nid,
            colormap=DRIVER_COLOR.get(driver, "gray"),
            blending="additive",       # 疊加混色，多條神經元才看得出交會處
            rendering="mip",           # 最大強度投影；GUI 右上可切 attenuated_mip 等
            contrast_limits=[0, vmax],
            gamma=GAMMA,
            translate=(z0, y0, x0),    # 擺回標準腦座標
            scale=(n, n, n),           # 降取樣後仍維持正確的世界座標尺寸
        )
        print(f"  {nid:24s} {tuple(data.shape[::-1])}  -> {DRIVER_COLOR.get(driver,'gray')}")

    viewer.scale_bar.visible = True
    # 注意：不要設 viewer.scale_bar.unit = "voxel"。napari 的比例尺用 pint 解析單位字串，
    # "voxel" 不是 pint 認得的物理單位，賦值當下就會丟 UndefinedUnitError 讓程式中斷。
    # 不指定單位即可，比例尺會直接顯示數字——本來就是以 voxel 為單位（間距 1.0）。
    viewer.axes.visible = True          # 右下角顯示 xyz 軸向
    viewer.reset_view()

    print("""
──────────────────────────────────────────────
  滑鼠：左鍵拖曳 = 旋轉   滾輪 = 縮放   Shift+左鍵拖曳 = 平移
  左側圖層清單：可個別開關、改顏色、調透明度與對比
  左下角 2D/3D 按鈕：切回 2D 逐層瀏覽
  右上 rendering 下拉：mip / attenuated_mip / iso 等不同呈現方式
──────────────────────────────────────────────
""")
    napari.run()


if __name__ == "__main__":
    main()
