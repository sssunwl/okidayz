"""額外的在地活動來源。每個函式回傳跟 okinawa_events_crawler 相同格式的 event dict 清單。

- okimeguri:沖繩縣官方「おきめぐり」,走它前端用的公開 API(結構化、附主辦方官網)
- jalan:じゃらんnet 沖繩活動列表(離島祭典、馬拉松、大型活動)
- goyah:ごーやーどっとネット(在地社區活動,每天有新文章),走 WordPress REST API
- naha / pref:那霸市、沖繩縣官網活動行事曆(/event.js),只收一般活動
- prtimes:PR TIMES 新聞稿(新開張、聯名、限定活動),標題要有沖繩地名

任何一個來源失敗都只回傳空清單,不影響其他來源。
"""
import html
import re
import time
import unicodedata
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
WINDOW_DAYS = 180
# おきめぐり 有很多飯店 buffet、海灘營業期間這類「長期公告」,不算活動
OKIMEGURI_MAX_SPAN_DAYS = 45


def _to_iso(dt):
    return dt.strftime("%Y-%m-%d")


def _in_window(start, end, now):
    return end >= now.replace(hour=0, minute=0, second=0, microsecond=0) and \
        start <= now + timedelta(days=WINDOW_DAYS)


# 徵選/報名公告不是旅客能去的活動
_NOT_EVENT = re.compile(r"募集|エントリー受付|出店者|出演者")


def _event(name, start, end, url, source, **extra):
    event = {
        "name": name, "name_zh": "",
        "date_start": _to_iso(start), "date_end": _to_iso(end),
        "url": url, "source": source,
        "category": "", "stars": 0,
        "description": "", "image": "", "location": "", "price": "", "official_url": "",
    }
    event.update({k: v for k, v in extra.items() if v})
    return event


def _safe_url(url):
    url = (url or "").strip()
    return url if url.startswith(("http://", "https://")) else ""


