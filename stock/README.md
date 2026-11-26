# stock/ - put your OWN CMU dumps here

This repository contains **no Mazda/ proprietary files**. Everything under `stock/` is gitignored
(except this README) - you fill it with dumps taken from **your own** CMU. The overlay builder
(`tools/make_overlay.py`) refuses to build unless your v74 dump matches the md5 list you made on the
CMU itself, so a wrong or modified dump can never produce an overlay.

Connect with SSH (see <https://github.com/espen795/mzd-toolkit>):

```
ssh -p 2222 cmu@<CMU_IP>
```

## Quick way: use the fetch scripts

Both routes copy `/jci/gui` + an md5 list made on the CMU, and verify the copy. Nothing is written
on the CMU (the USB route writes only to the stick).

**Over SSH** (run on the PC, needs SSH root on v74, see the mzd-toolkit repo):

```
sh tools/fetch_stock_ssh.sh <CMU_IP>          # port 2222, user cmu by default
```

**Over USB** (no SSH needed, but you need a root shell on the CMU, e.g. the diag terminal):

```
# 1. copy tools/dump_stock_usb.sh to a FAT32 stick (~150 MB free), plug it into the car, then on the CMU:
sh /tmp/mnt/sda1/dump_stock_usb.sh
# 2. back on the PC:
sh tools/import_stock_usb.sh /path/to/stick/mzd-stock
```

Then build: `python3 tools/make_overlay.py`. The manual steps below do the same by hand.

## stock/v74/jci/gui - REQUIRED: the v74 GUI tree from your own CMU

Copy the whole `/jci/gui` from your v74.00.324 CMU, preserving structure, e.g. over SSH from the host:

```
ssh -p 2222 cmu@<CMU_IP> 'tar -C / -cf - jci/gui' | tar -C stock/v74 -xf -
```

(or `cp -a /jci/gui stock/v74/` on a mounted share). Result: `stock/v74/jci/gui/apps/...`, `.../common/...`,
`index.html`, etc. - roughly 1100 files.

## stock/v74/MD5SUMS.cmu - REQUIRED: checksums made ON the CMU

On the CMU (so the paths and hashes are exactly what the running system has):

```
cd / && find jci/gui -type f | xargs md5sum > /data_persist/MD5SUMS.cmu
```

then copy that file to `stock/v74/MD5SUMS.cmu` on the host. `make_overlay.py` reads it and verifies every
stock file it patches (the 4 ecoenergy templates) against it.

## stock/v59-gui-dump/ - OPTIONAL: older full GUI dump, harness only

Only needed to run the headless harness (`harness/build_root.sh`). It needs a full older GUI dump
including the fonts, i.e. a directory with at least:

```
stock/v59-gui-dump/gui/            (full GUI tree of an older firmware)
stock/v59-gui-dump/fonts/Tipperary.ttf
stock/v59-gui-dump/fonts/TipperarySemibold.ttf
```

The harness serves `stock/v59-gui-dump/gui` as the base images/fonts layer and layers
`stock/v74/jci/gui` (the v74 code) on top, mimicking what `/jci/gui` serves at boot on v74. Without this
dump you can still build the overlay and run on-car tests - only the host harness needs it.

## What NOT to commit

Everything under `stock/` except this README is gitignored. Never commit dumps of `/jci/gui` (they are
Mazda's proprietary files); the md5 list `MD5SUMS.cmu` contains only hashes and paths, but it also stays
local for consistency.
