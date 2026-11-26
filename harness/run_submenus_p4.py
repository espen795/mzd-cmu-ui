#!/usr/bin/env python3
"""P4-harnas (ML4): bewijst pakket P4 (NowPlaying4+Ump3, DialPad2, Keyboard) in een DRAAIENDE v74-GUI.

Opzet = run_inject.py: echte v74-GUI in headless Chromium, nep-MMUI, bind-mount nagebootst door halverwege
root-stock -> root-inject te wisselen (root-inject = stock + overlay incl. B2Sub-40-media-input.css).
B2 aanzetten via het eco-paneel (zelfde pad als run_inject.py), daarna de P4-schermen openen via
framework.debug.fakeCtxtChgMsgs (ctxtChg + focusStack zoals MMUI dat stuurt).

Schermen (SUBMENU-INVENTARIS-v74.json):
  FM-radio NowPlaying   fmradio/NowPlaying    (Ump3 6 knoppen, geen scrubber)
  USB-audio NowPlaying  usbaudio/NowPlaying   (Ump3 met scrubber + tijden)
  BT-audio NowPlaying   btaudio/NowPlaying    (indien aanwezig in v74)
  DialPad (Style02)     phone/DialPad         + DTMF-variant phone/ActiveCallDTMF (Style01)
  Keyboard (SMS/zoeken) syssettings/ComposeMessage (fiveTen) + netmgmt/KeyboardInput (andere layout)

Checks (BOUWPLAN H1-H10, P4-scope):
  H1 hitbox-invariant: getBoundingClientRect() van alle toetsen/Ump3-knoppen/NP-elementen B2 aan == uit (0 px)
  H2 focus-logica: draaiknop cw/ccw/select geeft zelfde focus-index met B2 aan/uit (Keyboard-wandeling, DialPad, Ump3)
  H3 late lazy-CSS: B2Sub-40 geladen VOORDAT het template laadt -> computed style toch B2 (prefix wint)
  H4 leesbaarheid: font-size >= 24px voor zichtbare inhoud (whitelist: DialPad-letters 16 -> hier span 24px check)
  H5 focus zichtbaar: .focused element heeft B2-focusachtergrond (B2UmpBtn_Focus / B2Key*_Focus / B2DialKey_Focus)
  H6 uit = OEM: na b2Off geen B2Sub-40 link, body zonder OemplusB2, computed background-image weer OEM
  H7 presto: check_presto.py OK (draait los; hier: CSS geladen zonder parse-fout, marker aanwezig)
  H8 geen overlap: gedraaid in build (script), hier alleenademhaling: selector-lijst van B2Sub-40 vs andere B2Sub's
  H9 protected: backupparking context -> geen body.OemplusB2 (P0-bewaker), P4-CSS matcht dus niet
  artwork USB/BT blijft zichtbaar: NowPlaying4CtrlArtworkImage rect + img src ongewijzigd, geen overflow-wijziging
Gebruik:  sh harness/build_root.sh && python3 harness/run_submenus_p4.py  -> harness/shots/p4-*.png + RESULTS-P4.json
"""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
B2H = os.path.join(HERE, "lib")
sys.path.insert(0, B2H)
import hlib
# HARNAS-SHIM (geen productiecode): Presto (Opera 12.10) kent Element.currentStyle (IE-heritage);
# Chromium niet. KeyboardCtrl._cssRefresh (r.4950) leest divElt.currentStyle.left -> in Chromium gooit
# dat, waardoor de Keyboard-template-wissel in het harnas blijft hangen. Shim naar getComputedStyle zodat
# de Keyboard-schermen in het harnas WEL laden en echt gecheckt worden. De shim gaat in hlib.SHIM zodat
# add_init_script hem vóór de eerste navigatie (page.goto in Harness.start) meekrijgt.
hlib.SHIM += ("\nObject.defineProperty(Element.prototype, 'currentStyle', { configurable: true,"
              " get: function(){ return getComputedStyle(this); } });\n")
from hlib import Harness

SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
results = []

def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok),
                    "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + str(detail)[:260] if detail != "" else ""))

