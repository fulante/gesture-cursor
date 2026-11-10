# Legacy snapshot (pre-v1.1)

Snapshot date: 2026-11-09
Reason: preserve the original gesture logic before the v1.1 stability update.

This folder contains the project files as they were before the changes:

- `config.py` — old pixel thresholds (`PINCH_THRESHOLD`, `SCROLL_SENSITIVITY`, ...)
- `gesture_controller.py` — original y-coordinate finger detection, level-triggered right click, anchor-reset scroll
- `hand_tracker.py` — original landmark constants
- `main.py`, `mouse_controller.py`, `utils.py` — original versions
- `README.md`, `DEPLOYMENT.md`, `.gitignore`, `requirements.txt` — original docs/config

`SHA256SUMS.txt` records the SHA-256 of every file in this snapshot.
`v1.1.diff` is a unified diff from this snapshot to the current v1.1.x code,
useful for reviewing exactly what changed.

These files are **reference only**; do not import them into the running app.
`legacy/config.py` has the old pixel-based settings and is not compatible with
the current `gesture_controller.py`.

## Run the original version side-by-side

Double-click `run_legacy.bat` in the project root (or run
`legacy\main.py` with the project venv). It runs the files in this folder
using the legacy pixel thresholds, which is useful for comparing old vs new
right-click/scroll behavior. The new version is still `run.bat`.

## Restore the original version

From the project root:

```powershell
Copy-Item legacy\config.py,legacy\gesture_controller.py,legacy\hand_tracker.py,legacy\main.py,legacy\mouse_controller.py,legacy\utils.py . -Force
```

Then run `run.bat` as before. To switch back to v1.1, restore the current
files from your backup (or re-apply the v1.1 changes described in
`CHANGELOG.md`).

## Why the original was replaced

The original right-click and scroll paths had structural issues, not just
mistuned thresholds:

- right click required the middle finger to be "extended", but a real
  thumb-middle tap curls it;
- pinch/scroll priority could suppress right click;
- right click was level-triggered and repeated while held;
- scroll used a hard dead zone, anchor reset and integer division, so slow
  motion was discarded and fast motion jumped.

See `CHANGELOG.md` for the full analysis and the new behavior.
