#!/usr/bin/env python3
"""OkiDayz 品牌素材生成器：鉛筆線稿圖示、紋樣、紅色印章。

規格見 BRAND.md。輸出到 assets/brand/，改這支再重跑，不要手改 SVG。
手繪感靠「座標抖動＋雙描＋斜線排線」做出來，不靠濾鏡，所以放大縮小都一樣。

    python3 tools/brand_assets.py              # 全部
    python3 tools/brand_assets.py --event-art  # 只出活動保底插畫
"""
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "brand"

PAPER = "#fdfaf4"
TILE = "#d4523a"   # 赤瓦
MANGO = "#f4a72e"  # 芒果
SUN = "#ffd27a"    # 陽光
SEA = "#1a9bb3"    # 海
FOAM = "#d8f1f4"   # 泡
INK = "#2f2420"    # 墨
FONT = "'jf-openhuninn','Huninn','PingFang TC','Noto Sans TC',sans-serif"


# ── 手繪線條 ────────────────────────────────────────────

def f(n):
    return f"{n:.1f}".rstrip("0").rstrip(".")


def jitter(pts, rng, amt):
    return [(x + rng.uniform(-amt, amt), y + rng.uniform(-amt, amt)) for x, y in pts]


def smooth(pts, closed):
    """Catmull-Rom 轉三次貝茲，讓抖過的點連成順手的曲線。"""
    if len(pts) < 3:
        return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    p = pts[:]
    n = len(p)
    d = f"M{f(p[0][0])} {f(p[0][1])}"
    segs = n if closed else n - 1
    for i in range(segs):
        p0 = p[(i - 1) % n] if (closed or i > 0) else p[0]
        p1 = p[i]
        p2 = p[(i + 1) % n]
        p3 = p[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return d + (" Z" if closed else "")


def densify(pts, closed, step=7.0):
    """直線段中間補點，抖動後直線才會微微彎，像手畫。"""
    out = []
    n = len(pts)
    segs = n if closed else n - 1
    for i in range(segs):
        a, b = pts[i], pts[(i + 1) % n]
        k = max(1, int(math.dist(a, b) // step))
        for j in range(k):
            t = j / k
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    if not closed:
        out.append(pts[-1])
    return out


def circle(cx, cy, r, n=12, rng=None, wob=0.0, start=0.0):
    pts = []
    for i in range(n):
        a = start + 2 * math.pi * i / n
        rr = r * (1 + (rng.uniform(-wob, wob) if rng else 0))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


class Pen:
    """一支鉛筆：每條線畫兩次（主線＋錯開的細鬼影線）。"""

    def __init__(self, seed, scale=1.0):
        self.rng = random.Random(seed)
        self.s = scale
        self.clip_n = 0
        self.defs = []
        self.body = []

    def line(self, pts, closed=False, width=2.4, color=INK, fill="none", amt=0.9, corner=False):
        if corner:  # 保留直角：每條邊分開畫，手畫方框本來就是四筆
            n = len(pts)
            for i in range(n if closed else n - 1):
                self.line([pts[i], pts[(i + 1) % n]], False, width, color, "none", amt)
            return
        base = densify(pts, closed, 7 * self.s)
        a = jitter(base, self.rng, amt * self.s)
        b = jitter(base, self.rng, amt * 1.3 * self.s)
        b = [(x + 0.7 * self.s, y + 0.5 * self.s) for x, y in b]
        cap = 'stroke-linecap="round" stroke-linejoin="round"'
        if fill != "none":
            self.body.append(f'<path d="{smooth(a, closed)}" fill="{fill}" stroke="none"/>')
        self.body.append(f'<path d="{smooth(a, closed)}" fill="none" stroke="{color}" stroke-width="{f(width * self.s)}" {cap}/>')
        self.body.append(f'<path d="{smooth(b, closed)}" fill="none" stroke="{color}" stroke-width="{f(width * 0.42 * self.s)}" opacity=".5" {cap}/>')

    def hatch(self, pts, color, angle=38, gap=3.4, width=1.5, closed=True):
        """色鉛筆排線：斜線用 clipPath 裁進形狀，每條線都略彎、長短不一。"""
        self.clip_n += 1
        cid = f"c{self.clip_n}"
        self.defs.append(f'<clipPath id="{cid}"><path d="{smooth(pts, closed)}"/></clipPath>')
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        R = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 4
        a = math.radians(angle)
        ux, uy = math.cos(a), math.sin(a)
        vx, vy = -uy, ux
        lines = []
        g = gap * self.s
        k = -R
        while k <= R:
            o = k + self.rng.uniform(-0.6, 0.6) * self.s
            l0 = -R + self.rng.uniform(0, 3) * self.s
            l1 = R - self.rng.uniform(0, 3) * self.s
            p0 = (cx + vx * o + ux * l0, cy + vy * o + uy * l0)
            p1 = (cx + vx * o + ux * l1, cy + vy * o + uy * l1)
            mid = ((p0[0] + p1[0]) / 2 + self.rng.uniform(-1, 1) * self.s,
                   (p0[1] + p1[1]) / 2 + self.rng.uniform(-1, 1) * self.s)
            lines.append(f"M{f(p0[0])} {f(p0[1])} Q{f(mid[0])} {f(mid[1])} {f(p1[0])} {f(p1[1])}")
            k += g
        self.body.append(
            f'<g clip-path="url(#{cid})" stroke="{color}" stroke-width="{f(width * self.s)}" '
            f'stroke-linecap="round" fill="none" opacity=".85"><path d="{" ".join(lines)}"/></g>')

    def dot(self, x, y, r, color=INK):
        pts = circle(x, y, r, 7, self.rng, 0.15)
        self.body.append(f'<path d="{smooth(pts, True)}" fill="{color}"/>')

    def raw(self, s):
        self.body.append(s)

    def svg(self, w, h):
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
                f"{defs}{''.join(self.body)}</svg>\n")


def wave_pts(x0, x1, y, amp, period, step=3):
    pts = []
    x = x0
    while x <= x1 + 0.01:
        pts.append((x, y - amp * math.sin((x - x0) / period * 2 * math.pi)))
        x += step
    return pts


# ── 圖示（64×64）────────────────────────────────────────

def icon_spot(p):  # 景點：紅瓦屋
    roof = [(5, 31), (16, 16), (48, 16), (59, 31)]
    p.hatch(roof, TILE)
    p.line(roof, True)
    p.line([(12, 31), (12, 55), (52, 55), (52, 31)])
    p.line([(28, 55), (28, 41), (36, 41), (36, 55)])
    p.line([(28, 16), (29, 12), (33, 11), (36, 13), (36, 16)], width=2)  # 屋頂上的風獅爺


def icon_sea(p):  # 海況
    band = wave_pts(6, 58, 34, 4, 17) + [(58, 52), (6, 52)]
    p.hatch(band, SEA, angle=-25)
    p.line(wave_pts(6, 58, 34, 4, 17))
    p.line(wave_pts(12, 52, 46, 3, 14), width=2)
    p.dot(46, 16, 1.6)
    p.line([(18, 20), (22, 16), (26, 20)], width=2)


def icon_weather(p):  # 天氣
    sun = circle(25, 23, 11, 12, p.rng, 0.05)
    p.hatch(sun, MANGO)
    p.line(sun, True)
    for a in range(0, 360, 45):
        r = math.radians(a)
        if 20 < a < 110:
            continue
        p.line([(25 + 15 * math.cos(r), 23 + 15 * math.sin(r)), (25 + 20 * math.cos(r), 23 + 20 * math.sin(r))], width=2)
    cloud = [(20, 50), (19, 42), (26, 37), (33, 39), (38, 32), (48, 33), (53, 40), (57, 46), (52, 52)]
    p.line(cloud, True, fill=PAPER)


def icon_food(p):  # 美食：沖繩麵
    bowl = [(7, 31), (57, 31), (52, 45), (42, 53), (22, 53), (12, 45)]
    p.hatch(bowl, MANGO)
    p.line(bowl, True)
    p.line(wave_pts(14, 50, 27, 1.6, 9), width=1.8)
    p.line([(44, 6), (32, 28)], width=2.2)
    p.line([(53, 9), (38, 29)], width=2.2)


def icon_event(p):  # 活動：票
    stub = [(41, 17), (57, 17), (57, 27), (53, 32), (57, 37), (57, 47), (41, 47)]
    p.hatch(stub, TILE)
    p.line([(7, 17), (57, 17), (57, 27), (53, 32), (57, 37), (57, 47), (7, 47), (7, 37), (11, 32), (7, 27)], True)
    for y in range(20, 46, 5):
        p.line([(41, y), (41, y + 2.5)], width=1.6, amt=0.3)
    p.line([(15, 27), (32, 27)], width=2)
    p.line([(15, 35), (27, 35)], width=2)


def icon_bus(p):  # 交通
    body = [(8, 15), (56, 15), (57, 46), (7, 46)]
    p.hatch([(7, 36), (57, 36), (57, 46), (7, 46)], SEA, angle=-30)
    p.line(body, True)
    p.line([(12, 20), (28, 20), (28, 31), (12, 31)], True, width=2)
    p.line([(33, 20), (52, 20), (52, 31), (33, 31)], True, width=2)
    for x in (18, 46):
        c = circle(x, 49, 5, 9, p.rng, 0.08)
        p.line(c, True, fill=PAPER)


def icon_typhoon(p):  # 颱風
    pts = []
    for i in range(46):
        t = i / 45 * 3.1 * math.pi
        r = 3 + t * 2.6
        pts.append((32 + r * math.cos(t), 32 + r * math.sin(t)))
    p.line(pts, width=2.4, amt=0.5)
    p.dot(32, 32, 3, TILE)


def icon_festival(p):  # 祭典：Eisa 太鼓
    body = [(14, 22), (50, 22), (50, 44), (14, 44)]
    p.hatch(body, TILE)
    top = circle(32, 22, 18, 14, p.rng, 0.03)
    top = [(x, 22 + (y - 22) * 0.32) for x, y in top]
    bot = [(x, y + 22) for x, y in top]
    p.line(top, True, fill=PAPER)
    p.line([(14, 22), (14, 44)])
    p.line([(50, 22), (50, 44)])
    p.line(bot[:8], False)
    p.line([(40, 4), (30, 18)], width=2.2)
    p.line([(56, 8), (44, 19)], width=2.2)


def icon_shop(p):  # 購物
    bag = [(12, 24), (52, 24), (55, 56), (9, 56)]
    p.hatch(bag, MANGO)
    p.line(bag, True)
    p.line([(23, 24), (23, 16), (27, 10), (37, 10), (41, 16), (41, 24)], width=2.2)
    p.dot(23, 30, 1.6)
    p.dot(41, 30, 1.6)


def icon_culture(p):  # 文化：風獅爺
    mane = []
    for i in range(36):
        a = 2 * math.pi * i / 36
        r = 24 + 3.2 * math.sin(a * 9)
        mane.append((32 + r * math.cos(a), 33 + r * math.sin(a)))
    p.hatch(mane, MANGO)
    p.line(mane, True, amt=0.6)
    face = circle(32, 34, 13, 12, p.rng, 0.04)
    p.line(face, True, fill=PAPER)
    p.dot(27, 30, 2)
    p.dot(37, 30, 2)
    p.line([(25, 38), (29, 42), (35, 42), (39, 38)], width=2)
    p.line([(30, 40), (30, 43)], width=1.4, amt=0.2)
    p.line([(34, 40), (34, 43)], width=1.4, amt=0.2)


ICONS = [
    ("spot", "景點", icon_spot), ("sea", "海況", icon_sea), ("weather", "天氣", icon_weather),
    ("food", "美食", icon_food), ("event", "活動", icon_event), ("bus", "交通", icon_bus),
    ("typhoon", "颱風", icon_typhoon), ("festival", "祭典", icon_festival),
    ("shop", "購物", icon_shop), ("culture", "文化", icon_culture),
]


# ── 紋樣（無縫拼貼，96×96）──────────────────────────────

def pattern_tiles(p):  # 赤瓦
    for row, y in enumerate(range(12, 97, 16)):
        off = 0 if row % 2 == 0 else 12
        for x in range(-24 + off, 120, 24):
            pts = [(x + 12 + 12 * math.cos(math.pi * t / 6), y - 9 * math.sin(math.pi * t / 6)) for t in range(7)]
            p.line(pts, width=1.8, color=TILE, amt=0.5)


def pattern_block(p):  # 花ブロック
    for gx in (0, 48):
        for gy in (0, 48):
            sq = [(gx + 4, gy + 4), (gx + 44, gy + 4), (gx + 44, gy + 44), (gx + 4, gy + 44)]
            p.line(sq, True, width=1.6, amt=0.6, corner=True)
            for dx, dy in ((0, -9), (9, 0), (0, 9), (-9, 0)):
                petal = circle(gx + 24 + dx, gy + 24 + dy, 7, 10, p.rng, 0.06)
                p.hatch(petal, MANGO, gap=2.8, width=1.1)
                p.line(petal, True, width=1.4, amt=0.4)


def pattern_wave(p):  # 浪
    for i, y in enumerate(range(8, 96, 16)):
        x0 = -12 if i % 2 else 0
        p.line(wave_pts(x0 - 24, 120, y, 3.2, 24), width=1.8, color=SEA, amt=0.5)


PATTERNS = [("tiles", "赤瓦", pattern_tiles), ("block", "花ブロック", pattern_block), ("wave", "浪", pattern_wave)]


# ── 紅色印章 ────────────────────────────────────────────

STAMP_FILTER = (
    '<filter id="ink" x="-10%" y="-10%" width="120%" height="120%">'
    '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="{seed}" result="n"/>'
    '<feColorMatrix in="n" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2.4 0 0 0 2.05" result="m"/>'
    '<feComposite in="SourceGraphic" in2="m" operator="in" result="t"/>'
    '<feTurbulence type="fractalNoise" baseFrequency="0.06" seed="{seed2}" result="d"/>'
    '<feDisplacementMap in="t" in2="d" scale="3"/></filter>')


def stamp(seed, w, h, shape, lines, rotate):
    p = Pen(seed)
    cx, cy = w / 2, h / 2
    if shape == "circle":
        r = min(w, h) / 2 - 5
        p.line(circle(cx, cy, r, 16, p.rng, 0.02), True, width=3.4, color=TILE, amt=0.4)
        p.line(circle(cx, cy, r - 6, 16, p.rng, 0.02), True, width=1.3, color=TILE, amt=0.3)
    elif shape == "oval":
        pts = [(cx + (w / 2 - 5) * math.cos(a), cy + (h / 2 - 5) * math.sin(a))
               for a in [2 * math.pi * i / 18 for i in range(18)]]
        p.line(pts, True, width=3, color=TILE, amt=0.4)
    else:
        p.line([(5, 5), (w - 5, 5), (w - 5, h - 5), (5, h - 5)], True, width=3, color=TILE, amt=0.5, corner=True)
    n = len(lines)
    for i, (text, size) in enumerate(lines):
        y = cy + (i - (n - 1) / 2) * size * 1.15 + size * 0.36
        p.raw(f'<text x="{f(cx)}" y="{f(y)}" text-anchor="middle" font-family="{FONT}" '
              f'font-size="{size}" font-weight="700" fill="{TILE}" letter-spacing="1">{text}</text>')
    inner = "".join(p.body)
    filt = STAMP_FILTER.format(seed=seed, seed2=seed + 3)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<defs>{filt}</defs><g filter="url(#ink)" transform="rotate({rotate} {f(cx)} {f(cy)})">{inner}</g></svg>\n')


STAMPS = [
    ("this-week", "本週", 21, 120, 120, "circle", [("本週", 26), ("OKIDAYZ", 12)], -8),
    ("weekend", "週末", 22, 150, 64, "rect", [("週末去", 26)], 3),
    ("free", "免費", 23, 130, 76, "oval", [("免費", 28)], -5),
    ("local", "在地推薦", 24, 124, 124, "circle", [("在地", 24), ("推薦", 24)], 6),
    ("rain-ok", "雨天OK", 25, 150, 64, "rect", [("雨天OK", 24)], -3),
    ("date", "日期", 26, 150, 64, "rect", [("11 / 3", 28)], 2),
]


# ── Logo(2026-11-06)──────────────────────────────────
# 圓框裡:芒果太陽從赤瓦屋頂後面升起,下面一條海。42px 也看得出「屋頂＋太陽」。

def logo_mark(p, ink=INK, tile=TILE, mango=MANGO, sea=SEA):
    S = 120
    p.line(circle(60, 60, 54, 28, p.rng, 0.004), True, width=3.2, fill="#fff", amt=0.35, color=ink)
    sun = circle(78, 40, 17, 12, p.rng, 0.03)
    p.hatch(sun, mango, angle=-40, gap=3.2, width=1.7)
    p.line(sun, True, width=2.2, color=ink)
    for k in range(7):  # 光芒
        a = math.radians(-160 + k * 30)
        p.line([(78 + 22 * math.cos(a), 40 + 22 * math.sin(a)), (78 + 29 * math.cos(a), 40 + 29 * math.sin(a))], width=1.8, amt=0.4, color=ink)
    roof = [(22, 66), (38, 48), (82, 48), (98, 66)]
    p.line(roof, True, width=2.6, fill="#fff", corner=True, color=ink)
    p.hatch(densify(roof, True, 3), tile, angle=20, gap=3, width=1.8)
    p.line(roof, True, width=2.6, corner=True, color=ink)
    p.line([(36, 50), (84, 50)], width=1.6, amt=0.4, color=ink)  # 屋脊白漆喰
    for x in (44, 56, 68, 80):  # 瓦溝
        p.line([(x, 51), (x - 6, 64)], width=1.2, amt=0.4, color=ink)
    p.line([(30, 66), (30, 80), (90, 80), (90, 66)], width=2.4, amt=0.5, color=ink)  # 牆
    p.line([(54, 80), (54, 70), (66, 70), (66, 80)], width=2, amt=0.4, color=ink)  # 門
    p.line(wave_pts(18, 102, 90, 2.6, 18, 4), width=2.4, color=sea, amt=0.5)
    p.line(wave_pts(30, 90, 99, 2, 16, 4), width=1.8, color=sea, amt=0.5)
    return S


def logo_mark_mini(p):
    """32px 以下用：同一個構圖，拿掉瓦溝、門、光芒，線加粗、色塊塗滿，16px 還看得出屋頂＋太陽＋海。"""
    S = 120
    p.line(circle(60, 60, 53, 28, p.rng, 0.004), True, width=7, fill="#fff", amt=0.25)
    sun = circle(78, 38, 19, 14, p.rng, 0.02)
    p.raw(f'<path d="{smooth(sun, True)}" fill="{MANGO}"/>')
    p.line(sun, True, width=5, amt=0.25)
    roof = [(20, 66), (37, 47), (83, 47), (100, 66)]
    p.raw(f'<path d="M{" L".join(f"{f(x)} {f(y)}" for x, y in roof)} Z" fill="{TILE}"/>')
    p.line(roof, True, width=5.5, corner=True, amt=0.25)
    p.line([(31, 66), (31, 80), (89, 80), (89, 66)], width=5.5, amt=0.25)
    p.line(wave_pts(18, 102, 93, 3, 20, 4), width=6, color=SEA, amt=0.25)
    return S


# ── 字標(2026-11-22 SS 定案:Caveat 手寫)────────────────
# 「Oki」墨＋「Dayz」赤瓦，Dayz 底下一條陽光色螢光筆。字轉成外框路徑，不靠字型檔。
# Caveat 是 OFL 字型(assets/fonts/OFL-caveat.txt)，轉外框做 logo 可以。

CAVEAT = ROOT / "assets" / "fonts" / "caveat-700.woff2"
WM_SIZE = 100  # 字級(font units → px)，字標 viewBox 以這個為準


def caveat_glyphs(text, size=WM_SIZE):
    """回傳 [(字, path d, 字框)]、總寬。基線 y=0，往上是負。需要 fonttools＋brotli。"""
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    font = TTFont(CAVEAT)
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    k = size / font["head"].unitsPerEm
    x, out = 0.0, []
    for ch in text:
        name = cmap[ord(ch)]
        tr = (k, 0, 0, -k, x, 0)
        sp, bp = SVGPathPen(gs), BoundsPen(gs)
        gs[name].draw(TransformPen(sp, tr))
        gs[name].draw(TransformPen(bp, tr))
        out.append((ch, sp.getCommands(), bp.bounds))
        x += hmtx[name][0] * k
    return out, x


def wordmark_parts(oki=INK, dayz=TILE, marker=SUN, seed=310):
    """字標的 SVG 內容(不含外框)＋邊界 (x0, y0, x1, y1)。marker=None 不畫螢光筆。"""
    glyphs, _w = caveat_glyphs("OkiDayz")
    rng = random.Random(seed)
    body = []
    d0 = glyphs[3][2]
    z1 = glyphs[6][2]
    if marker:  # 螢光筆：一條略斜、邊緣抖動的色帶，畫在 Dayz 後面
        x0, x1 = d0[0] - 4, z1[2] + 3
        top = [(x0 + (x1 - x0) * t, -27 + 2 * t) for t in [i / 10 for i in range(11)]]
        bot = [(x1 - (x1 - x0) * t, -5 + 1.5 * (1 - t)) for t in [i / 10 for i in range(11)]]
        band = jitter(top, rng, 1.2) + jitter(bot, rng, 1.2)
        body.append(f'<path d="{smooth(band, True)}" fill="{marker}"/>')
    for i, (_ch, d, _b) in enumerate(glyphs):
        body.append(f'<path d="{d}" fill="{oki if i < 3 else dayz}"/>')
    xs0 = min(b[0] for _c, _d, b in glyphs)
    ys0 = min(b[1] for _c, _d, b in glyphs)
    xs1 = max(b[2] for _c, _d, b in glyphs)
    ys1 = max(b[3] for _c, _d, b in glyphs)
    return "".join(body), (xs0 - 4, ys0 - 4, xs1 + 5, max(ys1, 0) + 4)


def svg_wrap(inner, box, h=None):
    x0, y0, x1, y1 = box
    w, hh = x1 - x0, y1 - y0
    size = f' width="{f(w)}" height="{f(hh)}"' if h is None else f' width="{f(w * h / hh)}" height="{h}"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(x0)} {f(y0)} {f(w)} {f(hh)}"{size}>'
            f"{inner}</svg>\n")


def nested(svg_text, x, y, w, h):
    """把一張完整 SVG 塞進另一張(nested <svg>)，給組合版用。"""
    head, rest = svg_text.split(">", 1)
    vb = head.split('viewBox="')[1].split('"')[0]
    return f'<svg x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" viewBox="{vb}">{rest.rstrip()}'


# 字標各色版：(檔名, Oki 色, Dayz 色, 螢光筆)
WORDMARKS = [
    ("wordmark", INK, TILE, SUN),        # 標準：亮底
    ("wordmark-rev", "#fff", SUN, None),  # 反白：赤瓦／墨／照片暗處
    ("wordmark-mono", INK, INK, None),    # 單色：墨
    ("wordmark-white", "#fff", "#fff", None),  # 單色：白
]


def logo_files():
    """產生 logo/ 全套 SVG，回傳 {檔名: svg 文字}。"""
    files = {}
    p = Pen(300)
    logo_mark(p)
    files["mark"] = p.svg(120, 120)
    p = Pen(300)
    logo_mark(p, ink=INK, tile=INK, mango=INK, sea=INK)
    files["mark-mono"] = p.svg(120, 120)
    p = Pen(301)
    logo_mark_mini(p)
    files["mark-mini"] = p.svg(120, 120)
    for name, oki, dayz, marker in WORDMARKS:
        inner, box = wordmark_parts(oki, dayz, marker)
        files[name] = svg_wrap(inner, box)
    # 橫式：圓章高 = 字標框高 × 1.25，間距 = 圓章 0.14
    for name, wm in (("lockup", "wordmark"), ("lockup-rev", "wordmark-rev"), ("lockup-mono", "wordmark-mono")):
        _i, (x0, y0, x1, y1) = wordmark_parts()
        wh, ww = y1 - y0, x1 - x0
        m = round(wh * 1.25)
        gap = round(m * 0.14)
        W, H = m + gap + ww, m
        mk = files["mark-mono" if name == "lockup-mono" else "mark"]
        body = nested(mk, 0, 0, m, m) + nested(files[wm], m + gap, (m - wh) / 2 + 2, ww, wh)
        files[name] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(W)} {f(H)}" '
                       f'width="{f(W)}" height="{f(H)}">{body}</svg>\n')
    # 直式：圓章在上，字標寬 = 圓章 1.6 倍
    _i, (x0, y0, x1, y1) = wordmark_parts()
    ww, wh = x1 - x0, y1 - y0
    m = 200
    tw = m * 1.6
    th = tw * wh / ww
    W, H = tw, m + 14 + th
    body = nested(files["mark"], (W - m) / 2, 0, m, m) + nested(files["wordmark"], 0, m + 14, tw, th)
    files["lockup-v"] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(W)} {f(H)}" '
                         f'width="{f(W)}" height="{f(H)}">{body}</svg>\n')
    return files


