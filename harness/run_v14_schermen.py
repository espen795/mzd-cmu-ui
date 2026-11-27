#!/usr/bin/env python3
"""v1.4-harnas punten 5+6 (ML4): reproduceert de live-bevindingen "Systeeminformatie-tab toont niet goed",
"Muziekdatabase bijwerken toont niet goed" (syssettings/SystemTab, List2Tmplt + tabsStyle2 + smallItemText)
en "inkomende-oproep-popup redelijk defect" (phone/IncomingCall, Dialog3Tmplt style04 titleStyle02,
2 knoppen red/green) met B2 aan vs uit in een DRAAIENDE v74-GUI; meet layout (rects, overflow, font-sizes,
zichtbaarheid) en nimmt screenshots aan/uit.

Punt 5: SystemTab openen (tab 7 = System), vergelijkt alle zichtbare .ListItem-rects + titel + tabs met B2
aan/uit; checkt of tekst buiten het item valt (scrollWidth > clientWidth zonder ellipsis?), of items
onder de 416px-grens vallen, font-size >= 24; ook About (List2 listTitle smallItemText) en de
sysupdate/Dialog3 (SearchMusicDBUpdates = "Muziekdatabase bijwerken" flow).
Punt 6: phone/IncomingCall openen, checkt Dialog3 paneel-rect binnen 800x416, knoppenrij y 318-398,
2 knoppen 330 breed, titleStyle02 titel zichtbaar, style04 Text1/Text2 (contactnaam/bron) binnen paneel,
hitboxes gelijk B2 aan/uit (H1), focus-wandeling gelijk (H2).

Gebruik:  sh harness/build_root.sh && python3 harness/run_v14_schermen.py
Output:   harness/RESULTS-V14-SCHERMEN.json + shots/v14-sys-*.png / v14-call-*.png ; exit 1 bij fail.
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

def goto(h, p, uia, ctxt, wait=2600):
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

STATE_JS = """() => ({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(),
  subCls: document.body.classList.contains('OemplusB2'), body: document.body.className,
  inj: window.OemplusInject ? window.OemplusInject.status() : null})"""

LAYOUT_JS = """(function(){
  function rect(el){ var r = el.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }
  var out = {items: [], titel: null, tabs: [], dialog: null, knoppen: [], texts: []};
  var t = document.querySelector('.List2CtrlTitle') || document.querySelector('.TabsCtrl') || document.querySelector('[class*="TabsCtrl"]') || document.querySelector('[class*="tabsCtrl"]');
  if (t) out.titel = {rect: rect(t), fs: t.querySelector('.line1') ? getComputedStyle(t.querySelector('.line1')).fontSize : getComputedStyle(t).fontSize, cls: t.className};
  var tabs = document.querySelectorAll('.TabsCtrlStyle2 [class*="ButtonEnabled"], .TabsCtrlStyle2 [class*="Button"]');
  for (var i = 0; i < tabs.length && i < 10; i++) out.tabs.push({cls: tabs[i].className, rect: rect(tabs[i])});
  var items = document.querySelectorAll('.List2Ctrl .ListItem');
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    var l1 = it.querySelector('.line1'), l2 = it.querySelector('.line2');
    out.items.push({cls: it.className, rect: rect(it),
      fs1: l1 ? getComputedStyle(l1).fontSize : null, fs2: l2 ? getComputedStyle(l2).fontSize : null,
      overflow: l1 ? (l1.scrollWidth > l1.clientWidth + 1) : null,
      bottom: Math.round(it.getBoundingClientRect().bottom)});
  }
  var d = document.querySelector('.Dialog3Ctrl');
  if (d) {
    out.dialog = {rect: rect(d), cls: d.className};
    var btns = d.querySelectorAll('.Dialog3Ctrl_Buttons [class*="ButtonStyle"]');
    for (var i = 0; i < btns.length; i++) out.knoppen.push({cls: btns[i].className, rect: rect(btns[i]),
      fs: getComputedStyle(btns[i]).fontSize, color: getComputedStyle(btns[i]).color});
    var txts = d.querySelectorAll('[class*="_Text"], [class*="TitleStyle"]');
    for (var i = 0; i < txts.length && i < 8; i++) { var e = txts[i]; var r = e.getBoundingClientRect();
      out.texts.push({cls: e.className, rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)],
        fs: getComputedStyle(e).fontSize, inPanel: r.left >= 0 && r.right <= 800 && r.top >= 64 && r.bottom <= 480}); }
  }
  return out;
})()"""

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
    p.keyboard.press("m"); p.wait_for_timeout(250); p.keyboard.press("n"); p.wait_for_timeout(300)
    p.keyboard.press("Enter"); p.wait_for_timeout(1600)
    st = h.ev("window.OemplusInject.status()")
    check("setup: B2 aan", st["on"] and st["subOn"], {k: st[k] for k in ("on", "subOn", "subLinks")})

    # ================= punt 5a: syssettings/SystemTab (tab 7) =================
    goto(h, p, "syssettings", "SystemTab", 3000)
    st = h.ev(STATE_JS)
    check("punt5 setup: syssettings/SystemTab geladen met B2 (body %s)" % st["body"],
          st["app"] == "syssettings" and st["ctxt"] == "SystemTab" and st["subCls"] is True, {k: st[k] for k in ("app", "ctxt", "subCls", "body")})
    # tab 7 (System) selecteren zoals de gebruiker doet
    h.ev("""(function(){ var a = framework.getAppInstance('syssettings'); var t = a._currentContextTemplate;
        if (t && t.list2Ctrl && t.list2Ctrl.tabsCtrl) { try { t.list2Ctrl.tabsCtrl.handleControllerEvent('right'); } catch(e){} }
        try { t.handleControllerEvent('controllerActive'); } catch(e){} })()""")
    p.wait_for_timeout(400)
    lay_on = h.ev(LAYOUT_JS)
    p.screenshot(path=os.path.join(SHOTS, "v14-sys-systemtab-aan.png"))
    hb_on = hitboxes(h, ".List2Ctrl .ListItem")
    hb_on_tabs = hitboxes(h, ".TabsCtrlStyle2 [class*='Button']")
    foc_on = focus_walk(h, 6, ["cw", "cw", "cw", "ccw", "select", "cw"])
    # B2 uit -> zelfde scherm, compare
    h.ev("OemplusInject.b2Off()"); p.wait_for_timeout(700)
    st_off = h.ev(STATE_JS)
    lay_off = h.ev(LAYOUT_JS)
    p.screenshot(path=os.path.join(SHOTS, "v14-sys-systemtab-uit.png"))
    hb_off = hitboxes(h, ".List2Ctrl .ListItem")
    hb_off_tabs = hitboxes(h, ".TabsCtrlStyle2 [class*='Button']")
    foc_off = focus_walk(h, 6, ["cw", "cw", "cw", "ccw", "select", "cw"])
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(600)
    check("punt5 SystemTab (H1): item-hitboxes gelijk B2 aan/uit", hb_on == hb_off, {"diff": [x for x in hb_on if x not in hb_off]})
    check("punt5 SystemTab (H1): tab-hitboxes gelijk B2 aan/uit", hb_on_tabs == hb_off_tabs, {"diff": [x for x in hb_on_tabs if x not in hb_off_tabs]})
    check("punt5 SystemTab (H2): focus-wandeling gelijk B2 aan/uit", foc_on == foc_off, {"aan": foc_on, "uit": foc_off})
    # layout-sanity met B2 aan: alle items binnen content (y 64..480), titel aanwezig, font >= 24 (smallItemText!
    # SystemTab zet smallItemText:true -> OEM line1 is dan kleiner; B2-token forceert 30px !important)
    items_ok = all(it["rect"][1] >= 64 and it["bottom"] <= 480 for it in lay_on["items"]) if lay_on["items"] else False
    fs_ok = all((it["fs1"] is None or float(re.sub(r"[^0-9.]", "", it["fs1"])) >= 24) for it in lay_on["items"])
    check("punt5 SystemTab: %d items allemaal binnen y 64..480 met B2 aan" % len(lay_on["items"]), items_ok and len(lay_on["items"]) > 0,
          [it for it in lay_on["items"] if it["rect"][1] < 64 or it["bottom"] > 480][:5])
    check("punt5 SystemTab: item line1 font-size >= 24px met B2 aan (smallItemText override)", fs_ok,
          [(it["fs1"], it["cls"][:40]) for it in lay_on["items"]])
    tabs_dom = h.ev("""(function(){ var els = document.querySelectorAll('[class*="TabsCtrl"], [class*="tabsCtrl"], .List2CtrlTitle');
        var out = []; for (var i = 0; i < els.length && i < 12; i++) { var r = els[i].getBoundingClientRect();
          out.push([els[i].className.split(' ')[0], Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height), getComputedStyle(els[i]).visibility]); }
        return out; })()""")
    check("punt5 SystemTab: tabbalk/titel-elementen in DOM met B2 aan (n=%d, allemaal visible)" % len(tabs_dom),
          len(tabs_dom) > 0 and all(t[5] == "visible" for t in tabs_dom), tabs_dom)
    # v1.4-fix check: bij tabsTitle is de titel-tekst verborgen (visibility hidden), niet over de tabs
    titel_vis = h.ev("""(function(){
        var l = document.querySelector('.List2Ctrl .List2CtrlTitle .line1') || document.querySelector('.List2CtrlTitle .line1');
        if (l) return 'line1:' + getComputedStyle(l).visibility;
        var tabs = document.querySelector('.TabsCtrl, [class*="TabsCtrl"], [class*="tabsCtrl"]');
        if (tabs) return 'TABS:' + getComputedStyle(tabs).visibility + ':' + tabs.className;
        return 'GEEN-TITEL-NIET-NIET'; })()""")
    check("punt5 SystemTab: titel-zone met tabsTitle (line1 hidden OF tabbalk zichtbaar) -- geen overlap over tabs: %s" % titel_vis,
          str(titel_vis).startswith("line1:hidden") or str(titel_vis).startswith("TABS:visible"), titel_vis)
    # verschilanalyse: wat is ANDERS aan de layout aan vs uit (behalve font/kleur)?
    lay_diff = []
    for a, b in zip(lay_on["items"], lay_off["items"]):
        if a["rect"] != b["rect"]:
            lay_diff.append({"aan": a["rect"], "uit": b["rect"], "cls": a["cls"][:50]})
    check("punt5 SystemTab: geen rect-wijziging per item (alleen skin mag verschillen)", not lay_diff, lay_diff[:5])
    check("punt5 SystemTab: geen JS-fouten", not errs(h), errs(h))

    # ================= punt 5b: syssettings/About (listTitle + smallItemText) =================
    goto(h, p, "syssettings", "About", 2600)
    st = h.ev(STATE_JS)
    check("punt5b setup: syssettings/About geladen met B2", st["ctxt"] == "About" and st["subCls"] is True, {k: st[k] for k in ("ctxt", "subCls")})
    lay = h.ev(LAYOUT_JS)
    p.screenshot(path=os.path.join(SHOTS, "v14-sys-about-aan.png"))
    items_ok = all(it["rect"][1] >= 64 and it["bottom"] <= 480 for it in lay["items"]) if lay["items"] else False
    fs_ok = all((it["fs1"] is None or float(re.sub(r"[^0-9.]", "", it["fs1"])) >= 24) for it in lay["items"])
    check("punt5b About: items binnen y 64..480 + font >= 24 met B2 aan (n=%d)" % len(lay["items"]), items_ok and fs_ok and len(lay["items"]) > 0,
          {"items": [(it["rect"], it["fs1"]) for it in lay["items"]], "titel": lay["titel"]})

    # ================= punt 5c: sysupdate/SearchMusicDBUpdates (Dialog3 "Muziekdatabase bijwerken") =================
    goto(h, p, "sysupdate", "SearchMusicDBUpdates", 3000)
    st = h.ev(STATE_JS)
    lay = h.ev(LAYOUT_JS)
    p.screenshot(path=os.path.join(SHOTS, "v14-sys-musicdb-aan.png"))
    d_ok = lay["dialog"] is not None and lay["dialog"]["rect"][0] == 0 and lay["dialog"]["rect"][1] == 64
    txt_ok = all(t["inPanel"] for t in lay["texts"]) if lay["texts"] else False
    fs_ok = all(float(re.sub(r"[^0-9.]", "", t["fs"])) >= 24 for t in lay["texts"]) if lay["texts"] else False
    check("punt5c sysupdate/SearchMusicDBUpdates: dialog 800x416 op y64, teksten binnen paneel, fs >= 24 (n=%d)" % len(lay["texts"]),
          d_ok and txt_ok and fs_ok and len(lay["texts"]) > 0,
          {"dialog": lay["dialog"], "texts": lay["texts"][:6], "ctxt": st["ctxt"]})
    # v1.4 live-bewijs (v13-muziekdb.png): de onderliggende lijst mag NIET door de dialoog heen zichtbaar zijn.
    # Pixel-check: lees de alpha van B2DialogBg.png op een punt BUITEN het paneel maar binnen de dialog
    # (bijv. x 400, y 20 = boven het paneel, binnen de 416 zone) -- daar moet de scrim dekkend zijn (alpha 255).
    px = h.ev("""(function(){
      return new Promise(function(res){
        var img = new Image();
        img.onload = function(){
          var c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
          var ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
          var d = ctx.getImageData(400, 5, 1, 1).data;     // scrim-zone boven paneel (y 5, binnen 416)
          var d2 = ctx.getImageData(5, 200, 1, 1).data;    // scrim-zone links van paneel
          res({scrimTop: [d[0], d[1], d[2], d[3]], scrimLeft: [d2[0], d2[1], d2[2], d2[3]]});
        };
        img.onerror = function(){ res({err:'img load fail'}); };
        img.src = 'common/oemplusb2/images/B2DialogBg.png';
      });
    })()""")
    p.screenshot(path=os.path.join(SHOTS, "v14-sys-musicdb-aan.png"))
    scrim = h.ev("""(function(){
      var d = document.querySelector('.Dialog3Ctrl');
      if (!d) return {err: 'geen dialog'};
      var el = document.elementFromPoint(400, 240);
      var inDlg = false, e = el; while (e) { if (e === d) { inDlg = true; break; } e = e.parentNode; }
      return {topEl: el ? (el.className || el.tagName) : null, inDlg: inDlg};
    })()""")
    check("punt5c dekking: B2DialogBg.png scrim alpha=255 buiten paneel (top=%s left=%s); element op (400,240) in dialog=%s"
          % (px.get("scrimTop"), px.get("scrimLeft"), scrim.get("inDlg")),
          isinstance(px, dict) and px.get("scrimTop") and px["scrimTop"][3] == 255 and px.get("scrimLeft") and px["scrimLeft"][3] == 255 and scrim.get("inDlg") is True,
          {"px": px, "scrim": scrim})

    # ================= punt 5d: sysupdate/SoftwareInfo (style23, 3 tekstregels + OK) -- exact v13-sysinfo.png =================
    goto(h, p, "sysupdate", "SoftwareInfo", 3000)
    st = h.ev(STATE_JS)
    lay = h.ev(LAYOUT_JS)
    p.screenshot(path=os.path.join(SHOTS, "v14-sys-softwareinfo-aan.png"))
    t23 = [t for t in lay["texts"] if "Style23" in t["cls"]]
    # Style23 content-zone: top 86 + height 233 binnen dialog (y 64..480) => tekst-bottoms <= 64+86+233 = 383;
    # knoppenrij start op dialog-y 318 => pagina-y 382. Eis: geen Style23-tekst over de knoppenrij (bottom <= 382).
    overlap = [t for t in t23 if t["rect"][1] + t["rect"][3] > 382]
    d_ok = lay["dialog"] and lay["dialog"]["rect"] == [0, 64, 800, 416]
    check("punt5d sysupdate/SoftwareInfo (style23): dialog 800x416 op y64, %d Style23-teksten, geen overlap met knoppenrij (bottom <= 382)" % len(t23),
          d_ok and len(t23) == 3 and not overlap, {"dialog": lay["dialog"], "t23": t23})
    scrim2 = h.ev("""(function(){ var d = document.querySelector('.Dialog3Ctrl'); var el = document.elementFromPoint(400, 240);
      var inDlg = false, e = el; while (e) { if (e === d) { inDlg = true; break; } e = e.parentNode; } return inDlg; })()""")
    check("punt5d SoftwareInfo: element op (400,240) zit IN de dialog (dekking boven onderliggende lijst)", scrim2 is True, scrim2)

    # ================= punt 6: phone/IncomingCall (Dialog3 style04, 2 knoppen red/green) =================
    goto(h, p, "phone", "IncomingCall", 3000)
    st = h.ev(STATE_JS)
    check("punt6 setup: phone/IncomingCall geladen met B2 (body %s)" % st["body"],
          st["app"] == "phone" and st["ctxt"] == "IncomingCall" and st["subCls"] is True, {k: st[k] for k in ("app", "ctxt", "subCls", "body")})
    lay_on = h.ev(LAYOUT_JS)
    p.screenshot(path=os.path.join(SHOTS, "v14-call-incoming-aan.png"))
    hb_on = hitboxes(h, ".Dialog3Ctrl_Buttons [class*='ButtonStyle']")
    foc_on = focus_walk(h, 5, ["cw", "cw", "select", "ccw", "select"])
    # B2 uit
    h.ev("OemplusInject.b2Off()"); p.wait_for_timeout(700)
    lay_off = h.ev(LAYOUT_JS)
    p.screenshot(path=os.path.join(SHOTS, "v14-call-incoming-uit.png"))
    hb_off = hitboxes(h, ".Dialog3Ctrl_Buttons [class*='ButtonStyle']")
    foc_off = focus_walk(h, 5, ["cw", "cw", "select", "ccw", "select"])
    h.ev("new Promise(function(res){ OemplusInject.b2On(function(ok){ res(ok); }); })")
    p.wait_for_timeout(600)
    check("punt6 IncomingCall (H1): knop-hitboxes exact gelijk B2 aan/uit (OEM-identiek)", hb_on == hb_off,
          {"aan": hb_on, "uit": hb_off})
    check("punt6 IncomingCall (H2): focus/select-gedrag gelijk B2 aan/uit", foc_on == foc_off, {"aan": foc_on, "uit": foc_off})
    check("punt6 IncomingCall: dialog 800x416 op y64 met B2 aan", lay_on["dialog"] and lay_on["dialog"]["rect"] == [0, 64, 800, 416], lay_on["dialog"])
    check("punt6 IncomingCall: 2 knoppen in rij y 382..462 (knoppenrij y 318 binnen dialog + 64 offset), 330 breed, 80 hoog", len(lay_on["knoppen"]) == 2 and
          all(k["rect"][1] == 382 and k["rect"][3] == 80 and k["rect"][2] == 330 for k in lay_on["knoppen"]), lay_on["knoppen"])
    red_green = [k["cls"] for k in lay_on["knoppen"]]
    check("punt6 IncomingCall: knop-klassen red+green intact (weigeren/opnemen) met B2 aan", any("Red" in c for c in red_green) and any("Green" in c for c in red_green), red_green)
    txt_ok = all(t["inPanel"] for t in lay_on["texts"] if "Image" not in t["cls"]) if lay_on["texts"] else False
    fs_ok = all(float(re.sub(r"[^0-9.]", "", t["fs"])) >= 24 for t in lay_on["texts"] if "Image" not in t["cls"]) if lay_on["texts"] else False
    check("punt6 IncomingCall: alle TEKSTEN (titel style02 + style04 Text1/Text2) binnen 800x480 paneel, fs >= 24 (n=%d; Image-vak 12px is icoon, whitelist)" % len([t for t in lay_on["texts"] if "Image" not in t["cls"]]),
          txt_ok and fs_ok and len(lay_on["texts"]) > 0, lay_on["texts"])
    # knop-rects moeten gelijk zijn aan/uit (H1) -- al gecheckt; extra: titel niet over knoppenrij
    titel = [t for t in lay_on["texts"] if "TitleStyle" in t["cls"]]
    check("punt6 IncomingCall: titel boven knoppenrij (bottom <= 382)", all(t["rect"][1] + t["rect"][3] <= 382 for t in titel), titel)
    check("punt6: geen JS-fouten", not errs(h), errs(h))
    h.stop()

    nfail = sum(1 for r in results if r["ok"] is False)
    json.dump({"pakket": "v1.4 punten 5+6 (SystemTab/About/MusicDB + IncomingCall)", "checks": results, "failed": nfail},
              open(os.path.join(HERE, "RESULTS-V14-SCHERMEN.json"), "w"), indent=1)
    print("\n%d checks, %d gefaald" % (len(results), nfail))
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
