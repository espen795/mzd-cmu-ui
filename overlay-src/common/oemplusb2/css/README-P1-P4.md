# P1–P4 bestandsposities (OEMPLUS-B2 submenu's, BOUWPLAN.md) — LEES DIT VÓÓR JE SCHRIJFT

P0 (deze map, `B2Sub-00-base.css` + `../images/B2SubBg|B2StatusBarBg|B2IcnSbHome|B2BtnBack_*|B2BtnFldrUp_*`) is de
enige die JS raakt (`src/OemplusInject.js`): body-klasse `OemplusB2`, CSS-lader in vaste volgorde, bewaker die de
klasse weghaalt op protected schermen.

Elke P1–P4-agent schrijft ALLEEN in zijn eigen bestanden hieronder (geen overlap, BOUWPLAN "Eigenaarschap"):

| pakket | CSS-bestand (DEZE map) | generator (`ui-oemplus-inject-v1.3/tools/assets/`) | PNG-prefixen (`../images/`) |
|---|---|---|---|
| P1 List2 | `B2Sub-10-list2.css` | `p1_list2.py` | `B2List*`, `B2TitleBg`, `B2Caret*`, `B2Check_*`, `B2Radio_*`, `B2Tick`, `B2Toggle_*`, `B2Slider*`, `B2Plus`, `B2Minus`, `B2Scroll*` |
| P2 Dialog3 | `B2Sub-20-dialog3.css` | `p2_dialog3.py` | `B2Dialog*`, `B2DlgBtn*`, `B2Indeterminate_*`, `B2Progress*`, `B2Pin*` |
| P3 Tabs/Slider/Button | `B2Sub-30-tabs-slider-button.css` | `p3_tabs.py` | `B2Tab*`, `B2Btn150*`, `B2TabArrow_*` (hergebruikt P1 `B2Slider*` alleen-lezen) |
| P4 media & invoer | `B2Sub-40-media-input.css` | `p4_media.py` | `B2ArtFrame`, `B2Ump*`, `B2DialKey_*`, `B2Key*` |

## Afspraken

- **Laadvolgorde is vast**: de P0-lader laadt `B2Sub-00-base.css`, dan `B2Sub-10-list2.css`, `B2Sub-20-dialog3.css`,
  `B2Sub-30-tabs-slider-button.css`, `B2Sub-40-media-input.css` — een ontbrekend bestand wordt overgeslagen zonder
  fout, dus elk pakket kan los landen. Selector-volgorde = tie-breaker; herhaal NOoit een selector van een ander
  pakket (harnascheck H8).
- **Prefix**: elke selector begint met `body.OemplusB2 ` (specificiteit +0,1,1 wint van lazy OEM-CSS ongeacht
  laadvolgorde). Zonder de body-klasse matcht niets (uit = OEM, harnas H6).
- **Alleen skin**: color/font/background-image/opacity/border-color op decoratieve delen; NOOIT left/top/width/height
  van hitbox-elementen (H1: getBoundingClientRect gelijk met B2 aan/uit).
- **Presto 2.12 / ASCII-only**, marker `OEMPLUS-B2` in elk bestand; valideer met `python3 ../tools/check_presto.py`
  (aangepast voor v1.3) — geen gradients/flex/grid/calc/box-shadow, transitions alleen `-o-`.
- **Startpunt**: prototype in `ui-mockup-v1.0/submenus/css/B2Sub-NN-*.css` + `tools/make_assets.py`; generator splitst
  in `_lib.py` (staat al in `tools/assets/`) + `pN_*.py`. Afwijkingen van DESIGN-SYSTEEM motiveren in `NOTITIE-PN.md`.
- **PNG's**: genereer met je eigen `pN_*.py` naar `../images/` met je eigen prefix; P0's PNG's niet overschrijven.
- **Harnas**: breid `harness/run_submenus.py` (nieuwe file, gebaseerd op `harness/run_inject.py`) uit met H1–H10
  uit BOUWPLAN voor jouw schermen; alle checks PASS + `check_presto.py` OK vóór commit. Commit alleen je eigen bestanden.
