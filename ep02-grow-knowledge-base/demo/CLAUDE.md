# CLAUDE.md — 腦連結體論文知識庫（schema 層）

> 這是知識庫的「設定檔／維護規則」。任何 LLM agent（Claude Code 等）在這個資料夾工作前，**先讀完本檔**，照規則維護，不要當成一般聊天。
> 靈感來自 Karpathy 的 LLM Wiki 模式（見 `references/karpathy-llm-wiki.md`），但**改用 HTML** 當人類可讀層，對非工程背景的 BSC 同仁更易讀、資訊更豐富。

---

## 1. 這個知識庫在做什麼

把「連結體（connectome）相關論文」整理成一個**會持續累積、互相連結的 HTML 知識庫**。
原始 PDF 進來 → LLM 讀懂、抽重點、寫成一頁 HTML、更新關聯 → 人用瀏覽器瀏覽。
知識被**編譯一次後保持更新**，而不是每次提問才從頭 RAG。

主題範圍：以**果蠅（Drosophila）腦連結體與 FlyCircuit 資料庫及其工具鏈（影像分割、視覺化、網路分析）為核心**，並延伸收錄**通用／跨物種的連結體重建與成像方法**（如 EM／光學顯微鏡的神經元分割與重建、哺乳類腦連結體、神經活性記錄等），以利對照與脈絡化。

---

## 2. 三層架構

| 層 | 位置 | 誰擁有 | 說明 |
|---|---|---|---|
| **原始來源** | `F:/FlyCircuit/Papers/`（及未來的 `sources/`） | 人 | 不可變的 PDF / 圖。LLM 只讀不改。 |
| **Wiki（人讀層）** | `papers/*.html`（論文）＋ `topics/*.html`（概念條目） | LLM | **真實來源 (source of truth)**。每頁含豐富中文內容 + 內嵌機器可讀 metadata。 |
| **導覽（自動生成）** | `index.html` `papers.html` `graph.html` `keywords.html` `log.html` | build.py | 由 papers + topics 自動重生，**不要手改**。 |

兩種「人讀」頁：
- **論文頁 `papers/<id>.html`**：一篇論文一頁（摘要／關鍵發現／方法／重要性／相關論文）。
- **概念條目 `topics/<id>.html`**：綜整多篇論文寫成的 wiki 文章，建立全貌、連到相關論文、列出關鍵字。**首頁（index）只放概念條目（主題地圖，可切換條列／磚塊，預設條列）**；完整論文清單獨立成 `papers.html`，首頁只放一個入口連結（論文會越來越多）。

```
Knowledge/
├── CLAUDE.md              # 本檔（schema / 維護規則）
├── index.html      *      # 概念導向首頁（只放主題地圖＋論文清單入口；條列/磚塊切換）
├── papers.html     *      # 完整論文清單（依年份；首頁的入口連到這）
├── graph.html      *      # 論文連結網路（節點標籤＝英文主題＋年份；作者含 BSC 成員者加框）
├── keywords.html   *      # 關鍵字網路（點關鍵字＝顯示 ~300 字說明＋搜尋出所有相關頁面）
├── log.html        *      # 時間軸
├── log.jsonl              # 時間軸 append-only 資料
├── keyword_notes.json     # 關鍵字說明（~300 字/個）→ build.py 嵌入 keywords.html
├── build.py               # ★常駐工具：papers + topics → 四個導覽頁
├── make_topics.py         # 一次性概念條目產生器（已用過，平時別再跑）
├── scaffold.py            # 一次性論文頁產生器（已用過，平時別再跑）
├── data/papers.json       # 建庫種子（非真實來源，build.py 不讀）
├── assets/style.css       # 共用樣式（一改全站變）
├── papers/<id>.html       # ★論文頁（真實來源）
├── topics/<id>.html       # ★概念條目（真實來源）
└── references/            # 參考素材（Karpathy 原文等）
        ( * = 自動生成，勿手改 )
```

---

## 3. 論文頁慣例（papers/<id>.html）

