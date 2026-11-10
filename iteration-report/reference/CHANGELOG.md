# Changelog

## v1.1.5 — 2026-11-10 — Failsafe release + real camera resolution

Status: implemented; awaiting field validation.

### Background

Code review found three integration issues:

1. A PyAutoGUI failsafe at a screen corner could leave the left button held:
   `mouseUp` itself goes through the failsafe check, so swallowing its exception
   never released the drag.
2. The camera may ignore the requested `CAP_PROP_FRAME_WIDTH/HEIGHT`. Landmark
   pixels and cursor mapping were still built from `config.CAMERA_WIDTH/HEIGHT`,
   causing offset/compression.
3. When the hand left the active region, `np.interp` clamped the cursor to the
   screen edge, which looked like the cursor was stuck.

### Fixes

- `MouseController.release_all()` temporarily disables `pyautogui.FAILSAFE`,
  releases left/right buttons, then restores the setting.
- `mouse_up()` uses the same failsafe-bypassing release path.
- `main.py` finally block calls `release_all()` instead of `mouse_up()`.
- `main.py` reads the first frame after opening the camera and constructs the
  controller with the actual `frame.shape[1], frame.shape[0]`.
- `FRAME_REDUCTION` is scaled from the configured reference resolution to the
  actual frame size; the HUD active rectangle uses the actual controller area.
- When the index finger is outside the active rectangle, the cursor holds its
  last position and the HUD shows `Out of Area` instead of snapping to an edge.

### Note on normalization

Palm-size normalization solves **gesture distance** scaling; it does not solve
**pixel coordinate mapping**. The actual camera resolution is still required for
the active region and cursor mapping. Both are now used together.

### Tests

Added regression tests for:

- `release_all()` releases both buttons while bypassing failsafe;
- active area scales for a 1280×720 frame (200/150 margins);
- an index fingertip outside the active area does not move the cursor.

Suite is now **38 tests** (29 gesture + 6 mouse + 3 volume).

### Notes

- The camera banner prints the actual resolution next to the requested one.
- If a camera changes resolution mid-session, restart the app; the controller
  uses the first-frame size.
- Known limitation: camera access may still require administrator rights on the
  current machine.

## v1.1.4 — 2026-11-10 — Volume control gesture

Status: implemented; awaiting field validation.

### Goal

Add system volume control without taking over single click, double click,
right click or scroll.

### Design

- Gesture: **thumb + ring fingertip pinch**, then move the whole hand up/down.
  The ring finger was otherwise unused, so it does not collide with:
  - index pinch (left click / drag / double click);
  - middle pinch (right click);
  - index + middle pose (scroll).
- The user must first separate thumb and ring (`d_tr > VOLUME_EXIT_RATIO`) and
  then pinch them. This arming step prevents a resting fist from entering
  volume mode.
- The ring fingertip must be the closest one to the thumb
  (`d_tr < d_ti` and `d_tr < d_tm`); otherwise normal click/right/scroll
  arbitration applies.
- Volume is checked before right click so a deliberate ring pinch is not stolen
  by thumb-middle proximity.
- Movement uses the same fractional accumulator/dead-zone approach as scroll:
  hand up = louder, hand down = quieter, capped per frame.
- Windows sends `VK_VOLUME_UP` / `VK_VOLUME_DOWN` via `keybd_event` with the
  extended-key flag; other platforms fall back to PyAutoGUI media keys.

### Changes

- New `volume_controller.py` (`VolumeController.up/down/mute`).
- `GestureController` gains an optional `volume=` dependency and
  `STATE_VOLUME`.
- `main.py` creates the volume controller and prints the new gesture in the
  banner.
- New config:
  - `VOLUME_ENTER_RATIO / VOLUME_EXIT_RATIO`
  - `VOLUME_DEAD_ZONE_RATIO / VOLUME_PALM_PER_STEP`
  - `VOLUME_MAX_STEPS_PER_FRAME / VOLUME_CONFIRM_FRAMES`
