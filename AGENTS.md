# OkiDayz 公開網站規則

本資料夾是 OkiDayz 對外旅遊資訊平台的網站、內容與資料爬蟲。網站的第一任務是幫旅客快速回答「今天在沖繩可以做什麼」，第二任務是提供自己整理的旅遊內容。

改版藍圖與分期進度見 `SITE_PLAN.md`；架構與寫作規格見 `README.md`。

## 品牌與內容

- 對外品牌一律寫作 `OkiDayz`，不加中文副名。舊名 OKIPLAYGROUND（沖繩遊樂園）是另一個獨立品牌，站上任何位置都不要再出現，包括社群連結。
- 使用繁體中文，語氣像住在沖繩的朋友：直接、具體、有溫度，不堆砌旅遊形容詞。
- 不使用「沖繩藍」或沒有根據的最高級表述。
- 不要在對外頁面秀內部指標（資料筆數、更新時間戳、語言標示這類）。旅客不在乎。
- 活動日期、地點與安全資訊必須有來源；爬取內容只顯示原始來源連結，不擅自補寫未驗證資訊。
- **活動的主要外連只給主辦方官網**，其他旅遊平台降級為小字「資料來源」。
- 品牌視覺（配色、畫風、素材）以 `BRAND.md` 為準（2026-10-26 起；舊的 `../SonaSNS-Platform/brands/OKIPLAYGROUND/BRAND_DNA.md` 是客戶品牌 OKIPLAYGROUND 的，不再適用本站視覺）。

## 全自動發佈

內容與新聞都是自動產生、自動上線，沒有人工審核那道關。所以關卡放在 build：

- 缺必要欄位、格式錯誤的內容一律跳過，不產出半成品頁；原因寫進 `docs/build-report.json`。
- 新聞只做短摘要與原文連結，**不做全文翻譯轉載**。
- 抓取失敗時保留上一版資料，不要產生空白頁。
- 每頁頁尾保留「本站內容由 AI 自動整理」聲明與回報連結。

## 網站實作

- `build.py` 是唯一的頁面產生器；`okinawa_events_crawler.py` 只負責寫 `docs/*.json`，最後呼叫 `build_site()`。
- `docs/` 是 GitHub Pages 產物，不要手改；改完模板或內容要重新 build，並以桌面、手機尺寸檢查。
- 站內連結一律用相對路徑（`build.py` 會依頁面深度算 prefix），將來換網域不必改檔案。
- 所有從外部網站爬取的文字在插入 DOM 前必須 escape；外部 URL 只接受 `http:` 或 `https:`。
- 互動功能必須可用鍵盤操作，動畫需尊重 `prefers-reduced-motion`。
- 不加入需要 API key 的前端功能；需要外部資料的小工具（例如匯率）改成 Actions 每日寫成 json，前端讀靜態檔。
- 憑證只使用 GitHub Secrets。

## Big Dayz（2026-11-09 開）

- BigDayz（一個字，放在「攻略」底下，不另開導覽列）：求婚 → 婚紗旅拍 → 教堂行禮 → 紀念日旅行。**不叫婚禮專區**，教堂先當景點寫，每頁最後才接「想在這裡行禮？」。流量起來再照規則獨立成「沖繩婚禮誌」。
- 地點頁（build.py `load_places`）：景點／海灘 → `guide/spots/<slug>/`（資料 `data/places.json`），教堂／婚宴場地 → `guide/bigdayz/<slug>/`（`data/bigdayz.json`、`data/bigdayz_venues.json`）。頁上「今天」面板由 `assets/place.js` 在瀏覽器讀 events/weather/海況 json，不必重 build。一日遊文章用 front matter `stops:` 串地點頁。
- 教堂資料由 `tools/bigdayz_sync.py` 從 `../wedding/data/chapels.json` 同步（本機跑，產 `data/bigdayz.json` 與教堂地圖文章）；照片只用各教堂／婚宴場地官網圖（直連，每張標小字出處），不用 JWC 客戶的圖。景點照片用 Commons（`tools/spot_photos.py`，標作者與授權）。
- 文章 `cover` 可以填完整 https 網址（場地官網圖），不一定要放 `assets/covers/`。
