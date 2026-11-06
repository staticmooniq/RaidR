"""RaidR — Clean Minimal Widgets with smooth animations."""
from __future__ import annotations
from PySide6.QtCore import Qt, QRectF, QSize, QPointF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF, QLinearGradient
from PySide6.QtWidgets import QCheckBox, QFrame, QLabel, QPushButton, QVBoxLayout
from app.ui.qt.theme import SPACING, TOKENS


class Card(QFrame):
    def __init__(self, parent=None, variant='default'):
        super().__init__(parent)
        self.setObjectName('Card')
        if variant != 'default':
            self.setProperty('variant', variant)
            self.style().unpolish(self)
            self.style().polish(self)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACING['lg'], SPACING['md'],
                                         SPACING['lg'], SPACING['md'])
        self._layout.setSpacing(SPACING['sm'])

    @property
    def card_layout(self):
        return self._layout


class SectionTitle(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setObjectName('SectionTitle')


class PageTitle(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName('PageTitle')


class ToggleSwitch(QCheckBox):
    # Generous dimensions for track & knob to prevent any edge clipping
    _TW, _TH = 44.0, 24.0
    _KD = 18.0
    _PADDING = 3.0  # Safe inset padding from bounding box

    def __init__(self, text='', *, parent=None, danger=False, under_development=False):
        super().__init__(text, parent)
        self.setObjectName('ToggleSwitch')
        self._danger = danger
        self._ud = under_development
        self.setFixedHeight(28)
        
        # Smooth animation property for knob
        initial_x = (self._TW - self._KD - 3.0) if self.isChecked() and not self._ud else 3.0
        self._knob_x = float(initial_x)
        self._animation = QPropertyAnimation(self, b"knob_x", self)
        self._animation.setDuration(160)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        if under_development:
            self.setChecked(False)

        self.toggled.connect(self._on_toggled)

    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, val: float):
        self._knob_x = val
        self.update()

    knob_x = Property(float, _get_knob_x, _set_knob_x)

    def _on_toggled(self, checked: bool):
        target_x = float(self._TW - self._KD - 3.0) if checked and not self._ud else 3.0
        self._animation.stop()
        self._animation.setStartValue(self._knob_x)
        self._animation.setEndValue(target_x)
        self._animation.start()

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        target_x = float(self._TW - self._KD - 3.0) if checked and not self._ud else 3.0
        self._knob_x = target_x
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        tw, th, kd = self._TW, self._TH, self._KD
        pad = self._PADDING
        # Offset track from left edge by `pad` so full antialiased stroke fits cleanly
        x0 = pad
        y0 = (self.height() - th) / 2.0
        chk = self.isChecked() and not self._ud

        track_rect = QRectF(x0, y0, tw, th)
        track = QPainterPath()
        track.addRoundedRect(track_rect, th / 2.0, th / 2.0)
        p.setPen(Qt.NoPen)

        if self._ud:
            p.fillPath(track, QColor(30, 36, 44))
            p.setPen(QPen(QColor(60, 70, 84), 1))
            p.drawPath(track)
            text_col = QColor(TOKENS['text_faint'])
        elif self._danger:
            if chk:
                p.fillPath(track, QColor(TOKENS['danger']))
            else:
                p.fillPath(track, QColor(48, 24, 28))
                p.setPen(QPen(QColor(90, 40, 48), 1))
                p.drawPath(track)
            text_col = QColor(TOKENS['danger'] if chk else TOKENS['text_muted'])
        else:
            if chk:
                # Active glossy gradient matching current template
                grad = QLinearGradient(x0, y0, x0, y0 + th)
                grad.setColorAt(0.0, QColor(TOKENS.get('grad_top', '#5CB5FF')))
                grad.setColorAt(0.08, QColor(TOKENS.get('grad_hi', '#40A6FF')))
                grad.setColorAt(0.5, QColor(TOKENS.get('grad_mid', '#2693FF')))
                grad.setColorAt(1.0, QColor(TOKENS.get('grad_low', '#147DE8')))
                p.fillPath(track, grad)
                p.setPen(QPen(QColor(TOKENS.get('btn_border', '#75C1FF')), 1))
                p.drawPath(track)
            else:
                p.fillPath(track, QColor(25, 34, 46))
                p.setPen(QPen(QColor(60, 75, 95), 1))
                p.drawPath(track)
            text_col = QColor(TOKENS['primary'] if chk else TOKENS['text_muted'])

        # Smooth white knob with gentle drop shadow
        kx = x0 + self._knob_x
        ky = y0 + (th - kd) / 2.0
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255) if not self._ud else QColor(90, 100, 115))
        p.drawEllipse(QRectF(kx, ky, kd, kd))

        # Label with DEMIBOLD contrast
        if self.text():
            p.setPen(text_col)
            font = p.font()
            font.setPointSize(10)
            font.setWeight(font.Weight.DemiBold if chk else font.Weight.Normal)
            p.setFont(font)
            p.drawText(QRectF(x0 + tw + 12.0, 0, self.width() - (x0 + tw + 12.0), self.height()),
                       Qt.AlignVCenter | Qt.AlignLeft, self.text())

    def mousePressEvent(self, event):
        if self._ud:
            from app.ui.qt.dialogs import show_under_development
            show_under_development(self.window())
            return
        super().mousePressEvent(event)

    def sizeHint(self):
        tw = self.fontMetrics().horizontalAdvance(self.text()) + 16 if self.text() else 0
        return QSize(int(self._PADDING + self._TW + 16.0 + tw), 28)

    def hitButton(self, pos):
        return self.rect().contains(pos)


