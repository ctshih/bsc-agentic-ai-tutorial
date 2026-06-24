# -*- coding: utf-8 -*-
"""
build.py — 知識庫常駐工具（EP02 改版）。

掃描 topics/*.html（概念條目）與 papers/*.html（論文），從各頁內嵌的
<script id="meta"> 取出 metadata，重生四個導覽頁：
  - index.html     概念導向首頁（主題地圖 + 論文清單）
  - graph.html     論文連結網路（節點＝論文，標籤用 node_label）
  - keywords.html  關鍵字網路（節點＝關鍵字，點擊＝搜尋出所有相關頁面）
  - log.html       時間軸（讀 log.jsonl）

日常流程：編輯/新增 topics 或 papers 的 *.html 後，跑  python build.py
真實來源是 topics/*.html 與 papers/*.html，本工具只讀不改它們。
"""
import json, os, re, glob, html, math

ROOT = os.path.dirname(os.path.abspath(__file__))
PAPERS_DIR = os.path.join(ROOT, "papers")
TOPICS_DIR = os.path.join(ROOT, "topics")

SCALE = {
    "mesoscale":   ("#2563eb", "中尺度"),
    "single-cell": ("#0d9488", "單細胞"),
    "synaptic":    ("#db2777", "突觸級"),
    "macroscale":  ("#7c3aed", "巨觀"),
    "method/tool": ("#ea580c", "方法/工具"),
}
# BSC（腦空間體中心）成員——論文作者含這些人時，論文網路節點會加框 highlight。
# 名單會持續增加；新成員就把英文全名（要與論文 authors 內寫法一致）加進這個 set。
BSC_MEMBERS = {
    "Chi-Tin Shih",       # 施奇廷
    "Ann-Shyn Chiang",    # 江安世
    "Ting-Kuo Lee",       # 李定國
    "Chung-Chuan Lo",     # 羅中泉
    "Ching-Che Charng",   # 強敬哲
    "Kuan-Lin Feng",      # 馮冠霖
}

# 關鍵字分類 → keywords.html 節點顏色（飽和、不過淺）。新關鍵字記得歸到某一類。
KW_CATEGORIES = [
    ("連結體與資料庫", "#2563eb", ["連結體", "連結體尺度", "突觸級連結體", "連結體重建", "FlyCircuit", "開放資料庫"]),
    ("腦結構與生物",   "#16a34a", ["果蠅腦", "哺乳類腦", "神經氈", "LPU", "蕈狀體", "投射神經元", "單神經元", "嗅覺"]),
    ("成像與分割方法", "#ea580c", ["影像分割", "深度學習", "神經元追蹤", "影像配準", "視覺化", "電子顯微鏡", "光學顯微鏡連結體", "擴展顯微術", "體積成像"]),
    ("網路分析",       "#7c3aed", ["網路分析", "資訊流", "社群結構", "富俱樂部", "小世界", "中心性"]),
    ("神經活性與功能", "#e11d48", ["神經光子學", "神經活性記錄"]),
]
KW_COLOR = {kw: color for _, color, kws in KW_CATEGORIES for kw in kws}
KW_UNCAT = "#64748b"   # 未分類 → 灰

OP_LABEL = {"ingest": "收錄", "build": "重建", "query": "查詢", "lint": "健檢"}
OP_ORDER = {"ingest": 0, "query": 1, "lint": 2, "build": 3}
NAV = [("index", "首頁"), ("graph", "論文網路"), ("keywords", "關鍵字網路"), ("log", "時間軸")]

META_RE = re.compile(r'<script type="application/json" id="meta">(.*?)</script>', re.DOTALL)


def esc(s): return html.escape(str(s), quote=True)
def scolor(s): return SCALE.get(s, ("#64748b", s))[0]
def slabel(s): return SCALE.get(s, ("#64748b", s))[1]


def topbar(active, prefix=""):
    nav = "".join(
        f'<a href="{prefix}{k}.html"{" class=\"active\"" if k == active else ""}>{lab}</a>'
        for k, lab in NAV)
    return (f'<div class="topbar"><div class="inner">'
            f'<div class="brand">🧠 FlyCircuit 連結體論文知識庫 <small>· BSC Knowledge Base</small></div>'
            f'<nav>{nav}</nav></div></div>')


def load_dir(d):
    out = []
    for path in sorted(glob.glob(os.path.join(d, "*.html"))):
        with open(path, encoding="utf-8") as f:
            m = META_RE.search(f.read())
        if m:
            out.append(json.loads(m.group(1)))
    return out


