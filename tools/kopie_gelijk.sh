#!/bin/sh
# kopie_gelijk.sh v1.0 -- draait OP DE CMU (busybox 1.19 ash). ALLEEN LEZEN (lijsten in /tmp). R-cmu H1/V1.
# Volledige boomvergelijking proefkopie /data_persist/oemplus-test/gui <-> /jci/gui, in beide richtingen, per bestand md5.
# Gebruik:  sh kopie_gelijk.sh schoon    kopie moet EXACT gelijk zijn aan /jci/gui (voor apply, na revert)
#           sh kopie_gelijk.sh overlay   enige toegestane differences = de 183 inject-v1.3-paden (4 vervangen + 179 nieuw), en die moeten exact de
#                                        overlay-md5 hebben (na apply, voor de mount)
# Ook: symlinks in kopie == symlinks in /jci/gui (zelfde paden); geen enkel overlay-pad is een symlink.
# Eis: /jci/gui NIET gemount (anders vergelijk je de kopie met zichzelf).
# Exit: 0 = gelijk (volgens modus) | 1 = verschil of precheck faalt (STOP: niet mounten)
MODE=${1:-}
BASE=/data_persist/oemplus-test
COPY=$BASE/gui
OVL=$BASE/injectv13/overlay
ORIG=$OVL/ORIGINAL-MD5.txt
OVMD5=$OVL/OVERLAY-MD5.txt

fail() { echo "STOP: $*"; exit 1; }
case "$MODE" in schoon|overlay) ;; *) fail "gebruik: sh kopie_gelijk.sh schoon|overlay";; esac
[ -d "$COPY" ] || fail "proefkopie $COPY ontbreekt"
[ -L "$COPY" ] && fail "$COPY is een symlink"
[ -f "$ORIG" ] && [ -f "$OVMD5" ] || fail "pakketlijsten ontbreken in $OVL"
if grep -q " /jci/gui " /proc/mounts || mount | grep -q " on /jci/gui "; then fail "/jci/gui is gemount -- vergelijken kan alleen ongemount"; fi

T=/tmp/oemplus-kg.$$
rm -rf "$T"; mkdir -p "$T" || fail "mkdir $T"
trap 'rm -rf "$T"' EXIT
echo "kopie_gelijk ($MODE): md5 van beide bomen (duurt ~1 min) ..."
( cd /jci/gui && find . -type f -exec md5sum {} \; ) > "$T/a" 2>"$T/ea" || fail "md5 /jci/gui faalt"
( cd "$COPY" && find . -type f -exec md5sum {} \; ) > "$T/b" 2>"$T/eb" || fail "md5 kopie faalt"
[ -s "$T/ea" ] && { cat "$T/ea"; fail "leesfout in /jci/gui"; }
[ -s "$T/eb" ] && { cat "$T/eb"; fail "leesfout in kopie"; }
( cd /jci/gui && find . -type l ) > "$T/la"
( cd "$COPY" && find . -type l ) > "$T/lb"
( cd /jci/gui && find . -type d ) > "$T/da"
( cd "$COPY" && find . -type d ) > "$T/db"

# Regelformaat md5sum: 32 hex, 2 spaties, pad (pad kan spaties bevatten: substr vanaf kolom 35).
awk -v mode="$MODE" -v fa="$T/a" -v fb="$T/b" -v fla="$T/la" -v flb="$T/lb" -v fda="$T/da" -v fdb="$T/db" -v fo="$ORIG" -v fv="$OVMD5" '
BEGIN {
  while ((getline l < fo) > 0) {
    if (l ~ /^#NEW /) { p = "./" substr(l, 6); nw[p] = 1; continue }
    if (l ~ /^#/ || l == "") continue
    p = "./" substr(l, 35); rp[p] = substr(l, 1, 32)
  }
  while ((getline l < fv) > 0) { if (l == "") continue; ov["./" substr(l, 35)] = substr(l, 1, 32); nov++ }
  while ((getline l < fa) > 0) { A[substr(l, 35)] = substr(l, 1, 32); na++ }
  while ((getline l < fb) > 0) { B[substr(l, 35)] = substr(l, 1, 32); nb++ }
  while ((getline l < fla) > 0) LA[l] = 1
  while ((getline l < flb) > 0) LB[l] = 1
  while ((getline l < fda) > 0) DA[l] = 1
  while ((getline l < fdb) > 0) DB[l] = 1
  bad = 0; same = 0; allowed = 0
  for (p in A) {
    if (!(p in B)) { print "ONTBREEKT in kopie: " p; bad++; continue }
    if (A[p] == B[p]) { same++; continue }
    if (mode == "overlay" && (p in rp) && A[p] == rp[p] && B[p] == ov[p]) { allowed++; continue }
    print "VERSCHIL: " p " (/jci/gui " A[p] ", kopie " B[p] ")"; bad++
  }
  for (p in B) {
    if (p in A) continue
    if (mode == "overlay" && (p in nw) && B[p] == ov[p]) { allowed++; continue }
    print "EXTRA in kopie: " p; bad++
  }
  if (mode == "overlay") {
    for (p in ov) if (!(p in B)) { print "OVERLAY-BESTAND ONTBREEKT in kopie: " p; bad++ }
    for (p in rp) if ((p in A) && A[p] != rp[p]) { print "/jci/gui " p " is niet v74 (" A[p] ")"; bad++ }
  }
  for (p in LA) if (!(p in LB)) { print "SYMLINK ontbreekt in kopie: " p; bad++ }
  for (p in LB) {
    if (!(p in LA)) { print "SYMLINK extra in kopie: " p; bad++ }
    if ((p in ov) || (p in nw) || (p in rp)) { print "SYMLINK op overlay-pad: " p; bad++ }
  }
  # F8: mapstructuur ook vergelijken; in modus overlay mogen de overlay-mappen (uit ov/nw afgeleid) extra zijn
  for (p in ov) { d = p; sub(/[^\/]*$/, "", d); while (d != "" && d != "./") { ovdirs[d] = 1; d = substr(d, 1, length(d)-1) } }
  for (p in nw) { d = p; sub(/[^\/]*$/, "", d); while (d != "" && d != "./") { ovdirs[d] = 1; d = substr(d, 1, length(d)-1) } }
  for (p in DB) if (!(p in DA) && !(p in ovdirs)) { print "MAP extra in kopie: " p; bad++ }
  for (p in DA) if (!(p in DB)) { print "MAP ontbreekt in kopie: " p; bad++ }
  if (na < 1000) { print "VERDACHT: /jci/gui heeft maar " na " bestanden"; bad++ }
  printf "telling: /jci/gui %d bestanden, kopie %d; gelijk %d, toegestaan (overlay) %d, afwijkend %d\n", na, nb, same, allowed, bad
  if (mode == "overlay" && allowed != nov) { print "VERWACHT " nov " overlay-paden, gezien " allowed; bad++ }
  exit (bad == 0 ? 0 : 1)
}' </dev/null
RC=$?
if [ "$RC" = 0 ]; then
  if [ "$MODE" = schoon ]; then echo "KOPIE GELIJK: proefkopie == /jci/gui (hele boom, md5)"; else echo "KOPIE GELIJK: alleen de inject-v1.3-overlaypaden wijken af (hele boom, md5)"; fi
  exit 0
fi
echo "STOP: proefkopie wijkt af van /jci/gui ($MODE) -- NIET mounten. Herstel: revert van de overlay; blijft het verschil: sh $BASE/injectv13/kopie_vers.sh"
exit 1
