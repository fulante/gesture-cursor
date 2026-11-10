# Gesture Mouse Control

A real-time, hand gesture–controlled virtual mouse built with **MediaPipe**, **OpenCV** and **PyAutoGUI**. Move and click your computer's cursor without touching the trackpad — purely from your webcam.

The project is intentionally split into small, single-responsibility modules so each piece (hand detection, gesture interpretation, OS interaction) can be replaced or extended independently.

---

## Features

- 21-landmark single-hand tracking via MediaPipe (≈ 30 FPS on a mid-range laptop).
- Smooth, low-jitter cursor motion (exponential smoothing + active-region remap).
- Full mouse vocabulary:
  - **Move** — index finger only.
  - **Left click** — quick pinch (thumb + index).
  - **Double click** — two stationary pinches whose click events fall inside the double-click window.
  - **Drag & drop** — pinch, hold briefly **and move**; a stationary hold is a click.
  - **Right click** — quick thumb + middle tap (a resting thumb does not count).
  - **Scroll** — index + middle extended, move vertically.
  - **Volume** — thumb + ring pinch, then move the hand up/down.
- Live HUD showing FPS, current state and last action, plus the cursor-active region.
- Click debouncing prevents stuttery double-fires.
- Configurable thresholds, sensitivity and smoothing in a single `config.py`.
- Clean separation: `HandTracker` / `GestureController` / `MouseController`.
- Graceful exit on `q` / `Esc` / window-close / `Ctrl+C`, even mid-drag.
- Scale-normalized gestures (palm-size relative), tolerant to hand distance and camera resolution.
- Edge-triggered right click and accumulator-based scroll (no repeat-fire, no slow-scroll dead zone).
- Right click requires a real tap motion; a thumb resting against the middle finger is ignored.
- Synthetic-landmark regression tests under `tests/`.

> **v1.1.5 stability update:** gesture distances are normalized by palm size,
> finger extension uses joint ratios/angles instead of raw y coordinates,
> right click requires a tap motion and has a bounded latch, scroll uses a
> fractional accumulator with a grace period, drag needs real movement,
> **two stationary pinches act as a double-click**, **thumb + ring pinch with
> vertical movement controls system volume**, and **cursor mapping uses the
> camera's real first-frame resolution**. Cursor mapping keeps an 8 px margin
> from screen corners, and failsafe release never leaves a mouse button held.
> See `CHANGELOG.md` for details; `legacy/` keeps the original pre-update snapshot.

---

## Project Structure

```
gesture_mouse/
├── main.py                # Entry point - capture loop & wiring
├── config.py              # All tunable constants (thresholds, sensitivity, ...)
├── hand_tracker.py        # MediaPipe wrapper - returns 21 pixel landmarks
├── gesture_controller.py  # State machine - landmarks -> mouse actions
├── mouse_controller.py    # PyAutoGUI wrapper
├── volume_controller.py   # Windows volume media-key wrapper
├── utils.py               # FPS counter, HUD drawing, math helpers
├── tests/                 # Synthetic-landmark regression tests
├── constraints.txt        # Reproducible dependency pins
├── CHANGELOG.md           # v1.1.x changes, tests and rollback notes
├── ITERATIONS.md          # Product-facing iteration log and talking points
├── BACKLOG.md             # Prioritized remaining product/engineering issues
├── final-product/         # Clean, runnable product source snapshot
├── iteration-report/      # Integrated product iteration report
├── legacy/                # Original pre-v1.1 source snapshot
├── run_legacy.bat         # Runs the legacy snapshot for comparison
├── requirements.txt
└── README.md              # (you are here)
```

---

## Installation

### 1. Python version

**Python 3.12 is required** (3.9–3.12 work; 3.13 does not).

This pins the project to mediapipe 0.10.21, which is the last release that
combines a working `mp.solutions.hands` API with stable Windows wheels. Newer
mediapipe versions either removed `mp.solutions` (0.10.22+) or have a broken
Windows ctypes binding (0.10.30+).

If your system Python is 3.13 (or anything else), install 3.12 alongside it
(they coexist fine on Windows, macOS, and Linux):

