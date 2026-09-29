# 工單：輸出統一訊號檔 `docs/signals.json`

> 2026-09-29。給 Codex 實作，Claude 審查。
> 目標：把現有的新聞、警報、活動、今天是、天氣合併成一份有標籤的清單，讓其他工具只讀這一份，不必各自重爬。
> **只加輸出，不改現有網頁的行為**；`news.json`、`events.json`、`weather.json` 的格式和用途維持不變。

## 範圍
- 新增 `signals.py`：讀 `docs/news.json`、`docs/events.json`、`docs/weather.json`，寫出 `docs/signals.json`。
- `news_crawler.py`：在**現有那一次** OpenAI 呼叫的 JSON 裡多要三個欄位（見下），存進 `news.json`。不准為了標籤多呼叫一次。
- `news.yml`、`crawler.yml` 兩個 workflow 的最後都要跑 `python3 signals.py`（純本機運算，不需要 key）。
- 不改 `templates/`、`assets/`，也不改任何頁面。

## `signals.json` 格式

```json
{
  "generated_at": "2026-09-29T07:30:00+09:00",
  "items": [
    {
      "id": "news-9f2c1a7b",
      "kind": "news",
      "title": "繁中標題",
      "summary": "繁中摘要，最多 120 字",
      "source": "沖縄タイムス",
      "url": "https://...",
      "date": "2026-09-29",
      "date_end": null,
      "area": "中部",
      "category": "交通",
      "tourist_impact": "high",
      "local_life": false,
      "vibe": false
    }
  ]
}
```

| 欄位 | 說明 |
|---|---|
| `id` | `<kind>-<sha1(url 或 kind+name+date_start) 前 8 碼>`，**同一則內容每天重跑都要得到同一個 id** |
| `kind` | `news`／`alert`（氣象庁警報）／`event`／`today`（events.json 裡 `source == "today_is"`）／`weather`（一週預報一則） |
| `date`、`date_end` | 活動用 `date_start`／`date_end`；其他只填 `date` |
| `area` | `那霸`／`北部`／`中部`／`南部`／`離島`／`全島`；判斷不出來就填 `全島` |
| `category` | 新聞沿用現有 `CATEGORIES`；活動沿用 events.json 的 category，空字串就填 `活動` |
| `tourist_impact` | `high`／`low`／`none`：這則會不會直接影響旅客今天或這幾天的安排（警報、交通管制、颱風、大型活動、設施休館屬於 `high`） |
| `local_life` | 在地生活感：社區祭典、公民館、市場、新開店、在地人日常，會是 true |
| `vibe` | 年輕潮感：音樂、DJ、fes、派對、pop-up、街頭文化、古著市集、運動賽事，會是 true |

### 標籤怎麼來
- **新聞**：由 OpenAI 在同一次呼叫裡回傳 `area`、`tourist_impact`、`local_life`、`vibe`（`alert` 保留）。prompt 補上以上定義。回傳值不合法就用預設（`全島`／`low`／`false`／`false`），**不要因此把整則跳過**。
- **警報**：`kind=alert`；有效的 `alert` 一律是 `tourist_impact=high`，已解除的是 `none`。
- **活動**：**不呼叫 AI**，用規則判斷：
  - `local_life`：`source == "goyah"`，或 category 屬於 `傳統`／`生活`，或名稱含 `公民館`、`自治会`、`豊年祭`、`エイサー`、`市場`、`マルシェ`、`朝市`
  - `vibe`：名稱或描述含 `ライブ`、`LIVE`、`DJ`、`フェス`、`fes`、`音楽`、`パーティ`、`ポップアップ`、`pop-up`、`古着`、`ナイト`、`クラブ`、`サーフィン大会`
  - `tourist_impact`：`stars >= 4` 或 category 是 `大型活動` → `high`，其餘是 `low`
  - `area`：優先用 events.json 的 `area`，沒有的話用 `location` 比對市町村名稱（寫一張市町村 → 地區的對照表）
- **今天是**：`kind=today`，`tourist_impact=low`；category 是 `傳統` 時 `local_life=true`。
- **天氣**：從 weather.json 產生一則 `kind=weather`，`summary` 寫成一週概況（例如「週三起轉雨，週末晴」），`tourist_impact=high`。

### 範圍與清理
- 只收：新聞與警報是 `news.json` 目前留存的全部；活動與今天是**從今天起未來 60 天**；已結束的活動不收。
- 依 `date` 由新到舊排序。
- 任一來源檔讀取失敗時，保留上一版 `signals.json` 裡該 kind 的項目，**不輸出缺一大塊的檔案**；原因寫進 `docs/build-report.json`。
- 外部 URL 只接受 `http:`／`https:`，不合格的那則直接跳過。

## 驗收
1. 在本機依序跑 `python3 news_crawler.py`（沒有 key 也要能跑）、`python3 signals.py`，都不能報錯。
2. 用同一份輸入重跑兩次，所有 `id` 都一樣。
3. `python3 -c "import json;d=json.load(open('docs/signals.json'));import collections;print(collections.Counter(i['kind'] for i in d['items']))"`：五種 kind 都要有（警報有可能剛好是 0）。
4. 隨機抽 10 則活動，人工檢查 `local_life`／`vibe`／`area` 是否合理，把結果貼在 PR 說明裡。
5. 網站頁面沒有任何變化（`git diff docs/*.html` 是空的）。

## 不要做
- 不要在這個 repo 寫任何品牌分派、社群帳號、合作或收入相關內容；這個檔案只提供中性標籤。
- 不要新增爬蟲或新的資料來源。
- 不要改現有 json 的欄位名稱（其他頁面和外部工具正在讀）。
