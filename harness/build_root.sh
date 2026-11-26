#!/bin/sh
# Bouwt harness/root-stock/ (v59-beelden/fonts + v74-code = wat /jci/gui bij boot serveert) en
# harness/root-inject/ (= root-stock + overlay = proefkopie na make_overlay; wat na de bind-mount gelezen wordt).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
MZD=$(cd "$HERE/.." && pwd)
DUMP="$MZD/stock/v59-gui-dump"
V74="$MZD/stock/v74/jci/gui"
for MODE in stock inject; do
  ROOT="$HERE/root-$MODE"
  rm -rf "$ROOT"; mkdir -p "$ROOT"
  cp -a "$DUMP/gui/." "$ROOT/"
  cp -a "$V74/." "$ROOT/"
  if [ "$MODE" = inject ]; then
    (cd "$HERE/../overlay" && find . -type f ! -name ORIGINAL-MD5.txt ! -name OVERLAY-MD5.txt ! -name SHA256SUMS | while read f; do
       mkdir -p "$ROOT/$(dirname "$f")"; cp "$f" "$ROOT/$f"; done)
  fi
  mkdir -p "$ROOT/_harness_fonts"
  cp "$DUMP/fonts/Tipperary.ttf" "$DUMP/fonts/TipperarySemibold.ttf" "$ROOT/_harness_fonts/" 2>/dev/null || \
  { echo "Tipperary fonts missing: copy them from YOUR OWN CMU dump into stock/v59-gui-dump/fonts/" >&2; exit 1; }
  echo "root: $ROOT"
done
