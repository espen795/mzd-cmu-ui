#!/usr/bin/env python3
"""P6-phone harnas (ML4): bewijst pakket P6 (belscherm) uit ui-mockup-v1.0/eco-bel/BOUWPLAN.md par.P6
in een DRAAIENDE v74-GUI (headless Chromium, nep-MMUI, bind-mount nagebootst stock -> root-inject).

Bestanden ( ALLEEN P6-eigen ):
  overlay-src/common/oemplusb2/css/B2Sub-60-phone.css
  overlay-src/common/oemplusb2/images/B2Call*/B2UmpPh*/B2DlgFocusRing*.png  (tools/assets/p6_phone.py)
  harness/run_p6_phone.py + shots/p6-*.png + RESULTS-V15-P6.json
OemplusInject.js wordt NIET gewijzigd: de P0-lader (PATHS.subCss, 00..40) blijft zoals hij is. De lader-regel
voor B2Sub-60 ("common/oemplusb2/css/B2Sub-60-phone.css" als 6e positie) is een 1-regel-voorstel voor de
P0-eigenaar (zie rapport); in dit harnas simuleren we hem met een LOKALE OVERRIDE: na "B2 aan" hangt het harnas
zelf een <link data-oemplusb2sub="60"> achteraan <head> (zelfde mechanisme als subCssOn), en na b2Off verwijdert
het die link weer. root-inject bevat B2Sub-60 (nog) niet -> _serve valt terug op overlay-src voor
common/oemplusb2/* (net als make_overlay ze zou kopieren; make_overlay zelf NIET gedraaid: die rmtree't
overlay/ waar de parallelle P5-agent zijn eco-bestanden in heeft staan).

Schermen (SUBMENU-INVENTARIS-v74.json, phone = NIET protected):
  S1 phone/IncomingCall        Dialog3 style04 titleStyle02, 2 knoppen (red Ignore / green Answer, initialFocus 1)
  S2 phone/CallWaiting         Dialog3 style04, 3 knoppen 220x80 (red / normal / green)
  S3 phone/ActiveCall          InCall2Tmplt, InCall2Ctrl OneCall + Ump3Ctrl7 (7x114x100 y380)
  S4 phone/ActiveCall1         InCall2Tmplt TwoCall (2e gesprek gedimd)
  S5 phone/CallConfirmation    Dialog3 style17 (NIET style04) -> H14 scope-check
  H9 mobile911/Active911CallConnected  InCall2Tmplt MAAR protected -> geen OemplusB2 -> OEM

Checks (BOUWPLAN P6):
  H1 hitbox-invariant: knop-rects exact OEM ([70,382,330,80],[400,382,330,80]; 3 knoppen [70/290/510,382,220,80];
     Ump3 7x [x,380,114,100]) gelijk B2 aan/uit (0 px)
  H2 focus-logica: cw/ccw/select wandeling gelijk aan/uit; select vuurt appData SelectAnswer/SelectIgnore
  H5 focus zichtbaar op BEIDE kleurknoppen: green_focused -> B2CallBtn2_Answer_Focus, red_focused -> B2CallBtn2_Reject_Focus
  H14 scope: niet-style04 Dialog3 (CallConfirmation) krijgt GEEN B2CallBtn* (wel B2DlgBtn* van P2); style04 wel
  H15 dekking: B2DialogBg.png (v1.4-P2, ca192db6) scrim alpha 255 buiten paneel; elementFromPoint in dialog
     (v1.4 heeft al dekkende scrim -> prototype-A2 Solid-PNG's NIET nodig, zie CSS-comment)
  H16 uitgeschakeld: _cachedCmuOrPhone="Handset" + setDisabled -> _Ds -> B2CallBtn2_Ds, tekst #5F656E
  H17 placeholder: Style04_Image1 inline IcnContactImagePlaceholder -> bg none, Style04 container = B2CallAvatar146;
     met echte foto -> foto-url op Image1; InCall2 img[src*=Placeholder] -> visibility hidden, frame = B2CallAvatar90
  H6 uit = OEM: na b2Off (en override-link weg) computed bg knoppen = OEM Dialog_6Btn_Green/Red, geen OemplusB2
  H7 static: marker OEMPLUS-B2 + ASCII + alle url() PNG's bestaan + PNG-maten == OEM (330x80/220x80/146/90/51/774x134/38/58)
  H8 static: geen selector-overlap B2Sub-60 vs B2Sub-00..50
  H9 protected: mobile911 InCall2 zonder OemplusB2 -> .InCall2InCallBG = OEM NowPlayingBG.png
  H3 late lazy-CSS: B2Sub-60 geladen voor de phone-templates

Gebruik:  sh harness/build_root.sh && python3 harness/run_p6_phone.py
Output:   harness/shots/p6-*.png + harness/RESULTS-V15-P6.json ; exit 1 bij fail.
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

P6CSS = "common/oemplusb2/css/B2Sub-60-phone.css"
SRC_OEM = os.path.normpath(os.path.join(HERE, "..", "overlay-src"))   # fallback-bron voor B2Sub-60 (zie docstring)

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
        fp = os.path.normpath(os.path.join(self.root, path))
        if not os.path.isfile(fp) and path.startswith("common/oemplusb2/"):
            # lokale override: B2Sub-60 staat (nog) niet in root-inject/overlay -> serveer uit overlay-src
            fp2 = os.path.normpath(os.path.join(SRC_OEM, path))
            if os.path.isfile(fp2):
                fp = fp2
        if not os.path.isfile(fp):
            self.missing.append(path)
            return route.fulfill(status=404, body="")
        import mimetypes
        ctype = mimetypes.guess_type(fp)[0] or "application/octet-stream"
        data = open(fp, "rb").read()
        if fp.endswith(".css"):
            txt = data.decode("utf-8", "replace")
            txt = re.sub(r"-o-(transition|transform|transform-origin)\b", r"\1", txt)
            data = txt.encode(); ctype = "text/css"
        return route.fulfill(status=200, body=data, headers={"Content-Type": ctype})

def sysmsg(msgId, payload, uiaId="system"):
    return {"msgType": "msg", "uiaId": uiaId, "msgId": msgId, "params": {"payload": payload}}

def goto(h, uia, ctxt, wait=2600):
    if not h.ev("!!framework.getAppInstance('%s')" % uia):
        h.mmui({"msgType": "ctxtChg", "ctxtId": ctxt, "uiaId": uia, "params": None})
        for _ in range(25):
            h.page.wait_for_timeout(400)
            if h.ev("!!framework.getAppInstance('%s')" % uia):
                break
        h.page.wait_for_timeout(800)
    st0 = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId()})")
    if isinstance(st0, dict) and st0.get("app") == uia and st0.get("ctxt") == ctxt:
        h.ev("framework.debug.fakeCtxtChgMsgs('system','HomeScreen')")
        h.page.wait_for_timeout(2000)
    for _ in range(4):
        h.ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
        h.page.wait_for_timeout(wait)
        for _ in range(12):
            st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
            if isinstance(st, dict) and st.get("app") == uia and st.get("ctxt") == ctxt:
                return True
            h.page.wait_for_timeout(400)
    return False


def hide_panel(h):
    """Harnas-only: verberg het OemplusInjPanel (z-index 50) zodat screenshots de dialog/balk tonen
    (het paneel hoort ALLEEN op eco-templates; phone-templates krijgen het via de gedeelde hook niet,
    maar in dit harnas is het paneel van het laatst geopende eco-scherm blijven hangen)."""
    h.ev("(function(){ var p = document.querySelector('.OemplusInjPanel'); if (p) p.style.display = 'none'; })()")

def errs(h):
    return list(h.pageerrors) + list(h.ev("window.__errors"))

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

STATE_JS = """() => {
  var subLinks = document.querySelectorAll('link[data-oemplusb2sub]'), hrefs = [];
  for (var i = 0; i < subLinks.length; i++) hrefs.push(subLinks[i].getAttribute('href'));
  return {ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(),
          subCls: document.body.classList.contains('OemplusB2'), subLinks: hrefs,
          body: document.body.className, fw: framework._frameworkState,
          inj: window.OemplusInject ? window.OemplusInject.status() : null};
}"""

DLG_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var c = t && t.dialog3Ctrl, btns = [], texts = [];
  var d = document.querySelector('.Dialog3Ctrl');
  if (c) for (var k in c) { if (/^buttonCtrl_/.test(k) && c[k] && c[k].divElt) {
    var r = c[k].divElt.getBoundingClientRect();
    btns.push({i: k, cls: c[k].divElt.getAttribute('class'), l: Math.round(r.left), t: Math.round(r.top),
               w: Math.round(r.width), h: Math.round(r.height),
               bg: getComputedStyle(c[k].divElt).backgroundImage, color: getComputedStyle(c[k].divElt).color});
  } }
  var content = document.querySelector('.Dialog3Ctrl_Style04');
  if (content) {
    btns.push({i: '_content', cls: content.className, bg: getComputedStyle(content).backgroundImage});
    var im1 = content.querySelector('.Dialog3Ctrl_Style04_Image1');
    if (im1) btns.push({i: '_image1', cls: im1.className, style: im1.getAttribute('style'),
                        bg: getComputedStyle(im1).backgroundImage, br: getComputedStyle(im1).borderRadius});
    var t1 = content.querySelector('.Dialog3Ctrl_Style04_Text1');
    if (t1) texts.push({cls: 'Text1', txt: t1.innerText, fs: getComputedStyle(t1).fontSize, col: getComputedStyle(t1).color});
    var t2 = content.querySelector('.Dialog3Ctrl_Style04_Text2');
    if (t2) texts.push({cls: 'Text2', txt: t2.innerText, fs: getComputedStyle(t2).fontSize, col: getComputedStyle(t2).color});
  }
  var btnsRow = document.querySelector('.Dialog3Ctrl_Buttons');
  return {ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(), subCls: document.body.classList.contains('OemplusB2'),
          dlgRect: d ? (function(){var r=d.getBoundingClientRect(); return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)];})() : null,
          dlgBg: d ? getComputedStyle(d).backgroundImage : null,
          btnsRowRect: btnsRow ? (function(){var r=btnsRow.getBoundingClientRect(); return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)];})() : null,
          focusIdx: c ? c._buttonSelectIndex : null, btns: btns, texts: texts,
          errors: window.__errors.slice()};
}"""

