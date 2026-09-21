# 派工單：OkiDayz 正式上線（L 系列）

> 品牌 2026-09-21 定案由 OkinawaSundays 改名 **OkiDayz**，正式網域 `okidayz.com`（L1b 處理改名）。

> 2026-09-21 Claude 起草，實作給 Codex。每張工單都可以單獨做；**請照編號順序，一張做完、build 過、Claude 審過再做下一張**。
> 全部工單都要遵守 `AGENTS.md`（品牌規則、`docs/` 不手改、外部文字要 escape、不在前端放 API key）。
> **不要做工單沒寫的事**：不要順手重構、不要改設計風格、不要新增套件相依。有疑問就在回報裡列出來，不要自己決定。

每張做完都要回報：改了哪些檔案、`python3 build.py` 的輸出、`docs/build-report.json` 的 skipped / warnings 數量、桌面（1280）和手機（375）各一張截圖說明。

---

## L0｜部署架構：產物不再 commit 進 git（先做，後面都靠它）

**問題**：4 條 workflow（crawler / news / ocean / rates）每次跑完都 `git add docs/` 再 commit。ocean 每 3 小時一次，git 歷史被 build 產物塞滿，本機 push 前幾乎每次都要處理 rebase 衝突。

**做法**
1. 爬蟲產生的**資料**（`events.json`、`news.json`、`ocean-conditions.json`、`surf-conditions.json`、`weather.json`、`rates.json`、`seen_events.json`、`ig-queue.json`）移到新資料夾 `data/`，只 commit 這一層（小 json，變動可追蹤）。
2. `build.py` 從 `data/` 讀，輸出到 `docs/`（或改名 `dist/`，二選一，寫在回報裡）。產物資料夾加進 `.gitignore`。
3. 新增 `.github/workflows/deploy.yml`：push 到 main 或其他 workflow 更新 `data/` 之後 → 跑 `build.py` → 用 `actions/upload-pages-artifact` + `actions/deploy-pages` 部署。GitHub Pages 的來源改成 "GitHub Actions"（這步 SS 要到 repo 設定手動切，請在回報裡提醒）。
4. 4 條爬蟲 workflow 改成只 commit `data/`，然後觸發 deploy（`workflow_run` 或在同一條 job 裡直接 deploy，選一個並說明原因）。
5. 前端有直接 fetch `docs/*.json` 的地方（例如 `rates.json`），build 時要把 json 複製到產物資料夾，確保路徑不變。

**驗收**：本機 `python3 build.py` 產出完整站；`git status` 看不到任何產物檔；手動觸發 deploy 之後，線上站跟改之前一樣。

---

## L1｜正式網域 + SITE_URL

- `build.py:26` 已經支援 `SITE_URL` 環境變數。deploy workflow 設 `SITE_URL=https://<正式網域>/`，網域先用 repo variable `SITE_URL`（SS 會填，正式為 `https://okidayz.com/`）。
- 產物根目錄輸出 `CNAME`（內容讀 SITE_URL 的 host；SITE_URL 還是 github.io 時就不輸出）。
- 檢查 canonical、og:url、sitemap、robots 全部跟著 SITE_URL 變；站內連結維持相對路徑（AGENTS.md 規定）。
- 做一個 `404.html`（用 base 模板，放回首頁、活動、攻略三個入口）。

**驗收**：`SITE_URL=https://example.com/ python3 build.py` 之後，`grep -r "sssunwl.github.io" <產物資料夾>` 找不到任何結果。

---

## L1b｜品牌改名 OkinawaSundays → OkiDayz

- 對外品牌一律寫作 `OkiDayz`（大小寫固定：O、D 大寫，結尾是 z 不是 s），**不加中文副名**。
- 要改的地方（`grep -rn OkinawaSundays . --exclude-dir=docs --exclude-dir=.git`）：`build.py`（10 處）、`templates/base.html`（5 處，含 og:site_name）、`assets/site.js`、`news_crawler.py`、`AGENTS.md`、`README.md`。
- `SITE_PLAN.md` 是歷史紀錄，只在開頭加一行「2026-09-21 起品牌改名 OkiDayz」，內文不改。
- logo 圖（`mark-*.png`）如果圖上有字要列出來回報，**不要自己重畫**，SS 會另外提供新 logo。
- repo 和資料夾已經由 SS 改名為 `okidayz`（2026-09-21），`build.py` 預設 SITE_URL 也已改好。Discord 頻道 `n-okinews` 是外部設定，不要改。
- 不要動 `../SonaSNS-Platform/`，那是另一個專案。

