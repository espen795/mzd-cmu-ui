# DESIGN - architecture of the B2 overlay

Target runtime: Mazda Connect CMU, firmware v74.00.324, GUI = Opera 12.10 (Presto 2.12) rendering an
HTML/JS app tree from `/jci/gui`. The GUI process is never restarted; the overlay is injected into the
running page.

## 1. Injection point: the four ecoenergy templates

All visible Applications rows have their `*App.js` loaded at boot (MMUI messages), but **context templates
load lazily** on first use (`framework._addTmpltFiles`). The `ecoenergy` app (Applications > Fuel
consumption) owns four app-specific templates that no other screen uses:

- `apps/ecoenergy/templates/FuelConsumption/js/FuelConsumptionTmplt.js`
- `apps/ecoenergy/templates/EcoStatus/js/EcoStatusTmplt.js`
- `apps/ecoenergy/templates/EcoFlow/js/EcoFlowTmplt.js`
- `apps/ecoenergy/templates/EcoEffect/js/EcoEffectTmplt.js`

`tools/make_overlay.py` patches exactly these four files, adding only two insertions each (verified: the
whole file must still parse as ES5 and no original line may be removed):

1. at the end of the template constructor: `try { OemplusInjectHook(this); } catch (e) {}`
2. before `framework.registerTmpltLoaded(...)`: a one-time `utility.loadCss/loadScript` of
   `apps/ecoenergy/oemplus/OemplusInject.{css,js}` plus the `OemplusInjectHook()` definition.

Because the overlay is bind-mounted over `/jci/gui` while Opera is running, the first read of these
templates after the mount comes from the overlay copy. Everything else in the copy is byte-identical to
the stock tree (enforced by full-tree md5 comparison, see `tools/kopie_gelijk.sh`).

## 2. The loader: `OemplusInject.js`

Loaded once into the running page. On every opening of an ecoenergy screen it attaches a small toggle
panel (740x416) over the template:

- **B2 on** / **B2 off (until reboot)** / **Info** / **Continue to eco screen**

Operated with the command dial (rotate/select/tilt) or touch (press+release on a row). The Back key keeps
working (it is sent to MMUI before the template).

"B2 on" performs, entirely in RAM (nothing is persisted; a reboot = factory):

1. Load `MainMenuCtrl-oemplusb2.js` and let it call `framework.registerCtrlLoaded("MainMenuCtrl")` exactly
   once; that single call is swallowed by a temporary wrapper so the framework load-state is untouched.
   Success = the swallowed call (synchronous), not `onload`; `onerror`/`onload` are only accelerators and
   the fallback is an 8 s timeout. A late-arriving file is swallowed and changes nothing.
2. Replace `window.MainMenuCtrl` with a **guarded constructor**. The home template is re-instantiated on
   every context change, so the next home screen builds the B2 control. If the B2 constructor throws, the
   half-built DOM and its listeners are removed, everything is rolled back and the original control is
   built in the same place; every B2 method that calls template/framework/systemApp is wrapped in
   try/catch - an error turns B2 off (next home is stock) without hanging the framework transition.
3. CSS: the original `MainMenuCtrl.css` `<link>` is removed from the DOM (not disabled) and re-inserted at
   the exact same position on "off"; the B2 stylesheets are added next to it.
4. `systemApp` message handlers (notifications, audio source, missed calls, scheduled maintenance) are
   wrapped per instance (the table entries are `.bind()`ed, so a prototype patch would not work) - only
   read access, no MMUI re-requests.
5. Log source via `log.addSrcFile("OemplusInject.js", "system")`.

"B2 off" restores constructor, CSS links, handlers and body classes; the next home is stock.

## 3. Body classes and the protected-screen guard

- `body.OemplusB2Home` - home-screen-specific B2 state (set/removed by the B2 control itself, guarded by a
  500 ms tick that removes it whenever the current context is not `system/HomeScreen`).
- `body.OemplusB2` - the global "B2 submenu skin active" class. All submenu CSS selectors are prefixed with
  `body.OemplusB2 `, so without the class nothing matches and the OEM look is untouched.

