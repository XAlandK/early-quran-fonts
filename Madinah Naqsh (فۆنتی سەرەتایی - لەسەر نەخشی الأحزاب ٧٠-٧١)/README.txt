Madinah Naqsh — draft 0.100
===========================

کوردی
-----
فۆنتێکی سەرەتاییە کە لە نەخشێکی بەردی دەوری مەدینە هێڵکاری کراوە. نەخشەکە
ئایەتەکانی ٧٠ و ٧١ی سورەتی الأحزابە:

    بسم الله الرحمن الرحيم
    يايها الذين امنوا اتقوا الله وقولوا
    قولا سديدا يصلح لكم اعملكم
    ويغفر لكم ذنوبكم ومن يطع الله
    ورسوله فقد فاز فوزا عظيما

وێنەکە هی محمد المغذوی یە (ئەکاونتی «نوادر الآثار والنقوش»، ‎@mohammed93athar
لە X، پۆستی ٣٠ی تشرینی یەکەمی ٢٠٢٠):
    https://x.com/mohammed93athar/status/1322206509770694656
ئەو نەخشەکەی دۆزیوەتەوە، وێنەی گرتووە و خوێندوویەتییەوە. بۆ بەکارهێنانی خۆتە؛ بڵاوکردنەوەی وێنەکە
پێویستی بە ڕەزامەندیی ئەوە.

بۆچی «سەرەتایی»:
  - وێنەکە تەنها ١٠٢٤×٦٧٣ پیکسڵە و لێڵە. پیتەکان تێیدا ٣٠ تا ٧٠ پیکسڵ بەرزن
    (لە وێنەی دەستنووسی بیرمینگهامدا ١٥٠ بوون، بە لێواری ڕوون). فۆنتەکە شێوەی
    گشتیی هەڵکۆڵینەکە دەگرێت، نەک وردەکاریی لێوارەکانی.
  - وێنەکە لە گۆشەیەکەوە گیراوە: هێڵەکانی خوارەوە گەورەترن لە سەرەوە. هەر
    هێڵێک ڕاست کراوەتەوە و گەورە کراوە تا «ا»ی هەموویان نزیکەی یەک بەرزی بێت
    (هێڵی ٥: ×٢٫١، هێڵی ٤: ×٢٫٩٥، هێڵی ٣: ×٣٫٥). ئەمە خەمڵاندنە، نەک پێوانە.
  - تەنها سێ هێڵی خوارەوە بەکارهاتوون. دوو هێڵی سەرەوە زۆر بچووکن.
  - لێوارەکان بە نزیکەی یەک پیکسڵی وێنەکە نەرم کراون، چونکە لەوە وردتر لە
    وێنەکەدا نییە. لە پیتەکانی هێڵی سێیەمدا ٢٫٥ پیکسڵ (ی پەڕە گەورەکراوەکە)
    لە هەر لایەک لابراوە، چونکە لێڵیی وێنەکە پیتە بچووکەکان ئەستوورتر دەکات.

چی لە نەخشەکەوە هاتووە (٢٨ شێوە):
    ا (تەنها، کۆتایی) · ب/ی/ن (سەرەتا) · ن (کۆتایی) · ح (کۆتایی) ·
    د (تەنها، کۆتایی) · ر (تەنها، کۆتایی) · س (سەرەتا) · ص (ناوەڕاست) ·
    ط (ناوەڕاست) · ع (سەرەتا، ناوەڕاست، کۆتایی) · ف (سەرەتا، ناوەڕاست) ·
    ق (سەرەتا، ناوەڕاست) · ک (ناوەڕاست) · ل (سەرەتا، ناوەڕاست) · لا (تەنها) ·
    م (سەرەتا، کۆتایی) · ه (کۆتایی) · و (تەنها، کۆتایی)
  شوێنی هەر نموونەیەک لە source/exemplars.py نووسراوە.

