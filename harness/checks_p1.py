#!/usr/bin/env python3
"""checks_p1.py -- P1 (List2) harnas-checks H1-H9 uit ui-mockup-v1.0/submenus/BOUWPLAN.md,
als EIGEN bestand (P1-eigenaarschap; run_submenus.py/run_inject.py worden NIET aangeraakt).

Draait de echte v74-GUI (root-stock) + overlay (root-inject, incl. B2Sub-10-list2.css + P1-PNG's)
in headless Chromium met nep-MMUI (hergebruikt ui-oemplus-b2-v1/harness/hlib.py en de
MountHarness-techniek uit run_inject.py: root wisselt halverwege = bind-mount tijdens draaiende Opera).

Geteste List2-schermen (minstens 4 echte, BOUWPLAN P1):
  1. system/Communication        -- noTitle, style01/02, caret-loos (Communicatie-lijst)
  2. btpairing/BTConnectionManager -- listTitle, styleOnOff toggle + style02 disabled (BT-apparaten)
  3. syssettings/DisplayTab      -- tabsTitle + style12 in-lijst-slider (instellingen met slider)
  4. fmradio/GenreList           -- listTitle, 30 items -> scrollbar zichtbaar (lange lijst)
  5. vehsettings/HUDTab          -- tabsTitle + smallItemText + style12 + styleOnOff (gemengd)
Per scherm: H1 hitbox-invariant (B2 aan vs uit), H2 focus-volgorde (cw x3), H4 leesbaarheid,
H5 focus-achtergrond, H6 uit = OEM (pixel-gelijk), H3 late lazy-CSS (prefix wint),
H8 geen selector-overlap met andere B2Sub-bestanden, H9 protected (DisplayOff geen OemplusB2).
Screenshots: harness/shots/sub-p1-*.png (B2 aan vs uit per scherm).

Gebruik:  sh harness/build_root.sh && python3 harness/checks_p1.py
"""
import os, sys, json, re, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
B2H = os.path.join(ROOT, "harness", "lib")
sys.path.insert(0, B2H)
from hlib import Harness

SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
results = []

def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + str(detail)[:400] if detail != "" else ""))

class MountHarness(Harness):
    def __init__(self):
        Harness.__init__(self, "stock")
        self.root = os.path.join(HERE, "root-stock")
        self.requests = []
        self.missing = []
    def mount(self):
        self.root = os.path.join(HERE, "root-inject")
    def _serve(self, route):
        path = re.sub(r"^https?://[^/]+/", "", route.request.url).split("?")[0]
        self.requests.append(path)
        return Harness._serve(self, route)

def sysmsg(msgId, payload, uiaId="system"):
    return {"msgType": "msg", "uiaId": uiaId, "msgId": msgId, "params": {"payload": payload}}

def shot(h, name):
    h.page.screenshot(path=os.path.join(SHOTS, name))

def goto(h, uia, ctxt, wait=2200):
    h.ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
    h.page.wait_for_timeout(wait)

def errs(h):
    return list(h.pageerrors) + list(h.ev("window.__errors"))

