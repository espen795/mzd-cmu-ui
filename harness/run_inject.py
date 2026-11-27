#!/usr/bin/env python3
"""inject-v1.5 harnas: bewijst de B2-live-injectie in een DRAAIENDE v74-GUI zonder reload + de v1.2-wensen:
SBN-banner in B2-stijl bovenin (klok/rijen eronder), straatnaam-SBN onderdrukt, panelen gevuld uit systemApp-cache.

Opzet (hergebruikt ui-oemplus-b2-v1/harness/hlib.py: echte v74-framework/systemApp/Common in headless Chromium,
nep-MMUI via framework.routeMmuiMsg, Presto-shims):
  1. "boot" uit root-stock (= /jci/gui fabriek): home origineel; ecoenergy-app laadt door een MMUI-bericht (zoals op de
     auto: FuelType/IgnitionStatus bij boot) -> ecoenergyApp.js uit stock; eco-templates nog NIET geladen.
  2. "mount": vanaf nu serveert het harnas uit root-inject (= proefkopie + overlay) -- zoals mount --bind tijdens
     draaiende Opera. Alle verzoeken na de mount worden gelogd (bewijs: geen systemApp.js/GuiFramework.js/MainMenuCtrl.js).
  3. Applicaties -> Eco-energie (ctxtChg ecoenergy/FuelConsumption) -> template lazy uit de overlay -> paneel.
  4. Draaiknop: "B2 aan" -> Home -> B2 zichtbaar; berichten komen via de omwikkelde systemApp-handlers binnen.
   v1.3 / P0: bij "B2 aan" landen ook de B2Sub-* links (00..40, ontbrekend = overgeslagen) en body.OemplusB2
   op niet-protected schermen; op protected contexts (backupparking etc.) geen OemplusB2.
  5. Eco opnieuw -> touch "B2 uit" -> Home -> origineel (CSS, constructor, handlers, body-klasse, submenu-links weg).
  6. "Verder naar Eco-scherm" -> origineel eco-scherm; ander eco-template (ControlStatus) krijgt ook het paneel.
  7. Negatief: B2-bestand ontbreekt (404) -> "B2 aan" weigert netjes, home blijft origineel.
Gebruik:  sh harness/build_root.sh && python3 harness/run_inject.py   -> harness/shots/*.png + RESULTS.json
"""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
B2H = os.path.join(HERE, "lib")  # hlib.py blijft uit b2-v1
sys.path.insert(0, B2H)
from hlib import Harness

SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
results = []

def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": detail if isinstance(detail, (str, int, float, bool, list, dict, type(None))) else str(detail)})
    print(("PASS " if ok else "FAIL ") + name + ("  -- " + str(detail)[:300] if detail != "" else ""))


class MountHarness(Harness):
    """Harness met wisselbare root (= bind-mount tijdens draaiende pagina) en verzoek-log."""
    def __init__(self):
        Harness.__init__(self, "stock")
        self.root = os.path.join(HERE, "root-stock")
        self.phase = "boot"
        self.requests = []
        self.block = set()
        self.override = {}      # pad -> bytes (gemanipuleerde B2-variant voor faalpad-checks)
        self.hold = set()       # pad -> verzoek niet beantwoorden (M1: te laat binnenkomend bestand)
        self.held = []

    def mount(self):
        self.root = os.path.join(HERE, "root-inject")
        self.phase = "mounted"

    def _serve(self, route):
        path = re.sub(r"^https?://[^/]+/", "", route.request.url).split("?")[0]
        self.requests.append((self.phase, path))
        if path in self.block:
            return route.fulfill(status=404, body="")
        if path in self.hold:
            self.held.append(route)
            return None
        if path in self.override:
            return route.fulfill(status=200, body=self.override[path], headers={"Content-Type": "application/javascript"})
        return Harness._serve(self, route)

    def release(self):
        """Beantwoord vastgehouden verzoeken alsnog met het echte bestand (te laat)."""
        held, self.held = self.held, []
        self.hold = set()
        for r in held:
            Harness._serve(self, r)


def sysmsg(msgId, payload, uiaId="system"):
    return {"msgType": "msg", "uiaId": uiaId, "msgId": msgId, "params": {"payload": payload}}

def shot(h, name):
    h.page.screenshot(path=os.path.join(SHOTS, name))

def press(h, key, wait=350):
    h.page.keyboard.press(key)
    h.page.wait_for_timeout(wait)

HOME_JS = """() => {
  var t = framework.getAppInstance('system')._currentContextTemplate, c = t && t.mainMenuControl;
  var links = document.querySelectorAll('link'), orgCss = null, b2Css = null, sbCss = null, sbnCss = null, orgIdx = -1;
  var hk = document.head.children;
  for (var i = 0; i < links.length; i++) { var h = links[i].getAttribute('href') || '';
    if (/MainMenu\\/css\\/MainMenuCtrl\\.css$/.test(h)) { orgCss = !links[i].disabled; orgIdx = Array.prototype.indexOf.call(hk, links[i]); }
    if (/MainMenuCtrl-oemplusb2\\.css$/.test(h)) b2Css = !links[i].disabled;
    if (/StatusBarCtrl-oemplusb2\\.css$/.test(h)) sbCss = !links[i].disabled;
    if (/SbnCtrl-oemplusb2\\.css$/.test(h)) sbnCss = !links[i].disabled; }
  var sys = framework.getAppInstance('system'), hooks = 0;
  ['StatusUpdateNotifications','StatusUpdateAudioSource','StatusUpdateMissedCallCount','StatusUpdateSchedMaint'].forEach(function(n){
    if (sys._messageTable[n] && sys._messageTable[n].oemplusInjectWrapper) hooks++; });
  var sbn = document.querySelector('.SbnCtrl');
  var clock = document.querySelector('.MainMenuCtrlB2Clock');
  var row0 = document.querySelector('.MainMenuCtrlAppDiv');
  var sbnRect = sbn ? sbn.getBoundingClientRect() : null;
  var clockRect = clock ? clock.getBoundingClientRect() : null;
  var rowRect = row0 ? row0.getBoundingClientRect() : null;
  /* v1.2-fix B1: rect van het ZICHTBARE contextvak (Focus-div van de gefocuste rij) + watcher-klasse + hit-test */
  var boxEl = null;
  try {
    if (c && c._b2 && c._b2.els) {
      var keys = ['App','Ent','Com','Nav','Set'];
      for (var ki = 0; ki < keys.length; ki++) {
        var e = c._b2.els[keys[ki]];
        if (e && e.box && e.box.parentNode) { boxEl = e.box; break; }
      }
    }
  } catch (eBox) {}
  var boxRect = boxEl ? boxEl.getBoundingClientRect() : null;
  var hitAbove = null, hitIn = null;
  try { if (c && c._hitTestEvent) { hitAbove = c._hitTestEvent({pageX: 600, pageY: 180}); hitIn = c._hitTestEvent({pageX: 600, pageY: 200}); } } catch (eHit) {}
  var subLinks = document.querySelectorAll('link[data-oemplusb2sub]'), subOk = 0, subMissing = [];
  for (var si = 0; si < subLinks.length; si++) { var sh = subLinks[si].getAttribute('href') || '';
    if (/B2Sub-\d\d-.*\.css$/.test(sh)) { subOk++; } }
  var subCls = document.body.classList.contains('OemplusB2');
  return {ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(), hasCtrl: !!c, b2: !!(c && c._b2),
          subCls: subCls, subLinks: subOk, subHrefs: (function(){var a=[]; for (var i=0;i<subLinks.length;i++) a.push(subLinks[i].getAttribute('href')); return a;})(),
          b2Clock: !!clock, body: document.body.className,
          sbVis: getComputedStyle(document.querySelector('.StatusBarCtrl')).visibility,
          sbnVis: sbn ? getComputedStyle(sbn).visibility : null,
          sbnTop: sbnRect ? Math.round(sbnRect.top) : null, sbnBottom: sbnRect ? Math.round(sbnRect.bottom) : null,
          clockTop: clockRect ? Math.round(clockRect.top) : null, rowTop: rowRect ? Math.round(rowRect.top) : null,
          boxTop: boxRect ? Math.round(boxRect.top) : null, boxBottom: boxRect ? Math.round(boxRect.bottom) : null,
          watchCls: document.body.classList.contains('B2SbnWatch'),
          hitAbove: hitAbove, hitIn: hitIn,
          orgCss: orgCss, orgIdx: orgIdx, b2Css: b2Css, sbCss: sbCss, sbnCss: sbnCss, hooks: hooks, fw: framework._frameworkState,
          nCtrl: document.querySelectorAll('.MainMenuCtrl').length, inj: window.OemplusInject ? window.OemplusInject.status() : null,
          comText: c && c._coins && c._coins[2] ? c._coins[2].div.innerText.replace(/\\s+/g,' ').trim() : null,
          entText: c && c._coins && c._coins[1] ? c._coins[1].div.innerText.replace(/\\s+/g,' ').trim() : null,
          setText: c && c._coins && c._coins[4] ? c._coins[4].div.innerText.replace(/\\s+/g,' ').trim() : null};
}"""

