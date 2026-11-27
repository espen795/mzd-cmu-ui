#!/bin/sh
# revert_inject.sh v1.1 -- draait OP DE CMU (busybox 1.19 ash). Haalt de inject-v1-overlay uit de PROEFKOPIE.
# v1.3: zet de 4 eco-templates terug (bron /jci/gui, terugval backup) en verwijdert de 270 nieuwe bestanden (v1.5).
# Schrijft uitsluitend onder /data_persist/oemplus-test/. Eis: /jci/gui NIET gemount. Geen mount/smctl/kill.
# v1.1 (R-cmu): symlink-check ook op de nieuwe mappen (L2); nacontrole = volledige boom kopie == /jci/gui (H1/V1).
# Exit: 0 = kopie weer == /jci/gui (hele boom) | 1 = precheck faalt (niets gewijzigd) | 2 = nacontrole faalt
BASE=/data_persist/oemplus-test
COPY=$BASE/gui
PKG=$BASE/injectv15
OVL=$PKG/overlay
BAK=$BASE/injectv15-backup
ORIG=$OVL/ORIGINAL-MD5.txt
MARK=$BASE/OVERLAY-ACTIEF

fail() { echo "STOP: $*"; exit 1; }
md5of() { md5sum "$1" 2>/dev/null | cut -d' ' -f1; }

case "$COPY" in /data_persist/oemplus-test/*) ;; *) fail "pad buiten /data_persist/oemplus-test";; esac
[ -d "$COPY" ] || fail "proefkopie $COPY ontbreekt"
[ -f "$ORIG" ] || fail "$ORIG ontbreekt"
[ -e "$MARK" ] && [ "$(cat "$MARK")" != "injectv15" ] && fail "OVERLAY-ACTIEF = '$(cat "$MARK")', niet injectv15 -- revert van die overlay gebruiken"
grep -q " /jci/gui " /proc/mounts && fail "/jci/gui is nog gemount -- eerst umount /jci/gui (daarna reboot volgens draaiboek)"

for D in apps/ecoenergy/oemplus apps/system/controls/MainMenu/images/b2 apps/system/controls/MainMenu/js apps/system/controls/MainMenu/css common/controls/StatusBar/css common/controls/Sbn/css common/oemplusb2 common/oemplusb2/css common/oemplusb2/images; do
  [ -L "$COPY/$D" ] && fail "map $D in kopie is een symlink"
done

# 1. Precheck: per vervangen bestand een bron met de originele md5
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  if [ "$(md5of "/jci/gui/$F")" != "$M" ] && [ "$(md5of "$BAK/$F")" != "$M" ]; then
    fail "geen bron met originele md5 voor $F (/jci/gui en backup wijken af)"
  fi
  [ -L "$COPY/$F" ] && fail "$F in kopie is een symlink"
done < "$ORIG"
while read -r T F; do
  [ "$T" = "#NEW" ] || continue
  [ -L "$COPY/$F" ] && fail "$F in kopie is een symlink"
done < "$ORIG"
# (F8: symlink-check nu incl. common/oemplusb2{,/css,/images} -- zie boven)

# 2. Terugzetten / verwijderen
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  if [ "$(md5of "/jci/gui/$F")" = "$M" ]; then SRC="/jci/gui/$F"; else SRC="$BAK/$F"; fi
  cp "$SRC" "$COPY/$F" || { echo "FOUT cp $F"; exit 2; }
  echo "  terug: $F (bron $SRC)"
done < "$ORIG"
while read -r T F; do
  [ "$T" = "#NEW" ] || continue
  rm -f "$COPY/$F"
done < "$ORIG"
# F8: ruim ALLE lege oemplus-mappen op (ook common/oemplusb2/css, /images, /common/oemplusb2 zelf)
rmdir "$COPY/apps/system/controls/MainMenu/images/b2" "$COPY/apps/ecoenergy/oemplus" \
      "$COPY/common/oemplusb2/css" "$COPY/common/oemplusb2/images" "$COPY/common/oemplusb2" 2>/dev/null
sync

# 3. Nacontrole
RC=0
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  [ "$(md5of "$COPY/$F")" = "$M" ] || { echo "NACONTROLE FAALT: $F"; RC=2; }
  grep -q "OEMPLUS-INJECT" "$COPY/$F" 2>/dev/null && { echo "NACONTROLE FAALT: marker in $F"; RC=2; }
done < "$ORIG"
while read -r T F; do
  [ "$T" = "#NEW" ] || continue
  [ -e "$COPY/$F" ] && { echo "NACONTROLE FAALT: $F staat er nog"; RC=2; }
done < "$ORIG"
[ "$RC" = 0 ] || exit 2
rm -f "$MARK"
sync
if [ -f "$PKG/kopie_gelijk.sh" ]; then
  sh "$PKG/kopie_gelijk.sh" schoon || { echo "NACONTROLE FAALT: kopie != /jci/gui (hele boom) -- sh $PKG/kopie_vers.sh"; exit 2; }
else
  echo "NACONTROLE FAALT: $PKG/kopie_gelijk.sh ontbreekt"; exit 2
fi
echo "OK: inject-v1.5 uit de proefkopie (4 templates terug, 270 nieuwe weg; OVERLAY-ACTIEF weg; kopie == /jci/gui); backup blijft in $BAK"
exit 0
