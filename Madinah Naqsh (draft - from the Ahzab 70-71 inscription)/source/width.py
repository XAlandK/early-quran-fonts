#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
How wide are the carved strokes, and how unsharp is the photograph?

tracer.py takes the centre line of every stroke from the photograph and gives the stroke
the width that is read across it.  This script makes the same readings over the whole
inscription and sets them out, so that the numbers the tracer works with (LEVEL, BLUR)
can be checked.

  1. Across every centre line, every two page pixels, the brightness of the photograph
     itself is read along the normal (its brightness only: the colour of a JPEG picture is
     stored at half the sharpness, and would make every stroke look wider).  The width of
     the stroke there is the distance between the two points where the brightness is
     half-way between the rock and the top of the stroke ("full width at half height").
     Places where another stroke stands within reach, and the ends and forks of a line,
     are left out.
  2. The photograph is not sharp, and that widens every stroke.  How unsharp it is, is
     measured on the smallest bright specks of the rock: a speck that is a mere point is
     seen as wide as the blur.  A groove of true width w, seen through a blur b, measures
     sqrt(w^2 + b^2) to a good approximation; the true width is taken back from that.

What comes out (px of the photograph):
  * level strokes are 5.8, 4.2 and 3.6 px wide on the three lines.  The lines are enlarged
    2.1, 2.95 and 3.5 times to bring their alifs to one height, which brings these widths
    to 12.2, 12.5 and 12.6 px of the page: one width, tracer.LEVEL = 12.4.
  * upright strokes are about 8 to 9 px wide on every line: the stems of alif and lam and
    the teeth are one and a half times to twice as wide as the level strokes.  That is why
    the tracer reads the width of every stroke instead of drawing all strokes alike.

Usage:  python width.py <traced.json> <dump_dir> [out.json]
        (dump_dir is written by:  python tracer.py page.png lines.json traced.json - - dump_dir)
Needs:  numpy, pillow, scipy
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tracer as T  # noqa: E402

REACH = 8.0         # how far the brightness is read to each side of a centre line (px of the photograph)
STEP = 2.0          # distance between two readings along a line (page px)
SKIP = 12.0         # readings this near an end or a fork of a line are left out (page px)


def blur_of_photograph():
    """Width (full width at half height, px of the photograph) of the blur, from the
    smallest bright specks of the rock.  Returns (along x, along y, number of specks)."""
    g = photograph()
    d = g - ndi.median_filter(g, size=15)
    sm = ndi.gaussian_filter(d, 1.0)
    ys, xs = np.where((sm == ndi.maximum_filter(sm, size=9)) & (sm > 18))

    def fwhm(p, k):
        h = p[k] / 2
        a = k
        while a > 0 and p[a] > h:
            a -= 1
        b = k
        while b < len(p) - 1 and p[b] > h:
            b += 1
        if p[a] > h or p[b] > h:
            return None
        return (b - (h - p[b]) / (p[b - 1] - p[b])) - (a + (h - p[a]) / (p[a + 1] - p[a]))
    out = []
    for y, x in zip(ys, xs):
        if not (10 < y < g.shape[0] - 10 and 10 < x < g.shape[1] - 10):
            continue
        w = d[y - 7:y + 8, x - 7:x + 8]
        if w[5:10, 5:10].max() < 30:
            continue
        iy, ix = np.unravel_index(np.argmax(w[5:10, 5:10]), (5, 5))
        wx, wy = fwhm(w[iy + 5], ix + 5), fwhm(w[:, ix + 5], iy + 5)
        if wx and wy:
            out.append((wx, wy))
    o = np.array(out)
    small = o[np.minimum(o[:, 0], o[:, 1]) < 3.0]           # specks that are a mere point one way at least
    return float(np.percentile(small[:, 0], 25)), float(np.percentile(small[:, 1], 25)), len(small)


def photograph():
    im = np.asarray(Image.open(os.path.join(HERE, 'naqsh', 'photo.jpg')).convert('RGB')).astype(np.float32)
    return im @ np.array([0.299, 0.587, 0.114], dtype=np.float32)


