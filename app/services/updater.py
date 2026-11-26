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
            with urllib.request.urlopen(req, timeout=45) as resp:
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

            # Verification: ensure file was completely downloaded and valid
            if not os.path.exists(self.target_path):
                raise RuntimeError("Downloaded executable file not found on disk.")

            actual_size = os.path.getsize(self.target_path)
            if total > 0 and downloaded < total:
                raise RuntimeError(f"Download incomplete: received {downloaded} of {total} bytes.")
            if actual_size < 10_000_000:
                raise RuntimeError(f"Downloaded file is suspiciously small ({actual_size} bytes). Update aborted.")

            # Check PE magic header (MZ)
            with open(self.target_path, 'rb') as fp:
                magic = fp.read(2)
                if magic != b'MZ':
                    raise RuntimeError("Downloaded file does not have a valid Windows executable signature.")

            self.finished.emit(self.target_path)
        except Exception as e:
            if os.path.exists(self.target_path):
                try:
                    os.remove(self.target_path)
                except Exception:
                    pass
            self.error.emit(str(e))


def launch_self_update_and_restart(downloaded_file: str) -> bool:
    """
    Schedules an in-place executable replacement and restarts into the updated version.
    Uses PowerShell in the background with a sanitized environment so child processes
    do not inherit PyInstaller temporary extraction directories (_MEIPASS2 / _PYI_*).
    """
    try:
        if getattr(sys, 'frozen', False):
            target_exe = os.path.abspath(sys.executable)
        else:
            # Development mode: default to dist/RaidR.exe
            target_exe = os.path.abspath('dist/RaidR.exe')

        pid = os.getpid()
        temp_dir = tempfile.gettempdir()
        ps1_path = os.path.join(temp_dir, f"raidr_update_{pid}.ps1")

        # Escaped paths for PowerShell single quotes
        ps_new = downloaded_file.replace("'", "''")
        ps_target = target_exe.replace("'", "''")

        script_content = f"""# RaidR in-place updater
# Strip any inherited PyInstaller bootloader environment variables immediately
Remove-Item env:_MEIPASS* -ErrorAction SilentlyContinue
Remove-Item env:_PYI* -ErrorAction SilentlyContinue
Get-ChildItem env: | Where-Object {{ $_.Name -like "*MEI*" -or $_.Name -like "*PYI*" }} | ForEach-Object {{ Remove-Item "env:$($_.Name)" -ErrorAction SilentlyContinue }}

$targetPid = {pid}
$newExe = '{ps_new}'
$targetExe = '{ps_target}'

# Wait for parent PID to exit (up to 30 seconds)
$timeout = 0
while ((Get-Process -Id $targetPid -ErrorAction SilentlyContinue) -and ($timeout -lt 60)) {{
    Start-Sleep -Milliseconds 500
    $timeout++
}}

# Allow Windows handles and temporary PyInstaller directories to fully close & release
Start-Sleep -Milliseconds 1500

# Overwrite target executable with retry loop
$replaced = $false
for ($i = 0; $i -lt 10; $i++) {{
    try {{
        Copy-Item -Path $newExe -Destination $targetExe -Force -ErrorAction Stop
        $replaced = $true
        break
    }} catch {{
        Start-Sleep -Milliseconds 500
    }}
}}

if (-not $replaced) {{
    try {{
        Move-Item -Path $newExe -Destination $targetExe -Force -ErrorAction Stop
        $replaced = $true
    }} catch {{
        # Fallback failed
    }}
}}

# Clean up downloaded temp file if Copy-Item was used
if (Test-Path $newExe) {{
    Remove-Item -Path $newExe -Force -ErrorAction SilentlyContinue
}}

# Strip environment variables again right before launching new executable
Remove-Item env:_MEIPASS* -ErrorAction SilentlyContinue
Remove-Item env:_PYI* -ErrorAction SilentlyContinue
Get-ChildItem env: | Where-Object {{ $_.Name -like "*MEI*" -or $_.Name -like "*PYI*" }} | ForEach-Object {{ Remove-Item "env:$($_.Name)" -ErrorAction SilentlyContinue }}

# Relaunch the updated app in clean working directory
if (Test-Path $targetExe) {{
    Start-Process -FilePath $targetExe -WorkingDirectory (Split-Path -Parent $targetExe) -WindowStyle Normal
}}

# Self-destruct updater script
Remove-Item -Path $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
"""

        with open(ps1_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # Build clean environment without PyInstaller variables
        clean_env = os.environ.copy()
        for k in list(clean_env.keys()):
            if 'MEI' in k or 'PYI' in k or k in ('_MEIPASS2', '_MEIPASS'):
                del clean_env[k]

        # Launch detached hidden PowerShell script with independent process group
        CREATE_NO_WINDOW = 0x08000000
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        flags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            [
                'powershell.exe',
                '-NoProfile',
                '-NonInteractive',
                '-WindowStyle', 'Hidden',
                '-ExecutionPolicy', 'Bypass',
                '-File', ps1_path
            ],
            creationflags=flags,
            env=clean_env,
            close_fds=True
        )

        # Force immediate exit so executable file locks are instantly released
        os._exit(0)
        return True
    except Exception as e:
        print(f"Failed to launch in-place updater: {e}")
        return False