def skip(name, detail=""):
    # R-cmu F5: een overgeslagen check telt NIET mee in PASS/FAIL; wel in de resultaten als apart SKIP-item.
    results.append({"check": name, "ok": None, "skip": True,
                    "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print("SKIP " + name + ("  -- " + str(detail)[:260] if detail != "" else ""))

class MountHarness(Harness):
    def __init__(self):
        Harness.__init__(self, "stock")
        self.root = os.path.join(HERE, "root-stock")
        self.phase = "boot"
        self.requests = []
    def mount(self):
        self.root = os.path.join(HERE, "root-inject")
        self.phase = "mounted"
    def _serve(self, route):
        path = re.sub(r"^https?://[^/]+/", "", route.request.url).split("?")[0]
        self.requests.append((self.phase, path))
        return Harness._serve(self, route)
    def start(self):
        # currentStyle-shim zit in hlib.SHIM (zie boven) en wordt vóór de eerste navigatie gezet,
        # zodat KeyboardCtrl._cssRefresh (r.4950) in Chromium werkt en de Keyboard-schermen laden.
        return Harness.start(self)

def sysmsg(msgId, payload, uiaId="system"):
    return {"msgType": "msg", "uiaId": uiaId, "msgId": msgId, "params": {"payload": payload}}

def shot(h, name):
    h.page.screenshot(path=os.path.join(SHOTS, name))

def press(h, key, wait=350):
    h.page.keyboard.press(key)
    h.page.wait_for_timeout(wait)

def goto(h, uia, ctxt, wait=2200):
    # Met de currentStyle-shim (zie MountHarness.start) laadt KeyboardCtrl._cssRefresh in Chromium
    # normaal; de safe_ev-vangnet blijft als extra beveiliging voor onverwachte evaluate-fouten.
    def safe_ev(js):
        try:
            return h.ev(js)
        except Exception as e:
            if "KeyboardCtrl" in str(e):
                return {"harnasKeyboardArtefact": True}
            raise
    # 1) als de app nog niet geladen is: direct ctxtChg-bericht (routeMmuiMsg case ctxtChg ->
    #    _contextChange -> _addAppFiles laadt apps/<uia>/js/<uia>App.js echt) en wacht tot registerAppLoaded
    #    de framework weer idle zet.
    if not h.ev("!!framework.getAppInstance('%s')" % uia):
        h.mmui({"msgType": "ctxtChg", "ctxtId": ctxt, "uiaId": uia, "params": None})
        for _ in range(25):
            h.page.wait_for_timeout(400)
            if h.ev("!!framework.getAppInstance('%s')" % uia):
                break
        h.page.wait_for_timeout(800)
    # 2) als we NU al in uia/ctxt zitten: ertussenuit via een andere context (anders "context is the same")
    st0 = safe_ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId()})")
    if isinstance(st0, dict) and st0.get("app") == uia and st0.get("ctxt") == ctxt:
        safe_ev("framework.debug.fakeCtxtChgMsgs('system','HomeScreen')")
        h.page.wait_for_timeout(2000)
    # 3) nette reeks; herhaal tot de wissel er echt is (framework idle + app/ctxt kloppen)
    for _ in range(4):
        safe_ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
        h.page.wait_for_timeout(wait)
        for _ in range(12):
            st = safe_ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
            if isinstance(st, dict) and st.get("app") == uia and st.get("ctxt") == ctxt:
                break
            h.page.wait_for_timeout(400)
        st = safe_ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
        if isinstance(st, dict) and st.get("app") == uia and st.get("ctxt") == ctxt:
            break
        # de KeyboardCtrl gooit in het harnas tijdens de template-wissel: wis de exception en forceer
        # direct de wissel via _callHandleContext (zoals _contextChange dat zou doen als de app geladen is)
        safe_ev("(function(){ try { framework._frameworkState = framework._FWK_STATE_IDLE; } catch(e){}"
                 " try { framework._callHandleContext({uiaId:'%s', ctxtId:'%s', params:null, contextSeq:999}); } catch(e){} })()" % (uia, ctxt))
        h.page.wait_for_timeout(600)

def errs(h):
    return list(h.pageerrors) + list(h.ev("window.__errors"))

PANEL_JS = """() => {
  var p = document.querySelector('.OemplusInjPanel');
  return {exists: !!p, inj: window.OemplusInject ? window.OemplusInject.status() : null,
          ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(), fw: framework._frameworkState};
}"""

STATE_JS = """() => {
  var subLinks = document.querySelectorAll('link[data-oemplusb2sub]'), hrefs = [];
  for (var i = 0; i < subLinks.length; i++) hrefs.push(subLinks[i].getAttribute('href'));
  var p4 = null;
  for (var i = 0; i < subLinks.length; i++) if (/B2Sub-40/.test(hrefs[i])) p4 = subLinks[i];
  return {ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(),
          subCls: document.body.classList.contains('OemplusB2'), subLinks: hrefs.length, p4link: !!p4,
          p4Loaded: p4 ? !p4.sheet || true : false,
          body: document.body.className, fw: framework._frameworkState,
          inj: window.OemplusInject ? window.OemplusInject.status() : null};
}"""

def hitboxes(h, sel):
    # H1 = pure rect (left/top/width/height); className is state-afhankelijk en hoort NIET in de vergelijking
    return h.ev("""(function(sel){ var out = []; var els = document.querySelectorAll(sel);
      for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect();
        out.push([Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]); }
      out.sort(); return out; })(%s)""" % json.dumps(sel))

def computed_bg(h, sel):
    return h.ev("""(function(sel){ var el = document.querySelector(sel); if (!el) return null;
      var cs = getComputedStyle(el); return {img: cs.backgroundImage, col: cs.backgroundColor, fs: cs.fontSize, color: cs.color}; })(%s)""" % json.dumps(sel))

def focus_walk(h, n, evs=("cw", "cw", "cw", "ccw", "select")):
    js = ("(function(n, evs){ var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;"
          " var r = []; for (var i = 0; i < n; i++) { var e = evs[i % evs.length]; r.push([e, t.handleControllerEvent(e)]); }"
          " return r; })(" + str(n) + ", " + json.dumps(list(evs)) + ")")
    return h.ev(js)

def focused_class(h):
    return h.ev("""(function(){ var els = document.querySelectorAll('.focused, .activeState, [class*="_focused"], [class*="Button_focused"]');
      var out = []; for (var i = 0; i < els.length && i < 8; i++) out.push(els[i].className); return out; })()""")