def measure(traced, dump_dir):
    lines = json.load(open(os.path.join(HERE, 'lines.json')))['N']
    lum = photograph()
    rows = []
    for key, rec in sorted(traced.items()):
        path = os.path.join(dump_dir, key + '.npz')
        if key.startswith('_') or not os.path.exists(path):
            continue
        d = np.load(path)
        mask, ink = d['mask'], d['ink']
        L = lines[int(d['line']) - 1]
        scale, th, (ox, oy) = float(L['scale']), float(L['angle']), L['origin']
        cs, sn = np.cos(th), np.sin(th)
        u0, t0 = float(d['u0']), float(d['t0'])

        def to_photo(col, row):
            """(column, row) of the crop of the page -> (x, y) in the photograph"""
            u, t = (u0 + col) / scale, (t0 + row) / scale
            return ox + u * cs - t * sn, oy + u * sn + t * cs

        ring = ndi.binary_dilation(mask, structure=T.disk(14)) & ~ndi.binary_dilation(mask | ink, structure=T.disk(4))
        ry, rx = np.where(ring)
        px, py = to_photo(rx, ry)
        ok = (px > 0) & (px < lum.shape[1] - 1) & (py > 0) & (py < lum.shape[0] - 1)
        rock = float(np.percentile(ndi.map_coordinates(lum, [py[ok], px[ok]], order=1), 40))
        ybase, x_left = d['ybase'], float(d['x_left'])
        t = np.arange(-REACH, REACH + 0.01, 0.1)
        for pts in rec['paths']:
            u = np.asarray(pts, dtype=float)
            x = x_left + u[:, 0] * T.PXU / float(d['squeeze'])
            y = np.interp(x, np.arange(len(ybase)), ybase) - (u[:, 1] - T.BL) * T.PXU
            seg = np.hypot(np.diff(x), np.diff(y))
            s = np.concatenate([[0], np.cumsum(seg)])
            if s[-1] < 2 * SKIP + STEP:
                continue
            for at in np.arange(SKIP, s[-1] - SKIP, STEP):
                x0, y0 = to_photo(np.interp(at, s, x), np.interp(at, s, y))
                xa, ya = to_photo(np.interp(at - 2, s, x), np.interp(at - 2, s, y))
                xb, yb = to_photo(np.interp(at + 2, s, x), np.interp(at + 2, s, y))
                dx, dy = xb - xa, yb - ya
                Ln = np.hypot(dx, dy)
                if Ln < 1e-6:
                    continue
                nx, ny = -dy / Ln, dx / Ln
                yy, xx = y0 + t * ny, x0 + t * nx
                if yy.min() < 0 or xx.min() < 0 or yy.max() > lum.shape[0] - 1 or xx.max() > lum.shape[1] - 1:
                    continue
                p = ndi.map_coordinates(lum, [yy, xx], order=3)
                mid = np.abs(t) <= 1.5
                k = int(np.argmax(np.where(mid, p, -1e9)))
                if p[k] - rock < 25:                         # too faint here to measure
                    continue
                half = rock + 0.5 * (p[k] - rock)
                a = k
                while a > 0 and p[a] > half:
                    a -= 1
                b = k
                while b < len(p) - 1 and p[b] > half:
                    b += 1
                if p[a] > half or p[b] > half:               # another stroke within reach
                    continue
                left = t[a] + (half - p[a]) / (p[a + 1] - p[a]) * 0.1
                right = t[b] - (half - p[b]) / (p[b - 1] - p[b]) * 0.1
                ang = np.degrees(np.arctan2(abs(dy), abs(dx)))
                rows.append((key, int(d['line']), scale, 'level' if ang < 25 else 'upright' if ang > 65 else 'slanting',
                             right - left, (right - left) * scale, float(p[k] - rock)))
    return rows


def main():
    traced = json.load(open(sys.argv[1], encoding='utf-8'))
    rows = measure(traced, sys.argv[2])
    bx, by, n_specks = blur_of_photograph()
    blur = (bx + by) / 2
    print('blur of the photograph: %.2f px along x, %.2f px along y (full width at half height), from %d specks; '
          'taken as %.1f' % (bx, by, n_specks, T.BLUR))
    blur = T.BLUR
    w = np.array([r[4] for r in rows])
    out = {'blur_x': round(bx, 2), 'blur_y': round(by, 2), 'blur_used': blur, 'specks': n_specks,
           'readings': len(rows), 'by': {}}
    print('\nwidth of the strokes at half height, px of the photograph')
    print('%-26s %8s %8s %8s %6s   %10s %10s' % ('', 'median', '25 %', '75 %', 'n', 'less blur', 'px of page'))
    names = {1: 'line 5 (lowest)', 2: 'line 4', 3: 'line 3'}
    for ln in (1, 2, 3):
        for kind in ('level', 'slanting', 'upright'):
            sel = np.array([r[1] == ln and r[3] == kind for r in rows])
            if sel.sum() < 5:
                continue
            m, q1, q3 = np.median(w[sel]), np.percentile(w[sel], 25), np.percentile(w[sel], 75)
            true = float(np.sqrt(max(m * m - blur * blur, 0)))
            sc = rows[int(np.argmax(sel))][2]
            print('%-26s %8.2f %8.2f %8.2f %6d   %10.2f %10.1f' % (names[ln] + ' ' + kind, m, q1, q3, sel.sum(), true, true * sc))
            out['by']['%s %s' % (names[ln], kind)] = {'median': round(float(m), 2), 'q1': round(float(q1), 2),
                                                      'q3': round(float(q3), 2), 'n': int(sel.sum()),
                                                      'true': round(true, 2), 'page': round(true * sc, 1)}
    level = [v['page'] for k, v in out['by'].items() if k.endswith('level')]
    out['level_page'] = round(float(np.mean(level)), 1)
    print('\na level stroke, brought to the size of the page: %s px on the three lines; tracer.LEVEL is %.1f'
          % (', '.join('%.1f' % v for v in level), T.LEVEL))
    if len(sys.argv) > 3:
        json.dump(out, open(sys.argv[3], 'w'), indent=1)
    return rows, blur


if __name__ == '__main__':
    main()
