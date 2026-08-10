"""
amread.py — 讀取 AmiraMesh (.am) 單通道體積影像
------------------------------------------------
FlyCircuit 的 *_warp_volume.am 檔結構：

    # AmiraMesh BINARY-LITTLE-ENDIAN 2.1      <- 純文字檔頭
    define Lattice 279 308 168                <- 格點數 (nx, ny, nz)
    Parameters { ... BoundingBox x0 x1 y0 y1 z0 z1 ... }
    Lattice { ushort Data } @1(HxZip,793970)  <- 資料段編號與壓縮方式
    # Data section follows
    @1
    <二進位資料>

重點：
  * HxZip 就是標準 zlib（開頭 magic 78 9c），Python 內建 zlib 就能解，不需要 Amira。
  * 資料是 x 變化最快（Fortran order），所以 reshape 成 (nz, ny, nx) 之後
    索引順序是 v[z, y, x]。
  * BoundingBox 是這塊體積在「標準腦座標」中的位置；除以格點數可得 voxel 間距，
    這批資料三軸都剛好是 1.0，代表所有檔案共用同一個座標系。
"""

import re
import zlib
import numpy as np

# AmiraMesh 型別名稱 -> numpy dtype（little-endian）
_DTYPE = {"byte": "<u1", "ushort": "<u2", "short": "<i2",
          "int": "<i4", "float": "<f4", "double": "<f8"}


class AmiraVolume:
    """一個 AmiraMesh 體積：資料本身 + 它在標準腦座標中的位置。"""

    def __init__(self, data, bbox, path):
        self.data = data            # numpy 陣列，索引順序 (z, y, x)
        self.bbox = bbox            # (x0, x1, y0, y1, z0, z1)
        self.path = path

    @property
    def dims(self):
        """回傳 (nx, ny, nz)，和檔頭 define Lattice 的順序一致。"""
        nz, ny, nx = self.data.shape
        return nx, ny, nz

    @property
    def spacing(self):
        """每個 voxel 的邊長（三軸）。用 BoundingBox 跨距 / (格點數 - 1) 算出來。"""
        nx, ny, nz = self.dims
        x0, x1, y0, y1, z0, z1 = self.bbox
        return ((x1 - x0) / max(nx - 1, 1),
                (y1 - y0) / max(ny - 1, 1),
                (z1 - z0) / max(nz - 1, 1))


def read_am(path):
    """讀一個 .am 檔，回傳 AmiraVolume。只支援單一 Lattice、uniform coordinates。"""
    raw = open(path, "rb").read()

    # 檔頭是 ASCII，但整個檔含二進位資料，所以只把前面一段解成文字來剖析。
    head = raw[:4096].decode("latin-1")

    m = re.search(r"define\s+Lattice\s+(\d+)\s+(\d+)\s+(\d+)", head)
    if not m:
        raise ValueError(f"找不到 define Lattice：{path}")
    nx, ny, nz = (int(g) for g in m.groups())

    m = re.search(r"BoundingBox\s+([-\d.eE+ ]+)", head)
    bbox = tuple(float(t) for t in m.group(1).split()[:6]) if m else None

    # 例：Lattice { ushort Data } @1(HxZip,793970)
    m = re.search(r"Lattice\s*\{\s*(\w+)\s+\w+\s*\}\s*@(\d+)(?:\((\w+),(\d+)\))?", head)
    if not m:
        raise ValueError(f"找不到 Lattice 資料段宣告：{path}")
    typename, section, codec, _nbytes = m.group(1), m.group(2), m.group(3), m.group(4)
    if typename not in _DTYPE:
        raise NotImplementedError(f"尚未支援的資料型別：{typename}")

    # 資料段起點：'# Data section follows' 之後的 '@N\n'
    marker = f"@{section}\n".encode()
    start = raw.find(marker, raw.find(b"# Data section follows"))
    if start < 0:
        raise ValueError(f"找不到資料段 @{section}：{path}")
    blob = raw[start + len(marker):]

    if codec == "HxZip":
        blob = zlib.decompress(blob)
    elif codec is not None:
        raise NotImplementedError(f"尚未支援的壓縮方式：{codec}（本批資料只用到 HxZip）")

    arr = np.frombuffer(blob, dtype=_DTYPE[typename], count=nx * ny * nz)
    # x 變化最快 -> 最後一維是 x
    return AmiraVolume(arr.reshape((nz, ny, nx)), bbox, path)


if __name__ == "__main__":
    import sys
    v = read_am(sys.argv[1])
    print("dims (nx,ny,nz) =", v.dims)
    print("bbox            =", v.bbox)
    print("spacing         =", tuple(round(s, 4) for s in v.spacing))
    print("value range     =", int(v.data.min()), "-", int(v.data.max()))
    print("nonzero voxels  =", int((v.data > 0).sum()))
