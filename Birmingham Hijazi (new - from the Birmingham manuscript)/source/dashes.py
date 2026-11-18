#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
The dots of the manuscript.

The scribe writes a dot as a short slanted dash, and two or three dots as
dashes stacked one over the other; clusters of the same dashes close a verse.
This script finds the dashes that stand free on the two pages of the
Birmingham photograph, measures them (length, thickness, slant, how far
stacked dashes are apart, in the dots of a letter and in the mark that closes
a verse, and how far a dash stands from its letter), picks the
dash that is nearest to the median in all three measures, traces its outline in
the same way as the letters, and writes dash.json for build.py.  Only dashes
of dark, whole ink are candidates for tracing (ink at least 110 grey levels
darker than the parchment, outline at least 93 % of its convex hull).

Usage:  python dashes.py [manuscript/full.jpg] [dash.json] [picture.png]
Needs:  numpy, pillow, scipy, scikit-image, shapely
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from skimage import measure
from skimage.morphology import convex_hull_image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tracer as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
K = T.K


def axes(mask, k=1):
    """Length, thickness and slant (degrees, up to the right) of a mask."""
    ys, xs = np.nonzero(mask)
    q = np.stack([xs, -ys], 1).astype(float) / k
    q -= q.mean(0)
    ev, evec = np.linalg.eigh(np.cov(q.T))
    v = evec[:, 1] if evec[0, 1] >= 0 else -evec[:, 1]
    return float(np.ptp(q @ v)), float(np.ptp(q @ evec[:, 0])), float(np.degrees(np.arctan2(v[1], v[0])))


def fine(crop, m):
    """The dash K times finer, cut at the grey half-way between its ink and the parchment;
    and how much darker than the parchment its ink is."""
    dark = np.percentile(crop[m], 20)
    paper = np.median(crop[~ndi.binary_dilation(m, iterations=3)])
    if paper - dark < 50:
        return None, 0.0
    big = T.enlarge(crop, 3) < (dark + paper) / 2
    lab, n = ndi.label(big)
    if not n:
        return None, 0.0
    keep = np.argmax(ndi.sum(big, lab, np.arange(1, n + 1))) + 1
    return lab == keep, float(paper - dark)


