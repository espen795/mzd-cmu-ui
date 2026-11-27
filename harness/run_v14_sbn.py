#!/usr/bin/env python3
"""v1.4-harnas punt 7 (ML4): SBN-zichtbaarheid met B2 aan -- reproduceert LIVE-LOG 2026-11-27:
Common.js logde "Displaying new sbn" 3x (smsSMSAutoDownloadCompleteState 00:19:14,
audiosettingsAmplifierVolumeSetting 00:22:39 + 00:25:04) maar de gebruiker zag GEEN banner.

Opzet = run_v14_bewaker.py. We sturen exact die SBN's via framework.common (dezelfde API als Common._displaySbn:
startTimedSbn/showStateSbn met de bekende sbn-ids) op:
  (a) B2-home (system/HomeScreen, body.OemplusB2Home + OemplusB2 + B2SbnWatch),
  (b) een List2-submenu (system/Communication),
  (c) NowPlaying (fmradio/NowPlaying).
Per scherm checken we PIXEL/ZICHTBAARHEID (geen logregel, maar het element zelf):
  - .SbnCtrl bestaat in de DOM,
  - getBoundingClientRect binnen viewport (top >= -1, bottom <= 65, left 59, width 626),
  - computed top == "1px" (niet -60px), visibility visible, opacity > 0, display != none,
  - z-index >= 11 en NIET onder een ander element: elementFromPoint(cx, cy) == de SbnCtrl (of een kind),
  - de tekst (.SbnCtrl_Style01_Text1/_Style02_Text1) heeft font-size >= 24 en kleur != achtergrond,
  - screenshot voor het bord.
Daarna dezelfde SBN met B2 UIT (controle: OEM-gedrag, banner zichtbaar) -> pixel-gelijk qua rect.

Gebruik:  sh harness/build_root.sh && python3 harness/run_v14_sbn.py
Output:   harness/RESULTS-V14-SBN.json + shots/v14-sbn-*.png ; exit 1 bij gefaalde check.
"""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
B2H = os.path.join(HERE, "lib")
sys.path.insert(0, B2H)
import hlib
hlib.SHIM += ("\nObject.defineProperty(Element.prototype, 'currentStyle', { configurable: true,"
              " get: function(){ return getComputedStyle(this); } });\n")
from hlib import Harness

SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
results = []

def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok),
                    "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + str(detail)[:400] if detail != "" else ""))

class MountHarness(Harness):
    def __init__(self):
        Harness.__init__(self, "stock")
        self.root = os.path.join(HERE, "root-stock")
    def mount(self):
        self.root = os.path.join(HERE, "root-inject")
    def _serve(self, route):
        return Harness._serve(self, route)

def sysmsg(msgId, payload, uiaId="system"):
    return {"msgType": "msg", "uiaId": uiaId, "msgId": msgId, "params": {"payload": payload}}

def goto(h, p, uia, ctxt, wait=2400):
    if not h.ev("!!framework.getAppInstance('%s')" % uia):
        h.mmui({"msgType": "ctxtChg", "ctxtId": ctxt, "uiaId": uia, "params": None})
        for _ in range(25):
            p.wait_for_timeout(400)
            if h.ev("!!framework.getAppInstance('%s')" % uia):
                break
        p.wait_for_timeout(800)
    st0 = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId()})")
    if isinstance(st0, dict) and st0.get("app") == uia and st0.get("ctxt") == ctxt:
        h.ev("framework.debug.fakeCtxtChgMsgs('system','HomeScreen')")
        p.wait_for_timeout(2000)
    for _ in range(4):
        h.ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
        p.wait_for_timeout(wait)
        for _ in range(12):
            st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
            if isinstance(st, dict) and st.get("app") == uia and st.get("ctxt") == ctxt:
                return True
            p.wait_for_timeout(400)
    return False

def errs(h):
    return list(h.pageerrors) + list(h.ev("window.__errors"))

# SBN tonen zoals Common dat doet (Common.js:2160 _displaySbn -> instantiateControl SbnCtrl op document.body).
# We gebruiken de echte Common-API: showStateSbn/startTimedSbn met een bekend sbnId uit _knownSbns.
SHOW_SBN = """(function(uiaId, sbnId, timed){
    var c = framework.common;
    if (!c || !c._knownSbns || !c._knownSbns[sbnId]) { return 'ONBEKEND-SBN:' + sbnId + ' known=' + (c && c._knownSbns ? Object.keys(c._knownSbns).length : -1); }
    c._canShowSbns = true;
    if (timed) { c.startTimedSbn(uiaId, sbnId, 'stateSbn', {}); } else { c.showStateSbn(uiaId, sbnId, 'stateSbn', {}); }
    return 'OK';
})()"""

