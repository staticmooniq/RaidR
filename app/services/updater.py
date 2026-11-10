"""
RaidR — Autonomous Update Service & Self-Updating Engine.
Checks for releases on GitHub and downloads/replaces the running executable in-place.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication

GITHUB_REPO_OWNER = 'staticmooniq'
GITHUB_REPO_NAME = 'RaidR'
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"


@dataclass
class UpdateInfo:
    version: str
    tag_name: str
    asset_name: str
    download_url: str
    asset_size: int
    release_notes: str
    published_at: str
    html_url: str


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Parse a semantic version string (e.g. 'v1.0.2', '1.1') into an integer tuple."""
    parts = [int(p) for p in re.findall(r'\d+', str(v_str))]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(latest_tag: str, current_version: str) -> bool:
    """Returns True if latest_tag represents a strictly higher version than current_version."""
    return parse_version(latest_tag) > parse_version(current_version)


def find_executable_asset(assets: list) -> Optional[dict]:
    """Find the pre-compiled binary executable asset in release assets list."""
    if not assets:
        return None
    # 1. Look for asset named RaidR*.exe
    for a in assets:
        name = a.get('name', '').lower()
        if name.startswith('raidr') and name.endswith('.exe'):
            return a
    # 2. Look for any *.exe
    for a in assets:
        name = a.get('name', '').lower()
        if name.endswith('.exe'):
            return a
    return None


class UpdateCheckerThread(QThread):
    """Asynchronously checks the GitHub Releases API for new updates."""
    updateAvailable = Signal(object)      # Emits UpdateInfo
    upToDate = Signal(str)               # Emits current_version
    checkFailed = Signal(str)            # Emits error_msg

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    'User-Agent': f'RaidR-Updater/{self.current_version}',
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            tag_name = data.get('tag_name', '')
            if not tag_name:
                self.upToDate.emit(self.current_version)
                return

            if is_newer_version(tag_name, self.current_version):
                asset = find_executable_asset(data.get('assets', []))
                if asset:
                    clean_ver = tag_name.lstrip('vV')
                    info = UpdateInfo(
                        version=clean_ver,
                        tag_name=tag_name,
                        asset_name=asset.get('name', 'RaidR.exe'),
                        download_url=asset.get('browser_download_url', ''),
                        asset_size=int(asset.get('size', 0)),
                        release_notes=data.get('body', '') or 'No release notes provided.',
                        published_at=data.get('published_at', ''),
                        html_url=data.get('html_url', '')
                    )
                    self.updateAvailable.emit(info)
                    return

            self.upToDate.emit(self.current_version)
        except Exception as e:
            self.checkFailed.emit(str(e))


class UpdateDownloadThread(QThread):
    """Asynchronously downloads the new executable with progress telemetry."""
    progress = Signal(int, int)       # (downloaded_bytes, total_bytes)
    finished = Signal(str)            # downloaded_file_path
    error = Signal(str)               # error_msg

    def __init__(self, download_url: str, total_size: int, target_path: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.total_size = total_size
        self.target_path = target_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            os.makedirs(os.path.dirname(self.target_path), exist_ok=True)
            req = urllib.request.Request(
                self.download_url,
                headers={'User-Agent': 'RaidR-Updater'}
            )
            downloaded = 0
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get('content-length', self.total_size))
                with open(self.target_path, 'wb') as fp:
                    while True:
                        if self._cancelled:
                            fp.close()
                            if os.path.exists(self.target_path):
                                os.remove(self.target_path)
                            return
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        fp.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)

            self.finished.emit(self.target_path)
        except Exception as e:
            self.error.emit(str(e))


def launch_self_update_and_restart(downloaded_file: str) -> bool:
    """
    Schedules an in-place executable replacement and restarts into the updated version.
    """
    try:
        if getattr(sys, 'frozen', False):
            target_exe = os.path.abspath(sys.executable)
        else:
            # Development mode: default to dist/RaidR.exe
            target_exe = os.path.abspath('dist/RaidR.exe')

        pid = os.getpid()
        temp_dir = tempfile.gettempdir()
        bat_path = os.path.join(temp_dir, f"raidr_update_{pid}.bat")

        # The batch script waits until current PID exits, then overwrites target_exe and relaunches it.
        script_content = f"""@echo off
chcp 65001 > nul
set PID={pid}
set NEW_EXE="{downloaded_file}"
set TARGET_EXE="{target_exe}"

:wait_pid
tasklist /fi "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_pid
)

timeout /t 1 /nobreak >nul

copy /y %NEW_EXE% %TARGET_EXE% >nul 2>&1
if errorlevel 1 (
    move /y %NEW_EXE% %TARGET_EXE% >nul 2>&1
) else (
    del /f /q %NEW_EXE% >nul 2>&1
)

start "" %TARGET_EXE%
del "%~f0" >nul 2>&1
"""

        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # Launch detached batch script
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        flags = CREATE_NO_WINDOW | DETACHED_PROCESS

        subprocess.Popen(
            ['cmd.exe', '/c', bat_path],
            creationflags=flags,
            close_fds=True
        )

        QApplication.quit()
        return True
    except Exception as e:
        print(f"Failed to launch in-place updater: {e}")
        return False
