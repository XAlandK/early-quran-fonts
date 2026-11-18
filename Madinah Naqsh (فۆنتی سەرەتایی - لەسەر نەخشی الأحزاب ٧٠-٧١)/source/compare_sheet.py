#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Letter-by-letter comparison: each exemplar as it stands in the manuscript,
next to the outline traced from it.

Usage:  python compare_sheet.py <full.jpg> <lines.json> <traced.json> <out_dir> [cells per sheet]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from shapely import wkt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tracer as T  # noqa: E402

CW, CH = 250, 250          # one half of a cell
XL, XR = -330, 330         # units shown left of x=0 and right of x=adv
YT, YB = 760, -470         # units shown above / below the baseline


def cell(page, key, rec, scale=None, parts=False):
    adv = rec['adv']
    src = rec['src']
    wu = adv + XR - XL
    sc = min(CW / wu, CH / (YT - YB)) if scale is None else scale
    W, H = CW, CH
    ox = (W - wu * sc) / 2 - XL * sc          # pixel x of unit x=0
    oy = H - (H - (YT - YB) * sc) / 2 + YB * sc   # pixel y of unit y=0
    # manuscript
    xa = max(int(src['x0'] + XL * T.PXU) - 2, 0)
    xb = int(src['x1'] + XR * T.PXU) + 2
    g, rgb = page.deskew(src['page'], src['line'], xa, xb)
    r0 = int(src['yb'] - (YT - T.BL) * T.PXU)
    r1 = int(src['yb'] + (T.BL - YB) * T.PXU)
    pad = np.full((max(r1, rgb.shape[0]) - min(r0, 0), rgb.shape[1], 3), 235, dtype=np.uint8)
    pad[-min(r0, 0):-min(r0, 0) + rgb.shape[0]] = rgb
    crop = Image.fromarray(pad[r0 - min(r0, 0):r1 - min(r0, 0)])
    f = sc / T.PXU                            # manuscript px -> cell px
    crop = crop.resize((max(int(crop.width * f), 1), max(int(crop.height * f), 1)), Image.LANCZOS)
    left = Image.new('RGB', (W, H), (235, 228, 210))
    mx = ox - (src['x0'] - xa) * f
    my = oy - YT * sc
    left.paste(crop, (int(round(mx)), int(round(my))))
    # traced outline
    right = Image.new('RGB', (W, H), (250, 247, 240))
    d = ImageDraw.Draw(right)
    geom = wkt.loads(rec['wkt'])
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    tr = lambda x, y: (ox + x * sc, oy - y * sc)
    for p in polys:
        d.polygon([tr(x, y) for x, y in p.exterior.coords], fill=(40, 26, 14))
        for hole in p.interiors:
            d.polygon([tr(x, y) for x, y in hole.coords], fill=(250, 247, 240))
    for im in (left, right):
        dd = ImageDraw.Draw(im, 'RGBA')
        dd.line([tr(XL - 500, T.BL), tr(adv + XR + 500, T.BL)], fill=(220, 0, 0, 110))
        dd.line([tr(0, YB), tr(0, YT)], fill=(0, 90, 255, 110))
        dd.line([tr(adv, YB), tr(adv, YT)], fill=(0, 90, 255, 110))
    if parts:
        return left, right
    out = Image.new('RGB', (2 * W + 6, H + 16), (255, 255, 255))
    out.paste(left, (0, 16))
    out.paste(right, (W + 6, 16))
    ImageDraw.Draw(out).text((3, 2), '%s   adv %d   %s' % (key, adv, src['id']), fill=(0, 0, 0))
    return out


def main():
    full, lines, traced, out_dir = sys.argv[1:5]
    per = int(sys.argv[5]) if len(sys.argv) > 5 else 15
    page = T.Page(full, json.load(open(lines)))
    data = json.load(open(traced))
    keys = sorted(k for k in data if k != '_all')
    tag = 'letters'
    if len(sys.argv) > 6:                       # alternatives of some forms
        data = json.load(open(traced + '.alts'))
        keys = sorted(k for k in data if any(k.startswith(p) for p in sys.argv[6].split(',')))
        tag = 'alt'
    cols = 3
    for s in range(0, len(keys), per):
        chunk = keys[s:s + per]
        cells = [cell(page, k, data[k], scale=0.19) for k in chunk]
        cw, ch = cells[0].size
        rows = (len(cells) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * (cw + 8), rows * (ch + 8)), (255, 255, 255))
        for i, c in enumerate(cells):
            sheet.paste(c, ((i % cols) * (cw + 8), (i // cols) * (ch + 8)))
        name = '%s/%s_%02d.jpg' % (out_dir, tag, s // per + 1)
        sheet.save(name, quality=86)
        print(name, sheet.size)


if __name__ == '__main__':
    main()
