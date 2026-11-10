"""
volume_controller.py
--------------------
Small OS wrapper for system volume keys.

Windows uses the virtual-key media events (VK_VOLUME_UP/DOWN/MUTE) through
``keybd_event``. Other platforms fall back to PyAutoGUI's media-key names.
"""

import ctypes
import sys

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _press(vk, fallback_key):
    """Send one volume key press; testable in isolation."""
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(vk, 0,
                           KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    else:
        import pyautogui
        pyautogui.press(fallback_key)


class VolumeController:
    """System volume controls used by the gesture state machine."""

    def up(self):
        _press(VK_VOLUME_UP, "volumeup")

    def down(self):
        _press(VK_VOLUME_DOWN, "volumedown")

    def mute(self):
        _press(VK_VOLUME_MUTE, "volumemute")
