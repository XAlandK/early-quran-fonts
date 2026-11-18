#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Draw the figures shown in the README at the root of the repository.

  docs/images/birmingham-hijazi-specimen.png       text set in Birmingham Hijazi
  docs/images/birmingham-hijazi-vs-manuscript.jpg  manuscript lines, the same text in the font under each
  docs/images/birmingham-hijazi-audit.jpg          nine letters of the pixel audit
  docs/images/birmingham-hijazi-paris-forms.jpg    the audit of the nine forms from the Paris leaves
  docs/images/madinah-naqsh-specimen.png           text set in Madinah Naqsh

Only the two fonts and photographs of the manuscript itself are used: the
Birmingham leaves (public domain) and, in the pictures of the nine forms taken
from them, small crops of the Paris leaves (source gallica.bnf.fr / BnF). The
photograph of the Medina inscription is not used, because it belongs to its
photographer.

Usage:  python make_readme_figures.py [project folder]
        (run audit.py first: the audit figure is made from source/audit/)
Needs:  numpy, pillow, uharfbuzz, freetype-py
"""
import json
import os
import sys

import freetype
import numpy as np
import uharfbuzz as hb
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..")
BH_TTF = os.path.join(HERE, "..", "BirminghamHijazi-Regular.ttf")
MN_TTF = os.path.join(ROOT, "Madinah Naqsh (draft - from the Ahzab 70-71 inscription)", "MadinahNaqsh-Regular.ttf")
OUT = os.path.join(ROOT, "docs", "images")

PAPER = np.array([243, 234, 214], dtype=np.float32)
INK = np.array([58, 36, 18], dtype=np.float32)
PXU = 0.225                 # manuscript pixels per font unit (tracer.PXU)
WIDTH = 1600                # width of every figure


def shape_line(font_path, text, px, features=None):
    """Coverage (0..1) of one line of text, and the baseline row in it."""
    face = hb.Face(hb.Blob.from_file_path(font_path))
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    sc = px / face.upem
    ft = freetype.Face(font_path)
    ft.set_pixel_sizes(0, px)
    total = int(np.ceil(sum(p.x_advance for p in buf.glyph_positions) * sc)) + 4
    up, dn = int(px * 1.05), int(px * 0.62)
    img = np.zeros((up + dn, total + 2 * px), dtype=np.float32)
    x = float(px)
    for info, p in zip(buf.glyph_infos, buf.glyph_positions):
        ft.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING)
        g = ft.glyph
        bm = g.bitmap
        if bm.width and bm.rows:
            a = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width] / 255.0
            gx = int(round(x + p.x_offset * sc)) + g.bitmap_left
            gy = up - int(round(p.y_offset * sc)) - g.bitmap_top
            ya, xa = max(gy, 0), max(gx, 0)
            yb, xb = min(gy + bm.rows, img.shape[0]), min(gx + bm.width, img.shape[1])
            if yb > ya and xb > xa:
                img[ya:yb, xa:xb] = np.maximum(img[ya:yb, xa:xb], a[ya - gy:yb - gy, xa - gx:xb - gx])
        x += p.x_advance * sc
    cols = np.where(img.max(axis=0) > 0.02)[0]
    return img[:, cols.min():cols.max() + 1], up


def colour(cov):
    a = cov[..., None]
    return (PAPER * (1 - a) + INK * a).astype(np.uint8)


def specimen(font_path, lines, out, margin=60, gap=18):
    """Lines of text, right-aligned as Arabic script is, on the paper colour."""
    rows = []
    for text, px, feats in lines:
        cov, _ = shape_line(font_path, text, px, feats)
        if cov.shape[1] > WIDTH - 2 * margin:                  # too wide: scale the line down
            f = (WIDTH - 2 * margin) / cov.shape[1]
            cov = np.asarray(Image.fromarray((cov * 255).astype(np.uint8)).resize(
                (int(cov.shape[1] * f), int(cov.shape[0] * f)), Image.LANCZOS)) / 255.0
        row = np.zeros((cov.shape[0], WIDTH), dtype=np.float32)
        row[:, WIDTH - margin - cov.shape[1]:WIDTH - margin] = cov
        rows.append(row)
        rows.append(np.zeros((gap, WIDTH), dtype=np.float32))
    cov = np.vstack([np.zeros((margin // 2, WIDTH), dtype=np.float32)] + rows +
                    [np.zeros((margin // 2, WIDTH), dtype=np.float32)])
    Image.fromarray(colour(cov)).save(out, optimize=True)
    return cov.shape


def manuscript_vs_font(out):
    """Three lines of the manuscript, each with the same text set in the font at the same size."""
    sys.path.insert(0, HERE)
    import make_preview as MP                                   # its list of lines and their text
    full = np.asarray(Image.open(os.path.join(HERE, "manuscript", "full.jpg")).convert("RGB"))
    lines = json.load(open(os.path.join(HERE, "lines.json")))
    px = int(round(1000 * PXU))                                 # the manuscript's scale
    up, dn = 185, 125
    blocks = []
    for pg, idx, x0, x1, text, _ in MP.LINES:
        L = lines[pg][idx - 1]
        strip = np.full((up + dn, x1 - x0, 3), 235, dtype=np.uint8)
        for x in range(x0, x1):
            yb = int(round(L["r"] + L["m"] * (x - L["x0"])))
            strip[:, x - x0] = full[yb - up:yb + dn, x]
        cov, base = shape_line(BH_TTF, text, px, {"ss01": 1, "ss02": 1})
        under = np.zeros((up + dn, x1 - x0), dtype=np.float32)
        top = up - base + int(round(40 * PXU))                 # baseline of the font on the strip's baseline row
        right = (x1 - x0) - 20
        w = min(cov.shape[1], right)
        ya, yb_ = max(top, 0), min(top + cov.shape[0], under.shape[0])
        under[ya:yb_, right - w:right] = cov[ya - top:yb_ - top, cov.shape[1] - w:]
        blocks += [strip, np.full((4, x1 - x0, 3), 255, np.uint8), colour(under), np.full((22, x1 - x0, 3), 255, np.uint8)]
    im = Image.fromarray(np.vstack(blocks[:-1]))
    im = im.resize((WIDTH, int(im.height * WIDTH / im.width)), Image.LANCZOS)
    im.save(out, quality=84, optimize=True)
    return im.size


# letters of the audit figure, by row; each row is scaled to the full width, so the
# pictures of a row are chosen to have about the same total width-to-height ratio
AUDIT_ROWS = (("ALIF.isol", "WAW.isol"), ("LAMALEF.isol", "HEH.fina"), ("AIN.medi", "TAH.medi"),
              ("KAF.isol", "LAM.init"), ("SAD.isol",))
# the nine forms that do not occur on the two Birmingham pages and come from the Paris leaves
PARIS_ROWS = (("MEEM.isol", "QAF.isol"), ("AIN.isol", "HAH.isol"), ("HAH.fina", "FEH.isol"),
              ("FEH.fina", "SAD.fina"), ("TAH.fina",))


def audit_grid(out, rows=AUDIT_ROWS, gap=20):
    """Pictures of the pixel audit, in justified rows."""
    strips = []
    for keys in rows:
        row = [Image.open(os.path.join(HERE, "audit", k + ".jpg")).convert("RGB") for k in keys]
        h = int((WIDTH - gap * (len(row) - 1)) / sum(c.width / c.height for c in row))
        strip = Image.new("RGB", (WIDTH, h), (255, 255, 255))
        x = 0
        for k, c in enumerate(row):
            w = WIDTH - x if k == len(row) - 1 else int(round(c.width * h / c.height))
            strip.paste(c.resize((w, h), Image.LANCZOS), (x, 0))
            x += w + gap
        strips.append(strip)
    sheet = Image.new("RGB", (WIDTH, sum(r.height for r in strips) + gap * (len(strips) - 1)), (255, 255, 255))
    y = 0
    for r in strips:
        sheet.paste(r, (0, y))
        y += r.height + gap
    sheet.save(out, quality=84, optimize=True)
    return sheet.size


def main():
    os.makedirs(OUT, exist_ok=True)
    rasm = {"ss01": 1}
    print("specimen", specimen(BH_TTF, [
        ("بسم الله الرحمن الرحيم", 150, rasm),
        ("طه ۔ ما انزلنا عليك القران لتشقى ۔ الا تذكره لمن يخشى", 92, rasm),
        ("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ", 92, None),
        ("ئەم فۆنتە لە دەستنووسی قورئانی بیرمینگهامەوە هێڵکاری کراوە", 80, None),
        ("قوم نوح ۔ صلح ۔ سوف ۔ كيف ۔ محيط ۔ ورزق ربك ۔ تجوع ۔ متربص", 80, rasm),
        ("ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي", 74, None),
    ], os.path.join(OUT, "birmingham-hijazi-specimen.png")))
    print("lines", manuscript_vs_font(os.path.join(OUT, "birmingham-hijazi-vs-manuscript.jpg")))
    print("audit", audit_grid(os.path.join(OUT, "birmingham-hijazi-audit.jpg")))
    print("paris", audit_grid(os.path.join(OUT, "birmingham-hijazi-paris-forms.jpg"), PARIS_ROWS))
    print("madinah", specimen(MN_TTF, [
        ("يايها الذين امنوا اتقوا الله وقولوا", 120, rasm),
        ("قولا سديدا يصلح لكم اعملكم", 120, rasm),
        ("ويغفر لكم ذنوبكم ومن يطع الله", 120, rasm),
        ("ورسوله فقد فاز فوزا عظيما", 120, rasm),
        ("ئەم فۆنتە لە نەخشێکی بەردی مەدینەوە هێڵکاری کراوە", 74, None),
    ], os.path.join(OUT, "madinah-naqsh-specimen.png")))


if __name__ == "__main__":
    main()
