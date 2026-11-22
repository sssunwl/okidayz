#!/usr/bin/env python3
"""沖繩新鮮事：從 PR TIMES 的企業新聞稿挑出「旅客到沖繩用得上」的新東西，寫進 docs/new.json。

PR TIMES 搜「沖縄」等關鍵字，一頁 40 則，大半是只順帶提到沖繩的全國新聞。
所以兩道篩：先看內文有沒有沖繩地名，再請 OpenAI 判斷旅客用不用得上
（新開幕、期間限定、沖繩限定商品、在沖繩辦的活動、住宿方案、交通新航線…），
用得上的才整理成繁中。判過不收的記在 docs/new-seen.json，不重問。

只做短摘要＋原文連結，不轉載全文。新聞稿配圖先不放（授權等 SS 決定），
只記在 image 欄，網站開關是 build.py 的 FRESH_SHOW_IMAGES。

    python3 prtimes_crawler.py
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from news_crawler import HEADERS, JST, get_openai_client

ROOT = Path(__file__).parent
NEW_FILE = ROOT / "docs" / "new.json"
SEEN_FILE = ROOT / "docs" / "new-seen.json"

KEYWORDS = ["沖縄", "那覇", "石垣島", "宮古島"]
SEARCH_URL = "https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word={}"
BASE = "https://prtimes.jp"
MAX_ASK = 45          # 每次最多問 OpenAI 幾則（新聞稿一天約 20 則）
KEEP_DAYS = 30        # 發布超過幾天、又沒寫結束日的就下架
SEEN_DAYS = 45        # 判過不收的記多久
SUMMARY_MAX_CHARS = 110

KINDS = ["新開幕", "期間限定", "沖繩限定", "活動", "住宿", "交通", "其他"]
AREAS = ["那霸", "北部", "中部", "南部", "離島", "全島"]
# 內文要提到其中一個，才值得問 OpenAI
OKINAWA_WORDS = re.compile(
    "沖縄|那覇|浦添|宜野湾|北谷|読谷|恩納|名護|本部|今帰仁|国頭|うるま|沖縄市|豊見城|糸満|南城|"
    "八重瀬|与那原|西原|石垣|宮古|久米島|座間味|渡嘉敷|竹富|西表|与那国|瀬底|古宇利|伊江")

REPORT = {"generated": "", "listed": 0, "asked": 0, "kept": 0, "skipped": []}


def skip(what, why):
    REPORT["skipped"].append({"item": what, "reason": why})
    print("⏭️  跳過 {}：{}".format(what, why))


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# ── PR TIMES 抓取 ─────────────────────────────────────────────────────

def list_releases(keyword):
    url = SEARCH_URL.format(quote(keyword))
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
    except requests.RequestException as error:
        skip("搜尋 " + keyword, "抓取失敗（{}）".format(error))
        return []
    soup = BeautifulSoup(res.text, "html.parser")
    items = []
    for article in soup.find_all("article"):
        link = article.find("a", href=re.compile(r"^/main/html/rd/p/\d+\.\d+\.html$"))
        title = article.find("h3")
        if not link or not title:
            continue
        company = article.find("a", href=re.compile(r"/company_id/"))
        items.append({
            "url": BASE + link["href"],
            "title_ja": title.get_text(strip=True),
            "company": company.get_text(strip=True) if company else "",
        })
    return items


def fetch_release(url):
    res = requests.get(url, headers=HEADERS, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    info = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except ValueError:
            continue
        for node in data if isinstance(data, list) else [data]:
            if isinstance(node, dict) and node.get("@type") == "NewsArticle":
                info = node
    body = soup.select_one(".press-release-body-v3-0-0") or soup.find("article")
    text = re.sub(r"\s+", " ", body.get_text(" ")).strip() if body else ""
    image = (info.get("image") or {}).get("url", "") if isinstance(info.get("image"), dict) else ""
    return {
        "date": str(info.get("datePublished") or "")[:10],
        "company": ((info.get("author") or {}).get("name") or "") if isinstance(info.get("author"), dict) else "",
        "section": str(info.get("articleSection") or ""),
        "body": text,
        "image": image.split("?")[0] if image.startswith("https://") else "",
    }


# ── OpenAI 判斷＋整理 ─────────────────────────────────────────────────

SYSTEM_PROMPT = """你是沖繩旅遊網站 OkiDayz 的編輯，正在從日本企業新聞稿裡挑「來沖繩的旅客用得上的新東西」。
收到一則日文新聞稿（標題、發布企業、內文），請判斷並整理成繁體中文。

1. relevant：旅客人在沖繩時，能不能去、吃、買、住、參加或搭到它？
   要收（true）：沖繩的新店／新設施開幕、在沖繩可吃可買的期間限定或沖繩限定商品、在沖繩舉辦的活動（觀光客也能參加）、
   沖繩的飯店新方案或新開幕、往返沖繩的新航線或交通新服務、沖繩景點的新體驗。
   不收（false）：只是全國商品順帶在沖繩也有賣、全國連鎖促銷、網購特賣、徵才、財報與企業合作、B2B 研討會或商業論壇、
   問卷調查、健康講座、婚禮企劃、從日本其他城市出發的旅行團、只給在地居民或企業的活動、只是提到「沖縄県代表」等、運動隊伍新聞（除非是觀光客可買票的賽事）。
   拿不準就 false。
