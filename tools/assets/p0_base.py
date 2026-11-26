#!/usr/bin/env python3
"""p0_base.py -- genereert ALLEEN de P0 "basis" B2Sub-assets (BOUWPLAN.md P0):
  B2SubBg.png (800x480), B2StatusBarBg.png (800x64), B2IcnSbHome.png (58x62),
  B2BtnBack_{En,Focus,Hit,Ds}.png en B2BtnFldrUp_{En,Focus,Hit,Ds}.png (94x416 hitbox, beeld erin).

Gebruik (vanaf ui-oemplus-inject-v1.3/):  python3 tools/assets/p0_base.py
Output: overlay-src/common/oemplusb2/images/  (op de CMU: jci/gui/common/oemplusb2/images/)
Eigenaarschap (BOUWPLAN): alleen P0 schrijft deze PNG's; P1-P4 gebruiken eigen prefixen.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from _lib import OUT, SS, GREY, WHITE, canvas, done, red_bar, hfade_line


def bg():
    """B2SubBg.png 800x480: radiaal donker #030405 -> #15181d (DESIGN-SYSTEEM §2 bg)."""
    w, h = 800, 480
    im = Image.new("RGB", (w, h), (3, 4, 5))
    px = im.load()
    cx, cy, rx, ry = 470.0, 230.0, 620.0, 420.0
    c0, c1, c2 = (21, 24, 29), (10, 12, 15), (3, 4, 5)
    for y in range(h):
        for x in range(w):
            d = (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) ** 0.5
            if d < 0.48:
                t = d / 0.48; c = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
            else:
                t = min(1, (d - 0.48) / 0.52); c = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            px[x, y] = c
    im.save(os.path.join(OUT, "B2SubBg.png"), optimize=True)


def statusbar():
    """B2StatusBarBg.png 800x64: transparant + haarlijn y 63 (wit 16%, fade aan beide kanten)."""
    w, h = 800, 64
    im = Image.new("RGBA", (w, h), (3, 4, 5, 0))
    line = Image.new("RGBA", (w, 1), (0, 0, 0, 0))
    lp = line.load()
    for x in range(w):
        t = x / (w - 1)
        a = 0.16 * min(1, t / 0.18, (1 - t) / 0.18)
        lp[x, 0] = (255, 255, 255, int(255 * a))
    im.paste(line, (0, 63))
    im.save(os.path.join(OUT, "B2StatusBarBg.png"), optimize=True)


def icon_home(name="B2IcnSbHome.png", col=GREY):
    """B2IcnSbHome.png 58x62: lijn-huisicoon (64-raster, lijn 2.6, ronde uiteinden)."""
    w, h = 58, 62
    im = canvas(w, h); d = ImageDraw.Draw(im); s = SS; lw = int(2.6 * s)
    cx, cy = 29, 31
    pts = [(cx - 12, cy - 1), (cx, cy - 12), (cx + 12, cy - 1)]
    d.line([(p[0] * s, p[1] * s) for p in pts], fill=col + (255,), width=lw, joint="curve")
    d.line([((cx - 9) * s, (cy - 3) * s), ((cx - 9) * s, (cy + 11) * s), ((cx + 9) * s, (cy + 11) * s),
            ((cx + 9) * s, (cy - 3) * s)], fill=col + (255,), width=lw, joint="curve")
    return done(im, name, w, h)


def leftbtn(kind, state):
    """LeftBtn PNG 94x416 (hitbox ongewijzigd, zie DESIGN-SYSTEEM §1): chevron op (31,272), state-kleur.

    kind: "Back" (pijl links) of "FldrUp" (map-omhoog); state: En/Focus/Hit/Ds.
    Focus = wit + Soul-Red bar; Hit = feller vlak; Ds = gedimd.
    """
    w, h = 94, 416
    name = "B2Btn%s_%s.png" % (kind, state)
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    s = SS
    cx, cy = 31, 272
    col = GREY if state in ("En", "Ds") else WHITE
    alpha = 255 if state != "Ds" else 110
    lw = int(3.4 * s)
    if kind == "Back":
        pts = [(cx + 9, cy - 14), (cx - 8, cy), (cx + 9, cy + 14)]
        d.line([(p[0] * s, p[1] * s) for p in pts], fill=col + (alpha,), width=lw, joint="curve")
    else:  # FldrUp: map-icoon (folder) met pijl omhoog
        fw, fh = 30, 20
        fx, fy = cx - fw // 2, cy - fh // 2 + 3
        d.line([(fx * s, (fy + 5) * s), ((fx + 6) * s, fy * s), ((fx + fw - 6) * s, fy * s), ((fx + fw) * s, (fy + 5) * s),
                ((fx + fw) * s, (fy + fh) * s), (fx * s, (fy + fh) * s), (fx * s, (fy + 5) * s)],
               fill=col + (alpha,), width=lw, joint="curve")
        d.line([(cx * s, (cy - 12) * s), (cx * s, (cy + 6) * s)], fill=col + (alpha,), width=lw)
        d.line([((cx - 6) * s, (cy - 6) * s), (cx * s, (cy - 12) * s), ((cx + 6) * s, (cy - 6) * s)],
               fill=col + (alpha,), width=lw, joint="curve")
    if state == "Focus":
        im = Image.alpha_composite(im, red_bar(w, h, 2, cy - 16, 4, 32))
    elif state == "Hit":
        d.rectangle([0, (cy - 30) * s, 60 * s, (cy + 30) * s], fill=(255, 255, 255, 26))
    return done(im, name, w, h)


def main():
    bg()
    statusbar()
    icon_home()
    for k in ("Back", "FldrUp"):
        for st in ("En", "Focus", "Hit", "Ds"):
            leftbtn(k, st)
    print("p0_base ->", OUT, "(B2SubBg, B2StatusBarBg, B2IcnSbHome, B2BtnBack_*, B2BtnFldrUp_*)")


if __name__ == "__main__":
    main()
