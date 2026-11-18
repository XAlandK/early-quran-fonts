# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""The photographs the letters are taken from, and their scale.

The Birmingham manuscript (Mingana Islamic Arabic 1572a) is two leaves of a
Qur'an of which sixteen more leaves are in Paris (Bibliotheque nationale de
France, Arabe 328, folios 71-86, "Arabe 328(c)").  Only two of the four
Birmingham pages have been published in a photograph large enough to trace
from; the Paris leaves, written in the same hand, are used for the letter
forms that do not occur on those two pages, and to compare many more
instances of every letter.

page key   photograph                               scale
  L        manuscript/full.jpg  (folio 2 recto)      1
  R        manuscript/full.jpg  (folio 1 verso)      1
  P071r .. P086v   manuscript/bnf/071r.jpg ...       BNF_SCALE

Every page is brought to the scale of the Birmingham photograph, so that one
pixel is the same length of parchment everywhere (the "plain" scale):
  * the Birmingham leaves measure 343 x 258 mm (Cadbury Research Library) and
    are 4005 x 3050 px in the photograph: 11.75 px per mm;
  * the Paris photographs are 400 dpi, 15.748 px per mm (which makes the leaf
    of folio 71 346 mm high, the height of the Birmingham leaves).
A page on which the scribe wrote smaller is enlarged further, see MODULE below.
The Paris pictures are not kept in the repository; fetch_bnf.py downloads them.
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BHAM_PX_MM = 11.75
BNF_PX_MM = 400 / 25.4
BNF_SCALE = BHAM_PX_MM / BNF_PX_MM          # 0.746
BNF_FOLIOS = ['%03d%s' % (f, s) for f in range(71, 87) for s in 'rv']

# The scribe did not write every leaf at the same size.  module.py lays Birmingham letters
# over a whole page at a range of sizes and finds the size at which they fit best: the
# size of the writing of that page, as a fraction of that of the Birmingham pages (which
# come out as 1.00 and 0.98; the numbers are its figure for all letters together).  A
# page that is listed here is enlarged by 1 / this number, so that a letter taken from it
# has the size and the weight of the Birmingham letters.  variation.py checks the result
# against the traced letters: after the enlargement the letters of these three pages are
# 0.98 - 1.01 of the Birmingham ones in height and 0.84 - 0.97 in the thickness of their
# strokes.  Folios 78 and 79 are not enlarged: module.py finds their writing a little
# smaller too (0.85 - 0.93), but their pen is as heavy as on the Birmingham pages
# (strokes 1.09 - 1.13), so enlarging them would make their letters too bold.
MODULE = {
    'P071r': 0.89,
    'P075r': 0.83,
    'P077r': 0.85,
}


def module(key):
    """Size of the writing on a page, as a fraction of that of the Birmingham pages."""
    return MODULE.get(key, 1.0)


def source(key, plain=False):
    """(path of the photograph, scale it is brought to) of a page key.  plain: the scale at
    which one pixel is the same length of parchment as in the Birmingham photograph,
    without the enlargement of a page that is written smaller."""
    if key in ('L', 'R'):
        return os.path.join(HERE, 'manuscript', 'full.jpg'), 1.0
    if key.startswith('P') and key[1:] in BNF_FOLIOS:
        return os.path.join(HERE, 'manuscript', 'bnf', key[1:] + '.jpg'), BNF_SCALE / (1.0 if plain else module(key))
    raise KeyError(key)


_CACHE = {}


def load(key, plain=False):
    """The photograph of a page as an RGB array."""
    path, scale = source(key, plain)
    if (path, scale) not in _CACHE:
        if not os.path.exists(path):
            raise FileNotFoundError('%s is missing; run fetch_bnf.py to download the Paris leaves' % path)
        im = Image.open(path).convert('RGB')
        if scale != 1.0:
            im = im.resize((int(round(im.width * scale)), int(round(im.height * scale))), Image.LANCZOS)
        if len(_CACHE) > 3:                  # the pictures are large: keep only a few
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[(path, scale)] = np.asarray(im)
    return _CACHE[(path, scale)]
