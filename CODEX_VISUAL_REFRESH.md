# 派工單：OkiDayz 字體與配色小改款（V 系列）

> 2026-09-23 Claude 起草，實作給 Codex。跟 `CODEX_LAUNCH.md` 是分開的批次——L 系列工單最後「不在這批工單裡」明確排除了換字體／換顏色，這批專門做這件事，兩份工單互不干擾，可以獨立跑，不用等 L 系列做完。
>
> **背景**：SS 發現同類型的 oki-trip.com 跟 OkiDayz 在兩個地方撞了——底色都是米白＋深藏青＋藍綠、`<h1>` 標題都是瀏覽器預設的 Noto Sans TC/Arial。這批工單只處理「字體」和「底色」，方向是 BRAND_DNA.md 定義的貼紙／票券圖形語言裡最小改動、風險最低的一種：**手感貼紙 + Coral Pop**。
>
> 照 `AGENTS.md` 規則（品牌語氣、`docs/` 不手改、外部文字要 escape）。**不要做工單沒寫的事**：不要重排首屏版面、不要動票券／扇貝卡／太陽軌道的形狀或陰影規則、不要換掉中文字堆疊、**不要動 `../SonaSNS-Platform/`**。有疑問就在回報裡列出來，不要自己決定。
>
> 每張做完都要回報：改了哪些檔案、`python3 build.py` 輸出、桌面（1280）和手機（375）各一張截圖，還有這張工單特別要求的檢查項目。**請照編號順序，一張做完、build 過、Claude 審過再做下一張。**

---

## V1｜自架兩支強調字體

**現況**：全站只有一個字體堆疊（`assets/site.css:25` 的系統中文字），沒有任何 webfont。L6（OG 圖工單）的作法是把開源字體放進 repo 自架、不吃外部 CDN，這次比照辦理。

**做法**
1. 下載兩支 Google Fonts 開源字（OFL 授權，可重新散布），各只要一個字重：
   - **Space Grotesk** 700（Bold）——拉丁字母＋數字用，給 kicker 標籤、日期數字、月曆數字。
   - **Caveat** 700（Bold）——手寫感，只用在 V3 的一個裝飾性小標籤。
2. 轉成 woff2，放 `assets/fonts/space-grotesk-700.woff2`、`assets/fonts/caveat-700.woff2`；授權檔比照 L6 放一起（`OFL.txt` 或授權連結），回報裡註明字體版本／來源。
3. `assets/site.css` 加 `@font-face`（`font-display:swap`），`:root`（第 1–20 行）新增兩個變數：
   ```css
   --font-accent:'Space Grotesk',system-ui,sans-serif;
   --font-hand:'Caveat',cursive;
   ```
4. **不要**動 `body`（第 23–27 行）現有的中文字堆疊——這兩支字只補拉丁字母／數字／裝飾，不取代中文顯示。

**驗收**：`assets/fonts/` 底下看得到兩個 woff2 檔＋授權說明；`python3 build.py` 之後檢查頁面請求，只多兩個本地字體請求，沒有任何 `fonts.googleapis.com` 之類的外部 CDN。

---

## V2｜底色換成 Coral Pop

**現況**：`assets/site.css:9` 的 `--sand:#fff7e8`（米白）是全站主底色，跟 oki-trip.com 的米白撞色。

**做法**
1. `--sand` 改成 `#ffebdf`（暖珊瑚米色）。
2. 連動的硬編碼顏色一起改（同一份檔案搜得到）：
   - `.site-header`（約第 46 行）`rgba(255,247,232,.42)` → `rgba(255,235,223,.42)`
   - `.site-header.scrolled`（約第 47 行）`rgba(255,247,232,.9)` → `rgba(255,235,223,.9)`
3. `--paper`、`--navy`、`--blue`、`--coral`、`--sun`、`--lagoon`、`--lagoon-soft` 全部不動——只換底色，三個重點色（藏青／珊瑚／太陽黃）維持原樣，這樣現有的票券硬陰影、扇貝卡、太陽軌道才不用重畫。
4. 換完之後自己過一輪桌面＋手機，特別看這幾個「小面積珊瑚色／太陽黃元素」貼在新底色上會不會糊掉：`.live-dot`、`.quick-search` 的 `box-shadow:8px 8px 0 var(--sun)`、`.count-badge`。看起來對比不夠就在回報裡提出來，**不要自己動這些元素的顏色**，等 Claude 看過再說。

**驗收**：全站截圖底色是珊瑚米色不是米白；三個重點色 hex 沒有任何一個被改到；`grep -rn "fff7e8\|255,247,232" assets/` 找不到結果。

---

## V3｜Hero 標題套用手感貼紙處理

**現況**：`.hero h1`（`assets/site.css:76` 起）目前用瀏覽器預設粗細，跟 kicker／日期數字是同一套字，沒有分層。

**做法**
1. `.hero h1` 加一行 `font-weight:900`（其他屬性不動，`letter-spacing`／`line-height` 保留）。
2. 以下「主要放英文字母／數字」的元素改套 `var(--font-accent)`（Space Grotesk），中文內容不受影響：
   - `.hero-kicker`
   - `.eyebrow`
   - `.ticket small`、`.ticket strong`
   - `.event-date`（月曆卡片的日期數字）
   - `.wx-date`
3. Hero 標題旁加一個裝飾性手寫貼紙：套 `var(--font-hand)`，顏色 `var(--coral)`，`transform:rotate(-6deg)`。

   **文字改成英文「local pick」（小寫）**，不要用中文——V1 回報已經確認 Caveat 不含中文字形，中文套上去會直接 fallback 成系統 cursive，看不出手寫感。「local pick」是短標籤，符合 `BRAND_DNA.md`「介面中的英文只用在品牌與短標籤」的規則，**不要自己換別的文案**。

   位置貼在 `.hero h1` 右上角或 `.hero-kicker` 旁，不要蓋到主標題或任何可點擊元素；手機版如果窄到會重疊，直接 `display:none` 隱藏，不用硬擠。

**驗收**：桌面截圖看得到手寫貼紙，沒有蓋到任何按鈕或連結；手機 375 寬截圖裡貼紙要嘛好好躺著、要嘛不顯示，不能被切一半。

---

## 不在這批工單裡（別做）
- 首屏版面重排（天氣卡、票券卡的位置不動）
- 票券／扇貝卡／太陽軌道的形狀或陰影規則
- 三個品牌重點色（藏青／珊瑚／太陽黃）的 hex 值
- 中文字體堆疊（body 的 `font-family`）
- `../SonaSNS-Platform/` 底下任何檔案——`BRAND_DNA.md` 的色票之後由 Claude 另外同步，Codex 不用管

---

## 給 Claude 自己的後續（Codex 做完再處理，不寫進工單）
- ~~V2 確定顏色定案後，回頭更新 `../SonaSNS-Platform/brands/OKIPLAYGROUND/BRAND_DNA.md` 的視覺系統色票（`Sand Cream` 那一列的 hex），保持「唯一真相來源」同步。~~ 2026-09-23 已完成：`Sand Cream #FFF7E8` → `Coral Sand #FFEBDF`，並加了異動註記。

## 狀態：V1–V3 全部完成（2026-09-23）
