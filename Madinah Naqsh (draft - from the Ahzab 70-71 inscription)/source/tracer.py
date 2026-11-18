#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Trace letterforms from the photograph of a rock inscription near Medina that carries
Qur'an 33:70-71 (photograph: Muhammad al-Maghdhawi, @mohammed93athar).

The photograph is small (an alif is 40 to 70 pixels tall, a level stroke 4 to 6 wide), so
the outline of a letter in it is mostly the outline of its own blur.  What the photograph
does hold is where each stroke runs and how wide it is.  This tracer therefore takes from
it, for every stroke, the CENTRE LINE and the WIDTH, and writes the stroke out as a clean
band of that width along that line.

For every letter form one exemplar is picked in the inscription (exemplars.py).  On the
page that prep.py makes (the lines level and at one letter size) the word is cut where the
letters join, and for that one letter:

  * the pixels of the letter are found at the grey half-way between carving and rock,
    worked out locally, as for a manuscript;
  * within them every stroke is narrowed to its crest, the part brighter than 62 % of the
    way from the rock to the top of the stroke there.  Blur widens a stroke to both sides
    alike, so the middle of the crest is the middle of the groove; and the crest is narrow
    enough to part two strokes that the blur has run together, and to open the eye of a
    loop;
  * the crest is thinned to a line one sample wide, on samples a third of a page pixel
    apart.  In a letter that has a head (fa', qaf, mim, waw, ...), where the crest is
    clearly wider than a stroke - a loop too small for the photograph to show its eye -
    the line runs round it, half a stroke inside its edge, instead of through its middle;
  * side twigs shorter than a stroke is wide are dropped; a free end is carried on, in
    the direction the line was running, to the end of the carving at the half-way grey;
  * the line is relieved of the stair-steps of the samples by a low-pass along its length
    that is compensated so that bends are not pulled in;
  * across the line the brightness of the photograph is read, and the width of the stroke
    taken from it (stroke_widths below): each straight part of a stroke gets the width
    read on it; a stroke that runs beside another cannot be read and gets the width of a
    level stroke, LEVEL;
  * the bands are joined, their ends left square as on the stone, and written out in font
    units.  The level direction is narrowed by the "squeeze" of the line (see prep.py).

What is decided by hand is written down in exemplars.py, letter by letter: ink that is not
of the letter, a twig kept or dropped, a stroke that damage has interrupted.

Usage:  python tracer.py <page.png> <lines.json> <traced.json> [qa_dir|-] [group ids|-] [dump_dir]
Needs:  numpy, pillow, scipy, scikit-image, shapely
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from collections import Counter

from shapely.geometry import Point, Polygon, box
from shapely.ops import transform as shapely_transform
from shapely.ops import unary_union

from skimage.morphology import skeletonize
from skimage.segmentation import watershed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exemplars import GROUPS  # noqa: E402
import prep  # noqa: E402

PXU = 0.225        # manuscript pixels per font unit
BL = 40            # font-unit height of the centre of the baseline stroke
LEVEL = 12.4       # width (px of the page) of a level stroke of the inscription, and so of every
                   # joining stroke (measured by width.py: 5.8, 4.2 and 3.6 px of the photograph on
                   # the three lines, which the enlargement of the lines brings to one size)
BLUR = 2.8         # blur of the photograph (full width at half height, px of the photograph),
                   # measured by width.py on the smallest specks of the rock
REACH = 8.0        # how far the brightness is read to each side of a centre line (px of the photograph)
STEPW = 1.5        # distance between two readings of the width along a line (px of the page)
SKIP = 9.0         # readings this near a fork or a cut are left out (px of the page)
UP, DN = 215, 150  # rows kept above / below the fitted baseline
ABOVE, BELOW = 182, 128   # ink beyond these rows belongs to the neighbouring lines
MARGIN = 150       # columns kept left and right of a group
THR = 150          # first, rough separation of carving from rock (for cutting the words apart)
STD = 28.0         # thickness (px) of a joining stroke in that rough separation (the blur included)
BEAR = 13          # side bearing (px) on a side that does not join
K = 3              # the centre line is located on the grey values enlarged K times


def disk(r):
    r = int(round(r))
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


class Page:
    def __init__(self, path, lines):
        self.rgb = np.asarray(Image.open(path).convert('RGB'))
        self.gray = self.rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        colour = os.path.join(os.path.dirname(path), 'page_rgb.jpg')      # the same page in the photograph's colours
        if os.path.exists(colour):
            self.rgb = np.asarray(Image.open(colour).convert('RGB'))
        self.lines = lines
        self.H, self.W = self.gray.shape
        v, col, _, _ = prep.levelled()
        self.v = v                         # strength of the carving, not cut off at either end
        self.lum = col @ np.array([0.299, 0.587, 0.114], dtype=np.float32)      # brightness of the photograph
        assert self.v.shape == self.gray.shape, 'page.png is not the page of this photograph: run prep.py'

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
        v = ndi.map_coordinates(self.v, [Y, X], order=3, mode='constant', cval=0.0)
        lum = ndi.map_coordinates(self.lum, [Y, X], order=3, mode='nearest')
        return g.astype(np.float32), np.clip(c, 0, 255).astype(np.uint8), v.astype(np.float32), lum.astype(np.float32)


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

    Returns the fine mask and the window (r0, r1, c0, c1) of the crop it covers."""
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
    ref = fill_small_holes(ref, max(opt.get('hole', 0), 30) * K * K)
    lab, n = ndi.label(ref)
    if n > 1:
        sizes = ndi.sum(ref, lab, np.arange(1, n + 1))
        ref = np.isin(lab, [i for i, sz in enumerate(sizes, 1) if sz >= 0.04 * sizes.max()])
    return ref, (r0, r1, c0, c1)


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


EXT = 14 * K       # how far the stroke is run on past a cut, so that its centre line crosses the cut
# Letters that have a head or a loop.  Only in these may a place where the crest is wider
# than a stroke be read as a head too small to show its eye; in the others (alif, lam,
# the teeth, dal, ra', kaf, nun, ha') a wide place is a stroke that the blur has widened.
HEADED = ('FEH', 'QAF', 'MEEM', 'WAW', 'HEH', 'AIN', 'SAD', 'TAH', 'LAMALEF')


def crest(fine, vk, cuts, opt):
    """The letter narrowed to the crest of its strokes: the part of it that is brighter than
    62 % of the way from the rock to the top of the stroke at that place.  The blur spreads
    a stroke to both sides alike, so the middle of the crest is the middle of the groove;
    and the crest is narrow enough to part two strokes that the blur has run together at
    the half-way grey, and to open the eye of a loop."""
    vs = ndi.gaussian_filter(vk, opt.get('sigma', 1.5) * K)
    ring = ndi.binary_dilation(fine, structure=disk(14 * K)) & ~ndi.binary_dilation(fine, structure=disk(4 * K))
    rock = float(np.percentile(vs[ring], 30)) if ring.sum() > 200 else float(np.percentile(vs, 20))
    top = ndi.maximum_filter(np.where(fine, vs, -1e9), size=int(opt.get('reach', 20) * K))
    band = fine & (vs > rock + opt.get('core', 0.62) * (top - rock))
    band = ndi.binary_opening(band, structure=disk(0.5 * K)) | ndi.binary_erosion(band, structure=disk(1))
    band = fill_small_holes(band, opt.get('eye', 4) * K * K)        # a pin-hole is noise, not an eye
    for (a, b, c, d) in opt.get('bridge', []):                       # a stroke the noise has broken
        band[b:d, a:c] |= fine[b:d, a:c]
    for (a, b, c, d) in opt.get('paint', []):                        # a stroke that damage has interrupted
        band[max(b, 0):max(d, 0), max(a, 0):max(c, 0)] = True
    for (a, b, c, d) in opt.get('part', []) + opt.get('drop', []):   # two strokes the blur has run together;
        band[max(b, 0):max(d, 0), max(a, 0):max(c, 0)] = False       # ink that is not of this letter
    lab, n = ndi.label(band, structure=np.ones((3, 3), int))
    if n > 1:
        sizes = ndi.sum(band, lab, np.arange(1, n + 1))
        band = np.isin(lab, [i for i, sz in enumerate(sizes, 1) if sz >= 0.06 * sizes.max()])
    pieces = ndi.label(band, structure=np.ones((3, 3), int))[1]
    for side, (jc, ic, thick) in cuts.items():
        run = None if thick else (fine_run(band, jc, ic, 8 * K) or fine_run(fine, jc, ic, 8 * K))
        if run is None:
            run = (int(ic - 2 * K), int(ic + 2 * K))
        if side == 'r':
            band[:, jc + 1:] = False
            band[run[0]:run[1] + 1, jc + 1:jc + 1 + EXT] = True
            if thick:
                band[run[0]:run[1] + 1, jc - 2 * K:jc + 1] = True
        else:
            band[:, :jc] = False
            band[run[0]:run[1] + 1, max(jc - EXT, 0):jc] = True
            if thick:
                band[run[0]:run[1] + 1, jc:jc + 2 * K + 1] = True
    return band, pieces


def _neighbours(pix):
    """Which samples of a one-sample-wide line follow on each other.  A step across a corner
    is not taken where the two samples are also joined by a step along a side."""
    adj = {}
    for (i, j) in pix:
        out = [q for q in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)) if q in pix]
        for di, dj in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            if (i + di, j + dj) in pix and (i + di, j) not in pix and (i, j + dj) not in pix:
                out.append((i + di, j + dj))
        adj[(i, j)] = out
    return adj


def chains(pix):
    """A line drawing as a set of samples -> its pieces: runs of samples from one end or
    fork to the next.  A closed ring without a fork begins and ends on the same sample."""
    adj = _neighbours(pix)
    nodes = {p for p in pix if len(adj[p]) != 2}
    out, used = [], set()
    for a in sorted(nodes):
        for q in adj[a]:
            if (a, q) in used:
                continue
            ch = [a, q]
            used.add((a, q))
            prev, cur = a, q
            while cur not in nodes:
                nxt = [x for x in adj[cur] if x != prev]
                prev, cur = cur, nxt[0]
                ch.append(cur)
            used.add((cur, prev))
            out.append(ch)
    left = pix - {p for ch in out for p in ch} - nodes
    while left:
        a = min(left)
        ch = [a]
        prev, cur = a, adj[a][0]
        while cur != a:
            ch.append(cur)
            nxt = [x for x in adj[cur] if x != prev]
            prev, cur = cur, nxt[0]
        ch.append(a)
        left -= set(ch)
        out.append(ch)
    return out


def _length(ch):
    a = np.asarray(ch, dtype=float)
    return float(np.hypot(*np.diff(a, axis=0).T).sum())


def prune(pix, keep, least):
    """Drop side twigs shorter than `least` samples, the shortest first.  A twig is a piece
    that ends freely at one end and at a fork at the other; `keep` are ends that stay."""
    while True:
        chs = chains(pix)
        deg = Counter()
        for ch in chs:
            deg[ch[0]] += 1
            deg[ch[-1]] += 1
        twigs = []
        for ch in chs:
            for a, b, body in ((ch[0], ch[-1], ch[:-1]), (ch[-1], ch[0], ch[1:])):
                if a != b and deg[a] == 1 and deg[b] >= 3 and a not in keep and _length(ch) < least:
                    twigs.append((_length(ch), body))
        if not twigs:
            return pix, chs
        pix = pix - set(min(twigs)[1])


def centre_lines(fine, vk, cuts, opt):
    """Centre lines of the strokes of one letter.

    fine   the letter at the half-way grey, K times finer than the page
    vk     the strength of the carving on the same samples
    cuts   side -> (column of the cut, row of the centre of the stroke there, cut in a thick place?)
    Returns a list of (points as (row, column) in fine samples, kinds of its two ends), and
    what was measured on the way.  An end is 'free', a 'fork', or a cut ('r' / 'l')."""
    band, pieces = crest(fine, vk, cuts, opt)
    dt = ndi.distance_transform_edt(band)
    sk = skeletonize(band)
    h = float(np.median(dt[sk]))                      # half the width of the crest of a plain stroke
    # heads: where the crest is clearly wider than a stroke, the line runs round, not through
    inner = ndi.binary_opening(dt > 1.12 * h, structure=disk(0.3 * h))
    lab, n = ndi.label(inner)
    heads = np.zeros(band.shape, dtype=bool)
    def nearest(points):                              # the wide places nearest the points given by hand
        found = []
        if n:
            _, (ii, jj) = ndi.distance_transform_edt(lab == 0, return_indices=True)
            for (j, i) in points:
                if 0 <= i < lab.shape[0] and 0 <= j < lab.shape[1] and \
                        np.hypot(ii[i, j] - i, jj[i, j] - j) <= 2.5 * h:
                    found.append(lab[ii[i, j], jj[i, j]])
        return found
    forced, banned = nearest(opt.get('ring', [])), nearest(opt.get('noring', []))
    for i in range(1, n + 1):
        comp = lab == i
        if i in banned:
            continue
        fat = dt[comp].max() / h
        # a place where three strokes meet is a little wider than a stroke too: it is told
        # from a head by the strokes that leave it, unless it is far too wide for a meeting
        shell = ndi.binary_dilation(comp, iterations=2) & ~comp
        leave = ndi.label(sk & shell, structure=np.ones((3, 3), int))[1]
        ys, xs = np.where(comp)
        long_ = max(np.ptp(ys), np.ptp(xs)) + 1 > 3.2 * (2 * dt[comp].max() - 2 * h + 1)
        if i in forced or (opt.get('headed', True) and not long_ and
                           (fat >= opt.get('head2', 1.9) or (fat >= opt.get('head', 1.5) and leave <= 2))):
            heads |= comp
    for side, (jc, ic, thick) in cuts.items():       # never at a cut
        lo, hi = (jc - 2 * K, band.shape[1]) if side == 'r' else (0, jc + 2 * K)
        heads[:, max(lo, 0):hi] = False
    rim = heads & ~ndi.binary_erosion(heads)
    pix = skeletonize((sk & ~heads) | rim)
    for side, (jc, ic, thick) in cuts.items():       # the line ends on the cut
        if side == 'r':
            pix[:, jc + 1:] = False
        else:
            pix[:, :jc] = False
    pset = set(zip(*[a.tolist() for a in np.where(pix)]))
    ends = {}
    for side, (jc, ic, thick) in cuts.items():
        col = [p for p in pset if p[1] == jc]
        if col:
            ends[min(col, key=lambda p: abs(p[0] - ic))] = side
    pset, chs = prune(pset, set(ends), opt.get('twig', 1.3) * h)
    deg = Counter()
    for ch in chs:
        deg[ch[0]] += 1
        deg[ch[-1]] += 1
    kind = lambda p: ends.get(p) or ('free' if deg[p] == 1 else 'fork')
    out = []
    for ch in chs:
        if len(ch) < 2:
            continue
        closed = ch[0] == ch[-1]
        if not closed and _length(ch) < 0.6 * h and kind(ch[0]) == 'free' and kind(ch[-1]) == 'free':
            continue                                              # a speck
        out.append((np.asarray(ch, dtype=float), ('ring', 'ring') if closed else (kind(ch[0]), kind(ch[-1]))))
    return out, {'h': h / K, 'heads': int(ndi.label(heads)[1]), 'pieces': pieces, 'band': band, 'headmask': heads}


def carry_on(pts, at_end, fine, r, h):
    """A free end of a centre line, carried on (or taken back) along its own direction until
    a round end of radius r touches the end of the carving at the half-way grey."""
    p = pts if at_end else pts[::-1]
    d = np.hypot(*(p - p[-1]).T)
    # Within one stroke width of its end a thinned line strays towards a corner of the end.
    # It is made to run on straight there, the way it was running before.
    k1 = int(np.argmax(d <= 1.3 * h))                # first point of the end piece
    k0 = int(np.argmax(d <= 3.0 * h))                # where its direction is taken from
    if k1 > k0 and k1 < len(p) - 1:
        v = p[k1] - p[k0]
        v = v / max(np.hypot(*v), 1e-9)
        p = np.vstack([p[:k1 + 1], p[k1] + v * max(np.dot(p[-1] - p[k1], v), 1.0)])
        d = np.hypot(*(p - p[-1]).T)
    else:
        far = p[d <= max(2.5 * h, 6)]
        v = p[-1] - far[0]
        if np.hypot(*v) < 1e-6:
            return pts
        v = v / np.hypot(*v)
    inside = lambda q: 0 <= q[0] < fine.shape[0] - 1 and 0 <= q[1] < fine.shape[1] - 1 and \
        ndi.map_coordinates(fine.astype(np.float32), [[q[0]], [q[1]]], order=1)[0] > 0.5
    end = p[-1]
    if inside(end + r * v):
        s = 0.0
        while s < 2 * h and inside(end + (s + 0.5 + r) * v):
            s += 0.5
        if s > 0:
            p = np.vstack([p, end + s * v])
    else:
        k = len(p) - 1
        while k > 2 and d[k] < 2.0 * h and not inside(p[k] + r * v):
            k -= 1
        p = p[:k + 1]
    return p if at_end else p[::-1]


def soften(pts, sigma, closed, step=4.0):
    """Low-pass a line along its length.  It takes out the stair-steps of the samples; the
    second, compensating pass (2G - G*G) keeps bends from being pulled in.  The two ends of
    an open line stay where they are."""
    pts = np.asarray(pts, dtype=float)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    total = float(seg.sum())
    if total < 2 * step or len(pts) < 3:
        return pts
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(int(total / step), 6)
    if closed:
        t = np.linspace(0, total, n, endpoint=False)
        k = min(sigma, total / 16) / (total / n)
        lp = lambda v: ndi.gaussian_filter1d(v, k, mode='wrap')
        cols = []
        for c in (0, 1):
            v = np.interp(t, s, pts[:, c])
            v1 = lp(v)
            cols.append(2 * v1 - lp(v1))
        out = np.column_stack(cols)
        return np.vstack([out, out[:1]])
    t = np.linspace(0, total, n + 1)
    k = min(sigma, total / 6) / (total / n)

    def lp(v):
        base = v[0] + (v[-1] - v[0]) * np.linspace(0, 1, len(v))
        d = v - base
        ext = np.concatenate([-d[:0:-1], d, -d[-2::-1]])           # mirrored about both ends
        return base + ndi.gaussian_filter1d(ext, k, mode='nearest')[len(d) - 1:2 * len(d) - 1]
    cols = []
    for c in (0, 1):
        v = np.interp(t, s, pts[:, c])
        v1 = lp(v)
        cols.append(2 * v1 - lp(v1))
    return np.column_stack(cols)


def stroke_widths(pts, kinds, lum, rock, blur, reach, away, others):
    """Width of the carved stroke along one centre line (px of the page).

    Every STEPW pixels the brightness of the photograph is read across the line.  To each
    side of the top of the stroke, the stroke reaches as far as the point at which the
    brightness is half-way between the rock and that top; the width is the distance between
    the two points, less the blur of the photograph (a stroke of width w seen through a
    blur b measures sqrt(w^2 + b^2)).  A reading counts only where the stroke stands free:
    on both sides the brightness must go on down nearly to the rock, without a trough on
    the way, and the two points must lie nearer to this centre line than to any other
    (`away`: distance of every pixel to the nearest centre line of the letter).

    The uprights of this inscription are about twice as wide as its level strokes, so a
    stroke is given one width for each part of it that runs one way (more level than
    upright, or more upright than level): the middle of the readings along that part.  A
    part that could not be read, or that runs alongside another stroke (`others`: distance
    to the nearest OTHER centre line) - the sides of a loop, the two lines of a sad or a
    kaf, the teeth of a sin - gets the width of a level stroke, LEVEL.
    Returns one width for every point of the line, and the number of readings used."""
    n = len(pts)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(-reach, reach + 0.01, 0.25)
    m = int(round(1.2 * blur / 0.25))
    got_s, got_w = [], []
    lo = SKIP if kinds[0] != 'free' else 0.6 * SKIP
    hi = s[-1] - (SKIP if kinds[1] != 'free' else 0.6 * SKIP)
    for at in np.arange(lo, hi, STEPW):
        cx, cy = np.interp(at, s, pts[:, 0]), np.interp(at, s, pts[:, 1])
        dx = np.interp(min(at + 2, s[-1]), s, pts[:, 0]) - np.interp(max(at - 2, 0), s, pts[:, 0])
        dy = np.interp(min(at + 2, s[-1]), s, pts[:, 1]) - np.interp(max(at - 2, 0), s, pts[:, 1])
        L = np.hypot(dx, dy)
        if L < 1e-6:
            continue
        yy, xx = cy + t * dx / L, cx - t * dy / L
        if yy.min() < 0 or xx.min() < 0 or yy.max() > lum.shape[0] - 1 or xx.max() > lum.shape[1] - 1:
            continue
        p = ndi.map_coordinates(lum, [yy, xx], order=3)
        far = ndi.map_coordinates(away, [yy, xx], order=1)
        k = int(np.argmax(np.where(np.abs(t) <= 2.5, p, -1e9)))
        if p[k] - rock < 25:                         # too faint here to measure
            continue
        half = rock + 0.5 * (p[k] - rock)
        low = rock + 0.3 * (p[k] - rock)
        sides = []
        for step in (-1, 1):
            i = k
            while 0 < i < len(p) - 1 and p[i] > half:
                i += step
            if p[i] > half:
                break                                 # no end within reach
            cross = t[i] - step * (half - p[i]) / (p[i - step] - p[i]) * 0.25
            j0, j1 = (max(i - m, 0), i + 1) if step < 0 else (i, min(i + m + 1, len(p)))
            if p[j0:j1].min() > low:
                break                                 # does not come down to the rock: another stroke
            run = p[min(i, k):max(i, k) + 1]
            run = run if step > 0 else run[::-1]      # from the top outwards
            if (np.maximum.accumulate(run[::-1])[::-1] > run + 0.25 * (p[k] - rock)).any():
                break                                 # it rises again on the way: a trough
            d = abs(cross - t[k])
            ii = min(max(i if abs(t[i]) > 1 else i + step * 4, 0), len(t) - 1)
            if d > 1.9 * LEVEL or far[ii] < 0.8 * abs(t[ii]):
                break                                 # nearer to another centre line
            sides.append(d)
        if len(sides) < 2:
            continue
        w = sum(sides)
        got_s.append(at)
        got_w.append(np.sqrt(max(w * w - blur * blur, (0.5 * LEVEL) ** 2)))
    got_s, got_w = np.array(got_s), np.array(got_w)
    # the parts of the line that run one way
    k5 = max(int(5 / max(np.median(seg), 1e-6)), 1)
    tx = ndi.uniform_filter1d(np.gradient(pts[:, 0]), 2 * k5 + 1, mode='nearest')
    ty = ndi.uniform_filter1d(np.gradient(pts[:, 1]), 2 * k5 + 1, mode='nearest')
    upright = np.abs(ty) > np.abs(tx)
    beside = ndi.map_coordinates(others, [pts[:, 1], pts[:, 0]], order=1) < 2.5 * LEVEL
    w = np.full(n, LEVEL)
    used = 0
    start = 0
    for i in range(1, n + 1):
        if i == n or upright[i] != upright[start]:
            a0, a1 = s[start], s[i - 1]
            sel = (got_s >= a0) & (got_s <= a1) if len(got_s) else np.zeros(0, bool)
            if a1 - a0 >= 0.8 * LEVEL and sel.sum() >= 5 and sel.sum() * STEPW >= 0.3 * (a1 - a0) \
                    and beside[start:i].mean() < 0.5:
                w[start:i] = np.clip(np.median(got_w[sel]), 0.8 * LEVEL, 3.2 * LEVEL)
                used += int(sel.sum())
            start = i
    # a groove does not change its width at once: the step between two parts is spread over a few pixels
    grid = np.arange(0, s[-1] + 0.5, 0.5)
    w = np.interp(s, grid, ndi.gaussian_filter1d(np.interp(grid, s, w), 6.0, mode='nearest'))
    return w, used


def ribbon(pts, w, kinds, cut_w):
    """The stroke as an area: the centre line, as wide at every point as measured there.
    A free end is cut off square (the ends of the carved strokes are); at a fork the stroke
    ends round, inside the stroke it meets; towards a cut it comes to the width that every
    joining stroke is given."""
    pts, w = np.asarray(pts, dtype=float), np.asarray(w, dtype=float).copy()
    seg = np.hypot(*np.diff(pts, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    for k, end in ((0, kinds[0]), (-1, kinds[1])):
        if end in ('r', 'l'):                         # blend into the joining stroke over 10 px
            d = s if k == 0 else s[-1] - s
            f = np.clip(d / 10.0, 0, 1)
            w = f * w + (1 - f) * cut_w
    parts = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        L = np.hypot(x1 - x0, y1 - y0)
        if L < 1e-9:
            continue
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        r0, r1 = w[i] / 2, w[i + 1] / 2
        parts.append(Polygon([(x0 + nx * r0, y0 + ny * r0), (x1 + nx * r1, y1 + ny * r1),
                              (x1 - nx * r1, y1 - ny * r1), (x0 - nx * r0, y0 - ny * r0)]).buffer(0))
    for i in range(len(pts)):                        # round bends; but a free end and a cut stay square
        if (kinds[0] not in ('fork', 'ring') and s[i] < w[i] / 2) or \
                (kinds[1] not in ('fork', 'ring') and s[-1] - s[i] < w[i] / 2):
            continue
        parts.append(Point(pts[i]).buffer(w[i] / 2, 12))
    return unary_union([p for p in parts if not p.is_empty])


def to_units(lines, win, edges, yb_free, opt, lum, rock, scale, squeeze):
    """The letter in font units: its strokes as areas, its centre lines, its advance width.

    lines    from centre_lines(), already carried on at their free ends
    win      (r0, r1, c0, c1): the window of the crop the fine samples cover
    lum      brightness of the photograph over the crop;  rock: its level on the rock here
    scale    page pixels per pixel of the photograph on this line
    squeeze  what the level direction of this line is narrowed by (see prep.py)"""
    r0, _, c0, _ = win
    col = lambda j: c0 + (j + 0.5) / K - 0.5        # fine index -> coordinate in the crop
    row = lambda i: r0 + (i + 0.5) / K - 0.5
    xy = [np.column_stack([col(p[:, 1]), row(p[:, 0])]) for p, _ in lines]       # (x, y) in the crop
    at_cut = {}
    for a, (p, kinds) in zip(xy, lines):
        for k, e in ((0, kinds[0]), (-1, kinds[1])):
            if e in ('r', 'l'):
                a[k, 0] = edges[e][0]                # the line ends exactly on the cut
                at_cut[e] = a[k, 1]
    jr, jl = 'r' in edges, 'l' in edges
    yr = at_cut.get('r', edges['r'][1] if jr else None)
    yl = at_cut.get('l', edges['l'][1] if jl else None)
    if jr and jl:
        (c1, c2) = edges['r'][0], edges['l'][0]
        slope = (yr - yl) / (c1 - c2) if c1 - c2 > 40 else 0.0
        ybase = lambda c: yl + slope * (c - c2)
    elif jr:
        ybase = lambda c: yr
    elif jl:
        ybase = lambda c: yl
    else:
        ybase = lambda c: yb_free
    # the lines without the stair-steps of the samples, and the width of the stroke along each
    xy = [soften(a, opt.get('soften', 6.0), kinds[0] == 'ring', step=1.0) for a, (p, kinds) in zip(xy, lines)]
    blur = BLUR * scale
    on = np.ones(lum.shape, dtype=bool)               # distance of every pixel to the nearest centre line
    for a in xy:
        dense = np.vstack([np.linspace(a[i], a[i + 1], 4) for i in range(len(a) - 1)])
        ix = np.clip(np.round(dense[:, 0]).astype(int), 0, lum.shape[1] - 1)
        iy = np.clip(np.round(dense[:, 1]).astype(int), 0, lum.shape[0] - 1)
        on[iy, ix] = False
    away = ndi.distance_transform_edt(on).astype(np.float32)

    def raster(a):
        im = np.zeros(lum.shape, dtype=bool)
        dense = np.vstack([np.linspace(a[i], a[i + 1], 4) for i in range(len(a) - 1)])
        im[np.clip(np.round(dense[:, 1]).astype(int), 0, lum.shape[0] - 1),
           np.clip(np.round(dense[:, 0]).astype(int), 0, lum.shape[1] - 1)] = True
        return im
    marks = [raster(a) for a in xy]
    ws, read = [], 0
    for q, (a, (p, kinds)) in enumerate(zip(xy, lines)):
        rest = np.zeros(lum.shape, dtype=bool)
        for j, mk_ in enumerate(marks):
            if j != q:
                rest |= mk_
        # other lines, but not where they meet this one (within 1.5 LEVEL of its ends)
        for end in (a[0], a[-1]):
            yy_, xx_ = np.ogrid[:lum.shape[0], :lum.shape[1]]
            rest[(yy_ - end[1]) ** 2 + (xx_ - end[0]) ** 2 < (1.5 * LEVEL) ** 2] = False
        others = ndi.distance_transform_edt(~rest).astype(np.float32) if rest.any() else np.full(lum.shape, 1e3, np.float32)
        w, n = stroke_widths(a, kinds, lum, rock, blur, REACH * scale, away, others)
        ws.append(w)
        read += n
    for w_, (p, kinds) in zip(ws, lines):
        if 'w' in opt:
            w_[:] = opt['w']
    geom = unary_union([ribbon(a, w, kinds, LEVEL) for a, w, (p, kinds) in zip(xy, ws, lines)])
    geom = geom.buffer(0.8).buffer(-2.4).buffer(1.6)             # hair-cracks shut, corners a little round
    slits = []                                                   # a gap too narrow for the photograph to show
    for poly in ([geom] if geom.geom_type == 'Polygon' else geom.geoms):
        slits += [Polygon(r) for r in poly.interiors if Polygon(r).buffer(-opt.get('slit', 2.5)).is_empty]
    if slits:
        geom = unary_union([geom] + slits)
    # advance width: from cut to cut; on a free side from the ink near the baseline
    ymid = ybase(float(np.median(np.vstack(xy)[:, 0])))
    near = geom.intersection(box(-1e5, ymid - 85, 1e5, ymid + 16))
    if near.is_empty:
        near = geom
    x_right = edges['r'][0] if jr else near.bounds[2] + opt.get('rsb', BEAR) / squeeze
    x_left = edges['l'][0] if jl else near.bounds[0] - opt.get('lsb', BEAR) / squeeze
    adv = (x_right - x_left) * squeeze / PXU
    unit = lambda x, y: ((x - x_left) * squeeze / PXU, BL + (ybase(x) - y) / PXU)
    geom_u = shapely_transform(lambda x, y, z=None: unit(np.asarray(x), np.asarray(y)), geom)
    h = LEVEL / PXU / 2
    if jr:      # an exact, shared end for the joining stroke
        geom_u = geom_u.difference(box(adv, -3000, adv + 3000, 3000))
        geom_u = unary_union([geom_u, box(adv - 14, BL - h, adv + 3, BL + h)])
    if jl:
        geom_u = geom_u.difference(box(-3000, -3000, 0, 3000))
        geom_u = unary_union([geom_u, box(-3, BL - h, 14, BL + h)])
    geom_u = geom_u.simplify(0.5, preserve_topology=True).buffer(0)
    paths = [np.column_stack(unit(a[:, 0], np.array(a[:, 1]))) for a in xy]
    return geom_u, paths, ws, adv, (x_left, x_right), ybase, xy, geom, read


PALETTE = [(230, 30, 30), (20, 110, 230), (20, 150, 60), (220, 120, 0), (150, 40, 200), (0, 150, 160)]


def close_up(path, rgb, fine, info, win, xy, xa, area=None, z=2):
    """One letter, 2 K times the size of the page, for checking by eye: the letter at the
    half-way grey (light blue), its crest (yellow), heads (orange), the centre lines (red),
    on a grid of page coordinates (x along the line, rows below the baseline)."""
    r0, r1, c0, c1 = win
    f = K * z
    im = Image.fromarray(rgb[r0:r1, c0:c1]).resize(((c1 - c0) * f, (r1 - r0) * f), Image.LANCZOS)
    a = np.asarray(im).copy()
    up = lambda m: np.kron(m, np.ones((z, z), dtype=bool))
    edge = lambda m: m & ~ndi.binary_erosion(m)
    a[edge(up(fine))] = (90, 200, 255)
    a[edge(up(info['band']))] = (255, 235, 0)
    a[edge(up(info['headmask']))] = (255, 140, 0)
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im, 'RGBA')
    for x in range(((c0 + xa) // 10 + 1) * 10, c1 + xa, 10):
        X = (x - xa - c0 + 0.5) * f
        d.line([(X, 0), (X, im.height)], fill=(255, 255, 255, 70 if x % 50 else 150), width=1)
        if x % 50 == 0:
            d.text((X + 2, 2), str(x), fill=(255, 255, 255, 255))
    for y in range(((r0 - UP) // 10 + 1) * 10, r1 - UP, 10):
        Y = (y + UP - r0 + 0.5) * f
        d.line([(0, Y), (im.width, Y)], fill=(255, 255, 255, 70 if y % 50 else 150), width=1)
        if y % 50 == 0:
            d.text((2, Y + 2), str(y), fill=(255, 255, 255, 255))
    for pts in xy:
        d.line([((x - c0 + 0.5) * f, (y - r0 + 0.5) * f) for x, y in pts], fill=(255, 0, 0, 255), width=2)
    if area is not None:                                 # the strokes as they will be drawn
        for poly in ([area] if area.geom_type == 'Polygon' else area.geoms):
            for ring in [poly.exterior] + list(poly.interiors):
                d.line([((x - c0 + 0.5) * f, (y - r0 + 0.5) * f) for x, y in ring.coords], fill=(255, 255, 255, 255), width=2)
    im.save(path)


def run(page_png, lines_json, out_json, qa_dir=None, only=None, dump_dir=None):
    page = Page(page_png, json.load(open(lines_json)))
    try:
        out = json.load(open(out_json))
    except Exception:
        out = {}
    try:                                   # alternative exemplars, kept apart from the font's own
        out['_all'] = json.load(open(out_json + '.alts'))
    except Exception:
        out['_all'] = {}
    crests = []
    for grp in GROUPS:
        if only and grp['id'] not in only:
            continue
        pg, ln = grp['page'], grp['line']
        U = lambda x, dy=0.0: page.to_line(pg, ln, x, dy)       # page -> levelled line
        us = [U(x)[0] for it in grp['items'] for x in it[1:3]]
        xa, xb = int(min(us)) - MARGIN, int(max(us)) + MARGIN
        g, rgb, v, lum = page.deskew(pg, ln, xa, xb)
        scale = float(page.lines[pg][ln - 1].get('scale', 1.0))
        squeeze = float(page.lines[pg][ln - 1].get('squeeze', 1.0))
        ink = ink_mask(g, grp.get('thr', THR), grp.get('hole', 14))
        y_nom = UP + grp.get('dy', 0)
        snapped = {}
        drawn = []
        print(grp['id'])
        for n, it in enumerate(grp['items']):
            key, xr, xl = it[0], it[1], it[2]
            opt = dict(grp.get('opt', {}))
            opt.update(it[3] if len(it) > 3 else {})
            kind = key.split('.')[1].split('#')[0]
            cr, cl = int(round(U(xr)[0])) - xa, int(round(U(xl)[0])) - xa
            for k in ('erase', 'fill', 'drop', 'bridge', 'part', 'paint'):
                if k in opt:
                    rects = []
                    for (a, b, c, d) in opt[k]:
                        (ua, ta), (ub_, tb) = U(a, b), U(c, d)
                        rects.append((int(round(ua)) - xa, UP + int(round(ta)), int(round(ub_)) - xa, UP + int(round(tb))))
                    opt[k] = rects
            if 'erase_poly' in opt:
                opt['erase_poly'] = [[(U(a, b)[0] - xa, UP + U(a, b)[1]) for (a, b) in poly] for poly in opt['erase_poly']]
            for k in ('also', 'ring', 'noring'):
                if k in opt:
                    opt[k] = [(int(round(U(a, b)[0])) - xa, UP + int(round(U(a, b)[1]))) for (a, b) in opt[k]]
            y_loc = local_baseline(ink, (cr + cl) // 2, y_nom) + opt.get('dyb', 0)
            if kind in ('medi', 'fina'):
                cr = snapped.setdefault(xr, cr if opt.get('exact', True) else snap(ink, cr, y_loc))
            if kind in ('init', 'medi'):
                cl = snapped.setdefault(xl, cl if opt.get('exact', True) else snap(ink, cl, y_loc))
            try:
                mask, edges, forced = extract(ink, kind, cr, cl, y_loc, opt)
            except TypeError:
                print('    !! no joining stroke at a cut:', key)
                continue
            if not mask.any():
                print('    !! empty', key)
                continue
            fine, win = refine(mask, g, ink & ~mask, opt, forced)
            if not fine.any():
                print('    !! nothing left of', key)
                continue
            r0, r1, c0, c1 = win
            vk = enlarge(ndi.gaussian_filter(v[r0:r1, c0:c1], 0.6), 3)
            cuts, notes = {}, []
            for side in ('r', 'l'):                         # the centre of the stroke at the cut, located finely
                if side in edges:
                    c, yc, _ = edges[side]
                    j = (c - c0) * K + (K - 1 if side == 'r' else 0)
                    i0 = (yc - r0 + 0.5) * K - 0.5
                    run_ = fine_run(fine, j, i0, 8 * K)
                    if side in opt.get('ycut', {}):                                      # given by hand
                        cuts[side] = (j, (UP + opt['ycut'][side] - r0 + 0.5) * K - 0.5, True)
                    elif run_ is not None and run_[1] - run_[0] + 1 > 1.5 * STD * K:    # cut in a thick place
                        other = [s for s in edges if s != side]
                        yc = edges[other[0]][1] if other else y_loc
                        cuts[side] = (j, (yc - r0 + 0.5) * K - 0.5, True)
                        notes.append('thick cut ' + side)
                    else:
                        cuts[side] = (j, (run_[0] + run_[1]) / 2 if run_ else i0, False)
            to_fine = lambda x, y: (int(round((x - c0) * K + 1)), int(round((y - r0) * K + 1)))
            fopt = dict(opt)
            fopt.setdefault('headed', key.split('.')[0] in HEADED)
            for k in ('ring', 'noring'):
                if k in opt:
                    fopt[k] = [to_fine(x, y) for (x, y) in opt[k]]
            for k in ('bridge', 'part', 'drop', 'paint'):
                if k in opt:
                    fopt[k] = [to_fine(a, b) + to_fine(c, d) for (a, b, c, d) in opt[k]]
            lines, info = centre_lines(fine, vk, cuts, fopt)
            if not lines:
                print('    !! no centre line found for', key)
                continue
            rad = 0.0                                       # the line runs to the very end of the carving
            ends_in = fine.copy()                           # where a free end may be carried on to
            for k in ('part', 'drop'):
                for (a_, b_, c_, d_) in fopt.get(k, []):
                    ends_in[max(b_, 0):max(d_, 0), max(a_, 0):max(c_, 0)] = False
            hk = info['h'] * K
            lines = [(carry_on(carry_on(p, True, ends_in, rad, hk) if kn[1] == 'free' else p, False, ends_in, rad, hk)
                      if kn[0] == 'free' else (carry_on(p, True, ends_in, rad, hk) if kn[1] == 'free' else p), kn)
                     for p, kn in lines]
            for side in cuts:
                if not any(side in kn for _, kn in lines):
                    notes.append('the line does not reach the cut ' + side)
            if info['pieces'] > 1:
                notes.append('%d pieces' % info['pieces'])
            around = ndi.binary_dilation(mask, structure=disk(14)) & ~ndi.binary_dilation(mask | ink, structure=disk(4))
            rock = float(np.percentile(lum[around], 40)) if around.sum() > 100 else float(np.percentile(lum, 30))
            geom, paths, widths, adv, (x_l, x_r), ybase, xy, area, read = to_units(
                lines, win, edges, y_loc, opt, lum, rock, scale, squeeze)
            if geom.is_empty:
                print('    !! nothing left of', key)
                continue
            name = key.split('#')[0]
            src = {'page': pg, 'line': ln, 'id': grp['id'],
                   'x0': round(float(x_l + xa), 2), 'x1': round(float(x_r + xa), 2),
                   'yb': round(float(ybase((x_l + x_r) / 2)), 2), 'crest': round(2 * info['h'], 2)}
            rec = {'adv': round(float(adv), 1), 'wkt': geom.wkt,
                   'paths': [[[round(float(x), 1), round(float(y), 1)] for x, y in p] for p in paths],
                   'widths': [round(float(np.median(w)), 2) for w in widths],
                   'src': src}
            out.setdefault('_all', {})[name + '@' + grp['id'] + (':%d' % n)] = rec
            if '#' not in key:
                out[name] = rec
                crests.append(2 * info['h'])
                if dump_dir:
                    ys, xs_ = np.where(mask)
                    a0, a1 = max(ys.min() - 30, 0), min(ys.max() + 31, mask.shape[0])
                    b0, b1 = max(xs_.min() - 30, 0), min(xs_.max() + 31, mask.shape[1])
                    np.savez_compressed(os.path.join(dump_dir, name + '.npz'), g=g[a0:a1, b0:b1], v=v[a0:a1, b0:b1],
                                        rgb=rgb[a0:a1, b0:b1], mask=mask[a0:a1, b0:b1], ink=ink[a0:a1, b0:b1],
                                        lum=lum[a0:a1, b0:b1], squeeze=squeeze, scale=scale,
                                        fine=fine, win=np.array(win), corner=np.array([a0, b0]),
                                        x_left=x_l - b0, adv=adv,
                                        ybase=np.array([ybase(c) for c in range(b0, b1)]) - a0,
                                        cuts=np.array([e[0] - b0 for e in edges.values()]),
                                        u0=xa + b0, t0=a0 - UP, page=pg, line=ln)
            gb = geom.bounds
            allu = np.array([[gb[0], gb[1]], [gb[2], gb[3]]])
            notes.append('width read at %d places: %.1f - %.1f px' % (read, min(w.min() for w in widths), max(w.max() for w in widths)))
            cutrow = {}
            for a_, (p_, kn_) in zip(xy, lines):
                for k_, e_ in ((0, kn_[0]), (-1, kn_[1])):
                    if e_ in ('r', 'l'):
                        cutrow[e_] = a_[k_, 1] - UP
            ct = lambda sd, c_: ('%d(%+.0f)' % (c_ + xa, cutrow[sd]) if sd in cutrow else '%d(?)' % (c_ + xa)) if sd in edges else '-'
            print('    %-14s adv=%4d  x[%4d,%4d] y[%4d,%4d]  cut r=%s l=%s  lines=%d rings=%d crest=%.1f%s' % (
                key, adv, allu[:, 0].min(), allu[:, 0].max(), allu[:, 1].min(), allu[:, 1].max(),
                ct('r', cr), ct('l', cl), len(lines), info['heads'],
                2 * info['h'], ('   ' + '; '.join(notes)) if notes else ''))
            drawn.append((key, n, xy, [kn for _, kn in lines], edges, mask, area))
            if qa_dir and '#' not in key:
                close_up(os.path.join(qa_dir, 'L_%s.png' % name), rgb, fine, info, win, xy, xa, area)
        if qa_dir and drawn:
            z = min(grp.get('zoom', 3.0), 3900 / rgb.shape[1])
            W_, H_ = int(rgb.shape[1] * z), int(rgb.shape[0] * z)
            top = Image.fromarray(rgb).resize((W_, H_), Image.LANCZOS)
            low = Image.new('RGB', (W_, H_), (236, 229, 211))
            dt_, dl_ = ImageDraw.Draw(top), ImageDraw.Draw(low)
            for key, n, xy, kinds, edges, mask, area in drawn:
                for poly in ([area] if area.geom_type == 'Polygon' else area.geoms):
                    dl_.polygon([(x * z + z / 2, y * z + z / 2) for x, y in poly.exterior.coords], fill=(62, 39, 22))
                    for hole in poly.interiors:
                        dl_.polygon([(x * z + z / 2, y * z + z / 2) for x, y in hole.coords], fill=(236, 229, 211))
                colr = PALETTE[n % len(PALETTE)]
                for a, kn in zip(xy, kinds):
                    pts = [(x * z + z / 2, y * z + z / 2) for x, y in a]
                    dt_.line(pts, fill=colr, width=2)
                    for (x, y), e in ((pts[0], kn[0]), (pts[-1], kn[1])):
                        if e == 'free':
                            dt_.ellipse([x - 3, y - 3, x + 3, y + 3], outline=colr)
                for e in edges.values():
                    for d_ in (dt_, dl_):
                        d_.line([(e[0] * z, (e[1] - 30) * z), (e[0] * z, (e[1] + 30) * z)], fill=(0, 0, 0), width=1)
                ys, xs_ = np.where(mask)
                dt_.text((int(xs_.mean() * z) - 22, max(int(ys.min() * z) - 14, 14)), key.replace('.', ' '), fill=colr)
            for x in range((xa // 50 + 1) * 50, xb, 50):
                dt_.line([((x - xa) * z, 0), ((x - xa) * z, 5 if x % 100 else 11)], fill=(0, 0, 200))
                if x % 100 == 0:
                    dt_.rectangle([(x - xa) * z + 1, 0, (x - xa) * z + 28, 10], fill=(255, 255, 255))
                    dt_.text(((x - xa) * z + 2, 0), str(x), fill=(0, 0, 160))
            qa = Image.new('RGB', (W_, 2 * H_ + 6), (255, 255, 255))
            qa.paste(top, (0, 0))
            qa.paste(low, (0, H_ + 6))
            cut = int(90 * z)
            qa.crop((cut, 0, W_ - cut, qa.height)).save('%s/%s.jpg' % (qa_dir, grp['id']), quality=86)
    alts = out.pop('_all', {})
    json.dump(out, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    if qa_dir:
        json.dump(alts, open(out_json + '.alts', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    return out

if __name__ == '__main__':
    only = set(sys.argv[5].split(',')) if len(sys.argv) > 5 and sys.argv[5] != '-' else None
    run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None, only,
        sys.argv[6] if len(sys.argv) > 6 else None)
