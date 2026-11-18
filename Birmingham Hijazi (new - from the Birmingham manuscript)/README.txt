Birmingham Hijazi — v3.000
==========================

کوردی
-----
فۆنتێکی حیجازییە کە پیتەکانی ڕاستەوخۆ لە مەرەکەبی دەستنووسی قورئانی
بیرمینگهام (Mingana Islamic Arabic 1572a) هێڵکاری کراون. تەمەنی پێستی
دەستنووسەکە بە کاربۆنی ڕادیۆیی ٥٦٨–٦٤٥ ی زایینییە.

وەشانەکان:
  v1  بە دەست کێشرابوو (لە فۆڵدەری «Previous version (v1 - hand-drawn)» دایە).
  v2  یەکەم هێڵکاری لە وێنەکەوە (لە فۆڵدەری «Previous version (v2 - first tracing)» دایە).
  v3  دوای پشکنینی پیکسڵ بە پیکسڵ. ئەمانە چاک کران:
      - لێواری مەرەکەب بە یەک ئاستی ڕەنگ بۆ هەموو پەڕەکە دیاری دەکرا، بۆیە
        هێڵە کاڵەکان نزیکەی نیو پیکسڵ لە هەر لایەک باریکتر دەردەچوون. ئێستا
        بۆ هەر شوێنێک نیوەی نێوان ڕەنگی مەرەکەبی ئەو هێڵە و پێستەکە وەردەگیرێت.
      - نەرمکردنی لێوارەکان نووک و گۆشەکانی کورت دەکردەوە. ئێستا قەرەبوو
        دەکرێتەوە و لێوارەکە لەسەر سێ‌یەکی پیکسڵ دەدۆزرێتەوە.
      - هێڵەکان بە لارکردنەوە (shear) ڕاست دەکرانەوە؛ ئێستا بە سووڕاندن، تا
        گۆشە و دوورییەکانی ناو پیتەکە وەک وێنەکە بمێننەوە.
      - کەوانەکانی فۆنتەکە (TrueType) چەماوەکانیان کەمێک کورت دەبڕی؛ ئێستا
        قەرەبوو کراوەتەوە.
      - «ق»ی کۆتایی و «ن»ی تەنها لەگەڵ پیتی هێڵی خوارەوە تێکەڵ بووبوون؛
        بە دەست لە درزە کاڵەکەی نێوانیاندا جیا کرانەوە.
      - ئەستووریی هێڵی پەیوەستبوون لە ١٥ەوە کرا بە ١٦ پیکسڵ (ناوەندی پێوراو).

پشکنینەکە (source/audit.py):
  هەر پیتێک لە فایلی فۆنتەکەوە وێنە دەکرێت و لەسەر هەمان پیتی دەستنووسەکە
  دادەنرێت. لێواری مەرەکەب سەربەخۆ لە وێنەکە دەردەهێنرێت و دووریی نێوان
  هەردوو لێوارەکە بە پیکسڵی وێنەکە دەپێورێت. ئەنجام بۆ ٥٣ شێوەکە:
      تێکڕای دووریی لێوارەکان   ٠٫١٥ پیکسڵ   (v2: ٠٫٦٨)
      ٩٥٪ی لێوارەکان لەمە نزیکترن ٠٫٤١ پیکسڵ   (v2: ١٫٧٥)
      جیاوازیی ڕووبەر             ٠٫٥٪        (v2: ٤٫٦٪ باریکتر)
  وێنە و ژمارەی هەر پیتێک لە source/audit/ دایە و لە پەڕەی پیشاندانیشدا.
  تێبینی: شوێنی پەیوەستبوونی پیتەکان لە پێوانەکە دەرکراوە، چونکە لەوێ
  ئەستووریی هێڵەکە بە مەبەست یەکسان کراوە تا هەموو پیتەکان بە یەکەوە بلکێن.

چی لە دەستنووسەکەوە هاتووە:
  - ٥٣ شێوەی پیت (تەنها / سەرەتا / ناوەڕاست / کۆتایی)، لە پەڕەی ٢ ڕوو
    (مریم ٩١ – طه ١٣) و پەڕەی ١ پشت (الکهف ٢٣–٣١).
    شوێنی هەر نموونەیەک لە source/exemplars.py نووسراوە.
  - ئەستووری، لاری، درێژیی هێڵی بنەڕەت.
  - خاڵەکان وەک دەستنووسەکە هێڵی بچووکی لارن، لەسەر یەک دانراون.

چی دەقاودەقی دەستنووسەکە نییە:
  - نۆ شێوە لەو دوو پەڕەیەدا نەهاتوون و لە پارچە بڕدراوەکان دروستکراون:
    م (تەنها)، ق (تەنها)، ع (تەنها)، ص و ط (کۆتایی)، ف (کۆتایی و تەنها)،
    ج ح خ (کۆتایی و تەنها — بە پێی وشەی «تخرج» لە پەڕەی ٢ پشت).
  - هەمزە، بزوێنەکان، ژمارەکان، خاڵبەندی، و نیشانە کوردییەکان
    (ڤ ی سەر ڵ ڕ ۆ ێ، هێڵی دووەمی گ) بە هەمان ئەستووری کێشراون.
  - ئەو شوێنانەی مەرەکەبەکە وەریوە پڕ کراونەتەوە (درز و خاڵە سپییەکانی ناو
    هێڵەکان). لە پێنج پیتدا ئەمە بە دەست دیاری کراوە (لە exemplars.py).
  - لە یازدە شێوەدا پیتەکە لە دەستنووسەکەدا ڕاستەوخۆ بە پیتی تەنیشتییەوە
    لکاوە؛ لەوێ ملێکی ٤ پیکسڵی زیاد کراوە تا بگاتە ئەستووریی هێڵی بەستن.
  - بۆشایی: نووسەرەکە بۆشایی نێوان وشەکان و بۆشایی دوای پیتە نەبەستراوەکان
    جیا ناکاتەوە (ناوەندی هەردووکیان نزیکەی ٤٧ پیکسڵە). فۆنتەکە بۆ ئاسانیی
    خوێندنەوە ٣٦ پیکسڵ دەدات لە ناو وشە و ٦٨ لە نێوان وشەکان؛ تێکڕاکەی
    وەک دەستنووسەکەیە، بەڵام دابەشبوونەکەی نا.