def _plain(text):
    text = re.sub(r"<br\s*/?>", "\n", text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


# ── おきめぐり(沖繩縣官方) ────────────────────────────────────────

OKIMEGURI_API = "https://backend.okimeguri.com/v1/prediction-calendar/schedules"
OKIMEGURI_CATEGORIES = (1, 2)  # 1=イベントスケジュール 2=大型イベント早見表(3=MICE 不要)


def get_okimeguri_events(now=None):
    now = now or datetime.now()
    headers = dict(HEADERS, Origin="https://okimeguri.com", Referer="https://okimeguri.com/")
    rows = {}
    for category in OKIMEGURI_CATEGORIES:
        offset = 0
        while offset < 1000:
            params = {
                "offset": offset, "sortBy": "開催日順",
                "period_start_filter": _to_iso(now),
                "period_end_filter": _to_iso(now + timedelta(days=WINDOW_DAYS)),
                "event_category_id": category, "items_per_page": 100,
            }
            try:
                res = requests.get(OKIMEGURI_API, params=params, headers=headers, timeout=30)
                res.raise_for_status()
                data = res.json()
            except Exception as e:
                print(f"⚠️ okimeguri 分類 {category} 失敗：{e}")
                break
            batch = data.get("rows") or []
            for row in batch:
                row["_big"] = category == 2
                rows.setdefault(row["id"], row)
            offset += len(batch)
            if not batch or offset >= int(data.get("count") or 0):
                break
            time.sleep(0.3)

    events = []
    for row in rows.values():
        try:
            start = datetime.strptime(row["period_start"][:10], "%Y-%m-%d")
            end = datetime.strptime((row.get("period_end") or row["period_start"])[:10], "%Y-%m-%d")
        except Exception:
            continue
        if not _in_window(start, end, now):
            continue
        if (end - start).days > OKIMEGURI_MAX_SPAN_DAYS and not row["_big"]:
            continue
        name = (row.get("name") or "").strip()
        if not name or _NOT_EVENT.search(name):
            continue
        area = row.get("area") or row.get("city") or ""
        place = row.get("place") or ""
        fee = (row.get("fee") or "").strip()
        events.append(_event(
            name, start, end,
            f"https://okimeguri.com/prediction-calendar/details/events/{row['id']}",
            "okimeguri",
            area=area,
            location=" ・ ".join(p for p in (place, area) if p),
            price="免費" if fee in ("無料", "無料。") else fee,
            official_url=_safe_url(row.get("official_url")),
            description=_plain(row.get("introductory_text"))[:200],
            category="大型活動" if row["_big"] else "",
        ))
    print(f"✅ okimeguri: {len(events)} 筆")
    return events


# ── じゃらんnet ──────────────────────────────────────────────────────

JALAN_BASE = "https://www.jalan.net/event/470000/"
_JALAN_DATE = re.compile(
    r"(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*[～〜~]\s*(?:(\d{4})年)?(?:(\d{1,2})月)?(\d{1,2})日)?")


def parse_jalan_period(text):
    m = _JALAN_DATE.search(text or "")
    if not m:
        return None, None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    start = datetime(y, mo, d)
    if not m.group(6):
        return start, start
    ey = int(m.group(4)) if m.group(4) else y
    em = int(m.group(5)) if m.group(5) else mo
    end = datetime(ey, em, int(m.group(6)))
    if end < start:  # 例:12月20日～1月5日 沒寫年
        end = datetime(ey + 1, em, int(m.group(6)))
    return start, end


def get_jalan_events(now=None):
    now = now or datetime.now()
    events = []
    seen = set()
    for page in range(1, 10):
        url = JALAN_BASE + (f"page_{page}/" if page > 1 else "")
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code == 404:
                break
            res.raise_for_status()
            res.encoding = "cp932"
        except Exception as e:
            print(f"⚠️ jalan page {page} 失敗：{e}")
            break
        soup = BeautifulSoup(res.text, "lxml")
        items = soup.select("li.item")
        if not items:
            break
        for item in items:
            link = item.select_one("p.item-name a[href*='/event/evt_']")
            if not link:
                continue
            m = re.search(r"/event/(evt_\d+)/", link["href"])
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            info = {}
            dl = item.select_one("dl.item-eventInfo")
            if dl:
                for dt in dl.find_all("dt"):
                    dd = dt.find_next_sibling("dd")
                    if dd:
                        info[dt.get_text(strip=True).rstrip("：:")] = dd.get_text(" ", strip=True)
            start, end = parse_jalan_period(info.get("期間", ""))
            if not start or not _in_window(start, end, now):
                continue
            area_tag = item.select_one("p.item-categories")
            area = area_tag.get_text(strip=True) if area_tag else ""
            desc_tag = item.select_one(".item-desc-e")
            img = item.select_one(".item-mainImg img")
            image = ""
            if img and img.get("src"):
                src = img["src"]
                image = "https://www.jalan.net" + src if src.startswith("/") else _safe_url(src)
            events.append(_event(
                link.get_text(strip=True), start, end,
                f"https://www.jalan.net/event/{m.group(1)}/", "jalan",
                area=area,
                location=info.get("場所", ""),
                image=image,
                description=desc_tag.get_text(" ", strip=True) if desc_tag else "",
            ))
        time.sleep(0.5)
    print(f"✅ jalan: {len(events)} 筆")
    return events


# ── ごーやーどっとネット ────────────────────────────────────────────

GOYAH_API = "https://goyah.net/wp-json/wp/v2/posts"
_GOYAH_DATE = re.compile(
    r"(?:(令和)\s*(\d{1,2})年|(\d{4})年)?\s*(\d{1,2})月\s*(\d{1,2})日"
    r"(?:[^〜～~\-－–\n]{0,12}[〜～~\-－–]\s*(?:(\d{1,2})月)?\s*(\d{1,2})日)?")
_GOYAH_DATE_LINE = re.compile(r"(日\s*時|日\s*程|開催日|開催期間|期\s*間)\s*[：:]")
_GOYAH_PLACE_LINE = re.compile(r"(会\s*場|場\s*所|開催場所)\s*[：:]\s*(.+)")


def _goyah_year(match, posted):
    if match.group(1):
        return 2018 + int(match.group(2))
    if match.group(3):
        return int(match.group(3))
    return None


def parse_goyah_dates(text, posted):
    """優先找『日時：』那一行;沒有才退回第一個出現的日期。年份沒寫就取發文後最近的那一次。"""
    text = unicodedata.normalize("NFKC", text)
    candidates = []
    for line in text.split("\n"):
        if _GOYAH_DATE_LINE.search(line):
            candidates.append(line)
    candidates.append(text[:400])
    for chunk in candidates:
        m = _GOYAH_DATE.search(chunk)
        if not m:
            continue
        month, day = int(m.group(4)), int(m.group(5))
        year = _goyah_year(m, posted) or posted.year
        try:
            start = datetime(year, month, day)
            if not _goyah_year(m, posted) and start < posted - timedelta(days=30):
                start = datetime(year + 1, month, day)
            end = start
            if m.group(7):
                end_month = int(m.group(6)) if m.group(6) else month
                end = datetime(start.year, end_month, int(m.group(7)))
                if end < start:
                    end = datetime(start.year + 1, end_month, int(m.group(7)))
        except ValueError:
            continue
        return start, end
    return None, None


def _goyah_posts_from_feed():
    """REST API 在 GitHub Actions 的 IP 會被擋 403,退回讀 RSS(最新幾篇、含全文)。"""
    posts = []
    for page in (1, 2, 3):
        try:
            res = requests.get("https://goyah.net/feed", params={"paged": page} if page > 1 else None,
                               headers=HEADERS, timeout=25)
            res.raise_for_status()
        except Exception as e:
            if page == 1:
                print(f"⚠️ goyah RSS 失敗：{e}")
            break
        soup = BeautifulSoup(res.content, "xml")
        for item in soup.find_all("item"):
            try:
                posted = datetime.strptime(item.pubDate.text.strip()[5:16], "%d %b %Y")
            except Exception:
                continue
            body = item.find("encoded")
            desc = item.find("description")
            posts.append({
                "date": _to_iso(posted),
                "link": item.link.text.strip() if item.link else "",
                "title": {"rendered": item.title.text if item.title else ""},
                "excerpt": {"rendered": desc.text if desc else ""},
                "content": {"rendered": body.text if body else ""},
            })
        time.sleep(0.5)
    return posts


def get_goyah_events(now=None, pages=2):
    now = now or datetime.now()
    events = []
    batches = []
    for page in range(1, pages + 1):
        try:
            res = requests.get(GOYAH_API, headers=HEADERS, timeout=25, params={
                "per_page": 50, "page": page, "orderby": "date",
                "_fields": "id,date,link,title,excerpt,content",
            })
            if res.status_code == 400:
                break
            res.raise_for_status()
            batches.append(res.json())
        except Exception as e:
            print(f"⚠️ goyah API page {page} 失敗：{e}")
            break
        time.sleep(0.5)
    if not batches:
        batches = [_goyah_posts_from_feed()]
    for posts in batches:
        for post in posts:
            try:
                posted = datetime.strptime(post["date"][:10], "%Y-%m-%d")
            except Exception:
                continue
            body = _plain(post.get("content", {}).get("rendered", ""))
            start, end = parse_goyah_dates(body or _plain(post.get("excerpt", {}).get("rendered", "")), posted)
            if not start or not _in_window(start, end, now):
                continue
            place = ""
            for line in unicodedata.normalize("NFKC", body).split("\n"):
                pm = _GOYAH_PLACE_LINE.search(line)
                if pm:
                    place = pm.group(2).strip()[:80]
                    break
            events.append(_event(
                _plain(post.get("title", {}).get("rendered", "")), start, end,
                _safe_url(post.get("link")), "goyah",
                location=place,
                description=_plain(post.get("excerpt", {}).get("rendered", "")).replace("[…]", "").strip()[:200],
            ))
    events = [e for e in events if e["name"] and e["url"] and not _NOT_EVENT.search(e["name"])]
    print(f"✅ goyah: {len(events)} 筆")
    return events


# ── 那霸市／沖繩縣官網的活動行事曆(同一套 CMS,資料在 /event.js) ───────────

# 公所行事曆一大半是講座、說明會、招募,旅客用不到
_CIVIC_SKIP = re.compile(
    r"募集|説明会|相談|研修|講座|学級|シンポジウム|セミナー|ワークショップ|会議|就職|就農|教室|"
    r"受付終了|講演|養成|障がい|事業者|審議|入札|検診|健診|プログラム|ミーティング|お知らせ$")
CIVIC_SITES = (
    ("naha", "https://www.city.naha.okinawa.jp", "那覇市"),
    ("pref", "https://www.pref.okinawa.lg.jp", ""),
)


def _civic_event_js(base):
    res = requests.get(base + "/event.js", headers=HEADERS, timeout=25)
    res.raise_for_status()
    text = res.content.decode("utf-8", "replace")
    start = text.index("events:") + len("events:")
    events, _ = __import__("json").JSONDecoder().raw_decode(text[start:].lstrip())
    return events


def get_civic_events(now=None):
    """category 10 = 一般活動。只收一般民眾/旅客能去的,而且期間不超過 45 天。"""
    now = now or datetime.now()
    out = []
    for source, base, city in CIVIC_SITES:
        try:
            items = _civic_event_js(base)
        except Exception as e:
            print(f"⚠️ {source} 活動行事曆失敗：{e}")
            continue
        count = 0
        for item in items:
            title = unicodedata.normalize("NFKC", item.get("eventtitle", "")).strip()
            if "10" not in (item.get("category") or []) or not title or _CIVIC_SKIP.search(title):
                continue
            days = sorted(d for d in item.get("opendays") or [] if re.match(r"\d{4}/\d{2}/\d{2}$", d))
            if not days:
                continue
            start = datetime.strptime(days[0], "%Y/%m/%d")
            end = datetime.strptime(days[-1], "%Y/%m/%d")
            if (end - start).days > OKIMEGURI_MAX_SPAN_DAYS or not _in_window(start, end, now):
                continue
            place = (item.get("place2") or item.get("place") or "").strip()
            if re.search(r"東京|大阪|名古屋|福岡|〒[0-8]", place):
                continue  # 縣政府在縣外辦的展覽/說明會
            out.append(_event(
                re.sub(r"(の)?(開催)?(について|のお知らせ|のご案内|特設サイト)$", "", title).strip(), start, end,
                _safe_url(base + item.get("url", "")), source,
                location=(place or city)[:80],
                description=_plain(item.get("description", ""))[:200],
                official_url=_safe_url(base + item.get("url", "")),
            ))
            count += 1
        print(f"✅ {source}: {count} 筆")
    return out


# ── PR TIMES(店家／品牌新聞稿：新開張、聯名、限定活動) ──────────────────

PRTIMES_API = "https://prtimes.jp/api/keyword_search.php/search"
# 標題裡要有沖繩的地名才算沖繩的消息(否則「沖縄物産展 in 東京」也會進來)
_OKI_PLACE = re.compile(
    r"沖縄|那覇|国際通り|首里|宮古|石垣|八重山|北谷|美浜|読谷|恩納|名護|本部|美ら海|海洋博|今帰仁|"
    r"浦添|宜野湾|うるま|糸満|豊見城|南城|瀬長島|久米島|西表|竹富|やんばる|古宇利|慶良間|座間味")
_PR_SKIP = re.compile(r"物産展|物産フェア|アンテナショップ|ふるさと納税|発着|ツアー|採用|求人|資金調達|"
                      r"業務提携|協定|就航|運賃|セール|プレゼント|キャンペーン|カンファレンス|企業向け|研修|"
                      r"東京|大阪|名古屋|福岡|鎌倉|横浜|京都|札幌|ソウル|台北|台湾|香港|韓国")
_PR_EVENT = re.compile(r"開催|オープン|開業|誕生|新店舗|出店|期間限定|限定|フェア|フェス|イベント|コラボ|公開|開幕")
_PR_DATE = re.compile(r"(?:(\d{4})年)?\s*(\d{1,2})月(\d{1,2})日")


def get_prtimes_events(now=None, pages=3):
    now = now or datetime.now()
    out, seen = [], set()
    for page in range(1, pages + 1):
        try:
            res = requests.get(PRTIMES_API, headers=HEADERS, timeout=25,
                               params={"keyword": "沖縄", "page": page, "limit": 40})
            res.raise_for_status()
            items = (res.json().get("data") or {}).get("release_list") or []
        except Exception as e:
            print(f"⚠️ PR TIMES page {page} 失敗：{e}")
            break
        for item in items:
            title = unicodedata.normalize("NFKC", item.get("title", "")).strip()
            url = _safe_url("https://prtimes.jp" + (item.get("release_url") or ""))
            if not url or url in seen or not _OKI_PLACE.search(title) or _PR_SKIP.search(title) \
                    or not _PR_EVENT.search(title):
                continue
            seen.add(url)
            dates = []
            for y, m, d in _PR_DATE.findall(title):
                year = int(y) if y else now.year
                try:
                    dt = datetime(year, int(m), int(d))
                except ValueError:
                    continue
                if not y and dt < now - timedelta(days=60):
                    dt = dt.replace(year=now.year + 1)
                dates.append(dt)
            opening = re.search(r"オープン|開業|誕生|新店舗|出店", title)
            if not dates:
                if not opening:
                    continue
                dates = [now]  # 新開張沒寫日期:當天上架,放一個月
                dates.append(now + timedelta(days=30))
            start, end = min(dates), max(dates)
            if opening and end == start:
                end = start + timedelta(days=30)
            if not _in_window(start, end, now):
                continue
            out.append(_event(
                title, start, end, url, "prtimes",
                category="新開張" if opening else "",
                description=title,
                image=_safe_url((item.get("thumbnail_url") or "").split("?")[0]),
                location=item.get("company_name", "")[:60],
            ))
        time.sleep(0.5)
    print(f"✅ prtimes: {len(out)} 筆")
    return out


# ── 跨來源去重 ──────────────────────────────────────────────────────

def normalize_name(name):
    text = unicodedata.normalize("NFKC", name or "").lower()
    text = re.sub(r"第\s*\d+\s*回", "", text)
    text = re.sub(r"(20\d\d|令和\s*\d*)\s*(年度?)?", "", text)
    text = re.sub(r"(行事)?(開催)?(決定|のお知らせ|について|のご案内|のおしらせ)|行事開催|開催", "", text)
    text = re.sub(r"[\s\W_]+", "", text)
    return text


def dedupe_across_sources(events):
    """開始日相差 3 天內、名稱互相包含(正規化後)就視為同一個活動。
    保留排在前面的那筆,缺的欄位(官網、圖片、地點…)用後面那筆補上。"""
    kept = []
    for event in events:
        if not event.get("url"):
            kept.append(event)
            continue
        key = normalize_name(event.get("name"))
        start = datetime.strptime(event["date_start"], "%Y-%m-%d")
        twin = None
        if len(key) >= 4:
            for other in kept:
                other_key = other.get("_norm", "")
                if len(other_key) < 4 or abs((other["_start"] - start).days) > 3:
                    continue
                if key in other_key or other_key in key:
                    twin = other
                    break
        if twin:
            for field in ("official_url", "image", "location", "price", "description", "area"):
                if not twin.get(field) and event.get(field):
                    twin[field] = event[field]
            twin.setdefault("_dup_urls", []).append(event["url"])
            continue
        event["_norm"] = key
        event["_start"] = start
        kept.append(event)
    for event in kept:
        event.pop("_norm", None)
        event.pop("_start", None)
    return kept
