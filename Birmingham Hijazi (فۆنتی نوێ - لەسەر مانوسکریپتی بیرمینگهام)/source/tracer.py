#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trace letterforms straight from the photograph of the Birmingham Qur'an
manuscript (Mingana Islamic Arabic 1572a).

For every letter form one exemplar is picked in the manuscript.  The line it
sits in is turned level, the word is cut where the letters join, and the
outline of the ink of that one letter is written out in font units.  Nothing
is redrawn by hand: the outline in the font is the outline of the scribe's ink.

How the outline is found
  * The line is levelled by a rigid turn (no shear), so distances and angles
    inside a letter are those of the photograph.
  * The edge of a stroke is put where the grey is half-way between the ink of
    that stroke and the parchment around the letter.  The ink is not equally
    dark everywhere, so this level is worked out locally, not once for the page.
  * The edge is located on the grey values enlarged three times, i.e. to a
    third of a pixel of the photograph.
  * Cracks and flaked specks inside a stroke are closed; the outline is then
    relieved of the stair-steps of pixels and JPEG blocks by a low-pass along
    its length that is compensated so that tips and corners are not pulled in.

Usage:  python tracer.py <full.jpg> <lines.json> <traced.json> [qa_dir|-] [group ids|-] [dump_dir]
Needs:  numpy, pillow, scipy, scikit-image, shapely
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from skimage import measure
from skimage.segmentation import watershed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exemplars import GROUPS  # noqa: E402

PXU = 0.225        # manuscript pixels per font unit
BL = 40            # font-unit height of the centre of the baseline stroke
STD = 16.0         # thickness (px) every joining stroke is brought to at a join
                   # (the median of the joining strokes of the exemplars)
UP, DN = 215, 150  # rows kept above / below the fitted baseline
ABOVE, BELOW = 182, 128   # ink beyond these rows belongs to the neighbouring lines
MARGIN = 150       # columns kept left and right of a group
THR = 128          # first, rough separation of ink from parchment (for cutting the words apart)
BEAR = 18          # side bearing (px) on a side that does not join: the scribe leaves
                   # almost as much room after an unjoined letter as between words
K = 3              # the edge of the ink is located on the grey values enlarged K times


def disk(r):
    r = int(round(r))
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


class Page:
    def __init__(self, path, lines):
        self.rgb = np.asarray(Image.open(path).convert('RGB'))
        self.gray = self.rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        self.lines = lines
        self.H, self.W = self.gray.shape

    def to_line(self, page, idx, x, dy=0.0):
        """A point of the photograph given as (x, distance below the baseline at x) ->
        (distance along the levelled line, distance below it)."""
        L = self.lines[page][idx - 1]
        th = math.atan(L['m'])
        return L['x0'] + (x - L['x0']) / math.cos(th) + dy * math.sin(th), dy * math.cos(th)

    def deskew(self, page, idx, ua, ub):
        """Columns ua..ub of a line (measured along its baseline), turned rigidly so that
        the fitted baseline is horizontal (row UP)."""
        L = self.lines[page][idx - 1]
        th = math.atan(L['m'])
        cs, sn = math.cos(th), math.sin(th)
        s = np.arange(ua, ub, dtype=np.float32) - L['x0']
        t = np.arange(-UP, DN, dtype=np.float32)
        X = L['x0'] + s[None, :] * cs - t[:, None] * sn
        Y = L['r'] + s[None, :] * sn + t[:, None] * cs
        g = ndi.map_coordinates(self.gray, [Y, X], order=3, mode='constant', cval=255.0)
        c = np.stack([ndi.map_coordinates(self.rgb[..., k].astype(np.float32), [Y, X], order=1,
                                          mode='constant', cval=235.0) for k in range(3)], axis=-1)
        return g.astype(np.float32), np.clip(c, 0, 255).astype(np.uint8)


def ink_mask(g, thr, hole):
    ink = ndi.gaussian_filter(g, 0.7) < thr
    ink = ndi.binary_closing(ink, structure=disk(2), border_value=0)
    holes = ndi.binary_fill_holes(ink) & ~ink
    lab, n = ndi.label(holes)
    if n:
        sizes = ndi.sum(holes, lab, np.arange(1, n + 1))
        for i, sz in enumerate(sizes, 1):
            if sz < hole:
                ink[lab == i] = True
    return ink


