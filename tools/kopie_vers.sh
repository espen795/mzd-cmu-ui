#!/bin/sh
# kopie_vers.sh v1.0 -- draait OP DE CMU (busybox 1.19 ash). Maakt de PROEFKOPIE opnieuw: verwijdert
# /data_persist/oemplus-test/gui en kopieert /jci/gui (alleen lezen) opnieuw met cp -a. Daarna kopie_gelijk.sh schoon.
# Alleen nodig als kopie_gelijk.sh een verschil meldt dat de revert-scripts niet oplossen (W7-resten, introfix-hook.js, ...).
# Schrijft uitsluitend onder /data_persist/oemplus-test/. Geen mount/smctl/kill. Eis: /jci/gui NIET gemount.
# Exit: 0 = verse kopie, gelijk aan /jci/gui | 1 = precheck faalt (niets gewijzigd) | 2 = fout tijdens/na kopieren
BASE=/data_persist/oemplus-test
COPY=$BASE/gui
HERE=$(cd "$(dirname "$0")" && pwd)

fail() { echo "STOP: $*"; exit 1; }
[ "$COPY" = /data_persist/oemplus-test/gui ] || fail "pad klopt niet"
if grep -q " /jci/gui " /proc/mounts || mount | grep -q " on /jci/gui "; then fail "/jci/gui is gemount -- eerst terug (umount + reboot)"; fi
grep -q " $COPY " /proc/mounts && fail "$COPY is zelf een mountpoint"
[ -L "$COPY" ] && fail "$COPY is een symlink"
[ -d /jci/gui ] || fail "/jci/gui ontbreekt"
[ -f "$HERE/kopie_gelijk.sh" ] || fail "$HERE/kopie_gelijk.sh ontbreekt"
NEED=$(du -sk /jci/gui | cut -f1)
OLD=0; [ -d "$COPY" ] && OLD=$(du -sk "$COPY" | cut -f1)
FREE=$(df -k /data_persist 2>/dev/null | tail -1 | awk '{print $(NF-2)}')
case "$FREE" in
  ''|*[!0-9]*) echo "INFO: vrije ruimte op /data_persist onbekend (df); een te volle schijf geeft hieronder 'FOUT cp' (alleen de kopie raakt dan onvolledig)";;
  *) echo "nodig ${NEED} kB, vrij ${FREE} kB (+${OLD} kB na verwijderen oude kopie)"
     [ $((FREE + OLD)) -gt $((NEED + 5120)) ] || fail "te weinig ruimte op /data_persist";;
esac

if [ -d "$COPY" ]; then
  rm -rf "$COPY" || { echo "FOUT: oude kopie niet volledig verwijderd"; exit 2; }
fi
cp -a /jci/gui "$COPY" || { echo "FOUT: cp -a /jci/gui $COPY"; exit 2; }
sync
# een verse kopie bevat geen overlay meer: marker en backups van eerdere overlays zijn achterhaald
[ -e "$BASE/OVERLAY-ACTIEF" ] && { echo "OVERLAY-ACTIEF ($(cat "$BASE/OVERLAY-ACTIEF")) verwijderd: verse kopie"; rm -f "$BASE/OVERLAY-ACTIEF"; }
sync
sh "$HERE/kopie_gelijk.sh" schoon || { echo "FOUT: verse kopie niet gelijk aan /jci/gui"; exit 2; }
echo "OK: verse proefkopie $COPY == /jci/gui"
exit 0
