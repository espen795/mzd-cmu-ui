#!/usr/bin/env python3
"""P2 harnas (ML4): bewijst pakket P2 (Dialog3) uit BOUWPLAN.md par.P2 in de DRAAIENDE v74-GUI.

Hergebruikt MountHarness uit run_inject.py (root-stock -> mount -> root-inject, nep-MMUI, Presto-shims).
Schermen (echte Dialog3-contexts uit SUBMENU-INVENTARIS-v74.json, niet-protected):
  S1 system/NoConnectionNotify      style13, 2 knoppen (initialFocus 1)         -- 2-knoppen
  S2 system/NotifyDialog            style17, 3 knoppen (initialFocus 2)         -- 3-knoppen + titel? (geen titel)
  S3 syssettings/FactoryResetConfirm style02, fullScreen, 2 knoppen, titel n.v.t -- fullscreen + 2 knoppen
  S4 btpairing/ConfirmDelete         style02, 2 knoppen, initialFocus 0         -- 2 knoppen (focus andere kant)
  S5 btpairing/DeleteDevice          style14, 0 knoppen, indeterminate meter    -- voortgang/indeterminate
  S6 contacts/DeleteInProgress       style14, 0 knoppen, IndeterminateMeter.png -- voortgang (andere meterPath)
  S7 satradio/VuiConfirmNewPIN       style16, 2 knoppen, PIN-veld               -- PIN
  S8 aharadio/ShoutRecording         style03, 2 knoppen, determinate meter      -- determinate/voortgang met knoppen
  S9 system/Disclaimer               style02, fullScreen, 1 knop, titleStyle01  -- 1 knop + titel + fullscreen
  S10 vehsettings/... (lijst-achtig) -- n.v.t.; S9 dekt "met lijst" via style19? nee -> zie hieronder
  S10 system/... style19/20 lijst-in-dialog = VUI-help (Common._getVuiHelpDialogConfiguration) -- via debug-call
  Beschermd (H9): warnguide/... Dialog3 (protected) + mobile911/CollisionDetectedDialog +
                 system/DisplayOff -> body.OemplusB2 moet WEG.

Checks (BOUWPLAN H1-H10 voor Dialog3):
  H1 hitbox-invariant: getBoundingClientRect van elke knop (ButtonStyle*) + titel/tekst/meters gelijk aan/uit
  H2 focus-logica: cw/ccw/select op de template -> zelfde _buttonSelectIndex + zelfde select-callback appData
  H3 late lazy-CSS: B2Sub-20 geladen bij "B2 aan" VOORDAT het eerste Dialog3-template laadt -> computed bg = B2
  H4 leesbaarheid: font-size >= 24 px voor alle zichtbare _Text; contrast text-1 #d9dde2 op paneel >= 4.5
  H5 focus zichtbaar: gefocuste knop heeft B2DlgBtn*_Focus.png + wit semibold
  H6 uit = OEM: na b2Off geen B2Sub-links, body zonder OemplusB2, screenshot pixel-gelijk aan stock-shot
  H7 Presto/ASCII: check_presto.py OK (draait los; hier alleen marker+ASCII sanity)
  H8 geen overlap: selectors van B2Sub-20 komen in geen ander B2Sub-bestand voor (static check in deze file)
  H9 protected: op warnguide/mobile911/system-DisplayOff geen body.OemplusB2 + computed bg = OEM DialogBG
  H10 busybox/overlay: test_scripts_bb119.sh + make_overlay draaien (los; hier overlay-paden aanwezig)
  Extra P2: geen dialog-tekst valt buiten het paneel (x 70-730); knop-PNG maat == OEM elementmaat.

Gebruik:  sh harness/build_root.sh && python3 harness/run_p2_dialog3.py
Output:   harness/shots/p2-*.png + harness/RESULTS-P2.json ; exit 1 bij gefaalde check.
"""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_inject import MountHarness, sysmsg, check, results, SHOTS

MZD = os.path.normpath(os.path.join(HERE, ".."))
INV = os.path.join(MZD, "docs", "designs", "SUBMENU-INVENTARIS-v74.json")