每頁結構固定（照現有頁即可）：
- `<head>` 內含 **`<script type="application/json" id="meta">…</script>`** — 這是該頁的 metadata，也是 build.py 唯一解析的東西。**改 metadata 要改這裡**。
- `<body>` 是人讀內容，固定順序：標題、badges、一句話總結（callout）、**論文基本資料**、中文摘要、**科普版介紹**、**學術版介紹**、相關論文。
  - **論文基本資料**（`section.bib-block`，接在 callout 後）：期刊／卷期／頁碼／發表年月／機構，用 `<dl class="bib">`，**機構全部寫成一列**（institution 層級、去重、`；` 分隔）。資料同時存進 meta 的 `bib`。
  - **科普版介紹**（`section.popsci-block`，接在中文摘要後）：讀者對象＝對科學有興趣的高中生，**1500–2000 字**，白話、可用比喻；h2 後接 `<span class="aud aud-pop">` 標讀者。
  - **學術版介紹**（`section.academic-block`，接在科普版後）：讀者對象＝研究生以上專業人士；內含 `<h3>` 子段 **關鍵發現／方法／重要性與定位**（即原本那三段的擴寫版，方法要詳細），取代舊的獨立三段；h2 後接 `<span class="aud aud-aca">`。
  - 寫這三項**務必回原始 PDF 重讀**，不要只用既有文字擴寫（使用者要求）。
  - **數學式用 LaTeX**：每個論文頁 `<head>` 都載入 MathJax 3（CDN，`tex-mml-chtml.js`）。方程式寫成 LaTeX——行內 `\( … \)`、獨立置中 `\[ … \]`（HTML 內直接寫單一反斜線）。**注意：絕不可把 `\(` 之類反斜線寫進 `<script id="meta">` 的 JSON**（會讓 JSON 失效）——meta 維持純文字數據，LaTeX 只放在 `<body>`。新論文頁照辦：head 加 MathJax loader、body 數學用 LaTeX。
  - **另一個雷（務必）**：內文與方程式裡的不等號 `<`、`>` 一律寫成 `&lt;`、`&gt;`（**即使在 `\( … \)` 內也是**）。否則瀏覽器在 MathJax 執行前就把「`< 0.001`」當成 HTML 標籤、連同後面內容一起吃掉，造成渲染錯亂與括號失衡。收錄後用「body 裡是否有非標籤的裸 `<`」與全形括號平衡做 lint。
- 樣式全靠 `../assets/style.css`，不要在頁內寫死樣式（保留 `badge.scale` 的 `background` inline 色票即可）。

### metadata 欄位

| 欄位 | 必填 | 說明 |
|---|---|---|
| `id` | ✓ | 檔名（不含 .html）。命名：`<第一作者姓氏或工具名>-<年>-<關鍵字?>`，全小寫、連字號。例 `chiang-2011-flycircuit`。 |
| `title` / `title_zh` | ✓ | 英文原標題 / 中文標題（可意譯）。 |
| `authors` | ✓ | 陣列，最多約 6 位後接 `"et al."`。 |
| `year` `venue` `doi` | ✓/✓/可空 | 年份、期刊、DOI（有就填，會自動連到 doi.org）。 |
| `bib` | ✓ | 物件：`{journal, volume, issue, pages, published, institutions[]}`。驅動「論文基本資料」區塊。`pages` 可放頁碼範圍或文章編號；`published` 用「YYYY 年 M 月」；`institutions` 收斂到機構層級、去重。 |
| `species` | ✓ | 如 `Drosophila (adult)`。 |
| `scale` | ✓ | 研究尺度，**用受控詞彙**（見 §5）。 |
| `technique` | ✓ | 陣列，方法關鍵字（會變成目錄的「方法」篩選選項）。 |
| `region` | ✓ | 腦區或 `whole brain` / `N/A`。 |
| `dataset` | 可 | 如 `FlyCircuit v1.2`；無則 `—`。 |
| `tags` | 可 | 自由標籤（中英皆可，進全文搜尋）。 |
| `keywords` | ✓ | 陣列，**統一關鍵字詞彙**（中文為主）← `keywords.html` 關鍵字網路的來源；同一關鍵字會把概念條目與論文串起來。 |
| `node_label` | ✓ | 論文網路節點短標：**主題／工具名／年份**（英文，可縮寫；有命名工具/資料庫才放中段，沒有就「主題／年份」兩段）。例 `Vis/Kaleido/2018`、`Seg/NeuroRetriever/2021`、`DB/FlyCircuit/2011`、`Info Flow/2015`。（用英文是使用者要求；同一主題用一致字眼）。 |
| `related` | ✓ | 其他論文 **id 陣列** ← 這就是 `graph.html` 的連線來源。雙向擇一即可，build.py 會去重。 |
| `tldr` | ✓ | 一句話總結（繁中）。 |
| `abstract_zh` `key_findings` `methods` `significance` | ✓ | 中文摘要 / 關鍵發現（陣列）/ 方法 / 重要性。 |

