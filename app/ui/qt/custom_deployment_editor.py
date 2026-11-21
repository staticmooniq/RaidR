"""Custom Deployment Designer — Interactive canvas for user-drawn deployment lines & points."""
from __future__ import annotations
import math
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from PySide6.QtCore import Qt, QPoint, QRect, QRectF, Signal, QSize
from PySide6.QtGui import (
    QColor, QCursor, QFont, QImage, QPainter, QPainterPath, QPen, QBrush, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDoubleSpinBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget, QButtonGroup
)

from app.services.window import WindowService
from app.services.input import InputService
from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import (
    Card, SectionTitle, chip_button, danger_button, neutral_button, primary_button
)
from app.utils.common import get_resource_path
from app.utils.custom_strategy_store import sample_line_points
from app.utils.logger import setup_logger

logger = setup_logger('CustomDeploymentEditor')


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


class CustomDeploymentCanvas(QWidget):
    """
    Interactive canvas displaying the zoomed-out game screenshot (or reference base),
    allowing the user to draw deployment lines or click discrete deployment points.
    """
    pointChanged = Signal()

    def __init__(self, full_image: QImage, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._image = full_image
        self._mode = 'line'  # 'line', 'point', 'erase'

        # Current set data:
        # points: list of dicts: {'x': int, 'y': int, 'nx': float, 'ny': float, 'source': 'click'|'line', 'line_idx': int}
        # lines: list of dicts: {'start': (x,y), 'end': (x,y), 'count': int, 'min_spacing': float, 'sampled_points': list}
        self._points: List[Dict[str, Any]] = []
        self._lines: List[Dict[str, Any]] = []
        self._history: List[Tuple[str, Any]] = []  # ('line', line_dict) or ('point', pt_dict)

        # Drawing state:
        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_dragging = False

        # Configurable parameters for line tool:
        self.points_per_line = 8
        self.min_spacing = 40.0

        self._draw_rect = QRect()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == 'erase':
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def set_image(self, img: QImage):
        self._image = img
        self.update()

    def load_set_data(self, points: List[Dict[str, Any]], lines: List[Dict[str, Any]]):
        self._points = [dict(p) for p in points]
        self._lines = [dict(l) for l in lines]
        self._history.clear()
        for l in self._lines:
            self._history.append(('line', l))
        for p in self._points:
            if p.get('source') != 'line':
                self._history.append(('point', p))
        self.update()
        self.pointChanged.emit()

    def get_set_data(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        return list(self._points), list(self._lines)

    def clear_canvas(self):
        self._points.clear()
        self._lines.clear()
        self._history.clear()
        self.update()
        self.pointChanged.emit()

    def undo_last(self):
        if not self._history:
            return
        last_type, last_item = self._history.pop()
        if last_type == 'line':
            if last_item in self._lines:
                self._lines.remove(last_item)
            # Remove all points created by this line
            self._points = [p for p in self._points if p.get('line_id') != last_item.get('id')]
        elif last_type == 'point':
            if last_item in self._points:
                self._points.remove(last_item)
        self.update()
        self.pointChanged.emit()

    # Coordinate mapping between canvas widget and original screenshot pixels:
    def _canvas_to_orig(self, pt: QPoint) -> Optional[Tuple[int, int]]:
        if self._image.isNull() or self._draw_rect.isEmpty():
            return None
        if not self._draw_rect.contains(pt):
            return None
        # Relative in draw rect
        rx = (pt.x() - self._draw_rect.left()) / float(self._draw_rect.width())
        ry = (pt.y() - self._draw_rect.top()) / float(self._draw_rect.height())
        orig_w = self._image.width()
        orig_h = self._image.height()
        ox = int(round(rx * orig_w))
        oy = int(round(ry * orig_h))
        return (max(0, min(orig_w - 1, ox)), max(0, min(orig_h - 1, oy)))

    def _orig_to_canvas(self, ox: float, oy: float) -> QPoint:
        if self._image.isNull() or self._draw_rect.isEmpty():
            return QPoint(0, 0)
        orig_w = self._image.width()
        orig_h = self._image.height()
        rx = ox / float(orig_w)
        ry = oy / float(orig_h)
        cx = int(round(self._draw_rect.left() + rx * self._draw_rect.width()))
        cy = int(round(self._draw_rect.top() + ry * self._draw_rect.height()))
        return QPoint(cx, cy)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            orig_pt = self._canvas_to_orig(event.pos())
            if orig_pt is None:
                return

            if self._mode == 'line':
                self._start_pos = event.pos()
                self._current_pos = event.pos()
                self._is_dragging = True
            elif self._mode == 'point':
                # Check min spacing against all existing points
                ox, oy = orig_pt
                too_close = False
                for p in self._points:
                    if math.hypot(ox - p['x'], oy - p['y']) < self.min_spacing:
                        too_close = True
                        break
                if not too_close:
                    orig_w = self._image.width()
                    orig_h = self._image.height()
                    pt_dict = {
                        'x': ox,
                        'y': oy,
                        'nx': round(ox / float(orig_w), 4),
                        'ny': round(oy / float(orig_h), 4),
                        'source': 'click'
                    }
                    self._points.append(pt_dict)
                    self._history.append(('point', pt_dict))
                    self.update()
                    self.pointChanged.emit()
            elif self._mode == 'erase':
                # Delete closest point if within 25px
                ox, oy = orig_pt
                closest_idx = None
                min_d = 999999
                for i, p in enumerate(self._points):
                    d = math.hypot(ox - p['x'], oy - p['y'])
                    if d < min_d and d < 35:
                        min_d = d
                        closest_idx = i
                if closest_idx is not None:
                    removed = self._points.pop(closest_idx)
                    self._history = [h for h in self._history if h[1] != removed]
                    self.update()
                    self.pointChanged.emit()

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._mode == 'line':
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging and self._mode == 'line':
            self._is_dragging = False
            if self._start_pos and self._current_pos:
                p1 = self._canvas_to_orig(self._start_pos)
                p2 = self._canvas_to_orig(self._current_pos)
                if p1 and p2 and (p1[0] != p2[0] or p1[1] != p2[1]):
                    orig_w = self._image.width()
                    orig_h = self._image.height()
                    existing = [(p['x'], p['y']) for p in self._points]

                    sampled = sample_line_points(
                        p1, p2,
                        count=self.points_per_line,
                        min_spacing=self.min_spacing,
                        existing_points=existing
                    )

                    if sampled:
                        line_id = f"line_{int(time.time()*1000)%100000}_{random.randint(100,999)}"
                        line_dict = {
                            'id': line_id,
                            'start': {'x': p1[0], 'y': p1[1], 'nx': round(p1[0]/orig_w, 4), 'ny': round(p1[1]/orig_h, 4)},
                            'end': {'x': p2[0], 'y': p2[1], 'nx': round(p2[0]/orig_w, 4), 'ny': round(p2[1]/orig_h, 4)},
                            'count': len(sampled),
                            'min_spacing': self.min_spacing,
                        }
                        self._lines.append(line_dict)
                        self._history.append(('line', line_dict))

                        for sp_x, sp_y in sampled:
                            pt_dict = {
                                'x': sp_x,
                                'y': sp_y,
                                'nx': round(sp_x / float(orig_w), 4),
                                'ny': round(sp_y / float(orig_h), 4),
                                'source': 'line',
                                'line_id': line_id
                            }
                            self._points.append(pt_dict)

                        self.pointChanged.emit()

            self._start_pos = None
            self._current_pos = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        canvas_rect = self.rect()
        if self._image.isNull():
            painter.fillRect(canvas_rect, QColor(16, 20, 28))
            painter.setPen(QColor(180, 190, 205))
            painter.drawText(canvas_rect, Qt.AlignmentFlag.AlignCenter, "No game screen captured.")
            return

        # Fit image maintaining 16:9 / 16:10 aspect ratio
        img_scaled = self._image.scaled(
            canvas_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        ox = (canvas_rect.width() - img_scaled.width()) // 2
        oy = (canvas_rect.height() - img_scaled.height()) // 2
        self._draw_rect = QRect(ox, oy, img_scaled.width(), img_scaled.height())

        # Render background
        painter.fillRect(canvas_rect, QColor(10, 13, 18))
        painter.drawImage(self._draw_rect, img_scaled)

        # Subtle dark border around active game screen
        painter.setPen(QPen(QColor(TOKENS.get('border_hi', '#3E4D66')), 2))
        painter.drawRect(self._draw_rect)

        # 1. Draw completed lines
        pen_line = QPen(QColor(46, 167, 255, 180), 3, Qt.PenStyle.DashLine)
        painter.setPen(pen_line)
        for line in self._lines:
            c1 = self._orig_to_canvas(line['start']['x'], line['start']['y'])
            c2 = self._orig_to_canvas(line['end']['x'], line['end']['y'])
            painter.drawLine(c1, c2)

        # 2. Draw live dragging line preview
        if self._is_dragging and self._start_pos and self._current_pos:
            pen_preview = QPen(QColor(0, 230, 255, 230), 3, Qt.PenStyle.SolidLine)
            painter.setPen(pen_preview)
            painter.drawLine(self._start_pos, self._current_pos)

        # 3. Draw deployment points
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)

        radius = 12
        for idx, pt in enumerate(self._points, start=1):
            c_pos = self._orig_to_canvas(pt['x'], pt['y'])

            # Outer glow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(46, 167, 255, 60))
            painter.drawEllipse(c_pos, radius + 4, radius + 4)

            # Circle body (cyan/blue if click, emerald/teal if line)
            if pt.get('source') == 'line':
                body_color = QColor(16, 185, 129)  # Emerald
            else:
                body_color = QColor(46, 167, 255)  # Cyan

            painter.setBrush(body_color)
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.drawEllipse(c_pos, radius, radius)

            # Number badge inside
            painter.setPen(QColor(255, 255, 255))
            txt = str(idx)
            text_rect = QRect(c_pos.x() - radius, c_pos.y() - radius, radius * 2, radius * 2)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, txt)


class CustomDeploymentDialog(QDialog):
    """
    Dialog to design, manage, and configure up to 7 custom deployment sets per strategy.
    Simulates zoom-out and screen capture from the active game window.
    """

    def __init__(
        self,
        strategy_name: str = 'Strategy',
        custom_deployments: Optional[List[Dict[str, Any]]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle('Custom Deployment Designer — RaidR')
        self.resize(1140, 780)
        self.setMinimumSize(960, 640)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {TOKENS.get('bg_c1', '#11151C')};
                color: {TOKENS.get('text', '#FFFFFF')};
            }}
        """)

        self._strategy_name = strategy_name
        self._window_service = WindowService()

        # Load or initialize up to 7 sets:
        self._sets: List[Dict[str, Any]] = []
        if custom_deployments and isinstance(custom_deployments, list):
            for s in custom_deployments[:7]:
                self._sets.append(dict(s))

        if not self._sets:
            self._sets = [self._create_empty_set(1)]

        self._active_set_idx = 0

        # Build Main UI
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(SPACING['lg'], SPACING['md'], SPACING['lg'], SPACING['md'])
        main_layout.setSpacing(SPACING['md'])

        # 1. Top Header Bar
        top_header = QHBoxLayout()
        top_header.setSpacing(12)

        lbl_title = QLabel(f"🎯 CUSTOM DEPLOYMENT DESIGNER — <span style='color: {TOKENS['primary']};'>{self._strategy_name}</span>")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        top_header.addWidget(lbl_title)
        top_header.addStretch()

        self._btn_zoom_capture = primary_button("🔍 Zoom Out & Capture Game", parent=self)
        self._btn_zoom_capture.setToolTip("Zooms out the game camera and captures the exact 1:1 battlefield screen.")
        self._btn_zoom_capture.clicked.connect(self._on_zoom_capture_clicked)
        top_header.addWidget(self._btn_zoom_capture)

        self._status_badge = QLabel("Connecting...")
        self._status_badge.setStyleSheet(f"""
            background: {TOKENS.get('surface_hi', '#1E293B')};
            border: 1px solid {TOKENS.get('border_hi', '#3E4D66')};
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        top_header.addWidget(self._status_badge)
        main_layout.addLayout(top_header)

        # 2. Sets Selector Strip (Up to 7 sets)
        card_sets = Card()
        sets_layout = card_sets.card_layout
        sets_layout.setContentsMargins(12, 8, 12, 8)
        sets_layout.setSpacing(8)

        row_sets = QHBoxLayout()
        row_sets.setSpacing(8)

        lbl_sets_tag = QLabel("SAVED SETS (MAX 7):")
        lbl_sets_tag.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        row_sets.addWidget(lbl_sets_tag)

        self._set_buttons_container = QHBoxLayout()
        self._set_buttons_container.setSpacing(6)
        row_sets.addLayout(self._set_buttons_container)

        self._btn_add_set = chip_button("+ New Set", parent=self)
        self._btn_add_set.setToolTip("Add another deployment variation (bot picks 1 randomly during battle)")
        self._btn_add_set.clicked.connect(self._add_new_set)
        row_sets.addWidget(self._btn_add_set)

        row_sets.addStretch()

        self._btn_dup_set = neutral_button("Duplicate Set", parent=self)
        self._btn_dup_set.setFixedHeight(28)
        self._btn_dup_set.clicked.connect(self._duplicate_current_set)
        row_sets.addWidget(self._btn_dup_set)

        self._btn_del_set = danger_button("Delete Set", parent=self)
        self._btn_del_set.setFixedHeight(28)
        self._btn_del_set.clicked.connect(self._delete_current_set)
        row_sets.addWidget(self._btn_del_set)

        sets_layout.addLayout(row_sets)
        main_layout.addWidget(card_sets)

        # 3. Middle Body: Interactive Canvas + Sidebar Settings
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(SPACING['md'])

        # Left: Canvas
        self._canvas = CustomDeploymentCanvas(QImage(), parent=self)
        self._canvas.pointChanged.connect(self._sync_canvas_to_current_set)
        mid_layout.addWidget(self._canvas, stretch=1)

        # Right: Tool & Settings Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(310)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(10)

        # Card: Tools
        card_tools = Card()
        t_lay = card_tools.card_layout
        t_lay.setSpacing(8)
        t_lay.addWidget(SectionTitle("CANVAS TOOLS", parent=card_tools))

        tool_btn_layout = QHBoxLayout()
        tool_btn_layout.setSpacing(6)

        self._btn_tool_line = chip_button("✏️ Draw Line", parent=card_tools)
        self._btn_tool_line.setCheckable(True)
        self._btn_tool_line.setChecked(True)
        self._btn_tool_line.clicked.connect(lambda: self._select_tool('line'))

        self._btn_tool_point = chip_button("📍 Click Point", parent=card_tools)
        self._btn_tool_point.setCheckable(True)
        self._btn_tool_point.clicked.connect(lambda: self._select_tool('point'))

        self._btn_tool_erase = chip_button("🧹 Erase", parent=card_tools)
        self._btn_tool_erase.setCheckable(True)
        self._btn_tool_erase.clicked.connect(lambda: self._select_tool('erase'))

        tool_btn_layout.addWidget(self._btn_tool_line)
        tool_btn_layout.addWidget(self._btn_tool_point)
        tool_btn_layout.addWidget(self._btn_tool_erase)
        t_lay.addLayout(tool_btn_layout)

        # Undo and Clear
        action_btn_layout = QHBoxLayout()
        action_btn_layout.setSpacing(6)
        btn_undo = neutral_button("↩ Undo", parent=card_tools)
        btn_undo.setFixedHeight(28)
        btn_undo.clicked.connect(self._canvas.undo_last)

        btn_clear = neutral_button("🗑️ Clear Set", parent=card_tools)
        btn_clear.setFixedHeight(28)
        btn_clear.clicked.connect(self._canvas.clear_canvas)

        action_btn_layout.addWidget(btn_undo)
        action_btn_layout.addWidget(btn_clear)
        t_lay.addLayout(action_btn_layout)
        side_layout.addWidget(card_tools)

        # Card: Line Sampling Constraints
        card_sampling = Card()
        s_lay = card_sampling.card_layout
        s_lay.setSpacing(8)
        s_lay.addWidget(SectionTitle("LINE SAMPLING RESTRICTION", parent=card_sampling))

        row_spc = QHBoxLayout()
        lbl_spc = QLabel("Min point spacing:")
        lbl_spc.setStyleSheet("font-size: 11px;")
        self._spin_min_spacing = QSpinBox()
        self._spin_min_spacing.setRange(20, 150)
        self._spin_min_spacing.setValue(40)
        self._spin_min_spacing.setSuffix(" px")
        self._spin_min_spacing.valueChanged.connect(self._on_sampling_changed)
        row_spc.addWidget(lbl_spc)
        row_spc.addWidget(self._spin_min_spacing)
        s_lay.addLayout(row_spc)

        lbl_spc_desc = QLabel("Guarantees no 2 points along drawn line land too close to each other.")
        lbl_spc_desc.setWordWrap(True)
        lbl_spc_desc.setStyleSheet(f"font-size: 10px; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        s_lay.addWidget(lbl_spc_desc)

        row_cnt = QHBoxLayout()
        lbl_cnt = QLabel("Target points per line:")
        lbl_cnt.setStyleSheet("font-size: 11px;")
        self._spin_line_count = QSpinBox()
        self._spin_line_count.setRange(2, 30)
        self._spin_line_count.setValue(8)
        self._spin_line_count.valueChanged.connect(self._on_sampling_changed)
        row_cnt.addWidget(lbl_cnt)
        row_cnt.addWidget(self._spin_line_count)
        s_lay.addLayout(row_cnt)
        side_layout.addWidget(card_sampling)

        # Card: Deployment Timing
        card_timing = Card()
        tm_lay = card_timing.card_layout
        tm_lay.setSpacing(8)
        tm_lay.addWidget(SectionTitle("DEPLOYMENT TIMING", parent=card_timing))

        row_mode = QHBoxLayout()
        self._combo_delay_mode = QComboBox()
        self._combo_delay_mode.addItem("🎲 Random Delay (Human-like)", "random")
        self._combo_delay_mode.addItem("⏱️ Custom Fixed Delay", "custom")
        self._combo_delay_mode.currentIndexChanged.connect(self._update_timing_visibility)
        row_mode.addWidget(self._combo_delay_mode)
        tm_lay.addLayout(row_mode)

        # Random Range inputs
        self._widget_random_timing = QWidget()
        w_rand_lay = QHBoxLayout(self._widget_random_timing)
        w_rand_lay.setContentsMargins(0, 0, 0, 0)
        lbl_min = QLabel("Min:")
        self._spin_min_delay = QDoubleSpinBox()
        self._spin_min_delay.setRange(0.04, 1.0)
        self._spin_min_delay.setSingleStep(0.02)
        self._spin_min_delay.setValue(0.08)
        self._spin_min_delay.setSuffix("s")
        self._spin_min_delay.valueChanged.connect(self._sync_settings_to_current_set)

        lbl_max = QLabel("Max:")
        self._spin_max_delay = QDoubleSpinBox()
        self._spin_max_delay.setRange(0.06, 2.0)
        self._spin_max_delay.setSingleStep(0.02)
        self._spin_max_delay.setValue(0.22)
        self._spin_max_delay.setSuffix("s")
        self._spin_max_delay.valueChanged.connect(self._sync_settings_to_current_set)

        w_rand_lay.addWidget(lbl_min)
        w_rand_lay.addWidget(self._spin_min_delay)
        w_rand_lay.addWidget(lbl_max)
        w_rand_lay.addWidget(self._spin_max_delay)
        tm_lay.addWidget(self._widget_random_timing)

        # Custom Fixed input
        self._widget_custom_timing = QWidget()
        w_cust_lay = QHBoxLayout(self._widget_custom_timing)
        w_cust_lay.setContentsMargins(0, 0, 0, 0)
        lbl_fixed = QLabel("Fixed Delay:")
        self._spin_custom_delay = QDoubleSpinBox()
        self._spin_custom_delay.setRange(0.04, 2.0)
        self._spin_custom_delay.setSingleStep(0.02)
        self._spin_custom_delay.setValue(0.15)
        self._spin_custom_delay.setSuffix("s")
        self._spin_custom_delay.valueChanged.connect(self._sync_settings_to_current_set)

        w_cust_lay.addWidget(lbl_fixed)
        w_cust_lay.addWidget(self._spin_custom_delay)
        tm_lay.addWidget(self._widget_custom_timing)
        side_layout.addWidget(card_timing)

        # Card: Deployment Order
        card_order = Card()
        o_lay = card_order.card_layout
        o_lay.setSpacing(8)
        o_lay.addWidget(SectionTitle("DEPLOYMENT ORDER", parent=card_order))

        self._combo_order = QComboBox()
        self._combo_order.addItem("🎲 Randomized Order (Each Battle)", "randomized")
        self._combo_order.addItem("🔢 Sequential (As Drawn: 1, 2, 3...)", "sequential")
        self._combo_order.addItem("🔄 Reverse Order", "reverse")
        self._combo_order.currentIndexChanged.connect(self._sync_settings_to_current_set)
        o_lay.addWidget(self._combo_order)

        lbl_order_desc = QLabel("Randomized order rearranges tap sequence on every attack for maximum anti-ban unpredictability.")
        lbl_order_desc.setWordWrap(True)
        lbl_order_desc.setStyleSheet(f"font-size: 10px; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        o_lay.addWidget(lbl_order_desc)
        side_layout.addWidget(card_order)

        side_layout.addStretch()
        mid_layout.addWidget(sidebar)
        main_layout.addLayout(mid_layout, stretch=1)

        # 4. Bottom Action Bar
        bot_bar = QHBoxLayout()
        self._lbl_footer_info = QLabel("")
        self._lbl_footer_info.setStyleSheet(f"font-size: 11px; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        bot_bar.addWidget(self._lbl_footer_info)
        bot_bar.addStretch()

        btn_cancel = neutral_button("Cancel", parent=self)
        btn_cancel.clicked.connect(self.reject)
        bot_bar.addWidget(btn_cancel)

        btn_save = primary_button("💾 Save Custom Deployments", parent=self)
        btn_save.setMinimumWidth(180)
        btn_save.setMinimumHeight(38)
        btn_save.clicked.connect(self._on_save_clicked)
        bot_bar.addWidget(btn_save)

        main_layout.addLayout(bot_bar)

        # Initialize screen and active set
        self._capture_game_with_zoom()
        self._render_set_buttons()
        self._load_active_set_to_ui()

    def _create_empty_set(self, set_idx: int) -> Dict[str, Any]:
        return {
            'set_id': set_idx,
            'name': f"Set {set_idx}",
            'delay_mode': 'random',
            'min_delay': 0.08,
            'max_delay': 0.22,
            'custom_delay': 0.15,
            'order_mode': 'randomized',
            'min_spacing': 40,
            'points_per_line': 8,
            'points': [],
            'lines': []
        }

    def _on_zoom_capture_clicked(self):
        self._capture_game_with_zoom(force_refresh=True)

    def _capture_game_with_zoom(self, force_refresh: bool = False):
        """Attaches to game, sends scroll-out to reach standard bot view, and grabs frame."""
        frame = None
        if self._window_service.find_window():
            try:
                inp = InputService(self._window_service)
                w, h = self._window_service.get_outer_pixel_size()
                # Zoom out all the way using scroll 20
                inp.scroll(w // 2, h // 2, 20)
                time.sleep(0.35)
                frame = self._window_service.screenshot()
            except Exception as e:
                logger.warning("Zoom-out input failed: %s", e)

        if frame is not None:
            fh, fw = frame.shape[:2]
            self._status_badge.setText(f"🟢 Active Game: {fw}×{fh} px")
            self._status_badge.setStyleSheet(f"""
                background: rgba(16, 185, 129, 0.15);
                border: 1px solid #10B981;
                color: #A7F3D0;
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            """)
            self._canvas.set_image(cv2_to_qimage(frame))
        else:
            # Fallback to reference base
            ref_path = get_resource_path('assets/reference_base.png')
            if ref_path.is_file():
                frame = cv2.imread(str(ref_path))
                if frame is not None:
                    fh, fw = frame.shape[:2]
                    self._status_badge.setText(f"🟡 Standard Reference: {fw}×{fh} px")
                    self._status_badge.setStyleSheet(f"""
                        background: rgba(245, 158, 11, 0.15);
                        border: 1px solid #F59E0B;
                        color: #FDE68A;
                        border-radius: 12px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: 600;
                    """)
                    self._canvas.set_image(cv2_to_qimage(frame))

    def _select_tool(self, tool_name: str):
        self._btn_tool_line.setChecked(tool_name == 'line')
        self._btn_tool_point.setChecked(tool_name == 'point')
        self._btn_tool_erase.setChecked(tool_name == 'erase')
        self._canvas.set_mode(tool_name)

    def _render_set_buttons(self):
        # Clear existing buttons
        while self._set_buttons_container.count():
            item = self._set_buttons_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, s in enumerate(self._sets):
            pts_count = len(s.get('points', []))
            btn = chip_button(f"{s.get('name', f'Set {idx+1}')} ({pts_count} pts)", parent=self)
            btn.setCheckable(True)
            btn.setChecked(idx == self._active_set_idx)
            btn.clicked.connect(lambda _, i=idx: self._switch_to_set(i))
            self._set_buttons_container.addWidget(btn)

        self._btn_add_set.setEnabled(len(self._sets) < 7)
        self._btn_add_set.setText(f"+ New Set ({len(self._sets)}/7)")
        self._btn_del_set.setEnabled(len(self._sets) > 1)

    def _switch_to_set(self, idx: int):
        if idx == self._active_set_idx or idx < 0 or idx >= len(self._sets):
            return
        # Save current UI state to existing set
        self._sync_settings_to_current_set()
        self._active_set_idx = idx
        self._render_set_buttons()
        self._load_active_set_to_ui()

    def _add_new_set(self):
        if len(self._sets) >= 7:
            QMessageBox.information(self, "Max Sets", "Maximum of 7 custom deployment sets per strategy allowed.")
            return
        self._sync_settings_to_current_set()
        new_set = self._create_empty_set(len(self._sets) + 1)
        self._sets.append(new_set)
        self._active_set_idx = len(self._sets) - 1
        self._render_set_buttons()
        self._load_active_set_to_ui()

    def _duplicate_current_set(self):
        if len(self._sets) >= 7:
            QMessageBox.information(self, "Max Sets", "Maximum of 7 custom deployment sets per strategy allowed.")
            return
        self._sync_settings_to_current_set()
        current = self._sets[self._active_set_idx]
        dup = dict(current)
        dup['set_id'] = len(self._sets) + 1
        dup['name'] = f"Set {len(self._sets) + 1}"
        dup['points'] = [dict(p) for p in current.get('points', [])]
        dup['lines'] = [dict(l) for l in current.get('lines', [])]
        self._sets.append(dup)
        self._active_set_idx = len(self._sets) - 1
        self._render_set_buttons()
        self._load_active_set_to_ui()

    def _delete_current_set(self):
        if len(self._sets) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "Strategy must have at least one deployment set!")
            return
        self._sets.pop(self._active_set_idx)
        self._active_set_idx = max(0, self._active_set_idx - 1)
        # Rename remaining sets cleanly
        for i, s in enumerate(self._sets, start=1):
            s['set_id'] = i
            s['name'] = f"Set {i}"
        self._render_set_buttons()
        self._load_active_set_to_ui()

    def _load_active_set_to_ui(self):
        if not self._sets:
            return
        s = self._sets[self._active_set_idx]

        # Load points and lines into canvas
        self._canvas.load_set_data(s.get('points', []), s.get('lines', []))

        # Line sampling
        self._spin_min_spacing.setValue(int(s.get('min_spacing', 40)))
        self._spin_line_count.setValue(int(s.get('points_per_line', 8)))
        self._canvas.min_spacing = float(self._spin_min_spacing.value())
        self._canvas.points_per_line = int(self._spin_line_count.value())

        # Timing
        d_mode = s.get('delay_mode', 'random')
        idx = self._combo_delay_mode.findData(d_mode)
        if idx >= 0:
            self._combo_delay_mode.setCurrentIndex(idx)
        self._spin_min_delay.setValue(float(s.get('min_delay', 0.08)))
        self._spin_max_delay.setValue(float(s.get('max_delay', 0.22)))
        self._spin_custom_delay.setValue(float(s.get('custom_delay', 0.15)))
        self._update_timing_visibility()

        # Order
        o_mode = s.get('order_mode', 'randomized')
        idx_o = self._combo_order.findData(o_mode)
        if idx_o >= 0:
            self._combo_order.setCurrentIndex(idx_o)

        self._update_footer()

    def _sync_canvas_to_current_set(self):
        if not self._sets:
            return
        pts, lines = self._canvas.get_set_data()
        current = self._sets[self._active_set_idx]
        current['points'] = pts
        current['lines'] = lines
        current['ref_width'] = self._canvas._image.width() if not self._canvas._image.isNull() else 2560
        current['ref_height'] = self._canvas._image.height() if not self._canvas._image.isNull() else 1440
        self._render_set_buttons()
        self._update_footer()

    def _sync_settings_to_current_set(self):
        if not self._sets:
            return
        current = self._sets[self._active_set_idx]
        current['min_spacing'] = self._spin_min_spacing.value()
        current['points_per_line'] = self._spin_line_count.value()
        current['delay_mode'] = self._combo_delay_mode.currentData()
        current['min_delay'] = self._spin_min_delay.value()
        current['max_delay'] = self._spin_max_delay.value()
        current['custom_delay'] = self._spin_custom_delay.value()
        current['order_mode'] = self._combo_order.currentData()

    def _on_sampling_changed(self):
        self._canvas.min_spacing = float(self._spin_min_spacing.value())
        self._canvas.points_per_line = int(self._spin_line_count.value())
        self._sync_settings_to_current_set()

    def _update_timing_visibility(self):
        mode = self._combo_delay_mode.currentData()
        self._widget_random_timing.setVisible(mode == 'random')
        self._widget_custom_timing.setVisible(mode == 'custom')
        self._sync_settings_to_current_set()

    def _update_footer(self):
        if not self._sets:
            return
        current = self._sets[self._active_set_idx]
        pts_c = len(current.get('points', []))
        lines_c = len(current.get('lines', []))
        self._lbl_footer_info.setText(
            f"Active: <b>{current.get('name')}</b> ({pts_c} points, {lines_c} lines) | "
            f"Total sets: {len(self._sets)}/7 | Bot will pick 1 set randomly per battle."
        )

    def _on_save_clicked(self):
        self._sync_canvas_to_current_set()
        self._sync_settings_to_current_set()
        self.accept()

    def get_custom_deployments(self) -> List[Dict[str, Any]]:
        return self._sets
