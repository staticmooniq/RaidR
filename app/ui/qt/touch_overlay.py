'''Transparent, click-through overlay window to visualize bot touches & drags in game.'''
from __future__ import annotations
import ctypes
from ctypes import wintypes
import time
from typing import List, Tuple
from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget
from app.services.window import WindowService
from app.ui.qt.theme import TOKENS
from app.utils.logger import setup_logger

logger = setup_logger('TouchOverlay')

# Win32 Constants for click-through layered transparent window
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
GWL_EXSTYLE = -20


class Ripple:
    __slots__ = ('x', 'y', 'start_time', 'duration', 'max_radius', 'color_rgb')

    def __init__(self, x: float, y: float, duration: float = 0.45, max_radius: float = 34.0, color_rgb: Tuple[int, int, int] = (92, 181, 255)):
        self.x = x
        self.y = y
        self.start_time = time.perf_counter()
        self.duration = duration
        self.max_radius = max_radius
        self.color_rgb = color_rgb

    @property
    def progress(self) -> float:
        return (time.perf_counter() - self.start_time) / self.duration

    @property
    def is_alive(self) -> bool:
        return self.progress < 1.0


class TouchOverlay(QWidget):
    """
    Transparent, click-through window positioned exactly over the target game client.
    Renders sleek, glowing ripples whenever the bot clicks, drags, or moves.
    """

    def __init__(self, window_service: WindowService, parent=None):
        super().__init__(parent)
        self.window_service = window_service
        self._ripples: List[Ripple] = []
        self._active = False

        # Configure transparent, always-on-top, non-activating window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Repaint timer (~60 FPS when ripples are active)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_frame)

        # Sync geometry timer with the game window (100ms)
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(100)
        self._sync_timer.timeout.connect(self._sync_geometry)

    def start(self):
        self._active = True
        self._sync_geometry()
        self.show()
        self._make_click_through()
        self._sync_timer.start()

    def stop(self):
        self._active = False
        self._sync_timer.stop()
        self._anim_timer.stop()
        self._ripples.clear()
        self.hide()

    def add_touch(self, client_x: int, client_y: int, duration: float = 0.45, max_radius: float = 34.0):
        """Called when a bot click or drag event occurs at game client coordinates."""
        if not self._active:
            return

        # Hex primary token to RGB
        hex_col = TOKENS.get('primary', '#5CB5FF').lstrip('#')
        if len(hex_col) == 6:
            r = int(hex_col[0:2], 16)
            g = int(hex_col[2:4], 16)
            b = int(hex_col[4:6], 16)
        else:
            r, g, b = (92, 181, 255)

        self._ripples.append(Ripple(client_x, client_y, duration=duration, max_radius=max_radius, color_rgb=(r, g, b)))
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self.update()

    def _make_click_through(self):
        """Ensure OS level pass-through for all mouse events so bot and user clicks never get blocked."""
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE)
        except Exception as e:
            logger.debug(f"Could not apply win32 click-through flags: {e}")

    def _sync_geometry(self):
        if not self._active:
            return

        hwnd = self.window_service.hwnd
        if not hwnd:
            if not self.window_service.find_window():
                if self.isVisible():
                    self.hide()
                return
            hwnd = self.window_service.hwnd

        rect = wintypes.RECT()
        user32 = ctypes.windll.user32
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return

        # Check if window is minimized
        if rect.left <= -31999 or rect.top <= -31999:
            if self.isVisible():
                self.hide()
            return

        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 10 or h <= 10:
            if self.isVisible():
                self.hide()
            return

        curr_geom = self.geometry()
        if (curr_geom.x() != rect.left or curr_geom.y() != rect.top or
                curr_geom.width() != w or curr_geom.height() != h):
            self.setGeometry(rect.left, rect.top, w, h)
            self._make_click_through()

        if not self.isVisible():
            self.show()
            self._make_click_through()

    def _on_anim_frame(self):
        if not self._ripples:
            self._anim_timer.stop()
            self.update()
            return

        # Retain only alive ripples
        self._ripples = [r for r in self._ripples if r.is_alive]
        self.update()

    def paintEvent(self, event):
        if not self._ripples:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for rip in self._ripples:
            p = rip.progress
            if p >= 1.0:
                continue

            r, g, b = rip.color_rgb
            # Smooth ease-out expansion
            radius = rip.max_radius * (1.0 - (1.0 - p) ** 2)
            alpha = int(220 * (1.0 - p))
            ring_alpha = int(255 * (1.0 - p))

            # Outer expanding glow ring
            pen = QPen(QColor(r, g, b, ring_alpha))
            pen.setWidthF(max(1.5, 3.0 * (1.0 - p)))
            painter.setPen(pen)

            # Radial glow gradient fill
            grad = QRadialGradient(rip.x, rip.y, max(1.0, radius))
            grad.setColorAt(0.0, QColor(r, g, b, int(alpha * 0.7)))
            grad.setColorAt(0.4, QColor(r, g, b, int(alpha * 0.4)))
            grad.setColorAt(0.8, QColor(r, g, b, int(alpha * 0.1)))
            grad.setColorAt(1.0, QColor(r, g, b, 0))
            painter.setBrush(QBrush(grad))

            painter.drawEllipse(QPoint(int(rip.x), int(rip.y)), int(radius), int(radius))

            # Inner bright core dot
            core_alpha = int(255 * (1.0 - p * 0.7))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, core_alpha))
            core_radius = max(2.0, 5.0 * (1.0 - p))
            painter.drawEllipse(QPoint(int(rip.x), int(rip.y)), int(core_radius), int(core_radius))

        painter.end()
