"""Synthetic-landmark regression tests for the gesture state machine.

Run from the project root:

    .venv\\Scripts\\python.exe -m unittest discover -s tests -v

The tests deliberately avoid a camera and MediaPipe: they build 21 fake
landmarks with a known geometry and assert which mouse actions are emitted.
"""

import math
import unittest
from unittest.mock import patch

import config
from gesture_controller import GestureController


class FakeMouse:
    screen_w, screen_h = 1920, 1080

    def __init__(self):
        self.calls = []
        self.pos = (0, 0)

    def position(self):
        return self.pos

    def move(self, x, y):
        self.pos = (int(x), int(y))
        self.calls.append(("move", int(x), int(y)))

    def click(self):
        self.calls.append(("click",))

    def right_click(self):
        self.calls.append(("right_click",))

    def mouse_down(self):
        self.calls.append(("mouse_down",))

    def mouse_up(self):
        self.calls.append(("mouse_up",))

    def scroll(self, amount):
        self.calls.append(("scroll", int(amount)))


class FakeVolume:
    def __init__(self):
        self.calls = []

    def up(self):
        self.calls.append(("up",))

    def down(self):
        self.calls.append(("down",))

    def mute(self):
        self.calls.append(("mute",))


class Clock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make_hand(index_tip=(265, 200), middle_tip=(320, 200),
              ring_tip=(370, 200), pinky_tip=(410, 200),
              thumb=(230, 220)):
    """Build a 21-point hand with palm size = 100 px.

    Extended fingers point up; a folded finger uses a tip near its MCP.
    """
    pts = [(320, 400)] * 21
    pts[0] = (320, 400)          # wrist
    pts[1] = (300, 360)          # thumb CMC
    pts[2] = (285, 340)          # thumb MCP
    pts[3] = (270, 330)          # thumb IP
    pts[4] = thumb               # thumb tip

    pts[5] = (280, 300)          # index MCP
    pts[6] = (270, 250)          # index PIP
    pts[7] = (265, 225)          # index DIP
    pts[8] = index_tip

    pts[9] = (320, 300)          # middle MCP
    pts[10] = (320, 250)         # middle PIP
    pts[11] = (320, 225)         # middle DIP
    pts[12] = middle_tip

    pts[13] = (360, 300)         # ring MCP
    pts[14] = (370, 250)         # ring PIP
    pts[15] = (370, 225)         # ring DIP
    pts[16] = ring_tip

    pts[17] = (400, 300)         # pinky MCP
    pts[18] = (410, 250)         # pinky PIP
    pts[19] = (410, 225)         # pinky DIP
    pts[20] = pinky_tip
    return pts


def folded(name):
    """Return a folded tip for the given finger name."""
    return {
        "index": (275, 320),
        "middle": (320, 320),
        "ring": (370, 320),
        "pinky": (410, 320),
    }[name]


def shift(hand, dy):
    return [(x, y + dy) for x, y in hand]


