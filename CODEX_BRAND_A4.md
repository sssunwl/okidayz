# 派工單：OkiDayz 換成 A4 品牌視覺（B 系列）

> 2026-10-26 Claude 起草，Codex 實作，Claude 審查後 commit。
> 品牌規格以 `BRAND.md` 為準（請先讀完）。素材已經做好，在 `assets/brand/`：
> - `icons/*.svg`：spot 景點、sea 海況、weather 天氣、food 美食、event 活動、bus 交通、typhoon 颱風、festival 祭典、shop 購物、culture 文化（64×64，鉛筆線稿）
> - `stamps/*.svg`：this-week 本週、weekend 週末去、free 免費、local 在地推薦、rain-ok 雨天OK、date 日期（紅色印章）
> - `patterns/*.svg`：tiles 赤瓦、block 花ブロック、wave 浪（96×96 無縫）
> - `illustrations/hero-village.png`（1536×1024，首頁主視覺）
>
> **素材本身不要改**（它們由 `tools/brand_assets.py` 生成）。

## 規則

- 已在 branch `feat/brand-a4`。**不要 commit、不要碰 `.git`**，Claude 審完自己 commit。
- 照 `AGENTS.md`：`docs/` 是產物不手改，改 `assets/`、`templates/`、`build.py` 後跑 `python3 build.py`。
- **只做這張工單寫的事**。不要動爬蟲（`*_crawler.py`、`event_sources.py`、`signals.py`、`news_crawler.py`）、不要動 `content/`、不要動 `../SonaSNS-Platform/`、不要重排版面結構、不要改文案。
- 中文大標：`line-height` ≥ 1.05、`letter-spacing` ≥ -0.01em（現在的 -.06em／-.075em 會讓中文黏在一起，要改）。

## B1｜色票換成 A4

`assets/site.css` 的 `:root` 改成：

```css
--paper:#fdfaf4;     /* 漆喰白：頁面底色 */
--card:#ffffff;      /* 卡片底 */
--tile:#d4523a;      /* 赤瓦：品牌色、按鈕、印章、週末日期 */
--tile-dark:#b8432d; /* 赤瓦 hover */
--mango:#f4a72e;     /* 芒果：標籤、強調 */
--sun:#ffd27a;       /* 陽光：螢光筆底線 */
--sea:#1a9bb3;       /* 海：只用在海況、玩水、雨量水滴 */
--foam:#d8f1f4;      /* 泡：海的淺底 */
--ink:#2f2420;       /* 墨：文字、深色區塊 */
--muted:#7a6a5e;
--line:rgba(47,36,32,.13);
```

然後把舊變數全部換掉（不要留舊名當別名）：

| 舊 | 新 |
|---|---|
| `--navy`、`--navy-2`、`#1c2b4a`、`rgba(6,42,58,*)` | `--ink`／`rgba(47,36,32,*)`（透明度照舊） |
| `--blue` 用在**非海**的地方（連結、eyebrow、`.play` 標題） | `--tile` |
| `--blue`、`--lagoon`、`--lagoon-soft`、`rgba(8,127,156,*)` 用在**海況／玩水** | `--sea`／`--foam` |
| `--coral`、`rgba(255,102,90,*)` | `--tile`／`rgba(212,82,58,*)` |
| 舊 `--sun:#ffd447`、`#f2b134` | 標籤底用 `--mango`，螢光筆底線用 `--sun` |
| `--sand` 頁面底 | `--paper` |
| 綠色 `#3fb897`、`rgba(63,184,151,*)`（海況「適合」） | `--sea` |
| 頁尾的 `#a9cad1`、`#79d9e6`、`#e5f4f6`、`#7fa9b2`、`#b8d9df` | 深底上的淺字一律用 `rgba(253,250,244,.72)`；標題小字用 `--sun` |
| `#fff3d6`／`#9a6b00`／`#7a5200`（注意提醒） | 底 `#fff1d6`、字 `#8a5a12`（芒果系，保留） |

**驗收**：`grep -nE "#(062a3a|0b4052|087f9c|79d9e6|dff7f8|ff665a|ffd447|ffebdf|3fb897|1c2b4a|7fa9b2|a9cad1|b8d9df|e5f4f6)|rgba\((6,42,58|8,127,156|255,102,90|63,184,151)" assets/*.css assets/*.js templates/*.html build.py` 要零結果。