# PNG:(輸出路徑(相對 ROOT), 來源 svg, 邊長, 底色 None=透明, 圓章佔比)
LOGO_PNGS = [
    ("assets/mark-32.png", "mark-mini", 32, None, 1.0),       # favicon
    ("assets/mark-180.png", "mark", 180, PAPER, 0.92),       # apple-touch-icon(iOS 會把透明變黑，所以墊漆喰白)
    ("assets/mark-512.png", "mark", 512, None, 1.0),         # PWA／大圖示
    ("assets/brand/logo/png/avatar-1080.png", "mark", 1080, PAPER, 1.0),  # IG／Threads 頭像，上傳後圓形裁切剛好落在圓框外
    ("assets/brand/logo/png/mark-1024.png", "mark", 1024, None, 1.0),
]


def chrome_bin():
    import shutil
    for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome"), shutil.which("chromium")):
        if c and Path(c).exists():
            return c
    return None


def export_png(svg_path, out_path, size, bg=None, scale=1.0, width=None):
    """用 headless Chrome 把 SVG 轉 PNG(本機沒有 rsvg/cairo)。width 給了就是寬幅圖，高度照比例。"""
    import subprocess
    import tempfile
    chrome = chrome_bin()
    if not chrome:
        print("  ⚠ 找不到 Chrome，跳過 PNG:", out_path)
        return
    svg = Path(svg_path).read_text(encoding="utf-8")
    vb = [float(v) for v in svg.split('viewBox="')[1].split('"')[0].split()]
    W = width or size
    H = round(W * vb[3] / vb[2]) if width else size
    inner = round(min(W, H) * scale) if not width else W
    page = (f'<!doctype html><html><body style="margin:0;width:{W}px;height:{H}px;display:grid;place-items:center;'
            f'background:{bg or "transparent"}"><img src="file://{svg_path}" style="width:{inner}px;height:auto;display:block">'
            f"</body></html>")
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "p.html"
        html.write_text(page, encoding="utf-8")
        shot = Path(tmp) / "s.png"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--default-background-color=00000000", f"--window-size={W},{H}", "--allow-file-access-from-files",
                        f"--screenshot={shot}", f"file://{html}"], check=True, capture_output=True, timeout=60)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(shot.read_bytes())


