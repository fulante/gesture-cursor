"""
gesture_controller.py
---------------------
The "brain" of the system: takes raw hand landmarks each frame, decides
which gesture is currently active, and drives the MouseController
accordingly.

Designed as a finite state machine so behaviours like
    pinch-and-hold -> drag    vs    quick-pinch -> click
work without juggling flags scattered through the code.

State diagram
=============

        +----------+   index up only        +----------+
        |   IDLE   |----------------------> |  CURSOR  |
        +----------+ <--------------------- +----------+
             | ^                                  |
             | | release                          |  pinch
             | +----------------------------------+
             v
       +-----------+   held > DRAG_HOLD_TIME   +-----------+
       | PINCH_DWN |--------------------------> | DRAGGING |
       +-----------+                            +-----------+
            | release (quick)                       |
            v                                       | release
        emits CLICK                                 v
                                                emits DROP

        +-----------+
        | SCROLLING |  (index + middle up; vertical motion drives scroll)
        +-----------+

Stability update (v1.1)
=======================
Gesture geometry is normalized by palm size instead of raw pixels, finger
extension uses joint ratios/angles instead of y coordinates, right click is
edge-triggered, and scroll uses a fractional accumulator with hysteresis.
"""

import ctypes
import math
import sys
import time
from collections import deque

import numpy as np

import config
from hand_tracker import HandTracker
from utils import euclidean