- New tests: volume arming, up/down, exit, per-frame cap, and volume-key
  wrapper. Suite is now **35 tests** (27 gesture + 5 mouse + 3 volume).

### Notes

- If the ring gesture is hard to trigger, raise `VOLUME_ENTER_RATIO`
  (e.g. `0.34`); if it triggers accidentally, lower it.
- Volume keys are sent as media keys; Windows must allow media-key input.
- The HUD shows `VOLUME` / `Volume Up` / `Volume Down` / `Volume Ready`.

## v1.1.3 — 2026-11-09 — Double click via two pinches

Status: implemented; thresholds relaxed after the first field test; final
double-click field confirmation pending.

### Goal

Add double-click without adding a new hand pose or breaking single click,
drag, right click or scroll.

### Design

- Double click is **two complete, stationary thumb-index pinch cycles**.
- The first click is emitted immediately on release (no buffering, unchanged
  single-click latency).
- The second click is emitted on its release if it lands within
  `DOUBLE_CLICK_WINDOW` and the cursor moved no more than
  `DOUBLE_CLICK_MAX_MOVE_PX`; the cursor is snapped back to the first click
  point before the second click. Windows then recognizes the pair as a
  double-click. On Windows the app uses the stricter of the configured window
  and `GetDoubleClickTime()`.
- The app does **not** call `pyautogui.doubleClick()`: the first click has
  already been delivered, so calling `doubleClick()` would produce three
  clicks.
- If the second pinch is too slow or cursor drift is too large, it degrades to
  two separate single clicks.
- Each individual pinch's hold duration is **not** an app-level gate; only the
  click-to-click window and cursor drift matter. (First field test showed the
  earlier "quick pinch" gate was unnecessarily strict.)
- `CLICK_DEBOUNCE` lowered from 0.30 s to 0.10 s so the second click is not
  swallowed; the pinch state machine already guarantees one click per release.

### Conflict prevention

- `RIGHT_CLICK_SUPPRESS_AFTER_CLICK = 0.30`: a thumb returning to the middle
  finger after a left click cannot steal the second click as a right click.
- Double-click uses the index pinch; keep the middle finger folded so the
  scroll pose is not active.
- Drag still requires hold + movement, so two stationary pinches do not
  start a drag.

### Tests

Added regression tests for:

- one pinch = one click;
- two stationary pinches = two clicks + `Double Click` action;
- second pinch beyond `DOUBLE_CLICK_WINDOW` = two single clicks;
- second pinch with >16 px cursor drift = two single clicks;
- a long first pinch can still group if the two click events fall within the
  double-click window (hold duration is not an app-level gate);
- right click suppressed after a left click.

Suite is now **29 tests** (24 gesture + 5 mouse).

### Notes

- Real OS double-click timing still matters: the two click events must fall
  within the Windows double-click time, and the cursor must stay still. If
  users cannot do this reliably, the fallback is a dedicated thumb-ring tap
  mapped directly to `doubleClick()`.
- Test in Explorer: double-clicking a folder should open it; a single pinch
  should only select it.

## v1.1.2 — 2026-11-09 — Freeze and left-click stabilization

Status: accepted by user (2026-11-09); core features work. Minor camera/display
latency remains and is tracked in `BACKLOG.md`.

### Symptoms reported

- Cursor sometimes stops in an area, stays frozen for a while, then gesture
  control resumes.
- Left click sometimes does nothing when moving to a window control (e.g. the
  close button) and clicking.

### Root causes

1. The right-click latch could stay active indefinitely if the thumb remained
   near the middle fingertip. While latched, every frame returned early and
   cursor movement was blocked.
2. Pinch-to-drag was decided by time only. A stationary pinch held longer than
   `DRAG_HOLD_TIME` became a drag, and releasing it produced neither a drag
   drop nor a click — the common "slow click on a close button does nothing".
3. Cursor mapping reached exact physical screen corners. PyAutoGUI's failsafe
   then raised on every move, but the old handler swallowed the exception
   while leaving the cursor parked in the corner, so it could appear frozen.

