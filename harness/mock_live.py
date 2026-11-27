#!/usr/bin/env python3
"""mock_live.py (HOST harnas) -- mock van de Pi-service mzd-live.py op 127.0.0.1:8765.
Stdlib only. Modi (env MOCK_MODE of --mode):
  live       contract-fixture, WS push 1x/s + /live.json + /live.js (JSONP)
  oud        WS open, geen frames (of alleen /live.json leeg)
  geen       poort dicht (niets draait -> client-side fail)
  kapot      afwisselend geldige JSON, {kapot, v:2, []
  nostream   frames met age_s=40
  motoruit   rpm_schatting null (alleen contact)
  rijdend    nu.rijdend=true, kmh=62
  geenws     alleen /live.js + /live.json (geen WS-upgrade -> 400)
  segment    seg wisselt na 10 s
Fixtures: harness/fixtures/live-sample.json (synthetic) (aangevuld met rit/vorige_rit voor de paneel-pagina's).
Gebruik: python3 mock_live.py --mode live --port 8765  (draait tot stop)
"""
import json, os, sys, time, hashlib, base64, struct, threading, socketserver, re

HERE = os.path.dirname(os.path.abspath(__file__))
MZD = os.path.normpath(os.path.join(HERE, "../.."))
FIX = os.path.join(HERE, "fixtures", "live-sample.json")  # synthetic sample

def fixture():
    d = json.load(open(FIX, encoding="utf-8"))
    # contract v1-velden voor het paneel (B2DriveView leest nu/rit/vorige_rit met NL-sleutels)
    d.setdefault("nu", {})
    d["nu"].setdefault("kmh", 0.1); d["nu"].setdefault("rijdend", False)
    d["nu"]["rpm_schatting"] = 650
    d.setdefault("rit", {})
    # review v1.5: recent (laatste 2 min) bewust ANDERS dan de hele rit, zodat verwisselen opvalt
    d["rit"].update({"km": 12.3, "rijdend_min": 18.5, "schakelingen": 11, "soepel": 9, "cijfer_voorlopig": True,
                     "recent": {"soepel": 2, "schakelingen": 3, "merkbaar": 1, "hard": 0, "calm_2min": 0.82},
                     "opschakelen_rpm": 1850, "hard_optrekken": 1, "hard_remmen": 0,
                     "ruwste": {"van": "2", "naar": "3", "min": 12}})
    d.setdefault("vorige_rit", {})
    d["vorige_rit"].update({"start": "2026-01-09 17:30:00", "km": 115.1, "rijdend_min": 82,
                            "cijfer": 8.6, "trend": [8.1, 8.6],
                            "deelcijfers": {"Inkoppelen (koppeling op)": 8.2, "Gas los / koppeling in": 5.4,
                                            "Schakelmoment": 9.5, "Rustig optrekken": 8.2,
                                            "Anticiperen / remmen": 10.0, "Motorvriendelijk": 10.0,
                                            "Constante snelheid": 9.2},
                            "tip": "Laat het gas iets eerder los voor je de koppeling intrapt."})
    return d

def make(mode):
    d = fixture()
    if mode == "nostream":
        d["age_s"] = 40
    if mode == "motoruit":
        d["nu"]["rpm_schatting"] = None
    if mode == "rijdend":
        d["nu"]["rijdend"] = True; d["nu"]["kmh"] = 62.0
        d["rit"]["recent"]["calm_2min"] = 0.41
    if mode == "segment":
        pass  # seg-wissel dynamiques in handler
    return d

