#!/usr/bin/env python3
"""p2_dialog3.py -- genereert ALLEEN de P2 "Dialog3" B2Sub-assets (BOUWPLAN.md P2):
  B2DialogBg.png (800x416), B2DialogBgFs.png (800x480), B2DialogTitleSep.png (664x1),
  B2DlgBtn{1..4}_{En,Focus,Hit,Red,Green}.png (exact OEM-elementmaat 662/330/220/165 x 80, transparante marge),
  B2Indeterminate_0{1,2,3}.png (112x112, statische frames van de OEM-APNG),
  B2ProgressTrack.png (642x12 = OEM Dialog_ProgressBar_Background), B2ProgressFill.png (repeat-x),
  B2PinField.png (495x91 = OEM PinEntryBkg maat).

Gebruik (vanaf ui-oemplus-inject-v1.3/):  python3 tools/assets/p2_dialog3.py
Output: overlay-src/common/oemplusb2/images/  (op de CMU: jci/gui/common/oemplusb2/images/)
Eigenaarschap (BOUWPLAN): alleen P2 schrijft deze PNG's; P0/P1/P3/P4 niet overschrijven.
Bron van maten: v74 common/controls/Dialog3/images/*.png (hitbox-invariant, DESIGN-SYSTEEM par.0.2).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from _lib import OUT, SS, RED, WHITE, LIGHT, INK, canvas, done, red_bar


def dialog_bg():
    """B2DialogBg.png 800x416: paneel x 70-730, y 10-406, radius 16.
     * v1.4 (live 27-11 v13-sysinfo.png): de oude PNG had een paneel van wit alpha 10 -> de dialoog-achtergrond
     * liet de ONDERLIGGENDE lijst doorschijnen (tekst "OS-versie..." liep over "Overeenkomsten en rechten").
     * Fix: dekkend donker vlak (bg #030405, alpha 255) over het hele 800x416, met het lichtere paneel
     * (wit 10% + rand 26%) erbovenop -- net als OEM DialogBG_Style01 (alpha 247 in het midden) maar dan
     * echt dekkend. Buiten het paneel blijft de PNG transparant zodat de hoeken van het scherm de
     * B2-achtergrond (B2SubBg) tonen. Fullscreen-variant idem binnen y 74..470."""
    w, h = 800, 416
    im = canvas(w, h); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w * SS - 1, h * SS - 1], fill=(3, 4, 5, 255))          # dekkend scrim
    box = [70 * SS, 10 * SS, 730 * SS, 406 * SS]
    d.rounded_rectangle(box, radius=16 * SS, fill=(255, 255, 255, 10))
    d.rounded_rectangle(box, radius=16 * SS, outline=(255, 255, 255, 26), width=SS)
    done(im, "B2DialogBg.png", w, h)
    # fullscreen-variant (Dialog3CtrlFs / .TemplateFull, 800x480): paneel binnen y 74..470 (64 px banner vrij)
    w, h = 800, 480
    im = canvas(w, h); d = ImageDraw.Draw(im)
    d.rectangle([0, 64 * SS, w * SS - 1, h * SS - 1], fill=(3, 4, 5, 255))      # dekkend onder de banner
    box = [70 * SS, 74 * SS, 730 * SS, 470 * SS]
    d.rounded_rectangle(box, radius=16 * SS, fill=(255, 255, 255, 10))
    d.rounded_rectangle(box, radius=16 * SS, outline=(255, 255, 255, 26), width=SS)
    done(im, "B2DialogBgFs.png", w, h)
    # titel-scheiding 664x1 (titel-breedte binnen het paneel; fade aan beide kanten, wit 14%)
    sep = Image.new("RGBA", (664, 1), (0, 0, 0, 0)); p = sep.load()
    for x in range(664):
        t = x / 663.0
        a = 0.14 * min(1.0, t / 0.15, (1.0 - t) / 0.15)
        p[x, 0] = (255, 255, 255, int(255 * a))
    sep.save(os.path.join(OUT, "B2DialogTitleSep.png"), optimize=True)


def dlg_btn(n, w, state):
    """Dialog-knop PNG op EXACT de OEM-elementmaat (hitbox gelijk, H1): 1=662, 2=330, 3=220, 4=165 breed x 80.
    Zichtbaar vlak iets kleiner (transparante marge 5x6), radius 10. States: En/Focus/Hit/Red/Green.
    Focus/Hit krijgen een Soul-Red bar onder (40% van de knopbreedte, DESIGN-SYSTEEM par.5)."""
    h = 80
    name = "B2DlgBtn%d_%s.png" % (n, state)
    im = canvas(w, h); d = ImageDraw.Draw(im)
    ix, iy = 5 * SS, 6 * SS
    box = [ix, iy, (w - 5) * SS - 1, (h - 6) * SS - 1]
    r = 10 * SS
    if state == "En":
        d.rounded_rectangle(box, radius=r, fill=WHITE + (20,))
        d.rounded_rectangle(box, radius=r, outline=WHITE + (38,), width=SS)
    elif state == "Focus":
        d.rounded_rectangle(box, radius=r, fill=WHITE + (41,))
        d.rounded_rectangle(box, radius=r, outline=WHITE + (80,), width=SS)
        bw = min(72, int((w - 10) * 0.4)) * SS
        bx = (w * SS - bw) // 2
        by = (h - 6) * SS - 4 * SS
        d.rounded_rectangle([bx, by, bx + bw - 1, by + 3 * SS - 1], radius=SS, fill=RED + (255,))
    elif state == "Hit":
        d.rounded_rectangle(box, radius=r, fill=WHITE + (68,))
        d.rounded_rectangle(box, radius=r, outline=WHITE + (90,), width=SS)
    elif state == "Red":
        # destructief: Soul-Red vlak (DESIGN-SYSTEEM par.2: rood = onomkeerbaar)
        d.rounded_rectangle(box, radius=r, fill=RED + (255,))
    elif state == "Green":
        # primair: GEEN vulling, alleen 2px lichte omlijning (focus blijft het opvallendst)
        d.rounded_rectangle(box, radius=r, outline=LIGHT + (215,), width=2 * SS)
    return done(im, name, w, h)


def indeterminate():
    """B2Indeterminate_0{1,2,3}.png 112x112: 3 punten; frame i = punt i fel (OEM-APNG had 12 frames,
    Presto speelt APNG niet af in een div-background -> statische 3 frames zoals het prototype)."""
    for i in range(3):
        w = h = 112
        m = canvas(w, h); d = ImageDraw.Draw(m)
        for j in range(3):
            a = 255 if j == i else 70
            cx = 32 + j * 24
            d.ellipse([(cx - 6) * SS, 50 * SS, (cx + 6) * SS, 62 * SS], fill=LIGHT + (a,))
        done(m, "B2Indeterminate_0%d.png" % (i + 1), w, h)


def progress():
    """B2ProgressTrack.png 642x12 (OEM Dialog_ProgressBar_Background maat) + B2ProgressFill.png 8x12 repeat-x.
    De highlight-breedte zet Dialog3Ctrl.js inline (style.width) -> alleen het beeld wijzigt (H1 veilig)."""
    w, h = 642, 12
    t = canvas(w, h); d = ImageDraw.Draw(t)
    d.rounded_rectangle([0, 4 * SS, w * SS - 1, 8 * SS - 1], radius=2 * SS, fill=(255, 255, 255, 46))
    done(t, "B2ProgressTrack.png", w, h)
    f = Image.new("RGBA", (8, 12), (0, 0, 0, 0)); p = f.load()
    for x in range(8):
        for y in (4, 5, 6, 7):
            p[x, y] = LIGHT + (255,)
    f.save(os.path.join(OUT, "B2ProgressFill.png"), optimize=True)


def pin_field():
    """B2PinField.png 495x91 (OEM PinEntryBkg maat): 4 vakken wit 6% + 1px rand, radius 8, 55x55 gat per PIN-veld."""
    w, h = 495, 91
    im = canvas(w, h); d = ImageDraw.Draw(im)
    # 4 pin-vakken zoals OEM (Pin1..4 op left 110/234/355/484 binnen Style16, image1 op left 75 -> relatief)
    xs = [35, 159, 280, 409]  # 110-75, 234-75, 355-75, 484-75
    for x in xs:
        box = [x * SS, 18 * SS, (x + 55) * SS - 1, 73 * SS - 1]
        d.rounded_rectangle(box, radius=8 * SS, fill=(255, 255, 255, 15))
        d.rounded_rectangle(box, radius=8 * SS, outline=(255, 255, 255, 38), width=SS)
    return done(im, "B2PinField.png", w, h)


def main():
    dialog_bg()
    for n, w in ((1, 662), (2, 330), (3, 220), (4, 165)):
        for st in ("En", "Focus", "Hit", "Red", "Green"):
            dlg_btn(n, w, st)
    indeterminate()
    progress()
    pin_field()
    print("p2_dialog3 ->", OUT,
          "(B2DialogBg{,Fs}, B2DialogTitleSep, B2DlgBtn1-4_*, B2Indeterminate_01-03, B2Progress{Track,Fill}, B2PinField)")


if __name__ == "__main__":
    main()
