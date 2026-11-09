"""BigDayz 教堂資料同步：wedding/ 素材庫 → data/bigdayz.json ＋ 攻略文章。

來源是 ../wedding/data/chapels.json（SS 自己的素材庫，jwc/ 的唯讀副本）；GitHub Actions 讀不到
工作區外的資料，所以要在本機跑這支，把網站需要的欄位抄進 data/bigdayz.json 再 commit。
照片只用各教堂／婚宴場地官網的圖（直連不搬檔），頁面上標小字出處。
用法：python3 tools/bigdayz_sync.py，再跑 build.py。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT.parent / "wedding" / "data" / "chapels.json"
OUT = ROOT / "data" / "bigdayz.json"
ARTICLE = ROOT / "content" / "guide" / "okinawa-seaview-chapels.md"

# 中文名用 JWC 慣用譯名的第一個；日文名用官網名稱，旅客問飯店櫃台、看指標都用得上。
# 順序＝從南到北的開車路線。
PLACES = {
    "centlegenda-chapel": ("セントレジェンダ OKINAWA", "北谷町", "北谷町", "中部",
        "在北谷美濱，離美國村很近，從那霸過來最近的一座。"),
    "lazor-siele-chapel": ("ラソール シー リゾート シエール教会", "読谷村", "讀谷村", "中部",
        "2025 年 2 月才開的新教堂，蓋在讀谷都屋的白沙灘旁，挑高玻璃牆整面對著海。"),
    "lazor-garden-alivila": ("ラソール ガーデン・アリビラ クリスティア教会", "読谷村", "讀谷村", "中部",
        "在日航アリビラ和虹夕諾雅沖繩中間，住這兩間的人散步五分鐘就到。"),
    "alivila-glory-church": ("アリビラ・グローリー教会", "読谷村", "讀谷村", "中部",
        "紅瓦白牆、尖塔加彩繪玻璃，就在日航アリビラ旁邊，是讀谷海岸線最好認的一座。"),
    "aquagrace-wedding-chapel": ("ザ・ヨミタンリゾート アクアグレイス・チャペル", "読谷村", "讀谷村", "中部",
        "在殘波岬附近的宇座海灘，順路玩殘波岬燈塔的話可以一起排。"),
    "monterey-lumer-chapel": ("モントレ・ルメール教会", "恩納村", "恩納村", "中部",
        "在ホテルモントレ沖縄旁，恩納村西海岸一整排度假飯店的其中一段。"),
    "renaissance-ribera-church": ("ルネッサンス・リベーラ教会", "恩納村", "恩納村", "中部",
        "離ルネッサンス リゾート オキナワ走路約 5 分鐘，住這間的人最方便順路。"),
    "diamond-ocean-chapel": ("チャペル・ダイアモンドオーシャン", "恩納村", "恩納村", "中部",
        "在沖縄かりゆしビーチリゾート・オーシャンスパ的丘上，全面玻璃往下看海。"),
    "eines-villa-di-nozze-okinawa": ("アイネス ヴィラノッツェ 沖縄", "名護市", "名護市", "北部",
        "名護許田附近，玻璃教堂正對海灘，北上去美麗海水族館前會經過這一帶。"),
    "grand-bleu-chapel": ("アイネス ヴィラノッツェ in カヌチャベイ グラン・ブルーチャペル", "名護市", "名護市", "北部",
        "在東海岸的カヌチャリゾート園區裡，跟西海岸那排完全是另一種安靜。"),
    "kouri-island-celeste-chapel": ("古宇利島 空と海の教会", "今帰仁村", "今歸仁村", "北部",
        "過古宇利大橋上島就到，白色三角形屋頂很好認，玩古宇利島可以一起看。"),
}
# 教堂旁邊順路的海灘／景點（地點頁的 slug），頁面上「附近可以順路」用
NEARBY = {
    "centlegenda-chapel": ["american-village", "sunset-beach", "araha-beach"],
    "lazor-siele-chapel": ["yomitan-yachimun", "zanpa-cape"],
    "lazor-garden-alivila": ["yomitan-yachimun", "zanpa-cape"],
    "alivila-glory-church": ["yomitan-yachimun", "zanpa-cape"],
    "aquagrace-wedding-chapel": ["zanpa-cape", "zanpa-beach"],
    "monterey-lumer-chapel": ["manzamo", "moon-beach"],
    "renaissance-ribera-church": ["manzamo", "moon-beach"],
    "diamond-ocean-chapel": ["manzamo"],
    "eines-villa-di-nozze-okinawa": ["churaumi", "bise-fukugi"],
    "grand-bleu-chapel": [],
    "kouri-island-celeste-chapel": ["kouri-bridge", "kouri-beach", "nakijin-castle"],
}


def first_name(text):
    return re.split(r"\s*/\s*", str(text))[0].strip()


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    source = {c["slug"]: c for c in data["chapels"]}
    chapels = []
    for slug, (ja, area_ja, area_zh, region, why) in PLACES.items():
        c = source[slug]
        if not c.get("official_url"):
            raise SystemExit("缺官網資料：" + slug)
        chapels.append({
            "slug": slug,
            "name": {"zh": first_name(c["name_zh"]), "en": c["name_en"], "ja": ja},
            "area_ja": area_ja, "area_zh": area_zh, "region": region, "summary": why,
            "capacity": re.split(r"[(（]", str(c.get("capacity", "")))[0],
            "aisle_m": c.get("aisle_m"),
            "ocean_view": bool(c.get("ocean_view")),
            "opened": c.get("opened") or "",
            "cuisine": c.get("cuisine") or "",
            "nearby_hotel": c.get("nearby_hotel") or "",
            "photos": (c.get("image_urls") or [])[:8],
            "source": c["official_source"], "official_url": c["official_url"],
            "nearby": NEARBY.get(slug, []),
        })
    OUT.write_text(json.dumps({"_note": "由 tools/bigdayz_sync.py 從 wedding/data/chapels.json 產生，不要手改。",
                               "chapels": chapels}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_article(chapels)
    print("寫入", OUT.relative_to(ROOT), "與", ARTICLE.relative_to(ROOT))


def write_article(chapels):
    lines = [
        "---",
        "title: 沖繩海景教堂地圖：十一座可以順路看的海邊教堂",
        "slug: okinawa-seaview-chapels",
        "summary: 北谷、讀谷、恩納、名護到古宇利島，十一座海邊教堂依路線排好。不結婚也可以當景點順路看，最後再告訴你想在這裡行禮要找誰。",
        "tags: [BigDayz, 教堂, 沖繩本島, 中部, 北部]",
        "updated: 2026-11-09",
        "cover: {}".format(chapels[-1]["photos"][0]),
        "---",
        "",
        "沖繩的海邊教堂幾乎都蓋在度假飯店旁邊，不少是**整面玻璃正對著海**。就算這趟不是來結婚，"
        "住在附近、或剛好開車經過，也值得繞過去看一眼。",
        "",
        "下面依照從南到北的開車路線排：北谷、讀谷、恩納，最後是名護和古宇利島。每座都有自己的地點頁，"
        "看得到宴會廳、附近順路的景點，還有當天的天氣和活動。",
        "",
        "## 去看之前先知道",
        "",
        "- 教堂是婚禮場地，**不是隨時開放的觀光點**。外觀多半從飯店或海灘就看得到，室內要看通常得預約見學（ブライダルフェア），日程看各官網。",
        "- 白天常有婚禮進行，遇到儀式請不要靠近、不要拍新人。",
        "- 停車多半是飯店停車場，先確認能不能給非住客停。",
        "",
    ]
    for c in chapels:
        lines += [
            "## {}".format(c["name"]["zh"]),
            "",
            "{}｜{}".format(c["name"]["en"], c["name"]["ja"]),
            "",
            "**{}・{}**　{}　[看教堂頁](../bigdayz/{}/)".format(c["area_zh"], c["region"], c["summary"], c["slug"]),
            "",
        ]
    lines += [
        "## 想在這裡行禮？",
        "",
        "每座教堂的地點頁都放了官網連結，挙式方案、見學預約、婚紗旅拍（フォトウェディング）都可以從那裡問。"
        "第一次聯絡時先講好日期、人數和要不要辦宴會，回覆會快很多。",
    ]
    ARTICLE.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
