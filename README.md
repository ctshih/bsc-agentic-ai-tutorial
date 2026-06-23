# BSC with Agentic AI Tutorial

給 BSC（腦空間體中心）同仁的 Agentic AI 實戰教學系列。純靜態網站（HTML / CSS / JS，無後端），可直接放上任何靜態主機。

```
Tutorial/                     ← 這個資料夾就是整個網站，index.html 是首頁
├── index.html                ← 系列總覽（各集列表）
└── ep01-knowledge-base/      ← EP01「建立知識庫雛形」
    ├── index.html            ← 教學頁（含嵌入的 YouTube 影片）
    ├── quiz.html             ← 10 題互動測驗（當場計分）
    └── images/
```

新增集數：加一個 `epNN-xxx/` 子資料夾，並在 `index.html` 增一張卡片。

---

## 一、部署到 GitHub Pages（靜態網站）

1. 在 GitHub 建一個新的 repo（例如 `bsc-agentic-ai-tutorial`），可設 Public。
2. 把**這個 `Tutorial/` 資料夾的內容**推上去（讓 `index.html` 在 repo 根目錄）：
   ```bash
   cd Tutorial
   git init
   git add -A
   git commit -m "EP01 tutorial site"
   git branch -M main
   git remote add origin https://github.com/<你的帳號>/<repo>.git
   git push -u origin main
   ```
   （本機已先 `git init` 並 commit 好，你只要加 remote 再 push。）
3. 到 repo 的 **Settings → Pages**，Source 選 `Deploy from a branch`，Branch 選 `main` / `/ (root)`，存檔。
4. 約一分鐘後，網址會是 `https://<你的帳號>.github.io/<repo>/`。
   - **影片在這裡就能正常播放了**（https 來源，沒有 file:// 限制）。

> 之後加新集數或改內容，只要 `git add -A && git commit && git push`，網站會自動更新。

---

## 二、（選用）讓測驗成績存進 Google 試算表

測驗本身**不需要這一步也能用**（當場計分）。若想收集大家的成績，用 Google Apps Script 當輕量後端：

### 步驟
1. 開一份新的 **Google 試算表**（這份就是成績簿）。
2. 上方選單 **擴充功能 → Apps Script**，把下面整段貼進去、存檔：

   ```javascript
   // BSC with Agentic AI Tutorial — 隨堂測驗成績收集
   function doPost(e) {
     const ss = SpreadsheetApp.getActiveSpreadsheet();
     let sheet = ss.getSheetByName('成績');
     if (!sheet) {
       sheet = ss.insertSheet('成績');
       sheet.appendRow(['時間', '姓名', '分數', '總題數', '各題(1對/0錯)']);
     }
     const d = JSON.parse(e.postData.contents);
     sheet.appendRow([new Date(), d.name || '(未填)', d.score, d.total, (d.marks || []).join('')]);
     return ContentService.createTextOutput('ok');
   }
   ```
3. 右上 **部署 → 新增部署作業 → 類型選「網頁應用程式」**：
   - 「執行身分」= **我**
   - 「誰可以存取」= **任何人**
   - 按「部署」，授權，複製產生的**網頁應用程式網址**（長得像 `https://script.google.com/macros/s/AKfyc.../exec`）。
4. 打開 `ep01-knowledge-base/quiz.html`，找到最上面：
   ```javascript
   const SCRIPT_URL = '';
   ```
   把網址貼進引號內：
   ```javascript
   const SCRIPT_URL = 'https://script.google.com/macros/s/AKfyc.../exec';
   ```
5. commit + push。之後每個人作答交卷，成績（時間 / 姓名 / 分數 / 各題對錯）就會自動寫進你的試算表。

> 備註：用的是 `fetch(..., {mode:'no-cors'})` 送出，瀏覽器不會擋、也不需要處理 CORS；缺點是前端讀不到回應（但我們只需要把資料寫進去，不影響當場計分）。姓名欄是選填。

---

*由 Claude Code 協作產生。教學內容為一次真實人機協作的完整重演。*