**驗收**：build 之後 `grep -r "OkinawaSundays" <產物資料夾>` 找不到任何結果。

---

## L2｜分析 + Search Console

- 在 `templates/base.html` 加 **Cloudflare Web Analytics**（不用 cookie，不用跳同意視窗）。token 從 build 環境變數 `CF_BEACON_TOKEN` 讀；沒設的話就不輸出 script（本機 build 不會送資料）。
- 用同樣方式加 Google Search Console 驗證 meta：變數 `GSC_VERIFICATION`，有值才輸出。
- **不要**加 GA4、不要加任何需要 cookie 同意的東西。

**驗收**：有沒有設 token，產出的 HTML 差別只在那一行。

---

## L3｜首頁日期 bug

`assets/home.js:32` 把中文星期接上「曜日」，畫面顯示「9月21日 **一曜日**」。
改成「9月21日（一）」，跟 `site.js:39` 的格式一致。

---

## L4｜活動資料品質關卡（最影響第一印象）

現況（`events.json` 255 筆）：
- 111 筆標題有日文假名。部分是抓錯欄位的內容，例如首頁出現「イベントカレンダー　9月22日 前夜祭　[御神輿] 9月23日 大東宮例祭　[神事・奉納相撲・奉納演芸]」。
- 首頁活動卡的說明全部是同一句「點開看活動詳情與官方資訊。」，這句是佔位字，不是內容。
- `okinawa_events_crawler.py:449` 對 okinawastory 的活動寫入 `name_zh: ""`。

**做法**
1. 爬蟲：okinawastory 的標題去掉「イベントカレンダー」和日期、括號清單這類雜訊，只留活動名稱。
2. 標題翻譯：跟新聞一樣走 OpenAI（沿用 `news_crawler.py` 的 client 和 model 設定），產生 `name_zh` 和一句 20–40 字的 `summary_zh`。**只根據來源頁的文字寫，不補來源沒有的資訊**。已經翻過的用快取（以 url 當 key），不要每次重翻。
3. build 關卡：`name_zh` 空白或 `summary_zh` 空白的活動 → 可以列在年曆裡，但**不上首頁「近日推薦」**，原因寫進 build-report。
4. 首頁卡片的說明改用 `summary_zh`；刪掉佔位句。
5. 活動頁（`templates/event.html`）加：
   - 「在 Google 地圖開啟」連結（用地點名稱＋地址組搜尋網址 `https://www.google.com/maps/search/?api=1&query=`，要做 URL encode）
   - 地區標籤（從地址判斷市町村 → 那霸／南部／中部／北部／離島）

**驗收**：首頁 4 張活動卡都是繁中標題和真的說明；build-report 列出被擋下的筆數和原因。

---

## L5｜新聞只留跟旅客有關的

現況：首頁「TODAY'S NEWS」出現政治評論（「情報戰與認知戰擴散…」）；氣象廳警報變成兩條沒內容的「要注意○○地區氣象警報・注意報」。

**做法**
1. OpenAI 整理新聞時多輸出一個欄位 `traveler_relevance`：`high`（颱風、航班、道路封閉、大型活動交通管制、海灘關閉）、`mid`（觀光、活動、生活）、`low`（政治、社論、犯罪、人事）。
2. 首頁只放 `high` + `mid`，`low` 只出現在 `/news/`。
3. 氣象廳警報：同一次抓到的合併成一則，標題要寫出**是哪一種警報**（大雨／波浪／強風／雷），例如「沖繩本島：波浪注意報、雷注意報」。沒有警報就不顯示這一則。

---

## L6｜每頁的 OG 圖

現況：全站共用一張 `assets/og-image.png`，攻略或活動分享到 IG、LINE、Threads 時預覽圖都一樣。

**做法**：build 時用 Pillow 幫每篇攻略、活動、月份頁產生 1200×630 的圖：品牌底色 + 標題（中文要換行、不能超出框）+ 分類小字 + logo。字體用 repo 內附的開源字體（Noto Sans TC，放 `assets/fonts/`，要附授權檔）。有快取：標題沒變就不重畫。
- 中文大標的 line-height 至少 1.05、letter-spacing 至少 -0.01em，不能讓字黏在一起。

