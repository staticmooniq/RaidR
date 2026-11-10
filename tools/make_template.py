"""
Universal RaidR template maker.

Run from the RaidR project root with the game showing the button/element you want:

    python make_template.py <template_filename.png>

Example:
    python make_template.py breturnhome.png
    python make_template.py bbstar.png
    python make_template.py flyingmachine.png

What it does:
  1. Screenshots the game window
  2. Opens it in a window — drag a rectangle over the element you want
  3. Scales your selection up to the reference resolution automatically
  4. Saves it as templates/<aspect>/<template_filename.png>
  5. Immediately runs a match check and prints the score

Controls in the selection window:
  - Left-click + drag: draw your selection box
  - R: redo the selection (clear and try again)
  - Enter / Space: confirm and save
  - Escape: cancel without saving
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

import cv2
import numpy as np
from app.config import Config
from app.services.window import WindowService
from app.services.vision import VisionService
from app.utils.common import get_template_path

THRESHOLD = 0.8
BOX_COLOR = (0, 255, 0)
BOX_THICKNESS = 2

drawing = False
start_pt = None
end_pt = None
confirmed = False
cancelled = False


def mouse_cb(event, x, y, flags, param):
    global drawing, start_pt, end_pt, confirmed
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_pt = (x, y)
        end_pt = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        end_pt = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_pt = (x, y)


def select_region(frame):
    global drawing, start_pt, end_pt, confirmed, cancelled
    drawing = False
    start_pt = None
    end_pt = None
    confirmed = False
    cancelled = False

    display = frame.copy()
    win = 'Select region — drag box, Enter to confirm, R to redo, Esc to cancel'
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, mouse_cb)

    while True:
        vis = display.copy()
        if start_pt and end_pt:
            cv2.rectangle(vis, start_pt, end_pt, BOX_COLOR, BOX_THICKNESS)
        cv2.imshow(win, vis)
        key = cv2.waitKey(20) & 0xFF
        if key in (13, 32):  # Enter or Space
            if start_pt and end_pt and start_pt != end_pt:
                confirmed = True
                break
        elif key == ord('r') or key == ord('R'):
            start_pt = None
            end_pt = None
        elif key == 27:  # Escape
            cancelled = True
            break

    cv2.destroyAllWindows()
    if cancelled or not confirmed or not start_pt or not end_pt:
        return None
    x1 = min(start_pt[0], end_pt[0])
    y1 = min(start_pt[1], end_pt[1])
    x2 = max(start_pt[0], end_pt[0])
    y2 = max(start_pt[1], end_pt[1])
    if x2 - x1 < 4 or y2 - y1 < 4:
        print("Selection too small — try again.")
        return None
    return (x1, y1, x2, y2)


def check_score(frame, template_path, template_name):
    template = cv2.imread(str(template_path))
    if template is None:
        return
    scaled = VisionService._resize_template_for_screen(template, frame)
    (t_h, t_w) = scaled.shape[:2]
    (s_h, s_w) = frame.shape[:2]
    if t_w > s_w or t_h > s_h:
        print(f"Warning: scaled template ({t_w}x{t_h}) bigger than capture ({s_w}x{s_h}) — can't match")
        return
    result = cv2.matchTemplate(frame, scaled, cv2.TM_CCOEFF_NORMED)
    (_, max_val, _, max_loc) = cv2.minMaxLoc(result)
    status = "PASS ✓" if max_val >= THRESHOLD else f"FAIL (below {THRESHOLD} threshold)"
    print(f"\nMatch score: {max_val:.3f}  →  {status}")
    annotated = frame.copy()
    (x, y) = max_loc
    cv2.rectangle(annotated, (x, y), (x + t_w, y + t_h), (0, 0, 255), 2)
    cv2.imwrite("debug_match.png", annotated)
    print("Saved debug_match.png — red box shows where it matched on screen.")
    if max_val < THRESHOLD:
        print("\nScore too low. Tips:")
        print("  - Crop tighter (less background around the element)")
        print("  - Make sure the game is showing this element at its normal size when you run the script")
        print("  - Re-run and try a slightly different crop")


def main():
    if len(sys.argv) != 2:
        print("Usage: python make_template.py <template_filename.png>")
        print("Example: python make_template.py breturnhome.png")
        return

    template_name = sys.argv[1]

    print(f"Taking screenshot of game window...")
    window = WindowService()
    frame = window.screenshot()
    if frame is None:
        print("!! Couldn't screenshot the game window.")
        print("   Make sure the game is open and pinned in Settings -> Game window.")
        return

    (h, w) = frame.shape[:2]
    cfg = Config()
    cfg.set_aspect_for_screen_size(w, h)
    print(f"Capture: {w}x{h}  |  aspect: {cfg.aspect_key}  |  ref: {cfg.ref_width}x{cfg.ref_height}")
    print(f"\nDrag a box around '{template_name}' in the window that opens.")
    print("Enter/Space to confirm, R to redo, Esc to cancel.\n")

    cv2.imwrite("debug_screenshot.png", frame)

    region = select_region(frame)
    if region is None:
        print("Cancelled — nothing saved.")
        return

    (x1, y1, x2, y2) = region
    crop = frame[y1:y2, x1:x2]

    scale_x = cfg.ref_width / w
    scale_y = cfg.ref_height / h
    new_w = max(1, round(crop.shape[1] * scale_x))
    new_h = max(1, round(crop.shape[0] * scale_y))
    resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    out_path = get_template_path(template_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), resized)

    print(f"Crop: {crop.shape[1]}x{crop.shape[0]}  →  scaled to {new_w}x{new_h}")
    print(f"Saved: {out_path}")

    check_score(frame, out_path, template_name)


if __name__ == "__main__":
    main()
