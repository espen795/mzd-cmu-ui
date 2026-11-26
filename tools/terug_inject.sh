#!/bin/sh
# terug_inject.sh v1.0 -- draait OP DE CMU (busybox 1.19 ash). TERUG = umount + reboot (geen Opera-reload: 1023-hang).
# Schrijft alleen een regel in /data_persist/oemplus-test/injectv13-sessie.log. Geen smctl, geen kill.
# Na de reboot draait de GUI weer uit /jci/gui (fabriek). Daarna: wachten op AA-guard, stap0_v74.sh 5d, revert_inject.sh.
# Gebruik: sh terug_inject.sh            (umount + reboot)
#          sh terug_inject.sh geen-reboot (alleen umount + log; reboot doet de gebruiker: Mute+Navi 10 s)
BASE=/data_persist/oemplus-test
SLOG=$BASE/injectv13-sessie.log
bootid() { cat /proc/sys/kernel/random/boot_id 2>/dev/null || grep '^btime' /proc/stat | cut -d' ' -f2; }
B=$(bootid)
if grep -q " /jci/gui " /proc/mounts; then
  umount /jci/gui && echo "umount OK" || echo "umount mislukt (geen probleem: reboot haalt de mount weg)"
else
  echo "/jci/gui was niet gemount"
fi
echo "$B terug uptime=$(cut -d' ' -f1 /proc/uptime)" >> "$SLOG"
sync
if [ "$1" = geen-reboot ]; then
  echo "Geen reboot door het script: de gebruiker nu Mute+Navi 10 s (verplicht voor rijden; eco-template/B2 zit nog in Opera-RAM)."
  exit 0
fi
echo "REBOOT nu. Daarna: contact aan laten, wachten tot aa_wacht.sh OK (>= 480 s), dan draaiboek stap 9."
sync
reboot
exit 0
