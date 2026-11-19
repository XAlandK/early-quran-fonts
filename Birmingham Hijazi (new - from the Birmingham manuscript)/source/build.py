#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Birmingham Hijazi — build script (version 4.101).

The letterforms are not drawn: they are the outlines of the scribe's ink,
traced by tracer.py from the photograph of the Birmingham Qur'an manuscript
(Cadbury Research Library, Mingana Islamic Arabic 1572a) and, for the nine
forms that do not occur on its two large pages, from the leaves of the same
Qur'an in Paris (BnF Arabe 328, folios 71-86), and stored in traced.json.
This script turns them into a font:

  * every Arabic letter takes its four shapes from the traced forms;
  * a form that is missing from traced.json is assembled from traced pieces
    (see DERIVED below; with the Paris leaves none is missing);
  * a dot is the manuscript's own short slanted dash, traced by dashes.py, at
    the distances it measured; hamzas, vowel signs, digits and punctuation,
    which the manuscript does not have, are drawn with a pen of the same weight;
  * Arabic shaping (init / medi / fina, lam-alef), mark positioning and two
    stylistic sets are added:
        ss01  rasm only: no dots, hamzas or small v's, as in the manuscript
        ss02  hide vowel marks

Usage:  python build.py [output.ttf]
Needs:  fonttools, shapely
"""
import json
import math
import os
import sys

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from shapely import wkt
from shapely.affinity import translate
from shapely.geometry import MultiPoint, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Metrics (font units, UPM 1000).  One manuscript pixel is 1 / 0.225 units.
# --------------------------------------------------------------------------
BL = 40                 # height of the centre of the baseline stroke
STD = 16 / 0.225        # thickness of the joining stroke where two letters meet (tracer.STD)
HS = STD / 2
RX, RY = 46, 33         # pen for the few drawn parts (same weight as the ink)
OVER = 12               # how far a joining stroke runs into its neighbour


# --------------------------------------------------------------------------
# Pen machinery (dots, marks, digits and the reconstructed pieces)
# --------------------------------------------------------------------------
def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return tuple(
        0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2
               + (-a + 3 * b - 3 * c + d) * t3)
        for a, b, c, d in zip(p0, p1, p2, p3))


def spline(pts, closed=False, step=5.0):
    """Catmull-Rom curve through pts, sampled every ~step units."""
    pts = [(float(x), float(y)) for x, y in pts]
    n = len(pts)
    if n == 1:
        return pts
    if closed:
        P = [pts[-1]] + pts + [pts[0], pts[1]]
        segs = range(1, n + 1)
    else:
        P = [pts[0]] + pts + [pts[-1]]
        segs = range(1, n)
    out = []
    for i in segs:
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        k = max(1, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        out.extend(_cr(p0, p1, p2, p3, j / k) for j in range(k))
    out.append(P[segs[-1] + 1])
    return out


_NIBS = {}


def _nib(rx, ry, n=20):
    key = (rx, ry, n)
    if key not in _NIBS:
        _NIBS[key] = [(rx * math.cos(2 * math.pi * k / n), ry * math.sin(2 * math.pi * k / n))
                      for k in range(n)]
    return _NIBS[key]


def sweep(path, rx, ry, w0=1.0, w1=None):
    """Area covered by an elliptical nib dragged along path (scale w0 -> w1)."""
    w1 = w0 if w1 is None else w1
    base = _nib(rx, ry)
    N = len(path)
    hulls, prev = [], None
    for i, (x, y) in enumerate(path):
        s = w0 + (w1 - w0) * (i / (N - 1) if N > 1 else 0.0)
        cur = [(x + s * a, y + s * b) for a, b in base]
        hulls.append(MultiPoint(cur + (prev or [])).convex_hull)
        prev = cur
    return unary_union(hulls)


class G:
    """A glyph: advance width, ink, and where dots above / below it sit."""

    def __init__(self, adv, geom=None):
        self.adv = adv
        self.parts = [geom] if geom is not None else []
        self.above = (adv / 2, 300)
        self.below = (adv / 2, -60)

    def s(self, pts, w=1.0, w1=None, closed=False, rx=RX, ry=RY):
        self.parts.append(sweep(spline(pts, closed), rx, ry, w, w1))
        return self

    def geom(self):
        parts = [p for p in self.parts if p is not None and not p.is_empty]
        return unary_union(parts) if parts else None

    def copy(self):
        g = G(self.adv)
        g.parts = list(self.parts)
        g.above, g.below = self.above, self.below
        return g


# --------------------------------------------------------------------------
# The traced letterforms
# --------------------------------------------------------------------------
with open(os.path.join(HERE, 'traced.json'), encoding='utf-8') as fh:
    _RAW = json.load(fh)
TRACED = {k: (v['adv'], wkt.loads(v['wkt'])) for k, v in _RAW.items() if not k.startswith('_')}


def join_box(x, side):
    """The exact end every joining stroke is given, so that neighbours meet without a seam."""
    if side == 'r':
        return box(x - 14, BL - HS, x + OVER, BL + HS)
    return box(-OVER, BL - HS, 14, BL + HS)


def traced(key):
    adv, geom = TRACED[key]
    form = key.split('.')[1]
    parts = [geom]
    if form in ('medi', 'fina'):
        parts.append(join_box(adv, 'r'))
    if form in ('init', 'medi'):
        parts.append(join_box(0, 'l'))
    return adv, unary_union(parts)


def band_extent(geom, side, half=38):
    """Right- or leftmost x of the ink that lies on the baseline."""
    b = geom.intersection(box(-5000, BL - half, 5000, BL + half)).bounds
    return b[2] if side == 'r' else b[0]


def strip_right(key, cut, bearing=80):
    """A form that joined on the right, with its joining stroke taken away."""
    adv, geom = TRACED[key]
    geom = geom.difference(box(cut, BL - 60, adv + 60, BL + 60))
    geom = unary_union([geom, sweep([(cut - 2, BL)], RY + 1, HS)])     # a rounded end
    right = max(band_extent(geom, 'r'), cut) + bearing
    return right, geom


def add_right_join(key, reach=70):
    """A free-standing form given a joining stroke on its right."""
    adv, geom = TRACED[key]
    xr = band_extent(geom, 'r', half=30)
    new_adv = xr + reach
    geom = unary_union([geom, box(xr - 45, BL - HS, new_adv + OVER, BL + HS)])
    return new_adv, geom


def add_left_tail(key, pts, hook=None):
    """A medial form followed by a drawn tail that runs on to the left."""
    adv, geom = traced(key)
    tail = sweep(spline(pts), RY + 2, HS)
    L = -min(x for x, _ in pts) + 40
    geom = translate(unary_union([geom, tail]), L, 0)
    return adv + L, geom


FLAT_TAIL = [(20, BL), (-200, BL), (-420, BL - 2), (-560, BL - 6), (-640, BL - 12)]
JIM_TAIL = [(20, BL), (-260, BL), (-470, BL - 2), (-540, BL - 14), (-566, BL - 52), (-548, BL - 92),
            (-500, BL - 108)]


def _derived():
    """Forms assembled from traced pieces.  Since the Paris leaves of the manuscript were
    added, all nine are traced from the ink like the rest; these are only made for a form
    that is missing from traced.json (for instance when the Paris pictures have not been
    downloaded and tracer.py was run without them)."""
    d = {}
    make = {
        # mim on its own: the final form without the stroke that joined it
        'MEEM.isol': lambda: strip_right('MEEM.fina', TRACED['MEEM.fina'][0] - 62),
        'QAF.isol': lambda: strip_right('QAF.fina', TRACED['QAF.fina'][0] - 30),
        'AIN.isol': lambda: strip_right('AIN.fina', TRACED['AIN.fina'][0] - 70),
        # sad and ta' at the end of a word: the free-standing form, joined
        'SAD.fina': lambda: add_right_join('SAD.isol'),
        'TAH.fina': lambda: add_right_join('TAH.isol'),
        # fa' at the end of a word: its loop, then the flat tail the scribe gives ba'
        'FEH.fina': lambda: add_left_tail('FEH.medi', FLAT_TAIL),
        'FEH.isol': lambda: add_left_tail('FEH.init', FLAT_TAIL),
        # jim / ha' / kha' at the end of a word: the head of the initial form on a long
        # stroke that runs on to the left and ends in a small downward hook
        'HAH.fina': lambda: add_left_tail('HAH.medi', JIM_TAIL),
        'HAH.isol': lambda: add_left_tail('HAH.init', JIM_TAIL),
    }
    for key, fn in make.items():
        if key not in TRACED:
            d[key] = fn()
    return d


DERIVED = _derived()


def shape(name, form):
    key = '%s.%s' % (name, form)
    if key in TRACED:
        adv, geom = traced(key)
    elif key in DERIVED:
        adv, geom = DERIVED[key]
    else:
        raise KeyError(key)
    g = G(adv, geom)
    g.above = ANCHOR_ABOVE.get(key) or auto_anchor(geom, adv, 'above', loop_only=(name == 'TAH'))
    g.below = ANCHOR_BELOW.get(key) or auto_anchor(geom, adv, 'below')
    return g


def auto_anchor(geom, adv, where, loop_only=False):
    """Where the dot nearest the letter sits (centre of the dash)."""
    win = geom.intersection(box(-30, -3000, adv + 30, 3000))
    if win.is_empty:
        win = geom
    if where == 'above' and loop_only:                     # za': over the loop, beside the stem
        body = win.intersection(box(-9999, -9999, 9999, BL + 150))
        cx = body.bounds[2] - 150
        col = body.intersection(box(cx - 50, -9999, cx + 50, 9999))
        return (cx, (col.bounds[3] if not col.is_empty else body.bounds[3]) + 64)
    if where == 'above':
        up = win.intersection(box(-9999, BL + 34, 9999, 9999))
        base = up if (not up.is_empty and up.area > 900) else win
        if base.bounds[3] - BL > 430:                      # a tall stem: sit on its top
            top = base.intersection(box(-9999, base.bounds[3] - 60, 9999, 9999))
            return (top.centroid.x - 6, base.bounds[3] + 64)
        cx = base.centroid.x
        col = geom.intersection(box(cx - 50, -9999, cx + 50, 9999))
        return (cx, (col.bounds[3] if not col.is_empty else base.bounds[3]) + 64)
    lo = win.intersection(box(-9999, -9999, 9999, BL + 46))
    base = lo if not lo.is_empty else win
    cx = base.centroid.x
    col = geom.intersection(box(cx - 50, -9999, cx + 50, 9999))
    return (cx, (col.bounds[1] if not col.is_empty else base.bounds[1]) - 64)


# Dot positions the automatic rule gets wrong (font units).
ANCHOR_ABOVE = {}
ANCHOR_BELOW = {}


# --------------------------------------------------------------------------
# Small marks: i'jam dashes, hamza, madda, v, wasla
# --------------------------------------------------------------------------
DRX, DRY = 15, 13        # nib for the marks the manuscript does not have
PXU = 0.225              # manuscript pixels per font unit (tracer.PXU)

# The dot of the manuscript is a short slanted dash.  dashes.py measures the dashes that
# stand free on the two Birmingham pages and traces the one nearest to their median
# length, thickness and slant; the distances are the medians it measured.
with open(os.path.join(HERE, 'dash.json'), encoding='utf-8') as fh:
    _DASH = json.load(fh)
DASH_GEOM = wkt.loads(_DASH['wkt'])
_mid = DASH_GEOM.intersection(box(-4, -999, 4, 999)).bounds
DSTEP = _DASH['stack_down'] / PXU                 # from one dash of a letter to the next
DSHIFT = _DASH['stack_right'] / PXU               # ... the lower one stands this far to the right
DOT_OFF = _DASH['gap'] / PXU + (_mid[3] - _mid[1]) / 2 - 64   # the nearest dash, beyond the anchor of the letter


def dash(g, cx, cy):
    g.parts.append(translate(DASH_GEOM, cx, cy))
    return g


def dots(g, n, where, pos=None):
    """The manuscript writes dots as short slanted dashes, stacked one over the other."""
    cx, cy = pos or (g.above if where == 'above' else g.below)
    d = 1 if where == 'above' else -1
    for i in range(n):
        dash(g, cx - d * i * DSHIFT, cy + d * (DOT_OFF + i * DSTEP))


def vmark(g, cx, cy):
    """Kurdish small v; cy is the centre of the mark."""
    g.s([(cx - 30, cy + 22), (cx, cy - 20)], rx=DRX - 2, ry=DRY - 2)
    g.s([(cx, cy - 20), (cx + 30, cy + 22)], rx=DRX - 2, ry=DRY - 2)


def hamza(g, cx, cy, sc=1.0, rx=DRX - 2, ry=DRY - 2):
    """Small hamza; cy is the bottom of the mark."""
    P = lambda x, y: (cx + x * sc, cy + y * sc)
    g.s([P(28, 58), P(4, 70), P(-17, 54), P(-7, 33), P(24, 28)], rx=rx, ry=ry)
    g.s([P(24, 28), P(-28, 2)], rx=rx, ry=ry)


def madda(g, cx, cy):
    g.s([(cx - 56, cy + 2), (cx - 28, cy + 26), (cx, cy + 12), (cx + 28, cy - 2), (cx + 56, cy + 18)],
        rx=DRX - 2, ry=DRY - 2)


def wasla(g, cx, cy):
    g.s([(cx - 46, cy + 6), (cx - 30, cy + 34), (cx + 12, cy + 42), (cx + 34, cy + 26),
         (cx + 14, cy + 9), (cx - 46, cy + 6)], rx=DRX - 3, ry=DRY - 3)


def gaf_stroke(g):
    """Kurdish / Persian gaf: a second stroke laid alongside the arm of kaf."""
    geom = g.geom()
    top = geom.bounds[3]
    arm = geom.intersection(box(-9999, BL + 0.42 * (top - BL), 9999, 9999))
    if arm.geom_type != 'Polygon':
        arm = max(arm.geoms, key=lambda p: p.area)
    c = list(arm.minimum_rotated_rectangle.exterior.coords)[:4]
    e = [(c[i], c[(i + 1) % 4]) for i in range(4)]
    (p, q) = max(e, key=lambda s: math.hypot(s[1][0] - s[0][0], s[1][1] - s[0][1]))
    if q[1] < p[1]:
        p, q = q, p
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
    nx, ny = -uy, ux                                   # up and to the left of the arm
    cx, cy = arm.centroid.x, arm.centroid.y
    off = 118
    a = (cx + nx * off - ux * 0.36 * L, cy + ny * off - uy * 0.36 * L)
    b = (cx + nx * off + ux * 0.46 * L, cy + ny * off + uy * 0.46 * L)
    g.s([a, b], 1.0, 0.75, rx=30, ry=26)


def apply_marks(g, marks):
    for m in marks:
        kind = m[0]
        if kind == "dots":
            dots(g, m[1], m[2])
        elif kind == "hamza":
            if m[1] == "above":
                hamza(g, g.above[0], g.above[1] - 22)
            else:
                hamza(g, g.below[0], g.below[1] - 50)
        elif kind == "v":
            if m[1] == "above":
                vmark(g, g.above[0], g.above[1] + 6)
            else:
                vmark(g, g.below[0], g.below[1] - 6)
        elif kind == "madda":
            madda(g, g.above[0], g.above[1] - 12)
        elif kind == "wasla":
            wasla(g, g.above[0], g.above[1] - 18)
        elif kind == "gaf":
            gaf_stroke(g)


# --------------------------------------------------------------------------
# Letters: (codepoint, joining, form for init/medi, marks,
#           form for fina/isol, marks for fina/isol)
# --------------------------------------------------------------------------
D1a, D2a, D3a = ("dots", 1, "above"), ("dots", 2, "above"), ("dots", 3, "above")
D1b, D2b, D3b = ("dots", 1, "below"), ("dots", 2, "below"), ("dots", 3, "below")
HZa, HZb = ("hamza", "above"), ("hamza", "below")
Va, Vb = ("v", "above"), ("v", "below")
GF = ("gaf",)

LETTERS = []


def L(cp, join, skel, marks=(), skel_f=None, marks_f=None):
    LETTERS.append((cp, join, skel, list(marks), skel_f or skel,
                    list(marks if marks_f is None else marks_f)))


L(0x0627, "R", "ALIF")
L(0x0622, "R", "ALIF", [("madda",)])
L(0x0623, "R", "ALIF", [HZa])
L(0x0625, "R", "ALIF", [HZb])
L(0x0671, "R", "ALIF", [("wasla",)])
L(0x0628, "D", "BEH", [D1b])
L(0x062A, "D", "BEH", [D2a])
L(0x062B, "D", "BEH", [D3a])
L(0x067E, "D", "BEH", [D3b])
L(0x066E, "D", "BEH")
L(0x0646, "D", "BEH", [D1a], "NOON", [D1a])
L(0x06BA, "D", "BEH", [], "NOON", [])
L(0x064A, "D", "BEH", [D2b], "YEH", [D2b])
L(0x0649, "D", "BEH", [], "YEH", [])
L(0x06CC, "D", "BEH", [D2b], "YEH", [])
L(0x06CE, "D", "BEH", [D2b, Va], "YEH", [Va])
L(0x0626, "D", "BEH", [HZa], "YEH", [HZa])
L(0x062C, "D", "HAH", [D1b])
L(0x062D, "D", "HAH")
L(0x062E, "D", "HAH", [D1a])
L(0x0686, "D", "HAH", [D3b])
L(0x062F, "R", "DAL")
L(0x0630, "R", "DAL", [D1a])
L(0x0631, "R", "REH")
L(0x0632, "R", "REH", [D1a])
L(0x0698, "R", "REH", [D3a])
L(0x0695, "R", "REH", [Vb])
L(0x0633, "D", "SEEN")
L(0x0634, "D", "SEEN", [D3a])
L(0x0635, "D", "SAD")
L(0x0636, "D", "SAD", [D1a])
L(0x0637, "D", "TAH")
L(0x0638, "D", "TAH", [D1a])
L(0x0639, "D", "AIN")
L(0x063A, "D", "AIN", [D1a])
L(0x0641, "D", "FEH", [D1a])
L(0x06A1, "D", "FEH")
L(0x06A4, "D", "FEH", [D3a])
L(0x0642, "D", "QAF", [D2a])
L(0x066F, "D", "QAF")
L(0x0643, "D", "KAF")
L(0x06A9, "D", "KAF")
L(0x06AF, "D", "KAF", [GF])
L(0x0644, "D", "LAM")
L(0x06B5, "D", "LAM", [Va])
L(0x0645, "D", "MEEM")
L(0x0647, "D", "HEH")
L(0x06BE, "D", "HEH")
L(0x06D5, "R", "HEH")
L(0x0629, "R", "HEH", [D2a])
L(0x0648, "R", "WAW")
L(0x06C6, "R", "WAW", [Va])
L(0x0624, "R", "WAW", [HZa])

LAMALEF_VARIANTS = [  # alef codepoint, marks on the ligature
    (0x0627, []), (0x0622, [("madda",)]), (0x0623, [HZa]), (0x0625, [HZb]), (0x0671, [("wasla",)]),
]


# --------------------------------------------------------------------------
# Other glyphs (none of these occur in the manuscript; drawn at its weight)
# --------------------------------------------------------------------------
def g_tatweel():
    g = G(150)
    g.parts.append(box(-OVER, BL - HS, 150 + OVER, BL + HS))
    return g


def g_hamza():
    g = G(170)
    hamza(g, 88, 34, 1.7, rx=24, ry=20)
    return g


def g_verse_end():
    """Cluster of slanted dashes that closes a verse in the manuscript."""
    down, right, beside = (_DASH[k] / PXU for k in ('verse_down', 'verse_right', 'verse_beside'))
    g = G(round(beside + 220))
    for i in range(2):                              # two columns of three, as most of them are
        for j in range(3):
            dash(g, 110 + i * beside - (j - 1) * right, 40 + down + (j - 1) * down + i * 14)
    return g


def g_period():
    g = G(200)
    dash(g, 100, 40)
    return g


def g_comma():
    g = G(190)
    g.s([(90, 46), (84, 84), (98, 128), (130, 158)], 1.0, 0.6, rx=24, ry=20)
    return g


def g_semicolon():
    g = G(190)
    g.s([(90, 190), (84, 226), (98, 270), (130, 300)], 1.0, 0.6, rx=24, ry=20)
    dash(g, 98, 52)
    return g


def g_question():
    g = G(290)
    g.s([(216, 340), (184, 396), (116, 380), (106, 312), (164, 264), (166, 176)], rx=30, ry=24)
    dash(g, 166, 52)
    return g


def circle(cx, cy, r, n=8, ry=None):
    ry = r if ry is None else ry
    return [(cx + r * math.cos(2 * math.pi * k / n - math.pi / 2),
             cy + ry * math.sin(2 * math.pi * k / n - math.pi / 2)) for k in range(n)]


def lean(x, y0, y1, sl):
    return (x + sl * (y1 - y0), y1)


DSL = 0.2
DR = dict(rx=RX * 0.8, ry=RY * 0.8)


def g_digit(d):
    g = G(320)
    if d == 0:
        g.s(circle(160, 150, 14, n=6), closed=True, rx=24, ry=22)
    elif d == 1:
        g.s([(136, 20), lean(136, 20, 400, DSL)], **DR)
    elif d == 2:
        g.s([(132, 20), lean(132, 20, 350, DSL)], **DR)
        g.s([lean(132, 20, 350, DSL), (212, 318), (252, 392)], **DR)
    elif d == 3:
        g.s([(116, 20), lean(116, 20, 350, DSL)], **DR)
        g.s([lean(116, 20, 350, DSL), (182, 312), (202, 380)], **DR)
        g.s([(202, 380), (232, 312), (266, 388)], **DR)
    elif d == 4:
        g.s([(236, 392), (170, 376), (142, 322), (188, 276), (228, 270), (156, 244), (114, 168),
             (142, 76), (240, 46)], **DR)
    elif d == 5:
        g.s([(160, 30), (224, 72), (234, 178), (182, 304), (160, 346), (138, 304), (86, 178),
             (96, 72)], closed=True, **DR)
    elif d == 6:
        g.s([(88, 336), (148, 364), (208, 382), (194, 210), (170, 20)], **DR)
    elif d == 7:
        g.s([(80, 392), (160, 42)], **DR)
        g.s([(160, 42), (246, 392)], **DR)
    elif d == 8:
        g.s([(76, 30), (160, 382)], **DR)
        g.s([(160, 382), (242, 30)], **DR)
    elif d == 9:
        g.s(circle(134, 300, 58, n=8), closed=True, **DR)
        g.s([(192, 304), (188, 190), (170, 20)], **DR)
    return g


# Vowel and Qur'anic marks: drawn around x = 0; top marks rest on y = 0,
# bottom marks hang from y = 0.
MRX, MRY = 15, 12


def mk(fn):
    g = G(0)
    fn(g)
    return g


def _fatha(g, dy=0):
    g.s([(-36, 12 + dy), (36, 42 + dy)], rx=MRX, ry=MRY)


def _kasra(g, dy=0):
    g.s([(-36, -42 + dy), (36, -12 + dy)], rx=MRX, ry=MRY)


def _damma(g, dx=0):
    g.s(circle(6 + dx, 64, 17), closed=True, rx=MRX - 3, ry=MRY - 3)
    g.s([(-8 + dx, 50), (-20 + dx, 22), (-38 + dx, 8)], rx=MRX - 3, ry=MRY - 3)


MARKS_TOP = {
    0x064E: lambda g: _fatha(g),
    0x064B: lambda g: (_fatha(g), _fatha(g, 44)),
    0x064F: lambda g: _damma(g),
    0x064C: lambda g: (_damma(g, -24), _damma(g, 26)),
    0x0651: lambda g: g.s([(-46, 52), (-30, 10), (-2, 40), (20, 10), (44, 52)], rx=MRX - 2, ry=MRY - 2),
    0x0652: lambda g: g.s(circle(0, 30, 18), closed=True, rx=MRX - 4, ry=MRY - 4),
    0x06E1: lambda g: g.s([(-32, 32), (-18, 56), (14, 58), (30, 32)], rx=MRX - 4, ry=MRY - 4),
    0x0670: lambda g: g.s([(-8, 12), (16, 108)], rx=MRX, ry=MRY),
    0x0653: lambda g: madda(g, 0, 12),
    0x0654: lambda g: hamza(g, 0, 8),
}
MARKS_BOTTOM = {
    0x0650: lambda g: _kasra(g),
    0x064D: lambda g: (_kasra(g), _kasra(g, -44)),
    0x0655: lambda g: hamza(g, 0, -74),
}
# Qur'anic annotation signs the manuscript does not have: kept as empty marks.
MARKS_EMPTY = (list(range(0x0610, 0x061B)) + list(range(0x0656, 0x0660)) +
               list(range(0x06D6, 0x06DD)) + [0x06DF, 0x06E0] + list(range(0x06E2, 0x06E9)) +
               list(range(0x06EA, 0x06EE)))


# --------------------------------------------------------------------------
# Outline conversion
# --------------------------------------------------------------------------
def _densify(pts, maxlen=14.0):
    out = []
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        out.append((x0, y0))
        d = math.hypot(x1 - x0, y1 - y0)
        k = int(d // maxlen)
        for j in range(1, k + 1):
            t = j / (k + 1)
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def to_glyph(geom):
    """Polygon(s) -> TrueType glyph made of smooth quadratic contours."""
    pen = TTGlyphPen(None)
    if geom is None or geom.is_empty:
        return pen.glyph(), 0
    geom = geom.buffer(0)
    polys = [geom] if geom.geom_type == "Polygon" else [p for p in geom.geoms if p.geom_type == "Polygon"]
    xmin = None
    for p in polys:
        p = orient(p.simplify(0.7, preserve_topology=True), sign=-1.0)
        for ring in [p.exterior] + list(p.interiors):
            pts = _densify(list(ring.coords)[:-1])
            # The curve of the font runs through the mid-points of its control points and so
            # cuts every bend a little short.  Move each control point outwards by what the
            # curve will cut, so that the curve lies on the traced outline.
            m = len(pts)
            pts = [(pts[i][0] - (pts[i - 1][0] - 2 * pts[i][0] + pts[(i + 1) % m][0]) / 8,
                    pts[i][1] - (pts[i - 1][1] - 2 * pts[i][1] + pts[(i + 1) % m][1]) / 8) for i in range(m)]
            pts = [(round(x), round(y)) for x, y in pts]
            clean = [pt for i, pt in enumerate(pts) if pt != pts[i - 1]]
            if len(clean) < 3:
                continue
            xmin = min([xmin] + [x for x, _ in clean]) if xmin is not None else min(x for x, _ in clean)
            # every polygon vertex becomes a quadratic control point; the on-curve
            # points between them are written out explicitly for compatibility
            n = len(clean)
            mids = [((clean[i - 1][0] + clean[i][0]) / 2, (clean[i - 1][1] + clean[i][1]) / 2)
                    for i in range(n)]
            mids = [(round(x), round(y)) for x, y in mids]
            pen.moveTo(mids[0])
            for i in range(n):
                pen.qCurveTo(clean[i], mids[(i + 1) % n])
            pen.closePath()
    return pen.glyph(), (xmin or 0)


def anchors(geom, adv):
    """Top and bottom attachment points for vowel marks."""
    if geom is None or geom.is_empty:
        return (adv / 2, 300), (adv / 2, -100)
    lo, hi = (-10, adv + 10) if adv > 0 else (-200, 200)
    clip = geom.intersection(Polygon([(lo, -3000), (hi, -3000), (hi, 3000), (lo, 3000)]))
    if clip.is_empty:
        clip = geom
    pts = []
    for p in ([clip] if clip.geom_type == "Polygon" else list(getattr(clip, "geoms", []))):
        if p.geom_type == "Polygon":
            pts += list(p.exterior.coords)
    ymax = max(y for _, y in pts)
    ymin = min(y for _, y in pts)
    top = [x for x, y in pts if y > ymax - 70]
    bot = [x for x, y in pts if y < ymin + 50]
    tx = sum(top) / len(top)
    bx = sum(bot) / len(bot)
    return (round(tx), round(ymax + 64)), (round(bx), round(ymin - 54))


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
FORMS_D = ["isol", "init", "medi", "fina"]
FORMS_R = ["isol", "fina"]


def gname(cp, form="isol"):
    base = "uni%04X" % cp
    return base if form == "isol" else base + "." + form


def build(out_path):
    glyphs = {}     # name -> G
    order = [".notdef", "space", "nbspace", "zwnj", "zwj", "lrm", "rlm"]
    cmap = {0x20: "space", 0xA0: "nbspace", 0x200C: "zwnj", 0x200D: "zwj", 0x200E: "lrm", 0x200F: "rlm"}
    for n, w in (("space", 140), ("nbspace", 140), ("zwnj", 0), ("zwj", 0), ("lrm", 0), ("rlm", 0)):
        glyphs[n] = G(w)
    nd = G(500)
    nd.s([(80, 0), (420, 0), (420, 650), (80, 650), (80, 0)], rx=20, ry=20)
    glyphs[".notdef"] = nd

    cache = {}

    def base(name, form):
        if (name, form) not in cache:
            cache[(name, form)] = shape(name, form)
        return cache[(name, form)]

    def make(name, form, marks):
        g = base(name, form).copy()
        apply_marks(g, marks)
        return g

    rasm = {}       # glyph name -> undotted glyph name (for ss01)
    init_sub, medi_sub, fina_sub = [], [], []

    for cp, join, sk, marks, sk_f, marks_f in LETTERS:
        forms = FORMS_D if join == "D" else FORMS_R
        for f in forms:
            s_name, m = (sk_f, marks_f) if f in ("isol", "fina") else (sk, marks)
            n = gname(cp, f)
            glyphs[n] = make(s_name, f, m)
            order.append(n)
            plain = [x for x in m if x[0] == "gaf"]
            if m and m != plain:
                sn = "sk.%s%s.%s" % (s_name, "G" if plain else "", f)
                if sn not in glyphs:
                    glyphs[sn] = make(s_name, f, plain)
                rasm[n] = sn
            if f == "init":
                init_sub.append(n)
            elif f == "medi":
                medi_sub.append(n)
            elif f == "fina":
                fina_sub.append(n)
        cmap[cp] = gname(cp)

    for n in sorted(k for k in glyphs if k.startswith("sk.")):
        order.append(n)

    # lam-alef ligatures
    lig_rules = []
    for acp, marks in LAMALEF_VARIANTS:
        for f in ("isol", "fina"):
            n = "lam_alef%s%s" % ("" if acp == 0x0627 else "_%04X" % acp, "" if f == "isol" else ".fina")
            glyphs[n] = make("LAMALEF", f, marks)
            order.append(n)
            lam = gname(0x0644, "init" if f == "isol" else "medi")
            lig_rules.append((lam, gname(acp, "fina"), n))
            if marks:
                rasm[n] = "lam_alef" + ("" if f == "isol" else ".fina")

    # other spacing glyphs
    extra = {
        0x0640: g_tatweel(), 0x0621: g_hamza(), 0x06D4: g_verse_end(), 0x002E: g_period(),
        0x060C: g_comma(), 0x061B: g_semicolon(), 0x061F: g_question(),
    }
    for d in range(10):
        extra[0x0660 + d] = g_digit(d)
    for cp, g in extra.items():
        n = gname(cp)
        glyphs[n] = g
        order.append(n)
        cmap[cp] = n
    for d in (0, 1, 2, 3, 7, 8, 9):   # Persian digits that share the Arabic shapes
        cmap[0x06F0 + d] = gname(0x0660 + d)
    cmap[0x06DD] = gname(0x06D4)      # end of ayah: the manuscript's cluster of dashes

    # marks
    top_marks, bot_marks, empty_marks = [], [], []
    for cp, fn in MARKS_TOP.items():
        n = gname(cp)
        glyphs[n] = mk(fn)
        top_marks.append(n)
    for cp, fn in MARKS_BOTTOM.items():
        n = gname(cp)
        glyphs[n] = mk(fn)
        bot_marks.append(n)
    for cp in MARKS_EMPTY:
        n = gname(cp)
        glyphs[n] = G(0)
        empty_marks.append(n)
    glyphs["_hidden"] = G(0)
    for n in top_marks + bot_marks + empty_marks:
        order.append(n)
        cmap[int(n[3:], 16)] = n
    order.append("_hidden")
    mark_glyphs = set(top_marks + bot_marks + empty_marks + ["_hidden"])

    # Besides the hamza on alif, waw and ya' (above), ss01 takes away the two other hamzas,
    # which the manuscript never wrote either:
    #  * the hamza that stands on its own (شيء، السماء، جاء) becomes an empty glyph with no
    #    width, so that شيء is set as شى with no gap.  It is a base, not a mark, so a vowel
    #    written on the hamza stays where the hamza was (see the mark feature) instead of
    #    falling on the letter before it.  Last in the glyph order, so every other glyph keeps
    #    its number.
    #  * the combining hamza above or below (U+0654, U+0655, as in بِـَٔايَٰتِنَا and تِلۡقَآيِٕ) is a
    #    mark, and becomes the empty mark _hidden, as the vowels do under ss02; a vowel
    #    written over it then sits on the letter itself.
    glyphs["uni0621.ss01"] = G(0)
    order.append("uni0621.ss01")
    rasm[gname(0x0621)] = "uni0621.ss01"
    rasm[gname(0x0654)] = rasm[gname(0x0655)] = "_hidden"

    # outlines and metrics
    glyf, hmtx, geoms = {}, {}, {}
    for n in order:
        g = glyphs[n]
        geom = g.geom()
        geoms[n] = geom
        tt, xmin = to_glyph(geom)
        glyf[n] = tt
        hmtx[n] = (0 if n in mark_glyphs else int(round(g.adv)), int(xmin))

    # ---------------- OpenType features ----------------
    fea = ["languagesystem DFLT dflt;", "languagesystem arab dflt;", ""]
    bases = [n for n in order if n not in mark_glyphs and n != ".notdef"]
    fea.append("table GDEF {\n  GlyphClassDef [%s], , [%s], ;\n} GDEF;\n"
               % (" ".join(bases), " ".join(sorted(mark_glyphs))))

    def single(tag, names):
        lines = ["feature %s {" % tag]
        for n in names:
            lines.append("  sub %s by %s;" % (n.rsplit(".", 1)[0], n))
        lines.append("} %s;\n" % tag)
        return lines

    fea += single("init", init_sub)
    fea += single("medi", medi_sub)
    fea += single("fina", fina_sub)

    fea.append("feature rlig {\n  lookup LAMALEF {\n    lookupflag IgnoreMarks;")
    for a, b, lig in lig_rules:
        fea.append("    sub %s %s by %s;" % (a, b, lig))
    fea.append("  } LAMALEF;\n} rlig;\n")

    fea.append("feature ss01 {\n  featureNames { name \"Rasm only (no dots)\"; };")
    for n, sn in sorted(rasm.items()):
        fea.append("  sub %s by %s;" % (n, sn))
    fea.append("} ss01;\n")

    vis = top_marks + bot_marks
    fea.append("feature ss02 {\n  featureNames { name \"Hide vowel marks\"; };\n  sub [%s] by _hidden;\n} ss02;\n"
               % " ".join(vis))

    fea.append("markClass [%s] <anchor 0 0> @TOP;" % " ".join(top_marks))
    fea.append("markClass [%s] <anchor 0 0> @BOT;\n" % " ".join(bot_marks))
    fea.append("feature mark {")
    for n in bases:
        if glyphs[n].adv == 0 or geoms[n] is None:
            continue
        (tx, ty), (bx, by) = anchors(geoms[n], glyphs[n].adv)
        fea.append("  pos base %s <anchor %d %d> mark @TOP <anchor %d %d> mark @BOT;" % (n, tx, ty, bx, by))
    # the hamza that ss01 takes away: a vowel on it sits at the hamza's own height, where it was
    (_, ty), (_, by) = anchors(geoms["uni0621"], glyphs["uni0621"].adv)
    fea.append("  pos base uni0621.ss01 <anchor 0 %d> mark @TOP <anchor 0 %d> mark @BOT;" % (ty, by))
    fea.append("} mark;\n")
    fea.append("feature mkmk {")
    for n in top_marks:
        b = geoms[n].bounds
        fea.append("  pos mark %s <anchor 0 %d> mark @TOP;" % (n, round(b[3] + 24)))
    for n in bot_marks:
        b = geoms[n].bounds
        fea.append("  pos mark %s <anchor 0 %d> mark @BOT;" % (n, round(b[1] - 24)))
    fea.append("} mkmk;\n")
    fea_text = "\n".join(fea)

    # ---------------- assemble ----------------
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(hmtx)
    fb.setupHorizontalHeader(ascent=1040, descent=-560)
    fb.setupNameTable({
        "familyName": "Birmingham Hijazi",
        "styleName": "Regular",
        "uniqueFontIdentifier": "BirminghamHijazi-Regular-4.101",
        "fullName": "Birmingham Hijazi Regular",
        "psName": "BirminghamHijazi-Regular",
        "version": "Version 4.101",
        "copyright": "Copyright (c) 2026 Aland Kawa Ali",
        "licenseDescription": ("Licensed under the Aland Attribution & Non-Commercial License (AANCL) v1.0. "
                               "Attribution is required; commercial use requires prior written permission. "
                               "See the LICENSE file."),
        "licenseInfoURL": "https://github.com/XAlandK/early-quran-fonts/blob/main/LICENSE",
        "description": ("Hijazi typeface whose letterforms are traced from the ink of the Birmingham "
                        "Qur'an manuscript (Cadbury Research Library, Mingana Islamic Arabic 1572a) and "
                        "of the leaves of the same Qur'an in Paris (BnF Arabe 328, ff. 71-86). "
                        "ss01: rasm only (no dots). ss02: hide vowel marks."),
    })
    fb.setupOS2(sTypoAscender=820, sTypoDescender=-460, sTypoLineGap=300,
                usWinAscent=1040, usWinDescent=560, achVendID="NONE", fsType=0)
    fb.setupPost()
    fb.addOpenTypeFeatures(fea_text)
    os2 = fb.font["OS/2"]
    os2.recalcUnicodeRanges(fb.font)
    if hasattr(os2, "recalcCodePageRanges"):
        os2.recalcCodePageRanges(fb.font)
    fb.save(out_path)
    return len(order), fea_text


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "BirminghamHijazi-Regular.ttf"
    n, fea = build(out)
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(fea)
    print("built %s (%d glyphs)" % (out, n))
