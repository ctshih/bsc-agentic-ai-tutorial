# CLAUDE.md — FlyCircuit 連結體論文知識庫（schema 層）

> 這是知識庫的「設定檔／維護規則」。任何 LLM agent（Claude Code 等）在這個資料夾工作前，**先讀完本檔**，照規則維護，不要當成一般聊天。
> 靈感來自 Karpathy 的 LLM Wiki 模式（見 `references/karpathy-llm-wiki.md`），但**改用 HTML** 當人類可讀層，對非工程背景的 BSC 同仁更易讀、資訊更豐富。

---

## 1. 這個知識庫在做什麼

把「連結體（connectome）相關論文」整理成一個**會持續累積、互相連結的 HTML 知識庫**。
原始 PDF 進來 → LLM 讀懂、抽重點、寫成一頁 HTML、更新關聯 → 人用瀏覽器瀏覽。
知識被**編譯一次後保持更新**，而不是每次提問才從頭 RAG。

主題範圍：果蠅（Drosophila）腦連結體、FlyCircuit 資料庫與其工具鏈（影像分割、視覺化、網路分析）。

---

## 2. 三層架構

| 層 | 位置 | 誰擁有 | 說明 |
|---|---|---|---|
| **原始來源** | `F:/FlyCircuit/Papers/`（及未來的 `sources/`） | 人 | 不可變的 PDF / 圖。LLM 只讀不改。 |
| **Wiki（人讀層）** | `papers/*.html` | LLM | **真實來源 (source of truth)**。每篇論文一頁，含豐富中文重點 + 內嵌機器可讀 metadata。 |
| **導覽（自動生成）** | `index.html` `graph.html` `log.html` | build.py | 由 `papers/*.html` 自動重生，**不要手改**。 |

```
Knowledge/
├── CLAUDE.md              # 本檔（schema / 維護規則）
├── index.html  *          # 論文目錄（可篩選/搜尋）
├── graph.html  *          # 論文連結網路圖
├── log.html    *          # 時間軸
├── log.jsonl              # 時間軸的 append-only 資料（人/LLM 維護）
├── build.py               # ★常駐工具：papers/*.html → 三個導覽頁
├── scaffold.py            # 一次性 v1 產生器（已用過，平時別再跑）
├── data/papers.json       # v1 建庫種子（已用過；非真實來源，build.py 不讀它）
├── assets/style.css       # 共用樣式（一改全站變）
├── assets/wiki.js         # 共用互動（目錄篩選）
├── papers/<id>.html       # ★每篇論文一頁（真實來源）
└── references/            # 參考素材（Karpathy 原文等）
        ( * = 自動生成，勿手改 )
```

---

## 3. 論文頁慣例（papers/<id>.html）

每頁結構固定（照現有頁即可）：
- `<head>` 內含 **`<script type="application/json" id="meta">…</script>`** — 這是該頁的 metadata，也是 build.py 唯一解析的東西。**改 metadata 要改這裡**。
- `<body>` 是人讀內容：標題、badges、一句話總結（callout）、中文摘要、關鍵發現、方法、重要性、相關論文。
- 樣式全靠 `../assets/style.css`，不要在頁內寫死樣式（保留 `badge.scale` 的 `background` inline 色票即可）。

### metadata 欄位

| 欄位 | 必填 | 說明 |
|---|---|---|
| `id` | ✓ | 檔名（不含 .html）。命名：`<第一作者姓氏或工具名>-<年>-<關鍵字?>`，全小寫、連字號。例 `chiang-2011-flycircuit`。 |
| `title` / `title_zh` | ✓ | 英文原標題 / 中文標題（可意譯）。 |
| `authors` | ✓ | 陣列，最多約 6 位後接 `"et al."`。 |
| `year` `venue` `doi` | ✓/✓/可空 | 年份、期刊、DOI（有就填，會自動連到 doi.org）。 |
| `species` | ✓ | 如 `Drosophila (adult)`。 |
| `scale` | ✓ | 研究尺度，**用受控詞彙**（見 §5）。 |
| `technique` | ✓ | 陣列，方法關鍵字（會變成目錄的「方法」篩選選項）。 |
| `region` | ✓ | 腦區或 `whole brain` / `N/A`。 |
| `dataset` | 可 | 如 `FlyCircuit v1.2`；無則 `—`。 |
| `tags` | 可 | 自由標籤（中英皆可，進全文搜尋）。 |
| `related` | ✓ | 其他論文 **id 陣列** ← 這就是 `graph.html` 的連線來源。雙向擇一即可，build.py 會去重。 |
| `tldr` | ✓ | 一句話總結（繁中）。 |
| `abstract_zh` `key_findings` `methods` `significance` | ✓ | 中文摘要 / 關鍵發現（陣列）/ 方法 / 重要性。 |
| `source_pdf` | 可 | 原始 PDF 絕對路徑（會在頁面給「原始 PDF」連結）。 |

**語言**：人讀內容一律**繁體中文（台灣）**，技術術語、專有名詞、作者名、標題保留原文。中文重點屬摘要性質，提醒讀者引用前以原文為準。

---

## 4. 操作流程（Ingest / Query / Lint）

### Ingest（收錄一篇新論文）
1. 取得 PDF（放 `F:/FlyCircuit/Papers/` 或 `sources/`）。
2. 讀 PDF（abstract、intro、主要圖表、conclusion 足矣），抽出 §3 的所有 metadata 欄位與中文重點。
   - 篇數多時可派 subagent 平行讀，一個 subagent 一篇，回傳 JSON。
3. 仿照現有頁，**新增 `papers/<id>.html`**（內嵌 meta + 人讀內容）。
4. 更新**相關論文的 `related`**：新頁連到舊頁，也視情況讓舊頁連回新頁（雙向更自然）。
5. 在 `log.jsonl` **append 一行** ingest 紀錄（格式見下）。
6. 跑 `python build.py` 重生導覽頁。
7. 給使用者看新頁與更新處，討論要不要調整重點。

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

1. **`papers/*.html` 是真實來源**；`index/graph/log.html` 是產物，永遠用 `python build.py` 重生，不要手改。
2. **改完論文頁就跑 `build.py`**，否則目錄/網路圖/時間軸會與內容不同步。
3. **別再跑 `scaffold.py`**（會覆蓋手動修改的論文頁）；它只是 v1 的一次性產生器。
4. metadata 的 `<script id="meta">` 區塊必須是合法 JSON（繁中直接寫、不轉義；勿出現 `</script>` 字串）。
5. 破壞性操作（刪頁、大改、批次覆寫）先問使用者。
