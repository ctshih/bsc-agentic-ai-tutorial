"""
build_page.py — 把 render_mip.py 產出的圖與 summary.json 組成一頁 HTML
--------------------------------------------------------------------
刻意和 render_mip.py 分開：算圖很慢（要解壓 20 個上百 MB 的體積），
但排版常常要改。分開之後改版面只要重跑這支，幾毫秒就好。

輸出：index.html（引用 images/ 底下的 PNG，直接用瀏覽器開即可）
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
records = json.loads((OUT / "data" / "summary.json").read_text(encoding="utf-8"))

# 旋轉動畫由 render_spin.py 另外產生；沒跑過也不影響靜態三視圖，頁面自動略過該欄。
spin_path = OUT / "data" / "spin.json"
spin = json.loads(spin_path.read_text(encoding="utf-8")) if spin_path.exists() else {}

# driver line 的顯示順序與代表色（同一品系用同一色，方便一眼分群）
DRIVER_ORDER = ["TH", "Tdc2", "Trh", "VGlut", "Gad1", "fru"]
DRIVER_COLOR = {
    "TH":    "#f2777a",
    "Tdc2":  "#f0a15e",
    "Trh":   "#6cc2a8",
    "VGlut": "#6aa9f0",
    "Gad1":  "#b08cf0",
    "fru":   "#e79ac4",
}
VIEWS = [
    ("xy", "XY", "沿 z 軸投影"),
    ("xz", "XZ", "沿 y 軸投影"),
    ("zy", "ZY", "沿 x 軸投影"),
]

records.sort(key=lambda r: (DRIVER_ORDER.index(r["driver"])
                            if r["driver"] in DRIVER_ORDER else 99, r["id"]))

# ---------- 統計摘要 ----------
counts = {}
for r in records:
    counts[r["driver"]] = counts.get(r["driver"], 0) + 1
n_female = sum(1 for r in records if r["sex"] == "F")

CSS = """
*{box-sizing:border-box}
:root{
  --bg:#f6f7f9; --card:#fff; --fg:#1b1f24; --muted:#6b7280; --line:#e3e6ea;
  --accent:#c2410c; --shadow:0 1px 3px rgba(0,0,0,.08),0 8px 24px rgba(0,0,0,.05);
}
@media (prefers-color-scheme:dark){
  :root{ --bg:#0e1116; --card:#161a21; --fg:#e6e9ee; --muted:#9aa3af; --line:#252b34;
         --accent:#fb923c; --shadow:0 1px 3px rgba(0,0,0,.5); }
}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);
  font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;
  line-height:1.7;font-size:15px}
.wrap{max-width:1180px;margin:0 auto;padding:36px 20px 80px}
header h1{font-size:1.9rem;margin:0 0 6px;letter-spacing:.5px}
header p.sub{color:var(--muted);margin:0 0 24px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:18px 22px;margin-bottom:22px;box-shadow:var(--shadow)}
.panel h2{font-size:1.05rem;margin:0 0 10px}
.panel p{margin:0 0 8px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 0}
.stat{background:var(--bg);border:1px solid var(--line);border-radius:9px;
  padding:8px 14px;min-width:96px}
.stat b{display:block;font-size:1.3rem;line-height:1.2}
.stat span{color:var(--muted);font-size:.78rem}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);
  background:var(--bg);border-radius:999px;padding:4px 12px;font-size:.82rem;
  cursor:pointer;user-select:none}
.chip .dot{width:9px;height:9px;border-radius:50%}
.chip.off{opacity:.35}
.controls{display:flex;flex-wrap:wrap;gap:16px;align-items:center;
  margin-top:14px;font-size:.85rem;color:var(--muted)}
.controls label{display:inline-flex;align-items:center;gap:6px;cursor:pointer}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-bottom:18px;box-shadow:var(--shadow)}
.card.hidden{display:none}
.card-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;
  border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:12px}
