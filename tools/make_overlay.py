#!/usr/bin/env python3
"""make_overlay.py (HOST) -- bouwt ui-oemplus-inject-v1.3/overlay/ uit:
  * v74-dump (stock/v74/jci/gui): 4 ecoenergy-templates, byte-exact gepatcht (2 invoegingen)
  * src/OemplusInject.{js,css}                       -> apps/ecoenergy/oemplus/
  * v1.2 B2-bestanden (DEZE map, overlay-src/apps/... en overlay-src/common/...):
      MainMenuCtrl-oemplusb2.js/.css (v1.2+fixes: SBN-reservering bovenin, seed uit systemApp-cache, B1/B2/B3)
      StatusBarCtrl-oemplusb2.css  (B2-blok onder body.OemplusB2Home; SBN blijft zichtbaar)
      SbnCtrl-oemplusb2.css        (v1.2: B2-stijl voor de SBN-banner, fail-visible)
      images/b2/*.png              -> apps/system/controls/MainMenu/images/b2/
  * v1.3 / P0: common/oemplusb2/css/B2Sub-00-base.css + common/oemplusb2/images/*.png (uit overlay-src/common/oemplusb2/)
  * v1.1 nam de B2 MainMenuCtrl.js/.css ongewijzigd over uit ui-oemplus-b2-v1/overlay; v1.2/v1.3 gebruiken de eigen
    (aangepaste) kopieen in deze map, zodat ui-oemplus-b2-v1 en ui-oemplus-inject-v1.1/.v1.2 ongemoeid blijven.
  Originele v74-bestanden in de proefkopie: alleen de 4 templates worden vervangen; de rest is NIEUW.
  Schrijft ORIGINAL-MD5.txt, OVERLAY-MD5.txt, SHA256SUMS. Eist dat de v74-dump de CMU-md5 heeft (MD5SUMS.cmu).
"""
import os, re, sys, glob, shutil, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
MZD = ROOT  # public repo: own CMU dumps live in <repo>/stock/
V74 = os.path.join(MZD, "stock/v74/jci/gui")
CMU_MD5 = os.path.join(MZD, "stock/v74/MD5SUMS.cmu")
B2 = os.path.join(MZD, "tools/b2-overlay")  # alleen images/b2/*.png komen hier nog vandaan
SRCB2 = os.path.join(ROOT, "overlay-src")          # v1.2: aangepaste B2 MainMenu/StatusBar/Sbn bestanden
OUT = os.path.join(ROOT, "overlay")

TEMPLATES = ["FuelConsumption", "EcoStatus", "EcoFlow", "EcoEffect"]

HOOK_CTOR = b"    /* OEMPLUS-INJECT v1.2 */ try { OemplusInjectHook(this); } catch (eOemplusInject) { }\r\n"
HOOK_FILE = (
    b"/* OEMPLUS-INJECT v1.2 (2026-11-26): laadt eenmalig apps/ecoenergy/oemplus/OemplusInject.js (B2-keuzepaneel) en hangt\r\n"
    b" * het paneel aan dit eco-template. Runtime-fouten in de haak (try/catch) laten het eco-scherm ongemoeid;\r\n"
    b" * een laad-/parsefout van dit bestand zelf niet (State Timeout -> reset, zie README). */\r\n"
    b"function OemplusInjectHook(tmpl)\r\n"
    b"{\r\n"
    b"    try\r\n"
    b"    {\r\n"
    b"        if (window.OemplusInject && window.OemplusInject.attach)\r\n"
    b"        {\r\n"
    b"            window.OemplusInject.attach(tmpl);\r\n"
    b"        }\r\n"
    b"        else\r\n"
    b"        {\r\n"
    b"            window.OemplusInjectPending = tmpl;\r\n"
    b"        }\r\n"
    b"    }\r\n"
    b"    catch (e) { }\r\n"
    b"}\r\n"
    b"try\r\n"
    b"{\r\n"
    b"    if (!window.OemplusInject && !window.OemplusInjectLoading)\r\n"
    b"    {\r\n"
    b"        window.OemplusInjectLoading = true;\r\n"
    b"        utility.loadCss(\"apps/ecoenergy/oemplus/OemplusInject.css\");\r\n"
    b"        utility.loadScript(\"apps/ecoenergy/oemplus/OemplusInject.js\");\r\n"
    b"    }\r\n"
    b"}\r\n"
    b"catch (eOemplusInject) { }\r\n"
    b"\r\n"
)

def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()

def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def cmu_md5s():
    d = {}
    for line in open(CMU_MD5, encoding="utf-8", errors="replace"):
        m = re.match(r"([0-9a-f]{32})\s+\*?(.+)$", line.strip())
        if m:
            p = m.group(2)
            p = re.sub(r"^(\./)?(jci/gui/|/jci/gui/)?", "", p)
            d[p] = m.group(1)
    return d

