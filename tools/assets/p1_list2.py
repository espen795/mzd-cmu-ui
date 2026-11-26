#!/usr/bin/env python3
"""p1_list2.py -- genereert ALLEEN de P1 "List2" B2Sub-assets (BOUWPLAN.md P1):
  B2ListFocus{,_Thick,_Press,_Press_Thick,_Gray,_Gray_Thick}.png (732x64/82),
  B2ListSep.png (732x2), B2TitleBg.png (730x69),
  B2Caret.png / B2Caret_Focus.png (10x20),
  B2Check_{On,Off}_{En,Ds}.png, B2Radio_{On,Off}_{En,Ds}.png, B2Tick.png (53x53),
  B2Toggle_{On,Off}_{En,Ds}.png (53x53),
  B2SliderTrack.png (346x13), B2SliderFill.png (8x11), B2SliderKnob_{En,Focus}.png (43x43),
  B2Plus.png / B2Minus.png (36x36),
  B2ScrollTrack.png (36x416), B2ScrollThumb.png (30x64).

Gebruik (vanaf ui-oemplus-inject-v1.3/):  python3 tools/assets/p1_list2.py
Output: overlay-src/common/oemplusb2/images/  (op de CMU: jci/gui/common/oemplusb2/images/)
Eigenaarschap (BOUWPLAN): alleen P1 schrijft deze PNG's; P0/P2-P4 gebruiken eigen prefixen.
Maten = exacte OEM-elementmaten uit v74 List2Ctrl.css (hitbox-invariant, H1):
  item 732x64/82, caret 10x20, image1/image2 53x53, slider 346x13 + fill 344x11 + knob 43x43,
  plus/minus 36x36, scrollbar wrapper 36 breed (indicator 30 breed), titel 730x69.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
from _lib import OUT, SS, RED, WHITE, LIGHT, INK, GREY, canvas, done, hfade_line, red_bar, band


def list_focus(h, name, a_l, a_r, red=True):
    """Focusband 732 x item-hoogte: horizontaal wit verloop + haarlijn boven + Soul-Red bar links."""
    w = 732
    b = band(w, h, int(255 * a_l), int(255 * a_r), int(255 * 0.24), int(255 * 0.12))
    b = b.resize((w * SS, h * SS))
    if red:
        b = Image.alpha_composite(b, red_bar(w, h, 6, h // 2 - 16, 4, 32))
    done(b, name, w, h)


def list_sep():
    """B2ListSep.png 732x2: 1px scheiding onderaan item, fade naar rechts (DESIGN-SYSTEEM §4 haarlijnen)."""
    w = 732
    im = Image.new("RGBA", (w, 2), (0, 0, 0, 0))
    im.paste(hfade_line(w, 0, 71, int(255 * 0.09), 0.6), (0, 1))
    im.save(os.path.join(OUT, "B2ListSep.png"), optimize=True)


def title_bg():
    """B2TitleBg.png 730x69: titelbalk = transparant + haarlijn onderaan (titeltekst = CSS-token)."""
    w, h = 730, 69
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.paste(hfade_line(w, 0, 20, int(255 * 0.16), 0.5), (0, h - 1))
    im.save(os.path.join(OUT, "B2TitleBg.png"), optimize=True)


def caret(name, col, a):
    """B2Caret.png 10x20: chevron rechts (OEM Caret.png is 10x21, element 10x20)."""
    w, h = 10, 20
    im = canvas(w, h); d = ImageDraw.Draw(im)
    d.line([(2 * SS, 3 * SS), (8 * SS, 10 * SS), (2 * SS, 17 * SS)], fill=col + (a,), width=int(2.4 * SS), joint="curve")
    done(im, name, w, h)


def scroll():
    """B2ScrollTrack 36x416 (wrapper) + B2ScrollThumb 30x64 (duim, 1 item hoog).

    OEM-mechanisme (List2Ctrl.js): de duim is EEN PNG (Scrollbar.png 31x416) met
    background-attachment:fixed; JS zet alleen style.top (positie) en style.height (lengte).
    Daarom moet de duim-PNG de VOLLE track-hoogte hebben (416) met het zichtbare pil in het
    bovenste 64 px; door background-attachment:fixed schuift het pil mee met top. Breedte 30
    = OEM .List2CtrlScrollIndicator width (right:2 in een 36px wrapper).
    """
    w, h = 36, 416
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    p = im.load()
    for y in range(8, h - 8):
        p[17, y] = (255, 255, 255, int(255 * 0.10))
        p[18, y] = (255, 255, 255, int(255 * 0.10))
    im.save(os.path.join(OUT, "B2ScrollTrack.png"), optimize=True)
    tw, th = 30, 416          # zelfde hoogte als OEM Scrollbar.png -> top/height-truc werkt identiek
    t = canvas(tw, th); d = ImageDraw.Draw(t)
    # pil in de bovenste 64 px, gecentreerd op x 13..17 (zoals OEM: 4px breed midden in 30px)
    d.rounded_rectangle([13 * SS, 2 * SS, 17 * SS, 64 * SS - 2 * SS], radius=2 * SS, fill=(232, 234, 238, 210))
    done(t, "B2ScrollThumb.png", tw, th)


def toggle(on, ds):
    """B2Toggle 53x53: pil-schakelaar (OEM image2 styleOnOff). Aan = licht pil + ink knop rechts."""
    w, h = 53, 53
    im = canvas(w, h); d = ImageDraw.Draw(im)
    a = 255 if not ds else 100
    x0, y0, x1, y1 = 4, 13, 49, 40
    if on:
        d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=14 * SS, fill=LIGHT + (a,))
        d.ellipse([(x1 - 24) * SS, (y0 + 3) * SS, (x1 - 3) * SS, (y1 - 3) * SS], fill=INK + (a,))
    else:
        d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=14 * SS, fill=(255, 255, 255, int(a * 0.06)),
                            outline=(255, 255, 255, int(a * 0.45)), width=int(2 * SS))
        d.ellipse([(x0 + 4) * SS, (y0 + 4) * SS, (x0 + 23) * SS, (y1 - 4) * SS], fill=(160, 166, 175, a))
    done(im, "B2Toggle_%s_%s.png" % ("On" if on else "Off", "Ds" if ds else "En"), w, h)


def checkbox(checked, ds):
    """B2Check 53x53: vierkant vakje + vinkje (OEM image1 style03.checkbox)."""
    w, h = 53, 53
    im = canvas(w, h); d = ImageDraw.Draw(im); a = 255 if not ds else 100
    r = [12 * SS, 12 * SS, 41 * SS, 41 * SS]
    if checked:
        d.rounded_rectangle(r, radius=6 * SS, fill=LIGHT + (a,))
        d.line([(18 * SS, 27 * SS), (24 * SS, 33 * SS), (35 * SS, 20 * SS)], fill=INK + (a,), width=int(3.4 * SS), joint="curve")
    else:
        d.rounded_rectangle(r, radius=6 * SS, outline=(255, 255, 255, int(a * 0.55)), width=int(2.2 * SS))
    done(im, "B2Check_%s_%s.png" % ("On" if checked else "Off", "Ds" if ds else "En"), w, h)


def radio(checked, ds):
    """B2Radio 53x53: rondje + dot (OEM image1 style03.radio)."""
    w, h = 53, 53
    im = canvas(w, h); d = ImageDraw.Draw(im); a = 255 if not ds else 100
    d.ellipse([12 * SS, 12 * SS, 41 * SS, 41 * SS], outline=(255, 255, 255, int(a * (0.9 if checked else 0.55))), width=int(2.2 * SS))
    if checked:
        d.ellipse([19 * SS, 19 * SS, 34 * SS, 34 * SS], fill=LIGHT + (a,))
    done(im, "B2Radio_%s_%s.png" % ("On" if checked else "Off", "Ds" if ds else "En"), w, h)


def tick():
    """B2Tick.png 53x53: los vinkje (OEM image1 style03.tick)."""
    w, h = 53, 53
    im = canvas(w, h); d = ImageDraw.Draw(im)
    d.line([(15 * SS, 27 * SS), (23 * SS, 35 * SS), (38 * SS, 18 * SS)], fill=LIGHT + (255,), width=int(3.4 * SS), joint="curve")
    done(im, "B2Tick.png", w, h)


def red_ring(w, h):
    """Soul-Red ring met gloed (in PNG) voor de gefocuste sliderknop."""
    g = canvas(w, h); d = ImageDraw.Draw(g)
    c = w / 2.0
    d.ellipse([(c - 17) * SS, (c - 17) * SS, (c + 17) * SS, (c + 17) * SS], outline=RED + (255,), width=int(3 * SS))
    glow = g.filter(ImageFilter.GaussianBlur(4 * SS))
    return Image.alpha_composite(glow, g)


def slider_list():
    """In-lijst slider (style12/13/28): track 346x13, fill 8x11 tile (repeat-x), knob 43x43.

    OEM: .List2CtrlSliderCtrl 346x13 (ListItem_SliderBG-1.png), Fill 344x11, Handle 43x43 top:-15
    (steekt 15px boven de track uit -> CSS mag GEEN overflow:hidden zetten; wij raken geen layout).
    """
    w, h = 346, 13
    im = canvas(w, h); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 5 * SS, w * SS - 1, 8 * SS - 1], radius=int(1.5 * SS), fill=(255, 255, 255, 46))
    done(im, "B2SliderTrack.png", w, h)
    im = Image.new("RGBA", (8, 11), (0, 0, 0, 0)); p = im.load()
    for x in range(8):
        for y in (4, 5, 6):
            p[x, y] = LIGHT + (255,)
    im.save(os.path.join(OUT, "B2SliderFill.png"), optimize=True)
    for st in ("En", "Focus"):
        w = h = 43
        k = canvas(w, h)
        if st == "Focus":
            k = Image.alpha_composite(k, red_ring(w, h))
        d = ImageDraw.Draw(k)
        rr = 11 if st == "En" else 12
        d.ellipse([(21.5 - rr) * SS, (21.5 - rr) * SS, (21.5 + rr) * SS, (21.5 + rr) * SS], fill=WHITE + (255,))
        done(k, "B2SliderKnob_%s.png" % st, w, h)


def plusminus():
    """B2Plus/B2Minus 36x36: stapper-knoppen (styleStep .plus/.minus, OEM 36x36)."""
    for nm, plus in (("B2Plus.png", True), ("B2Minus.png", False)):
        w = h = 36
        im = canvas(w, h); d = ImageDraw.Draw(im)
        d.ellipse([1 * SS, 1 * SS, 35 * SS, 35 * SS], outline=(255, 255, 255, 110), width=int(1.6 * SS))
        d.line([(11 * SS, 18 * SS), (25 * SS, 18 * SS)], fill=LIGHT + (255,), width=int(2.6 * SS))
        if plus:
            d.line([(18 * SS, 11 * SS), (18 * SS, 25 * SS)], fill=LIGHT + (255,), width=int(2.6 * SS))
        done(im, nm, w, h)


def main():
    list_focus(64, "B2ListFocus.png", 0.135, 0.035)
    list_focus(82, "B2ListFocus_Thick.png", 0.135, 0.035)
    list_focus(64, "B2ListFocus_Press.png", 0.24, 0.08)
    list_focus(82, "B2ListFocus_Press_Thick.png", 0.24, 0.08)
    list_focus(64, "B2ListFocus_Gray.png", 0.07, 0.02, red=False)
    list_focus(82, "B2ListFocus_Gray_Thick.png", 0.07, 0.02, red=False)
    list_sep(); title_bg(); scroll()
    caret("B2Caret.png", (138, 145, 155), 255)
    caret("B2Caret_Focus.png", WHITE, 255)
    for on in (False, True):
        for ds in (False, True):
            toggle(on, ds); checkbox(on, ds); radio(on, ds)
    tick(); slider_list(); plusminus()
    print("p1_list2 ->", OUT,
          "(B2List*, B2TitleBg, B2Caret*, B2Check_*, B2Radio_*, B2Tick, B2Toggle_*, B2Slider*, B2Plus, B2Minus, B2Scroll*)")


if __name__ == "__main__":
    main()