.card-head .name{font-weight:700;font-size:1.05rem;font-family:ui-monospace,Menlo,Consolas,monospace}
.tag{font-size:.75rem;border-radius:999px;padding:2px 10px;color:#111;font-weight:600}
.meta{color:var(--muted);font-size:.78rem;margin-left:auto;
  font-family:ui-monospace,Menlo,Consolas,monospace}
.views{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media (max-width:1080px){.views{grid-template-columns:repeat(2,1fr)}}
@media (max-width:620px){.views{grid-template-columns:1fr}}
.view{border:1px solid var(--line);border-radius:9px;overflow:hidden;background:#000}
.view.spin{border-color:var(--accent)}
.view.spin .cap{background:color-mix(in srgb,var(--accent) 14%,var(--bg))}
.view .cap{display:flex;justify-content:space-between;align-items:center;
  background:var(--bg);color:var(--muted);font-size:.74rem;padding:4px 9px;
  border-bottom:1px solid var(--line)}
.view .cap b{color:var(--fg);font-size:.8rem;letter-spacing:.5px}
.view .box{display:flex;align-items:center;justify-content:center;
  min-height:120px;padding:6px;overflow:auto}
.view img{display:block;cursor:zoom-in;image-rendering:auto}
body.fit .view img{max-width:100%;max-height:230px;width:auto;height:auto}
body.scaled .view img{width:calc(var(--w) * 0.42px);height:auto;max-width:none}
.foot{color:var(--muted);font-size:.8rem;text-align:center;margin-top:30px}
code{background:var(--bg);border:1px solid var(--line);border-radius:4px;
  padding:1px 5px;font-size:.85em}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;
  align-items:center;justify-content:center;z-index:50;cursor:zoom-out;padding:20px}
#lb.on{display:flex}
#lb img{max-width:100%;max-height:88vh;object-fit:contain}
#lb .cap2{position:absolute;bottom:16px;left:0;right:0;text-align:center;
  color:#ddd;font-size:.85rem;font-family:ui-monospace,Menlo,Consolas,monospace}
"""

JS = """
// 依 driver line 篩選
document.querySelectorAll('.chip[data-driver]').forEach(function(c){
  c.addEventListener('click', function(){
    c.classList.toggle('off');
    var on = new Set([].slice.call(document.querySelectorAll('.chip[data-driver]:not(.off)'))
                       .map(function(x){return x.dataset.driver}));
    document.querySelectorAll('.card').forEach(function(card){
      card.classList.toggle('hidden', !on.has(card.dataset.driver));
    });
  });
});
// 顯示模式：填滿框 vs 依實際 voxel 尺寸等比例
var sw = document.getElementById('scaleToggle');
sw.addEventListener('change', function(){
  document.body.classList.toggle('scaled', sw.checked);
  document.body.classList.toggle('fit', !sw.checked);
});
// 點圖放大
var lb = document.getElementById('lb'), lbImg = lb.querySelector('img'),
    lbCap = lb.querySelector('.cap2');
document.querySelectorAll('.view img').forEach(function(im){
  im.addEventListener('click', function(){
    lbImg.src = im.src; lbCap.textContent = im.alt; lb.classList.add('on');
  });
});
lb.addEventListener('click', function(){ lb.classList.remove('on'); });
document.addEventListener('keydown', function(e){
  if(e.key === 'Escape') lb.classList.remove('on');
});
"""


def card_html(r):
    color = DRIVER_COLOR.get(r["driver"], "#999")
    nx, ny, nz = r["dims"]
    views = []

    # 第一欄：繞 Y 軸旋轉的動畫
    sp = spin.get(r["id"])
    if sp:
        alt = (f"{r['id']} — 繞 Y 軸旋轉（{sp['frames']} 格，"
               f"{sp['w']}×{sp['h']} voxel 畫布）")
        views.append(
            f'<div class="view spin"><div class="cap"><b>3D 旋轉</b>'
            f'<span>繞 Y 軸｜{sp["frames"]} 格</span></div>'
            f'<div class="box"><img src="images/{r["id"]}_spin.webp" alt="{alt}" '
            f'loading="lazy" style="--w:{sp["w"]};--h:{sp["h"]}"></div></div>')

    for key, label, desc in VIEWS:
        w, h = r["sizes"][key]
        src = f"images/{r['id']}_{key}.png"
        alt = f"{r['id']} — {label}（{desc}）{w}×{h} px"
        views.append(
            f'<div class="view"><div class="cap"><b>{label}</b><span>{desc}｜{w}×{h}</span></div>'
            f'<div class="box"><img src="{src}" alt="{alt}" loading="lazy" '
            f'style="--w:{w};--h:{h}"></div></div>')
    return f"""<article class="card" data-driver="{r['driver']}">
  <div class="card-head">
    <span class="name">{r['id']}</span>
    <span class="tag" style="background:{color}">{r['driver']}｜{r['nt_zh']}</span>
    <span class="tag" style="background:var(--bg);color:var(--muted);border:1px solid var(--line)">
      {'雌' if r['sex'] == 'F' else '雄'}</span>
    <span class="meta">{nx}×{ny}×{nz} voxel｜非零 {r['nonzero']:,}（{r['nonzero_pct']}%）｜
      最大值 {r['vmax']}｜質心 ({r['centroid'][0]}, {r['centroid'][1]}, {r['centroid'][2]})</span>
  </div>
  <div class="views">{''.join(views)}</div>
</article>"""


legend = "".join(
    f'<span class="chip" data-driver="{d}"><span class="dot" style="background:'
    f'{DRIVER_COLOR[d]}"></span>{d}（{[r for r in records if r["driver"] == d][0]["nt_zh"]}）'
    f' ×{counts[d]}</span>'
    for d in DRIVER_ORDER if d in counts)

html = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>果蠅神經元三視圖｜FlyCircuit 體積影像</title>
<style>{CSS}</style>
</head>
<body class="fit">
<div class="wrap">

<header>
  <h1>果蠅單神經元三視圖</h1>
  <p class="sub">FCdata/neurons 的 {len(records)} 個 FlyCircuit 體積影像（<code>.am</code>），
     每個神經元以一段繞 Y 軸的旋轉動畫 + 三個正交方向的最大強度投影呈現。</p>
</header>

<section class="panel">
  <h2>這些圖是怎麼來的</h2>
  <p>原始檔是 <b>AmiraMesh</b> 格式的 3D 灰階體積：純文字檔頭 + zlib（<code>HxZip</code>）壓縮的
     16-bit 資料，數值範圍 0–4095。神經元本體只佔 <b>0.5%–4%</b> 的 voxel，其餘皆為 0。</p>
  <p>因為結構稀疏又是立體樹狀，單看任何一張切片都只會切到零星幾段，所以改用
     <b>最大強度投影（Maximum Intensity Projection, MIP）</b>：沿著某一軸，取每條射線上的最大值，
     把整個立體壓成一張圖。三個方向合起來就能還原神經元的立體走向。</p>
  <p>影像處理：以非零值的 {99.5} 百分位當白點，再套 gamma 0.5 提亮暗部（否則只看得到主幹、
     看不到細突起），最後用 inferno 色階上色 —— 亮黃 = 訊號強，紫黑 = 訊號弱。
     左下角白色橫棒 = <b>100 voxel</b>。</p>
  <div class="stats">
    <div class="stat"><b>{len(records)}</b><span>神經元</span></div>
    <div class="stat"><b>{len(counts)}</b><span>driver line</span></div>
    <div class="stat"><b>{n_female}／{len(records) - n_female}</b><span>雌／雄</span></div>
    <div class="stat"><b>1.0</b><span>voxel 間距（三軸）</span></div>
    <div class="stat"><b>{len(records) * 3}</b><span>投影圖</span></div>
    <div class="stat"><b>{len(spin)}</b><span>旋轉動畫</span></div>
  </div>
  <div class="legend">{legend}</div>
  <div class="controls">
    <span>點上面的品系可以篩選；點任一張圖可放大。</span>
    <label><input type="checkbox" id="scaleToggle"> 依實際 voxel 尺寸等比例顯示（可比較大小）</label>
  </div>
</section>

<section class="panel">
  <h2>四個欄位怎麼看</h2>
  <p><b>第一欄「3D 旋轉」</b>：繞 <b>Y 軸</b>（畫面的垂直方向、通過影像檔正中央）旋轉一圈，
     每 10 度一格共 36 格。靜態投影會把立體結構壓扁，看不出前後關係；轉起來之後，
     人眼會自動從運動視差還原深度。這也是繞開下面那個解析度問題最有效的辦法。</p>
  <p><b>後三欄</b>：<b>XY</b>＝沿 z 軸投影、<b>XZ</b>＝沿 y 軸投影、<b>ZY</b>＝沿 x 軸投影。
     三張圖是同一塊裁切區域，所以同一條神經元的三視圖彼此對得起來。</p>
  <p><b>為什麼 XZ 和 ZY 看起來比較糊？</b>不是繪圖的問題，是資料本身：共軛焦顯微鏡的
     點擴散函數在光軸（z）方向是拉長的，軸向解析度比橫向差 2–3 倍。實測這批資料沿 z 的
     自相關要走 <b>1.5–2.2 倍</b>的距離才掉到一半，代表同一個結構沿 z 被抹開成約兩倍寬。
     XY 是唯一不含 z 軸的視角，所以最銳利；旋轉動畫轉到側面時同樣會變糊，屬正常現象。</p>
  <p>需要注意：這裡的 X／Y／Z 是<b>資料座標軸</b>，還沒對應到解剖學上的前後／背腹／左右。
     要標成「正面觀／水平觀／矢狀觀」必須先確認這批標準腦的軸向定義，尚未查證。</p>
</section>

{''.join(card_html(r) for r in records)}

<p class="foot">資料來源：FlyCircuit <code>*_seg001_warp_volume.am</code>；
   由 <code>render_mip.py</code> + <code>build_page.py</code> 產生。</p>
</div>

<div id="lb"><img alt=""><div class="cap2"></div></div>
<script>{JS}</script>
</body>
</html>
"""

(OUT / "index.html").write_text(html, encoding="utf-8")
print(f"已產生 {OUT / 'index.html'}（{len(records)} 張卡片、{len(records) * 3} 張圖）")
