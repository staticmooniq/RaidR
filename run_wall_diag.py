import time
import os
import cv2
import numpy as np
from app.core.bot import Bot
from app.services.vision import VisionService
from app.utils.logger import setup_logger

logger = setup_logger('WallDiag')

def run_diagnostic():
    logger.info("Initializing Bot and attaching to game window...")
    bot = Bot()
    if not bot.window.find_window():
        logger.error("Could not find game window!")
        return

    frame = bot.window.screenshot()
    if frame is None:
        logger.error("Screenshot failed!")
        return

    bot._update_config_size(frame)
    cv2.imwrite("debug/diag_00_initial.png", frame)
    logger.info("Saved debug/diag_00_initial.png (resolution: %s)", frame.shape)

    # Run the wall upgrade procedure
    logger.info("Starting bot._upgrade_walls_from_build_panel(village='home')...")
    res = bot._upgrade_walls_from_build_panel(village='home')
    logger.info("Result of _upgrade_walls_from_build_panel: %s", res)

    final_frame = bot.window.screenshot()
    if final_frame is not None:
        cv2.imwrite("debug/diag_final.png", final_frame)
        logger.info("Saved debug/diag_final.png")

if __name__ == '__main__':
    run_diagnostic()
