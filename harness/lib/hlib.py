"""Gedeelde harnas-helpers: laadt de échte v74-GUI (root-*) in Chromium met nep-MMUI-websockets.
- Bestanden worden via page.route uit root-<mode>/ geserveerd onder http://cmu.local/.
- CSS: -o-transition/-o-transform/-o-transform-origin worden voor Chromium unprefixed (Presto-gedrag nabootsen).
- JS-shim: 'OTransitionEnd' -> 'transitionend' (Presto-eventnaam).
- Websockets (MMUI 2700, AppSDK 2800, DBAPI 2766) worden lokaal geaccepteerd; GUI->MMUI-berichten worden gelogd.
"""
import os, re, json, mimetypes, glob
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))

def chrome_path():
    c = sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell")))
    return c[-1] if c else None

SHIM = r"""
(function(){
  window.opera = { version: function(){ return '12.10'; }, postError: function(){} };
  var add = EventTarget.prototype.addEventListener, rem = EventTarget.prototype.removeEventListener;
  function map(t){ return t === 'OTransitionEnd' || t === 'oTransitionEnd' ? 'transitionend' : t; }
  EventTarget.prototype.addEventListener = function(t, f, c){ return add.call(this, map(t), f, c); };
  EventTarget.prototype.removeEventListener = function(t, f, c){ return rem.call(this, map(t), f, c); };
  window.__errors = [];
  window.addEventListener('error', function(e){ window.__errors.push(String(e.message) + ' @' + e.filename + ':' + e.lineno); });
  document.addEventListener('DOMContentLoaded', function(){
    var s = document.createElement('style');
    s.textContent = "@font-face{font-family:'Tipperary';src:url(/_harness_fonts/Tipperary.ttf)}" +
                    "@font-face{font-family:'Tipperary Semibold';src:url(/_harness_fonts/TipperarySemibold.ttf)}" +
                    "@font-face{font-family:'TipperarySemibold';src:url(/_harness_fonts/TipperarySemibold.ttf)}" +
                    "body{-webkit-font-smoothing:antialiased}";
    document.head.appendChild(s);
  });
})();
"""

class Harness:
    def __init__(self, mode="overlay"):
        self.root = os.path.join(HERE, "root-" + mode)
        self.mmui_out = []
        self.console = []
        self.pageerrors = []
        self.missing = []

    def _serve(self, route):
        url = route.request.url
        path = re.sub(r"^https?://[^/]+/", "", url).split("?")[0]
        fp = os.path.normpath(os.path.join(self.root, path))
        if not fp.startswith(self.root) or not os.path.isfile(fp):
            self.missing.append(path)
            return route.fulfill(status=404, body="")
        ctype = mimetypes.guess_type(fp)[0] or "application/octet-stream"
        data = open(fp, "rb").read()
        if fp.endswith(".css"):
            txt = data.decode("utf-8", "replace")
            txt = re.sub(r"-o-(transition|transform|transform-origin)\b", r"\1", txt)
            data = txt.encode()
            ctype = "text/css"
        return route.fulfill(status=200, body=data, headers={"Content-Type": ctype})

    def _ws(self, ws):
        def on_msg(m):
            self.mmui_out.append(m if isinstance(m, str) else repr(m))
        ws.on_message(on_msg)

    def start(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(executable_path=chrome_path())
        self.page = self.browser.new_page(viewport={"width": 800, "height": 480})
        self.page.add_init_script(SHIM)
        self.page.route("http://cmu.local/**", self._serve)
        self.page.route_web_socket(re.compile(r"ws://.*"), self._ws)
        self.page.on("console", lambda m: self.console.append(m.type + ": " + m.text))
        self.page.on("pageerror", lambda e: self.pageerrors.append(str(e)))
        self.page.goto("http://cmu.local/index.html")
        return self.page

    def ev(self, js, arg=None):
        return self.page.evaluate(js, arg) if arg is not None else self.page.evaluate(js)

    def mmui(self, *msgs):
        """Stuur MMUI-berichten (dicts) via de framework-route (zoals Debug.sendMmuiMsg)."""
        for m in msgs:
            self.page.evaluate("m => framework.routeMmuiMsg(m)", m)

    def stop(self):
        self.browser.close(); self.pw.stop()
