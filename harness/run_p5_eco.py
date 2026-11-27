#!/usr/bin/env python3
"""run_p5_eco.py -- P5-eco harnas (optie B, 2026-11-27) in de DRAAIENDE v74-GUI (headless Chromium,
nep-MMUI, stock -> root-inject mount). Bouwt op run_p6_phone.py (MountHarness met overlay-src fallback).

P5 bestanden (eigenaarschap BOUWPLAN eco-bel):
  overlay-src/common/oemplusb2/css/B2Sub-50-eco.css
  overlay-src/common/oemplusb2/images/B2Eco*.png/.jpg   (tools/assets/p5_eco.py)
  src/OemplusInject.js: PATHS.subCss + 50/60, TPMS-hook (read-only warnguide) -- hier WEL in de lader,
  dus GEEN lokale override-link nodig (in tegenstelling tot run_p6_phone.py).

Schermen: ecoenergy FuelConsumption / ControlStatus (i-stop) / Effectiveness / EnergyFlow.

Checks (taak + BOUWPLAN P5):
  setup  B2 aan via eco-paneel -> 8 B2Sub-links (00..40,50,60,70) uit de lader, body.OemplusB2 aan
  H1     hitboxes exact OEM (SwitchView, ShowUmp/switchElementBtn, Ump3-knoppen incl. UITGEKLAPT y380,
         Home, auto-/motorlagen, .OemplusInjPanel) B2 aan == uit, per scherm
  H2     focus-wandeling (cw/ccw/select) + UMP focus-index/appData gelijk aan/uit
  H3     B2Sub-50 geladen VOORDAT de eerste eco-context opent (link staat er voor goto) -> computed
         background van .EcoStatusCtrl_iEloop_Container = B2EcoCarPhoto_B.jpg
  H4     leesbaarheid: zichtbare teksten >= 24 px (whitelist: assen 21, kickers 18)
  H5     i-stop toestanden via ECHTE MMUI-berichten (echte v74-DOM):
         - iStopStatCntrlStatus TRUE/FALSE/DISPLAY_OFF per element -> Glow/plain/Hidden PNG
         - iStopModeCntrlStatus STATUS/TIME/ERROR -> pil / Time-kaart / Error-kaart
         - Time: iEloopEngine -> EngineGlow = B2EcoGlowOk.png (donkerrood)
         - Error: iStopErrorText klasse + Line1/Line2
         - TreeData 1/2/3 -> juiste boom-PNG (eco-groen)
         - staafhoogtes uit CurrDrvEcoPerInstBarGraph (JS height werkt, B2EcoBar* rood)
  H5t    TPMS: warnguide WarningStatus met 21/22/86 -> B2EcoTpms*_Low (+puls), 41/42 -> _Fault,
         count 0 -> _Ok, nooit bericht -> verborgen (B2EcoTpmsHidden); wrapper aangeroepen?
         B2 uit -> divs weg, wrapper van prototype af
  H6     B2 uit = OEM: geen body.OemplusB2, 0 B2Sub-links, computed bg = OEM (geen B2Eco/B2Sub)
  H7     check_presto.py OK (apart)
  H8     static: 0 selector-overlap B2Sub-50 met B2Sub-00..40/60; ASCII; marker; alle url() bestaan
  H9     protected: warnguide-context -> geen body.OemplusB2 (TPMS lezen mag wel, klasse niet)
  H12    inject-paneel intact met B2Sub-50 aan: zichtbaar, z-index 50, 4 rijen, hit-test
  A1     geen 404 op oemplusb2-assets; A2 geen JS-fouten

Gebruik:  sh harness/build_root.sh && python3 harness/run_p5_eco.py
Output:   harness/shots/p5-*.png + harness/RESULTS-V15-P5.json ; exit 1 bij fail.
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
SRC_OEM = os.path.normpath(os.path.join(HERE, "..", "overlay-src"))

def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok),
                    "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + str(detail)[:300] if detail != "" else ""))

class MountHarness(Harness):
    def __init__(self):
        Harness.__init__(self, "stock")
        self.root = os.path.join(HERE, "root-stock")
        self.phase = "boot"
    def mount(self):
        self.root = os.path.join(HERE, "root-inject")
        self.phase = "mounted"
    def _serve(self, route):
        path = re.sub(r"^https?://[^/]+/", "", route.request.url).split("?")[0]
        fp = os.path.normpath(os.path.join(self.root, path))
        # v1.4-r2 (review): GEEN overlay-src-fallback meer -- die maskeerde dat B2EcoCarPhoto_B.jpg niet in de
        # overlay/bundel zat (make_overlay kopieerde alleen *.png). Wat niet in root-inject staat = 404 = FAIL A1.
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

def sysmsg(msgId, payload, uiaId="ecoenergy"):
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

def errs(h):
    return list(h.pageerrors) + list(h.ev("window.__errors"))

def hide_panel(h):
    # v1.4-r2: via de echte Panel.hide() ("Verder naar Eco-scherm"), zodat ook de marker B2EcoPanelOpen
    # van de template-div gaat -- precies wat de gebruiker ziet na het proefmenu.
    h.ev("""(function(){ var a = framework.getAppInstance('ecoenergy'); var t = a && a._currentContextTemplate;
      if (t && t.oemplusInjPanel && t.oemplusInjPanel.visible) { t.oemplusInjPanel.hide(); return; }
      var p = document.querySelector('.OemplusInjPanel'); if (p) p.style.display = 'none'; })()""")
    h.page.wait_for_timeout(300)

# ------------------------------------------------------------------ v1.4-r2: geometrie- + pixeltoetsen
from PIL import Image as _PILImage
TEXTBOX_JS = """(sel) => { var o = [], els = document.querySelectorAll(sel);
  for (var i = 0; i < els.length; i++) { var e = els[i], cs = getComputedStyle(e), r = e.getBoundingClientRect();
    var u = null, walk = [e], n;
    while (walk.length) { n = walk.pop();
      for (var c = n.firstChild; c; c = c.nextSibling) {
        if (c.nodeType === 1) { walk.push(c); continue; }
        if (c.nodeType !== 3 || !/\S/.test(c.nodeValue)) continue;
        var g = document.createRange(); g.selectNodeContents(c); var rs = g.getClientRects();
        for (var k = 0; k < rs.length; k++) { var q = rs[k]; if (!q.width) continue;
          if (!u) u = [q.left, q.top, q.right, q.bottom];
          else { u[0] = Math.min(u[0], q.left); u[1] = Math.min(u[1], q.top); u[2] = Math.max(u[2], q.right); u[3] = Math.max(u[3], q.bottom); } } } }
    o.push({cls: (typeof e.className === 'string' ? e.className.split(' ')[0] : ''), disp: cs.display, vis: cs.visibility,
      fs: parseFloat(cs.fontSize), txt: (e.textContent || '').replace(/\s+/g, ' ').replace(/^ | $/g, ''),
      box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
      glyph: u ? [Math.floor(u[0]), Math.floor(u[1]), Math.ceil(u[2] - u[0]), Math.ceil(u[3] - u[1])] : null,
      sw: e.scrollWidth, cw: e.clientWidth, sh: e.scrollHeight, ch: e.clientHeight}); }
  return o; }"""

def textboxes(h, sel):
    return h.ev(TEXTBOX_JS, sel) or []

def rect_in(inner, outer, pad=0):
    """inner/outer = [x, y, w, h] (pagina-px); True als inner volledig binnen outer valt met 'pad' px marge."""
    if not inner or not outer:
        return False
    return (inner[0] >= outer[0] + pad and inner[1] >= outer[1] + pad and
            inner[0] + inner[2] <= outer[0] + outer[2] - pad and inner[1] + inner[3] <= outer[1] + outer[3] - pad)

def rect_overlap(a, b):
    return bool(a and b and not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]))

def shot(h, name, meta=None):
    """Screenshot + manifest-regel (echte staat op het moment van de opname; gebruikt door BORD-BOUW)."""
    path = os.path.join(SHOTS, name)
    h.page.screenshot(path=path)
    st = h.ev("""() => { var a = framework.getAppInstance('ecoenergy'); var t = a && a._currentContextTemplate;
      var c = t && t.ecoStatusCtrl; var p = document.querySelector('.OemplusInjPanel');
      var u = document.querySelectorAll('.Ump3Ctrl [class*="Button_"]'), uy = null;
      for (var i = 0; i < u.length; i++) { var r = u[i].getBoundingClientRect(); if (r.width && r.height) uy = uy === null ? Math.round(r.top) : Math.min(uy, Math.round(r.top)); }
      return {app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), b2: document.body.classList.contains('OemplusB2'),
        panel: !!(p && getComputedStyle(p).display !== 'none'), panelCls: !!(t && t.divElt && /B2EcoPanelOpen/.test(t.divElt.className)),
        mode: c ? c._iStopMode : null, tpms: window.OemplusInject ? window.OemplusInject.status().tpmsState : null,
        pil: (document.querySelector('.EcoStatusCtrl_iStop_Status_Text') || {}).textContent || null, umpTop: uy}; }""")
    st["file"] = name
    if meta:
        st.update(meta)
    MANIFEST[name] = st
    return path

MANIFEST = {}

def px_img(path):
    return _PILImage.open(path).convert("RGB")

def px_count(im, box, pred):
    x0, y0, x1, y1 = box
    n = 0
    for y in range(max(0, y0), min(im.size[1], y1)):
        for x in range(max(0, x0), min(im.size[0], x1)):
            if pred(im.getpixel((x, y))):
                n += 1
    return n

def px_max(im, box):
    x0, y0, x1, y1 = box
    m = 0
    for y in range(max(0, y0), min(im.size[1], y1)):
        for x in range(max(0, x0), min(im.size[0], x1)):
            m = max(m, max(im.getpixel((x, y))))
    return m

BRIGHT = lambda c: max(c) > 140
REDTXT = lambda c: c[0] > 150 and c[1] < 100 and c[2] < 110
AMBER = lambda c: c[0] > 180 and 110 < c[1] < 200 and c[2] < 110
ISRED = lambda c: c[0] > 70 and c[0] > 1.8 * c[1] and c[0] > 1.6 * c[2]
ISGREY = lambda c: abs(c[0] - c[1]) < 25 and abs(c[0] - c[2]) < 25 and c[0] > 60
ECOGREEN = lambda c: c[1] > 120 and c[1] > c[0] + 50 and c[1] > c[2] + 10


HIT_SEL = ("[class*='SwitchView'],[class*='ShowUmp'],.switchElementBtn,.switchElementBtnHit,"
           ".Ump3Ctrl [class*='Button_'],.StatusBarCtrlHomeBtn,.LeftBtnCtrl,"
           "[class*='CarBottomLayer'],[class*='CarTopLayer'],[class*='CarGlow'],.EcoStatusCtrl_iEloop_Engine,"
           "[class*='EcoFlowCtrlCar'],[class*='EcoStatusCtrl_anim'],#EcoIstopEffectiveRateDrawingCanvas,"
           ".FuelConsumptionCtrlCDFEBarGraphCore,.FuelConsumptionCtrlCDFEBarGraphCoreCurrent,"
           ".OemplusInjPanel,.OemplusInjRow,.B2EcoTpmsL,.B2EcoTpmsR,"
           ".EcoStatusCtrl_iStop_Title")

RECTS = """(sel) => { var out = [], els = document.querySelectorAll(sel);
  for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    var cn = typeof els[i].className === 'string' ? els[i].className : els[i].id;
    out.push(cn.split(' ')[0] + '@' + [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)].join(',')); }
  out.sort(); return out; }"""

def hitboxes(h, sel=HIT_SEL):
    return h.ev(RECTS, sel)

FOCUS_JS = """(evs) => { var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
  var r = []; for (var i = 0; i < evs.length; i++) { try { r.push([evs[i], t.handleControllerEvent(evs[i])]); } catch(e){ r.push([evs[i], 'ERR:'+e.message]); } }
  return r; }"""

def ump_focus_state(h):
    return h.ev("""(function(){ var t = framework.getAppInstance(framework.getCurrentApp())._currentContextTemplate;
      var u = null; for (var k in t) { if (t[k] && t[k]._focusIndex !== undefined && t[k].properties && t[k].properties.buttonConfig) { u = t[k]; break; } }
      if (!u) { for (var k2 in t) { if (t[k2] && t[k2].constructor && t[k2].constructor.name === 'Ump3Ctrl') { u = t[k2]; break; } } }
      if (!u) return null;
      var btns = u.properties.buttonConfig || {}, keys = []; for (var b in btns) { if (btns.hasOwnProperty(b)) keys.push(b + ':' + btns[b].appData + (btns[b].disabled ? ':ds' : '')); }
      return {focusIndex: u._focusIndex, keys: keys.sort(), cls: u.divElt ? u.divElt.className : null}; })()""")

def ump_toggle(h, on=True):
    # v1.4-r2 (review): de oude variant drukte de SwitchView-knop in -- op ControlStatus opent die de UMP
    # NIET (Ump3-knoppen bleven op y 584), dus "H1 UMP uitgeklapt" mat daar de dichte UMP. Nu via de OEM-API
    # ctrl.toggleUmpPanel('showPanel'/'hidePanel') (EcoStatus/EcoEffect/EcoFlow), anders de oude knop-route.
    done = h.ev("""(on) => { var t = framework.getAppInstance('ecoenergy')._currentContextTemplate;
      for (var k in t) { if (t[k] && typeof t[k].toggleUmpPanel === 'function') { t[k].toggleUmpPanel(on ? 'showPanel' : 'hidePanel'); return k; } }
      return null; }""", bool(on))
    if done:
        return
    h.ev("""(function(){ var t = framework.getAppInstance('ecoenergy')._currentContextTemplate;
      var sw = null; for (var k in t) { if (t[k] && t[k].divElt && /SwitchView|ShowUmp|switchElementBtn/.test(t[k].divElt.className)) { sw = t[k]; break; } }
      if (sw) { try { sw.handleControllerEvent('select'); } catch(e){} }
      return !!sw; })()""")

STATE_JS = """() => {
  var subLinks = document.querySelectorAll('link[data-oemplusb2sub]'), hrefs = [];
  for (var i = 0; i < subLinks.length; i++) hrefs.push(subLinks[i].getAttribute('href'));
  return {ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(),
          subCls: document.body.classList.contains('OemplusB2'), subLinks: hrefs,
          body: document.body.className, fw: framework._frameworkState,
          inj: window.OemplusInject ? window.OemplusInject.status() : null};
}"""

BG_JS = """(sel) => { var e = document.querySelector(sel); return e ? getComputedStyle(e).backgroundImage : null; }"""

def eco_data(h, feat="ISTOP"):
    E = "ecoenergy"
    cur = [{"Drv1AvlFuelE": v} for v in (142, 168, 151, 189, 174, 126, 198, 213, 182, 164, 201)]
    cum = [{"cumlAvgEfficiency": v} for v in (151, 163, 158, 171, 166, 174)]
    h.mmui(sysmsg("CurrEquippedFeature", {"CurrFeature": feat}, E),
           sysmsg("CurrDrvEcoPerInstBarGraph", {"CurrDrvFuelEco_BarGraph": {"EEM_CurDrvAvgFuelEco": cur}}, E),
           sysmsg("CumFuelResetEcoGraphData", {"CumFuelResetEcoGraph": {"EEM_cumAvgFuelEffAfterReset": cum}}, E),
           sysmsg("CurrAvgDriveFuelEco", {"CurrentAvgFuelEco": {"CurdrvAvlFuel": {"Drv1AvlFuelE": 178},
                                                                "CurdrvAvlFuel_unit": "FuelEffUnit_km_L"}}, E),
           sysmsg("iStopModeCntrlStatus", {"iStop_ModeStatus": "STATUS"}, E),
           sysmsg("iStopStatCntrlStatus", {"iStop_StatCntrlStatus": {"gasolinedieselStandby": {"enginetypeStandy": "TRUE"},
                                                                      "batterystandby": {"batteryStandby": "TRUE"},
                                                                      "heaterstandby": {"heaterControlStandby": "TRUE"},
                                                                      "istopStatus": {"istpStatus": "TRUE"}}}, E),
           sysmsg("iStopEffectiveRate", {"iStop_EffectiveRate": {"iStop_effective_rate": 23}}, E),
           sysmsg("iStopEffectiveTimeData", {"iStop_EffectiveTime": {"effectiveness_iStop_time": {"iStop_timeIG": 214, "iStopTotalTime": 931},
                                                                     "effectiveness_TotStpTime": {"tot_time_veh_stopped": 412}}}, E),
           sysmsg("TreeData", {"LeavesIcon_growth": 2, "TreeGrowth": {"TreeIcon_growth": 3}}, E),
           # v1.4-r2: Gem. km/L op ControlStatus komt uit CumulativeAvgFuelEconomy (r.948 -> setFuelEfficiency)
           sysmsg("CumulativeAvgFuelEconomy", {"CumulativeAvgFuelEco": {"cumlEff_unit": "FuelEffUnit_km_L",
                                                                       "cntrlstat_fuelEff": {"cumlAvgEfficiency": 178}}}, E))

def set_istop(h, engine="TRUE", batt="TRUE", ac="TRUE", ready="TRUE"):
    h.mmui(sysmsg("iStopStatCntrlStatus", {"iStop_StatCntrlStatus": {
        "gasolinedieselStandby": {"enginetypeStandy": engine},
        "batterystandby": {"batteryStandby": batt},
        "heaterstandby": {"heaterControlStandby": ac},
        "istopStatus": {"istpStatus": ready}}}, "ecoenergy"))

def set_mode(h, mode):
    h.mmui(sysmsg("iStopModeCntrlStatus", {"iStop_ModeStatus": mode}, "ecoenergy"))

def set_error(h, cond="POWER_STEERING"):
    h.mmui(sysmsg("iStopErrorCntrlStatus", {"iStop_ErrorCntrlStatus": {
        "istop_denied_condition": cond, "istopActivated": "FALSE", "istopStandbyNOtFullfilled": "TRUE"}}, "ecoenergy"))

def set_time(h, t=42, tot=931):
    # v1.4-r2 FIX: msgId is "iStopTimeCntrlStatus" (ecoenergyApp._messageTable r.931); het oude
    # "iStop_TimeStatus" bestond niet -> OEM toonde 0 ms = lege stoptijd + "0m" totaal (de zwevende "0m").
    h.mmui(sysmsg("iStopTimeCntrlStatus", {"iStop_TimeStatus": {"iStop_timeIG": t, "iStopTotalTime": tot}}, "ecoenergy"))

def set_tree(h, n):
    h.mmui(sysmsg("TreeData", {"LeavesIcon_growth": n, "TreeGrowth": {"TreeIcon_growth": n}}, "ecoenergy"))

def warnguide_status(h, count, values):
    h.mmui(sysmsg("WarningStatus", {"WarningList": {"Warning_count": count, "Warning_Values": values}}, "warnguide"))

TPMS_JS = """() => { var wg = framework._appInstances && framework._appInstances.warnguide;
  var tbl = wg && wg._messageTable && wg._messageTable["WarningStatus"];
  var o = {hooked: !!(tbl && tbl.oemplusTpmsWrapper) || !!(window.warnguideApp && warnguideApp.prototype._WarningStatusMsgHandler && warnguideApp.prototype._WarningStatusMsgHandler.oemplusTpmsWrapper),
  state: window.OemplusInject ? window.OemplusInject.status().tpmsState : null,
  seen: window.OemplusInject ? window.OemplusInject.status().tpmsSeen : null,
  divs: []};
  var d = document.querySelectorAll('.B2EcoTpmsL,.B2EcoTpmsR');
  for (var i = 0; i < d.length; i++) o.divs.push(d[i].className);
  return o; }"""

# ------------------------------------------------------------------ v1.4-r2: BORD-BOUW uit het manifest
# Elke tegel claimt een scherm + staat; de claim wordt getoetst tegen de ECHTE staat bij de opname (manifest).
BORD_TILES = [
    ("ControlStatus · GEREED (alles klaar)", "p5-status-gereed.png", {"ctxt": "ControlStatus", "panel": False, "mode": "Status", "pil": "GEREED"}),
    ("ControlStatus · NIET GEREED (accu + airco)", "p5-niet-gereed.png", {"ctxt": "ControlStatus", "panel": False, "mode": "Status", "pil": "NIET GEREED"}),
    ("ControlStatus · TIME motor uit 42s / tot. 15m", "p5-time.png", {"ctxt": "ControlStatus", "panel": False, "mode": "Time"}),
    ("ControlStatus · ERROR i-stop niet actief", "p5-error.png", {"ctxt": "ControlStatus", "panel": False, "mode": "Error"}),
    ("ControlStatus · TPMS laag (Druk laag)", "p5-tpms-laag.png", {"ctxt": "ControlStatus", "panel": False, "mode": "Status", "tpms": "low"}),
    ("ControlStatus · TPMS storing", "p5-tpms-storing.png", {"ctxt": "ControlStatus", "panel": False, "mode": "Status", "tpms": "fault"}),
    ("ControlStatus · TPMS ok", "p5-tpms-ok.png", {"ctxt": "ControlStatus", "panel": False, "mode": "Status", "tpms": "ok"}),
    ("ControlStatus · UMP open (KPI blijft rij 1)", "p5-controlstatus-ump-b2.png", {"ctxt": "ControlStatus", "panel": False, "ump": True}),
    ("ControlStatus · OEM+ proefmenu open (geen lek)", "p5-controlstatus-aan.png", {"ctxt": "ControlStatus", "panel": True}),
    ("FuelConsumption · staven rood (huidig helder)", "p5-fuel.png", {"ctxt": "FuelConsumption", "panel": False}),
    ("Effectiveness · B2-kaarten, bomen eco-groen", "p5-effect-b2.png", {"ctxt": "Effectiveness", "panel": False}),
    ("EnergyFlow · B2 (proefmenu dicht)", "p5-energyflow-b2.png", {"ctxt": "EnergyFlow", "panel": False}),
]

def bord(results_ref):
    from PIL import ImageDraw, ImageFont
    json.dump(MANIFEST, open(os.path.join(SHOTS, "p5-manifest.json"), "w"), indent=1, ensure_ascii=False)
    fails = []
    for label, f, want in BORD_TILES:
        st = MANIFEST.get(f)
        if not st:
            fails.append((label, f, "geen opname")); continue
        bad = {}
        for k, v in want.items():
            if k == "ump":
                got = st.get("umpTop") is not None and st.get("umpTop") <= 400
            elif k == "pil":
                got = (st.get("pil") or "").strip().upper() == v
                if got: continue
                bad[k] = st.get("pil"); continue
            else:
                got = st.get(k)
            if (got is not v) if isinstance(v, bool) else (got != v):
                bad[k] = got
        if st.get("b2") is not True or (want.get("panel") is False and st.get("panelCls")):
            bad["b2/panelCls"] = [st.get("b2"), st.get("panelCls")]
        if bad:
            fails.append((label, f, bad))
    check("P5r2 BORD-BOUW: elke tegel-label klopt met de ECHTE staat bij de opname (scherm, proefmenu open/dicht, i-stop-modus, pil, TPMS, UMP)",
          not fails, fails or len(BORD_TILES))
    fd = os.path.join(HERE, "root-stock", "_harness_fonts")
    try:
        fT = ImageFont.truetype(os.path.join(fd, "TipperarySemibold.ttf"), 22)
        fL = ImageFont.truetype(os.path.join(fd, "TipperarySemibold.ttf"), 15)
        fS = ImageFont.truetype(os.path.join(fd, "Tipperary.ttf"), 13)
    except Exception:
        fT = fL = fS = ImageFont.load_default()
    cols, tw, th, gap, top = 4, 384, 230, 14, 70
    W = cols * tw + (cols + 1) * gap
    rows = (len(BORD_TILES) + cols - 1) // cols
    H = top + rows * (th + 26 + gap) + gap
    B = _PILImage.new("RGB", (W, H), (16, 18, 22))
    d = ImageDraw.Draw(B)
    nok = sum(1 for r in results_ref if r["ok"]); nall = len(results_ref)
    d.text((gap, 12), "P5-eco optie B — reviewronde 2 (2026-11-27) · inject-v1.5 · run_p5_eco %d/%d PASS" % (nok, nall), font=fT, fill=(240, 242, 245))
    d.text((gap, 42), "Labels getoetst tegen p5-manifest.json (echte staat bij opname). Time-kaart 328x88 · KPI rij 1 · menu zonder lek · staven rood · Effectiviteit kaarten · TPMS 2 regels",
           font=fS, fill=(160, 166, 175))
    for i, (label, f, want) in enumerate(BORD_TILES):
        cx, cy = gap + (i % cols) * (tw + gap), top + (i // cols) * (th + 26 + gap)
        d.text((cx, cy), label, font=fL, fill=(230, 232, 236))
        fp = os.path.join(SHOTS, f)
        if os.path.isfile(fp):
            B.paste(_PILImage.open(fp).convert("RGB").resize((tw, th), _PILImage.LANCZOS), (cx, cy + 22))
        d.rectangle([cx - 1, cy + 21, cx + tw, cy + 22 + th], outline=(60, 64, 72))
    B.save(os.path.join(SHOTS, "BORD-BOUW.png"))

def main():
    # ---------- static H8/H7 ----------
    cssdir = os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "css")
    imgdir = os.path.join(HERE, "..", "overlay-src", "common", "oemplusb2", "images")
    mine = os.path.join(cssdir, "B2Sub-50-eco.css")
    txt = open(mine, encoding="utf-8").read()
    check("H7 static: marker OEMPLUS-B2 + ASCII-only in B2Sub-50-eco.css",
          "OEMPLUS-B2" in txt and all(ord(c) < 128 for c in txt))
    missing = [u for u in re.findall(r"url\(\.\./images/([^)]+)\)", txt) if not os.path.isfile(os.path.join(imgdir, u))]
    check("P5 assets: elke url(../images/...) in de CSS bestaat (B2Eco*)", not missing, missing)
    check("P5 foto: B2EcoCarPhoto_B.jpg is JPEG 800x416",
          os.path.isfile(os.path.join(imgdir, "B2EcoCarPhoto_B.jpg")) and
          __import__("PIL.Image", fromlist=["Image"]).open(os.path.join(imgdir, "B2EcoCarPhoto_B.jpg")).size == (800, 416))
    # v1.4-r2 (defect 1): de kaart-PNG's moeten EXACT de CSS-boxmaat hebben (B2EcoTimeCard was 800x416 i.p.v.
    # 328x88 -> 2,4x opgeblazen "MOTOR UIT" onder de kaartrand). Maat uit de CSS-regel zelf gelezen.
    PIL_Image = __import__("PIL.Image", fromlist=["Image"])
    def css_box(selector):
        m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", txt)
        if not m:
            return None
        w = re.search(r"\bwidth:\s*(\d+)px", m.group(1)); hh = re.search(r"\bheight:\s*(\d+)px", m.group(1))
        return (int(w.group(1)), int(hh.group(1))) if w and hh else None
    sizes = {}
    for png, sel, exact in (("B2EcoTimeCard.png", "body.OemplusB2 .EcoStatusCtrl_iStop_Time_Frame", True),
                            ("B2EcoKpiCard.png", "body.OemplusB2 .EcoStatusCtrl_FuelEfficiency_Container", True),
                            ("B2EcoGereedPill.png", "body.OemplusB2 .EcoStatusCtrl_iStop_Status_Text", True),
                            ("B2EcoErrorHead.png", "body.OemplusB2 .EcoStatusCtrl_iStop_Error_Text", False)):
        im_sz = PIL_Image.open(os.path.join(imgdir, png)).size
        box = css_box(sel)
        sizes[png] = {"png": im_sz, "css": box}
        sizes[png]["ok"] = bool(box) and ((im_sz == box) if exact else (im_sz[0] <= box[0] and im_sz[1] <= box[1]))
    check("P5r2 static: kaart-PNG's hebben de CSS-boxmaat (TimeCard 328x88, KPI 176x64, pil 260x52; ErrorHead <= kaart) -- defect 1 oorzaak",
          all(v["ok"] for v in sizes.values()), sizes)
    check("P5r2 static: B2EcoCarPhoto_B.jpg staat in overlay/ (OVERLAY-MD5) -- zat NIET in de bundel (alleen *.png gekopieerd)",
          "common/oemplusb2/images/B2EcoCarPhoto_B.jpg" in open(os.path.join(HERE, "..", "overlay", "OVERLAY-MD5.txt")).read())
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
        if f.startswith("B2Sub-") and f != "B2Sub-50-eco.css" and f.endswith(".css"):
            d = sm & sels(os.path.join(cssdir, f))
            if d:
                dup.append((f, sorted(d)))
    check("H8 static: geen selector van B2Sub-50 in een ander B2Sub-bestand (00..40,60)", not dup, dup)
    css_code = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    check("H8 static: B2Sub-50 bevat geen .OemplusInj-selector (paneel blijft onaangeraakt)",
          not re.search(r"OemplusInj", css_code))

    # ---------- boot -> mount -> eco -> B2 aan ----------
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(700)
    h.ev("framework.common.updateSbClock(new Date(2026, 10, 27, 10, 9, 0).getTime())")
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}, "system"),
           # warnguide laadt bij boot (boot-log: GUI_WARNGUIDE Constructor called) -> receive WarningStatus count 0
           sysmsg("WarningStatus", {"WarningList": {"Warning_count": 0, "Warning_Values": [0, 0, 0]}}, "warnguide"))
    p.wait_for_timeout(1200)
    goto(h, "system", "HomeScreen", 2200)
    h.mount()
    goto(h, "ecoenergy", "FuelConsumption", 2400)
    # paneel -> B2 aan (draaiknop m/n + Enter zoals run_inject)
    p.keyboard.press("m"); p.wait_for_timeout(300); p.keyboard.press("n"); p.wait_for_timeout(400)
    p.keyboard.press("Enter"); p.wait_for_timeout(1600)
    inj = h.ev("OemplusInject.status()")
    check("setup: B2 aan via eco-paneel; 8 B2Sub-links (00..40,50,60,70) UIT DE LADER",
          inj["on"] and inj["subOn"] is True and inj["subLinks"] == 8, {k: inj[k] for k in ("on", "subOn", "subLinks")})
    st = h.ev(STATE_JS)
    check("setup: B2Sub-50-eco.css + B2Sub-60-phone.css in de DOM (data-oemplusb2sub 5/6)",
          any("B2Sub-50-eco.css" in s for s in st["subLinks"]) and any("B2Sub-60-phone.css" in s for s in st["subLinks"]),
          st["subLinks"])
    miss50 = [m for m in h.missing if "B2Sub-50" in m or "B2Eco" in m]
    check("setup: geen 404 op B2Sub-50/B2Eco-assets", not miss50, sorted(set(miss50))[:8])

    # ---------- H12 inject-paneel intact ----------
    pn = h.ev("""() => { var p = document.querySelector('.OemplusInjPanel');
      if (!p) return {exists:false};
      var r = p.getBoundingClientRect();
      return {exists: !!p, vis: getComputedStyle(p).display, z: getComputedStyle(p).zIndex,
              rows: document.querySelectorAll('.OemplusInjPanel .OemplusInjRow').length,
              hit: (function(){ var e = document.elementFromPoint(Math.round(r.left + r.width/2), Math.round(r.top + 30)); var o=false; while(e){ if(e===p){o=true;break;} e=e.parentNode;} return o; })()}; }""")
    check("H12 inject-paneel intact met B2Sub-50 aan: zichtbaar, z-index 50, 4 rijen, bovenliggend",
          pn.get("exists") and pn.get("vis") == "block" and pn.get("z") == "50" and pn.get("rows") == 4 and pn.get("hit") is True, pn)

    # ---------- per scherm H1/H2/H3/H4/H6 ----------
    screens = [("FuelConsumption", "ISTOP"), ("ControlStatus", "ISTOP"),
               ("Effectiveness", "ISTOP"), ("EnergyFlow", "ISTOP_IELOOP")]
    for ctxt, feat in screens:
        eco_data(h, feat)
        p.wait_for_timeout(900)
        goto(h, "ecoenergy", ctxt, 2600)
        st = h.ev(STATE_JS)
        check("P5 %s: geladen met body.OemplusB2 (feat %s)" % (ctxt, feat),
              st["app"] == "ecoenergy" and st["ctxt"] == ctxt and st["subCls"] is True,
              {k: st[k] for k in ("app", "ctxt", "subCls")})
        # NIEUW (defect 3): Gem. km/L-kaart ALLEEN zichtbaar op ControlStatus, verborgen op de andere schermen
        # (gemeten NADAT het scherm geladen is; de container zit in de controlDiv van het HUIDIGE scherm)
        kpi_vis = h.ev("""() => { var els = document.querySelectorAll('.EcoStatusCtrl_FuelEfficiency_Container');
          var o = []; for (var i = 0; i < els.length; i++) { var cs = getComputedStyle(els[i]); var r = els[i].getBoundingClientRect();
            o.push({cls: els[i].className, disp: cs.display, bg: cs.backgroundImage.replace(/^.*\\//,''), rect: [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]}); }
          return o; }""")
        if ctxt == "ControlStatus":
            # v1.4-r2 (defect 2): bij binnenkomst staat het OEM+ proefmenu OPEN -> KPI-kaart + alle B2-bubbels weg
            pan = h.ev("""() => { var t = framework.getAppInstance('ecoenergy')._currentContextTemplate; var o = {};
              o.panel = !!(t.oemplusInjPanel && t.oemplusInjPanel.visible); o.cls = /B2EcoPanelOpen/.test(t.divElt.className);
              var sel = '.EcoStatusCtrl_FuelEfficiency_Container,[class*="iStop_Status_"],.B2EcoTpmsL,.B2EcoTpmsR';
              var e = document.querySelectorAll(sel); o.zichtbaar = [];
              for (var i = 0; i < e.length; i++) { var r = e[i].getBoundingClientRect(); if (getComputedStyle(e[i]).display !== 'none' && r.width && r.height) o.zichtbaar.push(e[i].className); }
              return o; }""")
            check("P5r2 ControlStatus proefmenu OPEN: marker B2EcoPanelOpen + KPI-kaart/statusbubbels/pil/TPMS display:none (geen lek; defect 2)",
                  pan["panel"] and pan["cls"] and not pan["zichtbaar"], pan)
        else:
            check("P5 KPI-leak %s: Gem. km/L-kaart VERBORGEN (display:none / geen B2EcoKpiCard) -- lekt niet naar dit scherm (defect 3)" % ctxt,
                  all(k["disp"] == "none" or "B2EcoKpiCard" not in k["bg"] for k in kpi_vis), kpi_vis)
        bgctrl = {"FuelConsumption": ".FuelConsumptionCtrl", "ControlStatus": ".EcoStatusCtrl_iEloop_Container",
                  "Effectiveness": ".EcoEffectCtrl", "EnergyFlow": ".EcoFlowCtrl"}[ctxt]
        bg = h.ev(BG_JS, bgctrl)
        if ctxt == "ControlStatus":
            check("H3 %s: foto-achtergrond B2EcoCarPhoto_B.jpg actief (B2Sub-50 geladen voor lazy eco-CSS)" % ctxt,
                  "B2EcoCarPhoto_B.jpg" in (bg or ""), bg)
        hb_on = hitboxes(h)
        shp = shot(h, "p5-%s-aan.png" % ctxt.lower(), {"label_state": "proefmenu open"})
        if ctxt == "ControlStatus":
            im = px_img(shp)
            # rechts naast het 740-brede menu (x 742..798) en op de oude/nieuwe KPI-plek: alleen donkere foto (max <= 60)
            strip = px_max(im, (742, 66, 798, 476))
            check("P5r2 ControlStatus proefmenu OPEN (pixels): strook x742..798 y66..476 naast het menu is donker (max %d <= 60): geen KPI-kaart/Accu-/bandbubbel-rest" % strip,
                  strip <= 60, {"max": strip})
        foc_on = h.ev(FOCUS_JS, ["cw", "ccw", "select", "cw", "cw"])
        ump_on = ump_focus_state(h)
        ump_toggle(h, True); p.wait_for_timeout(900)
        hb_on_ump = hitboxes(h)
        # NIEUW (defect 3): ook met UMP UITGEKLAPT mag de KPI-kaart niet lekken naar niet-ControlStatus schermen
        if ctxt != "ControlStatus":
            kpi_ump = h.ev("""() => { var els = document.querySelectorAll('.EcoStatusCtrl_FuelEfficiency_Container');
              var o = []; for (var i = 0; i < els.length; i++) { var cs = getComputedStyle(els[i]);
                o.push({disp: cs.display, bg: cs.backgroundImage.replace(/^.*\\//,'')}); } return o; }""")
            check("P5 KPI-leak %s (UMP open): kaart nog steeds verborgen (defect p5-controlstatus-aan-ump)" % ctxt,
                  all(k["disp"] == "none" or "B2EcoKpiCard" not in k["bg"] for k in kpi_ump), kpi_ump)
        p.screenshot(path=os.path.join(SHOTS, "p5-%s-aan-ump.png" % ctxt.lower()))
        ump_toggle(h, False); p.wait_for_timeout(700)
        # B2 uit -> H6
        h.ev("OemplusInject.b2Off()")
        p.wait_for_timeout(800)
        st_off = h.ev(STATE_JS)
        check("H6 %s: b2Off -> geen body.OemplusB2, 0 B2Sub-links" % ctxt,
              st_off["subCls"] is False and len(st_off["subLinks"]) == 0, {k: st_off[k] for k in ("subCls", "subLinks")})
        bg_off = h.ev(BG_JS, bgctrl)
        check("H6 %s: b2Off -> computed bg %s is weer OEM (geen B2Eco)" % (ctxt, bgctrl),
              "B2Eco" not in (bg_off or ""), bg_off)
        hb_off = hitboxes(h)
        ump_toggle(h, True); p.wait_for_timeout(800)
        hb_off_ump = hitboxes(h)
        ump_toggle(h, False); p.wait_for_timeout(600)
        foc_off = h.ev(FOCUS_JS, ["cw", "ccw", "select", "cw", "cw"])
        ump_off = ump_focus_state(h)
        p.screenshot(path=os.path.join(SHOTS, "p5-%s-uit.png" % ctxt.lower()))
        # B2 weer aan
        h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
        p.wait_for_timeout(900)
        check("H1 %s: hitboxes B2 aan == uit (%d elementen)" % (ctxt, len(hb_on)), hb_on == hb_off,
              {"alleen_aan": sorted(set(hb_on) - set(hb_off))[:6], "alleen_uit": sorted(set(hb_off) - set(hb_on))[:6]} if hb_on != hb_off else "")
        check("H1 %s (UMP uitgeklapt): hitboxes aan == uit (%d elementen)" % (ctxt, len(hb_on_ump)), hb_on_ump == hb_off_ump,
              {"aan": sorted(set(hb_on_ump) - set(hb_off_ump))[:6], "uit": sorted(set(hb_off_ump) - set(hb_on_ump))[:6]} if hb_on_ump != hb_off_ump else "")
        check("H2 %s: focus-wandeling gelijk B2 aan/uit" % ctxt, foc_on == foc_off,
              {"aan": foc_on, "uit": foc_off} if foc_on != foc_off else "")
        check("H2 %s: UMP focus-index + appData gelijk B2 aan/uit" % ctxt, ump_on == ump_off, {"aan": ump_on, "uit": ump_off})
        check("P5 %s: geen JS-fouten" % ctxt, not errs(h), errs(h)[:4])

    # ---------- H5: ControlStatus i-stop toestanden (echte MMUI, echte v74-DOM) ----------
    eco_data(h, "ISTOP")
    p.wait_for_timeout(900)
    goto(h, "ecoenergy", "ControlStatus", 2600)
    hide_panel(h)
    st = h.ev(STATE_JS)
    check("H5 ControlStatus: ISTOP geladen met B2 (subCls=%s)" % st["subCls"],
          st["ctxt"] == "ControlStatus" and st["subCls"] is True)
    deco = h.ev("""() => { var o = {};
      var e = document.querySelector('.EcoStatusCtrl_iStop_Status_Text'); var r = e.getBoundingClientRect();
      o.pil = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
      var k = document.querySelector('.EcoStatusCtrl_FuelEfficiency_Container'); r = k.getBoundingClientRect();
      o.kpi = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
      var c = document.querySelector('.StatusBarCtrlClock'); r = c ? c.getBoundingClientRect() : null;
      o.clock = r ? [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] : null;
      o.panelCls = /B2EcoPanelOpen/.test(framework.getAppInstance('ecoenergy')._currentContextTemplate.divElt.className);
      return o; }""")
    check("H1b ControlStatus (proefmenu dicht): pil op (270,320), KPI-kaart op (612,88) = rij 1 (ONTWERP-B), NIET over de klok; marker weg",
          deco["pil"][:2] == [270, 320] and deco["pil"][2] >= 260 and deco["kpi"][:2] == [612, 88]
          and not rect_overlap(deco["kpi"], deco["clock"]) and deco["panelCls"] is False, deco)
    # --- per element Good/Bad/DisplayOff ---
    VAK = {"Engine": "Engine", "Battery": "Batt", "AC": "AC"}
    for el in ("Engine", "Battery", "AC"):
        base = el   # 'Engine' | 'Battery' | 'AC'
        for val, expect in (("TRUE", "_Glow"), ("FALSE", None), ("DISPLAY_OFF", "HIDDEN")):
            kw = {"engine": "TRUE", "batt": "TRUE", "ac": "TRUE"}
            kw[{"Engine": "engine", "Battery": "batt", "AC": "ac"}[el].lower()] = val
            set_istop(h, kw["engine"], kw["batt"], kw["ac"])
            p.wait_for_timeout(900)
            st_vak = h.ev("""(el) => { var out = [];
                var c = framework.getAppInstance('ecoenergy')._currentContextTemplate.ecoStatusCtrl;
                var key = {'Engine':'iStopStatusEngine', 'Battery':'iStopStatusBattery', 'AC':'iStopStatusAC'}[el];
                var e = c && c[key];
                if (e) { var cs = getComputedStyle(e); var r = e.getBoundingClientRect();
                  out.push({cls: e.className, disp: cs.display, vis: cs.visibility, w: Math.round(r.width), h: Math.round(r.height), bg: cs.backgroundImage}); }
                else { out.push({error: 'geen ctrl/element', hasCtrl: !!c, keys: c ? Object.keys(c).filter(function(k){return /iStopStatus/.test(k);}) : null}); }
                return out; }""", el)
            if expect == "HIDDEN":
                ok_h = any(v.get("disp") == "none" or v.get("w") == 0 or v.get("h") == 0 or "Hidden" in v.get("cls", "") for v in st_vak) if isinstance(st_vak, list) else False
                check("H5 i-stop %s DISPLAY_OFF -> verborgen (EcoStatusCtrlHidden / display:none / 0-maat)" % el, ok_h, st_vak)
            else:
                want = "B2EcoIstop%s%s.png" % (VAK[el], expect or "")
                ok_v = any((expect or "") in v.get("cls", "") and want in (v.get("bg") or "") for v in st_vak) if isinstance(st_vak, list) else False
                check("H5 i-stop %s %s -> klasse met %s + PNG %s" % (el, val, expect, want), ok_v, st_vak)
            p.screenshot(path=os.path.join(SHOTS, "p5-istop-%s-%s.png" % (el.lower(), val.lower())))
    # alles Good + Ready -> GEREED pil wit
    set_istop(h, "TRUE", "TRUE", "TRUE", "TRUE")
    p.wait_for_timeout(900)
    pil = h.ev("""() => { var e = document.querySelector('.EcoStatusCtrl_iStop_Status_Text');
      if (!e) return null; var r = e.getBoundingClientRect(); var cs = getComputedStyle(e);
      return {txt: e.textContent, cls: e.className, rect: [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)],
              bg: cs.backgroundImage, color: cs.color, fs: cs.fontSize}; }""")
    check("H5 Status-modus: GEREED-pil op pagina (270,320), wit CSS-only (B2EcoGereedPill.png)",
          pil and "GEREED" in (pil["txt"] or "").upper() and pil["rect"][:2] == [270, 320] and "B2EcoGereedPill.png" in (pil["bg"] or ""),
          pil)
    shp = shot(h, "p5-status-gereed.png", {"label_state": "gereed"})
    # Gem. km/L kaart rechtsboven (rij 1)
    kpi = h.ev("""() => { var e = document.querySelector('.EcoStatusCtrl_FuelEfficiency_Container');
      if (!e) return null; var r = e.getBoundingClientRect(); var cs = getComputedStyle(e);
      return {rect: [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)], bg: cs.backgroundImage}; }""")
    check("H5 Gem. km/L-kaart (position:fixed) op (612,88) 176x64 met B2EcoKpiCard.png",
          kpi and kpi["rect"][:2] == [612, 88] and kpi["rect"][2] >= 176 and "B2EcoKpiCard.png" in (kpi["bg"] or ""), kpi)
    kv = textboxes(h, ".EcoStatusCtrl_FuelEfficiency_Value, .EcoStatusCtrl_WithCylinder_Value")
    kv = [k for k in kv if k["disp"] != "none" and k["glyph"]]
    check("P5r2 KPI-waarde '17.8 km/L' (CumulativeAvgFuelEconomy, eenheid = OEM-span) glyph-bbox BINNEN de kaart (612,88,176,64) met >=4px marge, >= 24px",
          len(kv) == 1 and kv[0]["txt"].replace(" ", "") == "17.8km/L" and rect_in(kv[0]["glyph"], kpi["rect"], 4) and kv[0]["fs"] >= 24, kv)
    im = px_img(shp)
    rand_kpi = px_count(im, (630, 87, 770, 91), lambda c: max(c) > 30)
    tekst_kpi = px_count(im, (624, 112, 776, 150), lambda c: max(c) > 200)
    check("P5r2 KPI (pixels): kaart-bovenrand op y 88 zichtbaar (%d px) en witte waarde '17.8' in de kaart (%d px)" % (rand_kpi, tekst_kpi),
          rand_kpi >= 120 and tekst_kpi >= 60, {"rand_px": rand_kpi, "waarde_px": tekst_kpi})
    # --- Time-modus ---
    set_mode(h, "TIME")
    set_time(h, 42, 931)
    p.wait_for_timeout(1000)
    tf = h.ev("""() => { var e = document.querySelector('.EcoStatusCtrl_iStop_Time_Frame');
      if (!e) return null; var r = e.getBoundingClientRect(); var cs = getComputedStyle(e);
      return {cls: e.className, rect: [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)], bg: cs.backgroundImage}; }""")
    check("H5 Time-modus: iStopTimeFrame kaart 328x88 op pagina (236,290), onderrand 378 (binnen 64..480)",
          tf and tf["rect"] == [236, 290, 328, 88] and "B2EcoTimeCard.png" in (tf["bg"] or ""), tf)
    # v1.4-r2 (defect 1): echte waarden + glyph-bbox van ELKE tekst in de kaart (Range.getClientRects)
    tt = textboxes(h, ".EcoStatusCtrl_iStop_Time_Value, .EcoStatusCtrl_iStop_Time_TotalValue")
    vals = dict((t["cls"], t) for t in tt)
    v, tot = vals.get("EcoStatusCtrl_iStop_Time_Value"), vals.get("EcoStatusCtrl_iStop_Time_TotalValue")
    check("P5r2 Time: stoptijd = '42s' en totaal = '15m' (iStopTimeCntrlStatus 42/931 s via OEM-formattering)",
          v and tot and v["txt"] == "42s" and tot["txt"] == "15m", [v and v["txt"], tot and tot["txt"]])
    check("P5r2 Time: glyph-bbox stoptijd + totaal BINNEN de kaart (236,290,328,88) met >= 6px marge, niet afgekapt (scrollWidth<=clientWidth), >= 30px",
          all(t and t["glyph"] and rect_in(t["glyph"], tf["rect"], 6) and t["sw"] <= t["cw"] and t["fs"] >= 30 for t in (v, tot)),
          {"frame": tf["rect"], "value": v, "total": tot})
    # NIEUW (defect p5-time): waarden + kickers BINNEN de kaart-rect, geen overflow/clipping
    tv = h.ev("""() => { var o = {};
      function r(s){ var e = document.querySelector(s); if(!e) return null; var b = e.getBoundingClientRect();
        return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; }
      var fr = r('.EcoStatusCtrl_iStop_Time_Frame');
      o.frame = fr; o.value = r('.EcoStatusCtrl_iStop_Time_Value'); o.total = r('.EcoStatusCtrl_iStop_Time_TotalValue');
      o.inside = function(b){ return fr && b && b[0] >= fr[0]-1 && b[1] >= fr[1]-1 && b[0]+b[2] <= fr[0]+fr[2]+1 && b[1]+b[3] <= fr[1]+fr[3]+1; };
      o.val_inside = o.inside(o.value); o.tot_inside = o.inside(o.total);
      o.val_txt = (document.querySelector('.EcoStatusCtrl_iStop_Time_Value')||{}).textContent;
      o.tot_txt = (document.querySelector('.EcoStatusCtrl_iStop_Time_TotalValue')||{}).textContent;
      return o; }""")
    check("H5b Time-modus: stoptijd + totaal BINNEN de kaart-rect (geen overflow onder de kaart; defect p5-time)",
          tv and tv.get("val_inside") and tv.get("tot_inside") and tv["frame"][1] + tv["frame"][3] <= 480,
          tv)
    englow = h.ev("""() => { var o = []; var els = document.querySelectorAll('[class*=\"iEloop_Engine\"]');
      for (var i = 0; i < els.length; i++) o.push(els[i].className + '=' + getComputedStyle(els[i]).backgroundImage); return o; }""")
    check("H5 Time-modus: motorgloed (EngineGlow) = B2EcoGlowOk.png (donkerrood, de gebruiker)",
          any("EngineGlow" in e and "B2EcoGlowOk.png" in e for e in (englow or [])), englow)
    # statusdivs verborgen in Time
    hid = h.ev("""() => { var c = framework.getAppInstance('ecoenergy')._currentContextTemplate.ecoStatusCtrl;
      var e = c.iStopStatusEngine; return e ? getComputedStyle(e).display + '|' + e.className : 'geen'; }""")
    check("H5 Time-modus: statusvak Engine verborgen (OEM EcoStatusCtrlHidden)", isinstance(hid, str) and hid.startswith("none"), hid)
    shp = shot(h, "p5-time.png", {"label_state": "time"})
    im = px_img(shp)
    # pixels: (a) donkerrode kaartrand links, (b) kicker 'MOTOR UIT' leesbaar rood in de kaart (y 296..322),
    # (c) GEEN heldere/rode tekstpixels in de onderste binnenrand (y 370..375) = niets afgekapt onder de kaart
    rand = px_count(im, (236, 302, 239, 366), lambda c: c[0] > 90 and c[0] > 2 * c[1])
    kick = px_count(im, (250, 296, 400, 322), REDTXT)
    waarde = px_count(im, (250, 324, 408, 372), BRIGHT)
    onder = px_count(im, (252, 371, 548, 376), lambda c: BRIGHT(c) or REDTXT(c))
    check("P5r2 Time (pixels): rand links rood (%d), kicker MOTOR UIT rood leesbaar (%d px), stoptijd wit (%d px), onderrand-band y371..375 leeg (%d)" % (rand, kick, waarde, onder),
          rand >= 40 and kick >= 60 and waarde >= 150 and onder == 0, {"rand": rand, "kicker": kick, "waarde": waarde, "onderband": onder})
    # 'zwevende 0m': geen zichtbare timeUnit-span buiten de kaart
    tu = textboxes(h, ".EcoStatusCtrl_timeUnit")
    out_tu = [t for t in tu if t["vis"] != "hidden" and t["disp"] != "none" and t["glyph"] and not rect_in(t["glyph"], tf["rect"], 0)]
    check("P5r2 Time: geen zwevende eenheid-span ('m'/'s') buiten de kaart", not out_tu, out_tu)
    # --- Error-modus ---
    set_mode(h, "ERROR")
    set_error(h, "POWER_STEERING")
    p.wait_for_timeout(1000)
    er = h.ev("""() => { var e = document.querySelector('.EcoStatusCtrl_iStop_Error_Text');
      if (!e) return null; var r = e.getBoundingClientRect(); var cs = getComputedStyle(e);
      var l1 = e.querySelector('[class*="Line1"], [class*="LineCenter"]'); var l2 = e.querySelector('[class*="Line2"]');
      return {cls: e.className, rect: [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)],
              bg: cs.backgroundImage, border: cs.borderColor, l1: l1 ? l1.textContent : null, l2: l2 ? l2.textContent : null}; }""")
    check("H5 Error-modus: iStopErrorText kaart op pagina (236,258) 328x120, onderrand 378 (rij 3), B2EcoErrorHead.png + amber rand + Line1/Line2",
          er and er["rect"] == [236, 258, 328, 120]
          and "B2EcoErrorHead.png" in (er["bg"] or "") and er["l1"] and er["l2"], er)
    # NIEUW (defect p5-error): error-kaart ZICHTBAAR binnen het scherm + Line1/Line2 binnen de kaart-rect
    er2 = h.ev("""() => { var e = document.querySelector('.EcoStatusCtrl_iStop_Error_Text'); if (!e) return null;
      var fr = e.getBoundingClientRect(); var cs = getComputedStyle(e);
      function r(s){ var x = e.querySelector(s); if(!x) return null; var b = x.getBoundingClientRect();
        return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; }
      var l1 = r('[class*="Line1"], [class*="LineCenter"]'), l2 = r('[class*="Line2"]');
      function inside(b){ return b && b[0] >= fr.left-1 && b[1] >= fr.top-1 && b[0]+b[2] <= fr.left+fr.width+1 && b[1]+b[3] <= fr.top+fr.height+1; }
      return {rect: [Math.round(fr.left), Math.round(fr.top), Math.round(fr.width), Math.round(fr.height)],
              disp: cs.display, vis: cs.visibility, l1: l1, l2: l2, l1_in: inside(l1), l2_in: inside(l2)}; }""")
    check("H5b Error-modus: error-kaart ZICHTBAAR (display block) binnen scherm y 64..480 EN Line1/Line2 binnen kaart (defect p5-error)",
          er2 and er2["disp"] == "block" and er2["vis"] == "visible" and er2["rect"][1] >= 64 and er2["rect"][1] + er2["rect"][3] <= 480
          and er2.get("l1_in") and er2.get("l2_in"), er2)
    et = textboxes(h, ".EcoStatusCtrl_iStop_Error_Text_Line1, .EcoStatusCtrl_iStop_Error_Text_Line2, .EcoStatusCtrl_iStop_Error_Text_LineCenter")
    et = [t for t in et if t["disp"] != "none" and t["txt"]]
    check("P5r2 Error: conditie + OEM-status volledig zichtbaar (geen ellipsis/afkapping: scroll<=client) en glyph-bbox BINNEN de kaart (>=4px), >= 20px",
          len(et) >= 2 and all(t["glyph"] and rect_in(t["glyph"], er["rect"], 4) and t["sw"] <= t["cw"] and t["sh"] <= t["ch"] and t["fs"] >= 20 for t in et),
          et)
    shp = shot(h, "p5-error.png", {"label_state": "error"})
    im = px_img(shp)
    amb = px_count(im, (236, 274, 239, 362), AMBER)
    onder = px_count(im, (252, 371, 548, 376), BRIGHT)
    check("P5r2 Error (pixels): amber rand links (%d px) + onderste binnenband leeg (%d)" % (amb, onder), amb >= 40 and onder == 0,
          {"amber": amb, "onderband": onder})
    # --- terug naar Status ---
    set_mode(h, "STATUS")
    set_istop(h, "TRUE", "FALSE", "FALSE", "FALSE")   # accu+airco blokkeren (B2-niet-gereed)
    p.wait_for_timeout(1000)
    bgs = h.ev("""() => { var o = {};
      o.engine = getComputedStyle(document.querySelector("[class*='iStop_Status_Engine']")).backgroundImage;
      o.batt = getComputedStyle(document.querySelector("[class*='iStop_Status_Battery']")).backgroundImage;
      o.ac = getComputedStyle(document.querySelector("[class*='iStop_Status_AC']")).backgroundImage;
      return o; }""")
    check("H5 Status niet-gereed: Engine Glow (klaar), Batt+AC plain (amber blokkeert)",
          "B2EcoIstopEngine_Glow.png" in (bgs["engine"] or "") and "B2EcoIstopBatt.png" in (bgs["batt"] or "")
          and "B2EcoIstopBatt_Glow" not in (bgs["batt"] or "") and "B2EcoIstopAC.png" in (bgs["ac"] or ""), bgs)
    shot(h, "p5-niet-gereed.png", {"label_state": "niet gereed"})
    set_istop(h, "TRUE", "TRUE", "TRUE", "TRUE")   # TPMS-tegels op een GEREED-scherm (alleen de banden variëren)
    p.wait_for_timeout(800)

    # ---------- H5t: TPMS (warnguide read-only) ----------
    tp0 = h.ev(TPMS_JS)
    wgdbg = h.ev("""() => ({hasApp: !!window.warnguideApp,
      inst: !!(framework._appInstances && framework._appInstances.warnguide),
      protoFn: !!(window.warnguideApp && typeof window.warnguideApp.prototype._WarningStatusMsgHandler),
      instCtorName: (framework._appInstances && framework._appInstances.warnguide && framework._appInstances.warnguide.constructor) ? framework._appInstances.warnguide.constructor.name : null,
      instProtoSame: !!(framework._appInstances && framework._appInstances.warnguide && window.warnguideApp && framework._appInstances.warnguide.constructor.prototype === window.warnguideApp.prototype)})""")
    check("H5t TPMS: wrapper op warnguideApp.prototype._WarningStatusMsgHandler staat (read-only)",
          tp0["hooked"] is True, {"tpms": tp0, "dbg": wgdbg})
    # nooit data gehad? boot stuurt warnguide een WarningStatus count 0 -> state ok
    check("H5t TPMS: initiele state uit cache (count 0 -> ok)", tp0["state"] in ("ok", "none"), tp0)
    warnguide_status(h, 1, [21])
    p.wait_for_timeout(900)
    tp1 = h.ev(TPMS_JS)
    check("H5t TPMS: WarningStatus [21] -> state=low, beide bandbubbels B2EcoTpms*_Low(/LowPulse)",
          tp1["state"] == "low" and len(tp1["divs"]) == 2 and all(("_Low" in c) for c in tp1["divs"]), tp1)
    # NIEUW (defect 6): tekst "Bandendruk laag" past RUIM binnen de bubbel.
    # Meet in de PNG waar de TEKST eindigt (bubbelrand negeren: scan x 16..172 binnen bubbel x 12..188,
    # tekstregel 2 = control-y 282..310) -> marge rechts moet > 8 px zijn.
    tpms_fit = h.ev("""() => { return new Promise(function(res){
      var im = new Image(); im.src = 'common/oemplusb2/images/B2EcoTpmsL_LowPulse.png';
      im.onload = function(){ var c = document.createElement('canvas'); c.width = im.naturalWidth; c.height = im.naturalHeight;
        var x = c.getContext('2d'); x.drawImage(im, 0, 0);
        var d = x.getImageData(0, 0, c.width, c.height).data, maxX = 0;
        for (var yy = 282; yy < 310; yy++) { for (var xx = 16; xx < 172; xx++) {
          var a = d[(yy*c.width+xx)*4+3]; if (a > 40) { if (xx - 12 > maxX) maxX = xx - 12; } } }
        res({png_w: im.naturalWidth, png_h: im.naturalHeight, tekst_max_x_in_bubbel: maxX, bubbel_breedte: 176, marge_rechts: 176 - maxX});
      }; setTimeout(function(){ res({timeout:true}); }, 2000); }); }""")
    check("H5t TPMS bubbel: PNG 800x416 en tekstregel eindigt binnen de bubbel met marge rechts > 8px (defect 'Bandendruk laag past krap')",
          tpms_fit and tpms_fit.get("png_w") == 800 and tpms_fit.get("marge_rechts", 0) > 8, tpms_fit)
    # v1.4-r2 (defect 5): de oude check scande alleen x 16..172 van de LINKER bubbel (kon nooit falen).
    # Nu op de screenshot: per bubbel (L 12..188 / R 612..788, y 310..382) moet de binnenste 12px-band
    # tegen de rechterrand (x+164..x+172) vrij zijn van tekstpixels, en er moet amber tekst IN de bubbel staan.
    warnguide_status(h, 1, [21])
    p.wait_for_timeout(200)
    shp = shot(h, "p5-tpms-laag.png", {"label_state": "tpms laag"})
    im = px_img(shp)
    tp_px = {}
    for side, bx in (("L", 12), ("R", 612)):
        band = px_count(im, (bx + 164, 324, bx + 173, 368), lambda c: max(c) > 110)   # zonder de ronde hoeken
        tekst = px_count(im, (bx + 10, 346, bx + 164, 378), AMBER)
        rand = px_count(im, (bx + 174, 330, bx + 177, 362), AMBER)
        tp_px[side] = {"band_rechts": band, "amber_tekst": tekst, "rand": rand}
    check("P5r2 TPMS laag (pixels): beide bubbels -- tekst ruim binnen de rand (12px band rechts leeg), amber tekst aanwezig, amber rand",
          all(v["band_rechts"] == 0 and v["amber_tekst"] >= 40 and v["rand"] >= 20 for v in tp_px.values()), tp_px)
    warnguide_status(h, 1, [41])
    p.wait_for_timeout(900)
    tp2 = h.ev(TPMS_JS)
    check("H5t TPMS: WarningStatus [41] -> state=fault, B2EcoTpms*_Fault (amber, niet pulserend)",
          tp2["state"] == "fault" and all("_Fault" in c for c in tp2["divs"]), tp2)
    shp = shot(h, "p5-tpms-storing.png", {"label_state": "tpms storing"})
    im = px_img(shp)
    bands = [px_count(im, (bx + 164, 324, bx + 173, 368), lambda c: max(c) > 110) for bx in (12, 612)]
    check("P5r2 TPMS storing (pixels): 'TPMS-storing' past (12px band rechts leeg, beide kanten)", bands == [0, 0], bands)
    warnguide_status(h, 2, [86, 41])   # 86 = low wint van 41? low check eerst -> low
    p.wait_for_timeout(900)
    tp3 = h.ev(TPMS_JS)
    check("H5t TPMS: [86,41] -> low (86 = Low_Tire_Air_Pressure wint)", tp3["state"] == "low", tp3)
    warnguide_status(h, 0, [0, 0, 0])
    p.wait_for_timeout(900)
    tp4 = h.ev(TPMS_JS)
    check("H5t TPMS: WarningStatus count 0 -> state=ok, B2EcoTpms*_Ok (rood-accent)",
          tp4["state"] == "ok" and all("_Ok" in c for c in tp4["divs"]), tp4)
    shot(h, "p5-tpms-ok.png", {"label_state": "tpms ok"})
    # extra BORD-tegel: ControlStatus GEREED met UMP open (proefmenu dicht)
    ump_toggle(h, True); p.wait_for_timeout(900)
    shp = shot(h, "p5-controlstatus-ump-b2.png", {"label_state": "ump open"})
    ku = h.ev("""() => { var k = document.querySelector('.EcoStatusCtrl_FuelEfficiency_Container'); var r = k.getBoundingClientRect();
      return {disp: getComputedStyle(k).display, rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]}; }""")
    check("P5r2 ControlStatus UMP open: KPI-kaart blijft op (612,88) (alleen op het echte i-stop-scherm)", ku["disp"] != "none" and ku["rect"][:2] == [612, 88], ku)
    ump_toggle(h, False); p.wait_for_timeout(700)
    # B2 uit -> TPMS divs weg + wrapper eraf
    h.ev("OemplusInject.b2Off()")
    p.wait_for_timeout(800)
    tp5 = h.ev(TPMS_JS)
    check("H5t TPMS: b2Off -> TPMS-divs weg uit de DOM + wrapper van prototype af",
          tp5["hooked"] is False and len(tp5["divs"]) == 0, tp5)
    check("H6 ControlStatus: b2Off -> TPMS state none, geen B2EcoTpms", tp5["state"] in (None, "none"), tp5)
    # B2 weer aan, TPMS 다시 ok (cache count 0)
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(900)
    goto(h, "ecoenergy", "ControlStatus", 2400)
    hide_panel(h)
    tp6 = h.ev(TPMS_JS)
    check("H5t TPMS: na b2On opnieuw: wrapper terug + state uit cache (ok) + divs aangemaakt in nieuwe ecoStatusCtrl",
          tp6["hooked"] is True and tp6["state"] == "ok" and len(tp6["divs"]) == 2 and all("_Ok" in c for c in tp6["divs"]), tp6)

    # ---------- H5: TreeData + staven ----------
    goto(h, "ecoenergy", "Effectiveness", 2400)
    hide_panel(h)
    for n, expect in ((1, "B2EcoTree_01"), (2, "B2EcoTree_02"), (3, "B2EcoTree_03.png")):
        set_tree(h, n)
        p.wait_for_timeout(900)
        bgs = h.ev("""() => { var o = [], els = document.querySelectorAll('.EcoEffectCtrl .treeWithTwoLeaves, .EcoEffectCtrl .treeWithThreeLeaves, .EcoEffectCtrl .fullBlownTree, .EcoEffectCtrl .tree');
          for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); if (r.width && r.height) o.push(els[i].className.split(' ')[0] + '=' + getComputedStyle(els[i]).backgroundImage.replace(/^.*\\//, '')); } return o; }""")
        # OEM: TreeGrowth.TreeIcon_growth -> fullBlownTree/treeWithThreeLeaves/treeWithTwoLeaves; LeavesIcon_growth -> .tree
        want_any = {1: ["B2EcoTree_01", "B2EcoTree_03_sm"], 2: ["B2EcoTree_02", "B2EcoTree_03_sm"], 3: ["B2EcoTree_03"]}
        check("H5 TreeData %d -> boom-PNG %s (eco-groen) zichtbaar" % (n, expect),
              any(any(w in b for w in want_any[n]) for b in bgs), bgs)
        p.screenshot(path=os.path.join(SHOTS, "p5-tree-%d.png" % n))
    # NIEUW (defect 5): Effectiviteit in B2-kaartstijl -- bg + meter-kaart + percent-badge + tree-bg zijn B2Eco*
    effb = h.ev("""() => { function bg(s){ var e = document.querySelector(s); return e ? getComputedStyle(e).backgroundImage.replace(/^.*\\//,'') : null; }
      return {ctrl: bg('.EcoEffectCtrl'), meter: bg('.EcoEffectCtrl #EcoIstopEffectiveRateDrawingCanvas'),
              percent: bg('.EcoEffectCtrl .percentDiv'), treebg: bg('.EcoEffectCtrl .treeBackground')}; }""")
    check("H5b Effectiviteit: B2-kaartstijl -- .EcoEffectCtrl bg B2EcoEffectBg + meter B2EcoMeterCard + percent B2EcoPercent + tree-bg B2EcoTreeBg (defect p5-tree-3)",
          all(v and v.startswith("B2Eco") for v in effb.values()), effb)
    # v1.4-r2 (defect 4): kaarten echt zichtbaar (pixels) en elke OEM-tekst BINNEN zijn kaart (glyph-bbox)
    CARDS = {"meter": [150, 118, 164, 164], "times": [322, 136, 462, 130], "boost": [504, 304, 280, 136]}
    shp = shot(h, "p5-effect-b2.png", {"label_state": "b2-kaarten boom 3"})
    im = px_img(shp)
    randen = {}
    for k, (x, y, w, hh) in CARDS.items():
        randen[k] = {"boven": px_count(im, (x + 20, y, x + w - 20, y + 2), lambda c: max(c) > 50),
                     "links": px_count(im, (x, y + 20, x + 2, y + hh - 20), lambda c: max(c) > 50)}
    check("P5r2 Effectiviteit (pixels): 3 B2-kaarten (meter / i-stop ON+Gestopt / Gestimuleerd) hebben een zichtbare haarlijn-rand",
          all(v["boven"] >= (CARDS[k][2] - 40) * 0.8 and v["links"] >= (CARDS[k][3] - 40) * 0.8 for k, v in randen.items()), randen)
    eb = textboxes(h, ".EcoEffectCtrl .actualTime, .EcoEffectCtrl .actualTimeValue, .EcoEffectCtrl .stopTime, .EcoEffectCtrl .stopTimeValue, .EcoEffectCtrl .iStopBoostText, .EcoEffectCtrl .iStopBoostValue")
    waar = {"actualTime": "times", "actualTimeValue": "times", "stopTime": "times", "stopTimeValue": "times", "iStopBoostText": "boost", "iStopBoostValue": "boost"}
    mis = [(t["cls"], t["glyph"], CARDS[waar[t["cls"]]]) for t in eb if t["glyph"] and not rect_in(t["glyph"], CARDS[waar.get(t["cls"], "times")], 4)]
    cv = h.ev("""() => { var c = document.getElementById('EcoIstopEffectiveRateDrawingCanvas'); var r = c.getBoundingClientRect();
      return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }""")
    check("P5r2 Effectiviteit: elke tekst (i-stop ON / Gestopt / Gestimuleerd + waarden) BINNEN zijn kaart (>=4px) en %-meter-canvas binnen meter-kaart",
          len(eb) == 6 and not mis and rect_in(cv, CARDS["meter"], 4), {"buiten": mis, "canvas": cv, "n": len(eb)})
    tr = h.ev("""() => { var o = {}, s = ['treeWithTwoLeaves','treeWithThreeLeaves','fullBlownTree','tree','treeBackground'];
      for (var i = 0; i < s.length; i++) { var e = document.querySelector('.EcoEffectCtrl .' + s[i]); if (!e) continue; var r = e.getBoundingClientRect();
        if (r.width && r.height) o[s[i]] = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; } return o; }""")
    groen = {}
    for k, r in tr.items():
        groen[k] = px_count(im, (r[0], r[1], min(r[0] + r[2], 800), min(r[1] + r[3], 480)), ECOGREEN)
    rood_effect = px_count(im, (80, 70, 790, 470), lambda c: c[0] > 150 and c[1] < 80)
    check("P5r2 Effectiviteit (pixels): bomen ECO-GROEN (groot + klein + groene rand boom-kaart), geen rood buiten de terugknop",
          groen.get("treeWithTwoLeaves", groen.get("treeWithThreeLeaves", groen.get("fullBlownTree", 0))) >= 60 and groen.get("tree", 0) >= 20
          and groen.get("treeBackground", 0) >= 150 and rood_effect == 0, {"groen": groen, "rood": rood_effect, "rects": tr})
    goto(h, "ecoenergy", "FuelConsumption", 2400)
    hide_panel(h)
    eco_data(h, "ISTOP")
    p.wait_for_timeout(1200)
    bars = h.ev("""() => { var o = [], els = document.querySelectorAll('.FuelConsumptionCtrlCDFEBarGraphCore, .FuelConsumptionCtrlCDFEBarGraphCoreCurrent, .FuelConsumptionCtrlCDFEBarGraphCap, .FuelConsumptionCtrlCFERBarGraphCore');
      for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect();
        if (r.width && r.height) o.push([els[i].className.split(' ')[0], Math.round(r.height), getComputedStyle(els[i]).backgroundImage.replace(/^.*\\//,'')]); }
      return o; }""")
    check("H5 FuelConsumption: staven hebben JS-hoogte (>0) EN B2EcoBar* (rood) als bg (n=%d)" % len(bars),
          len(bars) >= 5 and all(b[1] > 0 and b[2].startswith("B2EcoBar") for b in bars), bars[:6])
    # NIEUW (defect 4): kleur per staafklasse -- huidige reis HELDER ROOD, zuinig donkerrood, rest grijs.
    # Alle zichtbare staven meten ([class*=BarGraphCore], height > 2) zodat de Current-staaf echt meedoet.
    barcls = h.ev("""() => { var o = [], els = document.querySelectorAll('[class*="BarGraphCore"]');
      for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect();
        if (r.width && r.height > 2) o.push([els[i].className.split(' ')[0], Math.round(r.height),
          getComputedStyle(els[i]).backgroundImage.replace(/^.*\\//,'').replace(/[)"']+$/,'')]); }
      return o; }""")
    cur_red = [b for b in barcls if "Current" in b[0] and "Current" in b[2]]     # B2EcoBar*_Current*.png (helder rood)
    green_dark = [b for b in barcls if "Green" in b[0] and "Green" in b[2]]       # B2EcoBar*_Green*.png (donkerrood)
    grey = [b for b in barcls if (b[0].endswith("BarGraphCore") or b[0].endswith("BarGraphCoreRight"))
            and b[2] in ("B2EcoBarNarrow.png", "B2EcoBarWide.png")]
    check("H5b FuelConsumption: huidige-reis staaf -> B2EcoBar*_Current, overige -> B2EcoBarNarrow/Wide (nu gedempt rood) (defect p5-fuel)",
          len(cur_red) >= 1 and len(grey) >= 5, {"current": cur_red[:3], "green": green_dark[:2], "overig_n": len(grey),
                                                 "alle": barcls})
    # NIEUW (defect 4): rechterkolom overlapt NIET met de klok (klok y 1..62, kolom y>=64); KPI-kaart verborgen op dit scherm
    lap = h.ev("""() => { function r(s){ var e = document.querySelector(s); if(!e) return null; var b = e.getBoundingClientRect();
        return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; }
      var clock = r('.StatusBarCtrlClock'); var eff = r('.FuelConsumptionCtrlFuelEfficiencyArea');
      var kpis = document.querySelectorAll('.EcoStatusCtrl_FuelEfficiency_Container');
      var kpi_disp = []; for (var i=0;i<kpis.length;i++) kpi_disp.push(getComputedStyle(kpis[i]).display);
      var overlap = function(a, b){ return !!(a && b && !(a[0]+a[2] <= b[0] || b[0]+b[2] <= a[0] || a[1]+a[3] <= b[1] || b[1]+b[3] <= a[1])); };
      return {clock: clock, effArea: eff, eff_overlap_clock: overlap(eff, clock), kpi_disp: kpi_disp}; }""")
    check("H5b FuelConsumption: rechterkolom (FuelEfficiencyArea y>=64) overlapt NIET met de klok (y 1..62); KPI-kaart verborgen (display:none) (defect 4)",
          lap and lap["eff_overlap_clock"] is False and lap["effArea"][1] >= 64 and all(d == "none" for d in lap["kpi_disp"]), lap)
    # v1.4-r2 (defect 3): KLEUR op de screenshot meten (de oude check keek alleen naar PNG-namen; de 'overige'
    # PNG was grijs -> grafiek grijs). Per zichtbare staaf de mediane kernpixel: ALLES rood, geen grijs; de
    # huidige reis duidelijk helderder dan de overige; onderste grafiek (gemiddeld per reis) ook rood.
    shp = shot(h, "p5-fuel.png", {"label_state": "staven rood"})
    im = px_img(shp)
    brs = h.ev("""() => { var o = [], els = document.querySelectorAll('[class*="BarGraphCore"]');
      for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); if (r.width > 4 && r.height > 6)
        o.push([els[i].className.split(' ')[0], Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]); }
      return o; }""")
    kleur = []
    for cls, x, y, w, hh in brs:
        cs = sorted(im.getpixel((x + w // 2 + dx, y + hh // 2 + dy)) for dx in (-2, 0, 2) for dy in (-2, 0, 2))
        c = cs[len(cs) // 2]
        kleur.append({"cls": cls, "rgb": c, "rood": ISRED(c), "grijs": ISGREY(c), "cur": "Current" in cls, "cfer": "CFER" in cls})
    cur = [k for k in kleur if k["cur"]]
    rest = [k for k in kleur if not k["cur"] and "Green" not in k["cls"]]   # zuinig (Green) = #B0202C, apart
    check("P5r2 Brandstofverbruik (pixels): ALLE %d staven rood-tint (0 grijs), boven- EN ondergrafiek" % len(kleur),
          len(kleur) >= 10 and all(k["rood"] and not k["grijs"] for k in kleur) and any(k["cfer"] for k in kleur) and any(not k["cfer"] for k in kleur), kleur)
    check("P5r2 Brandstofverbruik (pixels): huidige reis HELDER rood (R>=200), overige gedempt donkerrood (R 80..150), contrast >= 60",
          cur and all(k["rgb"][0] >= 200 for k in cur) and rest and all(80 <= k["rgb"][0] <= 150 for k in rest)
          and min(k["rgb"][0] for k in cur) - max(k["rgb"][0] for k in rest) >= 60, {"cur": cur, "rest_R": sorted(set(k["rgb"][0] for k in rest))})

    goto(h, "ecoenergy", "EnergyFlow", 2400)
    hide_panel(h)
    shot(h, "p5-energyflow-b2.png", {"label_state": "b2"})

    # ---------- H9 protected: warnguide context ----------
    ok_wg = False
    for _ in range(6):
        h.ev("framework.debug.fakeCtxtChgMsgs('warnguide','WarningList')")
        p.wait_for_timeout(1200)
        st9 = h.ev(STATE_JS)
        if st9["app"] == "warnguide":
            ok_wg = True
            break
    check("H9 setup: warnguide/WarningList geladen (protected app)", ok_wg, {k: st9[k] for k in ("app", "ctxt", "subCls")})
    check("H9 protected: warnguide/WarningList -> GEEN body.OemplusB2 (TPMS lezen mag, klasse niet)",
          st9["app"] == "warnguide" and st9["subCls"] is False, {k: st9[k] for k in ("app", "ctxt", "subCls")})
    tpw = h.ev(TPMS_JS)
    check("H9 protected: TPMS-wrapper staat WEL (read-only lezen mag op protected app)", tpw["hooked"] is True, tpw)

    # ---------- A1/A2 ----------
    missing_b2 = [m for m in h.missing if "oemplusb2" in m]
    check("A1 geen ontbrekende B2Sub-assets/CSS (404)", not missing_b2, sorted(set(missing_b2))[:10])
    check("A2 geen JS-paginafouten", not h.pageerrors, h.pageerrors[:5])
    check("einde: geen JS-fouten", not errs(h), errs(h)[:4])
    h.stop()
    bord(results)

    nfail = sum(1 for r in results if r["ok"] is False)  # (incl. BORD-labelcheck)
    json.dump({"pakket": "P5-eco optie B (B2Sub-50-eco.css + 35 B2Eco* incl. foto 800x416 + TPMS-hook in OemplusInject.js) in ui-oemplus-inject-v1.5; lader 00..40,50,60",
               "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-V15-P5.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
