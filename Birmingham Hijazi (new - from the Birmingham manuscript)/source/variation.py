#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
How typical is the exemplar the font uses for each letter form?

The scribe never wrote a letter twice in exactly the same way.  This script
takes every traced instance of a form (the one the font uses and all the
alternatives marked '#' in exemplars.py, on every page), lays each pair over
each other at the best shift, and measures how far their outlines are apart,
in pixels of the Birmingham photograph (the median over both outlines, so
that a joining stroke cut a little longer or shorter does not count).

For each form it reports
  n        how many instances were traced
  scribe   the typical distance between two instances written by the scribe
  used     the typical distance from the font's exemplar to the others
  best     the same for the most central instance (the medoid), and which it is
  rank     where the font's exemplar stands among the n (1 = the most central)

Usage:  python variation.py <traced.json.alts> [out.json] [picture folder]
Needs:  numpy, pillow, scipy, shapely
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely import wkt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pages as PG  # noqa: E402
import tracer as T  # noqa: E402

Z = 2                      # samples per pixel of the photograph
PAD = 60                   # px of room around a glyph, for the shifts
SX, SY = 36, 8             # shifts tried, in px of the photograph


def raster(geom):
    """Mask of an outline given in font units, Z samples per px, and where unit (0, BL) falls in it."""
    x0, y0, x1, y1 = geom.bounds
    s = T.PXU * Z
    w = int((x1 - x0) * s) + 2 * PAD * Z
    h = int((y1 - y0) * s) + 2 * PAD * Z
    im = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(im)
    tr = lambda x, y: ((x - x0) * s + PAD * Z, (y1 - y) * s + PAD * Z)
    for p in ([geom] if geom.geom_type == 'Polygon' else geom.geoms):
        d.polygon([tr(x, y) for x, y in p.exterior.coords], fill=1)
        for hole in p.interiors:
            d.polygon([tr(x, y) for x, y in hole.coords], fill=0)
    m = np.asarray(im) > 0
    return m, tr(0, T.BL)


class Inst:
    def __init__(self, key, rec):
        self.key = key
        self.src = rec['src']
        self.adv = rec['adv']
        self.mask, self.origin = raster(wkt.loads(rec['wkt']))
        edge = self.mask & ~ndi.binary_erosion(self.mask)
        self.ey, self.ex = np.nonzero(edge)
        self.dt = ndi.distance_transform_edt(~edge).astype(np.float32) / Z
        geom = wkt.loads(rec['wkt'])
        self.height = (geom.bounds[3] - geom.bounds[1]) * T.PXU          # px of the photograph
        self.stroke = 2 * geom.area / geom.length * T.PXU                # mean thickness of its strokes


def dist(a, b, form):
    """Median distance between the outlines of two instances at the best shift (px)."""
    # start with the two glyphs on a common point: the right cut for forms joined on the
    # right, the left cut for initial forms, the middle of the letter for isolated ones
    if form in ('fina', 'medi'):
        ax, bx = a.origin[0] + a.adv * T.PXU * Z, b.origin[0] + b.adv * T.PXU * Z
    elif form == 'init':
        ax, bx = a.origin[0], b.origin[0]
    else:
        ax, bx = a.ex.mean(), b.ex.mean()
    ox, oy = bx - ax, b.origin[1] - a.origin[1]                 # a's sample (x, y) lies at (x + ox, y + oy) in b
    best = None
    for step, (rx, ry) in ((2 * Z, (SX * Z, SY * Z)), (1, (2 * Z, 2 * Z))):
        cx, cy = (0, 0) if best is None else best[1]
        for dy in range(cy - ry, cy + ry + 1, step):
            for dx in range(cx - rx, cx + rx + 1, step):
                # a's outline in b's distance map, and b's outline in a's
                xa = np.clip((a.ex + ox + dx).round().astype(int), 0, b.dt.shape[1] - 1)
                ya = np.clip((a.ey + oy + dy).round().astype(int), 0, b.dt.shape[0] - 1)
                xb = np.clip((b.ex - ox - dx).round().astype(int), 0, a.dt.shape[1] - 1)
                yb = np.clip((b.ey - oy - dy).round().astype(int), 0, a.dt.shape[0] - 1)
                d = float(np.median(np.concatenate([b.dt[ya, xa], a.dt[yb, xb]])))
                if best is None or d < best[0]:
                    best = (d, (dx, dy))
    return best