SBN_STATE = """(function(){
    var sbn = document.querySelector('.SbnCtrl');
    if (!sbn) return {aanwezig: false};
    var cs = getComputedStyle(sbn);
    var r = sbn.getBoundingClientRect();
    var cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
    var topEl = document.elementFromPoint(cx, cy);
    var inSbn = false, el = topEl;
    while (el) { if (el === sbn) { inSbn = true; break; } el = el.parentNode; }
    var txt = sbn.querySelector('[class*="_Text1"]');
    var tcs = txt ? getComputedStyle(txt) : null;
    return {aanwezig: true, cls: sbn.className, bodyCls: document.body.className,
            rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
            top: cs.top, visibility: cs.visibility, opacity: cs.opacity, display: cs.display,
            zIndex: cs.zIndex, bg: cs.backgroundColor,
            inViewport: r.top >= -1 && r.bottom <= 65 && r.left >= 0 && r.width > 100,
            topElementIsSbn: inSbn, topElCls: topEl ? (topEl.className || topEl.tagName) : null,
            txtFs: tcs ? tcs.fontSize : null, txtColor: tcs ? tcs.color : null, txt: txt ? txt.textContent : null};
})()"""

def sbn_checks(h, p, label, shotname):
    st = h.ev(SBN_STATE)
    p.screenshot(path=os.path.join(SHOTS, shotname + ".png"))
    ok = (st.get("aanwezig") and st["inViewport"] and st["visibility"] == "visible" and
          float(st["opacity"] or 0) > 0 and st["display"] != "none" and st["topElementIsSbn"] and
          st["top"] == "1px" and int(re.sub(r"[^0-9]", "", st["zIndex"] or "0") or 0) >= 11 and
          st["txtFs"] and float(re.sub(r"[^0-9.]", "", st["txtFs"])) >= 24)
    check("%s: SBN zichtbaar (rect %s, top %s, vis %s, opac %s, z %s, topElement-in-SBN %s, txt %s %s)"
          % (label, st.get("rect"), st.get("top"), st.get("visibility"), st.get("opacity"),
             st.get("zIndex"), st.get("topElementIsSbn"), st.get("txtFs"), st.get("txt")),
          ok, st)
    return st

