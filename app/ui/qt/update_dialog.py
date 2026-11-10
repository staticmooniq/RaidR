"""
RaidR — Visual Auto-Updater UI Components.
Includes the dismissible top notification banner and the full in-app updater modal dialog.
"""
from __future__ import annotations

import os
import tempfile
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget, QMessageBox
)

from app import __version__
from app.services.updater import (
    UpdateInfo, UpdateDownloadThread, launch_self_update_and_restart
)
from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import Card, chip_button, primary_button, neutral_button


def _format_markdown_notes(raw: str) -> str:
    lines = []
    in_list = False
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith('### '):
            if in_list:
                lines.append('</ul>')
                in_list = False
            lines.append(f"<h4 style='margin: 8px 0 4px 0; color: {TOKENS.get('primary', '#E11D48')}; font-size: 13px;'>{line[4:]}</h4>")
        elif line.startswith('## '):
            if in_list:
                lines.append('</ul>')
                in_list = False
            lines.append(f"<h3 style='margin: 10px 0 6px 0; color: {TOKENS.get('primary', '#E11D48')}; font-size: 14px;'>{line[3:]}</h3>")
        elif line.startswith('- ') or line.startswith('* '):
            if not in_list:
                lines.append("<ul style='margin: 4px 0 8px 16px; padding: 0;'>")
                in_list = True
            lines.append(f"<li style='margin-bottom: 4px;'>{line[2:]}</li>")
        elif line:
            if in_list:
                lines.append('</ul>')
                in_list = False
            lines.append(f"<p style='margin: 4px 0;'>{line}</p>")
    if in_list:
        lines.append('</ul>')
    return ''.join(lines)