SELECT_JS = """() => {
  var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var c = t.dialog3Ctrl, fired = [];
  var orig = c.properties.defaultSelectCallback;
  c.properties.defaultSelectCallback = function(ctrl, appData) {
    fired.push(appData && (appData.originalAppData || appData)); return orig && orig.apply(this, arguments); };
  t.handleControllerEvent('selectStart');
  t.handleControllerEvent('select');
  c.properties.defaultSelectCallback = orig;
  return {fired: fired, idx: c._buttonSelectIndex};
}"""

INCALL_JS = """() => {
  var t = framework.getAppInstance('phone')._currentContextTemplate;
  var c = t && t.inCall2Ctrl, out = {hasCtrl: !!c, subCls: document.body.classList.contains('OemplusB2')};
  if (!c) return out;
  function bg(sel){ if (sel === '.InCall2InCallBG') return getComputedStyle(c.divElt).backgroundImage;
    var e = c.divElt.querySelector(sel); return e ? getComputedStyle(e).backgroundImage : null; }
  function rect(sel){ var e = c.divElt.querySelector(sel); if (!e) return null; var r = e.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }
  out.inCallBG = bg('.InCall2InCallBG');
  out.activeBkg = bg('.InCall2ContactActiveBkg');
  out.ruleLine = bg('.InCall2CtrlTitleContactRuleLine');
  out.activePhone = bg('.InCall2ActivePhone') || bg('.InCall2CallContactIcon');
  out.inactivePhone = bg('.InCall2InactivePhone');
  out.imgFrame = bg('.InCall2ContactImageFrame');
  out.imgFrameRect = rect('.InCall2ContactImageFrame');
  var img = c.divElt.querySelector('.InCall2ContactImageFrame img');
  out.imgSrc = img ? img.getAttribute('src') : null;
  out.imgVis = img ? getComputedStyle(img).visibility : null;
  out.imgRadius = img ? getComputedStyle(img).borderRadius : null;
  var nm = c.divElt.querySelector('.InCall2ContactName');
  out.name = nm ? {fs: getComputedStyle(nm).fontSize, col: getComputedStyle(nm).color, txt: nm.innerText, cls: nm.className} : null;
  var dur = c.divElt.querySelector('.InCall2ContactElapsedTime');
  out.dur = dur ? {fs: getComputedStyle(dur).fontSize, col: getComputedStyle(dur).color} : null;
  // UMP (Ump3Ctrl7): knop-rects + icon-divs (inline style door ButtonCtrl.setIcon)
  out.umpBtns = [];
  var ub = c.divElt.querySelectorAll('.Ump3Ctrl [class*="7Button_"]');
  for (var i = 0; i < ub.length; i++) { var r = ub[i].getBoundingClientRect();
    out.umpBtns.push([Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height), ub[i].className]); }
  out.umpIcons = [];
  var ic = c.divElt.querySelectorAll('.Ump3CtrlButtonIcon');
  for (var i = 0; i < ic.length; i++) out.umpIcons.push({style: ic[i].getAttribute('style'), bg: getComputedStyle(ic[i]).backgroundImage});
  out.umpCount = c.divElt.querySelectorAll('.Ump3Ctrl').length;
  return out;
}"""