بەکارهێنان:
  ss01 : تەنها ڕەسم — هەموو خاڵ و هەمزەکان لادەبات (وەک دەستنووسەکە).
  ss02 : بزوێنەکان (فەتحە، کەسرە، ...) دەشارێتەوە.
  بۆ نموونە لە CSS:  font-feature-settings: "ss01", "ss02";
  بۆ ئەوەی دەق بە قەبارەی دەستنووسەکە دەربکەوێت: ١ em = ٢٢٥ پیکسڵی وێنەکە.

English
-------
A Hijazi typeface whose letterforms are traced from the ink of the Birmingham
Qur'an manuscript (Cadbury Research Library, University of Birmingham, Mingana
Islamic Arabic 1572a; parchment radiocarbon-dated 568–645 CE).

v1 was drawn by hand; v2 was the first tracing; v3 follows a pixel audit of v2.
What the audit found and v3 corrects: the ink edge was taken at one grey level
for the whole page, which made pale strokes about half a pixel thin on each
side (now half-way between the ink of each stroke and the parchment, located to
a third of a pixel); outline smoothing pulled tips and corners in (now
compensated); lines were levelled by shear (now by a rigid turn); the TrueType
curves cut bends short (now compensated); final qaf and isolated nun were fused
with a letter of the line below (now parted along the pale seam); the joining
stroke is 16 px, the measured median, instead of 15.

Audit (source/audit.py): every glyph is rendered from the .ttf and laid over
its exemplar; the ink edge is extracted from the photograph independently.
Over the 53 traced forms: mean edge distance 0.15 px of the photograph (v2:
0.68), 95 % of the outline within 0.41 px (v2: 1.75), area within 0.5 % (v2:
4.6 % thin).  The joins are left out of the measurement, because there the
stroke is deliberately brought to one thickness so that all letters connect.

Not from the manuscript: nine forms that do not occur on the two leaves and are
assembled from traced pieces (isolated mim, qaf, 'ayn; final sad, ta'; final
and isolated fa' and jim/ha'/kha'); hamza, vowel marks, digits, punctuation
and the Kurdish diacritics; flaked ink is filled in; where a letter is fused
with its neighbour a 4 px neck is added.  The scribe leaves about the same gap
between words as after an unjoined letter (median 47 px); the font gives 36 px
inside a word and 68 px between words, for legibility.

  ss01  rasm only (no dots / hamzas), as in the manuscript
  ss02  hide vowel marks

Files
-----
  BirminghamHijazi-Regular.ttf   the font
  source/manuscript/full.jpg     the photograph the letters are traced from
                                 (Cadbury Research Library; public domain,
                                 Wikimedia Commons)
  source/lines.json              fitted baseline of every line of the two pages
  source/exemplars.py            where each letter form was taken from
  source/tracer.py               cuts the exemplars out and writes traced.json
  source/traced.json             the traced outlines, in font units
  source/build.py                builds the font from traced.json
  source/audit.py                lays the built font over the manuscript and measures
  source/audit/                  its pictures (one per form) and audit.json
  source/compare_sheet.py        side-by-side sheets of exemplar and outline
  source/make_readme_figures.py  draws the figures in ../docs/images/ shown in the
                                 README at the root of the repository
  source/make_preview.py         rebuilds ../پیشاندانی-فۆنتەکان.html, the Kurdish/English
                                 preview page of all the fonts (needs the Madinah
                                 photographs, which are not in the public repository)

Rebuild:  pip install fonttools shapely numpy pillow scipy scikit-image freetype-py
          cd source
          python tracer.py manuscript/full.jpg lines.json traced.json - - _dump
          python build.py ../BirminghamHijazi-Regular.ttf
          python audit.py ../BirminghamHijazi-Regular.ttf _dump audit
          python make_preview.py
          (the _dump folder is only needed by audit.py and can be deleted)

License
-------
Copyright (c) 2026 Aland Kawa Ali

The font and its source are licensed under the Aland Attribution &
Non-Commercial License (AANCL) v1.0; see the LICENSE file at the root of the
repository. Attribution is mandatory: credit Aland Kawa Ali, keep the copyright
notice and license intact, and mark any changes. Commercial use requires prior
written permission from the copyright holder.

The license covers the font and the code, not the manuscript. The letterforms
of the 7th-century manuscript, and the photographs of it in source/manuscript/
(Wikimedia Commons), are in the public domain; see THIRD_PARTY_NOTICES.md.

مۆڵەت: فۆنتەکە و سەرچاوەکەی لە ژێر مۆڵەتی AANCL v1.0 دان (فایلی LICENSE لە
ڕەگی ڕیپۆکەدا)، مافی لەبەرگرتنەوە بۆ Aland Kawa Ali. ناوهێنانی خاوەنەکەی
پێویستە؛ بەکارهێنانی تیجاری ڕەزامەندیی نووسراوی پێشوەختەی دەوێت. دەستنووسەکە
خۆی و وێنەکانی Public Domain ن و ئەم مۆڵەتە نایانگرێتەوە.
