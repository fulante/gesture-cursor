"""Tests for the system volume-key wrapper."""

import unittest
from unittest.mock import patch

import volume_controller
from volume_controller import (VK_VOLUME_DOWN, VK_VOLUME_MUTE,
                               VK_VOLUME_UP, VolumeController)


class VolumeControllerTests(unittest.TestCase):
    def test_up(self):
        with patch.object(volume_controller, "_press") as press:
            VolumeController().up()
            press.assert_called_once_with(VK_VOLUME_UP, "volumeup")

    def test_down(self):
        with patch.object(volume_controller, "_press") as press:
            VolumeController().down()
            press.assert_called_once_with(VK_VOLUME_DOWN, "volumedown")

    def test_mute(self):
        with patch.object(volume_controller, "_press") as press:
            VolumeController().mute()
            press.assert_called_once_with(VK_VOLUME_MUTE, "volumemute")


if __name__ == "__main__":
    unittest.main(verbosity=2)