class H(socketserver.StreamRequestHandler):
    mode = "live"
    t0 = time.time()
    def handle(self):
        try:
            req = self.rfile.readline(4096).decode("latin1").split()
            hdr = {}
            while True:
                l = self.rfile.readline(4096).decode("latin1").strip()
                if not l: break
                k, _, v = l.partition(":")
                hdr[k.strip().lower()] = v.strip()
            if req and req[0] == "OPTIONS":
                return self.send(200, "text/plain", b"")
            self.raw_path = (req[1] if len(req) > 1 else "/")
            path = self.raw_path.split("?")[0]
            if path == "/live" and hdr.get("upgrade", "").lower() == "websocket":
                if self.mode == "geenws":
                    return self.send(400, "text/plain", b"no ws")
                return self.ws(hdr)
            if path in ("/live.json", "/live.js"):
                if self.mode == "kapot":
                    n = int(time.time()) % 4
                    body = [b"{kapot", b'{"v":2}', b"[]", json.dumps(make(self.mode)).encode()][n]
                elif self.mode == "oud":
                    body = b"{}"
                else:
                    d = make(self.mode)
                    if self.mode == "segment" and time.time() - self.t0 > 10:
                        d["seg"] = "00022-pi3e87cc70.raw"
                    body = json.dumps(d, separators=(",", ":")).encode()
                if path.endswith(".js"):
                    m_cb = re.search(r"[?&]cb=([A-Za-z0-9_.$]+)", self.raw_path if hasattr(self, "raw_path") else "")
                    cb = m_cb.group(1) if m_cb else "OemplusLiveCb"   # zoals mzd-live: ?cb= kiest de callback
                    body = ("%s(%s);" % (cb, body.decode())).encode()
                    return self.send(200, "application/javascript", body)
                return self.send(200, "application/json", body)
            if path == "/health":
                return self.send(200, "application/json", json.dumps({"versie": "mock", "mode": self.mode}).encode())
            return self.send(404, "text/plain", b"nf")
        except OSError:
            return
    def send(self, code, ct, b):
        self.wfile.write(("HTTP/1.1 %d X\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
                          "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n"
                          % (code, ct, len(b))).encode() + b)
    def ws(self, hdr):
        acc = base64.b64encode(hashlib.sha1((hdr.get("sec-websocket-key", "") + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.wfile.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                          "Sec-WebSocket-Accept: %s\r\n\r\n" % acc).encode())
        self.connection.settimeout(None)
        i = 0
        while True:
            if self.mode == "oud":
                time.sleep(60); continue
            if self.mode == "kapot":
                n = i % 4
                p = [b"{kapot", b'{"v":2}', b"[]", json.dumps(make(self.mode)).encode()][n]
            else:
                d = make(self.mode)
                if self.mode == "segment" and time.time() - self.t0 > 10:
                    d["seg"] = "00022-pi3e87cc70.raw"
                p = json.dumps(d, separators=(",", ":")).encode()
            n = len(p)
            if n < 126:
                h = bytes([0x81, n])
            elif n < 65536:
                h = bytes([0x81, 126]) + struct.pack(">H", n)
            else:
                h = bytes([0x81, 127]) + struct.pack(">Q", n)
            self.wfile.write(h + p); self.wfile.flush()
            i += 1
            time.sleep(1)

class Srv(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def state_writer(mode):
    """Schrijft elke 0,5 s de huidige live-state naar /tmp/mocklive-<mode>.json (voor het harnas via cmu.local/mocklive/)."""
    while True:
        try:
            d = make(mode)
            if mode == "segment" and time.time() - T0[0] > 10:
                d["seg"] = "00022-pi3e87cc70.raw"
            if mode == "kapot":
                n = int(time.time()) % 4
                body = [b"{kapot", b'{"v":2}', b"[]", json.dumps(d).encode()][n]
            elif mode == "oud":
                body = b"{}"
            else:
                body = json.dumps(d, separators=(",", ":")).encode()
            open("/tmp/mocklive-%s.json" % mode, "wb").write(body)
        except Exception:
            pass
        time.sleep(0.5)

T0 = [time.time()]

if __name__ == "__main__":
    a = sys.argv[1:]
    mode = a[a.index("--mode") + 1] if "--mode" in a else "live"
    port = int(a[a.index("--port") + 1]) if "--port" in a else 8765
    H.mode = mode
    import threading as _th
    _th.Thread(target=state_writer, args=(mode,), daemon=True).start()
    print("mock_live mode=%s port=%d" % (mode, port))
    Srv(("127.0.0.1", port), H).serve_forever()