PANEL_JS = """() => {
  var p = document.querySelector('.OemplusInjPanel');
  var rows = document.querySelectorAll('.OemplusInjPanel .OemplusInjRow'), r = [];
  for (var i = 0; i < rows.length; i++) r.push({t: rows[i].textContent, cls: rows[i].className});
  return {exists: !!p, vis: p ? getComputedStyle(p).display : null, rows: r,
          state: p ? p.querySelector('.OemplusInjState').textContent : null,
          info: p ? p.querySelector('.OemplusInjInfo').textContent : null,
          inj: window.OemplusInject ? window.OemplusInject.status() : null,
          ctxt: framework.getCurrCtxtId(), app: framework.getCurrentApp(), fw: framework._frameworkState,
          tmpl: (framework.getAppInstance('ecoenergy') && framework.getAppInstance('ecoenergy')._currentContextTemplate || {}).templateName || null};
}"""

def goto(h, uia, ctxt, wait=1800):
    h.ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
    h.page.wait_for_timeout(wait)

def errs(h):
    return list(h.pageerrors) + list(h.ev("window.__errors"))

def main():
    h = MountHarness()
    p = h.start()
    p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)")
    p.wait_for_timeout(800)
    h.ev("framework.common.updateSbClock(new Date(2026,10,25,12,7,0).getTime())")
    # boot-berichten zoals op de auto (postfix-boot-log: ecoenergy FuelType/IgnitionStatus, StatusMenu Available)
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy"),
           sysmsg("StatusMenu", {"statusMenu": {"appName": "ecoenergy", "appStatus": "Available"}}))
    p.wait_for_timeout(1500)
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    check("1 boot (stock): home origineel, geen B2", st["ctxt"] == "HomeScreen" and st["hasCtrl"] and not st["b2"] and not st["b2Clock"] and "OemplusB2Home" not in st["body"], st)
    loaded = h.ev("({eco: !!framework.getAppInstance('ecoenergy'), fc: typeof window.FuelConsumptionTmplt, inj: typeof window.OemplusInject})")
    check("1 boot: ecoenergyApp.js geladen (door MMUI-bericht), eco-templates en inject NIET", loaded == {"eco": True, "fc": "undefined", "inj": "undefined"}, loaded)
    check("1 boot: geen JS-fouten", not errs(h), errs(h))
    org_idx0 = st["orgIdx"]
    shot(h, "i1-boot-home-stock.png")

    # ---- v1.2: statusberichten NA boot maar VOOR de injectie (zoals op de auto) -> systemApp cache ----
    h.mmui(sysmsg("StatusUpdateNotifications", {"messageCounts": {"countEmail": 1, "countSMS": 2}}),
           sysmsg("StatusUpdateMissedCallCount", {"missedCallCount": 5}),
           sysmsg("StatusUpdateSchedMaint", {"due": True}),
           sysmsg("StatusUpdateAudioSource", {"statusAudio": {"audioSource": "FMRadio", "audioActive": "Play"}}))
    p.wait_for_timeout(600)

    # ---- 2. mount ----
    h.mount()
    n_boot = len(h.requests)

    # ---- 3. Applicaties -> Eco-energie ----
    goto(h, "system", "Applications", 2000)
    apps = h.ev("""(function(){var l=framework.getAppInstance('system')._currentContextTemplate.list2Ctrl, r=[];
       for(var i=0;i<l.dataList.items.length;i++){var it=l.dataList.items[i]; r.push(it.appData.appName+(it.disabled?':uit':':aan'));} return r;})()""")
    check("3 Applicaties-lijst (VehicleConfigData Old/onbekend): rij ecoenergy zichtbaar en aan", "ecoenergy:aan" in apps, apps)
    shot(h, "i2-applicaties.png")
    goto(h, "ecoenergy", "FuelConsumption", 2500)
    pn = h.ev(PANEL_JS)
    check("3 eco-scherm opent, FuelConsumptionTmplt lazy uit overlay + paneel getoond",
          pn["exists"] and pn["vis"] == "block" and pn["tmpl"] == "FuelConsumptionTmplt" and len(pn["rows"]) == 4, pn)
    after = [r for ph, r in h.requests[n_boot:]]
    check("3 na mount geladen: FuelConsumptionTmplt.js + OemplusInject.js/.css", all(x in after for x in [
        "apps/ecoenergy/templates/FuelConsumption/js/FuelConsumptionTmplt.js", "apps/ecoenergy/oemplus/OemplusInject.js", "apps/ecoenergy/oemplus/OemplusInject.css"]), after)
    check("3 geen JS-fouten", not errs(h), errs(h))
    shot(h, "i3-eco-paneel.png")

    # ---- 4. draaiknop: B2 aan ----
    press(h, "m"); press(h, "n")          # eerste controller-event = controllerActive; focus naar rij 0
    pn = h.ev(PANEL_JS)
    check("4 draaiknop: focus op 'B2 aan'", "OemplusInjFocus" in pn["rows"][0]["cls"], [r["cls"] for r in pn["rows"]])
    press(h, "Enter", 1500)
    pn = h.ev(PANEL_JS)
    check("4 'B2 aan': B2-bestand geladen, constructor = B2, 4/4 hooks, geen fout", pn["inj"]["on"] and pn["inj"]["ctor"] == "B2" and pn["inj"]["hooks"] == 4 and not pn["inj"]["lastErr"], pn["inj"])
    fw = h.ev("({reg: framework.registerCtrlLoaded === GuiFramework.prototype.registerCtrlLoaded, st: framework._frameworkState, idle: framework._FWK_STATE_IDLE})")
    check("4 framework onverstoord: registerCtrlLoaded terug, state idle", fw["reg"] and fw["st"] == fw["idle"], fw)
    shot(h, "i4-eco-b2-aan.png")
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    check("4 Home: B2 zichtbaar (B2-ctrl, klok, body.OemplusB2Home, statusbalk verborgen, B2-CSS aan, OEM-CSS-link uit de DOM (M3))",
          st["b2"] and st["b2Clock"] and "OemplusB2Home" in st["body"] and st["sbVis"] == "hidden" and st["b2Css"] and st["orgCss"] is None and st["sbCss"], st)
    # ---- v1.3 / P0: submenu-basis ----
    check("4 v1.3 P0: body.OemplusB2 staat op home (niet protected)", st["subCls"] is True, st["body"])
    SUB_EXPECT = ["common/oemplusb2/css/B2Sub-00-base.css",
              "common/oemplusb2/css/B2Sub-10-list2.css", "common/oemplusb2/css/B2Sub-20-dialog3.css",
              "common/oemplusb2/css/B2Sub-30-tabs-slider-button.css", "common/oemplusb2/css/B2Sub-40-media-input.css",
              "common/oemplusb2/css/B2Sub-50-eco.css", "common/oemplusb2/css/B2Sub-60-phone.css"]
    check("4 v1.4 P0: 7 B2Sub-links in DOM in vaste volgorde 00..40,50,60 (P5-eco + P6-phone geland sinds v1.4)",
          st["subLinks"] == 7 and st["subHrefs"] == SUB_EXPECT, st["subHrefs"])
    # P0-check: ALLE B2Sub-paden worden geprobeerd; een bestand dat nu WEL bestaat (P1-P4 geland) mag geladen
    # zijn, een nog-ontbrekend bestand is 404 en wordt overgeslagen zonder fout. Essentieel: 00 geladen + geen
    # B2Sub-pad in 'missing' dat WEL in de overlay zit.
    sub_missing = [m for m in h.missing if "B2Sub" in m]
    sub_present = [p for ph, p in h.requests if "B2Sub-" in p]
    overlay_has = set()
    ovl_css = os.path.join(HERE, "..", "overlay", "common", "oemplusb2", "css")
    if os.path.isdir(ovl_css):
        overlay_has = {"common/oemplusb2/css/" + f for f in os.listdir(ovl_css) if f.endswith(".css")}
    bad_missing = [m for m in sub_missing if m in overlay_has]
    check("4 v1.3 P0: B2Sub-lader probeert alle 5 paden; 00 geladen; geen overlay-aanwezig B2Sub-bestand 404t",
          "common/oemplusb2/css/B2Sub-00-base.css" not in h.missing and not bad_missing,
          {"missing": sub_missing, "present": sorted(overlay_has), "bad_missing": bad_missing, "geladen00": "common/oemplusb2/css/B2Sub-00-base.css" not in h.missing})
    sub_bg = h.ev("getComputedStyle(document.querySelector('.CommonBgImg')).backgroundImage")
    check("4 v1.3 P0: B2Sub-00-base.css actief (CommonBgImg = B2SubBg.png)", "B2SubBg.png" in (sub_bg or ""), sub_bg)
    check("4 v1.3 P0: statusbalk op home verborgen (OemplusB2Home) maar submenu-klasse mag niet storen",
          st["sbVis"] == "hidden" and st["subCls"] is True, {k: st[k] for k in ("sbVis", "subCls")})
    # ---- v1.2: SBN-banner in B2-stijl bovenin; klok/rijen eronder (geen overlap) ----
    st = h.ev(HOME_JS)
    check("4 v1.2: sbnCss (SbnCtrl-oemplusb2.css) geladen naast sbCss", st["sbnCss"] is True and st["sbCss"] is True, {k: st[k] for k in ("sbCss", "sbnCss")})
    check("4 v1.2: klok begint onder de 64px SBN-reservering (clockTop >= 64)", st["b2Clock"] and st["clockTop"] is not None and st["clockTop"] >= 64, st["clockTop"])
    check("4 v1.2: eerste rij begint onder de SBN-reservering (rowTop >= 64)", st["rowTop"] is not None and st["rowTop"] >= 64, st["rowTop"])
    # ---- v1.2-fix B1 (V1): contextvak staat exact op y 188-474 en de touch-zone klopt ----
    check("4 v1.2-fix B1: contextvak top == 188 en bottom <= 480 (was 234-520)",
          st["boxTop"] == 188 and st["boxBottom"] is not None and st["boxBottom"] <= 480,
          {k: st[k] for k in ("boxTop", "boxBottom")})
    check("4 v1.2-fix B1: touch-zone klopt (tik y 180 = geen vak, tik y 200 = vak/focus)",
          st["hitAbove"] == -1 and st["hitIn"] is not None and st["hitIn"] >= 0,
          {k: st[k] for k in ("hitAbove", "hitIn")})
    check("4 v1.2-fix B2: watcher-klasse B2SbnWatch staat op body zolang de watcher draait", st["watchCls"] is True, st["body"])
    # BT-SBN (Style02, typeG btConnecting) zichtbaar in B2-stijl op home.
    # btpairing laadt pas bij een MMUI-bericht (routeMmuiMsg case "msg" -> _addAppFiles); daarna SbnPhoneConnectionStatus.
    # De SBN gaat via framework.common.startTimedSbn (eigen wrapper) -> mag NIET onderdrukt worden.
    h.ev("framework.common.startTimedSbn('btpairing', 'PhoneConnectionStatus', 'btConnecting', {sbnStyle: 'Style02', text1Id: 'PhoneConnected', imagePath1: 'common/images/icons/IcnSbBluetooth.png'})")
    p.wait_for_timeout(1200)
    st = h.ev(HOME_JS)
    check("4 v1.2: BT-SBN (Style02) WEL zichtbaar op B2-home (sbnVis visible)", st["sbnVis"] == "visible" and st["sbnTop"] is not None and st["sbnBottom"] <= 64,
          {k: st[k] for k in ("sbnVis", "sbnTop", "sbnBottom")})
    check("4 v1.2-fix B2: met levende watcher schuift de banner in (sbnTop == 1 na B2SbnIn, binnen de 64px band)",
          st["sbnTop"] == 1, st["sbnTop"])
    shot(h, "i5c-home-b2-bt-sbn.png")
    # straatnaam-SBN (emnavi StateSbn_NextTurn, Style05 navigationNear) wordt ONDERDRUKT
    n_dropped0 = st["inj"]["sbnDropped"]
    h.ev("framework.common.showStateSbn('emnavi', 'emnaviTurnByTurnStateSbn', 'navigationNear', {sbnStyle: 'Style05', hasManeuverIcon: true, hasManeuverDistance: true, imagePath1: 'common/images/icons/IcnTbt3.png', text1Id: 'Meter', text1SubMap: {value: 5, spacing: ''}, text3: 'Teststraat 12'})")
    p.wait_for_timeout(900)
    st = h.ev(HOME_JS)
    check("4 v1.2: straatnaam-SBN (Style05 navigationNear) ONDERDRUKT (sbnDropped +1, BT-SBN blijft staan)",
          st["inj"]["sbnDropped"] == n_dropped0 + 1 and st["sbnVis"] == "visible" and st["sbnBottom"] <= 64,
          {"dropped": st["inj"]["sbnDropped"], "sbnVis": st["sbnVis"], "sbnBottom": st["sbnBottom"]})
    h.ev("framework.common.showStateSbn('emnavi', 'emnaviTurnByTurnStateSbn', 'navigationFar', {sbnStyle: 'Style05', text3: 'Teststraat 12'})")
    p.wait_for_timeout(600)
    st = h.ev(HOME_JS)
    check("4 v1.2: navigationFar (typeJ) ook onderdrukt (sbnDropped +2)", st["inj"]["sbnDropped"] == n_dropped0 + 2, st["inj"]["sbnDropped"])
    # de BT-SBN is intussen afgelopen (timed) -> nu zou GEEN SbnCtrl moeten staan; stuur een errorNotification
    # (typeF, veiligheid) -> WEL tonen (nooit onderdrukt)
    h.ev("framework.common.startTimedSbn('btaudio', 'MobileDeviceError', 'errorNotification', {sbnStyle: 'Style02', text1Id: 'MobileDeviceError', imagePath1: 'common/images/icons/IcnSbnSystemError.png'})")
    p.wait_for_timeout(1200)
    st = h.ev(HOME_JS)
    check("4 v1.2: veiligheidsmelding (typeF errorNotification) wordt NIET onderdrukt (wel SbnCtrl, dropped gelijk)",
          st["sbnVis"] == "visible" and st["inj"]["sbnDropped"] == n_dropped0 + 2, {"sbnVis": st["sbnVis"], "dropped": st["inj"]["sbnDropped"]})
    shot(h, "i5d-home-b2-veiligheid-sbn.png")
    h.mmui(sysmsg("StatusUpdateMissedCallCount", {"missedCallCount": 3}))
    p.wait_for_timeout(400)
    st = h.ev(HOME_JS)
    check("4 B2 krijgt systemApp-bericht via omwikkelde handler (3 gemist)", st["hooks"] == 4 and st["comText"] and " 3 GEMIST" in st["comText"], st["comText"])
    # v1.2-fix B3-repro: audio-bericht KOMT NA 'aan' binnen -> echte status in de cache én in het paneel
    h.mmui(sysmsg("StatusUpdateAudioSource", {"statusAudio": {"audioSource": "FMRadio", "audioActive": "Play"}}))
    p.wait_for_timeout(400)
    st = h.ev(HOME_JS)
    check("4 v1.2-fix B3: bericht na 'aan' zet Ent op 'Speelt nu' (cache + paneel)",
          st["entText"] and "Speelt nu" in st["entText"], st["entText"])
    orig_ok = h.ev("framework.getAppInstance('system')._missedCallCount !== undefined || true")
    check("4 geen JS-fouten", not errs(h), errs(h))
    shot(h, "i5-home-b2.png")
    # v1.2: panelen direct gevuld uit de systemApp-cache (berichten kwamen voor de injectie binnen)
    st = h.ev(HOME_JS)
    check("4 v1.2: Com-paneel gevuld uit cache (tellers gevuld, geen streepjes: gemist + berichten)",
          st["comText"] and "GEMIST" in st["comText"] and "BERICHTEN" in st["comText"] and "\u2013" not in st["comText"] and "-" not in st["comText"].replace("display","").replace("geluid",""), st["comText"])
    check("4 v1.2: Set-paneel gevuld uit cache (_SchedMaintDueStatus due=true -> Onderhoud nodig)",
          st["setText"] and "Onderhoud nodig" in st["setText"], st["setText"])
    check("4 v1.2: Ent-paneel gevuld uit cache (now-playing icon -> FMRadio)",
          st["entText"] and ("FM" in st["entText"] or "Radio" in st["entText"] or "radio" in st["entText"]), st["entText"])
    p.keyboard.press("m"); p.wait_for_timeout(300); p.keyboard.press("n"); p.wait_for_timeout(500)
    shot(h, "i5b-home-b2-focus.png")

    # ---- 5. weg en terug; dan uit via touch ----
    goto(h, "system", "Communication", 1800)
    st = h.ev(HOME_JS)
    check("5 weg van home: statusbalk terug, body-klasse OemplusB2Home weg", "OemplusB2Home" not in st["body"] and st["sbVis"] == "visible", st)
    # v1.3 / P0: op een basis-List2-scherm (Communication = List2Tmplt) WEL OemplusB2 (niet protected)
    check("5 v1.4 P0: op Communication (List2) staat body.OemplusB2 (7 links)", st["subCls"] is True and st["subLinks"] == 7, {k: st[k] for k in ("subCls", "subLinks")})
    # P0-generieke checks op dit basis-List2-scherm: hitboxes gelijk met B2 aan/uit, focus-volgorde gelijk
    hb_on = h.ev("""(function(){ var out = []; var els = document.querySelectorAll('.ListItem, .LeftBtnCtrlBackBtn, .StatusBarCtrlHomeBtn');
      for (var i = 0; i < els.length && i < 12; i++) { var r = els[i].getBoundingClientRect(); out.push([els[i].className.split(' ')[0], Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]); }
      out.sort(); return out; })()""")
    foc_on = h.ev("(function(){ var t = framework.getAppInstance('system')._currentContextTemplate; var r = []; for (var k = 0; k < 3; k++) { r.push(t.handleControllerEvent('cw')); } return r; })()")
    # protected context: system/DisplayOff moet de klasse weghalen SYNCHROON (R-cmu F1/V1): registreer de klasse
    # op het moment van template-constructie + transitie-einde (hook in het harnas), niet na een wachttijd.
    h.ev("""(function(){ window.__h9 = []; window.__h9save = {i: framework.instantiateTemplate, t: framework._transitionChange};
        var fw = framework;
        var oi = fw.instantiateTemplate;
        fw.instantiateTemplate = function(){ window.__h9.push(['inst', arguments[2], document.body.classList.contains('OemplusB2')]); return oi.apply(fw, arguments); };
        var ot = fw._transitionChange;
        fw._transitionChange = function(en){ var r = ot.apply(fw, arguments); window.__h9.push(['trans-end', fw.getCurrentApp(), fw.getCurrCtxtId(), document.body.classList.contains('OemplusB2')]); return r; };
        return true; })()""")
    goto(h, "system", "DisplayOff", 1500)
    h9 = h.ev("window.__h9")
    h.ev("""(function(){ var fw = framework, sv = window.__h9save; fw.instantiateTemplate = sv.i;
        fw._transitionChange = sv.t; window.__h9 = null; window.__h9save = null; })()""")
    st = h.ev(HOME_JS)
    inst = [e for e in h9 if e[0] == "inst" and len(e) > 2]
    # alleen de instantiateTemplate(s) van de DisplayOff-transitie (de OffScreenTmplt direct na de ctxt-wissel);
    # trans-end van een ANDERE context (bv. nog Communication) hoort daar niet bij.
    trans = [e for e in h9 if e[0] == "trans-end" and len(e) > 3 and e[2] == "DisplayOff"]
    check("5 v1.4 P0 (H9 synchroon, echte meting): protected system/DisplayOff -> %d inst + %d trans-end, ALLEmaal ZONDER OemplusB2 (nu subCls=%s)" % (len(inst), len(trans), st["subCls"]),
          st["subCls"] is False and len(inst) >= 1 and all(e[2] is False for e in inst) and len(trans) > 0 and all(e[3] is False for e in trans),
          {"h9": h9, "st": {k: st[k] for k in ("ctxt", "subCls", "body")}})
    # v1.4 (H2 harnas-fix): mutatietest -- bewaker-wrappers eraf -> de H9-check hierboven MOET falen als hij
    # echt meet. We meten ALLEEN binnen instantiateTemplate (synchroon, vóór de 500 ms guardTick) met de klasse
    # handmatig AAN en de twee inject-wrappers vervangen door de prototype-functies; daarna direct herstellen.
    mut = h.ev("""(function(){ var fw = framework;
        window.__mut = {t: fw._transitionChange, c: fw._callHandleContext};
        if (fw._transitionChange && fw._transitionChange.oemplusInjectWrapper) fw._transitionChange = GuiFramework.prototype._transitionChange;
        if (fw._callHandleContext && fw._callHandleContext.oemplusInjectWrapper) fw._callHandleContext = GuiFramework.prototype._callHandleContext;
        document.body.classList.add('OemplusB2');
        window.__h9m = [];
        var oi = fw.instantiateTemplate; window.__h9moi = oi;
        fw.instantiateTemplate = function(){ window.__h9m.push(['inst', arguments[2], document.body.classList.contains('OemplusB2')]); return oi.apply(fw, arguments); };
        return [fw._transitionChange === GuiFramework.prototype._transitionChange, fw._callHandleContext === GuiFramework.prototype._callHandleContext]; })()""")
    # forceer direct de context-wissel (zoals _contextChange dat doet) en lees de recorder VÓÓR enige timer
    h.ev("(function(){ try { framework._callHandleContext({uiaId:'system', ctxtId:'DisplayOff', params:null, contextSeq:998}); } catch(e){} try { framework._transitionChange(false); } catch(e2){} })()")
    p.wait_for_timeout(300)
    h9m = h.ev("window.__h9m")
    h.ev("""(function(){ var fw = framework;
        if (window.__h9moi) { fw.instantiateTemplate = window.__h9moi; window.__h9moi = null; }
        if (window.__mut) { fw._transitionChange = window.__mut.t; fw._callHandleContext = window.__mut.c; window.__mut = null; }
        window.__h9m = null; document.body.classList.remove('OemplusB2'); })()""")
    instm = [e for e in h9m if e[0] == "inst" and len(e) > 2]
    # met bewaker UIT moet de klasse tijdens constructie AAN zijn (mutatie) -> H9 zou FALEN = check is echt
    check("5 v1.4 (H2 mutatietest, wrappers weg %s): inst-event ZIET klasse AAN (%s) => H9-check is echt (zou FAIL)" % (mut, instm),
          len(instm) >= 1 and any(e[2] is True for e in instm), {"h9m": h9m, "mut": mut})
    goto(h, "system", "Communication", 2000)
    st = h.ev(HOME_JS)
    check("5 v1.4 mutatie-opruim: na restore staat OemplusB2 weer correct (subCls=%s op Communication)" % st["subCls"], st["subCls"] is True, {k: st[k] for k in ("ctxt", "subCls")})
    # B2 uit -> hitboxes moeten identiek blijven (H1) en focus-volgorde gelijk (H2)
    h.ev("OemplusInject.b2Off()")
    p.wait_for_timeout(600)
    st_off = h.ev(HOME_JS)
    check("5 v1.3 P0 (H6): na b2Off geen body.OemplusB2 en geen B2Sub-links meer", st_off["subCls"] is False and st_off["subLinks"] == 0, {k: st_off[k] for k in ("subCls", "subLinks")})
    hb_off = h.ev("""(function(){ var out = []; var els = document.querySelectorAll('.ListItem, .LeftBtnCtrlBackBtn, .StatusBarCtrlHomeBtn');
      for (var i = 0; i < els.length && i < 12; i++) { var r = els[i].getBoundingClientRect(); out.push([els[i].className.split(' ')[0], Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]); }
      out.sort(); return out; })()""")
    check("5 v1.3 P0 (H1): touch-hitboxes List2-scherm gelijk met B2 aan/uit (0 px verschil)", hb_on == hb_off, {"aan": hb_on, "uit": hb_off})
    foc_off = h.ev("(function(){ var t = framework.getAppInstance('system')._currentContextTemplate; var r = []; for (var k = 0; k < 3; k++) { r.push(t.handleControllerEvent('cw')); } return r; })()")
    check("5 v1.3 P0 (H2): focus-volgorde (cw x3) gelijk met B2 aan/uit", foc_on == foc_off, {"aan": foc_on, "uit": foc_off})
    # late lazy-CSS: B2Sub-00 geladen vóór het List2-template -> computed style toch B2 (H3).
    # B2Sub-00 raadt ALLEEN boot-controls (CommonBgImg/StatusBar/LeftBtn/Sbn); de lijst-tekst zelf is P1.
    # H3 hier geverifieerd op een boot-control: CommonBgImg moet B2SubBg.png tonen ook al is de
    # List2-template-CSS later in <head> geladen (prefix body.OemplusB2 wint op specificiteit).
    b2on_again = h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(400)
    bg_on = h.ev("getComputedStyle(document.querySelector('.CommonBgImg')).backgroundImage")
    sbapp_col = h.ev("(function(){ var el = document.querySelector('.StatusBarCtrlAppName'); return el ? getComputedStyle(el).fontSize : null; })()")
    check("5 v1.3 P0 (H3): B2Sub-00 prefix wint van later geladen lazy-CSS (CommonBgImg = B2SubBg.png, app-naam 30px)",
          b2on_again is True and "B2SubBg.png" in (bg_on or "") and sbapp_col == "30px", {"bg": bg_on, "appNameFs": sbapp_col})
    # B2 opnieuw aan voor de rest van het script
    goto(h, "system", "HomeScreen", 2200)
    st = h.ev(HOME_JS)
    check("5 v1.3 P0: na her-aan weer B2 home + OemplusB2", st["b2"] and "OemplusB2Home" in st["body"] and st["subCls"] is True, {k: st[k] for k in ("b2", "body", "subCls")})
    check("5 terug op home: weer B2 (cache: 3 gemist)", st["b2"] and "OemplusB2Home" in st["body"] and st["comText"] and " 3 GEMIST" in st["comText"], st["comText"])
    # v1.2-fix B3 (V3): tweede home-bezoek: Ent toont de echte audiostatus uit de cache ("Speelt nu"),
    # de seed mag die NIET overschrijven met "Actieve bron" (bericht kwam na 'aan' binnen -> in cache)
    check("5 v1.2-fix B3: tweede home-bezoek toont Ent 'Speelt nu' uit cache (seed overschrijft niet)",
          st["entText"] and "Speelt nu" in st["entText"] and "Actieve bron" not in st["entText"], st["entText"])
    check("5 v1.2-fix B2: na weg-terug is de watcher-klasse er weer (B2SbnWatch aan)", st["watchCls"] is True, st["body"])
    # panel-klikkers: de rijen zitten in PAGINA-coördinaten (paneel top 64 + template offset). Rijen: top 128/182/236/290, 48 hoog.
    def click_row(i, wait=700):
        p.mouse.click(340, 128 + i * 54 + 24)
        p.wait_for_timeout(wait)
    goto(h, "ecoenergy", "FuelConsumption", 2200)
    pn = h.ev(PANEL_JS)
    check("5 eco opnieuw: paneel weer (status 'B2 (actief)')", pn["exists"] and "B2 (actief)" in (pn["state"] or ""), pn["state"])
    click_row(1, 900)                               # rij 1 "B2 uit"
    pn = h.ev(PANEL_JS)
    check("5 touch 'B2 uit': constructor origineel, hooks 0, subOn false, geen OemplusB2, geen B2Sub-links",
          (not pn["inj"]["on"]) and pn["inj"]["ctor"] == "origineel" and pn["inj"]["hooks"] == 0 and pn["inj"]["subOn"] is False and pn["inj"]["subClass"] is False and pn["inj"]["subLinks"] == 0, pn["inj"])
    shot(h, "i6-eco-b2-uit.png")
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    check("5 Home na 'uit': origineel (geen B2, OEM-CSS aan, B2-CSS weg, sbnCss weg, statusbalk zichtbaar, geen OemplusB2/B2Sub)",
          st["hasCtrl"] and not st["b2"] and not st["b2Clock"] and "OemplusB2Home" not in st["body"] and st["orgCss"] is True and st["b2Css"] is None and st["sbCss"] is None and st["sbnCss"] is None and st["sbVis"] == "visible" and st["subCls"] is False and st["subLinks"] == 0, st)
    check("5 M3: originele MainMenuCtrl.css-link op exact dezelfde plek in <head> terug", st["orgIdx"] == org_idx0 and org_idx0 >= 0, [org_idx0, st["orgIdx"]])
    sbnhooks = h.ev("['startTimedSbn','showStateSbn','endStateSbn','cancelTimedSbn'].filter(function(n){return framework.common[n] && framework.common[n].oemplusInjectSbnWrapper;}).length")
    check("5 v1.2: na 'uit' zijn de 4 SBN-hooks weg (Common-prototype onaangeroerd)", sbnhooks == 0, sbnhooks)
    shot(h, "i7-home-origineel-terug.png")

    # ---- 5b. M2: "aan" terwijl het OEM-home in beeld is -> CSS pas bij de eerste B2-constructie ----
    on = h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(400)
    st = h.ev(HOME_JS)
    check("5b M2: 'aan' op het OEM-home: OEM-CSS blijft, B2-CSS/sbnCss nog niet (uitgesteld), home blijft origineel",
          on and st["ctxt"] == "HomeScreen" and not st["b2"] and st["orgCss"] is True and st["b2Css"] is None and st["sbnCss"] is None and st["inj"]["on"] and not st["inj"]["cssOn"], st)
    goto(h, "system", "Communication", 1800)
    goto(h, "system", "HomeScreen", 2400)
    st = h.ev(HOME_JS)
    check("5b M2: volgende Home = B2, nu pas B2-CSS + sbnCss aan en OEM-CSS-link weg", st["b2"] and st["b2Css"] and st["sbnCss"] and st["orgCss"] is None and st["inj"]["cssOn"], st)
    goto(h, "system", "Communication", 1800)
    # M4: klasse die blijft hangen buiten home wordt door de bewaker weggehaald
    h.ev("document.body.classList.add('OemplusB2Home')")
    p.wait_for_timeout(900)
    st = h.ev(HOME_JS)
    check("5b M4: body.OemplusB2Home buiten home binnen 1 s weg (bewaker), statusbalk zichtbaar", "OemplusB2Home" not in st["body"] and st["sbVis"] == "visible", st["body"])
    h.ev("OemplusInject.b2Off()")
    goto(h, "system", "HomeScreen", 2200)
    st = h.ev(HOME_JS)
    check("5b na b2Off: home origineel, OEM-CSS terug op dezelfde plek", not st["b2"] and st["orgCss"] is True and st["orgIdx"] == org_idx0 and st["b2Css"] is None, st)
    stock = os.path.join(HERE, "shots", "i1-boot-home-stock.png")

    # ---- 6. Info / verder naar eco / ander template / tweede keer aan ----
    goto(h, "ecoenergy", "FuelConsumption", 2000)
    click_row(2, 600)                               # rij 2 "Info"
    pn = h.ev(PANEL_JS)
    check("6 Info toont versie + status", "inject-v1" in (pn["info"] or ""), pn["info"])
    shot(h, "i8-eco-info.png")
    click_row(3, 600)                               # rij 3 "Verder naar Eco-scherm"
    pn = h.ev(PANEL_JS)
    ev = h.ev("(function(){var t=framework.getAppInstance('ecoenergy')._currentContextTemplate; return t.handleControllerEvent('cw');})()")
    check("6 'Verder naar Eco-scherm': paneel weg, events naar originele FuelConsumptionCtrl", pn["vis"] == "none" and not errs(h), {"vis": pn["vis"], "cw": ev})
    shot(h, "i9-eco-origineel.png")
    goto(h, "ecoenergy", "ControlStatus", 2200)
    pn = h.ev(PANEL_JS)
    check("6 ander eco-template (EcoStatusTmplt) lazy uit overlay, ook met paneel", pn["exists"] and pn["tmpl"] == "EcoStatusTmplt", pn["tmpl"])
    press(h, "m"); press(h, "n"); press(h, "Enter", 1200)
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    check("6 tweede keer 'aan' (bestand al geladen, geen 2e load): B2 op home", st["b2"] and "OemplusB2Home" in st["body"], st)
    nload = sum(1 for ph, r in h.requests if r.endswith("MainMenuCtrl-oemplusb2.js"))
    check("6 MainMenuCtrl-oemplusb2.js precies 1x opgehaald", nload == 1, nload)
    goto(h, "ecoenergy", "FuelConsumption", 1800)
    h.ev("OemplusInject.b2Off()")
    goto(h, "system", "HomeScreen", 2200)
    st = h.ev(HOME_JS)
    check("6 weer uit -> home origineel", not st["b2"] and st["orgCss"] is True, st)

    # ---- bewijs: niets van de al geladen kern opnieuw gelezen ----
    after = sorted(set(r for ph, r in h.requests[n_boot:]))
    core = [r for r in after if r in ("apps/system/js/systemApp.js", "framework/js/GuiFramework.js", "common/js/Common.js",
                                      "apps/system/controls/MainMenu/js/MainMenuCtrl.js", "apps/system/templates/MainMenu/js/MainMenuTmplt.js",
                                      "apps/ecoenergy/js/ecoenergyApp.js", "index.html")]
    check("bewijs: na mount GEEN herlezing van systemApp/GuiFramework/Common/MainMenuCtrl/MainMenuTmplt/ecoenergyApp/index.html", core == [], core)
    check("einde: geen JS-fouten", not errs(h), errs(h))
    reqlog = {"boot": sorted(set(r for ph, r in h.requests[:n_boot])), "na_mount": after}
    h.stop()

    # ---- 7. negatief: B2-bestand ontbreekt ----
    h2 = MountHarness()
    h2.block.add("apps/system/controls/MainMenu/js/MainMenuCtrl-oemplusb2.js")
    p2 = h2.start(); p2.wait_for_timeout(2500)
    h2.ev("framework.localize.setLanguage('nl_NL', false)"); p2.wait_for_timeout(600)
    h2.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy")); p2.wait_for_timeout(1000)
    goto(h2, "system", "HomeScreen", 2000)
    h2.mount()
    goto(h2, "ecoenergy", "FuelConsumption", 2200)
    press(h2, "m"); press(h2, "n"); press(h2, "Enter", 1500)
    pn = h2.ev(PANEL_JS)
    check("7 negatief (B2-bestand 404): 'aan' weigert, fout in Info, constructor origineel", (not pn["inj"]["on"]) and pn["inj"]["ctor"] == "origineel" and pn["inj"]["lastErr"] and "NIET" in (pn["info"] or ""), pn["inj"])
    fw = h2.ev("({reg: framework.registerCtrlLoaded === GuiFramework.prototype.registerCtrlLoaded, st: framework._frameworkState, idle: framework._FWK_STATE_IDLE})")
    check("7 negatief: framework onverstoord", fw["reg"] and fw["st"] == fw["idle"], fw)
    shot(h2, "i10-negatief-404.png")
    goto(h2, "system", "HomeScreen", 2200)
    st = h2.ev(HOME_JS)
    check("7 negatief: home origineel", st["hasCtrl"] and not st["b2"] and st["orgCss"] is True and "OemplusB2Home" not in st["body"], st)
    check("7 negatief: alleen verwachte fout (geen pageerror)", not h2.pageerrors, h2.pageerrors)
    h2.stop()

    failpaths()

    nfail = sum(1 for r in results if not r["ok"])
    json.dump({"checks": results, "failed": nfail, "requests": reqlog, "console_errors": [c for c in h.console if c.startswith("error")]},
              open(os.path.join(HERE, "RESULTS.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

def boot_mounted(override=None, hold=None):
    """Nieuwe sessie: boot uit stock, Home, mount, eco openen. override: pad->bytes; hold: set van paden."""
    h = MountHarness()
    if override:
        h.override.update(override)
    if hold:
        h.hold.update(hold)
    p = h.start(); p.wait_for_timeout(2500)
    h.ev("framework.localize.setLanguage('nl_NL', false)"); p.wait_for_timeout(600)
    h.mmui(sysmsg("FuelType", {"FuelType": 0}, "ecoenergy")); p.wait_for_timeout(1000)
    goto(h, "system", "HomeScreen", 2000)
    h.mount()
    goto(h, "ecoenergy", "FuelConsumption", 2200)
    return h, p

B2JS = "apps/system/controls/MainMenu/js/MainMenuCtrl-oemplusb2.js"

def b2variant(fn):
    data = open(os.path.join(HERE, "root-inject", B2JS), "rb").read().decode("ascii")
    out = fn(data)
    assert out != data, "variant niet toegepast"
    return out.encode("ascii")

FW_JS = "({reg: framework.registerCtrlLoaded === GuiFramework.prototype.registerCtrlLoaded, st: framework._frameworkState, idle: framework._FWK_STATE_IDLE})"

def home_is_original(st):
    return st["ctxt"] == "HomeScreen" and st["hasCtrl"] and not st["b2"] and not st["b2Clock"] and st["nCtrl"] == 1 and \
        st["orgCss"] is True and st["b2Css"] is None and st["sbCss"] is None and st.get("sbnCss") is None and \
        "OemplusB2Home" not in st["body"] and st["sbVis"] == "visible" and \
        st.get("subCls") is False and st.get("subLinks") == 0   # v1.3: ook submenu-klasse/links weg

def failpaths():
    CTOR = "function MainMenuCtrl(uiaId, parentDiv, controlId, properties)\n{\n"
    # ---- 8. H2: B2-constructor gooit meteen ----
    h, p = boot_mounted(override={B2JS: b2variant(lambda d: d.replace(CTOR, CTOR + "    throw new Error('harnas: B2-ctor gooit (begin)');\n", 1))})
    press(h, "m"); press(h, "n"); press(h, "Enter", 1500)
    pn = h.ev(PANEL_JS)
    check("8 H2 (ctor gooit bij begin): 'aan' zelf lukt (bestand geladen)", pn["inj"]["on"] and pn["inj"]["ctor"] == "B2", pn["inj"])
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    fw = h.ev(FW_JS)
    check("8 H2: zelfde Home toont het ORIGINELE home (1 control, OEM-CSS, geen B2-resten)", home_is_original(st), st)
    check("8 H2: B2 automatisch uit (on=false, ctor origineel, hooks 0), fout 'B2-constructor' in Info", (not st["inj"]["on"]) and st["inj"]["ctor"] == "origineel" and
          st["inj"]["hooks"] == 0 and "B2-constructor" in st["inj"]["lastErr"] and st["inj"]["b2Errors"] >= 1, st["inj"])
    check("8 H2: framework idle (geen hangende transitie), geen pageerror", fw["st"] == fw["idle"] and not h.pageerrors, [fw, h.pageerrors])
    shot(h, "i11-h2-ctor-gooit-home-origineel.png")
    goto(h, "system", "Communication", 1800); goto(h, "system", "HomeScreen", 2200)
    st = h.ev(HOME_JS)
    check("8 H2: ook de volgende Home origineel", home_is_original(st), st)
    h.stop()

    # ---- 9. H2: B2-constructor gooit halverwege (na DOM-opbouw en body-luisteraar) ----
    h, p = boot_mounted(override={B2JS: b2variant(lambda d: d.replace("    this._b2Start();\n}", "    throw new Error('harnas: B2-ctor gooit (halverwege)');\n    this._b2Start();\n}", 1))})
    nb = h.ev("(function(){ var n = 0, a = EventTarget.prototype.addEventListener, r = EventTarget.prototype.removeEventListener; window.__bodyL = 0;"
              " EventTarget.prototype.addEventListener = function(t,f,c){ if (this === document.body && t === 'mousedown') window.__bodyL++; return a.call(this,t,f,c); };"
              " EventTarget.prototype.removeEventListener = function(t,f,c){ if (this === document.body && t === 'mousedown') window.__bodyL--; return r.call(this,t,f,c); }; return 1; })()")
    press(h, "m"); press(h, "n"); press(h, "Enter", 1500)
    l0 = h.ev("window.__bodyL")
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    check("9 H2 (ctor gooit halverwege): origineel home, halve B2-DOM weg (1 MainMenuCtrl, geen B2-klok)", home_is_original(st), st)
    l1 = h.ev("window.__bodyL")
    check("9 H2: mousedown-luisteraar van de halve B2-instantie verwijderd (netto alleen die van het originele home)", l1 - l0 == 1, [l0, l1])
    check("9 H2: B2 uit, fout gemeld, geen pageerror", (not st["inj"]["on"]) and "B2-constructor" in st["inj"]["lastErr"] and not h.pageerrors, [st["inj"], h.pageerrors])
    h.stop()

    # ---- 10. H3-pad 2: B2-methode gooit tijdens de transitie weg van home ----
    h, p = boot_mounted(override={B2JS: b2variant(lambda d: d.replace('framework.registerCtrlLoaded("MainMenuCtrl");',
        "MainMenuCtrl.prototype.startTransitionFrom = function () { throw new Error('harnas: transitie gooit'); };\n"
        'framework.registerCtrlLoaded("MainMenuCtrl");', 1))})
    press(h, "m"); press(h, "n"); press(h, "Enter", 1500)
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    check("10 (transitie gooit): B2-home eerst normaal zichtbaar", st["b2"] and "OemplusB2Home" in st["body"], st)
    goto(h, "system", "Communication", 2200)
    st = h.ev(HOME_JS); fw = h.ev(FW_JS)
    check("10 weg van home ondanks gooiende startTransitionFrom: ctxt Communication, framework idle (geen State Timeout)",
          st["ctxt"] == "Communication" and fw["st"] == fw["idle"], [st["ctxt"], fw])
    check("10 body-klasse weg, statusbalk zichtbaar, B2 automatisch uit, fout gemeld", "OemplusB2Home" not in st["body"] and st["sbVis"] == "visible" and
          (not st["inj"]["on"]) and "startTransitionFrom" in st["inj"]["lastErr"] and st["inj"]["liveB2"] == 0, st)
    goto(h, "system", "HomeScreen", 2400)
    st = h.ev(HOME_JS)
    check("10 volgende Home origineel (OEM-CSS terug na cleanUp van de B2-instantie)", home_is_original(st), st)
    check("10 geen pageerror", not h.pageerrors, h.pageerrors)
    shot(h, "i12-transitiefout-home-origineel.png")
    h.stop()

    # ---- 11. M1: B2-bestand komt pas na de 8 s-timeout binnen ----
    h, p = boot_mounted(hold={B2JS})
    press(h, "m"); press(h, "n"); press(h, "Enter", 400)
    p.wait_for_timeout(9000)
    pn = h.ev(PANEL_JS)
    check("11 M1: na 8 s timeout: 'NIET aangezet', constructor origineel", (not pn["inj"]["on"]) and pn["inj"]["ctor"] == "origineel" and "timeout" in pn["inj"]["lastErr"] and "NIET" in (pn["info"] or ""), pn["inj"])
    shot(h, "i13-m1-timeout.png")
    h.release()
    p.wait_for_timeout(1500)
    late = h.ev("({ctorOrg: window.MainMenuCtrl === MainMenuCtrl && !(window.MainMenuCtrl.prototype && window.MainMenuCtrl.prototype._b2Start), "
                "reg: framework.registerCtrlLoaded === GuiFramework.prototype.registerCtrlLoaded, st: OemplusInject.status()})")
    check("11 M1: te laat binnengekomen B2-bestand verandert niets (MainMenuCtrl = origineel, registerCtrlLoaded terug, 'te laat' gelogd)",
          late["ctorOrg"] and late["reg"] and not late["st"]["on"] and any("te laat" in e for e in late["st"]["events"]), late)
    goto(h, "system", "HomeScreen", 2400)
    st = h.ev(HOME_JS); fw = h.ev(FW_JS)
    check("11 M1: Home origineel, framework idle, geen pageerror", home_is_original(st) and fw["st"] == fw["idle"] and not h.pageerrors, [st, fw, h.pageerrors])
    h.stop()

    # ---- 12. B2-bestand voert uit maar registreert niet (fout halverwege het script) ----
    h, p = boot_mounted(override={B2JS: b2variant(lambda d: d.replace('framework.registerCtrlLoaded("MainMenuCtrl");', "throw new Error('harnas: script breekt af');", 1))})
    press(h, "m"); press(h, "n"); press(h, "Enter", 1500)
    pn = h.ev(PANEL_JS)
    ctor = h.ev("!(window.MainMenuCtrl.prototype && window.MainMenuCtrl.prototype._b2Start)")
    check("12 script zonder registratie: 'aan' weigert snel, window.MainMenuCtrl terug op het origineel", (not pn["inj"]["on"]) and ctor and "NIET" in (pn["info"] or ""), [pn["inj"], ctor])
    goto(h, "system", "HomeScreen", 2400)
    st = h.ev(HOME_JS)
    check("12 Home origineel", home_is_original(st), st)
    h.stop()

    # ---- 13. fix B2 (V2): _b2WatchSbn gooit -> geen watcher, geen B2SbnWatch, maar de SBN-banner is WEL zichtbaar ----
    h, p = boot_mounted(override={B2JS: b2variant(lambda d: d.replace("this._b2WatchSbn();", "throw new Error('harnas: watcher faalt');", 1))})
    press(h, "m"); press(h, "n"); press(h, "Enter", 1500)
    goto(h, "system", "HomeScreen", 2500)
    st = h.ev(HOME_JS)
    check("13 B2-fail (watcher faalt): home is B2 + body.OemplusB2Home, maar B2SbnWatch NIET gezet",
          st["b2"] and "OemplusB2Home" in st["body"] and st["watchCls"] is False, {k: st[k] for k in ("b2", "body", "watchCls")})
    h.ev("framework.common.startTimedSbn('btpairing', 'PhoneConnectionStatus', 'btConnecting', {sbnStyle: 'Style02', text1Id: 'PhoneConnected', imagePath1: 'common/images/icons/IcnSbBluetooth.png'})")
    p.wait_for_timeout(1200)
    st = h.ev(HOME_JS)
    check("13 B2-fail: SBN-banner ZICHTBAAR zonder watcher (fail-visible: top == 1, NIET -60; bottom <= 64)",
          st["sbnVis"] == "visible" and st["sbnTop"] == 1 and st["sbnBottom"] is not None and st["sbnBottom"] <= 64,
          {k: st[k] for k in ("sbnVis", "sbnTop", "sbnBottom", "watchCls")})
    check("13 B2-fail: geen pageerror", not h.pageerrors, h.pageerrors)
    shot(h, "i14-b2-fail-sbn-zichtbaar.png")
    h.stop()

if __name__ == "__main__":
    main()
