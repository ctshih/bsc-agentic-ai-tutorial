"""
build_page.py — 把 data/ 與 images/ 組成單一頁面 index.html
============================================================
成品頁的敘事順序刻意和「讀者的疑問順序」一致：
    看到成果 -> 這跟隨機上色差在哪 -> 演算法怎麼運作 -> 論文的第二個主張 -> 復刻筆記
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

CSS = """
:root{--bg:#ffffff;--fg:#1a1d23;--soft:#5b6472;--line:#e2e8f0;--card:#f8fafc;
      --accent:#2563eb;--accent-soft:#eff4ff;--warn:#9d4edd;--warn-soft:#f6efff}
@media (prefers-color-scheme:dark){
:root{--bg:#12151a;--fg:#e6e9ef;--soft:#9aa4b2;--line:#2a313c;--card:#181c23;
      --accent:#5b9bff;--accent-soft:#18233a;--warn:#c89bff;--warn-soft:#241a33}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;
     line-height:1.75;font-size:16px}
.wrap{max-width:1000px;margin:0 auto;padding:0 20px 80px}
header{padding:48px 0 28px;border-bottom:1px solid var(--line);margin-bottom:36px}
h1{font-size:2rem;margin:0 0 8px;letter-spacing:-.01em}
.sub{color:var(--soft);margin:0}
h2{font-size:1.35rem;margin:52px 0 14px;padding-top:8px}
h3{font-size:1.06rem;margin:30px 0 10px}
p{margin:.7em 0}
code{background:var(--card);padding:.12em .4em;border-radius:4px;
     font-family:ui-monospace,"Cascadia Code",Consolas,monospace;font-size:.9em}
figure{margin:22px 0}
figure img{width:100%;height:auto;border-radius:10px;border:1px solid var(--line);
           background:#000;display:block}
figcaption{color:var(--soft);font-size:.88rem;margin-top:8px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.pair figure{margin:0}
@media(max-width:720px){.pair{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%;margin:18px 0;font-size:.93rem;
      display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;
      white-space:nowrap}
th{color:var(--soft);font-weight:600}
td.num,th.num{text-align:right}
.callout{border-left:3px solid var(--accent);background:var(--accent-soft);
         padding:14px 18px;border-radius:0 8px 8px 0;margin:22px 0}
.callout.warn{border-color:var(--warn);background:var(--warn-soft)}
.callout p:first-child{margin-top:0}
.callout p:last-child{margin-bottom:0}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
     gap:14px;margin:26px 0}
.kpi div{background:var(--card);border:1px solid var(--line);border-radius:10px;
         padding:14px 16px}
.kpi b{display:block;font-size:1.5rem;line-height:1.25}
.kpi span{color:var(--soft);font-size:.83rem}
.formula{background:var(--card);border:1px solid var(--line);border-radius:8px;
         padding:14px 18px;margin:16px 0;overflow-x:auto;font-size:.95rem}
footer{margin-top:64px;padding-top:20px;border-top:1px solid var(--line);
       color:var(--soft);font-size:.85rem}
.swatches{display:flex;flex-wrap:wrap;gap:4px;margin:12px 0}
.swatches i{width:20px;height:20px;border-radius:4px;display:block}
"""

MATHJAX = """
<script>window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],
 displayMath:[['\\\\[','\\\\]']]},svg:{fontCache:'global'}};</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
"""


def hsv_swatch(hue):
    """色相角 -> CSS hsl()，飽和度與明度固定，純粹呈現色相環的分布。"""
    return f"hsl({hue:.0f} 100% 50%)"


def main():
    meta = json.loads((DATA / "neurons.json").read_text(encoding="utf-8"))
    energy = json.loads((DATA / "energy.json").read_text(encoding="utf-8"))
    render = json.loads((DATA / "render.json").read_text(encoding="utf-8"))
    scaling = json.loads((DATA / "scaling.json").read_text(encoding="utf-8"))

    g = energy["gap"]
    base = energy["random_baseline"]
    ann = energy["annealed"]
    pap = energy["paper_10N"]
    nx, ny, nz = meta["dims"]
    n = len(meta["neurons"])
    ex = scaling["extrapolate"]
    clashes = render.get("clashes", [])
    # 色環圖用「隨機配色下差距最小」的那一對舉例，與 hue_wheel_fig.py 挑的一致
    clash0 = (min(clashes, key=lambda x: x["hue_gap_random"]) if clashes
              else {"pair": ["", ""]})

    sw_k = "".join(f'<i style="background:{hsv_swatch(r["hue_kaleido"])}"></i>'
                   for r in sorted(meta["neurons"], key=lambda r: r["hue_kaleido"]))

    rows_scaling = "".join(
        f"<tr><td class='num'>{r['N']}</td><td class='num'>{r['src_mb']:,.1f}</td>"
        f"<td class='num'>{r['dense_mb']:,.1f}</td>"
        f"<td class='num'><b>{r['merged_mb']:,.1f}</b></td>"
        f"<td class='num'>{r['t_load']:.2f}</td><td class='num'>{r['t_dist']:.3f}</td>"
        f"<td class='num'>{r['t_mc']:.3f}</td></tr>"
        for r in scaling["rows"])

    rows_clash = "".join(
        f"<tr><td>{c['pair'][0]}<br>{c['pair'][1]}</td>"
        f"<td class='num'>{c['dist']}</td>"
        f"<td class='num'>{c['hue_gap_random']}°</td>"
        f"<td class='num'><b>{c['hue_gap_kaleido']}°</b></td></tr>"
        for c in clashes)

    html = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>復刻 Kaleido：{n} 個果蠅神經元的自動配色</title>
<style>{CSS}</style>
{MATHJAX}
</head>
<body>
<div class="wrap">

<header>
  <h1>復刻 Kaleido：{n} 個果蠅神經元的自動配色</h1>
  <p class="sub">依 Wang et al., <i>Neuroinformatics</i> 16(2): 207–215 (2018) 重新實作，
  跑在 FlyCircuit 的 {n} 個單神經元影像上</p>
</header>

<p>Kaleido 要解決的問題只有一句話：<b>把上萬條神經元畫在同一張圖裡，還要讓人分得出誰是誰。</b>
隨機上色遠看沒問題，但擠在一起的兩條總會不巧撞成同一個顏色。Kaleido 的辦法是把
「相鄰卻同色」定義成一種能量，再用蒙地卡羅把能量壓到最低。</p>

<div class="kpi">
  <div><b>{n}</b><span>果蠅單神經元</span></div>
  <div><b>{render['voxels']:,}</b><span>非零體素</span></div>
  <div><b>{nx}×{ny}×{nz}</b><span>標準腦網格</span></div>
  <div><b>{g['median_kaleido']}°</b><span>最近鄰色相差中位數<br>（隨機配色 {g['median_random']}°）</span></div>
</div>

<h2>一、成果</h2>

<figure>
  <img src="images/mip_kaleido_xy.png" alt="Kaleido 配色的 {n} 個神經元">
  <figcaption>{n} 個神經元合併成單一張影像，色相由蒙地卡羅自動指派。
  沿 z 軸的最大強度投影；左下白棒 = 100 體素。</figcaption>
</figure>

<figure>
  <img src="images/spin_kaleido.webp" alt="繞 Y 軸旋轉">
  <figcaption>同一份合併影像繞 Y 軸旋轉。正交投影下，
  「旋轉點雲再投影」與「旋轉體積再做 MIP」等價，但快兩個數量級。</figcaption>
</figure>

<p>色相環上的 {n} 個角度，被演算法重新分配給 {n} 條神經元：</p>
<div class="swatches">{sw_k}</div>

<h2>二、跟隨機上色差在哪</h2>

<p>論文 Fig. 2 的比較方式是：找一塊細胞本體擠在一起的地方，看隨機配色會不會把鄰居
塗成同色。這裡自動找出細胞本體最密集的薄片
（{render['zoom']['size'][0]}×{render['zoom']['size'][1]}×{render['zoom']['slab']} 體素，
含 {render['zoom']['n_somas']} 顆細胞本體），
並把「隨機配色下靠得近又同色」的幾對用白圈標出來。</p>

<div class="pair">
  <figure>
    <img src="images/zoom_random.png" alt="隨機配色">
    <figcaption><b>隨機配色</b>：白圈裡是兩顆幾乎同色的細胞本體，分不出來。</figcaption>
  </figure>
  <figure>
    <img src="images/zoom_kaleido.png" alt="Kaleido 配色">
    <figcaption><b>Kaleido 配色</b>：同樣位置，兩顆變成對比色。</figcaption>
  </figure>
</div>

<table>
<thead><tr><th>撞色的一對</th><th class="num">相距（體素）</th>
<th class="num">隨機配色的色相差</th><th class="num">Kaleido 的色相差</th></tr></thead>
<tbody>{rows_clash}</tbody>
</table>

<p>把這件事量化到全部 {n} 條神經元上：每條神經元跟它<b>空間上最近的鄰居</b>之間的
色相差，越大越好認。</p>

<figure>
  <img src="images/chart_gap.png" alt="最近鄰色相差分布">
  <figcaption>隨機配色的中位數落在 {base['nn_mean']}°（{base['n_draw']} 次抽樣的平均，
  標準差 {base['nn_sd']}°）；Kaleido 把它推到 {g['median_kaleido']}°，
  而且幾乎沒有神經元落在 30° 以下的「撞色區」。</figcaption>
</figure>

<h2>三、演算法</h2>

<h3>先講清楚：顏色為什麼是「角度」</h3>

<p>這一頁從頭到尾都在講「色相差幾度」。Kaleido 用的是 <b>HSV 色彩模型</b>，把顏色拆成三個維度：
<b>色相</b>（顏色的種類，是一個 0°～360° 的<b>環</b>）、<b>飽和度</b>（固定為 1）、
<b>明度</b>（交給每個體素的訊號強度）。<b>演算法只動色相這一個維度</b>——
所謂「配色」，就是把色環上 N 個等距的角度重新分配給 N 條神經元。</p>

<figure>
  <img src="images/hue-wheel.png" alt="HSV 色相環與真實範例">
  <figcaption>左：色相環，0° 紅、120° 綠、240° 藍。中、右：同一對神經元
  （{clash0['pair'][0]} 與 {clash0['pair'][1]}）在兩種配色下的色相角。
  因為色相是一個環，兩色的差距<b>最多只有 180°</b>——那就是對比色。</figcaption>
</figure>

<p>對 N 個神經元，色相角在色相環上均勻分布：\\(\\theta(i)=360^\\circ\\times i/N\\)。
一組配色就是 1…N 的一個排列 \\(\\vec H\\)，共有 \\(N!\\) 種。能量函數是</p>

<div class="formula">
\\[ E(\\vec H)=\\sum_{{i=2}}^{{N}}\\sum_{{j=1}}^{{i-1}}
\\frac{{1}}{{d_{{ij}}\\times\\min(\\Delta_{{ij}},\\,360^\\circ-\\Delta_{{ij}})}} \\]
</div>

<p>\\(d_{{ij}}\\) 是兩條神經元的空間距離（各隨機抽 100 個體素估算），
\\(\\Delta_{{ij}}\\) 是色相差。兩者都在<b>分母</b>：靠得近又同色 → 分母小 → 這一項很貴。
把總能量壓低，就等於把擠在一起的神經元推到色相環的兩端。</p>

<div class="callout warn">
<p><b>復刻時踩到的第一個坑。</b>我們自己的知識庫把這個公式抄成了
\\(\\frac{{1}}{{d_{{ij}}}}\\times\\min(\\Delta_{{ij}},360^\\circ-\\Delta_{{ij}})\\)，
分母的 min 項被搬到了分子。兩者意義完全相反：抄錯的版本在「相鄰又同色」時能量<b>最低</b>，
最小化它會把鄰居塗成同一種顏色。回頭比對原始 PDF 才發現分數線是涵蓋整個分母的。</p>
</div>

<figure>
  <img src="images/mip_misread_xy.png" alt="用抄錯的公式最佳化">
  <figcaption>用抄錯的公式跑出來的結果：顏色變成漂亮的空間漸層，
  左視葉全藍、右視葉全洋紅——每條神經元都跟鄰居同色，
  最近鄰色相差中位數只有 {g['median_misread']}°。作為「位置編碼」很好看，
  作為「分辨個體」則完全失效。</figcaption>
</figure>

<h3>蒙地卡羅：論文的步數不夠用</h3>

<p>論文的動作定義是：找出目前能量最高的一對，隨機選兩個神經元跟它們交換色相，
以 \\(P=\\min(1,e^{{-\\beta\\Delta E}})\\) 決定接受與否，步數設 <code>10N</code>。
在 N={n} 時 <code>10N</code> 只有 {pap['info']['n_steps']} 步——能量才降
{pap['info']['drop_pct']:.1f}% 就結束了。改成降溫退火、加長到 <code>2000N</code>
（{ann['info']['n_steps']:,} 步，實際只花 {ann['info']['seconds']:.1f} 秒）才壓得下去。</p>

<figure>
  <img src="images/chart_energy.png" alt="能量下降曲線">
  <figcaption>橘線是論文設定，在 {pap['info']['n_steps']} 步處戛然而止；
  藍線是退火版，能量持續下降到 {ann['info']['E_best']:.3f}。</figcaption>
</figure>

<table>
<thead><tr><th>配色方式</th><th class="num">最近鄰色相差中位數</th>
<th class="num">能量降幅</th></tr></thead>
<tbody>
<tr><td>隨機配色（{base['n_draw']} 次抽樣）</td>
    <td class="num">{base['nn_mean']}° ± {base['nn_sd']}°</td><td class="num">—</td></tr>
<tr><td>論文設定：固定溫度、10N 步（8 個種子）</td>
    <td class="num">{pap['stat']['nn_mean']}° ± {pap['stat']['nn_sd']}°</td>
    <td class="num">{pap['stat']['drop_mean']:.1f}%</td></tr>
<tr><td><b>退火、2000N 步（8 個種子）</b></td>
    <td class="num"><b>{ann['stat']['nn_mean']}° ± {ann['stat']['nn_sd']}°</b></td>
    <td class="num">{ann['stat']['drop_mean']:.1f}%</td></tr>
<tr><td>用抄錯的公式（3 個種子）</td>
    <td class="num">{energy['misread']['stat']['nn_mean']}°
        ± {energy['misread']['stat']['nn_sd']}°</td>
    <td class="num">{energy['misread']['stat']['drop_mean']:.1f}%</td></tr>
</tbody>
</table>

<div class="callout">
<p><b>踩到的第二個坑：只跑一次就下結論。</b>隨機配色的中位數本身標準差就有
{base['nn_sd']}°（{base['n_draw']} 次抽樣的範圍是 {base['nn_lo']}°~{base['nn_hi']}°）。
第一次比較時隨機那次剛好抽到 113°、最佳化那次是 88°，看起來「最佳化讓結果變差」——
其實兩個都只是雜訊。跑 8 個種子才看得出來：最佳化不只把中位數推高，
還把變異從 ±{base['nn_sd']}° 收斂到 ±{ann['stat']['nn_sd']}°。</p>
</div>

<h3>其他配色模式</h3>
<p>論文提供四種模式。上面用的是 <code>color by distance</code>；
<code>color by file</code> 可以依生物意義上色——這裡改成依 driver line
（標記的神經傳導物質）分組：</p>

<figure>
  <img src="images/mip_nt_xy.png" alt="依神經傳導物質配色">
  <figcaption>同一批神經元改用 <code>color by file</code> 模式，
  依 driver line 分組上色（{len(meta['drivers'])} 組）。
  這時顏色不再為了「好分辨」，而是為了「看出生物規律」。</figcaption>
</figure>

<h2>四、論文的第二個主張：檔案大小與神經元數量脫鉤</h2>

<p>論文說，合併成單一 RGBA 影像後，大小「只由標準腦解析度決定」。
在 N = 10, 25, 50, 100 上實際量測（標準腦網格固定為
{nx}×{ny}×{nz}，不隨 N 縮放）：</p>

<table>
<thead><tr><th class="num">N</th><th class="num">原始 .am（MB）</th>
<th class="num">各自展開成稠密體積（MB）</th><th class="num">合併後單一 RGBA（MB）</th>
<th class="num">載入（秒）</th><th class="num">距離矩陣（秒）</th>
<th class="num">蒙地卡羅 10N（秒）</th></tr></thead>
<tbody>{rows_scaling}</tbody>
</table>

<figure>
  <img src="images/chart_scaling.png" alt="大小與時間對 N 的關係">
  <figcaption>左：各自展開會隨 N 線性成長，合併後永遠是同一個數字。
  右：這個規模下時間仍由檔案 I/O 主導，蒙地卡羅只佔千分之一。</figcaption>
</figure>

<p>外推到 FlyCircuit 全腦約 {ex['n_flycircuit']:,} 個神經元：各自展開需要
<b>{ex['naive_tb']} TB</b>（論文說的是「10 TB 等級」，同一個量級），
合併後仍然是 <b>{ex['merged_mb']:,.0f} MB</b>。</p>

<div class="callout">
<p><b>一個沒有複現的細節。</b>論文推導蒙地卡羅的時間複雜度是 \\(O(N^2)\\)
（步數 10N × 每步更新 2(N−2) 對）。這裡實測到的是
\\(N^{{{scaling['mc_exponent']}}}\\)——因為 N 只到 100，每一步的固定開銷
（numpy 呼叫成本）還壓過 \\(O(N)\\) 的實質計算，漸近行為根本還沒開始。
要驗證 \\(O(N^2)\\) 得把 N 拉到上千。</p>
</div>

<h2>五、復刻筆記：論文沒寫、必須自己補的決定</h2>

<ul>
<li><b>距離的不對稱性</b>：論文的 \\(d_{{ij}}\\) 定義（「對 i 的每個抽樣體素找 j 最近的」）
從兩個方向算會得到不同的值，論文沒說用哪一邊。這裡取兩個方向的平均。</li>
<li><b>\\(\\beta\\) 取多少</b>：論文只說是「對應人造溫度倒數的可調參數」。
這裡先跑 300 次試探測出典型的 \\(|\\Delta E|\\)，再用它當尺度定 \\(\\beta\\)，
換到別的資料上也還適用。</li>
<li><b>強度正規化</b>：這批檔案的動態範圍不一致（有的最大值 255、有的 4095），
論文只說「正規化後的訊號強度」。這裡用每個神經元自己的 99.5 百分位當白點。</li>
<li><b>增量更新</b>：論文的複雜度分析假設一次換色只重算受影響的 2(N−2) 對。
照字面每步重算整個 N×N 矩陣會變成 \\(O(N^3)\\)，計時就失真了。</li>
</ul>

<footer>
  資料來源：FlyCircuit（Chiang et al., 2011）的 {n} 個單神經元 warp 影像。
  演算法依 Kaleido（Wang et al., 2018, DOI 10.1007/s12021-018-9363-3）重新實作，
  非原作者程式碼。本頁由 <code>build_page.py</code> 自 <code>data/</code> 產生。
</footer>

</div>
</body>
</html>
"""
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"完成 -> {out}（{out.stat().st_size / 1024:.0f} KB）")


if __name__ == "__main__":
    main()