def _btn(text, role, parent=None):
    b = QPushButton(text, parent)
    b.setProperty('role', role)
    b.style().unpolish(b)
    b.style().polish(b)
    return b


def primary_button(text, *, parent=None):   return _btn(text, 'primary', parent)
def danger_button(text, *, parent=None):    return _btn(text, 'danger', parent)
def neutral_button(text, *, parent=None):   return _btn(text, 'neutral', parent)
def chip_button(text, *, parent=None):      return _btn(text, 'chip', parent)


def segment_button(text, *, parent=None, under_development=False):
    b = _btn(text, 'segment', parent)
    if under_development:
        b.setCheckable(False)
        b.setProperty('underDevelopment', True)
    else:
        b.setCheckable(True)
    b.style().unpolish(b)
    b.style().polish(b)
    b.setMinimumWidth(int(b.sizeHint().width() * 1.15))
    return b


class StepperButton(QPushButton):
    def __init__(self, *, up, parent=None):
        super().__init__(parent)
        self._up = up
        self.setProperty('role', 'stepper')
        self.setFixedSize(24, 14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.style().unpolish(self)
        self.style().polish(self)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isEnabled():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.NoPen)
        # Black arrow inside vibrant glossy theme background for maximum contrast
        p.setBrush(QColor('#050811'))
        cx, cy = self.width() / 2, self.height() / 2
        if self._up:
            pts = [QPointF(cx, cy - 3), QPointF(cx - 4, cy + 2), QPointF(cx + 4, cy + 2)]
        else:
            pts = [QPointF(cx, cy + 3), QPointF(cx - 4, cy - 2), QPointF(cx + 4, cy - 2)]
        p.drawPolygon(QPolygonF(pts))


class HelpButton(QPushButton):
    def __init__(self, on_click, *, parent=None):
        super().__init__('?', parent)
        self.setProperty('role', 'help')
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.style().unpolish(self)
        self.style().polish(self)
        self.clicked.connect(on_click)


class VisibilityToggleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty('role', 'icon')
        self.setCheckable(True)
        self.setFixedSize(34, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.style().unpolish(self)
        self.style().polish(self)
        self.toggled.connect(lambda _: self.update())

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(TOKENS['text']), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2
        p.drawEllipse(QRectF(cx - 9, cy - 6, 18, 12))
        if self.isChecked():
            p.drawLine(int(cx - 8), int(cy + 6), int(cx + 8), int(cy - 6))
            return
        p.setBrush(QColor(TOKENS['text']))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx - 2.5, cy - 2.5, 5, 5))