## B2｜build 會複製 `assets/brand/`

`build.py` 約第 1422–1430 行目前只複製 `assets/` 頂層檔案＋`fonts/`＋`covers/`。照 `fonts` 的寫法加一段 `brand/`（`shutil.copytree(..., dirs_exist_ok=True)`），**但不要複製 `brand/index.html`**（那是內部總覽頁，用 `ignore=shutil.ignore_patterns("index.html")`）。

## B3｜首頁 hero

`templates/home.html` 的 `.hero.today-board` 與 `assets/site.css`：

1. 拿掉 `.hero::before`（湖水藍色塊＋blob 動畫）和 `.hero::after`（珊瑚圓圈）。
2. 改放主視覺：`assets/brand/illustrations/hero-village.png` 當 hero 底部的背景插畫（`background: url(...) no-repeat center bottom / min(1280px,100%) auto`），hero 底部留足夠 padding 讓插畫的屋子和海露出來（桌面約 260px、手機約 150px），文字和卡片不能壓在屋子上。圖的上方本來就留白，標題放那裡。
3. `玩什麼？`（`.play`）：字色改 `--ink`，底下的黃色橢圓改成螢光筆：`background:linear-gradient(transparent 58%, var(--sun) 58%)`，拿掉 `::after` 橢圓。
4. 右上 `local pick` 手寫字（`.hero-hand-label`，Caveat 字體）換成 `<img src="assets/brand/stamps/this-week.svg">` 印章，約 84px 寬，位置照舊在標題右上，手機 ≤460px 照舊隱藏。Caveat 字體如果全站不再使用，`@font-face` 和 `--font-hand` 一起拿掉、`assets/fonts/caveat-700.woff2` 留著不刪。
5. `.live-dot` 改赤瓦紅、去掉光暈 box-shadow。

## B4｜區塊標題加圖示

每個 `.section-head` 的 eyebrow 前面加一個 28×28 的品牌圖示（`<img class="eyebrow-icon" src="{prefix}assets/brand/icons/xxx.svg" alt="">`，跟 eyebrow 同一行、垂直置中）：

| 區塊 | 圖示 |
|---|---|
| Now in Okinawa（活動） | `event` |
| Travel Guide | `spot` |
| Ocean Time | `sea` |
| Okinawa Goods | `shop` |
| This Week's Weather | `weather` |
| Know Okinawa 卡（`<<<OKINAWA_BANNER>>>`） | `culture` |

只改首頁。路徑前綴照 `build.py` 現有的 prefix 算法，不要寫死。

## B5｜深色區塊與按鈕

1. Know Okinawa 深藍卡（`.know-card` 一類）：底色改 `--tile` 赤瓦紅、字白色，按鈕改 `--mango` 底＋`--ink` 字；右下角加 `patterns/tiles.svg` 當淡淡的紋樣（`opacity:.18`，只鋪卡片右側 40%）。
2. 所有藏青實心按鈕（`.section-more` 等）：改 `--ink` 底、白字，hover 改 `--tile`。
3. 頁尾 `footer`：底色 `--ink`，頂邊加一條 18px 高的 `patterns/tiles.svg` 橫條（用 `::before`，`background-size:96px`，紋樣顏色本來就是赤瓦紅）。
4. 手機底部 `.mobile-bar`：`rgba(47,36,32,.94)`。

## B6｜海的區塊

只有「Ocean Time 玩水・潛水」區塊和 `/ocean/` 頁可以用 `--sea`／`--foam`：

1. 首頁 Ocean Time 區塊底部加一條 46px 高的 `patterns/wave.svg` 橫條（`background-size:96px`）。
2. 海況卡：「適合」用 `--sea`，「注意」用芒果系，「避開」用 `--tile`。

## B7｜週末

週曆裡的週末日期（`.wx-date.weekend`）維持紅字，顏色改 `--tile`。

## 回報

1. 改了哪些檔案（列出來）。
2. `python3 build.py` 的輸出。
3. B1 的驗收 grep 結果（要零結果）。
4. 你自己覺得有疑問、或工單沒寫清楚而你沒做的地方。
5. 你跑不了瀏覽器沒關係，版面 Claude 這邊會量。
