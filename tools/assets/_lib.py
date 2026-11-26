#!/usr/bin/env python3
"""_lib.py -- gedeelde helpers voor de B2Sub-asset-generatoren (P0..P4) in ui-oemplus-inject-v1.3/tools/assets/.

Gesplitst uit ui-mockup-v1.0/submenus/tools/make_assets.py (BOUWPLAN.md P0): canvas/red_bar/band/key-helpers en de
kleuren uit DESIGN-SYSTEEM.md §2. Elk pakket pN_*.py importeert dit bestand NIET via package, maar voegt de eigen map
aan sys.path (of draait vanaf deze dir), en schrijft naar ../common/oemplusb2/images/ (op de CMU:
jci/gui/common/oemplusb2/images/; de CSS in ../css/ gebruikt url(../images/X.png)).

Gebruik:  python3 tools/assets/p0_base.py   (vanaf ui-oemplus-inject-v1.3/)
Presto-veilig: alle verlopen/gloed/afgeronde vormen zitten IN de PNG; de CSS gebruikt alleen url(), rgba(),
border-radius. Alles 4x supersampled en teruggeschaald (anti-aliasing).
"""
import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "overlay-src", "common", "oemplusb2", "images"))
os.makedirs(OUT, exist_ok=True)
SS = 4  # supersample

# DESIGN-SYSTEEM.md §2
RED = (200, 16, 46)        # accent Soul Red #C8102E
WHITE = (255, 255, 255)    # text-focus
LIGHT = (232, 234, 238)    # primary-outline #E8EAEE
INK = (11, 13, 16)         # ink #0B0D10
GREY = (201, 206, 214)     # text-value #AEB4BD


def canvas(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def done(img, name, w, h):
    img = img.resize((w, h), Image.LANCZOS)
    img.save(os.path.join(OUT, name), optimize=True)
    return name


def hfade_line(w, y, x0, alpha_max, fade_from=0.55, h=1):
    """1px horizontale lijn die van alpha_max (bij x0) naar 0 (rechts) loopt."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for x in range(x0, w):
        t = (x - x0) / max(1, (w - x0))
        a = alpha_max if t < fade_from else alpha_max * max(0.0, 1 - (t - fade_from) / (1 - fade_from))
        for yy in range(h):
            px[x, yy] = (255, 255, 255, int(a))
    return im


def red_bar(w, h, x, y, bw, bh, vertical=True, glow=True):
    """Soul-Red accentstreep met zachte gloed (gloed = geblurde kopie, in de PNG)."""
    im = canvas(w, h)
    if glow:
        g = canvas(w, h)
        d = ImageDraw.Draw(g)
        pad = 3 * SS
        d.rounded_rectangle([x * SS - pad, y * SS - pad, (x + bw) * SS + pad, (y + bh) * SS + pad],
                            radius=4 * SS, fill=RED + (150,))
        g = g.filter(ImageFilter.GaussianBlur(7 * SS))
        im = Image.alpha_composite(im, g)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x * SS, y * SS, (x + bw) * SS - 1, (y + bh) * SS - 1], radius=int(min(bw, bh) / 2 * SS),
                        fill=RED + (255,))
    return im


def band(w, h, a_left, a_right, top_a, bot_a):
    """Focusband: horizontaal verloop wit a_left -> a_right, haarlijn boven/onder."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for x in range(w):
        t = x / (w - 1)
        a = a_left + (a_right - a_left) * t
        ta = top_a * (1 - 0.85 * t)
        ba = bot_a * (1 - 0.85 * t)
        for y in range(h):
            v = a
            if y == 0:
                v = max(a, ta)
            elif y == h - 1:
                v = max(a, ba)
            px[x, y] = (255, 255, 255, int(v))
    return im


def key(w, h, state, name, inset=(6, 8), radius=9, bar_w=None):
    """Generieke knop/toets PNG: vlak wit alpha per state + optionele Soul-Red bar onder (focus/primary).

    state: "En" (wit 7-8%), "Focus" (16% + rode bar), "Hit" (26-28%), "Ds" (gedimd),
           "Red" (Soul-Red vlak), "Green" (lichte omlijning, primair).
    """
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    x0, y0 = inset[0] * SS, inset[1] * SS
    x1, y1 = (w - inset[0]) * SS, (h - inset[1]) * SS
    r = radius * SS
    if state == "En":
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=WHITE + (20,))
    elif state == "Focus":
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=WHITE + (41,))
        if bar_w:
            bw = bar_w * SS
            bx = (w * SS - bw) // 2
            by = h * SS - inset[1] * SS - 3 * SS
            d.rounded_rectangle([bx, by, bx + bw - 1, by + 3 * SS - 1], radius=SS, fill=RED + (255,))
    elif state == "Hit":
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=WHITE + (68,))
    elif state == "Ds":
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=WHITE + (10,))
    elif state == "Red":
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=RED + (255,))
    elif state == "Green":
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=LIGHT + (255,), width=2 * SS)
    return done(im, name, w, h)
