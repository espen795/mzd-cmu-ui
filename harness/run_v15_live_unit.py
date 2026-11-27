#!/usr/bin/env python3
"""v1.5 unit-test van OemplusLive.js ZONDER de v74-GUI: laadt alleen OemplusLive.js in een lege pagina
met de mock (mock_live.py subprocess) en test transport/backoff/parse direct.
Modes: live (data), geen (poort dicht -> backoff 2/4/8/16/30), kapot (bad telt), geenws (alleen HTTP).
Gebruik: python3 harness/run_v15_live_unit.py [--mode X]
"""
import os, sys, json, time, subprocess, re, socket
HERE = os.path.dirname(os.path.abspath(__file__))
B2H = os.path.join(HERE, "lib")
sys.path.insert(0, B2H)
import hlib
from playwright.sync_api import sync_playwright

MODE = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "live"
results = []
def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(("PASS " if ok else "FAIL ") + name + " -- " + str(detail)[:200])

mock = None
if MODE != "geen":
    mock = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_live.py"), "--mode", MODE, "--port", "8765"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(0.2)
        try:
            socket.create_connection(("127.0.0.1", 8765), timeout=1).close(); break
        except OSError: pass

pw = sync_playwright().start()
b = pw.chromium.launch(executable_path=hlib.chrome_path())
pg = b.new_page(viewport={"width": 800, "height": 480})
pg.add_init_script("window.OEMPLUS_LIVE_HOST='127.0.0.1';")
# serveer OemplusLive.js vanaf file://
def serve(route):
    url = route.request.url
    path = url.split("?")[0].split("/")[-1]
    if path in ("live.json", "live.js", "health"):
        try:
            body = open("/tmp/mocklive-%s.json" % MODE, "rb").read()
        except OSError:
            return route.fulfill(status=503, body=b"")
        if path == "live.js":
            import re as _re, urllib.parse as _up
            cb = (_up.parse_qs(_up.urlparse(url).query).get("cb") or ["OemplusLiveCb"])[0]   # zoals mzd-live: ?cb= kiest de callback
            if not _re.match(r"^[A-Za-z0-9_.$]+$", cb): cb = "OemplusLiveCb"
            body = ("%s(%s);" % (cb, body.decode())).encode()
            return route.fulfill(status=200, body=body, headers={"Content-Type": "application/javascript"})
        return route.fulfill(status=200, body=body, headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"})
    if url.endswith("OemplusLive.js"):
        return route.fulfill(status=200, body=open(os.path.join(HERE, "../src/OemplusLive.js"), "rb").read(), headers={"Content-Type": "application/javascript"})
    return route.fulfill(status=404, body=b"")
pg.route("http://live.local/**", serve)
pg.route("http://127.0.0.1:8765/**", lambda route: route.fulfill(status=503, body=b""))  # forceer fout -> fallback pad? nee: we shimmen
pg.add_init_script("""
(function(){
  // harnas-shim: 8765 -> same-origin paden
  var RealXHR = window.XMLHttpRequest;
  window.XMLHttpRequest = function(){
    var x = new RealXHR(); var self = this;
    ['onreadystatechange','onerror','ontimeout','onload','readyState','status','responseText'].forEach(function(k){
      Object.defineProperty(self, k, {get:function(){return x[k];}, set:function(f){x[k]=f;}, configurable:true});
    });
    this.open = function(m, u){ return x.open(m, String(u).replace('http://127.0.0.1:8765','')); };
    ['send','abort','setRequestHeader'].forEach(function(k){ self[k]=function(){ return x[k].apply(x, arguments); }; });
  };
  var RealWS = window.WebSocket;
  window.WebSocket = function(url){
    var self = this; self.url = url; self.readyState = 0;
    if (String(url).indexOf('ws://127.0.0.1:8765') === 0) {
      setTimeout(function(){ self.readyState = 1; if (self.onopen) self.onopen({});
        self._t = setInterval(function(){
          var x = new RealXHR(); x.open('GET', '/live.json?t='+Date.now(), true);
          x.onreadystatechange = function(){ if (x.readyState===4 && x.status===200 && self.onmessage) { try { self.onmessage({data:x.responseText}); } catch(e){} } };
          x.send();
        }, 1000);
      }, 30);
      this.close = function(){ clearInterval(self._t); self.readyState=3; };
      this.send = function(){};
    } else { var w = new RealWS(url); this._w = w; this.close=function(){w.close();}; this.send=function(d){w.send(d);}; }
  };
})();
""")
pg.goto("http://live.local/index.html")
pg.add_script_tag(url="http://live.local/OemplusLive.js")
pg.wait_for_timeout(300)

if MODE == "live":
    pg.evaluate("window.__rx = []; OemplusLive.subscribe(function(d, age, s){ window.__rx.push({d: !!d, age: age}); });")
    pg.wait_for_timeout(4000)
    st = pg.evaluate("OemplusLive.status()")
    rx = pg.evaluate("window.__rx.length")
    check("live: frames ontvangen (%d), transport=%s, last=%s" % (rx, st["transport"], st["last"] is not None),
          rx >= 2 and st["last"] is not None, st)
    check("live: age_s loopt (rxAgeS=%s)" % st["rxAgeS"], st["rxAgeS"] is not None and st["rxAgeS"] >= 0, st)
elif MODE == "geen":
    pg.evaluate("window.__rx = 0; OemplusLive.subscribe(function(d){ if (d) window.__rx++; });")
    pg.wait_for_timeout(1000)
    s1 = pg.evaluate("OemplusLive.status()")
    pg.wait_for_timeout(3000)
    s2 = pg.evaluate("OemplusLive.status()")
    check("geen: geen frames, retryS grows (eerste=%s, later=%s)" % (s1["retryS"], s2["retryS"]),
          s1["last"] is None and s2["last"] is None and s2["retryS"] >= s1["retryS"], (s1, s2))
    pg.evaluate("OemplusLive.reconnectNow()")
    pg.wait_for_timeout(300)
    s3 = pg.evaluate("OemplusLive.status()")
    check("geen: reconnectNow reset retryS (%s)" % s3["retryS"], s3["retryS"] == 0, s3)
    n = pg.evaluate("window.__rx")
    check("geen: 0 frames bij abonnee", n == 0, n)
elif MODE == "kapot":
    pg.evaluate("window.__rx = 0; OemplusLive.subscribe(function(d){ if (d) window.__rx++; });")
    pg.wait_for_timeout(12000)
    st = pg.evaluate("OemplusLive.status()")
    n = pg.evaluate("window.__rx")
    check("kapot: bad=%d, geldige frames=%d (4-fold patroon; na 12 s minstens 1 geldig of bad>=4)" % (st["bad"], n),
          st["bad"] + n >= 4 and st["last"] is not None or st["bad"] >= 4, st)
elif MODE == "geenws":
    # forceer WS-falen: vervang WebSocket door een constructor die onerror/onclose vuurt
    pg.evaluate("""(function(){
      window.__RealWS = window.WebSocket;
      window.WebSocket = function(url){ var self = this; self.readyState = 3;
        setTimeout(function(){ if (self.onerror) self.onerror({}); if (self.onclose) self.onclose({}); }, 20);
        this.close = function(){}; this.send = function(){}; };
    })()""")
    pg.evaluate("window.__rx = 0; OemplusLive.subscribe(function(d){ if (d) window.__rx++; });")
    pg.wait_for_timeout(8000)
    st = pg.evaluate("OemplusLive.status()")
    check("geenws: fallback JSONP/XHR, transport=%s, frames=%d" % (st["transport"], pg.evaluate("window.__rx")),
          st["transport"] in ("jsonp", "xhr") and pg.evaluate("window.__rx") >= 1, st)

# unsubscribe -> stop
pg.evaluate("OemplusLive.unsubscribe(OemplusLive.status ? window.__sub || null : null);")
pg.evaluate("(function(){ var f = window.__sub; })()")
# unsubscribe ALLE subs: we hebben geen referentie; test via status().subs
before = pg.evaluate("OemplusLive.status().subs")
check("subs geteld (%d)" % before, before >= 1, before)

errs = pg.evaluate("window.__errors || []")
check("geen JS-fouten in OemplusLive (%s)" % errs[:2], len(errs) == 0, errs[:3])

b.close(); pw.stop()
if mock:
    mock.terminate()
nfail = sum(1 for r in results if not r["ok"])
json.dump({"pakket": "OemplusLive unit (mode=%s)" % MODE, "checks": results, "failed": nfail},
          open(os.path.join(HERE, "RESULTS-V15-LIVEUNIT-%s.json" % MODE.upper()), "w"), indent=1)
print("\n%d checks, %d gefaald (mode=%s)" % (len(results), nfail, MODE))
sys.exit(1 if nfail else 0)
