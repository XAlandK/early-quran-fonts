#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Write the self-contained font preview page (fonts and images embedded).

The page is bilingual: every piece of interface text is written in Central
Kurdish and in English, and a button in the header switches between them
(the choice is remembered; ?lang=en or ?lang=ckb in the address picks one).
Arabic-script samples, letter tables and quotations stay right-to-left in both.

Usage:  python make_preview.py [project folder]
        (run audit.py first: the page shows its pictures and figures from source/audit/)
Needs:  numpy, pillow, scipy, scikit-image, shapely
"""
import base64
import html
import io
import json
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tracer as T  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..")
BH_DIR = "Birmingham Hijazi (new - from the Birmingham manuscript)"
KUFI = "Kufic (later style - not Birmingham)"
MN_DIR = "Madinah Naqsh (draft - from the Ahzab 70-71 inscription)"
HIJAZI = "Hijazi - general (Khalid Alabdullah, 2019)"

FONTS = [
    # css name, path, title, (subtitle ckb, en), [(tag ckb, en)], (badge ckb, en) or None
    # (fonts with a badge are ours and have ss01 / ss02)
    ("Birmingham Hijazi", f"{BH_DIR}/BirminghamHijazi-Regular.ttf", "Birmingham Hijazi",
     ("وەشانی ٤٫١ — پیتەکان ڕاستەوخۆ لە مەرەکەبی دەستنووسی بیرمینگهام و پەڕەکانی هەمان مصحف لە پاریس هێڵکاری کراون",
      "Version 4.1 — the letters are traced directly from the ink of the Birmingham manuscript "
      "and of the leaves of the same Qur'an in Paris"),
     [("خەتی حیجازی", "Hijazi script"), ("سەدەی یەکەمی کۆچی (٥٦٨–٦٤٥ ز)", "1st century AH (568–645 CE)"),
      ("ss01 · ss02", "ss01 · ss02"), ("کوردیش دەنووسێت", "Writes Kurdish too")],
     ("نوێ", "New")),
    ("Madinah Naqsh", f"{MN_DIR}/MadinahNaqsh-Regular.ttf", "Madinah Naqsh",
     ("وەشانی سەرەتایی ٠٫٢ — هێڵی ناوەڕاست و ئەستووریی هەر هێڵێک لە نەخشێکی بەردی دەوری مەدینە (الأحزاب ٧٠–٧١)",
      "Draft 0.2 — the centre line and width of every stroke, from a rock inscription near Medina (al-Ahzab 70–71)"),
     [("نەخشی بەرد", "Rock inscription"), ("٢٨ شێوەی هێڵکاریکراو، ٣٤ی دروستکراو", "28 forms traced, 34 assembled"),
      ("ss01 · ss02", "ss01 · ss02"), ("کوردیش دەنووسێت", "Writes Kurdish too")],
     ("سەرەتایی", "Draft")),
    ("Hijazi KA", f"{HIJAZI}/hijazi.ttf", "Hijazi",
     ("حیجازیی گشتی — خالید العبدالله، ٢٠١٩ (وەشانی تاقیکاری)",
      "General Hijazi — Khalid Alabdullah, 2019 (experimental version)"),
     [("خەتی حیجازی", "Hijazi script"), ("CC BY-NC 4.0 — بازرگانی نا", "CC BY-NC 4.0 — non-commercial")],
     None),
    ("Raqq", f"{KUFI}/Raqq/Raqq.ttf", "Raqq · رَقّ",
     ("کوفیی مصحفی — شێوازی سەدەی سێیەمی کۆچی (Aliftype)",
      "Qur'anic Kufic — the style of the 3rd century AH (Aliftype)"),
     [("کوفی", "Kufic"), ("AGPL-3.0", "AGPL-3.0")], None),
    ("Qahiri", f"{KUFI}/Qahiri/Qahiri-Regular.ttf", "Qahiri · قاهري",
     ("کوفیی مصحفیی ڕێکخراو (Aliftype)", "Regularised Qur'anic Kufic (Aliftype)"),
     [("کوفی", "Kufic"), ("OFL 1.1", "OFL 1.1")], None),
    ("Qashib", f"{KUFI}/Qashib/Qashib.ttf", "Qashib · قشيب",
     ("کوفیی مصحفیی نوێکراوە، پیتی ئاسانتر بۆ خوێندنەوە (Aliftype)",
      "Modernised Qur'anic Kufic, with letters that are easier to read (Aliftype)"),
     [("کوفی", "Kufic"), ("AGPL-3.0", "AGPL-3.0")], None),
]

PRESETS = [
    (("دەقی دەستنووسەکە", "Manuscript text"),
     "بسم الله الرحمن الرحيم طه ۔ ما انزلنا عليك القران لتشقى ۔ الا تذكره لمن يخشى ۔ "
     "تنزيلا ممن خلق الارض والسموت العلى ۔ الرحمن على العرش استوى ۔"),
    (("دەقی نەخشەکە", "Inscription text"),
     "يايها الذين امنوا اتقوا الله وقولوا قولا سديدا يصلح لكم اعملكم ويغفر لكم ذنوبكم "
     "ومن يطع الله ورسوله فقد فاز فوزا عظيما"),
    (("بە بزوێنەوە", "With vowel marks"),
     "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ ۔ طه ۔ مَآ أَنزَلْنَا عَلَيْكَ ٱلْقُرْءَانَ لِتَشْقَىٰٓ"),
    (("کوردی", "Kurdish"), "ئەم فۆنتە لە دەستنووسی قورئانی بیرمینگهامەوە هێڵکاری کراوە، ڕۆژێکی خۆش ڵ گ ڤ پ چ ژ"),
    (("پیتەکان", "Letters"), "ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي ء ة ى لا"),
    (("ژمارەکان", "Digits"), "٠ ١ ٢ ٣ ٤ ٥ ٦ ٧ ٨ ٩ ، ؛ ؟"),
]

# manuscript lines set again in the font: (page, line index, x0, x1, text as the scribe spelled it, caption)
LINES = [
    ("L", 12, 280, 1780, "الا تذكره لمن يخشى",
     ("هێڵی ١١ی پەڕەی ٢ ڕوو (سورەتی طه، ئایەتی ٣)", "Folio 2r, line 11 (Sura Ta-Ha, verse 3)")),
    ("L", 17, 280, 1780, "الا هو له الاسما ا",
     ("هێڵی ١٦ی پەڕەی ٢ ڕوو (سورەتی طه، ئایەتی ٨)", "Folio 2r, line 16 (Sura Ta-Ha, verse 8)")),
    ("L", 21, 280, 1780, "تيها نودى يموسى",
     ("هێڵی ٢٠ی پەڕەی ٢ ڕوو (سورەتی طه، ئایەتی ١١)", "Folio 2r, line 20 (Sura Ta-Ha, verse 11)")),
]

RASM = [("ALIF", "ا"), ("BEH", "ب ت ث"), ("NOON", "ن"), ("YEH", "ی"), ("HAH", "ج ح خ"), ("DAL", "د ذ"),
        ("REH", "ر ز"), ("SEEN", "س ش"), ("SAD", "ص ض"), ("TAH", "ط ظ"), ("AIN", "ع غ"), ("FEH", "ف"),
        ("QAF", "ق"), ("KAF", "ک"), ("LAM", "ل"), ("MEEM", "م"), ("HEH", "ه"), ("WAW", "و"),
        ("LAMALEF", "لا")]
FORM = [("isol", "تەنها", "isolated"), ("init", "سەرەتا", "initial"),
        ("medi", "ناوەڕاست", "medial"), ("fina", "کۆتایی", "final")]
# the nine forms that do not occur on the two large Birmingham pages: where each was found
# on the leaves of the same Qur'an in Paris (BnF Arabe 328, folios 71-86)
PARIS = [
    ("MEEM.isol", "م", ("تەنها", "isolated"), "قوم", ("هود ٨٩", "Q 11:89"), "77r"),
    ("QAF.isol", "ق", ("تەنها", "isolated"), "ورزق", ("طه ١٣١", "Q 20:131"), "79r"),
    ("AIN.isol", "ع غ", ("تەنها", "isolated"), "تجوع", ("طه ١١٨", "Q 20:118"), "78v"),
    ("SAD.fina", "ص ض", ("کۆتایی", "final"), "متربص", ("طه ١٣٥", "Q 20:135"), "79r"),
    ("TAH.fina", "ط ظ", ("کۆتایی", "final"), "محيط", ("هود ٨٤", "Q 11:84"), "77r"),
    ("FEH.fina", "ف", ("کۆتایی", "final"), "كيف", ("يونس ٣٥", "Q 10:35"), "71r"),
    ("FEH.isol", "ف", ("تەنها", "isolated"), "سوف", ("هود ٩٣", "Q 11:93"), "77r"),
    ("HAH.fina", "ج ح خ", ("کۆتایی", "final"), "صلح", ("هود ٨٩", "Q 11:89"), "77r"),
    ("HAH.isol", "ج ح خ", ("تەنها", "isolated"), "ينوح", ("هود ٣٢", "Q 11:32"), "75r"),
]
PARIS_AT = {p[0]: p for p in PARIS}


def folio(f):
    """'77r' -> ('٧٧ ڕوو', '77r')"""
    return ku(f[:-1]) + (" ڕوو" if f[-1] == "r" else " پشت"), f


LETTERS = "ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي ى ة پ چ ژ ڕ ڤ ک گ ڵ ە ۆ ی ێ".split()
DUAL = set("ب ت ث ج ح خ س ش ص ض ط ظ ع غ ف ق ك ل م ن ه ي ى پ چ ڤ ک گ ڵ ی ێ")
DIGITS = "٠١٢٣٤٥٦٧٨٩"


def ku(n):
    return "".join(DIGITS[int(c)] if c.isdigit() else ("٫" if c == "." else c) for c in str(n))


def L(ckb, en):
    """The same content in Kurdish and in English; the page shows one of them."""
    return '<span data-l="ckb">%s</span><span data-l="en">%s</span>' % (ckb, en)


def Lx(pair):
    """L() for a (Kurdish, English) pair of plain text."""
    return L(html.escape(pair[0]), html.escape(pair[1]))


def num(x, unit=""):
    """A number in Kurdish (Eastern Arabic) and in English (Western) digits."""
    return L(ku(x) + unit, str(x) + unit)


def b64(path):
    with open(os.path.join(ROOT, path), "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def jpg(im, q=74):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=q, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def line_strip(page, pg, idx, x0, x1, up=185, dn=120):
    L_ = page.lines[pg][idx - 1]
    out = np.full((up + dn, x1 - x0, 3), 235, dtype=np.uint8)
    for x in range(x0, x1):
        yb = int(round(L_['r'] + L_['m'] * (x - L_['x0'])))
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


def figure_line(em, alt, pic, text, caption, mn=False):
    """A line of the source with the same text set in the font underneath."""
    return ('<figure class="cmp" data-em="%.4f">'
            '<img alt="%s" data-alt-en="%s" src="data:image/jpeg;base64,%s">'
            '<div class="cmp-font%s" dir="rtl">%s</div>'
            '<figcaption>%s</figcaption>'
            '</figure>' % (em, html.escape(alt[0]), html.escape(alt[1]), pic, " mn" if mn else "",
                           html.escape(text), caption))


def letter_cell(letters, form, pic, where):
    form_ckb, form_en = next((k, e) for f, k, e in FORM if f == form)
    return ('<figure class="lt">'
            '<img loading="lazy" alt="%s %s" data-alt-en="%s %s" src="data:image/jpeg;base64,%s">'
            '<figcaption><span class="lbl"><b dir="rtl">%s</b> · %s</span><span class="where">%s</span></figcaption>'
            '</figure>' % (html.escape(letters), form_ckb, html.escape(letters), form_en, pic,
                           html.escape(letters), L(form_ckb, form_en), where))


def derived_list(items):
    return "".join('<li><b dir="rtl">%s</b> (%s): %s</li>' % (html.escape(a), Lx(b), Lx(c)) for a, b, c in items)


def paris_list():
    out = []
    for key, letters, form, word, verse, f in PARIS:
        out.append('<li><b dir="rtl">%s</b> (%s): %s</li>' % (
            html.escape(letters), Lx(form),
            L('لە وشەی «<span dir="rtl">%s</span>» (%s)، پەڕەی %s' % (html.escape(word), html.escape(verse[0]), folio(f)[0]),
              'from the word «<span dir="rtl">%s</span>» (%s), folio %s' % (html.escape(word), verse[1], f))))
    return "".join(out)


MN_LINES = [   # line of prep's page, x0, x1, text as carved, caption
    (1, 100, 2060, "ورسوله فقد فاز فوزا عظيما", ("هێڵی پێنجەم", "Fifth line")),
    (2, 620, 2880, "ويغفر لكم ذنوبكم ومن يطع",
     ("هێڵی چوارەم (بێ وشەی «الله»ی کۆتایی)", "Fourth line (without its last word, «الله»)")),
    (3, 1180, 3350, "قولا سديدا يصلح لكم",
     ("هێڵی سێیەم (بێ وشەی «اعملكم»)", "Third line (without the word «اعملكم»)")),
]
MN_DERIVED = [
    ("ب ت ث ن ی", ("ناوەڕاست", "medial"),
     ("ددانی سەرەتا، لەگەڵ هێڵی بەستن لە لای ڕاست", "the initial tooth, with a joining stroke on the right")),
    ("ب ت ث", ("کۆتایی و تەنها", "final and isolated"),
     ("ددانەکە، لەگەڵ هێڵێکی تەخت بەرەو چەپ", "the tooth, with a flat stroke to the left")),
    ("ن", ("تەنها", "isolated"), ("«ن»ی کۆتایی، بێ هێڵی بەستن", "final nun, without the joining stroke")),
    ("ی", ("کۆتایی و تەنها", "final and isolated"),
     ("ددانەکە، لەگەڵ کلکی «ن»ی کۆتایی — لە نەخشەکەدا «ی»ی کۆتایی نییە",
      "the tooth, with the tail of final nun — the inscription has no final ya'")),
    ("ج ح خ", ("سەرەتا، ناوەڕاست، تەنها", "initial, medial, isolated"),
     ("سەری «ح»ی کۆتایی، بێ کلکەکەی یان بێ هێڵی بەستن",
      "the head of final ha', without its tail or without the joining stroke")),
    ("س ش", ("ناوەڕاست", "medial"), ("ددانەکانی سەرەتا، لەگەڵ هێڵی بەستن", "the teeth of initial sin, with a joining stroke")),
    ("س ش · ص ض · ق · ل", ("کۆتایی و تەنها", "final and isolated"),
     ("شێوەی ناوەڕاست یان سەرەتا، لەگەڵ کلکی «ن»ی کۆتایی", "the medial or initial form, with the tail of final nun")),
    ("ص ض", ("سەرەتا", "initial"), ("«ص»ی ناوەڕاست، بێ هێڵی بەستنی ڕاست", "medial sad, without the joining stroke on the right")),
    ("ط ظ", ("سەرەتا، کۆتایی، تەنها", "initial, final, isolated"),
     ("«ط»ی ناوەڕاست، بێ هێڵی بەستنی یەک لا یان هەردوو لا",
      "medial ta', without the joining stroke on one side or on both")),
    ("ع غ", ("تەنها", "isolated"), ("«ع»ی کۆتایی، بێ هێڵی بەستن", "final 'ayn, without the joining stroke")),
    ("ف", ("کۆتایی و تەنها", "final and isolated"),
     ("بازنەکەی، لەگەڵ هێڵێکی تەخت بەرەو چەپ", "its loop, with a flat stroke to the left")),
    ("ک", ("سەرەتا، کۆتایی، تەنها", "initial, final, isolated"),
     ("«ک»ی ناوەڕاست، بێ هێڵی بەستنی یەک لا یان هەردوو لا",
      "medial kaf, without the joining stroke on one side or on both")),
    ("م", ("ناوەڕاست و تەنها", "medial and isolated"),
     ("«م»ی سەرەتا لەگەڵ هێڵی بەستن؛ «م»ی کۆتایی بێ هێڵی بەستن",
      "initial mim with a joining stroke; final mim without one")),
    ("ه", ("سەرەتا، ناوەڕاست، تەنها", "initial, medial, isolated"),
     ("«ه»ی کۆتایی، لەگەڵ یان بێ هێڵی بەستن", "final ha', with or without joining strokes")),
    ("لا", ("کۆتایی", "final"), ("«لا»ی تەنها، لەگەڵ هێڵی بەستن", "isolated lam-alif, with a joining stroke")),
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
        sq = float(lines[idx - 1].get("squeeze", 1.0))          # the line is narrowed by this in the font
        im = Image.fromarray(page[r - up:r + dn, x0:x1])
        im = im.resize((1200, int(im.height * 1200 / (im.width * sq))), Image.LANCZOS)
        caption = L(html.escape(cap[0]) + " — سەرەوە نەخشەکە (ڕاستکراوە، گەورەکراو و بە پێی لاری وێنەکە تەسککراو)، خوارەوە هەمان دەق بە فۆنتەکە بە هەمان قەبارە.",
                    html.escape(cap[1]) + " — top: the inscription (levelled, enlarged, and narrowed for the slant of the photograph); bottom: the same text in the font at the same size.")
        out_lines.append(figure_line(1000 * T.PXU / ((x1 - x0) * sq), cap, jpg(im, 80), text, caption, mn=True))
    cells = []
    for name, letters in RASM:
        for form, _, _ in FORM:
            key = "%s.%s" % (name, form)
            if key not in traced or key not in arow:
                continue
            ln = lines[traced[key]["src"]["line"] - 1]["name"]
            e = "%.2f" % arow[key]["crest"]
            with open(os.path.join(src, "audit", key + ".jpg"), "rb") as fh:
                pic = base64.b64encode(fh.read()).decode("ascii")
            where = L("دێڕی %s · هێڵی ناوەڕاست %s px لە لووتکەی هەڵکۆڵینەکە" % (ku(ln), ku(e)),
                      "line %s · centre line %s px from the crest of the carving" % (ln, e))
            cells.append(letter_cell(letters, form, pic, where))
    photo = Image.open(os.path.join(src, "naqsh", "photo.jpg")).convert("RGB")
    am = audit["mean"]
    return {
        "%%MN_PHOTO%%": jpg(photo, 80), "%%MN_LINES%%": "\n".join(out_lines), "%%MN_CELLS%%": "\n".join(cells),
        "%%MN_N%%": num(len(cells)), "%%MN_EDGE%%": num("%.2f" % am["crest"], " px"),
        "%%MN_P95%%": num("%.2f" % am["c95"], " px"), "%%MN_EDGE2%%": num("%.2f" % am["edge"], " px"),
        "%%MN_DERIVED%%": derived_list(MN_DERIVED),
    }


def main():
    src = os.path.join(HERE, "manuscript", "full.jpg")
    page = T.Page(src, json.load(open(os.path.join(HERE, "lines.json"))))
    traced = json.load(open(os.path.join(HERE, "traced.json"), encoding="utf-8"))

    faces = "\n".join(
        '@font-face{font-family:"%s";src:url(data:font/ttf;base64,%s) format("truetype");font-display:block}'
        % (f[0], b64(f[1])) for f in FONTS)

    # 1. whole lines
    lines_html = []
    em = 1000 * T.PXU          # manuscript pixels per em
    for pg, idx, x0, x1, text, cap in LINES:
        im = line_strip(page, pg, idx, x0, x1)
        caption = L(html.escape(cap[0]) + " — سەرەوە دەستنووسەکە، خوارەوە هەمان دەق بە فۆنتەکە بە هەمان قەبارە.",
                    html.escape(cap[1]) + " — top: the manuscript; bottom: the same text in the font at the same size.")
        lines_html.append(figure_line(em / (x1 - x0), cap, jpg(im, 78), text, caption))

    # 2. letter by letter: the pictures and figures of the pixel audit
    audit = json.load(open(os.path.join(HERE, "audit", "audit.json")))
    arow = {r["key"]: r for r in audit["rows"]}
    cells = []
    for name, letters in RASM:
        for form, _, _ in FORM:
            key = "%s.%s" % (name, form)
            if key not in traced or key not in arow:
                continue
            s = traced[key]["src"]
            e = "%.2f" % arow[key]["edge"]
            if key in PARIS_AT:                    # one of the nine forms from the Paris leaves
                _, _, _, word, verse, f = PARIS_AT[key]
                where = L("پاریس، پەڕەی %s، «%s» (%s) · جیاوازیی لێوار %s px" % (folio(f)[0], html.escape(word), verse[0], ku(e)),
                          "Paris, folio %s, «%s» (%s) · edge difference %s px" % (f, html.escape(word), verse[1], e))
            else:
                ln = text_line(s["page"], s["line"])
                where = L("%s، هێڵی %s · جیاوازیی لێوار %s px" % ("پەڕەی ٢ ڕوو" if s["page"] == "L" else "پەڕەی ١ پشت", ku(ln), ku(e)),
                          "%s, line %s · edge difference %s px" % ("folio 2r" if s["page"] == "L" else "folio 1v", ln, e))
            with open(os.path.join(HERE, "audit", key + ".jpg"), "rb") as fh:
                pic = base64.b64encode(fh.read()).decode("ascii")
            cells.append(letter_cell(letters, form, pic, where))
    am = audit["mean"]
    worst = max(audit["rows"], key=lambda r: r["edge"])
    var = json.load(open(os.path.join(HERE, "audit", "variation.json")))["summary"]
    dash = json.load(open(os.path.join(HERE, "dash.json")))
    cen = json.load(open(os.path.join(HERE, "audit", "census.json")))
    px = lambda v, f="%.1f": num(f % v, " px")

    cards = []
    for css, path, title, sub, tags, badge in FONTS:
        tag_html = "".join('<span class="tag">%s</span>' % Lx(t) for t in tags)
        cards.append(
            '<section class="card%s">'
            '<div class="meta"><div><h3>%s%s</h3><p>%s</p></div><div class="tags">%s</div></div>'
            '<div class="sample%s" dir="rtl" style="font-family:\'%s\'"></div>'
            '<div class="path" dir="ltr">%s</div>'
            '</section>' % (
                " new" if badge else "", html.escape(title),
                ' <span class="badge">%s</span>' % Lx(badge) if badge else "", Lx(sub), tag_html,
                " bh" if badge else "", css, html.escape(path)))

    preset_btns = "".join('<button type="button" data-i="%d">%s</button>' % (i, Lx(n))
                          for i, (n, _) in enumerate(PRESETS))
    presets_js = "[" + ",".join('"%s"' % t.replace("\\", "\\\\").replace('"', '\\"') for _, t in PRESETS) + "]"

    full = Image.open(src)
    full = full.resize((1100, int(full.height * 1100 / full.width)), Image.LANCZOS)

    # [[Kurdish||English]] in the template -> both, one of which is shown
    page_html = re.sub(r"\[\[(.*?)\|\|(.*?)\]\]", lambda m: L(m.group(1), m.group(2)), TEMPLATE, flags=re.S)
    for k, v in madinah().items():
        page_html = page_html.replace(k, v)
    for k, v in {
        "%%PRESET_BTNS%%": preset_btns, "%%PRESETS%%": presets_js, "%%CARDS%%": "\n".join(cards),
        "%%LINES%%": "\n".join(lines_html), "%%CELLS%%": "\n".join(cells), "%%NTRACED%%": num(len(cells)),
        "%%PARIS%%": paris_list(), "%%A_EDGE%%": num("%.2f" % am["edge"], " px"),
        "%%V_N%%": num(var["instances"]), "%%V_SCRIBE%%": px(var["scribe"], "%.2f"),
        "%%V_FONT%%": px(var["font"], "%.2f"),
        "%%X_N%%": num(var.get("cross_paris", 0)), "%%X_WITHIN%%": px(var.get("within", 0), "%.2f"),
        "%%X_ACROSS%%": px(var.get("across", 0), "%.2f"),
        "%%C_PAGES%%": num(cen["summary"]["pages"]), "%%C_PLACES%%": num(cen["summary"]["places_looked_at"]),
        "%%C_N%%": num(cen["summary"]["instances"]),
        "%%C_DONE%%": num(sum("rank" in f for f in cen["forms"].values())),
        "%%C_GOOD%%": num(sum(f.get("rank", 1) < 0.5 for f in cen["forms"].values())),
        "%%C_SCRIBE%%": px(cen["summary"]["to_middle_scribe"], "%.2f"), "%%C_FONT%%": px(cen["summary"]["to_middle_font"], "%.2f"),
        "%%C_HEH%%": b64(os.path.join(BH_DIR, "source", "audit", "census", "HEH.medi.jpg")),
        "%%C_MEEM%%": b64(os.path.join(BH_DIR, "source", "audit", "census", "MEEM.fina.jpg")),
        "%%C_WAW%%": b64(os.path.join(BH_DIR, "source", "audit", "census", "WAW.isol.jpg")),
        "%%C_KAF%%": b64(os.path.join(BH_DIR, "source", "audit", "census", "KAF.init.jpg")),
        "%%D_N%%": num(dash["n"]), "%%D_LEN%%": px(dash["length"]), "%%D_THICK%%": px(dash["thickness"]),
        "%%D_ANGLE%%": num("%.0f" % dash["angle"], "°"), "%%D_STACK%%": px(dash["stack_down"]),
        "%%D_GAP%%": px(dash["gap"]),
        "%%A_P95%%": num("%.2f" % am["p95"], " px"),
        "%%A_AREA%%": L(ku("%.1f" % (abs(am["area"] - 1) * 100)) + "٪", "%.1f%%" % (abs(am["area"] - 1) * 100)),
        "%%A_WORST%%": num("%.2f" % worst["edge"], " px"), "%%FORMS%%": forms_table(),
        "%%MS_FULL%%": jpg(full, 72), "%%FACES%%": faces,
    }.items():
        page_html = page_html.replace(k, v)
    out = os.path.join(ROOT, "پیشاندانی-فۆنتەکان.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page_html)
    print("wrote", out, round(len(page_html) / 1024), "KB,", len(cells), "traced forms")


TEMPLATE = r"""<!doctype html>
<html lang="ckb" dir="rtl" data-title-ckb="فۆنتە کۆنەکانی قورئان" data-title-en="Early Qur'an Fonts">
<head>
<!-- Copyright (c) 2026 Aland Kawa Ali. Licensed under AANCL v1.0. See the LICENSE file.
     The third-party fonts and photographs embedded in this page keep their own licenses;
     see THIRD_PARTY_NOTICES.md. -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>فۆنتە کۆنەکانی قورئان</title>
