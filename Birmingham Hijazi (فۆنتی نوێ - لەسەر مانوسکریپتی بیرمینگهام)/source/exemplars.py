# -*- coding: utf-8 -*-
"""Where each letter form was taken from in the manuscript.

page   L = folio 2 recto (Q 19:91 - 20:13), R = folio 1 verso (Q 18:23-31), as they
       sit side by side in the Cadbury Research Library photograph.
line   index into lines.json (fitted baselines).
items  (form, x_right, x_left[, options]) in pixels of the photograph.  On a side
       that joins, x is where the word is cut (snapped to the plainest column
       nearby); on a free side it is only a hint.
       A '#' after the form marks an alternative exemplar that is traced for
       comparison but not used in the font.
"""
GROUPS = [
    # عليك القران لتشقى
    {'id': 'L12a', 'page': 'L', 'line': 12, 'items': [
        ('AIN.init', 2900, 2745), ('LAM.medi', 2745, 2692, {'hole': 300}), ('BEH.medi', 2692, 2650, {'hole': 300}), ('KAF.fina', 2650, 2445, {'hole': 300}),
        ('LAM.init#', 2370, 2300), ('QAF.medi#', 2300, 2230), ('REH.fina#', 2230, 2165),
        ('ALIF.isol#', 2165, 2100),
        ('LAM.init#', 2005, 1935), ('BEH.medi#', 1935, 1905), ('SEEN.medi#', 1905, 1820),
        ('QAF.medi#', 1820, 1755), ('YEH.fina#', 1755, 1695)]},
    # الا تذكره لمن يخشى
    {'id': 'L12b', 'page': 'L', 'line': 12, 'items': [
        ('ALIF.isol#', 1575, 1515), ('LAMALEF.isol', 1505, 1405),
        ('BEH.init', 1340, 1285), ('DAL.fina', 1285, 1150),
        ('KAF.init', 1125, 952), ('REH.fina', 952, 890), ('HEH.isol', 865, 800, {'hole': 400}),
        ('LAM.init#', 780, 718), ('MEEM.medi#', 718, 648), ('NOON.fina#', 648, 600),
        ('BEH.init#', 610, 575), ('HAH.medi', 575, 490), ('SEEN.medi', 490, 385), ('YEH.fina#', 385, 315)]},
    # تنزيلا ممن خلق الارض
    {'id': 'L13a', 'page': 'L', 'line': 13, 'items': [
        ('BEH.init#', 2640, 2597), ('LAMALEF.fina', 2597, 2500),
        ('MEEM.init', 2465, 2390), ('MEEM.medi', 2390, 2320), ('NOON.fina#', 2320, 2180),
        ('HAH.init#', 2245, 2145), ('LAM.medi#', 2145, 2080), ('QAF.fina#', 2080, 1890),
        ('LAMALEF.isol#', 1855, 1755)]},
    # والسموت العلى
    {'id': 'L13b', 'page': 'L', 'line': 13, 'items': [
        ('WAW.isol', 1445, 1340), ('ALIF.isol', 1330, 1280),
        ('LAM.init#', 1255, 1185), ('SEEN.medi#', 1185, 1070), ('MEEM.medi#', 1070, 995), ('WAW.fina', 995, 900),
        ('BEH.isol', 905, 685),
        ('ALIF.isol#', 690, 630), ('LAM.init#', 605, 545), ('AIN.medi#', 545, 495), ('LAM.medi#', 495, 430),
        ('YEH.fina#', 430, 340)]},
    # الرحمن على العرش
    {'id': 'L14a', 'page': 'L', 'line': 14, 'items': [
        ('LAM.init#', 2795, 2735), ('REH.fina#', 2735, 2685),
        ('HAH.init#', 2655, 2490), ('MEEM.medi#', 2490, 2435), ('NOON.fina#', 2435, 2190),
        ('AIN.init#', 2385, 2280), ('LAM.medi#', 2280, 2185), ('YEH.fina#', 2185, 2100),
        ('ALIF.isol#', 2105, 2050), ('LAM.init#', 2015, 1945), ('AIN.medi', 1945, 1890), ('REH.fina#', 1890, 1825),
        ('SEEN.isol', 1805, 1640)]},
    # استوى له ما فى السمو
    {'id': 'L14b', 'page': 'L', 'line': 14, 'items': [
        ('ALIF.isol#', 1680, 1600), ('SEEN.init#', 1525, 1425), ('BEH.medi#', 1425, 1395), ('WAW.fina#', 1395, 1330),
        ('YEH.isol#', 1330, 1235),
        ('LAM.init', 1085, 1028), ('HEH.fina#', 1028, 965),
        ('MEEM.init#', 935, 870), ('ALIF.fina#', 870, 800),
        ('FEH.init#', 785, 720), ('YEH.fina#', 720, 625),
        ('ALIF.isol#', 615, 560), ('LAM.init#', 545, 490), ('SEEN.medi#', 490, 385)]},
    # ت وما فى الارض
    {'id': 'L15a', 'page': 'L', 'line': 15, 'items': [
        ('BEH.isol#', 2875, 2685), ('WAW.isol#', 2645, 2545), ('MEEM.init#', 2535, 2460), ('ALIF.fina#', 2460, 2400),
        ('FEH.init#', 2345, 2280), ('YEH.fina#', 2280, 2200),
        ('ALIF.isol#', 2195, 2105), ('LAMALEF.isol#', 2085, 1985), ('REH.isol#', 1945, 1885), ('SAD.isol', 1865, 1690, {'nosplit': 1, 'erase': [(1624, 12, 1692, 81), (1603, 99, 1681, 130)]})]},
    # وما بينهما وما تحت
    {'id': 'L15b', 'page': 'L', 'line': 15, 'items': [
        ('WAW.isol#', 1675, 1575), ('MEEM.init#', 1550, 1485), ('ALIF.fina#', 1485, 1420),
        ('BEH.init#', 1375, 1325), ('BEH.medi#', 1325, 1280), ('BEH.medi#', 1280, 1235), ('HEH.medi#', 1235, 1150),
        ('MEEM.medi#', 1150, 1060), ('ALIF.fina#', 1060, 1000),
        ('WAW.isol#', 965, 870), ('MEEM.init#', 860, 785), ('ALIF.fina#', 785, 720),
        ('BEH.init#', 705, 650), ('HAH.medi#', 650, 550), ('BEH.fina', 550, 355)]},
    # الثرى وان تجهر
    {'id': 'L16a', 'page': 'L', 'line': 16, 'items': [
        ('ALIF.isol#', 2895, 2815), ('LAM.init#', 2770, 2690), ('BEH.medi#', 2690, 2645), ('REH.fina#', 2645, 2590),
        ('YEH.isol#', 2590, 2475),
        ('WAW.isol#', 2385, 2295), ('ALIF.isol#', 2295, 2225), ('NOON.isol', 2182, 2120, {'nosplit': 1, 'hole': 300, 'erase_poly': [
            # a stem of the line below runs up against the nun and crosses its bend; the two are
            # parted along the pale seam between them
            [(2182, 3), (2214, 3), (2214, 48), (2168.5, 48), (2169.5, 26), (2176, 14)],
            [(2168.5, 48), (2214, 48), (2214, 125), (2147.5, 125), (2147.5, 67), (2155, 64.5),
             (2163, 60.5), (2167.5, 55)]]}),
        ('BEH.init#', 2105, 2060), ('HAH.medi#', 2060, 1925), ('HEH.medi#', 1925, 1840), ('REH.fina#', 1840, 1760)]},
    # بالقول فانه يعلم السر
    {'id': 'L16b', 'page': 'L', 'line': 16, 'items': [
        ('BEH.init#', 1725, 1685), ('ALIF.fina#', 1685, 1615),
        ('LAM.init#', 1585, 1518), ('QAF.medi#', 1518, 1455), ('WAW.fina#', 1455, 1360),
        ('LAM.isol', 1385, 1245, {'hole': 300}),
        ('FEH.init#', 1195, 1120), ('ALIF.fina#', 1120, 1045),
        ('BEH.init#', 1015, 975), ('HEH.fina#', 975, 905),
        ('BEH.init#', 885, 855), ('AIN.medi#', 855, 780), ('LAM.medi#', 780, 700), ('MEEM.fina', 700, 605),
        ('ALIF.isol#', 605, 545), ('LAM.init#', 520, 478), ('SEEN.medi#', 478, 392), ('REH.fina#', 392, 300)]},
    # واخفى الله لا اله
    {'id': 'L17a', 'page': 'L', 'line': 17, 'items': [
        ('WAW.isol#', 2885, 2795), ('ALIF.isol#', 2805, 2715),
        ('HAH.init#', 2650, 2550), ('FEH.medi', 2550, 2485), ('YEH.fina', 2485, 2420),
        ('ALIF.isol#', 2365, 2285), ('LAM.init#', 2265, 2170), ('LAM.medi#', 2170, 2110), ('HEH.fina#', 2110, 2035),
        ('LAMALEF.isol#', 2015, 1925),
        ('ALIF.isol#', 1895, 1825), ('LAM.init#', 1800, 1722), ('HEH.fina#', 1722, 1648)]},
    # الا هو له الاسما ا
    {'id': 'L17b', 'page': 'L', 'line': 17, 'items': [
        ('ALIF.isol#', 1615, 1535), ('LAMALEF.isol#', 1515, 1405),
        ('HEH.init', 1345, 1280), ('WAW.fina#', 1280, 1210),
        ('LAM.init#', 1185, 1100), ('HEH.fina', 1100, 1020, {'hole': 40}),
        ('ALIF.isol#', 1005, 930), ('LAMALEF.isol#', 895, 805),
        ('SEEN.init', 735, 620, {'hole': 200}), ('MEEM.medi#', 620, 530), ('ALIF.fina#', 530, 475),
        ('ALIF.isol#', 455, 385)]},
    # وهل اتيك
    {'id': 'L18a', 'page': 'L', 'line': 18, 'items': [
        ('WAW.isol#', 2505, 2415), ('HEH.init#', 2385, 2295), ('LAM.fina#', 2295, 2185),
        ('ALIF.isol#', 2165, 2075),
        ('BEH.init#', 2035, 2000), ('BEH.medi#', 2000, 1965), ('KAF.fina#', 1965, 1715)]},
    # حديث موسى اذ
    {'id': 'L18b', 'page': 'L', 'line': 18, 'items': [
        ('HAH.init', 1665, 1480), ('DAL.fina#', 1480, 1365),
        ('BEH.init#', 1335, 1300), ('BEH.fina#', 1300, 1075),
        ('MEEM.init#', 1045, 970), ('WAW.fina#', 970, 880),
        ('SEEN.init#', 845, 740), ('YEH.fina#', 740, 670),
        ('ALIF.isol#', 595, 525), ('DAL.isol', 485, 370)]},
    # را نارا فقل لاهله
    {'id': 'L19a', 'page': 'L', 'line': 19, 'items': [
        ('REH.isol#', 2905, 2825), ('ALIF.isol#', 2815, 2745),
        ('BEH.init#', 2690, 2640), ('ALIF.fina#', 2640, 2595),
        ('REH.isol', 2565, 2485), ('ALIF.isol#', 2485, 2405),
        ('FEH.init#', 2365, 2290), ('QAF.medi#', 2290, 2220), ('LAM.fina#', 2220, 2095),
        ('LAMALEF.isol#', 2105, 2005),
        ('HEH.init#', 1945, 1880), ('LAM.medi#', 1880, 1795), ('HEH.fina#', 1795, 1715)]},
    # امكثوا انى انست نا
    {'id': 'L19b', 'page': 'L', 'line': 19, 'items': [
        ('ALIF.isol#', 1685, 1615), ('MEEM.init#', 1575, 1505), ('KAF.medi', 1505, 1340, {'hole': 300, 'smooth': 0.9}), ('BEH.medi#', 1340, 1305),
        ('WAW.fina#', 1305, 1215), ('ALIF.isol#', 1225, 1155),
        ('ALIF.isol#', 1125, 1055), ('BEH.init#', 1005, 975), ('YEH.fina#', 975, 895),
        ('BEH.init#', 775, 730), ('SEEN.medi#', 730, 600), ('BEH.fina#', 600, 455),
        ('BEH.init#', 435, 400), ('ALIF.fina#', 400, 335)]},
    # را لعلى اتيكم منها
    {'id': 'L20a', 'page': 'L', 'line': 20, 'items': [
        ('REH.isol#', 2895, 2815), ('ALIF.isol#', 2795, 2705),
        ('LAM.init#', 2665, 2595), ('AIN.medi#', 2595, 2535), ('LAM.medi#', 2535, 2480), ('YEH.fina#', 2480, 2400),
        ('ALIF.isol#', 2395, 2315),
        ('BEH.init#', 2245, 2215), ('BEH.medi#', 2215, 2190), ('KAF.medi#', 2190, 2005), ('MEEM.fina#', 2005, 1925),
        ('MEEM.init#', 1885, 1820), ('BEH.medi#', 1820, 1765), ('HEH.medi#', 1765, 1695), ('ALIF.fina#', 1695, 1615)]},
    # بقبس او اجد على ا
    {'id': 'L20b', 'page': 'L', 'line': 20, 'items': [
        ('BEH.init#', 1555, 1515), ('QAF.medi', 1515, 1440), ('BEH.medi#', 1440, 1405), ('SEEN.fina', 1405, 1175),
        ('ALIF.isol#', 1265, 1195), ('WAW.isol#', 1175, 1085), ('ALIF.isol#', 1085, 995),
        ('HAH.init#', 985, 825), ('DAL.fina#', 825, 715),
        ('AIN.init#', 725, 545), ('LAM.medi#', 545, 495), ('YEH.fina#', 495, 410),
        ('ALIF.isol#', 425, 335)]},
    # لنار هدى فلما ا
    {'id': 'L21a', 'page': 'L', 'line': 21, 'items': [
        ('LAM.init#', 2925, 2855), ('BEH.medi#', 2855, 2815), ('ALIF.fina#', 2815, 2755),
        ('REH.isol#', 2695, 2615),
        ('HEH.init#', 2535, 2460), ('DAL.fina#', 2460, 2335), ('YEH.isol#', 2285, 2215),
        ('FEH.init', 2065, 1990), ('LAM.medi#', 1990, 1935), ('MEEM.medi#', 1935, 1870), ('ALIF.fina', 1870, 1820, {'hole': 300, 'fill': [(1848, -32, 1856, -19)]}),
        ('ALIF.isol#', 1775, 1695)]},
    # تيها نودى يموسى
    {'id': 'L21b', 'page': 'L', 'line': 21, 'items': [
        ('BEH.init#', 1660, 1618), ('BEH.medi#', 1618, 1580), ('HEH.medi', 1580, 1495, {'hole': 80}), ('ALIF.fina#', 1495, 1420),
        ('BEH.init#', 1325, 1292), ('WAW.fina#', 1292, 1205), ('DAL.isol#', 1175, 1065), ('YEH.isol', 1045, 965),
        ('BEH.init#', 860, 820), ('MEEM.medi#', 820, 750), ('WAW.fina#', 750, 655),
        ('SEEN.init#', 605, 500), ('YEH.fina#', 500, 455)]},
    # انى انا ربك فا
    {'id': 'L22a', 'page': 'L', 'line': 22, 'items': [
        ('ALIF.isol#', 2945, 2875), ('BEH.init#', 2795, 2770), ('YEH.fina#', 2770, 2715),
        ('ALIF.isol#', 2625, 2555), ('BEH.init#', 2505, 2465), ('ALIF.fina#', 2465, 2395),
        ('REH.isol#', 2325, 2255),
        ('BEH.init#', 2205, 2165), ('KAF.fina#', 2165, 1980),
        ('FEH.init#', 1915, 1850), ('ALIF.fina#', 1850, 1765)]},
    # خلع نعليك انك با
    {'id': 'L22b', 'page': 'L', 'line': 22, 'items': [
        ('HAH.init#', 1755, 1570), ('LAM.medi#', 1570, 1525), ('AIN.fina', 1525, 1440, {'hole': 40}),
        ('BEH.init#', 1385, 1345), ('AIN.medi#', 1345, 1280), ('LAM.medi#', 1280, 1205), ('BEH.medi#', 1205, 1165),
        ('KAF.fina#', 1165, 965),
        ('ALIF.isol#', 935, 865), ('BEH.init#', 810, 770), ('KAF.fina#', 770, 575),
        ('BEH.init#', 535, 495), ('ALIF.fina#', 495, 405)]},
    # لواد المقدس
    {'id': 'L23a', 'page': 'L', 'line': 23, 'items': [
        ('LAM.init#', 2905, 2845), ('WAW.fina#', 2845, 2755),
        ('ALIF.isol#', 2655, 2575), ('DAL.isol#', 2545, 2425), ('ALIF.isol#', 2385, 2295),
        ('LAM.init#', 2285, 2210), ('MEEM.medi#', 2210, 2140), ('QAF.medi#', 2140, 2070),
        ('SEEN.isol#', 1925, 1715)]},
    # طوى وانا اخترتك
    {'id': 'L23b', 'page': 'L', 'line': 23, 'items': [
        ('TAH.init', 1765, 1565), ('WAW.fina#', 1565, 1455), ('YEH.isol#', 1415, 1350),
        ('WAW.isol#', 1225, 1130), ('ALIF.isol#', 1145, 1065),
        ('BEH.init#', 1030, 995), ('ALIF.fina#', 995, 925), ('ALIF.isol#', 905, 805),
        ('HAH.init#', 805, 660), ('BEH.medi#', 660, 625), ('REH.fina#', 625, 570)]},
    # --- folio 1 verso (the right-hand page of the photograph) and the upper lines of folio 2 recto ---
    # واصبر
    {'id': 'R10a', 'page': 'R', 'line': 10, 'items': [
        ('WAW.isol#', 5395, 5315), ('ALIF.isol#', 5305, 5215),
        ('SAD.init', 5175, 5050), ('BEH.medi#', 5050, 5015), ('REH.fina#', 5015, 4930)]},
    # مع الذين
    {'id': 'R10b', 'page': 'R', 'line': 10, 'items': [
        ('MEEM.init#', 4395, 4322), ('AIN.fina#', 4322, 4260),
        ('BEH.init#', 3900, 3870), ('NOON.fina', 3870, 3735)]},
    # ولا تطع
    {'id': 'R13a', 'page': 'R', 'line': 13, 'items': [
        ('WAW.isol#', 5255, 5175), ('LAMALEF.isol#', 5155, 5055),
        ('BEH.init#', 4985, 4943), ('TAH.medi', 4943, 4820, {'hole': 50}), ('AIN.fina#', 4820, 4735)]},
    # قلبه عن
    {'id': 'R13b', 'page': 'R', 'line': 13, 'items': [
        ('QAF.init', 4085, 4020), ('LAM.medi#', 4020, 3965),
        ('AIN.init#', 3805, 3680), ('NOON.fina#', 3680, 3525)]},
    # امره فرطا وقل
    {'id': 'R14b', 'page': 'R', 'line': 14, 'items': [
        ('HEH.isol#', 4305, 4235), ('FEH.init#', 4175, 4120), ('REH.fina#', 4120, 4025),
        ('TAH.init', 4015, 3857), ('ALIF.fina#', 3857, 3805),
        ('WAW.isol#', 3705, 3635), ('QAF.init#', 3585, 3530), ('LAM.fina', 3530, 3395)]},
    # للظلمين
    {'id': 'R16a', 'page': 'R', 'line': 16, 'items': [
        ('LAM.init#', 5045, 5000), ('LAM.medi#', 5000, 4925), ('TAH.medi#', 4925, 4795), ('LAM.medi#', 4795, 4740)]},
    # احاط
    {'id': 'R16b', 'page': 'R', 'line': 16, 'items': [
        ('ALIF.isol#', 4165, 4095), ('TAH.isol', 3845, 3675, {'hole': 150})]},
    # يشرك
    {'id': 'R07b', 'page': 'R', 'line': 7, 'items': [
        ('KAF.isol', 4215, 4015), ('FEH.init#', 3985, 3915)]},
    # ربكم
    {'id': 'R15a', 'page': 'R', 'line': 15, 'items': [
        ('REH.isol#', 5445, 5385), ('BEH.init#', 5325, 5295), ('KAF.medi#', 5295, 5135), ('MEEM.fina#', 5135, 5055),
        ('QAF.fina#', 5700, 5575)]},
    # من ... من
    {'id': 'L08a', 'page': 'L', 'line': 8, 'thr': 150, 'items': [
        ('MEEM.init#', 1965, 1885), ('NOON.fina#', 1885, 1750)]},
    {'id': 'L08b', 'page': 'L', 'line': 8, 'thr': 150, 'items': [
        ('MEEM.init#', 815, 770), ('NOON.fina#', 770, 630)]},
    # الصلحت
    {'id': 'L05b', 'page': 'L', 'line': 5, 'thr': 150, 'items': [
        ('LAM.init#', 575, 515), ('SAD.medi', 515, 405), ('LAM.medi#', 405, 360)]},
    # ابصر ... الارض
    {'id': 'R06b', 'page': 'R', 'line': 6, 'items': [
        ('SAD.isol#', 4815, 4660), ('BEH.init#', 4495, 4450), ('SAD.medi', 4450, 4325, {'hole': 100}), ('REH.fina#', 4325, 4245)]},
    # خلق : the tail of the qaf is crossed by a stem of the line below, which is cut away by hand
    {'id': 'L13q', 'page': 'L', 'line': 13, 'thr': 158, 'zoom': 2.2, 'items': [
        ('QAF.fina', 2083, 1900, {'exact': 1, 'nosplit': 1, 'hole': 200, 'drop': [(2079, -75, 2100, -10)],
                                      'erase': [(1968, 14, 2024, 57), (1950, 71, 2024, 140)]})]},
]