### Fixes

- Added `RIGHT_CLICK_LATCH_TIMEOUT = 0.80`. If the thumb stays near the middle
  after a right click, the latch expires and normal pinch/scroll/cursor
  arbitration resumes.
- Drag now requires **both** `elapsed > DRAG_HOLD_TIME` **and** actual
  movement of at least `DRAG_START_MOVE_RATIO` palm widths. A stationary hold
  is a click on release, even if it lasted longer than `DRAG_HOLD_TIME`.
- Added `SCREEN_EDGE_MARGIN = 8`: the mapped cursor stays 8 px away from the
  physical corners, avoiding accidental PyAutoGUI failsafe freezes.
- `MouseController` now records `failsafe_triggered`; `main.py` exits cleanly
  with a message instead of swallowing the abort and leaving the cursor parked
  in a corner.
- Added regression tests: latch timeout unblocks the cursor; long stationary
  pinch is a click; cursor mapping stays clear of corners. Total suite is now
  **23 tests**.

### Notes

- A quick pinch with no movement is a click. Drag requires holding briefly and
  moving the hand; if drag starts too easily, raise
  `DRAG_START_MOVE_RATIO` (e.g. `0.20`).
- If the cursor freezes, check the HUD state:
  `Right Click` / `PINCH` / `SCROLL` indicates the state machine is holding a
  gesture; `No Hand` indicates tracking loss.

## v1.1.1 — 2026-11-09 — Right-click tap discrimination + Windows wheel delta

Status: implemented; awaiting field validation on the user's webcam.

### Symptoms reported

- While moving the cursor with the index finger, the thumb naturally rests
  against the middle finger, and right click fired accidentally.
- The HUD showed `SCROLL`, but moving the hand up/down did not scroll the page.

### Fixes

- **Right click is now a tap, not a static contact.** A right click requires
  the thumb-middle distance to have been at least
  `RIGHT_CLICK_TAP_DELTA` (0.12 palm) farther away within
  `RIGHT_CLICK_TAP_WINDOW` (0.30 s), then close the gap. A thumb that simply
  rests on the middle finger has no such recent drop and no longer fires.
  Because the right-click branch is skipped for a resting thumb, it also no
  longer steals frames from the scroll state.
- **Scroll thresholds made more responsive.** `SCROLL_DEAD_ZONE_RATIO`
  0.035 → 0.02 and `SCROLL_PALM_PER_TICK` 0.22 → 0.15, so a small vertical
  hand movement produces a wheel tick instead of being swallowed.
- **Windows wheel delta fixed.** PyAutoGUI 0.9.54's Windows backend passes the
  click count directly to `mouse_event` as `dwData`, but Windows expects
  multiples of `WHEEL_DELTA` (120). `scroll(1)` was therefore 1/120 of a
  notch. `MouseController` now sends `amount * 120` through
  `mouse_controller._send_wheel`, capped at 3 notches per call.
- Added regression tests: resting thumb does not right-click; scroll works
  while the thumb rests on the middle finger; Windows wheel events use
  `WHEEL_DELTA` units. Total suite is now **20 tests**.

### Notes

- Right click now requires a deliberate quick tap. If it feels too hard,
  lower `RIGHT_CLICK_TAP_DELTA` (e.g. `0.08`) or increase
  `RIGHT_CLICK_TAP_WINDOW` (e.g. `0.40`).
- Scroll events go to the focused window. Click the page/document first and
  keep the cursor over the scrollable area, not over the OpenCV preview.

## v1.1.0 — 2026-11-09 — Gesture stability update

Baseline preserved in `legacy/` (original files + `legacy/SHA256SUMS.txt`).

### Motivation

Live use showed that **scroll** and **right click** were unreliable: they were
either not triggered at all, triggered accidentally, or repeated while the
pose was held. The problems were structural, not just a matter of increasing
a threshold.

### Root causes found

