"""
mouse_controller.py
------------------
Thin OS-mouse wrapper around PyAutoGUI.

Centralising mouse interactions here keeps gesture logic free of any
platform-specific quirks and makes the system easier to swap to another
backend (e.g., pynput) later.

v1.1: every action is guarded against PyAutoGUI's FailSafeException (not
only ``move``), and a single scroll call is capped so a noisy frame cannot
send dozens of wheel ticks at once.
"""

import ctypes
import sys
import time

import pyautogui

MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120


def _send_wheel(amount):
    """Send a proper Windows wheel event at the current cursor position.

    PyAutoGUI 0.9.54's Windows backend passes the click count straight to
    ``mouse_event`` as ``dwData``, but Windows expects multiples of
    ``WHEEL_DELTA`` (120). ``scroll(1)`` therefore becomes 1/120 of a notch.
    This helper sends the correct unit.
    """
    ctypes.windll.user32.mouse_event(
        MOUSEEVENTF_WHEEL, 0, 0, int(amount) * WHEEL_DELTA, 0)


class MouseController:
    """Wrapper around PyAutoGUI providing safe, low-latency mouse actions."""

    MAX_SCROLL_PER_CALL = 3

    def __init__(self, failsafe=True):
        # FAILSAFE: jerk the cursor to a screen corner to abort if something
        # goes wrong. Keep it on by default - it has saved many demos.
        pyautogui.FAILSAFE = failsafe
        pyautogui.PAUSE = 0  # Disable PyAutoGUI's built-in delay
        self.screen_w, self.screen_h = pyautogui.size()
        self._last_failsafe_print = -1e9
        self.failsafe_triggered = False

    # ---------------------------------------------------------- Helpers ---
    def _safe(self, action, *args, **kwargs):
        """Run a PyAutoGUI action, swallowing failsafe aborts."""
        try:
            return action(*args, **kwargs)
        except pyautogui.FailSafeException:
            # Do not crash the capture loop, but let main() exit cleanly:
            # swallowing this while the cursor is parked in a corner would
            # otherwise make every subsequent move fail (a frozen cursor).
            self.failsafe_triggered = True
            now = time.perf_counter()
            if now - self._last_failsafe_print > 1.0:
                print("[MouseController] FailSafe triggered "
                      "(cursor at screen corner).")
                self._last_failsafe_print = now
            return None

    # ---------------------------------------------------------- Movement ---
    def position(self):
        """Return the current cursor position, or None if unavailable."""
        try:
            pos = pyautogui.position()
            return int(pos[0]), int(pos[1])
        except Exception:
            return None

    def move(self, x, y):
        """Move the cursor to absolute screen coordinates (clamped to bounds)."""
        x = max(0, min(self.screen_w - 1, int(x)))
        y = max(0, min(self.screen_h - 1, int(y)))
        self._safe(pyautogui.moveTo, x, y, _pause=False)

    # ------------------------------------------------------------ Clicks ---
    def click(self):
        self._safe(pyautogui.click, _pause=False)

    def right_click(self):
        self._safe(pyautogui.rightClick, _pause=False)

    def double_click(self):
        self._safe(pyautogui.doubleClick, _pause=False)

    # ------------------------------------------------ Drag (manual hold) ---
    def _release_button(self, button):
        """Release one button even when the cursor is in a failsafe corner."""
        old = pyautogui.FAILSAFE
        pyautogui.FAILSAFE = False
        try:
            pyautogui.mouseUp(button=button, _pause=False)
            return True
        except Exception:
            return False
        finally:
            pyautogui.FAILSAFE = old

    def mouse_down(self):
        self._safe(pyautogui.mouseDown, _pause=False)

    def mouse_up(self):
        self._release_button("left")

    def release_all(self):
        """Best-effort release of drag buttons after a crash/failsafe.

        ``mouseUp`` itself goes through PyAutoGUI's failsafe check. If the
        cursor is parked in a corner, swallowing the exception would leave the
        left button held down. Temporarily disabling FAILSAFE for this release
        is the only reliable way out; the previous setting is restored.
        """
        for button in ("left", "right"):
            self._release_button(button)

    # ------------------------------------------------------------ Scroll ---
    def scroll(self, amount):
        """Vertical scroll. Positive = up, negative = down."""
        amount = max(-self.MAX_SCROLL_PER_CALL,
                     min(self.MAX_SCROLL_PER_CALL, int(amount)))
        if amount == 0:
            return
        if sys.platform == "win32":
            _send_wheel(amount)
        else:
            self._safe(pyautogui.scroll, amount, _pause=False)
