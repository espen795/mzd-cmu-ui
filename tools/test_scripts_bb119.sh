#!/bin/bash
# test_scripts_bb119.sh (HOST) v1.3 -- test de CMU-scripts van inject-v1.5 onder de officiele busybox 1.19.0 als ash,
# in een eigen user+mount+pid-namespace met chroot: /jci = kopie van de harnas-stock-root (v74), /data_persist = tmp.
# Scripts: apply_inject.sh, revert_inject.sh, kopie_gelijk.sh, kopie_vers.sh, aa_wacht.sh, mount_inject.sh, terug_inject.sh.
# Nep: /proc/uptime (bind-mount van een bestand), Opera-proces (sh-script), /bin/reboot (schrijft een vlag).
# Raakt de CMU niet. Vereist /tmp/rcmu-bb119/busybox (sha256 0d8564c5...) en harness/root-stock (build_root.sh).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
BB=/tmp/rcmu-bb119/busybox
[ "$(sha256sum $BB | cut -d' ' -f1)" = 0d8564c5a85b0976eeed24afc99894e1b2a1d21d54bb5cb673c33f72b3743f8c ] || { echo "busybox 1.19.0 ontbreekt"; exit 1; }
[ -d "$ROOT/harness/root-stock" ] || sh "$ROOT/harness/build_root.sh" >/dev/null
T=$(mktemp -d /tmp/inject-bb119-XXXX)
R=$T/root
mkdir -p $R/dev $R/bin $R/jci/opera $R/data_persist/oemplus-test/injectv15 $R/proc $R/tmp
cp $BB $R/bin/busybox
for a in $($BB --list); do [ "$a" = busybox ] || ln -s busybox $R/bin/$a; done
rm $R/bin/reboot
printf '#!/bin/ash\necho called > /tmp/reboot-called\n' > $R/bin/reboot; chmod 755 $R/bin/reboot
printf '#!/bin/ash\nsleep 3600\n' > $R/jci/opera/opera; chmod 755 $R/jci/opera/opera
cp -a "$ROOT/harness/root-stock" $R/jci/gui; rm -rf $R/jci/gui/_harness_fonts
cp -a $R/jci/gui $R/data_persist/oemplus-test/gui
cp -a "$ROOT/overlay" $R/data_persist/oemplus-test/injectv15/overlay
for s in apply_inject.sh revert_inject.sh kopie_gelijk.sh kopie_vers.sh aa_wacht.sh mount_inject.sh terug_inject.sh; do
  cp "$ROOT/tools/$s" $R/data_persist/oemplus-test/injectv15/
done
(cd $R/data_persist/oemplus-test/injectv15 && md5sum *.sh > TOOLS-MD5.txt)
cat > $R/t.sh <<'EOF'
P=0; F=0
ok() { if [ "$1" = 0 ]; then P=$((P+1)); echo "PASS $2"; else F=$((F+1)); echo "FAIL $2"; fi; }
B=/data_persist/oemplus-test
I=$B/injectv15
C=$B/gui
AA=/data_persist/dev/aa
up() { echo "$1.00 100.00" > /tmp/fakeup; }
mnt() { grep -c " /jci/gui " /proc/mounts; }
touch /tmp/fakeup; up 900; mount --bind /tmp/fakeup /proc/uptime
[ "$(cut -d' ' -f1 /proc/uptime)" = 900.00 ]; ok $? "testopzet: nep-uptime werkt"
sh /jci/opera/opera -u /jci/gui/index.html &
OP=$!
J0=$(find /jci -type f -exec md5sum {} \; | sort | md5sum)

