"""
Isolates WHY a template scores high when made but low when debugged.

Usage (game showing the element, don't touch anything while it runs):
    python selftest_template.py nightwitch.png
"""
import sys, time
import cv2
import numpy as np
from app.config import Config
from app.services.window import WindowService
from app.services.vision import VisionService
from app.utils.common import get_template_path


def score(frame, template_name):
    path = get_template_path(template_name)
    tpl = cv2.imread(str(path))
    if tpl is None:
        return None, None, path, None
    scaled = VisionService._resize_template_for_screen(tpl, frame)
    th, tw = scaled.shape[:2]
    if tw > frame.shape[1] or th > frame.shape[0]:
        return 0.0, None, path, (tw, th)
    res = cv2.matchTemplate(frame, scaled, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    return mx, loc, path, (tw, th)


def main():
    if len(sys.argv) != 2:
        print("Usage: python selftest_template.py <template.png>")
        return
    name = sys.argv[1]
    win = WindowService()
    a = win.screenshot()
    time.sleep(2)
    b = win.screenshot()
    if a is None or b is None:
        print("Screenshot failed.")
        return

    cfg = Config()
    cfg.set_aspect_for_screen_size(a.shape[1], a.shape[0])
    print(f"Shot A: {a.shape[1]}x{a.shape[0]}   Shot B: {b.shape[1]}x{b.shape[0]}")
    print(f"aspect_key: {cfg.aspect_key}  ref: {cfg.ref_width}x{cfg.ref_height}")

    if a.shape == b.shape:
        diff = float(np.mean(cv2.absdiff(a, b)))
        print(f"Avg pixel difference between A and B: {diff:.2f}  (0 = identical, >5 = screen is changing/animating)")
    else:
        print("!! A and B have DIFFERENT SIZES -> capture is unstable. That alone breaks matching.")

    for label, fr in (("A", a), ("B", b)):
        s, loc, path, size = score(fr, name)
        if s is None:
            print(f"Template NOT FOUND: {path}")
            return
        print(f"Shot {label}: score={s:.3f} at {loc}   template file: {path}   scaled size: {size}")

    cv2.imwrite("selftest_A.png", a)
    cv2.imwrite("selftest_B.png", b)
    print("Saved selftest_A.png / selftest_B.png")


if __name__ == "__main__":
    main()