* **Windows:** `winget install Python.Python.3.12` (or [python.org](https://www.python.org/downloads/release/python-3128/))
* **macOS (Homebrew):** `brew install python@3.12`
* **Ubuntu/Debian:** `sudo apt install python3.12 python3.12-venv`

### 2. Create a virtual environment (required, not just recommended)

The pin to mediapipe 0.10.21 + numpy < 2 will fight any other ML projects in your global Python, so always use a dedicated venv for this project.

```bash
# Windows
py -3.12 -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Apple Silicon (M1/M2/M3) note:** if `mediapipe` fails to install, try
> `pip install mediapipe-silicon` instead, or use Python 3.10/3.11.

### 4. Run

```bash
python main.py
```

A window titled **Gesture Mouse Control** should appear with your webcam feed. Move your hand into view and you're controlling the cursor.

Press **`q`** (or `Esc`) in the preview window to exit.

---

## Gesture Reference

| Gesture | Action | How |
|---|---|---|
| ☝️ Index up only | **Move cursor** | Only the index finger extended. |
| 🤏 Quick pinch | **Left click** | Touch thumb tip to index tip and release within ~0.3 s. |
| 🤏 Hold pinch | **Drag** | Pinch and keep it pinched while you move; release to drop. |
| ✌️ Thumb + middle pinch | **Right click** | Tap your middle fingertip with your thumb. |
| 🖖 Index + middle | **Scroll** | Both fingers extended; move hand up to scroll up, down to scroll down. |

The currently-detected gesture is shown in the on-screen HUD.

---

## Configuration

All tunables live in `config.py`. The most useful knobs:

| Setting | What it does |
|---|---|
| `FRAME_REDUCTION` | Dead zone around the camera frame, calibrated at the configured resolution; scaled to the camera's actual first-frame resolution. |
| `SMOOTHING_FACTOR` | `0.0` (frozen) → `1.0` (instant). `0.3 – 0.5` is the sweet spot. |
| `CURSOR_SENSITIVITY` | Multiplier around screen centre. `1.0` = neutral. |
| `SCREEN_EDGE_MARGIN` | Pixels kept between the cursor and physical screen corners (avoids failsafe freezes). |
| `PINCH_ENTER_RATIO` / `PINCH_EXIT_RATIO` | Thumb-index distance, in palm widths, for starting/releasing a left pinch. |
| `RIGHT_CLICK_ENTER_RATIO` / `RIGHT_CLICK_EXIT_RATIO` | Thumb-middle distance for right-click and its release/re-arm threshold. |
| `RIGHT_CLICK_DOMINANCE` | How much closer the thumb must be to the middle than to the index for a right click. |
| `RIGHT_CLICK_TAP_DELTA` / `RIGHT_CLICK_TAP_WINDOW` | How far the thumb must have moved toward the middle, and within how many seconds, for a real right-click tap. |
| `RIGHT_CLICK_LATCH_TIMEOUT` | Maximum time a right-click latch may block cursor/other gestures. |
| `FINGER_EXTENDED_RATIO_ENTER` / `_EXIT` | Tip-to-MCP / PIP-to-MCP ratio used to decide whether a finger is extended. |
| `SCROLL_DEAD_ZONE_RATIO` | Vertical dead zone before scrolling, in palm widths. |
| `SCROLL_PALM_PER_TICK` | Palm widths of hand movement per wheel tick; smaller = faster scroll. |
| `VOLUME_ENTER_RATIO` / `VOLUME_EXIT_RATIO` | Thumb-ring distance for entering/leaving volume mode. |
| `VOLUME_DEAD_ZONE_RATIO` / `VOLUME_PALM_PER_STEP` | Vertical dead zone and hand movement per volume step. |
| `VOLUME_MAX_STEPS_PER_FRAME` | Maximum volume key presses sent in one frame. |
| `DRAG_HOLD_TIME` | Minimum hold time before a moving pinch can become a drag. |
| `DRAG_START_MOVE_RATIO` | Movement required (palm widths) before that pinch becomes a drag. |
| `DOUBLE_CLICK_WINDOW` | Maximum time between two stationary pinches to count as a double-click (Windows' own double-click time may be stricter). |
| `DOUBLE_CLICK_MAX_MOVE_PX` | Maximum cursor drift between the two clicks; larger drift becomes two singles. |
| `RIGHT_CLICK_SUPPRESS_AFTER_CLICK` | Time after a left click during which right-click candidates are ignored. |
| `CLICK_DEBOUNCE` | Minimum interval between clicks (anti-stutter). |
| `GESTURE_CONFIRM_FRAMES` | Consecutive frames required before right-click/scroll starts. |
| `SCROLL_EXIT_GRACE` | Seconds to keep scroll state through a brief landmark dropout. |
| `CAMERA_WIDTH/HEIGHT` | Lower for more FPS, higher for more precision. |

All gesture ratios are relative to palm size, so they do not need retuning when
the camera resolution or the distance between your hand and the camera changes.

No restart-tooling is needed — just edit and re-run.

---

## Performance Tips

- Drop `MODEL_COMPLEXITY` to `0` in `config.py` for ~30% faster inference on weak hardware.
- Reduce `CAMERA_WIDTH` / `CAMERA_HEIGHT` (e.g. 480×360) on slow CPUs.
- Close other webcam-using applications (browsers, video calls) — they often hold the device in low-FPS modes.
- The active-area rectangle (the magenta box) shows where your fingertip needs to be for cursor mapping; if you're constantly hitting the edges, increase `FRAME_REDUCTION`.

---

## Troubleshooting

**`AttributeError: module 'mediapipe' has no attribute 'solutions'`**
You're on **mediapipe ≥ 0.10.22**, which dropped the legacy `mp.solutions` API. Re-create the venv on Python 3.12 and `pip install -r requirements.txt` — the pin guarantees 0.10.21.

**`AttributeError: function 'free' not found` (Windows)**
You're on **mediapipe ≥ 0.10.30**, which has a [broken Windows ctypes binding](https://github.com/google-ai-edge/mediapipe/issues/6187). Same fix — Python 3.12 venv with the pinned `requirements.txt`.

**`ERROR: Could not find a version that satisfies the requirement mediapipe==0.10.21`**
Your active Python is 3.13 (or older than 3.9). mediapipe 0.10.21 only ships wheels for cp39 – cp312. Activate a Python 3.12 venv and try again — see "Installation" above.

**"Could not open camera at index 0"**
Another app is using the webcam, or your default camera lives at a different index. Try `CAMERA_INDEX = 1` (or 2) in `config.py`.

**Cursor doesn't move on macOS**
Grant the terminal/IDE running this script *Accessibility* and *Screen Recording* permissions:
*System Settings → Privacy & Security → Accessibility / Screen Recording.*

**Cursor doesn't move on Linux**
PyAutoGUI uses `xdotool` under the hood. Install it with your package manager:
`sudo apt install scrot python3-tk python3-dev` and ensure you're on X11 (Wayland support is limited).

**Cursor jumps or jitters**
Lower `SMOOTHING_FACTOR` (e.g. `0.3`) and ensure even lighting on your hand — MediaPipe loses precision in low light.

**Clicks fire when I don't want them**
Decrease `PINCH_ENTER_RATIO` (e.g. `0.26`) so the thumb must come closer to the
index, and/or increase `CLICK_DEBOUNCE`. If right clicks fire too easily,
decrease `RIGHT_CLICK_ENTER_RATIO` or `RIGHT_CLICK_DOMINANCE`, or increase
`RIGHT_CLICK_TAP_DELTA`.

**Right click fires while I am just moving the cursor**
This is the "thumb resting on the middle finger" case. v1.1.1 requires a real
tap motion before firing. If it still happens, increase
`RIGHT_CLICK_TAP_DELTA` (e.g. `0.16`) or decrease
`RIGHT_CLICK_ENTER_RATIO`.

**The HUD says SCROLL but the page does not move**
Click the page/document first so it owns the focus, and keep the cursor over
the scrollable area while moving the hand. Wheel events go to the focused
window, not to the OpenCV preview. v1.1.1 also fixes the Windows wheel unit
(`WHEEL_DELTA = 120`), which previously made `scroll(1)` almost invisible.

**Volume gesture does not change the volume**
Separate thumb and ring first, then pinch them; the HUD should show `VOLUME`.
The ring fingertip must be the closest one to the thumb (closer than index and
middle), otherwise the gesture is treated as click/right/scroll. Move the hand
up for louder, down for quieter. If it is hard to reach, raise
`VOLUME_ENTER_RATIO` (e.g. `0.34`) or use the Windows volume keys once to check
that media keys are not blocked.

**The cursor freezes in one area for a while**
Check the HUD `State` first. v1.1.2 bounds the right-click latch to
`RIGHT_CLICK_LATCH_TIMEOUT` and keeps the cursor `SCREEN_EDGE_MARGIN` pixels
away from screen corners, so a held thumb or a corner failsafe no longer parks
the cursor indefinitely. v1.1.5 also shows `Out of Area` instead of snapping to
an edge when the hand leaves the active region. If `State` is `PINCH` or
`SCROLL`, the state machine is still holding a gesture; release the pinch /
drop the two-finger pose.

**The cursor is offset from my hand / buttons stay held after a corner abort**
v1.1.5 reads the camera's actual first-frame resolution and uses it for cursor
mapping; the startup banner prints the actual size next to the requested size.
If the camera changes resolution mid-session, restart. A real PyAutoGUI
failsafe now releases all drag buttons before exiting.

**Left click sometimes does nothing on a close button**
A stationary pinch held longer than `DRAG_HOLD_TIME` is now a click on release;
drag requires actual movement. If clicks still turn into drags, increase
`DRAG_START_MOVE_RATIO` (e.g. `0.20`). If clicks are suppressed, wait for
`CLICK_DEBOUNCE` between clicks.

**Double click only selects, does not open**
The two clicks must fall inside Windows' double-click time, and the cursor must
stay within `DOUBLE_CLICK_MAX_MOVE_PX` (16 px). Keep the hand still between the
two pinches, and make sure the thumb-index distance exceeds `PINCH_EXIT_RATIO`
between them (otherwise the second pinch is not a new click). The app uses the
stricter of `DOUBLE_CLICK_WINDOW` and `GetDoubleClickTime()`. To allow a longer
interval, slow Windows' double-click speed in Mouse settings **and** raise
`DOUBLE_CLICK_WINDOW` to match; raising only one of them is not enough. If the
second click is too slow or the cursor drifted too far, it behaves as two
separate single clicks.

**The PyAutoGUI failsafe keeps firing**
The cursor reaching a screen corner aborts actions. Either keep the cursor away from corners, or set `failsafe=False` when constructing `MouseController` in `main.py` (not recommended).

---

## Documentation

- [ITERATIONS.md](ITERATIONS.md) — iteration history, current metrics and
  product-introduction talking points.
- [iteration-report/Iteration-Report.md](iteration-report/Iteration-Report.md) —
  integrated product iteration report (why, UX, root causes, fixes).
- [final-product/README.md](final-product/README.md) — clean final product
  source snapshot (v1.1.5).
- [BACKLOG.md](BACKLOG.md) — prioritized remaining product/engineering issues.
- [CHANGELOG.md](CHANGELOG.md) — detailed version changes, root causes and tests.
- [DEPLOYMENT.md](DEPLOYMENT.md) — environment, camera setup and tuning guide.
- [legacy/SNAPSHOT.md](legacy/SNAPSHOT.md) — original source snapshot and rollback.
- [docs/系统工程师交付说明.md](docs/系统工程师交付说明.md) — engineering delivery:
  environment, CI, release/rollback and acceptance checklist (Chinese).

---

## Extending the System

The `GestureController` is a small finite-state machine. To add a new gesture:

1. Add any new threshold to `config.py`.
2. In `gesture_controller.py`, classify it alongside the other "intent" booleans (`is_pinch`, `is_scroll`, …) at the top of `update()`.
3. Insert the corresponding state-transition block — keep it ordered so high-priority gestures (pinch/drag) are checked before lower-priority ones (cursor move).
4. Call the desired action on `self.mouse` (extend `MouseController` if you need a new primitive — e.g. `pyautogui.hotkey('ctrl', 'c')`).

Ideas you could plug in:
- **Volume control** — pinch-then-rotate gesture.
- **Workspace switch** — three-finger swipe.
- **Multi-hand support** — bump `MAX_NUM_HANDS` to 2 in `config.py` and extend `HandTracker.process` to return a list.
- **Dynamic calibration** — record a few seconds of "neutral" hand poses and auto-tune thresholds.

---

## License

Provided as-is for educational and personal use.
