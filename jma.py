"""日本氣象廳(沖縄気象台)公開資料:府縣預報、警報・注意報、那霸潮位表。

只做「原文轉載＋逐詞翻譯」,不自己算好壞——在日本對外提供自家推算的浪況/天氣判斷屬於「予報業務」要許可。
翻譯規則移植自 ryukyusurfbase/worker/src/(phrases.ts、weatherCodes.ts、jma.ts、tide.ts):
任何一個片語查不到就回傳 None,畫面改顯示日文原文——寧可不翻,也不要猜。
"""
import re
from datetime import date, datetime, timedelta, timezone

import requests

JST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "OkiDayzWeather/1.0 (https://okidayz.com/)"}

OFFICE = "471000"  # 沖縄本島地方
FORECAST_URL = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{OFFICE}.json"
# 2026-05-28 起的新制警報 JSON;舊的 bosai/warning/data/warning/ 從那天起停止更新
WARNING_URL = f"https://www.jma.go.jp/bosai/warning/data/r8/{OFFICE}.json"
FORECAST_PAGE_URL = f"https://www.jma.go.jp/bosai/forecast/#area_type=offices&area_code={OFFICE}"
WARNING_PAGE_URL = f"https://www.jma.go.jp/bosai/warning/#area_type=offices&area_code={OFFICE}"
TIDE_PAGE_URL = "https://www.data.jma.go.jp/kaiyou/db/tide/suisan/suisan.php?stn=NH"
NAHA_TEMP_CODE = "91197"
SOURCE_LABEL = "日本氣象廳（沖縄気象台）"

AREAS = {"471010": "本島中南部", "471020": "本島北部"}

# ── 風、浪片語(原文用全形空白分隔) ──
DIRECTIONS = {
    "北": "北", "北北東": "北北東", "北東": "東北", "東北東": "東北東",
    "東": "東", "東南東": "東南東", "南東": "東南", "南南東": "南南東",
    "南": "南", "南南西": "南南西", "南西": "西南", "西南西": "西南西",
    "西": "西", "西北西": "西北西", "北西": "西北", "北北西": "北北西",
}
WORDS = {
    "後": "後轉", "やや強く": "稍強", "強く": "強", "非常に強く": "非常強",
    "海上": "海上", "では": "", "陸上": "陸上", "所により": "局部",
    "一時": "短暫", "時々": "時而", "朝": "早上", "昼前": "上午", "昼過ぎ": "午後",
    "夕方": "傍晚", "夜": "夜間", "夜遅く": "深夜", "明け方": "清晨", "から": "起",
    "うねり": "湧浪", "やや高く": "稍高", "高く": "高",
}
_FULLWIDTH = str.maketrans("０１２３４５６７８９．", "0123456789.")


def normalize(text):
    return (text or "").translate(_FULLWIDTH)


def _token_zh(token):
    m = re.fullmatch(r"(.+)の風", token)
    if m and m.group(1) in DIRECTIONS:
        return DIRECTIONS[m.group(1)] + "風"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)メートル", token)
    if m:
        return f"{m.group(1)} 公尺"
    return WORDS.get(token)


def translate_phrase(original):
    """「東の風　後　北東の風」→「東風後轉東北風」;有查不到的片語就回 None。"""
    if not original:
        return None
    tokens = [t.strip() for t in normalize(original).split("　") if t.strip()]
    out = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "うねり" and i + 1 < len(tokens) and tokens[i + 1] == "を伴う":
            out.append("伴有湧浪")
            i += 2
            continue
        word = _token_zh(tokens[i])
        if word is None:
            return None
        if word:
            out.append(word)
        i += 1
    text = re.sub(r"，(後轉|起)，?", r"\1", "，".join(out))
    return re.sub(r"(後轉|起)(\d)", r"\1 \2", text)


def phrase(original):
    """回傳 {ja, zh};zh 可能是 None(前端改顯示日文)。"""
    if not original:
        return None
    return {"ja": normalize(original).replace("　", " "), "zh": translate_phrase(original)}