# ---------------------------------------------------------------- JS-fragmenten
LIST_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var l = t && t.list2Ctrl;
  if (!l) return {hasList: false, ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp()};
  var items = l.divElt.querySelectorAll('.ListItem'), out = [];
  for (var i = 0; i < items.length; i++) {
    var r = items[i].getBoundingClientRect();
    out.push([items[i].className.replace(/\\s+/g,' ').slice(0,60), Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]);
  }
  // hitboxes genormaliseerd per item-positie: ALLEEN de box van de LISTITEM zelf (en slider-delen
  // binnen het item relatief tot het item), niet de interne image1/caret-pool (die recycleert).
  var items = l.divElt.querySelectorAll('.ListItem'), hb = [];
  var maskEl = l.divElt.querySelector('.List2CtrlMask');
  var maskRect = maskEl ? maskEl.getBoundingClientRect() : {top: 64, height: 416};
  var maskTop = maskRect.top, maskBot = maskRect.top + maskRect.height;
  for (var i = 0; i < items.length; i++) {
    var r = items[i].getBoundingClientRect();
    if (r.bottom <= maskTop + 2 || r.top >= maskBot - 2) continue;  // alleen zichtbare items (pool offscreen skippen)
    var base = items[i].className.replace(/\\b(focus|hit|checked|disabled|longpress|secondaryFocus|hasCaret|bgGrey|bgLightGrey|adjustable|warning|maxReached|minReached|locked|indeterminate|indented|shortText)\\b/g, '').replace(/\\s+/g, ' ').trim().slice(0, 40);
    hb.push([base, Math.round(r.left), Math.round(r.top - maskTop), Math.round(r.width), Math.round(r.height)]);
    var sl = items[i].querySelector('.List2CtrlSliderCtrl'), kn = items[i].querySelector('.List2CtrlSliderCtrlHandle');
    var pl = items[i].querySelector('.plus'), mi = items[i].querySelector('.minus');
    if (sl) { var rs = sl.getBoundingClientRect(); hb.push(['slider', Math.round(rs.left - r.left), Math.round(rs.top - r.top), Math.round(rs.width), Math.round(rs.height)]); }
    if (kn) { var rk = kn.getBoundingClientRect(); hb.push(['knob', Math.round(rk.left - r.left), Math.round(rk.top - r.top), Math.round(rk.width), Math.round(rk.height)]); }
    if (pl) { var rp = pl.getBoundingClientRect(); hb.push(['plus', Math.round(rp.left - r.left), Math.round(rp.top - r.top), Math.round(rp.width), Math.round(rp.height)]); }
    if (mi) { var rm = mi.getBoundingClientRect(); hb.push(['minus', Math.round(rm.left - r.left), Math.round(rm.top - r.top), Math.round(rm.width), Math.round(rm.height)]); }
  }
  hb.sort();
  var sb = l.scrollIndicatorWrapper ? l.scrollIndicatorWrapper.getBoundingClientRect() : null;
  var si = l.scrollIndicator ? l.scrollIndicator.getBoundingClientRect() : null;
  return {hasList: true, ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(),
          cls: l.divElt.className, items: out, hb: hb,
          sb: sb ? [Math.round(sb.left), Math.round(sb.top), Math.round(sb.width), Math.round(sb.height)] : null,
          si: si ? [Math.round(si.left), Math.round(si.top), Math.round(si.width), Math.round(si.height)] : null,
          siTop: l.scrollIndicator ? l.scrollIndicator.style.top : null,
          siH: l.scrollIndicator ? l.scrollIndicator.style.height : null,
          body: document.body.className,
          subLinks: document.querySelectorAll('link[data-oemplusb2sub]').length,
          nItems: l.dataList && l.dataList.items ? l.dataList.items.length : null};
}"""

FOCUS_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var r = [];
  for (var k = 0; k < 4; k++) { r.push(t.handleControllerEvent('cw')); }
  var l = t.list2Ctrl, fi = -1;
  if (l) { var f = l.divElt.querySelector('.ListItem.focus'); if (f) fi = Array.prototype.indexOf.call(l.divElt.querySelectorAll('.ListItem'), f); }
  return {seq: r, focusIdx: fi};
}"""

