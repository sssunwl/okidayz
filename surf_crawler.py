#!/usr/bin/env python3
"""三個沖繩衝浪點的官方海況資訊，寫進 docs/surf-conditions.json。

跟 ocean_crawler.py 用同一套日本氣象廳資料（見 jma.py）：府縣預報的風／浪原文翻譯、
各點市町村的警報・注意報、那霸潮位表。2026-11-18 起不再自己推算浪況好壞
（在日本屬於要許可的「予報業務」），只轉載官方資訊；實際永遠以現場、教練與官方公告為準。
"""

import json
from pathlib import Path

import requests

import jma

ROOT = Path(__file__).parent
OUTPUT_FILE = ROOT / "docs" / "surf-conditions.json"

GENERAL_CAUTION = (
    "沖繩多數浪點是礁盤 reef break，干潮時礁石會外露，浪大時更容易割傷擦傷；"
    "離岸流、突然變大的湧浪、閃電雷雨一律先上岸。新手不建議在浪超過腰高或有經驗者"
    "都收板的時段還硬下水。"
)

SPOTS = [
    {
        "slug": "sunabe-surf",
        "name": "砂邊 Sunabe Surf Point",
        "region": "中部・北谷",
        "kind": "礁盤浪點・沙灘旁，多個 peak",
        "jma_area": "471010",
        "jma_town": "4732600",  # 北谷町
        "exposure": "面西開闊礁盤，多個 peak，跟砂邊岸潛區域共用海域；浪大時留意水裡有沒有潛水的人。",
        "reference_url": "https://www.windy.com/?waves,26.3179,127.7552,11",
    },
    {
        "slug": "maeda-surf",
        "name": "真栄田 Cape Maeda Surf Point",
        "region": "中部・恩納村",
        "kind": "礁盤浪點・岬角地形，浪大偏進階",
        "jma_area": "471020",  # 恩納村在氣象廳分區屬「本島北部」
        "jma_town": "4731100",  # 恩納村
        "exposure": "跟青の洞窟浮潛區同一個岬角，浪起來時請跟浮潛船、潛水員保持距離。",
        "reference_url": "https://www.windy.com/?waves,26.5057,127.8783,11",
    },
    {
        "slug": "zanpa-surf",
        "name": "殘波岬 Cape Zanpa Surf Point",
        "region": "中部・讀谷",
        "kind": "礁盤浪點・岬角地形，離岸流常見，偏進階",
        "jma_area": "471010",
        "jma_town": "4732400",  # 讀谷村
        "exposure": "岬角地形離岸流常見，礁盤範圍大、干潮外露面積也大，新手不建議、務必結伴。",
        "reference_url": "https://www.windy.com/?waves,26.4332,127.7108,11",
    },
]


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
            spots_out.append(jma.spot_conditions(spot, *sources, now))
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
    print("🏄 浪況更新完成：{} 個點".format(len(spots_out)))


if __name__ == "__main__":
    main()