# --- kopie_gelijk / apply / revert (oude checks + H1) ---
ash $I/kopie_gelijk.sh schoon > /tmp/k0.log 2>&1; ok $? "kopie_gelijk schoon op verse kopie exit 0"
ash $I/apply_inject.sh > /tmp/a1.log 2>&1; ok $? "apply exit 0"
[ "$(cat $B/OVERLAY-ACTIEF)" = injectv15 ]; ok $? "marker injectv15"
grep -q OEMPLUS-INJECT $C/apps/ecoenergy/templates/FuelConsumption/js/FuelConsumptionTmplt.js; ok $? "template gepatcht in kopie"
[ -f $C/apps/system/controls/MainMenu/js/MainMenuCtrl-oemplusb2.js ]; ok $? "B2-js nieuw in kopie"
cmp -s $C/apps/system/js/systemApp.js /jci/gui/apps/system/js/systemApp.js; ok $? "systemApp.js in kopie onaangeroerd"
grep -q "KOPIE GELIJK: alleen de inject-v1.5-overlaypaden" /tmp/a1.log; ok $? "apply draaide kopie_gelijk overlay (H1)"
ash $I/kopie_gelijk.sh overlay > /tmp/k1.log 2>&1; ok $? "kopie_gelijk overlay na apply exit 0"
grep -q "toegestaan (overlay) 274" /tmp/k1.log; ok $? "precies 274 toegestane overlaypaden (v1.5: 4 vervangen + 270 nieuw; v1.4 was 267, +7 nieuw: OemplusLive.js, B2DriveView.js, B2Sub-70-drive.css, 4x B2Drive*.png)"
ash $I/kopie_gelijk.sh schoon > /tmp/k2.log 2>&1; [ $? = 1 ]; ok $? "kopie_gelijk schoon na apply exit 1"
ash $I/apply_inject.sh > /tmp/a2.log 2>&1; [ $? = 1 ]; ok $? "tweede apply weigert (exit 1)"
# H1: afwijking buiten de overlay na apply -> overlay-check faalt
cp $C/apps/backupparking/js/backupparkingApp.js /tmp/bp.js; echo "// x" >> $C/apps/backupparking/js/backupparkingApp.js
ash $I/kopie_gelijk.sh overlay > /tmp/k3.log 2>&1; [ $? = 1 ] && grep -q "VERSCHIL: ./apps/backupparking/js/backupparkingApp.js" /tmp/k3.log; ok $? "overlay-check ziet gewijzigd backupparkingApp.js (T5)"
cp /tmp/bp.js $C/apps/backupparking/js/backupparkingApp.js
echo y >> $C/apps/ecoenergy/oemplus/OemplusInject.js
ash $I/kopie_gelijk.sh overlay > /tmp/k4.log 2>&1; [ $? = 1 ]; ok $? "overlay-check ziet beschadigd overlaybestand in kopie"
cp $I/overlay/apps/ecoenergy/oemplus/OemplusInject.js $C/apps/ecoenergy/oemplus/OemplusInject.js
mount --bind $C /jci/gui
ash $I/revert_inject.sh > /tmp/r0.log 2>&1; [ $? = 1 ]; ok $? "revert weigert zolang /jci/gui gemount is"
ash $I/kopie_gelijk.sh overlay > /tmp/k5.log 2>&1; [ $? = 1 ]; ok $? "kopie_gelijk weigert zolang /jci/gui gemount is"
umount /jci/gui
ash $I/revert_inject.sh > /tmp/r1.log 2>&1; ok $? "revert exit 0"
grep -q "KOPIE GELIJK: proefkopie == /jci/gui" /tmp/r1.log; ok $? "revert eindigt met volledige boomcheck (V1)"
D=$(cd /jci/gui && find . -type f -exec md5sum {} \; | sort | md5sum); E=$(cd $C && find . -type f -exec md5sum {} \; | sort | md5sum)
[ "$D" = "$E" ]; ok $? "kopie na revert == /jci/gui (hele boom, onafhankelijk)"
[ ! -e $B/OVERLAY-ACTIEF ]; ok $? "marker weg"
# H1 voor apply: gewijzigd bestand / extra bestand / symlink in kopie -> apply weigert, kopie ongewijzigd
echo "// x" >> $C/apps/backupparking/js/backupparkingApp.js
ash $I/apply_inject.sh > /tmp/a5.log 2>&1; R5=$?
[ $R5 = 1 ] && [ ! -e $B/OVERLAY-ACTIEF ] && ! grep -q OEMPLUS-INJECT $C/apps/ecoenergy/templates/FuelConsumption/js/FuelConsumptionTmplt.js; ok $? "apply weigert bij gewijzigd backupparkingApp.js (T5 -> nu exit 1)"
cp /tmp/bp.js $C/apps/backupparking/js/backupparkingApp.js
echo "hook" > $C/introfix-hook.js
ash $I/apply_inject.sh > /tmp/a6.log 2>&1; [ $? = 1 ] && grep -q "EXTRA in kopie: ./introfix-hook.js" /tmp/a6.log; ok $? "apply weigert bij extra bestand (introfix-hook.js)"
rm $C/introfix-hook.js
ln -s /etc/passwd $C/common/zz-link
ash $I/kopie_gelijk.sh schoon > /tmp/k6.log 2>&1; [ $? = 1 ] && grep -q "SYMLINK extra in kopie" /tmp/k6.log; ok $? "kopie_gelijk ziet symlink in kopie"
rm $C/common/zz-link
rm $C/apps/system/controls/MainMenu/images/Ellipse.png
ash $I/kopie_gelijk.sh schoon > /tmp/k7.log 2>&1; [ $? = 1 ] && grep -q "ONTBREEKT in kopie" /tmp/k7.log; ok $? "kopie_gelijk ziet ontbrekend bestand"
# kopie_vers herstelt alles (ook extra bestanden/marker)
echo "hook" > $C/introfix-hook.js; echo b2v1 > $B/OVERLAY-ACTIEF
ash $I/kopie_vers.sh > /tmp/v1.log 2>&1; ok $? "kopie_vers exit 0"
[ ! -e $C/introfix-hook.js ] && [ ! -e $B/OVERLAY-ACTIEF ] && [ -f $C/apps/system/controls/MainMenu/images/Ellipse.png ]; ok $? "kopie_vers: extra weg, ontbrekend terug, marker weg"
mount --bind $C /jci/gui
ash $I/kopie_vers.sh > /tmp/v2.log 2>&1; [ $? = 1 ]; ok $? "kopie_vers weigert zolang gemount"
umount /jci/gui
[ "$(find /jci -type f -exec md5sum {} \; | sort | md5sum)" = "$J0" ]; ok $? "/jci onaangeroerd (na kopie/apply/revert)"
echo b2v1 > $B/OVERLAY-ACTIEF
ash $I/apply_inject.sh > /tmp/a3.log 2>&1; [ $? = 1 ]; ok $? "apply weigert bij andere overlay (b2v1)"
rm $B/OVERLAY-ACTIEF
cp $I/overlay/apps/ecoenergy/oemplus/OemplusInject.js /tmp/inj.js; echo x >> $I/overlay/apps/ecoenergy/oemplus/OemplusInject.js
ash $I/apply_inject.sh > /tmp/a4.log 2>&1; [ $? = 1 ]; ok $? "apply weigert bij beschadigde overdracht"
cp /tmp/inj.js $I/overlay/apps/ecoenergy/oemplus/OemplusInject.js