def baseline_run(ink, col, y0, reach=20):
    """(top, bottom) of the ink run in a column that lies nearest row y0."""
    colv = ink[:, col]
    y0 = int(round(y0))
    best = None
    for dy in range(0, int(reach) + 1):
        for y in (y0 - dy, y0 + dy):
            if 0 <= y < len(colv) and colv[y]:
                best = y
                break
        if best is not None:
            break
    if best is None:
        return None
    t = b = best
    while t > 0 and colv[t - 1]:
        t -= 1
    while b < len(colv) - 1 and colv[b + 1]:
        b += 1
    return t, b


def plain_cost(ink, col, y0):
    """Low where the column holds nothing but a plain joining stroke."""
    run = baseline_run(ink, col, y0)
    if run is None:
        return 1e9
    t, b = run
    th = b - t + 1
    y0 = int(round(y0))
    other = ink[max(y0 - 34, 0):t, col].sum() + ink[b + 1:y0 + 24, col].sum()
    return th + 4.0 * other + (200 if th > 1.6 * STD else 0)


def snap(ink, col, y0, rad=16):
    cands = range(max(col - rad, 3), min(col + rad, ink.shape[1] - 3) + 1)
    return min(cands, key=lambda c: (plain_cost(ink, c, y0) + 0.2 * abs(c - col)))


def local_baseline(ink, col, y0, reach=240):
    """Centre row of the plain joining strokes near a column."""
    cs, ws = [], []
    for c in range(max(col - reach, 0), min(col + reach, ink.shape[1])):
        run = baseline_run(ink, c, y0, reach=16)
        if run is None:
            continue
        t, b = run
        if 0.6 * STD <= b - t + 1 <= 1.4 * STD and ink[max(t - 30, 0):t, c].sum() == 0:
            cs.append((t + b) / 2)
            ws.append(1.0 / (40 + abs(c - col)))
    if len(cs) < 10:
        return float(y0)
    cs, ws = np.array(cs), np.array(ws)
    order = np.argsort(cs)
    cum = np.cumsum(ws[order])
    return float(cs[order][np.searchsorted(cum, cum[-1] / 2)])


def extract(ink0, kind, cr, cl, y0, opt):
    """The pixels of one letter: its word cut at the joins, and anything that merely
    touches it (a stem of the line below, a tail of the line above) parted from it."""
    ink = ink0.copy()
    for (a, b, c, d) in opt.get('erase', []):
        ink[b:d, a:c] = False
    for (a, b, c, d) in opt.get('fill', []):
        ink[b:d, a:c] = True
    for poly in opt.get('erase_poly', []):       # ink of another line that crosses the letter
        im = Image.new('L', (ink.shape[1], ink.shape[0]), 0)
        ImageDraw.Draw(im).polygon(poly, fill=1)
        ink[np.asarray(im) > 0] = False
    jr, jl = kind in ('medi', 'fina'), kind in ('init', 'medi')
    edges = {}
    if jr:
        t, b = baseline_run(ink, cr, y0)
        edges['r'] = (cr, (t + b) / 2, b - t + 1)
        ink[max(t - 5, 0):b + 6, cr + 1:cr + 3] = False
    if jl:
        t, b = baseline_run(ink, cl, y0)
        edges['l'] = (cl, (t + b) / 2, b - t + 1)
        ink[max(t - 5, 0):b + 6, cl - 2:cl] = False
    lab, _ = ndi.label(ink)
    mark = np.zeros(ink.shape, dtype=np.int32)
    if jr:
        (c, yc, th) = edges['r']
        mark[int(yc) - 2:int(yc) + 3, c - 4:c + 1] = 1
        mark[int(yc - th / 2):int(yc + th / 2) + 1, c + 4:c + 9] = 3
    if jl:
        (c, yc, th) = edges['l']
        mark[int(yc) - 2:int(yc) + 3, c:c + 5] = 1
        mark[int(yc - th / 2):int(yc + th / 2) + 1, c - 8:c - 3] = 3
    if not (jr or jl):
        yy = int(round(y0))
        mark[yy - 9:yy + 10, cl:cr + 1] = 1
    for (x, y) in opt.get('also', []):
        mark[y - 1:y + 2, x - 1:x + 2] = 1
    mark[~ink] = 0
    seeds = set(lab[mark == 1].ravel().tolist())
    seeds.discard(0)
    comp = np.isin(lab, list(seeds))
    yy = int(round(y0))
    alien = comp.copy()
    alien[max(yy - opt.get('above', ABOVE), 0):yy + opt.get('below', BELOW)] = False   # the lines above and below
    mark[alien] = 2
    mark[~comp] = 0
    if (mark >= 2).any() and not opt.get('nosplit'):
        # the letter touches something that is not part of it: part them at the neck
        dist = ndi.distance_transform_edt(comp)
        mask = watershed(-dist, mark, mask=comp) == 1
    else:
        mask = comp
    for (a, b, c, d) in opt.get('drop', []):
        mask[b:d, a:c] = False
    lab2, n2 = ndi.label(mask)
    if n2 > 1:                                   # specks
        sizes = ndi.sum(mask, lab2, np.arange(1, n2 + 1))
        for i, sz in enumerate(sizes, 1):
            if sz < 0.04 * sizes.max():
                mask[lab2 == i] = False
    forced = np.zeros(ink.shape, dtype=bool)
    for (a, b, c, d) in opt.get('fill', []):
        forced[b:d, a:c] = True
    return mask, edges, forced


