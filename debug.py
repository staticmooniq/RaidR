"""
Diagnostic for "can't find breturnhome.png even though it's visible on screen".

Run this from the RaidR project root (same folder as main.py), with the game
showing the Builder Base post-battle Return Home button on screen:

    python debug_breturnhome.py

It takes one screenshot, tries both breturnhome templates the same way bot.py does,
and prints:
  - the window/game capture size
  - which aspect profile (16_9 / 16_10) and ref resolution Config picked
  - the best match score (0.0-1.0) it found for each template, and where
  - whether that score would have passed the bot's 0.8 threshold

It also saves two files next to it:
  - debug_screenshot.png   (what the bot actually captured)
  - debug_match.png        (screenshot with a box drawn where the best match was found)

Send those two images + the printed output and we can tell exactly what's wrong
(wrong template art, scale mismatch, wrong aspect profile, etc).
"""
import cv2
from app.config import Config
from app.services.window import WindowService
from app.services.vision import VisionService
from app.utils.common import get_template_path

TEMPLATES_TO_TRY = ["chestclaim.png"]
THRESHOLD = 0.8


def main():
    window = WindowService()
    frame = window.screenshot()
    if frame is None:
        print("!! screenshot() returned None -- RaidR can't see the game window at all.")
        print("   Check Settings -> Game window in the app and make sure it's pinned to the right window.")
        return

    (h, w) = frame.shape[:2]
    cv2.imwrite("debug_screenshot.png", frame)

    cfg = Config()
    cfg.set_aspect_for_screen_size(w, h)
    print(f"Capture size: {w}x{h}")
    print(f"Config.aspect_key: {cfg.aspect_key}")
    print(f"Config ref_width/ref_height: {cfg.ref_width}x{cfg.ref_height}")
    print()

    best_overall = (None, 0.0, None)
    for template_name in TEMPLATES_TO_TRY:
        template_path = get_template_path(template_name)
        template = cv2.imread(str(template_path))
        if template is None:
            print(f"{template_name}: FILE NOT FOUND at {template_path} (missing for this aspect)")
            continue

        scaled = VisionService._resize_template_for_screen(template, frame)
        (t_h, t_w) = scaled.shape[:2]
        (s_h, s_w) = frame.shape[:2]
        if t_w > s_w or t_h > s_h:
            print(f"{template_name}: scaled template ({t_w}x{t_h}) is BIGGER than the capture ({s_w}x{s_h}) -- can never match")
            continue

        result = cv2.matchTemplate(frame, scaled, cv2.TM_CCOEFF_NORMED)
        (_, max_val, _, max_loc) = cv2.minMaxLoc(result)
        passed = "PASS" if max_val >= THRESHOLD else "FAIL (below 0.8 threshold)"
        print(f"{template_name}: best match score = {max_val:.3f}  ->  {passed}")
        print(f"   original template size: {template.shape[1]}x{template.shape[0]}")
        print(f"   scaled-for-screen size: {t_w}x{t_h}, matched at {max_loc}")
        print()

        if max_val > best_overall[1]:
            best_overall = (template_name, max_val, (max_loc, t_w, t_h))

    if best_overall[0]:
        (name, score, (loc, tw, th)) = best_overall
        annotated = frame.copy()
        (x, y) = loc
        cv2.rectangle(annotated, (x, y), (x + tw, y + th), (0, 0, 255), 3)
        cv2.imwrite("debug_match.png", annotated)
        print(f"Best overall: {name} at {score:.3f} -- see debug_match.png for the red box it thinks is the closest match.")
    print("\nSaved debug_screenshot.png and debug_match.png in this folder.")


if __name__ == "__main__":
    main()
