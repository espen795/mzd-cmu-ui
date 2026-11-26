#!/usr/bin/env python3
"""p4_media.py -- genereert ALLEEN de P4 "media & invoer" B2Sub-assets (BOUWPLAN.md P4):
  B2ArtFrame.png (146x146, OEM NowPlaying4CtrlArtworkImageBorder-maat),
  B2UmpBtn_Focus.png (114x84 gecentreerd, werkt voor elke Ump3CtrlNButton_*),
  B2UmpScrubTrack/B2UmpScrubFill (Ump-scrubber track/vulling, eigen P4-kopie, NIET P2's PNG's),
  B2DialKey_{En,Focus,Hit,Green}.png (126x79, OEM .DialPad2Ctrl .btn-maat),
  B2Key{w}x{h}_{En,Focus,Hit,Green}.png per toetsmaat uit KeyboardCtrl.css (per layout:
    fiveTen 74x91 / sixTen 75x68 / sixTwelve 62x68 / suggFiveTen 75x71 / suggSevenTen 75x46 /
    suggSevenEleven 68x46; controls: fiveTen/sixTen/sixTwelve/suggFiveTen #btnShift 112/113/94/108 x 91/68/68/70,
    #btnCancel/#btnOK 93x65, #btnSpacebar 511x64 (suggSeven* 460x46), #btnGlobe 62x64 (suggSeven* 75x46),
    #btnMod 75x46, delete 75x59 -> eigen B2Key{w}x{h}_* set per maat).

Gebruik (vanaf ui-oemplus-inject-v1.3/):  python3 tools/assets/p4_media.py
Output: overlay-src/common/oemplusb2/images/  (op de CMU: jci/gui/common/oemplusb2/images/)
Eigenaarschap (BOUWPLAN): alleen P4 schrijft deze PNG's (prefix B2ArtFrame/B2Ump*/B2DialKey_*/B2Key*);
P0/P1/P2/P3-PNG's worden niet overschreven.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from _lib import OUT, SS, RED, WHITE, LIGHT, GREY, canvas, done, red_bar, key


def artframe():
    """B2ArtFrame.png 146x146: dunne afgeronde rand (wit 16%) als vervanging van NowPlayingImageFrame.png."""
    w = h = 146
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([1 * SS, 1 * SS, (w - 1) * SS, (h - 1) * SS], radius=12 * SS, outline=WHITE + (40,), width=SS)
    return done(im, "B2ArtFrame.png", w, h)


def ump_btn_focus():
    """B2UmpBtn_Focus.png 114x84: focusvlak wit 16% + Soul-Red bar onder (werkt gecentreerd op elke Ump3CtrlNButton_*)."""
    w, h = 114, 84
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8 * SS, 6 * SS, (w - 8) * SS, (h - 6) * SS], radius=12 * SS, fill=WHITE + (41,))
    im = Image.alpha_composite(im, red_bar(w, h, w // 2 - 24, h - 10, 48, 3, vertical=False))
    return done(im, "B2UmpBtn_Focus.png", w, h)


def ump_scrub():
    """B2UmpScrubTrack/Fill: Ump3-scrubber (UmpScrubberStyle01..06 track 12px, fill 8px) in B2-stijl.
    Eigen P4-kopie (BOUWPLAN P4: niet P2's B2Progress* delen). Track = 12px hoog donker vlak met
    haarlijn; fill = 8px LIGHT balk. repeat-x in CSS (width staat via JS inline)."""
    for w, h, name, col in ((582, 12, "B2UmpScrubTrack.png", None), (582, 8, "B2UmpScrubFill.png", LIGHT)):
        im = canvas(w, h)
        d = ImageDraw.Draw(im)
        if col is None:
            d.rounded_rectangle([0, 2 * SS, w * SS - 1, h * SS - 1], radius=4 * SS, fill=WHITE + (22,))
            d.line([(0, 2 * SS), (w * SS - 1, 2 * SS)], fill=WHITE + (60,), width=SS)
        else:
            d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=4 * SS, fill=col + (255,))
        done(im, name, w, h)


def dialkey():
    """B2DialKey_{En,Focus,Hit,Green}.png 126x79 (OEM .DialPad2Ctrl .btn). Green = bel-toets (callBtn)."""
    for s in ("En", "Focus", "Hit", "Green"):
        key(126, 79, s, "B2DialKey_%s.png" % s, inset=(5, 5), radius=10, bar_w=44)


# toetsmaten uit common/controls/Keyboard/css/KeyboardCtrl.css (v74): layout -> (btn w x h)
KEY_LAYOUTS = {
    "fiveTen": (74, 91), "sixTen": (75, 68), "sixTwelve": (62, 68),
    "suggFiveTen": (75, 71), "suggSevenTen": (75, 46), "suggSevenEleven": (68, 46),
}
# controlsWrapper #id-maten per layout (uit KeyboardCtrl.css)
CTRL_LAYOUTS = {
    "fiveTen":        {"btnShift": (112, 91), "btnLayoutSwitch": (112, 91), "btnCancel": (93, 65),
                       "btnOK": (93, 65), "btnSpacebar": (511, 64), "btnGlobe": (62, 64), "btnMod": (75, 46)},
    "sixTen":         {"btnShift": (113, 68), "btnLayoutSwitch": (113, 68), "btnCancel": (93, 65),
                       "btnOK": (93, 65), "btnSpacebar": (511, 64), "btnGlobe": (62, 64), "btnMod": (75, 46)},
    "sixTwelve":      {"btnShift": (94, 68), "btnLayoutSwitch": (94, 68), "btnCancel": (93, 65),
                       "btnOK": (93, 65), "btnSpacebar": (511, 64), "btnGlobe": (62, 64), "btnMod": (75, 46)},
    "suggFiveTen":    {"btnShift": (108, 70), "btnLayoutSwitch": (108, 70), "btnCancel": (93, 65),
                       "btnOK": (93, 65), "btnSpacebar": (511, 64), "btnGlobe": (62, 64), "btnMod": (75, 46)},
    "suggSevenTen":   {"btnShift": (75, 46), "btnLayoutSwitch": (75, 46), "btnCancel": (75, 46),
                       "btnOK": (75, 46), "btnSpacebar": (460, 46), "btnGlobe": (75, 46), "btnMod": (75, 46)},
    "suggSevenEleven": {"btnShift": (75, 46), "btnLayoutSwitch": (75, 46), "btnCancel": (75, 46),
                        "btnOK": (75, 46), "btnSpacebar": (460, 46), "btnGlobe": (75, 46), "btnMod": (75, 46)},
}
DELETE_BTN = (75, 59)  # KeyboardCtrlDeleteBtn_{En,Ds,Fs,Dwn,Hd}


def keyboard():
    """B2Key{w}x{h}_{En,Focus,Hit,Green}.png per unieke toetsmaat (layouts + controls + delete)."""
    sizes = set()
    for lay, (w, h) in KEY_LAYOUTS.items():
        sizes.add((w, h))
    for lay, ctrls in CTRL_LAYOUTS.items():
        for bid, (w, h) in ctrls.items():
            sizes.add((w, h))
    sizes.add(DELETE_BTN)
    for (w, h) in sorted(sizes):
        inset = (3, 4) if h <= 70 else (4, 5)
        radius = 8 if h <= 70 else 9
        bar_w = max(20, int(w * 0.4))
        for s in ("En", "Focus", "Hit"):
            key(w, h, s, "B2Key%dx%d_%s.png" % (w, h, s), inset=inset, radius=radius, bar_w=bar_w)
        # Green = primaire omlijning (OK-knop) -- alleen voor de OK-maat (93x65) en bel-achtige toetsen
        if (w, h) == (93, 65):
            key(w, h, "Green", "B2Key%dx%d_Green.png" % (w, h), inset=inset, radius=radius)


def main():
    artframe()
    ump_btn_focus()
    ump_scrub()
    dialkey()
    keyboard()
    print("p4_media ->", OUT, "(B2ArtFrame, B2UmpBtn_Focus, B2UmpScrub*, B2DialKey_*, B2Key*)")


if __name__ == "__main__":
    main()
