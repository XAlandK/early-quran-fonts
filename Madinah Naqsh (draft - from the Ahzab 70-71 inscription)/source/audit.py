#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Audit: every traced glyph of the built font, laid over the carving of the exemplar it was
traced from, at the same place and scale.

The font does not copy the edge of the carving in the photograph (that edge is mostly
blur); it draws the centre line of every stroke at a measured width.  So two things are
checked, both against the brightness of the photograph, which the tracer did not use to
find the centre lines (it used brightness and colour together):

  crest   how far the centre line of the font lies from the brightest line of the stroke
          in the photograph: at every two pixels along every centre line the brightness is
          read across it, and the distance to its top is taken.
  edge    how far the outline of the font lies from the outline of the carving at the grey
          half-way between the rock and the top of the stroke (worked out here, on its own).
          The glyph is rendered from the .ttf itself, widened again by what the line of the
          inscription was narrowed by, so the check covers tracing, widths, the conversion
          to TrueType curves and the build.

For each glyph it reports, in pixels of the photograph:
  crest  mean distance of the centre line from the top of the stroke;  c95: 95 % within
  edge   mean distance between the outline of the font and the outline of the carving
  p95    the distance that 95 % of the outline stays within
  bias   mean signed distance (+ the font is fatter than the carving, - thinner)
  area   area of the font glyph / area of the carving

For each glyph it also writes a picture of three panels: the exemplar in the photograph;
the same with the outline of the carving (light blue) and, over it, the outline of the
font (red); and the difference (dark: both, blue: carving the font lacks, red: font where
there is no carving, grey: the joins, left out).

Usage:  python audit.py <font.ttf> <traced.json> <dump_dir> <out_dir> [keys|-] [png]
        (dump_dir is written by:  python tracer.py page.png lines.json traced.json - - dump_dir;
         'png' also keeps the pictures at full size)
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


def half_level(lum, mask, ink):
    """Brightness of the rock around this letter, and, for every place, the brightness
    half-way between it and the top of the stroke there.  Worked out here on its own."""
    ls = ndi.gaussian_filter(lum, 0.6)
    ring = ndi.binary_dilation(mask, structure=T.disk(14)) & ~ndi.binary_dilation(ink | mask, structure=T.disk(4))
    rock = float(np.percentile(ls[ring], 40)) if ring.sum() > 50 else float(np.percentile(ls, 30))
    top = ndi.maximum_filter(np.where(mask, ls, -1e9), size=21)
    top = ndi.gaussian_filter(np.maximum(top, rock + 30), 2.0)
    return rock, rock + 0.5 * (top - rock)


def crest_offset(rec, d):
    """Distances (px of the page) between the centre lines of the font and the top of the
    brightness of the stroke, read across every centre line."""
    lum = ndi.gaussian_filter(d['lum'], 0.6)
    ybase, x_left, sq = d['ybase'], float(d['x_left']), float(d['squeeze'])
    mask, ink = d['mask'], d['ink']
    ring = ndi.binary_dilation(mask, structure=T.disk(14)) & ~ndi.binary_dilation(ink | mask, structure=T.disk(4))
    rock = float(np.percentile(lum[ring], 40)) if ring.sum() > 50 else float(np.percentile(lum, 30))
    t = np.arange(-5, 5.01, 0.25)
    out = []
    for pts in rec['paths']:
        u = np.asarray(pts, dtype=float)
        x = x_left + u[:, 0] * T.PXU / sq
        y = np.interp(x, np.arange(len(ybase)), ybase) - (u[:, 1] - T.BL) * T.PXU
        seg = np.hypot(np.diff(x), np.diff(y))
        s = np.concatenate([[0], np.cumsum(seg)])
        for at in np.arange(9.0, s[-1] - 9.0, 2.0):
            cx, cy = np.interp(at, s, x), np.interp(at, s, y)
            dx = np.interp(at + 2, s, x) - np.interp(at - 2, s, x)
            dy = np.interp(at + 2, s, y) - np.interp(at - 2, s, y)
            L = np.hypot(dx, dy)
            if L < 1e-6:
                continue
            yy, xx = cy + t * dx / L, cx - t * dy / L
            if yy.min() < 0 or xx.min() < 0 or yy.max() > lum.shape[0] - 1 or xx.max() > lum.shape[1] - 1:
                continue
            p = ndi.map_coordinates(lum, [yy, xx], order=3)
            k = int(np.argmax(p))
            if p[k] - rock < 25 or k in (0, len(p) - 1):       # too faint, or the top is another stroke's
                continue
            near = p >= p[k] - 0.08 * (p[k] - rock)             # a flat top has no one highest point:
            out.append(abs(float(t[near].mean())))              # the middle of what is as bright as the top
    return out


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


