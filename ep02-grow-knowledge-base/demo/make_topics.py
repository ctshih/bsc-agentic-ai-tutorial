# -*- coding: utf-8 -*-
"""
make_topics.py — 一次性：產生 topics/*.html（概念條目 / wiki 文章）。
產生後 topics/*.html 即為真實來源層，日後直接編輯該頁、再跑 build.py。
"""
import json, os, html

ROOT = os.path.dirname(os.path.abspath(__file__))
TOPICS_DIR = os.path.join(ROOT, "topics")

# 論文 id → (中文標題, 年份)，給「相關論文」卡片用
PAPERS = {
    "chiang-2011-flycircuit": ("果蠅全腦連結網路的單細胞解析度三維重建", 2011),
    "shih-2015-information-flow": ("以連結體學分析果蠅腦中的資訊流", 2015),
    "kaleido-2018": ("Kaleido：以自動配色法視覺化大規模腦部單神經元影像資料", 2018),
    "community-2019": ("果蠅腦神經元層級連結體中多樣的社群結構", 2019),
    "neuroretriever-2021": ("NeuroRetriever：用於連結體組裝的自動化神經元分割演算法", 2021),
    "lynsu-2024": ("LYNSU：果蠅腦螢光影像的自動化 3D 神經氈分割方法", 2024),
}


def P(pid):
    """內文引用論文的連結。"""
    t, y = PAPERS[pid]
    return f'<a href="../papers/{pid}.html">{t}（{y}）</a>'


def topbar():
    return """<div class="topbar"><div class="inner">
  <div class="brand">🧠 腦連結體論文知識庫 <small>· BSC Knowledge Base</small></div>
  <nav>
    <a href="../index.html">首頁</a>
    <a href="../graph.html">論文網路</a>
    <a href="../keywords.html">關鍵字網路</a>
    <a href="../log.html">時間軸</a>
  </nav>
</div></div>"""


