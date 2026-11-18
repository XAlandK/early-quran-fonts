#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pixel audit: every traced glyph of the built font, laid over the ink of the
exemplar it was traced from, at the same place and scale.

The reference is taken from the photograph again, independently of the outline
that went into the font: the grey values of the exemplar are enlarged four
times and cut at the grey half-way between the ink and the parchment around
that letter.  The glyph is rendered from the .ttf itself, so the audit covers
tracing, smoothing, the conversion to TrueType curves and the build.

For each glyph it reports, in pixels of the photograph:
  edge   mean distance between the outline of the font and the outline of the ink
  p95    the distance that 95 % of the outline stays within
  bias   mean signed distance (+ the font is fatter than the ink, - thinner)
  area   area of the font glyph / area of the ink

For each glyph it also writes a picture of three panels: the exemplar in the
photograph; the same with the outline of the ink (light blue) and, over it, the
outline of the font (red); and the difference (dark: both, blue: ink the font
lacks, red: font where there is no ink, grey: the joins, left out).

Usage:  python audit.py <font.ttf> <dump_dir> <out_dir> [keys|-] [png]
        (dump_dir is written by:  python tracer.py full.jpg lines.json traced.json - - dump_dir;
         'png' also keeps the pictures at four times the size of the photograph)
"""
import glob
import json
import os
import sys

import freetype
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tracer as T  # noqa: E402

Z = 4          # enlargement of the photograph for the comparison
GLYPH = {'ALIF': 'uni0627', 'BEH': 'uni066E', 'NOON': 'uni06BA', 'YEH': 'uni0649', 'HAH': 'uni062D',
         'DAL': 'uni062F', 'REH': 'uni0631', 'SEEN': 'uni0633', 'SAD': 'uni0635', 'TAH': 'uni0637',
         'AIN': 'uni0639', 'FEH': 'uni06A1', 'QAF': 'uni066F', 'KAF': 'uni0643', 'LAM': 'uni0644',
         'MEEM': 'uni0645', 'HEH': 'uni0647', 'WAW': 'uni0648', 'LAMALEF': 'lam_alef'}


def glyph_name(key):
    name, form = key.split('.')
    return GLYPH[name] + ('' if form == 'isol' else '.' + form)


def enlarge(a, order=3):
    """Z-fold enlargement in which each pixel of the photograph becomes Z x Z samples."""
    h, w = a.shape
    yy = (np.arange(h * Z) + 0.5) / Z - 0.5
    xx = (np.arange(w * Z) + 0.5) / Z - 0.5
    return ndi.map_coordinates(a.astype(np.float32), np.meshgrid(yy, xx, indexing='ij'), order=order, mode='nearest')


def unshear(a, ybase, order=1):
    """Shift every column so that the baseline the tracer used becomes one straight row."""
    yb0 = float(ybase[len(ybase) // 2])
    h, w = a.shape[:2]
    out = np.empty_like(a, dtype=np.float32)
    rows = np.arange(h, dtype=np.float32)
    for c in range(w):
        src = rows + (ybase[c] - yb0)
        if a.ndim == 2:
            out[:, c] = np.interp(src, rows, a[:, c].astype(np.float32))
        else:
            for k in range(a.shape[2]):
                out[:, c, k] = np.interp(src, rows, a[:, c, k].astype(np.float32))
    return out, yb0


def levels(g, mask, ink):
    """Grey of the parchment around this letter, and, for every place, the grey half-way
    between it and the ink of the stroke there (the ink is not equally dark everywhere).
    Worked out here on its own, not taken from the tracer."""
    gs = ndi.gaussian_filter(g, 1.0)
    ring = ndi.binary_dilation(mask, structure=T.disk(14)) & ~ndi.binary_dilation(ink | mask, structure=T.disk(4))
    paper = float(np.median(gs[ring])) if ring.sum() > 50 else 215.0
    core = ndi.grey_erosion(np.where(mask, gs, 255.0), footprint=T.disk(5))      # darkest grey within 5 px
    core = ndi.gaussian_filter(np.minimum(core + 6, paper - 44), 2.5)
    half = np.clip((core + paper) / 2, 96, paper - 22)
    inside = ndi.binary_erosion(mask, structure=T.disk(3))
    dark = float(np.median(g[inside])) if inside.sum() > 20 else float(np.percentile(g[mask], 25))
    return dark, paper, half


def render(ft, gid, shape, x0, y0):
    """Coverage of a glyph on a canvas, its origin (x=0, y=0 units) at the sub-pixel point (x0, y0)."""
    fx, fy = x0 - np.floor(x0), np.ceil(y0) - y0
    ft.set_transform(freetype.Matrix(0x10000, 0, 0, 0x10000), freetype.Vector(int(round(fx * 64)), int(round(fy * 64))))
    ft.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
    g = ft.glyph
    bm = g.bitmap
    out = np.zeros(shape, dtype=np.float32)
    if not (bm.width and bm.rows):
        return out
    arr = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width].astype(np.float32) / 255
    gx = int(np.floor(x0)) + g.bitmap_left
    gy = int(np.ceil(y0)) - g.bitmap_top
    ya, xa = max(gy, 0), max(gx, 0)
    yb, xb = min(gy + bm.rows, shape[0]), min(gx + bm.width, shape[1])
    if yb > ya and xb > xa:
        out[ya:yb, xa:xb] = arr[ya - gy:yb - gy, xa - gx:xb - gx]
    return out


def audit_one(ft, order, key, d, out_dir=None, full_res=False):
    g, mask, ink, rgb = d['g'], d['mask'], d['ink'], d['rgb']
    ybase = d['ybase']
    g2, yb0 = unshear(g, ybase)
    m2 = unshear(mask.astype(np.float32), ybase)[0] > 0.5
    i2 = unshear(ink.astype(np.float32), ybase)[0] > 0.5
    dark, paper, half = levels(g2, m2, i2)
    thr = enlarge(half, order=1)
    gz = enlarge(ndi.gaussian_filter(g2, 0.5))
    mz = enlarge(m2.astype(np.float32), order=1) > 0.5
    others = enlarge((i2 & ~ndi.binary_dilation(m2, structure=T.disk(2))).astype(np.float32), order=1) > 0.5
    region = ndi.binary_dilation(mz, structure=T.disk(int(2.5 * Z))) & ~ndi.binary_dilation(others, structure=T.disk(Z))
    ref = (gz < thr) & region
    ref = ndi.binary_closing(ref, structure=T.disk(1.4 * Z))
    # the glyph, from the font file
    x0 = (float(d['x_left']) + 0.5) * Z
    y0 = (yb0 + 0.5) * Z + T.BL * T.PXU * Z
    cov = render(ft, order.index(glyph_name(key)), gz.shape, x0, y0)
    fnt = cov > 0.5
    # pale patches shut inside the ink: where the font has ink over them they are flaked
    # ink (counted apart), where the font is open too they are counters
    holes = ndi.binary_fill_holes(ref) & ~ref
    lab, n = ndi.label(holes)
    flaked = 0
    for i in range(1, n + 1):
        h = lab == i
        if (h & fnt).sum() >= 0.6 * h.sum():
            ref[h] = True
            flaked += int(h.sum())
    # leave the joins out: there the stroke is deliberately brought to a standard thickness
    keep = np.ones(gz.shape, dtype=bool)
    band = slice(int((yb0 - 13) * Z), int((yb0 + 14) * Z))
    form = key.split('.')[1]
    cuts = sorted(float(c) for c in d['cuts'])
    if form in ('medi', 'fina'):
        keep[band, int((cuts[-1] - 13) * Z):] = False
    if form in ('init', 'medi'):
        keep[band, :int((cuts[0] + 14) * Z)] = False
    A, B = fnt & keep, ref & keep
    inter, union = (A & B).sum(), (A | B).sum()
    eA = A & ~ndi.binary_erosion(A) & keep
    eB = B & ~ndi.binary_erosion(B) & keep
    eA &= ndi.binary_erosion(keep, structure=T.disk(2))
    eB &= ndi.binary_erosion(keep, structure=T.disk(2))
    dB = ndi.distance_transform_edt(~eB) / Z
    dA = ndi.distance_transform_edt(~eA) / Z
    sgn = (ndi.distance_transform_edt(~B) - ndi.distance_transform_edt(B)) / Z   # + outside the ink
    dist = np.concatenate([dB[eA], dA[eB]])
    res = {'key': key, 'iou': inter / max(union, 1), 'edge': float(dist.mean()), 'p95': float(np.percentile(dist, 95)),
           'max': float(dist.max()), 'bias': float(sgn[eA].mean()), 'area': A.sum() / max(B.sum(), 1),
           'flaked': flaked / max(B.sum(), 1), 'ink': dark, 'paper': paper, 'thr': float(np.median(half[m2]))}
    if out_dir:
        rz = np.stack([enlarge(unshear(rgb[..., k], ybase)[0], order=1) for k in range(3)], axis=-1)
        rz = np.clip(rz, 0, 255).astype(np.uint8)
        over = rz.copy()
        over[eB] = (0, 200, 255)             # outline of the ink
        over[eA] = (255, 30, 30)             # outline of the font
        diff = np.full(rz.shape, 245, dtype=np.uint8)
        diff[A & B] = (60, 40, 24)           # both
        diff[B & ~A] = (0, 150, 255)         # ink the font lacks
        diff[A & ~B] = (255, 60, 40)         # font where there is no ink
        diff[~keep] = (225, 225, 225)
        ys, xs = np.where(A | B)
        if len(ys):
            pad = 6 * Z
            sl = (slice(max(ys.min() - pad, 0), ys.max() + pad), slice(max(xs.min() - pad, 0), xs.max() + pad))
            gap = np.full((rz[sl].shape[0], 2 * Z, 3), 255, dtype=np.uint8)
            trip = Image.fromarray(np.hstack([rz[sl], gap, over[sl], gap, diff[sl]]))
            if full_res:
                trip.save(os.path.join(out_dir, key + '.png'))
            f = min(1.0, 1500 / trip.width, 520 / trip.height)       # a copy small enough to keep with the font
            trip.resize((int(trip.width * f), int(trip.height * f)), Image.LANCZOS).save(
                os.path.join(out_dir, key + '.jpg'), quality=86)
    return res


def main():
    font, dump, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    only = sys.argv[4].split(',') if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    full_res = len(sys.argv) > 5 and sys.argv[5] == 'png'
    os.makedirs(out_dir, exist_ok=True)
    order = TTFont(font).getGlyphOrder()
    ft = freetype.Face(font)
    ft.set_pixel_sizes(0, int(round(1000 * T.PXU * Z)))
    rows = []
    for path in sorted(glob.glob(os.path.join(dump, '*.npz'))):
        key = os.path.basename(path)[:-4]
        if only and key not in only:
            continue
        rows.append(audit_one(ft, order, key, np.load(path), out_dir, full_res))
    print('%-14s %6s %6s %6s %6s %7s %6s   %s' % ('glyph', 'IoU', 'edge', 'p95', 'max', 'bias', 'area', 'ink/paper/half'))
    for r in rows:
        print('%-14s %6.3f %6.2f %6.2f %6.2f %+7.2f %6.3f   %3.0f/%3.0f/%3.0f' % (
            r['key'], r['iou'], r['edge'], r['p95'], r['max'], r['bias'], r['area'], r['ink'], r['paper'], r['thr']))
    f = lambda k: float(np.mean([r[k] for r in rows]))
    print('%-14s %6.3f %6.2f %6.2f %6.2f %+7.2f %6.3f' % ('MEAN', f('iou'), f('edge'), f('p95'), f('max'), f('bias'), f('area')))
    mean = {k: round(f(k), 4) for k in ('iou', 'edge', 'p95', 'max', 'bias', 'area')}
    json.dump({'font': os.path.basename(font), 'glyphs': len(rows), 'mean': mean,
               'rows': [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows]},
              open(os.path.join(out_dir, 'audit.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
