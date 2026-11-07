"""網站上的 emoji 全部換成品牌手繪版(同 brand_assets.py 的鉛筆筆觸)。
用法：python3 tools/emoji_icons.py
輸出 assets/brand/emoji/<名>.svg ＋ assets/emoji.js(對照表＋換圖程式)。
網頁載入 assets/emoji.js 後，畫面上的 emoji 會被換成這套圖；沒對到的用 spark。
新 emoji 要對到哪張圖，改下面 MAP 再重跑。"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand_assets import INK, MANGO, PAPER, SEA, SUN, TILE, FOAM, Pen, circle, wave_pts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "brand" / "emoji"
LEAF = "#6fa83a"
PINK = "#e0457b"


def sun(p):
    c = circle(32, 32, 12, 12, p.rng, 0.05)
    p.hatch(c, MANGO); p.line(c, True)
    for a in range(0, 360, 45):
        r = math.radians(a)
        p.line([(32 + 17 * math.cos(r), 32 + 17 * math.sin(r)), (32 + 24 * math.cos(r), 32 + 24 * math.sin(r))], width=2.2)


def cloud_pts(dx=0, dy=0):
    return [(x + dx, y + dy) for x, y in [(12, 46), (10, 37), (18, 31), (26, 32), (31, 22), (43, 22), (49, 31), (56, 34), (56, 44), (50, 47)]]


def cloud(p):
    c = cloud_pts()
    p.hatch(c, FOAM, gap=4); p.line(c, True, fill=PAPER)


def suncloud(p):
    s = circle(22, 22, 10, 12, p.rng, 0.05)
    p.hatch(s, MANGO); p.line(s, True)
    for a in (180, 225, 270, 315):
        r = math.radians(a)
        p.line([(22 + 14 * math.cos(r), 22 + 14 * math.sin(r)), (22 + 19 * math.cos(r), 22 + 19 * math.sin(r))], width=2)
    p.line(cloud_pts(4, 8), True, fill=PAPER)


def rain(p):
    p.line(cloud_pts(0, -8), True, fill=PAPER)
    for x in (20, 32, 44):
        p.line([(x, 44), (x - 4, 56)], width=2.4, color=SEA)


def storm(p):
    c = cloud_pts(0, -10)
    p.hatch(c, "#9aa7ad", gap=4); p.line(c, True)
    bolt = [(34, 38), (26, 50), (33, 50), (28, 61), (42, 46), (35, 46), (40, 38)]
    p.hatch(bolt, MANGO, gap=2.5); p.line(bolt, True)


def snow(p):
    for a in (0, 60, 120):
        r = math.radians(a)
        p.line([(32 - 22 * math.cos(r), 32 - 22 * math.sin(r)), (32 + 22 * math.cos(r), 32 + 22 * math.sin(r))], width=2.4, color=SEA)
    p.dot(32, 32, 3, SEA)


def moon(p):
    c = [(38, 8), (26, 12), (18, 24), (18, 38), (26, 50), (40, 56), (52, 52), (40, 46), (32, 34), (32, 22)]
    p.hatch(c, SUN); p.line(c, True)


def drop(p):
    c = [(32, 8), (40, 24), (46, 36), (44, 48), (36, 56), (26, 55), (19, 46), (19, 35), (25, 23)]
    p.hatch(c, SEA, angle=-30); p.line(c, True)


def wave(p):
    band = wave_pts(6, 58, 30, 5, 18) + [(58, 52), (6, 52)]
    p.hatch(band, SEA, angle=-25)
    p.line(wave_pts(6, 58, 30, 5, 18))
    p.line(wave_pts(10, 54, 44, 3, 14), width=2)


def island(p):
    sand = [(6, 50), (14, 42), (32, 39), (50, 42), (58, 50)]
    p.hatch(sand + [(58, 54), (6, 54)], SUN); p.line(sand)
    p.line(wave_pts(4, 60, 56, 1.6, 10), width=2, color=SEA)
    p.line([(30, 40), (32, 28), (35, 16)], width=2.6)
    for a, b in [((35, 16), (22, 18)), ((35, 16), (46, 20)), ((35, 16), (26, 10)), ((35, 16), (44, 8))]:
        p.line([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 3), b], width=2.4, color=LEAF)


def turtle(p):
    shell = circle(32, 34, 15, 12, p.rng, 0.04)
    p.hatch(shell, "#6aa58a"); p.line(shell, True)
    p.line(circle(32, 15, 5, 8, p.rng, 0.05), True)
    for x, y in [(15, 24), (49, 24), (16, 46), (48, 46)]:
        p.line(circle(x, y, 4, 7, p.rng, 0.1), True)


def pin(p):
    c = [(32, 58), (20, 38), (17, 26), (22, 14), (32, 9), (42, 14), (47, 26), (44, 38)]
    p.hatch(c, TILE); p.line(c, True)
    p.line(circle(32, 26, 6, 9, p.rng, 0.05), True, fill=PAPER)


def news(p):
    pg = [(10, 12), (50, 12), (50, 54), (14, 54), (10, 50)]
    p.line(pg, True, fill=PAPER, corner=True)
    p.hatch([(16, 18), (30, 18), (30, 30), (16, 30)], SEA)
    p.line([(16, 18), (30, 18), (30, 30), (16, 30)], True, width=1.8, corner=True)
    for y in (20, 26, 36, 42, 48):
        p.line([(36 if y < 32 else 16, y), (44, y)], width=1.8)
    p.line([(50, 24), (56, 24), (56, 52), (50, 54)], width=2)


def suitcase(p):
    b = [(10, 22), (54, 22), (54, 54), (10, 54)]
    p.hatch(b, MANGO); p.line(b, True, corner=True)
    p.line([(24, 22), (24, 14), (40, 14), (40, 22)], corner=True)
    p.line([(10, 34), (54, 34)], width=1.8)


def calendar(p):
    b = [(10, 16), (54, 16), (54, 56), (10, 56)]
    p.line(b, True, fill=PAPER, corner=True)
    p.hatch([(10, 16), (54, 16), (54, 26), (10, 26)], TILE)
    p.line([(10, 26), (54, 26)], width=2)
    p.line([(22, 10), (22, 20)], width=2.6); p.line([(42, 10), (42, 20)], width=2.6)
    for i, (x, y) in enumerate([(20, 36), (32, 36), (44, 36), (20, 47), (32, 47)]):
        p.dot(x, y, 2.4, TILE if i == 4 else INK)


def coin(p):
    c = circle(32, 32, 20, 14, p.rng, 0.03)
    p.hatch(c, SUN); p.line(c, True)
    p.line(circle(32, 32, 14, 12, p.rng, 0.03), True, width=1.6)
    p.line([(25, 22), (32, 32), (39, 22)], width=2.2); p.line([(32, 32), (32, 44)], width=2.2)
    p.line([(26, 34), (38, 34)], width=1.8); p.line([(26, 39), (38, 39)], width=1.8)


def car(p):
    body = [(8, 42), (12, 32), (20, 30), (26, 20), (42, 20), (50, 30), (56, 34), (56, 44), (8, 44)]
    p.hatch(body, SEA); p.line(body, True)
    p.line([(28, 24), (40, 24), (44, 30), (24, 30)], True, width=1.8, fill=PAPER)
    for x in (19, 45):
        p.line(circle(x, 45, 6, 9, p.rng, 0.05), True, fill=INK)


def speech(p):
    b = [(10, 14), (54, 14), (54, 40), (30, 40), (20, 52), (21, 40), (10, 40)]
    p.hatch(b, FOAM); p.line(b, True)
    for x in (22, 32, 42):
        p.dot(x, 27, 2.4)


def heart(p):
    c = [(32, 54), (14, 38), (9, 26), (13, 16), (23, 13), (32, 21), (41, 13), (51, 16), (55, 26), (50, 38)]
    p.hatch(c, TILE); p.line(c, True)


def heart_o(p):  # 空心:還沒存的愛心
    c = [(32, 54), (14, 38), (9, 26), (13, 16), (23, 13), (32, 21), (41, 13), (51, 16), (55, 26), (50, 38)]
    p.line(c, True, fill=PAPER)


def compass(p):
    c = circle(32, 32, 22, 14, p.rng, 0.03)
    p.line(c, True, fill=PAPER)
    n = [(32, 14), (37, 32), (27, 32)]
    p.hatch(n, TILE, gap=2.4); p.line(n, True)
    p.line([(27, 32), (32, 50), (37, 32)], True, width=1.8)
    p.dot(32, 32, 2.4)


def menu(p):
    for y in (18, 32, 46):
        p.line([(12, y), (52, y)], width=3)


def close(p):
    p.line([(16, 16), (48, 48)], width=3.2); p.line([(48, 16), (16, 48)], width=3.2)


def warn(p):
    t = [(32, 8), (58, 54), (6, 54)]
    p.hatch(t, MANGO); p.line(t, True, corner=True)
    p.line([(32, 24), (32, 40)], width=3.4); p.dot(32, 47, 2.6)


def pencil(p):
    b = [(14, 50), (44, 14), (52, 22), (22, 56)]
    p.hatch(b, MANGO); p.line(b, True, corner=True)
    p.line([(14, 50), (10, 60), (22, 56)], width=2)


def flower(p):
    for a in range(0, 360, 72):
        r = math.radians(a - 90)
        pts = circle(32 + 12 * math.cos(r), 32 + 12 * math.sin(r), 9, 9, p.rng, 0.08)
        p.hatch(pts, PINK, gap=3); p.line(pts, True)
    p.line(circle(32, 32, 5, 8, p.rng, 0.05), True, fill=SUN)


def leaf(p):
    l1 = [(12, 52), (14, 30), (28, 14), (52, 10), (48, 32), (34, 48)]
    p.hatch(l1, LEAF); p.line(l1, True)
    p.line([(12, 52), (30, 32), (46, 16)], width=1.8)


def food(p):
    bowl = [(7, 31), (57, 31), (52, 45), (42, 53), (22, 53), (12, 45)]
    p.hatch(bowl, MANGO); p.line(bowl, True)
    p.line(wave_pts(14, 50, 27, 1.6, 9), width=1.8)
    p.line([(44, 6), (32, 28)], width=2.2); p.line([(53, 9), (38, 29)], width=2.2)


def drink(p):
    b = [(22, 18), (42, 18), (44, 54), (20, 54)]
    p.hatch(b, SEA, angle=-30); p.line(b, True, corner=True)
    p.line([(24, 30), (40, 30)], width=1.6)
    p.line([(36, 18), (42, 6)], width=2.2)


def festival(p):  # 祭典:Eisa 太鼓
    drum = [(14, 26), (50, 26), (50, 44), (14, 44)]
    p.hatch(drum, TILE); p.line(drum, True)
    p.line(circle(32, 26, 18, 14, p.rng, 0.02)[7:] + circle(32, 26, 18, 14, p.rng, 0.02)[:1], False, width=1.6)
    p.line([(40, 14), (56, 4)], width=2.6); p.line([(24, 14), (8, 4)], width=2.6)


def lantern(p):
    b = [(22, 14), (42, 14), (48, 32), (42, 50), (22, 50), (16, 32)]
    p.hatch(b, TILE); p.line(b, True)
    p.line([(32, 6), (32, 14)], width=2); p.line([(26, 50), (26, 56), (38, 56), (38, 50)], width=2)
    p.line([(18, 26), (46, 26)], width=1.4); p.line([(18, 38), (46, 38)], width=1.4)


def shrine(p):  # 鳥居
    p.hatch([(6, 12), (58, 12), (54, 20), (10, 20)], TILE)
    p.line([(4, 12), (60, 10)], width=3)
    p.line([(10, 22), (54, 22)], width=2.6)
    p.line([(18, 12), (16, 58)], width=3); p.line([(46, 12), (48, 58)], width=3)


def mountain(p):
    m = [(4, 54), (24, 18), (34, 32), (42, 24), (60, 54)]
    p.hatch(m, LEAF); p.line(m, True, corner=True)


def onsen(p):
    bowl = [(10, 40), (54, 40), (48, 54), (16, 54)]
    p.hatch(bowl, SEA); p.line(bowl, True)
    for x in (22, 32, 42):
        p.line([(x, 34), (x - 4, 26), (x + 2, 18), (x - 2, 8)], width=2.2, color=TILE)


def spark(p):  # 沒對到的 emoji 一律用這個
    pts = []
    for i in range(8):
        r = math.radians(i * 45 - 90)
        rr = 24 if i % 2 == 0 else 9
        pts.append((32 + rr * math.cos(r), 32 + rr * math.sin(r)))
    p.hatch(pts, MANGO, gap=2.6); p.line(pts, True)


ICONS = {f.__name__: f for f in [sun, cloud, suncloud, rain, storm, snow, moon, drop, wave, island, turtle, pin, news, suitcase,
                                  calendar, coin, car, speech, heart, heart_o, compass, menu, close, warn, pencil, flower, leaf, food,
                                  drink, festival, lantern, shrine, mountain, onsen, spark]}

# emoji → 圖(不寫的就用 spark)
MAP = {
    "☀": "sun", "🌞": "sun", "🌤": "suncloud", "⛅": "suncloud", "🌥": "suncloud", "🌦": "rain", "☁": "cloud", "🌫": "cloud",
    "🌧": "rain", "☔": "rain", "⛈": "storm", "🌩": "storm", "🌬": "storm", "🌀": "storm", "❄": "snow", "🌨": "snow", "🌙": "moon",
    "💧": "drop", "🌊": "wave", "🏄": "wave", "🤿": "wave", "🪸": "wave", "🏖": "island", "🏝": "island", "🐢": "turtle",
    "📍": "pin", "📰": "news", "📡": "news", "🗾": "news", "📄": "news", "📚": "news", "✉": "news", "🧳": "suitcase", "📦": "suitcase",
    "📅": "calendar", "🗓": "calendar", "💱": "coin", "💰": "coin", "💴": "coin", "💯": "coin", "🚗": "car", "🚌": "car",
    "🗣": "speech", "🔊": "speech", "♡": "heart_o","♥": "heart", "💝": "heart", "❤": "heart", "🧭": "compass", "☰": "menu",
    "✕": "close", "☓": "close", "⚠": "warn", "✎": "pencil", "🎨": "pencil",
    "🌸": "flower", "🌺": "flower", "🌼": "flower", "🌿": "leaf", "🌳": "leaf", "🌾": "leaf", "🍂": "leaf", "🍋": "leaf", "🎋": "leaf", "🎍": "leaf",
    "🍙": "food", "🍔": "food", "🍧": "food", "🫘": "food", "🍠": "food", "🍫": "food", "🌶": "food", "🧂": "food", "🍜": "food",
    "☕": "drink", "🍶": "drink", "🥃": "drink", "🍺": "drink",
    "🥁": "festival", "🎭": "festival", "👹": "festival", "🎎": "festival", "🎃": "lantern", "🏮": "lantern", "🎄": "leaf",
    "⛩": "shrine", "🏯": "shrine", "🙏": "shrine", "🕊": "shrine", "👘": "shrine", "⛰": "mountain", "♨": "onsen",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (name, fn) in enumerate(ICONS.items()):
        p = Pen(500 + i)
        fn(p)
        (OUT / f"{name}.svg").write_text(p.svg(64, 64), encoding="utf-8")
    js = (ROOT / "tools" / "emoji_swap.js").read_text(encoding="utf-8")
    (ROOT / "assets" / "emoji.js").write_text(
        "// tools/emoji_icons.py 產生,不要手改(程式本體在 tools/emoji_swap.js)\n"
        + js.replace("__MAP__", json.dumps(MAP, ensure_ascii=False)), encoding="utf-8")
    print(f"{len(ICONS)} icons, {len(MAP)} emoji")


if __name__ == "__main__":
    main()