def page(title, active, body, prefix="", extra_head=""):
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
{extra_head}
</head>
<body>
{topbar(active, prefix)}
{body}
</body>
</html>
"""


# ---------------- index.html（概念導向首頁） ----------------
def build_index(topics, papers):
    kw_all = sorted({k for t in topics for k in t.get("keywords", [])}
                    | {k for p in papers for k in p.get("keywords", [])})
    stats = [(len(topics), "概念條目"), (len(papers), "收錄論文"), (len(kw_all), "關鍵字")]
    stat_html = "\n".join(
        f'    <div class="stat"><div class="n">{esc(n)}</div><div class="l">{esc(l)}</div></div>'
        for n, l in stats)

    cards = []
    for t in topics:
        chips = "".join(f'<span class="kw-chip">{esc(k)}</span>' for k in t.get("keywords", []))
        cards.append(f"""    <a class="topic-card" href="topics/{esc(t['id'])}.html">
      <h3>{esc(t['title'])}</h3>
      <p>{esc(t.get('tldr',''))}</p>
      <div class="kw-row">{chips}</div>
    </a>""")

    body = f"""<div class="wrap wide">
  <header class="home-hero">
    <h1 class="page-title">FlyCircuit 連結體論文知識庫</h1>
    <p class="page-sub">關於果蠅（Drosophila）腦連結體與 FlyCircuit 工具鏈的知識庫。先從<b>概念條目</b>建立全貌，再深入個別論文；想找特定主題，到<a href="keywords.html">關鍵字網路</a>點關鍵字即可。</p>
    <div class="stats">
{stat_html}
    </div>
  </header>

  <div class="sec-head">
    <h2 class="sec-title">主題地圖 · 概念條目</h2>
    <div class="view-toggle" role="group" aria-label="檢視方式">
      <button type="button" data-view="list">≣&nbsp; 條列</button>
      <button type="button" data-view="grid">▦&nbsp; 磚塊</button>
    </div>
  </div>
  <div id="topics" class="topic-wrap view-list">
{chr(10).join(cards)}
  </div>

  <a class="all-papers" href="papers.html">
    <span class="ap-ico">📄</span>
    <span class="ap-txt"><b>收錄論文（{len(papers)} 篇）</b><br><span class="ap-sub">查看完整論文清單 →</span></span>
  </a>
</div>
<div class="foot">由 build.py 自動生成 · {len(topics)} 概念條目 / {len(papers)} 論文 · 編輯 topics 或 papers 的 *.html 後重跑 build.py</div>
<script>
(function(){{
  const wrap = document.getElementById('topics');
  const btns = document.querySelectorAll('.view-toggle button');
  function apply(v){{
    wrap.classList.toggle('view-grid', v === 'grid');
    wrap.classList.toggle('view-list', v !== 'grid');
    btns.forEach(b => b.classList.toggle('active', b.dataset.view === v));
  }}
  let v = localStorage.getItem('kb-topic-view') || 'list';   // 預設條列
  apply(v);
  btns.forEach(b => b.addEventListener('click', () => {{
    v = b.dataset.view; localStorage.setItem('kb-topic-view', v); apply(v);
  }}));
}})();
</script>"""
    return page("FlyCircuit 連結體論文知識庫", "index", body)


# ---------------- papers.html（完整論文清單） ----------------
def build_papers(papers):
    rows = []
    for p in sorted(papers, key=lambda r: r.get("year", 0)):
        authors = "、".join(p.get("authors", [])[:3]) + " et al."
        rows.append(f"""    <a class="paper-row" href="papers/{esc(p['id'])}.html">
      <span class="pr-badge" style="background:{scolor(p['scale'])}">{esc(slabel(p['scale']))}</span>
      <span class="pr-body"><b>{esc(p['title_zh'])}</b><br><span class="pr-meta">{esc(p['year'])} · {esc(authors)} · {esc(p['venue'])}</span></span>
    </a>""")
    body = f"""<div class="wrap wide">
  <h1 class="page-title">收錄論文</h1>
  <p class="page-sub">目前共 {len(papers)} 篇，依年份排序。點任一篇進入整理頁；想看論文之間的關聯，請看<a href="graph.html">論文網路</a>，想依主題瀏覽請回<a href="index.html">首頁</a>。</p>
  <div class="paper-list">
{chr(10).join(rows)}
  </div>