def find(path):
    rgb = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    g = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    gs = ndi.gaussian_filter(g, 0.6)
    H, W = g.shape
    paper = ndi.percentile_filter(gs[::4, ::4], 80, size=41)
    paper = np.asarray(Image.fromarray(paper).resize((W, H), Image.BILINEAR))
    ink = gs < (paper + 70) / 2
    lab, n = ndi.label(ink)
    boxes = ndi.find_objects(lab)
    area = ndi.sum(ink, lab, np.arange(1, n + 1))
    letters = np.isin(lab, np.nonzero(area > 400)[0] + 1)           # ink too large to be a dash
    free, small = [], []
    for i, (s, a) in enumerate(zip(boxes, area), 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        if not (35 <= a <= 330 and max(h, w) <= 48 and min(h, w) >= 5):
            continue
        cy, cx = ndi.center_of_mass(lab[s] == i)
        if w >= 1.3 * h:
            small.append((s[1].start + cx, s[0].start + cy))
        r0, r1 = max(s[0].start - 6, 0), min(s[0].stop + 6, H)
        c0, c1 = max(s[1].start - 6, 0), min(s[1].stop + 6, W)
        m = lab[r0:r1, c0:c1] == i
        if (lab[r0:r1, c0:c1] > 0).sum() > 1.15 * m.sum():           # something else in its box
            continue
        f, contrast = fine(gs[r0:r1, c0:c1], m)
        if f is None:
            continue
        L, Tk, ang = axes(f, K)
        if L / Tk < 1.7:
            continue
        # how far the dash stands from the letter it belongs to: the nearer of the ink above and below
        x = int(round(s[1].start + cx))
        col = letters[:, max(x - 4, 0):x + 5].any(axis=1)
        up = np.nonzero(col[:s[0].start][::-1])[0]
        dn = np.nonzero(col[s[0].stop:])[0]
        gaps = [int(v[0]) for v in (up, dn) if len(v)]
        free.append({'x': s[1].start + cx, 'y': s[0].start + cy, 'len': L, 'thick': Tk, 'angle': ang,
                     'gap': min(gaps) if gaps else None, 'box': (r0, r1, c0, c1), 'mask': f, 'grey': gs[r0:r1, c0:c1],
                     'contrast': contrast, 'solid': float(f.sum() / convex_hull_image(f).sum())})
    small = np.array(small)
    # dashes that belong together (within 30 px of each other): two or three are the dots
    # of a letter, four to six close a verse
    group = list(range(len(small)))

    def root(a):
        while group[a] != a:
            group[a] = group[group[a]]
            a = group[a]
        return a

    for i in range(len(small)):
        near = np.nonzero(np.hypot(*(small[i + 1:] - small[i]).T) < 30)[0] + i + 1
        for j in near:
            group[root(int(j))] = root(i)
    members = {}
    for i in range(len(small)):
        members.setdefault(root(i), []).append(i)
    stack, rows, cols = [], [], []
    for m in members.values():
        p = small[m]
        for (x, y) in p:
            dx, dy = p[:, 0] - x, p[:, 1] - y
            below = (dy > 5) & (np.abs(dx) < 13)
            beside = (dx > 12) & (np.abs(dy) < 12)
            if below.any():
                j = np.nonzero(below)[0][np.argmin(np.hypot(dx[below], dy[below]))]
                (stack if len(m) <= 3 else rows if len(m) <= 6 else []).append((dx[j], dy[j]))
            if beside.any() and 4 <= len(m) <= 6:
                j = np.nonzero(beside)[0][np.argmin(np.hypot(dx[beside], dy[beside]))]
                cols.append((dx[j], dy[j]))
    return free, np.array(stack), np.array(rows), np.array(cols)


def outline(mask):
    """Outline of a fine mask in font units, about its own centre, smoothed like the letters."""
    pad = 3 * K
    F = ndi.gaussian_filter(np.pad(mask.astype(np.float32), pad), 0.45 * K)
    cont = max(measure.find_contours(F, 0.5), key=len)
    ys, xs = np.nonzero(mask)
    cx, cy = xs.mean(), ys.mean()
    poly = Polygon([((j - pad - cx) / K / T.PXU, (cy - (i - pad)) / K / T.PXU) for i, j in cont]).buffer(0)
    return T.smooth_geom(poly, 4).simplify(0.4)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'manuscript', 'full.jpg')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'dash.json')
    free, stack, rows, cols = find(path)
    med = {k: float(np.median([d[k] for d in free])) for k in ('len', 'thick', 'angle')}
    iqr = {k: [float(v) for v in np.percentile([d[k] for d in free], [25, 75])] for k in ('len', 'thick', 'angle')}
    gaps = [d['gap'] for d in free if d['gap'] is not None and d['gap'] < 40]
    score = lambda d: sum(abs(d[k] - med[k]) / (iqr[k][1] - iqr[k][0]) for k in med)
    clean = [d for d in free if d['contrast'] >= 110 and d['solid'] >= 0.93]
    best = min(clean, key=score)
    geom = outline(best['mask'])
    print('%d dashes stand free on the two pages' % len(free))
    print('  length     %.1f px  (half of them between %.1f and %.1f)' % (med['len'], *iqr['len']))
    print('  thickness  %.1f px  (%.1f - %.1f)' % (med['thick'], *iqr['thick']))
    print('  slant      %.1f deg (%.1f - %.1f)' % (med['angle'], *iqr['angle']))
    print('  dots of one letter: the lower dash is %.1f px down and %.1f px to the right (%d pairs)' % (
        np.median(stack[:, 1]), np.median(stack[:, 0]), len(stack)))
    print('  end of a verse: the dash below is %.1f px down and %.1f px to the right (%d pairs),' % (
        np.median(rows[:, 1]), np.median(rows[:, 0]), len(rows)))
    print('                  the dash beside it %.1f px to the right (%d pairs)' % (np.median(cols[:, 0]), len(cols)))
    print('  from the dash to its letter: %.1f px (%d dashes)' % (np.median(gaps), len(gaps)))
    print('the dash traced (the nearest to these among %d dashes of dark, whole ink): at x %.0f, y %.0f of the\n'
          '  photograph; length %.1f, thickness %.1f, slant %.1f' % (
              len(clean), best['x'], best['y'], best['len'], best['thick'], best['angle']))
    json.dump({'wkt': geom.wkt, 'n': len(free), 'length': round(med['len'], 2), 'thickness': round(med['thick'], 2),
               'angle': round(med['angle'], 2), 'stack_down': round(float(np.median(stack[:, 1])), 2),
               'stack_right': round(float(np.median(stack[:, 0])), 2), 'pairs': int(len(stack)),
               'verse_down': round(float(np.median(rows[:, 1])), 2), 'verse_right': round(float(np.median(rows[:, 0])), 2),
               'verse_beside': round(float(np.median(cols[:, 0])), 2),
               'gap': round(float(np.median(gaps)), 2),
               'src': {'x': round(best['x'], 1), 'y': round(best['y'], 1), 'length': round(best['len'], 2),
                       'thickness': round(best['thick'], 2), 'angle': round(best['angle'], 2)}},
              open(out, 'w'), indent=1)
    if len(sys.argv) > 3:                                 # the dash and its outline, enlarged
        r0, r1, c0, c1 = best['box']
        z = 12
        g = np.clip(T.enlarge(best['grey'], 3), 0, 255)
        im = Image.fromarray(g.astype(np.uint8)).resize(((c1 - c0) * z, (r1 - r0) * z), Image.BICUBIC).convert('RGB')
        edge = best['mask'] & ~ndi.binary_erosion(best['mask'])
        e = np.asarray(Image.fromarray((edge * 255).astype(np.uint8)).resize(im.size, Image.NEAREST)) > 0
        a = np.asarray(im).copy()
        a[e] = (255, 30, 30)
        Image.fromarray(a).save(sys.argv[3])


if __name__ == '__main__':
    main()
