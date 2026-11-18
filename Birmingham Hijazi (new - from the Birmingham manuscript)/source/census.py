#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Aland Kawa Ali
# Licensed under AANCL v1.0. See the LICENSE file.
"""
Census: every letter form of the font, looked for on every page of the manuscript.

The font takes each letter form from one exemplar.  audit.py checks the font against that
exemplar, variation.py against the other instances that were traced by hand, on a few
pages.  This script goes over the whole manuscript: the two Birmingham pages and the 32
pages of the same Qur'an in Paris (BnF Arabe 328, folios 71-86).

For every page
  * the size of its writing is measured as in module.py (Birmingham letters laid over the
    page at a range of sizes);
  * every letter form of the font (traced.json) is laid over the page at that size, and
    the places where it fits best are taken as instances of the form.  Where two forms
    claim the same place, the one that fits better keeps it;
  * each instance is cut out, brought to the size of the Birmingham writing, and compared
    with the letter of the font: how much of the two coincides, and how far their outlines
    are apart.  A place counts as an instance only if every part of the letter is there
    (same_letter below): the long tail of a final 'ayn alone fits many a slanted stroke;
  * the free-standing dashes (the dots of the letters) are measured as in dashes.py.

For every form, over all its instances
  * the instances are laid over each other: the "middle letter" of the scribe, in which
    every point says how many of the instances have ink there;
  * the font is compared with it: ink of the font where fewer than a quarter of the
    instances have ink, places where more than three quarters have ink and the font has
    none, counters (eyes) of the font that most instances do not have, and counters of
    the middle letter that the font has not;
  * every instance and the font are measured against the middle letter, which shows where
    the font stands among the scribe's own letters.

A warning that belongs with the numbers: an instance is found because it looks like the
letter of the font.  A letter the scribe wrote very differently is not found, so the
spread measured here is smaller than the true one.  The check can show that the font
differs from what the scribe usually wrote; it cannot show everything he wrote.

Usage:  python census.py <out_dir> [page keys ...]        (all 34 pages if none are named)
        python census.py <out_dir> --report               (only put the pages together again)
Needs:  numpy, pillow, scipy, scikit-image, shapely
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely import wkt
from skimage.feature import match_template

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import module as MD  # noqa: E402
import pages as PG  # noqa: E402
import tracer as T  # noqa: E402

SIZE_LETTERS = ('WAW.isol', 'LAMALEF.isol', 'MEEM.init', 'HEH.fina', 'QAF.init', 'DAL.isol')
SIZES = np.round(np.arange(0.76, 1.241, 0.04), 2)
TOP = 25            # places looked at for one form on one page
FIT = 0.45          # the least fit (normalised cross-correlation) of a place that is looked at
KEEP_IOU = 0.50     # an instance counts if this much of it and of the font's letter coincide
PAGES = ['L', 'R'] + ['P' + f for f in PG.BNF_FOLIOS]


def page_image(key):
    """The page at the plain scale of pages.py (one pixel is the same length of parchment as
    in the Birmingham photograph); for L and R the half of that photograph."""
    path, scale = PG.source(key, plain=True)
    im = Image.open(path).convert('RGB')
    if scale != 1.0:
        im = im.resize((int(round(im.width * scale)), int(round(im.height * scale))), Image.LANCZOS)
    rgb = np.asarray(im)
    if key in ('L', 'R'):
        half = rgb.shape[1] // 2
        return (rgb[:, :half], 0) if key == 'L' else (rgb[:, half:], half)
    return rgb, 0


def halve(a):
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    return a[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def best_places(r, shape, n, least):
    """The n best places in a map of fits, each at least a template apart from the others."""
    out = []
    r = r.copy()
    h, w = shape
    for _ in range(n):
        i, j = np.unravel_index(np.argmax(r), r.shape)
        if r[i, j] < least:
            break
        out.append((int(i), int(j), float(r[i, j])))
        r[max(i - h // 2, 0):i + h // 2 + 1, max(j - w // 2, 0):j + w // 2 + 1] = -1
    return out


def writing_size(dark2, traced):
    score = np.zeros((len(SIZE_LETTERS), len(SIZES)))
    for a, name in enumerate(SIZE_LETTERS):
        geom = wkt.loads(traced[name]['wkt'])
        for b, size in enumerate(SIZES):
            t = MD.template(geom, size / 2)
            r = match_template(dark2, t)
            score[a, b] = np.mean([p[2] for p in best_places(r, t.shape, 6, -1)])

    def peak(curve):
        k = int(np.argmax(curve))
        if 0 < k < len(curve) - 1:
            a, b, c = curve[k - 1:k + 2]
            k = k + 0.5 * (a - c) / (a - 2 * b + c)
        return float(np.interp(k, np.arange(len(SIZES)), SIZES))
    each = [peak(score[a]) for a in range(len(SIZE_LETTERS))]
    return peak(score.mean(axis=0)), float(np.median(each)), float(score.mean(axis=0).max())


def edges(m):
    return m & ~ndi.binary_erosion(m)


def compare(F, I):
    """How well a letter of the font (mask F) and an instance (mask I, same frame) coincide:
    (share that coincides, mean distance between their outlines in pixels)."""
    region = np.zeros(F.shape, dtype=bool)
    ys, xs = np.where(F)
    region[max(ys.min() - 7, 0):ys.max() + 8, xs.min():xs.max() + 1] = True
    region &= ndi.binary_dilation(F, structure=T.disk(7))
    I = I & region
    if I.sum() < 20:
        return 0.0, 99.0, I
    iou = (F & I).sum() / (F | I).sum()
    eF, eI = edges(F), edges(I)
    eF[:, [xs.min(), xs.max()]] = False                  # the faces where a joining stroke is cut
    eI[:, [xs.min(), xs.max()]] = False
    if not eF.any() or not eI.any():
        return float(iou), 99.0, I
    dI = ndi.distance_transform_edt(~eI)
    dF = ndi.distance_transform_edt(~eF)
    return float(iou), float((dI[eF].mean() + dF[eI].mean()) / 2), I


def dashes_of(dark, size):
    """The free-standing dashes of a page: length, thickness and slant of each (in pixels of
    the Birmingham writing), and how far the lower dash of a stacked pair is from the upper."""
    ink = dark > 0.5
    lab, n = ndi.label(ink)
    if n == 0:
        return [], []
    boxes = ndi.find_objects(lab)
    area = ndi.sum(ink, lab, np.arange(1, n + 1))
    s2 = size * size
    found = []
    for i, (s, a) in enumerate(zip(boxes, area), 1):
        h, w = s[0].stop - s[0].start, s[1].stop - s[1].start
        if not (35 * s2 <= a <= 330 * s2 and max(h, w) <= 48 * size and min(h, w) >= 5 * size):
            continue
        r0, r1 = max(s[0].start - 6, 0), min(s[0].stop + 6, ink.shape[0])
        c0, c1 = max(s[1].start - 6, 0), min(s[1].stop + 6, ink.shape[1])
        m = lab[r0:r1, c0:c1] == i
        if (lab[r0:r1, c0:c1] > 0).sum() > 1.15 * m.sum():            # something else in its box
            continue
        ys, xs = np.nonzero(m)
        c = np.cov(np.vstack([xs, -ys]))                               # y upwards
        ev, evec = np.linalg.eigh(c)
        length, thick = 4 * np.sqrt(ev[1]) / size, 4 * np.sqrt(max(ev[0], 1e-6)) / size
        if length / thick < 1.7:
            continue
        ang = np.degrees(np.arctan2(evec[1, 1], evec[0, 1]))
        ang = (ang + 90) % 180 - 90                                    # between -90 and 90
        found.append((s[1].start + xs.mean() - 6 + (c0 - s[1].start + 6), s[0].start + ys.mean() - 6 + (r0 - s[0].start + 6),
                      float(length), float(thick), float(ang)))
    stack = []
    for (x, y, *_r) in found:
        below = [(yy - y) / size for (xx, yy, *_q) in found if abs(xx - x) < 9 * size and 8 * size < yy - y < 32 * size]
        if below:
            stack.append(min(below))
    return [f[2:] for f in found], stack


def do_page(args):
    key, out_dir = args
    try:
        traced = json.load(open(os.path.join(HERE, 'traced.json'), encoding='utf-8'))
        rgb, x_off = page_image(key)
        dark = MD.darkness(rgb).astype(np.float32)
        dark2 = halve(dark)
        size, size_each, fit = writing_size(dark2, traced)
        geoms = {k: wkt.loads(v['wkt']) for k, v in traced.items() if not k.startswith('_')}
        cands = []
        for form, geom in geoms.items():
            t = MD.template(geom, size / 2)
            if t.shape[0] >= dark2.shape[0] or t.shape[1] >= dark2.shape[1]:
                continue
            r = match_template(dark2, t)
            for i, j, sc in best_places(r, t.shape, TOP, FIT):
                cands.append((sc, form, 2 * i, 2 * j, 2 * t.shape[0], 2 * t.shape[1]))
        cands.sort(reverse=True)
        kept = []
        for c in cands:                                   # where two forms claim one place, the better fit keeps it
            _, _, y, x, h, w = c
            ok = True
            for (_, _, y2, x2, h2, w2) in kept:
                iy = min(y + h, y2 + h2) - max(y, y2)
                ix = min(x + w, x2 + w2) - max(x, x2)
                if iy > 0 and ix > 0 and iy * ix > 0.6 * min(h * w, h2 * w2):
                    ok = False
                    break
            if ok:
                kept.append(c)
        rows, crops = [], {}
        for sc, form, y, x, h, w in kept:
            geom = geoms[form]
            best = None
            for s in (size * 0.94, size, size * 1.06):    # the letter itself may be a little larger or smaller
                t = MD.template(geom, s)
                a0, b0 = max(y - 10, 0), max(x - 10, 0)
                win = dark[a0:a0 + t.shape[0] + 20 + abs(t.shape[0] - h), b0:b0 + t.shape[1] + 20 + abs(t.shape[1] - w)]
                if win.shape[0] <= t.shape[0] or win.shape[1] <= t.shape[1]:
                    continue
                r = match_template(win, t)
                i, j = np.unravel_index(np.argmax(r), r.shape)
                if best is None or r[i, j] > best[0]:
                    best = (float(r[i, j]), s, a0 + int(i), b0 + int(j), t)
            if best is None:
                continue
            fit2, s, yy, xx, t = best
            crop = dark[yy:yy + t.shape[0], xx:xx + t.shape[1]]
            if crop.shape != t.shape:
                continue
            iou, dist, _ = compare(t > 0.5, crop > 0.5)
            canon = MD.template(geom, 1.0).shape          # the frame of the letter at the Birmingham size
            norm = np.asarray(Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).resize(
                (canon[1], canon[0]), Image.BILINEAR))
            rows.append({'page': key, 'form': form, 'x': int(xx + x_off), 'y': int(yy), 'size': round(float(s), 3),
                         'fit': round(fit2, 3), 'iou': round(iou, 3), 'dist': round(dist / s, 3),
                         'ink': round(float((crop > 0.5).sum() / max((t > 0.5).sum(), 1)), 3)})
            crops.setdefault(form, []).append(norm)
        dsh, stack = dashes_of(dark, size)
        np.savez_compressed(os.path.join(out_dir, 'page_%s.npz' % key),
                            **{form: np.stack(v) for form, v in crops.items()})
        res = {'page': key, 'size': round(size, 3), 'size_each': round(size_each, 3), 'size_fit': round(fit, 3),
               'rows': rows, 'dashes': [[round(v, 2) for v in d] for d in dsh], 'stack': [round(v, 2) for v in stack]}
        json.dump(res, open(os.path.join(out_dir, 'page_%s.json' % key), 'w'))
        return key, size, size_each, len(rows), sum(r['iou'] >= KEEP_IOU for r in rows), len(dsh)
    except Exception as e:                                # one page must not stop the others
        import traceback
        return key, None, None, 0, 0, traceback.format_exc()


def font_mask(geom):
    return MD.template(geom, 1.0) > 0.5


def same_letter(F, I):
    """Is the ink I (in the frame of the font's letter F) an instance of that letter?

    A long tail or stem fits many strokes that are not this letter at all, so the overall
    fit is not enough.  The frame of the letter is divided three by three; in every part
    that holds a real share of the letter (5 % of its ink) the instance must have ink over
    at least 40 % of the letter's, and nine tenths of the instance's own ink near the letter
    must lie on or beside it.  Returns (yes or no, the smallest share, the share beside)."""
    ys, xs = np.where(F)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    total = F.sum()
    low = 1.0
    for a in range(3):
        for b in range(3):
            sl = (slice(y0 + (y1 - y0) * a // 3, y0 + (y1 - y0) * (a + 1) // 3),
                  slice(x0 + (x1 - x0) * b // 3, x0 + (x1 - x0) * (b + 1) // 3))
            n = F[sl].sum()
            if n >= 0.05 * total:
                low = min(low, (F[sl] & I[sl]).sum() / n)
    region = np.zeros(F.shape, dtype=bool)
    region[max(y0 - 7, 0):y1 + 7, x0:x1] = True
    near = I & region & ndi.binary_dilation(F, structure=T.disk(12))
    beside = (near & ndi.binary_dilation(F, structure=T.disk(4))).sum() / max(near.sum(), 1)
    return bool(low >= 0.40 and beside >= 0.90), float(low), float(beside)


def report(out_dir):
    traced = json.load(open(os.path.join(HERE, 'traced.json'), encoding='utf-8'))
    pages, rows = {}, []
    for key in PAGES:
        p = os.path.join(out_dir, 'page_%s.json' % key)
        if os.path.exists(p):
            d = json.load(open(p))
            pages[key] = d
            rows += [dict(r, n=i) for i, r in enumerate(d['rows'])]
    # which crop belongs to which row: the crops of a form are stored in the order of its rows
    counter, where = {}, []
    for r in rows:
        k = (r['page'], r['form'])
        where.append(counter.get(k, 0))
        counter[k] = counter.get(k, 0) + 1
    store = {key: np.load(os.path.join(out_dir, 'page_%s.npz' % key)) for key in pages}
    os.makedirs(os.path.join(out_dir, 'forms'), exist_ok=True)
    forms = {}
    for form in sorted(k for k in traced if not k.startswith('_')):
        geom = wkt.loads(traced[form]['wkt'])
        F = font_mask(geom)
        looked = [(r, w) for r, w in zip(rows, where) if r['form'] == form and r['iou'] >= KEEP_IOU]
        sel = []
        for r, w in looked:
            ok, low, beside = same_letter(F, store[r['page']][form][w] > 127)
            r['low'], r['beside'], r['ok'] = round(low, 3), round(beside, 3), ok
            if ok:
                sel.append((r, w))
        home = traced[form]['src']['page']
        rec = {'home': home, 'looked': len(looked), 'found': len(sel), 'pages': len(set(r['page'] for r, _ in sel)),
               'birmingham': sum(r['page'] in ('L', 'R') for r, _ in sel)}
        if len(sel) >= 5:
            stack = np.stack([store[r['page']][form][w] for r, w in sel]).astype(np.float32) / 255
            mean = (stack > 0.5).mean(axis=0)             # share of the instances that have ink at each point
            # Only what lies near the letter is looked at: further off the instances show their
            # neighbours.  Nor the last pixels before a cut, where the next letter begins.
            zone = ndi.binary_dilation(F, structure=T.disk(12))
            xs = np.where(F.any(axis=0))[0]
            kind = form.split('.')[1]
            if kind in ('init', 'medi'):
                zone[:, :xs.min() + 12] = False
            if kind in ('medi', 'fina'):
                zone[:, xs.max() - 11:] = False
            mid = (mean > 0.5) & zone                     # the middle letter
            Fn = F & zone                                 # the font's letter, near itself only
            rec['only_font'] = round(float((Fn & (mean < 0.25)).sum() / F.sum()), 4)             # ink few instances have
            rec['font_lacks'] = round(float(((mean > 0.75) & ~F & zone).sum() / F.sum()), 4)     # ink most have, the font not
            eyes = ndi.binary_fill_holes(F) & ~F          # the counters of the font's letter
            rec['eye_filled'] = round(float((eyes & (mean > 0.75)).sum() / F.sum()), 4)          # a counter most instances lack
            eyes_mid = ndi.binary_fill_holes(mean > 0.5) & (mean < 0.5)                          # the counters of the middle letter
            rec['eye_missing'] = round(float((eyes_mid & F).sum() / F.sum()), 4)                 # a counter the font has not
            rec['eye_font'] = int(eyes.sum())             # area of the counters of the font's letter (px of the photograph)
            rec['eye_middle'] = int((eyes_mid & zone).sum())                                     # ... of the middle letter
            open_ = [(ndi.binary_fill_holes(s_ > 0.5) & ~(s_ > 0.5) & ndi.binary_dilation(eyes_mid | eyes, iterations=3)).any()
                     for s_ in stack] if (eyes_mid | eyes).any() else []
            rec['eye_share'] = round(float(np.mean(open_)), 3) if open_ else None                # share of instances with an eye there
            d_inst = [compare(mid, (s > 0.5) & zone)[1] for s in stack]
            for (r, w), d_ in zip(sel, d_inst):
                r['to_middle'] = round(float(d_), 3)
            d_font = compare(mid, Fn)[1]
            rec['to_middle_scribe'] = round(float(np.median(d_inst)), 3)
            rec['to_middle_font'] = round(float(d_font), 3)
            rec['rank'] = round(float(np.mean(np.array(d_inst) < d_font)), 3)   # share of instances nearer the middle
            rec['dist'] = round(float(np.median([r['dist'] for r, _ in sel])), 3)
            rec['ink'] = round(float(np.median([r['ink'] for r, _ in sel])), 3)
            # picture: the middle letter in greys, the outline of the font over it
            z = 3
            g = Image.fromarray((255 - mean * 215).astype(np.uint8)).resize((F.shape[1] * z, F.shape[0] * z), Image.BICUBIC)
            a = np.asarray(g.convert('RGB')).copy()
            Fz = np.kron(F, np.ones((z, z), dtype=bool))
            e = Fz & ~ndi.binary_erosion(Fz, iterations=2)
            a[e] = (220, 30, 30)
            lack = np.kron((mean > 0.75) & ~F & zone, np.ones((z, z), dtype=bool))
            only = np.kron(Fn & (mean < 0.25), np.ones((z, z), dtype=bool))
            a[lack & ~e] = (0, 140, 255)
            a[only & ~e] = (255, 200, 60)
            Image.fromarray(a).save(os.path.join(out_dir, 'forms', form + '.jpg'), quality=88)
        forms[form] = rec
    # the pages
    ptab = {}
    for key, d in pages.items():
        good = [r for r in rows if r['page'] == key and r.get('ok')]
        ds = np.array(d['dashes']) if d['dashes'] else np.zeros((0, 3))
        ptab[key] = {'size': d['size'], 'size_each': d['size_each'], 'instances': len(good),
                     'forms': len(set(r['form'] for r in good)),
                     'letter_size': round(float(np.median([r['size'] for r in good])), 3) if good else None,
                     'ink': round(float(np.median([r['ink'] for r in good])), 3) if good else None,
                     'dist': round(float(np.median([r['dist'] for r in good])), 3) if good else None,
                     'dashes': int(len(ds)),
                     'dash_len': round(float(np.median(ds[:, 0])), 2) if len(ds) >= 8 else None,
                     'dash_thick': round(float(np.median(ds[:, 1])), 2) if len(ds) >= 8 else None,
                     'dash_angle': round(float(np.median(ds[:, 2])), 1) if len(ds) >= 8 else None,
                     'dash_stack': round(float(np.median(d['stack'])), 2) if len(d['stack']) >= 5 else None}
    good = [r for r in rows if r.get('ok')]
    done = [f for f in forms.values() if 'rank' in f]
    json.dump([{k: v for k, v in r.items() if k != 'n'} for r in rows], open(os.path.join(out_dir, 'instances.json'), 'w'))
    summary = {'pages': len(pages), 'places_looked_at': len(rows), 'instances': len(good),
               'forms_found': sum(f['found'] >= 5 for f in forms.values()), 'forms': len(forms),
               'dist': round(float(np.median([r['dist'] for r in good])), 3) if good else None,
               'to_middle_scribe': round(float(np.median([f['to_middle_scribe'] for f in done])), 3) if done else None,
               'to_middle_font': round(float(np.median([f['to_middle_font'] for f in done])), 3) if done else None}
    json.dump({'summary': summary, 'forms': forms, 'pages': ptab}, open(os.path.join(out_dir, 'census.json'), 'w'), indent=1)
    print(summary)
    print('\n%-14s %6s %5s %5s %5s  %7s %7s %7s %7s  %7s %7s %5s  %s' % ('form', 'looked', 'found', 'pages', 'Bham', 'onlyF', 'lacks', 'eye+', 'eye-', 'scribe', 'font', 'rank', 'home'))
    for form, f in forms.items():
        if 'rank' in f:
            print('%-14s %6d %5d %5d %5d  %7.3f %7.3f %7.3f %7.3f  %7.2f %7.2f %5.2f  %s' % (
                form, f['looked'], f['found'], f['pages'], f['birmingham'], f['only_font'], f['font_lacks'], f['eye_filled'], f['eye_missing'],
                f['to_middle_scribe'], f['to_middle_font'], f['rank'], f['home']))
        else:
            print('%-14s %6d %5d %5d %5d  (too few to compare)  %s' % (form, f['looked'], f['found'], f['pages'], f['birmingham'], f['home']))
    print('\n%-6s %6s %6s %5s %5s  %6s %6s %6s   %5s %6s %6s %6s %6s' % (
        'page', 'size', 'each', 'inst', 'forms', 'lsize', 'ink', 'dist', 'dash', 'len', 'thick', 'slant', 'stack'))
    f = lambda v, n=2: ('%.' + str(n) + 'f') % v if v is not None else '-'
    for key, p in ptab.items():
        print('%-6s %6.2f %6.2f %5d %5d  %6s %6s %6s   %5d %6s %6s %6s %6s' % (
            key, p['size'], p['size_each'], p['instances'], p['forms'], f(p['letter_size']), f(p['ink']), f(p['dist']),
            p['dashes'], f(p['dash_len'], 1), f(p['dash_thick'], 1), f(p['dash_angle'], 1), f(p['dash_stack'], 1)))


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    if '--report' not in sys.argv:
        keys = [k for k in sys.argv[2:] if not k.startswith('-')] or PAGES
        with Pool(min(6, len(keys))) as pool:
            for res in pool.imap_unordered(do_page, [(k, out_dir) for k in keys]):
                if res[1] is None:
                    print('!!', res[0], res[5])
                else:
                    print('%-6s size %.2f / %.2f   %4d places, %4d instances, %4d dashes' % res, flush=True)
    report(out_dir)


if __name__ == '__main__':
    main()
