#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare the photograph of the rock inscription for tracing.

The inscription (Qur'an 33:70-71, in the hills around Medina; photograph by Muhammad
al-Maghdhawi, @mohammed93athar) is carved, so its letters are light on dark rock, and the
photograph was taken at an angle, so the lower lines are larger than the upper ones.

This script
  * separates the cream of the carving from the blue-grey rock and evens out the lighting,
  * turns each line level and enlarges it so that all lines have the same letter size,
  * writes the lines one under the other as dark letters on a light ground (page.png),
    the same lines in the colours of the photograph (page_rgb.jpg), and lines.json.

The tracer then treats page.png exactly like the photograph of a manuscript page.

Usage:  python prep.py [ruler_dir]
Needs:  numpy, pillow, scipy
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))

# line of the inscription -> (two points of its baseline in the photograph, enlargement)
# The enlargement brings an alif to about 150 px, the size the tracer is set up for.
LINES = [
    ('5', (150, 427.0), (760, 463.0), 2.10),   # ورسوله فقد فاز فوزا عظيما
    ('4', (100, 277.0), (820, 313.0), 2.95),   # ويغفر لكم ذنوبكم ومن يطع الله
    ('3', (220, 176.0), (850, 186.0), 3.50),   # قولا سديدا يصلح لكم اعملكم
]
UP, DN = 215, 150          # rows kept above / below a baseline (as in tracer.py)
BAND = 400                 # height given to each line on the page
FIRST = 240                # row of the first baseline


def carving(rgb):
    """How much a pixel looks like the cream-yellow carving rather than the rock."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    v = 0.55 * (r + g) / 2 + 0.9 * ((r + g) / 2 - b)       # light, and yellower than the rock
    v = ndi.gaussian_filter(v, 0.9)                         # JPEG blocks and sharpening halos
    return v - ndi.gaussian_filter(v, 40)                   # even out the lighting


def main():
    rgb = np.asarray(Image.open(os.path.join(HERE, 'naqsh', 'photo.jpg')).convert('RGB')).astype(np.float32)
    v = carving(rgb)
    width = int(max(rgb.shape[1] * s for _, _, _, s in LINES)) + 40
    H = FIRST + BAND * (len(LINES) - 1) + DN + 60
    grey = np.zeros((H, width), dtype=np.float32)
    col = np.full((H, width, 3), 128, dtype=np.float32)
    have = np.zeros((H, width), dtype=bool)
    lines = []
    for i, (name, p0, p1, s) in enumerate(LINES):
        th = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        cs, sn = math.cos(th), math.sin(th)
        ox, oy = p0[0] - p0[0] / cs * cs, p0[1] - p0[0] / cs * sn       # where the baseline meets x = 0
        r = FIRST + BAND * i
        w = int(rgb.shape[1] * s)
        u = np.arange(w, dtype=np.float32) / s
        t = np.arange(-UP, DN, dtype=np.float32) / s
        X = ox + u[None, :] * cs - t[:, None] * sn
        Y = oy + u[None, :] * sn + t[:, None] * cs
        ok = (X >= 0) & (X <= rgb.shape[1] - 1) & (Y >= 0) & (Y <= rgb.shape[0] - 1)
        grey[r - UP:r + DN, :w] = ndi.map_coordinates(v, [Y, X], order=3, mode='nearest')
        for k in range(3):
            col[r - UP:r + DN, :w, k] = ndi.map_coordinates(rgb[..., k], [Y, X], order=3, mode='nearest')
        have[r - UP:r + DN, :w] = ok
        lines.append({'x0': 0, 'r': r, 'm': 0.0, 'name': name, 'scale': s,
                      'origin': [round(ox, 3), round(oy, 3)], 'angle': round(th, 6)})
    lo, hi = np.percentile(grey[have], 66), np.percentile(grey[have], 98.7)
    tone = np.clip((grey - lo) / (hi - lo), 0, 1) ** 0.8
    page = np.where(have, 232 - tone * 190, 232).astype(np.uint8)       # carving dark, rock light
    Image.fromarray(page).save(os.path.join(HERE, 'page.png'))
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(HERE, 'page_rgb.jpg'), quality=90)
    json.dump({'N': lines}, open(os.path.join(HERE, 'lines.json'), 'w'), indent=1)
    print('page', page.shape, 'levels', round(float(lo), 1), round(float(hi), 1))
    if len(sys.argv) > 1:                                   # ruled strips for marking the cuts
        out = sys.argv[1]
        pg = Image.fromarray(page).convert('RGB')
        for i, (name, _, _, s) in enumerate(LINES):
            r = FIRST + BAND * i
            w = int(rgb.shape[1] * s)
            n = max(1, round(w / 1500))
            for j in range(n):
                x0, x1 = j * w // n - 30, (j + 1) * w // n + 30
                x0, x1 = max(x0, 0), min(x1, w)
                c = pg.crop((x0, r - UP + 15, x1, r + DN - 10))
                d = ImageDraw.Draw(c, 'RGBA')
                for x in range((x0 // 50 + 1) * 50, x1, 50):
                    d.line([(x - x0, 0), (x - x0, c.height)], fill=(0, 90, 255, 120 if x % 100 == 0 else 45), width=1)
                    if x % 100 == 0:
                        d.rectangle([x - x0 + 1, 0, x - x0 + 30, 11], fill=(255, 255, 255, 220))
                        d.text((x - x0 + 2, 0), str(x), fill=(0, 0, 160, 255))
                d.line([(0, UP - 15), (c.width, UP - 15)], fill=(255, 0, 0, 110), width=1)
                c.save(os.path.join(out, 'L%s_%d.jpg' % (name, n - j)), quality=84)


if __name__ == '__main__':
    main()
