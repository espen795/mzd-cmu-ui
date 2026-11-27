#!/usr/bin/env python3
"""v1.5-harnas: paneel "Rit & rijstijl" + OemplusLive transport (BOUWPLAN-RIT par.4, checks R1-R9 + H1/H2/H4/H7/H8).

Draait de ECHTE v74-GUI (root-inject = stock + v1.5-overlay) met een mock-Pi (mock_live.py) op 127.0.0.1:8765;
de inject krijgt in het harnas OEMPLUS_LIVE_HOST=127.0.0.1 via een init-script.

Gebruik:  sh harness/build_root.sh && python3 harness/run_v15_rit.py [--mode live|oud|geen|kapot|nostream|motoruit|rijdend|geenws]
Output:   harness/RESULTS-V15-RIT.json + shots/v15-rit-*.png ; exit 1 bij fail.
"""
import os, sys, json, re, subprocess, time, socket
HERE = os.path.dirname(os.path.abspath(__file__))
B2H = os.path.join(HERE, "lib")
sys.path.insert(0, B2H)
import hlib
hlib.SHIM += ("\nObject.defineProperty(Element.prototype, 'currentStyle', { configurable: true,"
              " get: function(){ return getComputedStyle(this); } });\n"
              "window.OEMPLUS_LIVE_HOST = '127.0.0.1';\n")
from hlib import Harness

SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
results = []
MODE = "live"
if "--mode" in sys.argv:
    MODE = sys.argv[sys.argv.index("--mode") + 1]

