#!/usr/bin/env python3
"""check_presto.py (HOST) -- statische Opera 12.10/Presto 2.12-check voor ui-oemplus-inject-v1.5/overlay.

Hergebruikt de regels van ui-oemplus-b2-v1/tools/check_presto.py (JS_RULES, CSS_RULES, strip_js, acorn ES5-parse):
  * NIEUWE JS/CSS: hele bestand: ASCII, ES5-regels / CSS-regels, marker OEMPLUS-INJECT of OEMPLUS-B2.
  * VERVANGEN v74-bestanden (de 4 ecoenergy-templates): ASCII- en regex-regels alleen op de TOEGEVOEGDE regels
    (de OEM-tekst heeft al niet-ASCII in commentaar), marker OEMPLUS-INJECT verplicht, en het HELE bestand moet
    ES5-parsen (acorn ecmaVersion 5). Daarnaast: verwijderde regels t.o.v. v74 = fout (alleen invoegen toegestaan).
Exit 0 = OK, 1 = overtreding(en).
"""
import os, re, sys, glob, difflib, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
MZD = ROOT  # public repo: own CMU dumps live in <repo>/stock/
V74 = os.path.join(MZD, "stock/v74/jci/gui")
OVL = os.path.join(ROOT, "overlay")

# regels uit de B2-check laden zonder die uit te voeren (die draait op import zijn eigen main-code)
B2CHK = os.path.join(MZD, "tools/lib/check_presto_b2.py")
src = open(B2CHK, encoding="utf-8").read()
cut = src.index("jsfiles = sorted(")
ns = {"__file__": B2CHK}
exec(compile(src[:cut].replace("OVL = sys.argv[1]", "OVL = \"/\" #"), B2CHK, "exec"), ns)
JS_RULES, CSS_RULES, strip_js, acorn_parse = ns["JS_RULES"], ns["CSS_RULES"], ns["strip_js"], ns["acorn_parse"]

errors, notes = [], []
MARK = ("OEMPLUS-INJECT", "OEMPLUS-B2")

def added_lines(orig, new):
    a, b = orig.split("\n"), new.split("\n")
    out, removed = [], 0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            out.extend(range(j1, j2))
    return out, removed

jsfiles = sorted(glob.glob(os.path.join(OVL, "**", "*.js"), recursive=True))
cssfiles = sorted(glob.glob(os.path.join(OVL, "**", "*.css"), recursive=True))

for f in jsfiles:
    rel = os.path.relpath(f, OVL)
    raw = open(f, "rb").read()
    txt = raw.decode("latin-1")
    orig_p = os.path.join(V74, rel)
    if os.path.exists(orig_p):
        otxt = open(orig_p, "rb").read().decode("latin-1")
        idx, removed = added_lines(otxt, txt)
        if removed:
            errors.append("%s: %d originele regel(s) gewijzigd/verwijderd (alleen invoegen toegestaan)" % (rel, removed))
        if "OEMPLUS-INJECT" not in txt:
            errors.append("%s: marker OEMPLUS-INJECT ontbreekt" % rel)
        notes.append("%s: vervangen v74-bestand, %d toegevoegde regels gecontroleerd" % (rel, len(idx)))
    else:
        idx = None
        if not any(m in txt for m in MARK):
            errors.append("%s: marker ontbreekt" % rel)
    lines = txt.split("\n")
    code = strip_js(txt).split("\n")
    for ln in (idx if idx is not None else range(len(lines))):
        if any(ord(c) > 127 for c in lines[ln]):
            errors.append("%s:%d niet-ASCII-teken" % (rel, ln + 1))
        for rx, what in JS_RULES:
            if ln < len(code) and re.search(rx, code[ln]):
                errors.append("%s:%d %s: %s" % (rel, ln + 1, what, lines[ln].strip()[:90]))
    res = acorn_parse(f)
    if res is None:
        notes.append("%s: acorn niet gevonden, alleen regex-check" % rel)
    elif res != "OK":
        errors.append("%s: ES5-parse (acorn ecmaVersion 5) faalt: %s" % (rel, res))
    else:
        notes.append("%s: ES5-parse OK (acorn ecmaVersion 5)" % rel)

for f in cssfiles:
    rel = os.path.relpath(f, OVL)
    s = open(f, encoding="utf-8").read()
    if not any(m in s for m in MARK):
        errors.append("%s: marker ontbreekt" % rel)
    if any(ord(c) > 127 for c in s):
        errors.append("%s: niet-ASCII" % rel)
    code = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), s, flags=re.S)
    for ln, line in enumerate(code.split("\n"), 1):
        for rx, what in CSS_RULES:
            if re.search(rx, line):
                errors.append("%s:%d %s: %s" % (rel, ln, what, line.strip()[:90]))

print("check_presto (inject-v1.5): %d JS, %d CSS in %s" % (len(jsfiles), len(cssfiles), OVL))
for n in notes:
    print("  info  " + n)
for e in errors:
    print("  FOUT  " + e)
print("RESULTAAT: " + ("OK" if not errors else "%d overtreding(en)" % len(errors)))
sys.exit(1 if errors else 0)
