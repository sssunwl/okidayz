#!/usr/bin/env python3
"""三個沖繩潛點的官方海況資訊，寫進 docs/ocean-conditions.json。

資料全部來自日本氣象廳（見 jma.py）：
- 府縣預報的天氣／風／浪（本島中南部、本島北部，今天起 3 天，日文原文逐詞翻譯）
- 各點所在市町村的警報・注意報
- 那霸潮位表的滿潮／乾潮時刻
另外抓真栄田岬官網的現場遊泳可否。

2026-11-18 起不再自己推算「平穩／不建議」：在日本對外提供自家推算的海況判斷屬於
氣象業務法的「予報業務」，要許可。卡片的分級只依官方資訊（現場禁止、警報、注意報），
網站上照樣標示僅供參考，實際以現場、教練與官方公告為準。
"""

import json
import re
from pathlib import Path

import requests

import jma

ROOT = Path(__file__).parent
OUTPUT_FILE = ROOT / "docs" / "ocean-conditions.json"
FLAG_LOG_FILE = ROOT / "docs" / "official-flag-log.json"
FLAG_LOG_LIMIT = 1500  # 每 3 小時一筆，約留一年半
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

GENERAL_CAUTION = (
    "氣象廳發布波浪、強風（暴風）、高潮或雷的注意報以上時，岸潛和浮潛都先別排；"
    "能見度變差、突然起風湧、或現場出現離岸流跡象時也一樣，先上岸再說。"
)

# jma_area：府縣預報區（471010 本島中南部／471020 本島北部）；jma_town：警報用的市町村代碼。
SPOTS = [
    {
        "slug": "sunabe",
        "name": "砂邊2號點 Sunabe II",
        "region": "中部・北谷",
        "kind": "岸潛・夜潛熱門點",
        "jma_area": "471010",
        "jma_town": "4732600",  # 北谷町
        "exposure": "面向西側開闊海域，東風或微風最穩，西／西北強風會直接推浪上岸壁。",
        "reference_url": "https://windy.app/forecast2/spot/4013465/Sunabe+II",
    },
    {
        "slug": "cape-maeda",
        "name": "青の洞窟 Cape Maeda",
        "region": "中部・恩納村",
        "kind": "岬角浮潛・沿階梯下水",
        # 恩納村在氣象廳分區屬「本島北部」
        "jma_area": "471020",
        "jma_town": "4731100",  # 恩納村
        "exposure": "岬角北側的洞口、沿階梯下水，北風季（11–2 月）最常關閉，西／西北強風同樣危險；關閉時店家常改去砂邊或殘波。",
        "reference_url": "https://windy.app/forecast2/spot/8519891/Cape+Maeda+Blue+Cave",
        "official_note": "真栄田岬官網有即時影像與旗幟（藍=可能／黃=注意，穿防護衣與救生衣／紅=禁止），以現場公告為準。",
        "official_url": "https://maedamisaki.jp/sea-status",
        "official_label": "真栄田岬official 即時海況 ↗",
        "official_status_url": "https://maedamisaki.jp/sea-status",
    },
    {
        "slug": "gorilla-chop",
        "name": "大猩猩 Gorilla Chop",
        "region": "北部・本部",
        "kind": "岸潛・浮潛，適合初學",
        "jma_area": "471020",
        "jma_town": "4730800",  # 本部町
        "exposure": "本部半島南岸，北側有山擋風，是全島少數北風越強越穩的岸潛點；5-10月南風季吹南風時反而最容易停潛。",
        "reference_url": "https://windy.app/forecast2/spot/5967071/Gorilla+Chop",
    },
]


def fetch_official_status(url):
    """真栄田岬官網的現場遊泳可否。抓不到回空字串，不影響其他海況。"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except requests.RequestException as error:
        print("⚠️ 官方狀態抓取失敗（{}）".format(error))
        return ""
    res.encoding = "utf-8"
    match = re.search(r'id="nowstatus"[^>]*>([^<]+)<', res.text)
    return match.group(1).strip() if match else ""


def append_flag_log(entry):
    """記下現場官方狀態和當時的氣象廳資訊，日後對照用。"""
    try:
        log = json.loads(FLAG_LOG_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        log = []
    log.append(entry)
    FLAG_LOG_FILE.write_text(json.dumps(log[-FLAG_LOG_LIMIT:], ensure_ascii=False, indent=0), encoding="utf-8")


def build_spot(spot, sources, now):
    card = jma.spot_conditions(spot, *sources, now)
    if spot.get("official_status_url"):
        status = fetch_official_status(spot["official_status_url"])
        card["official_status"] = status
        if status:
            today = card["forecast"][0] if card["forecast"] else {}
            append_flag_log({
                "at": now.strftime("%Y-%m-%d %H:%M"), "spot": spot["slug"], "official": status,
                "our_verdict": card["verdict"],
                "jma_warnings": [w["name"] for w in card["warnings"]],
                "jma_wind": (today.get("wind") or {}).get("ja", ""),
                "jma_wave": (today.get("wave") or {}).get("ja", ""),
            })
        # 現場公告禁止時，一律以現場為準
        if "☓" in status:
            card["verdict"], card["verdict_label"] = "avoid", "官方禁止中"
            card["verdict_reason"] = "現場公告：" + status
    return card


def main():
    now = jma.now_jst()
    try:
        sources = jma.fetch_all_for_spots(now)
    except (requests.RequestException, ValueError, KeyError, IndexError) as error:
        print("⚠️ 氣象廳預報抓取失敗（{}），保留上一版".format(error))
        return

    spots_out = []
    for spot in SPOTS:
        try:
            spots_out.append(build_spot(spot, sources, now))
        except (KeyError, IndexError, ValueError) as error:
            print("⚠️ {} 整理失敗（{}），略過這個點".format(spot["name"], error))
    if not spots_out:
        print("⚠️ 全部點都失敗，保留上一版")
        return

    output = {
        "updated": now.strftime("%Y-%m-%d %H:%M"),
        "source": jma.SOURCE_LABEL,
        "forecast_url": jma.FORECAST_PAGE_URL,
        "warning_url": jma.WARNING_PAGE_URL,
        "tide_url": jma.TIDE_PAGE_URL,
        "general_caution": GENERAL_CAUTION,
        "spots": spots_out,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("🌊 海況更新完成：{} 個點".format(len(spots_out)))


if __name__ == "__main__":
    main()
