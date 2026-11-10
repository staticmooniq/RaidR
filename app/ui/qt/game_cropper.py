"""Interactive in-game snip / crop tool to accurately capture troop deployment icons."""
from __future__ import annotations
import cv2
import numpy as np
from typing import Optional, Tuple
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QCursor, QFont
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget

from app.services.window import WindowService
from app.ui.qt.theme import TOKENS


def cv2_to_qimage(cv_img: np.ndarray) -> QImage:
    """Converts a BGR or RGB cv2/numpy image to QImage."""
    if cv_img is None or len(cv_img.shape) < 2:
        return QImage()
    if len(cv_img.shape) == 2:
        h, w = cv_img.shape
        return QImage(cv_img.data, w, h, w, QImage.Format.Format_Grayscale8).copy()
    h, w, ch = cv_img.shape
    rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    bytes_per_line = ch * w
    return QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()


class SnipCanvas(QWidget):
    """Interactive canvas that displays the game screenshot and lets the user click-and-drag a crop rect."""
    cropFinished = Signal(QImage)

    def __init__(self, full_image: QImage, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._full_image = full_image
        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_selecting = False
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Scale image to canvas if needed, or draw 1:1 with letterbox/fit
        canvas_rect = self.rect()
        if self._full_image.isNull():
            painter.fillRect(canvas_rect, QColor(20, 20, 20))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(canvas_rect, Qt.AlignmentFlag.AlignCenter, "Could not capture game window.")
            return

        # Fit image maintaining aspect ratio
        img_scaled = self._full_image.scaled(
            canvas_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        # Compute draw offset to center the scaled image
        ox = (canvas_rect.width() - img_scaled.width()) // 2
        oy = (canvas_rect.height() - img_scaled.height()) // 2
        self._draw_rect = QRect(ox, oy, img_scaled.width(), img_scaled.height())

        painter.drawImage(self._draw_rect, img_scaled)

        # Dark overlay over non-image areas
        painter.fillRect(0, 0, canvas_rect.width(), oy, QColor(0, 0, 0, 180))
        painter.fillRect(0, oy + img_scaled.height(), canvas_rect.width(), canvas_rect.height() - (oy + img_scaled.height()), QColor(0, 0, 0, 180))
        painter.fillRect(0, oy, ox, img_scaled.height(), QColor(0, 0, 0, 180))
        painter.fillRect(ox + img_scaled.width(), oy, canvas_rect.width() - (ox + img_scaled.width()), img_scaled.height(), QColor(0, 0, 0, 180))

        # Selection rectangle
        if self._start_pos and self._current_pos:
            sel_rect = QRect(self._start_pos, self._current_pos).normalized()
            # Intersect with image bounds
            sel_rect = sel_rect.intersected(self._draw_rect)

            # Draw semi-transparent dimming outside the selection inside the image area
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 120))
            # 4 regions around sel_rect within self._draw_rect
            top_h = max(0, sel_rect.top() - self._draw_rect.top())
            painter.drawRect(self._draw_rect.left(), self._draw_rect.top(), self._draw_rect.width(), top_h)
            bot_h = max(0, self._draw_rect.bottom() - sel_rect.bottom())
            painter.drawRect(self._draw_rect.left(), sel_rect.bottom() + 1, self._draw_rect.width(), bot_h)
            painter.drawRect(self._draw_rect.left(), sel_rect.top(), max(0, sel_rect.left() - self._draw_rect.left()), sel_rect.height())
            painter.drawRect(sel_rect.right() + 1, sel_rect.top(), max(0, self._draw_rect.right() - sel_rect.right()), sel_rect.height())

            # Glowing selection border
            pen = QPen(QColor(TOKENS.get('primary', '#2EA7FF')), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sel_rect)

            # Dimensions badge
            orig_w, orig_h = self._map_to_original_dims(sel_rect)
            badge_text = f"{orig_w} × {orig_h} px"
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 20, 28, 220))
            badge_rect = QRect(sel_rect.left(), max(self._draw_rect.top() + 5, sel_rect.top() - 24), 90, 20)
            painter.drawRoundedRect(badge_rect, 4, 4)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

    def _map_to_original_dims(self, sel_rect: QRect) -> Tuple[int, int]:
        if not hasattr(self, '_draw_rect') or self._draw_rect.width() == 0 or self._draw_rect.height() == 0:
            return (0, 0)
        scale_x = self._full_image.width() / float(self._draw_rect.width())
        scale_y = self._full_image.height() / float(self._draw_rect.height())
        return (int(round(sel_rect.width() * scale_x)), int(round(sel_rect.height() * scale_y)))

    def _get_cropped_original(self, sel_rect: QRect) -> QImage:
        scale_x = self._full_image.width() / float(self._draw_rect.width())
        scale_y = self._full_image.height() / float(self._draw_rect.height())

        rx = int(round((sel_rect.left() - self._draw_rect.left()) * scale_x))
        ry = int(round((sel_rect.top() - self._draw_rect.top()) * scale_y))
        rw = int(round(sel_rect.width() * scale_x))
        rh = int(round(sel_rect.height() * scale_y))

        rx = max(0, min(self._full_image.width() - 1, rx))
        ry = max(0, min(self._full_image.height() - 1, ry))
        rw = max(1, min(self._full_image.width() - rx, rw))
        rh = max(1, min(self._full_image.height() - ry, rh))

        return self._full_image.copy(rx, ry, rw, rh)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, '_draw_rect'):
            pt = event.position().toPoint()
            if self._draw_rect.contains(pt):
                self._start_pos = pt
                self._current_pos = pt
                self._is_selecting = True
                self.update()

    def mouseMoveEvent(self, event):
        if self._is_selecting:
            self._current_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            self._current_pos = event.position().toPoint()
            sel_rect = QRect(self._start_pos, self._current_pos).normalized()
            sel_rect = sel_rect.intersected(self._draw_rect)
            if sel_rect.width() > 10 and sel_rect.height() > 10:
                crop = self._get_cropped_original(sel_rect)
                self.cropFinished.emit(crop)
            self.update()


