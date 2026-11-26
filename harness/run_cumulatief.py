#!/usr/bin/env python3
"""Cumulatieve H8-check (integratie v1.3): ALLE B2Sub-CSS tegelijk geladen (00..40) op 4 echte
v74-schermen (list2-, dialog3-, tabs- en nowplaying-scherm) -> hitbox/focus-gelijkheid B2 aan/uit.

GEEN productiecode; alleen harnas. Hergebruikt hlib uit ui-oemplus-b2-v1 (met currentStyle-shim, zodat
Keyboard-schermen ook laden -- hier niet nodig, maar consistent met run_submenus_p4.py).

Gebruik:  sh harness/build_root.sh && python3 harness/run_cumulatief.py
Output:   harness/RESULTS-CUM.json + shots/cum-*.png ; exit 1 bij gefaalde check.
"""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
B2H = os.path.join(HERE, "lib")
sys.path.insert(0, B2H)
import hlib
# currentStyle-shim (Presto-heritage) zodat álle controls in Chromium laden; geen productiecode.
hlib.SHIM += ("\nObject.defineProperty(Element.prototype, 'currentStyle', { configurable: true,"
              " get: function(){ return getComputedStyle(this); } });\n")
from hlib import Harness

SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
results = []

def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok),
                    "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + str(detail)[:300] if detail != "" else ""))

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

def sysmsg(msgId, payload, uiaId="system"):
    return {"msgType": "msg", "uiaId": uiaId, "msgId": msgId, "params": {"payload": payload}}

def press(h, key, wait=350):
    h.page.keyboard.press(key)
    h.page.wait_for_timeout(wait)

STATE_JS = """() => {
  var subLinks = document.querySelectorAll('link[data-oemplusb2sub]'), hrefs = [];
  for (var i = 0; i < subLinks.length; i++) hrefs.push(subLinks[i].getAttribute('href'));
  return {ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(),
          subCls: document.body.classList.contains('OemplusB2'), subLinks: hrefs.length, hrefs: hrefs,
          fw: framework._frameworkState,
          inj: window.OemplusInject ? window.OemplusInject.status() : null};
}"""

def hitboxes(h, sel):
    return h.ev("""(function(sel){ var out = []; var els = document.querySelectorAll(sel);
      for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect();
        out.push([Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]); }
      out.sort(); return out; })(%s)""" % json.dumps(sel))

def focus_walk(h, n, evs):
    js = ("(function(n, evs){ var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;"
          " var r = []; for (var i = 0; i < n; i++) { var e = evs[i % evs.length]; r.push([e, t.handleControllerEvent(e)]); }"
          " return r; })(" + str(n) + ", " + json.dumps(list(evs)) + ")")
    return h.ev(js)

def goto(h, uia, ctxt, wait=2500):
    if not h.ev("!!framework.getAppInstance('%s')" % uia):
        h.mmui({"msgType": "ctxtChg", "ctxtId": ctxt, "uiaId": uia, "params": None})
        for _ in range(25):
            h.page.wait_for_timeout(400)
            if h.ev("!!framework.getAppInstance('%s')" % uia):
                break
        h.page.wait_for_timeout(800)
    st0 = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId()})")
    if st0["app"] == uia and st0["ctxt"] == ctxt:
        h.ev("framework.debug.fakeCtxtChgMsgs('system','HomeScreen')")
        h.page.wait_for_timeout(2200)
    for _ in range(5):
        h.ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
        h.page.wait_for_timeout(wait)
        for _ in range(12):
            st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
            if st["app"] == uia and st["ctxt"] == ctxt and st["fw"] == "idle":
                return True
            h.page.wait_for_timeout(400)
    st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
    return st["app"] == uia and st["ctxt"] == ctxt

def errs(h):
    return list(h.pageerrors) + list(h.ev("window.__errors"))

PANEL_JS = """() => {
  var p = document.querySelector('.OemplusInjPanel');
  return {exists: !!p, inj: window.OemplusInject ? window.OemplusInject.status() : null,
          ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(), fw: framework._frameworkState};
}"""

