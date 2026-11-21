# OkiDayz 品牌視覺

> 2026-10-26 SS 定案。OkiDayz 是 SS 自己的沖繩品牌，OKIPLAYGROUND 是幫 Okiblues 做的客戶品牌，**兩者視覺必須分開**（舊站沿用 OKIPLAYGROUND 的藏青＋湖水藍，已作廢）。

## 配色：A4「赤瓦 × 芒果，海用藍」

靈感是沖繩舊屋的紅瓦屋頂、白色漆喰、曬太陽的芒果和海。每個顏色只做一件事：

| 名稱 | 色碼 | 用途 |
|---|---|---|
| 漆喰白 | `#fdfaf4` | 頁面底色，要亮，不要偏黃偏舊 |
| 赤瓦 | `#d4523a` | 品牌色：Logo、按鈕、印章 |
| 芒果 | `#f4a72e` | 螢光筆底線、週末標籤、插畫重點 |
| 陽光 | `#ffd27a` | 芒果的淺色，標題螢光筆底 |
| 海 | `#1a9bb3` | **只用在海況、海灘、潛水滑浪** |
| 泡 | `#d8f1f4` | 海的淺色底 |
| 墨 | `#2f2420` | 文字、線稿 |

不要再加其他顏色。OffDayz 已經用森林綠＋陶土橘，OkiDayz 不用綠。

## 畫風：鉛筆線稿 ＋ 紅色印章

- **線稿**：墨色單線、手震、雙描（一粗一細略錯開），不是幾何正圓正方。
- **上色**：用斜線排線（赤瓦／芒果／海三色），像色鉛筆塗，不平塗滿。
- **印章**：只用赤瓦紅，粗邊、斑駁。用在「本週」「週末」「免費」、日期這類小標記。
- 底色要亮（漆喰白），不要做舊。
- 已否決：版畫套色＋貼紙（字體和畫風不搭）、純幾何扁平圖示（太 AI）。

## Logo

> 2026-11-22 SS 定案。完整規範頁 `assets/brand/logo/index.html`（網站上是 okidayz.com/assets/brand/logo/）。

- **組成**：鉛筆圓章（赤瓦屋頂後面升起芒果太陽，下面兩條海）＋ Caveat 手寫字標「Oki」墨色、「Dayz」赤瓦色，Dayz 底下一條陽光色螢光筆。字已轉外框，不靠字型檔。
- **版本**：橫式 `lockup`（主用）、直式 `lockup-v`、圓章 `mark`、字標 `wordmark`；32px 以下改用 `mark-mini`（拿掉瓦溝、門、光芒，線加粗）。
- **色版只有三種**：標準（亮底）、反白 `-rev`（赤瓦／墨／海色底、照片暗處：字白、Dayz 陽光色、無螢光筆）、單色 `-mono`／`wordmark-white`。圓章本身有白底，任何底色都直接放。
- **留白**：四周至少圓章直徑的 1/4。**最小**：橫式 120px、字標 72px、圓章 24px（印刷橫式 25mm）。
- **IG／Threads 頭像**：上傳 `assets/brand/logo/png/avatar-1080.png`。
- **不要**：拉長、換色、加陰影外框、旋轉、用別的字體重打 OkiDayz。
- **作廢**：深藍底＋魚＋彩虹的扁平圓章（Sona 舊 `mark-180.png`，11/22 前誤用在 11/23 自我介紹封面）。
- 所有 logo 檔（含 favicon `assets/mark-32/180/512.png`）都由 `tools/brand_assets.py` 生成，需要 `pip3 install fonttools brotli`，PNG 用本機 Chrome 轉。Sona 的副本在 `SonaSNS-Platform/assets/brandbook/okidayz/logo/`，改完要同步過去。

## 素材

- 圖示、紋樣、印章全部由 `tools/brand_assets.py` 生成到 `assets/brand/`，**改生成器再重跑，不要手改 SVG**。總覽頁 `assets/brand/index.html`。
- 主視覺插畫（大圖）由 Codex 訂閱生圖，附 `assets/brand/` 的總覽圖當參考，風格要跟線稿＋印章一致。
- 真實照片（SS 自己拍、人物專訪受訪者提供）永遠優先於插畫。
