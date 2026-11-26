#!/bin/sh
# import_stock_usb.sh (run on the PC) - import what dump_stock_usb.sh wrote to the stick into stock/.
# Usage:  sh tools/import_stock_usb.sh <path-to-stick>/mzd-stock
set -e
SRC=${1:?usage: sh tools/import_stock_usb.sh <stick>/mzd-stock}
HERE=$(cd "$(dirname "$0")/.." && pwd)
DST="$HERE/stock/v74"
[ -f "$SRC/jci-gui.tar" ] && [ -f "$SRC/MD5SUMS.cmu" ] || { echo "ERROR: $SRC has no jci-gui.tar / MD5SUMS.cmu"; exit 1; }
cat "$SRC/version.txt" 2>/dev/null || true
mkdir -p "$DST"; rm -rf "$DST/jci"
tar -C "$DST" -xf "$SRC/jci-gui.tar"
cp "$SRC/MD5SUMS.cmu" "$DST/MD5SUMS.cmu"
( cd "$DST" && md5sum -c --quiet MD5SUMS.cmu ) && echo "OK: copy matches the CMU md5 list" || { echo "ERROR: copy differs (stick corrupt? re-run the dump)"; exit 1; }
echo "Done. Next: python3 tools/make_overlay.py"
