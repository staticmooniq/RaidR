'''PySide6 GUI entry point.'''
from __future__ import annotations
import sys
from PySide6.QtCore import QTimer, QSettings
from PySide6.QtWidgets import QApplication
from app.ui.qt.branding import apply_app_icon
from app.ui.qt.main_window import MainWindow
from app.ui.qt.theme import apply_theme

def _parse_autostart(argv):
    '''``--autostart [--builder-base|--bb] [--minutes N] [--walls] [--upgrades off|dry|maxer|rusher]`` ->
    (minutes, walls, upgrades, builder_base) or None. ``--minutes 0`` = run until maxed (no limit).'''
    if '--autostart' not in argv:
        return None
    builder_base = ('--builder-base' in argv or '--bb' in argv)
    minutes = 15
    if '--minutes' in argv:
        try:
            minutes = max(0, min(999, int(argv[argv.index('--minutes') + 1])))
        except (IndexError, ValueError):
            pass
    upgrades = 'off'
    if '--upgrades' in argv:
        try:
            candidate = argv[argv.index('--upgrades') + 1].lower()
            if candidate in ('off', 'dry', 'maxer', 'rusher'):
                upgrades = candidate
        except IndexError:
            pass
    return (minutes, '--walls' in argv or '--bb-walls' in argv, upgrades, builder_base)


def run_gui():
    app = QApplication(sys.argv)
    app.setApplicationName('RaidR')
    apply_app_icon(app)

    settings = QSettings('RaidR', 'UI')
    saved_theme = settings.value('theme/template', 'Electric Blue')
    apply_theme(app, saved_theme)

    window = MainWindow()
    if '--simulate-update' in sys.argv:
        from app.services.updater import UpdateCheckerThread
        window._update_checker = UpdateCheckerThread(current_version='0.9.9', parent=window)
        window._update_checker.updateAvailable.connect(window._on_update_available)
        window._update_checker.upToDate.connect(window._on_up_to_date)
        QTimer.singleShot(1000, window._update_checker.start)
    apply_app_icon(window)
    window.show()
    autostart = _parse_autostart(sys.argv[1:])
    if autostart is not None:
        (minutes, walls, upgrades, builder_base) = autostart
        QTimer.singleShot(3000, (lambda : window.autostart_run(minutes, walls, upgrades, builder_base=builder_base)))
    sys.exit(app.exec())