def overlay(a, b, shift, form, path):
    """Picture of two instances over each other: a in red, b in blue, both in dark."""
    if form in ('fina', 'medi'):
        ax, bx = a.origin[0] + a.adv * T.PXU * Z, b.origin[0] + b.adv * T.PXU * Z
    elif form == 'init':
        ax, bx = a.origin[0], b.origin[0]
    else:
        ax, bx = a.ex.mean(), b.ex.mean()
    ox, oy = int(round(bx - ax + shift[0])), int(round(b.origin[1] - a.origin[1] + shift[1]))
    h, w = b.mask.shape
    am = np.zeros((h, w), bool)
    ys, xs = np.nonzero(a.mask)
    ok = (ys + oy >= 0) & (ys + oy < h) & (xs + ox >= 0) & (xs + ox < w)
    am[ys[ok] + oy, xs[ok] + ox] = True
    im = np.full((h, w, 3), 250, np.uint8)
    im[am & ~b.mask] = (235, 70, 50)
    im[b.mask & ~am] = (40, 130, 235)
    im[am & b.mask] = (60, 40, 24)
    ys, xs = np.nonzero(am | b.mask)
    Image.fromarray(im[max(ys.min() - 8, 0):ys.max() + 9, max(xs.min() - 8, 0):xs.max() + 9]).save(path)