The guard (`setSubClass`) runs **synchronously** via wrappers on `framework._callHandleContext` (reads the
incoming context before the original runs) and `framework._transitionChange`, so a protected screen is never
painted with the class; the 500 ms guard tick is the fallback. Protected contexts: backupparking (reversing
camera), warnguide, mobile911, androidauto, carplay, emnavi, diag, tutorial, and
system/{DisplayOff, IdleStandby, WaitForEnding, IntroAnimation, QuickStartLoop, PowerDownAnimation}.
On any wrapper error the class is removed (fail-safe = stock) and the original call always runs.

## 4. CSS loader order

On "B2 on", `OemplusInject.js` appends one `<link>` per file at the end of `<head>`, in fixed order:

1. `common/oemplusb2/css/B2Sub-00-base.css`   (background, status bar, base assets)
2. `common/oemplusb2/css/B2Sub-10-list2.css`  (P1: lists)
3. `common/oemplusb2/css/B2Sub-20-dialog3.css` (P2: dialogs)
4. `common/oemplusb2/css/B2Sub-30-tabs-slider-button.css` (P3: tabs, sliders, buttons)
5. `common/oemplusb2/css/B2Sub-40-media-input.css` (P4: media + keyboard/dialpad)

A missing file 404s and is skipped without error, so the parts can land independently. The
`body.OemplusB2` prefix gives specificity +0,1,1 over late-loading OEM CSS regardless of link order.
Rules only change skin (colors, fonts, background images, border colors on decorative parts) - never
left/top/width/height of hitbox elements, so hitboxes and focus order are identical with B2 on/off
(harness checks H1/H2 verify this at 0 px difference).

## 5. SBN banner handling

The status-notification banner (SbnCtrl) is an Opera DOM control on `document.body`. In B2 style it stays
**visible** (the stock status bar is hidden on the B2 home, the banner is not), with a dark flat background
and a subtle slide-in via `-o-transition`. The top 64 px of the B2 home are reserved for it, so it never
overlaps the clock or rows. While B2 is on, only the navigation street-name banners (Style05,
navigationNear/navigationFar) are filtered out of `framework.common.startTimedSbn/showStateSbn/...` via
instance-property wrappers; an already displayed navigation banner is ended immediately. Safety
notifications (error, device removed, Bluetooth, volume, ...) are never filtered, and the filter is fully
removed on "B2 off".

## 6. Context panels seeded from cached state (read-only)

On the B2 home, the context panels (communication, settings/maintenance, entertainment) are seeded at
"B2 on" from the **cached** `systemApp` state (`_communicationsDataList`, `_SchedMaintDueStatus` /
`SelectSchedMaint`, the now-playing icon in the entertainment list). This is strictly read-only - no MMUI
re-request is sent, because any MMUI message could trigger a vehicle action and there is no proven-safe
re-request. Panels show "-" until the corresponding status message arrives again, which is expected.

## 7. Presto / Opera 12 constraints

All injected code is ES5 only (checked by `tools/check_presto.py`, which also acorn-parses the patched
templates with ecmaVersion 5):

- no `classList` reliance, no gradients/flex/grid/calc/box-shadow/keyframes; transitions only as `-o-`
  prefixed properties;
- CSS links are moved by removing/re-inserting DOM nodes, not via `link.disabled`;
- APNG spinners are not animated in a div background on Presto, so the B2 indeterminate meter uses static
  frames and the OEM `<img>` is hidden;
- every function body of the hook is wrapped in try/catch; a runtime error leaves the stock screen intact.

## 8. Asset generators

All PNG art is generated, not traced: `tools/assets/_lib.py` holds the shared drawing helpers and
`tools/assets/p0_base.py` ... `p4_media.py` generate the per-part assets into
`overlay-src/common/oemplusb2/images/` (137 PNGs: backgrounds, list rows, focus frames, dialog buttons,
progress track/fill, PIN field, tab arrows, 150x100 buttons, artwork frame, Ump3 buttons/scrubber, dialpad
keys, and keyboard keys in the exact OEM key sizes read from `KeyboardCtrl.css`: 74x91, 75x68, 62x68,
75x71, 75x46, 68x46, plus the control keys). Each part owns its own PNG prefix so parts never collide;
a few P1 assets (slider track/fill/knob, list separator, checkbox) are referenced read-only by P2/P3.