**驗收**：隨便挑 3 頁，用 og:image 網址打開，每張圖都不一樣，標題也都完整沒被切掉。

---

## L7｜結構化資料（JSON-LD）

在 base 模板加一個 `<<<JSONLD>>>` 位置，每種頁面輸出：
- 首頁：`WebSite`
- 攻略／認識沖繩／好物／玩水文章：`Article`（headline、datePublished、dateModified、image = 該頁 OG 圖）＋ `BreadcrumbList`
- 活動頁：`Event`（name、startDate、endDate、location.name、location.address、url = 官方網址）。**缺日期或地點就不輸出 Event**，不能用猜的。
- sitemap 每個網址加 `<lastmod>`

**驗收**：挑 3 種頁面的 JSON-LD 貼進 Google Rich Results Test 都沒有錯誤（在回報裡附上 JSON-LD 原文）。

---

## L8｜法務頁 + 回報管道 + 社群連結

上線和之後放分潤連結都需要：
1. 新頁 `/about/`（關於 OkiDayz，一段就好）、`/privacy/`（隱私權政策：Cloudflare Web Analytics、分潤連結、不蒐集個資）、`/disclosure/`（分潤揭露：「部分連結為合作連結，你透過連結消費不會多付錢，本站可能獲得佣金；推薦內容不受合作影響」）。文案用繁中，照 AGENTS.md 的語氣。
2. 頁尾加這三頁的連結。
3. **回報連結**：AGENTS.md 規定每頁頁尾要有 AI 聲明和回報連結，但改名時跟 FB 一起拿掉了，現在頁尾只有聲明。改成讀 build 變數 `REPORT_URL`（SS 之後會提供 Google 表單或信箱），沒設就不顯示連結。
4. 社群連結：讀 `SOCIAL_IG`、`SOCIAL_THREADS` 變數，有值才出現在頁尾。**不要**放任何 OKIPLAYGROUND 相關的連結。

---

## L9｜分潤連結元件（先做機制，連結之後由 SS 填）

1. 新增 `data/affiliates.json`：
   ```json
   { "car-rental": { "label": "預約租車", "url": "", "partner": "" },
     "diving-experience": { "label": "預約體驗潛水", "url": "", "partner": "" } }
   ```
2. md 內容支援短碼 `{{aff:car-rental}}`，build 時換成按鈕：`<a rel="sponsored nofollow noopener" target="_blank">`，旁邊有小字「合作連結」，並連到 `/disclosure/`。
3. `url` 空白 → 整顆按鈕都不輸出（不能出現壞掉的按鈕），並寫進 build-report 的 warnings。
4. 外部 URL 只接受 https（AGENTS.md）。
5. 玩水頁的即時海況卡片下面預留一個 `diving-experience` 位置；小抄「機場・自駕」預留 `car-rental` 位置。
6. `car-rental` 這個位置**先保持空白**：之後會放特定合作租車公司的連結，**不要**先填 Klook、KKday 或其他租車比價的連結。

**驗收**：json 全部空白時，網站看起來跟現在一模一樣；填入一個測試網址後，只有對應的位置出現按鈕。

---

## L10｜首頁手機版瘦身

現況：手機（375 寬）首頁總高度約 8000px；打開第一個畫面只有標題和天氣卡，看不到任何活動或攻略。

**做法**（只調版面，不改設計語言）：
1. 手機版天氣卡改成精簡的橫條（圖示＋溫度＋降雨機率一行），完整卡片點開才展開。
2. 「今天是什麼日子」卡片在手機上放進天氣橫條下方，只顯示一行。
3. 天氣說明文案要跟天氣圖示一致：現在顯示 🌧️、降雨機率 36%，說明卻寫「天氣還算穩定，適合把戶外行程排滿一點」。有雨的圖示時要換另一套說明。

**驗收**：手機 375×812 打開首頁，第一個畫面內要看得到「近日活動」的標題。

---

## 不在這批工單裡（別做）
- 新增攻略文章內容（由 SS／Claude 另外寫，會直接放進 `content/`）
- 換網站視覺、換字體、改顏色
- 任何會員／登入／留言功能
- 展示廣告（AdSense）
