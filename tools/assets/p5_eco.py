#!/usr/bin/env python3
"""p5_eco.py -- pakket P5-eco (optie B, 2026-11-27) asset-generator voor ui-oemplus-inject-v1.4.

BRON: ui-mockup-v1.0/eco-bel/optieB/ (commit 601d9626): ONTWERP-B.md + BORD-B.png + optieB/assets/
(bake_optieB.py -> B2EcoCarPhoto_B.jpg 800x416) en tools/build_optieB.py (raster, hotspots, leader-lines).

Wijzigingen t.o.v. BORD-B (keuzes de gebruiker, zie taak):
  * Klaar/OK = donkerrood Mazda-stijl (Soul Red donker): lijn #8E1A22, accent #B0202C -- NIET groen, en
    duidelijk anders dan focus (fel rood #C8102E met gloed, zie DESIGN-SYSTEEM par.2).
  * Waarschuwing/blokkeert blijft amber #E7A23A. Motor-uit gloed = donkerrood ipv groen.
  * Effectiviteit-bomen mogen eco-groen #3FB68B blijven ("snap ik bij eco").
  * Brandstofverbruik-staven = rood (huidige rit / beste in helder rood #E8323C, rest grijs) ipv groen.
  * TPMS = indirect: GEEN bar-waarden/per-wiel. Twee bandenbubbels (L/R voorband) met tekst
    "Banden OK" (rood-accent) / "Bandendruk laag" (amber, pulserend) / "TPMS-storing" (amber, niet
    pulserend); geen data = verborgen (ONTWERP-B B6).

Output: overlay-src/common/oemplusb2/images/B2Eco*.png (+ .jpg) -- eigen prefix B2Eco (BOUWPLAN P5).
Op de CMU: jci/gui/common/oemplusb2/images/; CSS ../css/B2Sub-50-eco.css gebruikt url(../images/X).

Gebruik:  python3 tools/assets/p5_eco.py   (vanuit ui-oemplus-inject-v1.4/)
Host-only. Presto-veilig: alle vormen/gloed/tekst zitten IN de PNG (4x supersampled); CSS gebruikt
alleen url()/rgba()/border-radius. Foto = JPEG 800x416 (nooit groter dan het scherm).
"""
import os
import sys
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _lib  # noqa: E402  gedeelde helpers (OUT = overlay-src/common/oemplusb2/images, SS=4)

MZD = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ECO_BEL = os.path.join(MZD, "ui-mockup-v1.0", "eco-bel")
OPTIEB = os.path.join(ECO_BEL, "optieB")
STOCK = os.path.normpath(os.path.join(HERE, "..", "..", "harness", "root-stock"))
FONTS = os.path.join(STOCK, "_harness_fonts")
OUT = _lib.OUT

SS = _lib.SS
WHITE = _lib.WHITE
INK = _lib.INK
RED = _lib.RED                       # #C8102E focus (fel rood met gloed) -- NIET voor OK
# --- P5-eco tokens (de gebruiker-wijzigingen t.o.v. BORD-B) ---
OK_LINE = (142, 26, 34)             # #8E1A22  Klaar/OK lijnen (donkerrood, Mazda Soul Red donker)
OK_ACC = (176, 32, 44)               # #B0202C  Klaar/OK accent (schijfjes, randen 100%, tekst)
OK_SOFT = (142, 26, 34, 171)         # rand 67% dekking
WARN = (231, 162, 58)                # #E7A23A  amber: blokkeert / lage druk / storing (ongewijzigd)
WARN_RGBA = (231, 162, 58, 255)
ECO = (63, 182, 139)                 # #3FB68B  eco-groen: ALLEEN Effectiviteit-bomen (de gebruiker)
BAR_CUR = (232, 50, 60)              # #E8323C  Brandstofverbruik: huidige/beste staaf (helder rood)
BAR_OK = (176, 32, 44)               # #B0202C  zuinige staven donkerrood
BAR_GREY = (120, 128, 140)           # #78808C  (niet meer voor staven; v1.4-r2: de gebruiker wil GEEN grijze staven)
BAR_DIM = (112, 30, 38)              # #701E26  overige staven gedempt donkerrood (v1.4-r2, i.p.v. grijs)
BAR_CAP = (214, 92, 100)             # #D65C64  staaf-kapje lichtrood (was lichtgrijs)
TXT_OKRED = (214, 62, 72)            # #D63E48  leesbare rood-accent tekst op donker (kickers Time-kaart)
GREY = (107, 114, 124)               # #6B727C
TXT_HERO = (242, 243, 245)           # #F2F3F5
TXT_1 = (217, 221, 226)              # #D9DDE2
TXT_2 = (154, 161, 170)              # #9AA1AA
TXT_3 = (138, 145, 155)              # #8A919B