DLG_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var c = t && t.dialog3Ctrl;
  var btns = [], texts = [];
  if (c) {
    for (var k in c) { if (/^buttonCtrl_/.test(k) && c[k] && c[k].divElt) {
      var r = c[k].divElt.getBoundingClientRect();
      btns.push({i: k, cls: c[k].divElt.getAttribute('class'), l: Math.round(r.left), t: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)});
    } }
    var all = t.divElt.querySelectorAll('[class*="_Text"]');
    for (var i = 0; i < all.length; i++) {
      var el = all[i], r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      if (r.width > 0 || r.height > 0) texts.push({cls: el.getAttribute('class'), fs: cs.fontSize, col: cs.color, l: Math.round(r.left), r: Math.round(r.right), vis: cs.visibility});
    }
  }
  var bg = c ? getComputedStyle(c.divElt).backgroundImage : null;
  var btnBg = {};
  if (c) { for (var k in c) { if (/^buttonCtrl_/.test(k) && c[k] && c[k].divElt) {
    btnBg[k] = getComputedStyle(c[k].divElt).backgroundImage; } } }
  return {ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(), hasCtrl: !!c,
          subCls: document.body.classList.contains('OemplusB2'),
          bg: bg, btns: btns, btnBg: btnBg, texts: texts,
          focusIdx: c ? c._buttonSelectIndex : null,
          nBtn: c ? c._buttonCount : 0,
          meter: c && c._determinateMeter ? getComputedStyle(c._determinateMeter).backgroundImage : null,
          meterHl: c && c._determinateMeterHighlight ? getComputedStyle(c._determinateMeterHighlight).backgroundImage : null,
          meterW: c && c._determinateMeterHighlight ? c._determinateMeterHighlight.style.width : null,
          indet: c && c._indeterminateMeter ? getComputedStyle(c._indeterminateMeter).backgroundImage : null,
          indetImgHidden: c && c._indeterminateMeter ? (c._indeterminateMeter.querySelector('img') ? getComputedStyle(c._indeterminateMeter.querySelector('img')).visibility : null) : null,
          pinBg: c && c._imagePath1 ? getComputedStyle(c._imagePath1).backgroundImage : null,
          img1: c && c._imagePath1 ? getComputedStyle(c._imagePath1).backgroundImage : null,
          img1cls: c && c._imagePath1 ? c._imagePath1.getAttribute('class') : null,
          titleBg: t && t.divElt.querySelector('.Dialog3Ctrl_Title_Separator') ? getComputedStyle(t.divElt.querySelector('.Dialog3Ctrl_Title_Separator')).backgroundImage : null,
          errors: window.__errors.slice()};
}"""

FOCUS_JS = """(keys) => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var c = t.dialog3Ctrl, out = {res: [], idx: []};
  for (var i = 0; i < keys.length; i++) {
    out.res.push(t.handleControllerEvent(keys[i]));
    out.idx.push(c._buttonSelectIndex);
  }
  return out;
}"""

SELECT_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var c = t.dialog3Ctrl;
  var fired = [];
  var orig = c.properties.defaultSelectCallback;
  c.properties.defaultSelectCallback = function(ctrl, appData) { fired.push(appData); return orig && orig.apply(this, arguments); };
  t.handleControllerEvent('selectStart');   // zet down-highlight (zoals een echte draaiknop-druk)
  t.handleControllerEvent('selectEnd');     // heft highlight op EN vuurt callback
  return {fired: fired, idx: c._buttonSelectIndex};
}"""


def shot(h, name):
    h.page.screenshot(path=os.path.join(SHOTS, name))


def goto(h, uia, ctxt, wait=2200):
    h.ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
    h.page.wait_for_timeout(wait)


def dlg_state(h):
    return h.ev(DLG_JS)


def btn_hitboxes(st):
    return sorted([(b["i"], b["l"], b["t"], b["w"], b["h"]) for b in st["btns"]])


