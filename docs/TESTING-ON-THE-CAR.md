# TESTING ON THE CAR - build, harness, and an on-car test session

Everything below assumes firmware **v74.00.324** and SSH access to the CMU:

```
ssh -p 2222 cmu@<CMU_IP>
```

(see <https://github.com/espen795/mzd-toolkit> for enabling SSH on v74).

## 0. Prepare the repo on the host

1. Put your own CMU dumps in place (see `stock/README.md`):
   - `stock/v74/jci/gui/` - a copy of `/jci/gui` from your own v74 CMU
   - `stock/v74/MD5SUMS.cmu` - md5 list made **on the CMU** (see `stock/README.md`)
   - `stock/v59-gui-dump/` - optional, harness only (older full GUI dump incl. fonts)
2. Build the overlay (host):

   ```
   python3 tools/make_overlay.py
   ```

   This patches the 4 ecoenergy templates from `stock/v74/jci/gui`, copies `src/` and `overlay-src/`
   into `overlay/`, and verifies each stock file against `stock/v74/MD5SUMS.cmu`. It writes
   `overlay/ORIGINAL-MD5.txt`, `overlay/OVERLAY-MD5.txt` and `overlay/SHA256SUMS`.
   Static Presto/ES5 check:

   ```
   python3 tools/check_presto.py
   ```

3. Copy the payload to the CMU (into `/data_persist/oemplus-test/injectv13/`): the scripts
   `tools/{apply_inject,revert_inject,kopie_gelijk,kopie_vers,aa_wacht,mount_inject,terug_inject}.sh`
   plus `overlay/` and a `TOOLS-MD5.txt` (md5 of the scripts themselves, made on the host).
   Also create the test copy of the GUI (on the CMU):

   ```
   mkdir -p /data_persist/oemplus-test
   cp -a /jci/gui /data_persist/oemplus-test/gui
   ```

## 1. Headless harness (host, no car needed)

The harness runs the **real v74 GUI code** (framework, systemApp, Common, ecoenergy, ...) in headless
Chromium with a mock MMUI, and simulates the bind mount by switching the served root mid-session:

```
sh harness/build_root.sh                 # builds harness/root-stock and harness/root-inject
python3 harness/run_inject.py            # 86 checks: inject panel, B2 on/off, failure paths
python3 harness/checks_p1.py             # 54 checks: List2
python3 harness/run_p2_dialog3.py        # 82 checks: Dialog3
python3 harness/run_p3.py                # 72 checks: tabs/sliders/buttons
python3 harness/run_submenus_p4.py       # 52 checks: media + keyboard/dialpad
python3 harness/run_cumulatief.py        # 28 checks: all 5 B2Sub CSS files together
```

Results land in `harness/RESULTS*.json`, screenshots in `harness/shots/`. Requires Python 3 +
Playwright (`pip install playwright && playwright install chromium`).
The shell scripts are also tested on the host under busybox 1.19.0-ash in a chroot:
`bash tools/test_scripts_bb119.sh` (53 checks: apply/revert, full-tree comparison both directions,
mount prechecks, max one mount per boot, `/jci` untouched).

## 2. On-car test session (on the CMU, busybox ash)

All scripts run on the CMU and write only under `/data_persist/oemplus-test/`. They never write to
`/jci`, never touch `sm.conf`/autorun, and never kill or restart the GUI process.

1. **Wait for a healthy boot** (crash-counter guard): `sh aa_wacht.sh` must print `AA-WACHT OK`
   (uptime >= 480 s, bootcount 0, guard not disabled). Retry every minute; exit 3 = keep waiting.
2. **Apply the overlay to the test copy** (not active yet):

   ```
   sh /data_persist/oemplus-test/injectv13/apply_inject.sh
   ```

   Prechecks: scripts match `TOOLS-MD5.txt`, the test copy is a full-tree md5-exact copy of `/jci/gui`
   (`kopie_gelijk.sh schoon`), `/jci/gui` itself still has the v74 originals; afterwards the copy may
   differ from `/jci/gui` only in the 183 overlay paths (`kopie_gelijk.sh overlay`).
3. **Reversing-camera check (mandatory, this boot)**: put the car in R, confirm the camera image works,
   then back to P.
4. **Mount**:

   ```
   sh /data_persist/oemplus-test/injectv13/mount_inject.sh camera-ok
   ```

   Prechecks include: AA-guard OK, overlay applied, full-tree check, >= 40 MB MemFree and >= 200 MB
   MemFree+Cached, exactly one Opera process, no second mount in this boot, no unexplained reset earlier
   in the session. It then does `mount --bind /data_persist/oemplus-test/gui /jci/gui` and proves the
   mount (entry in /proc/mounts + md5 of the injected loader read through `/jci/gui`).
   From now on, files the GUI has not cached yet are served from the overlay.
5. **In the car**: open **Applications > Fuel consumption** - the overlay panel appears
   ("B2 on (home + submenus)", "B2 off", "Info", "Continue to eco screen"). Choose **B2 on**, go Home,
   and browse: Applications list, Communication, a dialog, Settings tabs, FM radio Now Playing, DialPad.
   Take photos of anything unexpected.
6. **Revert**:

   ```
   sh /data_persist/oemplus-test/injectv13/terug_inject.sh
   ```

   This unmounts `/jci/gui` and reboots the CMU. **Do not drive between mount and reboot** - the patched
   templates stay in the running GUI's RAM until the reboot.
7. **Reboot** = hold **Mute + Navi** for 10 s (the script also offers `terug_inject.sh geen-reboot`, then
   you reboot manually). After the reboot the GUI runs from `/jci/gui` again: factory.
8. After the reboot, wait for `aa_wacht.sh` OK again, then remove the overlay from the test copy:

   ```
   sh /data_persist/oemplus-test/injectv13/revert_inject.sh
   ```

   This restores the 4 original templates (from `/jci/gui` or the backup), deletes the 179 added files and
   ends with a full-tree check that the copy equals `/jci/gui` again. If that check ever fails:
   `sh .../kopie_vers.sh` recreates a fresh copy (`cp -a /jci/gui`).

### Failure paths

| Symptom | What you see | Recovery |
|---|---|---|
| Runtime error in hook/panel | eco screen without or with a half panel | nothing changed; revert via reboot |
| Panel does not appear | normal eco screen | stop; revert (reboot) |
| B2 file missing/late/invalid | "B2 NOT enabled", home stays stock | revert via reboot |
| B2 constructor throws | home shows the **stock** screen, error in Info | revert via reboot |
| Patched template itself fails to load/parse | ~8 s blank screen, then automatic board reset | self-healing: after reset the mount is gone, CMU is factory |
| B2 visible but not operable | home does not respond to dial/touch | Nav/Audio button, else reboot |

A reboot is sufficient in every case: nothing is ever persisted.