<script>
// choose the language before the page is drawn: ?lang=, then the last choice, then Kurdish
(function(){
  var l = 'ckb';
  try { l = localStorage.getItem('fontsLang') || l; } catch (e) {}
  var q = new URLSearchParams(location.search).get('lang');
  if (q === 'en' || q === 'ckb') l = q;
  var h = document.documentElement;
  h.lang = l; h.dir = l === 'en' ? 'ltr' : 'rtl';
  document.title = l === 'en' ? h.dataset.titleEn : h.dataset.titleCkb;
})();
</script>
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
html[lang=ckb] [data-l=en], html[lang=en] [data-l=ckb]{display:none !important}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI","Noto Sans Arabic","Geeza Pro",sans-serif;line-height:1.6}
.wrap{max-width:1100px;margin:0 auto;padding:0 16px 48px}
header{padding:28px 0 8px}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
h1{font-size:clamp(22px,4vw,32px);margin:0 0 4px}
.lead{color:var(--muted);margin:0}
#lang{flex:none;margin-top:6px;font-weight:600}
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
  overflow-wrap:anywhere;white-space:pre-wrap;text-align:right}
.path{font-size:11px;color:var(--muted);text-align:left;opacity:.8;overflow-wrap:anywhere}
figure{margin:0}
.note{font-size:14px;color:var(--muted)}
.cmp{margin:0 0 18px}
.cmp img{width:100%;height:auto;display:block;border-radius:10px 10px 0 0}
.cmp-font.mn{font-family:"Madinah Naqsh";line-height:1.9}
.cmp-font{font-family:"Birmingham Hijazi";font-feature-settings:"ss01","ss02";color:#3a2412;background:#ece4ce;
  border-radius:0 0 10px 10px;white-space:nowrap;overflow:hidden;text-align:right;line-height:1.55;
  padding:0 0 0 0;padding-inline-start:1.2%;font-size:40px}
