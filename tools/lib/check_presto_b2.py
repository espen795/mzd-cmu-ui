#!/usr/bin/env python3
"""check_presto.py -- statische check van de overlay voor Opera 12.10 / Presto 2.12 (HOST).

JS  (alle overlay/**/*.js):
  * alleen ASCII (eis amendement v1.3 A6.5)
  * geen ES6: let/const, =>, template strings, class, spread, for..of, default params, async/await,
    Promise/Map/Set/Symbol, Object.assign, .includes(), .startsWith/.endsWith, generator function*
  * echte ES5-parse met acorn (ecmaVersion 5) als acorn beschikbaar is (anders alleen regex)
  * elke overlay-JS bevat de marker OEMPLUS-B2
CSS (alle overlay/**/*.css):
  * transform/transition/transform-origin alleen met -o- prefix (OEM-stijl; animation mag unprefixed zoals OEM)
  * geen CSS-variabelen (var(--, --x:), geen grid, geen flex, geen calc(), geen CSS-gradients, geen filter/box-shadow
  * marker OEMPLUS-B2 aanwezig
Exit 0 = alles OK, 1 = overtreding(en).  Gebruik: python3 tools/check_presto.py [overlay-dir]
"""
import os, re, sys, glob, json, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OVL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "overlay")
OVL = os.path.normpath(OVL)
errors = []
notes = []

def strip_js(src):
    """Verwijder commentaar en string-/regex-inhoud (ruw, voldoende voor deze code) zodat regels op code werken."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("//", i):
            j = src.find("\n", i); j = n if j < 0 else j; out.append(" " * (j - i)); i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", src[i:j])); i = j
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(c + " " * (j - i - 1) + c); i = j + 1
        elif c == "`":
            out.append("`"); i += 1      # template string: laten staan zodat de regel hem vindt
        else:
            out.append(c); i += 1
    return "".join(out)

JS_RULES = [
    (r"\blet\s+[A-Za-z_$]", "let"),
    (r"\bconst\s+[A-Za-z_$]", "const"),
    (r"=>", "arrow function"),
    (r"`", "template string"),
    (r"\bclass\s+[A-Za-z_$]", "class"),
    (r"\.\.\.", "spread/rest"),
    (r"\bfor\s*\([^)]*\bof\b", "for..of"),
    (r"function\s*\*", "generator"),
    (r"\basync\s+function|\bawait\s", "async/await"),
    (r"\b(Promise|Map|Set|WeakMap|Symbol|Proxy|Reflect)\s*[.(]", "ES6 builtin"),
    (r"Object\.assign|Array\.from|\.includes\(|\.startsWith\(|\.endsWith\(|\.find\(|\.findIndex\(", "ES6 methode"),
    (r"function\s*[A-Za-z_$]*\s*\([^)]*=", "default parameter"),
]

CSS_RULES = [
    (r"(?<![-\w])transform\s*:", "transform zonder -o-"),
    (r"(?<![-\w])transition\s*:", "transition zonder -o-"),
    (r"(?<![-\w])transition-(property|duration|timing-function|delay)\s*:", "transition-* zonder -o-"),
    (r"(?<![-\w])transform-origin\s*:", "transform-origin zonder -o-"),
    (r"var\(\s*--", "CSS-variabele"),
    (r"(^|[;{\s])--[A-Za-z][\w-]*\s*:", "CSS custom property"),
    (r"display\s*:\s*(-\w+-)?(inline-)?(grid|flex)", "grid/flex"),
    (r"\bgrid-(template|area|column|row)", "grid"),
    (r"\bcalc\(", "calc()"),
    (r"gradient\(", "CSS-gradient (hoort in PNG)"),
    (r"(?<![-\w])(filter|box-shadow|backdrop-filter)\s*:", "filter/box-shadow"),
]

def acorn_parse(path):
    mod = os.path.expanduser("~/.local/lib/node_modules/openclaw/node_modules/acorn")
    if not os.path.isdir(mod):
        return None
    js = ("const a=require(%s);const fs=require('fs');try{a.parse(fs.readFileSync(%s,'utf8'),{ecmaVersion:5});"
          "console.log('OK')}catch(e){console.log('ERR '+e.message)}") % (json.dumps(mod), json.dumps(path))
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()

jsfiles = sorted(glob.glob(os.path.join(OVL, "**", "*.js"), recursive=True))
cssfiles = sorted(glob.glob(os.path.join(OVL, "**", "*.css"), recursive=True))
for f in jsfiles:
    rel = os.path.relpath(f, OVL)
    raw = open(f, "rb").read()
    try:
        raw.decode("ascii")
    except UnicodeDecodeError as e:
        line = raw[:e.start].count(b"\n") + 1
        errors.append("%s:%d niet-ASCII-teken" % (rel, line))
    src = raw.decode("utf-8", "replace")
    if "OEMPLUS-B2" not in src:
        errors.append("%s: marker OEMPLUS-B2 ontbreekt" % rel)
    code = strip_js(src)
    for ln, line in enumerate(code.split("\n"), 1):
        for rx, what in JS_RULES:
            if re.search(rx, line):
                errors.append("%s:%d %s: %s" % (rel, ln, what, src.split("\n")[ln - 1].strip()[:90]))
    res = acorn_parse(f)
    if res is None:
        notes.append("%s: acorn niet gevonden, alleen regex-check" % rel)
    elif res != "OK":
        errors.append("%s: ES5-parse (acorn ecmaVersion 5) faalt: %s" % (rel, res))
    else:
        notes.append("%s: ES5-parse OK (acorn ecmaVersion 5)" % rel)

for f in cssfiles:
    rel = os.path.relpath(f, OVL)
    src = open(f, encoding="utf-8").read()
    if "OEMPLUS-B2" not in src:
        errors.append("%s: marker OEMPLUS-B2 ontbreekt" % rel)
    code = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), src, flags=re.S)
    # alleen de OEMPLUS-B2-delen streng checken? Nee: het hele bestand (stock StatusBarCtrl.css is al -o-/OEM-conform)
    for ln, line in enumerate(code.split("\n"), 1):
        for rx, what in CSS_RULES:
            if re.search(rx, line):
                errors.append("%s:%d %s: %s" % (rel, ln, what, line.strip()[:90]))

print("check_presto: %d JS, %d CSS in %s" % (len(jsfiles), len(cssfiles), OVL))
for n in notes:
    print("  info  " + n)
for e in errors:
    print("  FOUT  " + e)
print("RESULTAAT: " + ("OK" if not errors else "%d overtreding(en)" % len(errors)))
sys.exit(1 if errors else 0)