2. 下面欄位只在 relevant 為 true 時填，否則全部給空字串：
   title_zh：繁中標題，講清楚「是什麼、在哪」，不超過 32 字，不要用驚嘆號和宣傳腔。
   summary_zh：2 句繁中摘要，只寫內文有的事實（日期、地點、價錢、怎麼參加），不超過 {max_chars} 字，不要形容詞堆疊。
   kind：從 {kinds} 選一個。
   area：從 {areas} 選一個（那霸含首里、新都心、おもろまち、小祿；離島＝石垣、宮古、久米島、慶良間等）。判斷不出來用「全島」。
   where_zh：店名或地點，例如「國際通 OPA 1 樓」，不超過 20 字；沒寫用空字串。
   start、end：開始與結束日期 YYYY-MM-DD，內文沒寫就空字串；只有開幕日就只填 start。

只回傳這個 JSON，不要加其他文字、不要加 markdown code fence：
{{"relevant": false, "title_zh": "", "summary_zh": "", "kind": "", "area": "", "where_zh": "", "start": "", "end": ""}}""".format(
    max_chars=SUMMARY_MAX_CHARS, kinds="、".join(KINDS), areas="、".join(AREAS))


def judge(client, item, release):
    user_content = "標題：{}\n發布企業：{}\n分類：{}\n內文：{}".format(
        item["title_ja"], release["company"] or item["company"], release["section"], release["body"][:2500])
    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": user_content}],
        )
        raw = response.choices[0].message.content.strip()
    except Exception as error:  # noqa: BLE001 — 第三方 API 各種例外都當成跳過處理
        skip(item["title_ja"][:30], "OpenAI 呼叫失敗（{}）".format(error))
        return None
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
    except ValueError:
        skip(item["title_ja"][:30], "回傳不是合法 JSON")
        return None
    return data if isinstance(data, dict) else None


def clean_date(value):
    value = str(value or "").strip()
    return value if re.fullmatch(r"20\d\d-\d\d-\d\d", value) else ""


def to_entry(item, release, data):
    title = str(data.get("title_zh") or "").strip()
    summary = str(data.get("summary_zh") or "").strip()
    if not title or not summary:
        return None
    if len(summary) > SUMMARY_MAX_CHARS:
        summary = summary[:SUMMARY_MAX_CHARS].rstrip() + "…"
    kind = str(data.get("kind") or "").strip()
    area = str(data.get("area") or "").strip()
    return {
        "date": release["date"],
        "title": title[:40],
        "summary": summary,
        "kind": kind if kind in KINDS else "其他",
        "area": area if area in AREAS else "全島",
        "where": str(data.get("where_zh") or "").strip()[:24],
        "start": clean_date(data.get("start")),
        "end": clean_date(data.get("end")),
        "company": release["company"] or item["company"],
        "title_ja": item["title_ja"],
        "url": item["url"],
        "image": release["image"],
        "source": "PR TIMES",
    }


# ── 主流程 ────────────────────────────────────────────────────────────

def still_fresh(entry, today):
    if entry.get("end"):
        return entry["end"] >= today
    if entry.get("start"):
        if entry["start"] >= today:
            return True
        if entry.get("kind") == "活動":
            return False  # 已經開始、沒寫結束日的活動，當作辦完了
    cutoff = (datetime.now(JST) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    return entry.get("date", "") >= cutoff


def run(client):
    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")
    REPORT["generated"] = now.strftime("%Y-%m-%d %H:%M")

    existing = read_json(NEW_FILE, [])
    by_url = {entry["url"]: entry for entry in existing if entry.get("url")}
    seen_cutoff = (now - timedelta(days=SEEN_DAYS)).strftime("%Y-%m-%d")
    seen = {url: day for url, day in read_json(SEEN_FILE, {}).items() if day >= seen_cutoff}

    listed = {}
    for keyword in KEYWORDS:
        for item in list_releases(keyword):
            listed.setdefault(item["url"], item)
    REPORT["listed"] = len(listed)

    for url, item in listed.items():
        if url in by_url or url in seen:
            continue
        if REPORT["asked"] >= MAX_ASK:
            break
        try:
            release = fetch_release(url)
        except requests.RequestException as error:
            skip(item["title_ja"][:30], "新聞稿抓取失敗（{}）".format(error))
            continue
        if not OKINAWA_WORDS.search(item["title_ja"] + release["body"]):
            seen[url] = today
            continue
        REPORT["asked"] += 1
        data = judge(client, item, release)
        if data is None:
            continue  # 這次失敗不記 seen，下次再試
        entry = to_entry(item, release, data) if data.get("relevant") is True else None
        if entry:
            by_url[url] = entry
            REPORT["kept"] += 1
        else:
            seen[url] = today

    final = [entry for entry in by_url.values() if still_fresh(entry, today)]
    final.sort(key=lambda entry: entry.get("date", ""), reverse=True)
    if not final and existing:
        print("⚠️  這次一則都沒有，保留上一版")
        final = existing

    NEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    NEW_FILE.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    (ROOT / "docs" / "new-report.json").write_text(
        json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    print("🆕 沖繩新鮮事：列出 {} 則、問 {} 則、新收 {} 則、上線 {} 則".format(
        REPORT["listed"], REPORT["asked"], REPORT["kept"], len(final)))


def main():
    from build import build_site
    client = get_openai_client()
    if client is None:
        print("⚠️  沒有可用的 OpenAI key，只重建網頁、不更新新鮮事")
    else:
        run(client)
    events = read_json(ROOT / "docs" / "events.json", [])
    weather = read_json(ROOT / "docs" / "weather.json", [])
    build_site(events=events, weather=weather, updated=datetime.now(JST).strftime("%Y-%m-%d %H:%M"))


if __name__ == "__main__":
    main()
