# Changelog - mzd-cmu-ui (B2 overlay)

> DRAFT project, firmware **v74.00.324**. "Tested on the car" below means: run once on a real CMU in a
> stationary car during a supervised test session (mount, browse, revert + reboot). "Harness" means: proven in
> the headless test harness only (real v74 GUI code in headless Chromium), **not yet on a car**.

## v1.5 (2026-11-27) - NEW, NOT YET TESTED ON THE CAR

Status: harness only. Everything below still has to be tested on the car.

New: **"Trip & driving style" panel** (on-screen name: *Rit & rijstijl*)
- New item in **Applications**, directly below *Fuel consumption*. Opens a B2-styled panel with 7 pages:
  this trip, shifting, accelerating & braking, previous trip (score + one driving tip), sub-scores, trend,
  explanation.
- Navigation like the stock lists: rotate / tilt left-right on the commander knob, touch only while
  stationary, long press closes, the Back button behaves as stock.
- While driving the same pages stay available (no lock screen), but refresh is limited to 1x/s and there are no
  animations. The start page is *previous trip* until the current trip is at least 0.5 km.
- Home: the *Applications* row shows a one-line summary (driving-style score / trip km + smooth shifts);
  hidden when there is no data.
- **Needs a companion live-data server** that is not part of this repo yet: the panel reads a small JSON API
  from `192.168.0.1:8765` (a Raspberry Pi on the CMU's USB-ethernet link that decodes the D-Bus capture and
  computes the trip/driving-style figures, see the trip-report tools in
  [mzd-toolkit](https://github.com/espen795/mzd-toolkit)). Without that server the panel shows "geen data"
  (no data) and the home line stays hidden; nothing else is affected.
- `OemplusLive.js`: transport with fallback WebSocket -> JSONP -> XHR, back-off 2/4/8/16/30 s, only active
  while something on screen subscribes (no sockets/timers otherwise).
- Fix: the third eco row (tyre-pressure / battery bubbles) is hidden while the media player bar is open.

Harness (v1.5, all 0 failures): see the numbers in the README "Status" section. The test suite uses a mock
data server (`harness/mock_live.py`) with a **synthetic** sample (`harness/fixtures/live-sample.json`).

## v1.4 (2026-11-27) - fixes from the v1.3 car test + eco/phone restyle - NOT YET TESTED ON THE CAR

Status: harness only (part of v1.5; v1.4 was never deployed separately).

Fixes for the findings of the 2026-11-27 car test (see v1.3 below):
- **Protected-screen guard no longer flaps**: during the switch to the reversing camera the B2 class was briefly
  removed, re-added 3 ms later and removed again. Now it is removed once and stays off until the camera screen
  is gone (harness proves the event order, incl. a mutation test that makes the check fail when the guard is off).
- In-car toggle panel *Info* text fits on screen (was running off the bottom).
- Media player control bar has a dark background (buttons were hard to see on a transparent bar).
- Settings > *System information* and *Update music database* dialogs: opaque background (the list behind was
  visible through the dialog), tab title no longer overlaps the tab bar.
- Incoming-call popup checked in the harness: hitboxes/focus identical to stock; no B2 defect found
  (the rough look comes from the stock content; the phone restyle below addresses the visuals).

New:
- **Terminal item in Applications** at runtime (RAM only, removed again on "B2 off"); needs the terminal
  trigger from [mzd-toolkit](https://github.com/espen795/mzd-toolkit) (`toolkit-v74/terminal/`).
- **P5 eco screens** restyled (fuel consumption, eco status, energy flow, effectiveness), incl. indirect
  tyre-pressure (TPMS) status bubbles read-only from the warning-guide app state. The eco status background
  photo in this repo is a neutral placeholder; drop your own 800x416 JPEG in
  `overlay-src/common/oemplusb2/images/B2EcoCarPhoto_B.jpg` if you want a car picture.
- **P6 phone screens** restyled (call screen, incoming call, dial pad focus rings).

## v1.3 (2026-11-26) - submenu skins P0-P4 - TESTED ON THE CAR 2026-11-27

v1.3 = v1.2 (unchanged) + the submenu skin layer (P0 base/loader/guard, P1 lists, P2 dialogs, P3 tabs/sliders,
P4 media/input). It is the build in which the v1.2 home changes were tested on the car.

Car test 2026-11-27 (stationary, ~20 min, firmware v74.00.324):
- Copy/apply/mount clean: full-tree comparison of the test copy OK, overlay applied with 0 deviations,
  mount prechecks passed, reversing-camera check 1 OK before mounting.
- "B2 on" worked; Info panel: home B2 active, 4/4 template hooks, 4/4 notification hooks, 0 B2 errors,
  submenu skins active.
- FM radio *Now Playing* rendered in B2 style; all menus usable.
- **Reversing camera from a B2 submenu: OK** (camera image fine, B2 class removed). The log showed the guard
  briefly re-adding the class during the transition (final state correct) -> fixed in v1.4.
- Revert: unmount + reboot OK, CMU back to factory.
- Findings (all addressed in v1.4, still to be re-tested): System information tab and *Update music database*
  dialog not readable, eco screens not yet restyled, transparent media control bar, incoming-call popup looked
  rough, Info text ran off-screen.
- Notification banners: the GUI log shows 3 banners while B2 was on (SMS download, 2x volume), but nobody
  looked at them consciously, so on-car visibility is **unproven**; the harness proves they are visible.
  Next car session: turn the volume knob on home, a list and the radio and check the volume bar.

### v1.2 changes (home screen) - tested on the car as part of v1.3

Changes after the first car test of v1.1 (2026-11-26):
1. Top 64 px of the B2 home reserved for the notification banner (the street-name banner covered the clock).
2. Notification banner restyled to match B2 (dark flat background, B2 typography).
3. Navigation street-name banners suppressed while B2 is on (only navigation style/type; safety, Bluetooth,
   volume and error notifications are never filtered).
4. Context panels on home filled immediately from the cached system state (unread messages, maintenance due,
   active audio source) - read only.

Results on the car (2026-11-27): the clock now sits below the reserved banner area and is no longer covered;
the stock status icons (signal/battery) stay visible top right; home rows and context panels render as in the
harness. Street-name suppression and the banner styling were not separately observed on the car (see the
notification note above).

## v1.1 (2026-11-26) - first car test

First supervised car test: overlay mounted, B2 home appeared live, all menu items worked from the B2 home,
reversing camera OK from B2, revert + reboot OK. Findings: street-name banner covered the clock, context panels
lacked live data -> v1.2.