1. **Pixel-based thresholds**
   `PINCH_THRESHOLD = 40`, `RIGHT_CLICK_THRESHOLD = 40`,
   `SCROLL_DEAD_ZONE = 6` and `THUMB_EXTENDED_DISTANCE = 60` all depended on
   the hand's distance from the camera and the frame resolution.
2. **Y-coordinate finger detection**
   `landmarks[tip].y < landmarks[pip].y` broke whenever the hand was tilted;
   every gesture depended on this.
3. **Right-click required an extended middle finger**
   A natural thumb-middle tap bends the middle finger, so `fingers[2]` became
   `0` and the right click never fired.
4. **Priority conflicts**
   Pinch was handled before right click and required `not is_pinch`; scroll
   was handled before right click and required index+middle extended. A
   right-click pose with the index up was stolen by pinch or scroll. Right
   click only worked with the index folded — an unnatural pose.
5. **Right click was level-triggered**
   Holding the pose re-fired once per `RIGHT_CLICK_DEBOUNCE` (0.45 s). There
   was no armed/released state.
6. **Scroll mapping lost motion**
   Movement below 6 px was ignored. When it exceeded 6 px, the full delta was
   sent and the anchor was reset. With `SCROLL_SENSITIVITY > 1`,
   `int(delta / sensitivity)` could be 0 while the anchor still reset, so slow
   motion was permanently discarded. With `SCROLL_SENSITIVITY = 1`, a 10 px
   movement sent 10 wheel ticks at once, which felt like a jump.
7. **No temporal confirmation or hysteresis**
   A single noisy frame could start/stop a gesture.
8. **Mouse fail-safe only guarded `move`**
   `click` / `right_click` / `scroll` / `mouse_down` / `mouse_up` could raise
   `FailSafeException` and crash the capture loop.
9. **`time.time()`**
   Wall-clock jumps could affect hold/debounce durations.

### Changes

#### `config.py`

Replaced pixel thresholds with palm-size-normalized ratios:

- `PINCH_ENTER_RATIO` / `PINCH_EXIT_RATIO`
- `RIGHT_CLICK_ENTER_RATIO` / `RIGHT_CLICK_EXIT_RATIO` / `RIGHT_CLICK_DOMINANCE`
- `FINGER_EXTENDED_RATIO_ENTER` / `FINGER_EXTENDED_RATIO_EXIT`
- `SCROLL_DEAD_ZONE_RATIO` / `SCROLL_PALM_PER_TICK`
- `SCROLL_MAX_TICKS_PER_FRAME`
- `GESTURE_CONFIRM_FRAMES` / `SCROLL_EXIT_GRACE`

The old values remain available in `legacy/config.py` for reference.

#### `gesture_controller.py`

- Palm-size normalization: `palm = distance(wrist, middle MCP)`, every
  thumb/finger distance is divided by it.
- Finger extension uses `tip-to-MCP / PIP-to-MCP` plus the PIP joint angle,
  with enter/exit hysteresis. Raw `y` comparisons are gone.
- **Right click**:
  - checked before pinch and scroll;
  - middle finger may be bent;
  - requires thumb-middle to be clearly closer than thumb-index
    (`RIGHT_CLICK_DOMINANCE`);
  - requires `GESTURE_CONFIRM_FRAMES` consecutive frames;
  - latches after firing and only re-arms after the thumb moves beyond
    `RIGHT_CLICK_EXIT_RATIO` (no repeat while held).
- **Scroll**:
  - index+middle extended, ring+pinky not both extended (open palm excluded);
  - removed the old `pinch_dist > 1.5 * PINCH_THRESHOLD` gate;
  - uses the palm-centre y, not the index tip y;
  - fractional accumulator: `acc += -delta / pixels_per_tick`,
    emits `int(acc)`, keeps the remainder;
  - dead zone and pixels-per-tick are palm-relative;
  - max `SCROLL_MAX_TICKS_PER_FRAME` per frame;
  - `SCROLL_EXIT_GRACE` keeps the anchor through short landmark dropouts.
