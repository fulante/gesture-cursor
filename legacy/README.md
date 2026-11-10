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
  - **Drag & drop** — pinch and **hold** (≥ 0.3 s), release to drop.
  - **Right click** — thumb + middle pinch.
  - **Scroll** — index + middle extended, move vertically.
- Live HUD showing FPS, current state and last action, plus the cursor-active region.
- Click debouncing prevents stuttery double-fires.
- Configurable thresholds, sensitivity and smoothing in a single `config.py`.
- Clean separation: `HandTracker` / `GestureController` / `MouseController`.
- Graceful exit on `q` / `Esc` / window-close / `Ctrl+C`, even mid-drag.

---

## Project Structure

```
gesture_mouse/
├── main.py                # Entry point - capture loop & wiring
├── config.py              # All tunable constants (thresholds, sensitivity, ...)
├── hand_tracker.py        # MediaPipe wrapper - returns 21 pixel landmarks
├── gesture_controller.py  # State machine - landmarks -> mouse actions
├── mouse_controller.py    # PyAutoGUI wrapper
├── utils.py               # FPS counter, HUD drawing, math helpers
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
| `FRAME_REDUCTION` | Pixels of "dead zone" around the camera frame. Larger = more sensitive (small hand movement covers more screen). |
| `SMOOTHING_FACTOR` | `0.0` (frozen) → `1.0` (instant). `0.3 – 0.5` is the sweet spot. |
| `CURSOR_SENSITIVITY` | Multiplier around screen centre. `1.0` = neutral. |
| `PINCH_THRESHOLD` | Pixel distance below which thumb+index counts as a pinch. |
| `RIGHT_CLICK_THRESHOLD` | Pixel distance for the thumb+middle right-click gesture. |
| `DRAG_HOLD_TIME` | Seconds a pinch must be held before becoming a drag. |
| `CLICK_DEBOUNCE` | Minimum interval between clicks (anti-stutter). |
| `SCROLL_SENSITIVITY` | Higher = slower scroll. |
| `CAMERA_WIDTH/HEIGHT` | Lower for more FPS, higher for more precision. |

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
Increase `PINCH_THRESHOLD` (default `40` px) and/or `CLICK_DEBOUNCE`.

**The PyAutoGUI failsafe keeps firing**
The cursor reaching a screen corner aborts actions. Either keep the cursor away from corners, or set `failsafe=False` when constructing `MouseController` in `main.py` (not recommended).

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
