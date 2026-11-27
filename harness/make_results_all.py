#!/usr/bin/env python3
"""Bouwt harness/RESULTS-ALL.json voor v1.4 uit de individuele suite-RESULTS + tool-checks (zelfde formaat als v1.3)."""
import os, json, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = ["RESULTS.json", "RESULTS-P1.json", "RESULTS-P2.json", "RESULTS-P3.json", "RESULTS-P4.json",
          "RESULTS-CUM.json", "RESULTS-V14-BEWAKER.json", "RESULTS-V14-SBN.json", "RESULTS-V14-SCHERMEN.json",
          "RESULTS-V14-TERMINAL.json", "RESULTS-P5.json", "RESULTS-P6.json"]
out = {"datum": "2026-11-27", "integratie": "v1.4 (kopie v1.3 stand 7af37847 + live-bevindingen 2026-11-27 + punt 8 terminal)", "suites": {}}
tot = fail = skip = 0
for f in SUITES:
    fp = os.path.join(HERE, f)
    if not os.path.isfile(fp):
        continue
    d = json.load(open(fp))
    checks = d.get("checks", d.get("results", []))
    n = len(checks)
    nf = sum(1 for c in checks if c.get("ok") is False)
    ns = sum(1 for c in checks if c.get("skip"))
    out["suites"][f] = {"pakket": d.get("pakket", f), "checks": n, "failed": nf, "skipped": ns}
    tot += n; fail += nf; skip += ns
r = subprocess.run([sys.executable, os.path.join(HERE, "..", "tools", "check_presto.py")],
                   capture_output=True, text=True)
out["tools/check_presto.py"] = {"pakket": "Presto/ES5 + ASCII (JS+CSS in overlay)",
                                "checks": "OK" if "RESULTAAT: OK" in r.stdout else r.stdout[-200:], "failed": 0 if "RESULTAAT: OK" in r.stdout else 1}
r2 = subprocess.run(["sh", os.path.join(HERE, "..", "tools", "test_scripts_bb119.sh")], capture_output=True, text=True)
m = [l for l in r2.stdout.splitlines() if "PASS" in l and "FAIL" in l]
bb = m[-1] if m else "onbekend"
out["tools/test_scripts_bb119.sh"] = {"pakket": "busybox 1.19 chroot; overlay 183 toegestaan; revert -> kopie == /jci/gui",
                                       "checks": bb.strip(), "failed": 0 if "0 FAIL" in bb else 1}
out["totaal_checks"] = tot
out["totaal_fail"] = fail
out["totaal_skip"] = skip
json.dump(out, open(os.path.join(HERE, "RESULTS-ALL.json"), "w"), indent=1)
print(json.dumps(out, indent=1)[:1200])
print("TOTAAL: %d checks, %d fail, %d skip" % (tot, fail, skip))
sys.exit(1 if fail else 0)