# ── 天氣代碼(日文短標籤是氣象廳 Forecast.Const.TELOPS) ──
WEATHER_CODES = {
    "100": "晴", "101": "晴時々曇", "102": "晴一時雨", "103": "晴時々雨", "104": "晴一時雪", "105": "晴時々雪",
    "106": "晴一時雨か雪", "107": "晴時々雨か雪", "108": "晴一時雨か雷雨", "110": "晴後時々曇", "111": "晴後曇",
    "112": "晴後一時雨", "113": "晴後時々雨", "114": "晴後雨", "115": "晴後一時雪", "116": "晴後時々雪", "117": "晴後雪",
    "118": "晴後雨か雪", "119": "晴後雨か雷雨", "120": "晴朝夕一時雨", "121": "晴朝の内一時雨", "122": "晴夕方一時雨",
    "123": "晴山沿い雷雨", "124": "晴山沿い雪", "125": "晴午後は雷雨", "126": "晴昼頃から雨", "127": "晴夕方から雨",
    "128": "晴夜は雨", "130": "朝の内霧後晴", "131": "晴明け方霧", "132": "晴朝夕曇", "140": "晴時々雨で雷を伴う",
    "160": "晴一時雪か雨", "170": "晴時々雪か雨", "181": "晴後雪か雨", "200": "曇", "201": "曇時々晴", "202": "曇一時雨",
    "203": "曇時々雨", "204": "曇一時雪", "205": "曇時々雪", "206": "曇一時雨か雪", "207": "曇時々雨か雪",
    "208": "曇一時雨か雷雨", "209": "霧", "210": "曇後時々晴", "211": "曇後晴", "212": "曇後一時雨", "213": "曇後時々雨",
    "214": "曇後雨", "215": "曇後一時雪", "216": "曇後時々雪", "217": "曇後雪", "218": "曇後雨か雪", "219": "曇後雨か雷雨",
    "220": "曇朝夕一時雨", "221": "曇朝の内一時雨", "222": "曇夕方一時雨", "223": "曇日中時々晴", "224": "曇昼頃から雨",
    "225": "曇夕方から雨", "226": "曇夜は雨", "228": "曇昼頃から雪", "229": "曇夕方から雪", "230": "曇夜は雪",
    "231": "曇海上海岸は霧か霧雨", "240": "曇時々雨で雷を伴う", "250": "曇時々雪で雷を伴う", "260": "曇一時雪か雨",
    "270": "曇時々雪か雨", "281": "曇後雪か雨", "300": "雨", "301": "雨時々晴", "302": "雨時々止む", "303": "雨時々雪",
    "304": "雨か雪", "306": "大雨", "308": "雨で暴風を伴う", "309": "雨一時雪", "311": "雨後晴", "313": "雨後曇",
    "314": "雨後時々雪", "315": "雨後雪", "316": "雨か雪後晴", "317": "雨か雪後曇", "320": "朝の内雨後晴",
    "321": "朝の内雨後曇", "322": "雨朝晩一時雪", "323": "雨昼頃から晴", "324": "雨夕方から晴", "325": "雨夜は晴",
    "326": "雨夕方から雪", "327": "雨夜は雪", "328": "雨一時強く降る", "329": "雨一時みぞれ", "340": "雪か雨",
    "350": "雨で雷を伴う", "361": "雪か雨後晴", "371": "雪か雨後曇", "400": "雪", "401": "雪時々晴", "402": "雪時々止む",
    "403": "雪時々雨", "405": "大雪", "406": "風雪強い", "407": "暴風雪", "409": "雪一時雨", "411": "雪後晴", "413": "雪後曇",
    "414": "雪後雨", "420": "朝の内雪後晴", "421": "朝の内雪後曇", "422": "雪昼頃から雨", "423": "雪夕方から雨",
    "425": "雪一時強く降る", "426": "雪後みぞれ", "427": "雪一時みぞれ", "450": "雪で雷を伴う",
}
# 長的片語先換,避免被短的規則拆開
ZH_RULES = [
    ("雨で暴風を伴う", "暴風雨"), ("で雷を伴う", "並伴有雷"), ("海上海岸は", "海上與海岸"), ("一時強く降る", "短暫強降雨"),
    ("朝の内", "早上"), ("明け方", "清晨"), ("昼頃から", "中午起"), ("夕方から", "傍晚起"), ("午後は", "午後"), ("夜は", "夜間"),
    ("山沿い", "山區"), ("朝夕", "早晚"), ("朝晩", "早晚"), ("日中", "白天"), ("夕方", "傍晚"),
    ("時々止む", "時停"), ("時々", "時"), ("一時", "短暫"), ("後", "轉"), ("か", "或"),
    ("風雪強い", "強風雪"), ("みぞれ", "雨夾雪"), ("霧雨", "毛毛雨"), ("曇", "多雲"),
]
_KANA = re.compile(r"[぀-ヿ]")