- **Pinch** uses enter/exit hysteresis; click/drag behavior is preserved.
- All timers use `time.perf_counter()`.
- `THUMB_EXTENDED_DISTANCE` / unused thumb threshold removed; thumb state is
  diagnostic only.

#### `hand_tracker.py`

Added `MIDDLE_MCP`, `RING_MCP`, `PINKY_MCP` constants used by the new geometry
code. No detection behavior change.

#### `mouse_controller.py`

- Every PyAutoGUI action goes through a failsafe guard, not just `move`.
- Failsafe messages are throttled to once per second.
- A single `scroll()` call is capped to ±`MAX_SCROLL_PER_CALL` (3) ticks.

#### Tests

Added `tests/test_gestures.py` with 13 synthetic-landmark gesture tests:

- rotation-tolerant finger detection;
- slow scroll accumulates instead of dying in the dead zone;
- relaxed thumb does not block scroll;
- per-frame scroll cap;
- bent-middle right click;
- right-click hold fires once;
- right-click re-arms after release;
- left pinch click and drag still work;
- cursor move still works;
- open palm does not scroll;
- tilted-hand scroll;
- losing the hand releases an active drag.

Added `tests/test_mouse_controller.py` with 4 safety tests:

- scroll amount is capped to ±3;
- failsafe exceptions from click/right-click are swallowed;
- cursor movement is clamped to the screen.

Run them with:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

#### Documentation

- `README.md` configuration table updated to the normalized settings.
- `DEPLOYMENT.md` gained a v1.1 section.
- `legacy/` stores the original code and hashes.
- `legacy/v1.1.diff` is the full unified diff from the legacy snapshot to v1.1.
- `run_legacy.bat` runs the legacy snapshot for side-by-side comparison.

### Verification results

- `python -m unittest discover -s tests -v`: **17 tests, OK**.
- Real MediaPipe sample hand: palm 122 px, fingers `[0, 1, 1, 1, 1]`,
  thumb-index ratio 0.43, thumb-middle ratio 0.82; controller stayed IDLE
  (open palm, correctly not treated as scroll).
- Full `main.py` loop with a fake camera and fake mouse: complete 8-frame
  cycle, HUD/state machine/cleanup all passed.
- Existing `camera_test.py` / `run.bat` behavior unchanged.

### Compatibility / migration notes

- Gestures themselves are unchanged: index move, pinch click/drag,
  thumb-middle right click, index+middle scroll.
- Old config names (`PINCH_THRESHOLD`, `RIGHT_CLICK_THRESHOLD`,
  `SCROLL_SENSITIVITY`, `SCROLL_DEAD_ZONE`, `THUMB_EXTENDED_DISTANCE`) are no
  longer used. Use the new ratios in `config.py`; the old values are preserved
  in `legacy/config.py` for reference.
- Right click now fires once per tap; to tap again, move the thumb away from
  the middle fingertip (beyond `RIGHT_CLICK_EXIT_RATIO`) first.
- Scroll now needs index+middle extended and ring+pinky not both extended;
  a fully open palm will not scroll.

### Rollback

```powershell
Copy-Item legacy\config.py,legacy\gesture_controller.py,legacy\hand_tracker.py,legacy\main.py,legacy\mouse_controller.py,legacy\utils.py . -Force
```

`legacy/SHA256SUMS.txt` can be used to verify the restored files.

### Known limitations / next steps

- Normalized ratios are calibrated from synthetic landmarks and one real
  MediaPipe sample; field-tune `PINCH_ENTER_RATIO` / `RIGHT_CLICK_ENTER_RATIO`
  with your own camera and hand size.
- Finger extension is still 2D; adding MediaPipe `z` would improve extreme
  hand angles.
- No automatic per-user calibration yet.
- The rest of the stability plan (temporal voting for pinch, DPI-aware cursor
  mapping, camera reconnect, multi-monitor) remains open.
