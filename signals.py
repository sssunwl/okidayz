#!/usr/bin/env python3
"""Combine news, alerts, events, today entries, and weather into signals.json."""

import hashlib
import re
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
NEWS_FILE = DOCS / "news.json"
EVENTS_FILE = DOCS / "events.json"
WEATHER_FILE = DOCS / "weather.json"
SIGNALS_FILE = DOCS / "signals.json"
BUILD_REPORT_FILE = DOCS / "build-report.json"

JST = timezone(timedelta(hours=9))
WINDOW_DAYS = 60
SUMMARY_MAX_CHARS = 120

AREAS = {"那霸", "北部", "中部", "南部", "離島", "全島"}
NEWS_CATEGORIES = {"生活", "交通", "天氣警報", "觀光", "全國"}
TOURIST_IMPACTS = {"high", "low", "none"}

LOCAL_LIFE_CATEGORIES = {"傳統", "生活"}
LOCAL_LIFE_TERMS = (
    "公民館", "自治会", "豊年祭", "エイサー", "市場", "マルシェ", "朝市",
    "まつり", "祭り", "産業祭", "綱引", "綱挽", "区民", "市民", "町民", "村民",
    "地域", "旗頭", "獅子舞", "ハーリー", "伝統行事",
)
# 日文詞用子字串比對；英文詞用字邊界，避免 live 命中 delivery、fes 命中 professional
VIBE_TERMS = (
    "ライブ", "フェス", "音楽", "パーティ", "ポップアップ", "古着", "ナイト", "クラブ",
    "サーフィン大会",
)
VIBE_WORDS = re.compile(r"\b(live|dj|fes|festival|pop-?up|party)\b", re.IGNORECASE)
# 會封路、人潮大到影響旅客行程的活動
HIGH_IMPACT_TERMS = (
    "大綱挽", "大綱引", "マラソン", "花火", "交通規制", "通行止め", "大拔河", "馬拉松", "煙火",
)

# Put islands and Naha before mainland regions so a more specific match wins.
AREA_KEYWORDS = {
    "那霸": ("那覇市", "那霸市", "那覇", "那霸"),
    "離島": (
        "離島", "石垣", "宮古島", "久米島", "竹富", "与那国", "與那國", "西表",
        "小浜島", "黒島", "波照間", "渡嘉敷", "座間味", "阿嘉島", "慶留間",
        "粟国", "渡名喜", "南大東", "北大東", "伊平屋", "伊是名", "多良間",
    ),
    "北部": (
        "北部地域", "やんばる", "山原", "名護", "国頭", "國頭", "大宜味", "東村",
        "今帰仁", "今歸仁", "本部", "恩納", "宜野座", "金武", "伊江",
    ),
    "中部": (
        "沖縄市", "沖繩市", "コザ", "うるま", "宇流麻", "宜野湾", "宜野灣",
        "読谷", "讀谷", "嘉手納", "北谷", "北中城", "中城",
    ),
    "南部": (
        "浦添", "糸満", "糸滿", "絲滿", "豊見城", "豐見城", "南城", "南風原",
        "与那原", "與那原", "八重瀬", "八重瀨", "西原",
    ),
}

WEATHER_LABELS = {
    "☀️": "晴",
    "🌤️": "晴時多雲",
    "⛅": "多雲時晴",
    "☁️": "多雲",
    "🌧️": "有雨",
    "🌦️": "短暫雨",
    "⛈️": "雷雨",
    "🌨️": "降雪",
}


def text(value):
    """Return a stripped string without turning None into the word 'None'."""
    return value.strip() if isinstance(value, str) else ""


def truncate(value, limit=SUMMARY_MAX_CHARS):
    value = text(value)
    if len(value) <= limit:
        return value
    return value[:limit - 1].rstrip() + "…"


def valid_url(value):
    value = text(value)
    if not value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def stable_id(kind, url="", name="", date_start=""):
    # 活動一律用名稱＋開始日：不同活動常共用同一個官網網址
    if kind in {"event", "today"} or not valid_url(url):
        seed = "{}{}{}".format(kind, name, date_start)
    else:
        seed = url
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    return "{}-{}".format(kind, digest)


def valid_date(value):
    value = text(value)
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def normalize_area(value, fallback=""):
    candidates = (text(value), text(fallback))
    for candidate in candidates:
        if candidate in AREAS:
            return candidate
        for area, keywords in AREA_KEYWORDS.items():
            if any(keyword in candidate for keyword in keywords):
                return area
    return "全島"


def normalized_bool(value):
    return value if isinstance(value, bool) else False


def load_previous_items():
    try:
        data = json.loads(SIGNALS_FILE.read_text(encoding="utf-8"))
        items = data.get("items")
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]
    except (OSError, ValueError, AttributeError):
        return []


