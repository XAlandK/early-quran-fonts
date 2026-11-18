# -*- coding: utf-8 -*-
"""Where each letter form was taken from in the inscription (Qur'an 33:70-71).

page   'N', the page made by prep.py: line 1 is the fifth (lowest, largest) line of the
       inscription, line 2 the fourth, line 3 the third.
items  (form, x_right, x_left[, options]) in pixels of that page.  On a side that joins,
       x is the column where the word is cut; on a free side it is only a hint.
       A '#' after the form marks an alternative exemplar, traced for comparison only.
opt    options for every item of a group; 'thin' takes that many pixels off each side of
       the strokes (the smaller lines of the photograph are blurred fatter).
thr    grey level that separates carving from rock for a group (default tracer.THR).
"""
GROUPS = [
    # ورسوله فقد
    {'id': 'N5a', 'page': 'N', 'line': 1, 'items': [
        ('WAW.isol#', 2005, 1915), ('REH.isol', 1795, 1700),
        ('SEEN.init', 1630, 1532), ('WAW.fina', 1532, 1440),
        ('LAM.init', 1415, 1382), ('HEH.fina', 1382, 1305),
        ('FEH.init', 1295, 1229), ('QAF.medi', 1229, 1168), ('DAL.fina', 1168, 1075)]},
    # فاز
    {'id': 'N5c', 'page': 'N', 'line': 1, 'thr': 185, 'items': [
        ('FEH.init#', 1048, 996), ('ALIF.fina', 996, 955, {'drop': [(930, 17, 1000, 90)]}), ('REH.isol#', 940, 872)]},
    # فوزا
    {'id': 'N5d', 'page': 'N', 'line': 1, 'thr': 170, 'items': [
        ('FEH.init#', 860, 806), ('WAW.fina#', 806, 715), ('ALIF.isol#', 632, 585)]},
    # عظيما
    {'id': 'N5b', 'page': 'N', 'line': 1, 'zoom': 2.4, 'items': [
        ('AIN.init', 505, 415), ('TAH.medi', 415, 246, {'also': [(330, -24), (262, -22), (272, -55), (285, -85)], 'erase': [(241, -90, 249, -3)], 'drop': [(290, 17, 370, 70)]}),
        ('BEH.medi#', 246, 217), ('MEEM.medi#', 217, 177, {'drop': [(170, 14, 222, 90)]}),
        ('ALIF.fina#', 177, 120)]},
    # ويغفر لكم
    {'id': 'N4a', 'page': 'N', 'line': 2, 'items': [
        ('WAW.isol', 2855, 2765),
        ('BEH.init', 2735, 2683), ('AIN.medi', 2683, 2577), ('FEH.medi', 2577, 2495), ('REH.fina', 2495, 2415),
        ('LAM.init#', 2405, 2349), ('MEEM.fina', 2062, 1985)]},
    # ذنوبكم
    {'id': 'N4b', 'page': 'N', 'line': 2, 'items': [
        ('DAL.isol', 1965, 1835),
        ('BEH.init#', 1778, 1745), ('WAW.fina#', 1745, 1680),
        ('BEH.init#', 1675, 1637), ('KAF.medi#', 1637, 1448), ('MEEM.fina#', 1448, 1385)]},
    # ومن يطع
    {'id': 'N4c', 'page': 'N', 'line': 2, 'items': [
        ('WAW.isol#', 1365, 1285), ('MEEM.init', 1258, 1203, {'drop': [(1203, 15, 1275, 95)]}), ('NOON.fina', 1203, 1040),
        ('BEH.init#', 1065, 1020), ('TAH.medi#', 1020, 720, {'also': [(880, -20), (790, -90)], 'dyb': 10}), ('AIN.fina', 720, 640, {'dyb': 10, 'below': 170})]},
    # قولا سديدا
    {'id': 'N3a', 'page': 'N', 'line': 3, 'opt': {'thin': 2.5}, 'items': [
        ('QAF.init', 3333, 3163), ('WAW.fina#', 3163, 3085),
        ('LAMALEF.isol', 3025, 2925),
        ('SEEN.init#', 2895, 2685), ('DAL.fina#', 2685, 2530),
        ('BEH.init#', 2502, 2452), ('DAL.fina#', 2452, 2350),
        ('ALIF.isol', 2325, 2265)]},
    # يصلح لكم
    {'id': 'N3b', 'page': 'N', 'line': 3, 'opt': {'thin': 2.5}, 'items': [
        ('BEH.init#', 2105, 2063), ('SAD.medi', 2063, 1827), ('LAM.medi', 1827, 1765, {'exact': 0, 'drop': [(1770, 14, 1860, 110)]}),
        ('HAH.fina', 1765, 1575, {'exact': 0}),
        ('LAM.init#', 1600, 1500), ('KAF.medi', 1500, 1284, {'drop': [(1400, 22, 1480, 90)]}), ('MEEM.fina#', 1284, 1195)]},
]
