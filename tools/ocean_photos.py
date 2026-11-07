"""幫 data/ocean_spots.json 的每個點位找一張 Wikimedia Commons 照片(可商用授權，要標作者)。
用法：python3 tools/ocean_photos.py [--force]
先用 photo_q(手動指定的搜尋字)，沒有就用日文名搜。找到後一定要人工看過，抓錯就填 photo_q 重跑。"""
import json
import re
import sys
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data" / "ocean_spots.json"
API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "OkiDayz/1.0 (https://sssunwl.github.io/okidayz/)"}
OK_LICENSE = re.compile(r"^(CC0|CC BY|CC BY-SA|Public domain|PD)", re.I)


def find_photo(query):
    res = requests.get(API, headers=HEADERS, timeout=25, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": query + " filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 8, "prop": "imageinfo", "iiprop": "url|extmetadata|size",
        "iiurlwidth": 640,
    })
    pages = sorted((res.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if not OK_LICENSE.search(lic) or info.get("width", 0) < info.get("height", 1):
            continue  # 只要可商用、橫的
        artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip()
        return {"url": (info.get("thumburl") or "").split("?")[0], "page": info.get("descriptionurl"),
                "credit": (artist or "Wikimedia Commons")[:60], "license": lic}
    return None


def main():
    force = "--force" in sys.argv
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for spot in data["spots"]:
        if spot.get("photo") and not force:
            continue
        query = spot.get("photo_q") or re.sub(r"（.*?）", "", spot["ja"])
        photo = find_photo(query)
        spot["photo"] = photo
        print(("✓" if photo else "✗"), spot["name"], query, (photo or {}).get("page", ""))
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