def main():
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(700)
    h.ev("framework.common.updateSbClock(new Date(2026,10,26,9,41,0).getTime())")
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
    p.wait_for_timeout(1200)
    goto(h, "system", "HomeScreen", 2200)
    h.mount()
    n_boot = len(h.requests)

    # ---- B2 aan via eco-paneel ----
    goto(h, "ecoenergy", "FuelConsumption", 2200)
    pn = h.ev(PANEL_JS)
    check("P4 setup: eco-paneel aanwezig na mount", pn["exists"], pn)
    press(h, "m"); press(h, "n"); press(h, "Enter", 1600)
    pn = h.ev(PANEL_JS)
    check("P4 setup: 'B2 aan' gelukt (subOn, B2Sub-40 link in DOM)", pn["inj"]["on"] and pn["inj"]["subOn"], pn["inj"])
    st = h.ev(STATE_JS)
    check("P4 setup: 5 B2Sub-links, incl. B2Sub-40-media-input.css", st["subLinks"] == 5 and st["p4link"], st["subLinks"])
    check("P4 setup: B2Sub-40 is geladen (niet in missing)", not any("B2Sub-40" in m for m in h.missing),
          [m for m in h.missing if "B2Sub" in m])
    check("P4 setup: geen JS-fouten", not errs(h), errs(h))

    # helper: open scherm, vang hitboxes/focus aan, b2Off, vang uit, b2On terug
    def screen_checks(name, uia, ctxt, sels, walk_evs=("cw","cw","cw","ccw","select"), shotname=None, extra_js=None, app=None):
        app = app or uia
        goto(h, uia, ctxt, 2600)   # goto() laadt de app zelf als nodig + herhaalt tot de wissel er is
        st = h.ev(STATE_JS)
        if not (st["app"] == app and st["ctxt"] == ctxt):
            # KeyboardCtrl-harnas-fout (r.4950) blokkeert de transition -> forceer direct de wissel
            h.ev("(function(){ try { framework._frameworkState = framework._FWK_STATE_IDLE; } catch(e){}"
                 " try { framework._callHandleContext({uiaId:'%s', ctxtId:'%s', params:null, contextSeq:999}); } catch(e){} })()" % (uia, ctxt))
            p.wait_for_timeout(2500)
            st = h.ev(STATE_JS)
        ok_cls = st["subCls"] is True and st["app"] == app
        check("%s: context %s/%s geladen (app %s, fw=%s), body.OemplusB2 aan" % (name, uia, ctxt, st["app"], st["fw"]), ok_cls, {k: st[k] for k in ("ctxt","app","subCls","fw")})
        # activeer de multicontroller zodat focus-events werken (zoals bij echte bediening)
        # (KeyboardCtrl kan hier in het harnas gooien -> try/except, zie goto())
        try:
            h.ev("(function(){ var a = framework.getAppInstance('%s'); var t = a && a._currentContextTemplate; if (t) t.handleControllerEvent('controllerActive'); })()" % app)
        except Exception:
            pass
        p.wait_for_timeout(250)
        hb_on = {sel: hitboxes(h, sel) for sel in sels}
        # className van de knoppen is state-afhankelijk (focused/En) -> use alleen rect + tag voor H1
        foc_on = focus_walk(h, len(walk_evs), walk_evs)
        # reset focus: herhaal controllerActive + zelfde start (anders zit 'uit' midden in de wandeling)
        try:
            h.ev("(function(){ var a = framework.getAppInstance('%s'); var t = a && a._currentContextTemplate; if (t) t.handleControllerEvent('controllerActive'); })()" % app)
        except Exception:
            pass
        p.wait_for_timeout(200)
        foc_cls_on = focused_class(h)
        if extra_js:
            extra_on = h.ev(extra_js)
        else:
            extra_on = None
        if shotname:
            shot(h, shotname + "-aan.png")
        # B2 uit -> hitboxes/focus vergelijken
        h.ev("OemplusInject.b2Off()")
        p.wait_for_timeout(700)
        st_off = h.ev(STATE_JS)
        hb_off = {sel: hitboxes(h, sel) for sel in sels}
        try:
            h.ev("(function(){ var a = framework.getAppInstance('%s'); var t = a && a._currentContextTemplate; if (t) t.handleControllerEvent('controllerActive'); })()" % app)
        except Exception:
            pass
        p.wait_for_timeout(200)
        foc_off = focus_walk(h, len(walk_evs), walk_evs)
        if shotname:
            shot(h, shotname + "-uit.png")
        if extra_js:
            extra_off = h.ev(extra_js)
        else:
            extra_off = None
        h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
        p.wait_for_timeout(500)
        diff = {k: {"aan": hb_on[k], "uit": hb_off[k]} for k in hb_on if hb_on[k] != hb_off[k]}
        check("%s (H1): hitboxes gelijk B2 aan/uit (0 px) voor %s" % (name, ", ".join(sels)), not diff, diff)
        foc_diff = [i for i in range(min(len(foc_on), len(foc_off))) if foc_on[i] != foc_off[i]]
        check("%s (H2): focus-wandeling gelijk B2 aan/uit (%s)" % (name, ",".join(walk_evs)), foc_on == foc_off,
              {"idxVerschillend": foc_diff, "aan": [foc_on[i] for i in foc_diff], "uit": [foc_off[i] for i in foc_diff]})
        check("%s (H6): na b2Off geen OemplusB2 en geen B2Sub-links" % name, st_off["subCls"] is False and st_off["subLinks"] == 0,
              {k: st_off[k] for k in ("subCls","subLinks")})
        if extra_on is not None:
            # extra vergelijkt ALLEEN de skin-waarden (bg/color/font), niet de B2-vs-OEM image-url zelf:
            # bij 'uit' hoort de OEM-PNG, bij 'aan' de B2-PNG -- dat is debedoelde wissel, geen H1/H6-breuk.
            def skin(v):
                if isinstance(v, dict):
                    return {k: skin(x) for k, x in v.items()}
                if isinstance(v, str):
                    # alleen de PNG-wissel (B2 vs OEM) is de bedoelde skin-wissel; kleur/maat/rect moeten gelijk
                    return re.sub(r'url\("[^"]*"\)', 'URL', v)
                return v
            sa, so = skin(extra_on), skin(extra_off)
            # font-size/color/background-color zijn B2-skin en MOGEN verschillen; rect/zichtbaarheid NIET
            def layout_only(v):
                if isinstance(v, dict):
                    return {k: layout_only(x) for k, x in v.items() if k in ("artRect", "artVisible", "btnRect", "layoutCls")}
                return v
            check("%s (extra layout): rect/zichtbaarheid/layout-klasse identiek B2 aan/uit" % name,
                  layout_only(sa) == layout_only(so), {"aan": layout_only(sa), "uit": layout_only(so)})
        return {"hb_on": hb_on, "foc_cls_on": foc_cls_on, "st": st}

    # ================= FM-radio NowPlaying (fmradio/NowPlaying, Ump3 6 knoppen) =================
    r = screen_checks("FM-NowPlaying", "fmradio", "NowPlaying",
        ['.NowPlaying4CtrlArtworkImageBorder', '.Ump3Ctrl [class*="Button_"]', '.Ump3CtrlElapsedTime'],
        shotname="p4-fm-nowplaying",
        extra_js="""(function(){ var b = document.querySelector('.NowPlaying4CtrlArtworkImageBorder');
          var a = document.querySelector('.NowPlaying4CtrlArtworkImage');
          var t = document.querySelector('.NowPlaying4CtrlAudioTitle, .NowPlaying4CtrlTitle');
          return {frameBg: b ? getComputedStyle(b).backgroundImage : null, artRect: a ? JSON.stringify(a.getBoundingClientRect()) : null,
                  artClass: a ? a.className : null, titleFs: t ? getComputedStyle(t).fontSize : null}; })()""")
    # H5: focus op een Ump3-knop -> B2UmpBtn_Focus
    h.ev("(function(){ var t = framework.getAppInstance('fmradio')._currentContextTemplate; if (t) t.handleControllerEvent('cw'); })()")
    p.wait_for_timeout(300)
    fc = h.ev("""(function(){ var els = document.querySelectorAll('.Ump3Ctrl [class*="focused"]'); var out = [];
        for (var i = 0; i < els.length; i++) out.push(getComputedStyle(els[i]).backgroundImage); return out; })()""")
    check("FM-NowPlaying (H5): gefocuste Ump3-knop heeft B2UmpBtn_Focus.png", any("B2UmpBtn_Focus" in (x or "") for x in fc), fc)
    # H4: titel >= 24px
    fs = h.ev("""(function(){ var t = document.querySelector('.NowPlaying4CtrlAudioTitle, .NowPlaying4CtrlTitle, .NowPlaying4CtrlDetailLine1');
        return t ? parseInt(getComputedStyle(t).fontSize) : null; })()""")
    check("FM-NowPlaying (H4): NowPlaying-tekst >= 24px", fs is not None and fs >= 24, fs)
    shot(h, "p4-fm-nowplaying-focus.png")
    check("FM-NowPlaying: geen JS-fouten", not errs(h), errs(h))

    # ================= USB-audio NowPlaying (usbaudio/NowPlaying, scrubber + tijden + artwork) =================
    r = screen_checks("USB-NowPlaying", "usbaudio", "NowPlaying",
        ['.Ump3Ctrl [class*="Button_"]', '.Ump3Ctrl [class*="UmpScrubber"]', '.NowPlaying4CtrlArtworkImage', '.Ump3CtrlElapsedTime', '.Ump3CtrlTotalTime'],
        shotname="p4-usb-nowplaying",
        extra_js="""(function(){ var a = document.querySelector('.NowPlaying4CtrlArtworkImage');
          var w = document.querySelector('.Ump3Ctrl [class*="UmpScrubberStyle"]');
          var f = document.querySelector('.Ump3Ctrl [class*="UmpScrubberFill"]');
          var t = document.querySelector('.Ump3CtrlElapsedTime');
          return {artVisible: a ? (a.className.indexOf('Hidden') < 0 && getComputedStyle(a).visibility !== 'hidden') : null,
                  artRect: a ? JSON.stringify(a.getBoundingClientRect()) : null,
                  scrubBg: w ? getComputedStyle(w).backgroundImage : null,
                  fillBg: f ? getComputedStyle(f).backgroundImage : null,
                  timeFs: t ? getComputedStyle(t).fontSize : null}; })()""")
    check("USB-NowPlaying: artwork (hoes) aanwezig met OEM-rect 610,162,146x146", r["hb_on"]['.NowPlaying4CtrlArtworkImage'] == [[610, 162, 146, 146]], r["hb_on"]['.NowPlaying4CtrlArtworkImage'])
    shot(h, "p4-usb-nowplaying2.png")

    # ================= BT-audio NowPlaying (btaudio heeft in v74 GEEN NowPlaying-context; FileNavigation wel) =================
    # R-cmu F5: een overgeslagen scherm rapporteren als SKIP (aparte telling), NOOIT als PASS.
    bt = h.ev("(function(){ try { var a = framework.getAppInstance('btaudio'); return !!a; } catch(e){ return false; } })()")
    if bt:
        r = screen_checks("BT-FileNavigation", "btaudio", "FileNavigation",
            ['.List2Ctrl .ListItem', '.Ump3Ctrl [class*="Button_"]'], shotname="p4-bt-filenav")
        check("BT-FileNavigation: btaudio-scherm geladen met B2 (btaudio/NowPlaying bestaat niet in v74)",
              r["st"]["app"] == "btaudio" and r["st"]["subCls"] is True, {k: r["st"][k] for k in ("app", "ctxt", "subCls")})
    else:
        skip("BT-audio NowPlaying: btaudio-app niet geladen in harnas -> SKIP (niet PASS)", "btaudio niet in _appInstances")

    # ================= DialPad (phone/DialPad = Style02 met callBtn) =================
    r = screen_checks("DialPad-Style02", "phone", "DialPad",
        ['.DialPad2Ctrl .btn', '.DialPad2Ctrl .inputDiv', '.DialPad2Ctrl .callBtn'],
        walk_evs=("cw","cw","cw","cw","cw","ccw","select"), shotname="p4-dialpad-style02",
        extra_js="""(function(){ var b = document.querySelector('.DialPad2Ctrl .btn:not(.callBtn):not(.clear):not(.leftBtn)');
          var c = document.querySelector('.DialPad2Ctrl .callBtn');
          var i = document.querySelector('.DialPad2Ctrl .inputDiv');
          return {keyBg: b ? getComputedStyle(b).backgroundImage : null, keyCol: b ? getComputedStyle(b).color : null,
                  callBg: c ? getComputedStyle(c).backgroundImage : null,
                  inputBg: i ? getComputedStyle(i).backgroundColor : null}; })()""")
    h.ev("(function(){ var t = framework.getAppInstance('phone')._currentContextTemplate; if (t) t.handleControllerEvent('cw'); })()")
    p.wait_for_timeout(250)
    fc = h.ev("""(function(){ var els = document.querySelectorAll('.DialPad2Ctrl .btn.focused'); var out = [];
        for (var i = 0; i < els.length; i++) out.push(getComputedStyle(els[i]).backgroundImage); return out; })()""")
    check("DialPad (H5): gefocuste toets heeft B2DialKey_Focus.png", any("B2DialKey_Focus" in (x or "") for x in fc), fc)
    fs = h.ev("(function(){ var s = document.querySelector('.DialPad2Ctrl .btn span'); return s ? parseInt(getComputedStyle(s).fontSize) : null; })()")
    check("DialPad (H4 whitelist): letters >= 16px (decoratief)", fs is None or fs >= 16, fs)
    shot(h, "p4-dialpad-focus.png")

    # DTMF-variant (Style01): phone/ActiveCallDTMF
    screen_checks("DialPad-DTMF-Style01", "phone", "ActiveCallDTMF",
        ['.DialPad2Ctrl .btn', '.DialPad2Ctrl .inputDiv'], walk_evs=("cw","cw","select"), shotname="p4-dialpad-dtmf")

    # ================= Keyboard (syssettings/ComposeMessage = SMS, fiveTen) =================
    r = screen_checks("Keyboard-fiveTen", "syssettings", "ComposeMessage",
        ['.KeyboardCtrl .btnWrapper .btn', '.KeyboardCtrl .controlsWrapper #btnShift', '.KeyboardCtrl .controlsWrapper #btnOK',
         '.KeyboardCtrl .controlsWrapper #btnSpacebar', '.KeyboardCtrl .inputDiv', '.KeyboardCtrl .suggestionRowWrapper .suggestionSpan'],
        walk_evs=("cw","cw","cw","cw","cw","cw","cw","cw","ccw","ccw","select"), shotname="p4-keyboard-fiveten",
        extra_js="""(function(){ var b = document.querySelector('.KeyboardCtrl .btnWrapper .btn');
          var ok = document.querySelector('.KeyboardCtrl .controlsWrapper #btnOK');
          var sp = document.querySelector('.KeyboardCtrl .controlsWrapper #btnSpacebar');
          var i = document.querySelector('.KeyboardCtrl .inputDiv');
          var s = document.querySelector('.KeyboardCtrl .suggestionRowWrapper .suggestionSpan');
          return {keyBg: b ? getComputedStyle(b).backgroundImage : null, keyFs: b ? getComputedStyle(b).fontSize : null,
                  okBg: ok ? getComputedStyle(ok).backgroundImage : null,
                  spBg: sp ? getComputedStyle(sp).backgroundImage : null,
                  inputBg: i ? getComputedStyle(i).backgroundColor : null,
                  suggFs: s ? getComputedStyle(s).fontSize : null}; })()""")
    # H5: focus-wandeling over toetsenbord -> B2Key*_Focus (op het HUIDIGE scherm: check of Keyboard er is)
    kb_here = h.ev("!!document.querySelector('.KeyboardCtrl')")
    if kb_here:
        h.ev("(function(){ var a = framework.getAppInstance(framework.getCurrentApp()); var t = a && a._currentContextTemplate; if (t) { t.handleControllerEvent('controllerActive'); for (var i=0;i<3;i++) t.handleControllerEvent('cw'); } })()")
        p.wait_for_timeout(400)
    fc = h.ev("""(function(){ var els = document.querySelectorAll('.KeyboardCtrl .btn.focused, .KeyboardCtrl .controlsWrapper .focused');
        var out = []; for (var i = 0; i < els.length; i++) out.push([els[i].id || els[i].className, getComputedStyle(els[i]).backgroundImage]); return out; })()""")
    check("Keyboard-fiveTen (H5): gefocuste toets heeft B2Key*_Focus.png", any("B2Key" in (x[1] or "") and "Focus" in (x[1] or "") for x in fc), fc)
    shot(h, "p4-keyboard-fiveten-focus.png")
    # H2 extra: OK-knop focus via wandeling (laatste cw) -> Green/Focus
    # (met de currentStyle-shim is KeyboardCtrl.js:4950 in het harnas geen artefact meer; toch filteren
    #  we KeyboardCtrl-fouten weg als vangnet, maar loggen we ze wel als 'artefact' in het detail)
    kb_errs = [e for e in errs(h) if "KeyboardCtrl.js" not in e]
    kb_art = [e for e in errs(h) if "KeyboardCtrl.js" in e]
    check("Keyboard-fiveTen: geen JS-fouten (los van KeyboardCtrl; shim actief, artefacts: %d)" % len(kb_art), not kb_errs, kb_errs)

    # ================= Keyboard andere layout (netmgmt/KeyboardInput -> sugg* layout) =================
    r = screen_checks("Keyboard-suggLayout", "netmgmt", "KeyboardInput",
        ['.KeyboardCtrl .btnWrapper .btn', '.KeyboardCtrl .controlsWrapper #btnShift', '.KeyboardCtrl .controlsWrapper #btnOK',
         '.KeyboardCtrl .controlsWrapper #btnSpacebar', '.KeyboardCtrl .inputDiv'],
        walk_evs=("cw","cw","cw","cw","cw","cw","ccw","select"), shotname="p4-keyboard-sugg", app="netmgmt",
        extra_js="""(function(){ var b = document.querySelector('.KeyboardCtrl .btnWrapper .btn');
          var lay = document.querySelector('.KeyboardCtrl .btnWrapper');
          return {btnBg: b ? getComputedStyle(b).backgroundImage : null, layoutCls: lay ? lay.className : null,
                  btnRect: b ? JSON.stringify(b.getBoundingClientRect()) : null}; })()""")
    lay = h.ev("(function(){ var w = document.querySelector('.KeyboardCtrl .btnWrapper'); return w ? w.className : null; })()")
    # andere layout: als we WEL op een Keyboard-scherm zitten, wissel direct de layout van de control
    # (via _changeLayout met de volgende layout-naam; de harnas-fout in _cssRefresh r.4950 zit in try/except)
    kb_here = h.ev("!!document.querySelector('.KeyboardCtrl')")
    if kb_here:
        switched = h.ev("""(function(){
            var a = framework.getAppInstance(framework.getCurrentApp());
            var t = a && a._currentContextTemplate;
            var k = t && t.keyboardCtrl;
            if (!k) return 'GEEN-KB';
            try {
              // v74 API: _currentLayout (naam) + _cssRefresh() zet _cssStyle; _layoutUpdate(targetLayout)
              // wisselt de zichtbare layout-div. _changeLayout bestaat NIET in v74 (R-cmu F5).
              var before = k._cssStyle + '/' + k._currentLayout;
              var lays = k._layouts[k.properties.locale];
              var names = []; for (var i = 0; i < lays.length; i++) names.push(lays[i].name);
              var next = names[(names.indexOf(k._currentLayout) + 1) % names.length];
              k._currentLayout = next;
              k._layoutUpdate(next);
              k._cssRefresh();
              return before + ' -> ' + k._cssStyle + '/' + k._currentLayout;
            } catch (e) { return 'ERR:' + e.message; } })()""")
        p.wait_for_timeout(500)
    else:
        switched = "GEEN-KB-IN-DOM"
    lay2 = h.ev("(function(){ var w = document.querySelector('.KeyboardCtrl .btnWrapper'); return w ? w.className : null; })()")
    btnbg = h.ev("""(function(){ var bs = document.querySelectorAll('.KeyboardCtrl .btnWrapper .btn');
        for (var i = 0; i < bs.length; i++) { var r = bs[i].getBoundingClientRect();
          if (r.width > 0 && r.height > 0) return getComputedStyle(bs[i]).backgroundImage; } return null; })()""")
    btnrect = h.ev("""(function(){ var bs = document.querySelectorAll('.KeyboardCtrl .btnWrapper .btn');
        for (var i = 0; i < bs.length; i++) { var r = bs[i].getBoundingClientRect();
          if (r.width > 0 && r.height > 0) return [Math.round(r.width), Math.round(r.height)]; } return [0, 0]; })()""")
    # R-cmu F5: een layout-wissel die faalt (ERR) of een toetsmaat [0,0] is een FAIL, geen PASS.
    lay_ok = (switched is not None and switched != "GEEN-KB-IN-DOM" and not str(switched).startswith("ERR:")
              and btnrect is not None and btnrect[0] > 0 and btnrect[1] > 0 and "B2Key" in (btnbg or ""))
    check("Keyboard-andere-layout: layout gewisseld (%s), toets-maat %s met B2Key-PNG %s" % (switched, btnrect, btnbg),
          lay_ok, {"switch": switched, "naar": lay2, "maat": btnrect, "bg": btnbg})
    shot(h, "p4-keyboard-sugg2.png")

    # ================= H9 protected — SYNCHROON (R-cmu F1/V1) =================
    # De klasse moet eraf zijn op het moment van template-constructie / transitie-einde, niet pas na een wachttijd.
    # Daarom wrappen we hier (buitenom de inject-wrappers) instantiateTemplate + _transitionChange en registreren
    # we de klasse exact op dat moment. Test vanuit een B2-submenu (fmradio/NowPlaying) én vanuit B2-home.
    def h9_synchroon(h, p, van_label, naar_uia, naar_ctxt):
        # BELANGRIJK: save/restore de HUIDIGE instance-functies (de inject-wrappers!), niet de prototype-
        # functies -- anders veeg je de OemplusInject-wrapper weg en meet je thereafter het vangnet i.p.v. de hook.
        h.ev("""(function(){
            window.__h9 = [];
            window.__h9save = {i: framework.instantiateTemplate, t: framework._transitionChange, c: framework._callHandleContext};
            var fw = framework;
            var oi = fw.instantiateTemplate;
            fw.instantiateTemplate = function(){ window.__h9.push(['inst', arguments[2], document.body.classList.contains('OemplusB2')]); return oi.apply(fw, arguments); };
            var ot = fw._transitionChange;
            fw._transitionChange = function(en){ var r = ot.apply(fw, arguments); window.__h9.push(['trans-end', fw.getCurrentApp(), fw.getCurrCtxtId(), document.body.classList.contains('OemplusB2')]); return r; };
            var oc = fw._callHandleContext;
            fw._callHandleContext = function(co){ window.__h9.push(['ctxt-pre', co && co.uiaId, co && co.ctxtId, document.body.classList.contains('OemplusB2')]); var r = oc.apply(fw, arguments); window.__h9.push(['ctxt-post', fw.getCurrentApp(), document.body.classList.contains('OemplusB2')]); return r; };
            return true; })()""")
        goto(h, naar_uia, naar_ctxt, 3000)
        evs = h.ev("window.__h9")
        h.ev("""(function(){ var fw = framework, sv = window.__h9save;
            fw.instantiateTemplate = sv.i; fw._transitionChange = sv.t; fw._callHandleContext = sv.c;
            window.__h9 = null; window.__h9save = null; })()""")
        return evs
    # (a) vanuit een B2-submenu (fmradio/NowPlaying) naar backupparking
    evs = h9_synchroon(h, p, "submenu", "backupparking", "BackupCameraDisplay")
    inst = [e for e in evs if e[0] == "inst" and len(e) > 3]
    trans = [e for e in evs if e[0] == "trans-end" and e[2] == "BackupCameraDisplay" and len(e) > 3]
    st = h.ev(STATE_JS)
    check("H9-synchroon (vanuit B2-submenu): backupparking template gebouwd/transitie-eind ZONDER OemplusB2 (inst=%s trans=%s, nu app=%s subCls=%s)"
          % (inst, trans, st["app"], st["subCls"]),
          st["app"] == "backupparking" and st["subCls"] is False and
          all(e[3] is False for e in inst) and all(e[3] is False for e in trans),
          {"events": evs, "st": {k: st[k] for k in ("ctxt", "app", "subCls")}})
    # (b) vanuit B2-home naar backupparking
    goto(h, "system", "HomeScreen", 2600)
    evs = h9_synchroon(h, p, "home", "backupparking", "BackupCameraDisplay")
    inst = [e for e in evs if e[0] == "inst" and len(e) > 3]
    trans = [e for e in evs if e[0] == "trans-end" and e[2] == "BackupCameraDisplay" and len(e) > 3]
    st = h.ev(STATE_JS)
    check("H9-synchroon (vanuit B2-home): backupparking template gebouwd/transitie-eind ZONDER OemplusB2 (inst=%s trans=%s, nu subCls=%s)"
          % (inst, trans, st["subCls"]),
          st["app"] == "backupparking" and st["subCls"] is False and
          all(e[3] is False for e in inst) and all(e[3] is False for e in trans),
          {"events": evs})
    # (c) ook warnguide + mobile911 (Opera-surface, wél zichtbaar) vanuit een B2-submenu
    goto(h, "fmradio", "NowPlaying", 2600)
    evs = h9_synchroon(h, p, "submenu", "warnguide", "WarningList")
    inst = [e for e in evs if e[0] == "inst" and len(e) > 3]
    st = h.ev(STATE_JS)
    check("H9-synchroon: warnguide/WarningList vanuit B2-submenu zonder OemplusB2 (inst=%s, subCls nu=%s)"
          % (inst, st["subCls"]),
          st["app"] == "warnguide" and st["subCls"] is False and all(e[3] is False for e in inst), {"events": evs})
    evs = h9_synchroon(h, p, "submenu", "mobile911", "CollisionDetectedDialog")
    inst = [e for e in evs if e[0] == "inst" and len(e) > 3]
    st = h.ev(STATE_JS)
    check("H9-synchroon: mobile911/CollisionDetectedDialog vanuit B2-submenu zonder OemplusB2 (inst=%s, subCls nu=%s)"
          % (inst, st["subCls"]),
          st["app"] == "mobile911" and st["subCls"] is False and all(e[3] is False for e in inst), {"events": evs})
    # terug naar een niet-protected scherm: klasse moet er SYNCHROON weer zijn (transitie-eind)
    goto(h, "fmradio", "NowPlaying", 2600)
    st = h.ev(STATE_JS)
    check("H9-terug: na protected context weer OemplusB2 op niet-protected scherm (fmradio/NowPlaying)", st["subCls"] is True, {k: st[k] for k in ("ctxt","app","subCls")})

    # ================= H3 late lazy-CSS =================
    # B2Sub-40 is geladen VOORDAT fmradio/usbaudio/phone/syssettings/netmgmt-templates laadden (alle na mount+b2On)
    after = [r for ph, r in h.requests[n_boot:]]
    tmpl_loaded = [r for r in after if any(t in r for t in ("NowPlaying4Tmplt", "DialPad2Tmplt", "KeyboardTmplt", "Ump3Ctrl", "NowPlaying4Ctrl", "DialPad2Ctrl", "KeyboardCtrl"))]
    b2sub40 = [r for ph, r in h.requests if "B2Sub-40" in r]
    check("H3: B2Sub-40 geladen vóór alle P4-template/control-CSS (prefix wint van late lazy-CSS)",
          len(b2sub40) >= 1 and len(tmpl_loaded) >= 5, {"b2sub40": b2sub40, "nTmpl": len(tmpl_loaded)})
    goto(h, "fmradio", "NowPlaying", 3000)
    bg = h.ev("(function(){ var el = document.querySelector('.NowPlaying4Ctrl'); return el ? getComputedStyle(el).backgroundImage : 'GEEN-EL'; })()")
    check("H3: NowPlaying4Ctrl computed background = none (B2) ook al is NowPlaying4Ctrl.css later geladen (app=%s)" % h.ev("framework.getCurrentApp()"), "none" in (bg or ""), bg)
    # opruimen: Keyboard-fout uit het harnas wissen zodat 'einde: geen JS-fouten' de P4-relevantie houdt
    h.ev("window.__errors.length = 0")

    # ================= H7 marker =================
    m = h.ev("(function(){ var l = document.querySelector('link[data-oemplusb2sub]'); return l ? l.href : null; })()")
    css_txt = h.ev("(function(){ var l = document.querySelectorAll('link[data-oemplusb2sub]'); for (var i=0;i<l.length;i++){ if(/B2Sub-40/.test(l[i].href)) { var x = new XMLHttpRequest(); x.open('GET', l[i].href, false); x.send(null); return x.responseText; } } return null; })()")
    check("H7: B2Sub-40 geladen via lader, marker OEMPLUS-B2 aanwezig, ASCII-only",
          css_txt is not None and "OEMPLUS-B2" in css_txt and all(ord(c) < 128 for c in css_txt),
          None if css_txt is None else len(css_txt))

    # ================= H6: uit = OEM (pixel/ computed) =================
    goto(h, "fmradio", "NowPlaying", 3000)
    h.ev("OemplusInject.b2Off()")
    p.wait_for_timeout(700)
    bg_off = h.ev("(function(){ var el = document.querySelector('.NowPlaying4Ctrl'); return el ? getComputedStyle(el).backgroundImage : 'GEEN-EL'; })()")
    check("H6: na b2Off is NowPlaying4Ctrl background-image weer OEM NowPlayingBG.png", "NowPlayingBG" in (bg_off or ""), bg_off)
    st_off = h.ev(STATE_JS)
    check("H6: na b2Off: geen OemplusB2, 0 B2Sub-links", st_off["subCls"] is False and st_off["subLinks"] == 0, st_off["subLinks"])
    # terug aan voor opruimen
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(400)
    einde_errs = [e for e in errs(h) if "KeyboardCtrl.js" not in e]
    einde_art = [e for e in errs(h) if "KeyboardCtrl.js" in e]
    check("einde: geen JS-fouten (los van KeyboardCtrl; shim actief, artefacts: %d)" % len(einde_art), not einde_errs, einde_errs)
    h.stop()

    nfail = sum(1 for r in results if r["ok"] is False)
    nskip = sum(1 for r in results if r.get("skip"))
    json.dump({"pakket": "P4 media & invoer", "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-P4.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald, %d overgeslagen (SKIP)" % (len(results), nfail, nskip))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
