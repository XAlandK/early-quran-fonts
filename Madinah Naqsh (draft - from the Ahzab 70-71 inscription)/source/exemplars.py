# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""Where each letter form was taken from in the inscription (Qur'an 33:70-71).

page   'N', the page made by prep.py: line 1 is the fifth (lowest, largest) line of the
       inscription, line 2 the fourth, line 3 the third.
items  (form, x_right, x_left[, options]) in pixels of that page.  On a side that joins,
       x is the column where the word is cut; on a free side it is only a hint.
       A '#' after the form marks an alternative exemplar, traced for comparison only.
thr    grey level that separates carving from rock for a group (default tracer.THR).

Options of an item.  Places are given as (x, rows below the baseline) on the page, areas as
(x left, row top, x right, row bottom).
  erase, fill, drop, also, exact, dyb, below   as in the tracer of the manuscript font:
                 ink taken away before / after the letter is cut out, ink that belongs to
                 it although it does not touch, where its baseline lies
  part     an area taken out of the crest: ink of a neighbouring letter or a scratch of
           the rock that the blur has run into the letter
  bridge   an area in which the crest takes in all of the letter at the half-way grey: a
           faint stroke that the crest alone would lose
  paint    an area that is made crest: a stroke that damage of the rock has interrupted
  ring     a wide place that is to be read as a head (the line runs round it)
  noring   a wide place that is not a head (the line runs through it)
  twig     side twigs shorter than this many half-widths of the crest are dropped
           (default 1.3; lower to keep a short tooth, higher to drop a stray twig)
  ycut     {'r' or 'l': row}: the row of the joining stroke at a cut that lies in a thick place
  slit     gaps narrower than twice this are filled (default 2.5 px): what the photograph
           cannot show
"""
GROUPS = [
    # ورسوله فقد
    {'id': 'N5a', 'page': 'N', 'line': 1, 'items': [
        ('WAW.isol#', 2005, 1915), ('REH.isol', 1795, 1700),
        ('SEEN.init', 1630, 1532, {'twig': 0.5}), ('WAW.fina', 1532, 1440),
        ('LAM.init', 1415, 1382), ('HEH.fina', 1382, 1305),
        ('FEH.init', 1295, 1229), ('QAF.medi', 1229, 1168), ('DAL.fina', 1168, 1075)]},
    # فاز
    {'id': 'N5c', 'page': 'N', 'line': 1, 'thr': 185, 'items': [
        ('FEH.init#', 1048, 996), ('ALIF.fina', 996, 955, {'drop': [(930, 17, 1000, 90)], 'part': [(983, -78, 997, -7)], 'twig': 2.5}), ('REH.isol#', 940, 872)]},
    # فوزا
    {'id': 'N5d', 'page': 'N', 'line': 1, 'thr': 170, 'items': [
        ('FEH.init#', 860, 806), ('WAW.fina#', 806, 715), ('ALIF.isol#', 632, 585)]},
    # عظيما
    {'id': 'N5b', 'page': 'N', 'line': 1, 'zoom': 2.4, 'items': [
        ('AIN.init', 505, 415, {'noring': [(444, -5)], 'bridge': [(440, -48, 458, -32)]}), ('TAH.medi', 415, 246, {'also': [(330, -24), (262, -22), (272, -55), (285, -85)], 'erase': [(241, -90, 249, -3)], 'drop': [(290, 17, 370, 70)],
                                 'paint': [(348, -27, 369, -14), (247, -16, 256, 6)], 'part': [(296, -14, 314, 2)], 'noring': [(290, 2)]}),
        ('BEH.medi#', 246, 217), ('MEEM.medi#', 217, 177, {'drop': [(170, 14, 222, 90)]}),
        ('ALIF.fina#', 177, 120)]},
    # ويغفر لكم
    {'id': 'N4a', 'page': 'N', 'line': 2, 'items': [
        ('WAW.isol', 2855, 2765, {'ring': [(2815, 22)], 'part': [(2840, 27, 2870, 55)]}),
        ('BEH.init', 2735, 2683, {'twig': 2.6}), ('AIN.medi', 2683, 2577), ('FEH.medi', 2577, 2495), ('REH.fina', 2495, 2415),
        ('LAM.init#', 2405, 2349), ('MEEM.fina', 2062, 1985)]},
    # ذنوبكم
    {'id': 'N4b', 'page': 'N', 'line': 2, 'items': [
        ('DAL.isol', 1965, 1835, {'bridge': [(1850, -66, 1872, -24)], 'twig': 2.0}),
        ('BEH.init#', 1778, 1745), ('WAW.fina#', 1745, 1680),
        ('BEH.init#', 1675, 1637), ('KAF.medi#', 1637, 1448), ('MEEM.fina#', 1448, 1385)]},
    # ومن يطع
    {'id': 'N4c', 'page': 'N', 'line': 2, 'items': [
        ('WAW.isol#', 1365, 1285), ('MEEM.init', 1258, 1203, {'drop': [(1203, 15, 1275, 95)], 'noring': [(1244, -8)]}), ('NOON.fina', 1203, 1040, {'ycut': {'r': 5}, 'part': [(1192, 52, 1208, 78)]}),
        ('BEH.init#', 1065, 1020), ('TAH.medi#', 1020, 720, {'also': [(880, -20), (790, -90)], 'dyb': 10}), ('AIN.fina', 720, 640, {'dyb': 10, 'below': 170, 'noring': [(661, 85), (698, -8)], 'part': [(615, 48, 646, 86)]})]},
    # قولا سديدا
    {'id': 'N3a', 'page': 'N', 'line': 3, 'items': [
        ('QAF.init', 3333, 3163, {'noring': [(3226, 6)], 'slit': 7}), ('WAW.fina#', 3163, 3085),
        ('LAMALEF.isol', 3025, 2925),
        ('SEEN.init#', 2895, 2685), ('DAL.fina#', 2685, 2530),
        ('BEH.init#', 2502, 2452), ('DAL.fina#', 2452, 2350),
        ('ALIF.isol', 2325, 2265)]},
    # يصلح لكم
    {'id': 'N3b', 'page': 'N', 'line': 3, 'items': [
        ('BEH.init#', 2105, 2063), ('SAD.medi', 2063, 1827), ('LAM.medi', 1827, 1765, {'exact': 0, 'drop': [(1770, 14, 1860, 110)], 'part': [(1753, 18, 1792, 60)], 'ycut': {'l': 6}}),
        ('HAH.fina', 1765, 1575, {'exact': 0, 'ycut': {'r': 6}}),
        ('LAM.init#', 1600, 1500), ('KAF.medi', 1500, 1284, {'drop': [(1400, 22, 1480, 90)], 'part': [(1489, -47, 1501, -21)], 'twig': 2.0}), ('MEEM.fina#', 1284, 1195)]},
]