# ------------------------------------------------------------------ raster (ONTWERP-B par.1, control-coord 0..800 x 0..416)
COL_W, BOX_H, R = 176, 64, 14
BOX_H_TIRE = 72                      # bandenbubbel iets hoger zodat "Bandendruk laag" ruim past
COL_L = 12
COL_R = 800 - 12 - COL_W             # 612
ROWS = (56, 169, 282)
PAD = 14
DISC = 40
DISC_TIRE = 34
UMP_Y = 380 - 64                     # niets wezenlijks onder control-y 316
HOT = {                              # hotspots op de foto (control-coord, zie build_optieB.py)
    'ac': (330, ROWS[0]),
    'engine': (330, 120),
    'batt': (470, 120),
    'tireL': (216, 298),
    'tireR': (584, 298),
}
SLOT = {'ac': ('L', 0), 'engine': ('L', 1), 'tireL': ('L', 2),
        'kpi': ('R', 0), 'batt': ('R', 1), 'tireR': ('R', 2)}
PILL = dict(x=270, y=ROWS[2] - 26, w=260, h=52)
CARD = dict(x=236, w=328, bottom=ROWS[2] + BOX_H // 2)   # 314


def S(v):
    return int(round(v * SS))


def col(c, a):
    return (c[0], c[1], c[2], int(a))


def font(px, semibold=False):
    f = "TipperarySemibold.ttf" if semibold else "Tipperary.ttf"
    return ImageFont.truetype(os.path.join(FONTS, f), px * SS)


def canvas(w, h):
    return Image.new("RGBA", (S(w), S(h)), (0, 0, 0, 0))


def done(img, name, w, h):
    img = img.resize((w, h), Image.LANCZOS)
    img.save(os.path.join(OUT, name), optimize=True)
    return name


def glow_img(im, rgb, radius, peak=0.65):
    """Voeg een radiale gloed toe rond de alfa van im (gloed IN de PNG)."""
    a = im.split()[3]
    g = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    bbox = a.getbbox()
    if bbox:
        gd.ellipse([bbox[0] - radius * SS, bbox[1] - radius * SS,
                    bbox[2] + radius * SS, bbox[3] + radius * SS], fill=col(rgb, int(255 * peak)))
    g = g.filter(ImageFilter.GaussianBlur(radius * SS))
    ga = g.split()[3].point(lambda v: int(v * 0.55))
    g.putalpha(ImageChopsMultiply(ga, a.point(lambda v: 255)))
    return Image.alpha_composite(g, im)


def ImageChopsMultiply(a, b):
    from PIL import ImageChops
    return ImageChops.multiply(a, b)


def radial_glow(d_size, rgb, peak=0.6):
    """Zuivere radiale gloed-PNG (d x d), alpha = (1-r)^2 * peak."""
    yy, xx = __import__("numpy").mgrid[0:d_size, 0:d_size]
    r = __import__("numpy").hypot(xx - d_size / 2, yy - d_size / 2) / (d_size / 2)
    a = __import__("numpy").clip(1 - r, 0, 1) ** 2 * peak
    import numpy as np
    im = np.zeros((d_size, d_size, 4), np.uint8)
    im[..., :3] = rgb
    im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im, "RGBA")


# ------------------------------------------------------------------ iconen (64-grid, stroke, zelfde stijl als build_optieB)
ICON = {
    'engine': ('<rect x="16" y="24" width="30" height="24" rx="3"/><path d="M23 24v-6h16v6M27 14h8M31 14v4"/>'
               '<path d="M16 31h-6v10h6M46 30h5l5-4v20l-5-4h-5"/><path d="M24 31v10M31 31v10M38 31v10"/>'),
    'batt': ('<rect x="9" y="21" width="46" height="29" rx="4"/><path d="M17 21v-5h8v5M39 21v-5h8v5'
             'M16 35h10M37 35h10M42 30v10"/>'),
    'ac': ('<path d="M32 9v46M12 20.5l40 23M12 43.5l40-23M25 11l7 6 7-6M25 53l7-6 7 6'
           'M11 28l9 1 3-8M53 36l-9-1-3 8M11 36l9-1 3 8M53 28l-9 1-3-8"/>'),
    'tire': ('<circle cx="32" cy="32" r="22"/><circle cx="32" cy="32" r="9"/>'
             '<path d="M32 10v6M32 48v6M10 32h6M48 32h6M16.5 16.5l4.2 4.2M43.3 43.3l4.2 4.2'
             'M47.5 16.5l-4.2 4.2M20.7 43.3l-4.2 4.2"/>'),
    'warnTri': '<path d="M32 10L56 52H8z"/><path d="M32 26v12"/><circle cx="32" cy="45" r="1.6"/>',
    'leaf': '<path d="M16 48C14 26 30 14 50 14c0 22-12 34-34 34zM16 48l18-18"/>',
}


