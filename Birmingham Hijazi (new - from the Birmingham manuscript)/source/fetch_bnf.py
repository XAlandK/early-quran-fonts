#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Download the Paris leaves of the manuscript.

Sixteen leaves of the Qur'an that the two Birmingham leaves come from are in
the Bibliotheque nationale de France: Arabe 328, folios 71-86 ("Arabe 328(c)",
Q 10:35 - 11:110 and 20:99 - 23:27).  The library publishes photographs of
them on Gallica; this script fetches the 32 pages at full size (400 dpi, about
93 MB) into manuscript/bnf/, where pages.py looks for them.

The pictures are not part of this repository.  Source: gallica.bnf.fr /
Bibliotheque nationale de France, ark:/12148/btv1b8415207g.  The library
allows them to be reused freely for non-commercial purposes if the source is
named; a commercial use needs its licence.

Usage:  python fetch_bnf.py
"""
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ARK = 'ark:/12148/btv1b8415207g'
FIRST_VIEW = 149                      # view number of folio 71 recto in the digitised volume
URL = 'https://openapi.bnf.fr/iiif/image/v3/%s/f%d/full/max/0/default.jpg'


def main():
    out = os.path.join(HERE, 'manuscript', 'bnf')
    os.makedirs(out, exist_ok=True)
    view = FIRST_VIEW
    for folio in range(71, 87):
        for side in 'rv':
            path = os.path.join(out, '%03d%s.jpg' % (folio, side))
            if not (os.path.exists(path) and os.path.getsize(path) > 500000):
                req = urllib.request.Request(URL % (ARK, view), headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                if data[:2] != b'\xff\xd8':
                    sys.exit('folio %d%s: the answer is not a picture' % (folio, side))
                open(path, 'wb').write(data)
                print('folio %d%s  %.1f MB' % (folio, side, len(data) / 1e6))
                time.sleep(1)
            view += 1


if __name__ == '__main__':
    main()
