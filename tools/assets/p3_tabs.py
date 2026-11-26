#!/usr/bin/env python3
"""p3_tabs.py -- genereert ALLEEN de P3 "Tabs / Slider / Button" B2Sub-assets (BOUWPLAN.md P3):
  B2TabsBg.png (747x70), B2TabCurrent.png / B2TabPress.png / B2TabPressCurrent.png (354x60, Style2),
  B2TabArrow_L_En/Hit.png en B2TabArrow_R_En/Hit.png (86x62, Style4 prev/next hitbox),
  B2Btn150_{En,Focus,Hit,Ds}.png (150x100, generieke ButtonCtrl).
Slider-assets (B2SliderTrack/Fill/Knob_*) zijn P1-eigendom (alleen-lezen voor P3; als ze ontbreken wordt
dezelfde bestandsnaam in de CSS gerefereerd en staat de afhankelijkheid in NOTITIE-P3.md).

Gebruik (vanaf ui-oemplus-inject-v1.3/):  python3 tools/assets/p3_tabs.py
Output: overlay-src/common/oemplusb2/images/  (op de CMU: jci/gui/common/oemplusb2/images/)
Eigenaarschap (BOUWPLAN): alleen P3 schrijft deze PNG's; P0/P1/P2/P4 gebruiken eigen prefixen.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
from _lib import OUT, SS, RED, WHITE, LIGHT, GREY, canvas, done, red_bar, hfade_line


def tabs_bg():
    """B2TabsBg.png 747x70: transparant + haarlijn onderaan (y 69, wit 14%, fade naar rechts)."""
    w, h = 747, 70
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.paste(hfade_line(w, 0, 16, int(255 * 0.14), 0.7), (0, 69))
    im.save(os.path.join(OUT, "B2TabsBg.png"), optimize=True)


def tab_current():
    """B2TabCurrent.png 354x60: actieve tab = Soul-Red horizontale streep onderaan (112x3, gecentreerd, y 54)."""
    w, h = 354, 60
    im = Image.alpha_composite(canvas(w, h), red_bar(w, h, (w - 112) // 2, 54, 112, 3, vertical=False))
    done(im, "B2TabCurrent.png", w, h)


def tab_press():
    """B2TabPress.png 354x60: ingedrukt = licht vlak (wit 18%) + B2TabPressCurrent = vlak + rode streep."""
    w, h = 354, 60
    p = canvas(w, h)
    d = ImageDraw.Draw(p)
    d.rounded_rectangle([10 * SS, 6 * SS, (w - 10) * SS - 1, (h - 4) * SS - 1], radius=10 * SS,
                        fill=(255, 255, 255, 46))
    done(p, "B2TabPress.png", w, h)
    p2 = Image.alpha_composite(p, red_bar(w, h, (w - 112) // 2, 54, 112, 3, vertical=False))
    done(p2, "B2TabPressCurrent.png", w, h)


def tab_arrow(side):
    """B2TabArrow_{L,R}_{En,Hit}.png 86x62: Style4 prev/next hitbox (86x62) met B2-lijnpijl (25x27 raster).

    En = grijze pijl; Hit = wit vlak (18%) + witte pijl + rode streep onder (focus-streep horizontaal).
    De OEM-icoon-div (ButtonCtrlIcon, 25x27 gecentreerd) wordt door CSS verborgen; de pijl zit in de PNG.
    """
    w, h = 86, 62
    cx = w // 2
    cy = h // 2
    for state in ("En", "Hit"):
        im = canvas(w, h)
        d = ImageDraw.Draw(im)
        col = GREY if state == "En" else WHITE
        lw = int(3.4 * SS)
        if side == "L":
            pts = [(cx + 7, cy - 11), (cx - 7, cy), (cx + 7, cy + 11)]
        else:
            pts = [(cx - 7, cy - 11), (cx + 7, cy), (cx - 7, cy + 11)]
        if state == "Hit":
            d.rounded_rectangle([8 * SS, 4 * SS, (w - 8) * SS - 1, (h - 4) * SS - 1], radius=8 * SS,
                                fill=(255, 255, 255, 46))
        d.line([(p[0] * SS, p[1] * SS) for p in pts], fill=col + (255,), width=lw, joint="curve")
        if state == "Hit":
            im = Image.alpha_composite(im, red_bar(w, h, (w - 34) // 2, h - 8, 34, 3, vertical=False))
        done(im, "B2TabArrow_%s_%s.png" % (side, state), w, h)


def btn150(state):
    """B2Btn150_{En,Focus,Hit,Ds}.png 150x100: generieke ButtonCtrl (hitbox = 150x100 OEM).

    En = wit 8% vlak radius 10 (inset 5,6); Focus = wit 16% + rode streep onder (60x3);
    Hit = wit 26%; Ds = wit 4% (tekst via CSS gedimd).
    """
    w, h = 150, 100
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    ix, iy = 5, 6
    box = [ix * SS, iy * SS, (w - ix) * SS - 1, (h - iy) * SS - 1]
    r = 10 * SS
    if state == "En":
        d.rounded_rectangle(box, radius=r, fill=WHITE + (20,))
    elif state == "Focus":
        d.rounded_rectangle(box, radius=r, fill=WHITE + (41,))
        im = Image.alpha_composite(im, red_bar(w, h, (w - 60) // 2, h - iy - 4, 60, 3, vertical=False))
    elif state == "Hit":
        d.rounded_rectangle(box, radius=r, fill=WHITE + (66,))
        im = Image.alpha_composite(im, red_bar(w, h, (w - 60) // 2, h - iy - 4, 60, 3, vertical=False))
    elif state == "Ds":
        d.rounded_rectangle(box, radius=r, fill=WHITE + (10,))
    done(im, "B2Btn150_%s.png" % state, w, h)


def main():
    tabs_bg()
    tab_current()
    tab_press()
    tab_arrow("L")
    tab_arrow("R")
    for st in ("En", "Focus", "Hit", "Ds"):
        btn150(st)
    print("p3_tabs ->", OUT,
          "(B2TabsBg, B2TabCurrent, B2TabPress, B2TabPressCurrent, B2TabArrow_L/R_{En,Hit}, B2Btn150_{En,Focus,Hit,Ds})")


if __name__ == "__main__":
    main()
