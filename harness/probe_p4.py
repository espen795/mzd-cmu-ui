#!/usr/bin/env python3
"""Kleine probe: waarom lukt de ctxtChg naar syssettings/ComposeMessage niet in het P4-harnas?"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
B2H = os.path.join(HERE, "lib")
sys.path.insert(0, B2H)
from hlib import Harness

class MH(Harness):
    def __init__(self):
        Harness.__init__(self, "stock")
        self.root = os.path.join(HERE, "root-stock")
    def _serve(self, route):
        path = re.sub(r"^https?://[^/]+/", "", route.request.url).split("?")[0]
        return Harness._serve(self, route)

h = MH()
p = h.start()
p.wait_for_timeout(2500)
h.ev("framework.localize.setLanguage('nl_NL', false)")
p.wait_for_timeout(600)
h.mmui({"msgType": "msg", "uiaId": "ecoenergy", "msgId": "FuelType", "params": {"payload": {"FuelType": 0}}})
p.wait_for_timeout(1200)
h.ev("framework.debug.fakeCtxtChgMsgs('system','HomeScreen')")
p.wait_for_timeout(2000)
print("boot app:", h.ev("framework.getCurrentApp()"), "ctxt:", h.ev("framework.getCurrCtxtId()"))

def wait_idle(uia):
    for _ in range(25):
        p.wait_for_timeout(400)
        if h.ev("!!framework.getAppInstance('%s')" % uia) and h.ev("framework._frameworkState") == h.ev("framework._FWK_STATE_IDLE"):
            return True
    return False

def goto(uia, ctxt, wait=2200):
    if not h.ev("!!framework.getAppInstance('%s')" % uia):
        h.mmui({"msgType": "ctxtChg", "ctxtId": ctxt, "uiaId": uia, "params": None})
        wait_idle(uia)
        p.wait_for_timeout(500)
    st0 = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId()})")
    if st0["app"] == uia and st0["ctxt"] == ctxt:
        h.ev("framework.debug.fakeCtxtChgMsgs('system','HomeScreen')")
        p.wait_for_timeout(2000)
    for _ in range(4):
        h.ev("framework.debug.fakeCtxtChgMsgs('%s','%s')" % (uia, ctxt))
        p.wait_for_timeout(wait)
        for _ in range(12):
            st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
            if st["app"] == uia and st["ctxt"] == ctxt and st["fw"] == h.ev("framework._FWK_STATE_IDLE"):
                break
            p.wait_for_timeout(400)
        st = h.ev("({app: framework.getCurrentApp(), ctxt: framework.getCurrCtxtId(), fw: framework._frameworkState})")
        print("  goto %s/%s -> app=%s ctxt=%s fw=%s" % (uia, ctxt, st["app"], st["ctxt"], st["fw"]))
        if st["app"] == uia and st["ctxt"] == ctxt:
            return True
    return False

print("--- goto syssettings/ComposeMessage")
ok = goto("syssettings", "ComposeMessage")
print("ok:", ok, "KB in DOM?", h.ev("!!document.querySelector('.KeyboardCtrl')"))
print("errors:", h.ev("window.__errors"), h.pageerrors)
print("missing tail:", h.missing[-8:])
p.screenshot(path=os.path.join(HERE, "shots", "probe-kb.png"))
print("--- goto phone/DialPad (terug)")
goto("phone", "DialPad")
print("--- goto backupparking/BackupCameraDisplay")
goto("backupparking", "BackupCameraDisplay")
print("body class:", h.ev("document.body.className"))
print("errors:", h.ev("window.__errors"), h.pageerrors)
h.stop()
