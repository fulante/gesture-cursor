"""
config.py
---------
Central configuration for the gesture-controlled virtual mouse.

Tweak the values below to tune sensitivity, smoothing, gesture thresholds,
camera settings and UI behaviour without touching the rest of the code.
"""

# ---------------------------------------------------------------------------
# Camera Settings
# ---------------------------------------------------------------------------
CAMERA_INDEX = 0          # 0 = default webcam, 1+ = additional cameras
CAMERA_WIDTH = 640        # Lower = faster processing, higher = more precision
CAMERA_HEIGHT = 480
CAMERA_FPS = 30           # Requested FPS from the camera driver

# OpenCV video backend. "ANY" lets OpenCV choose; if the camera cannot be
# opened, run camera_test.bat and copy the backend it reports.
CAMERA_BACKEND = "ANY"    # "ANY", "DSHOW" or "MSMF"

# Dead-zone size around the camera frame. This value is calibrated at
# CAMERA_WIDTH x CAMERA_HEIGHT; main.py reads the actual first frame and the
# controller scales it to that real resolution.
# A larger reduction means a smaller hand-movement area maps to the full
# screen, increasing effective sensitivity.
FRAME_REDUCTION = 100

# ---------------------------------------------------------------------------
# MediaPipe Hand Detection
# ---------------------------------------------------------------------------
MAX_NUM_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5
MODEL_COMPLEXITY = 1      # 0 = fastest, 1 = balanced

# ---------------------------------------------------------------------------
# Cursor Control
# ---------------------------------------------------------------------------
# Smoothing factor for cursor movement (exponential smoothing).
#   1.0 -> no smoothing (instant, jittery)
#   0.0 -> infinite smoothing (frozen)
# 0.3 - 0.6 is usually the sweet spot.
SMOOTHING_FACTOR = 0.4

# Sensitivity multiplier applied around the screen centre. Use values > 1
# to amplify hand motion, < 1 to dampen it.
CURSOR_SENSITIVITY = 1.0

# Keep the mapped cursor this many pixels away from the physical screen
# corners. PyAutoGUI's failsafe aborts when the cursor reaches a corner, and
# swallowing that exception while the cursor is still parked there can feel
# like the cursor is frozen.
SCREEN_EDGE_MARGIN = 8

# ---------------------------------------------------------------------------
# Gesture Thresholds (normalized by palm size, not pixels)
# ---------------------------------------------------------------------------
# Palm size = distance(wrist, middle MCP). Every distance below is divided
# by it, so the thresholds stay valid as the hand moves closer/farther away
# and when the camera resolution changes.
PINCH_ENTER_RATIO = 0.30        # thumb-index below this -> pinch starts
PINCH_EXIT_RATIO = 0.40         # thumb-index above this -> pinch releases

RIGHT_CLICK_ENTER_RATIO = 0.32  # thumb-middle below this -> right-click
RIGHT_CLICK_EXIT_RATIO = 0.44   # must exceed this before re-arming
RIGHT_CLICK_DOMINANCE = 0.78    # thumb-middle must be < this * thumb-index

# A right click is a TAP, not a static contact. Require thumb-middle to have
# been at least TAP_DELTA palm-widths farther away within TAP_WINDOW seconds.
# This prevents a thumb that naturally rests against the middle finger from
# firing right clicks while the cursor is moving.
RIGHT_CLICK_TAP_DELTA = 0.12
RIGHT_CLICK_TAP_WINDOW = 0.30

# Finger extension uses tip-to-MCP / PIP-to-MCP distance plus the angle at
# the PIP joint, instead of comparing raw y coordinates.
FINGER_EXTENDED_RATIO_ENTER = 1.22
FINGER_EXTENDED_RATIO_EXIT = 1.08

# Scroll is driven by moving the whole hand while index + middle are
# extended. Dead zone and wheel-tick distance are in palm widths.
SCROLL_DEAD_ZONE_RATIO = 0.02
SCROLL_PALM_PER_TICK = 0.15
SCROLL_MAX_TICKS_PER_FRAME = 3

# Volume: pinch thumb + ring finger, then move the hand vertically.
# Ring is otherwise unused, so this does not collide with click/right/scroll.
VOLUME_ENTER_RATIO = 0.30
VOLUME_EXIT_RATIO = 0.40
VOLUME_DEAD_ZONE_RATIO = 0.03
VOLUME_PALM_PER_STEP = 0.18
VOLUME_MAX_STEPS_PER_FRAME = 2
VOLUME_CONFIRM_FRAMES = 2

# ---------------------------------------------------------------------------
# Debounce / Timing (seconds)
# ---------------------------------------------------------------------------
CLICK_DEBOUNCE = 0.10           # Min interval between separate single clicks
RIGHT_CLICK_DEBOUNCE = 0.45     # Min interval between right-clicks
DRAG_HOLD_TIME = 0.30           # Min hold before a moving pinch becomes drag
DRAG_START_MOVE_RATIO = 0.15    # ... and it must move this much (palm widths)

# Two complete, stationary pinch cycles within this window are two clicks; the
# OS recognizes them as a double-click. Windows' own double-click time is used
# when it is stricter. The first click is never buffered.
DOUBLE_CLICK_WINDOW = 0.50
DOUBLE_CLICK_MAX_MOVE_PX = 16   # snap back to first click within this distance

# A left click temporarily suppresses right-click candidates. This prevents a
# thumb returning to the middle finger from stealing the second click.
RIGHT_CLICK_SUPPRESS_AFTER_CLICK = 0.30

# Once a right click fires, the latch blocks other actions only for this long.
# Without a timeout, a thumb that stays near the middle finger can keep the
# cursor frozen indefinitely.
RIGHT_CLICK_LATCH_TIMEOUT = 0.80

# Consecutive frames required before a right-click/scroll gesture starts.
GESTURE_CONFIRM_FRAMES = 2
# Keep scrolling through a brief landmark dropout instead of resetting.
SCROLL_EXIT_GRACE = 0.18

# ---------------------------------------------------------------------------
# UI Settings
# ---------------------------------------------------------------------------
SHOW_FPS = True
SHOW_LANDMARKS = True
SHOW_ACTIVE_AREA = True
SHOW_GESTURE_TEXT = True
WINDOW_NAME = "Gesture Mouse Control"
EXIT_KEY = "q"
