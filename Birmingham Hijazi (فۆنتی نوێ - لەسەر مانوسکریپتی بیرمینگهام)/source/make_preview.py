#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Write the self-contained font preview page (fonts and images embedded).

Usage:  python make_preview.py [project folder]
        (run audit.py first: the page shows its pictures and figures from source/audit/)
Needs:  numpy, pillow, scipy, scikit-image, shapely
"""
import base64
import html
import io
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tracer as T  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..")
BH_DIR = "Birmingham Hijazi (فۆنتی نوێ - لەسەر مانوسکریپتی بیرمینگهام)"
KUFI = "کوفی (دواتر - نەک بیرمینگهام)"
MN_DIR = "Madinah Naqsh (فۆنتی سەرەتایی - لەسەر نەخشی الأحزاب ٧٠-٧١)"

FONTS = [
    # css name, path, title, subtitle, tags, badge (fonts with a badge are ours and have ss01 / ss02)
    ("Birmingham Hijazi", f"{BH_DIR}/BirminghamHijazi-Regular.ttf",
     "Birmingham Hijazi", "وەشانی ٣ — پیتەکان ڕاستەوخۆ لە مەرەکەبی دەستنووسی بیرمینگهام هێڵکاری کراون",
     ["خەتی حیجازی", "سەدەی یەکەمی کۆچی (٥٦٨–٦٤٥ ز)", "ss01 · ss02", "کوردیش دەنووسێت"], "نوێ"),
    ("Madinah Naqsh", f"{MN_DIR}/MadinahNaqsh-Regular.ttf",
     "Madinah Naqsh", "وەشانی سەرەتایی ٠٫١ — لە نەخشێکی بەردی دەوری مەدینە (الأحزاب ٧٠–٧١) هێڵکاری کراوە",
     ["نەخشی بەرد", "٢٨ شێوەی هێڵکاریکراو، ٣٤ی دروستکراو", "ss01 · ss02", "کوردیش دەنووسێت"], "سەرەتایی"),
    ("Hijazi KA", "Hijazi - گشتی (خالید العبدالله، 2019)/hijazi.ttf",
     "Hijazi", "حیجازیی گشتی — خالید العبدالله، ٢٠١٩ (وەشانی تاقیکاری)",
     ["خەتی حیجازی", "CC BY-NC 4.0 — بازرگانی نا"], ""),
    ("Raqq", f"{KUFI}/Raqq/Raqq.ttf",
     "Raqq · رَقّ", "کوفیی مصحفی — شێوازی سەدەی سێیەمی کۆچی (Aliftype)",
     ["کوفی", "AGPL-3.0"], ""),
    ("Qahiri", f"{KUFI}/Qahiri/Qahiri-Regular.ttf",
     "Qahiri · قاهري", "کوفیی مصحفیی ڕێکخراو (Aliftype)",
     ["کوفی", "OFL 1.1"], ""),
    ("Qashib", f"{KUFI}/Qashib/Qashib.ttf",
     "Qashib · قشيب", "کوفیی مصحفیی نوێکراوە، پیتی ئاسانتر بۆ خوێندنەوە (Aliftype)",
     ["کوفی", "AGPL-3.0"], ""),
]

PRESETS = [
    ("دەقی دەستنووسەکە", "بسم الله الرحمن الرحيم طه ۔ ما انزلنا عليك القران لتشقى ۔ الا تذكره لمن يخشى ۔ "
                          "تنزيلا ممن خلق الارض والسموت العلى ۔ الرحمن على العرش استوى ۔"),
    ("دەقی نەخشەکە", "يايها الذين امنوا اتقوا الله وقولوا قولا سديدا يصلح لكم اعملكم ويغفر لكم ذنوبكم "
                      "ومن يطع الله ورسوله فقد فاز فوزا عظيما"),
    ("بە بزوێنەوە", "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ ۔ طه ۔ مَآ أَنزَلْنَا عَلَيْكَ ٱلْقُرْءَانَ لِتَشْقَىٰٓ"),
    ("کوردی", "ئەم فۆنتە لە دەستنووسی قورئانی بیرمینگهامەوە هێڵکاری کراوە، ڕۆژێکی خۆش ڵ گ ڤ پ چ ژ"),
    ("پیتەکان", "ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي ء ة ى لا"),
    ("ژمارەکان", "٠ ١ ٢ ٣ ٤ ٥ ٦ ٧ ٨ ٩ ، ؛ ؟"),
]

# manuscript lines set again in the font: (page, line index, x0, x1, text as the scribe spelled it, caption)
LINES = [
    ("L", 12, 280, 1780, "الا تذكره لمن يخشى", "هێڵی ١١ی پەڕەی ٢ ڕوو (سورەتی طه، ئایەتی ٣)"),
    ("L", 17, 280, 1780, "الا هو له الاسما ا", "هێڵی ١٦ی پەڕەی ٢ ڕوو (سورەتی طه، ئایەتی ٨)"),
    ("L", 21, 280, 1780, "تيها نودى يموسى", "هێڵی ٢٠ی پەڕەی ٢ ڕوو (سورەتی طه، ئایەتی ١١)"),
]

RASM = [("ALIF", "ا"), ("BEH", "ب ت ث"), ("NOON", "ن"), ("YEH", "ی"), ("HAH", "ج ح خ"), ("DAL", "د ذ"),
        ("REH", "ر ز"), ("SEEN", "س ش"), ("SAD", "ص ض"), ("TAH", "ط ظ"), ("AIN", "ع غ"), ("FEH", "ف"),
        ("QAF", "ق"), ("KAF", "ک"), ("LAM", "ل"), ("MEEM", "م"), ("HEH", "ه"), ("WAW", "و"),
        ("LAMALEF", "لا")]
FORM = [("isol", "تەنها"), ("init", "سەرەتا"), ("medi", "ناوەڕاست"), ("fina", "کۆتایی")]
DERIVED = [
    ("م", "تەنها", "«م»ی کۆتایی، بێ ئەو هێڵەی کە بە پیتی پێشووەوە دەیبەستێت"),
    ("ق", "تەنها", "«ق»ی کۆتایی، بێ هێڵی بەستنەکە"),
    ("ع غ", "تەنها", "«ع»ی کۆتایی، بێ هێڵی بەستنەکە"),
    ("ص ض", "کۆتایی", "«ص»ی تەنها، لەگەڵ هێڵی بەستن لە لای ڕاست"),
    ("ط ظ", "کۆتایی", "«ط»ی تەنها، لەگەڵ هێڵی بەستن لە لای ڕاست"),
    ("ف", "کۆتایی و تەنها", "بازنەی «ف»ی بڕدراو، لەگەڵ کلکێکی تەخت وەک کلکی «ب»"),
    ("ج ح خ", "کۆتایی و تەنها", "سەری «ح»ی بڕدراو، لەگەڵ هێڵێکی درێژ بەرەو چەپ کە بە قولاپێکی بچووک "
                                "کۆتایی دێت — وەک وشەی «تخرج» لە پەڕەی ٢ پشت (وێنەکەی وردیی کەمترە)"),
]

LETTERS = "ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي ى ة پ چ ژ ڕ ڤ ک گ ڵ ە ۆ ی ێ".split()
DUAL = set("ب ت ث ج ح خ س ش ص ض ط ظ ع غ ف ق ك ل م ن ه ي ى پ چ ڤ ک گ ڵ ی ێ")
DIGITS = "٠١٢٣٤٥٦٧٨٩"


def ku(n):
    return "".join(DIGITS[int(c)] if c.isdigit() else ("٫" if c == "." else c) for c in str(n))


def b64(path):
    with open(os.path.join(ROOT, path), "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def jpg(im, q=74):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=q, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def line_strip(page, pg, idx, x0, x1, up=185, dn=120):
    L = page.lines[pg][idx - 1]
    out = np.full((up + dn, x1 - x0, 3), 235, dtype=np.uint8)
    for x in range(x0, x1):
        yb = int(round(L['r'] + L['m'] * (x - L['x0'])))
        out[:, x - x0] = page.rgb[yb - up: yb + dn, x]
    im = Image.fromarray(out)
    return im.resize((1200, int(im.height * 1200 / im.width)), Image.LANCZOS)


def text_line(pg, idx):
    """line number on the page (lines.json also holds the ornament band of folio 2 recto)"""
    return idx - 1 if (pg == "L" and idx > 10) else idx


def forms_table():
    zwj = "‍"
    rows = []
    for ch in LETTERS:
        if ch in DUAL:
            cells = [ch + zwj, zwj + ch + zwj, zwj + ch, ch]
        else:
            cells = ["", "", zwj + ch, ch]
        tds = "".join('<td class="bh">%s</td>' % html.escape(c) if c else "<td></td>" for c in cells)
        rows.append("<tr>%s</tr>" % tds)
    return "\n".join(rows)


MN_LINES = [   # line of prep's page, x0, x1, text as carved, caption
    (1, 100, 2060, "ورسوله فقد فاز فوزا عظيما", "هێڵی پێنجەم"),
    (2, 620, 2880, "ويغفر لكم ذنوبكم ومن يطع", "هێڵی چوارەم (بێ وشەی «الله»ی کۆتایی)"),
    (3, 1180, 3350, "قولا سديدا يصلح لكم", "هێڵی سێیەم (بێ وشەی «اعملكم»)"),
]
MN_DERIVED = [
    ("ب ت ث ن ی", "ناوەڕاست", "ددانی سەرەتا، لەگەڵ هێڵی بەستن لە لای ڕاست"),
    ("ب ت ث", "کۆتایی و تەنها", "ددانەکە، لەگەڵ هێڵێکی تەخت بەرەو چەپ"),
    ("ن", "تەنها", "«ن»ی کۆتایی، بێ هێڵی بەستن"),
    ("ی", "کۆتایی و تەنها", "ددانەکە، لەگەڵ کلکی «ن»ی کۆتایی — لە نەخشەکەدا «ی»ی کۆتایی نییە"),
    ("ج ح خ", "سەرەتا، ناوەڕاست، تەنها", "سەری «ح»ی کۆتایی، بێ کلکەکەی یان بێ هێڵی بەستن"),
    ("س ش", "ناوەڕاست", "ددانەکانی سەرەتا، لەگەڵ هێڵی بەستن"),
    ("س ش · ص ض · ق · ل", "کۆتایی و تەنها", "شێوەی ناوەڕاست یان سەرەتا، لەگەڵ کلکی «ن»ی کۆتایی"),
    ("ص ض", "سەرەتا", "«ص»ی ناوەڕاست، بێ هێڵی بەستنی ڕاست"),
    ("ط ظ", "سەرەتا، کۆتایی، تەنها", "«ط»ی ناوەڕاست، بێ هێڵی بەستنی یەک لا یان هەردوو لا"),
    ("ع غ", "تەنها", "«ع»ی کۆتایی، بێ هێڵی بەستن"),
    ("ف", "کۆتایی و تەنها", "بازنەکەی، لەگەڵ هێڵێکی تەخت بەرەو چەپ"),
    ("ک", "سەرەتا، کۆتایی، تەنها", "«ک»ی ناوەڕاست، بێ هێڵی بەستنی یەک لا یان هەردوو لا"),
    ("م", "ناوەڕاست و تەنها", "«م»ی سەرەتا لەگەڵ هێڵی بەستن؛ «م»ی کۆتایی بێ هێڵی بەستن"),
    ("ه", "سەرەتا، ناوەڕاست، تەنها", "«ه»ی کۆتایی، لەگەڵ یان بێ هێڵی بەستن"),
    ("لا", "کۆتایی", "«لا»ی تەنها، لەگەڵ هێڵی بەستن"),
]


def madinah():
    """The parts of the page about the Madinah Naqsh draft."""
    src = os.path.join(ROOT, MN_DIR, "source")
    lines = json.load(open(os.path.join(src, "lines.json")))["N"]
    traced = json.load(open(os.path.join(src, "traced.json"), encoding="utf-8"))
    audit = json.load(open(os.path.join(src, "audit", "audit.json")))
    arow = {r["key"]: r for r in audit["rows"]}
    page = np.asarray(Image.open(os.path.join(src, "page_rgb.jpg")).convert("RGB"))
    up, dn = 185, 150
    out_lines = []
    for idx, x0, x1, text, cap in MN_LINES:
        r = lines[idx - 1]["r"]
        im = Image.fromarray(page[r - up:r + dn, x0:x1])
        im = im.resize((1200, int(im.height * 1200 / im.width)), Image.LANCZOS)
        out_lines.append(
            '<figure class="cmp" data-em="%.4f">'
            '<img loading="lazy" alt="%s" src="data:image/jpeg;base64,%s">'
            '<div class="cmp-font mn">%s</div>'
            '<figcaption>%s — سەرەوە نەخشەکە (ڕاستکراوە و گەورەکراو)، خوارەوە هەمان دەق بە فۆنتەکە بە هەمان قەبارە.</figcaption>'
            '</figure>' % (1000 * T.PXU / (x1 - x0), html.escape(cap), jpg(im, 80), html.escape(text), html.escape(cap)))
    cells = []
    for name, letters in RASM:
        for form, form_ku in FORM:
            key = "%s.%s" % (name, form)
            if key not in traced or key not in arow:
                continue
            ln = lines[traced[key]["src"]["line"] - 1]["name"]
            with open(os.path.join(src, "audit", key + ".jpg"), "rb") as fh:
                pic = base64.b64encode(fh.read()).decode("ascii")
            cells.append(
                '<figure class="lt">'
                '<img loading="lazy" alt="%s %s" src="data:image/jpeg;base64,%s">'
                '<figcaption><b>%s</b> · %s<span>هێڵی %s · جیاوازیی لێوار %s px ی وێنەکە</span></figcaption></figure>'
                % (html.escape(letters), form_ku, pic, html.escape(letters), form_ku, ku(ln),
                   ku("%.2f" % arow[key]["edge_photo"])))
    photo = Image.open(os.path.join(src, "naqsh", "photo.jpg")).convert("RGB")
    am = audit["mean"]
    return {
        "%%MN_PHOTO%%": jpg(photo, 80), "%%MN_LINES%%": "\n".join(out_lines), "%%MN_CELLS%%": "\n".join(cells),
        "%%MN_N%%": ku(len(cells)), "%%MN_EDGE%%": ku("%.2f" % am["edge_photo"]), "%%MN_P95%%": ku("%.2f" % am["p95_photo"]),
        "%%MN_DERIVED%%": "".join("<li><b>%s</b> (%s): %s</li>" % (html.escape(a), html.escape(b), html.escape(c))
                                  for a, b, c in MN_DERIVED),
    }


def main():
    src = os.path.join(HERE, "manuscript", "full.jpg")
    page = T.Page(src, json.load(open(os.path.join(HERE, "lines.json"))))
    traced = json.load(open(os.path.join(HERE, "traced.json"), encoding="utf-8"))

    faces = "\n".join(
        '@font-face{font-family:"%s";src:url(data:font/ttf;base64,%s) format("truetype");font-display:block}'
        % (css, b64(path)) for css, path, *_ in FONTS)

    # 1. whole lines
    lines_html = []
    em = 1000 * T.PXU          # manuscript pixels per em
    for pg, idx, x0, x1, text, cap in LINES:
        im = line_strip(page, pg, idx, x0, x1)
        lines_html.append(
            '<figure class="cmp" data-em="%.4f">'
            '<img alt="%s" src="data:image/jpeg;base64,%s">'
            '<div class="cmp-font">%s</div>'
            '<figcaption>%s — سەرەوە دەستنووسەکە، خوارەوە هەمان دەق بە فۆنتەکە بە هەمان قەبارە.</figcaption>'
            '</figure>' % (em / (x1 - x0), html.escape(cap), jpg(im, 78), html.escape(text), html.escape(cap)))

    # 2. letter by letter: the pictures and figures of the pixel audit
    audit = json.load(open(os.path.join(HERE, "audit", "audit.json")))
    arow = {r["key"]: r for r in audit["rows"]}
    cells = []
    n_traced = 0
    for name, letters in RASM:
        for form, form_ku in FORM:
            key = "%s.%s" % (name, form)
            if key not in traced or key not in arow:
                continue
            s = traced[key]["src"]
            where = "%s، هێڵی %s" % ("پەڕەی ٢ ڕوو" if s["page"] == "L" else "پەڕەی ١ پشت",
                                      ku(text_line(s["page"], s["line"])))
            with open(os.path.join(HERE, "audit", key + ".jpg"), "rb") as fh:
                pic = base64.b64encode(fh.read()).decode("ascii")
            cells.append(
                '<figure class="lt">'
                '<img loading="lazy" alt="%s %s" src="data:image/jpeg;base64,%s">'
                '<figcaption><b>%s</b> · %s<span>%s · جیاوازیی لێوار %s px</span></figcaption></figure>'
                % (html.escape(letters), form_ku, pic, html.escape(letters), form_ku, where,
                   ku("%.2f" % arow[key]["edge"])))
            n_traced += 1
    am = audit["mean"]
    worst = max(audit["rows"], key=lambda r: r["edge"])

    derived = "".join("<li><b>%s</b> (%s): %s</li>" % (html.escape(a), html.escape(b), html.escape(c))
                      for a, b, c in DERIVED)

    cards = []
    for css, path, title, sub, tags, new in FONTS:
        tag_html = "".join('<span class="tag">%s</span>' % html.escape(t) for t in tags)
        cards.append(
            '<section class="card%s">'
            '<div class="meta"><div><h3>%s%s</h3><p>%s</p></div><div class="tags">%s</div></div>'
            '<div class="sample%s" style="font-family:\'%s\'"></div>'
            '<div class="path" dir="ltr">%s</div>'
            '</section>' % (
                " new" if new else "", html.escape(title),
                ' <span class="badge">%s</span>' % new if new else "", html.escape(sub), tag_html,
                " bh" if new else "", css, html.escape(path)))

    preset_btns = "".join('<button type="button" data-i="%d">%s</button>' % (i, html.escape(n))
                          for i, (n, _) in enumerate(PRESETS))
    presets_js = "[" + ",".join('"%s"' % t.replace("\\", "\\\\").replace('"', '\\"') for _, t in PRESETS) + "]"

    full = Image.open(src)
    full = full.resize((1100, int(full.height * 1100 / full.width)), Image.LANCZOS)

    page_html = TEMPLATE
    for k, v in madinah().items():
        page_html = page_html.replace(k, v)
    for k, v in {
        "%%FACES%%": faces, "%%CARDS%%": "\n".join(cards), "%%PRESET_BTNS%%": preset_btns,
        "%%PRESETS%%": presets_js, "%%LINES%%": "\n".join(lines_html), "%%CELLS%%": "\n".join(cells),
        "%%NTRACED%%": ku(n_traced), "%%DERIVED%%": derived, "%%MS_FULL%%": jpg(full, 72),
        "%%A_EDGE%%": ku("%.2f" % am["edge"]), "%%A_P95%%": ku("%.2f" % am["p95"]),
        "%%A_AREA%%": ku("%.1f" % (abs(am["area"] - 1) * 100)), "%%A_WORST%%": ku("%.2f" % worst["edge"]),
        "%%FORMS%%": forms_table(),
    }.items():
        page_html = page_html.replace(k, v)
    out = os.path.join(ROOT, "پیشاندانی-فۆنتەکان.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page_html)
    print("wrote", out, round(len(page_html) / 1024), "KB,", n_traced, "traced forms")


TEMPLATE = r"""<!doctype html>
<html lang="ckb" dir="rtl">
<head>
<!-- Copyright (c) 2026 Aland Kawa Ali. Licensed under AANCL v1.0. See the LICENSE file.
     The third-party fonts and photographs embedded in this page keep their own licenses;
     see THIRD_PARTY_NOTICES.md. -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>فۆنتە کۆنەکانی قورئان</title>