</div>
<div class="foot">由 build.py 自動生成 · 共 {len(papers)} 篇。</div>"""
    return page("收錄論文｜FlyCircuit 知識庫", "papers", body)


# ---------------- graph.html（論文連結網路） ----------------
def build_graph(papers):
    ids = [p["id"] for p in papers]
    idset = set(ids)
    by_id = {p["id"]: p for p in papers}
    edges = set()
    for p in papers:
        for rid in p.get("related", []):
            if rid in idset and rid != p["id"]:
                edges.add(frozenset((p["id"], rid)))
    deg = {i: 0 for i in ids}
    for e in edges:
        for i in e:
            deg[i] += 1

    W, H = 820, 600
    cx, cy, R = 410, 285, 205
    n = len(ids)
    pos = {}
    for k, i in enumerate(ids):
        ang = 2 * math.pi * k / n - math.pi / 2
        pos[i] = (cx + R * math.cos(ang), cy + R * math.sin(ang), ang)

    edge_svg = [f'    <line x1="{pos[a][0]:.1f}" y1="{pos[a][1]:.1f}" x2="{pos[b][0]:.1f}" y2="{pos[b][1]:.1f}" stroke="var(--border)" stroke-width="1.6"/>'
                for a, b in (tuple(e) for e in edges)]
    node_svg = []
    bsc_any = False
    for i in ids:
        x, y, ang = pos[i]
        p = by_id[i]
        r = 15 + deg[i] * 3
        label = p.get("node_label") or i
        lx = x + (r + 10) * math.cos(ang)
        ly = y + (r + 10) * math.sin(ang)
        anchor = "start" if math.cos(ang) >= 0 else "end"
        dy = "0.7em" if math.sin(ang) > 0.3 else ("-0.2em" if math.sin(ang) < -0.3 else "0.32em")
        bsc = any(a in BSC_MEMBERS for a in p.get("authors", []))
        bsc_any = bsc_any or bsc
        ring = (f'\n    <circle class="bsc-halo" cx="{x:.1f}" cy="{y:.1f}" r="{r + 6:.1f}" fill="none"/>'
                f'\n    <circle class="bsc-ring" cx="{x:.1f}" cy="{y:.1f}" r="{r + 6:.1f}" fill="none"/>'
                if bsc else "")
        node_svg.append(f"""  <a href="papers/{esc(i)}.html" class="graph-node{' is-bsc' if bsc else ''}">
    <title>{esc(p['title_zh'])}{' · 作者含 BSC 成員' if bsc else ''}</title>{ring}
    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{scolor(p['scale'])}" stroke="var(--surface)" stroke-width="2.5"/>
    <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dy="{dy}">{esc(label)}</text>
  </a>""")
    used = [s for s in SCALE if any(p["scale"] == s for p in papers)]
    legend = "".join(f'<span><i style="background:{scolor(s)}"></i>{esc(slabel(s))}</span>' for s in used)
    if bsc_any:
        legend += '<span class="leg-bsc"><i></i>外框＝作者含 BSC 成員</span>'

    body = f"""<div class="wrap wide">
  <h1 class="page-title">論文連結網路</h1>
  <p class="page-sub">節點＝論文（標籤＝主題／工具名／年份，顏色＝研究尺度，大小＝關聯數，<b>有外框者代表作者含 BSC 成員</b>），連線＝彼此引用或延伸。點節點進入該論文。想看跨論文的主題關聯，請看<a href="keywords.html">關鍵字網路</a>。</p>
  <div class="graph-wrap">
    <svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="論文連結網路圖">
{chr(10).join(edge_svg)}
{chr(10).join(node_svg)}
    </svg>
  </div>
  <div class="legend">{legend}</div>