def rotate(hand, degrees):
    """Rotate the whole hand around the wrist (preserves ratios/angles)."""
    angle = math.radians(degrees)
    wx, wy = hand[0]
    c, s = math.cos(angle), math.sin(angle)
    out = []
    for x, y in hand:
        dx, dy = x - wx, y - wy
        out.append((wx + dx * c - dy * s, wy + dx * s + dy * c))
    return out


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self._patch = patch("gesture_controller.time.perf_counter", self.clock)
        self._patch.start()
        self.mouse = FakeMouse()
        self.ctrl = GestureController(self.mouse, 640, 480)
        self.ctrl._double_click_window = config.DOUBLE_CLICK_WINDOW

    def tearDown(self):
        self._patch.stop()

    def _scroll_values(self):
        return [c[1] for c in self.mouse.calls if c[0] == "scroll"]

    def _clear(self):
        self.mouse.calls.clear()

    def _right_hand(self, thumb):
        return make_hand(index_tip=(265, 200),
                         middle_tip=(255, 320),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=thumb)

    def _arm_right_click(self):
        """Move the thumb away so the next contact counts as a tap."""
        away = self._right_hand((230, 220))
        for _ in range(3):
            self.ctrl.update(away)
            self.clock.advance(1 / 30)

    def _click_once(self):
        """Perform one complete pinch click cycle at the current position."""
        pinched = make_hand(index_tip=(255, 320),
                            middle_tip=(320, 200),
                            ring_tip=folded("ring"),
                            pinky_tip=folded("pinky"),
                            thumb=(250, 320))
        self.ctrl.update(pinched)
        self.clock.advance(0.1)
        released = make_hand(index_tip=(265, 200),
                             middle_tip=(320, 200),
                             ring_tip=folded("ring"),
                             pinky_tip=folded("pinky"),
                             thumb=(230, 220))
        self.ctrl.update(released)
        self.clock.advance(0.1)

    def test_finger_detection_is_rotation_tolerant(self):
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"))
        upright = self.ctrl._fingers_up(hand)
        self.assertEqual(upright[1:], [1, 1, 0, 0])

        # Rebuild a fresh controller so per-finger hysteresis starts clean.
        self.ctrl = GestureController(self.mouse, 640, 480)
        tilted = self.ctrl._fingers_up(rotate(hand, 35))
        self.assertEqual(tilted[1:], [1, 1, 0, 0])

    def test_scroll_slow_movement_accumulates(self):
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=(240, 220))  # relaxed thumb, not a pinch

        # Two confirmation frames.
        for _ in range(2):
            self.ctrl.update(hand)
            self.clock.advance(1 / 30)
        self.assertEqual(self.ctrl.state, GestureController.STATE_SCROLLING)
        self._clear()

        total = 0
        for _ in range(60):
            hand = shift(hand, -2)
            self.ctrl.update(hand)
            values = self._scroll_values()
            total += sum(values)
            self.assertTrue(all(abs(v) <= 3 for v in values))
            self._clear()
            self.clock.advance(1 / 30)

        self.assertGreater(total, 0, "slow scroll must not be discarded")
        self.assertLessEqual(abs(total), 30, "slow scroll should be gentle")

    def test_scroll_is_not_blocked_by_relaxed_thumb(self):
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=(240, 220))

        self.ctrl.update(hand)
        self.clock.advance(1 / 30)
        self.ctrl.update(hand)
        self.clock.advance(1 / 30)
        self.assertEqual(self.ctrl.state, GestureController.STATE_SCROLLING)

        hand = shift(hand, -40)
        self.ctrl.update(hand)
        self.assertGreater(len(self._scroll_values()), 0)

    def test_scroll_per_frame_is_capped(self):
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=(230, 220))
        for _ in range(2):
            self.ctrl.update(hand)
            self.clock.advance(1 / 30)

        self.ctrl.update(shift(hand, -300))
        values = self._scroll_values()
        self.assertTrue(values)
        self.assertTrue(all(abs(v) <= 3 for v in values))

    def test_right_click_allows_bent_middle(self):
        # Index is up; middle is bent so its tip touches the thumb. The old
        # code required fingers[2] == 1 and could never fire this pose.
        self._arm_right_click()
        hand = self._right_hand((250, 320))
        self.ctrl.update(hand)
        self.clock.advance(1 / 30)
        self.ctrl.update(hand)
        self.assertIn(("right_click",), self.mouse.calls)
        self.assertEqual(self.ctrl.last_action, "Right Click")

    def test_right_click_held_fires_only_once(self):
        self._arm_right_click()
        hand = self._right_hand((250, 320))
        for _ in range(12):
            self.ctrl.update(hand)
            self.clock.advance(0.1)

        clicks = [c for c in self.mouse.calls if c == ("right_click",)]
        self.assertEqual(len(clicks), 1, "holding must not repeat right-click")

    def test_right_click_rearms_after_release(self):
        self._arm_right_click()
        hand = self._right_hand((250, 320))
        for _ in range(3):
            self.ctrl.update(hand)
            self.clock.advance(0.1)
        self.assertEqual(
            len([c for c in self.mouse.calls if c == ("right_click",)]), 1)

        # Move the thumb away for a few frames: latch releases and the next
        # contact is a fresh tap.
        away = self._right_hand((230, 220))
        for _ in range(2):
            self.ctrl.update(away)
            self.clock.advance(0.1)

        # Tap again.
        for _ in range(3):
            self.ctrl.update(hand)
            self.clock.advance(0.1)
        self.assertEqual(
            len([c for c in self.mouse.calls if c == ("right_click",)]), 2)

    def test_right_click_latch_timeout_unblocks_cursor(self):
        self._arm_right_click()
        hand = self._right_hand((250, 320))
        self.ctrl.update(hand)
        self.clock.advance(1 / 30)
        self.ctrl.update(hand)
        self.assertIn(("right_click",), self.mouse.calls)

        # The latch must expire even if the thumb stays near the middle.
        self.clock.advance(1.0)
        self._clear()
        self.ctrl.update(hand)
        self.assertEqual(self.ctrl.state, GestureController.STATE_CURSOR)
        self.assertIn("move", [c[0] for c in self.mouse.calls])

    def test_resting_thumb_does_not_right_click(self):
        # Reproduces the user's cursor pose: index is up, middle is folded and
        # the thumb naturally rests against the middle fingertip. Without a
        # recent tap motion this must not fire a right click.
        hand = self._right_hand((250, 320))
        for _ in range(15):
            self.ctrl.update(hand)
            self.clock.advance(1 / 30)

        self.assertNotIn(("right_click",), self.mouse.calls)
        self.assertEqual(self.ctrl.state, GestureController.STATE_CURSOR)

    def test_scroll_works_with_thumb_resting_on_middle(self):
        # Thumb rests near the middle finger while doing a two-finger scroll.
        # The old right-click branch could steal this pose; it must not.
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=(320, 210))
        for _ in range(2):
            self.ctrl.update(hand)
            self.clock.advance(1 / 30)
        self.assertEqual(self.ctrl.state, GestureController.STATE_SCROLLING)
        self.assertNotIn(("right_click",), self.mouse.calls)

        self.ctrl.update(shift(hand, -20))
        self.assertGreater(len(self._scroll_values()), 0)

    def test_left_pinch_still_clicks(self):
        pinched = make_hand(index_tip=(255, 320),
                            middle_tip=(320, 200),
                            ring_tip=folded("ring"),
                            pinky_tip=folded("pinky"),
                            thumb=(250, 320))
        self.ctrl.update(pinched)
        self.assertEqual(self.ctrl.state, GestureController.STATE_PINCH_DOWN)

        self.clock.advance(0.1)
        released = make_hand(index_tip=(265, 200),
                             middle_tip=(320, 200),
                             ring_tip=folded("ring"),
                             pinky_tip=folded("pinky"),
                             thumb=(230, 220))
        self.ctrl.update(released)
        self.assertIn(("click",), self.mouse.calls)

    def test_pinch_hold_still_drags(self):
        pinched = make_hand(index_tip=(255, 320),
                            middle_tip=(320, 200),
                            ring_tip=folded("ring"),
                            pinky_tip=folded("pinky"),
                            thumb=(250, 320))
        self.ctrl.update(pinched)

        self.clock.advance(0.4)
        self.ctrl.update(shift(pinched, -20))
        self.assertEqual(self.ctrl.state, GestureController.STATE_DRAGGING)
        self.assertIn(("mouse_down",), self.mouse.calls)

        self.clock.advance(0.1)
        released = make_hand(index_tip=(265, 200),
                             middle_tip=(320, 200),
                             ring_tip=folded("ring"),
                             pinky_tip=folded("pinky"),
                             thumb=(230, 220))
        self.ctrl.update(released)
        self.assertIn(("mouse_up",), self.mouse.calls)

    def test_long_stationary_pinch_is_a_click(self):
        pinched = make_hand(index_tip=(255, 320),
                            middle_tip=(320, 200),
                            ring_tip=folded("ring"),
                            pinky_tip=folded("pinky"),
                            thumb=(250, 320))
        self.ctrl.update(pinched)

        # Hold well past DRAG_HOLD_TIME without moving: a slow click must not
        # silently turn into a drag.
        self.clock.advance(0.6)
        self.ctrl.update(pinched)
        self.assertEqual(self.ctrl.state, GestureController.STATE_PINCH_DOWN)

        self.clock.advance(0.1)
        released = make_hand(index_tip=(265, 200),
                             middle_tip=(320, 200),
                             ring_tip=folded("ring"),
                             pinky_tip=folded("pinky"),
                             thumb=(230, 220))
        self.ctrl.update(released)
        self.assertIn(("click",), self.mouse.calls)
        self.assertNotIn(("mouse_down",), self.mouse.calls)

    def test_single_pinch_is_one_click(self):
        self._click_once()
        clicks = [c for c in self.mouse.calls if c == ("click",)]
        self.assertEqual(len(clicks), 1)
        self.assertEqual(self.ctrl.last_action, "Click")

    def test_double_pinch_is_two_clicks(self):
        self._click_once()
        self._click_once()
        clicks = [c for c in self.mouse.calls if c == ("click",)]
        self.assertEqual(len(clicks), 2)
        self.assertEqual(self.ctrl.last_action, "Double Click")

    def test_slow_second_pinch_is_two_single_clicks(self):
        self._click_once()
        self.clock.advance(0.6)  # beyond DOUBLE_CLICK_WINDOW
        self._click_once()
        clicks = [c for c in self.mouse.calls if c == ("click",)]
        self.assertEqual(len(clicks), 2)
        self.assertEqual(self.ctrl.last_action, "Click")

    def test_moved_second_pinch_is_two_single_clicks(self):
        self._click_once()
        self.mouse.pos = (20, 0)  # beyond DOUBLE_CLICK_MAX_MOVE_PX
        self._click_once()
        clicks = [c for c in self.mouse.calls if c == ("click",)]
        self.assertEqual(len(clicks), 2)
        self.assertEqual(self.ctrl.last_action, "Click")

    def test_long_first_pinch_can_still_group_into_double(self):
        pinched = make_hand(index_tip=(255, 320),
                            middle_tip=(320, 200),
                            ring_tip=folded("ring"),
                            pinky_tip=folded("pinky"),
                            thumb=(250, 320))
        self.ctrl.update(pinched)
        self.clock.advance(0.6)
        self.ctrl.update(pinched)
        self.clock.advance(0.1)
        released = make_hand(index_tip=(265, 200),
                             middle_tip=(320, 200),
                             ring_tip=folded("ring"),
                             pinky_tip=folded("pinky"),
                             thumb=(230, 220))
        self.ctrl.update(released)
        self.assertEqual(self.ctrl.last_action, "Click")

        self.clock.advance(0.15)
        self._click_once()
        clicks = [c for c in self.mouse.calls if c == ("click",)]
        self.assertEqual(len(clicks), 2)
        self.assertEqual(self.ctrl.last_action, "Double Click")

    def test_right_click_is_suppressed_after_left_click(self):
        self._click_once()
        self._arm_right_click()
        near = self._right_hand((250, 320))
        self.ctrl.update(near)
        self.clock.advance(1 / 30)
        self.ctrl.update(near)
        self.assertNotIn(("right_click",), self.mouse.calls)

        self.clock.advance(0.4)
        self._arm_right_click()
        self.ctrl.update(near)
        self.clock.advance(1 / 30)
        self.ctrl.update(near)
        self.assertIn(("right_click",), self.mouse.calls)

    def _volume_hand(self, ring_tip=(255, 320), thumb=(250, 320)):
        return make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=ring_tip,
                         pinky_tip=folded("pinky"),
                         thumb=thumb)

    def test_volume_requires_arming(self):
        vol = FakeVolume()
        self.ctrl.volume = vol
        hand = self._volume_hand()
        for _ in range(6):
            self.ctrl.update(hand)
            self.clock.advance(1 / 30)
        self.assertNotEqual(self.ctrl.state, GestureController.STATE_VOLUME)
        self.assertEqual(vol.calls, [])

    def test_volume_up_down_and_exit(self):
        vol = FakeVolume()
        self.ctrl.volume = vol

        # Arm by separating thumb and ring first.
        far = self._volume_hand(ring_tip=(410, 200))
        self.ctrl.update(far)

        near = self._volume_hand()
        self.ctrl.update(near)
        self.clock.advance(1 / 30)
        self.ctrl.update(near)
        self.clock.advance(1 / 30)
        self.assertEqual(self.ctrl.state, GestureController.STATE_VOLUME)

        self.ctrl.update(shift(near, -30))
        self.assertIn(("up",), vol.calls)

        self.ctrl.update(shift(near, 0))
        self.assertIn(("down",), vol.calls)

        # Releasing the ring exits volume mode.
        self.ctrl.update(self._volume_hand(ring_tip=(410, 200)))
        self.assertNotEqual(self.ctrl.state, GestureController.STATE_VOLUME)

    def test_volume_steps_are_capped(self):
        vol = FakeVolume()
        self.ctrl.volume = vol
        self.ctrl.update(self._volume_hand(ring_tip=(410, 200)))
        near = self._volume_hand()
        self.ctrl.update(near)
        self.clock.advance(1 / 30)
        self.ctrl.update(near)

        self.ctrl.update(shift(near, -200))
        self.assertLessEqual(len([c for c in vol.calls if c == ("up",)]),
                             config.VOLUME_MAX_STEPS_PER_FRAME)

    def test_cursor_move_still_works(self):
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=folded("middle"),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=(230, 220))
        self.ctrl.update(hand)
        self.assertEqual(self.ctrl.state, GestureController.STATE_CURSOR)
        self.assertIn("move", [c[0] for c in self.mouse.calls])

    def test_hand_outside_active_area_does_not_jump_to_edge(self):
        hand = make_hand(index_tip=(20, 50),
                         middle_tip=folded("middle"),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=(230, 220))
        self.ctrl.update(hand)
        self.assertEqual(self.ctrl.state, GestureController.STATE_CURSOR)
        self.assertEqual(self.ctrl.last_action, "Out of Area")
        self.assertEqual(self.mouse.calls, [])

    def test_cursor_mapping_stays_clear_of_screen_corners(self):
        margin = config.SCREEN_EDGE_MARGIN
        top_left = self.ctrl._map_to_screen(0, 0)
        bottom_right = self.ctrl._map_to_screen(10000, 10000)
        self.assertGreaterEqual(top_left[0], margin)
        self.assertGreaterEqual(top_left[1], margin)
        self.assertLessEqual(bottom_right[0], self.ctrl.screen_w - 1 - margin)
        self.assertLessEqual(bottom_right[1], self.ctrl.screen_h - 1 - margin)

    def test_active_area_scales_with_actual_resolution(self):
        ctrl = GestureController(FakeMouse(), 1280, 720)
        self.assertEqual(ctrl.active_area(), (200, 150, 1080, 570))

    def test_open_palm_does_not_scroll(self):
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=(370, 200),
                         pinky_tip=(410, 200),
                         thumb=(230, 220))
        for _ in range(5):
            self.ctrl.update(shift(hand, -10))
            self.clock.advance(1 / 30)
        self.assertNotEqual(self.ctrl.state, GestureController.STATE_SCROLLING)
        self.assertEqual(self._scroll_values(), [])

    def test_scroll_works_when_hand_is_tilted(self):
        hand = make_hand(index_tip=(265, 200),
                         middle_tip=(320, 200),
                         ring_tip=folded("ring"),
                         pinky_tip=folded("pinky"),
                         thumb=(230, 220))
        hand = rotate(hand, 30)
        for _ in range(2):
            self.ctrl.update(hand)
            self.clock.advance(1 / 30)
        self.assertEqual(self.ctrl.state, GestureController.STATE_SCROLLING)

        self.ctrl.update(shift(hand, -40))
        self.assertGreater(len(self._scroll_values()), 0)

    def test_no_hand_releases_drag(self):
        pinched = make_hand(index_tip=(255, 320),
                            middle_tip=(320, 200),
                            ring_tip=folded("ring"),
                            pinky_tip=folded("pinky"),
                            thumb=(250, 320))
        self.ctrl.update(pinched)
        self.clock.advance(0.4)
        self.ctrl.update(shift(pinched, -20))
        self.assertEqual(self.ctrl.state, GestureController.STATE_DRAGGING)

        self.ctrl.update(None)
        self.assertIn(("mouse_up",), self.mouse.calls)
        self.assertEqual(self.ctrl.state, GestureController.STATE_IDLE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
