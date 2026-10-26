#!/usr/bin/env python3
"""OkiDayz 品牌素材生成器：鉛筆線稿圖示、紋樣、紅色印章。

規格見 BRAND.md。輸出到 assets/brand/，改這支再重跑，不要手改 SVG。
手繪感靠「座標抖動＋雙描＋斜線排線」做出來，不靠濾鏡，所以放大縮小都一樣。

    python3 tools/brand_assets.py
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
    (OUT / "index.html").write_text(preview_html(), encoding="utf-8")
    print(f"{len(ICONS)} 圖示、{len(PATTERNS)} 紋樣、{len(STAMPS)} 印章 → {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