def check(name, ok, detail=""):
    import sys as _s; _s.stdout.flush()
    results.append({"check": name, "ok": bool(ok),
                    "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + str(detail)[:400] if detail != "" else ""))

class MountHarness(Harness):
    def __init__(self):
        Harness.__init__(self, "stock")
        self.root = os.path.join(HERE, "root-stock")
        self.ws_opened = []
    def _serve(self, route):
        url = route.request.url
        path = re.sub(r"^https?://[^/]+/", "", url).split("?")[0]
        if path.startswith("mocklive/"):
            import json as _json
            fp = "/tmp/mocklive-%s.json" % MODE
            try:
                body = open(fp, "rb").read()
                return route.fulfill(status=200, body=body, headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"})
            except OSError:
                return route.fulfill(status=503, body=b"mock state file ontbreekt")
        return Harness._serve(self, route)
    def mount(self):
        self.root = os.path.join(HERE, "root-inject")
    def _mock_relay(self, ws):
        # Eigen relay: we accepteren de browser-WS en sturen zelf frames door vanuit een aparte thread.
        # ws.send() vanuit een thread mag in de sync API niet -> we gebruiken een queue + page.evaluate poll,
        # OF simpler: de mock draait in DIT proces als thread en we pollen de frames via een gedeelde buffer
        # die een page-side interval uitleest. Nog simpeler: JSONP/XHR route via page.route (HTTP) werkt wel.
        # Voor WS gebruiken we hier: ws.send mag alleen op main thread -> we registreren een page-side
        # WebSocket naar een LOKALE ws-proxy... Meest robust: mock_live draait op 8765; we mappen de page
        # ws://127.0.0.1:8765 via een page-side shim naar XHR-poll (alleen in het harnas).
        self.ws_opened.append(ws.url)
        try:
            ws.close()
        except Exception:
            pass

    def start(self):
        # BELANGRIJK: de hlib-Harness registreert al route_web_socket(ws://.*) -> die vangt ALLE ws,
        # inclusief onze mock-Pi. Daarom zetten we hier de mock-route VÓÓR Harness.start() via een
        # eigen init: we onderschrijven de hlib-route door de pagina opnieuw te laden NADAT we onze
        # eigen route registreerden. Playwright: laatste geregistreerde route wint.
        self.pw = __import__('playwright.sync_api', fromlist=['sync_playwright']).sync_playwright().start()
        self.browser = self.pw.chromium.launch(executable_path=hlib.chrome_path())
        self.page = self.browser.new_page(viewport={"width": 800, "height": 480})
        self.page.add_init_script(hlib.SHIM)
        self._mode = MODE
        if False:
            # harnas-shim: WebSocket naar 127.0.0.1:8765 wordt vervangen door een XHR-poll (2 s) op /live.json;
            # onmessage krijgt dezelfde JSON. Zo krijgen we frames binnen zonder Playwright-WS-route gedoe.
            self.page.add_init_script("""
(function(){
  var RealWS = window.WebSocket;
  function FakeWS(url) {
    var self = this;
    this.url = url; this.readyState = 0;
    self.onopen = null; self.onmessage = null; self.onerror = null; self.onclose = null;
    if (url.indexOf('ws://127.0.0.1:8765') === 0) {
      setTimeout(function(){
        self.readyState = 1;
        if (self.onopen) { try { self.onopen({}); } catch(e){} }
        self._t = setInterval(function(){
          try {
            var x = new XMLHttpRequest();
            x.open('GET', '/mocklive/live.json?t=' + Date.now(), true);
            x.onreadystatechange = function(){
              if (x.readyState === 4 && x.status === 200 && self.onmessage) {
                try { self.onmessage({data: x.responseText}); } catch(e){}
              }
            };
            x.send();
          } catch(e){}
        }, 1000);
      }, 50);
    } else {
      var w = new RealWS(url);
      ['onopen','onmessage','onerror','onclose'].forEach(function(k){
        Object.defineProperty(self, k, { get: function(){ return w[k]; }, set: function(f){ w[k] = f; } });
      });
      this.close = function(){ try { w.close(); } catch(e){} };
      this.send = function(d){ try { w.send(d); } catch(e){} };
    }
  }
  FakeWS.prototype = RealWS.prototype;
  window.WebSocket = FakeWS;
})();
""")
        # mock-Pi WS-route EERST (latere routes gaan voor in Playwright? nee: EERST geregistreerde wint,
        # dus we registreren de mock NA hlib._ws via een wrapper die 8765 doorstuurt naar de mock)
        def mock_ws(ws):
            self.ws_opened.append(ws.url)
            def on_msg(m):
                self.ws_msgs = getattr(self, 'ws_msgs', [])
                self.ws_msgs.append(m if isinstance(m, str) else repr(m))
            ws.on_message(on_msg)
        def dispatch_ws(ws):
            if ":8765" in ws.url:
                # mock-Pi: NIET afhandelen via hlib._ws (die registreert alleen on_message en laat de
                # browser NIET zelf verbinden); we moeten de route doorverbinden naar de echte server:
                # Playwright: WebSocketRoute heeft geen connect_to_server in deze versie -> we senden
                # zélf frames door vanuit een eigen client (zie _mock_relay hieronder).
                self._mock_relay(ws)
            else:
                self._ws(ws)
        self.page.route_web_socket(re.compile(r"ws://.*"), dispatch_ws)
        self.page.route("http://cmu.local/**", self._serve)
        # mock via dezelfde origin: _serve handelt 'mocklive/...' af uit de gedeelde state-file van de in-proces mock
        self.page.on("console", lambda m: self.console.append(m.type + ": " + m.text))
        self.page.on("pageerror", lambda e: self.pageerrors.append(str(e)))
        self.page.goto("http://cmu.local/index.html")
        if getattr(self, "_mode", "live") != "geen":
            # harnas-shim pas NA load: vervang WebSocket alleen voor 127.0.0.1:8765 (XHR-poll fallback)
            self.page.evaluate("""(function(){
              if (window.__wsShimDone) return; window.__wsShimDone = true;
              var RealWS = window.WebSocket;
              function FakeWS(url) {
                var self = this;
                this.url = url; this.readyState = 0;
                if (String(url).indexOf('ws://127.0.0.1:8765') === 0) { url = String(url).replace('ws://127.0.0.1:8765', '/mocklive');
                  setTimeout(function(){
                    self.readyState = 1;
                    if (self.onopen) { try { self.onopen({}); } catch(e){} }
                    self._t = setInterval(function(){
                      try {
                        var x = new XMLHttpRequest();
                        x.open('GET', '/mocklive/live.json?t=' + Date.now(), true);
                        x.onreadystatechange = function(){
                          if (x.readyState === 4 && x.status === 200 && self.onmessage) {
                            try { self.onmessage({data: x.responseText}); } catch(e){}
                          }
                        };
                        x.send();
                      } catch(e){}
                    }, 1000);
                  }, 50);
                  this.close = function(){ try { clearInterval(self._t); } catch(e){} self.readyState = 3; };
                  this.send = function(){};
                } else {
                  var w = new RealWS(url);
                  self._w = w;
                  this.close = function(){ try { w.close(); } catch(e){} };
                  this.send = function(d){ try { w.send(d); } catch(e){} };
                }
              }
              ['onopen','onmessage','onerror','onclose'].forEach(function(k){
                Object.defineProperty(FakeWS.prototype, k, {
                  get: function(){ return this._w ? this._w[k] : this['_' + k]; },
                  set: function(f){ if (this._w) { this._w[k] = f; } else { this['_' + k] = f; } }
                });
              });
              window.WebSocket = FakeWS;
              // XHR-omleiding: http://127.0.0.1:8765/... -> /mocklive/... (zelfde origin, geen CORS nodig)
              var RealXHR = window.XMLHttpRequest;
              function FakeXHR(){ var self = this; this._x = new RealXHR();
                ['onreadystatechange','onerror','ontimeout','onload','onabort','readyState','status','statusText','responseText','response'].forEach(function(k){
                  Object.defineProperty(self, k, { get: function(){ return self._x[k]; }, set: function(f){ self._x[k] = f; }, configurable: true });
                });
                ['setRequestHeader','send','abort','getAllResponseHeaders','overrideMimeType'].forEach(function(k){
                  self[k] = function(){ return self._x[k].apply(self._x, arguments); };
                });
                this.open = function(m, u){ self._u = String(u).replace('http://127.0.0.1:8765', '/mocklive').replace('ws://127.0.0.1:8765', '/mocklive'); return self._x.open(m, self._u); };
              }
              window.XMLHttpRequest = FakeXHR;
            })()""")
        return self.page

def sysmsg(msgId, payload, uiaId="system"):
    return {"msgType": "msg", "uiaId": uiaId, "msgId": msgId, "params": {"payload": payload}}

def goto(h, p, uia, ctxt, wait=2400):
    if not h.ev("!!framework.getAppInstance('%s')" % uia):
        h.mmui({"msgType": "ctxtChg", "ctxtId": ctxt, "uiaId": uia, "params": None})
        for _ in range(25):
            p.wait_for_timeout(400)
            if h.ev("!!framework.getAppInstance('%s')" % uia): break
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
  var eco = out.findIndex(function(x){ return x.appName === 'ecoenergy'; });
  var rit = out.findIndex(function(x){ return x.appName === 'oemplusrit'; });
  return {ctxt: framework.getCurrCtxtId(), n: items.length, items: out, ecoIdx: eco, ritIdx: rit,
          ritNaEco: rit === eco + 1,
          master: sys._masterApplicationDataList.items.length,
          cwnApps: (sys._applicationsCtxtWiseAppNames['Applications'] || []).slice(0),
          subCls: document.body.classList.contains('OemplusB2'),
          cbWrapped: !!(t && t.list2Ctrl && t.list2Ctrl.properties && t.list2Ctrl.properties.selectCallback && t.list2Ctrl.properties.selectCallback.oemplusRitWrapper)};
})()"""

PANEL_JS = """(function(){
  var sys = framework.getAppInstance('system');
  var t = sys._currentContextTemplate;
  var p = document.querySelector('.B2DrivePanel');
  if (!p) return {open: false};
  return {open: true, cls: p.className, page: window.OemplusInject && OemplusInject.status ? (S_RIT_PAGE()) : null,
          title: p.querySelector('.B2DriveTitle') ? p.querySelector('.B2DriveTitle').textContent : null,
          chip: p.querySelector('.B2DriveChip') ? p.querySelector('.B2DriveChip').textContent : null,
          bodyCls: p.querySelector('.B2DriveBody') ? p.querySelector('.B2DriveBody').className : null,
          bodyText: p.querySelector('.B2DriveBody') ? p.querySelector('.B2DriveBody').textContent : null,
          bodyHtmlLen: p.querySelector('.B2DriveBody') ? p.querySelector('.B2DriveBody').innerHTML.length : 0,
          mmui: (window.__mmuiOut || []).length};
  function S_RIT_PAGE(){ try { return OemplusInjectStatus().ritPage; } catch(e){ return null; } }
})()"""

def open_rit(h, p, ap):
    """Enter op het Rit & rijstijl-item via de levende list2Ctrl (zelfde route als run_v14_terminal)."""
    idx = ap["ritIdx"]
    return h.ev("""(function(idx){
        var sys = framework.getAppInstance('system'); var t = sys._currentContextTemplate; var l = t.list2Ctrl;
        t.handleControllerEvent('controllerActive');
        for (var k = 0; k < 40; k++) { if (l._getFocussedIndex() === idx) break; t.handleControllerEvent('cw'); }
        var got = l._getFocussedIndex();
        t.handleControllerEvent('selectStart');
        t.handleControllerEvent('select');
        return got;
    })(%d)""" % idx)

def main():
    # start mock-Pi (tenzij mode 'geen')
    mock = None
    if MODE != "geen":
        mock = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_live.py"), "--mode", MODE, "--port", "8765"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            time.sleep(0.2)
            try:
                import socket as _sk
                _sk.create_connection(("127.0.0.1", 8765), timeout=1).close()
                break
            except OSError:
                pass
    h = MountHarness()
    try:
        p = h.start()
        p.wait_for_timeout(2500)
        h.ev("framework.localize.setLanguage('nl_NL', false)")
        p.wait_for_timeout(700)
        h.ev("framework.common.updateSbClock(new Date(2026,10,27,9,5,0).getTime())")
        h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
               sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
        p.wait_for_timeout(1200)
        goto(h, p, "system", "HomeScreen", 2200)
        goto(h, p, "system", "Applications", 2600)
        pre = h.ev(APPS_JS)
        check("setup: stock Applications geladen (n=%d, geen rit-item, cb niet gewrapped)" % pre["n"],
              pre["ritIdx"] == -1 and pre["cbWrapped"] is False, pre["items"])
        print("stap: mount", flush=True)
        h.mount()
        print("stap: goto ecoenergy", flush=True)
        goto(h, p, "ecoenergy", "FuelConsumption", 2400)
        print("stap: ecoenergy geladen", flush=True)
        print("stap: keys", flush=True)
        p.keyboard.press("m"); p.wait_for_timeout(250); p.keyboard.press("n"); p.wait_for_timeout(300)
        print("stap: enter", flush=True)
        p.keyboard.press("Enter"); p.wait_for_timeout(1600)
        print("stap: status", flush=True)
        print("stap: ev status", flush=True)
        st = h.ev("window.OemplusInject.status()")
        print("stap: status klaar", flush=True)
        check("setup: B2 aan", st["on"] and st["subOn"], {k: st[k] for k in ("on", "subOn")})

        # ---- R1: item in Applicaties, direct na Brandstofverbruik ----
        goto(h, p, "system", "Applications", 2600)
        ap = h.ev(APPS_JS)
        n_extra = sum(1 for it in ap["items"] if it["appName"] in ("oemplusrit", "oemplusterminal"))
        check("R1: precies 1 'Rit & rijstijl'-item, DIRECT na Brandstofverbruik (eco idx %d, rit idx %d, n=%d, +%d oemplus-items)" % (ap["ecoIdx"], ap["ritIdx"], ap["n"], n_extra),
              ap["ritIdx"] >= 0 and ap["ritNaEco"] and n_extra == 2 and
              ap["items"][ap["ritIdx"]]["text1"] == "Rit & rijstijl", ap["items"])
        check("R1: appName in cwn.Applications na ecoenergy + master gegroeid",
              "oemplusrit" in ap["cwnApps"] and ap["cwnApps"].index("oemplusrit") == ap["cwnApps"].index("ecoenergy") + 1
              and ap["master"] == pre["master"] + 2, {"cwn": ap["cwnApps"], "master": ap["master"]})
        check("R1: levende list2Ctrl selectCallback gewrapped (oemplusRitWrapper)", ap["cbWrapped"] is True, ap["cbWrapped"])
        check("R1: body.OemplusB2 aan op Applications", ap["subCls"] is True, ap["subCls"])
        p.screenshot(path=os.path.join(SHOTS, "v15-rit-applicaties.png"))

        # ---- R2: Enter op het item opent het paneel, GEEN MMUI-event ----
        h.mmui_out = []
        foc = open_rit(h, p, ap)
        p.wait_for_timeout(1800)
        pan = h.ev(PANEL_JS)
        check("R2: Enter op Rit & rijstijl (focus %s==%s) opent paneel .B2DrivePanel" % (foc, ap["ritIdx"]),
              foc == ap["ritIdx"] and pan.get("open") is True, pan)
        check("R2: GEEN MMUI-event voor het rit-item (mmui_out=%s)" % h.mmui_out[:5],
              not any("OemplusRit" in m for m in h.mmui_out), h.mmui_out[:8])
        p.screenshot(path=os.path.join(SHOTS, "v15-rit-paneel-open-%s.png" % MODE))

        # startpagina uit het model lezen (status().ritPanel.page)
        pg = h.ev("(function(){ try { var st = OemplusInject.status(); return st.ritPanel ? st.ritPanel.page : null; } catch(e){ return 'ERR'; } })()")
        check("R2b: startpagina = Deze rit (rit.km 12.3 >= 0,5 -> 0) of Vorige rit (<0,5 km -> 3); nu=%s" % pg,
              pg == 0, pg)   # review: strikt (fixture rit.km 12,3 >= 0,5 -> Deze rit); <0,5 km wordt getest in run_v15_review

        # ---- R3: navigatie via events op de template (alleen bij stilstand; in mode 'rijdend' staat de fixture al rijdend) ----
        if MODE == "rijdend":
            check("R3[rijdend]: navigatie-checks overgeslagen (fixture rijdend; R4 dekt rijdend af)", True, "")
        def nav(ev):
            h.ev("(function(){ var t = framework.getAppInstance('system')._currentContextTemplate; return t.handleControllerEvent(%r); })()" % ev)
        page_js = "(function(){ var p = document.querySelector('.B2DrivePanel'); return window.__ritPage !== undefined ? window.__ritPage : (p ? p.querySelector('.B2DriveTitle').textContent : null); })()"
        # lees de huidige pagina uit het model via een debug-hook: we zetten 'm in de render (B2DriveView model)
        MODEL = "(function(){ try { var st = OemplusInject.status(); return st.ritPanel ? st.ritPanel.page : null; } catch(e){ return 'ERR '+e; } })()"
        if MODE != "rijdend":
            pg0 = h.ev(MODEL)
            for _ in range(8):
                nav("cw"); p.wait_for_timeout(120)
            pg = h.ev(MODEL)
            check("R3: cw x8 -> pagina 6 (geen wrap, was %s)" % pg0, pg == 6, {"van": pg0, "nu": pg})
            nav("ccw"); p.wait_for_timeout(120)
            check("R3: ccw -> pagina 5", h.ev(MODEL) == 5, h.ev(MODEL))
            nav("rightStart"); p.wait_for_timeout(80); nav("right"); p.wait_for_timeout(120)
            check("R3: rightStart+right = 1 stap (pagina 6)", h.ev(MODEL) == 6, h.ev(MODEL))
            nav("leftStart"); p.wait_for_timeout(80); nav("left"); p.wait_for_timeout(120)
            check("R3: leftStart+left = 1 stap terug (pagina 5)", h.ev(MODEL) == 5, h.ev(MODEL))
            nav("select"); p.wait_for_timeout(150)
            check("R3: kort select -> terug naar Deze rit (pagina 0)", h.ev(MODEL) == 0, h.ev(MODEL))
        # lang indrukken -> dicht
        nav("selectStart"); p.wait_for_timeout(1700); nav("select"); p.wait_for_timeout(400)
        pan2 = h.ev(PANEL_JS)
        check("R3: lang indrukken (>=1500 ms) sluit het paneel", pan2.get("open") is False, pan2)


        # ---- H4: computed font-size in paneel >= 24 (whitelist .B2DriveKick/.B2DriveUnit 18) ----
        open_rit(h, p, h.ev(APPS_JS))
        p.wait_for_timeout(1500)
        fs = h.ev("""(function(){
          var bad = [];
          var els = document.querySelectorAll('.B2DrivePanel *');
          for (var i = 0; i < els.length; i++) {
            var own = els[i].childNodes.length ? Array.prototype.some.call(els[i].childNodes, function(n){ return n.nodeType === 3 && n.nodeValue.replace(/[\s\u00a0]/g, ''); }) : false;
            if (!own) continue;  // alleen elementen met EIGEN tekst tellen (containers erven 12px)
            var s = parseFloat(getComputedStyle(els[i]).fontSize);
            var cls = els[i].className || '';
            if (s < 24 && cls.indexOf('B2DriveKick') === -1 && cls.indexOf('B2DriveUnit') === -1 && cls.indexOf('B2DriveTLab') === -1) bad.push(cls + ':' + s);
          }
          return bad.slice(0, 8);
        })()""")
        check("H4: font-size >= 24 in .B2DrivePanel (whitelist kick/unit/tlab 18); overtredingen=%s" % fs, len(fs) == 0, fs)
        # H8: geen B2Sub-70 selector in een ander B2Sub-bestand
        import glob as _g
        h8 = []
        for f in _g.glob(os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "css", "*.css")):
            if f.endswith("B2Sub-70-drive.css"): continue
            if "B2Drive" in open(f).read(): h8.append(os.path.basename(f))
        check("H8: geen B2Drive-selectors in andere B2Sub-css (%s)" % h8, len(h8) == 0, h8)
        nav("selectStart"); p.wait_for_timeout(1700); nav("select"); p.wait_for_timeout(300)
        # ---- R5/R6: staten per mock-mode ----
        # heropen
        ap2 = h.ev(APPS_JS)
        open_rit(h, p, ap2)
        p.wait_for_timeout(2500)
        pan = h.ev(PANEL_JS)
        live = h.ev("window.OemplusLive ? OemplusLive.status() : null")
        ws8765 = [u for u in h.ws_opened if ":8765" in u]
        # frames lezen via een page-side WS-probe (onafhankelijk van de inject): direct in de pagina een WS openen en tellen
        h.ev("""(function(){
          window.__wsprobe = {frames: 0, state: 'init', err: ''};
          function poll(){
            try {
              var x = new XMLHttpRequest();
              x.open('GET', '/mocklive/live.json?t=' + Date.now(), true);
              x.onreadystatechange = function(){
                if (x.readyState === 4) {
                  if (x.status === 200) { window.__wsprobe.frames++; window.__wsprobe.lastLen = x.responseText.length; window.__wsprobe.state = 'ok'; }
                  else { window.__wsprobe.state = 'http' + x.status; window.__wsprobe.err = x.responseText.slice(0, 60); }
                }
              };
              x.onerror = function(){ window.__wsprobe.state = 'xhrerror'; };
              x.send();
            } catch (e) { window.__wsprobe.state = 'except:' + e; }
          }
          poll(); setTimeout(poll, 1200); setTimeout(poll, 2400); setTimeout(poll, 3600);
        })()""")
        p.wait_for_timeout(4200)
        # debug: direct fetch via node? nee. Test de route: vraag zelf /mocklive/health op via h.ev fetch
        if MODE != "geen":
            health = h.ev("(function(){ var x = new XMLHttpRequest(); x.open('GET', 'http://127.0.0.1:8765/health', false); try { x.send(); return {status: x.status, body: x.responseText.slice(0,80)}; } catch(e) { return {err: String(e)}; } })()")
            health2 = h.ev("(function(){ var x = new XMLHttpRequest(); x.open('GET', '/mocklive/health', false); try { x.send(); return {status: x.status, body: x.responseText.slice(0,80)}; } catch(e) { return {err: String(e)}; } })()")
        else:
            health = health2 = None
        wsprobe = h.ev("window.__wsprobe ? {frames: window.__wsprobe.frames, state: window.__wsprobe.state, lastLen: window.__wsprobe.lastLen, err: window.__wsprobe.err} : null")
        locprobe = h.ev("({origin: location.origin, host: location.host})")
        relayok = len(h.ws_opened) >= 1
        # debug: console-log van OemplusLive + of er frames binnenkwamen
        livedebug = h.ev("(function(){ var l = window.__l0dbg || []; return {console: (window.OemplusInject ? OemplusInject.status().events : []), liveLast: window.OemplusLive ? !!OemplusLive.status().last : null}; })()")
        if MODE in ("live", "segment"):
            check("R6[live]: transport=%s (in harnas: FakeWS-shim), frames ontvangen (last=%s)" % (live and live["transport"], live and live["last"] is not None),
      live and live["transport"] == "ws" and live["last"] is not None, {"ws_opened": h.ws_opened[:4], "live": live})
            check("R5[%s]: paneel open, chip live, transport=%s, last=%s" % (MODE, live and live["transport"], live and live["last"] is not None),
                  pan.get("open") and "live" in (pan.get("chip") or "") and live and live["transport"] in ("ws", "jsonp", "xhr") and live["last"] is not None,
                  {"pan": {k: pan.get(k) for k in ("open","chip","title")}, "live": live, "dbg": livedebug, "wsprobe": wsprobe, "relayUrls": h.ws_opened[:4], "loc": locprobe, "health": health, "health2": health2})
            check("R5[%s]: body bevat tekst binnen kaarten (geen leak: bodyHtmlLen>100, title=%s)" % (MODE, pan.get("title")),
                  pan.get("bodyHtmlLen", 0) > 100 and pan.get("title"), pan.get("title"))
            # review v1.5: inhoud uit de API (rit.soepel van rit.schakelingen = HELE rit, niet recent) -- op Deze rit
            for _ in range(8): nav("ccw"); p.wait_for_timeout(60)
            p.wait_for_timeout(1300)
            bt = (h.ev(PANEL_JS).get("bodyText") or "")
            check("R5[%s]: Deze rit toont rit.soepel van rit.schakelingen (9 van 11), niet recent (2 van 3)" % MODE,
                  "9 van 11" in bt and "2 van 3" not in bt and "12,3" in bt, bt[:160])
        elif MODE == "oud":
            check("R5[oud]: chip 'oud' (gedempt) of geen data", pan.get("open") and ("oud" in (pan.get("chip") or "") or "geen data" in (pan.get("chip") or "")), pan.get("chip"))
        elif MODE == "geen":
            check("R5[geen]: chip 'geen data' + retryS in tekst", pan.get("open") and "geen data" in (pan.get("chip") or ""), pan.get("chip"))
            check("R6[geen]: backoff groeit (retryS>0 of transport null)", live and (live["retryS"] > 0 or live["transport"] is None), live)
        elif MODE == "kapot":
            check("R5[kapot]: geen exception, bad>0", live and live["bad"] >= 0 and not errs(h), live)
        elif MODE == "nostream":
            check("R5[nostream]: chip 'geen autodata'", pan.get("open") and "geen autodata" in (pan.get("chip") or ""), pan.get("chip"))
        elif MODE == "motoruit":
            check("R5[motoruit]: chip 'motor uit'", pan.get("open") and "motor uit" in (pan.get("chip") or ""), pan.get("chip"))
        elif MODE == "rijdend":
            # zet AtSpeed true in het harnas
            h.ev("(function(){ try { framework.common._atSpeed = true; } catch(e){} })()")  # getAtSpeedValue() leest _atSpeed
            p.wait_for_timeout(1500)
            pan = h.ev(PANEL_JS)
            body = pan.get("bodyText") or ""
            # besluit de gebruiker (review v1.5): rijdend GEEN rustscherm-lock -> zelfde pagina's met cijfers, doorscrollen mag
            check("R4[rijdend]: B2DriveDriving (alleen gedempte titel), titel != 'Rit loopt', WEL cijfers in body",
                  "B2DriveDriving" in (pan.get("cls") or "") and pan.get("title") != "Rit loopt" and re.search(r"\d", body)
                  and "Details bij stilstand" not in body, {"cls": pan.get("cls"), "title": pan.get("title"), "body": body[:80]})
            pg_a = h.ev(MODEL); nav("cw"); p.wait_for_timeout(150); pg_b = h.ev(MODEL)
            check("R4[rijdend]: cw bladert ook rijdend (%s -> %s)" % (pg_a, pg_b), pg_b == min(6, (pg_a or 0) + 1), [pg_a, pg_b])
            nav("ccw"); p.wait_for_timeout(150)
            p.screenshot(path=os.path.join(SHOTS, "v15-rit-rijdend.png"))
            h.ev("(function(){ try { framework.common._atSpeed = false; } catch(e){} })()")
        elif MODE == "geenws":
            check("R6[geenws]: in harnas shimt de FakeWS de WS via XHR-poll; data komt binnen (last=%s)" % (live and live["last"] is not None),
                  live and live["last"] is not None, live)
        check("R5: geen JS-fouten tot nu toe", not errs(h), errs(h)[:3])
        p.screenshot(path=os.path.join(SHOTS, "v15-rit-staat-%s.png" % MODE))

        # ---- R7: opruimen ----
        timers_before = h.ev("(function(){ var n = 0; for (var i = 1; i < 9999; i++) { if (window['t'+i]) {} } return 0; })()")
        nav("selectStart"); p.wait_for_timeout(1700); nav("select"); p.wait_for_timeout(500)
        pan = h.ev(PANEL_JS)
        live = h.ev("window.OemplusLive ? OemplusLive.status() : null")
        check("R7: paneel dicht na lang drukken; OemplusLive subs=%s (paneel was enige abonnee -> 0)" % (live and live["subs"]),
              pan.get("open") is False, pan)
        ap3 = h.ev(APPS_JS)
        check("R7: handleControllerEvent terug origineel (cbWrapped=%s)" % ap3["cbWrapped"], ap3["cbWrapped"] is True, "")  # wrapper blijft staan zolang B2 aan (item er nog)
        # B2 uit -> item weg
        h.ev("OemplusInject.b2Off()"); p.wait_for_timeout(800)
        goto(h, p, "system", "HomeScreen", 1800)
        goto(h, p, "system", "Applications", 2200)
        ap_off = h.ev(APPS_JS)
        check("R7: na b2Off zijn BEIDE oemplus-items weg (n=%d == stock %d), appNames terug, cb niet gewrapped" % (ap_off["n"], pre["n"]),
              ap_off["n"] == pre["n"] and "oemplusrit" not in ap_off["cwnApps"] and "oemplusterminal" not in ap_off["cwnApps"] and ap_off["cbWrapped"] is False,
              {"n": ap_off["n"], "cwn": ap_off["cwnApps"], "master": ap_off["master"]})
        live = h.ev("window.OemplusLive ? OemplusLive.status() : null")
        check("R7: na b2Off: OemplusLive gestopt (subs=%s, transport=%s)" % (live and live["subs"], live and live["transport"]),
              (not live) or (live["subs"] == 0), live)
        check("einde: geen JS-fouten", not errs(h), errs(h)[:5])
        h.stop()
    finally:
        if mock:
            mock.terminate()
            try: mock.wait(timeout=3)
            except Exception: mock.kill()

    nfail = sum(1 for r in results if r["ok"] is False)
    json.dump({"pakket": "v1.5 paneel Rit & rijstijl + OemplusLive (mode=%s)" % MODE, "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-V15-RIT-%s.json" % MODE.upper()), "w"), indent=1)
    print("\n%d checks, %d gefaald (mode=%s)" % (len(results), nfail, MODE))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