class UpdateBannerWidget(QFrame):
    """
    Sleek, dismissible banner that appears directly beneath the top navigation bar
    when a new GitHub release is detected.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('UpdateBanner')
        self._info: Optional[UpdateInfo] = None
        self.setFixedHeight(44)
        self.setVisible(False)

        # Style with subtle translucent accent gradient
        primary = TOKENS.get('primary', '#E11D48')
        bg_surface = TOKENS.get('surface_hi', 'rgba(30, 41, 59, 0.95)')
        border_col = TOKENS.get('border_hi', '#3E4D66')
        text_col = TOKENS.get('text', '#FFFFFF')

        self.setStyleSheet(f"""
            QFrame#UpdateBanner {{
                background: {bg_surface};
                border-bottom: 1px solid {primary};
                border-top: 1px solid {border_col};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 4, 16, 4)
        layout.setSpacing(12)

        # Icon / Badge
        self._icon_lbl = QLabel('🚀')
        self._icon_lbl.setStyleSheet("font-size: 16px;")
        layout.addWidget(self._icon_lbl)

        # Text message
        self._msg_lbl = QLabel('A new version of RaidR is available!')
        self._msg_lbl.setStyleSheet(f"color: {text_col}; font-size: 12px; font-weight: 600;")
        layout.addWidget(self._msg_lbl)

        layout.addStretch()

        # Update Now button
        self._btn_update = primary_button('Update Now', parent=self)
        self._btn_update.setFixedHeight(28)
        self._btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_update.clicked.connect(self._open_update_dialog)
        layout.addWidget(self._btn_update)

        # Dismiss button (x)
        self._btn_close = QPushButton('✕')
        self._btn_close.setFixedSize(22, 22)
        self._btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TOKENS.get('text_muted', '#8FA0B8')};
                border: none;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #FFFFFF;
            }}
        """)
        self._btn_close.clicked.connect(self.hide)
        layout.addWidget(self._btn_close)

    def set_update_info(self, info: UpdateInfo):
        self._info = info
        self._msg_lbl.setText(f"Update Available: RaidR v{info.version} is ready to install (current: v{__version__})")
        self.setVisible(True)

    def _open_update_dialog(self):
        if not self._info:
            return
        dlg = UpdateDialog(self._info, parent=self.window())
        dlg.exec()


class UpdateDialog(QDialog):
    """
    Modern in-app updater dialog.
    Displays release notes and automatically downloads and applies the new version in-place.
    """
    def __init__(self, info: UpdateInfo, parent=None):
        super().__init__(parent)
        self._info = info
        self._download_thread: Optional[UpdateDownloadThread] = None

        self.setWindowTitle(f"RaidR v{info.version} Update")
        self.resize(560, 440)
        self.setMinimumSize(480, 360)

        bg_col = TOKENS.get('bg_c1', '#11151C')
        text_col = TOKENS.get('text', '#FFFFFF')
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_col};
                color: {text_col};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        layout.setSpacing(14)

        # Header Card
        card_header = Card(parent=self)
        header_layout = card_header.card_layout
        header_layout.setSpacing(6)

        title = QLabel(f"✨ RaidR v{self._info.version} is Available")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {TOKENS.get('primary', '#E11D48')};")
        header_layout.addWidget(title)

        sub = QLabel(f"Installed version: v{__version__}  ➔  Latest release: v{self._info.version}")
        sub.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        header_layout.addWidget(sub)

        size_mb = round(self._info.asset_size / (1024 * 1024), 1)
        meta = QLabel(f"Asset: {self._info.asset_name} ({size_mb} MB)")
        meta.setStyleSheet(f"font-size: 11px; color: {TOKENS.get('text_faint', '#4B5563')};")
        header_layout.addWidget(meta)

        layout.addWidget(card_header)

        # Release Notes Label
        lbl_notes = QLabel("RELEASE NOTES")
        lbl_notes.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        layout.addWidget(lbl_notes)

        # Release Notes Browser
        self._notes_browser = QTextBrowser()
        self._notes_browser.setOpenExternalLinks(True)
        # Format release notes with line breaks and styling
        formatted_notes = _format_markdown_notes(self._info.release_notes)
        self._notes_browser.setHtml(f"""
            <div style="font-family: sans-serif; font-size: 12px; color: {TOKENS.get('text', '#E2E8F0')}; line-height: 1.5;">
                {formatted_notes}
            </div>
        """)
        self._notes_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {TOKENS.get('surface_hi', '#1E293B')};
                border: 1px solid {TOKENS.get('border_hi', '#3E4D66')};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout.addWidget(self._notes_browser, stretch=1)

        # Download Progress Area (Hidden initially)
        self._progress_container = QWidget()
        progress_layout = QVBoxLayout(self._progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(6)

        self._lbl_progress = QLabel("Downloading update...")
        self._lbl_progress.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TOKENS.get('text', '#FFFFFF')};")
        progress_layout.addWidget(self._lbl_progress)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(18)
        self._bar.setTextVisible(True)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {TOKENS.get('surface_hi', '#1E293B')};
                border: 1px solid {TOKENS.get('border_hi', '#3E4D66')};
                border-radius: 9px;
                text-align: center;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: {TOKENS.get('primary', '#E11D48')};
                border-radius: 8px;
            }}
        """)
        progress_layout.addWidget(self._bar)
        self._progress_container.setVisible(False)
        layout.addWidget(self._progress_container)

        # Bottom Button Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self._btn_cancel = neutral_button("Remind Me Later", parent=self)
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)

        self._btn_install = primary_button("Download and Restart", parent=self)
        self._btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_install.clicked.connect(self._start_download)
        btn_row.addWidget(self._btn_install)

        layout.addLayout(btn_row)

    def _start_download(self):
        self._btn_install.setEnabled(False)
        self._btn_cancel.setText("Cancel Download")
        self._progress_container.setVisible(True)

        temp_dir = tempfile.gettempdir()
        target_path = os.path.join(temp_dir, f"RaidR_v{self._info.version}.exe")

        self._download_thread = UpdateDownloadThread(
            download_url=self._info.download_url,
            total_size=self._info.asset_size,
            target_path=target_path,
            parent=self
        )
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.error.connect(self._on_download_error)
        self._download_thread.start()

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self._bar.setValue(pct)
            down_mb = round(downloaded / (1024 * 1024), 1)
            total_mb = round(total / (1024 * 1024), 1)
            self._lbl_progress.setText(f"Downloading RaidR v{self._info.version}... {pct}% ({down_mb} MB / {total_mb} MB)")

    def _on_download_finished(self, downloaded_file: str):
        self._bar.setValue(100)
        self._lbl_progress.setText("Download complete! Applying update and restarting...")
        self._btn_cancel.setEnabled(False)
        self._btn_install.setText("Restarting...")
        # Give user half a second to see 100%, then trigger in-place restart
        from PySide6.QtCore import QTimer
        QTimer.singleShot(600, lambda: launch_self_update_and_restart(downloaded_file))

    def _on_download_error(self, err_msg: str):
        self._progress_container.setVisible(False)
        self._btn_install.setEnabled(True)
        self._btn_cancel.setText("Close")
        QMessageBox.critical(self, "Update Download Failed", f"Could not download update:\n{err_msg}")

    def _on_cancel(self):
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait(1000)
        self.reject()

    def closeEvent(self, event):
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait(1000)
        event.accept()