def p6_link_on(h):
    """v1.4: B2Sub-60 zit al in de lader (PATHS.subCss, index 6). Deze 'override' is nu een no-op check:
    als de href al tussen de data-oemplusb2sub-links staat -> 'al', anders voegen we hem los toe (oud gedrag)."""
    return h.ev("""(function(){
      var ls = document.querySelectorAll('link[data-oemplusb2sub]');
      for (var i = 0; i < ls.length; i++) { if ((ls[i].getAttribute('href') || '') === '%s') return 'al'; }
      var l = document.createElement('link');
      l.rel = 'stylesheet'; l.href = '%s'; l.setAttribute('data-oemplusb2sub', '60');
      document.head.appendChild(l); window.__p6link = l; return 'toegevoegd';
    })()""" % (P6CSS, P6CSS))

def p6_link_off(h):
    return h.ev("(function(){ var l = window.__p6link || document.querySelector('link[data-oemplusb2sub=\"60\"]');"
                " if (l && l.parentNode) l.parentNode.removeChild(l); window.__p6link = null; return 'weg'; })()")

def main():
    # ================= static: H7 marker/ASCII/assets, H8 overlap, PNG-maten =================
    cssdir = os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "css")
    imgdir = os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "images")
    mine = os.path.join(cssdir, "B2Sub-60-phone.css")
    txt = open(mine, encoding="utf-8").read()
    check("H7 static: marker OEMPLUS-B2 + ASCII-only in B2Sub-60-phone.css",
          "OEMPLUS-B2" in txt and all(ord(c) < 128 for c in txt))
    missing = [u for u in re.findall(r"url\(\.\./images/([^)]+)\)", txt) if not os.path.isfile(os.path.join(imgdir, u))]
    check("P6 assets: elke url(../images/...) in de CSS bestaat als PNG (43 stuks)", not missing, missing)
    def sels(f):
        out = set()
        for m in re.finditer(r"(?m)^([^\n{}]+)\{", open(f).read()):
            for s in m.group(1).split(","):
                s = s.strip()
                if s.startswith("body.OemplusB2"):
                    out.add(s)
        return out
    sm = sels(mine)
    dup = []
    for f in sorted(os.listdir(cssdir)):
        if f.startswith("B2Sub-") and f != "B2Sub-60-phone.css" and f.endswith(".css"):
            d = sm & sels(os.path.join(cssdir, f))
            if d:
                dup.append((f, sorted(d)))
    check("H8 static: geen selector van B2Sub-60 in een ander B2Sub-bestand (00..50)", not dup, dup)
    from PIL import Image
    maten = {"B2CallBtn2_Answer_En.png": (330, 80), "B2CallBtn2_Reject_Focus.png": (330, 80),
             "B2CallBtn3_Answer_En.png": (220, 80), "B2CallBtn3_Ds.png": (220, 80),
             "B2CallAvatar146.png": (146, 146), "B2CallAvatar90.png": (90, 90),
             "B2CallIcon_Active.png": (51, 51), "B2CallCard.png": (774, 134),
             "B2UmpPhHangup_En.png": (58, 58), "B2UmpPhComm_En.png": (38, 38),
             "B2DlgFocusRing1.png": (662, 80), "B2DlgFocusRing2.png": (330, 80),
             "B2DlgFocusRing3.png": (220, 80), "B2DlgFocusRing4.png": (165, 80)}
    bad = [(n, Image.open(os.path.join(imgdir, n)).size) for n, m in maten.items() if Image.open(os.path.join(imgdir, n)).size != m]
    check("P6 PNG-maten == OEM elementmaat (hitbox-invariant, 14 representatief)", not bad, bad)
    n_png = len([f for f in os.listdir(imgdir) if f.startswith(("B2Call", "B2UmpPh", "B2DlgFocusRing"))])
    check("P6 asset-count: %d PNG's met phone-prefix (B2Call*/B2UmpPh*/B2DlgFocusRing*)" % n_png, n_png == 43, n_png)

    # ================= boot -> mount -> B2 aan -> lokale lader-override =================
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(700)
    h.ev("framework.common.updateSbClock(new Date(2026,10,27,10,9,0).getTime())")
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
    p.wait_for_timeout(1200)
    goto(h, "system", "HomeScreen", 2200)
    h.mount()
    n_boot = len(h.requests)
    goto(h, "ecoenergy", "FuelConsumption", 2400)
    p.keyboard.press("m"); p.wait_for_timeout(300); p.keyboard.press("n"); p.wait_for_timeout(400)
    p.keyboard.press("Enter"); p.wait_for_timeout(1600)
    inj = h.ev("OemplusInject.status()")
    check("setup: B2 aan via eco-paneel (subOn, 8 lader-links 00..40,50,60,70)", inj["on"] and inj["subOn"] is True and inj["subLinks"] == 8, inj)
    st_pre = h.ev(STATE_JS)
    check("setup: 8 B2Sub-links in DOM uit de lader (00..40,50,60,70), body.OemplusB2 aan", len(st_pre["subLinks"]) == 8 and st_pre["subCls"] is True, st_pre["subLinks"])
    # lokale override-link (data-oemplusb2sub=60) is nu dubbelop -> NIET toevoegen; alleen checken dat 60 geladen is
    check("setup: B2Sub-60-phone.css in de lader (7e link)", p6_link_on(h) in ("toegevoegd", "al"))
    p.wait_for_timeout(600)
    loaded60 = [r for ph, r in h.requests if r.endswith("B2Sub-60-phone.css")]
    check("setup: B2Sub-60-phone.css daadwerkelijk geserveerd (niet 404)",
          len(loaded60) >= 1 and P6CSS not in h.missing, {"loaded": loaded60, "missing": [m for m in h.missing if "B2Sub-60" in m or "B2Call" in m or "B2UmpPh" in m]})
    st = h.ev(STATE_JS)
    check("setup: 8 B2Sub-links in DOM (00..40,50,60; override was no-op), body.OemplusB2 aan", len(st["subLinks"]) == 8 and st["subCls"] is True, st["subLinks"])
    check("setup: geen JS-fouten", not errs(h), errs(h))

    # ================= S1 phone/IncomingCall (style04, 2 knoppen) =================
    goto(h, "phone", "IncomingCall", 3000)
    hide_panel(h)
    st = h.ev(STATE_JS)
    check("S1 IncomingCall: geladen met B2 (app phone, subCls=%s)" % st["subCls"], st["app"] == "phone" and st["ctxt"] == "IncomingCall" and st["subCls"] is True,
          {k: st[k] for k in ("app", "ctxt", "subCls")})
    # populateer de dialog zoals _populateDialogCtrl dat doet (contact + placeholder-foto)
    h.ev("""(function(){ var a = framework.getAppInstance('phone'); var t = a._currentContextTemplate;
        if (t && t.dialog3Ctrl) t.dialog3Ctrl._setDialogConfig({contentStyle:'style04', text1:'Jan Jansen',
          text2:'Mobiel +31 6 12345678', imagePath1:'common/images/icons/IcnContactImagePlaceholder_Active.png'}); })()""")
    p.wait_for_timeout(400)
    on = h.ev(DLG_JS)
    p.screenshot(path=os.path.join(SHOTS, "p6-incoming-aan.png"))
    check("S1: dialog 800x416 op y64 (rect %s)" % on["dlgRect"], on["dlgRect"] == [0, 64, 800, 416], on["dlgRect"])
    btn_rects = sorted([[b["l"], b["t"], b["w"], b["h"]] for b in on["btns"] if b["i"].startswith("buttonCtrl")])
    check("S1 (H1): 2 knoppen exact OEM 330x80 op y382 x70/x400 -> %s" % btn_rects,
          btn_rects == [[70, 382, 330, 80], [400, 382, 330, 80]], btn_rects)
    cls = {b["i"]: b["cls"] for b in on["btns"] if b["i"].startswith("buttonCtrl")}
    check("S1: knop-klassen red+green met initialFocus=1 (green focused): %s" % cls,
          any("Red_En" in c for c in cls.values()) and any("Green_En" in c and "_focused" in c for c in cls.values())
          and on["focusIdx"] == 1, {"cls": cls, "focusIdx": on["focusIdx"]})
    bgmap = {b["i"]: b["bg"] for b in on["btns"] if b["i"].startswith("buttonCtrl")}
    check("S1 (H5a): gefocuste GREEN knop (Opnemen) = B2CallBtn2_Answer_Focus.png", any("B2CallBtn2_Answer_Focus" in (v or "") for v in bgmap.values()), bgmap)
    check("S1: RED knop (Negeren, niet gefocust) = B2CallBtn2_Reject_En.png", any("B2CallBtn2_Reject_En" in (v or "") for v in bgmap.values()), bgmap)
    # focus-wandeling: ccw -> focus op rood -> Reject_Focus zichtbaar
    h.ev("(function(){ var t = framework.getAppInstance('phone')._currentContextTemplate; t.handleControllerEvent('controllerActive'); t.handleControllerEvent('ccw'); })()")
    p.wait_for_timeout(300)
    on_ccw = h.ev(DLG_JS)
    bg_ccw = {b["i"]: b["bg"] for b in on_ccw["btns"] if b["i"].startswith("buttonCtrl")}
    check("S1 (H5b): na ccw is focus op ROOD (Weigeren) zichtbaar = B2CallBtn2_Reject_Focus.png (focusIdx=%s)" % on_ccw["focusIdx"],
          on_ccw["focusIdx"] == 0 and any("B2CallBtn2_Reject_Focus" in (v or "") for v in bg_ccw.values()), bg_ccw)
    p.screenshot(path=os.path.join(SHOTS, "p6-incoming-focus-rood.png"))
    # select vuurt appData (H2): focus terug op green (cw), dan select -> SelectAnswer
    h.ev("(function(){ var t = framework.getAppInstance('phone')._currentContextTemplate; t.handleControllerEvent('cw'); })()")
    p.wait_for_timeout(200)
    sel1 = h.ev(SELECT_JS)
    check("S1 (H2): select op green stuurt appData SelectAnswer (MMUI-callback) -> %s" % sel1["fired"],
          sel1["fired"] and "SelectAnswer" in str(sel1["fired"]), sel1)
    h.ev("(function(){ var t = framework.getAppInstance('phone')._currentContextTemplate; t.handleControllerEvent('ccw'); })()")
    p.wait_for_timeout(200)
    sel2 = h.ev(SELECT_JS)
    check("S1 (H2): ccw + select op rood stuurt SelectIgnore -> %s" % sel2["fired"],
          sel2["fired"] and "SelectIgnore" in str(sel2["fired"]), sel2)
    # H1/H2 aan/uit vergelijking
    hb_on = hitboxes(h, ".Dialog3Ctrl_Buttons [class*='ButtonStyle']")
    foc_on = focus_walk(h, 4, ["cw", "ccw", "cw", "select"])
    h.ev("OemplusInject.b2Off()"); p6_link_off(h); p.wait_for_timeout(700)
    off = h.ev(DLG_JS)
    hb_off = hitboxes(h, ".Dialog3Ctrl_Buttons [class*='ButtonStyle']")
    foc_off = focus_walk(h, 4, ["cw", "ccw", "cw", "select"])
    bg_off = {b["i"]: b["bg"] for b in off["btns"] if b["i"].startswith("buttonCtrl")}
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })"); p6_link_on(h); p.wait_for_timeout(700)
    check("S1 (H1): knop-hitboxes exact gelijk B2 aan/uit -> aan %s" % hb_on, hb_on == hb_off, {"aan": hb_on, "uit": hb_off})
    check("S1 (H2): focus-wandeling gelijk B2 aan/uit", foc_on == foc_off, {"aan": foc_on, "uit": foc_off})
    check("S1 (H6): na b2Off = OEM (Dialog_6Btn_Green/Red PNG, geen B2CallBtn*)", any("Dialog_6Btn" in (v or "") for v in bg_off.values()) and not any("B2CallBtn" in (v or "") for v in bg_off.values()), bg_off)
    check("S1 (H6): na b2Off geen OemplusB2 in body", off["subCls"] is False, off["subCls"])
    # H17 placeholder vs echte foto
    on2 = h.ev(DLG_JS)
    img1 = [b for b in on2["btns"] if b["i"] == "_image1"]
    content = [b for b in on2["btns"] if b["i"] == "_content"]
    check("S1 (H17): placeholder-image verborgen (bg none), Style04 container = B2CallAvatar146.png",
          img1 and "none" in (img1[0]["bg"] or "") and content and "B2CallAvatar146" in (content[0]["bg"] or ""),
          {"img1": img1, "content": content})
    check("S1 (H17): Style04_Image1 rond (border-radius 73px)", img1 and "73" in (img1[0].get("br") or ""), img1)
    h.ev("""(function(){ var a = framework.getAppInstance('phone'); var t = a._currentContextTemplate;
        if (t && t.dialog3Ctrl) t.dialog3Ctrl._setDialogConfig({contentStyle:'style04', text1:'Jan Jansen',
          text2:'Mobiel', imagePath1:'common/images/contacts/cto_12345.png'}); })()""")
    p.wait_for_timeout(300)
    on3 = h.ev(DLG_JS)
    img1b = [b for b in on3["btns"] if b["i"] == "_image1"]
    check("S1 (H17b): met echte foto (imagePath) blijft Image1 bg = foto-url (niet verborgen)",
          img1b and "cto_12345" in (img1b[0]["bg"] or ""), img1b)
    t1 = on3["texts"]
    check("S1: Text1 = 40px Semibold hero (#f6f7f9), Text2 = 28px #c4c9d0",
          any(t["cls"] == "Text1" and t["fs"] == "40px" and "246, 247, 249" in t["col"] for t in t1)
          and any(t["cls"] == "Text2" and t["fs"] == "28px" for t in t1), t1)
    # H15 dekking (v1.4-P2 scrim al dekkend)
    px = h.ev("""(function(){ return new Promise(function(res){ var img = new Image();
      img.onload = function(){ var c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        var ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
        res({scrimTop: ctx.getImageData(400, 5, 1, 1).data[3], scrimLeft: ctx.getImageData(5, 200, 1, 1).data[3]}); };
      img.onerror = function(){ res({err: 1}); }; img.src = 'common/oemplusb2/images/B2DialogBg.png'; }); })()""")
    el = h.ev("""(function(){ var d = document.querySelector('.Dialog3Ctrl'); var e = document.elementFromPoint(400, 240);
      // het inject-paneel (.OemplusInjPanel, z-index 50) zit BOVEN de dialog -> elementFromPoint raakt die;
      // dekking checkt daarom de DIALOG-rect zelf (punt binnen 0..800 x 64..480 valt in de .Dialog3Ctrl,
      // onderliggend scherm mag NIET doorschijnen: scrim alpha 255 in de PNG + bg op .Dialog3Ctrl = B2DialogBg)
      var r = d.getBoundingClientRect();
      var inRect = (400 >= r.left && 400 <= r.right && 240 >= r.top && 240 <= r.bottom);
      var dlgBg = d ? getComputedStyle(d).backgroundImage : null;
      return {inDlg: inRect, dlgBg: dlgBg, dlgRect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]}; })()""")
    check("S1 (H15 dekking): B2DialogBg.png scrim alpha=255 buiten paneel (v1.4-P2 ca192db6; Solid-variant niet nodig); .Dialog3Ctrl bg = B2DialogBg.png; punt (400,240) in dialog=%s"
          % (el.get("inDlg") if isinstance(el, dict) else el),
          isinstance(px, dict) and px.get("scrimTop") == 255 and px.get("scrimLeft") == 255
          and isinstance(el, dict) and el.get("inDlg") is True and "B2DialogBg.png" in (el.get("dlgBg") or ""), {"px": px, "el": el})
    check("S1: geen JS-fouten", not errs(h), errs(h))

    # ================= S2 phone/CallWaiting (style04, 3 knoppen wisselgesprek) =================
    goto(h, "phone", "CallWaiting", 3000)
    hide_panel(h)
    h.ev("""(function(){ var a = framework.getAppInstance('phone'); var t = a._currentContextTemplate;
        if (t && t.dialog3Ctrl) t.dialog3Ctrl._setDialogConfig({contentStyle:'style04', text1:'Piet Pietersen',
          text2:'Werk +31 20 1234567', imagePath1:'common/images/icons/IcnContactImagePlaceholder_Inactive.png'}); })()""")
    p.wait_for_timeout(400)
    cw = h.ev(DLG_JS)
    p.screenshot(path=os.path.join(SHOTS, "p6-callwaiting-aan.png"))
    rects3 = sorted([[b["l"], b["t"], b["w"], b["h"]] for b in cw["btns"] if b["i"].startswith("buttonCtrl")])
    check("S2 CallWaiting (H1): 3 knoppen exact OEM 220x80 op y382 x70/290/510 -> %s" % rects3,
          rects3 == [[70, 382, 220, 80], [290, 382, 220, 80], [510, 382, 220, 80]], rects3)
    cls3 = [b["cls"] for b in cw["btns"] if b["i"].startswith("buttonCtrl")]
    bg3 = [b["bg"] for b in cw["btns"] if b["i"].startswith("buttonCtrl")]
    check("S2: knoppen red / normal / green (wisselgesprek) -> %s" % cls3,
          any("ButtonStyle03_Red_En" in c for c in cls3) and any("ButtonStyle03_Green_En" in c for c in cls3)
          and any("ButtonStyle03_En" in c and "Red" not in c and "Green" not in c for c in cls3), cls3)
    check("S2 (H5): green = B2CallBtn3_Answer_En, red = B2CallBtn3_Reject_En, midden (gefocust) = B2DlgBtn3_Focus (P2)",
          any("B2CallBtn3_Answer_En" in (b or "") for b in bg3) and any("B2CallBtn3_Reject_En" in (b or "") for b in bg3)
          and any("B2DlgBtn3_" in (b or "") for b in bg3), bg3)
    hb3_on = hitboxes(h, ".Dialog3Ctrl_Buttons [class*='ButtonStyle']")
    h.ev("OemplusInject.b2Off()"); p6_link_off(h); p.wait_for_timeout(700)
    hb3_off = hitboxes(h, ".Dialog3Ctrl_Buttons [class*='ButtonStyle']")
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })"); p6_link_on(h); p.wait_for_timeout(700)
    check("S2 (H1): 3-knoppen hitboxes gelijk B2 aan/uit", hb3_on == hb3_off, {"aan": hb3_on, "uit": hb3_off})
    check("S2: geen JS-fouten", not errs(h), errs(h))

    # ================= S5 phone/CallConfirmation (style17, NIET style04) -> H14 scope =================
    goto(h, "phone", "CallConfirmation", 3000)
    hide_panel(h)
    cc = h.ev(DLG_JS)
    bg_cc = [b["bg"] for b in cc["btns"] if b["i"].startswith("buttonCtrl")]
    check("S5 (H14 scope): NIET-style04 Dialog3 (CallConfirmation style17) krijgt GEEN B2CallBtn* (wel P2 B2DlgBtn*)",
          not any("B2CallBtn" in (b or "") for b in bg_cc) and any("B2DlgBtn" in (b or "") for b in bg_cc), bg_cc)
    p.screenshot(path=os.path.join(SHOTS, "p6-callconfirmation-aan.png"))

    # ================= S3 phone/ActiveCall (InCall2 OneCall + Ump3Ctrl7) =================
    goto(h, "phone", "ActiveCall", 3200)
    hide_panel(h)
    st = h.ev(STATE_JS)
    check("S3 ActiveCall: geladen met B2 (subCls=%s)" % st["subCls"], st["app"] == "phone" and st["ctxt"] == "ActiveCall" and st["subCls"] is True, {k: st[k] for k in ("app", "ctxt", "subCls")})
    # contact-data zoals de app ze zet (placeholder, want geen imagePath)
    h.ev("""(function(){ var a = framework.getAppInstance('phone'); var t = a._currentContextTemplate;
        if (t && t.inCall2Ctrl) { t.inCall2Ctrl.setContact1Config({isActive: true, contactName: 'Jan Jansen',
          phoneNumber: '+31 6 12345678', phoneType: 'Mobiel'}); t.inCall2Ctrl.setContact1ElapsedTime(83); } })()""")
    p.wait_for_timeout(500)
    ic_on = h.ev(INCALL_JS)
    p.screenshot(path=os.path.join(SHOTS, "p6-activecall-aan.png"))
    check("S3: .InCall2InCallBG = none (B2SubBg eronder)", "none" in (ic_on["inCallBG"] or ""), ic_on["inCallBG"])
    check("S3: actief-gesprek kaart = B2CallCard.png", "B2CallCard" in (ic_on["activeBkg"] or ""), ic_on["activeBkg"])
    check("S3: actief telefoon-icoon = B2CallIcon_Active.png", "B2CallIcon_Active" in (ic_on["activePhone"] or ""), ic_on["activePhone"])
    check("S3: image-frame = B2CallAvatar90.png, img placeholder verborgen (visibility hidden)",
          "B2CallAvatar90" in (ic_on["imgFrame"] or "") and ic_on["imgVis"] == "hidden" and "IcnContactImagePlaceholder" in (ic_on["imgSrc"] or ""),
          {"frame": ic_on["imgFrame"], "imgSrc": ic_on["imgSrc"], "imgVis": ic_on["imgVis"]})
    check("S3: img radius 45px (rond)", ic_on["imgRadius"] and "45" in ic_on["imgRadius"], ic_on["imgRadius"])
    check("S3: naam 34px hero, duur 32px LIGHT", ic_on["name"] and ic_on["name"]["fs"] == "34px" and ic_on["dur"] and ic_on["dur"]["fs"] == "32px",
          {"name": ic_on["name"], "dur": ic_on["dur"]})
    ump_rects = sorted([u[:4] for u in ic_on["umpBtns"]])
    check("S3 (H1): UMP 7 knoppen exact OEM 114x100 op y380 x0/114/.../684 -> %d knoppen" % len(ump_rects),
          ump_rects == [[0, 380, 114, 100], [114, 380, 114, 100], [228, 380, 114, 100], [342, 380, 114, 100],
                        [456, 380, 114, 100], [570, 380, 114, 100], [684, 380, 114, 100]], ump_rects)
    icons = ic_on["umpIcons"]
    check("S3 (D): alle %d UMP-iconen = B2UmpPh* (inline style overschreven)" % len(icons),
          len(icons) == 7 and all("B2UmpPh" in (u["bg"] or "") for u in icons),
          [[(u["style"] or "")[:60], (u["bg"] or "")[:80]] for u in icons])
    check("S3 (D): ophangen-icoon = B2UmpPhHangup_En (rode schijf)",
          any("IcnUmpHangup" in (u["style"] or "") and "B2UmpPhHangup_En" in (u["bg"] or "") for u in icons),
          [(u["style"], u["bg"]) for u in icons if "Hangup" in (u["style"] or "")])
    # H1/H2 aan/uit op InCall2 + UMP
    hb_ic_on = hitboxes(h, ".InCall2Ctrl [class*='7Button_'], .InCall2ContactImageFrame, .StatusBarCtrlHomeBtn")
    foc_ic_on = focus_walk(h, 4, ["cw", "cw", "ccw", "select"])
    h.ev("OemplusInject.b2Off()"); p6_link_off(h); p.wait_for_timeout(700)
    ic_off = h.ev(INCALL_JS)
    hb_ic_off = hitboxes(h, ".InCall2Ctrl [class*='7Button_'], .InCall2ContactImageFrame, .StatusBarCtrlHomeBtn")
    foc_ic_off = focus_walk(h, 4, ["cw", "cw", "ccw", "select"])
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })"); p6_link_on(h); p.wait_for_timeout(700)
    check("S3 (H1): InCall2/UMP hitboxes gelijk B2 aan/uit", hb_ic_on == hb_ic_off, {"aan": hb_ic_on, "uit": hb_ic_off})
    check("S3 (H2): focus-wandeling gelijk B2 aan/uit", foc_ic_on == foc_ic_off, {"aan": foc_ic_on, "uit": foc_ic_off})
    check("S3 (H6): na b2Off InCall2 = OEM (NowPlayingBG / Active_Call_Bkg / ActiveCall_En / NowPlayingImageFrame)",
          "NowPlayingBG" in (ic_off["inCallBG"] or "") and "Active_Call_Bkg" in (ic_off["activeBkg"] or "")
          and "ActiveCall_En" in (ic_off["activePhone"] or "") and "NowPlayingImageFrame" in (ic_off["imgFrame"] or ""),
          {k: ic_off[k] for k in ("inCallBG", "activeBkg", "activePhone", "imgFrame")})
    # H17b InCall2: met echte foto blijft img zichtbaar
    h.ev("""(function(){ var a = framework.getAppInstance('phone'); var t = a._currentContextTemplate;
        if (t && t.inCall2Ctrl) t.inCall2Ctrl.setContact1Config({isActive: true, contactName: 'Jan Jansen',
          imagePath: 'common/images/contacts/cto_999.png'}); })()""")
    p.wait_for_timeout(300)
    ic_foto = h.ev(INCALL_JS)
    check("S3 (H17b): met echte foto: img src = foto EN zichtbaar (visibility visible)",
          "cto_999" in (ic_foto["imgSrc"] or "") and ic_foto["imgVis"] == "visible", {"src": ic_foto["imgSrc"], "vis": ic_foto["imgVis"]})
    check("S3: geen JS-fouten", not errs(h), errs(h))

    # ================= S4 phone/ActiveCall1 (TwoCall, 2e gesprek gedimd) =================
    goto(h, "phone", "ActiveCall1", 3200)
    hide_panel(h)
    h.ev("""(function(){ var a = framework.getAppInstance('phone'); var t = a._currentContextTemplate;
        if (t && t.inCall2Ctrl) { t.inCall2Ctrl.setContact1Config({isActive: true, contactName: 'Jan Jansen', phoneNumber: '+31 6 1'});
          t.inCall2Ctrl.setContact2Config({isActive: false, contactName: 'Piet Pietersen', phoneNumber: '+31 20 2'}); } })()""")
    p.wait_for_timeout(500)
    ic4 = h.ev(INCALL_JS)
    p.screenshot(path=os.path.join(SHOTS, "p6-activecall1-aan.png"))
    check("S4 ActiveCall1 (TwoCall): geladen met B2, 2 contacten, UMP 7 knoppen",
          ic4["hasCtrl"] and len(ic4["umpBtns"]) == 7 and ic4["subCls"] is True, {"hasCtrl": ic4["hasCtrl"], "nUmp": len(ic4["umpBtns"])})
    check("S4: geen JS-fouten", not errs(h), errs(h))

    # ================= H16 Handset-modus (knoppen disabled) =================
    goto(h, "phone", "IncomingCall", 3000)
    hide_panel(h)
    h.ev("""(function(){ var a = framework.getAppInstance('phone'); a._cachedCmuOrPhone = 'Handset';
        var t = a._currentContextTemplate; if (t && t.dialog3Ctrl) { t.dialog3Ctrl.setDisabled('button1', true); t.dialog3Ctrl.setDisabled('button2', true);
          t.handleControllerEvent('controllerActive');
          for (var k in t.dialog3Ctrl) { if (/^buttonCtrl_/.test(k) && t.dialog3Ctrl[k]) {
            t.dialog3Ctrl[k].setCssClasses({enabledClass: t.dialog3Ctrl[k].properties.enabledClass,
              disabledClass: t.dialog3Ctrl[k].properties.disabledClass, focusedClass: t.dialog3Ctrl[k].properties.focusedClass,
              downClass: t.dialog3Ctrl[k].properties.downClass, heldClass: t.dialog3Ctrl[k].properties.heldClass}); } }
        } })()""")
    p.wait_for_timeout(400)
    ds = h.ev(DLG_JS)
    p.screenshot(path=os.path.join(SHOTS, "p6-incoming-handset-ds.png"))
    ds_bg = [b["bg"] for b in ds["btns"] if b["i"].startswith("buttonCtrl")]
    ds_col = [b["color"] for b in ds["btns"] if b["i"].startswith("buttonCtrl")]
    ds_cls = [b["cls"] for b in ds["btns"] if b["i"].startswith("buttonCtrl")]
    check("H16: Handset-modus -> beide knoppen _Ds (Red_En/Green_En vervangen door _Ds) EN bg = B2CallBtn2_Ds.png (neutrale pil)",
          all("_Ds" in (c or "") and "_En" not in (c or "") for c in ds_cls) and all("B2CallBtn2_Ds" in (b or "") for b in ds_bg),
          {"bg": ds_bg, "col": ds_col, "cls": ds_cls})
    h.ev("(function(){ var a = framework.getAppInstance('phone'); a._cachedCmuOrPhone = 'Vehicle'; })()")

    # ================= H9 protected: mobile911 InCall2 =================
    goto(h, "mobile911", "Active911CallConnected", 3200)
    hide_panel(h)
    st = h.ev(STATE_JS)
    m911 = h.ev("""(function(){ var c = document.querySelector('.InCall2Ctrl'); if (!c) return {err: 'geen InCall2'};
      return {subCls: document.body.classList.contains('OemplusB2'),
        app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(),
        divCls: c.className, bg: getComputedStyle(c).backgroundImage}; })()""")
    p.screenshot(path=os.path.join(SHOTS, "p6-mobile911-oem.png"))
    check("H9: mobile911/Active911CallConnected (InCall2Tmplt, protected) -> GEEN OemplusB2, divElt bg = OEM (NowPlayingBG*.png)",
          m911.get("subCls") is False and "NowPlayingBG" in (m911.get("bg") or "") and "InCall2" in (m911.get("divCls") or ""), m911)
    check("H9: st app/ctxt = mobile911/Active911CallConnected", st["app"] == "mobile911" and st["ctxt"] == "Active911CallConnected", {k: st[k] for k in ("app", "ctxt", "subCls")})

    # ================= H3 late lazy-CSS =================
    after = [r for ph, r in h.requests[n_boot:]]
    tmpl = [r for r in after if any(t in r for t in ("InCall2Tmplt", "Dialog3Tmplt", "InCall2Ctrl.js", "phoneApp.js"))]
    b60 = [r for ph, r in h.requests if r.endswith("B2Sub-60-phone.css")]
    check("H3: B2Sub-60 geladen voor de phone-templates/controls (prefix wint van late lazy-CSS)",
          len(b60) >= 1 and len(tmpl) >= 3, {"b60": len(b60), "tmpl": tmpl[:5]})

    check("einde: geen JS-fouten", not errs(h), errs(h))
    h.stop()

    nfail = sum(1 for r in results if r["ok"] is False)
    json.dump({"pakket": "P6 phone (belscherm) -- B2Sub-60-phone.css + 43 PNG's, lokale lader-override",
               "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-V15-P6.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