</div>
<div class="foot">由 build.py 依各論文頁的 related 欄位自動生成。</div>"""
    return page("論文連結網路｜FlyCircuit 知識庫", "graph", body)


# ---------------- keywords.html（關鍵字網路 + 搜尋） ----------------
def _layout(nodes, edges, W, H, iters=320):
    n = len(nodes)
    pos = {nd: [0.5 + 0.42 * math.cos(2 * math.pi * i / n),
                0.5 + 0.42 * math.sin(2 * math.pi * i / n)] for i, nd in enumerate(nodes)}
    k = math.sqrt(1.0 / max(n, 1)) * 1.1
    temp = 0.10
    for _ in range(iters):
        disp = {nd: [0.0, 0.0] for nd in nodes}
        for i in range(n):
            for j in range(i + 1, n):
                a, b = nodes[i], nodes[j]
                dx = pos[a][0] - pos[b][0]; dy = pos[a][1] - pos[b][1]
                d = math.sqrt(dx * dx + dy * dy) + 1e-6
                f = k * k / d
                disp[a][0] += dx / d * f; disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f; disp[b][1] -= dy / d * f
        for a, b, w in edges:
            dx = pos[a][0] - pos[b][0]; dy = pos[a][1] - pos[b][1]
            d = math.sqrt(dx * dx + dy * dy) + 1e-6
            f = d * d / k * (1 + 0.35 * (w - 1))
            disp[a][0] -= dx / d * f; disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f; disp[b][1] += dy / d * f
        for nd in nodes:
            dx, dy = disp[nd]; d = math.sqrt(dx * dx + dy * dy) + 1e-9
            pos[nd][0] += dx / d * min(d, temp)
            pos[nd][1] += dy / d * min(d, temp)
            pos[nd][0] = min(0.97, max(0.03, pos[nd][0]))
            pos[nd][1] = min(0.97, max(0.03, pos[nd][1]))
        temp = max(0.004, temp * 0.985)
    m = 70
    return {nd: (m + p[0] * (W - 2 * m), m + p[1] * (H - 2 * m)) for nd, p in pos.items()}


def build_keywords(topics, papers):
    # 收集頁面（概念條目 + 論文）與其關鍵字
    pages = []
    for t in topics:
        pages.append({"id": t["id"], "title": t["title"], "url": "topics/" + t["id"] + ".html",
                      "type": "概念", "kws": t.get("keywords", [])})
    for p in papers:
        pages.append({"id": p["id"], "title": p["title_zh"], "url": "papers/" + p["id"] + ".html",
                      "type": "論文", "kws": p.get("keywords", [])})
    # 關鍵字 → 頁面索引；共現邊
    kw_pages = {}
    for idx, pg in enumerate(pages):
        for k in pg["kws"]:
            kw_pages.setdefault(k, []).append(idx)
    keywords = sorted(kw_pages, key=lambda k: (-len(kw_pages[k]), k))
    cooc = {}
    for pg in pages:
        ks = pg["kws"]
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                key = frozenset((ks[i], ks[j]))
                cooc[key] = cooc.get(key, 0) + 1
    edges = [(tuple(e)[0], tuple(e)[1], w) for e, w in cooc.items()]

    W, H = 1000, 660
    pos = _layout(keywords, edges, W, H)
    maxc = max(len(v) for v in kw_pages.values()) if kw_pages else 1

    edge_svg = "\n".join(
        f'    <line class="kw-edge" data-a="{esc(a)}" data-b="{esc(b)}" x1="{pos[a][0]:.1f}" y1="{pos[a][1]:.1f}" x2="{pos[b][0]:.1f}" y2="{pos[b][1]:.1f}" stroke="var(--border)" stroke-width="{1+0.7*(w-1):.1f}"/>'
        for a, b, w in edges)
    node_svg = []
    for k in keywords:
        x, y = pos[k]
        r = 13 + 16 * (len(kw_pages[k]) / maxc)
        node_svg.append(f"""  <g class="kw-node" data-kw="{esc(k)}" tabindex="0" role="button" aria-label="關鍵字 {esc(k)}">
    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{KW_COLOR.get(k, KW_UNCAT)}"/>
    <text x="{x:.1f}" y="{y+r+15:.1f}" text-anchor="middle">{esc(k)}</text>
  </g>""")
    uncat = [k for k in keywords if k not in KW_COLOR]
    if uncat:
        print("  [keywords] 未分類（顯示灰色，請歸到 KW_CATEGORIES）:", "、".join(uncat))

    # 關鍵字說明（~300 字／個），來源：keyword_notes.json（可手動編輯）
    notes_path = os.path.join(ROOT, "keyword_notes.json")
    notes = {}
    if os.path.exists(notes_path):
        with open(notes_path, encoding="utf-8") as f:
            notes = json.load(f)
    missing = [k for k in keywords if k not in notes]
    if missing:
        print("  [keywords] 缺少說明:", "、".join(missing))

    data = {"pages": [{"t": pg["title"], "u": pg["url"], "k": pg["type"], "kw": pg["kws"]} for pg in pages],
            "kw": {k: kw_pages[k] for k in keywords},
            "notes": {k: notes.get(k, "") for k in keywords}}
    data_json = json.dumps(data, ensure_ascii=False)
    legend = "".join(
        f'<span><i style="background:{color}"></i>{esc(name)}</span>'
        for name, color, kws in KW_CATEGORIES if any(k in kw_pages for k in kws))

    body = f"""<div class="wrap wide">
  <h1 class="page-title">關鍵字網路</h1>
  <p class="page-sub">節點＝關鍵字（大小＝出現次數、<b>顏色＝分類</b>），連線＝兩個關鍵字出現在同一頁。<b>點任一關鍵字</b>，下方就會列出所有提到它的頁面（概念條目與論文），等於一個搜尋。</p>
  <div class="kwnet">
    <svg id="kwsvg" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="關鍵字共現網路">
{edge_svg}
{chr(10).join(node_svg)}
    </svg>
  </div>
  <div class="legend kw-legend">{legend}</div>
  <div id="kwresult" class="kw-result"><p class="kw-hint">👆 點上面任一個關鍵字，看看哪些文章和論文提到它。</p></div>