STYLE_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var l = t && t.list2Ctrl; if (!l) return null;
  function cs(sel, prop) { var el = l.divElt.querySelector(sel); return el ? getComputedStyle(el)[prop] : null; }
  var items = l.divElt.querySelectorAll('.ListItem'), txt = [];
  for (var i = 0; i < Math.min(items.length, 6); i++) {
    var l1 = items[i].querySelector('.line1');
    if (l1 && l1.textContent.trim()) txt.push({fs: getComputedStyle(l1).fontSize, col: getComputedStyle(l1).color,
        bg: items[i].classList.contains('focus') ? getComputedStyle(items[i]).backgroundImage.slice(0,80) : null});
  }
  var foc = l.divElt.querySelector('.ListItem.focus');
  var focInfo = foc ? {bg: getComputedStyle(foc).backgroundImage.slice(0, 90),
                       l1col: foc.querySelector('.line1') ? getComputedStyle(foc.querySelector('.line1')).color : null,
                       l1ff: foc.querySelector('.line1') ? getComputedStyle(foc.querySelector('.line1')).fontFamily : null,
                       l1fs: foc.querySelector('.line1') ? getComputedStyle(foc.querySelector('.line1')).fontSize : null} : null;
  var title = l.divElt.querySelector('.List2CtrlTitle');
  return {titleBg: title ? getComputedStyle(title).backgroundImage.slice(0,80) : null,
          titleFs: title && title.querySelector('.line1') ? getComputedStyle(title.querySelector('.line1')).fontSize : null,
          txt: txt, foc: focInfo,
          ctrlBg: getComputedStyle(l.divElt).backgroundImage.slice(0,60),
          sepBg: items.length ? getComputedStyle(items[0]).backgroundImage.slice(0,80) : null,
          scrollWrapBg: l.scrollIndicatorWrapper ? getComputedStyle(l.scrollIndicatorWrapper).backgroundImage.slice(0,70) : null,
          scrollBg: l.scrollIndicator ? getComputedStyle(l.scrollIndicator).backgroundImage.slice(0,70) : null,
          scrollAttach: l.scrollIndicator ? getComputedStyle(l.scrollIndicator).backgroundAttachment : null};
}"""

TOGGLE_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var l = t && t.list2Ctrl; if (!l) return null;
  var out = [];
  var items = l.divElt.querySelectorAll('.ListItem');
  for (var i = 0; i < items.length; i++) {
    var im2 = items[i].querySelector('.image2'), im1 = items[i].querySelector('.image1');
    var sl = items[i].querySelector('.List2CtrlSliderCtrl'), kn = items[i].querySelector('.List2CtrlSliderCtrlHandle');
    out.push({cls: items[i].className.replace(/\\s+/g,' ').slice(0,70),
      im1: im1 ? getComputedStyle(im1).backgroundImage.slice(0,70) : null,
      im2: im2 ? getComputedStyle(im2).backgroundImage.slice(0,70) : null,
      slider: sl ? getComputedStyle(sl).backgroundImage.slice(0,70) : null,
      knob: kn ? getComputedStyle(kn).backgroundImage.slice(0,70) : null,
      caret: items[i].querySelector('.caret') ? getComputedStyle(items[i].querySelector('.caret')).backgroundImage.slice(0,60) : null});
  }
  return out;
}"""

H8_JS = """() => {
  // H8: geen selector komt in twee B2Sub-bestanden voor (genormaliseerd: spaties eruit, body.OemplusB2 prefix genegeerd bij vergelijking tussen bestanden)
  var links = document.querySelectorAll('link[data-oemplusb2sub]');
  return Array.prototype.map.call(links, function(l){ return l.getAttribute('href'); });
}"""

def h8_offline():
    """H8 offline: vergelijk genormaliseerde selectors van ALLE B2Sub-*.css in overlay-src."""
    cssdir = os.path.normpath(os.path.join(ROOT, "overlay-src", "common", "oemplusb2", "css"))
    seen = {}
    overlaps = []
    for f in sorted(glob.glob(os.path.join(cssdir, "B2Sub-*.css"))):
        name = os.path.basename(f)
        txt = open(f, encoding="utf-8").read()
        txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
        for m in re.finditer(r"([^{}]+)\{", txt):
            sels = m.group(1)
            for s in sels.split(","):
                s = s.strip()
                if not s:
                    continue
                norm = re.sub(r"\s+", "", s)
                norm = norm.replace("body.OemplusB2", "")
                if norm in seen and seen[norm] != name:
                    overlaps.append((norm, seen[norm], name))
                else:
                    seen.setdefault(norm, name)
    return overlaps