TOPICS = [
  {
    "id": "topic-connectome",
    "title": "連結體（Connectome）是什麼",
    "keywords": ["連結體", "連結體尺度", "網路分析", "果蠅腦"],
    "related": ["chiang-2011-flycircuit", "shih-2015-information-flow", "community-2019", "neuroretriever-2021", "lynsu-2024", "kaleido-2018"],
    "tldr": "連結體就是一個神經系統裡「哪個神經元連到哪個神經元」的完整線路圖；本知識庫的所有論文，都是在「建立」或「分析」果蠅腦的連結體。",
    "body": f"""
    <section class="block"><h2>一句話定義</h2>
    <p><b>連結體（connectome）</b>是一個神經系統中所有神經元、以及它們之間連結的完整地圖——簡單說，就是「<b>誰連到誰</b>」的線路圖。就像基因體（genome）是一個生物的完整基因清單，連結體是一個腦的完整接線清單。研究連結體的領域稱為 <b>connectomics（連結體學）</b>。</p></section>

    <section class="block"><h2>為什麼重要？</h2>
    <p>大腦的功能不只取決於有哪些神經元，更取決於它們<b>怎麼連</b>。同樣的元件、不同的接線，會產生完全不同的行為。因此「結構（誰連到誰）」是理解「功能（腦如何運作）」的基礎。有了連結體，研究者才能追問：訊息怎麼在腦中流動？哪些區域是樞紐？記憶、感覺、運動各靠哪些迴路？</p></section>

    <section class="block"><h2>連結體的「尺度」</h2>
    <p>連結體可以畫在不同的解析度，本知識庫用一套<b>受控詞彙</b>標示每篇論文的尺度：</p>
    <ul>
      <li><b>突觸級（synaptic）</b>：用電子顯微鏡看到每一個突觸，最精細，但資料量巨大。</li>
      <li><b>單細胞（single-cell）</b>：以「單一神經元」為單位，看神經元對神經元的連結。{P("community-2019")} 就是這個層級。</li>
      <li><b>中尺度（mesoscale）</b>：把腦分成功能區塊（如 LPU），看區塊對區塊的連結。{P("chiang-2011-flycircuit")} 與 {P("shih-2015-information-flow")} 屬此。</li>
      <li><b>巨觀（macroscale）</b>：全腦影像層級（如人腦的 fMRI / DTI）。</li>
    </ul>
    <p>尺度越精細，資料越完整、但取得與處理越困難。果蠅之所以成為理想對象，正是因為牠的腦夠小，能在單細胞解析度建出近乎完整的連結體。</p></section>

    <section class="block"><h2>在本知識庫中</h2>
    <p>這裡收錄的論文可分成兩大類，恰好對應連結體研究的兩個階段：<b>建立</b>連結體（取得影像、分割神經元、重建線路——見「<a href="topic-flycircuit.html">FlyCircuit 資料庫</a>」與「<a href="topic-imaging.html">影像方法</a>」），以及<b>分析</b>連結體（用網路科學找出其組織原則——見「<a href="topic-network.html">網路分析</a>」）。</p></section>
    """,
  },
  {
    "id": "topic-fly-brain",
    "title": "果蠅作為模式生物與大腦構造",
    "keywords": ["果蠅腦", "神經氈", "LPU", "單神經元"],
    "related": ["chiang-2011-flycircuit", "shih-2015-information-flow", "community-2019"],
    "tldr": "果蠅腦只有約十萬個神經元、又有強大的遺傳工具，是建立完整連結體最實際的模式生物；牠的腦由一塊塊「神經氈」組成，可進一步歸納成數十個「局部處理單元（LPU）」。",
    "body": f"""
    <section class="block"><h2>為什麼選果蠅？</h2>
    <p>果蠅（<i>Drosophila</i>）的腦只有約 <b>十萬個</b>神經元（人腦約八百億），小到有機會建出近乎完整的連結體，卻又複雜到能展現學習、記憶、求偶、導航等豐富行為。加上數十年累積的<b>遺傳工具</b>（可精準標記、操控特定神經元），讓研究者能在單一神經元層級觀察與實驗。這正是 {P("chiang-2011-flycircuit")} 能蒐集上萬個單神經元影像、建出 FlyCircuit 的前提。</p></section>

    <section class="block"><h2>神經氈（neuropil）</h2>
    <p>果蠅腦不是一團均勻的組織，而是由許多<b>神經氈</b>構成——神經纖維密集交織、進行訊號處理的區域，例如負責嗅覺的觸角葉（AL）、與學習記憶相關的蕈狀體（MB）、以及導航相關的中央複合體（FB/EB/PB）。辨識並分割這些神經氈，是分析的重要前處理；{P("lynsu-2024")} 就用深度學習自動分割神經氈。</p></section>

    <section class="block"><h2>局部處理單元（LPU）</h2>
    <p>把神經氈進一步歸納，{P("chiang-2011-flycircuit")} 將果蠅全腦整理成約 <b>41 個局部處理單元（LPU）</b>：每個 LPU 內部有局部中間神經元（LN），LPU 之間則由投射神經元（PN）連接。LPU 提供了一個「中尺度」的座標系——{P("shih-2015-information-flow")} 正是以 LPU 為節點，建構果蠅腦的中尺度網路。</p></section>

    <section class="block"><h2>從個體到標準腦</h2>
    <p>每隻果蠅的腦略有差異，因此研究者會把各個單神經元影像<b>配準（registration）</b>到同一個「標準模型腦」上，才能比較與整合。值得注意的是，{P("lynsu-2024")} 指出：若能在<b>個體原始影像</b>上直接分析，就能避免 warping 到標準腦所引入的空間誤差。</p></section>
    """,
  },
  {
    "id": "topic-flycircuit",
    "title": "FlyCircuit：單神經元解析度的果蠅連結體資料庫",
    "keywords": ["FlyCircuit", "單神經元", "開放資料庫", "影像配準", "果蠅腦"],
    "related": ["chiang-2011-flycircuit", "kaleido-2018", "neuroretriever-2021", "lynsu-2024", "shih-2015-information-flow", "community-2019"],
    "tldr": "FlyCircuit 是把上萬個果蠅單神經元影像配準到同一個標準腦、開放取用的資料庫，源自 2011 年的奠基論文，是本知識庫所有後續分析與工具的共同基礎。",
    "body": f"""
    <section class="block"><h2>它是什麼</h2>
    <p><b>FlyCircuit</b>（flycircuit.tw）是一個開放取用的果蠅<b>單神經元</b>三維影像資料庫。它把成千上萬個果蠅神經元，一個一個地拍下來、配準到同一個標準腦上，組成一個「虛擬果蠅腦」，供線上檢索、視覺化與分析。它是 {P("chiang-2011-flycircuit")} 的核心產物。</p></section>

    <section class="block"><h2>怎麼建出來的</h2>
    <ul>
      <li><b>單神經元標記</b>：用可控制的遺傳鑲嵌技術（MARCM）一次只讓<b>一個</b>神經元發出螢光，再以共軛焦顯微鏡取得它的高解析三維形態。</li>
      <li><b>配準到標準腦</b>：用全腦染色把每張影像對位到單一標準模型腦，使不同個體的神經元能放在同一座標系比較。</li>
      <li><b>規模</b>：奠基論文蒐集了約 <b>16,000 個</b>單神經元（佔全腦神經元逾 10%），據此定義出 41 個 LPU 與跨區纖維束。</li>
    </ul></section>

    <section class="block"><h2>為什麼是「基礎建設」</h2>
    <p>FlyCircuit 提供了後續研究共同的資料底座，本知識庫的論文幾乎都建立在它之上：{P("neuroretriever-2021")} 與 {P("lynsu-2024")} 改良它的影像分割流程、{P("kaleido-2018")} 解決它上萬神經元的視覺化瓶頸、而 {P("shih-2015-information-flow")} 與 {P("community-2019")} 則把它的影像資料推進為可做圖論分析的網路。</p></section>

    <section class="block"><h2>開放資料的價值</h2>
    <p>把資料<b>開放</b>出來，讓不同團隊能在同一份基礎上各自發展工具與分析，是 FlyCircuit 影響力的關鍵——這也呼應了本知識庫想傳達的精神：好的基礎建設會讓知識複利成長。</p></section>
    """,
  },
  {
    "id": "topic-imaging",
    "title": "從影像到連結體：分割、重建與視覺化方法",
    "keywords": ["影像分割", "深度學習", "神經元追蹤", "視覺化", "影像配準", "神經氈"],
    "related": ["neuroretriever-2021", "lynsu-2024", "kaleido-2018", "chiang-2011-flycircuit"],
    "tldr": "原始顯微影像要先「分割」出單一神經元或神經氈、重建形態、再「視覺化」，才能變成可分析的連結體；這條工具鏈是建立連結體的速率限制步驟，本知識庫有三篇論文專門在改良它。",
    "body": f"""
    <section class="block"><h2>從一張張影像，到一個連結體</h2>
    <p>顯微鏡拍到的是充滿雜訊的原始螢光影像。要變成連結體，中間要經過一條<b>影像處理流程</b>：把單一神經元或神經氈<b>分割</b>出來 → 重建其三維形態 → 配準到標準腦 → 最後<b>視覺化</b>讓人檢視。這條流程長期是高通量連結體重建的<b>速率限制步驟</b>，因此本知識庫有三篇論文專門在加速它。</p></section>

    <section class="block"><h2>神經元分割：NeuroRetriever（2021）</h2>
    <p>{P("neuroretriever-2021")} 提出自動化、無偏誤的單神經元分割。它用「分支穩健性分數」產生高動態範圍（HDR）閾值遮罩，搭配 FAST 追蹤演算法，能像人眼一樣依局部邊界判斷、同時去雜訊又保留弱訊號細部。套用到 FlyCircuit 的 22,037 張原始影像，自動擷取出 28,125 個單神經元，把原本仰賴人工的瓶頸自動化。</p></section>

    <section class="block"><h2>神經氈分割：LYNSU（2024）</h2>
    <p>{P("lynsu-2024")} 用<b>深度學習</b>分割神經氈：先用 YOLOv7 快速定位（準確率 99.4%），再用 3D U-Net 逐 voxel 分割。每個神經氈只需約 7 秒（人工需約 4 小時），精度媲美人工標註，並能在個體原始影像上直接分析、免除配準誤差。</p></section>

    <section class="block"><h2>視覺化：Kaleido（2018）</h2>
    <p>分割重建之後，還要讓人「看得到」。{P("kaleido-2018")} 解決了「上萬個神經元無法同時視覺化」的記憶體瓶頸：用 Monte Carlo 最佳化能量函數，自動為相鄰神經元配上對比鮮明的顏色，讓密集處（如蕈狀體 calyx）也能清楚辨識，並可依生物意義（出生日期、神經傳導物質）配色。</p></section>
    """,
  },
  {
    "id": "topic-network",
    "title": "果蠅連結體的網路分析",
    "keywords": ["網路分析", "資訊流", "社群結構", "富俱樂部", "小世界", "中心性", "連結體"],
    "related": ["shih-2015-information-flow", "community-2019"],
    "tldr": "把連結體當成一張「圖」，用網路科學的工具（社群、中心性、富俱樂部、小世界）來分析，就能找出果蠅腦的組織原則：模組化、有樞紐、訊息怎麼流動。",
    "body": f"""
    <section class="block"><h2>把腦當成一張網路</h2>
    <p>有了連結體，就能把它當成一張<b>圖（graph）</b>：神經元或腦區是<b>節點</b>，連結是<b>邊</b>。如此一來，數十年來發展的<b>網路科學</b>工具——社群偵測、中心性、富俱樂部、小世界——都能拿來分析腦的組織原則。本知識庫有兩篇論文示範了這件事。</p></section>

    <section class="block"><h2>中尺度的資訊流：Shih 2015</h2>
    <p>{P("shih-2015-information-flow")} 以 LPU 為節點、建出果蠅腦的<b>有向加權</b>連結體。發現它具<b>小世界</b>特性與階層模組（對應嗅覺、聽覺、左右視覺與前運動五大功能模組），並存在涵蓋所有感覺中樞的<b>富俱樂部（rich club）</b>。藉由模擬訊號傳播，還能推測行為時資訊在腦中的流動路徑。</p></section>

    <section class="block"><h2>單細胞的社群結構：Community 2019</h2>
    <p>{P("community-2019")} 進一步在<b>神經元對神經元</b>的層級分析。從近兩萬個神經元的網路中，辨識出八個與功能模組對應的<b>社群</b>（左右嗅覺、聽覺、運動、前運動、左右視覺等），並發現不同功能的社群主導不同類型的<b>中心性</b>；其富俱樂部核心多投射至中央複合體，暗示它在資訊整合中的樞紐角色。</p></section>

    <section class="block"><h2>共同的發現</h2>
    <p>兩篇論文在不同尺度上得到一致的圖像：果蠅腦是<b>模組化</b>的、有少數高度互連的<b>樞紐</b>、整體呈<b>小世界</b>，而且這些組織特徵與哺乳類腦有基本相似性。這說明「用網路科學看腦」是一個跨物種通用的視角。</p></section>
    """,
  },
]