class GestureController:
    """Translate hand landmarks into mouse actions through a small state machine."""

    # Public state constants (also used for the on-screen badge).
    STATE_IDLE = "IDLE"
    STATE_CURSOR = "CURSOR"
    STATE_PINCH_DOWN = "PINCH"
    STATE_DRAGGING = "DRAG"
    STATE_SCROLLING = "SCROLL"
    STATE_VOLUME = "VOLUME"

    def __init__(self, mouse, cam_w, cam_h, volume=None):
        self.mouse = mouse
        self.volume = volume
        self.cam_w = cam_w
        self.cam_h = cam_h
        self.screen_w = mouse.screen_w
        self.screen_h = mouse.screen_h

        # FRAME_REDUCTION is expressed at the configured reference resolution
        # (CAMERA_WIDTH x CAMERA_HEIGHT). Scale it to the actual first-frame
        # resolution so a camera that ignores the requested size does not
        # shift or compress the cursor mapping.
        ref_w = max(1, int(getattr(config, "CAMERA_WIDTH", cam_w)))
        ref_h = max(1, int(getattr(config, "CAMERA_HEIGHT", cam_h)))
        self._fr_x = max(1, int(round(config.FRAME_REDUCTION * cam_w / ref_w)))
        self._fr_y = max(1, int(round(config.FRAME_REDUCTION * cam_h / ref_h)))
        self._fr_x = min(self._fr_x, max(1, cam_w // 2 - 1))
        self._fr_y = min(self._fr_y, max(1, cam_h // 2 - 1))

        # Gesture state machine
        self.state = self.STATE_IDLE
        self._pinch_start_time = None
        self._pinch_start_mid = None
        self._pinch_active = False
        self._last_click_time = -1e9
        self._last_click_pos = None
        self._double_click_window = self._detect_double_click_window()
        self._last_right_click_time = -1e9
        self._right_frames = 0
        self._right_latched = False
        self._right_latch_time = 0.0
        self._right_history = deque(maxlen=60)
        self._scroll_anchor_y = None
        self._scroll_accum = 0.0
        self._scroll_last_seen = 0.0
        self._scroll_frames = 0
        self._volume_active = False
        self._volume_armed = False
        self._volume_frames = 0
        self._volume_anchor_y = None
        self._volume_accum = 0.0
        self._finger_state = [False] * 5

        # Smoothing state (None -> not yet initialised)
        self._smooth_x = None
        self._smooth_y = None

        # Diagnostics for the HUD
        self.last_action = "Idle"

    # =====================================================================
    #                       Finger / gesture detection
    # =====================================================================
    @staticmethod
    def _palm_size(landmarks):
        """Return a scale reference in pixels (wrist -> middle MCP)."""
        palm = euclidean(landmarks[HandTracker.WRIST],
                         landmarks[HandTracker.MIDDLE_MCP])
        if palm < 1.0:
            palm = euclidean(landmarks[HandTracker.WRIST],
                             landmarks[HandTracker.INDEX_MCP])
        return max(palm, 1.0)

    @staticmethod
    def _detect_double_click_window():
        """Use the OS double-click time when it is stricter than the config."""
        if sys.platform == "win32":
            try:
                ms = ctypes.windll.user32.GetDoubleClickTime()
                if 100 <= ms <= 1000:
                    return min(config.DOUBLE_CLICK_WINDOW, ms / 1000.0)
            except Exception:
                pass
        return config.DOUBLE_CLICK_WINDOW

    @staticmethod
    def _hysteresis(previous, value, enter, exit_):
        """Simple two-threshold latch to stop state flicker."""
        return value > exit_ if previous else value > enter

    def _update_fingers(self, landmarks, palm):
        """Return [thumb, index, middle, ring, pinky] booleans.

        A finger is extended when:
            * tip-to-MCP distance / PIP-to-MCP distance is large enough, and
            * the PIP joint is not sharply bent (cosine of the joint angle).

        This is rotation-tolerant; the old implementation compared raw y
        coordinates, which failed whenever the hand was tilted.
        """
        previous = self._finger_state
        states = [False] * 5

        # Thumb is only used diagnostically, but keep a stable state for the
        # HUD/tests. Distance is measured against the index MCP.
        thumb_ratio = euclidean(landmarks[HandTracker.THUMB_TIP],
                                landmarks[HandTracker.INDEX_MCP]) / palm
        states[0] = self._hysteresis(previous[0], thumb_ratio, 0.90, 0.70)

        specs = (
            (HandTracker.INDEX_TIP, HandTracker.INDEX_PIP, HandTracker.INDEX_MCP),
            (HandTracker.MIDDLE_TIP, HandTracker.MIDDLE_PIP, HandTracker.MIDDLE_MCP),
            (HandTracker.RING_TIP, HandTracker.RING_PIP, HandTracker.RING_MCP),
            (HandTracker.PINKY_TIP, HandTracker.PINKY_PIP, HandTracker.PINKY_MCP),
        )
        for i, (tip_i, pip_i, mcp_i) in enumerate(specs, start=1):
            tip = landmarks[tip_i]
            pip = landmarks[pip_i]
            mcp = landmarks[mcp_i]

            d_pip = euclidean(pip, mcp)
            d_tip = euclidean(tip, mcp)
            ratio = d_tip / max(d_pip, 1e-6)

            v1 = (pip[0] - mcp[0], pip[1] - mcp[1])
            v2 = (tip[0] - pip[0], tip[1] - pip[1])
            denom = math.hypot(v1[0], v1[1]) * math.hypot(v2[0], v2[1])
            cos_angle = ((v1[0] * v2[0] + v1[1] * v2[1]) / denom
                         if denom > 1e-6 else 0.0)

            if previous[i]:
                states[i] = (ratio > config.FINGER_EXTENDED_RATIO_EXIT
                             and cos_angle > -0.15)
            else:
                states[i] = (ratio > config.FINGER_EXTENDED_RATIO_ENTER
                             and cos_angle > 0.15)

        self._finger_state = states
        return states

    def _fingers_up(self, landmarks):
        """Debug/test helper: return finger states as 0/1 integers."""
        palm = self._palm_size(landmarks)
        return [int(v) for v in self._update_fingers(landmarks, palm)]

    @staticmethod
    def _palm_center_y(landmarks):
        """Average y of wrist + MCP joints; stable against finger waggle."""
        ys = [landmarks[i][1] for i in (HandTracker.WRIST,
                                        HandTracker.INDEX_MCP,
                                        HandTracker.MIDDLE_MCP,
                                        HandTracker.RING_MCP,
                                        HandTracker.PINKY_MCP)]
        return sum(ys) / len(ys)

    # =====================================================================
    #                          Coordinate mapping
    # =====================================================================
    def _map_to_screen(self, x, y):
        """Map a pixel inside the active camera region to absolute screen coords.

        The cursor sensitivity multiplier scales movement around the screen
        centre so users can keep the same active region and still adjust feel.
        """
        fr_x = self._fr_x
        fr_y = self._fr_y
        margin = max(0, int(getattr(config, "SCREEN_EDGE_MARGIN", 0)))
        max_x = max(margin, self.screen_w - 1 - margin)
        max_y = max(margin, self.screen_h - 1 - margin)
        sx = np.interp(x, (fr_x, self.cam_w - fr_x), (margin, max_x))
        sy = np.interp(y, (fr_y, self.cam_h - fr_y), (margin, max_y))

        # Sensitivity scaling around centre
        if config.CURSOR_SENSITIVITY != 1.0:
            cx, cy = self.screen_w / 2, self.screen_h / 2
            sx = (sx - cx) * config.CURSOR_SENSITIVITY + cx
            sy = (sy - cy) * config.CURSOR_SENSITIVITY + cy

        # Clamp, keeping clear of the physical corners (PyAutoGUI failsafe).
        sx = max(margin, min(max_x, sx))
        sy = max(margin, min(max_y, sy))
        return sx, sy

    def active_area(self):
        """Return the camera-space cursor-active rectangle."""
        return (self._fr_x, self._fr_y,
                self.cam_w - self._fr_x, self.cam_h - self._fr_y)

    def _in_active_area(self, point):
        return (self._fr_x <= point[0] <= self.cam_w - self._fr_x
                and self._fr_y <= point[1] <= self.cam_h - self._fr_y)

    def _smooth(self, x, y):
        """Exponential smoothing for buttery cursor motion."""
        a = config.SMOOTHING_FACTOR
        if self._smooth_x is None:
            # First sample - seed the filter
            self._smooth_x, self._smooth_y = x, y
        else:
            self._smooth_x += (x - self._smooth_x) * a
            self._smooth_y += (y - self._smooth_y) * a
        return self._smooth_x, self._smooth_y

    def _reset_smooth(self):
        """Clear smoothing memory (used when the hand re-appears)."""
        self._smooth_x = None
        self._smooth_y = None

    # =====================================================================
    #                          Volume gesture
    # =====================================================================
    def _update_volume(self, landmarks, palm, d_tr, now):
        """Adjust system volume while thumb+ring stay pinched."""
        if d_tr > config.VOLUME_EXIT_RATIO:
            self._volume_active = False
            self._volume_armed = True
            self._volume_anchor_y = None
            self._volume_accum = 0.0
            self.state = self.STATE_IDLE
            self.last_action = "Volume Stop"
            return

        cursor_y = self._palm_center_y(landmarks)
        if self._volume_anchor_y is None:
            self._volume_anchor_y = cursor_y
            self.last_action = "Volume Ready"
            return

        delta = cursor_y - self._volume_anchor_y
        dead_zone = palm * config.VOLUME_DEAD_ZONE_RATIO
        if abs(delta) > dead_zone:
            pixels_per_step = max(4.0, palm * config.VOLUME_PALM_PER_STEP)
            self._volume_accum += -delta / pixels_per_step

            steps = int(self._volume_accum)
            max_steps = config.VOLUME_MAX_STEPS_PER_FRAME
            steps = max(-max_steps, min(max_steps, steps))
            self._volume_accum -= steps
            self._volume_accum = max(-max_steps,
                                     min(max_steps, self._volume_accum))
            self._volume_anchor_y = cursor_y

            if steps:
                for _ in range(abs(steps)):
                    if steps > 0:
                        self.volume.up()
                    else:
                        self.volume.down()
                self.last_action = ("Volume Up" if steps > 0
                                    else "Volume Down")
            else:
                self.last_action = "Volume Ready"
        else:
            self.last_action = "Volume Ready"

    # =====================================================================
    #                          Pinch release
    # =====================================================================
    def _release_pinch(self, now):
        """Finish a left pinch: emit a click or drop a drag, then reset."""
        if self.state == self.STATE_DRAGGING:
            self.mouse.mouse_up()
            self.last_action = "Drop"
        elif self.state == self.STATE_PINCH_DOWN:
            # A stationary hold is a click, even if it lasted longer than
            # DRAG_HOLD_TIME. Drag requires movement (checked in update), so a
            # slow click on a close button must not silently become a drag.
            pos = self.mouse.position() if hasattr(self.mouse, "position") else None
            since_last = now - self._last_click_time

            is_double = (
                pos is not None
                and self._last_click_pos is not None
                and since_last <= self._double_click_window
                and euclidean(pos, self._last_click_pos)
                <= config.DOUBLE_CLICK_MAX_MOVE_PX
            )

            if is_double:
                # The first click is already delivered. Snap the cursor back
                # to the first click point (if it drifted a few pixels) and
                # deliver the second click; Windows recognizes the pair as a
                # double-click. Do not call pyautogui.doubleClick(), which
                # would add two more clicks.
                if pos != self._last_click_pos:
                    self.mouse.move(self._last_click_pos[0],
                                    self._last_click_pos[1])
                self.mouse.click()
                self._last_click_time = now
                self._last_click_pos = None
                self.last_action = "Double Click"
            elif since_last > config.CLICK_DEBOUNCE:
                self.mouse.click()
                self._last_click_time = now
                self._last_click_pos = pos
                self.last_action = "Click"
            else:
                self.last_action = "Click Suppressed"

        self.state = self.STATE_IDLE
        self._pinch_start_time = None
        self._pinch_start_mid = None
        self._pinch_active = False

    # =====================================================================
    #                              Main update
    # =====================================================================
    def update(self, landmarks):
        """Drive the state machine for one frame's worth of landmarks."""
        # ----- No hand: clean up any active state ---------------------------
        if landmarks is None:
            if self.state == self.STATE_DRAGGING:
                self.mouse.mouse_up()
            self.state = self.STATE_IDLE
            self._scroll_anchor_y = None
            self._scroll_accum = 0.0
            self._scroll_frames = 0
            self._pinch_start_time = None
            self._pinch_start_mid = None
            self._pinch_active = False
            self._last_click_time = -1e9
            self._last_click_pos = None
            self._right_latched = False
            self._right_frames = 0
            self._right_latch_time = 0.0
            self._right_history.clear()
            self._volume_active = False
            self._volume_armed = False
            self._volume_frames = 0
            self._volume_anchor_y = None
            self._volume_accum = 0.0
            self._finger_state = [False] * 5
            self._reset_smooth()
            self.last_action = "No Hand"
            return

        palm = self._palm_size(landmarks)
        fingers = self._update_fingers(landmarks, palm)
        thumb_tip = landmarks[HandTracker.THUMB_TIP]
        index_tip = landmarks[HandTracker.INDEX_TIP]
        middle_tip = landmarks[HandTracker.MIDDLE_TIP]
        now = time.perf_counter()

        # Normalized pinch distances. These are the core scale-free signals.
        d_ti = euclidean(thumb_tip, index_tip) / palm
        d_tm = euclidean(thumb_tip, middle_tip) / palm
        d_tr = euclidean(thumb_tip, landmarks[HandTracker.RING_TIP]) / palm

        # Volume has priority over other gestures only when the ring fingertip
        # is the closest one to the thumb. A fist where the thumb merely rests
        # near the ring must not start volume mode: the user first has to
        # separate the thumb (arm) and then pinch ring+thumb.
        if self._volume_active:
            self._update_volume(landmarks, palm, d_tr, now)
            return

        if (self.volume is not None
                and d_tr > config.VOLUME_EXIT_RATIO):
            self._volume_armed = True

        # Volume is checked before right click: when the ring fingertip is the
        # closest one to the thumb, the user is deliberately doing the volume
        # gesture even if the thumb also passes near the middle finger.
        volume_candidate = (
            self.volume is not None
            and not self._pinch_active
            and not self._right_latched
            and self._volume_armed
            and d_tr < config.VOLUME_ENTER_RATIO
            and d_tr < d_ti
            and d_tr < d_tm
        )
        if volume_candidate:
            self._volume_frames += 1
            if self._volume_frames >= config.VOLUME_CONFIRM_FRAMES:
                self._volume_active = True
                self._volume_armed = False
                self._volume_anchor_y = self._palm_center_y(landmarks)
                self._volume_accum = 0.0
                self.state = self.STATE_VOLUME
                self.last_action = "Volume Ready"
            else:
                self.state = self.STATE_IDLE
                self.last_action = "Volume Ready"
            return
        self._volume_frames = 0

        # ------------------------------------------------------------------
        # RIGHT CLICK
        # ------------------------------------------------------------------
        # A right click is a TAP: the thumb must have been clearly farther from
        # the middle fingertip recently, then close the gap. A thumb that is
        # simply resting against the middle finger (common while moving the
        # cursor with the index finger) has no such recent drop and must not
        # fire. This is what prevents the "resting thumb" false positives.
        self._right_history.append((now, d_tm))
        while (self._right_history
               and now - self._right_history[0][0]
               > config.RIGHT_CLICK_TAP_WINDOW):
            self._right_history.popleft()
        recent_max = max((value for _, value in self._right_history),
                         default=d_tm)
        right_tap = (recent_max - d_tm) >= config.RIGHT_CLICK_TAP_DELTA

        # Priority note: right click is checked before pinch and scroll.
        # The middle finger is allowed to be bent here - a real tap with the
        # middle fingertip naturally curls it, which the old code rejected.
        right_dominant = d_tm < d_ti * config.RIGHT_CLICK_DOMINANCE
        right_close = d_tm < config.RIGHT_CLICK_ENTER_RATIO
        left_click_recently = (
            now - self._last_click_time
            < config.RIGHT_CLICK_SUPPRESS_AFTER_CLICK
        )

        if self._right_latched:
            if (now - self._right_latch_time
                    > config.RIGHT_CLICK_LATCH_TIMEOUT):
                # Do not let a thumb that stays near the middle finger freeze
                # the cursor forever. After the timeout, fall through to the
                # normal pinch/scroll/cursor arbitration.
                self._right_latched = False
                self._right_frames = 0
            elif d_tm > config.RIGHT_CLICK_EXIT_RATIO or not right_dominant:
                self._right_latched = False
                self._right_frames = 0
            else:
                # Stay latched briefly after firing so a held pose cannot
                # fire repeatedly, but the timeout above keeps it bounded.
                self.state = self.STATE_IDLE
                self.last_action = "Right Click"
                return

        if (not self._pinch_active and not left_click_recently
                and right_dominant and right_close and right_tap):
            self._right_frames += 1
            if (self._right_frames >= config.GESTURE_CONFIRM_FRAMES
                    and now - self._last_right_click_time
                    > config.RIGHT_CLICK_DEBOUNCE):
                self.mouse.right_click()
                self._last_right_click_time = now
                self._right_latched = True
                self._right_latch_time = now
                self.last_action = "Right Click"
            else:
                self.last_action = "Right Ready"
            self.state = self.STATE_IDLE
            return
        self._right_frames = 0

        # ------------------------------------------------------------------
        # LEFT PINCH (click / drag)
        # ------------------------------------------------------------------
        if self._pinch_active:
            if d_ti > config.PINCH_EXIT_RATIO:
                self._release_pinch(now)
                return

            # Midpoint of thumb+index: stable drag anchor and movement metric.
            mid = ((thumb_tip[0] + index_tip[0]) // 2,
                   (thumb_tip[1] + index_tip[1]) // 2)
            moved = 0.0
            if self._pinch_start_mid is not None:
                moved = euclidean(mid, self._pinch_start_mid) / palm

            elapsed = now - (self._pinch_start_time or now)
            if (self.state == self.STATE_PINCH_DOWN
                    and elapsed > config.DRAG_HOLD_TIME
                    and moved > config.DRAG_START_MOVE_RATIO):
                self.mouse.mouse_down()
                self.state = self.STATE_DRAGGING
                self.last_action = "Dragging"

            if self.state == self.STATE_DRAGGING:
                sx, sy = self._map_to_screen(*mid)
                sx, sy = self._smooth(sx, sy)
                self.mouse.move(sx, sy)
                self.last_action = "Dragging"
            return

        if d_ti < config.PINCH_ENTER_RATIO:
            self._pinch_active = True
            self._pinch_start_time = now
            self._pinch_start_mid = (
                (thumb_tip[0] + index_tip[0]) // 2,
                (thumb_tip[1] + index_tip[1]) // 2,
            )
            self.state = self.STATE_PINCH_DOWN
            self.last_action = "Pinch"
            return

        # ------------------------------------------------------------------
        # SCROLL
        # ------------------------------------------------------------------
        # A two-finger scroll keeps index+middle extended. Do not allow a
        # fully open palm (ring+pinky also extended) to trigger scrolling.
        scroll_pose = (fingers[1] and fingers[2]
                       and not (fingers[3] and fingers[4]))
        self._scroll_frames = self._scroll_frames + 1 if scroll_pose else 0

        if self.state == self.STATE_SCROLLING:
            if scroll_pose:
                self._scroll_last_seen = now
                cursor_y = self._palm_center_y(landmarks)
                delta = cursor_y - self._scroll_anchor_y
                dead_zone = palm * config.SCROLL_DEAD_ZONE_RATIO

                if abs(delta) > dead_zone:
                    # Fractional accumulator: slow motion is not discarded,
                    # and fast motion is capped to a few ticks per frame.
                    pixels_per_tick = max(
                        4.0, palm * config.SCROLL_PALM_PER_TICK)
                    self._scroll_accum += -delta / pixels_per_tick

                    ticks = int(self._scroll_accum)
                    max_ticks = config.SCROLL_MAX_TICKS_PER_FRAME
                    ticks = max(-max_ticks, min(max_ticks, ticks))
                    self._scroll_accum -= ticks
                    self._scroll_accum = max(-max_ticks,
                                             min(max_ticks, self._scroll_accum))
                    self._scroll_anchor_y = cursor_y

                    if ticks:
                        self.mouse.scroll(ticks)
                        self.last_action = ("Scrolling Up"
                                            if ticks > 0 else "Scrolling Down")
                    else:
                        self.last_action = "Scroll Ready"
                else:
                    self.last_action = "Scroll Ready"
                return

            # Brief landmark dropout: keep the anchor instead of restarting.
            if now - self._scroll_last_seen <= config.SCROLL_EXIT_GRACE:
                self.last_action = "Scroll Hold"
                return

            self.state = self.STATE_IDLE
            self._scroll_anchor_y = None
            self._scroll_accum = 0.0
            self._scroll_frames = 0
            self.last_action = "Scroll Stop"
            return

        if scroll_pose and self._scroll_frames >= config.GESTURE_CONFIRM_FRAMES:
            self._scroll_anchor_y = self._palm_center_y(landmarks)
            self._scroll_accum = 0.0
            self._scroll_last_seen = now
            self.state = self.STATE_SCROLLING
            self.last_action = "Scroll Ready"
            return

        # ------------------------------------------------------------------
        # CURSOR MOVE (index only)
        # ------------------------------------------------------------------
        if fingers[1] and not fingers[2]:
            if not self._in_active_area(index_tip):
                # Do not snap the cursor to a screen edge when the hand leaves
                # the active region; hold the last position and let the HUD
                # explain why nothing is moving.
                self.state = self.STATE_CURSOR
                self.last_action = "Out of Area"
                return
            sx, sy = self._map_to_screen(index_tip[0], index_tip[1])
            sx, sy = self._smooth(sx, sy)
            self.mouse.move(sx, sy)
            self.state = self.STATE_CURSOR
            self.last_action = "Move"
            return

        # ------------------------------------------------------------------
        # Default: idle
        # ------------------------------------------------------------------
        self.state = self.STATE_IDLE
        self.last_action = "Idle"
