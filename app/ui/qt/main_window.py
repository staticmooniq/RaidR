'''Main application window — Horizontal Frosted Glass Shell.'''
from __future__ import annotations
import platform
import sys
from PySide6.QtCore import QSettings, QTimer, Qt, QPropertyAnimation, QEasingCurve, QUrl
from PySide6.QtGui import QCloseEvent, QPainter, QLinearGradient, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget, QButtonGroup, QPushButton, QFrame,
    QGraphicsOpacityEffect
)
from app import __version__
from app.services.updater import UpdateCheckerThread, UpdateInfo
from app.ui.qt.branding import apply_app_icon, logo_pixmap
from app.ui.qt.bot_controller import BotController
from app.ui.qt.dialogs import show_error
from app.ui.qt.pages.logs import LogsPage
from app.ui.qt.pages.run import RunPage
from app.ui.qt.pages.settings import SettingsPage
from app.ui.qt.taskbar_thumb_qt import QtTaskbarThumb
from app.ui.qt.theme import TOKENS, WINDOW_DEFAULT, WINDOW_MIN, NAV_HEIGHT
from app.ui.qt.touch_overlay import TouchOverlay
from app.ui.qt.update_dialog import UpdateBannerWidget

PAGE_KEYS = [
    'run',
    'settings',
    'logs'
]
PAGE_LABELS = [
    'Run',
    'Settings',
    'Logs'
]


