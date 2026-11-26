#!/bin/sh
# apply_inject.sh v1.1 -- draait OP DE CMU (busybox 1.19 ash). Zet de inject-v1-overlay in de PROEFKOPIE.
# Schrijft uitsluitend onder /data_persist/oemplus-test/. Raakt /jci nooit aan (alleen md5 lezen als bewijs).
# Geen mount, geen smctl, geen kill: mounten doet de operator (draaiboek), Opera blijft draaien.
# Indeling op de CMU:
#   /data_persist/oemplus-test/injectv13/overlay/<pad onder gui>  (4 vervangen eco-templates + 179 nieuw,
#                                                                plus ORIGINAL-MD5.txt, OVERLAY-MD5.txt, SHA256SUMS)
#   /data_persist/oemplus-test/injectv13/{apply_inject.sh,revert_inject.sh,kopie_gelijk.sh,...}
# v1.1 (R-cmu): kopie moet VOORAF exact == /jci/gui zijn (kopie_gelijk.sh schoon, H1) en ACHTERAF mogen alleen de
# 183 overlaypaden afwijken (kopie_gelijk.sh overlay). Geen mount: dat doet mount_inject.sh (met AA-guard-precheck).
# Exit: 0 = OK | 1 = precheck faalt (niets gewijzigd in de kopie) | 2 = fout tijdens/na kopieren (draai revert_inject.sh)
# Let op (L3): exit 1 bij de backup-stap (4) of later kan een (deels) geschreven $BASE/injectv13-backup achterlaten; dat is
# onschadelijk (wordt bij een volgende apply overschreven) en de kopie zelf is dan nog niet gewijzigd.
BASE=/data_persist/oemplus-test
COPY=$BASE/gui
PKG=$BASE/injectv13
OVL=$PKG/overlay
BAK=$BASE/injectv13-backup
ORIG=$OVL/ORIGINAL-MD5.txt
MARK=$BASE/OVERLAY-ACTIEF
NAME=injectv13
INDEX_V74_MD5=0ad187b787e242953a9a7612f55bfcfb
SYSAPP_V74_MD5=383d7e688256e09b825ced9e3eb69ee9
MMCTRL_V74_MD5=40ccb293b8c6f80960f0b953dd2e173e

fail() { echo "STOP: $*"; exit 1; }
md5of() { md5sum "$1" 2>/dev/null | cut -d' ' -f1; }

