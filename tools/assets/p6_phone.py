#!/usr/bin/env python3
"""p6_phone.py -- genereert ALLEEN de P6 "phone" B2Sub-assets (BOUWPLAN eco-bel P6-phone):
  B2CallCard.png (774x134), B2CallIcon_{Active,Inactive}.png (51x51), B2CallAvatar{90,146}.png,
  B2CallBtn{2,3}_{Answer,Reject}_{En,Focus,Hit}.png + B2CallBtn{2,3}_Ds.png (330x80 / 220x80 = OEM knopbox),
  B2DlgFocusRing{1..4}.png (662/330/220/165 x 80, generieke focus-ring voor het B2Sub-20-voorstel),
  B2UmpPh{Hangup,Comm,RouteHandset,RouteVehicle,Mute,Unmute,AddCall,Swap,Merge,Dialpad}_{En,Ds}.png
  (38x38; Hangup 58x58 rode schijf).

GEEN B2DialogBg*Solid.png: v1.4 (commit ca192db6, p2_dialog3.py) genereert B2DialogBg(Fs).png al met een
DEKKENDE scrim (alpha 255 over het hele vlak) -- de prototype-A2-dekkingsfix is in v1.4 dus al gedekt en
zou dubbel werk zijn (zie NOTITIE/rapport P6: overlap-analyse §A2).

Bron: potlood-functies overgenomen uit projects/mazda-mzd/tools/make_eco_bel_assets.py (call_assets(),
Ico/g_handset/g_person), output-ING naar DEZE map (v1.4 overlay-src) via _lib.OUT.
Maten = exact de OEM-elementmaat (hitbox-invariant H1, DESIGN-SYSTEEM par.0.2): Active_Call_Bkg 774x134,
ActiveCall_En 51x52 (Ds 52x52 -> 51x51 raster), NowPlayingImageFrame 146x146 (Dialog3 Style04_Image1),
InCall2 image-frame 90x90, Dialog3 knoppen 330/220x80, Ump3 iconen 40x40 OEM -> B2 38x38 (icon-div is
100%x100% met background-position center 62%, dus de PNG-maat is vrij binnen het icoon; 38x38 = B2-raster).

Gebruik (vanaf ui-oemplus-inject-v1.4/):  python3 tools/assets/p6_phone.py
Output: overlay-src/common/oemplusb2/images/  (op de CMU: jci/gui/common/oemplusb2/images/)
Eigenaarschap (BOUWPLAN): alleen P6 schrijft deze PNG's (prefix B2Call*/B2UmpPh*/B2DlgFocusRing*);
P0..P5-PNG's worden niet overschreven.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter
from _lib import OUT, SS, RED, WHITE, LIGHT, canvas, done

# ---- tokens (DESIGN-SYSTEEM par.2 + ONTWERP.md par.2 eco-bel) ----
TEXT3 = (138, 145, 155)     # text-3
VALUE = (174, 180, 189)     # icoon rust
DIS = (95, 101, 110)        # disabled
CALLG = (31, 170, 89)       # oproep-groen #1FAA59: ALLEEN 'opnemen' + actief-gesprek-indicator

written = []


def S(v):
    return int(round(v * SS))


def col(c, a):
    return tuple(c[:3]) + (int(a),)


def poly(d, pts, color, width, closed=False):
    P = [(S(x), S(y)) for x, y in pts]
    if closed:
        P = P + [P[0]]
    d.line(P, fill=color, width=S(width), joint="curve")
    r = S(width) / 2.0
    for p in (P[0], P[-1]):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)


def fillpoly(d, pts, color):
    d.polygon([(S(x), S(y)) for x, y in pts], fill=color)


def glow(img, color, radius, strength=1.0):
    a = img.split()[3].filter(ImageFilter.GaussianBlur(S(radius)))
    if strength != 1.0:
        a = a.point(lambda v: min(255, int(v * strength)))
    g = Image.new("RGBA", img.size, col(color, 255))
    g.putalpha(a)
    return Image.alpha_composite(g, img)


def done2(img, name, w, h):
    done(img, name, w, h)
    written.append(name)


# ---- icoon-raster (64x64 eenheden, gecentreerd in w x h) ----
class Ico:
    def __init__(self, w, h, size, cx=None, cy=None):
        self.w, self.h = w, h
        self.k = size / 64.0
        self.ox = (w if cx is None else 2 * cx) / 2.0 - size / 2.0
        self.oy = (h if cy is None else 2 * cy) / 2.0 - size / 2.0
        self.im = canvas(w, h)
        self.d = ImageDraw.Draw(self.im)

    def p(self, pts):
        return [(self.ox + x * self.k, self.oy + y * self.k) for x, y in pts]

    def line(self, pts, c, lw=3.4, closed=False):
        poly(self.d, self.p(pts), c, lw * self.k, closed)

    def fill(self, pts, c):
        fillpoly(self.d, self.p(pts), c)

    def rrect(self, x0, y0, x1, y1, r, c, lw=3.4, fillc=None):
        q = self.p([(x0, y0), (x1, y1)])
        box = [S(q[0][0]), S(q[0][1]), S(q[1][0]), S(q[1][1])]
        self.d.rounded_rectangle(box, radius=S(r * self.k), outline=c, width=S(lw * self.k), fill=fillc)

    def circle(self, cx, cy, r, c, lw=3.4, fillc=None):
        q = self.p([(cx - r, cy - r), (cx + r, cy + r)])
        self.d.ellipse([S(q[0][0]), S(q[0][1]), S(q[1][0]), S(q[1][1])], outline=c, width=S(lw * self.k), fill=fillc)

    def arc(self, cx, cy, r, a0, a1, c, lw=3.4):
        pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
               for a in [a0 + (a1 - a0) * i / 40.0 for i in range(41)]]
        self.line(pts, c, lw)


def g_handset(ic, c, lw=3.4, down=False, fillc=None):
    """Telefoonhoorn (64-raster); down=True = hoorn-omlaag (weigeren/ophangen)."""
    if not down:
        ic.line([(14, 44), (22, 36), (30, 44), (44, 58), (50, 52), (36, 38), (28, 46), (20, 50), (14, 44)], c, lw, closed=True)
    else:
        ic.line([(14, 20), (20, 14), (28, 18), (36, 30), (50, 44), (44, 50), (30, 36), (22, 28), (14, 20)], c, lw, closed=True)
    if fillc:
        ic.fill([(14, 44), (22, 36), (30, 44), (44, 58), (50, 52), (36, 38), (28, 46), (20, 50)], fillc)


def g_person(ic, c, lw=3.4):
    """Persoonsglyph (hoofd + schouders) voor de avatar-placeholder."""
    ic.circle(32, 22, 11, c, lw)
    ic.arc(32, 66, 22, 200, 340, c, lw)


def call_assets():
    # actief gesprek: kaart (OEM Active_Call_Bkg, element 774x134, background-size 100 %)
    im = canvas(774, 134)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([S(1), S(4), S(773), S(130)], radius=S(16), fill=col(WHITE, 14), outline=col(WHITE, 30), width=S(1))
    d.rounded_rectangle([S(10), S(49), S(14), S(85)], radius=S(2), fill=col(CALLG, 255))
    done2(im, "B2CallCard.png", 774, 134)
    # gesprek-icoon (OEM ActiveCall_En 51x52 / _Ds 52x52 -> 51x51)
    for name, c in (("B2CallIcon_Active.png", CALLG), ("B2CallIcon_Inactive.png", TEXT3)):
        ic = Ico(51, 51, 34)
        g_handset(ic, col(c, 255), 3.6)
        done2(ic.im, name, 51, 51)
    # avatar-ring 90x90 (OEM InCall2 image-frame) en 146x146 (Dialog3 Style04_Image1 / NowPlayingImageFrame)
    for name, n in (("B2CallAvatar90.png", 90), ("B2CallAvatar146.png", 146)):
        im = canvas(n, n)
        d = ImageDraw.Draw(im)
        d.ellipse([S(2), S(2), S(n - 2), S(n - 2)], fill=(36, 40, 47, 255), outline=col(WHITE, 60), width=S(1.6))
        ic = Ico(n, n, n * 0.52)
        g_person(ic, col(VALUE, 255), 3.4)
        im = Image.alpha_composite(im, ic.im)
        done2(im, name, n, n)
    # opnemen / weigeren: pil in de OEM-knopbox (Dialog3 ButtonStyle02 330x80, ButtonStyle03 220x80)
    for n, w in ((2, 330), (3, 220)):
        for kind, c in (("Answer", CALLG), ("Reject", RED)):
            for state in ("En", "Focus", "Hit"):
                im = canvas(w, 80)
                d = ImageDraw.Draw(im)
                inset = 7
                fill = c if state != "Hit" else tuple(min(255, int(v * 1.18 + 12)) for v in c)
                if state == "Focus":   # witte focusring 3 px buiten de pil (rood = de knop zelf, dus focus = wit)
                    d.rounded_rectangle([S(inset - 5), S(inset - 5), S(w - inset + 5), S(80 - inset + 5)],
                                        radius=S(38), outline=col(WHITE, 255), width=S(3))
                d.rounded_rectangle([S(inset), S(inset), S(w - inset), S(80 - inset)], radius=S(33), fill=col(fill, 255))
                if n == 2:  # 2-knops-variant: hoorn-icoon (bij 220 breed past het OEM-label 'Einde + Antw' niet over een icoon)
                    ic = Ico(w, 80, 40, cx=inset + 34, cy=40)
                    g_handset(ic, col(WHITE, 255), 4.2, down=(kind == "Reject"))
                    im = Image.alpha_composite(im, ic.im)
                done2(im, "B2CallBtn%d_%s_%s.png" % (n, kind, state), w, 80)
        # uitgeschakeld (Handset-modus: OEM zet beide knoppen disabled via _disableIncomingButtons)
        im = canvas(w, 80)
        ImageDraw.Draw(im).rounded_rectangle([S(7), S(7), S(w - 7), S(73)], radius=S(33), fill=col(WHITE, 16),
                                             outline=col(WHITE, 26), width=S(1))
        done2(im, "B2CallBtn%d_Ds.png" % n, w, 80)
    # generieke Dialog3-focusring (VOORSTEL voor B2Sub-20, zie BOUWPLAN P6 stap 1 / rapport:
    # '_Green_En/_Red_En' + '_focused' -> in B2Sub-20 was focus onzichtbaar op gekleurde knoppen)
    for n, w in ((1, 662), (2, 330), (3, 220), (4, 165)):
        im = canvas(w, 80)
        ImageDraw.Draw(im).rounded_rectangle([S(2.5), S(3.5), S(w - 2.5), S(76.5)], radius=S(13), outline=col(WHITE, 255),
                                             width=S(2.5))
        done2(im, "B2DlgFocusRing%d.png" % n, w, 80)
    # UMP-iconen gesprek (OEM 40x40 iconen in de 114x100 Ump3Ctrl7-knop; icon-div background-position center 62 %)
    def ump(name, fn, c=LIGHT, size=38):
        ic = Ico(size, size, size)
        fn(ic, col(c, 255))
        done2(ic.im, name, size, size)

    def comm2(ic, c):
        ic.rrect(6, 10, 58, 46, 7, c, 3.6)
        ic.line([(18, 46), (14, 57), (30, 46)], c, 3.6)
        ic.line([(18, 24), (46, 24)], c, 3.6)
        ic.line([(18, 33), (38, 33)], c, 3.6)

    def route_h(ic, c):  # geluid via telefoon (handset)
        ic.rrect(20, 6, 44, 58, 6, c, 3.6)
        ic.line([(28, 50), (36, 50)], c, 3.6)

    def route_v(ic, c):  # geluid via auto (luidspreker)
        ic.line([(10, 24), (20, 24), (34, 12), (34, 52), (20, 40), (10, 40), (10, 24)], c, 3.6)
        ic.arc(36, 32, 12, -45, 45, c, 3.6)
        ic.arc(36, 32, 22, -45, 45, c, 3.6)

    def mute(ic, c):
        ic.rrect(24, 6, 40, 38, 8, c, 3.6)
        ic.arc(32, 28, 16, 0, 180, c, 3.6)
        ic.line([(32, 44), (32, 54)], c, 3.6)
        ic.line([(10, 8), (54, 56)], c, 3.6)

    def unmute(ic, c):
        ic.rrect(24, 6, 40, 38, 8, c, 3.6)
        ic.arc(32, 28, 16, 0, 180, c, 3.6)
        ic.line([(32, 44), (32, 54)], c, 3.6)

    def add(ic, c):
        g_handset(ic, c, 3.6)
        ic.line([(44, 6), (44, 26)], c, 3.6)
        ic.line([(34, 16), (54, 16)], c, 3.6)

    def swap(ic, c):
        ic.line([(10, 22), (50, 22)], c, 3.6)
        ic.line([(40, 12), (50, 22), (40, 32)], c, 3.6)
        ic.line([(54, 44), (14, 44)], c, 3.6)
        ic.line([(24, 34), (14, 44), (24, 54)], c, 3.6)

    def merge(ic, c):
        ic.line([(10, 14), (32, 32), (54, 14)], c, 3.6)
        ic.line([(32, 32), (32, 56)], c, 3.6)

    def pad(ic, c):
        for x in (16, 32, 48):
            for y in (12, 26, 40):
                ic.circle(x, y, 3.2, c, 0.1, fillc=c)
        ic.circle(32, 54, 3.2, c, 0.1, fillc=c)

    for base, fn in (("Comm", comm2), ("RouteHandset", route_h), ("RouteVehicle", route_v), ("Mute", mute),
                     ("Unmute", unmute), ("AddCall", add), ("Swap", swap), ("Merge", merge), ("Dialpad", pad)):
        ump("B2UmpPh%s_En.png" % base, fn)
        ump("B2UmpPh%s_Ds.png" % base, fn, DIS)
    # ophangen: rode schijf d 56 met witte hoorn-omlaag (niet alleen een rood icoon: altijd herkenbaar)
    for st, a in (("En", 255), ("Ds", 90)):
        im = canvas(58, 58)
        d = ImageDraw.Draw(im)
        d.ellipse([S(1), S(1), S(57), S(57)], fill=col(RED, a))
        ic = Ico(58, 58, 34)
        g_handset(ic, col(WHITE, 255 if a == 255 else 150), 4.4, down=True)
        done2(Image.alpha_composite(im, ic.im), "B2UmpPhHangup_%s.png" % st, 58, 58)


def main():
    call_assets()
    print("P6-phone assets: %d -> %s" % (len(written), OUT))
    for n in sorted(written):
        from PIL import Image as _I
        print("  %s  %s" % (n, _I.open(os.path.join(OUT, n)).size))


if __name__ == "__main__":
    main()
