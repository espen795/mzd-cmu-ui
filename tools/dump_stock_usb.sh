#!/bin/sh
# dump_stock_usb.sh (run ON the CMU as root) - write the stock GUI to a USB stick, without SSH.
#
# Usage on the CMU:   sh /tmp/mnt/sda1/dump_stock_usb.sh            (auto-detects the stick)
#                     sh dump_stock_usb.sh /tmp/mnt/sdb1             (explicit stick)
# Writes to the stick:  mzd-stock/jci-gui.tar, mzd-stock/MD5SUMS.cmu, mzd-stock/version.txt
# Then on the PC:       sh tools/import_stock_usb.sh /media/<you>/<stick>/mzd-stock
# Read-only on the CMU: writes ONLY to the USB stick. FAT32 stick with ~150 MB free.
# v74 mounts USB sticks read-only; this script remounts the stick read-write.
USB=$1
if [ -z "$USB" ]; then
    for d in /tmp/mnt/sd[a-z]1 /tmp/mnt/sd[a-z]; do
        [ -d "$d" ] || continue
        case "$d" in *nav*) continue ;; esac
        USB=$d; break
    done
fi
[ -n "$USB" ] && [ -d "$USB" ] || { echo "ERROR: no USB stick found under /tmp/mnt"; exit 1; }
if ! touch "$USB/.mzdtest" 2>/dev/null; then
    mount -o remount,rw "$USB" 2>/dev/null
    touch "$USB/.mzdtest" 2>/dev/null || { echo "ERROR: $USB is read-only"; exit 1; }
fi
rm -f "$USB/.mzdtest"
OUT="$USB/mzd-stock"; mkdir -p "$OUT" || exit 1
NEED=$(du -sk /jci/gui | awk '{print $1}'); FREE=$(df -k "$USB" | awk 'NR==2{print $4}')
[ "$FREE" -gt $((NEED + 20000)) ] || { echo "ERROR: not enough space on $USB (${FREE} KB free, need ~${NEED} KB)"; exit 1; }

echo "== version";  grep -i JCI_SW_VER /jci/version.ini > "$OUT/version.txt" 2>/dev/null; cat "$OUT/version.txt"
echo "== md5 list"; (cd / && find jci/gui -type f | xargs md5sum) > "$OUT/MD5SUMS.cmu" || { echo "ERROR: md5 list failed"; exit 1; }
echo "== gui tar";  tar -C / -cf "$OUT/jci-gui.tar" jci/gui || { echo "ERROR: tar failed (stick full or read-only?)"; exit 1; }
sync
[ -s "$OUT/jci-gui.tar" ] && [ -s "$OUT/MD5SUMS.cmu" ] || { echo "ERROR: output incomplete"; exit 1; }
echo "Done: $(ls -la "$OUT" | wc -l) entries in $OUT. Remove the stick and run tools/import_stock_usb.sh on the PC."