def svg_paths(name, size, color, sw=3.6):
    """Rasteriseer een 64-grid icon (alleen circle/rect/path met M/L/z) op size x size. Eenvoudige parser
    voor de bovenstaande ICON-definities ( Genoeg voor deze iconen)."""
    import re
    im = Image.new("RGBA", (S(size), S(size)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sc = size / 64.0
    c = col(color, 255)
    lw = max(1, int(round(sw * sc * SS / sc * sc)))  # stroke in px * SS
    lw = S(sw * sc)
    for m in re.finditer(r"<(circle|rect|path)\b([^>]*)/>", ICON[name]):
        tag, attrs = m.group(1), m.group(2)
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs))
        if tag == "circle":
            cx, cy, r = float(a["cx"]) * sc, float(a["cy"]) * sc, float(a["r"]) * sc
            d.ellipse([S(cx - r), S(cy - r), S(cx + r), S(cy + r)], outline=c, width=lw)
        elif tag == "rect":
            x, y = float(a["x"]) * sc, float(a["y"]) * sc
            w, h = float(a["width"]) * sc, float(a["height"]) * sc
            rx = float(a.get("rx", 0)) * sc
            d.rounded_rectangle([S(x), S(y), S(x + w), S(y + h)], radius=S(rx), outline=c, width=lw)
        elif tag == "path":
            pts = []
            for tok in re.finditer(r"([ML])\s*([\d.\s,-]+)", a["d"]):
                nums = [float(v) for v in re.split(r"[\s,]+", tok.group(2).strip()) if v]
                for i in range(0, len(nums) - 1, 2):
                    pts.append((nums[i] * sc, nums[i + 1] * sc))
            if len(pts) >= 2:
                d.line([S(p[0]) for p in pts] and [(S(p[0]), S(p[1])) for p in pts], fill=c, width=lw,
                       joint="curve")
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ bouwstenen (raster uit ONTWERP-B par.1)
def box_xy(side, row):
    x = COL_L if side == 'L' else COL_R
    return x, ROWS[row] - BOX_H // 2


def leader_pts(side, row, hx, hy, r):
    """ONTWERP-B par.1 regel: horizontaal vanaf de binnenrand van de bubbel op de rijlijn; als het
    onderdeel niet op de rijlijn ligt precies 1 knik van 45 graden; lijn stopt op de schijfrand."""
    ry = ROWS[row]
    ex = COL_L + COL_W if side == 'L' else COL_R
    dy = hy - ry
    sgn = 1 if side == 'L' else -1
    kx = hx - sgn * abs(dy)
    pts = [(ex, ry), (kx, ry), (hx, hy)] if dy else [(ex, ry), (hx, hy)]
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    L = math.hypot(bx - ax, by - ay) or 1
    pts[-1] = (bx - (bx - ax) / L * r, by - (by - ay) / L * r)
    return pts