</div>
<div class="foot">由 build.py 依各頁的 keywords 欄位自動生成。</div>
<script>
const KW = {data_json};
const net = document.querySelector('.kwnet');
const result = document.getElementById('kwresult');
function select(kw){{
  net.classList.add('has-sel');
  document.querySelectorAll('.kw-node').forEach(g => g.classList.toggle('active', g.dataset.kw === kw));
  document.querySelectorAll('.kw-edge').forEach(e =>
    e.classList.toggle('lit', e.dataset.a === kw || e.dataset.b === kw));
  const idxs = KW.kw[kw] || [];
  const items = idxs.map(i => {{
    const p = KW.pages[i];
    return '<a class="kwr-item" href="'+p.u+'"><span class="kwr-type t-'+(p.k==='概念'?'topic':'paper')+'">'+p.k+'</span>'+p.t+'</a>';
  }}).join('');
  const note = (KW.notes && KW.notes[kw]) || '';
  const desc = note ? '<div class="kwr-desc"><h3 class="kwr-kw">'+kw+'</h3>'+note+'</div>' : '';
  result.innerHTML = desc + '<div class="kwr-head">提到「<b>'+kw+'</b>」的頁面（'+idxs.length+'）：</div>'+items;
  result.scrollIntoView({{behavior:'smooth', block:'nearest'}});
}}
document.querySelectorAll('.kw-node').forEach(g => {{
  g.addEventListener('click', () => select(g.dataset.kw));
  g.addEventListener('keydown', e => {{ if(e.key==='Enter'||e.key===' '){{e.preventDefault(); select(g.dataset.kw);}} }});
}});
// 支援 ?kw=關鍵字 直接帶入（從各頁的關鍵字 badge 連過來）
const q = new URLSearchParams(location.search).get('kw');
if (q && KW.kw[q]) select(q);
</script>"""
    return page("關鍵字網路｜FlyCircuit 知識庫", "keywords", body)


# ---------------- log.html（時間軸） ----------------
def build_log(topics, papers):
    by_id = {p["id"]: ("papers", p["title_zh"]) for p in papers}
    by_id.update({t["id"]: ("topics", t["title"]) for t in topics})
    path = os.path.join(ROOT, "log.jsonl")
    entries = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    # 反向時間軸：新的在上面（日期新→舊；同一天則後加入 log.jsonl 的在上）
    order = sorted(enumerate(entries), key=lambda ie: (ie[1].get("date", ""), ie[0]), reverse=True)
    entries = [e for _i, e in order]
    rows = []
    for e in entries:
        op = e.get("op", "")
        title = esc(e.get("title", ""))
        if e.get("id") in by_id and op != "build":
            d, _t = by_id[e["id"]]
            title = f'<a href="{d}/{esc(e["id"])}.html">{esc(e.get("title",""))}</a>'
        note = f'<span style="color:var(--text-soft)"> — {esc(e["note"])}</span>' if e.get("note") else ""
        rows.append(f"""  <div class="log-entry">
    <span class="date">{esc(e.get('date',''))}</span>
    <span class="op op-{esc(op)}">{esc(OP_LABEL.get(op, op))}</span>
    <span>{title}{note}</span>
  </div>""")
    body = f"""<div class="wrap">
  <h1 class="page-title">時間軸</h1>
  <p class="page-sub">知識庫的演進紀錄（收錄 / 重建 / 查詢 / 健檢），<b>最新的在最上面</b>。資料來源：log.jsonl（append-only）。</p>
{chr(10).join(rows) if rows else '<p style="color:var(--text-soft)">尚無紀錄。</p>'}
</div>
<div class="foot">由 build.py 讀 log.jsonl 生成 · 共 {len(entries)} 筆。</div>"""
    return page("時間軸｜FlyCircuit 知識庫", "log", body)


def main():
    topics = load_dir(TOPICS_DIR)
    papers = load_dir(PAPERS_DIR)
    if not papers:
        print("找不到 papers/*.html"); return
    outputs = {
        "index.html": build_index(topics, papers),
        "papers.html": build_papers(papers),
        "graph.html": build_graph(papers),
        "keywords.html": build_keywords(topics, papers),
        "log.html": build_log(topics, papers),
    }
    for name, content in outputs.items():
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    print("done: %d topics, %d papers" % (len(topics), len(papers)))


if __name__ == "__main__":
    main()