def enlarge(a, order):
    """K-fold enlargement in which every pixel of the photograph becomes K x K samples."""
    h, w = a.shape
    yy = (np.arange(h * K) + 0.5) / K - 0.5
    xx = (np.arange(w * K) + 0.5) / K - 0.5
    return ndi.map_coordinates(a.astype(np.float32), np.meshgrid(yy, xx, indexing='ij'), order=order, mode='nearest')


def fill_small_holes(m, limit):
    holes = ndi.binary_fill_holes(m) & ~m
    lab, n = ndi.label(holes)
    if n:
        sizes = ndi.sum(holes, lab, np.arange(1, n + 1))
        for i, sz in enumerate(sizes, 1):
            if sz < limit:
                m[lab == i] = True
    return m


def refine(mask, g, others, opt, forced=None):
    """The letter again, K times finer, its edge put where the grey is half-way between
    the ink of the stroke at that place and the parchment around the letter.

    Returns the fine mask and the row / column of the photograph crop its corner sits at."""
    ys, xs = np.where(mask)
    r0, r1 = max(ys.min() - 16, 0), min(ys.max() + 17, mask.shape[0])
    c0, c1 = max(xs.min() - 16, 0), min(xs.max() + 17, mask.shape[1])
    m = mask[r0:r1, c0:c1]
    oth = others[r0:r1, c0:c1]
    gs = ndi.gaussian_filter(g[r0:r1, c0:c1], 0.6)
    ring = ndi.binary_dilation(m, structure=disk(14)) & ~ndi.binary_dilation(m | oth, structure=disk(4))
    paper = float(np.median(gs[ring])) if ring.sum() > 60 else float(np.percentile(gs, 92))
    # how dark the ink of the stroke is hereabouts: the darker greys of the letter within 6 px
    dark = ndi.percentile_filter(np.where(m, gs, 255.0), 15, footprint=disk(6))
    dark = ndi.gaussian_filter(np.minimum(dark, paper - 44), 2.0)
    thr = np.clip((dark + paper) / 2 + opt.get('level', 0), 96, paper - 22)

    gk = enlarge(gs, 3)
    tk = enlarge(thr, 1)
    mk = enlarge(m, 0) > 0.5
    ok = enlarge(oth, 0) > 0.5
    cand = gk < tk
    grow = cand & ndi.binary_dilation(mk, structure=disk(3 * K)) & ~ndi.binary_dilation(ok, structure=disk(K))
    light = mk & ~cand                                           # too pale to be ink at this level
    peel = ndi.binary_propagation(light & ndi.binary_dilation(~mk), mask=light)   # ... and open to the outside
    ref = (mk | grow) & ~peel
    if forced is not None and forced.any():                      # ink marked by hand as flaked away
        ref |= enlarge(forced[r0:r1, c0:c1], 0) > 0.5
    ref = ndi.binary_closing(ref, structure=disk(1.4 * K))       # cracks in the ink
    # pale patches shut inside the ink: a counter if it is wide, flaked ink if it is a mere crack
    shut = light & ~peel & ref
    wide = ndi.binary_opening(shut, structure=disk(1.5 * K))
    lab, n = ndi.label(wide)
    if n:
        sizes = ndi.sum(wide, lab, np.arange(1, n + 1))
        big = np.isin(lab, [i for i, sz in enumerate(sizes, 1) if sz >= 12 * K * K])
        ref &= ~ndi.binary_propagation(big, mask=shut & ndi.binary_dilation(big, structure=disk(1.5 * K)))
    ref = fill_small_holes(ref, max(opt.get('hole', 0), 14) * K * K)
    lab, n = ndi.label(ref)
    if n > 1:
        sizes = ndi.sum(ref, lab, np.arange(1, n + 1))
        ref = np.isin(lab, [i for i, sz in enumerate(sizes, 1) if sz >= 0.04 * sizes.max()])
    return ref, r0, c0


