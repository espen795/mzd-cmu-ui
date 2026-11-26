#!/bin/sh
# aa_wacht.sh v1.0 -- draait OP DE CMU (busybox 1.19 ash). ALLEEN LEZEN. R-cmu H3/V3.
# Harde precheck voor de mount: de AA-crash-guard moet over DEZE boot al 'gezond' geoordeeld hebben, zodat een
# onverwachte reset tijdens de proef niet als mislukte AA-boot telt.
# OK = uptime >= 480 s EN /data_persist/dev/aa/bootcount = 0 EN geen 'disabled'. Zonder AA-kit: alleen de uptime-eis.
# Exit: 0 = OK, proef mag | 3 = nog wachten (opnieuw over 1 min) | 1 = STOP (guard niet gezond / disabled)
AA=/data_persist/dev/aa
MIN=480
MAXWAIT=720

read U _ < /proc/uptime
U=${U%%.*}
case "$U" in ''|*[!0-9]*) echo "STOP: uptime onleesbaar"; exit 1;; esac
echo "uptime ${U}s (eis >= ${MIN}s)"
if [ ! -d "$AA" ]; then
  [ "$U" -ge "$MIN" ] || { echo "WACHT: nog $((MIN - U)) s"; exit 3; }
  echo "INFO: geen AA-kit in $AA -- alleen de uptime-eis"
  echo "AA-WACHT OK"
  exit 0
fi
BC=$(head -n 1 "$AA/bootcount" 2>/dev/null)
echo "bootcount '${BC}' (eis 0)  disabled: $( [ -e "$AA/disabled" ] && cat "$AA/disabled" || echo nee)  DISABLE: $( [ -e "$AA/DISABLE" ] && echo ja || echo nee)"
echo "guard.log (laatste 3):"; tail -n 3 "$AA/guard.log" 2>/dev/null | sed 's/^/  /'
[ -e "$AA/disabled" ] && { echo "STOP: crash-guard staat op 'disabled' -- eerst analyseren (AA-kit), geen proef"; exit 1; }
if [ "$U" -lt "$MIN" ]; then echo "WACHT: nog $((MIN - U)) s"; exit 3; fi
if [ "$BC" != 0 ]; then
  if [ "$U" -lt "$MAXWAIT" ]; then echo "WACHT: guard nog geen 'gezond' (bootcount ${BC}); opnieuw over 1 min"; exit 3; fi
  echo "STOP: na ${U}s nog bootcount '${BC}' -- guard gaf deze boot geen 'gezond'; geen proef"
  exit 1
fi
echo "AA-WACHT OK"
exit 0