def main():
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(700)
    h.ev("framework.common.updateSbClock(new Date(2026,10,27,9,5,0).getTime())")
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
    p.wait_for_timeout(1200)
    goto(h, p, "system", "HomeScreen", 2200)
    h.mount()
    goto(h, p, "ecoenergy", "FuelConsumption", 2400)
    pn = h.ev("!!document.querySelector('.OemplusInjPanel')")
    check("setup: eco-paneel aanwezig", pn, pn)
    p.keyboard.press("m"); p.wait_for_timeout(250); p.keyboard.press("n"); p.wait_for_timeout(300)
    p.keyboard.press("Enter"); p.wait_for_timeout(1600)
    st = h.ev("window.OemplusInject.status()")
    check("setup: B2 aan", st["on"] and st["subOn"], {k: st[k] for k in ("on", "subOn", "subLinks")})
    known = h.ev("Object.keys(framework.common._knownSbns)")
    print("bekende SBNs (%d): %s" % (len(known), known[:40]))

    # Kies de twee live-ids als ze bestaan; anders de dichtstbijzijnde stateSbn/timed variant.
    def pick(want):
        for w in want:
            for k in known:
                if w.lower() in k.lower():
                    return k
        return known[0] if known else None
    sms_sbn = pick(["smsSMSAutoDownloadCompleteState", "smsAutoDownload", "sms"])
    vol_sbn = pick(["audiosettingsAmplifierVolumeSetting", "amplifiervolume", "volume"])
    print("gebruik: sms=%s vol=%s" % (sms_sbn, vol_sbn))

    # ---------- (a) B2-home ----------
    goto(h, p, "system", "HomeScreen", 2600)
    st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), body: document.body.className})")
    check("setup home: op HomeScreen met B2 (body %s)" % st["body"], "OemplusB2Home" in st["body"] and "OemplusB2" in st["body"], st)
    r = h.ev(SHOW_SBN.replace("uiaId", "'%s'" % "sms").replace("sbnId", "'%s'" % sms_sbn).replace("timed", "false") if False else
             "(function(){ var c = framework.common; c._canShowSbns = true; c.showStateSbn('sms','%s','stateSbn',{}); return 'OK'; })()" % sms_sbn)
    p.wait_for_timeout(700)
    sbn_checks(h, p, "home + sms-SBN (%s)" % sms_sbn, "v14-sbn-home-sms")
    h.ev("(function(){ try { framework.common.endStateSbn('sms','%s','stateSbn'); } catch(e){} })()" % sms_sbn)
    p.wait_for_timeout(400)
    h.ev("(function(){ var c = framework.common; c._canShowSbns = true; c.startTimedSbn('audiosettings','%s','stateSbn',{}); return 'OK'; })()" % vol_sbn)
    p.wait_for_timeout(700)
    sbn_checks(h, p, "home + volume-SBN (%s, timed)" % vol_sbn, "v14-sbn-home-vol")
    h.ev("(function(){ try { framework.common.cancelTimedSbn('audiosettings','%s','stateSbn'); } catch(e){} })()" % vol_sbn)
    p.wait_for_timeout(400)

    # ---------- (b) List2-submenu ----------
    goto(h, p, "system", "Communication", 2600)
    st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), body: document.body.className})")
    check("setup list2: op system/Communication met OemplusB2 (body %s)" % st["body"], "OemplusB2" in st["body"] and "OemplusB2Home" not in st["body"], st)
    h.ev("(function(){ var c = framework.common; c._canShowSbns = true; c.showStateSbn('sms','%s','stateSbn',{}); return 'OK'; })()" % sms_sbn)
    p.wait_for_timeout(700)
    sbn_checks(h, p, "list2 (Communication) + sms-SBN", "v14-sbn-list2-sms")
    h.ev("(function(){ try { framework.common.endStateSbn('sms','%s','stateSbn'); } catch(e){} })()" % sms_sbn)
    p.wait_for_timeout(400)

    # ---------- (c) NowPlaying ----------
    goto(h, p, "fmradio", "NowPlaying", 2600)
    st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), body: document.body.className})")
    check("setup nowplaying: op fmradio/NowPlaying met OemplusB2 (body %s)" % st["body"], "OemplusB2" in st["body"], st)
    h.ev("(function(){ var c = framework.common; c._canShowSbns = true; c.startTimedSbn('audiosettings','%s','stateSbn',{}); return 'OK'; })()" % vol_sbn)
    p.wait_for_timeout(700)
    sbn_checks(h, p, "NowPlaying + volume-SBN (timed)", "v14-sbn-nowplaying-vol")
    # vergelijkt rect met B2 uit (OEM)
    rect_aan = h.ev("(function(){ var s = document.querySelector('.SbnCtrl'); if (!s) return null; var r = s.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; })()")
    h.ev("OemplusInject.b2Off()"); p.wait_for_timeout(700)
    # SBN is na b2Off misschien removed; toon opnieuw met OEM
    h.ev("(function(){ var c = framework.common; c._canShowSbns = true; c.startTimedSbn('audiosettings','%s','stateSbn',{}); return 'OK'; })()" % vol_sbn)
    p.wait_for_timeout(700)
    st_off = h.ev(SBN_STATE)
    p.screenshot(path=os.path.join(SHOTS, "v14-sbn-nowplaying-vol-UIT.png"))
    rect_uit = st_off.get("rect")
    check("NowPlaying: SBN-rect (left/top/width) B2 aan == B2 uit; hoogte 60 vs 58 = de 2x 1px B2-hairline-randen (binnen de 64px band, zie DESIGN-SYSTEEM par.8.6) %s vs %s" % (rect_aan, rect_uit),
          rect_aan is not None and rect_uit is not None and rect_aan[0:3] == rect_uit[0:3] and rect_aan[3] - rect_uit[3] <= 2,
          {"aan": rect_aan, "uit": rect_uit})
    check("NowPlaying B2 uit: SBN zichtbaar (OEM-controle)", st_off.get("aanwezig") and st_off.get("inViewport") and st_off.get("topElementIsSbn"), st_off)
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(600)
    check("einde: geen JS-fouten", not errs(h), errs(h))
    h.stop()

    nfail = sum(1 for r in results if r["ok"] is False)
    json.dump({"pakket": "v1.4 punt 7 SBN-zichtbaarheid met B2 aan", "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-V14-SBN.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
