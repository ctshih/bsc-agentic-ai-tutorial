# -*- coding: utf-8 -*-
"""
build.py — 知識庫的常駐工具（steady-state）。

掃描 papers/*.html，從每頁內嵌的 <script id="meta"> 取出 metadata，
重新生成三個導覽頁：
  - index.html  論文目錄（可依物種 / 尺度 / 方法篩選 + 全文搜尋）
  - graph.html  論文之間的連結網路圖（related 關係）
  - log.html    時間軸（讀 log.jsonl）

日常流程：編輯或新增 papers/*.html 之後，跑一次   python build.py
論文頁本身是「真實來源」，本工具只讀不改它們。
"""
import json
import os
import re
import glob
import html
import math

ROOT = os.path.dirname(os.path.abspath(__file__))
PAPERS_DIR = os.path.join(ROOT, "papers")

SCALE = {
    "mesoscale":   ("#2563eb", "中尺度"),
    "single-cell": ("#0d9488", "單細胞"),
    "synaptic":    ("#db2777", "突觸級"),
    "macroscale":  ("#7c3aed", "巨觀"),
    "method/tool": ("#ea580c", "方法/工具"),
}
OP_LABEL = {"ingest": "收錄", "build": "重建", "query": "查詢", "lint": "健檢"}
OP_ORDER = {"ingest": 0, "query": 1, "lint": 2, "build": 3}

META_RE = re.compile(
    r'<script type="application/json" id="meta">(.*?)</script>', re.DOTALL)


def esc(s):
    return html.escape(str(s), quote=True)


def scolor(s):
    return SCALE.get(s, ("#64748b", s))[0]


def slabel(s):
    return SCALE.get(s, ("#64748b", s))[1]


def topbar(active):
    def cls(name):
        return ' class="active"' if name == active else ""
    return f"""<div class="topbar"><div class="inner">
  <div class="brand">🧠 FlyCircuit 連結體論文知識庫 <small>· BSC Knowledge Base</small></div>
  <nav>
    <a href="index.html"{cls('index')}>論文目錄</a>
    <a href="graph.html"{cls('graph')}>連結網路</a>
    <a href="log.html"{cls('log')}>時間軸</a>
  </nav>
</div></div>"""


def load_papers():
    recs = []
    for path in sorted(glob.glob(os.path.join(PAPERS_DIR, "*.html"))):
        with open(path, encoding="utf-8") as f:
            m = META_RE.search(f.read())
        if not m:
            print("  ! 無 metadata，略過:", os.path.basename(path))
            continue
        recs.append(json.loads(m.group(1)))
    return recs


def page(title, active, body, with_js=False):
    js = '<script src="assets/wiki.js"></script>' if with_js else ""
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
{topbar(active)}
{body}
{js}
</body>
</html>
"""


# ---------------- index.html ----------------
def build_index(recs):
    species = sorted({r["species"] for r in recs})
    scales = sorted({r["scale"] for r in recs}, key=lambda s: OP_ORDER.get(s, 9))
    techs = sorted({t for r in recs for t in r.get("technique", [])})

    yrs = [r["year"] for r in recs]
    venues = {r["venue"] for r in recs}
    edges = count_edges(recs)
    stats = [
        (len(recs), "篇論文"),
        (f"{min(yrs)}–{max(yrs)}", "年份跨度"),
        (len(venues), "個期刊"),
        (edges, "條關聯"),
    ]
    stat_html = "\n".join(
        f'    <div class="stat"><div class="n">{esc(n)}</div><div class="l">{esc(l)}</div></div>'
        for n, l in stats)

    def opts(values, labeler=lambda v: v):
        return "\n".join(
            f'      <option value="{esc(v)}">{esc(labeler(v))}</option>' for v in values)

    cards = []
    for r in sorted(recs, key=lambda r: (-r["year"], r["title"])):
        tech_attr = "|" + "|".join(r.get("technique", [])) + "|"
        search = " ".join([
            r["title"], r["title_zh"], " ".join(r.get("authors", [])),
            r["venue"], " ".join(r.get("tags", [])), r.get("tldr", ""), str(r["year"]),
        ]).lower()
        badges = [
            f'<span class="badge scale" style="background:{scolor(r["scale"])}">{esc(slabel(r["scale"]))}</span>',
            f'<span class="badge muted">{esc(r["venue"])}</span>',
            f'<span class="badge">{esc(r["species"])}</span>',
        ]
        if r.get("dataset") and r["dataset"] != "—":
            badges.append(f'<span class="badge">{esc(r["dataset"])}</span>')
        cards.append(f"""    <article class="card"
      data-species="{esc(r['species'])}" data-scale="{esc(r['scale'])}"
      data-technique="{esc(tech_attr)}" data-search="{esc(search)}">
      <h3><a href="papers/{esc(r['id'])}.html">{esc(r['title_zh'])}</a></h3>
      <p class="cyr">{esc(r['year'])} · {esc(', '.join(r.get('authors', [])[:3]))} et al.</p>
      <div class="badges">{''.join(badges)}</div>
      <p class="ctldr">{esc(r.get('tldr', ''))}</p>
    </article>""")

    body = f"""<div class="wrap wide">
  <h1 class="page-title">論文目錄</h1>
  <p class="page-sub">果蠅（Drosophila）連結體研究與 FlyCircuit 工具鏈。點任一篇進入整理頁。</p>
  <div class="stats">
{stat_html}
  </div>
  <div class="filters">
    <input id="q" type="search" placeholder="🔍 搜尋標題、作者、關鍵字…">
    <select id="f-species"><option value="">物種（全部）</option>
{opts(species)}
    </select>
    <select id="f-scale"><option value="">尺度（全部）</option>
{opts(scales, slabel)}
    </select>
    <select id="f-technique"><option value="">方法（全部）</option>
{opts(techs)}
    </select>
    <button id="reset">清除</button>
    <span id="count"></span>
  </div>
  <div class="cards">
{chr(10).join(cards)}
  </div>
