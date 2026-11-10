"""
RaidR — In-Built Game Launcher Service.
Launches Clash of Clans via Google Play Games PC.
"""
from __future__ import annotations
import os
import subprocess
from typing import Tuple
from app.utils.logger import setup_logger

logger = setup_logger('GameLauncher')

_COC_URI = 'googleplaygames://launch/?id=com.supercell.clashofclans&lid=1&pid=1'
_BOOTSTRAPPER_PATHS = [
    r'C:\Program Files\Google\Play Games\Bootstrapper.exe',
    r'C:\Program Files (x86)\Google\Play Games\Bootstrapper.exe',
]
_SHORTCUT_PATHS = [
    os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs\Google Play Games\Clash of Clans.lnk'),
    os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs\Google Play Games\Clash of Clans.lnk'),
    os.path.expandvars(r'%USERPROFILE%\Desktop\Clash of Clans.lnk'),
    os.path.expandvars(r'%PUBLIC%\Desktop\Clash of Clans.lnk'),
]


def launch_clash_of_clans() -> Tuple[bool, str]:
    """
    Attempts to launch Clash of Clans via Google Play Games PC.
    
    Tries multiple launch pathways:
    1. Direct URL protocol: googleplaygames://launch/?id=com.supercell.clashofclans
    2. Google Play Games Bootstrapper CLI
    3. Windows Start Menu / Desktop Advertised Shortcuts
    4. CMD shell fallback
    """
    logger.info("Attempting to launch Clash of Clans...")

    # Method 1: Protocol handler via Windows Shell
    try:
        os.startfile(_COC_URI)
        logger.info("Dispatched launch command via Google Play Games protocol URI")
        return True, "Launched Clash of Clans via Google Play Games protocol."
    except Exception as e:
        logger.debug("Protocol launch failed: %s", e)

    # Method 2: Bootstrapper executable
    for bootstrapper in _BOOTSTRAPPER_PATHS:
        if os.path.isfile(bootstrapper):
            try:
                subprocess.Popen([bootstrapper, _COC_URI])
                logger.info("Launched Clash of Clans via Bootstrapper: %s", bootstrapper)
                return True, "Launched Clash of Clans via Google Play Games Bootstrapper."
            except Exception as e:
                logger.debug("Bootstrapper launch failed for %s: %s", bootstrapper, e)

    # Method 3: Windows Shortcuts (.lnk)
    for shortcut in _SHORTCUT_PATHS:
        if os.path.isfile(shortcut):
            try:
                os.startfile(shortcut)
                logger.info("Launched Clash of Clans via shortcut: %s", shortcut)
                return True, f"Launched Clash of Clans via shortcut: {os.path.basename(shortcut)}"
            except Exception as e:
                logger.debug("Shortcut launch failed for %s: %s", shortcut, e)

    # Method 4: CMD fallback
    try:
        subprocess.Popen(['cmd.exe', '/c', 'start', '', _COC_URI], shell=False)
        logger.info("Dispatched launch command via shell start fallback")
        return True, "Launched Clash of Clans via shell command."
    except Exception as e:
        logger.error("All launch pathways failed: %s", e)
        return False, f"Could not launch game automatically: {e}"