（註：不放 `source_pdf` 等本機絕對路徑——會在公開網站洩漏本機資料夾結構。引用來源用 `doi`。）

**BSC 成員加框**：論文網路（graph.html）中，若論文 `authors` 含 BSC（腦空間體中心）成員，節點會加上橘色外框 highlight。名單寫在 `build.py` 的 `BSC_MEMBERS` set（用與 authors 一致的英文全名），**會持續增加，遇到新成員就加進去**。目前成員：`Chi-Tin Shih`（施奇廷）、`Ann-Shyn Chiang`（江安世）、`Ting-Kuo Lee`（李定國）、`Chung-Chuan Lo`（羅中泉）、`Ching-Che Charng`（強敬哲）、`Kuan-Lin Feng`（馮冠霖）。

**語言**：人讀內容一律**繁體中文（台灣）**，技術術語、專有名詞、作者名、標題保留原文。中文重點屬摘要性質，提醒讀者引用前以原文為準。

### 概念條目慣例（topics/<id>.html）
概念條目是「綜整多篇論文」寫成的 wiki 文章。結構照現有頁：`<head>` 內嵌 metadata、`<body>` 為 wiki 內文。metadata 欄位：

| 欄位 | 說明 |
|---|---|
| `id` | 檔名，慣例 `topic-<關鍵字>`，全小寫。 |
| `type` | 固定 `"topic"`（與論文頁區分）。 |
| `title` | 概念標題（繁中）。 |
| `keywords` | 陣列，統一關鍵字（驅動關鍵字網路）。 |
| `related` | 相關論文 **id 陣列**（內文也用 `<a href="../papers/<id>.html">` 連過去）。 |
| `tldr` | 一句話總結（繁中）。 |

內文每個關鍵字 badge 連到 `../keywords.html?kw=<關鍵字>`（點了會在關鍵字網路自動搜尋）。新增概念條目：仿照現有 `topics/*.html` 寫一頁（或用 `make_topics.py`，一次性、會覆蓋，平時別跑）。

---

## 4. 操作流程（Ingest / Query / Lint）

### Ingest（收錄一篇新論文）
> 原始 PDF 放 `F:/FlyCircuit/Papers/`（或 `sources/`）；`papers/` 放生成的 HTML 頁。**務必回原始 PDF 重讀**，不要只憑既有文字擴寫。

**A. 精讀與抽取**（派 subagent，一篇一個；篇數多就平行）
1. **定 `id`**：`<第一作者姓氏或工具名>-<年>-<關鍵字?>`，全小寫連字號。
2. **抽 §3 全部 metadata**：含 `scale`（受控詞彙，見 §5）、`keywords`（用既有統一詞彙）、`node_label`（**英文「主題／工具名／年份」**）、`related`、`tldr` 等。
3. **抽 `bib`**：期刊／卷／期／頁碼或文章編號／發表年月／機構（收斂到機構層級、去重）。
4. **抽人讀內容**：中文摘要、關鍵發現、詳細方法、重要性，外加**科普版介紹（高中生向 1500–2000 字）**與**學術版介紹（研究人員向，含關鍵發現／詳細方法／重要性三 h3 子段）**。

**B. 產生 `papers/<id>.html`**（仿現有頁）
5. body 固定順序：標題/badges → 一句話總結 → 論文基本資料 → 中文摘要 → 科普版 → 學術版 → 相關論文（見 §3）。`<head>` 內嵌 meta JSON（含 `bib`）＋ **MathJax loader**；方程式寫 **LaTeX**（`\(…\)`／`\[…\]`），**反斜線不可進 meta JSON**。