class _FrostedContainer(QWidget):
    """Background container providing a sleek dark canvas matching the reference theme."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        c1 = TOKENS.get('bg_c1', '#11151C')
        c2 = TOKENS.get('bg_c2', '#151A24')
        c3 = TOKENS.get('bg_c3', '#121620')
        grad.setColorAt(0.0, QColor(c1))
        grad.setColorAt(0.5, QColor(c2))
        grad.setColorAt(1.0, QColor(c3))
        painter.fillRect(self.rect(), grad)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('RaidR')
        self.resize(*WINDOW_DEFAULT)
        self.setMinimumSize(*WINDOW_MIN)
        self._settings = QSettings('RaidR', 'UI')
        self._migrate_legacy_ui_settings()
        self._controller = BotController(bot_version=__version__)
        self._overlay = TouchOverlay(self._controller._bot.window)
        self._controller.touchOccurred.connect(self._overlay.add_touch)
        self._taskbar = None
        self._taskbar_setup_attempts = 0
        self._taskbar_setup_done = False

        central = _FrostedContainer()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Horizontal Top Navigation Bar
        navbar = QFrame()
        navbar.setObjectName('NavBar')
        navbar.setFixedHeight(NAV_HEIGHT)
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(12)

        # Brand (Logo removed)
        self._brand_label = QLabel(f'''<span style="color:{TOKENS['primary']}">Raid</span><span style="color:{TOKENS['text']}">R</span>''')
        self._brand_label.setObjectName('Brand')
        self._brand_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        nav_layout.addWidget(self._brand_label)

        nav_layout.addSpacing(24)

        # Top Horizontal Tabs
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons = []

        for i, label in enumerate(PAGE_LABELS):
            btn = QPushButton(label)
            btn.setProperty('role', 'nav_tab')
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            self._nav_group.addButton(btn, i)
            self._nav_buttons.append(btn)
            nav_layout.addWidget(btn)

        nav_layout.addStretch()

        # Update Available Button in NavBar (hidden until update detected)
        self._nav_update_btn = QPushButton("Update Available ✨")
        self._nav_update_btn.setProperty("role", "nav_tab")
        self._nav_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nav_update_btn.setVisible(False)
        self._nav_update_btn.setStyleSheet(f"""
            QPushButton {{
                background: {TOKENS.get('primary', '#E11D48')};
                color: {TOKENS.get('on_primary', '#FFFFFF')};
                border: 1px solid rgba(255, 255, 255, 0.35);
                border-radius: 9px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                filter: brightness(1.15);
            }}
        """)
        self._nav_update_btn.clicked.connect(lambda: self._update_banner._open_update_dialog())
        nav_layout.addWidget(self._nav_update_btn)

        # Join Discord Button
        self._discord_btn = QPushButton("Join Discord")
        self._discord_btn.setProperty("role", "nav_tab")
        self._discord_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._discord_btn.setToolTip("Join our Discord community: https://discord.gg/TWwc4W6eMq")
        self._discord_btn.setStyleSheet("""
            QPushButton {
                background: rgba(88, 101, 242, 0.15);
                color: #FFFFFF;
                border: 1px solid rgba(88, 101, 242, 0.45);
                border-radius: 9px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #5865F2;
                color: #FFFFFF;
                border: 1px solid #7983F5;
            }
            QPushButton:pressed {
                background: #4752C4;
            }
        """)
        self._discord_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/TWwc4W6eMq")))
        nav_layout.addWidget(self._discord_btn)
        nav_layout.addSpacing(10)

        # Launch Game Button in Navbar
        self._nav_launch_btn = QPushButton("🎮 Launch Game")
        self._nav_launch_btn.setProperty("role", "nav_tab")
        self._nav_launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nav_launch_btn.setToolTip("Launch Clash of Clans via Google Play Games PC")
        self._nav_launch_btn.setStyleSheet("""
            QPushButton {
                background: rgba(34, 197, 94, 0.15);
                color: #22C55E;
                border: 1px solid rgba(34, 197, 94, 0.45);
                border-radius: 9px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(34, 197, 94, 0.28);
                color: #4ADE80;
                border: 1px solid rgba(34, 197, 94, 0.65);
            }
            QPushButton:pressed {
                background: rgba(34, 197, 94, 0.4);
            }
        """)
        self._nav_launch_btn.clicked.connect(self._launch_game_from_nav)
        nav_layout.addWidget(self._nav_launch_btn)
        nav_layout.addSpacing(10)

        root.addWidget(navbar)

        # Update Banner placed right below navbar
        self._update_banner = UpdateBannerWidget(parent=self)
        root.addWidget(self._update_banner)

        # Stacked Pages
        self._stack = QStackedWidget()
        self._run_page = RunPage(self._controller, self.navigate_to)
        self._settings_page = SettingsPage()
        self._logs_page = LogsPage()
        for page in (self._run_page, self._settings_page, self._logs_page):
            self._stack.addWidget(page)
        root.addWidget(self._stack, stretch=1)

        # Place the Village Selector on the right side of the top navbar
        self._village_selector = self._run_page.get_village_selector_widget()
        nav_layout.addWidget(self._village_selector)

        self._build_status_bar()
        self._wire_signals()

        self._nav_group.idClicked.connect(self._on_tab_changed)
        self._restore_geometry()

        # Background update checker (checks GitHub releases 1.5s after launch)
        self._update_checker = UpdateCheckerThread(current_version=__version__, parent=self)
        self._update_checker.updateAvailable.connect(self._on_update_available)
        self._update_checker.upToDate.connect(self._on_up_to_date)
        QTimer.singleShot(1500, self._update_checker.start)

    def _on_update_available(self, info: UpdateInfo):
        self._update_banner.set_update_info(info)
        self._nav_update_btn.setText(f"Update to v{info.version} ✨")
        self._nav_update_btn.setVisible(True)
        if hasattr(self, '_settings_page'):
            self._settings_page.notify_update_available(info)

    def _on_up_to_date(self, current_ver: str):
        if hasattr(self, '_settings_page'):
            self._settings_page.notify_up_to_date(current_ver)

    def _on_tab_changed(self, index: int):
        if hasattr(self, '_village_selector'):
            # Only show village selector on Run tab (index 0)
            self._village_selector.setVisible(index == 0)

        if index == self._stack.currentIndex():
            return
        
        self._stack.setCurrentIndex(index)

    def _migrate_legacy_ui_settings(self):
        '''One-time QSettings migration from the pre-rebrand org name.'''
        if self._settings.contains('geometry'):
            return None
        legacy = QSettings('ClashAutoLoot', 'UI')
        for key in ('geometry', 'windowState', 'run/autoUpgrade', 'run/upgradeWalls', 'run/untilMaxed', 'run/minutes'):
            if legacy.contains(key):
                self._settings.setValue(key, legacy.value(key))

    def _launch_game_from_nav(self):
        success, msg = self._controller.launch_game()
        self._status_label.setText(f"🎮 {msg}")

    def _build_status_bar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        self._status_label = QLabel('Ready')
        self._status_label.setStyleSheet(f'''color: {TOKENS['text_muted']}; font-weight: 600; padding-left: 8px;''')
        bar.addWidget(self._status_label, stretch=1)
        
        engine_lbl = QLabel('Google Play Games (PC)')
        engine_lbl.setStyleSheet(f'''color: {TOKENS['text_faint']}; font-size: 10px; padding-right: 8px;''')
        bar.addPermanentWidget(engine_lbl)

    def _wire_signals(self):
        self._controller.statusChanged.connect(self._on_status)
        self._controller.botStarted.connect(self._on_bot_started_status)
        self._controller.botFinished.connect(self._on_bot_finished)
        self._controller.runningChanged.connect(self._on_running_changed)

    def navigate_to(self, page_key):
        if page_key in PAGE_KEYS:
            idx = PAGE_KEYS.index(page_key)
            self._nav_buttons[idx].setChecked(True)
            self._on_tab_changed(idx)

    def autostart_run(self, minutes, upgrade_walls, auto_upgrade='off'):
        '''CLI ``--autostart``: configure the Run page and press Start.'''
        self._run_page.apply_autostart(minutes, upgrade_walls, auto_upgrade)

    def _restore_geometry(self):
        geo = self._settings.value('geometry')
        if geo is not None:
            self.restoreGeometry(geo)
        state = self._settings.value('windowState')
        if state is not None:
            self.restoreState(state)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._taskbar_setup_done:
            QTimer.singleShot(500, self._setup_taskbar_thumb)

    def closeEvent(self, event):
        if hasattr(self, '_overlay'):
            self._overlay.stop()
        if self._controller.is_running():
            self._controller.stop()
        if self._taskbar is not None:
            self._taskbar.teardown()
        if hasattr(self, '_run_page'):
            self._run_page._save_choices()
        self._settings.setValue('geometry', self.saveGeometry())
        self._settings.setValue('windowState', self.saveState())
        event.accept()

    def _setup_taskbar_thumb(self):
        if self._taskbar_setup_done or platform.system() != 'Windows':
            return None

        try:
            self._taskbar = QtTaskbarThumb(self._controller, self._run_page, parent=self)
            if self._taskbar.setup(self):
                self._taskbar.set_running(self._controller.is_running())
                self._taskbar_setup_done = True
                return None
            self._taskbar = None
            return None
        except Exception:
            self._taskbar = None
            return None

    def _on_status(self, msg, warning):
        color = TOKENS['danger'] if warning else TOKENS['text_muted']
        self._status_label.setText(msg)
        self._status_label.setStyleSheet(f'''color: {color}; font-weight: 600; padding-left: 8px;''')

    def _on_bot_started_status(self):
        if hasattr(self, '_overlay'):
            overlay_enabled = self._settings.value('overlay/enabled', True, type=bool)
            if overlay_enabled:
                self._overlay.start()
            else:
                self._overlay.stop()
        if self._run_page.is_star_bonus_enabled():
            self._status_label.setText('Star Bonus...')
        else:
            self._status_label.setText('Running...')
        self._status_label.setStyleSheet(f'''color: {TOKENS['primary']}; font-weight: 600; padding-left: 8px;''')

    def _on_bot_finished(self, error_msg):
        if hasattr(self, '_overlay'):
            self._overlay.stop()
        self._controller.on_bot_finished()
        if self._taskbar is not None:
            self._taskbar.set_running(False)
        if error_msg:
            preview = error_msg[:50] + '...' if len(error_msg) > 50 else error_msg
            self._status_label.setText(f'''Error: {preview}''')
            self._status_label.setStyleSheet(f'''color: {TOKENS['danger']}; font-weight: 600; padding-left: 8px;''')
            show_error(self, 'Error', str(error_msg))
            return None
        self._status_label.setText('Stopped')
        self._status_label.setStyleSheet(f'''color: {TOKENS['text_muted']}; font-weight: 600; padding-left: 8px;''')
        if sys.platform == 'win32':
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

    def _on_running_changed(self, running):
        if self._taskbar is not None:
            self._taskbar.set_running(running)