def fine_run(fine, j, i0, reach):
    """(top, bottom) of the run of a fine column that lies nearest fine row i0."""
    colv = fine[:, j]
    i0 = int(round(i0))
    best = None
    for d in range(0, int(reach) + 1):
        for i in (i0 - d, i0 + d):
            if 0 <= i < len(colv) and colv[i]:
                best = i
                break
        if best is not None:
            break
    if best is None:
        return None
    t = b = best
    while t > 0 and colv[t - 1]:
        t -= 1
    while b < len(colv) - 1 and colv[b + 1]:
        b += 1
    return t, b


def blend_edge(fine, j_cut, ic, side, T=12):
    """Bring the joining stroke to the standard thickness as it reaches the cut, and run it
    on a little past the cut so that smoothing rounds it off outside the glyph.

    j_cut is the last fine column of the letter, ic the fine row of the centre of the stroke."""
    half = STD * K / 2
    measured = None
    n = T * K
    for d in range(0, T * K + 1):                # where does the body of the letter begin?
        j = j_cut - d if side == 'r' else j_cut + d
        run = fine_run(fine, j, ic, 8 * K) if 0 <= j < fine.shape[1] else None
        if run is None or run[1] - run[0] + 1 > 1.3 * STD * K:
            n = max(d, 4 * K)
            break
    for d in range(0, n + 1):
        j = j_cut - d if side == 'r' else j_cut + d
        if not 0 <= j < fine.shape[1]:
            break
        run = fine_run(fine, j, ic, 8 * K)
        if run is None:
            break
        t, b = run
        if b - t + 1 > 1.7 * STD * K:
            break
        if d == 2 * K:
            measured = (b - t + 1) / K
        w = d / n
        nt = (1 - w) * (ic - half) + w * (t - 0.5)
        nb = (1 - w) * (ic + half) + w * (b + 0.5)
        fine[t:b + 1, j] = False
        fine[int(math.ceil(nt)):int(math.floor(nb)) + 1, j] = True
    for d in range(1, 11 * K + 1):
        j = j_cut + d if side == 'r' else j_cut - d
        if 0 <= j < fine.shape[1]:
            fine[int(math.ceil(ic - half)):int(math.floor(ic + half)) + 1, j] = True
    return measured


def taper_out(fine, j_cut, ic, side, run, n):
    """The letter had to be cut where its stroke is still thick, because the next letter
    starts at once: give it a short neck that narrows to the standard joining stroke.
    Returns the new last column of the letter."""
    t0, b0 = run
    half = STD * K / 2
    j = j_cut
    for d in range(1, n + 1):
        j = j_cut + d if side == 'r' else j_cut - d
        if not 0 <= j < fine.shape[1]:
            return j - 1 if side == 'r' else j + 1
        w = d / n
        w = w * w * (3 - 2 * w)
        nt = (1 - w) * (t0 - 0.5) + w * (ic - half)
        nb = (1 - w) * (b0 + 0.5) + w * (ic + half)
        fine[int(math.ceil(nt)):int(math.floor(nb)) + 1, j] = True
    return j


def smooth_ring(coords, sigma):
    """Low-pass a closed outline along its length.  It takes out the stair-steps of the
    photograph's pixels and JPEG blocks; the second, compensating pass (2G - G*G) keeps
    tips and corners from being pulled in, as a plain low-pass would."""
    pts = np.asarray(coords[:-1], dtype=float)
    seg = np.hypot(*np.diff(np.vstack([pts, pts[:1]]), axis=0).T)
    total = seg.sum()
    sigma = min(sigma, total / 16)
    n = max(int(total / 3), 16)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, total, n, endpoint=False)
    x = np.interp(t, s, np.append(pts[:, 0], pts[0, 0]))
    y = np.interp(t, s, np.append(pts[:, 1], pts[0, 1]))
    k = sigma / (total / n)
    lp = lambda v: ndi.gaussian_filter1d(v, k, mode='wrap')
    x1, y1 = lp(x), lp(y)
    return list(zip(2 * x1 - lp(x1), 2 * y1 - lp(y1)))


