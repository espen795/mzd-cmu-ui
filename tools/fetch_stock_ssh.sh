#!/bin/sh
# fetch_stock_ssh.sh (run on the PC) - fetch YOUR OWN CMU's stock GUI into stock/ over SSH.
#
# Usage:  sh tools/fetch_stock_ssh.sh <CMU_IP> [port=2222] [user=cmu]
#
# Creates (all gitignored, never commit them):
#   stock/v74/jci/gui/          copy of /jci/gui
#   stock/v74/MD5SUMS.cmu       md5 list made ON the CMU (make_overlay.py verifies against it)
# Read-only on the CMU: nothing is written there except a temp file in /tmp.
# Needs SSH root access on v74 (see the mzd-toolkit repo, docs/V74.md).
set -e
IP=${1:?usage: sh tools/fetch_stock_ssh.sh <CMU_IP> [port] [user]}
PORT=${2:-2222}; USR=${3:-cmu}
HERE=$(cd "$(dirname "$0")/.." && pwd)
DST="$HERE/stock/v74"
SSH="ssh -p $PORT -o PubkeyAcceptedAlgorithms=+ssh-rsa -o HostKeyAlgorithms=+ssh-rsa,ssh-dss $USR@$IP"

echo "== firmware check"
VER=$($SSH 'cat /jci/version.ini 2>/dev/null | grep -i JCI_SW_VER' || true)
echo "   $VER"
case "$VER" in *74.00*) ;; *) echo "WARNING: not v74 - the build will most likely refuse this dump." ;; esac

mkdir -p "$DST/jci"
echo "== md5 list on the CMU"
$SSH 'cd / && find jci/gui -type f | xargs md5sum' > "$DST/MD5SUMS.cmu"
echo "   $(wc -l < "$DST/MD5SUMS.cmu") files listed"

echo "== copying /jci/gui"
rm -rf "$DST/jci/gui"
$SSH 'tar -C / -cf - jci/gui' | tar -C "$DST" -xf -

echo "== verify copy against the CMU md5 list"
( cd "$DST" && md5sum -c --quiet MD5SUMS.cmu ) && echo "   OK: copy matches the CMU" || { echo "ERROR: copy differs from the CMU"; exit 1; }
echo "Done. Next: python3 tools/make_overlay.py"