def render(t):
    kbadges = "".join(
        f'<a class="badge" href="../keywords.html?kw={html.escape(k, quote=True)}">{html.escape(k)}</a>'
        for k in t["keywords"])
    rel = "\n".join(
        f'      <a href="../papers/{pid}.html"><span class="ry">{PAPERS[pid][1]} · 論文</span><br>'
        f'<span class="rt">{html.escape(PAPERS[pid][0])}</span></a>'
        for pid in t["related"])
    meta = {"id": t["id"], "type": "topic", "title": t["title"],
            "keywords": t["keywords"], "related": t["related"], "tldr": t["tldr"]}
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(t["title"])}｜FlyCircuit 知識庫</title>
<link rel="stylesheet" href="../assets/style.css">
<script type="application/json" id="meta">
{meta_json}
</script>
</head>
<body>
{topbar()}
<div class="wrap">
  <article>
    <header class="paper-header">
      <span class="badge scale" style="background:#7c3aed">概念條目</span>
      <h1>{html.escape(t["title"])}</h1>
      <div class="badges" style="margin-top:14px">{kbadges}</div>
    </header>
    <div class="callout"><span class="label">一句話</span>{html.escape(t["tldr"])}</div>
    {t["body"]}
    <section class="block">
      <h2>相關論文</h2>
      <div class="related-grid">
{rel}
      </div>
    </section>
  </article>
</div>
<div class="foot">概念條目由 LLM 綜整本知識庫論文撰寫；點關鍵字可在「關鍵字網路」看到所有相關頁面。｜id: <code>{t["id"]}</code></div>
</body>
</html>
"""


def main():
    os.makedirs(TOPICS_DIR, exist_ok=True)
    for t in TOPICS:
        out = os.path.join(TOPICS_DIR, t["id"] + ".html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(t))
        print("wrote topics/%s.html" % t["id"])


if __name__ == "__main__":
    main()