def weather_label(code):
    """天氣代碼 → {ja, zh};zh 轉不乾淨(還有假名)就是 None。"""
    ja = WEATHER_CODES.get(str(code or ""))
    if not ja:
        return None
    zh = ja
    for src, dst in ZH_RULES:
        zh = zh.replace(src, dst)
    return {"ja": ja, "zh": None if _KANA.search(zh) else zh}


def weather_icon(code):
    """代碼第一位是主天氣(1 晴、2 曇、3 雨、4 雪);只用來挑圖示,不做判斷。"""
    code = str(code or "")
    ja = WEATHER_CODES.get(code, "")
    if "雷" in ja:
        return "⛈️"
    if code.startswith("1"):
        return "🌤️" if ("曇" in ja or "雨" in ja) else "☀️"
    if code.startswith("2"):
        if code == "209":
            return "🌫️"
        if "雨" in ja:
            return "🌧️"
        return "⛅" if "晴" in ja else "☁️"
    if code.startswith("3"):
        return "🌧️"
    if code.startswith("4"):
        return "❄️"
    return "☁️"


# ── 預報 ──
def _num(value):
    try:
        return round(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def fetch_forecast():
    resp = requests.get(FORECAST_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def area_forecast(raw, area_code):
    """府縣預報的三天:天氣、風、浪。回傳 [{date, weather:{ja,zh}, weather_code, wind:{ja,zh}, wave:{ja,zh}}]。"""
    series = raw[0]["timeSeries"][0]
    area = next((a for a in series["areas"] if a["area"]["code"] == area_code), None)
    if not area:
        return []
    days = []
    for i, t in enumerate(series["timeDefines"]):
        def pick(key):
            values = area.get(key) or []
            return values[i] if i < len(values) else None

        days.append({
            "date": t[:10],
            "weather_code": pick("weatherCodes"),
            "weather": weather_label(pick("weatherCodes")),
            "wind": phrase(pick("winds")),
            "wave": phrase(pick("waves")),
        })
    return days


def daily_weather(raw, previous=None):
    """首頁 7 天天氣卡,欄位維持 weather.json 舊格式(Sona 品牌書也在讀)。
    今明兩天用府縣預報(本島中南部+那霸氣溫),之後用週間預報;UV 氣象廳沒有,留 None。"""
    previous = {d.get("date"): d for d in (previous or [])}
    short, weekly = raw[0], (raw[1] if len(raw) > 1 else None)
    out = {}

    s0 = short["timeSeries"][0]
    area = next(a for a in s0["areas"] if a["area"]["code"] == "471010")
    for i, t in enumerate(s0["timeDefines"]):
        out[t[:10]] = {"code": area["weatherCodes"][i], "pops": [], "temps": []}
    # 6 小時降雨機率,取每天最大值
    for t, p in zip(short["timeSeries"][1]["timeDefines"], next(a for a in short["timeSeries"][1]["areas"] if a["area"]["code"] == "471010")["pops"]):
        if t[:10] in out and p != "":
            out[t[:10]]["pops"].append(int(p))
    # 那霸氣溫:timeDefines 是當天 00:00(最低)/09:00(最高)。
    # 白天發的預報,「今天 00:00」那格其實是今天最高溫重複一次,不是最低溫 → 今天最低溫沿用上一版
    s2 = short["timeSeries"][2]
    naha = next((a for a in s2["areas"] if a["area"]["code"] == NAHA_TEMP_CODE), s2["areas"][0])
    report_day = short["reportDatetime"][:10]
    for t, v in zip(s2["timeDefines"], naha["temps"]):
        if t[:10] == report_day and t[11:13] == "00":
            continue
        if t[:10] in out:
            key = "max" if t[11:13] == "09" else "min"
            out[t[:10]][key] = _num(v)

    if weekly:
        w0, w1 = weekly["timeSeries"][0], weekly["timeSeries"][1]
        wa = w0["areas"][0]
        ta = next((a for a in w1["areas"] if a["area"]["code"] == NAHA_TEMP_CODE), w1["areas"][0])
        for i, t in enumerate(w0["timeDefines"]):
            d = t[:10]
            slot = out.setdefault(d, {"code": wa["weatherCodes"][i], "pops": [], "temps": []})
            if not slot["pops"] and wa["pops"][i] != "":
                slot["pops"].append(int(wa["pops"][i]))
            if slot.get("max") is None:
                slot["max"] = _num(ta["tempsMax"][i])
            if slot.get("min") is None:
                slot["min"] = _num(ta["tempsMin"][i])

    weekday = "一二三四五六日"
    items = []
    for d in sorted(out)[:7]:
        s = out[d]
        prev = previous.get(d, {})
        label = weather_label(s["code"]) or {}
        items.append({
            "date": d,
            "weekday": weekday[date.fromisoformat(d).weekday()],
            "icon": weather_icon(s["code"]),
            "weather": label.get("zh") or label.get("ja") or "",
            "temp_max": s.get("max") if s.get("max") is not None else prev.get("temp_max"),
            "temp_min": s.get("min") if s.get("min") is not None else prev.get("temp_min"),
            "rain_chance": max(s["pops"]) if s["pops"] else prev.get("rain_chance"),
            "uv": None,
            "uv_label": "",
        })
    return items


# ── 警報・注意報 ──
# kinds.code(氣象廳警報種別代碼);查不到的代碼顯示「{分類}相關資訊」並視為要留意
WARNING_KINDS = {
    "02": "暴風雪警報", "03": "大雨警報", "04": "洪水警報", "05": "暴風警報", "06": "大雪警報", "07": "波浪警報", "08": "高潮警報",
    "10": "大雨注意報", "12": "大雪注意報", "13": "風雪注意報", "14": "雷注意報", "15": "強風注意報", "16": "波浪注意報",
    "18": "洪水注意報", "19": "高潮注意報", "20": "濃霧注意報", "21": "乾燥注意報", "23": "低溫注意報",
    "32": "暴風雪特別警報", "33": "大雨特別警報", "35": "暴風特別警報", "36": "大雪特別警報", "37": "波浪特別警報", "38": "高潮特別警報",
}
CATEGORIES = {"VPWW55": "大雨", "VPWW56": "土石災害", "VPWW57": "高潮", "VPWW58": "暴風", "VPWW59": "波浪", "VPWW60": "大雪", "VPWW61": "其他"}
# 跟下水有關的:波浪、強風/暴風、高潮、雷
MARINE_CATEGORIES = {"VPWW57", "VPWW58", "VPWW59"}
MARINE_KINDS = {"14"}
INACTIVE_STATUSES = {"解除", "発表警報・注意報はなし"}


def fetch_warnings():
    resp = requests.get(WARNING_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def town_warnings(raw, town_code):
    """某市町村目前生效中的警報・注意報。level: special/warning/advisory。"""
    found = []
    for entry in raw:
        cat = entry.get("dataTypeCode", "")
        for item in (entry.get("warning") or {}).get("class20Items") or []:
            if item.get("areaCode") != town_code:
                continue
            for kind in item.get("kinds") or []:
                code, status = kind.get("code"), kind.get("status")
                if not code or not status or status in INACTIVE_STATUSES:
                    continue
                name = WARNING_KINDS.get(code) or f"{CATEGORIES.get(cat, '')}相關資訊"
                level = "special" if "特別警報" in name else "warning" if name.endswith("警報") else "advisory"
                found.append({
                    "code": code,
                    "name": name,
                    "level": level,
                    "marine": cat in MARINE_CATEGORIES or code in MARINE_KINDS,
                    "status": {"発表": "發布", "継続": "持續"}.get(status, status),
                })
    seen, unique = set(), []
    for w in found:
        if w["code"] not in seen:
            seen.add(w["code"])
            unique.append(w)
    order = {"special": 0, "warning": 1, "advisory": 2}
    return sorted(unique, key=lambda w: (order[w["level"]], not w["marine"], w["code"]))


# ── 潮位表(那霸 NH) ──
def tide_url(year, station="NH"):
    return f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{station}.txt"


def _events(block):
    events = []
    for slot in range(4):
        chunk = block[slot * 7: slot * 7 + 7]
        if len(chunk) < 7:
            break
        hh, mm, cm = chunk[0:2], chunk[2:4], chunk[4:7]
        if hh.strip() == "99" or cm.strip() == "999":
            continue
        events.append({"time": f"{int(hh):02d}:{int(mm):02d}", "cm": int(cm)})
    return events


def parse_tide(text):
    days = {}
    for line in text.splitlines():
        if len(line) < 136:
            continue
        try:
            y, m, d = int(line[72:74]), int(line[74:76]), int(line[76:78])
        except ValueError:
            continue
        days[f"20{y:02d}-{m:02d}-{d:02d}"] = {"highs": _events(line[80:108]), "lows": _events(line[108:136])}
    return days


def fetch_tide(dates, station="NH"):
    """回傳 {日期: {highs, lows}};跨年時兩個年度檔都抓。"""
    result = {}
    for year in sorted({d[:4] for d in dates}):
        resp = requests.get(tide_url(year, station), headers=HEADERS, timeout=20)
        resp.raise_for_status()
        table = parse_tide(resp.text)
        result.update({d: table[d] for d in dates if d in table})
    return result


def now_jst():
    return datetime.now(JST)


# ── 海況卡(ocean_crawler / surf_crawler 共用) ──
DAY_LABELS = ["今天", "明天", "後天"]


def _day_text(day):
    """{'weather': 中文或日文, 'wind': {...}, 'wave': {...}} 原樣帶出,前端決定顯示中文或日文。"""
    return {
        "date": day["date"],
        "weather": (day["weather"] or {}).get("zh") or (day["weather"] or {}).get("ja") or "",
        "wind": day["wind"],
        "wave": day["wave"],
    }


def spot_conditions(spot, forecast_raw, warnings_raw, tides, now):
    """把氣象廳的預報、警報、潮位整理成一張點位卡。
    verdict 只依官方資訊分級,不自己推算:
      avoid  = 現場官方禁止,或該市町村有警報/特別警報
      caution= 有跟下水有關的注意報(波浪、強風、高潮、雷)
      info   = 沒有上述官方資訊(不代表適合下水)
    """
    days = area_forecast(forecast_raw, spot["jma_area"])
    forecast = []
    for i, day in enumerate(days[:3]):
        item = _day_text(day)
        item["label"] = DAY_LABELS[i] if i < len(DAY_LABELS) else day["date"][5:]
        forecast.append(item)

    warnings = town_warnings(warnings_raw, spot["jma_town"]) if warnings_raw is not None else []
    heavy = [w for w in warnings if w["level"] in ("special", "warning")]
    marine = [w for w in warnings if w["level"] == "advisory" and w["marine"]]
    if warnings_raw is None:
        level, label = "info", "警報資料暫時抓不到，出發前請看氣象廳官網"
    elif heavy:
        level, label = "avoid", ("特別警報發布中" if any(w["level"] == "special" for w in heavy) else "警報發布中")
    elif marine:
        level, label = "caution", "注意報發布中"
    else:
        level, label = "info", "無海上相關警報"

    today = forecast[0] if forecast else None
    reason = ""
    if today:
        bits = []
        for key, name in (("wind", "風"), ("wave", "浪")):
            p = today.get(key)
            if p:
                bits.append(f"{name}：{p['zh'] or p['ja']}")
        reason = "氣象廳今天預報　" + "／".join(bits) if bits else ""

    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    tide = []
    for d, name in ((today_str, "今天"), (tomorrow_str, "明天")):
        if d in tides:
            tide.append({"label": name, "date": d, **tides[d]})

    return {
        "slug": spot["slug"],
        "name": spot["name"],
        "region": spot["region"],
        "kind": spot["kind"],
        "exposure": spot["exposure"],
        "official_note": spot.get("official_note", ""),
        "official_url": spot.get("official_url", ""),
        "official_label": spot.get("official_label", ""),
        "official_status": "",
        "reference_url": spot.get("reference_url", ""),
        "jma_area": spot["jma_area"],
        "jma_area_name": AREAS.get(spot["jma_area"], ""),
        "forecast": forecast,
        "warnings": warnings,
        "tide_station": "那霸",
        "tide": tide,
        "verdict": level,
        "verdict_label": label,
        "verdict_reason": reason,
    }


def fetch_all_for_spots(now):
    """一次抓齊預報、警報、潮位;警報或潮位失敗不擋整體(警報失敗時卡片會標示)。"""
    forecast_raw = fetch_forecast()
    try:
        warnings_raw = fetch_warnings()
    except (requests.RequestException, ValueError) as error:
        print(f"⚠️ 警報抓取失敗（{error}）")
        warnings_raw = None
    try:
        tides = fetch_tide([now.strftime("%Y-%m-%d"), (now + timedelta(days=1)).strftime("%Y-%m-%d")])
    except (requests.RequestException, ValueError) as error:
        print(f"⚠️ 潮位表抓取失敗（{error}）")
        tides = {}
    return forecast_raw, warnings_raw, tides