def load_source(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return None, "{} 讀取失敗（{}）".format(path.name, error)
    if not isinstance(data, list):
        return None, "{} 格式錯誤（最外層必須是陣列）".format(path.name)
    return data, None


def news_signals(items):
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = text(item.get("url"))
        title = text(item.get("title"))
        summary = truncate(item.get("summary"))
        source = text(item.get("source"))
        item_date = text(item.get("date"))
        if not (valid_url(url) and title and summary and source and valid_date(item_date)):
            continue

        kind = "alert" if source == "氣象庁警報" else "news"
        if kind == "alert":
            tourist_impact = "high" if item.get("alert") is True else "none"
        else:
            tourist_impact = item.get("tourist_impact", "low")
            if tourist_impact not in TOURIST_IMPACTS:
                tourist_impact = "low"

        category = text(item.get("category"))
        if category not in NEWS_CATEGORIES:
            category = "生活" if source != "NHK" else "全國"
        area = item.get("area", "全島")
        if area not in AREAS:
            area = "全島"

        results.append({
            "id": stable_id(kind, url=url),
            "kind": kind,
            "title": title,
            "summary": summary,
            "source": source,
            "url": url,
            "date": item_date,
            "date_end": None,
            "area": area,
            "category": category,
            "tourist_impact": tourist_impact,
            "local_life": normalized_bool(item.get("local_life")),
            "vibe": normalized_bool(item.get("vibe")),
        })
    return results


def event_flags(item, title):
    category = text(item.get("category"))
    haystack = "{} {}".format(text(item.get("name")) or title, text(item.get("description")))
    local_life = (
        item.get("source") == "goyah"
        or category in LOCAL_LIFE_CATEGORIES
        or any(term in haystack for term in LOCAL_LIFE_TERMS)
    )
    vibe = any(term in haystack for term in VIBE_TERMS) or bool(VIBE_WORDS.search(haystack))
    try:
        stars = float(item.get("stars", 0))
    except (TypeError, ValueError):
        stars = 0
    big = category == "大型活動" or any(term in haystack for term in HIGH_IMPACT_TERMS)
    impact = "high" if stars >= 4 or big else "low"
    return local_life, vibe, impact


def event_signals(items, today=None):
    today = today or datetime.now(JST).date()
    last_day = today + timedelta(days=WINDOW_DAYS)
    results = []

    for item in items:
        if not isinstance(item, dict):
            continue
        start_raw = text(item.get("date_start"))
        end_raw = text(item.get("date_end")) or start_raw
        start = valid_date(start_raw)
        end = valid_date(end_raw)
        if not start or not end or end < start or end < today or start > last_day:
            continue

        title = text(item.get("name_zh")) or text(item.get("name"))
        if not title:
            continue
        source = text(item.get("source"))
        category = text(item.get("category")) or "活動"
        summary = truncate(item.get("description"))
        area = normalize_area(item.get("area"), "{} {}".format(text(item.get("location")), text(item.get("name"))))

        if source == "today_is":
            kind = "today"
            url = ""
            local_life = category == "傳統"
            vibe = False
            impact = "low"
        else:
            kind = "event"
            official_url = text(item.get("official_url"))
            source_url = text(item.get("url"))
            url = official_url if valid_url(official_url) else source_url
            if not valid_url(url):
                continue
            local_life, vibe, impact = event_flags(item, title)

        results.append({
            "id": stable_id(kind, url=url, name=text(item.get("name")) or title, date_start=start_raw),
            "kind": kind,
            "title": title,
            "summary": summary,
            "source": source,
            "url": url,
            "date": start_raw,
            "date_end": end_raw,
            "area": area,
            "category": category,
            "tourist_impact": impact,
            "local_life": local_life,
            "vibe": vibe,
        })
    return results


def weather_summary(items):
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        weekday = text(item.get("weekday"))
        label = WEATHER_LABELS.get(text(item.get("icon")))
        if weekday and label:
            parts.append("週{}{}".format(weekday, label))

    temperatures = []
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("temp_min", "temp_max"):
            value = item.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                temperatures.append(value)
    overview = "、".join(parts) if parts else "請留意每日天氣變化"
    if temperatures:
        overview += "；氣溫約 {}～{}°C".format(min(temperatures), max(temperatures))
    return truncate(overview + "。")


def weather_signals(items):
    dated = []
    for item in items:
        if isinstance(item, dict) and valid_date(item.get("date")):
            dated.append(item)
    if not dated:
        return []
    dated.sort(key=lambda item: item["date"])
    first_date = text(dated[0].get("date"))
    return [{
        "id": stable_id("weather", name="沖繩一週天氣", date_start=first_date),
        "kind": "weather",
        "title": "沖繩一週天氣",
        "summary": weather_summary(dated),
        "source": "Open-Meteo",
        "url": "",
        "date": first_date,
        "date_end": None,
        "area": "全島",
        "category": "天氣",
        "tourist_impact": "high",
        "local_life": False,
        "vibe": False,
    }]


def record_failures(failures):
    if not failures:
        return
    try:
        report = json.loads(BUILD_REPORT_FILE.read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise ValueError("build report is not an object")
    except (OSError, ValueError):
        report = {"generated": "", "pages": 0, "skipped": [], "warnings": []}
    warnings = report.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    for failure in failures:
        message = "signals：{}；已保留上一版對應項目".format(failure)
        if message not in warnings:
            warnings.append(message)
        print("⚠️  " + message)
    report["warnings"] = warnings
    BUILD_REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    previous = load_previous_items()
    source_specs = (
        (NEWS_FILE, {"news", "alert"}, news_signals),
        (EVENTS_FILE, {"event", "today"}, event_signals),
        (WEATHER_FILE, {"weather"}, weather_signals),
    )

    combined = []
    failures = []
    for path, kinds, converter in source_specs:
        source_data, error = load_source(path)
        if error:
            failures.append(error)
            combined.extend(item for item in previous if item.get("kind") in kinds)
        else:
            combined.extend(converter(source_data))

    combined.sort(
        key=lambda item: (item.get("date", ""), item.get("kind", ""), item.get("title", "")),
        reverse=True,
    )
    output = {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "items": combined,
    }
    DOCS.mkdir(parents=True, exist_ok=True)
    SIGNALS_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    record_failures(failures)
    print("📡 統一訊號更新完成：{} 則".format(len(combined)))


if __name__ == "__main__":
    main()