def draw_leader(d, pts, color, alpha=0.85, width=2):
    p = [(S(x), S(y)) for x, y in pts]
    d.line(p, fill=col(color, 255 * alpha), width=S(width), joint="curve")
    # ronde uiteinden
    r = S(width) / 2
    for (x, y) in (p[0], p[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=col(color, 255 * alpha))


def draw_disc(d, hx, hy, diam, color, icon=None, icon_color=None, g=None, glow_rgb=None):
    """Hotspot-schijf: donkere vulling + 2px rand in toestandskleur + optionele gloed + icoon."""
    if g:
        gi = radial_glow(g, glow_rgb or color, 0.5).resize((S(g), S(g)), Image.LANCZOS)
        d._image.paste(gi, (S(hx - g // 2), S(hy - g // 2)), gi)
    r = S(diam / 2)
    cx, cy = S(hx), S(hy)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col(INK, 214), outline=col(color, 255), width=S(2))
    if icon:
        ic = svg_paths(icon, round(diam * 0.6), icon_color or TXT_HERO, 4.2)
        s = ic.size[0]
        d._image.paste(ic, (int(cx - s / 2), int(cy - s / 2)), ic)


class Layer:
    """800x416 RGBA laag (control-coord); alles 4x supersampled."""
    def __init__(self, w=800, h=416):
        self.im = Image.new("RGBA", (S(w), S(h)), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.d._image = self.im

    def bubble(self, side, row, l1, l2, border_rgba, l1col=None, l2col=None, l1px=26, l2px=24):
        x, y = box_xy(side, row)
        c = border_rgba
        self.d.rounded_rectangle([S(x), S(y), S(x + COL_W) - 1, S(y + BOX_H) - 1], radius=S(R),
                                 fill=col(INK, 204), outline=c, width=S(2))
        f1 = font(l1px, True)
        f2 = font(l2px, False)
        self.d.text((S(x + PAD - 2), S(y + 4)), l1, font=f1, fill=col(l1col or TXT_HERO, 255))
        self.d.text((S(x + PAD - 2), S(y + 33)), l2, font=f2, fill=col(l2col or TXT_1, 255))

    def finish(self, name):
        return done(self.im, name, 800, 416)


# ------------------------------------------------------------------ 1. statusvakken (iStopStatusEngine/Battery/AC per klasse)
# Vakken (ONTWERP-B par.6): AC x 12..385 / y 1..111 (373x110), Motor x 12..385 / y 65..201 (373x136),
# Accu x 415..788 / y 65..201 (373x136). Per klasse (Glow = klaar, plain = blokkeert) 1 PNG met
# bubbel + label + toestandstekst + lijn + schijf (+ gloed) + icoon.
VAC = {  # key -> (x, y) van het OEM-vak; de PNG zelf is 800x416 (control-coord, zie status_vak)
    'ac': (0, 0),
    'engine': (0, 0),
    'batt': (0, 0),
}
LABEL = {'engine': 'Motor', 'batt': 'Accu', 'ac': 'Airco'}
GOOD_TXT = {'engine': 'Klaar', 'batt': 'Klaar', 'ac': 'Klaar'}
BAD_TXT = {'engine': 'Niet klaar', 'batt': 'Lading laag', 'ac': 'Vraagt motor'}


def status_vak(key, good):
    """Maak 1 PNG (800x416, control-coord) met bubbel+lijn+schijf in de juiste toestandskleur.
    Het OEM-vak (iStopStatusX) is 373x136 op (12,65) etc.; de PNG wordt als background op dat vak
    gezet met background-position om de bubbel/lijn/schijf op de rasterpositie te landen."""
    w, h = 800, 416
    side, row = SLOT[key]
    hx, hy = HOT[key]
    lay = Layer(w, h)

    ok = good
    line_c = OK_LINE if ok else WARN
    acc_c = OK_ACC if ok else WARN
    # bubbel (in vak-coord)
    bx, by = box_xy(side, row)
    lay.d.rounded_rectangle([S(bx), S(by), S(bx + COL_W) - 1, S(by + BOX_H) - 1],
                            radius=S(R), fill=col(INK, 204),
                            outline=col(line_c, 171 if ok else 255), width=S(2))
    f1 = font(26, True)
    f2 = font(24, False)
    lay.d.text((S(bx + PAD - 2), S(by + 4)), LABEL[key], font=f1, fill=col(TXT_HERO, 255))
    lay.d.text((S(bx + PAD - 2), S(by + 33)), GOOD_TXT[key] if ok else BAD_TXT[key],
               font=f2, fill=col(acc_c, 255))
    # leader-lijn (control-coord -> vak-coord)
    pts = leader_pts(side, row, hx, hy, DISC // 2)
    draw_leader(lay.d, pts, line_c)
    # schijf (+ amber gloed bij blokkeert)
    g = 110 if not ok else None
    if g:
        gi = radial_glow(g, WARN, 0.5).resize((S(g), S(g)), Image.LANCZOS)
        lay.im.paste(gi, (S(hx - g // 2), S(hy - g // 2)), gi)
    r = S(DISC / 2)
    cx, cy = S(hx), S(hy)
    lay.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col(INK, 214), outline=col(acc_c, 255), width=S(2))
    ic = svg_paths(key, 24, TXT_HERO, 4.2)
    lay.im.paste(ic, (int(cx - 12), int(cy - 12)), ic)
    suffix = "_Glow" if ok else ""
    return lay.finish("B2EcoIstop%s%s.png" % (LABEL[key] and {'engine': 'Engine', 'batt': 'Batt', 'ac': 'AC'}[key], suffix))


# ------------------------------------------------------------------ 2. GEREED-pil (iStopStatusText), CSS-only wit
def gereed_pil():
    """PNG-achtergrond voor de pil (260x52): donker vlak + witte rand 22%. Tekst zet OEM-JS (wit 30px SB)."""
    w, h = PILL['w'], PILL['h']
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S(w) - 1, S(h) - 1], radius=S(R), fill=col(INK, 204),
                        outline=col(WHITE, 56), width=S(2))
    return done(im, "B2EcoGereedPill.png", w, h)


# ------------------------------------------------------------------ 3. Gem. km/L kaart (fuelEfficiencyContainer 176x64 op 612,24)
def kpi_card():
    im = canvas(COL_W, BOX_H)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S(COL_W) - 1, S(BOX_H) - 1], radius=S(R), fill=col(INK, 204),
                        outline=col(WHITE, 41), width=S(2))
    f1 = font(20, False)
    # v1.4-r2: label zonder eenheid -- de eenheid komt uit OEM (span achter de waarde, volgt km/L of L/100km)
    d.text((S(PAD - 2), S(3)), "Gemiddeld", font=f1, fill=col(TXT_2, 255))
    return done(im, "B2EcoKpiCard.png", COL_W, BOX_H)


# ------------------------------------------------------------------ 4. Time-kaart (iStopTimeFrame 328x88; CSS positioneert hem absoluut op control (236,226))
def time_card():
    """328x88 kaart: MOTOR UIT (kicker, donkerrood accent) + scheidingslijn + Totaal (kicker).
    De WAARDEN zet OEM-JS in iStopTimeValue/TotalValue (absolute binnen de kaart, zie CSS par.5),
    dus de PNG bevat alleen de kaart + kickers. Alles binnen 328x88 -> geen overflow/clipping."""
    # v1.4-r2 FIX: was Layer(w,h).finish() -> die schaalt ALTIJD naar 800x416, dus de 328x88-kaart werd
    # 2,4x opgeblazen (reuze "MOTOR UIT" onder de kaartrand, afgekapt). Nu exact 328x88 via done().
    w, h = CARD['w'], 88
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S(w) - 1, S(h) - 1], radius=S(R), fill=col(INK, 224),
                        outline=col(OK_LINE, 255), width=S(2))
    # MOTOR UIT (20px SB, letterspacing, leesbaar rood-accent) -- kicker linksboven (ONTWERP-B par.5)
    fk = font(20, True)
    tx = S(PAD + 2)
    for ch in "MOTOR UIT":
        d.text((tx, S(8)), ch, font=fk, fill=col(TXT_OKRED, 255))
        tx += S(fk.getlength(ch) / SS + 1.4)
    assert tx / SS < 176 - 8, "MOTOR UIT past niet links van de scheidingslijn"
    # scheidingslijn op x 176 + "Totaal" (kicker rechts; waarden zet OEM-JS, CSS par.5)
    d.line([(S(176), S(12)), (S(176), S(h - 12))], fill=col(WHITE, 46), width=S(1))
    d.text((S(192), S(8)), "Totaal", font=font(20, False), fill=col(TXT_2, 255))
    return done(im, "B2EcoTimeCard.png", w, h)


# ------------------------------------------------------------------ 5. Error-kaart kop (iStopErrorText 328x88, CSS absoluut op control (236,226))
def error_head():
    """Volledige 328x88 error-kaart als achtergrond-PNG (kaart + kop). CSS zet de kaart absoluut op
    control (236,226) met vaste hoogte 88 (onderrand 314 = rij 3) en overflow:hidden, dus de kaart is
    altijd binnen het scherm zichtbaar (defect p5-error: kaart was onzichtbaar). Line1/Line2 zet
    OEM-JS als absolute children binnen de kaart."""
    # v1.4-r2: alleen de KOP (driehoek + tekst, transparant) -- kaartvlak/amber rand/radius tekent de CSS, zodat
    # de kaart 112 hoog kan zijn (Line2 = conditie in max. 2 regels, ONTWERP-B par.5) zonder uitgerekte PNG.
    w, h = CARD['w'] - 4, 36
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    tri = svg_paths('warnTri', 22, WARN, 4.4)
    im.paste(tri, (S(PAD - 2), S(8)), tri)
    fk = font(18, True)
    txt = "I-STOP NIET ACTIEF"
    tx = S(PAD + 30)
    for ch in txt:
        d.text((tx, S(9)), ch, font=fk, fill=col(WARN, 255))
        tx += S(fk.getlength(ch) / SS + 1.6)
    return done(im, "B2EcoErrorHead.png", w, h)


# ------------------------------------------------------------------ 6. motorgloed (iEloopEngineGlow, Time-modus): donkerrood
def engine_glow():
    return done(radial_glow(280, OK_ACC, 0.5).resize((280, 280), Image.LANCZOS), "B2EcoGlowOk.png", 280, 280)


def warn_glow():
    return done(radial_glow(150, WARN, 0.6).resize((150, 150), Image.LANCZOS), "B2EcoGlowWarn.png", 150, 150)


# ------------------------------------------------------------------ 7. TPMS-bandenbubbels (JS-divs B2EcoTpmsL/R; indirect TPMS, geen bar)
TPMS_TXT = {'ok': "OK", 'low': "Druk laag", 'fault': "TPMS-storing"}
TPMS_MIN_MARGIN = 12


def tpms_text_fits(l2):
    """Eist dat label (24px SB) en toestand (22px) binnen de bubbel passen met >= TPMS_MIN_MARGIN rechts."""
    room = COL_W - (PAD - 2)
    for txt, f in (("Banden", font(24, True)), (l2, font(22, False))):
        wpx = f.getlength(txt) / SS
        assert room - wpx >= TPMS_MIN_MARGIN, "TPMS-tekst %r is %.0f px, marge %.0f < %d" % (txt, wpx, room - wpx, TPMS_MIN_MARGIN)


def tpms_bubble(side, mode):
    """mode: ok | low | fault. Bubbel 176x64 op rij 3 + korte leader + band-schijf (34px).
    Tekst: regel 1 = 'Banden' (label), regel 2 = toestand. low = amber + pulserende gloed (PNG-wissel),
    fault = amber zonder puls, ok = rood-accent.
    DEFECT-FIX (bandenbubbels): de bubbel is nu 176x72 (BOX_H_TIRE) zodat de langste tekst
    "Bandendruk laag" (24px) RUIM binnen de bubbel past (was 64px hoog -> tekst liep tegen de rand)."""
    k = 'tireL' if side == 'L' else 'tireR'
    _, row = SLOT[k]
    hx, hy = HOT[k]
    lay = Layer(800, 416)
    bh = BOX_H_TIRE                      # 72: extra ruimte voor de tekstregel
    by = ROWS[row] - bh // 2             # bubbel gecentreerd op de rij-lijn
    # v1.4-r2 FIX: "Bandendruk laag" (22px) was 166 px breed in een 176-bubbel met 12 px padding -> liep
    # tegen/over de rand. Nu 2 regels: label "Banden" + toestand "Druk laag"/"OK"/"TPMS-storing" (22px);
    # tpms_text_fits() eist >= 12 px vrije marge rechts binnen de bubbel.
    if mode == 'ok':
        line_c, acc_c = OK_LINE, OK_ACC
        l2 = TPMS_TXT['ok']
        g = None
    elif mode == 'low':
        line_c, acc_c = WARN, WARN
        l2 = TPMS_TXT['low']
        g = 80
    else:  # fault
        line_c, acc_c = WARN, WARN
        l2 = TPMS_TXT['fault']
        g = None
    tpms_text_fits(l2)
    bx = COL_L if side == 'L' else COL_R
    lay.d.rounded_rectangle([S(bx), S(by), S(bx + COL_W) - 1, S(by + bh) - 1], radius=S(R),
                            fill=col(INK, 204), outline=col(line_c, 171 if mode == 'ok' else 255), width=S(2))
    f1 = font(24, True)
    f2 = font(22, False)
    lay.d.text((S(bx + PAD - 2), S(by + 6)), "Banden", font=f1, fill=col(TXT_HERO, 255))
    lay.d.text((S(bx + PAD - 2), S(by + 36)), l2, font=f2, fill=col(acc_c, 255))
    pts = leader_pts(side, row, hx, hy, DISC_TIRE // 2)
    draw_leader(lay.d, pts, line_c)
    if g and mode == 'low':
        gi = radial_glow(g, WARN, 0.5).resize((S(g), S(g)), Image.LANCZOS)
        lay.im.paste(gi, (S(hx - g // 2), S(hy - g // 2)), gi)
    r = S(DISC_TIRE / 2)
    cx, cy = S(hx), S(hy)
    lay.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col(INK, 214), outline=col(acc_c, 255), width=S(2))
    ic = svg_paths('tire', round(DISC_TIRE * 0.6), TXT_HERO, 4.2)
    s = ic.size[0]
    lay.im.paste(ic, (int(cx - s / 2), int(cy - s / 2)), ic)
    return lay.finish("B2EcoTpms%s_%s.png" % (side, {'ok': 'Ok', 'low': 'Low', 'fault': 'Fault'}[mode]))


def tpms_pulse(side):
    """Puls-variant van 'low': zelfde bubbel/lijn (176x72), fellere amber gloed (peak 0.75) -- de JS
    wisselt Low <-> LowPulse voor het pulserende effect."""
    k = 'tireL' if side == 'L' else 'tireR'
    _, row = SLOT[k]
    hx, hy = HOT[k]
    lay = Layer(800, 416)
    bh = BOX_H_TIRE
    by = ROWS[row] - bh // 2
    bx = COL_L if side == 'L' else COL_R
    lay.d.rounded_rectangle([S(bx), S(by), S(bx + COL_W) - 1, S(by + bh) - 1], radius=S(R),
                            fill=col(INK, 204), outline=col(WARN, 255), width=S(2))
    f1 = font(24, True)
    f2 = font(22, False)
    lay.d.text((S(bx + PAD - 2), S(by + 6)), "Banden", font=f1, fill=col(TXT_HERO, 255))
    lay.d.text((S(bx + PAD - 2), S(by + 36)), TPMS_TXT['low'], font=f2, fill=col(WARN, 255))
    pts = leader_pts(side, row, hx, hy, DISC_TIRE // 2)
    draw_leader(lay.d, pts, WARN)
    g = 110
    gi = radial_glow(g, WARN, 0.75).resize((S(g), S(g)), Image.LANCZOS)
    lay.im.paste(gi, (S(hx - g // 2), S(hy - g // 2)), gi)
    r = S(DISC_TIRE / 2)
    cx, cy = S(hx), S(hy)
    lay.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col(INK, 240), outline=col(WARN, 255), width=S(2))
    ic = svg_paths('tire', round(DISC_TIRE * 0.6), TXT_HERO, 4.2)
    s = ic.size[0]
    lay.im.paste(ic, (int(cx - s / 2), int(cy - s / 2)), ic)
    return lay.finish("B2EcoTpms%s_LowPulse.png" % side)


# ------------------------------------------------------------------ 8. Brandstofverbruik: rode staven (de gebruiker-wijziging)
def fuel_bars():
    """Vervangt de OEM-staaf-PNG's (maten uit ASSETS.txt: narrow 21x106, wide 44x106, cap 21x2/44x2).
    Huidige/beste staaf = helder rood #E8323C, zuinige staven = donkerrood #B0202C, rest = grijs.
    JS zet alleen height (repeat-y) -> PNG is 1 kolom breed en wordt uitgerekt."""
    out = []
    # narrow (CDFE, 21x106)
    for name, c in (("B2EcoBarNarrow.png", BAR_DIM), ("B2EcoBarNarrow_Current.png", BAR_CUR),
                    ("B2EcoBarNarrow_Green.png", BAR_OK), ("B2EcoBarNarrow_GreenCurrent.png", BAR_CUR)):
        im = canvas(21, 106)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, S(21) - 1, S(106) - 1], radius=S(4), fill=col(c, 255))
        out.append(done(im, name, 21, 106))
    # wide (CFER, 44x106)
    for name, c in (("B2EcoBarWide.png", BAR_DIM), ("B2EcoBarWide_Current.png", BAR_CUR),
                    ("B2EcoBarWide_Green.png", BAR_OK), ("B2EcoBarWide_GreenCurrent.png", BAR_CUR)):
        im = canvas(44, 106)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, S(44) - 1, S(106) - 1], radius=S(4), fill=col(c, 255))
        out.append(done(im, name, 44, 106))
    # caps
    for name, w in (("B2EcoBarCapNarrow.png", 21), ("B2EcoBarCapWide.png", 44)):
        im = canvas(w, 2)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, S(w) - 1, S(2) - 1], fill=col(BAR_CAP, 255))
        out.append(done(im, name, w, 2))
    return out


# ------------------------------------------------------------------ 9. Effectiviteit: B2-kaartstijl + bomen eco-groen
def effect_bg():
    """B2-achtergrond voor .EcoEffectCtrl (780x421): donker B2-vlak zoals de andere B2-schermen,
    zodat het Effectiviteit-scherm consistent in de optie-B-lijn staat (defect p5-tree-3)."""
    # v1.4-r2: de B2-KAARTEN (optie B, E-effectiviteit-B.png) zitten IN deze achtergrond, precies achter de
    # OEM-tekstvakken (die verhuizen NIET: H1/hitboxes + canvas blijven OEM). Coord = pagina - (10, 64).
    w, h = 780, 421
    im = Image.new("RGBA", (S(w), S(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, S(w) - 1, S(h) - 1], fill=col(INK, 235))
    d.line([(0, 0), (S(w) - 1, 0)], fill=col(WHITE, 26), width=S(1))
    for name, (x0, y0, x1, y1) in EFFECT_CARDS.items():
        bx0, by0, bx1, by1 = x0 - 10, y0 - 64, x1 - 10, y1 - 64
        d.rounded_rectangle([S(bx0), S(by0), S(bx1) - 1, S(by1) - 1], radius=S(R), fill=col((20, 23, 28), 235),
                            outline=col(WHITE, 52), width=S(2))
        if name == 'times':   # scheidingslijn tussen "i-stop ON" en "Gestopt"
            ym = (EFFECT_DIVIDER_Y - 64)
            d.line([(S(bx0 + 14), S(ym)), (S(bx1 - 14), S(ym))], fill=col(WHITE, 36), width=S(1))
    return done(im, "B2EcoEffectBg.png", w, h)


# Effectiviteit-kaarten in PAGINA-coord (x0, y0, x1, y1), om de OEM-vakken heen gemeten in de v74-GUI:
#   canvas 174..297 x 124..272, %-badge 260..284 x 189..215 ; labels x 334, waarden 519..729 y 146..191 / 201..246 ;
#   'Gestimuleerd door i-stop' 516..746 x 314..384, waarde 515..745 x 386..431.
EFFECT_CARDS = {
    'meter': (150, 118, 314, 282),
    'times': (322, 136, 784, 266),
    'boost': (504, 304, 784, 440),
}
EFFECT_DIVIDER_Y = 197


def meter_card():
    """B2-kaart-rand voor de percent-meter (canvas 123x148 op control 164,60): donker vlak + witte
    haarlijn, consistent met de B2-kaartstijl (KPI-kaart/Time-kaart)."""
    w, h = 123, 148
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    # v1.4-r2: transparant -- de meter-kaart zit nu (groter, om canvas + %-badge heen) in B2EcoEffectBg.png
    return done(im, "B2EcoMeterCard.png", w, h)


def percent_badge():
    """B2-stijl '%'-badge voor .percentDiv (24x26): wit %-teken op donker vlak (was OEM PNG)."""
    w, h = 24, 26
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    f = font(20, True)
    d.text((S(4), S(2)), "%", font=f, fill=col(TXT_HERO, 255))
    return done(im, "B2EcoPercent.png", w, h)


def tree_bg():
    """B2-stijl achtergrond voor de kleine boom (treeBackground 148x85): donker vlak + haarlijn."""
    w, h = 148, 85
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S(w) - 1, S(h) - 1], radius=S(R), fill=col((20, 23, 28), 235),
                        outline=col(ECO, 190), width=S(2))     # v1.4-r2: eco-groene rand (boom-kaart, optie B)
    return done(im, "B2EcoTreeBg.png", w, h)


