#!/usr/bin/env python3
"""v1.4-harnas punt 8 (ML4): Terminal-item in Applicaties via RUNTIME-patch op de geladen systemApp.

Bewijst met B2 aan in een DRAAIENDE v74-GUI:
  - system/Applications toont een extra item met text1 "Terminal" (B2-stijl, body.OemplusB2),
  - Enter op Terminal opent een WebSocket naar ws://127.0.0.1:9997/ (gemockt via route_web_socket) en stuurt
    GEEN MMUI-event (h.mmui_out bevat geen OemplusTerminal/SelectX voor dat item),
  - een ANDER item (bv. Brandstofverbruik/ecoenergy) stuurt WEL zijn MMUI-event (SelectEcoEnergy),
  - idempotent: b2Off + b2On opnieuw -> nog steeds precies 1 terminal-item (geen dubbel),
  - bij B2 uit: item en appNames en wrapper weg (terug naar stock-aantal items).

Gebruik:  sh harness/build_root.sh && python3 harness/run_v15_terminal.py
Output:   harness/RESULTS-V15-TERMINAL.json + shots/v15-term-*.png ; exit 1 bij fail.
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
        self.ws_opened = []
    def mount(self):
        self.root = os.path.join(HERE, "root-inject")
    def _serve(self, route):
        return Harness._serve(self, route)
    def start(self):
        p = Harness.start(self)
        # mock de terminal-websocket: registreer welke ws-URLs geopend worden
        def on_ws(ws):
            self.ws_opened.append(ws.url)
            def on_msg(m): pass
            ws.on_message(on_msg)
        self.page.route_web_socket(re.compile(r"ws://127\.0\.0\.1:9997.*"), on_ws)
        return p

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

APPS_JS = """(function(){
  var sys = framework.getAppInstance('system');
  var t = sys._currentContextTemplate;
  var items = t && t.list2Ctrl && t.list2Ctrl.dataList ? t.list2Ctrl.dataList.items : [];
  var out = [];
  for (var i = 0; i < items.length; i++) out.push({i: i, text1: items[i].text1 || items[i].text1Id, appName: items[i].appData && items[i].appData.appName});
  return {ctxt: framework.getCurrCtxtId(), n: items.length, items: out,
          master: sys._masterApplicationDataList.items.length,
          cwnApps: (sys._applicationsCtxtWiseAppNames['Applications'] || []).slice(0),
          subCls: document.body.classList.contains('OemplusB2'),
          cbWrapped: !!(t && t.list2Ctrl && t.list2Ctrl.properties && t.list2Ctrl.properties.selectCallback && t.list2Ctrl.properties.selectCallback.oemplusTermWrapper)};
})()"""

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
    # stock-aantal items in Applications (vóór B2 aan)
    goto(h, p, "system", "Applications", 2600)
    pre = h.ev(APPS_JS)
    check("setup: stock Applications geladen (n=%d, geen Terminal, cb niet gewrapped)" % pre["n"],
          not any(it["appName"] == "oemplusterminal" for it in pre["items"]) and pre["cbWrapped"] is False, pre["items"])
    h.mount()
    goto(h, p, "ecoenergy", "FuelConsumption", 2400)
    p.keyboard.press("m"); p.wait_for_timeout(250); p.keyboard.press("n"); p.wait_for_timeout(300)
    p.keyboard.press("Enter"); p.wait_for_timeout(1600)
    st = h.ev("window.OemplusInject.status()")
    check("setup: B2 aan", st["on"] and st["subOn"], {k: st[k] for k in ("on", "subOn")})

    # ---- Applicaties met B2 aan: Terminal-item zichtbaar ----
    goto(h, p, "system", "Applications", 2600)
    ap = h.ev(APPS_JS)
    term = [it for it in ap["items"] if it["appName"] == "oemplusterminal"]
    check("punt8: Applications toont precies 1 Terminal-item EN 1 Rit-item (n=%d -> %d)" % (pre["n"], ap["n"]),
          len(term) == 1 and term[0]["text1"] == "Terminal" and ap["n"] == pre["n"] + 2, ap["items"])
    check("punt8: Terminal + Rit in cwn.Applications + master gegroeid (+2)",
          "oemplusterminal" in ap["cwnApps"] and "oemplusrit" in ap["cwnApps"] and ap["master"] == pre["master"] + 2, {"cwn": ap["cwnApps"], "master": ap["master"]})
    check("punt8: levende list2Ctrl selectCallback gewrapped (term OF rit)", ap["cbWrapped"] is True or h.ev("!!(framework.getAppInstance('system')._currentContextTemplate.list2Ctrl.properties.selectCallback.oemplusRitWrapper)"), ap["cbWrapped"])
    check("punt8: body.OemplusB2 aan op Applications (B2-stijl)", ap["subCls"] is True, ap["subCls"])
    p.screenshot(path=os.path.join(SHOTS, "v15-term-applicaties-aan.png"))

    # ---- Enter op Terminal: ws://127.0.0.1:9997, GEEN MMUI-event ----
    # List2Ctrl vuurt select alleen na selectStart (r.6623); focus-index lees je via _getFocussedIndex().
    h.ws_opened = []
    h.mmui_out = []
    term_idx = term[0]["i"]
    SEL = """(function(idx){
        var a = framework.getAppInstance('system'); var t = a._currentContextTemplate; var l = t.list2Ctrl;
        t.handleControllerEvent('controllerActive');
        // zet de focus exact op idx door cw te draaien todat _getFocussedIndex() == idx
        for (var k = 0; k < 40; k++) {
            if (l._getFocussedIndex() === idx) break;
            t.handleControllerEvent('cw');
        }
        var got = l._getFocussedIndex();
        t.handleControllerEvent('selectStart');
        t.handleControllerEvent('select');
        return got;
    })(%d)""" % term_idx
    foc = h.ev(SEL)
    p.wait_for_timeout(900)
    ws = [u for u in h.ws_opened if "127.0.0.1:9997" in u]
    check("punt8: Enter op Terminal (focus idx %s==%s) opent WebSocket ws://127.0.0.1:9997/ (ws=%s)" % (foc, term_idx, ws),
          foc == term_idx and len(ws) >= 1, {"foc": foc, "ws": h.ws_opened})
    p.screenshot(path=os.path.join(SHOTS, "v15-term-select.png"))
    check("punt8: Enter op Terminal stuurt GEEN MMUI-event (mmui_out=%s)" % h.mmui_out[:5],
          not any("OemplusTerminal" in m or "Terminal" in m for m in h.mmui_out), h.mmui_out[:8])

    # ---- ander item (ecoenergy) stuurt WEL zijn MMUI-event ----
    # direct via de gewrapte selectCallback (List2Ctrl vuurt 'select' alleen na 'selectStart' en mogelijk
    # alleen bij touch; de zuivere route is de properties.selectCallback zelf aanroepen zoals List2Ctrl r.5567)
    h.mmui_out = []
    eco_idx = next((it["i"] for it in ap["items"] if it["appName"] == "ecoenergy"), 0)
    h.ev("""(function(idx){
        var sys = framework.getAppInstance('system');
        var t = sys._currentContextTemplate; var l = t.list2Ctrl;
        var item = l.dataList.items[idx];
        return l.properties.selectCallback(l, item.appData, {itemIndex: idx, fromVui: false});
    })(%d)""" % eco_idx)
    p.wait_for_timeout(900)
    check("punt8: ander item (ecoenergy, idx %d) stuurt WEL MMUI-event via de callback (SelectEcoEnergy in %s)" % (eco_idx, h.mmui_out[:6]),
          any("SelectEcoEnergy" in m for m in h.mmui_out), h.mmui_out[:8])
    # en via dezelfde route het Terminal-item: GEEN mmui, WEL ws
    h.ws_opened = []
    h.mmui_out = []
    h.ev("""(function(idx){
        var sys = framework.getAppInstance('system');
        var t = sys._currentContextTemplate; var l = t.list2Ctrl;
        var item = l.dataList.items[idx];
        return l.properties.selectCallback(l, item.appData, {itemIndex: idx, fromVui: false});
    })(%d)""" % term_idx)
    p.wait_for_timeout(900)
    ws2 = [u for u in h.ws_opened if "127.0.0.1:9997" in u]
    check("punt8: Terminal via properties.selectCallback: ws=%s, mmui_out=%s (geen event)" % (ws2, h.mmui_out[:4]),
          len(ws2) >= 1 and not any("OemplusTerminal" in m for m in h.mmui_out), {"ws": h.ws_opened, "mmui": h.mmui_out[:6]})
    check("punt8: geen JS-fouten", not errs(h), errs(h))

    # ---- idempotent: b2Off + b2On opnieuw -> nog steeds 1 terminal-item ----
    # (de list2Ctrl.dataList is bij b2Off niet vervuild; we verversen de lijst via een context-wissel)
    h.ev("OemplusInject.b2Off()"); p.wait_for_timeout(700)
    goto(h, p, "system", "HomeScreen", 1800)
    goto(h, p, "system", "Applications", 2200)
    ap_off = h.ev(APPS_JS)
    check("punt8: na b2Off zijn Terminal EN Rit weg (n=%d == stock %d)" % (ap_off["n"], pre["n"]),
          ap_off["n"] == pre["n"] and "oemplusterminal" not in ap_off["cwnApps"] and "oemplusrit" not in ap_off["cwnApps"] and ap_off["cbWrapped"] is False,
          {"n": ap_off["n"], "cwn": ap_off["cwnApps"], "cb": ap_off["cbWrapped"], "master": ap_off["master"]})
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(800)
    goto(h, p, "system", "Applications", 2600)
    ap2 = h.ev(APPS_JS)
    term2 = [it for it in ap2["items"] if it["appName"] == "oemplusterminal"]
    check("punt8 idempotent: na her-aan precies 1 Terminal + 1 Rit (n=%d), master=%d (geen dubbel)" % (ap2["n"], ap2["master"]),
          len(term2) == 1 and ap2["n"] == pre["n"] + 2 and ap2["master"] == pre["master"] + 2 and sum(1 for it in ap2["items"] if it["appName"]=="oemplusrit") == 1, ap2["items"])
    # nogmaals b2On (dubbele aanroep) -> mag niet dubbel worden
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(500)
    ap3 = h.ev(APPS_JS)
    term3 = [it for it in ap3["items"] if it["appName"] == "oemplusterminal"]
    check("punt8 idempotent: dubbele b2On -> nog steeds 1 Terminal + 1 Rit (n=%d)" % ap3["n"], len(term3) == 1 and sum(1 for it in ap3["items"] if it["appName"]=="oemplusrit") == 1, ap3["items"])
    p.screenshot(path=os.path.join(SHOTS, "v15-term-applicaties-aan2.png"))
    check("einde: geen JS-fouten", not errs(h), errs(h))
    h.stop()

    nfail = sum(1 for r in results if r["ok"] is False)
    json.dump({"pakket": "v1.4 punt 8 Terminal-item in Applicaties (runtime-patch)", "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-V15-TERMINAL.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