# --- aa_wacht (H3/V3) ---
up 100; ash $I/aa_wacht.sh > /tmp/w1.log 2>&1; [ $? = 3 ]; ok $? "aa_wacht zonder kit, uptime 100 -> 3 (wachten)"
up 500; ash $I/aa_wacht.sh > /tmp/w2.log 2>&1; ok $? "aa_wacht zonder kit, uptime 500 -> 0"
mkdir -p $AA; echo 1 > $AA/bootcount; echo "[181s] gezond op 181s" > $AA/guard.log
up 500; ash $I/aa_wacht.sh > /tmp/w3.log 2>&1; [ $? = 3 ]; ok $? "aa_wacht bootcount 1, uptime 500 -> 3"
up 800; ash $I/aa_wacht.sh > /tmp/w4.log 2>&1; [ $? = 1 ]; ok $? "aa_wacht bootcount 1, uptime 800 -> 1 (STOP)"
echo 0 > $AA/bootcount
up 300; ash $I/aa_wacht.sh > /tmp/w5.log 2>&1; [ $? = 3 ]; ok $? "aa_wacht bootcount 0, uptime 300 -> 3"
up 500; ash $I/aa_wacht.sh > /tmp/w6.log 2>&1; ok $? "aa_wacht bootcount 0, uptime 500 -> 0"
echo "bootcount=3" > $AA/disabled
ash $I/aa_wacht.sh > /tmp/w7.log 2>&1; [ $? = 1 ]; ok $? "aa_wacht met 'disabled' -> 1 (STOP)"
rm $AA/disabled