def trees():
    """OEM Tree_01 91x98 / Tree_02 125x135 / Tree_03 92x144 / Tree_03_sm 50x75; eco-groen (de gebruiker: 'snap ik bij eco')."""
    def tree(w, h, leaves):
        im = canvas(w, h)
        d = ImageDraw.Draw(im)
        c = col(ECO, 255)
        lw = S(3.4)
        cx = w / 2
        d.line([(S(cx), S(h * 0.95)), (S(cx), S(h * 0.45))], fill=c, width=lw)
        # bladeren: ellipsen rond de top
        for i in range(leaves):
            ang = -90 + (i - (leaves - 1) / 2) * 55
            rad = math.radians(ang)
            lx = cx + math.cos(rad) * w * 0.26
            ly = h * 0.38 + math.sin(rad) * h * 0.22
            d.ellipse([S(lx - w * 0.16), S(ly - h * 0.13), S(lx + w * 0.16), S(ly + h * 0.13)],
                      outline=c, width=lw)
        return done(im, name, w, h)

    name = "B2EcoTree_01.png"
    tree(91, 98, 2)
    name = "B2EcoTree_02.png"
    tree(125, 135, 3)
    name = "B2EcoTree_03.png"
    tree(92, 144, 3)
    name = "B2EcoTree_03_sm.png"
    tree(50, 75, 2)
    return ["B2EcoTree_01.png", "B2EcoTree_02.png", "B2EcoTree_03.png", "B2EcoTree_03_sm.png"]