**C. 串接關聯**
6. **`related` 雙向**：新頁連舊頁，並視情況把相關舊頁的 `related` 加回新頁（驅動 `graph.html` 連線）。
7. **關鍵字**：沿用既有詞彙；若引入**新關鍵字**，到 `keyword_notes.json` 補一則約 300 字說明（否則 build.py 警告、點了沒說明卡）。
8. **概念條目**：若延伸既有主題，在相關 `topics/*.html` 補述並把新 id 加進它的 `related`；若帶出全新主題，評估是否新增一篇概念條目。
9. **BSC 成員**：作者若含新的 BSC 成員，把英文全名加進 `build.py` 的 `BSC_MEMBERS`（節點才會加框）。

**D. 收尾與驗證**
10. `log.jsonl` **append 一行** ingest 紀錄（格式見下）。
11. 跑 `python build.py` 重生五個導覽頁（**不要**跑 `scaffold.py` / `make_topics.py`）。
12. **驗證**：preview/headless 檢查新頁渲染（MathJax、段落、bib）；確認 graph 有新節點與連線、keywords 有新關鍵字、papers.html 出現新論文；meta JSON 合法、標點 lint、`related` 沒指向不存在的 id。
13. 給使用者看新頁與更新處，提醒科普／學術內容請過目。

### Query（對知識庫提問）
- 先看 `index.html`／各頁 metadata 找相關論文 → 讀該頁 → 綜整作答並附出處（連到論文頁）。
- **好答案要回存**：值得留下的比較表、整理、洞見，新增成一頁（可放 `papers/` 或未來的 `topics/`），別讓它只留在對話裡。

### Lint（定期健檢）
- 檢查：`related` 是否有指向不存在的 id；是否有孤立頁（沒人連到）；新論文是否該補進舊頁的 `related`；metadata 欄位是否齊全；中文重點與原文是否一致。
- 提出值得新增的論文或主題頁。

### log.jsonl 格式（append-only，一行一筆 JSON）
```json
{"date":"2026-06-22","op":"ingest","id":"<paper-id>","title":"中文標題","note":"做了什麼"}
```
`op` ∈ `ingest`（收錄）、`build`（重建）、`query`（查詢）、`lint`（健檢）。日期用絕對日期 `YYYY-MM-DD`。

---

## 5. 受控詞彙：scale（研究尺度）

決定 badge 顏色與網路圖節點顏色，請**只用**下列值（要新增先更新本表與 `build.py`/`scaffold.py` 的 `SCALE` 字典）：

| 值 | 中文 | 色 | 用途 |
|---|---|---|---|
| `synaptic` | 突觸級 | 粉紅 | EM 等突觸解析度連結體 |
| `single-cell` | 單細胞 | 青綠 | 單神經元層級網路 |
| `mesoscale` | 中尺度 | 藍 | LPU／腦區層級網路 |
| `macroscale` | 巨觀 | 紫 | 全腦影像（fMRI/DTI 等） |
| `method/tool` | 方法/工具 | 橙 | 分割、視覺化、演算法等工具型論文 |

---

## 6. 鐵則

1. **`papers/*.html` 與 `topics/*.html` 是真實來源**；`index/graph/keywords/log.html` 是產物，永遠用 `python build.py` 重生，不要手改。
2. **改完論文頁或概念條目就跑 `build.py`**，否則四個導覽頁會與內容不同步。
3. **別再跑 `scaffold.py` / `make_topics.py`**（會覆蓋手動修改的頁）；它們只是一次性產生器。
4. 新增論文時記得補 `keywords`（用既有統一詞彙）與 `node_label`；新增概念條目時補 `keywords` 與 `related`，關鍵字網路與論文網路才會正確。若引入**新關鍵字**，要做兩件事：(1) 到 `keyword_notes.json` 補一則約 300 字說明（key 用該關鍵字字串）；(2) 把它歸到 `build.py` 的 `KW_CATEGORIES`（決定關鍵字網路節點顏色的 5 大類）。漏了 (1) build.py 印「缺少說明」、點了沒說明卡；漏了 (2) 印「未分類」、節點顯示灰色。
5. metadata 的 `<script id="meta">` 區塊必須是合法 JSON（繁中直接寫、不轉義；勿出現 `</script>` 字串）。
6. 破壞性操作（刪頁、大改、批次覆寫）先問使用者。
