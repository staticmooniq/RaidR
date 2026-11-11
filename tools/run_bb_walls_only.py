"""Run Builder Base wall upgrading only, with periodic anti-inactivity zoom every 2 minutes."""
import sys
import os
import time
import signal

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.utils.tesseract_env import configure_tesseract
from app.utils.logger import setup_logger
from app.core.bot import Bot
from app.config import Config

logger = setup_logger('BBWallsRunner')

def run_bb_walls(once=False):
    configure_tesseract()
    logger.info("Starting Builder Base Wall Upgrader (WALLS ONLY mode)...")
    
    bot = Bot()
    if not bot.window.find_window():
        logger.error("Clash of Clans window not found. Please ensure the game is open.")
        return False
        
    logger.info(f"Connected to Clash of Clans (HWND: {bot.window.hwnd})")
    
    # Handle graceful exit on Ctrl+C
    def sig_handler(sig, frame):
        logger.info("Stop signal received, shutting down...")
        bot.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, sig_handler)
    
    bot.running = True
    bot.stop_event.clear()
    
    # Ensure on Builder Base
    logger.info("Verifying village is Builder Base...")
    bot._ensure_correct_village(builder_base=True)
    
    # Perform initial anti-inactivity zoom
    logger.info("Performing initial anti-inactivity zoom...")
    bot.maybe_anti_inactivity_zoom(force=True)
    
    pass_num = 1
    while not bot.stop_event.is_set():
        logger.info(f"--- Starting Builder Base Wall Upgrade Pass #{pass_num} ---")
        try:
            # Check if any leftover dialog is open and clear it
            bot._bb_deselect_wall_ui()
            
            upgraded = bot._maybe_upgrade_bb_walls(upgrade_walls=True, force=True)
            logger.info(f"Pass #{pass_num} result: upgraded = {upgraded}")
        except Exception as e:
            logger.error(f"Pass #{pass_num} encountered error: {e}", exc_info=True)
        finally:
            try:
                bot._bb_deselect_wall_ui()
                bot._bb_close_build_panel()
            except Exception:
                pass
                
        if once:
            logger.info("Single pass complete (--once specified). Exiting.")
            break
            
        pass_num += 1
        logger.info("Waiting 45s before next wall upgrade scan (anti-inactivity zoom monitored every 2 min)...")
        # Sleep in small increments while checking for 2-minute anti-inactivity zoom
        start_wait = time.monotonic()
        while time.monotonic() - start_wait < 45.0:
            bot._check_stop()
            time.sleep(1.0)
            
    bot.running = False
    logger.info("Builder Base Wall Upgrader finished.")
    return True

if __name__ == '__main__':
    once = '--once' in sys.argv
    run_bb_walls(once=once)
