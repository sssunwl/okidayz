"""Big Dayz「沖繩海景教堂地圖」產生器。

資料來源是 ../wedding/data/chapels.json（SS 自己的素材庫，jwc/ 的唯讀副本）。
照片只用各教堂／婚宴場地官網的圖（image_urls，直連不搬檔），每張都標官網出處。
改了教堂資料就重跑：python3 tools/bigdayz_chapels.py，再跑 build.py。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT.parent / "wedding" / "data" / "chapels.json"
OUT = ROOT / "content" / "bigdayz" / "okinawa-seaview-chapels.md"

# 教堂在地圖上的位置（區域標籤用 OkiDayz 共用那套）與一句「為什麼值得順路看」。
# 名稱用官網日文名，旅客到現場看指標、問飯店櫃台都用得上。
PLACES = {
    "centlegenda-chapel": ("セントレジェンダ OKINAWA", "北谷町", "中部",
        "在北谷美濱，離美國村很近，從那霸過來最近的一座。"),
    "lazor-siele-chapel": ("シエール教会（ラソール シー リゾート）", "讀谷村", "中部",
        "2025 年 2 月才開的新教堂，蓋在讀谷都屋的白沙灘旁，挑高玻璃牆整面對著海。"),
    "lazor-garden-alivila": ("クリスティア教会（ラソール ガーデン・アリビラ）", "讀谷村", "中部",
        "在日航アリビラ和虹夕諾雅沖繩中間，住這兩間的人散步五分鐘就到。"),
    "alivila-glory-church": ("アリビラ・グローリー教会", "讀谷村", "中部",
        "紅瓦白牆、尖塔加彩繪玻璃，就在日航アリビラ旁邊，是讀谷海岸線最好認的一座。"),
    "aquagrace-wedding-chapel": ("アクアグレイス・チャペル（ザ・ヨミタンリゾート）", "讀谷村", "中部",
        "在殘波岬附近的宇座海灘，順路玩殘波岬燈塔的話可以一起排。"),
    "monterey-lumer-chapel": ("モントレ・ルメール教会", "恩納村", "中部",
        "在ホテルモントレ沖縄旁，恩納村西海岸一整排度假飯店的其中一段。"),
    "renaissance-ribera-church": ("Renaissance Ribera Church", "恩納村", "中部",
        "離ルネッサンス リゾート オキナワ走路約 5 分鐘，住這間的人最方便順路。"),
    "diamond-ocean-chapel": ("チャペル・ダイアモンドオーシャン", "恩納村", "中部",
        "在沖縄かりゆしビーチリゾート・オーシャンスパ的丘上，全面玻璃往下看海。"),
    "eines-villa-di-nozze-okinawa": ("アイネス ヴィラノッツェ 沖縄", "名護市", "北部",
        "名護許田附近，玻璃教堂正對海灘，北上去美麗海水族館前會經過這一帶。"),
    "grand-bleu-chapel": ("グラン・ブルーチャペル（カヌチャベイ）", "名護市", "北部",
        "在東海岸的カヌチャリゾート園區裡，跟西海岸那排完全是另一種安靜。"),
    "kouri-island-celeste-chapel": ("古宇利島 空と海の教会", "今歸仁村", "北部",
        "過古宇利大橋上島就到，白色三角形屋頂很好認，玩古宇利島可以一起看。"),
}
ORDER = list(PLACES)


def chapel_block(chapel):
    name, town, region, why = PLACES[chapel["slug"]]
    images = chapel.get("image_urls") or []
    lines = ["## {}".format(name), ""]
    if images:
        lines += ["![{}]({})".format(name, images[0]), ""]
    lines += [
        "**{}・{}**　{}".format(town, region, why),
        "",
        "- 附近住宿：{}".format(chapel.get("nearby_hotel") or "—"),
        "- 教堂大小：約 {} 人，走道 {} 公尺".format(
            str(chapel.get("capacity", "")).split("(")[0].split("（")[0], chapel.get("aisle_m", "—")),
        "- 照片來源：[{}]({})".format(chapel["official_source"], chapel["official_url"]),
        "",
    ]
    return lines


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    chapels = {c["slug"]: c for c in data["chapels"]}
    missing = [slug for slug in ORDER if not chapels.get(slug, {}).get("official_url")]
    if missing:
        raise SystemExit("缺官網資料：" + ", ".join(missing))
    cover = chapels["kouri-island-celeste-chapel"]["image_urls"][0]

    lines = [
        "---",
        "title: 沖繩海景教堂地圖：十一座可以順路看的海邊教堂",
        "slug: okinawa-seaview-chapels",
        "summary: 北谷、讀谷、恩納、名護到古宇利島，十一座海邊教堂依路線排好。不結婚也可以當景點順路看，最後再告訴你想在這裡行禮要找誰。",
        "tags: [教堂, 沖繩本島, 中部, 北部]",
        "updated: 2026-11-09",
        "cover: {}".format(cover),
        "---",
        "",
        "沖繩的海邊教堂幾乎都蓋在度假飯店旁邊，不少是**整面玻璃正對著海**。就算這趟不是來結婚，"
        "住在附近、或剛好開車經過，也值得繞過去看一眼。",
        "",
        "下面依照從南到北的開車路線排：北谷、讀谷、恩納，最後是名護和古宇利島。",
        "",
        "## 去看之前先知道",
        "",
        "- 教堂是婚禮場地，**不是隨時開放的觀光點**。外觀多半從飯店或海灘就看得到，室內要看通常得預約見學（ブライダルフェア），日程看各官網。",
        "- 白天常有婚禮進行，遇到儀式請不要靠近、不要拍新人。",
        "- 停車多半是飯店停車場，先確認能不能給非住客停。",
        "",
    ]
    for slug in ORDER:
        lines += chapel_block(chapels[slug])
    lines += [
        "## 想在這裡行禮？",
        "",
        "每座教堂的照片下面都放了官網連結，挙式方案、見學預約、婚紗旅拍（フォトウェディング）都可以從那裡問。"
        "第一次聯絡時先講好日期、人數和要不要辦宴會，回覆會快很多。",
        "",
        "*本頁照片皆取自各教堂／婚宴場地官網，著作權屬原權利人。*",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("寫入", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
