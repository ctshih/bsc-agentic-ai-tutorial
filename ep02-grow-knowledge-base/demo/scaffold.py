# -*- coding: utf-8 -*-
"""
scaffold.py — 一次性：用 v1 論文資料 (data/papers.json) 產生 papers/*.html 與初始 log.jsonl。

⚠ 這支只在「建立第一版」時跑一次。
   日後請直接編輯 papers/*.html（那才是知識庫的真實來源 source of truth），
   不要再回頭跑這支，否則會覆蓋你對論文頁的手動修改。
   日常只需在 ingest / 改頁之後跑 build.py 重生導覽頁。
"""
import json
import os
import html
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
PAPERS_DIR = os.path.join(ROOT, "papers")

# scale（研究尺度）→（顯示色, 中文標籤）
SCALE = {
    "mesoscale":   ("#2563eb", "中尺度"),
    "single-cell": ("#0d9488", "單細胞"),
    "synaptic":    ("#db2777", "突觸級"),
    "macroscale":  ("#7c3aed", "巨觀"),
    "method/tool": ("#ea580c", "方法/工具"),
}


def esc(s):
    return html.escape(str(s), quote=True)


def scale_color(scale):
    return SCALE.get(scale, ("#64748b", scale))[0]


def scale_label(scale):
    return SCALE.get(scale, ("#64748b", scale))[1]


def topbar(active):
    def cls(name):
        return ' class="active"' if name == active else ""
    return f"""<div class="topbar"><div class="inner">
  <div class="brand">🧠 腦連結體論文知識庫 <small>· BSC Knowledge Base</small></div>
  <nav>
    <a href="../index.html"{cls('index')}>論文目錄</a>
    <a href="../graph.html"{cls('graph')}>連結網路</a>
    <a href="../log.html"{cls('log')}>時間軸</a>
  </nav>
</div></div>"""


def render_page(rec, by_id):
    sc = rec["scale"]
    badges = [
        f'<span class="badge scale" style="background:{scale_color(sc)}">{esc(scale_label(sc))}</span>',
        f'<span class="badge muted">{esc(rec["year"])}</span>',
        f'<span class="badge muted">{esc(rec["venue"])}</span>',
        f'<span class="badge">{esc(rec["species"])}</span>',
    ]
    if rec.get("dataset") and rec["dataset"] != "—":
        badges.append(f'<span class="badge">{esc(rec["dataset"])}</span>')
    for t in rec.get("technique", []):
        badges.append(f'<span class="badge muted">{esc(t)}</span>')

    authors = "、".join(rec.get("authors", []))

    doi_html = ""
    if rec.get("doi"):
        doi_html = f' · DOI: <a href="https://doi.org/{esc(rec["doi"])}" target="_blank" rel="noopener">{esc(rec["doi"])}</a>'
    pdf_html = ""
    if rec.get("source_pdf"):
        url = "file:///" + rec["source_pdf"].replace(" ", "%20")
        pdf_html = f' · <a href="{esc(url)}">原始 PDF ↗</a>'

    findings = "\n".join(f"      <li>{esc(x)}</li>" for x in rec.get("key_findings", []))

    related_cards = []
    for rid in rec.get("related", []):
        r = by_id.get(rid)
        if not r:
            continue
        related_cards.append(
            f'      <a href="{esc(rid)}.html"><span class="ry">{esc(r["year"])} · {esc(r["venue"])}</span><br>'
            f'<span class="rt">{esc(r["title_zh"])}</span></a>'
        )
    related_html = "\n".join(related_cards) if related_cards else '      <p style="color:var(--text-soft)">（暫無）</p>'

    # 機器可讀 metadata：這段是本頁的「真實來源」，build.py 會解析它來生導覽頁
    meta_json = json.dumps(rec, ensure_ascii=False, indent=2)

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(rec["title_zh"])}｜FlyCircuit 知識庫</title>
<link rel="stylesheet" href="../assets/style.css">
<script type="application/json" id="meta">
{meta_json}
</script>
</head>
<body>
{topbar('paper')}
<div class="wrap">
  <article>
    <header class="paper-header">
      <h1>{esc(rec["title"])}</h1>
      <p class="title-zh">{esc(rec["title_zh"])}</p>
      <p class="authors">{esc(authors)}</p>
      <div class="badges">
        {''.join(badges)}
      </div>
      <p class="meta-line">{esc(rec["venue"])} ({esc(rec["year"])}){doi_html}{pdf_html}</p>
    </header>

    <div class="callout">
      <span class="label">一句話總結</span>
      {esc(rec["tldr"])}
    </div>

    <section class="block">
      <h2>中文摘要</h2>
      <p>{esc(rec["abstract_zh"])}</p>
    </section>

    <section class="block">
      <h2>關鍵發現</h2>
      <ul>
{findings}
      </ul>
    </section>

    <section class="block">
      <h2>方法</h2>
      <p>{esc(rec["methods"])}</p>
    </section>

    <section class="block">
      <h2>重要性與定位</h2>
      <p>{esc(rec["significance"])}</p>
    </section>

    <section class="block">
      <h2>相關論文</h2>
      <div class="related-grid">
{related_html}
      </div>
    </section>
  </article>
</div>
<div class="foot">
  本頁由 LLM 依原始 PDF 整理；中文重點為摘要性質，引用前請以原文為準。｜id: <code>{esc(rec["id"])}</code>
</div>
</body>
</html>
"""


def main():
    with open(os.path.join(ROOT, "data", "papers.json"), encoding="utf-8") as f:
        papers = json.load(f)
    by_id = {p["id"]: p for p in papers}

    os.makedirs(PAPERS_DIR, exist_ok=True)
    for rec in papers:
        out = os.path.join(PAPERS_DIR, rec["id"] + ".html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render_page(rec, by_id))
        print("wrote papers/%s.html" % rec["id"])

    # 初始時間軸：每篇一筆 ingest + 一筆 build
    today = "2026-06-22"
    log_path = os.path.join(ROOT, "log.jsonl")
    lines = []
    for rec in papers:
        lines.append(json.dumps({
            "date": today, "op": "ingest", "id": rec["id"],
            "title": rec["title_zh"],
            "note": "由原始 PDF 抽取 metadata 與中文重點，建立論文頁"
        }, ensure_ascii=False))
    lines.append(json.dumps({
        "date": today, "op": "build", "id": "", "title": "建立第一版知識庫 (v1)",
        "note": "%d 篇論文，產生目錄、連結網路與時間軸" % len(papers)
    }, ensure_ascii=False))
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote log.jsonl (%d entries)" % len(lines))


if __name__ == "__main__":
    main()