class GameCropWindow(QDialog):
    """
    Dedicated window that grabs a real-time frame from the active target window,
    allowing the user to visually draw a box and crop troop/spell deploy icons directly.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Crop Troop from Game Screen — RaidR')
        self.resize(980, 660)
        self.setMinimumSize(780, 500)
        self.setStyleSheet(f"background-color: {TOKENS.get('bg_c1', '#11151C')}; color: #FFFFFF;")

        self.cropped_image: Optional[QImage] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header bar with instructions and Refresh button
        header = QHBoxLayout()
        header.setSpacing(12)

        info_box = QVBoxLayout()
        info_box.setSpacing(2)
        title_lbl = QLabel("SELECT & CROP TROOP ICON")
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {TOKENS.get('primary', '#2EA7FF')}; letter-spacing: 0.5px;")
        desc_lbl = QLabel("Click and drag over the troop's icon in the deployment bar below. Native 1:1 pixel accuracy.")
        desc_lbl.setStyleSheet("font-size: 11px; color: #8F9BAE;")
        info_box.addWidget(title_lbl)
        info_box.addWidget(desc_lbl)
        header.addLayout(info_box, stretch=1)

        self._btn_refresh = QPushButton("⟳ Refresh Screenshot")
        self._btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: {TOKENS.get('sidebar', '#18202F')};
                border: 1px solid {TOKENS.get('border_hi', '#2B384E')};
                border-radius: 8px;
                padding: 6px 14px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {TOKENS.get('border_hi', '#2B384E')};
                border-color: {TOKENS.get('primary', '#2EA7FF')};
            }}
        """)
        self._btn_refresh.clicked.connect(self._capture_screen)
        header.addWidget(self._btn_refresh)

        layout.addLayout(header)

        # Snip Canvas
        self._canvas_container = QWidget()
        self._canvas_layout = QVBoxLayout(self._canvas_container)
        self._canvas_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas_container, stretch=1)

        # Bottom Action Bar
        bottom = QHBoxLayout()
        self._status_lbl = QLabel("Ready. Drag to select troop icon.")
        self._status_lbl.setStyleSheet("font-size: 11px; color: #8F9BAE;")
        bottom.addWidget(self._status_lbl)
        bottom.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {TOKENS.get('border_hi', '#2B384E')};
                border-radius: 8px;
                padding: 6px 16px;
                color: #FFFFFF;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.05);
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)

        layout.addLayout(bottom)

        self._window_service = WindowService()
        self._capture_screen()

    def _capture_screen(self):
        frame = self._window_service.screenshot()
        if frame is None:
            self._status_lbl.setText("⚠️ Clash of Clans window not found! Open the game and press 'Refresh'.")
            full_img = QImage()
        else:
            h, w = frame.shape[:2]
            self._status_lbl.setText(f"Game window active ({w}×{h} px). Drag a box around the troop icon.")
            full_img = cv2_to_qimage(frame)

        # Clear old canvas
        while self._canvas_layout.count():
            item = self._canvas_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._canvas = SnipCanvas(full_img, parent=self)
        self._canvas.cropFinished.connect(self._on_crop_received)
        self._canvas_layout.addWidget(self._canvas)

    def _on_crop_received(self, cropped: QImage):
        if not cropped.isNull():
            self.cropped_image = cropped
            self.accept()
