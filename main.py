"""
main.py
-------
Entry point for the gesture-controlled virtual mouse.

Runs the webcam capture loop, feeds each frame to the HandTracker,
forwards the resulting landmarks to the GestureController, and renders the
debug HUD until the user presses the configured exit key.
"""

import sys
import time

import cv2

import config
from gesture_controller import GestureController
from hand_tracker import HandTracker
from mouse_controller import MouseController
from utils import FPSCounter, draw_hud
from volume_controller import VolumeController


def open_camera():
    """Open the webcam and apply requested resolution/FPS.

    Raises RuntimeError if the camera cannot be opened.
    """
    backend_name = getattr(config, "CAMERA_BACKEND", "ANY").upper()
    backend = getattr(cv2, f"CAP_{backend_name}", cv2.CAP_ANY)
    cap = cv2.VideoCapture(config.CAMERA_INDEX, backend)
    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera at index {config.CAMERA_INDEX} "
            f"(backend {backend_name}). Check that no other application "
            "is using the webcam, or run camera_test.bat to find the "
            "right index/backend."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)

    # Some cameras buffer many frames; this minimises latency where supported.
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass

    return cap


def print_intro(mouse, cam_w=None, cam_h=None):
    """Friendly banner so the user knows what gestures to use."""
    cam_w = cam_w or config.CAMERA_WIDTH
    cam_h = cam_h or config.CAMERA_HEIGHT
    banner = f"""
==============================================================
                Gesture Mouse Control
==============================================================
 Screen resolution : {mouse.screen_w} x {mouse.screen_h}
 Camera resolution : {cam_w} x {cam_h} (requested {config.CAMERA_WIDTH} x {config.CAMERA_HEIGHT})

 Gestures:
   * Index finger up only ............ Move cursor
   * Pinch (thumb + index, quick) .... Left click
   * Pinch twice ...................... Double click
   * Pinch and move .................. Drag (release to drop)
   * Thumb + middle finger pinch ..... Right click
   * Index + middle up (move up/dn) .. Scroll
   * Thumb + ring pinch (move up/dn) . Volume

 Press '{config.EXIT_KEY}' in the preview window to quit.
 Safety: jerk the mouse to a screen corner to abort (PyAutoGUI failsafe).
==============================================================
"""
    print(banner)


def main():
    # ---- Initialise components ------------------------------------------
    try:
        mouse = MouseController()
    except Exception as exc:
        print(f"[Fatal] Could not initialise mouse controller: {exc}")
        sys.exit(1)

    try:
        cap = open_camera()
    except RuntimeError as exc:
        print(f"[Fatal] {exc}")
        sys.exit(1)

    # Read one frame before constructing the controller: many cameras ignore
    # the requested CAP_PROP_FRAME_WIDTH/HEIGHT. The actual frame size must be
    # used for landmark pixel coordinates and cursor mapping.
    ok, first_frame = cap.read()
    if not ok or first_frame is None:
        print("[Fatal] Camera opened but returned no frame.")
        cap.release()
        sys.exit(1)
    cam_h, cam_w = first_frame.shape[:2]

    tracker = HandTracker()
    volume = VolumeController()
    controller = GestureController(mouse, cam_w, cam_h, volume=volume)
    fps_counter = FPSCounter()

    print_intro(mouse, cam_w, cam_h)

    active_area = controller.active_area() if config.SHOW_ACTIVE_AREA else None

    # ---- Main loop -------------------------------------------------------
    try:
        pending_frame = first_frame
        while True:
            if pending_frame is not None:
                frame = pending_frame
                pending_frame = None
            else:
                ok, frame = cap.read()
                if not ok or frame is None:
                    # Transient read failures happen on some webcams; back off briefly.
                    print("[Warn] Empty frame from camera, retrying...")
                    time.sleep(0.05)
                    continue

            # Mirror so user movement matches their reflection.
            frame = cv2.flip(frame, 1)

            # Hand detection
            landmarks, results = tracker.process(frame)

            # Gesture interpretation -> mouse actions
            controller.update(landmarks)

            # A corner failsafe is a deliberate abort. Exit instead of
            # swallowing it and leaving the cursor parked in the corner.
            if getattr(mouse, "failsafe_triggered", False):
                print("[Info] PyAutoGUI failsafe triggered; exiting.")
                break

            # Render overlays
            if config.SHOW_LANDMARKS:
                tracker.draw_landmarks(frame, results)

            draw_hud(
                frame,
                fps=fps_counter.update() if config.SHOW_FPS else None,
                action=controller.last_action if config.SHOW_GESTURE_TEXT else None,
                state=controller.state if config.SHOW_GESTURE_TEXT else None,
                active_area=active_area,
            )

            cv2.imshow(config.WINDOW_NAME, frame)

            # waitKey(1) keeps the OpenCV event loop responsive.
            key = cv2.waitKey(1) & 0xFF
            if key == ord(config.EXIT_KEY) or key == 27:  # q or ESC
                break

            # If the user closes the window, exit cleanly too.
            try:
                if cv2.getWindowProperty(config.WINDOW_NAME,
                                         cv2.WND_PROP_VISIBLE) < 1:
                    break
            except cv2.error:
                break

    except KeyboardInterrupt:
        print("\n[Info] Interrupted by user.")
    finally:
        # Always release drag buttons, even if the cursor is stuck in a
        # failsafe corner or we crashed mid-drag.
        try:
            mouse.release_all()
        except Exception:
            try:
                mouse.mouse_up()
            except Exception:
                pass
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[Info] Gesture Mouse exited cleanly.")


if __name__ == "__main__":
    main()