</div>
<div class="foot">由 build.py 自動生成 · 共 {len(recs)} 篇 · 編輯論文請改 papers/*.html 後重跑 build.py</div>"""
    return page("論文目錄｜FlyCircuit 知識庫", "index", body, with_js=True)


# ---------------- graph.html ----------------
def count_edges(recs):
    ids = {r["id"] for r in recs}
    edges = set()
    for r in recs:
        for rid in r.get("related", []):
            if rid in ids:
                edges.add(frozenset((r["id"], rid)))
    return len(edges)


def build_graph(recs):
    ids = [r["id"] for r in recs]
    idset = set(ids)
    by_id = {r["id"]: r for r in recs}
    edges = set()
    for r in recs:
        for rid in r.get("related", []):
            if rid in idset and rid != r["id"]:
                edges.add(frozenset((r["id"], rid)))

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

    edge_svg = []
    for e in edges:
        a, b = tuple(e)
        x1, y1, _ = pos[a]
        x2, y2, _ = pos[b]
        edge_svg.append(
            f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="var(--border)" stroke-width="1.6" />')

    node_svg = []
    for i in ids:
        x, y, ang = pos[i]
        r = by_id[i]
        rad = 15 + deg[i] * 3
        short = i.split("-")[0]
        short = {"lynsu": "LYNSU", "neuroretriever": "NeuroRetriever"}.get(short, short.capitalize())
        label = f"{short} {r['year']}"
        lx = x + (rad + 10) * math.cos(ang)
        ly = y + (rad + 10) * math.sin(ang)
        anchor = "start" if math.cos(ang) >= 0 else "end"
        dy = "0.7em" if math.sin(ang) > 0.3 else ("-0.2em" if math.sin(ang) < -0.3 else "0.32em")
        node_svg.append(f"""  <a href="papers/{esc(i)}.html" class="graph-node">
    <title>{esc(r['title_zh'])}</title>
    <circle cx="{x:.1f}" cy="{y:.1f}" r="{rad}" fill="{scolor(r['scale'])}" stroke="var(--surface)" stroke-width="2.5" />
    <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dy="{dy}">{esc(label)}</text>
  </a>""")

    used_scales = [s for s in SCALE if any(r["scale"] == s for r in recs)]
    legend = "".join(
        f'<span><i style="background:{scolor(s)}"></i>{esc(slabel(s))}</span>' for s in used_scales)

    body = f"""<div class="wrap wide">
  <h1 class="page-title">連結網路</h1>
  <p class="page-sub">節點＝論文（顏色＝研究尺度，大小＝關聯數），連線＝彼此引用或延伸關係。點節點進入該論文。</p>
  <div class="graph-wrap">
    <svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="論文連結網路圖">
{chr(10).join(edge_svg)}
{chr(10).join(node_svg)}
    </svg>
  </div>
  <div class="legend">{legend}</div>
</div>
<div class="foot">由 build.py 依各論文頁的 related 欄位自動生成。</div>"""
    return page("連結網路｜FlyCircuit 知識庫", "graph", body)


# ---------------- log.html ----------------
def build_log(recs):
    by_id = {r["id"]: r for r in recs}
    path = os.path.join(ROOT, "log.jsonl")
    entries = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    entries.sort(key=lambda e: (e.get("date", ""), OP_ORDER.get(e.get("op"), 9)))

    rows = []
    for e in entries:
        op = e.get("op", "")
        title = e.get("title", "")
        if e.get("id") in by_id and op != "build":
            title = f'<a href="papers/{esc(e["id"])}.html">{esc(title)}</a>'
        else:
            title = esc(title)
        note = f'<span style="color:var(--text-soft)"> — {esc(e["note"])}</span>' if e.get("note") else ""
        rows.append(f"""  <div class="log-entry">
    <span class="date">{esc(e.get('date',''))}</span>
    <span class="op op-{esc(op)}">{esc(OP_LABEL.get(op, op))}</span>
    <span>{title}{note}</span>
  </div>""")

    body = f"""<div class="wrap">
  <h1 class="page-title">時間軸</h1>
  <p class="page-sub">知識庫的演進紀錄（收錄 / 重建 / 查詢 / 健檢）。資料來源：log.jsonl（append-only）。</p>
{chr(10).join(rows) if rows else '<p style="color:var(--text-soft)">尚無紀錄。</p>'}
</div>
<div class="foot">由 build.py 讀 log.jsonl 生成 · 共 {len(entries)} 筆。</div>"""
    return page("時間軸｜FlyCircuit 知識庫", "log", body)


def main():
    recs = load_papers()
    if not recs:
        print("找不到任何 papers/*.html，請先跑 scaffold.py")
        return
    outputs = {
        "index.html": build_index(recs),
        "graph.html": build_graph(recs),
        "log.html": build_log(recs),
    }
    for name, content in outputs.items():
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    print("done: %d papers, %d edges" % (len(recs), count_edges(recs)))


if __name__ == "__main__":
    main()