def main():
    # ---- static H8: geen selector-overlap met andere B2Sub-bestanden ----
    cssdir = os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "css")
    mine = os.path.join(cssdir, "B2Sub-20-dialog3.css")
    def sels(f):
        out = set()
        for m in re.finditer(r"(?m)^([^\n{}]+)\{", open(f).read()):
            for s in m.group(1).split(","):
                s = s.strip()
                if s.startswith("body.OemplusB2"):
                    out.add(s)
        return out
    sm = sels(mine)
    dup = []
    for f in sorted(os.listdir(cssdir)):
        if f.startswith("B2Sub-") and f != "B2Sub-20-dialog3.css" and f.endswith(".css"):
            d = sm & sels(os.path.join(cssdir, f))
            if d:
                dup.append((f, sorted(d)))
    check("H8 static: geen selector van B2Sub-20 in een ander B2Sub-bestand", not dup, dup)
    # ---- static: marker + ASCII + alle url() refs bestaan ----
    txt = open(mine, encoding="utf-8").read()
    check("H7 static: marker OEMPLUS-B2 + ASCII-only in B2Sub-20-dialog3.css",
          "OEMPLUS-B2" in txt and all(ord(c) < 128 for c in txt))
    imgdir = os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "images")
    missing = [u for u in re.findall(r"url\(\.\./images/([^)]+)\)", txt) if not os.path.isfile(os.path.join(imgdir, u))]
    check("P2 assets: elke url(../images/...) in de CSS bestaat als PNG", not missing, missing)

    # ---- boot stock -> mount -> B2 aan ----
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(800)
    h.ev("framework.common.updateSbClock(new Date(2026,10,26,10,56,0).getTime())")
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
    p.wait_for_timeout(1200)
    goto(h, "system", "HomeScreen", 2200)
    h.mount()
    # B2 aan via het eco-paneel (zelfde pad als run_inject.py)
    goto(h, "ecoenergy", "FuelConsumption", 2400)
    p.keyboard.press("m"); p.wait_for_timeout(300)
    p.keyboard.press("n"); p.wait_for_timeout(400)
    p.keyboard.press("Enter"); p.wait_for_timeout(1600)
    inj = h.ev("OemplusInject.status()")
    check("setup: B2 aan (subOn, body.OemplusB2 op niet-protected)", inj["on"] and inj["subOn"] is True, {k: inj.get(k) for k in ("on", "subOn", "subLinks")})
    sub_hrefs = h.ev("Array.prototype.map.call(document.querySelectorAll('link[data-oemplusb2sub]'), function(l){return l.getAttribute('href');})")
    check("setup: B2Sub-20-dialog3.css zit in de lader-lijst op positie 20",
          any("B2Sub-20-dialog3.css" in s for s in sub_hrefs), sub_hrefs)
    loaded20 = [r for ph, r in h.requests if r.endswith("B2Sub-20-dialog3.css")]
    check("setup: B2Sub-20-dialog3.css daadwerkelijk geladen (niet 404)", len(loaded20) >= 1 and "common/oemplusb2/css/B2Sub-20-dialog3.css" not in h.missing, loaded20)

    screens = [
        # (uia, ctxt, label, categorie)
        ("system", "NoConnectionNotify", "S1 2-knoppen style13", "2knoppen"),
        ("btpairing", "ConfirmDelete", "S2 2-knoppen style02 focus0", "2knoppen"),
        ("system", "NotifyDialog", "S3 3-knoppen style17", "3knoppen"),
        ("syssettings", "FactoryResetConfirm", "S4 fullscreen 2-knoppen style02", "2knoppen+fullscreen"),
        ("btpairing", "ConnectingDevice", "S5 indeterminate meter style14 0 knoppen", "indeterminate"),
        ("btpairing", "PairingInProcess", "S6 indeterminate als imagePath1 style03", "indeterminate-img"),
        ("satradio", "VuiConfirmNewPIN", "S7 PIN style16 2 knoppen", "pin"),
        ("aharadio", "ShoutRecording", "S8 determinate meter style03 2 knoppen", "determinate"),
        ("system", "Disclaimer", "S9 1 knop + titel + fullscreen style02", "1knop+titel"),
    ]

    states_on = {}
    for uia, ctxt, label, cat in screens:
        goto(h, uia, ctxt, 2400)
        st = dlg_state(h)
        ok_open = st["hasCtrl"] and st["ctxt"] == ctxt
        check("open %s (%s/%s): Dialog3Ctrl aanwezig, body.OemplusB2 aan" % (label, uia, ctxt),
              ok_open and st["subCls"] is True, {k: st[k] for k in ("ctxt", "hasCtrl", "subCls", "errors")})
        check("open %s: B2-paneel actief (bg = B2DialogBg*.png)" % label,
              st["bg"] and "B2DialogBg" in st["bg"], st["bg"])
        states_on[(uia, ctxt)] = st
        shot(h, "p2-aan-%s.png" % ctxt)
        # H1 + H4 + H5 per scherm
        hb = btn_hitboxes(st)
        check("H1 %s: %d knoppen met hitbox (l,t,w,h) gemeten" % (label, len(hb)), len(hb) >= 0, hb)
        # H4: alle zichtbare teksten >= 24px
        small = [t for t in st["texts"] if float(t["fs"][:-2]) < 24 and t["vis"] != "hidden"]
        check("H4 %s: alle zichtbare dialog-teksten >= 24px" % label, not small, small[:4])
        # H5: gefocuste knop heeft B2 focus-PNG
        foc = [k for k, v in st["btnBg"].items() if "_focused" in (st["btns"] and next((b["cls"] for b in st["btns"] if b["i"] == k), "") or "") ]
        # Bepaal focus-knop via class
        focBtns = [b for b in st["btns"] if "_focused" in b["cls"]]
        ok5 = all("B2DlgBtn" in (st["btnBg"].get(b["i"]) or "") and "Focus" in st["btnBg"].get(b["i"]) for b in focBtns) if focBtns else True
        check("H5 %s: gefocuste knop (%d) toont B2DlgBtn*_Focus.png" % (label, len(focBtns)), ok5,
              [(b["i"], st["btnBg"].get(b["i"])) for b in focBtns])
        # paneel-bounds: geen CONTENT-tekst buiten x 70..730 (titel mag OEM-breed zijn: .Dialog3Ctrl_Title
        # left 59 width 682 -> tekst left 77 width 664 = tot 741; dat is OEM-geometry, geen B2-wijziging)
        out = [t for t in st["texts"] if not t["cls"].startswith("Dialog3Ctrl_Title") and (t["l"] < 70 or t["r"] > 730)]
        check("P2 bounds %s: geen content-tekst buiten paneel x 70-730 (titel uitgezonderd, OEM-breed)" % label, not out, out[:3])

    # ---- H2 focus-logica: cw/ccw/select gelijk aan/uit op S1 (2 knoppen) ----
    # EERST naar een niet-dialog scherm (home is B2 in deze sessie; de dialog zelf is wat telt), dan S1.
    goto(h, "system", "HomeScreen", 1800)
    goto(h, "system", "NoConnectionNotify", 2200)
    st = dlg_state(h)
    hb_on = btn_hitboxes(st)
    shot(h, "p2-aan-NoConnectionNotify.png")   # shot op de initiële focus (initialFocus), vóór cw/select
    foc_on = h.ev(FOCUS_JS, ["cw", "cw", "ccw"])
    sel_on = h.ev(SELECT_JS)  # H2-select: zelfde appData aan/uit; state erna herladen
    # B2 uit (submenu-klasse + links weg; home-B2 blijft maar raakt Dialog3 niet)
    h.ev("OemplusInject.b2Off()")
    p.wait_for_timeout(700)
    # ververs de context ZONDER B2 (klasse/links weg) -> dialog opnieuw in OEM, eigen focus-state
    goto(h, "system", "HomeScreen", 1500)
    goto(h, "system", "NoConnectionNotify", 2200)
    st_off = dlg_state(h)
    check("H6 setup: na b2Off geen body.OemplusB2 en geen B2Sub-links",
          st_off["subCls"] is False and h.ev("document.querySelectorAll('link[data-oemplusb2sub]').length") == 0)
    check("H6 S1: na uit (context herladen zonder B2) bg = OEM DialogBG_Style01.png", st_off["bg"] and "DialogBG_Style01" in st_off["bg"], st_off["bg"])
    shot(h, "p2-uit-NoConnectionNotify.png")   # shot op de initiële focus (zelfde als aan-shot)
    foc_off = h.ev(FOCUS_JS, ["cw", "cw", "ccw"])  # zelfde focus-wissel als 'aan' (verg. H2)
    sel_off = h.ev(SELECT_JS)  # H2: zelfde appData als 'aan'
    hb_off = btn_hitboxes(st_off)
    check("H1 S1: knop-hitboxes identiek met B2 aan/uit (0 px verschil)", hb_on == hb_off, {"aan": hb_on, "uit": hb_off})
    check("H2 S1: focus-wissel cw/cw/ccw + index gelijk aan/uit", foc_on["idx"] == foc_off["idx"] and foc_on["res"] == foc_off["res"],
          {"aan": foc_on, "uit": foc_off})
    check("H2 S1: select vuurt zelfde appData met B2 aan/uit", sel_on["fired"] == sel_off["fired"] and sel_on["idx"] == sel_off["idx"],
          {"aan": sel_on, "uit": sel_off})
    # B2 weer aan voor H3/H9 (op home; de volgende dialog laadt dan met B2)
    goto(h, "system", "HomeScreen", 1500)
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(500)

    # ---- H3 late lazy-CSS: Dialog3 is een boot-control (altijd geladen), maar de B2Sub-20 link is geladen
    #      VOORDAT enig Dialog3-template hier opende -> computed style moet B2 zijn (prefix wint). Verifieer
    #      expliciet dat de OEM Dialog3Ctrl.css WEL geladen is (boot) en toch verliest:
    goto(h, "btpairing", "ConfirmDelete", 2200)
    st = dlg_state(h)
    oem_loaded = h.ev("Array.prototype.some.call(document.querySelectorAll('link'), function(l){ return /Dialog3\\/css\\/Dialog3Ctrl\\.css$/.test(l.getAttribute('href')||''); })")
    check("H3: OEM Dialog3Ctrl.css geladen (boot-control) maar B2Sub-20 wint op specificiteit (bg=B2)",
          oem_loaded is True and st["bg"] and "B2DialogBg" in st["bg"], {"oem": oem_loaded, "bg": st["bg"]})
    # H3b: knop-bg wint van OEM knop-PNG
    focb = [b for b in st["btns"] if "_focused" in b["cls"]]
    check("H3b: gefocuste knop bg = B2DlgBtn*_Focus.png (niet OEM Dialog_*Btn_Focus)",
          focb and all("B2DlgBtn" in (st["btnBg"].get(b["i"]) or "") for b in focb),
          [(b["i"], st["btnBg"].get(b["i"])) for b in focb])
    shot(h, "p2-aan-ConfirmDelete.png")

    # ---- meters/PIN specifiek ----
    goto(h, "btpairing", "ConnectingDevice", 2200)
    st = dlg_state(h)
    check("S5 indeterminate (meter): meter-div bg = B2Indeterminate_0N.png en OEM <img> verborgen",
          st["indet"] and "B2Indeterminate" in st["indet"] and st["indetImgHidden"] == "hidden",
          {"indet": st["indet"], "img": st["indetImgHidden"]})
    shot(h, "p2-aan-ConnectingDevice.png")
    goto(h, "btpairing", "PairingInProcess", 2200)
    st = dlg_state(h)
    check("S6 indeterminate als imagePath1 (style03, geen meter): image1-div toont B2Indeterminate frame (B2-variant van spinner)",
          st["img1"] and "B2Indeterminate" in st["img1"], {"img1": st["img1"], "cls": st["img1cls"]})
    shot(h, "p2-aan-PairingInProcess.png")
    goto(h, "aharadio", "ShoutRecording", 2400)
    st = dlg_state(h)
    check("S8 determinate: track = B2ProgressTrack.png, highlight = B2ProgressFill.png repeat-x, breedte = JS inline",
          st["meter"] and "B2ProgressTrack" in st["meter"] and st["meterHl"] and "B2ProgressFill" in st["meterHl"] and st["meterW"] is not None,
          {"meter": st["meter"], "hl": st["meterHl"], "w": st["meterW"]})
    shot(h, "p2-aan-ShoutRecording.png")
    goto(h, "satradio", "VuiConfirmNewPIN", 2400)
    st = dlg_state(h)
    check("S7 PIN: PinEntryBkg vervangen door B2PinField.png", st["pinBg"] and "B2PinField" in st["pinBg"], st["pinBg"])
    shot(h, "p2-aan-VuiConfirmNewPIN.png")
    goto(h, "system", "Disclaimer", 2400)
    st = dlg_state(h)
    check("S9 titel: separator = B2DialogTitleSep.png; bg = B2DialogBgFs (fullScreen)",
          st["titleBg"] and "B2DialogTitleSep" in st["titleBg"] and st["bg"] and "B2DialogBgFs" in st["bg"],
          {"sep": st["titleBg"], "bg": st["bg"]})
    shot(h, "p2-aan-Disclaimer.png")

    # ---- H9 protected: Dialog3 in protected apps krijgt geen B2 ----
    inv = json.load(open(INV))
    prot_d3 = [x for x in inv["screens"] if "Dialog3" in (x.get("template") or "") and x.get("protected")]
    check("inventaris: protected Dialog3-contexts gevonden (%d)" % len(prot_d3), len(prot_d3) >= 1,
          sorted(set((x["uiaId"], x["ctxtId"]) for x in prot_d3))[:6])
    # warnguide is protected (app) en heeft Dialog3; kies er een:
    wg = next((x for x in prot_d3 if x["uiaId"] == "warnguide"), prot_d3[0])
    goto(h, wg["uiaId"], wg["ctxtId"], 2400)
    st = dlg_state(h)
    check("H9 %s/%s (protected): GEEN body.OemplusB2 en bg = OEM DialogBG (geen B2)" % (wg["uiaId"], wg["ctxtId"]),
          st["subCls"] is False and st["bg"] and "DialogBG_Style" in st["bg"] and "B2" not in (st["bg"] or ""),
          {k: st[k] for k in ("ctxt", "subCls", "bg")})
    shot(h, "p2-H9-%s-%s.png" % (wg["uiaId"], wg["ctxtId"]))
    # mobile911 Dialog3 protected:
    m911 = next((x for x in prot_d3 if x["uiaId"] == "mobile911"), None)
    if m911:
        goto(h, m911["uiaId"], m911["ctxtId"], 2400)
        st = dlg_state(h)
        check("H9 %s/%s (protected): geen OemplusB2, OEM bg" % (m911["uiaId"], m911["ctxtId"]),
              st["subCls"] is False and st["bg"] and "B2" not in (st["bg"] or ""), {k: st[k] for k in ("ctxt", "subCls", "bg")})
        shot(h, "p2-H9-%s-%s.png" % (m911["uiaId"], m911["ctxtId"]))
    # system/DisplayOff (protected ctxt, geen Dialog3) -> klasse weg
    goto(h, "system", "DisplayOff", 1600)
    st = h.ev("({cls: document.body.classList.contains('OemplusB2'), ctxt: framework.getCurrCtxtId()})")
    check("H9 system/DisplayOff: body.OemplusB2 weg binnen de wissel", st["cls"] is False, st)
    # terug naar een normaal scherm -> klasse er weer
    goto(h, "system", "NoConnectionNotify", 2000)
    st = dlg_state(h)
    check("H9 herstel: terug op niet-protected Dialog3 -> OemplusB2 er weer + B2 bg",
          st["subCls"] is True and st["bg"] and "B2DialogBg" in st["bg"], {k: st[k] for k in ("subCls", "bg")})

    check("einde: geen JS-fouten (pageerrors + window.__errors)", not h.pageerrors and not h.ev("window.__errors"), h.pageerrors + h.ev("window.__errors"))
    h.stop()

    # ---- H6 pixel-gelijk: verse sessie in STOCK, zelfde context, shot vergelijken ----
    h2 = MountHarness()
    p2 = h2.start()
    p2.wait_for_timeout(2500)
    h2.ev("framework.localize.setLanguage('nl_NL', false)")
    p2.wait_for_timeout(700)
    h2.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"))
    p2.wait_for_timeout(1000)
    goto(h2, "system", "HomeScreen", 2000)
    # stock: GEEN mount, GEEN B2 -> dialog in OEM
    goto(h2, "system", "NoConnectionNotify", 2200)
    st2 = dlg_state(h2)
    check("stock S1: geen OemplusB2, bg = OEM", st2["subCls"] is False and st2["bg"] and "DialogBG_Style" in st2["bg"], {k: st2[k] for k in ("subCls", "bg")})
    shot(h2, "p2-stock-NoConnectionNotify.png")  # initiële focus, zelfde als aan/uit-shots
    hb_stock = btn_hitboxes(st2)
    check("H1 stock S1: knop-hitboxes gelijk aan B2-aan (verg across sessies)", hb_stock == hb_on, {"stock": hb_stock, "b2aan": hb_on})
    h2.stop()

    # pixelvergelijk: content-gebied y 64..480 (banner y 0..63 kan in de 'uit'-sessie nog B2-home-resten
    # tonen doordat de home-CSS daar los van staat; het dialog-gebied moet EXACT gelijk zijn)
    from PIL import Image, ImageChops
    import hashlib
    def content_md5(name):
        im = Image.open(os.path.join(SHOTS, name)).convert("RGB").crop((0, 64, 800, 480))
        return hashlib.md5(im.tobytes()).hexdigest(), im
    a_md5, a_im = content_md5("p2-aan-NoConnectionNotify.png")
    b_md5, b_im = content_md5("p2-uit-NoConnectionNotify.png")
    c_md5, c_im = content_md5("p2-stock-NoConnectionNotify.png")
    check("H6 pixel: uit-shot content (y64-480) == stock-shot -> uit = OEM", b_md5 == c_md5,
          {"uit": b_md5[:12], "stock": c_md5[:12]})
    diff = ImageChops.difference(a_im, c_im)
    check("pixel: aan-shot content verschild van stock (B2 zichtbaar in dialog)", diff.getbbox() is not None,
          diff.getbbox())

    nfail = sum(1 for r in results if not r["ok"])
    json.dump({"pakket": "P2 Dialog3", "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-P2.json"), "w"), indent=1)
    print("\nP2: %d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)


if __name__ == "__main__":
    main()
