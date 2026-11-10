"""
camera_test.py
--------------
Standalone webcam diagnostic for Gesture Mouse Control.

Run it by double-clicking camera_test.bat from Windows Explorer (a normal
Medium-integrity desktop process). It tries the common OpenCV backends and
camera indices, prints the result, and saves a snapshot when a camera works.

This intentionally does not import main.py, so it can be used before the
camera index/backend in config.py is known.
"""

import os
import sys

import cv2

BACKENDS = [
    ("ANY", cv2.CAP_ANY),
    ("DSHOW", cv2.CAP_DSHOW),
    ("MSMF", cv2.CAP_MSMF),
]
INDICES = range(0, 6)
FORMATS = [
    ("default", None),
    ("1280x720", [cv2.CAP_PROP_FRAME_WIDTH, 1280,
                  cv2.CAP_PROP_FRAME_HEIGHT, 720]),
]


def try_open(index, backend, params):
    """Return ((cap, frame), status_text) or (None, status_text)."""
    try:
        if params is None:
            cap = cv2.VideoCapture(index, backend)
        else:
            cap = cv2.VideoCapture(index, backend, params)
    except Exception as exc:  # OpenCV can raise on some broken drivers
        return None, f"exception: {exc}"

    if not cap.isOpened():
        cap.release()
        return None, "not opened"

    ok, frame = cap.read()
    if not ok or frame is None:
        cap.release()
        return None, "opened but no frame"
    return (cap, frame), "ok"


def main():
    print(f"OpenCV: {cv2.__version__}")
    print("Trying camera indices 0-5 with ANY / DSHOW / MSMF...\n")

    for backend_label, backend in BACKENDS:
        for index in INDICES:
            for fmt_label, params in FORMATS:
                result, status = try_open(index, backend, params)
                print(f"  {backend_label:5s} index={index} "
                      f"fmt={fmt_label:7s} -> {status}")
                if result is not None:
                    cap, frame = result
                    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "camera_test.jpg")
                    cv2.imwrite(out, frame)
                    cap.release()
                    print("\n[OK] Camera works!")
                    print(f"     backend = {backend_label}")
                    print(f"     index   = {index}")
                    print(f"     format  = {fmt_label}")
                    print(f"     frame   = {frame.shape}")
                    print(f"     snapshot= {out}")
                    print("\nSet these values in config.py:")
                    print(f"    CAMERA_INDEX = {index}")
                    print(f'    CAMERA_BACKEND = "{backend_label}"')
                    return 0

    print("\n[FAIL] No camera could be opened.")
    print("1. Run this script from Windows Explorer / a normal terminal, "
          "not from the AI sandbox.")
    print("2. Close apps that may be using the camera (Camera, WeChat, "
          "Teams, OBS, Lenovo Vantage, ...).")
    print("3. Check the physical camera shutter / F-key and Lenovo Vantage "
          "camera privacy mode.")
    print("4. Update or reinstall the camera driver in Device Manager.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