چی لە نەخشەکەدا نییە (٣٤ شێوە، لە پارچە هێڵکاریکراوەکان دروستکراون):
    ب/ت/ث/ن/ی ناوەڕاست · ب/ت/ث کۆتایی و تەنها (بە هێڵێکی تەخت) · ن تەنها ·
    ی کۆتایی و تەنها (ددان + کلکی «ن») · ج/ح/خ سەرەتا، ناوەڕاست، تەنها ·
    س/ش ناوەڕاست، کۆتایی، تەنها · ص/ض سەرەتا، کۆتایی، تەنها ·
    ط/ظ سەرەتا، کۆتایی، تەنها · ع/غ تەنها · ف کۆتایی و تەنها ·
    ق کۆتایی و تەنها · ک سەرەتا، کۆتایی، تەنها · ل کۆتایی و تەنها ·
    م ناوەڕاست و تەنها · ه سەرەتا، ناوەڕاست، تەنها · لا کۆتایی
  تێبینی: «ی»ی کۆتایی و «ب»ی کۆتایی لە نەخشەکەدا هەر نین، بۆیە شێوەکانیان
  خەمڵاندنن. نەخشەکە خاڵ و بزوێنی نییە؛ خاڵەکان (بازنەیی)، هەمزە، بزوێنەکان،
  ژمارەکان، خاڵبەندی و نیشانە کوردییەکان بە قەڵەمێکی بازنەیی کێشراون.

پشکنین (source/audit.py):
  هەر یەک لە ٢٨ شێوەکە لە فایلی فۆنتەکەوە وێنە کراوە و لەسەر هەمان پیتی
  نەخشەکە دانراوە:
      تێکڕای دووریی لێوارەکان   ٠٫٣٧ پیکسڵی وێنەکە
      ٩٥٪ی لێوارەکان لەمە نزیکترن ٠٫٨٩ پیکسڵی وێنەکە
  ئەم ژمارانە دەڵێن فۆنتەکە لەسەر وێنەکەیە؛ ناڵێن وێنەکە ورد دەیبینێت.
  یەک پیکسڵی وێنەکە نزیکەی ٢٪ی بەرزیی پیتێکە.

بەکارهێنان:
  ss01 : تەنها ڕەسم — هەموو خاڵ و هەمزەکان لادەبات (وەک نەخشەکە).
  ss02 : بزوێنەکان دەشارێتەوە.

English
-------
A draft typeface traced from a rock inscription near Medina that carries
Qur'an 33:70-71.  The inscription was found, photographed and read by
Muhammad al-Maghdhawi (@mohammed93athar on X, account "Nawadir al-Athar
wa-l-Nuqush"), who posted the photograph on 30 October 2020:
    https://x.com/mohammed93athar/status/1322206509770694656
The photograph is kept here for personal use, not for republication.

It is a draft because the photograph is small (1024 x 673) and soft: its
letters are 30 to 70 pixels tall.  The font gives the overall shape of the
carving, not the detail of its edges.  The photograph was taken at an angle,
so each line was levelled and enlarged by its own factor (2.1, 2.95, 3.5) to
bring the alifs to one height; that is an estimate.  Only the three lower
lines are used.  Outlines are smoothed by about one pixel of the photograph,
and letters from the third line are thinned by 2.5 page pixels a side to
offset the blur.

28 letter forms are traced; 34 forms the inscription does not hold are
assembled from them (final and isolated ya' and ba' do not occur in it at
all, so their shapes are guesses).  Dots, hamza, vowel marks, digits,
punctuation and the Kurdish diacritics are drawn with a round pen.

Audit: mean distance between the font's edge and the carving's edge 0.37 px
of the photograph, 95 % within 0.89 px.  This says the font sits on the
photograph; it does not make the photograph sharper.

Files
-----
  MadinahNaqsh-Regular.ttf       the font
  source/naqsh/photo.jpg         the photograph
  source/prep.py                 levels and scales the lines -> page.png, page_rgb.jpg, lines.json
  source/exemplars.py            where each letter form was taken from
  source/tracer.py               cuts the exemplars out and writes traced.json
  source/build.py                builds the font; DERIVED lists the assembled forms
  source/audit.py, audit/        lays the font over the carving and measures
  source/compare_sheet.py        side-by-side sheets of exemplar and outline

Rebuild:  pip install fonttools shapely numpy pillow scipy scikit-image freetype-py
          cd source
          python prep.py
          python tracer.py page.png lines.json traced.json - - _dump
          python build.py ../MadinahNaqsh-Regular.ttf
          python audit.py ../MadinahNaqsh-Regular.ttf _dump audit
          (the preview page is rebuilt by make_preview.py in the Birmingham Hijazi source folder)

No license has been chosen.  The letterforms of the inscription are ancient;
the photograph belongs to its photographer.
