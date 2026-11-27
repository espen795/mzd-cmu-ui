#!/bin/sh
# mount_inject.sh v1.0 -- draait OP DE CMU (busybox 1.19 ash). Enige script dat mount: bind-mount van de proefkopie
# over /jci/gui (RAM-only; reboot = weg). Schrijft niets onder /jci; alleen het sessielog onder /data_persist/oemplus-test.
# Geen smctl, geen kill, geen Opera-reload.
# Gebruik:  sh mount_inject.sh camera-ok [--nieuwe-sessie]
#   camera-ok        bevestigt dat de gebruiker in DEZE boot voor de mount de achteruitrijcamera heeft gecontroleerd (R -> beeld -> P)
#   --nieuwe-sessie  eerste mount van een nieuwe sessie: oud sessielog wordt bewaard als .vorige
# Harde prechecks (alle STOP = niets gemount):
#   0. scripts == TOOLS-MD5.txt (M6)
#   1. aa_wacht.sh OK (H3/V3)        2. OVERLAY-ACTIEF = injectv15      3. kopie_gelijk.sh overlay (H1/V1)
#   4. MemFree >= 40 MB en MemFree+Cached >= 200 MB                     5. precies 1 Opera-proces
#   6. geen tweede mount in dezelfde boot; geen eerdere onverwachte reset in deze sessie (max. 1 reset per sessie = einde)
# Exit: 0 = gemount en bewezen | 1 = STOP (niets gemount) | 2 = mount mislukt/onbewezen (umount gedaan)
BASE=/data_persist/oemplus-test
COPY=$BASE/gui
PKG=$BASE/injectv15
OVL=$PKG/overlay
MARK=$BASE/OVERLAY-ACTIEF
SLOG=$BASE/injectv15-sessie.log
PROOF=apps/ecoenergy/oemplus/OemplusInject.js

fail() { echo "STOP: $*"; exit 1; }
md5of() { md5sum "$1" 2>/dev/null | cut -d' ' -f1; }
bootid() { cat /proc/sys/kernel/random/boot_id 2>/dev/null || grep '^btime' /proc/stat | cut -d' ' -f2; }

[ "$1" = camera-ok ] || fail "eerst camera-check (de gebruiker: R -> camerabeeld OK -> P), dan: sh mount_inject.sh camera-ok"
NEW=0; [ "$2" = --nieuwe-sessie ] && NEW=1
[ -n "$2" ] && [ "$NEW" = 0 ] && fail "onbekende optie '$2'"
B=$(bootid); [ -n "$B" ] || fail "boot-id onleesbaar"
if grep -q " /jci/gui " /proc/mounts || mount | grep -q " on /jci/gui "; then fail "/jci/gui is al gemount"; fi

# 6. sessielog: max. 1 mount per boot; een mount zonder 'terug' in een eerdere boot = onverwachte reset/noodgreep
if [ "$NEW" = 1 ] && [ -f "$SLOG" ]; then mv "$SLOG" "$SLOG.vorige" || fail "sessielog niet te archiveren"; echo "oud sessielog -> $SLOG.vorige"; fi
if [ -f "$SLOG" ]; then
  R=$(awk -v b="$B" '$2 == "mount" { m[$1] = 1 } $2 == "terug" { delete m[$1] } END { n = 0; for (k in m) if (k != b) n++; print n }' "$SLOG")
  [ "$R" = 0 ] || fail "$R onverwachte reset/noodgreep eerder in deze sessie (mount zonder terug) -- sessie-einde (V3). Nieuwe sessie (andere dag/na analyse): --nieuwe-sessie"
  grep -q "^$B mount" "$SLOG" && fail "in deze boot is al gemount (geen tweede poging in dezelfde boot; eerst terug_inject.sh)"
fi

# 0. eigen scripts intact (M6)
[ -f "$PKG/TOOLS-MD5.txt" ] || fail "$PKG/TOOLS-MD5.txt ontbreekt"
( cd "$PKG" && md5sum -c TOOLS-MD5.txt >/dev/null 2>&1 ) || { ( cd "$PKG" && md5sum -c TOOLS-MD5.txt 2>&1 | grep -v ': OK$' ); fail "scripts in $PKG kloppen niet met TOOLS-MD5.txt"; }
echo "scripts OK (TOOLS-MD5.txt)"

# 1. AA-guard
sh "$PKG/aa_wacht.sh"; A=$?
[ "$A" = 3 ] && { echo "STOP: nog wachten op het AA-guard-oordeel; over 1 min opnieuw"; exit 1; }
[ "$A" = 0 ] || fail "AA-guard niet OK"

# 2. overlay toegepast
[ "$(cat "$MARK" 2>/dev/null)" = injectv15 ] || fail "OVERLAY-ACTIEF is niet injectv15 -- eerst apply_inject.sh"

# 4. geheugen
MF=$(awk '/^MemFree:/ {print $2}' /proc/meminfo); CA=$(awk '/^Cached:/ {print $2}' /proc/meminfo)
echo "MemFree ${MF} kB, Cached ${CA} kB"
[ "$MF" -ge 40000 ] || fail "MemFree < 40 MB"
[ $((MF + CA)) -ge 200000 ] || fail "MemFree+Cached < 200 MB"

# 5. Opera
NO=$(ps | grep -c '[/]jci/opera/opera ')
[ "$NO" = 1 ] || fail "verwacht 1 Opera-proces, gezien $NO"

# 3. volledige boom (laatste check vlak voor de mount)
sh "$PKG/kopie_gelijk.sh" overlay || fail "kopie_gelijk overlay faalt"
WANT=$(grep "  $PROOF\$" "$OVL/OVERLAY-MD5.txt" | cut -d' ' -f1)
[ -n "$WANT" ] || fail "bewijs-md5 ontbreekt"

echo "$B mount uptime=$(cut -d' ' -f1 /proc/uptime)" >> "$SLOG"; sync
mount --bind "$COPY" /jci/gui || { echo "$B terug mount-faalde" >> "$SLOG"; sync; echo "FOUT: mount --bind faalt"; exit 2; }
if grep -q " /jci/gui " /proc/mounts && [ "$(md5of "/jci/gui/$PROOF")" = "$WANT" ]; then
  echo "GEMOUNT en bewezen: $(grep ' /jci/gui ' /proc/mounts | tail -1)"
  echo "Nu: de gebruiker opent Applicaties > Brandstofverbruik (paneel 'OEM+ - B2 (proef, v1.5)'). Terug: sh $PKG/terug_inject.sh"
  exit 0
fi
umount /jci/gui 2>/dev/null
echo "$B terug mount-onbewezen" >> "$SLOG"; sync
echo "FOUT: mount niet bewezen (proc/mounts of md5 via /jci/gui) -- umount gedaan; Opera heeft niets nieuws gelezen"
exit 2