# ── Logo 規範頁 ────────────────────────────────────────

def logo_page():
    files = [
        ("lockup.svg", "主 logo 橫式", "網站頁首、輪播收尾、名片、簡報"),
        ("lockup-v.svg", "主 logo 直式", "IG 收尾頁、貼紙、海報置中"),
        ("mark.svg", "圓章", "IG／Threads 頭像、App 圖示、浮水印"),
        ("mark-mini.svg", "圓章簡化版", "32px 以下：favicon、留言頭像"),
        ("wordmark.svg", "字標", "輪播頁腳、版面已經有圓章時"),
        ("lockup-rev.svg / wordmark-rev.svg", "反白", "赤瓦底、墨底、照片暗處"),
        ("mark-mono.svg / wordmark-mono.svg / lockup-mono.svg", "單色墨", "單色印刷、蓋章、燙印、傳真"),
        ("wordmark-white.svg", "單色白", "照片上、只能一色時"),
        ("png/avatar-1080.png", "IG 頭像原檔", "直接上傳 IG／Threads"),
        ("png/lockup-1200.png、png/lockup-v-1000.png、png/wordmark-1200.png、png/mark-1024.png", "PNG", "不能用 SVG 的地方（Canva、簡報、LINE）"),
        ("../../mark-32.png、mark-180.png、mark-512.png", "網站圖示", "favicon、iPhone 主畫面、PWA"),
    ]
    rows = "".join(f"<tr><td><code>{a}</code></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in files)
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OkiDayz Logo 規範</title>
<style>
@font-face{{font-family:"Caveat";src:url(../../fonts/caveat-700.woff2) format("woff2");font-weight:700}}
:root{{--paper:{PAPER};--tile:{TILE};--mango:{MANGO};--sun:{SUN};--sea:{SEA};--foam:{FOAM};--ink:{INK};--line:#eee3d2;--muted:#7a6a5e}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:{FONT};line-height:1.65}}
main{{max-width:1000px;margin:0 auto;padding:40px 16px 80px}}
h1{{font-size:32px;margin:0 0 4px;line-height:1.15}}
h1 mark{{background:linear-gradient(transparent 55%,var(--sun) 55%);color:inherit;padding:0 2px}}
h2{{font-size:19px;margin:48px 0 6px;color:var(--tile)}}
p{{margin:0 0 14px}} .note{{color:var(--muted);font-size:14px}}
code{{font-size:13px;background:#f3ece0;border-radius:4px;padding:1px 5px;word-break:break-all}}
.hero{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:48px 24px;display:grid;place-items:center;margin:24px 0 8px}}
.hero img{{width:min(560px,100%);height:auto}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}}
.tile-box{{border-radius:14px;min-height:170px;display:grid;place-items:center;padding:28px 20px;position:relative;border:1px solid var(--line);overflow:hidden}}
.tile-box img{{max-width:100%;height:auto;position:relative}}
.tile-box .lab{{position:absolute;left:12px;top:8px;font-size:12px;font-weight:700;color:var(--muted);z-index:1}}
.on-dark .lab{{color:rgba(255,255,255,.75)}}
.photo{{background:center/cover}}
.photo::before{{content:"";position:absolute;inset:0;background:linear-gradient(transparent 30%,rgba(47,36,32,.55))}}
.sizes{{display:flex;flex-wrap:wrap;gap:28px;align-items:flex-end;background:#fff;border:1px solid var(--line);border-radius:14px;padding:24px}}
figure{{margin:0;text-align:center}} figcaption{{font-size:12px;color:var(--muted);margin-top:6px}}
.clear{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:40px 20px;display:grid;place-items:center}}
.clear .box{{position:relative;padding:34px;outline:1.5px dashed var(--tile);outline-offset:0}}
.clear .box img{{display:block;width:min(420px,70vw);height:auto}}
.clear .x{{position:absolute;font-size:12px;font-weight:700;color:var(--tile)}}
.av{{display:flex;flex-wrap:wrap;gap:24px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:14px;padding:24px}}
.av img{{border-radius:50%;display:block;box-shadow:0 0 0 1px var(--line)}}
.igp{{display:flex;gap:14px;align-items:center;border:1px solid var(--line);border-radius:12px;padding:12px 16px}}
.igp b{{display:block;font-size:15px}} .igp span{{font-size:12px;color:var(--muted)}}
.dont{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}}
.dont div{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;text-align:center;font-size:13px;overflow:hidden}}
.dont img{{width:130px;height:auto;display:block;margin:6px auto 10px}}
.dont b{{color:var(--tile)}}
table{{width:100%;border-collapse:collapse;font-size:14px;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}}
td{{padding:10px 12px;border-top:1px solid var(--line);vertical-align:top}} td:first-child{{width:42%}} td:nth-child(2){{width:18%;white-space:nowrap}}
@media (max-width:600px){{h1{{font-size:26px}}table,tbody,tr,td{{display:block}}td{{border:0;padding:4px 12px}}tr{{border-top:1px solid var(--line);padding:8px 0}}}}
</style></head><body><main>
<h1>OkiDayz <mark>Logo</mark></h1>
<p class="note">2026-11-22 SS 定案：鉛筆圓章（赤瓦屋頂＋芒果太陽＋海）＋ Caveat 手寫字標。由 <code>tools/brand_assets.py</code> 生成，改生成器再重跑，不要手改 SVG。</p>

<div class="hero"><img src="lockup.svg" alt="OkiDayz"></div>
<p class="note">字標「Oki」墨色、「Dayz」赤瓦色，Dayz 底下一條陽光色螢光筆。字已轉成外框，不需要裝字型。</p>

<h2>1. 版本</h2>
<div class="grid">
  <div class="tile-box" style="background:#fff"><span class="lab">橫式 lockup.svg</span><img src="lockup.svg" alt="" style="width:260px"></div>
  <div class="tile-box" style="background:#fff"><span class="lab">直式 lockup-v.svg</span><img src="lockup-v.svg" alt="" style="width:150px"></div>
  <div class="tile-box" style="background:#fff"><span class="lab">圓章 mark.svg</span><img src="mark.svg" alt="" style="width:120px"></div>
  <div class="tile-box" style="background:#fff"><span class="lab">字標 wordmark.svg</span><img src="wordmark.svg" alt="" style="width:220px"></div>
</div>

<h2>2. 反白與單色</h2>
<p class="note">深底（赤瓦、墨、照片）用反白：字變白、Dayz 變陽光色、拿掉螢光筆；圓章本身有白底，任何底色都直接放。只能印一色時用單色。</p>
<div class="grid">
  <div class="tile-box on-dark" style="background:var(--tile)"><span class="lab">赤瓦底 lockup-rev</span><img src="lockup-rev.svg" alt="" style="width:240px"></div>
  <div class="tile-box on-dark" style="background:var(--ink)"><span class="lab">墨底 lockup-rev</span><img src="lockup-rev.svg" alt="" style="width:240px"></div>
  <div class="tile-box" style="background:#fff"><span class="lab">單色墨 lockup-mono</span><img src="lockup-mono.svg" alt="" style="width:240px"></div>
  <div class="tile-box on-dark" style="background:var(--tile)"><span class="lab">單色白 wordmark-white</span><img src="wordmark-white.svg" alt="" style="width:200px"></div>
</div>

<h2>3. 各種背景</h2>
<div class="grid">
  <div class="tile-box" style="background:var(--paper)"><span class="lab">漆喰白（標準）</span><img src="lockup.svg" alt="" style="width:240px"></div>
  <div class="tile-box" style="background:var(--foam)"><span class="lab">泡（海的頁面）</span><img src="lockup.svg" alt="" style="width:240px"></div>
  <div class="tile-box" style="background:var(--sun)"><span class="lab">陽光底：用單色墨</span><img src="lockup-mono.svg" alt="" style="width:240px"></div>
  <div class="tile-box on-dark photo" style="background-image:url(../../photos/north-coast.jpg)"><span class="lab">照片上：反白放暗處</span><img src="lockup-rev.svg" alt="" style="width:240px;align-self:end"></div>
  <div class="tile-box photo" style="background-image:url(../illustrations/hero-village.png)"><span class="lab">插畫上：只放圓章</span><img src="mark.svg" alt="" style="width:96px;justify-self:end;align-self:end"></div>
  <div class="tile-box on-dark" style="background:var(--sea)"><span class="lab">海色底：反白</span><img src="lockup-rev.svg" alt="" style="width:240px"></div>
</div>

<h2>4. 留白</h2>
<p class="note">四周至少留 <b>x ＝ 圓章直徑的 1/4</b>。這個範圍內不放字、圖、邊框。</p>
<div class="clear"><div class="box"><span class="x" style="left:8px;top:8px">x</span><span class="x" style="right:8px;bottom:8px">x</span><img src="lockup.svg" alt=""></div></div>

<h2>5. 最小尺寸</h2>
<p class="note">螢幕：橫式寬 ≥ 120px、直式寬 ≥ 80px、字標寬 ≥ 72px、圓章 ≥ 24px。<b>32px 以下一律換 mark-mini</b>（拿掉瓦溝、門、光芒，線加粗）。印刷：橫式寬 ≥ 25mm、圓章 ≥ 8mm。</p>
<div class="sizes">
  <figure><img src="lockup.svg" alt="" style="width:120px"><figcaption>橫式 120px（最小）</figcaption></figure>
  <figure><img src="wordmark.svg" alt="" style="width:72px"><figcaption>字標 72px（最小）</figcaption></figure>
  <figure><img src="mark.svg" alt="" style="width:48px"><figcaption>圓章 48px</figcaption></figure>
  <figure><img src="mark.svg" alt="" style="width:24px"><figcaption>圓章 24px（最小）</figcaption></figure>
  <figure><img src="mark-mini.svg" alt="" style="width:32px"><figcaption>mini 32px</figcaption></figure>
  <figure><img src="mark-mini.svg" alt="" style="width:16px"><figcaption>mini 16px</figcaption></figure>
</div>

<h2>6. IG／Threads 頭像</h2>
<p class="note">上傳 <code>png/avatar-1080.png</code>。IG 會裁成圓形，圓章的手繪圓框剛好落在裁切線內側。</p>
<div class="av">
  <figure><img src="png/avatar-1080.png" alt="" width="160" height="160"><figcaption>320 圓形裁切（半尺寸顯示）</figcaption></figure>
  <figure><img src="png/avatar-1080.png" alt="" width="110" height="110"><figcaption>個人頁 110</figcaption></figure>
  <figure><div class="igp"><img src="png/avatar-1080.png" alt="" width="56" height="56"><div><b>okidayz_</b><span>在沖繩，天天都是星期日</span></div></div><figcaption>動態 56</figcaption></figure>
  <figure><img src="png/avatar-1080.png" alt="" width="32" height="32"><figcaption>留言 32</figcaption></figure>
</div>

<h2>7. 不要這樣做</h2>
<div class="dont">
  <div><img src="lockup.svg" alt="" style="transform:scaleX(1.5)"><b>不要拉長壓扁</b></div>
  <div><img src="lockup.svg" alt="" style="filter:hue-rotate(160deg)"><b>不要換色</b>（只有標準／反白／單色三種）</div>
  <div><img src="lockup.svg" alt="" style="filter:drop-shadow(3px 3px 0 #1a9bb3)"><b>不要加陰影、外框</b></div>
  <div><span style="font:900 28px {FONT};display:block;margin:6px 0 10px">OkiDayz</span><b>不要用別的字體重打</b>（用 wordmark.svg）</div>
  <div><img src="lockup.svg" alt="" style="transform:rotate(-12deg)"><b>不要旋轉</b></div>
  <div><span style="display:block;margin:6px 0 10px;font-size:13px">深藍底、魚、彩虹的扁平圓章</span><b>舊圓章已作廢</b>，不要再用</div>
</div>

<h2>8. 檔案</h2>
<table>{rows}</table>
</main></body></html>
"""


# ── 總覽頁 ──────────────────────────────────────────────

def preview_html():
    icons = "".join(
        f'<figure><img src="icons/{k}.svg" alt=""><figcaption>{label}</figcaption></figure>'
        for k, label, _ in ICONS)
    stamps = "".join(
        f'<figure><img src="stamps/{k}.svg" alt="" style="height:{min(h, 96)}px"><figcaption>{label}</figcaption></figure>'
        for k, label, _s, _w, h, *_ in STAMPS)
    pats = "".join(
        f'<figure class="pat"><div style="background-image:url(patterns/{k}.svg)"></div><figcaption>{label}</figcaption></figure>'
        for k, label, _ in PATTERNS)
    ill_dir = OUT / "illustrations"
    ills = "".join(f'<img src="illustrations/{p.name}" alt="">' for p in sorted(ill_dir.glob("*.png"))) if ill_dir.exists() else ""
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OkiDayz 素材</title>
<style>
:root{{--paper:{PAPER};--tile:{TILE};--mango:{MANGO};--sun:{SUN};--sea:{SEA};--foam:{FOAM};--ink:{INK}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:{FONT};padding:32px 20px 60px}}
main{{max-width:960px;margin:0 auto}}
h1{{font-size:30px;margin:0 0 4px;line-height:1.15}}
h1 mark{{background:linear-gradient(transparent 55%,var(--sun) 55%);color:inherit;padding:0 2px}}
h2{{font-size:17px;margin:40px 0 14px;color:var(--tile)}}
p.note{{margin:0;color:#7a6a5e;font-size:14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:14px}}
figure{{margin:0;text-align:center}}
figure img{{height:64px;max-width:100%;display:block;margin:0 auto 6px}}
figcaption{{font-size:13px;color:#7a6a5e}}
.pat div{{height:150px;border-radius:10px;border:1px solid #eee3d2;background-size:96px}}
.pats{{grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}}
.sw{{display:flex;flex-wrap:wrap;gap:8px}}
.sw span{{width:92px;padding:34px 8px 6px;border-radius:8px;font-size:12px}}
.ill{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;align-items:start}}
.ill img{{width:100%;border-radius:10px;border:1px solid #eee3d2}}
.card{{position:relative;max-width:420px;background:#fff;border:1px solid #eee3d2;border-radius:14px;padding:22px 22px 26px;overflow:hidden}}
.card h3{{font-size:24px;margin:0 0 6px;line-height:1.2}}
.card h3 mark{{background:linear-gradient(transparent 55%,var(--sun) 55%);color:inherit}}
.card .row{{display:flex;gap:12px;align-items:center;padding:12px 0;border-top:1px dashed #e4d7c4}}
.card .row img{{height:44px}}
.card .row b{{display:block;font-size:16px}}
.card .row small{{color:#7a6a5e;font-size:13px}}
.card .stamp{{position:absolute;right:14px;top:12px;height:86px}}
.card .band{{height:46px;margin:6px -22px -26px;background:url(patterns/wave.svg) 0 0/96px}}
</style></head><body><main>
<h1>OkiDayz <mark>手繪素材</mark></h1>
<p class="note">鉛筆線稿＋紅色印章。由 tools/brand_assets.py 生成，改生成器再重跑。</p>
<h2>Logo</h2><div class="grid"><figure><img src="logo/lockup.svg" alt="" style="height:72px"><figcaption>lockup.svg</figcaption></figure><figure><img src="logo/mark.svg" alt="" style="height:72px"><figcaption>mark.svg</figcaption></figure></div>
<p class="note">完整規範（各版本、最小尺寸、留白、IG 頭像）：<a href="logo/">logo/</a></p>
<h2>配色</h2>
<div class="sw">
<span style="background:var(--paper);border:1px solid #eee3d2">漆喰白 {PAPER}</span>
<span style="background:var(--tile);color:#fff">赤瓦 {TILE}</span>
<span style="background:var(--mango)">芒果 {MANGO}</span>
<span style="background:var(--sun)">陽光 {SUN}</span>
<span style="background:var(--sea);color:#fff">海 {SEA}</span>
<span style="background:var(--foam)">泡 {FOAM}</span>
<span style="background:var(--ink);color:#fff">墨 {INK}</span>
</div>
<h2>圖示</h2><div class="grid">{icons}</div>
<h2>印章</h2><div class="grid">{stamps}</div>
<h2>紋樣</h2><div class="grid pats">{pats}</div>
<h2>主視覺插畫（Codex 生圖）</h2><div class="ill">{ills}</div>
<h2>用起來的樣子</h2>
<div class="card">
<img class="stamp" src="stamps/this-week.svg" alt="">
<h3>今天，在<mark>沖繩</mark>做什麼？</h3>
<p class="note">住在沖繩的朋友幫你挑好了。</p>
<div class="row"><img src="icons/festival.svg" alt=""><div><b>一萬人太鼓舞</b><small>11/3 · 那霸國際通</small></div></div>
<div class="row"><img src="icons/sea.svg" alt=""><div><b>北谷海況</b><small>浪 0.5m · 適合下水</small></div></div>
<div class="row"><img src="icons/food.svg" alt=""><div><b>新開的沖繩麵店</b><small>浦添 · 在地人排隊</small></div></div>
<div class="band"></div>
</div>
</main></body></html>
"""


# ── 活動保底插畫 ────────────────────────────────────────
# 活動沒有自己的照片時用的 4:3 卡片（首頁「這幾天」、活動頁）。底色淡、中間一個大圖示，
# 圖示直接拿上面生成好的 icons／emoji，不另畫新零件。build.py 的 event_art_key() 決定哪個活動用哪張。

EVENT_ART = [
    # (檔名, 說明, 圖示檔, 底色, 排線色)
    ("festival", "祭典", "icons/festival.svg", "#fdeee6", TILE),
    ("market", "市集", "icons/shop.svg", "#fff4dc", MANGO),
    ("music", "音樂・表演", "emoji/spark.svg", "#fff4dc", MANGO),
    ("light", "燈飾・夜間", "emoji/lantern.svg", "#f3ece4", MANGO),
    ("art", "展覽・工藝", "icons/culture.svg", "#fdeee6", TILE),
    ("sport", "運動・路跑", "emoji/compass.svg", FOAM, SEA),
    ("kids", "親子", "emoji/turtle.svg", FOAM, SEA),
    ("food", "美食", "icons/food.svg", "#fff4dc", MANGO),
    ("sea", "海", "icons/sea.svg", FOAM, SEA),
    ("nature", "花・自然", "emoji/flower.svg", "#fdeee6", TILE),
    ("season", "節氣・傳統", "emoji/moon.svg", "#f3ece4", MANGO),
    ("event", "活動", "icons/event.svg", "#fff4dc", TILE),
]


def event_art(seed, bg, color, icon_svg):
    W, H = 400, 300
    p = Pen(seed)
    p.raw(f'<rect width="{W}" height="{H}" fill="{bg}"/>')
    # 地平線：一條手抖的丘陵／浪，下面排線
    ground = wave_pts(-10, W + 10, 238, 7, 120)
    p.hatch(ground + [(W + 10, H + 10), (-10, H + 10)], color, angle=32, gap=6, width=1.8)
    p.line(ground, width=2.6)
    # 角落的芒果太陽
    sun = circle(332, 62, 26, 12, p.rng, 0.05)
    p.hatch(sun, MANGO, gap=4.5)
    p.line(sun, True)
    # 圖示後面墊一個漆喰白的手繪圓，讓圖示從底色跳出來
    disc = circle(200, 138, 92, 16, p.rng, 0.04)
    p.line(disc, True, width=2.2, fill=PAPER)
    # 圖示自己的 clipPath id 也叫 c1、c2…，換個字首免得跟外層撞名
    icon_svg = icon_svg.replace('id="c', 'id="ic').replace("url(#c", "url(#ic")
    p.raw(nested(icon_svg, 118, 56, 164, 164))
    return p.svg(W, H)


def write_event_art():
    (OUT / "event-art").mkdir(parents=True, exist_ok=True)
    for i, (key, _label, icon, bg, color) in enumerate(EVENT_ART):
        icon_svg = (OUT / icon).read_text(encoding="utf-8")
        (OUT / "event-art" / f"{key}.svg").write_text(event_art(400 + i, bg, color, icon_svg), encoding="utf-8")
    print(f"{len(EVENT_ART)} 張活動保底插畫 → {(OUT / 'event-art').relative_to(ROOT)}/")


def main():
    for sub in ("icons", "patterns", "stamps"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    for i, (key, _label, fn) in enumerate(ICONS):
        p = Pen(100 + i)
        fn(p)
        (OUT / "icons" / f"{key}.svg").write_text(p.svg(64, 64), encoding="utf-8")
    for i, (key, _label, fn) in enumerate(PATTERNS):
        p = Pen(200 + i)
        fn(p)
        (OUT / "patterns" / f"{key}.svg").write_text(p.svg(96, 96), encoding="utf-8")
    for key, _label, seed, w, h, shape, lines, rot in STAMPS:
        (OUT / "stamps" / f"{key}.svg").write_text(stamp(seed, w, h, shape, lines, rot), encoding="utf-8")
    (OUT / "logo").mkdir(parents=True, exist_ok=True)
    for name, svg in logo_files().items():
        (OUT / "logo" / f"{name}.svg").write_text(svg, encoding="utf-8")
    for rel, src, size, bg, scale in LOGO_PNGS:
        export_png(OUT / "logo" / f"{src}.svg", ROOT / rel, size, bg, scale)
    export_png(OUT / "logo" / "lockup.svg", OUT / "logo" / "png" / "lockup-1200.png", 0, None, width=1200)
    export_png(OUT / "logo" / "lockup-v.svg", OUT / "logo" / "png" / "lockup-v-1000.png", 0, None, width=1000)
    export_png(OUT / "logo" / "wordmark.svg", OUT / "logo" / "png" / "wordmark-1200.png", 0, None, width=1200)
    write_event_art()
    (OUT / "logo" / "index.html").write_text(logo_page(), encoding="utf-8")
    (OUT / "index.html").write_text(preview_html(), encoding="utf-8")
    print(f"{len(ICONS)} 圖示、{len(PATTERNS)} 紋樣、{len(STAMPS)} 印章 → {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    import sys
    if "--event-art" in sys.argv:  # 只重出活動插畫，不必跑 Chrome 轉 logo PNG
        write_event_art()
    else:
        main()