def main():
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(700)
    h.ev("framework.common.updateSbClock(new Date(2026, 10, 26, 9, 41, 0).getTime())")
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
    p.wait_for_timeout(1200)
    goto(h, "system", "HomeScreen", 2200)
    h.mount()
    n_boot = len(h.requests)

    # B2 aan via eco-paneel
    goto(h, "ecoenergy", "FuelConsumption", 2200)
    pn = h.ev(PANEL_JS)
    check("setup: eco-paneel aanwezig na mount", pn["exists"], pn)
    press(h, "m"); press(h, "n"); press(h, "Enter", 1600)
    pn = h.ev(PANEL_JS)
    check("setup: 'B2 aan' gelukt", pn["inj"]["on"] and pn["inj"]["subOn"], pn["inj"])
    st = h.ev(STATE_JS)
    check("setup: ALLE 5 B2Sub-links (00,10,20,30,40) in DOM, geen 404",
          st["subLinks"] == 5 and not any("B2Sub" in m for m in h.missing),
          {"n": st["subLinks"], "hrefs": st["hrefs"], "missing": [m for m in h.missing if "B2Sub" in m]})
    check("setup: geen JS-fouten", not errs(h), errs(h))

    # 4 schermen: list2 (system/Communication), dialog3 (een Dialog3-context), tabs (syssettings/DisplayTab), nowplaying (fmradio/NowPlaying)
    screens = [
        ("LIST2", "system", "Communication",
         ['.List2Ctrl .ListItem', '.List2Ctrl .TitleCtrl', '.LeftBtnCtrlBackBtn', '.List2Ctrl [class*="Slider"]'],
         ("cw", "cw", "cw", "ccw", "select"), "cum-list2"),
        ("TABS", "audiosettings", "SoundTab",
         ['.TabsCtrl [class*="Button"]', '.List2Ctrl .ListItem', '.SliderCtrl', '.List2Ctrl [class*="Slider"]'],
         ("cw", "cw", "cw", "cw", "ccw", "select"), "cum-tabs", True),  # scrollbare lijst: vergelijk per index
        ("NOWPLAYING", "fmradio", "NowPlaying",
         ['.NowPlaying4CtrlArtworkImageBorder', '.Ump3Ctrl [class*="Button_"]', '.Ump3CtrlElapsedTime'],
         ("cw", "cw", "ccw", "select"), "cum-nowplaying"),
        ("DIALOG3", "phone", "DialPad",
         ['.DialPad2Ctrl .btn', '.DialPad2Ctrl .inputDiv', '.DialPad2Ctrl .callBtn'],
         ("cw", "cw", "cw", "ccw", "select"), "cum-dialog"),
    ]
    for item in screens:
        name, uia, ctxt, sels, walk, shotname = item[:6]
        scroll_lijst = item[6] if len(item) > 6 else False
        ok = goto(h, uia, ctxt, 2800)
        st = h.ev(STATE_JS)
        check("%s: context %s/%s geladen, body.OemplusB2 aan, 5 B2Sub-links" % (name, uia, ctxt),
              ok and st["subCls"] is True and st["subLinks"] == 5,
              {k: st[k] for k in ("app", "ctxt", "subCls", "subLinks", "fw")})
        try:
            h.ev("(function(){ var a = framework.getAppInstance('%s'); var t = a && a._currentContextTemplate; if (t) t.handleControllerEvent('controllerActive'); })()" % uia)
        except Exception:
            pass
        h.page.wait_for_timeout(250)
        def top_scroll():
            # scrollbare lijst: zet de lijst terug naar boven zodat 'aan' en 'uit' hetzelfde venster vergelijken
            try:
                h.ev("""(function(){ var a = framework.getAppInstance('%s'); var t = a && a._currentContextTemplate;
                    var l = t && (t.listCtrl || t._listCtrl); if (l) { if (l.scrollToTop) l.scrollToTop(); else if (l.setScrollTop) l.setScrollTop(0); else if (l._scrollTop !== undefined) l._scrollTop = 0; } })()""" % uia)
            except Exception:
                pass
            h.page.wait_for_timeout(300)
        top_scroll()
        hb_on = {sel: hitboxes(h, sel) for sel in sels}
        foc_on = focus_walk(h, len(walk), walk)
        top_scroll()
        hb_on = {sel: hitboxes(h, sel) for sel in sels}
        h.page.screenshot(path=os.path.join(SHOTS, shotname + "-aan.png"))
        # B2 uit -> vergelijken
        h.ev("OemplusInject.b2Off()")
        h.page.wait_for_timeout(700)
        st_off = h.ev(STATE_JS)
        top_scroll()
        hb_off = {sel: hitboxes(h, sel) for sel in sels}
        try:
            h.ev("(function(){ var a = framework.getAppInstance('%s'); var t = a && a._currentContextTemplate; if (t) t.handleControllerEvent('controllerActive'); })()" % uia)
        except Exception:
            pass
        h.page.wait_for_timeout(200)
        foc_off = focus_walk(h, len(walk), walk)
        h.page.screenshot(path=os.path.join(SHOTS, shotname + "-uit.png"))
        h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
        h.page.wait_for_timeout(500)
        diff = {k: {"aan": hb_on[k], "uit": hb_off[k]} for k in hb_on if hb_on[k] != hb_off[k]}
        if scroll_lijst:
            # scrollbare lijst: het zichtbare venster schuift bij focus-wissels; vergelijk per index
            # (aantal items gelijk + elke zichtbare rij identiek), niet de hele gesorteerde lijst.
            n_ok = all(len(hb_on[k]) == len(hb_off[k]) for k in hb_on)
            per_idx = {k: [i for i in range(min(len(hb_on[k]), len(hb_off[k]))) if hb_on[k][i] != hb_off[k][i]]
                       for k in hb_on}
            n_rects = sum(len(v) for v in hb_on.values())
            check("%s (H1 cumulatief): hitboxes gelijk B2 aan/uit (scrollbare lijst: per index, %d rects over %d selectors)" % (name, n_rects, len(sels)),
                  n_ok and not any(per_idx.values()) and n_rects > 0, per_idx)
        else:
            check("%s (H1 cumulatief): hitboxes gelijk B2 aan/uit met ALLE B2Sub-CSS tegelijk" % name, not diff, diff)
        foc_diff = [i for i in range(min(len(foc_on), len(foc_off))) if foc_on[i] != foc_off[i]]
        check("%s (H2 cumulatief): focus-wandeling gelijk aan/uit (%s)" % (name, ",".join(walk)), foc_on == foc_off,
              {"idxVerschillend": foc_diff, "aan": [foc_on[i] for i in foc_diff], "uit": [foc_off[i] for i in foc_diff]})
        check("%s (H6): na b2Off geen OemplusB2 en 0 B2Sub-links" % name,
              st_off["subCls"] is False and st_off["subLinks"] == 0, {k: st_off[k] for k in ("subCls", "subLinks")})
        check("%s: geen JS-fouten" % name, not errs(h), errs(h))

    # H8 statisch: selector-overlap over ALLE B2Sub-bestanden samen (script-check, geen browser)
    import glob, collections
    files = sorted(glob.glob(os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "css", "B2Sub-*.css")))
    sel = collections.defaultdict(set)
    for f in files:
        for line in open(f, encoding="utf-8", errors="replace"):
            m = re.match(r"^(body\.OemplusB2[^\{,]*?)\s*\{", line.strip())
            if m:
                for s in m.group(1).split(","):
                    sel[s.strip()].add(os.path.basename(f))
    overlap = {s: sorted(fs) for s, fs in sel.items() if len(fs) > 1}
    check("H8 statisch: geen selector komt in >1 B2Sub-bestand voor (%d unieke selectors over %d bestanden)" % (len(sel), len(files)),
          not overlap, overlap)

    # H8 dynamisch: alle 5 CSS'en geladen -> computed styles echt B2 op elk scherm (spot-check per scherm)
    goto(h, "fmradio", "NowPlaying", 2800)
    bg = h.ev("(function(){ var el = document.querySelector('.NowPlaying4Ctrl'); return el ? getComputedStyle(el).backgroundImage : 'GEEN'; })()")
    check("H3 cumulatief: NowPlaying4Ctrl bg = none (B2Sub-40 wint) met alle 5 geladen", "none" in (bg or ""), bg)
    goto(h, "system", "Communication", 2800)
    bg2 = h.ev("(function(){ var el = document.querySelector('.CommonBgImg'); return el ? getComputedStyle(el).backgroundImage : 'GEEN'; })()")
    check("H3 cumulatief: CommonBgImg = B2SubBg.png (B2Sub-00) met alle 5 geladen", "B2SubBg.png" in (bg2 or ""), bg2)
    sep = h.ev("""(function(){ var el = document.querySelector('.List2Ctrl .ListItem'); return el ? getComputedStyle(el).backgroundImage : 'GEEN'; })()""")
    check("H3 cumulatief: List2-item heeft B2ListSep.png (B2Sub-10) met alle 5 geladen", "B2ListSep" in (sep or ""), sep)

    h.stop()
    nfail = sum(1 for r in results if not r["ok"])
    json.dump({"pakket": "CUMULATIEF v1.3 (alle B2Sub 00..40 tegelijk)", "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-CUM.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
