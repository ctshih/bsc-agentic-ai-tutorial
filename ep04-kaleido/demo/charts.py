"""
charts.py — 把 data/*.json 畫成圖表
====================================
和 render.py／scaling.py 分開，是因為改圖表配色、標籤時不必重跑兩分鐘的
體素渲染與檔案量測。三張圖：

    images/chart_energy.png    能量下降曲線（論文步數 vs 退火）
    images/chart_gap.png       最近鄰色相差分布（三種配色）
    images/chart_scaling.png   大小與時間對神經元數的關係

中文字型踩到的雷：Microsoft JhengHei 沒有 U+2212（數學減號）的字符，
log 軸的 10⁻¹ 會變成豆腐。設 axes.unicode_minus=False 只管一般刻度，
管不到 mathtext 的指數標籤 —— 所以這裡直接把 log 軸刻度改成十進位數字。
"""

import json
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import ticker as mticker

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
IMG_DIR = ROOT / "images"

plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C_PAPER = "#e07a5f"
C_ANNEAL = "#3d5a80"
C_RANDOM = "#8d99ae"
C_KALEIDO = "#2a9d8f"
C_MISREAD = "#9d4edd"


def plain_log_ticks(ax, axis="y"):
    """把 log 軸的 10⁻¹ 這種指數標籤換成 0.1，避開缺字問題。"""
    def fmt(v, _pos):
        if v <= 0:
            return ""
        if v >= 1:
            return f"{v:,.0f}"
        return f"{v:g}"
    a = ax.yaxis if axis == "y" else ax.xaxis
    a.set_major_formatter(mticker.FuncFormatter(fmt))
    a.set_minor_formatter(mticker.NullFormatter())


def chart_energy(energy):
    fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=150)
    for key, lab, col in (("paper_10N", "論文設定：固定溫度、10N 步", C_PAPER),
                          ("annealed", "改成退火、加長到 2000N 步", C_ANNEAL)):
        tr = energy[key]["trace"]
        st = energy[key]["info"]["trace_stride"]
        ax.plot(np.arange(len(tr)) * st, tr, label=lab, color=col, lw=1.3)
        ax.plot([len(tr) * st], [energy[key]["info"]["E_best"]], "o", color=col, ms=5)

    ax.set_xscale("symlog", linthresh=100)
    ax.set_xlabel("蒙地卡羅步數")
    ax.set_ylabel("能量 E")
    ax.set_title("論文的 10N 步在 N=100 時遠遠不夠")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=.25)
    plain_log_ticks(ax, "x")
    fig.tight_layout()
    fig.savefig(IMG_DIR / "chart_energy.png")
    plt.close(fig)


def chart_gap(energy):
    g = energy["gap"]
    base = energy["random_baseline"]
    fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=150)
    bins = np.linspace(0, 180, 19)

    ax.hist(g["misread"], bins=bins, color=C_MISREAD, alpha=.35,
            label=f"抄錯的公式（中位數 {g['median_misread']}°）")
    for key, lab, col in (("random", "隨機配色", C_RANDOM),
                          ("kaleido", "Kaleido 配色", C_KALEIDO)):
        ax.hist(g[key], bins=bins, histtype="step", lw=2.2, color=col,
                label=f"{lab}（中位數 {g['median_' + key]}°）")
    for key, col in (("misread", C_MISREAD), ("random", C_RANDOM),
                     ("kaleido", C_KALEIDO)):
        ax.axvline(g["median_" + key], color=col, ls="--", lw=1.2, alpha=.8)

    ax.set_xlim(0, 180)
    ax.set_xticks(np.arange(0, 181, 30))
    ax.set_xlabel("與最近鄰居的色相差（度）　→ 越右邊越好認")
    ax.set_ylabel("神經元數")
    ax.set_title(f"擠在一起的兩條，顏色差多少？"
                 f"（隨機基準 {base['nn_mean']}° ± {base['nn_sd']}°）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(IMG_DIR / "chart_gap.png")
    plt.close(fig)


def chart_scaling(sc):
    rows = sc["rows"]
    Ns = np.array([r["N"] for r in rows], dtype=float)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.8, 3.8), dpi=150)

    ax1.plot(Ns, [r["dense_mb"] for r in rows], "o-", color=C_PAPER,
             label="各自展開成稠密體積")
    ax1.plot(Ns, [r["src_mb"] for r in rows], "s-", color="#f2cc8f",
             label="原始 .am 壓縮檔")
    ax1.plot(Ns, [r["merged_mb"] for r in rows], "^-", color=C_ANNEAL,
             label="Kaleido 合併成單一 RGBA")
    ax1.annotate(f"{rows[-1]['merged_mb']:.0f} MB\n（四個 N 完全一樣）",
                 xy=(Ns[-1], rows[-1]["merged_mb"]), xytext=(-8, 34),
                 textcoords="offset points", fontsize=8, color=C_ANNEAL,
                 ha="right")
    ax1.set_xlabel("神經元數 N")
    ax1.set_ylabel("大小（MB）")
    ax1.set_title("合併後的大小與 N 無關")
    ax1.legend(frameon=False, fontsize=8, loc="upper left")
    ax1.grid(alpha=.25)

    ax2.plot(Ns, [r["t_load"] for r in rows], "o-", color=C_PAPER, label="載入檔案")
    ax2.plot(Ns, [r["t_dist"] for r in rows], "s-", color="#81b29a", label="距離矩陣")
    ax2.plot(Ns, [r["t_mc"] for r in rows], "^-", color=C_ANNEAL,
             label=f"蒙地卡羅 10N 步（實測 ~N^{sc['mc_exponent']:.1f}）")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("神經元數 N")
    ax2.set_ylabel("秒")
    ax2.set_title("時間：這個規模仍由檔案 I/O 主導")
    ax2.legend(frameon=False, fontsize=8, loc="upper left")
    ax2.grid(alpha=.25, which="both")
    plain_log_ticks(ax2, "y")
    plain_log_ticks(ax2, "x")

    fig.tight_layout()
    fig.savefig(IMG_DIR / "chart_scaling.png")
    plt.close(fig)


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    energy = json.loads((DATA_DIR / "energy.json").read_text(encoding="utf-8"))
    chart_energy(energy)
    chart_gap(energy)
    sc_path = DATA_DIR / "scaling.json"
    if sc_path.exists():
        chart_scaling(json.loads(sc_path.read_text(encoding="utf-8")))
    print("圖表完成 ->", IMG_DIR)


if __name__ == "__main__":
    main()