def audit_one(ft, order, key, rec, d, out_dir=None, full_res=False):
    lum, mask, ink, rgb = d['lum'], d['mask'], d['ink'], d['rgb']
    ybase = d['ybase']
    l2, yb0 = unshear(lum, ybase)
    m2 = unshear(mask.astype(np.float32), ybase)[0] > 0.5
    i2 = unshear(ink.astype(np.float32), ybase)[0] > 0.5
    rock, half = half_level(l2, m2, i2)
    lz = enlarge(ndi.gaussian_filter(l2, 0.5))
    mz = enlarge(m2.astype(np.float32), order=1) > 0.5
    others = enlarge((i2 & ~ndi.binary_dilation(m2, structure=T.disk(2))).astype(np.float32), order=1) > 0.5
    region = ndi.binary_dilation(mz, structure=T.disk(int(2.5 * Z))) & ~ndi.binary_dilation(others, structure=T.disk(Z))
    ref = (lz > enlarge(half, order=1)) & region
    ref = ndi.binary_closing(ref, structure=T.disk(1.0 * Z))
    # the glyph, from the font file, as wide again as it stands in the photograph
    x0 = (float(d['x_left']) + 0.5) * Z
    y0 = (yb0 + 0.5) * Z + T.BL * T.PXU * Z
    cov = render(ft, order.index(glyph_name(key)), lz.shape, x0, y0)
    fnt = cov > 0.5
    # leave the joins out: there the stroke is brought to the width of a level stroke
    keep = np.ones(lz.shape, dtype=bool)
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
    sgn = (ndi.distance_transform_edt(~B) - ndi.distance_transform_edt(B)) / Z   # + outside the carving
    dist = np.concatenate([dB[eA], dA[eB]])
    sc = float(d['scale'])                                   # page px per px of the photograph
    off = np.array(crest_offset(rec, d)) / sc
    res = {'key': key, 'scale': sc, 'squeeze': float(d['squeeze']),
           'crest': float(off.mean()) if len(off) else float('nan'),
           'c95': float(np.percentile(off, 95)) if len(off) else float('nan'), 'readings': int(len(off)),
           'edge': float(dist.mean()) / sc, 'p95': float(np.percentile(dist, 95)) / sc, 'max': float(dist.max()) / sc,
           'iou': inter / max(union, 1), 'bias': float(sgn[eA].mean()) / sc, 'area': A.sum() / max(B.sum(), 1)}
    if out_dir:
        rz = np.stack([enlarge(unshear(rgb[..., k], ybase)[0], order=1) for k in range(3)], axis=-1)
        rz = np.clip(rz, 0, 255).astype(np.uint8)
        over = rz.copy()
        over[eB] = (0, 200, 255)             # outline of the carving
        over[eA] = (255, 30, 30)             # outline of the font
        diff = np.full(rz.shape, 245, dtype=np.uint8)
        diff[A & B] = (60, 40, 24)           # both
        diff[B & ~A] = (0, 150, 255)         # carving the font lacks
        diff[A & ~B] = (255, 60, 40)         # font where there is no carving
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
    font, traced, dump, out_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    only = sys.argv[5].split(',') if len(sys.argv) > 5 and sys.argv[5] != '-' else None
    full_res = len(sys.argv) > 6 and sys.argv[6] == 'png'
    os.makedirs(out_dir, exist_ok=True)
    order = TTFont(font).getGlyphOrder()
    recs = json.load(open(traced, encoding='utf-8'))
    rows = []
    for path in sorted(glob.glob(os.path.join(dump, '*.npz'))):
        key = os.path.basename(path)[:-4]
        if only and key not in only:
            continue
        d = np.load(path)
        ft = freetype.Face(font)                       # as wide again as the line stands in the photograph
        ft.set_pixel_sizes(int(round(1000 * T.PXU * Z / float(d['squeeze']))), int(round(1000 * T.PXU * Z)))
        rows.append(audit_one(ft, order, key, recs[key], d, out_dir, full_res))
    print('in pixels of the photograph:')
    print('%-14s %6s %6s %6s %6s %6s %7s %6s %6s' % ('glyph', 'crest', 'c95', 'edge', 'p95', 'max', 'bias', 'area', 'IoU'))
    for r in rows:
        print('%-14s %6.2f %6.2f %6.2f %6.2f %6.2f %+7.2f %6.3f %6.3f' % (
            r['key'], r['crest'], r['c95'], r['edge'], r['p95'], r['max'], r['bias'], r['area'], r['iou']))
    f = lambda k: float(np.nanmean([r[k] for r in rows]))
    print('%-14s %6.2f %6.2f %6.2f %6.2f %6.2f %+7.2f %6.3f %6.3f' % (
        'MEAN', f('crest'), f('c95'), f('edge'), f('p95'), f('max'), f('bias'), f('area'), f('iou')))
    mean = {k: round(f(k), 4) for k in ('crest', 'c95', 'edge', 'p95', 'max', 'bias', 'area', 'iou')}
    json.dump({'font': os.path.basename(font), 'glyphs': len(rows), 'mean': mean,
               'rows': [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows]},
              open(os.path.join(out_dir, 'audit.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
