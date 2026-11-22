"""活動官網的分享預覽圖（og:image）快取。

活動來源沒給圖、但有主辦方官網的，到官網抓 og:image（主辦方自己放出來給人分享的圖）。
結果存在 docs/event-images.json：{官網網址: {"image": 圖網址或 "", "checked": 日期}}。
build.py 的 fill_event_images() 讀這份，抓不到的再用地點照片、類別插畫補。

只在爬蟲（Actions）跑，build 不連網。每次最多抓 limit 筆新的，抓過的 30 天內不重抓。

    python3 event_images.py   # 本機手動補一輪
"""
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from event_sources import HEADERS, _safe_url

CACHE_FILE = "docs/event-images.json"
JST = timezone(timedelta(hours=9))
RECHECK_DAYS = 30
# Instagram／Facebook 的圖網址帶簽章、幾天後就失效，不收
SKIP_HOSTS = ("cdninstagram.com", "fbcdn.net", "instagram.com", "facebook.com", "//localhost", "//127.0.0.1")
# 檔名或路徑看起來是站台 logo／預設圖的不要
SKIP_WORDS = ("logo", "favicon", "icon", "noimage", "no_image", "no-image", "default", "ogp_common", "common_ogp")


def load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def og_image(url):
    res = requests.get(url, headers=HEADERS, timeout=12)
    res.raise_for_status()
    res.encoding = res.apparent_encoding or res.encoding
    soup = BeautifulSoup(res.text, "html.parser")
    for attr, name in (("property", "og:image"), ("name", "og:image"), ("name", "twitter:image")):
        tag = soup.find("meta", attrs={attr: name})
        if tag and tag.get("content"):
            image = _safe_url(urljoin(res.url, tag["content"].strip()))
            if image and not any(w in image.lower() for w in SKIP_WORDS + SKIP_HOSTS):
                return image
    return ""


def refresh_official_images(events, limit=60):
    cache = load_cache()
    today = datetime.now(JST).date()
    todo = []
    for event in events:
        official = _safe_url(event.get("official_url"))
        if not official or _safe_url(event.get("image")):
            continue
        hit = cache.get(official)
        if hit:
            try:
                if (today - datetime.strptime(hit.get("checked", ""), "%Y-%m-%d").date()).days < RECHECK_DAYS:
                    continue
            except ValueError:
                pass
        if official not in todo:
            todo.append(official)
    found = 0
    for official in todo[:limit]:
        try:
            image = og_image(official)
        except Exception as error:  # 官網連不上就記空的，30 天後再試
            print(f"⚠️ og:image 抓不到 {official}：{error}")
            image = ""
        cache[official] = {"image": image, "checked": today.isoformat()}
        found += bool(image)
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"🖼️ 官網預覽圖：查 {min(len(todo), limit)} 個官網，找到 {found} 張（待查 {max(0, len(todo) - limit)}）")
    return cache


if __name__ == "__main__":
    with open("docs/events.json", encoding="utf-8") as f:
        refresh_official_images(json.load(f), limit=400)
