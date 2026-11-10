"""Safety tests for the PyAutoGUI wrapper (no real mouse movement)."""

import unittest
from unittest.mock import patch

import pyautogui

import mouse_controller
from mouse_controller import MouseController


class MouseControllerSafetyTests(unittest.TestCase):
    def setUp(self):
        with patch.object(pyautogui, "size", return_value=(1920, 1080)):
            self.mouse = MouseController()

    def test_scroll_is_capped(self):
        with patch("mouse_controller._send_wheel") as wheel:
            self.mouse.scroll(99)
            wheel.assert_called_once_with(3)

            wheel.reset_mock()
            self.mouse.scroll(-99)
            wheel.assert_called_once_with(-3)

    def test_wheel_uses_wheel_delta_units(self):
        with patch.object(mouse_controller.ctypes.windll.user32,
                          "mouse_event") as event:
            mouse_controller._send_wheel(2)
            event.assert_called_once_with(
                mouse_controller.MOUSEEVENTF_WHEEL, 0, 0, 240, 0)

    def test_failsafe_is_swallowed_for_click(self):
        with patch.object(pyautogui, "click",
                          side_effect=pyautogui.FailSafeException), \
                patch("builtins.print"):
            # Must not raise: a screen-corner abort should not kill the loop.
            self.mouse.click()
            self.assertTrue(self.mouse.failsafe_triggered)

    def test_failsafe_is_swallowed_for_right_click(self):
        with patch.object(pyautogui, "rightClick",
                          side_effect=pyautogui.FailSafeException), \
                patch("builtins.print"):
            self.mouse.right_click()
            self.assertTrue(self.mouse.failsafe_triggered)

    def test_release_all_bypasses_failsafe(self):
        with patch.object(pyautogui, "mouseUp") as mouse_up:
            old = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = True
            try:
                self.mouse.release_all()
            finally:
                pyautogui.FAILSAFE = old

            self.assertEqual(mouse_up.call_count, 2)
            mouse_up.assert_any_call(button="left", _pause=False)
            mouse_up.assert_any_call(button="right", _pause=False)
            self.assertTrue(pyautogui.FAILSAFE)

    def test_move_clamps_to_screen(self):
        with patch.object(pyautogui, "moveTo") as move_to:
            self.mouse.move(-50, 5000)
            move_to.assert_called_once_with(0, 1079, _pause=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