def smooth_geom(geom, sigma):
    polys = [geom] if geom.geom_type == 'Polygon' else [p for p in geom.geoms if p.geom_type == 'Polygon']
    out = []
    for p in polys:
        holes = [smooth_ring(h.coords, sigma * 0.6) for h in p.interiors if Polygon(h).area > 120]
        out.append(Polygon(smooth_ring(p.exterior.coords, sigma), holes).buffer(0))
    return unary_union(out)


def to_units(fine, r0, c0, edges, yb_free, opt):
    """Outline of a fine mask in font units, with its advance width."""
    col = lambda j: c0 + (j + 0.5) / K - 0.5        # fine index -> coordinate in the crop
    row = lambda i: r0 + (i + 0.5) / K - 0.5
    jr, jl = 'r' in edges, 'l' in edges
    if jr and jl:
        (c1, y1, _), (c2, y2, _) = edges['r'], edges['l']
        slope = (y1 - y2) / (c1 - c2) if c1 - c2 > 40 else 0.0
        ybase = lambda c: y2 + slope * (c - c2)
    elif jr:
        ybase = lambda c: edges['r'][1]
    elif jl:
        ybase = lambda c: edges['l'][1]
    else:
        ybase = lambda c: yb_free
    ymid = ybase(col(fine.shape[1] // 2))
    ia = max(int((ymid - 85 - r0) * K), 0)
    ib = max(int((ymid + 16 - r0) * K), ia + 1)
    cols = np.where(fine[ia:ib].any(axis=0))[0]
    if not len(cols):
        cols = np.where(fine.any(axis=0))[0]
    x_right = edges['r'][0] if jr else col(cols.max()) + 0.5 / K + opt.get('rsb', BEAR)
    x_left = edges['l'][0] if jl else col(cols.min()) - 0.5 / K - opt.get('lsb', BEAR)
    adv = (x_right - x_left) / PXU

    pad = 3 * K
    F = ndi.gaussian_filter(np.pad(fine.astype(np.float32), pad), opt.get('smooth', 0.45) * K)
    rings = []
    for cont in measure.find_contours(F, 0.5):
        if len(cont) < 8:
            continue
        pts = [((col(j - pad) - x_left) / PXU, BL + (ybase(col(j - pad)) - row(i - pad)) / PXU) for i, j in cont]
        p = Polygon(pts).buffer(0)
        if not p.is_empty:
            rings.append(p)
    rings.sort(key=lambda p: -p.area)
    geom = None
    for p in rings:                      # even-odd: a ring inside ink is a counter
        geom = p if geom is None else geom.symmetric_difference(p)
    if geom is None:
        return None, adv, (x_left, x_right), ybase
    # specks and hairs thinner than half a pixel of the photograph
    geom = geom.buffer(1.5).buffer(-3).buffer(1.5)
    if geom.is_empty:
        return None, adv, (x_left, x_right), ybase
    geom = smooth_geom(geom, opt.get('soften', 7))
    h = STD / PXU / 2
    if jr:      # an exact, shared end for the joining stroke
        geom = geom.difference(box(adv, BL - h - 25, adv + 300, BL + h + 25))
        geom = unary_union([geom, box(adv - 14, BL - h, adv + 3, BL + h)])
    if jl:
        geom = geom.difference(box(-300, BL - h - 25, 0, BL + h + 25))
        geom = unary_union([geom, box(-3, BL - h, 14, BL + h)])
    geom = geom.simplify(0.5, preserve_topology=True).buffer(0)
    return geom, adv, (x_left, x_right), ybase


PALETTE = [(230, 30, 30), (20, 110, 230), (20, 150, 60), (220, 120, 0), (150, 40, 200), (0, 150, 160)]


def run(full_jpg, lines_json, out_json, qa_dir=None, only=None, dump_dir=None):
    page = Page(full_jpg, json.load(open(lines_json)))
    try:
        out = json.load(open(out_json))
    except Exception:
        out = {}
    try:                                   # alternative exemplars, kept apart from the font's own
        out['_all'] = json.load(open(out_json + '.alts'))
    except Exception:
        out['_all'] = {}
    joins = []
    for grp in GROUPS:
        if only and grp['id'] not in only:
            continue
        pg, ln = grp['page'], grp['line']
        U = lambda x, dy=0.0: page.to_line(pg, ln, x, dy)       # photograph -> levelled line
        us = [U(x)[0] for it in grp['items'] for x in it[1:3]]
        xa, xb = int(min(us)) - MARGIN, int(max(us)) + MARGIN
        g, rgb = page.deskew(pg, ln, xa, xb)
        ink = ink_mask(g, grp.get('thr', THR), grp.get('hole', 14))
        y_nom = UP + grp.get('dy', 0)
        snapped = {}
        qa = Image.fromarray(rgb).convert('RGBA')
        ov = Image.new('RGBA', qa.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        print(grp['id'])
        for n, it in enumerate(grp['items']):
            key, xr, xl = it[0], it[1], it[2]
            opt = dict(it[3]) if len(it) > 3 else {}
            kind = key.split('.')[1].split('#')[0]
            cr, cl = int(round(U(xr)[0])) - xa, int(round(U(xl)[0])) - xa
            for k in ('erase', 'fill', 'drop'):
                if k in opt:
                    rects = []
                    for (a, b, c, d) in opt[k]:
                        (ua, ta), (ub_, tb) = U(a, b), U(c, d)
                        rects.append((int(round(ua)) - xa, UP + int(round(ta)), int(round(ub_)) - xa, UP + int(round(tb))))
                    opt[k] = rects
            if 'erase_poly' in opt:
                opt['erase_poly'] = [[(U(a, b)[0] - xa, UP + U(a, b)[1]) for (a, b) in poly] for poly in opt['erase_poly']]
            if 'also' in opt:
                opt['also'] = [(int(round(U(a, b)[0])) - xa, UP + int(round(U(a, b)[1]))) for (a, b) in opt['also']]
            y_loc = local_baseline(ink, (cr + cl) // 2, y_nom) + opt.get('dyb', 0)
            if kind in ('medi', 'fina'):
                cr = snapped.setdefault(xr, cr if opt.get('exact') else snap(ink, cr, y_loc))
            if kind in ('init', 'medi'):
                cl = snapped.setdefault(xl, cl if opt.get('exact') else snap(ink, cl, y_loc))
            try:
                mask, edges, forced = extract(ink, kind, cr, cl, y_loc, opt)
            except TypeError:
                print('    !! no joining stroke at a cut:', key)
                continue
            if not mask.any():
                print('    !! empty', key)
                continue
            fine, r0, c0 = refine(mask, g, ink & ~mask, opt, forced)
            if not fine.any():
                print('    !! nothing left of', key)
                continue
            meas, thick = [], {}
            for side in ('r', 'l'):                         # the centre of the stroke, located finely
                if side in edges:
                    c, yc, _ = edges[side]
                    j = (c - c0) * K + (K - 1 if side == 'r' else 0)
                    run_ = fine_run(fine, j, (yc - r0 + 0.5) * K - 0.5, 8 * K)
                    if run_ is None:
                        continue
                    if run_[1] - run_[0] + 1 > 1.5 * STD * K:
                        thick[side] = (j, run_)
                    else:
                        edges[side] = (c, r0 + ((run_[0] + run_[1]) / 2 + 0.5) / K - 0.5, (run_[1] - run_[0] + 1) / K)
            for side, (j, run_) in thick.items():           # cut in a thick place: add a neck
                other = [s for s in edges if s != side and s not in thick]
                yc = edges[other[0]][1] if other else y_loc
                j2 = taper_out(fine, j, (yc - r0 + 0.5) * K - 0.5, side, run_, 4 * K)
                c2 = edges[side][0] + (1 if side == 'r' else -1) * abs(j2 - j) // K
                edges[side] = (c2, yc, STD)
            for side in ('r', 'l'):
                if side in edges:
                    c, yc, _ = edges[side]
                    j = (c - c0) * K + (K - 1 if side == 'r' else 0)
                    m_ = blend_edge(fine, j, (yc - r0 + 0.5) * K - 0.5, side)
                    if m_ and side not in thick:
                        meas.append(m_)
            geom, adv, (x_l, x_r), ybase = to_units(fine, r0, c0, edges, y_loc, opt)
            if geom is None:
                print('    !! nothing left of', key)
                continue
            name = key.split('#')[0]
            src = {'page': pg, 'line': ln, 'id': grp['id'],
                   'x0': round(float(x_l + xa), 2), 'x1': round(float(x_r + xa), 2),
                   'yb': round(float(np.mean([e[1] for e in edges.values()])) if edges else y_loc, 2)}
            rec = {'adv': round(float(adv), 1), 'wkt': geom.wkt, 'src': src}
            out.setdefault('_all', {})[name + '@' + grp['id'] + (':%d' % n)] = rec
            if '#' not in key:
                out[name] = rec
                joins += meas
                if dump_dir:
                    ys, xs_ = np.where(mask)
                    a0, a1 = max(ys.min() - 30, 0), min(ys.max() + 31, mask.shape[0])
                    b0, b1 = max(xs_.min() - 30, 0), min(xs_.max() + 31, mask.shape[1])
                    np.savez_compressed(os.path.join(dump_dir, name + '.npz'), g=g[a0:a1, b0:b1],
                                        rgb=rgb[a0:a1, b0:b1], mask=mask[a0:a1, b0:b1], ink=ink[a0:a1, b0:b1],
                                        x_left=x_l - b0, adv=adv,
                                        ybase=np.array([ybase(c) for c in range(b0, b1)]) - a0,
                                        cuts=np.array([e[0] - b0 for e in edges.values()]),
                                        hole=opt.get('hole', 0), u0=xa + b0, t0=a0 - UP,
                                        page=pg, line=ln)
            b = geom.bounds
            print('    %-14s adv=%4d  x[%4d,%4d] y[%4d,%4d]  cut r=%s l=%s  th=%s' % (
                key, adv, b[0], b[2], b[1], b[3], cr + xa if 'r' in edges else '-',
                cl + xa if 'l' in edges else '-', ('/'.join('%.1f' % e[2] for e in edges.values()) or '-')
                + ('  (neck added: %s)' % ','.join(thick) if thick else '')))
            col = PALETTE[n % len(PALETTE)]
            edge = mask & ~ndi.binary_erosion(mask, structure=disk(1))
            ov.paste(Image.new('RGBA', qa.size, col + (255,)), mask=Image.fromarray((edge * 255).astype(np.uint8)))
            ov.paste(Image.new('RGBA', qa.size, col + (60,)),
                     mask=Image.fromarray(((mask & ~edge) * 60).astype(np.uint8)))
            for e in edges.values():
                od.line([(e[0], e[1] - 30), (e[0], e[1] + 30)], fill=(0, 0, 0, 255), width=1)
            ys, xs_ = np.where(mask)
            od.text((int(xs_.mean()) - 22, max(ys.min() - 12, 12)), key.replace('.', ' '), fill=col + (255,))
        if qa_dir:
            qa = Image.alpha_composite(qa, ov).convert('RGB')
            d = ImageDraw.Draw(qa)
            for x in range((xa // 50 + 1) * 50, xb, 50):
                d.line([(x - xa, 0), (x - xa, 5 if x % 100 else 11)], fill=(0, 0, 200))
                if x % 100 == 0:
                    d.rectangle([x - xa + 1, 0, x - xa + 28, 10], fill=(255, 255, 255))
                    d.text((x - xa + 2, 0), str(x), fill=(0, 0, 160))
            qa = qa.crop((90, 0, qa.width - 90, qa.height))
            z = min(grp.get('zoom', 1.25), 1560 / qa.width)
            qa = qa.resize((int(qa.width * z), int(qa.height * z)), Image.LANCZOS)
            qa.save('%s/%s.jpg' % (qa_dir, grp['id']), quality=84)
    if joins:
        print('joining strokes of the chosen exemplars: median thickness %.2f px (STD is %.2f)'
              % (float(np.median(joins)), STD))
    alts = out.pop('_all', {})
    json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    if qa_dir:
        json.dump(alts, open(out_json + '.alts', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    return out


if __name__ == '__main__':
    only = set(sys.argv[5].split(',')) if len(sys.argv) > 5 and sys.argv[5] != '-' else None
    run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None, only,
        sys.argv[6] if len(sys.argv) > 6 else None)
