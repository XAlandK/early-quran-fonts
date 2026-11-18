# Third-party notices

This repository contains, or is built from, material by other people. Each item
below keeps its own license or status. None of it is covered by the license of
this project.

## Fonts redistributed unchanged

| Font | Folder | Copyright | License | Source |
|---|---|---|---|---|
| Raqq 2.000 | `Kufic (later style - not Birmingham)/Raqq/` | © 2021–2023 The Raqq Project Authors | GNU AGPL v3 (`LICENSE` in the folder) | https://github.com/aliftype/raqq (release v2.00) |
| Qashib 2.000 | `Kufic (later style - not Birmingham)/Qashib/` | © 2025 The Qashib Project Authors | GNU AGPL v3 (`LICENSE` in the folder) | https://github.com/aliftype/qashib (release v2.00) |
| Qahiri 4.000 | `Kufic (later style - not Birmingham)/Qahiri/` | © 2021 The Qahiri Project Authors | SIL Open Font License 1.1 (`OFL.txt` in the folder) | https://github.com/aliftype/qahiri (release v4.00) |
| hijazi 1.00 | `Hijazi - general (Khalid Alabdullah, 2019)/` | © 2019 Khalid Alabdullah | Creative Commons Attribution-NonCommercial 4.0 International, https://creativecommons.org/licenses/by-nc/4.0/ | https://github.com/khalidalabdullah/hijazifont |

The font files are copied from the release archives or repositories named above
and have not been modified.

**Corresponding source for the AGPL fonts.** Raqq and Qashib are distributed here
as compiled `.ttf` files only. Their complete corresponding source is available at
no charge from the repositories above, at the tags `v2.00`.

## Photographs of the Birmingham Qur'an manuscript

The files in `Birmingham Hijazi (new - from the Birmingham manuscript)/source/manuscript/`,
and the crops of them in that folder's `source/audit/` (the letters from
folios 2 recto and 1 verso) and in
`docs/images/birmingham-hijazi-vs-manuscript.jpg` and
`docs/images/birmingham-hijazi-audit.jpg`, are photographs of the
Birmingham Qur'an manuscript (Cadbury Research Library, University of Birmingham,
Mingana Islamic Arabic 1572a). They were downloaded from Wikimedia Commons, where
they are marked as public domain:
https://commons.wikimedia.org/wiki/Category:Birmingham_Quran_manuscript

The manuscript itself, a 7th-century text, is in the public domain.

## Photographs of the Paris leaves of the same manuscript

Sixteen more leaves of the Qur'an that the two Birmingham leaves come from are
in the Bibliothèque nationale de France (Département des Manuscrits, Arabe 328,
folios 71–86). Nine letter forms of Birmingham Hijazi that do not occur on the
two large Birmingham pages are traced from the library's photographs of these
leaves, and other letters on them were traced for comparison.

Source: gallica.bnf.fr / Bibliothèque nationale de France,
https://gallica.bnf.fr/ark:/12148/btv1b8415207g

The photographs themselves are **not** included in this repository;
`source/fetch_bnf.py` downloads them from the library. What the repository
contains is the outlines traced from them (`traced.json`), the baselines of
their lines (`lines.json`), and small crops of single letters in the audit
pictures (`source/audit/` and `docs/images/birmingham-hijazi-paris-forms.jpg`).

The library allows non-commercial reuse of these photographs free of charge,
provided the source is named as above; commercial reuse of the photographs
needs a licence from the library (see "Conditions d'utilisation des contenus de
Gallica" on gallica.bnf.fr). The manuscript itself is in the public domain.

## Photograph of the rock inscription used for Madinah Naqsh

Madinah Naqsh is traced from a photograph of a rock inscription near Medina
(Qur'an 33:70-71). The inscription was found, photographed and read by
Muhammad al-Maghdhawi (@mohammed93athar on X, account "Nawadir al-Athar
wa-l-Nuqush"): https://x.com/mohammed93athar/status/1322206509770694656

The photograph, and every file that reproduces it, is **not** included in this
repository. The repository contains only the outlines traced from it
(`traced.json`), the measurements of its lines (`lines.json`) and the font built
from them.