def patch_template(name, data):
    nl = b"\r\n" if b"\r\n" in data else b"\n"
    hook_ctor = HOOK_CTOR.replace(b"\r\n", nl)
    hook_file = HOOK_FILE.replace(b"\r\n", nl)
    m = re.search(rb"function " + name.encode() + rb"Tmplt\s*\([^)]*\)\s*\{", data)
    if not m:
        raise SystemExit("constructor niet gevonden in " + name)
    # eerste regel die alleen '}' bevat na de constructor-kop = einde constructor
    m2 = re.compile(rb"(^|\n)\}[ \t]*\r?\n").search(data, m.end())
    if not m2:
        raise SystemExit("einde constructor niet gevonden in " + name)
    pos = m2.start() + (1 if data[m2.start():m2.start() + 1] == b"\n" else 0)
    data = data[:pos] + hook_ctor + data[pos:]
    idx = data.rfind(b"framework.registerTmpltLoaded(")
    if idx < 0:
        raise SystemExit("registerTmpltLoaded niet gevonden in " + name)
    data = data[:idx] + hook_file + data[idx:]
    return data

def main():
    cmu = cmu_md5s()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    replaced, new = [], []

    for t in TEMPLATES:
        rel = "apps/ecoenergy/templates/%s/js/%sTmplt.js" % (t, t)
        src = os.path.join(V74, rel)
        if cmu.get(rel) and cmu[rel] != md5(src):
            raise SystemExit("v74-dump wijkt af van CMU-md5: " + rel)
        if not cmu.get(rel):
            print("let op: geen CMU-md5 voor " + rel + " (dump-md5 " + md5(src) + ")")
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(patch_template(t, open(src, "rb").read()))
        replaced.append((rel, md5(src)))

    def put(src, rel):
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        if os.path.exists(os.path.join(V74, rel)):
            raise SystemExit("nieuw bestand bestaat al in v74: " + rel)
        new.append(rel)

    put(os.path.join(ROOT, "src/OemplusInject.js"), "apps/ecoenergy/oemplus/OemplusInject.js")
    put(os.path.join(ROOT, "src/OemplusInject.css"), "apps/ecoenergy/oemplus/OemplusInject.css")
    # v1.2: B2 MainMenuCtrl + StatusBar + Sbn komen uit SRC-B2 (aangepast), NIET meer uit ui-oemplus-b2-v1
    put(os.path.join(SRCB2, "apps/system/controls/MainMenu/js/MainMenuCtrl-oemplusb2.js"), "apps/system/controls/MainMenu/js/MainMenuCtrl-oemplusb2.js")
    put(os.path.join(SRCB2, "apps/system/controls/MainMenu/css/MainMenuCtrl-oemplusb2.css"), "apps/system/controls/MainMenu/css/MainMenuCtrl-oemplusb2.css")
    put(os.path.join(SRCB2, "common/controls/StatusBar/css/StatusBarCtrl-oemplusb2.css"), "common/controls/StatusBar/css/StatusBarCtrl-oemplusb2.css")
    put(os.path.join(SRCB2, "common/controls/Sbn/css/SbnCtrl-oemplusb2.css"), "common/controls/Sbn/css/SbnCtrl-oemplusb2.css")
    for png in sorted(glob.glob(os.path.join(B2, "apps/system/controls/MainMenu/images/b2/*.png"))):
        put(png, "apps/system/controls/MainMenu/images/b2/" + os.path.basename(png))
    # v1.3 / P0: B2-submenu basis (BOUWPLAN.md P0) uit overlay-src/common/oemplusb2/.
    # Alleen .css en .png landen in de overlay; de *-PLACEHOLDER.txt/README blijven in overlay-src (documentatie
    # voor de P1-P4-agents) en worden NIET naar de CMU gekopieerd.
    SUB = os.path.join(SRCB2, "common/oemplusb2")
    for css in sorted(glob.glob(os.path.join(SUB, "css/*.css"))):
        put(css, "common/oemplusb2/css/" + os.path.basename(css))
    for png in sorted(glob.glob(os.path.join(SUB, "images/*.png"))):
        put(png, "common/oemplusb2/images/" + os.path.basename(png))

    with open(os.path.join(OUT, "ORIGINAL-MD5.txt"), "w") as f:
        f.write("# inject-v1.3 - originele v74-bestanden die de overlay in de proefkopie VERVANGT (bron: v74-dump = MD5SUMS.cmu).\n")
        f.write("# Pad relatief t.o.v. /data_persist/oemplus-test/gui.\n")
        for rel, m in replaced:
            f.write("%s  %s\n" % (m, rel))
        f.write("# Nieuwe bestanden (bestaan niet in v74):\n")
        for rel in new:
            f.write("#NEW %s\n" % rel)
    files = sorted(replaced and [r for r, _ in replaced] + new)
    with open(os.path.join(OUT, "OVERLAY-MD5.txt"), "w") as f:
        for rel in files:
            f.write("%s  %s\n" % (md5(os.path.join(OUT, rel)), rel))
    with open(os.path.join(OUT, "SHA256SUMS"), "w") as f:
        for rel in files:
            f.write("%s  %s\n" % (sha256(os.path.join(OUT, rel)), rel))
    print("overlay: %d vervangen, %d nieuw -> %s" % (len(replaced), len(new), OUT))

if __name__ == "__main__":
    main()
