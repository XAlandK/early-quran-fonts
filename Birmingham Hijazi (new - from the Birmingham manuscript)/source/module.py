#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
How large is the writing on a page, compared with the Birmingham pages?

The scribe did not write every leaf at the same size: on some of the Paris
leaves the letters are smaller and the pen finer.  A letter taken from such a
page has to be enlarged before it can stand next to the Birmingham letters.

The size is measured with the letters themselves.  A few Birmingham letters
that are frequent and easy to tell apart (from traced.json) are laid over the
whole page at a range of sizes; at each size the best places are found by
normalised cross-correlation, and the size at which the letters fit the page
best is the size of its writing.  Two figures are printed: the size at which
all the letters together fit best, and the middle of the sizes at which the
single letters fit best.  On the two Birmingham pages themselves they are
1.00 / 1.01 and 0.98 / 0.97.  The single letters scatter by about a tenth, so
the result is good to a few hundredths where the two figures agree (folios 71,
75, 77: 0.89 / 0.89, 0.83 / 0.82, 0.85 / 0.85) and is not to be relied on where
they do not (the fragment folio 78: 0.76 / 0.93).  variation.py checks the
result against the traced letters.

Usage:  python module.py <page key> [<page key> ...]
        (the pages are taken at the plain scale of pages.py, without pages.MODULE)
Needs:  numpy, pillow, scipy, scikit-image, shapely
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely import wkt
from skimage.feature import match_template

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pages as PG  # noqa: E402
import tracer as T  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LETTERS = ('WAW.isol', 'LAMALEF.isol', 'MEEM.init', 'HEH.fina', 'QAF.init', 'KAF.fina', 'DAL.isol', 'AIN.init')
SIZES = np.round(np.arange(0.76, 1.241, 0.03), 2)
TOP = 6                         # the best places of a letter that count


def template(geom, size):
    """A letter as a picture (1 = ink), at `size` times its size in the Birmingham photograph."""
    s = T.PXU * size * 2                                   # drawn twice as large, then halved
    x0, y0, x1, y1 = geom.bounds
    pad = 8
    im = Image.new('L', (int((x1 - x0) * s) + 4 * pad, int((y1 - y0) * s) + 4 * pad), 0)
    d = ImageDraw.Draw(im)
    tr = lambda x, y: ((x - x0) * s + 2 * pad, (y1 - y) * s + 2 * pad)
    for p in ([geom] if geom.geom_type == 'Polygon' else geom.geoms):
        d.polygon([tr(x, y) for x, y in p.exterior.coords], fill=255)
        for hole in p.interiors:
            d.polygon([tr(x, y) for x, y in hole.coords], fill=0)
    im = im.resize((im.width // 2, im.height // 2), Image.BOX)
    return np.asarray(im, dtype=np.float32) / 255


def darkness(rgb):
    """The page as 'how much ink' (0 parchment .. 1 ink), so that pale and dark pages compare."""
    g = rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    gs = ndi.gaussian_filter(g, 0.7)
    paper = ndi.percentile_filter(gs[::4, ::4], 80, size=41)
    paper = np.asarray(Image.fromarray(paper).resize(gs.shape[::-1], Image.BILINEAR))
    ink = np.percentile(gs[gs < paper - 45], 30) if (gs < paper - 45).any() else 80.0
    return np.clip((paper - gs) / np.maximum(paper - ink, 30), 0, 1)


def measure(key, traced):
    path, scale = PG.source(key, plain=True)
    im = Image.open(path).convert('RGB')
    if scale != 1.0:
        im = im.resize((int(round(im.width * scale)), int(round(im.height * scale))), Image.LANCZOS)
    rgb = np.asarray(im)
    if key in ('L', 'R'):                                  # the two pages of the Birmingham photograph
        half = rgb.shape[1] // 2
        rgb = rgb[:, :half] if key == 'L' else rgb[:, half:]
    page = darkness(rgb)
    score = np.zeros((len(LETTERS), len(SIZES)))
    for a, name in enumerate(LETTERS):
        geom = wkt.loads(traced[name]['wkt'])
        for b, size in enumerate(SIZES):
            r = match_template(page, template(geom, size))
            best = []
            for _ in range(TOP):                           # the best places, each counted once
                i, j = np.unravel_index(np.argmax(r), r.shape)
                best.append(r[i, j])
                r[max(i - 25, 0):i + 26, max(j - 25, 0):j + 26] = -1
            score[a, b] = np.mean(best)
    return score


def peak(curve):
    """Size at the top of a curve of scores, between the sizes tried (parabola through the top three)."""
    k = int(np.argmax(curve))
    if 0 < k < len(curve) - 1:
        a, b, c = curve[k - 1:k + 2]
        k = k + 0.5 * (a - c) / (a - 2 * b + c)
    return float(np.interp(k, np.arange(len(SIZES)), SIZES))


def main():
    traced = json.load(open(os.path.join(HERE, 'traced.json'), encoding='utf-8'))
    for key in sys.argv[1:]:
        score = measure(key, traced)
        each = [peak(score[a]) for a in range(len(LETTERS))]
        print('%-6s the writing is %.2f the size of the Birmingham letters  (middle of the single letters %.2f:'
              ' %s)' % (key, peak(score.mean(axis=0)), np.median(each), ' '.join('%.2f' % e for e in each)))


if __name__ == '__main__':
    main()