case "$COPY" in /data_persist/oemplus-test/*) ;; *) fail "pad buiten /data_persist/oemplus-test";; esac
[ -d "$COPY" ] || fail "proefkopie $COPY ontbreekt (eerst: cp -a /jci/gui $COPY)"
[ -L "$COPY" ] && fail "$COPY is een symlink"
[ -f "$ORIG" ] && [ -f "$OVL/OVERLAY-MD5.txt" ] || fail "pakket onvolledig in $OVL"

# 1. Niet toepassen terwijl de kopie gemount is
grep -q " /jci/gui " /proc/mounts && fail "/jci/gui is gemount -- eerst umount /jci/gui (en reboot volgens draaiboek)"
grep -q " $COPY " /proc/mounts && fail "$COPY is zelf een mountpoint"

# 1b. Geen andere overlay in de kopie (B2 v1, probe)
[ -e "$MARK" ] && fail "overlay '$(cat "$MARK")' staat nog in de kopie ($MARK) -- eerst de revert van die overlay"
[ -e "$COPY/oemplus-probe" ] && fail "probe-map $COPY/oemplus-probe bestaat -- eerst revert_probe.sh"
[ "$(md5of "$COPY/index.html")" = "$INDEX_V74_MD5" ] || fail "kopie-index.html is niet het v74-origineel (probe-overlay? -> probe/revert_probe.sh)"
[ "$(md5of "$COPY/apps/system/js/systemApp.js")" = "$SYSAPP_V74_MD5" ] || fail "kopie-systemApp.js is niet v74 (B2-overlay?) -- eerst b2v1/revert_overlay.sh"
[ "$(md5of "$COPY/apps/system/controls/MainMenu/js/MainMenuCtrl.js")" = "$MMCTRL_V74_MD5" ] || fail "kopie-MainMenuCtrl.js is niet v74 -- eerst b2v1/revert_overlay.sh"
[ -e "$COPY/apps/system/controls/MainMenu/images/b2" ] && fail "images/b2 bestaat al in kopie (B2-overlay?) -- eerst b2v1/revert_overlay.sh"

# 2. Overlay-bestanden zelf intact (overdracht)?
( cd "$OVL" && md5sum -c OVERLAY-MD5.txt >/dev/null ) || { ( cd "$OVL" && md5sum -c OVERLAY-MD5.txt | grep -v ': OK$' ); fail "overlay-md5 klopt niet (overdracht mislukt)"; }
if which sha256sum >/dev/null 2>&1; then
  ( cd "$OVL" && sha256sum -c SHA256SUMS >/dev/null ) || fail "overlay-SHA256 klopt niet"
  echo "SHA256: overlay OK"
else
  echo "info: geen sha256sum op dit systeem; md5 (OVERLAY-MD5.txt) gecontroleerd"
fi

# 3. Kopie heeft de ORIGINELE v74-bestanden; nieuwe bestanden bestaan nog niet; geen symlinks
N=0
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  [ -L "$COPY/$F" ] && fail "$F in kopie is een symlink"
  H=$(md5of "$COPY/$F")
  [ "$H" = "$M" ] || fail "kopie $F md5 $H != origineel v74 $M (al toegepast? -> revert_inject.sh)"
  N=$((N+1))
done < "$ORIG"
[ "$N" -gt 0 ] || fail "ORIGINAL-MD5.txt bevat geen bestanden"
while read -r T F; do
  [ "$T" = "#NEW" ] || continue
  [ -e "$COPY/$F" ] && fail "nieuw bestand bestaat al in kopie: $F (al toegepast? -> revert_inject.sh)"
  [ -L "$COPY/$(dirname "$F")" ] && fail "map $(dirname "$F") is een symlink"
done < "$ORIG"
echo "precheck OK: $N originele bestanden in de kopie kloppen met v74"

# 3a. Volledige boom: kopie == /jci/gui (H1). Elke andere afwijking (W7-resten, introfix-hook.js, ...) = STOP.
[ -f "$PKG/kopie_gelijk.sh" ] || fail "$PKG/kopie_gelijk.sh ontbreekt"
sh "$PKG/kopie_gelijk.sh" schoon || fail "proefkopie is niet gelijk aan /jci/gui -- eerst herstellen (sh $PKG/kopie_vers.sh)"

# 3b. /jci/gui zelf moet de v74-originelen hebben (alleen lezen)
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  [ "$(md5of "/jci/gui/$F")" = "$M" ] || fail "/jci/gui/$F wijkt af van v74 $M (firmware veranderd?)"
done < "$ORIG"

# 4. Back-up van de originelen
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  mkdir -p "$BAK/$(dirname "$F")" || fail "mkdir backup"
  cp -a "$COPY/$F" "$BAK/$F" || fail "backup $F"
  [ "$(md5of "$BAK/$F")" = "$M" ] || fail "backup-md5 $F klopt niet"
done < "$ORIG"
echo "backup OK: $BAK"

# 5. Toepassen. Marker eerst: ook een halve apply blokkeert andere overlays.
echo "$NAME" > "$MARK" || fail "marker $MARK"
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  mkdir -p "$COPY/$(dirname "$F")" || { echo "FOUT mkdir $F"; exit 2; }
  cp "$OVL/$F" "$COPY/$F" || { echo "FOUT cp $F"; exit 2; }
done < "$OVL/OVERLAY-MD5.txt"
sync

# 6. Nacontrole
( cd "$COPY" && md5sum -c "$OVL/OVERLAY-MD5.txt" >/dev/null ) || { ( cd "$COPY" && md5sum -c "$OVL/OVERLAY-MD5.txt" | grep -v ': OK$' ); echo "POSTCHECK FAALT -- draai revert_inject.sh"; exit 2; }
echo "postcheck OK: $(grep -c '' "$OVL/OVERLAY-MD5.txt") bestanden in de kopie == overlay"

# 7. Bewijs: /jci/gui zelf onaangeroerd
RC=0
while read -r M F; do
  case "$M" in ""|\#*) continue;; esac
  H=$(md5of "/jci/gui/$F")
  if [ "$H" = "$M" ]; then echo "  /jci/gui/$F ongewijzigd ($H)"; else echo "  FOUT: /jci/gui/$F = $H (verwacht $M)"; RC=2; fi
done < "$ORIG"
[ "$RC" = 0 ] || { echo "STOP: /jci/gui wijkt af -- niet mounten; revert_inject.sh"; exit 2; }

# 8. Volledige boom na apply: alleen de overlaypaden wijken af (H1)
sh "$PKG/kopie_gelijk.sh" overlay || { echo "STOP: boomvergelijking na apply faalt -- niet mounten; revert_inject.sh"; exit 2; }
echo "OK: inject-v1.3 toegepast op $COPY (OVERLAY-ACTIEF=injectv13). Nog NIET actief: zie draaiboek (mount_inject.sh camera-ok)."
exit 0