def main():
    alts = json.load(open(sys.argv[1], encoding='utf-8'))
    used = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'traced.json'), encoding='utf-8'))
    out_json = sys.argv[2] if len(sys.argv) > 2 else None
    pic = sys.argv[3] if len(sys.argv) > 3 else None
    if pic:
        os.makedirs(pic, exist_ok=True)
    forms = defaultdict(list)
    for k, rec in alts.items():
        forms[k.split('@')[0]].append(Inst(k, rec))
    rows = []
    left_out = 0
    cross = []                                     # (within Birmingham, Birmingham against Paris) per form
    size = {}                                      # page -> (height, stroke) of its letters / Birmingham's
    print('%-13s %3s %7s %6s %6s %5s   %s' % ('form', 'n', 'scribe', 'used', 'best', 'rank', 'most central instance'))
    for name in sorted(forms):
        inst = forms[name]
        form = name.split('.')[1]
        # alternatives are not cleaned by hand: leave out those whose tracing clearly failed
        # (a sliver, or a letter fused with its neighbour), judged by the area of their ink
        area = np.array([a.mask.sum() for a in inst], dtype=float)
        ref = area[[i for i, a in enumerate(inst) if name in used and a.src == used[name]['src']] or
                   list(range(len(inst)))].mean()
        keep = (area > 0.5 * ref) & (area < 1.9 * ref)
        left_out += int((~keep).sum())
        inst = [a for a, k in zip(inst, keep) if k]
        n = len(inst)
        me = [i for i, a in enumerate(inst) if name in used and a.src == used[name]['src']]
        if n < 2 or not me:
            rows.append({'form': name, 'n': n})
            print('%-13s %3d' % (name, n))
            continue
        D = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                d = dist(inst[i], inst[j], form)[0]
                D[i, j] = D[j, i] = d
        typ = np.array([np.median(np.delete(D[i], i)) for i in range(n)])     # each instance against the others
        bh = [i for i, a in enumerate(inst) if a.src['page'] in ('L', 'R')]
        pa = [i for i, a in enumerate(inst) if a.src['page'] not in ('L', 'R')]
        if len(bh) >= 2 and pa:                       # do the Paris leaves show the same letter?
            within = [D[i, j] for i in bh for j in bh if i < j]
            across = [D[i, j] for i in bh for j in pa]
            cross.append((name, len(bh), len(pa), float(np.median(within)), float(np.median(across))))
            h, w = np.median([inst[i].height for i in bh]), np.median([inst[i].stroke for i in bh])
            for i in pa:                              # ... at the same size and with the same pen?
                size.setdefault(inst[i].src['page'], []).append((inst[i].height / h, inst[i].stroke / w))
        order = np.argsort(typ)
        u = me[0]
        row = {'form': name, 'n': n, 'scribe': round(float(np.median(D[np.triu_indices(n, 1)])), 2),
               'used': round(float(typ[u]), 2), 'best': round(float(typ[order[0]]), 2),
               'rank': int(np.where(order == u)[0][0]) + 1, 'medoid': inst[order[0]].key,
               'pages': sorted(set(a.src['page'] for a in inst))}
        rows.append(row)
        print('%-13s %3d %7.2f %6.2f %6.2f %2d/%-2d   %s' % (name, n, row['scribe'], row['used'], row['best'],
                                                           row['rank'], n, row['medoid'] if order[0] != u else '(the one used)'))
        if pic and order[0] != u:                    # the one used in red, the most central in blue
            a, b = inst[u], inst[int(order[0])]
            overlay(a, b, dist(a, b, form)[1], form, os.path.join(pic, name + '.png'))
    if cross:
        print()
        print('the same letter on the Birmingham pages and on the Paris leaves (median distance, px):')
        print('%-13s %5s %5s %9s %9s' % ('form', 'Bham', 'Paris', 'Bham-Bham', 'Bham-Paris'))
        for name, nb, np_, w, a in cross:
            print('%-13s %5d %5d %9.2f %9.2f' % (name, nb, np_, w, a))
        print('%-13s %5s %5s %9.2f %9.2f   (median of the forms)' % ('', '', '', np.median([c[3] for c in cross]),
                                                                    np.median([c[4] for c in cross])))
        print()
        print('letters of each Paris page against the same letters in Birmingham (1.00 = the same):')
        for pg in sorted(size):
            v = np.array(size[pg])
            print('  %s  %2d letters   height %.2f   thickness of the strokes %.2f%s' % (
                pg, len(v), np.median(v[:, 0]), np.median(v[:, 1]),
                '   (page enlarged by %.2f)' % (1 / PG.module(pg)) if PG.module(pg) != 1 else ''))
        print()
    print('instances left out because their tracing failed: %d' % left_out)
    ok = [r for r in rows if 'used' in r]
    summary = {'instances': len(alts), 'left_out': left_out, 'forms': len(ok),
               'scribe': round(float(np.median([r['scribe'] for r in ok])), 2),
               'font': round(float(np.median([r['used'] for r in ok])), 2)}
    if cross:
        summary.update(cross_forms=len(cross), cross_paris=int(sum(c[2] for c in cross)),
                       within=round(float(np.median([c[3] for c in cross])), 2),
                       across=round(float(np.median([c[4] for c in cross])), 2))
    print('forms with other instances: %d;  scribe against scribe %.2f px;  font against scribe %.2f px' % (
        len(ok), summary['scribe'], summary['font']))
    if out_json:
        json.dump({'summary': summary, 'rows': rows,
                   'cross': [dict(zip(('form', 'bham', 'paris', 'within', 'across'), c)) for c in cross],
                   'pages': {pg: {'letters': len(v), 'height': round(float(np.median([a for a, _ in v])), 2),
                                  'stroke': round(float(np.median([b for _, b in v])), 2),
                                  'enlarged': round(1 / PG.module(pg), 3)} for pg, v in sorted(size.items())}},
                  open(out_json, 'w'), indent=1)


if __name__ == '__main__':
    main()