# --- mount_inject / terug_inject ---
ash $I/apply_inject.sh > /tmp/a7.log 2>&1; ok $? "apply voor mount-tests exit 0"
ash $I/mount_inject.sh > /tmp/m1.log 2>&1; [ $? = 1 ] && [ "$(mnt)" = 0 ]; ok $? "mount zonder camera-ok weigert, niets gemount"
up 200; ash $I/mount_inject.sh camera-ok > /tmp/m2.log 2>&1; [ $? = 1 ] && [ "$(mnt)" = 0 ]; ok $? "mount weigert voor AA-oordeel (uptime 200), niets gemount"
up 600; echo "// x" >> $C/apps/backupparking/js/backupparkingApp.js
ash $I/mount_inject.sh camera-ok > /tmp/m3.log 2>&1; [ $? = 1 ] && [ "$(mnt)" = 0 ]; ok $? "mount weigert bij afwijking buiten overlay (H1), niets gemount"
cp /tmp/bp.js $C/apps/backupparking/js/backupparkingApp.js
kill $OP; wait $OP 2>/dev/null
ash $I/mount_inject.sh camera-ok > /tmp/m4.log 2>&1; [ $? = 1 ] && [ "$(mnt)" = 0 ]; ok $? "mount weigert zonder Opera-proces"
sh /jci/opera/opera -u /jci/gui/index.html &
OP=$!
cp $I/aa_wacht.sh /tmp/aw.sh; echo "# x" >> $I/aa_wacht.sh
ash $I/mount_inject.sh camera-ok > /tmp/m4b.log 2>&1; [ $? = 1 ] && grep -q "TOOLS-MD5" /tmp/m4b.log && [ "$(mnt)" = 0 ]; ok $? "mount weigert bij gewijzigd script (M6)"
cp /tmp/aw.sh $I/aa_wacht.sh
ash $I/mount_inject.sh camera-ok --nieuwe-sessie > /tmp/m5.log 2>&1; ok $? "mount_inject camera-ok exit 0"
[ "$(mnt)" = 1 ] && grep -q "OEMPLUS-INJECT" /jci/gui/apps/ecoenergy/templates/FuelConsumption/js/FuelConsumptionTmplt.js; ok $? "na mount: /jci/gui toont de kopie (bewezen)"
ash $I/mount_inject.sh camera-ok > /tmp/m6.log 2>&1; [ $? = 1 ] && [ "$(mnt)" = 1 ]; ok $? "tweede mount weigert (al gemount)"
ash $I/terug_inject.sh geen-reboot > /tmp/t1.log 2>&1; [ $? = 0 ] && [ "$(mnt)" = 0 ] && [ ! -e /tmp/reboot-called ]; ok $? "terug geen-reboot: umount, geen reboot"
ash $I/mount_inject.sh camera-ok > /tmp/m7.log 2>&1; [ $? = 1 ] && grep -q "al gemount" /tmp/m7.log; ok $? "geen tweede mount in dezelfde boot"
# onverwachte reset in deze sessie: mount van een andere boot zonder terug
echo "andere-boot-1234 mount uptime=600.00" >> $B/injectv15-sessie.log
ash $I/mount_inject.sh camera-ok > /tmp/m8.log 2>&1; [ $? = 1 ] && grep -q "onverwachte reset" /tmp/m8.log && [ "$(mnt)" = 0 ]; ok $? "na onverwachte reset in de sessie: mount weigert (V3)"
mount --bind $C /jci/gui
ash $I/terug_inject.sh > /tmp/t2.log 2>&1; [ "$(mnt)" = 0 ] && [ -e /tmp/reboot-called ]; ok $? "terug: umount + reboot aangeroepen"
grep -c " terug " $B/injectv15-sessie.log | grep -q 2; ok $? "sessielog: 2x terug"
umount /jci/gui 2>/dev/null
ash $I/revert_inject.sh > /tmp/r2.log 2>&1; ok $? "revert na sessie exit 0 (kopie == /jci/gui)"
[ "$(find /jci -type f -exec md5sum {} \; | sort | md5sum)" = "$J0" ]; ok $? "/jci onaangeroerd (einde)"
kill $OP 2>/dev/null
echo "== $P PASS / $F FAIL"
for f in /tmp/a1.log /tmp/m5.log /tmp/r2.log; do echo "--- $f"; tail -5 $f; done
[ $F = 0 ]
EOF
set +e
unshare -r -m -p -f --mount-proc bash -c "touch $R/dev/null && mount --bind /dev/null $R/dev/null && mount -t proc proc $R/proc && mount -t tmpfs tmpfs $R/tmp && /usr/sbin/chroot $R /bin/ash /t.sh"
RC=$?
rm -rf "$T"
exit $RC