figcaption{font-size:13px;color:var(--muted);margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,440px),1fr));gap:12px}
.lt{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px}
.cen{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:10px 0;align-items:end}.cen figure{margin:0}.cen img{width:100%;height:auto;display:block;border-radius:8px}.cen figcaption{font-size:.82rem;text-align:center;margin-top:4px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:10px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.stat > b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
.stat > span{display:block;font-size:12px;color:var(--muted)}
.key{display:inline-block;width:10px;height:10px;border-radius:2px;margin-inline-end:4px;vertical-align:middle}
.lt img{width:100%;height:auto;display:block;border-radius:6px}
.lt figcaption{display:flex;justify-content:space-between;gap:8px;align-items:baseline;font-size:13px;color:var(--ink)}
.lt figcaption b{font-size:16px}
.lt figcaption .where{color:var(--muted);font-size:12px}
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
  <div class="top">
    <div>
      <h1>[[فۆنتە کۆنەکانی قورئان||Early Qur'an Fonts]]</h1>
      <p class="lead">[[لێرە دەقێک بنووسە یان یەکێک لە نموونەکان هەڵبژێرە، هەموو فۆنتەکان پێکەوە نیشان دەدرێن.||Type a text, or pick one of the samples, and every font shows it.]]</p>
    </div>
    <button id="lang" type="button"><span data-l="ckb" lang="en">English</span><span data-l="en" lang="ckb">کوردی</span></button>
  </div>
</header>

<div class="controls">
  <textarea id="txt" dir="auto" aria-label="دەق" data-label-en="Text"></textarea>
  <div class="row">
    <div class="presets">%%PRESET_BTNS%%</div>
  </div>
  <div class="row">
    <label>[[قەبارە||Size]] <input id="size" type="range" min="18" max="120" value="44"> <span id="sizev">44</span>px</label>
    <label><input id="ss01" type="checkbox"> [[تەنها ڕەسم — بێ خاڵ (ss01)||Rasm only — no dots (ss01)]]</label>
    <label><input id="ss02" type="checkbox"> [[شاردنەوەی بزوێنەکان (ss02)||Hide vowel marks (ss02)]]</label>
  </div>
</div>

<h2>[[فۆنتەکان||Fonts]]</h2>
<p class="note">[[دوو هەڵبژاردەی ss01 و ss02 تەنها لە دوو فۆنتەکەی خۆماندا هەن: Birmingham Hijazi و Madinah Naqsh.||The ss01 and ss02 options exist only in our two fonts, Birmingham Hijazi and Madinah Naqsh.]]</p>
%%CARDS%%

<h2>[[بەراورد لەگەڵ دەستنووسەکە — هێڵ بە هێڵ||Compared with the manuscript — line by line]]</h2>
<p class="note">[[سێ هێڵی دەستنووسەکە، و لە ژێر هەر یەکێکیاندا هەمان دەق (بە ڕێنووسی نووسەرەکە، بێ خاڵ) بە فۆنتی Birmingham Hijazi.||Three lines of the manuscript, each with the same text (in the scribe's spelling, without dots) set in Birmingham Hijazi underneath.]]</p>
%%LINES%%

<h2>[[پشکنینی پیکسڵ بە پیکسڵ — پیت بە پیت||Pixel-by-pixel check — letter by letter]]</h2>
<p class="note">[[هەر یەک لە ||Each of the ]]%%NTRACED%%[[ شێوە پیتەکە لە فایلی فۆنتەکەوە وێنە کراوە و لەسەر هەمان پیتی دەستنووسەکە دانراوە، بە هەمان شوێن و قەبارە. لێواری مەرەکەبەکە سەربەخۆ لە وێنەکە دەرهێنراوە (ئەو شوێنەی ڕەنگەکە نیوەی نێوان مەرەکەب و پێستەکەیە) و دووریی نێوان هەردوو لێوارەکە بە پیکسڵی وێنەکە پێوراوە.|| letter forms was rendered from the font file and laid over the same letter in the manuscript, at the same place and size. The edge of the ink was taken from the photograph independently (where the colour is half-way between the ink and the parchment), and the distance between the two edges was measured in pixels of the photograph.]]</p>
<div class="stats">
  <div class="stat"><b>%%A_EDGE%%</b><span>[[تێکڕای دووریی لێواری فۆنت لە لێواری مەرەکەب||Mean distance between the font's edge and the ink's edge]]</span></div>
  <div class="stat"><b>%%A_P95%%</b><span>[[٩٥٪ی لێوارەکان لەمە نزیکترن||95% of the edges are closer than this]]</span></div>
  <div class="stat"><b>%%A_AREA%%</b><span>[[جیاوازیی ڕووبەری پیتەکان||Difference in the area of the letters]]</span></div>
  <div class="stat"><b>%%A_WORST%%</b><span>[[خراپترین پیت (تێکڕای لێوارەکەی)||The worst letter (its mean edge distance)]]</span></div>
</div>
<p class="note">[[نووسەرەکە خۆی هیچ پیتێکی دوو جار وەک یەک نەنووسیوە. %%V_N%% نموونەی پیتەکان لە هەموو لاپەڕەکان هێڵکاری کران و هەر دووانێکی هەمان پیت لەسەر یەک دانران: دوو نموونەی هەمان پیت بە دەستی نووسەرەکە بە ناوەندی %%V_SCRIBE%% لە یەکتر دوورن، و نموونەی فۆنتەکە %%V_FONT%% لە نموونەکانی تر دوورە. واتە پیتەکانی فۆنتەکە نموونەی ئاسایی نووسەرەکەن، و دووریی فۆنتەکە لە نموونەکەی خۆی زۆر لە جیاوازیی نێوان دوو پیتی نووسەرەکە خۆی کەمترە.||The scribe never wrote a letter twice in the same way. %%V_N%% instances of the letters were traced on all the pages and every two of the same letter laid over each other: two instances of a letter in the scribe's hand are typically %%V_SCRIBE%% apart, and the instance the font uses is %%V_FONT%% from the others. So the letters of the font are ordinary instances of the scribe's writing, and the font is far closer to its own exemplar than two letters of the scribe are to each other.]]</p>
<p class="legend">[[لە هەر خانەیەکدا سێ وێنە هەیە. چەپ: پیتەکە لە دەستنووسەکەدا. ناوەڕاست: هەمان وێنە، لێواری مەرەکەب بە <span class="key" style="background:#00c8ff"></span>شینی کاڵ و لەسەری لێواری فۆنتەکە بە <span class="key" style="background:#ff1e1e"></span>سوور. ڕاست: جیاوازییەکە — <span class="key" style="background:#3c2818"></span>هەردووکیان، <span class="key" style="background:#0096ff"></span>مەرەکەب هەیە و فۆنت نییە، <span class="key" style="background:#ff3c28"></span>فۆنت هەیە و مەرەکەب نییە، <span class="key" style="background:#e1e1e1"></span>شوێنی پەیوەستبوون (لە پێوانەکە دەرکراوە، چونکە لەوێ ئەستووریی هێڵەکە یەکسان کراوە).||Each cell holds three pictures. Left: the letter in the manuscript. Middle: the same picture, with the edge of the ink in <span class="key" style="background:#00c8ff"></span>light blue and the edge of the font over it in <span class="key" style="background:#ff1e1e"></span>red. Right: the difference — <span class="key" style="background:#3c2818"></span>both, <span class="key" style="background:#0096ff"></span>ink where the font has none, <span class="key" style="background:#ff3c28"></span>font where there is no ink, <span class="key" style="background:#e1e1e1"></span>the joins (left out of the measurement, because the stroke is given one thickness there).]]</p>
<div class="grid">
%%CELLS%%
</div>

<h2>[[نۆ شێوە لە پەڕەکانی پاریسەوە||Nine forms from the Paris leaves]]</h2>
<section class="card">
<p class="note">[[دەستنووسی بیرمینگهام دوو پەڕەیە لە مصحفێک کە شازدە پەڕەی تری لە پاریسن (کتێبخانەی نیشتمانیی فەڕەنسا، Arabe 328، پەڕەکانی ٧١–٨٦). لە چوار لاپەڕەکەی بیرمینگهام تەنها دووانیان بە وێنەی گەورە بڵاو کراونەتەوە، و ئەم نۆ شێوەیە لەو دوو لاپەڕەیەدا نەهاتوون. لە وەشانی ٣دا لە پارچەی پیتەکانی تر دروست کرابوون؛ ئێستا وەک هەموو پیتەکانی تر ڕاستەوخۆ لە مەرەکەبی هەمان نووسەر هێڵکاری کراون:||The Birmingham manuscript is two leaves of a Qur'an of which sixteen more leaves are in Paris (Bibliothèque nationale de France, Arabe 328, folios 71–86). Only two of the four Birmingham pages have been published in a large photograph, and these nine forms do not occur on them. In version 3 they were assembled from pieces of other letters; now they are traced from the ink of the same scribe, like all the others:]]</p>
<ul class="plain">%%PARIS%%</ul>
<p class="note">[[بۆ ئەوەی دڵنیا بین کە پەڕەکانی پاریس هەمان دەستخەتن، %%X_N%% پیتی تریشیان لێ هێڵکاری کرا و لەگەڵ هەمان پیت لە بیرمینگهام بەراورد کران: دووریی نێوان پیتێکی پاریس و پیتێکی بیرمینگهام %%X_ACROSS%%ـە، و دووریی نێوان دوو پیتی بیرمینگهام خۆیان %%X_WITHIN%%ـە. نووسەرەکە لە هەندێک لاپەڕەی پاریسدا بچووکتر نووسیویەتی؛ ئەو لاپەڕانە بە پێی پێوانە گەورە کراونەتەوە تا پیتەکانیان بە قەبارەی پیتەکانی بیرمینگهام بن.||To make sure the Paris leaves are in the same hand, %%X_N%% other letters were traced from them and compared with the same letters in Birmingham: a Paris letter is %%X_ACROSS%% from a Birmingham letter, and two Birmingham letters are %%X_WITHIN%% from each other. On some of the Paris pages the scribe wrote smaller; those pages are enlarged, by a measured amount, so that their letters have the size of the Birmingham letters.]]</p>
<p class="note">[[پشکنینی سێیەم هەموو مصحفەکەی گرتەوە: هەر شێوەیەکی فۆنتەکە لەسەر هەر %%C_PAGES%% لاپەڕەکە (دووی بیرمینگهام و سی و دووی پاریس) دانرا و %%C_N%% نموونەی پیتەکان دۆزرانەوە، لە %%C_PLACES%% شوێنی پشکنراو. نموونەکانی هەر پیتێک لەسەر یەک دانران تا «پیتی ناوەند»ی نووسەرەکە دەربکەوێت. نموونەیەکی نووسەرەکە %%C_SCRIBE%% لە پیتی ناوەند دوورە، و پیتی فۆنتەکە %%C_FONT%%. لە %%C_GOOD%% لە %%C_DONE%% شێوەدا پیتی فۆنتەکە لە زۆربەی نموونەکانی نووسەرەکە خۆی نزیکترە لە ناوەند. ئەم پشکنینە دوو هەڵەی دۆزییەوە کە پێشتر نەدەبینران، چونکە لە ناو پیتەکەدان نەک لە لێواری: لە «هـ»ی ناوەڕاستدا پەڵەیەکی مەرەکەبی هەڵوەریو وەک چاوی پیتەکە گیرابوو، و لە «م»ی کۆتاییدا چاوە باریکەکە پڕ کرابووەوە. هەردووکیان لە وەشانی ٤٫١دا چاک کراون. ئاگاداری: نموونەیەک بۆیە دەدۆزرێتەوە چونکە لە پیتی فۆنتەکە دەچێت، بۆیە جیاوازیی ڕاستەقینەی نووسەرەکە لەم ژمارانە گەورەترە.||The third audit took in the whole Qur'an: every form of the font was laid over each of the %%C_PAGES%% pages (two in Birmingham, thirty-two in Paris) and %%C_N%% instances of the letters were found, in %%C_PLACES%% places looked at. The instances of each letter were laid over each other to show the scribe's "middle letter". An instance of the scribe is %%C_SCRIBE%% from the middle letter, the letter of the font %%C_FONT%%. In %%C_GOOD%% of %%C_DONE%% forms the letter of the font is nearer to the middle than most of the scribe's own instances. This audit found two faults that could not be seen before, because they lie inside the letter, not on its edge: in medial ha' a patch of flaked ink had been taken for the eye of the letter, and in final mim the narrow eye had been filled. Both are corrected in version 4.1. A warning: an instance is found because it looks like the letter of the font, so the scribe's true variation is larger than these figures.]]</p>
<div class="cen">
  <figure><img loading="lazy" alt="هـ ی ناوەڕاست" data-alt-en="medial ha'" src="data:image/jpeg;base64,%%C_HEH%%"><figcaption>[[«هـ»ی ناوەڕاست||medial ha']]</figcaption></figure>
  <figure><img loading="lazy" alt="م ی کۆتایی" data-alt-en="final mim" src="data:image/jpeg;base64,%%C_MEEM%%"><figcaption>[[«م»ی کۆتایی||final mim]]</figcaption></figure>
  <figure><img loading="lazy" alt="و ی تەنها" data-alt-en="isolated waw" src="data:image/jpeg;base64,%%C_WAW%%"><figcaption>[[«و»ی تەنها||isolated waw]]</figcaption></figure>
  <figure><img loading="lazy" alt="ک ی سەرەتا" data-alt-en="initial kaf" src="data:image/jpeg;base64,%%C_KAF%%"><figcaption>[[«ک»ی سەرەتا||initial kaf]]</figcaption></figure>
</div>
<p class="legend">[[پیتی ناوەندی چوار شێوە: خۆڵەمێشی پیشان دەدات چەند لە نموونەکان لە هەر خاڵێکدا مەرەکەبیان هەیە (ڕەش = هەموویان)؛ هێڵی سوور لێواری پیتی فۆنتەکەیە. شین: مەرەکەبێک کە زۆربەی نموونەکان هەیانە و فۆنتەکە نییەتی؛ پرتەقاڵی: مەرەکەبی فۆنتەکە کە کەم نموونە هەیانە.||The middle letter of four forms: the grey shows how many of the instances have ink at each point (black = all of them); the red line is the outline of the font's letter. Blue: ink that most instances have and the font lacks; orange: ink of the font that few instances have.]]</p>
<p class="note">[[خاڵەکان: نووسەرەکە خاڵ وەک هێڵێکی بچووکی لار دەنووسێت. %%D_N%% خاڵی دەستنووسەکە پێوران (درێژی %%D_LEN%%، ئەستووری %%D_THICK%%، لاری %%D_ANGLE%%)؛ خاڵی فۆنتەکە هێڵکاریی ئەو خاڵەیە کە لە هەموویان نزیکترە لە ناوەند، و دووریی خاڵەکان لە یەکتر (%%D_STACK%%) و لە پیتەکەیان (%%D_GAP%%) هەمان دووریی پێوراوە. هەمزە، بزوێنەکان، ژمارەکان، نیشانەکانی خاڵبەندی و نیشانە کوردییەکان (ڤ ی سەر ڵ ڕ ۆ ێ، هێڵی دووەمی گ) لە دەستنووسەکەدا نین و بە هەمان ئەستووری کێشراون.||Dots: the scribe writes a dot as a short slanted dash. %%D_N%% dashes of the manuscript were measured (length %%D_LEN%%, thickness %%D_THICK%%, slant %%D_ANGLE%%); the dot of the font is the traced outline of the dash nearest to the middle of them all, and the dashes stand as far from each other (%%D_STACK%%) and from their letter (%%D_GAP%%) as was measured. Hamza, vowel marks, digits, punctuation and the Kurdish marks (the small v of ڵ ڕ ۆ ێ and the second stroke of گ) do not occur in the manuscript and are drawn at the same weight.]]</p>
</section>

<h2>Madinah Naqsh — [[نەخشی بەردی الأحزاب ٧٠–٧١||the rock inscription of al-Ahzab 70–71]]</h2>
<section class="card">
  <figure class="ms">
    <img loading="lazy" alt="نەخشی بەردی ئایەتەکانی ٧٠ و ٧١ی سورەتی الأحزاب" data-alt-en="Rock inscription of verses 70 and 71 of Sura al-Ahzab" src="data:image/jpeg;base64,%%MN_PHOTO%%">
    <figcaption>[[نەخشێکی بەرد لە دەوری مەدینە: ||A rock inscription near Medina: ]]<span dir="rtl">«بسم الله الرحمن الرحیم / یایها الذین امنوا اتقوا الله وقولوا / قولا سدیدا یصلح لکم اعملکم / ویغفر لکم ذنوبکم ومن یطع الله / ورسوله فقد فاز فوزا عظیما»</span>. [[دۆزینەوە، وێنەگرتن و خوێندنەوەی نەخشەکە: محمد المغذوی، ئەکاونتی «نوادر الآثار والنقوش»||Found, photographed and read by Muhammad al-Maghdhawi, of the account «نوادر الآثار والنقوش»]] (<a href="https://x.com/mohammed93athar" target="_blank" rel="noopener" dir="ltr">@mohammed93athar</a>) — <a href="https://x.com/mohammed93athar/status/1322206509770694656" target="_blank" rel="noopener">[[پۆستەکە||the post]]</a>. [[وێنەکە بۆ بەکارهێنانی خۆتە؛ بڵاوکردنەوەی پێویستی بە ڕەزامەندیی ئەوە.||The photograph is for your own use; publishing it needs his permission.]]</figcaption>
  </figure>
</section>
<p class="note">[[<b>ئەمە فۆنتێکی سەرەتاییە (وەشانی ٠٫٢).</b> وێنەکە تەنها ١٠٢٤×٦٧٣ پیکسڵە: ئەلفێک تێیدا ٤٠ تا ٧٠ پیکسڵ بەرزە و هێڵێکی ئاسۆیی ٤ تا ٦ پیکسڵ پانە. لێواری پیتەکان لە وێنەکەدا زۆربەی تەڵخیی وێنەکەیە، بۆیە فۆنتەکە لێوار هێڵکاری ناکات. لە جیاتی ئەوە دوو شت لە وێنەکەوە وەردەگرێت کە تەڵخی نایانگۆڕێت: هێڵی ناوەڕاستی هەر هێڵێک و ئەستوورییەکەی، و هێڵەکە بە لێواری پاک دەکێشێتەوە. هێڵە ئاسۆییەکان هەموو یەک ئەستوورین؛ ئەلف، لام و ددانەکان یەک و نیو تا دوو هێندە پانن، وەک لە بەردەکەدا. تەنها سێ دێڕی خوارەوە بەکارهاتوون.||<b>This is a draft font (version 0.2).</b> The photograph is only 1024×673 pixels: an alif is 40 to 70 pixels tall in it and a level stroke 4 to 6 wide. The edge of a letter in the photograph is mostly the blur of the photograph, so the font does not trace edges. It takes from the photograph two things that blur does not move, the centre line of every stroke and its width, and draws the stroke again with a clean edge. Level strokes all have one width; the stems of alif and lam and the teeth are one and a half times to twice as wide, as on the stone. Only the three lower lines are used.]]</p>
<p class="note">[[وێنەکە بە لاری گیراوە: دێڕەکانی سەرەوە دوورترن و پەستێوراون. بۆیە پیتەکانی دێڕی چوارەم بە ٠٫٨٤ و دێڕی سێیەم بە ٠٫٧٧ تەسک کراونەتەوە. ئەم دوو ژمارەیە لە یاسایەکەوە هاتوون (ڕوویەکی تەخت کە بە لاری دەبینرێت) و تا ١٠٪ هەڵەیان دەشێت. دێڕی خوارەوە خۆیشی بە لاری بینراوە بە بڕێک کە لە یەک وێنەوە نازانرێت؛ لەوانەیە هەموو پیتەکان ١٠ تا ٣٥٪ پانتر بن لەوەی لەسەر بەردەکەن.||The photograph looks along the rock: the upper lines are further away and foreshortened. The letters of the fourth line are therefore narrowed by 0.84 and those of the third by 0.77. Those two figures come from a rule (a flat face seen at a slant) and may be off by up to a tenth. The lowest line is itself seen at a slant, by an amount one photograph cannot give; all letters may be 10 to 35% wider than on the stone.]]</p>
%%MN_LINES%%
<div class="stats">
  <div class="stat"><b>%%MN_N%%</b><span>[[شێوەی پیت لە نەخشەکە هێڵکاری کراون||letter forms traced from the inscription]]</span></div>
  <div class="stat"><b>[[٣٤||34]]</b><span>[[شێوە لە پارچەکان دروستکراون||forms assembled from pieces]]</span></div>
  <div class="stat"><b>%%MN_EDGE%%</b><span>[[تێکڕای دووریی هێڵی ناوەڕاستی فۆنت لە ڕووناکترین هێڵی هەڵکۆڵینەکە، بە پیکسڵی وێنەکە||mean distance of the font's centre line from the brightest line of the carving, in pixels of the photograph]]</span></div>
  <div class="stat"><b>%%MN_P95%%</b><span>[[٩٥٪ی هێڵی ناوەڕاست لەمە نزیکترە||95% of the centre line is closer than this]]</span></div>
</div>
<p class="legend">[[هەمان سێ وێنەی سەرەوە: پیتەکە لە نەخشەکەدا، لێواری هەڵکۆڵینەکە لە نیوەی ڕووناکیدا (شینی کاڵ) و لێواری فۆنتەکە (سوور) لەسەری، و جیاوازییەکە (شین: هەڵکۆڵینێک کە فۆنتەکە نییەتی؛ سوور: فۆنت لە شوێنێک کە هەڵکۆڵین نییە). لێواری فۆنتەکە بە تێکڕا %%MN_EDGE2%% لە لێواری وێنەکە دوورە و کەمێک باریکترە. ئەمە بە مەبەستە: لێواری وێنەکە تەڵخییەکەشی تێدایە و هێڵە نزیکەکان پێکەوە دەلکێنێت، فۆنتەکە جیایان دەکاتەوە.||The same three pictures as above: the letter in the inscription, the edge of the carving at half brightness (light blue) and the edge of the font (red) over it, and the difference (blue: carving the font lacks; red: font where there is no carving). The edge of the font lies %%MN_EDGE2%% from the edge in the photograph on average, and is a little thinner. That is on purpose: the edge in the photograph includes the blur and runs close strokes together, which the font keeps apart.]]</p>
<div class="grid">
%%MN_CELLS%%
</div>
<section class="card">
<p class="note">[[ئەم شێوانە لە نەخشەکەدا نین و لە پارچە هێڵکاریکراوەکان دروستکراون:||These forms are not in the inscription and were assembled from traced pieces:]]</p>
<ul class="plain">%%MN_DERIVED%%</ul>
<p class="note">[[نەخشەکە خاڵ و بزوێنی نییە. خاڵەکان (بازنەیی)، هەمزە، بزوێنەکان، ژمارەکان، خاڵبەندی و نیشانە کوردییەکان بە قەڵەمێکی بازنەیی بە ئەستووریی هێڵێکی ئاسۆیی کێشراون.||The inscription has no dots or vowel marks. Dots (round), hamza, vowel marks, digits, punctuation and the Kurdish marks are drawn with a round pen as wide as a level stroke.]]</p>
</section>

<h2>[[شێوەکانی پیتەکان||Letter forms]] — Birmingham Hijazi</h2>
<section class="card forms-wrap">
<table class="forms" dir="rtl">
<thead><tr><th>[[سەرەتا||Initial]]</th><th>[[ناوەڕاست||Medial]]</th><th>[[کۆتایی||Final]]</th><th>[[تەنها||Isolated]]</th></tr></thead>
<tbody>
%%FORMS%%
</tbody>
</table>
</section>

<h2>[[سەرچاوە||Source]]</h2>
<section class="card">
  <figure class="ms">
    <img alt="هەردوو پەڕەی دەستنووسی قورئانی بیرمینگهام" data-alt-en="Both leaves of the Birmingham Qur'an manuscript" loading="lazy" src="data:image/jpeg;base64,%%MS_FULL%%">
    <figcaption>[[دەستنووسی قورئانی بیرمینگهام (Mingana Islamic Arabic 1572a)، کتێبخانەی توێژینەوەی کادبەری، زانکۆی بیرمینگهام. لای چەپ: پەڕەی ٢ ڕوو (مریم ٩١ – طه ١٣)؛ لای ڕاست: پەڕەی ١ پشت (الکهف ٢٣–٣١). وێنەکە Public Domain ە (Wikimedia Commons). تەمەنی پێست: ٥٦٨–٦٤٥ ز.||The Birmingham Qur'an manuscript (Mingana Islamic Arabic 1572a), Cadbury Research Library, University of Birmingham. Left: folio 2r (Maryam 91 – Ta-Ha 13); right: folio 1v (al-Kahf 23–31). The photograph is in the public domain (Wikimedia Commons). The parchment is dated 568–645 CE.]]</figcaption>
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
function setLang(l){
  const h = document.documentElement;
  h.lang = l; h.dir = l === 'en' ? 'ltr' : 'rtl';
  document.title = l === 'en' ? h.dataset.titleEn : h.dataset.titleCkb;
  if (!txt.dataset.labelCkb) txt.dataset.labelCkb = txt.getAttribute('aria-label');
  txt.setAttribute('aria-label', l === 'en' ? txt.dataset.labelEn : txt.dataset.labelCkb);
  document.querySelectorAll('img[data-alt-en]').forEach(i => {
    if (!i.dataset.altCkb) i.dataset.altCkb = i.alt;
    i.alt = l === 'en' ? i.dataset.altEn : i.dataset.altCkb;
  });
  try { localStorage.setItem('fontsLang', l); } catch (e) {}
  fitLines();
}
document.getElementById('lang').addEventListener('click', () => {
  setLang(document.documentElement.lang === 'en' ? 'ckb' : 'en');
});
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
setLang(document.documentElement.lang);
setSize(); render(); feats(); fitLines();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
