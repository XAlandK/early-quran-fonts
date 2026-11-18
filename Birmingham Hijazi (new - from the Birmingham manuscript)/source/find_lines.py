#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Find the baseline of every line of a page and add it to lines.json.

The page is cut into upright strips.  In each strip the rows that hold most of
the level strokes are the baselines; the peaks of neighbouring strips are
strung together.  The parchment of the Paris leaves is not flat, so a baseline
is kept as the string of points itself ({"pts": [[x, row], ...]}, at the plain
scale of pages.py); tracer.py
fits a straight line through the points near the word it is cutting out.

Usage:  python find_lines.py <page key> [<page key> ...] [--show <folder>]
Needs:  numpy, pillow, scipy
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.signal import find_peaks

import pages

HERE = os.path.dirname(os.path.abspath(__file__))
STRIP, STEP = 300, 100          # width of a strip and distance between strips (px)
PITCH = 100                     # the least distance between two lines (px)


def ink_of(rgb):
    g = rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    gs = ndi.gaussian_filter(g, 0.8)
    H, W = g.shape
    paper = ndi.percentile_filter(gs[::4, ::4], 80, size=41)
    paper = np.asarray(Image.fromarray(paper).resize((W, H), Image.BILINEAR))
    return gs < np.minimum((paper + 62) / 2, paper - 40)


def find(key):
    ink = ink_of(pages.load(key, plain=True))
    H, W = ink.shape
    level = ndi.binary_opening(ink, structure=np.ones((1, 25), bool))     # strokes that run along the line
    cols = np.where(ink.sum(axis=0) > 0.01 * H)[0]
    xa, xb = int(cols.min()), int(cols.max())
    chains = []                                       # each: list of (x, row)
    for x in range(xa, xb - STRIP // 2, STEP):
        p = ndi.gaussian_filter1d(level[:, x:x + STRIP].sum(axis=1).astype(float), 4)
        if p.max() < 40:
            continue
        pk, _ = find_peaks(p, distance=PITCH, prominence=0.12 * p.max())
        xc = x + STRIP / 2
        for y in pk:
            best = None
            for ch in chains:
                (x1, y1) = ch[-1]
                if xc - x1 > 4 * STEP:
                    continue
                slope = (ch[-1][1] - ch[-3][1]) / (ch[-1][0] - ch[-3][0]) if len(ch) >= 3 else 0.0
                err = abs(y - (y1 + slope * (xc - x1)))
                if err <= 14 and (best is None or err < best[0]):
                    best = (err, ch)
            if best:
                best[1].append((xc, int(y)))
            else:
                chains.append([(xc, int(y))])
    chains = [c for c in chains if len(c) >= 3]
    chains.sort(key=lambda c: -len(c))                # the longest strings first
    merged = []
    for c in chains:                                  # pieces of one line, parted by a gap
        cx, cy = np.array(c).T
        home = None
        for a in merged:
            ax, ay = np.array(a).T
            m, k = np.polyfit(ax, ay, 1) if len(a) >= 6 else (0.0, float(np.median(ay)))
            if np.abs(cy - (m * cx + k)).mean() < 45:
                home = a
                break
        if home is None:
            merged.append(list(c))
        else:
            have = set(p[0] for p in home)
            home += [p for p in c if p[0] not in have]
            home.sort()
    merged = [c for c in merged if len(c) >= 6]
    merged.sort(key=lambda c: float(np.median([p[1] for p in c])))
    return [{'pts': [[int(x), int(y)] for x, y in c]} for c in merged], (xa, xb)


def show(key, lines, folder):
    im = Image.fromarray(pages.load(key, plain=True))
    d = ImageDraw.Draw(im)
    for n, l in enumerate(lines, 1):
        d.line([tuple(p) for p in l['pts']], fill=(255, 0, 0), width=3)
        x, y = l['pts'][-1]
        d.text((x + 30, y - 30), str(n), fill=(0, 0, 255), font_size=54)
    for x in range(0, im.width, 100):
        d.line([(x, 0), (x, 16 if x % 500 else 40)], fill=(0, 0, 255), width=3)
        if x % 500 == 0:
            d.text((x + 6, 30), str(x), fill=(0, 0, 255), font_size=48)
    im = im.resize((im.width // 3, im.height // 3), Image.LANCZOS)
    im.save(os.path.join(folder, 'lines_%s.jpg' % key), quality=80)


def main():
    args = sys.argv[1:]
    folder = None
    if '--show' in args:
        i = args.index('--show')
        folder = args[i + 1]
        del args[i:i + 2]
    path = os.path.join(HERE, 'lines.json')
    data = json.load(open(path))
    for key in args:
        lines, _ = find(key)
        data[key] = lines
        print(key, len(lines), 'lines; rows at their right end', [l['pts'][-1][1] for l in lines])
        if folder:
            show(key, lines, folder)
    json.dump(data, open(path, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
