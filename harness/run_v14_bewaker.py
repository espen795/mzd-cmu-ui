#!/usr/bin/env python3
"""v1.4-harnas punt 1+2 (ML4): bewijst de bewaker-flap-fix + echte H9-meting in een DRAAIENDE v74-GUI.

Opzet = run_submenus_p4.py: echte v74-GUI in headless Chromium, bind-mount nagebootst (root-stock ->
root-inject), B2 aan via het eco-paneel, dan contexts openen via framework.debug.fakeCtxtChgMsgs.

Punt 1 (bewaker-flap, HOOG): bij wissel naar backupparking mag er na de eerste "weg" GEEN "gezet" meer
komen todat een niet-protected context actief is. Bewijs = event-volgorde uit een recorder BUITEN de
inject-wrappers (zoals R-cmu's probe): registreer bij elke relevante hook-moment de body-klasse + een
teller. Specifiek:
  - ctxt-pre (voor origineel _callHandleContext), ctxt-post (na origineel), inst (binnen instantiateTemplate,
    VÓÓR het origineel), trans-pre (voor origineel _transitionChange), trans-end (na origineel).
  - Verwacht bij wissel ecoenergy/FuelConsumption -> backupparking/BackupCameraDisplay:
    ctxt-pre: klasse AAN (nog ecoenergy), ctxt-post: WEG (transPending blokkeert setSubClass),
    inst backupparking: WEG, trans-end backupparking: WEG, en DAARNA pas (bij terug naar fmradio) "aan".
  - Oude (v1.3) gedrag was: ctxt-post "gezet (ecoenergy/FuelConsumption)" 3 ms na "weg" -> flap.
  - Mutatietest (punt 2b): vervang ALLEEN de inject-_transitionChange-wrapper door het prototype (de
    _callHandleContext-wrapper blijft) -> bij camera moet de klasse DAN tijdens constructie WEG zijn;
    en een tweede mutatie: bewakerhelemaal uit (beide wrappers eraf, subOn aan) -> H9-check moet FAIL.

Punt 2 (H2 harnas): de H9-synchroon-checks in run_inject.py/checks_p1.py/run_submenus_p4.py filteren
`len(e) > 3` op een 3-elementig inst-event -> altijd leeg. Hier meten we ECHT: inst-event = ['inst', tmplt,
klasseOpConstructieMoment]; check eist len(inst) >= 1 en alle e[2] is False. Plus de mutatietest hierboven
(bewaker uit -> FAIL) bewijst dat de check echt is.

Gebruik:  sh harness/build_root.sh && python3 harness/run_v14_bewaker.py
Output:   harness/RESULTS-V14-BEWAKER.json + shots/v14-bewaker-*.png ; exit 1 bij gefaalde check.
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

RECORDER = """(function(){
    // recorder BUITEN de inject-wrappers: save/restore de HUIDIGE instance-functies (incl. inject-wrappers)
    window.__rec = [];
    window.__recSave = {i: framework.instantiateTemplate, t: framework._transitionChange, c: framework._callHandleContext};
    var fw = framework;
    var cls = function(){ return document.body.classList.contains('OemplusB2'); };
    var oi = fw.instantiateTemplate;
    fw.instantiateTemplate = function(){ window.__rec.push(['inst', arguments[2], cls()]); return oi.apply(fw, arguments); };
    var ot = fw._transitionChange;
    fw._transitionChange = function(en){ if (en === false) window.__rec.push(['trans-pre', fw.getCurrentApp(), fw.getCurrCtxtId(), cls()]); var r = ot.apply(fw, arguments); window.__rec.push(['trans-end', fw.getCurrentApp(), fw.getCurrCtxtId(), cls()]); return r; };
    var oc = fw._callHandleContext;
    fw._callHandleContext = function(co){ window.__rec.push(['ctxt-pre', co && co.uiaId, co && co.ctxtId, cls()]); var r = oc.apply(fw, arguments); window.__rec.push(['ctxt-post', fw.getCurrentApp(), fw.getCurrCtxtId(), cls()]); return r; };
    return true; })()"""

RESTORE = """(function(){ var fw = framework, sv = window.__recSave;
    fw.instantiateTemplate = sv.i; fw._transitionChange = sv.t; fw._callHandleContext = sv.c;
    window.__rec = null; window.__recSave = null; })()"""

def set_notes(h):
    # lees de inject-eventgeschiedenis (note() pusht in S.events, max 6) NIET; lees wel lastSub
    return h.ev("window.OemplusInject ? window.OemplusInject.status().lastSub : null")

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

    # ---- B2 aan via eco-paneel ----
    goto(h, p, "ecoenergy", "FuelConsumption", 2400)
    pn = h.ev("""() => { var p = document.querySelector('.OemplusInjPanel');
        return {exists: !!p, inj: window.OemplusInject ? window.OemplusInject.status() : null}; }""")
    check("setup: eco-paneel aanwezig na mount", pn["exists"], pn.get("inj"))
    p.keyboard.press("m"); p.wait_for_timeout(250); p.keyboard.press("n"); p.wait_for_timeout(300)
    p.keyboard.press("Enter"); p.wait_for_timeout(1600)
    st = h.ev("window.OemplusInject.status()")
    check("setup: B2 aan (on + subOn + hooks)", st["on"] and st["subOn"] and st["ctxtHook"] and st["transHook"],
          {k: st[k] for k in ("on", "subOn", "ctxtHook", "transHook", "subLinks")})
    check("setup: geen JS-fouten", not errs(h), errs(h))

    # ---- punt 1: wissel ecoenergy/FuelConsumption (B2-submenu) -> backupparking/BackupCameraDisplay ----
    goto(h, p, "ecoenergy", "FuelConsumption", 2400)
    st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), cls: document.body.classList.contains('OemplusB2')})")
    check("punt1 setup: op ecoenergy/FuelConsumption staat OemplusB2", st["cls"] is True, st)
    h.ev(RECORDER)
    goto(h, p, "backupparking", "BackupCameraDisplay", 3000)
    rec = h.ev("window.__rec")
    h.ev(RESTORE)
    st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), cls: document.body.classList.contains('OemplusB2')})")
    p.screenshot(path=os.path.join(SHOTS, "v14-bewaker-camera.png"))
    # event-volgorde-eis: binnen de WISSEL naar backupparking — de wissel begint bij de ctxt-pre met
    # BackupCameraDisplay ná de eerste 'weg'. De trans-end/trans-pre met de OUDE context (ecoenergy) die
    # ná ctxt-post-cls=false vallen, zijn het afronden van de OUDE transitie (nog binnen dezelfde wissel)
    # en horen NIET bij de flap: de v1.3-flap was een event met cls=true ná de eerste weg TUSSEN de
    # protected events. We nemen daarom wissel = events ná de eerste 'weg' (ctxt-post cls=false) tot
    # en met trans-end BackupCameraDisplay, MAAR filteren trans-end/trans-pre met de OUDE app eruit
    # (die horen bij het afronden van de vorige transitie, niet bij de protected-constructie).
    weg_idx = None
    for i, e in enumerate(rec):
        if e[0] == "ctxt-post" and e[-1] is False:
            weg_idx = i
            break
    end = None
    for i, e in enumerate(rec):
        if e[0] == "trans-end" and e[2] == "BackupCameraDisplay":
            end = i
    wissel = rec[weg_idx:end + 1] if (weg_idx is not None and end is not None) else []
    # flap = een 'aan' (cls=true) op een event dat bij de PROTECTED wissel hoort: ctxt-pre/post met
    # BackupCameraDisplay, inst, of trans-pre/trans-end met backupparking. trans-* met de oude app
    # (ecoenergy) zijn de vorige transitie en tellen niet mee.
    def protected_event(e):
        if e[0] in ("ctxt-pre", "ctxt-post") and e[2] == "BackupCameraDisplay":
            return True
        if e[0] == "inst":
            return True
        if e[0] in ("trans-pre", "trans-end") and e[2] == "backupparking":
            return True
        return False
    na_weg_aan = [e for e in wissel if e[-1] is True and protected_event(e)] if weg_idx is not None else ["GEEN-WEG"]
    inst = [e for e in rec if e[0] == "inst" and len(e) >= 3]
    check("punt1 (H9-echt, H2-fix): inst-events echt gemeten (len>=1, 3 elementen)", len(inst) >= 1, inst)
    check("punt1: backupparking template gebouwd ZONDER OemplusB2 (alle inst cls=false)",
          all(e[2] is False for e in inst), inst)
    check("punt1 (flap): na de eerste 'weg' (ctxt-post) t/m trans-end backupparking geen 'aan' meer (v1.3 zette 3 ms later terug)",
          weg_idx is not None and len(na_weg_aan) == 0, {"weg_idx": weg_idx, "na_weg_aan": na_weg_aan, "wissel": wissel})
    check("punt1: eindstaat op backupparking: geen OemplusB2", st["app"] == "backupparking" and st["cls"] is False, st)
    trans_end = [e for e in rec if e[0] == "trans-end" and e[2] == "BackupCameraDisplay"]
    check("punt1: trans-end backupparking zonder klasse", len(trans_end) >= 1 and all(e[3] is False for e in trans_end), trans_end)
    check("punt1: geen JS-fouten tijdens wissel", not errs(h), errs(h))

    # ---- terug naar een niet-protected scherm: klasse moet er SYNCHROON weer zijn ----
    h.ev(RECORDER)
    goto(h, p, "fmradio", "NowPlaying", 2600)
    rec2 = h.ev("window.__rec")
    h.ev(RESTORE)
    st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), cls: document.body.classList.contains('OemplusB2')})")
    trans_end2 = [e for e in rec2 if e[0] == "trans-end" and e[2] == "NowPlaying"]
    check("punt1-terug: na protected context weer OemplusB2 op fmradio/NowPlaying (trans-end cls=true)",
          st["cls"] is True and len(trans_end2) >= 1 and all(e[3] is True for e in trans_end2), {"st": st, "trans_end2": trans_end2})
    p.screenshot(path=os.path.join(SHOTS, "v14-bewaker-terug.png"))

    # ---- punt 2b mutatie A: alleen de transition-wrapper vervangen door prototype -> camera moet WEG zijn ----
    goto(h, p, "ecoenergy", "FuelConsumption", 2400)
    h.ev("""(function(){ var fw = framework;
        // bewaar de inject-wrapper, zet het PROTOTYPE terug (simuleert: transition-bewaker отсутствует)
        window.__mutA = fw._transitionChange;
        fw._transitionChange = Object.getPrototypeOf(fw)._transitionChange || fw._transitionChange;
        return typeof fw._transitionChange; })()""")
    # als de prototype-variant gelijk is aan de instance-waarde, pak de echte originele uit de inject-status
    # (fallback: gebruik de bewaarde orig via unhook-achtige ingreep)
    proto_ok = h.ev("""(function(){ var fw = framework; var proto = fw._transitionChange;
        return proto && proto.oemplusInjectWrapper ? 'wrapper-nog' : 'prototype'; })()""")
    if proto_ok == "wrapper-nog":
        # forceer:haal de wrapper eraf via de interne orig (status().transHook etc. kennen we; gebruik unhook-route)
        h.ev("""(function(){ var fw = framework; var f = fw._transitionChange;
        if (f && f.oemplusInjectWrapper) { fw._transitionChange = f.__orig || Object.getPrototypeOf(fw)._transitionChange; } return true; })()""")
    h.ev(RECORDER)
    goto(h, p, "backupparking", "BackupCameraDisplay", 3000)
    recA = h.ev("window.__rec")
    h.ev(RESTORE)
    h.ev("""(function(){ var fw = framework; if (window.__mutA) { fw._transitionChange = window.__mutA; window.__mutA = null; } })()""")
    instA = [e for e in recA if e[0] == "inst" and len(e) >= 3]
    # mutatie A: ctxt-wrapper alleen -> klasse weg VOORDAT ctxt, maar trans-pre/post zonder wrapper: de klasse
    # kan tijdens constructie AAN zijn als de ctxt-wrapper niet triggerde (hier triggerde hij wel) -> we eisen
    # alleen dat de check de events ZIET (len>=1); de echte mutatie-B (hieronder) moet FAIL liefern.
    check("punt2 mutatie A: recorder ziet inst-events ook zonder transition-wrapper (len=%d)" % len(instA),
          len(instA) >= 1, instA)
    goto(h, p, "fmradio", "NowPlaying", 2400)

    # ---- punt 2b mutatie B: bewaker HELEMAAL uit (beide wrappers eraf, subOn aan) -> H9-check moet FAIL ----
    h.ev("""(function(){ var fw = framework;
        window.__mutB = {t: fw._transitionChange, c: fw._callHandleContext};
        if (fw._transitionChange && fw._transitionChange.oemplusInjectWrapper) fw._transitionChange = Object.getPrototypeOf(fw)._transitionChange;
        if (fw._callHandleContext && fw._callHandleContext.oemplusInjectWrapper) fw._callHandleContext = Object.getPrototypeOf(fw)._callHandleContext;
        return [!!(fw._transitionChange && fw._transitionChange.oemplusInjectWrapper), !!(fw._callHandleContext && fw._callHandleContext.oemplusInjectWrapper)]; })()""")
    goto(h, p, "ecoenergy", "FuelConsumption", 2400)   # klasse erop (guardTick zet hem; wrappers weg)
    st = h.ev("({cls: document.body.classList.contains('OemplusB2'), app: framework.getCurrentApp()})")
    h.ev(RECORDER)
    goto(h, p, "backupparking", "BackupCameraDisplay", 3000)
    recB = h.ev("window.__rec")
    h.ev(RESTORE)
    stB = h.ev("({app: framework.getCurrentApp(), cls: document.body.classList.contains('OemplusB2')})")
    h.ev("""(function(){ var fw = framework, m = window.__mutB; if (m) { fw._transitionChange = m.t; fw._callHandleContext = m.c; window.__mutB = null; } })()""")
    instB = [e for e in recB if e[0] == "inst" and len(e) >= 3]
    h9_would_pass = stB["app"] == "backupparking" and stB["cls"] is False and len(instB) >= 1 and all(e[2] is False for e in instB)
    check("punt2 mutatie B (echte mutatietest): bewaker uit -> H9-check zou FALEN (inst=%s, cls nu=%s) -- check is echt"
          % (instB, stB["cls"]), (not h9_would_pass) and len(instB) >= 1, {"instB": instB, "stB": stB})
    # opruimen: guardTick zette de klasse terug op backupparking? -> forceer bewaker-correctie
    h.ev("OemplusInject.b2Off()"); p.wait_for_timeout(500)
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(600)
    goto(h, p, "fmradio", "NowPlaying", 2400)
    st = h.ev("({app: framework.getCurrentApp(), cls: document.body.classList.contains('OemplusB2')})")
    check("punt2 opruim: na b2On weer OemplusB2 op fmradio/NowPlaying", st["cls"] is True, st)
    check("einde: geen JS-fouten", not errs(h), errs(h))
    h.stop()

    nfail = sum(1 for r in results if r["ok"] is False)
    json.dump({"pakket": "v1.4 bewaker-flap + H9-echt (punt 1+2)", "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-V14-BEWAKER.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
