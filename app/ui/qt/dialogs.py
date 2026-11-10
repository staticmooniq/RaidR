'''Modal dialogs for the Qt UI.'''
from __future__ import annotations
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QTextBrowser
from app import __version__
from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import danger_button, neutral_button

def show_error(parent, title, message):
    QMessageBox.critical(parent, title, message)


def show_under_development(parent):
    QMessageBox.information(parent, 'Under development', 'This feature is under development.')


def show_bb_prioritise_help(parent):
    QMessageBox.information(parent, 'Prioritise loot', 'Choose what the bot optimises for after each attack:\n\n• Gold — waits until 2 stars, then ends the battle.\n• Both — waits until 1 star, then ends the battle.\n• Elixir — surrenders immediately after deploying troops.')


class RankedAttackConfirmDialog(QDialog):

    def __init__(self, parent, minutes):
        super().__init__(parent)
        self.setWindowTitle('Ranked attack fill')
        self.setModal(True)
        self._remaining = 5
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_countdown)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        msg = f'''The bot will use up your ranked attacks up to {minutes} minutes, are you sure you want to continue?'''
        label = QLabel(msg)
        label.setWordWrap(True)
        label.setStyleSheet(f'''color: {TOKENS['text']};''')
        layout.addWidget(label)
        row = QHBoxLayout()
        row.addStretch()
        self._btn_no = neutral_button('No', parent = self)
        self._btn_no.clicked.connect(self.reject)
        row.addWidget(self._btn_no)
        self._btn_yes = danger_button('Yes (5)', parent = self)
        self._btn_yes.setEnabled(False)
        self._btn_yes.clicked.connect(self.accept)
        row.addWidget(self._btn_yes)
        layout.addLayout(row)
        self._tick_countdown()
        self._timer.start()


    def _tick_countdown(self):
        if self._remaining > 0:
            self._btn_yes.setText(f'''Yes ({self._remaining})''')
            self._btn_yes.setEnabled(False)
            self._remaining -= 1
            return None
        self._timer.stop()
        self._btn_yes.setText('Yes')
        self._btn_yes.setEnabled(True)


    @classmethod
    def ask(cls, parent, minutes):
        dlg = cls(parent, minutes)
        return dlg.exec() == QDialog.Accepted


class ChangelogDialog(QDialog):
    """Modal dialog displaying RaidR version changelog and release history."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"RaidR v{__version__} — Changelog")
        self.resize(540, 480)
        self.setMinimumSize(440, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        layout.setSpacing(12)

        title = QLabel(f"🚀 What's New in RaidR v{__version__}")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {TOKENS.get('primary', '#E11D48')};")
        layout.addWidget(title)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        html = self._get_changelog_html()
        browser.setHtml(html)
        browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {TOKENS.get('surface_hi', '#1E293B')};
                border: 1px solid {TOKENS.get('border_hi', '#3E4D66')};
                border-radius: 8px;
                padding: 12px;
                color: {TOKENS.get('text', '#E2E8F0')};
            }}
        """)
        layout.addWidget(browser, stretch=1)

        row = QHBoxLayout()
        row.addStretch()
        btn_close = neutral_button('Close', parent=self)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_close)
        layout.addLayout(row)

    def _get_changelog_html(self) -> str:
        return f"""
        <div style='font-family: sans-serif; font-size: 12px; line-height: 1.6; color: {TOKENS.get('text', '#E2E8F0')};'>
            <h3 style='color: {TOKENS.get('primary', '#E11D48')}; margin-bottom: 4px;'>Version 1.1 (Current)</h3>
            <ul>
                <li><b>Text-Only Wall Action Templates:</b> Replaced level-dependent wall templates with clean text-only crops for 'Upgrade More', 'Add Wall', and 'Remove Wall' to guarantee 100% accuracy across all wall levels.</li>
                <li><b>5-Wall Batch Upgrading:</b> Configured Builder Base wall upgrading to upgrade in batches of 5 walls per pass.</li>
                <li><b>Strict Anti-Inactivity Zoom:</b> Implemented 2-minute random zoom in/out keep-alive cycles to prevent game disconnection and inactivity logout.</li>
                <li><b>Automatic Bundled Tesseract Discovery:</b> Automatically resolves the bundled Tesseract OCR binaries in both source and frozen environments.</li>
                <li><b>Standalone Wall Runner:</b> Added <code>--bb-walls-only</code> CLI flag for dedicated Builder Base wall automation.</li>
            </ul>

            <h3 style='color: {TOKENS.get('text_muted', '#8FA0B8')}; margin-bottom: 4px; margin-top: 14px;'>Version 1.0.2</h3>
            <ul>
                <li>Matchmaking resource loot thresholds and skip limits.</li>
                <li>HUD optical telemetry and live gain rates.</li>
                <li>Automatic Clan Capital screen recovery.</li>
            </ul>

            <h3 style='color: {TOKENS.get('text_muted', '#8FA0B8')}; margin-bottom: 4px; margin-top: 14px;'>Version 1.0.1</h3>
            <ul>
                <li>Integrated in-app auto-updater and silent updater script.</li>
                <li>Taskbar thumbnail preview on Windows 10/11.</li>
            </ul>
        </div>
        """
