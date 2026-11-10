"""Custom Strategy Editor Dialog — full visual strategy designer."""
from __future__ import annotations
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget
)

from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import (
    Card, SectionTitle, ToggleSwitch, chip_button, danger_button,
    neutral_button, primary_button
)
from app.utils.common import ensure_dir, get_resource_path
from app.utils.custom_strategy_store import (
    STRATEGY_DEPLOY_PRESETS, get_custom_troops_dir
)
from app.ui.qt.game_cropper import GameCropWindow


class TroopRowWidget(QWidget):
    """Row representing one troop inside a custom strategy."""

    def __init__(self, troop_data: Dict[str, Any], on_delete: Optional[callable] = None, parent=None):
        super().__init__(parent)
        self.troop_data = dict(troop_data)
        self._on_delete = on_delete

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        # Image preview
        self._preview = QLabel()
        self._preview.setFixedSize(50, 50)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(f"""
            background: {TOKENS.get('surface_hi', 'rgba(26, 32, 45, 0.82)')};
            border: 1px solid {TOKENS.get('border_hi', '#3E4D66')};
            border-radius: 8px;
        """)
        layout.addWidget(self._preview)

        # Troop Name input
        vbox_name = QVBoxLayout()
        vbox_name.setSpacing(4)
        lbl_name = QLabel('TROOP NAME')
        lbl_name.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        self._name_input = QLineEdit(self.troop_data.get('name', 'Troop'))
        self._name_input.setFixedWidth(130)
        self._name_input.setFixedHeight(34)
        vbox_name.addWidget(lbl_name)
        vbox_name.addWidget(self._name_input)
        layout.addLayout(vbox_name)

        # Snip from Game / Upload / Paste buttons
        vbox_btns = QVBoxLayout()
        vbox_btns.setSpacing(4)

        lbl_icon = QLabel('TROOP ICON')
        lbl_icon.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        vbox_btns.addWidget(lbl_icon)

        btn_snip = primary_button('Snip from Game', parent=self)
        btn_snip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_snip.setFixedWidth(138)
        btn_snip.setFixedHeight(30)
        btn_snip.clicked.connect(self._snip_from_game)
        btn_snip.setToolTip('Grabs real-time Clash of Clans screen so you can crop with perfect pixel accuracy.')

        btn_row_extra = QHBoxLayout()
        btn_row_extra.setSpacing(6)
        btn_upload = chip_button('Upload', parent=self)
        btn_upload.setFixedWidth(66)
        btn_upload.setFixedHeight(22)
        btn_upload.setStyleSheet("padding: 2px 4px; font-size: 11px;")
        btn_upload.clicked.connect(self._select_image)

        btn_paste = chip_button('Paste', parent=self)
        btn_paste.setFixedWidth(66)
        btn_paste.setFixedHeight(22)
        btn_paste.setStyleSheet("padding: 2px 4px; font-size: 11px;")
        btn_paste.clicked.connect(self._paste_image)

        btn_row_extra.addWidget(btn_upload)
        btn_row_extra.addWidget(btn_paste)

        vbox_btns.addWidget(btn_snip)
        vbox_btns.addLayout(btn_row_extra)
        layout.addLayout(vbox_btns)

        # Deploy Pattern / Strategy selector
        vbox_style = QVBoxLayout()
        vbox_style.setSpacing(4)
        lbl_style = QLabel('DEPLOY STYLE')
        lbl_style.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        self._style_combo = QComboBox()
        self._style_combo.setFixedHeight(34)
        for label, val in STRATEGY_DEPLOY_PRESETS:
            self._style_combo.addItem(label, val)
        curr_style = self.troop_data.get('deploy_style', 'four_edge_spam')
        idx = self._style_combo.findData(curr_style)
        if idx >= 0:
            self._style_combo.setCurrentIndex(idx)
        vbox_style.addWidget(lbl_style)
        vbox_style.addWidget(self._style_combo)
        layout.addLayout(vbox_style, stretch=1)

        # Count
        vbox_count = QVBoxLayout()
        vbox_count.setSpacing(4)
        lbl_count = QLabel('COUNT (0=ALL)')
        lbl_count.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TOKENS.get('text_muted', '#8FA0B8')};")
        self._count_spin = QSpinBox()
        self._count_spin.setRange(0, 150)
        self._count_spin.setValue(int(self.troop_data.get('count', 0)))
        self._count_spin.setFixedWidth(85)
        self._count_spin.setFixedHeight(34)
        vbox_count.addWidget(lbl_count)
        vbox_count.addWidget(self._count_spin)
        layout.addLayout(vbox_count)

        # Delete button: sleek modern danger button
        self._del_btn = danger_button('', parent=self)
        self._del_btn.setFixedSize(32, 32)
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.setToolTip('Remove this troop')
        del_icon_path = get_resource_path('assets/icon_delete_x.png')
        if del_icon_path.is_file():
            self._del_btn.setIcon(QPixmap(str(del_icon_path)))
            self._del_btn.setIconSize(QSize(16, 16))
        else:
            self._del_btn.setText('✕')
        self._del_btn.clicked.connect(self._delete_clicked)
        layout.addWidget(self._del_btn)

        self._refresh_preview()

    def _delete_clicked(self):
        if self._on_delete:
            self._on_delete(self)

    def _refresh_preview(self):
        tmpl = self.troop_data.get('template', '')
        is_custom = self.troop_data.get('is_custom_image', False)

        img = QImage()
        if is_custom and tmpl and Path(tmpl).is_file():
            img = QImage(tmpl)
        elif tmpl:
            # Check built-in template paths
            cand = get_resource_path(f"templates/16_9/{tmpl if tmpl.endswith('.png') else tmpl + '.png'}")
            if cand.is_file():
                img = QImage(str(cand))

        if not img.isNull():
            self._preview.setPixmap(
                QPixmap.fromImage(img).scaled(
                    42, 42,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            # Show stylish crossed swords icon when no image has been uploaded
            sword_icon = get_resource_path('assets/sword_placeholder.png')
            if sword_icon.is_file():
                self._preview.setPixmap(
                    QPixmap.fromImage(QImage(str(sword_icon))).scaled(
                        38, 38,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            else:
                self._preview.setText('⚔')
                self._preview.setStyleSheet(f"font-size: 20px; color: {TOKENS['primary']}; border: 1px solid {TOKENS['border_hi']}; border-radius: 6px;")

    def _save_image_data(self, image: QImage):
        if image.isNull():
            return
        dest_dir = get_custom_troops_dir()
        filename = f"crop_{uuid.uuid4().hex[:8]}.png"
        path = dest_dir / filename
        image.convertToFormat(QImage.Format.Format_RGB32).save(str(path), 'PNG')

        self.troop_data['template'] = str(path)
        self.troop_data['is_custom_image'] = True
        self._refresh_preview()

    def _snip_from_game(self):
        cropper = GameCropWindow(parent=self.window())
        if cropper.exec() == QDialog.DialogCode.Accepted and cropper.cropped_image:
            self._save_image_data(cropper.cropped_image)

    def _select_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Select Troop Deploy Bar Icon Crop', '',
            'Images (*.png *.jpg *.jpeg *.bmp *.webp)'
        )
        if filename:
            self._save_image_data(QImage(filename))

    def _paste_image(self):
        img = QApplication.clipboard().image()
        if img.isNull():
            QMessageBox.warning(self, 'Clipboard Empty', 'Please copy a crop of the troop icon first.')
            return
        self._save_image_data(img)

    def get_data(self) -> Dict[str, Any]:
        self.troop_data['name'] = self._name_input.text().strip() or 'Troop'
        self.troop_data['deploy_style'] = self._style_combo.currentData()
        self.troop_data['count'] = self._count_spin.value()
        return dict(self.troop_data)


class StrategyEditorDialog(QDialog):
    """Full-featured visual editor to create and edit custom multi-troop strategies."""

    def __init__(self, strategy_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Strategy Designer — RaidR')
        self.resize(800, 600)
        self.setMinimumSize(740, 520)
        
        # Apply dark background container styling to the dialog itself
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {TOKENS.get('bg_c1', '#11151C')};
                color: {TOKENS.get('text', '#FFFFFF')};
            }}
        """)

        # Clone or create initial structure
        if strategy_data:
            self._data = dict(strategy_data)
            self._data['troops'] = [dict(t) for t in strategy_data.get('troops', [])]
        else:
            self._data = {
                'id': f"strat_{uuid.uuid4().hex[:8]}",
                'name': 'New Strategy',
                'deploy_heroes': True,
                'deploy_spells': True,
                'troops': [
                    {
                        'name': 'Troop 1',
                        'template': '',
                        'is_custom_image': True,
                        'deploy_style': 'four_edge_spam',
                        'count': 0,
                        'delay': 0.15,
                    }
                ]
            }

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        root.setSpacing(SPACING['md'])

        # Top Card: Strategy Details
        card_info = Card()
        info_layout = card_info.card_layout
        info_layout.setSpacing(12)

        lbl_section = SectionTitle('STRATEGY CONFIGURATION', parent=card_info)
        info_layout.addWidget(lbl_section)

        row_meta = QHBoxLayout()
        row_meta.setSpacing(SPACING['md'])

        lbl_name = QLabel('Strategy Name:', parent=card_info)
        lbl_name.setStyleSheet(f"font-weight: 700; color: {TOKENS['text']}; font-size: 13px;")
        self._name_field = QLineEdit(self._data.get('name', 'My Strategy'), parent=card_info)
        self._name_field.setFixedHeight(34)
        row_meta.addWidget(lbl_name)
        row_meta.addWidget(self._name_field, stretch=1)

        # Toggles
        self._toggle_heroes = ToggleSwitch(parent=card_info)
        self._toggle_heroes.setChecked(self._data.get('deploy_heroes', True))
        lbl_h = QLabel('Deploy Heroes', parent=card_info)
        lbl_h.setStyleSheet(f"color: {TOKENS['text']}; font-size: 12px; font-weight: 600;")
        row_meta.addWidget(self._toggle_heroes)
        row_meta.addWidget(lbl_h)

        row_meta.addSpacing(10)

        self._toggle_spells = ToggleSwitch(parent=card_info)
        self._toggle_spells.setChecked(self._data.get('deploy_spells', True))
        lbl_s = QLabel('Deploy Spells', parent=card_info)
        lbl_s.setStyleSheet(f"color: {TOKENS['text']}; font-size: 12px; font-weight: 600;")
        row_meta.addWidget(self._toggle_spells)
        row_meta.addWidget(lbl_s)

        info_layout.addLayout(row_meta)
        root.addWidget(card_info)

        # Troop List Section
        lbl_troops_sec = SectionTitle('TROOP DEPLOYMENT SEQUENCE (EXECUTED TOP TO BOTTOM)', parent=self)
        root.addWidget(lbl_troops_sec)

        # Scroll Area for Troops
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)

        self._troops_container = QWidget()
        self._troops_layout = QVBoxLayout(self._troops_container)
        self._troops_layout.setContentsMargins(0, 0, 0, 0)
        self._troops_layout.setSpacing(8)

        self._troop_rows: List[TroopRowWidget] = []
        for t_conf in self._data.get('troops', []):
            self._add_troop_row(t_conf)

        self._troops_layout.addStretch()
        scroll.setWidget(self._troops_container)
        root.addWidget(scroll, stretch=1)

        # Add Troop Button Row
        btn_add_troop = neutral_button('+ Add Another Troop to Strategy', parent=self)
        btn_add_troop.setMinimumHeight(34)
        btn_add_troop.clicked.connect(self._on_add_troop)
        root.addWidget(btn_add_troop)

        # Bottom Action Buttons
        bot_row = QHBoxLayout()
        bot_row.setSpacing(SPACING['md'])
        
        btn_cancel = neutral_button('Cancel', parent=self)
        btn_cancel.clicked.connect(self.reject)
        bot_row.addWidget(btn_cancel)

        bot_row.addStretch()

        btn_save = primary_button('Save Strategy', parent=self)
        btn_save.setMinimumHeight(38)
        btn_save.setMinimumWidth(140)
        btn_save.clicked.connect(self._on_save)
        bot_row.addWidget(btn_save)

        root.addLayout(bot_row)

    def _add_troop_row(self, troop_data: Dict[str, Any]):
        row = TroopRowWidget(troop_data, on_delete=self._remove_troop_row, parent=self._troops_container)
        self._troop_rows.append(row)
        # Insert before bottom stretch
        self._troops_layout.insertWidget(len(self._troop_rows) - 1, row)

    def _remove_troop_row(self, row: TroopRowWidget):
        if len(self._troop_rows) <= 1:
            QMessageBox.warning(self, 'Required Troop', 'Strategy must have at least one troop!')
            return
        if row in self._troop_rows:
            self._troop_rows.remove(row)
            self._troops_layout.removeWidget(row)
            row.deleteLater()

    def _on_add_troop(self):
        new_troop = {
            'name': f'Troop {len(self._troop_rows) + 1}',
            'template': '',
            'is_custom_image': True,
            'deploy_style': 'diamond_perimeter',
            'count': 10,
            'delay': 0.15,
        }
        self._add_troop_row(new_troop)

    def _on_save(self):
        name = self._name_field.text().strip()
        if not name:
            QMessageBox.warning(self, 'Invalid Name', 'Please provide a name for this strategy.')
            return

        troops_data = [row.get_data() for row in self._troop_rows]
        self._data['name'] = name
        self._data['deploy_heroes'] = self._toggle_heroes.isChecked()
        self._data['deploy_spells'] = self._toggle_spells.isChecked()
        self._data['troops'] = troops_data

        self.accept()

    def get_strategy(self) -> Dict[str, Any]:
        return self._data