<style>
%%FACES%%
:root{
  --paper:#f3ead6; --card:#fbf6ea; --ink:#2e1d0f; --muted:#7a6650; --line:#e3d5b9;
  --accent:#9a4416; --accent-soft:#f1dcc6; --script:#3a2412;
}
@media (prefers-color-scheme:dark){
  :root{--paper:#16110b; --card:#211a12; --ink:#efe3cc; --muted:#b19d82; --line:#3b2f21;
        --accent:#e59a62; --accent-soft:#3a2617; --script:#f0dfc0;}
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI","Noto Sans Arabic","Geeza Pro",sans-serif;line-height:1.6}
.wrap{max-width:1100px;margin:0 auto;padding:0 16px 48px}
header{padding:28px 0 8px}
h1{font-size:clamp(22px,4vw,32px);margin:0 0 4px}
.lead{color:var(--muted);margin:0}
.controls{position:static;background:var(--paper);padding:12px 0;border-bottom:1px solid var(--line);
  display:grid;gap:10px}
@media (min-width:900px){.controls{position:sticky;top:0;z-index:5}}
textarea{width:100%;min-height:62px;resize:vertical;font:inherit;font-size:17px;padding:10px 12px;border-radius:10px;
  border:1px solid var(--line);background:var(--card);color:var(--ink)}
.row{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
.presets{display:flex;flex-wrap:wrap;gap:6px}
button{font:inherit;font-size:14px;padding:5px 12px;border-radius:999px;border:1px solid var(--line);
  background:var(--card);color:var(--ink);cursor:pointer}
button:hover,button.on{background:var(--accent-soft);border-color:var(--accent)}
label{font-size:14px;color:var(--muted);display:inline-flex;gap:6px;align-items:center}
input[type=range]{width:160px;accent-color:var(--accent)}
input[type=checkbox]{accent-color:var(--accent)}
h2{font-size:20px;margin:30px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:14px 0}
.card.new{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.meta{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px}
.meta h3{margin:0;font-size:18px}
.meta p{margin:2px 0 0;color:var(--muted);font-size:14px}
.badge{font-size:12px;background:var(--accent);color:var(--card);padding:1px 8px;border-radius:999px;vertical-align:middle}
.tags{display:flex;flex-wrap:wrap;gap:6px;align-content:flex-start}
.tag{font-size:12px;border:1px solid var(--line);border-radius:999px;padding:1px 9px;color:var(--muted)}
.sample{font-size:var(--size,44px);line-height:2.3;color:var(--script);margin-top:6px;padding-inline-end:.5em;
  overflow-wrap:anywhere;white-space:pre-wrap}
.path{font-size:11px;color:var(--muted);text-align:left;opacity:.8;overflow-wrap:anywhere}
figure{margin:0}
.note{font-size:14px;color:var(--muted)}
.cmp{margin:0 0 18px}
.cmp img{width:100%;height:auto;display:block;border-radius:10px 10px 0 0}
.cmp-font.mn{font-family:"Madinah Naqsh";line-height:1.9}
.cmp-font{font-family:"Birmingham Hijazi";font-feature-settings:"ss01","ss02";color:#3a2412;background:#ece4ce;
  border-radius:0 0 10px 10px;white-space:nowrap;overflow:hidden;text-align:right;line-height:1.55;
  padding:0 1.2% 0 0;font-size:40px}
figcaption{font-size:13px;color:var(--muted);margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,440px),1fr));gap:12px}
.lt{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.stat b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
.stat span{font-size:12px;color:var(--muted)}
.key{display:inline-block;width:10px;height:10px;border-radius:2px;margin-inline-end:4px;vertical-align:middle}
.lt img{width:100%;height:auto;display:block;border-radius:6px}
.lt figcaption{display:flex;justify-content:space-between;gap:8px;align-items:baseline;font-size:13px;color:var(--ink)}
.lt figcaption b{font-size:16px}
.lt figcaption span{color:var(--muted);font-size:12px}
.legend{font-size:13px;color:var(--muted);margin:4px 0 10px}
ul.plain{margin:6px 0;padding-inline-start:20px;font-size:14px}
ul.plain li{margin:4px 0}
table.forms{border-collapse:collapse;width:100%;font-family:"Birmingham Hijazi"}
table.forms th{font:600 13px system-ui,sans-serif;color:var(--muted);padding:6px;border-bottom:1px solid var(--line)}
table.forms td{text-align:center;font-size:clamp(30px,6vw,54px);line-height:2;color:var(--script);
  border-bottom:1px solid var(--line);padding:0 6px}
.forms-wrap{overflow-x:auto}
.ms img{width:100%;height:auto;display:block;border-radius:10px}
a{color:var(--accent)}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>فۆنتە کۆنەکانی قورئان</h1>
  <p class="lead">لێرە دەقێک بنووسە یان یەکێک لە نموونەکان هەڵبژێرە، هەموو فۆنتەکان پێکەوە نیشان دەدرێن.</p>
</header>

<div class="controls">
  <textarea id="txt" aria-label="دەق"></textarea>
  <div class="row">
    <div class="presets">%%PRESET_BTNS%%</div>
  </div>
  <div class="row">
    <label>قەبارە <input id="size" type="range" min="18" max="120" value="44"> <span id="sizev">44</span>px</label>
    <label><input id="ss01" type="checkbox"> تەنها ڕەسم — بێ خاڵ (ss01)</label>
    <label><input id="ss02" type="checkbox"> شاردنەوەی بزوێنەکان (ss02)</label>
  </div>
</div>

<h2>فۆنتەکان</h2>
<p class="note">دوو هەڵبژاردەی ss01 و ss02 تەنها لە دوو فۆنتەکەی خۆماندا هەن: Birmingham Hijazi و Madinah Naqsh.</p>
%%CARDS%%

<h2>بەراورد لەگەڵ دەستنووسەکە — هێڵ بە هێڵ</h2>
<p class="note">سێ هێڵی دەستنووسەکە، و لە ژێر هەر یەکێکیاندا هەمان دەق (بە ڕێنووسی نووسەرەکە، بێ خاڵ) بە فۆنتی Birmingham Hijazi.</p>
%%LINES%%

<h2>پشکنینی پیکسڵ بە پیکسڵ — پیت بە پیت</h2>
<p class="note">هەر یەک لە %%NTRACED%% شێوە پیتەکە لە فایلی فۆنتەکەوە وێنە کراوە و لەسەر هەمان پیتی دەستنووسەکە دانراوە، بە هەمان شوێن و قەبارە. لێواری مەرەکەبەکە سەربەخۆ لە وێنەکە دەرهێنراوە (ئەو شوێنەی ڕەنگەکە نیوەی نێوان مەرەکەب و پێستەکەیە) و دووریی نێوان هەردوو لێوارەکە بە پیکسڵی وێنەکە پێوراوە.</p>
<div class="stats">
  <div class="stat"><b>%%A_EDGE%% px</b><span>تێکڕای دووریی لێواری فۆنت لە لێواری مەرەکەب</span></div>
  <div class="stat"><b>%%A_P95%% px</b><span>٩٥٪ی لێوارەکان لەمە نزیکترن</span></div>
  <div class="stat"><b>%%A_AREA%%٪</b><span>جیاوازیی ڕووبەری پیتەکان</span></div>
  <div class="stat"><b>%%A_WORST%% px</b><span>خراپترین پیت (تێکڕای لێوارەکەی)</span></div>
</div>
<p class="legend">لە هەر خانەیەکدا سێ وێنە هەیە. چەپ: پیتەکە لە دەستنووسەکەدا. ناوەڕاست: هەمان وێنە، لێواری مەرەکەب بە <span class="key" style="background:#00c8ff"></span>شینی کاڵ و لەسەری لێواری فۆنتەکە بە <span class="key" style="background:#ff1e1e"></span>سوور. ڕاست: جیاوازییەکە — <span class="key" style="background:#3c2818"></span>هەردووکیان، <span class="key" style="background:#0096ff"></span>مەرەکەب هەیە و فۆنت نییە، <span class="key" style="background:#ff3c28"></span>فۆنت هەیە و مەرەکەب نییە، <span class="key" style="background:#e1e1e1"></span>شوێنی پەیوەستبوون (لە پێوانەکە دەرکراوە، چونکە لەوێ ئەستووریی هێڵەکە یەکسان کراوە).</p>
<div class="grid">
%%CELLS%%
</div>

<h2>ئەو شێوانەی لەم دوو پەڕەیەدا نین</h2>
<section class="card">
<p class="note">ئەم شێوانە لە دوو پەڕە وردەکەی دەستنووسەکەدا نەهاتوون، بۆیە لە پارچە بڕدراوەکان دروستکراون:</p>
<ul class="plain">%%DERIVED%%</ul>
<p class="note">خاڵەکان وەک دەستنووسەکە هێڵی بچووکی لارن. هەمزە، بزوێنەکان، ژمارەکان، نیشانەکانی خاڵبەندی و نیشانە کوردییەکان (ڤ ی سەر ڵ ڕ ۆ ێ، هێڵی دووەمی گ) لە دەستنووسەکەدا نین و بە هەمان ئەستووری کێشراون.</p>
</section>

<h2>Madinah Naqsh — نەخشی بەردی الأحزاب ٧٠–٧١</h2>
<section class="card">
  <figure class="ms">
    <img loading="lazy" alt="نەخشی بەردی ئایەتەکانی ٧٠ و ٧١ی سورەتی الأحزاب" src="data:image/jpeg;base64,%%MN_PHOTO%%">
    <figcaption>نەخشێکی بەرد لە دەوری مەدینە: «بسم الله الرحمن الرحیم / یایها الذین امنوا اتقوا الله وقولوا / قولا سدیدا یصلح لکم اعملکم / ویغفر لکم ذنوبکم ومن یطع الله / ورسوله فقد فاز فوزا عظیما». دۆزینەوە، وێنەگرتن و خوێندنەوەی نەخشەکە: محمد المغذوی، ئەکاونتی «نوادر الآثار والنقوش» (<a href="https://x.com/mohammed93athar" target="_blank" rel="noopener" dir="ltr">@mohammed93athar</a>) — <a href="https://x.com/mohammed93athar/status/1322206509770694656" target="_blank" rel="noopener">پۆستەکە</a>. وێنەکە بۆ بەکارهێنانی خۆتە؛ بڵاوکردنەوەی پێویستی بە ڕەزامەندیی ئەوە.</figcaption>
  </figure>
</section>
<p class="note"><b>ئەمە فۆنتێکی سەرەتاییە.</b> وێنەکە تەنها ١٠٢٤×٦٧٣ پیکسڵە و لە گۆشەیەکەوە گیراوە، بۆیە پیتەکان تێیدا تەنها ٣٠ تا ٧٠ پیکسڵ بەرزن و هێڵەکانی خوارەوە گەورەترن لە سەرەوە. فۆنتەکە شێوەی گشتیی هەڵکۆڵینەکە دەگرێت، نەک وردەکاریی لێوارەکانی. تەنها سێ هێڵی خوارەوە بەکارهاتوون؛ دوو هێڵی سەرەوە زۆر بچووکن.</p>
%%MN_LINES%%
<div class="stats">
  <div class="stat"><b>%%MN_N%%</b><span>شێوەی پیت لە نەخشەکە هێڵکاری کراون</span></div>
  <div class="stat"><b>٣٤</b><span>شێوە لە پارچەکان دروستکراون</span></div>
  <div class="stat"><b>%%MN_EDGE%% px</b><span>تێکڕای دووریی لێواری فۆنت لە لێواری هەڵکۆڵینەکە، بە پیکسڵی وێنەکە</span></div>
  <div class="stat"><b>%%MN_P95%% px</b><span>٩٥٪ی لێوارەکان لەمە نزیکترن</span></div>
</div>
<p class="legend">هەمان سێ وێنەی سەرەوە: پیتەکە لە نەخشەکەدا، لێواری هەڵکۆڵینەکە (شینی کاڵ) و لێواری فۆنتەکە (سوور) لەسەری، و جیاوازییەکە. ژمارەکان بچووکن چونکە هەر پیکسڵێکی وێنەکە بەشێکی گەورەی پیتەکەیە؛ سنووردارکەرەکە وێنەکەیە نەک هێڵکارییەکە. لە پیتەکانی هێڵی سێیەمدا ٢٫٥ پیکسڵ لە هەر لایەک لابراوە، چونکە لێڵیی وێنەکە پیتە بچووکەکان ئەستوورتر پیشان دەدات.</p>
<div class="grid">
%%MN_CELLS%%
</div>
<section class="card">
<p class="note">ئەم شێوانە لە نەخشەکەدا نین و لە پارچە هێڵکاریکراوەکان دروستکراون:</p>
<ul class="plain">%%MN_DERIVED%%</ul>
<p class="note">نەخشەکە خاڵ و بزوێنی نییە. خاڵەکان (بازنەیی)، هەمزە، بزوێنەکان، ژمارەکان، خاڵبەندی و نیشانە کوردییەکان بە قەڵەمێکی بازنەیی بە ئەستووریی هەڵکۆڵینەکە کێشراون.</p>
</section>

<h2>شێوەکانی پیتەکان — Birmingham Hijazi</h2>
<section class="card forms-wrap">
<table class="forms">
<thead><tr><th>سەرەتا</th><th>ناوەڕاست</th><th>کۆتایی</th><th>تەنها</th></tr></thead>
<tbody>
%%FORMS%%
</tbody>
</table>
</section>

<h2>سەرچاوە</h2>
<section class="card">
  <figure class="ms">
    <img alt="هەردوو پەڕەی دەستنووسی قورئانی بیرمینگهام" loading="lazy" src="data:image/jpeg;base64,%%MS_FULL%%">
    <figcaption>دەستنووسی قورئانی بیرمینگهام (Mingana Islamic Arabic 1572a)، کتێبخانەی توێژینەوەی کادبەری، زانکۆی بیرمینگهام. لای چەپ: پەڕەی ٢ ڕوو (مریم ٩١ – طه ١٣)؛ لای ڕاست: پەڕەی ١ پشت (الکهف ٢٣–٣١). وێنەکە Public Domain ە (Wikimedia Commons). تەمەنی پێست: ٥٦٨–٦٤٥ ز.</figcaption>
  </figure>
</section>
</div>

<script>
const PRESETS = %%PRESETS%%;
const txt = document.getElementById('txt');
const size = document.getElementById('size');
const sizev = document.getElementById('sizev');
const ss01 = document.getElementById('ss01');
const ss02 = document.getElementById('ss02');
const btns = [...document.querySelectorAll('.presets button')];
function render(){
  document.querySelectorAll('.sample').forEach(el => { el.textContent = txt.value; });
}
function feats(){
  const f = [];
  if (ss01.checked) f.push('"ss01"');
  if (ss02.checked) f.push('"ss02"');
  document.querySelectorAll('.sample.bh').forEach(el => { el.style.fontFeatureSettings = f.join(',') || 'normal'; });
}
function setSize(){
  sizev.textContent = size.value;
  document.documentElement.style.setProperty('--size', size.value + 'px');
}
function fitLines(){
  // set each line in the font at the scale of the photograph above it
  document.querySelectorAll('.cmp').forEach(f => {
    const w = f.querySelector('img').clientWidth;
    if (w) f.querySelector('.cmp-font').style.fontSize = (w * parseFloat(f.dataset.em)) + 'px';
  });
}
btns.forEach(b => b.addEventListener('click', () => {
  txt.value = PRESETS[+b.dataset.i];
  btns.forEach(x => x.classList.toggle('on', x === b));
  render();
}));
txt.addEventListener('input', () => { btns.forEach(x => x.classList.remove('on')); render(); });
size.addEventListener('input', setSize);
ss01.addEventListener('change', feats);
ss02.addEventListener('change', feats);
window.addEventListener('resize', fitLines);
window.addEventListener('load', fitLines);
txt.value = PRESETS[0]; btns[0].classList.add('on');
setSize(); render(); feats(); fitLines();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
