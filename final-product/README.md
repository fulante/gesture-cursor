# Gesture Cursor — Final Product (v1.1.5)

A local, webcam-based virtual mouse built with **MediaPipe**, **OpenCV** and
**PyAutoGUI**. No extra hardware, no cloud upload.

This folder is the clean product snapshot. The full iteration history and
product report live in the sibling `iteration-report/` folder.

## Contents

| File | Purpose |
|---|---|
| `main.py` | Entry point: camera loop, HUD, wiring |
| `config.py` | Camera, cursor, gesture and timing settings |
| `hand_tracker.py` | MediaPipe 21-landmark wrapper |
| `gesture_controller.py` | Gesture state machine |
| `mouse_controller.py` | PyAutoGUI wrapper, failsafe and wheel handling |
| `volume_controller.py` | Windows volume media-key wrapper |
| `utils.py` | FPS counter, HUD drawing, distance helper |
| `camera_test.py` / `camera_test.bat` | Webcam index/backend diagnostic |
| `setup.bat` | Creates `.venv` and installs dependencies |
| `run.bat` | Launches `main.py` with the local `.venv` |
| `requirements.txt` / `constraints.txt` | Dependencies and compatible versions |
| `tests/` | 38 synthetic-landmark, mouse-safety, volume-key and resolution tests |

## Requirements

- Windows (the current implementation is Windows-first).
- Python **3.9–3.12**, Python **3.12** recommended.
- Do **not** use Python 3.13: `mediapipe==0.10.21` has no cp313 wheel.
- A working webcam. On the current machine, the camera may require running the
  app as administrator because of the local device policy.

## Quick start

```bat
setup.bat
```

`setup.bat` creates `.venv` with Python 3.12 and installs the pinned
dependencies. Then double-click `run.bat`, or run:

```bat
.venv\Scripts\python.exe main.py
```

Manual equivalent:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -c constraints.txt
python main.py
```

If the camera cannot be opened, double-click `camera_test.bat`; it tries
`ANY` / `DSHOW` / `MSMF` and indices 0–5, then prints the working
`CAMERA_INDEX` / `CAMERA_BACKEND` values for `config.py`.

## Gestures

| Gesture | Action |
|---|---|
| Index finger only | Move cursor |
| Thumb + index pinch, release | Left click |
| Two stationary pinches, click events within the double-click window | Double click |
| Pinch, hold >0.3 s and move >0.15 palm width | Drag; release to drop |
| Thumb + middle tap | Right click (a resting thumb does not count) |
| Index + middle extended, move hand vertically | Scroll (target window must have focus) |
| Thumb + ring pinch, move hand up/down | Volume up/down |

Double-click is implemented as two normal clicks; Windows recognizes the pair.
The first click is never buffered. A second pinch is ignored for double-click if
it is beyond the system double-click time or the cursor drifts more than
`DOUBLE_CLICK_MAX_MOVE_PX`.

## Tests

Run from this folder:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: **38 tests, OK**.

## Configuration

All settings live in `config.py`. Important groups:

- camera: `CAMERA_INDEX`, `CAMERA_WIDTH/HEIGHT`, `CAMERA_BACKEND`;
  `FRAME_REDUCTION` is scaled from the configured reference to the camera's
  actual first-frame resolution;
- cursor: `FRAME_REDUCTION`, `SMOOTHING_FACTOR`, `CURSOR_SENSITIVITY`,
  `SCREEN_EDGE_MARGIN`;
- gesture: `PINCH_*`, `RIGHT_CLICK_*`, `FINGER_EXTENDED_RATIO_*`;
- scroll: `SCROLL_DEAD_ZONE_RATIO`, `SCROLL_PALM_PER_TICK`,
  `SCROLL_MAX_TICKS_PER_FRAME`;
- volume: `VOLUME_ENTER_RATIO`, `VOLUME_EXIT_RATIO`,
  `VOLUME_DEAD_ZONE_RATIO`, `VOLUME_PALM_PER_STEP`,
  `VOLUME_MAX_STEPS_PER_FRAME`, `VOLUME_CONFIRM_FRAMES`;
- timing: `CLICK_DEBOUNCE`, `DRAG_HOLD_TIME`, `DRAG_START_MOVE_RATIO`,
  `DOUBLE_CLICK_WINDOW`, `DOUBLE_CLICK_MAX_MOVE_PX`,
  `RIGHT_CLICK_SUPPRESS_AFTER_CLICK`.

## Known limitations

- Camera access may require administrator rights on the current machine.
- No DPI-awareness / multi-monitor selection yet.
- End-to-end camera/display latency has not been instrumented.
- If the camera changes resolution mid-session, restart the app; mapping uses
  the first-frame resolution.
- No per-user calibration; tested primarily with one user and one camera.
- Not packaged as an installer; this is a source snapshot.

The detailed remaining backlog and product iteration report are in the sibling
`../iteration-report/` folder (`reference/BACKLOG.md` and
`Iteration-Report.md`).