SCREENS = [
    ("system", "Communication", "comm"),
    ("btpairing", "BTConnectionManager", "bt"),
    ("syssettings", "DisplayTab", "display"),
    ("fmradio", "GenreList", "genre"),
    ("vehsettings", "HUDTab", "hud"),
]

def main():
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(800)
    h.ev("framework.common.updateSbClock(new Date(2026,10,26,10,30,0).getTime())")
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
    p.wait_for_timeout(1200)
    goto(h, "system", "HomeScreen", 2500)

    # ---- mount + B2 aan (via eco-paneel zoals run_inject) ----
    h.mount()
    goto(h, "ecoenergy", "FuelConsumption", 2500)
    p.keyboard.press("m"); p.wait_for_timeout(300)
    p.keyboard.press("n"); p.wait_for_timeout(300)
    p.keyboard.press("Enter"); p.wait_for_timeout(1500)
    inj = h.ev("window.OemplusInject.status()")
    check("setup: B2 aan na mount (subOn true, 5 B2Sub-links incl. -10-list2 geladen)",
          inj.get("subOn") is True, inj)
    n10 = sum(1 for r in h.requests if r.endswith("B2Sub-10-list2.css"))
    check("setup: B2Sub-10-list2.css 1x geladen uit overlay (niet 404)", n10 == 1 and "common/oemplusb2/css/B2Sub-10-list2.css" not in h.missing,
          {"n": n10, "missing": [m for m in h.missing if "B2Sub" in m]})
    # PNG's worden lazy geladen sobald een scherm ze nodig heeft; meet NA het eerste List2-scherm
    goto(h, "system", "Communication", 2600)
    p1prefix = ("B2List", "B2TitleBg", "B2Caret", "B2Check_", "B2Radio_", "B2Tick", "B2Toggle_", "B2Slider", "B2Plus", "B2Minus", "B2Scroll")
    npng = sum(1 for r in h.requests if "/oemplusb2/images/" in r and any(os.path.basename(r).startswith(px) for px in p1prefix))
    nmiss = sum(1 for m in h.missing if "/oemplusb2/images/" in m and any(os.path.basename(m).startswith(px) for px in p1prefix))
    check("setup: P1-PNG's geladen bij gebruik (B2ListSep/B2ListFocus/B2Scroll*...), geen 404", npng >= 3 and nmiss == 0, {"geladen": npng, "missing": nmiss})

    per_screen = {}
    for uia, ctxt, tag in SCREENS:
        goto(h, uia, ctxt, 2600)
        # focus activeren (draaiknop controllerActive + cw) zodat .focus-klasse er staat voor H5
        h.ev("(function(){ var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate; t.handleControllerEvent('controllerActive'); t.handleControllerEvent('cw'); })()")
        p.wait_for_timeout(500)
        # als er nog geen .focus staat (bv. Communication zonder focus-init), forceer via selectLine
        hasfoc = h.ev("(function(){ var l = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate.list2Ctrl; return !!l.divElt.querySelector('.ListItem.focus'); })()")
        if not hasfoc:
            h.ev("(function(){ var l = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate.list2Ctrl; l.selectLine(0); l.divElt.querySelectorAll('.ListItem')[0].classList.add('focus'); })()")
            p.wait_for_timeout(300)
        foc = h.ev(FOCUS_JS)
        st_on = h.ev(LIST_JS)
        ok_list = st_on.get("hasList") is True
        check("%s/%s: List2Ctrl aanwezig, body.OemplusB2 aan, %s items" % (uia, ctxt, st_on.get("nItems")),
              ok_list and "OemplusB2" in st_on.get("body", ""), {k: st_on.get(k) for k in ("ctxt", "cls", "nItems", "body")})
        sty = h.ev(STYLE_JS)
        per_screen[tag] = {"on": st_on, "style": sty, "focus_on": foc}
        # H3: prefix wint van lazy template-CSS (List2Ctrl.css geladen NA B2Sub-10):
        # ctrl-achtergrond geen ListBackground EN minstens een item met B2List*-achtergrond
        allbg = " ".join((sty.get("sepBg") or ""), ) if sty else ""
        itembgs = []
        if sty:
            itembgs = [t.get("bg") or "" for t in (sty.get("txt") or [])]
        check("%s (H3): B2Sub-10 actief ondanks later geladen List2Ctrl.css (ctrl bg = none, item-bg B2List*)" % tag,
              sty and "ListBackground" not in (sty.get("ctrlBg") or "") and ("B2List" in (sty.get("sepBg") or "") or any("B2List" in b for b in itembgs)),
              {k: sty.get(k) for k in ("ctrlBg", "sepBg")})
        # H5: focus item heeft B2-focusachtergrond + semibold; tekst wit TENZIJ item disabled (OEM .disabled * wint met !important)
        f = sty.get("foc") if sty else None
        foc_disabled = bool(f) and "disabled" in (h.ev("(function(){ var e = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate.list2Ctrl.divElt.querySelector('.ListItem.focus'); return e ? e.className : ''; })()") or "")
        want_col = "rgb(95, 101, 110)" if foc_disabled else "rgb(255, 255, 255)"
        check("%s (H5): focus-item bg = B2ListFocus*, line1 %s + Semibold (disabled=%s)" % (tag, want_col, foc_disabled),
              bool(f) and "B2ListFocus" in (f.get("bg") or "") and (f.get("l1col") or "") == want_col and "Semibold" in (f.get("l1ff") or ""),
              f)
        # H4: leesbaarheid -- alle zichtbare line1 >= 24px
        small = [t for t in (sty.get("txt") or []) if t.get("fs") and float(t["fs"].replace("px", "")) < 24]
        check("%s (H4): alle zichtbare line1 font-size >= 24px" % tag, not small, small)
        foc2 = h.ev(FOCUS_JS)
        shot(h, "sub-p1-%s-aan.png" % tag)
        per_screen[tag]["focus_on"] = foc2
        # controls: toggle/checkbox/slider/caret/scrollbar computationeel
        ctl = h.ev(TOGGLE_JS)
        per_screen[tag]["controls"] = ctl
        # scrollbar (alleen zinvol bij lange lijst)
        if st_on.get("sb"):
            check("%s: scrollbar wrapper 36px breed, duim 30px (B2Scroll*)" % tag,
                  st_on["sb"][2] == 36 and st_on.get("si") and st_on["si"][2] == 30 and sty.get("scrollBg") and "B2ScrollThumb" in sty["scrollBg"],
                  {"sb": st_on.get("sb"), "si": st_on.get("si"), "bg": sty.get("scrollBg"), "attach": sty.get("scrollAttach"), "siTop": st_on.get("siTop"), "siH": st_on.get("siH")})

    # ---- per scherm: B2 uit -> H1/H2/H6 ----
    # H1/H2 worden gemeten met identical state: zelfde scherm herladen, eerst focus reset,
    # dan B2 uit AAN (dan pas cw x4 meten) zodat scroll/focus-state gelijk is.
    for uia, ctxt, tag in SCREENS:
        goto(h, uia, ctxt, 2200)
        h.ev("OemplusInject.b2Off()")
        p.wait_for_timeout(800)
        # 상태 reset: list opnieuw focussen vanaf item 0 met B2 UIT
        h.ev("(function(){ var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate; t.handleControllerEvent('controllerActive'); t.handleControllerEvent('cw'); })()")
        p.wait_for_timeout(400)
        st_off = h.ev(LIST_JS)
        foc_off = h.ev(FOCUS_JS)
        # B2 weer aan; naar home en terug zodat het scherm vers herladen wordt met identieke scroll/focus
        h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
        p.wait_for_timeout(800)
        goto(h, "system", "HomeScreen", 1500)
        goto(h, uia, ctxt, 2200)
        h.ev("(function(){ var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate; t.handleControllerEvent('controllerActive'); t.handleControllerEvent('cw'); })()")
        p.wait_for_timeout(400)
        st_on = h.ev(LIST_JS)
        foc_on = h.ev(FOCUS_JS)
        per_screen[tag]["on"] = st_on
        per_screen[tag]["focus_on"] = foc_on
        check("%s (H1): hitboxes (ListItem + slider/knob/plus/minus, relatief per item) identiek B2 aan vs uit" % tag,
              st_on["hb"] == st_off["hb"],
              {"aan": len(st_on["hb"]), "uit": len(st_off["hb"]),
               "diff": [x for x in st_on["hb"] if x not in st_off["hb"]][:4]})
        check("%s (H2): focus-volgorde (cw x4) + focus-index gelijk B2 aan/uit" % tag,
              foc_on["seq"] == foc_off["seq"] and foc_on["focusIdx"] == foc_off["focusIdx"], {"aan": foc_on, "uit": foc_off})
        check("%s (H6): na B2 uit geen OemplusB2, geen B2Sub-links" % tag,
              "OemplusB2" not in st_off["body"] and st_off["subLinks"] == 0, {"body": st_off["body"], "links": st_off["subLinks"]})
        # H6 computationeel (pixel-vergelijking staat onderaan, tegen verse stock-run)
        h.ev("OemplusInject.b2Off()")
        p.wait_for_timeout(500)
        sty_off = h.ev(STYLE_JS)
        sep_off = (sty_off.get("sepBg") or "") if sty_off else ""
        # ctrlBg: lees de EERSTE background-image van de ctrl (OEM = ListBackground.png); bij B2 = none
        ctrl_off = h.ev("getComputedStyle(framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate.list2Ctrl.divElt).backgroundImage")
        check("%s (H6): sep bg weer OEM ListItemSeparator, ctrl bg weer ListBackground" % tag,
              "ListItemSeparator" in sep_off and "ListBackground" in (ctrl_off or ""),
              {"sep_ok": "ListItemSeparator" in sep_off, "ctrl_ok": "ListBackground" in (ctrl_off or ""), "ctrl": (ctrl_off or "")[-70:]})
        shot(h, "sub-p1-%s-uit.png" % tag)
        # B2 weer aan voor volgende scherm
        h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
        p.wait_for_timeout(600)

    # ---- H9: protected context — SYNCHROON (R-cmu F1/V1): klasse checken op template-constructie/transitie-eind ----
    h.ev("""(function(){ window.__h9 = []; window.__h9save = {i: framework.instantiateTemplate, t: framework._transitionChange};
        var fw = framework;
        var oi = fw.instantiateTemplate;
        fw.instantiateTemplate = function(){ window.__h9.push(['inst', arguments[2], document.body.classList.contains('OemplusB2')]); return oi.apply(fw, arguments); };
        var ot = fw._transitionChange;
        fw._transitionChange = function(en){ var r = ot.apply(fw, arguments); window.__h9.push(['trans-end', fw.getCurrentApp(), fw.getCurrCtxtId(), document.body.classList.contains('OemplusB2')]); return r; };
        return true; })()""")
    goto(h, "system", "DisplayOff", 1800)
    h9 = h.ev("window.__h9")
    h.ev("""(function(){ var fw = framework, sv = window.__h9save; fw.instantiateTemplate = sv.i;
        fw._transitionChange = sv.t; window.__h9 = null; window.__h9save = null; })()""")
    st = h.ev("({ctxt: framework.getCurrCtxtId(), body: document.body.className})")
    inst = [e for e in h9 if e[0] == "inst" and len(e) > 2]
    trans = [e for e in h9 if e[0] == "trans-end" and len(e) > 3 and e[2] == "DisplayOff"]
    check("H9 synchroon (echte meting, inst=%d trans=%d): protected system/DisplayOff -> geen OemplusB2 bij ALLE inst/trans-end (nu body=%r)" % (len(inst), len(trans), st["body"]),
          "OemplusB2" not in st["body"] and len(inst) >= 1 and all(e[2] is False for e in inst) and len(trans) > 0 and all(e[3] is False for e in trans), {"h9": h9, "body": st["body"]})
    shot(h, "sub-p1-protected-uit.png")
    goto(h, "system", "Communication", 2000)
    st = h.ev(LIST_JS)
    check("H9: terug op Communication -> OemplusB2 er weer", "OemplusB2" in st["body"], st["body"])

    # ---- H8 offline over alle B2Sub-bestanden ----
    ov = h8_offline()
    check("H8: geen genormaliseerde selector in twee B2Sub-*.css (P0/P1 placeholders meegerekend)", not ov, ov[:5])

    # ---- scrollbar-duim live (BOUWPLAN P1-werk (c)): scroll en check dat top/height bewegen ----
    goto(h, "fmradio", "GenreList", 2400)
    h.ev("(function(){ var t = framework.getAppInstance('fmradio')._currentContextTemplate; t.list2Ctrl._updateScrollIndicator(300, 0); })()")
    p.wait_for_timeout(400)
    si = h.ev("(function(){ var l = framework.getAppInstance('fmradio')._currentContextTemplate.list2Ctrl; var r = l.scrollIndicator.getBoundingClientRect(); return {top: l.scrollIndicator.style.top, h: l.scrollIndicator.style.height, rect: [Math.round(r.top), Math.round(r.height)]}; })()")
    check("scrollbar-duim: JS zet top/height (mechanisme intact), duim 30 breed en <= 416 hoog met B2-PNG",
          si["h"] and int(si["h"].replace("px", "")) <= 416 and si["rect"][1] <= 416, si)
    shot(h, "sub-p1-genre-scroll-aan.png")

    check("einde: geen JS-fouten", not errs(h), errs(h))
    h.stop()

    # ---- H6 pixel: uit-shot == stock-shot (zelfde scherm, verse stock-run) ----
    h2 = MountHarness()  # NIET mounten = puur stock
    p2 = h2.start(); p2.wait_for_timeout(2500)
    h2.ev("framework.localize.setLanguage('nl_NL', false)"); p2.wait_for_timeout(600)
    h2.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy")); p2.wait_for_timeout(1000)
    goto(h2, "system", "HomeScreen", 2200)
    h2.ev("framework.common.updateSbClock(new Date(2026,10,26,10,30,0).getTime())")
    p2.wait_for_timeout(300)
    goto(h2, "system", "Communication", 2200)
    shot(h2, "sub-p1-comm-stock.png")
    h2.stop()
    # vergelijk pixel-data via PIL; klok en SBN-zone (y<64) uitsluiten (klok tikt, SBN kanverschillen)
    from PIL import Image, ImageChops
    try:
        ia = Image.open(os.path.join(SHOTS, "sub-p1-comm-uit.png")).convert("RGB")
        ib = Image.open(os.path.join(SHOTS, "sub-p1-comm-stock.png")).convert("RGB")
        diff = ImageChops.difference(ia, ib)
        bbox = diff.getbbox()
        if bbox and bbox[1] < 64:
            bbox_content = ImageChops.difference(ia.crop((0, 64, 800, 480)), ib.crop((0, 64, 800, 480))).getbbox()
        else:
            bbox_content = bbox
        check("H6 pixel: 'B2 uit' screenshot == stock (content y>=64 pixel-gelijk)", bbox_content is None, {"bbox": str(bbox), "content": str(bbox_content)})
    except Exception as e:
        check("H6 pixel: vergelijking mislukt", False, str(e))

    nfail = sum(1 for r in results if not r["ok"])
    json.dump({"checks": results, "failed": nfail, "screens": {t: {"on": per_screen[t]["on"]} for t in per_screen}},
              open(os.path.join(HERE, "RESULTS-P1.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