# ------------------------------------------------------------------ 10. foto-achtergrond (JPEG 800x416)
def car_photo():
    """Kopieer de gebakken foto uit optieB/assets (bake_optieB.py, foto ref/eco-car-front-logo-v1.jpg,
    JPEG q84 800x416 = .EcoStatusCtrl_iEloop_Container). Nooit groter dan het scherm aanleveren."""
    src = os.path.join(OPTIEB, "assets", "B2EcoCarPhoto_B.jpg")
    im = Image.open(src).convert("RGB")
    assert im.size == (800, 416), im.size
    dst = os.path.join(OUT, "B2EcoCarPhoto_B.jpg")
    im.save(dst, quality=84, optimize=True, progressive=False)
    return "B2EcoCarPhoto_B.jpg", os.path.getsize(dst)


# ------------------------------------------------------------------ main
def main():
    made = []
    # 1. statusvakken (6 PNG's: 3 elementen x Glow/plain)
    for key in ('ac', 'engine', 'batt'):
        made.append(status_vak(key, True))
        made.append(status_vak(key, False))
    # 2. GEREED-pil + KPI-kaart
    made.append(gereed_pil())
    made.append(kpi_card())
    # 4/5. Time-kaart + Error-kop
    made.append(time_card())
    made.append(error_head())
    # 6. gloed (motor-uit = donkerrood)
    made.append(engine_glow())
    made.append(warn_glow())
    # 7. TPMS (3 toestanden x 2 kanten + puls-variant van 'low' voor het pulseren)
    for side in ('L', 'R'):
        for mode in ('ok', 'low', 'fault'):
            made.append(tpms_bubble(side, mode))
    made.append(tpms_pulse('L'))
    made.append(tpms_pulse('R'))
    # 8. brandstof-staven (rood)
    made += fuel_bars()
    # 9. Effectiviteit: B2-kaartstijl + bomen (eco-groen)
    made.append(effect_bg())
    made.append(meter_card())
    made.append(percent_badge())
    made.append(tree_bg())
    made += trees()
    # 10. foto
    name, nbytes = car_photo()
    made.append(name)
    print("P5-eco assets geschreven naar %s:" % OUT)
    for m in made:
        p = os.path.join(OUT, m)
        print("  %-28s %s" % (m, ("%d bytes" % os.path.getsize(p)) if os.path.isfile(p) else "MISSING"))
    print("%d bestanden (%s = %d bytes)" % (len(made), name, nbytes))


if __name__ == "__main__":
    main()
