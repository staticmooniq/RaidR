'''Run page — attack, schedule, modes, live status, controls.'''
from __future__ import annotations
from typing import Callable, List, Optional
from pathlib import Path
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QListView, QMessageBox, QScrollArea, QSpinBox, QStyledItemDelegate, QVBoxLayout, QWidget
)
from app.config import check_game_window_aspect_for_start
from app.ui.qt._constants import ATTACK_STRATEGIES, BUILDER_BASE_ATTACK_STRATEGIES, BUILDER_BASE_ATTACK_STRATEGIES_UNDER_DEV, BUILDER_BASE_PRIORITISE_LABELS
from app.ui.qt.bot_controller import BotController
from app.ui.qt.dialogs import RankedAttackConfirmDialog, show_bb_prioritise_help, show_error, show_under_development
from app.ui.qt.strategy_editor import StrategyEditorDialog
from app.ui.qt.theme import SPACING, TOKENS
from app.ui.qt.widgets import Card, HelpButton, PageTitle, SectionTitle, StepperButton, ToggleSwitch, chip_button, danger_button, neutral_button, primary_button, segment_button
from app.utils.common import ensure_dir, get_user_app_data_dir, get_resource_path
from app.utils.custom_strategy_store import (
    load_strategies, save_strategies, get_strategy_by_id
)
from app.utils.player_list_store import PlayerEntry, load_players

class RunPage(QWidget):
    _STRATEGY_LABELS = [
        'Valkyries',
        'Sneaky Goblins',
        'Super Minions',
        'Edrags']
    _VILLAGE_LABELS = [
        'Home Village',
        'Builder Base']
    _AUTO_UPGRADE_LABELS = [
        ('Off', 'off'),
        ('Dry run', 'dry'),
        ('Maxer', 'maxer'),
        ('Rusher', 'rusher')]

    def __init__(self, controller, navigate_to, parent = None):
        super().__init__(parent)
        self._controller = controller
        self._navigate_to = navigate_to
        self._settings = QSettings('RaidR', 'UI')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACING['lg'], SPACING['md'], SPACING['lg'], SPACING['lg'])
        outer.setSpacing(SPACING['sm'])
        self._village_selector_widget = self._build_village_selector()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(SPACING['md'])
        self._attack_card = self._build_attack_card()
        layout.addWidget(self._attack_card)
        self._bb_attack_card = self._build_bb_attack_card()
        layout.addWidget(self._bb_attack_card)
        layout.addWidget(self._build_schedule_card())
        self._modes_card = self._build_modes_card()
        layout.addWidget(self._modes_card)
        self._bb_modes_card = self._build_bb_modes_card()
        layout.addWidget(self._bb_modes_card)
        self._bb_extras_card = self._build_bb_extras_card()
        layout.addWidget(self._bb_extras_card)
        self._hv_extras_card = self._build_hv_extras_card()
        layout.addWidget(self._hv_extras_card)
        self._status_card = self._build_status_card()
        layout.addWidget(self._status_card)
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addWidget(self._build_controls_card())
        self._apply_village_ui()
        self._restore_choices()
        self._controller.botStarted.connect(self._on_bot_started)
        self._controller.botFinished.connect(self._on_bot_finished_ui)
        self._controller.runningChanged.connect(self._on_running_changed)
        self._controller.stateChanged.connect(self._on_state_changed)
        self._controller.lootChanged.connect(self._on_loot_changed)
        self._controller.statusChanged.connect(self._on_status_line)

    
    def _build_village_selector(self):
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACING['sm'])
        self._village_group = QButtonGroup(self)
        self._village_group.setExclusive(True)
        for i, label in enumerate(self._VILLAGE_LABELS):
            btn = segment_button(label, parent = wrapper)
            if label == 'Home Village':
                btn.setChecked(True)
            self._village_group.addButton(btn, i)
            row.addWidget(btn)
        self._village_group.idClicked.connect(self._on_village_changed)
        return wrapper

    def get_village_selector_widget(self):
        return self._village_selector_widget

    
    def _is_builder_base(self):
        btn = self._village_group.checkedButton()
        return btn is not None and btn.text() == 'Builder Base'

    
    def _on_village_changed(self, _button_id):
        self._apply_village_ui()

    
    def _apply_village_ui(self):
        builder_base = self._is_builder_base()
        self._attack_card.setVisible(not builder_base)
        self._modes_card.setVisible(not builder_base)
        self._bb_attack_card.setVisible(builder_base)
        self._bb_modes_card.setVisible(builder_base)
        self._bb_extras_card.setVisible(builder_base)
        self._hv_extras_card.setVisible(not builder_base)
        # Until-maxed (and the auto-upgrader behind it) is Home Village only.
        self._until_maxed.setVisible(not builder_base)
        if builder_base and self._until_maxed.isChecked():
            self._until_maxed.setChecked(False)

    
    def _build_attack_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Attack Strategy'))
        
        # Header row: Dropdown + Action Buttons on Left, Live Troop Composition Preview on Right
        strat_row = QHBoxLayout()
        strat_row.setSpacing(SPACING['sm'])

        self._strategy_combo = QComboBox()
        self._strategy_combo.setObjectName('StrategyPicker')
        self._strategy_combo.setMinimumHeight(38)
        self._strategy_combo.setMinimumWidth(180)
        self._strategy_combo.setMaximumWidth(220)
        
        # Ensure crisp rendering and styling for popup
        view = QListView()
        self._strategy_combo.setView(view)
        self._strategy_combo.setItemDelegate(QStyledItemDelegate(self._strategy_combo))
        strat_row.addWidget(self._strategy_combo)

        # New Strategy button
        self._btn_new_strategy = primary_button('+ New Strategy', parent=card)
        self._btn_new_strategy.setMinimumHeight(38)
        self._btn_new_strategy.clicked.connect(self._create_new_strategy)
        strat_row.addWidget(self._btn_new_strategy)

        # Edit Strategy button
        self._btn_edit_strategy = neutral_button('Edit Strategy', parent=card)
        self._btn_edit_strategy.setMinimumHeight(38)
        self._btn_edit_strategy.clicked.connect(self._edit_current_strategy)
        strat_row.addWidget(self._btn_edit_strategy)

        # Delete Strategy button
        self._btn_del_strategy = danger_button('Delete', parent=card)
        self._btn_del_strategy.setMinimumHeight(38)
        self._btn_del_strategy.clicked.connect(self._delete_current_strategy)
        strat_row.addWidget(self._btn_del_strategy)

        strat_row.addSpacing(14)

        # Live Troop Preview Container directly inside this row for maximum neatness and space
        self._strat_preview_container = QWidget()
        self._strat_preview_container.setStyleSheet("background: transparent;")
        self._strat_preview_layout = QHBoxLayout(self._strat_preview_container)
        self._strat_preview_layout.setContentsMargins(0, 0, 0, 0)
        self._strat_preview_layout.setSpacing(10)
        strat_row.addWidget(self._strat_preview_container, stretch=1)

        card.card_layout.addLayout(strat_row)

        self._populate_strategy_dropdown()
        self._strategy_combo.currentIndexChanged.connect(self._on_strategy_selected)
        return card

    def _populate_strategy_dropdown(self, select_id: Optional[str] = None):
        self._strategy_combo.blockSignals(True)
        self._strategy_combo.clear()
        strategies = load_strategies()
        target_idx = 0
        for i, s in enumerate(strategies):
            name = s.get('name', 'Strategy')
            sid = s.get('id', '')
            is_custom = not s.get('builtin', False)
            tag = " ★" if is_custom else ""
            self._strategy_combo.addItem(f"{name}{tag}", sid)
            if select_id and sid == select_id:
                target_idx = i

        self._strategy_combo.setCurrentIndex(target_idx)
        self._strategy_combo.blockSignals(False)
        self._update_strategy_preview()

    def _on_strategy_selected(self, _index: int):
        self._update_strategy_preview()

    def _update_strategy_preview(self):
        # Clear existing preview icons
        while self._strat_preview_layout.count() > 0:
            item = self._strat_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sid = self._strategy_combo.currentData()
        strat = get_strategy_by_id(sid)
        if not strat:
            return

        is_builtin = strat.get('builtin', False)
        self._btn_del_strategy.setEnabled(not is_builtin)

        troops = strat.get('troops', [])
        for t in troops:
            box = QWidget()
            h_box = QHBoxLayout(box)
            h_box.setContentsMargins(6, 4, 10, 4)
            h_box.setSpacing(8)
            box.setStyleSheet(f"""
                QWidget {{
                    background: {TOKENS['surface_hi']};
                    border: 1px solid {TOKENS['border_hi']};
                    border-radius: 8px;
                }}
            """)

            icon_lbl = QLabel()
            icon_lbl.setFixedSize(54, 34)
            icon_lbl.setStyleSheet(f"border: 1px solid {TOKENS['border']}; border-radius: 6px; background: {TOKENS['sidebar']};")
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            tmpl = t.get('template', '')
            is_custom = t.get('is_custom_image', False)
            img = QImage()
            if is_custom and tmpl and Path(tmpl).is_file():
                img = QImage(tmpl)
            elif tmpl:
                tmpl_file = tmpl if tmpl.endswith('.png') else f"{tmpl}.png"
                cand = get_resource_path(f"templates/16_9/{tmpl_file}")
                if cand.is_file():
                    img = QImage(str(cand))

            if not img.isNull():
                icon_lbl.setPixmap(
                    QPixmap.fromImage(img).scaled(
                        50, 30,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            else:
                sword_icon = get_resource_path('assets/sword_placeholder.png')
                if sword_icon.is_file():
                    icon_lbl.setPixmap(
                        QPixmap.fromImage(QImage(str(sword_icon))).scaled(
                            30, 30,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                    )

            h_box.addWidget(icon_lbl)

            count_str = f" x{t.get('count')}" if t.get('count', 0) > 0 else " (All)"
            info_lbl = QLabel(f"<b style='font-size: 13px;'>{t.get('name', 'Troop')}</b> <span style='color:{TOKENS['primary']}; font-weight:700;'>{count_str}</span>")
            info_lbl.setStyleSheet("border: none; background: transparent;")
            h_box.addWidget(info_lbl)

            self._strat_preview_layout.addWidget(box)

        self._strat_preview_layout.addStretch()

    def _create_new_strategy(self):
        dlg = StrategyEditorDialog(parent=self.window())
        if dlg.exec():
            new_strat = dlg.get_strategy()
            strats = load_strategies()
            strats.append(new_strat)
            save_strategies(strats)
            self._populate_strategy_dropdown(select_id=new_strat['id'])

    def _edit_current_strategy(self):
        sid = self._strategy_combo.currentData()
        strat = get_strategy_by_id(sid)
        if not strat:
            return
        dlg = StrategyEditorDialog(strategy_data=strat, parent=self.window())
        if dlg.exec():
            updated = dlg.get_strategy()
            # If editing a built-in strategy, convert it into an editable custom clone if needed or update
            updated['builtin'] = False
            strats = load_strategies()
            for i, s in enumerate(strats):
                if s.get('id') == sid:
                    strats[i] = updated
                    break
            save_strategies(strats)
            self._populate_strategy_dropdown(select_id=updated['id'])

    def _delete_current_strategy(self):
        sid = self._strategy_combo.currentData()
        strat = get_strategy_by_id(sid)
        if not strat or strat.get('builtin', False):
            QMessageBox.information(self, 'Built-in Strategy', 'Default built-in strategies cannot be deleted.')
            return

        reply = QMessageBox.question(
            self, 'Delete Strategy',
            f"Are you sure you want to delete custom strategy '{strat.get('name')}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            strats = [s for s in load_strategies() if s.get('id') != sid]
            save_strategies(strats)
            self._populate_strategy_dropdown()

    @staticmethod
    def _secondary_image_path():
        return get_user_app_data_dir() / 'secondary_troop.png'

    def _on_secondary_troop_toggle(self, enabled):
        for widget in (self._secondary_upload, self._secondary_paste, self._secondary_count):
            widget.setEnabled(bool(enabled))

    def _placeholder_image_path(self):
        from app.utils.common import get_resource_path
        return get_resource_path('assets/default_troop_placeholder.png')

    def _show_secondary_image(self):
        path = self._secondary_image_path()
        image = QImage(str(path)) if path.is_file() else QImage()
        self._secondary_image_preview.setText('')
        if image.isNull():
            # Show transparent barbarian subject perfectly centered when no custom screenshot is uploaded
            placeholder = self._placeholder_image_path()
            if placeholder.is_file():
                ph_img = QImage(str(placeholder))
                self._secondary_image_preview.setPixmap(
                    QPixmap.fromImage(ph_img).scaled(
                        44, 44,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            else:
                self._secondary_image_preview.setPixmap(QPixmap())
            return False
        self._secondary_image_preview.setPixmap(
            QPixmap.fromImage(image).scaled(
                48, 48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        return True

    def _save_secondary_image(self, image):
        if image is None or image.isNull():
            show_error(self.window(), 'Secondary troop', 'The selected image could not be read.')
            return False
        ensure_dir(self._secondary_image_path().parent)
        image = image.convertToFormat(QImage.Format.Format_RGB32)
        if not image.save(str(self._secondary_image_path()), 'PNG'):
            show_error(self.window(), 'Secondary troop', 'Could not save the troop image.')
            return False
        self._show_secondary_image()
        return True

    def _select_secondary_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Select secondary troop image', '', 'Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if filename:
            self._save_secondary_image(QImage(filename))

    def _paste_secondary_image(self):
        image = QApplication.clipboard().image()
        if image.isNull():
            show_error(self.window(), 'Secondary troop', 'The clipboard does not contain an image. Copy a troop icon image first.')
            return
        self._save_secondary_image(image)

    
    def _build_bb_attack_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Attack Strategy'))
        row = QHBoxLayout()
        self._bb_strategy_group = QButtonGroup(self)
        self._bb_strategy_group.setExclusive(True)
        for i, label in enumerate(BUILDER_BASE_ATTACK_STRATEGIES):
            btn = segment_button(label, parent = card)
            if label == 'Baby Dragon':
                btn.setChecked(True)
            self._bb_strategy_group.addButton(btn, i)
            row.addWidget(btn)
        for label in BUILDER_BASE_ATTACK_STRATEGIES_UNDER_DEV:
            btn = segment_button(label, parent = card, under_development = True)
            btn.clicked.connect((lambda _checked = False: show_under_development(self.window())))
            row.addWidget(btn)
        row.addStretch()
        card.card_layout.addLayout(row)
        return card

    
    def _build_schedule_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Schedule'))
        self._star_bonus = ToggleSwitch('Star Bonus', parent = card)
        self._star_bonus.toggled.connect(self._on_star_bonus_toggle)
        card.card_layout.addWidget(self._star_bonus)
        self._until_maxed = ToggleSwitch('Run until maxed (no time limit)', parent = card)
        self._until_maxed.toggled.connect(self._on_until_maxed_toggle)
        card.card_layout.addWidget(self._until_maxed)
        until_hint = QLabel('Farms, upgrades, and idles in a loop until you press Stop. When storages are full and nothing can be started, the bot waits and rechecks every 5 minutes instead of attacking for nothing.')
        until_hint.setWordWrap(True)
        until_hint.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        card.card_layout.addWidget(until_hint)
        dur_row = QHBoxLayout()
        self._duration_label = SectionTitle('Duration')
        dur_row.addWidget(self._duration_label)
        self._minutes_spin = QSpinBox()
        self._minutes_spin.setObjectName('DurationSpin')
        self._minutes_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._minutes_spin.setRange(1, 999)
        self._minutes_spin.setValue(15)
        self._minutes_spin.setFixedSize(56, 28)
        self._minutes_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        step_col = QVBoxLayout()
        step_col.setSpacing(2)
        step_col.setContentsMargins(0, 0, 0, 0)
        self._btn_spin_up = StepperButton(up = True, parent = card)
        self._btn_spin_up.clicked.connect((lambda : self._step_minutes(1)))
        self._btn_spin_down = StepperButton(up = False, parent = card)
        self._btn_spin_down.clicked.connect((lambda : self._step_minutes(-1)))
        step_col.addWidget(self._btn_spin_up)
        step_col.addWidget(self._btn_spin_down)
        self._minutes_unit = QLabel('minutes')
        self._minutes_unit.setObjectName('DurationUnit')
        self._minutes_unit.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        spin_group = QHBoxLayout()
        spin_group.setSpacing(4)
        spin_group.addWidget(self._minutes_spin)
        spin_group.addLayout(step_col)
        spin_group.addWidget(self._minutes_unit)
        spin_group.addStretch()
        dur_row.addLayout(spin_group)
        dur_row.addStretch()
        card.card_layout.addLayout(dur_row)
        preset_row = QHBoxLayout()
        self._btn_5m = chip_button('5m', parent = card)
        self._btn_5m.clicked.connect((lambda : self._set_minutes(5)))
        preset_row.addWidget(self._btn_5m)
        self._btn_10m = chip_button('10m', parent = card)
        self._btn_10m.clicked.connect((lambda : self._set_minutes(10)))
        preset_row.addWidget(self._btn_10m)
        self._btn_20m = chip_button('20m', parent = card)
        self._btn_20m.clicked.connect((lambda : self._set_minutes(20)))
        preset_row.addWidget(self._btn_20m)
        preset_row.addStretch()
        card.card_layout.addLayout(preset_row)
        self._on_star_bonus_toggle(self._star_bonus.isChecked())
        return card

    
    def _build_modes_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Modes'))
        upg_row = QHBoxLayout()
        upg_row.addWidget(SectionTitle('Auto upgrade'))
        upg_row.addSpacing(SPACING['xs'])
        self._auto_upgrade_group = QButtonGroup(self)
        self._auto_upgrade_group.setExclusive(True)
        for i, (label, _key) in enumerate(self._AUTO_UPGRADE_LABELS):
            btn = segment_button(label, parent = card)
            if label == 'Off':
                btn.setChecked(True)
            self._auto_upgrade_group.addButton(btn, i)
            upg_row.addWidget(btn)
        upg_row.addStretch()
        card.card_layout.addLayout(upg_row)
        upg_hint = QLabel('Maxer starts the cheapest affordable upgrade with your loot (never the Town Hall); Rusher grabs the Town Hall the moment it is affordable. Dry run only logs what it would start. Works at any Town Hall level. Reserve builders for walls in Settings.')
        upg_hint.setWordWrap(True)
        upg_hint.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        card.card_layout.addWidget(upg_hint)
        self._ranked = ToggleSwitch('Ranked attack fill', parent = card, danger = True)
        card.card_layout.addWidget(self._ranked)
        self._upgrade_walls = ToggleSwitch('Upgrade walls', parent = card)
        card.card_layout.addWidget(self._upgrade_walls)
        mr_row = QHBoxLayout()
        self._multi_run = ToggleSwitch('Multi-run', parent = card)
        mr_row.addWidget(self._multi_run)
        mr_row.addStretch()
        edit_players = neutral_button('Edit player list', parent = card)
        edit_players.clicked.connect((lambda : self._navigate_to('settings')))
        mr_row.addWidget(edit_players)
        card.card_layout.addLayout(mr_row)
        return card

    
    def _build_bb_modes_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Modes'))
        prior_row = QHBoxLayout()
        prior_row.addWidget(SectionTitle('Prioritise'))
        prior_help = HelpButton((lambda : show_bb_prioritise_help(self.window())), parent = card)
        prior_row.addWidget(prior_help, alignment = Qt.AlignmentFlag.AlignVCenter)
        prior_row.addSpacing(SPACING['xs'])
        self._bb_prioritise_group = QButtonGroup(self)
        self._bb_prioritise_group.setExclusive(True)
        for i, label in enumerate(BUILDER_BASE_PRIORITISE_LABELS):
            btn = segment_button(label, parent = card)
            if label == 'Both':
                btn.setChecked(True)
            self._bb_prioritise_group.addButton(btn, i)
            prior_row.addWidget(btn)
        prior_row.addStretch()
        card.card_layout.addLayout(prior_row)
        self._bb_upgrade_walls = ToggleSwitch('Upgrade walls', parent = card)
        self._bb_upgrade_walls.setToolTip('Before and after battles, open Build, find a Wall row, add affordable walls, and confirm the upgrade.')
        card.card_layout.addWidget(self._bb_upgrade_walls)
        wall_hint = QLabel('Uses Builder Gold or Builder Elixir only when the wall batch is affordable.')
        wall_hint.setWordWrap(True)
        wall_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(wall_hint)
        mr_row = QHBoxLayout()
        self._bb_multi_run = ToggleSwitch('Multi-run', parent = card, under_development = True)
        mr_row.addWidget(self._bb_multi_run)
        mr_row.addStretch()
        edit_players = neutral_button('Edit player list', parent = card)
        edit_players.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        edit_players.clicked.connect((lambda : show_under_development(self.window())))
        mr_row.addWidget(edit_players)
        card.card_layout.addLayout(mr_row)
        return card

    
    def _build_hv_extras_card(self):
        card = Card(variant='extras')
        title_row = QHBoxLayout()
        extras_title = SectionTitle('Extras')
        extras_title.setStyleSheet(f"color: {TOKENS['primary']}; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        title_row.addWidget(extras_title)
        title_row.addStretch()
        card.card_layout.addLayout(title_row)
        self._three_star_toggle = ToggleSwitch('3 Star  — end battle only after 3 stars', parent=card)
        self._three_star_toggle.setChecked(True)
        self._three_star_toggle.setToolTip('When ON: waits for 3 stars before ending battle. When OFF: ends after 1 star.')
        card.card_layout.addWidget(self._three_star_toggle)
        self._rage_spell_toggle = ToggleSwitch('Rage Spell  — use rage instead of earthquake', parent=card)
        self._rage_spell_toggle.setChecked(False)
        self._rage_spell_toggle.setToolTip('When ON: bot places rage spells along the Edrag funnel path.')
        card.card_layout.addWidget(self._rage_spell_toggle)
        return card

    def _build_bb_extras_card(self):
        card = Card(variant='extras')
        title_row = QHBoxLayout()
        extras_title = SectionTitle('Extras')
        extras_title.setStyleSheet(f"color: {TOKENS['primary']}; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        title_row.addWidget(extras_title)
        title_row.addStretch()
        card.card_layout.addLayout(title_row)
        self._bb_two_star_toggle = ToggleSwitch('End after 2 stars', parent=card)
        self._bb_two_star_toggle.setChecked(False)
        self._bb_two_star_toggle.setToolTip('When on, ends the battle once two stars are detected. When off, keeps the existing full-battle flow.')
        card.card_layout.addWidget(self._bb_two_star_toggle)
        two_star_hint = QLabel('When off, the bot follows the normal Builder Base battle sequence.')
        two_star_hint.setWordWrap(True)
        two_star_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(two_star_hint)
        return card

    def is_two_star_enabled(self):
        return self._bb_two_star_toggle.isChecked()

    def is_three_star_enabled(self):
        return self._three_star_toggle.isChecked()

    def is_rage_spell_enabled(self):
        return self._rage_spell_toggle.isChecked()

    def _build_status_card(self):
        card = Card(variant='status')
        card.card_layout.addWidget(SectionTitle('Live status'))
        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING['lg'])
        grid.setVerticalSpacing(4)

        def stat(row, col, title):
            t = QLabel(title.upper())
            t.setObjectName('StatTitle')
            font = t.font()
            font.setLetterSpacing(font.SpacingType.PercentageSpacing, 110)
            t.setFont(font)
            v = QLabel('—')
            v.setObjectName('StatValue')
            # Word-wrap keeps a long readout (the storages triplet) from inflating the
            # card's minimum width past the viewport (clipped every card's right edge).
            v.setWordWrap(True)
            grid.addWidget(t, row * 2, col)
            grid.addWidget(v, row * 2 + 1, col)
            grid.setColumnStretch(col, 1)
            return v

        self._stat_state = stat(0, 0, 'State')
        self._stat_builders = stat(0, 1, 'Builders free')
        self._stat_lab = stat(0, 2, 'Lab free')
        self._stat_storages = stat(0, 3, 'Storages')
        self._stat_loot = stat(1, 0, 'Loot this session')
        self._stat_loot_rate = stat(1, 1, 'Loot / hour')
        self._stat_note = QLabel('Start the bot to see live village state here. Builders / lab / storages update while Auto upgrade is on.')
        self._stat_note.setWordWrap(True)
        self._stat_note.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
        card.card_layout.addLayout(grid)
        card.card_layout.addWidget(self._stat_note)
        return card

    @staticmethod
    def _fmt_amount(value):
        value = int(value)
        if value >= 1000000:
            return f'''{value / 1000000:.1f}M'''
        if value >= 10000:
            return f'''{value / 1000:.0f}k'''
        return str(value)

    _STATE_COLORS = {
        'farming': '#4ADE80',  # engaged green
        'idling': '#F59E0B',   # holding amber
    }

    def _on_state_changed(self, payload):
        state = payload.get('state')
        if state:
            self._stat_state.setText(str(state).upper())
            color = self._STATE_COLORS.get(str(state).lower(), TOKENS['text'])
            self._stat_state.setStyleSheet(f'''color: {color};''')
        builders = payload.get('builders')
        if builders:
            self._stat_builders.setText(f'''{builders[0]} / {builders[1]}''')
        lab = payload.get('lab')
        if lab:
            self._stat_lab.setText(f'''{lab[0]} / {lab[1]}''')
        storages = payload.get('storages')
        if storages:
            self._stat_storages.setText(str(storages))
        note = payload.get('note')
        if note:
            self._stat_note.setText(f'''Upgrades: {note}''')

    def _on_loot_changed(self, gold, elixir, dark, elapsed):
        self._stat_loot.setText(f'''{self._fmt_amount(gold)} / {self._fmt_amount(elixir)} / {self._fmt_amount(dark)}''')
        if elapsed < 600:
            # A per-hour figure extrapolated from a few minutes is noise — hold it back.
            self._stat_loot_rate.setText('— (needs 10m)')
            return None
        hours = elapsed / 3600
        self._stat_loot_rate.setText(f'''{self._fmt_amount(gold / hours)} / {self._fmt_amount(elixir / hours)} / {self._fmt_amount(dark / hours)}''')

    def _on_status_line(self, msg, _warning):
        if msg.lower().startswith(('idling', 'resuming')):
            idling = msg.lower().startswith('idling')
            self._stat_state.setText('IDLING' if idling else 'FARMING')
            self._stat_state.setStyleSheet(f'''color: {self._STATE_COLORS['idling' if idling else 'farming']};''')
            self._stat_note.setText(msg)

    def _confirm_bb_elixir_prioritise(self):
        reply = QMessageBox.warning(self.window(), 'Elixir priority', 'Prioritising Elixir will deplete your trophies.\n\nDo you want to continue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes

    
    def _build_controls_card(self):
        card = Card()
        card.setObjectName('RunControls')
        card.setStyleSheet(f'''QFrame#RunControls {{ background: {TOKENS['surface']}; border: 1px solid {TOKENS['border_hi']}; border-radius: 10px; }}''')
        card.card_layout.setContentsMargins(SPACING['lg'], SPACING['sm'], SPACING['lg'], SPACING['sm'])
        btn_row = QHBoxLayout()
        self._btn_start = primary_button('Start bot', parent = card)
        self._btn_start.setMinimumHeight(42)
        self._btn_start.setMinimumWidth(160)
        self._btn_start.clicked.connect(self.start_bot)
        btn_row.addWidget(self._btn_start)
        self._btn_stop = danger_button('Stop bot', parent = card)
        self._btn_stop.setMinimumHeight(42)
        self._btn_stop.setMinimumWidth(120)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._controller.stop)
        btn_row.addWidget(self._btn_stop)
        card.card_layout.addLayout(btn_row)
        return card

    
    def _clear_minutes_selection(self):
        editor = self._minutes_spin.lineEdit()
        if not editor is None:
            editor.deselect()
            editor.setCursorPosition(len(editor.text()))
            return None

    
    def _duration_locked(self):
        return self._star_bonus.isChecked() or self._until_maxed.isChecked()

    def _step_minutes(self, delta):
        if self._duration_locked():
            return None
        if delta > 0:
            self._minutes_spin.stepUp()
        else:
            self._minutes_spin.stepDown()
        self._clear_minutes_selection()
        QTimer.singleShot(0, self._clear_minutes_selection)


    def _set_minutes(self, value):
        if self._duration_locked():
            return None
        self._minutes_spin.setValue(value)
        self._clear_minutes_selection()


    def _update_duration_enabled(self):
        enabled = not self._duration_locked()
        duration_widgets = (self._duration_label, self._minutes_spin, self._btn_spin_up, self._btn_spin_down, self._minutes_unit, self._btn_5m, self._btn_10m, self._btn_20m)
        for widget in duration_widgets:
            widget.setEnabled(enabled)
        if enabled:
            self._minutes_unit.setStyleSheet(f'''color: {TOKENS['text_muted']};''')
            return None
        self._minutes_unit.setStyleSheet('color: #4a5568;')

    def _on_star_bonus_toggle(self, checked):
        if checked and getattr(self, '_until_maxed', None) is not None and self._until_maxed.isChecked():
            self._until_maxed.setChecked(False)
        self._update_duration_enabled()

    def _on_until_maxed_toggle(self, checked):
        if checked and self._star_bonus.isChecked():
            self._star_bonus.setChecked(False)
        self._update_duration_enabled()

    
    def _get_method(self):
        if self._is_builder_base():
            btn = self._bb_strategy_group.checkedButton()
            if btn is None:
                return BUILDER_BASE_ATTACK_STRATEGIES['Baby Dragon']
            return BUILDER_BASE_ATTACK_STRATEGIES.get(btn.text(), 5)
        
        sid = self._strategy_combo.currentData()
        strat = get_strategy_by_id(sid)
        if strat and strat.get('builtin', False):
            return strat.get('builtin_id', 3)
        return 100 # Custom Strategy indicator

    def _get_custom_strategy_data(self):
        if self._is_builder_base():
            return None
        sid = self._strategy_combo.currentData()
        strat = get_strategy_by_id(sid)
        if strat and not strat.get('builtin', False):
            return strat
        return None

    
    def _get_bb_prioritise(self):
        btn = self._bb_prioritise_group.checkedButton()
        if btn is None:
            return 'both'
        return btn.text().lower()


    def _get_auto_upgrade_mode(self):
        checked_id = self._auto_upgrade_group.checkedId()
        if 0 <= checked_id < len(self._AUTO_UPGRADE_LABELS):
            return self._AUTO_UPGRADE_LABELS[checked_id][1]
        return 'off'

    def _set_auto_upgrade_mode(self, mode):
        for i, (_label, key) in enumerate(self._AUTO_UPGRADE_LABELS):
            if key == mode:
                btn = self._auto_upgrade_group.button(i)
                if btn is not None:
                    btn.setChecked(True)
                return None

    def _restore_choices(self):
        '''Bring back the last run's choices (village, strategy, mode, walls, duration) across app starts.'''
        # Village choice
        village_idx = self._settings.value('run/villageIndex', 0, type=int)
        if 0 <= village_idx < len(self._VILLAGE_LABELS):
            btn = self._village_group.button(village_idx)
            if btn is not None:
                btn.setChecked(True)
                self._apply_village_ui()

        # Home Village attack strategy
        strategy_id = self._settings.value('run/strategyId', 'valkyries', type=str)
        idx = self._strategy_combo.findData(strategy_id)
        if idx >= 0:
            self._strategy_combo.setCurrentIndex(idx)

        # Builder Base attack strategy
        bb_strategy_idx = self._settings.value('run/bbStrategyIndex', 0, type=int)
        if 0 <= bb_strategy_idx < len(BUILDER_BASE_ATTACK_STRATEGIES):
            btn = self._bb_strategy_group.button(bb_strategy_idx)
            if btn is not None:
                btn.setChecked(True)

        # Builder Base prioritize
        bb_prioritise_idx = self._settings.value('run/bbPrioritiseIndex', 1, type=int)
        if 0 <= bb_prioritise_idx < len(BUILDER_BASE_PRIORITISE_LABELS):
            btn = self._bb_prioritise_group.button(bb_prioritise_idx)
            if btn is not None:
                btn.setChecked(True)

        # Home Village extras
        self._three_star_toggle.setChecked(self._settings.value('run/threeStar', True, type=bool))
        self._rage_spell_toggle.setChecked(self._settings.value('run/rageSpell', False, type=bool))

        # Ranked attack & Multi run
        self._ranked.setChecked(self._settings.value('run/rankedFill', False, type=bool))
        self._multi_run.setChecked(self._settings.value('run/multiRun', False, type=bool))

        # Star Bonus
        self._star_bonus.setChecked(self._settings.value('run/starBonus', False, type=bool))

        self._set_auto_upgrade_mode(str(self._settings.value('run/autoUpgrade', 'off')))
        self._upgrade_walls.setChecked(self._settings.value('run/upgradeWalls', False, type = bool))
        self._bb_upgrade_walls.setChecked(self._settings.value('run/bbUpgradeWalls', False, type = bool))
        self._bb_two_star_toggle.setChecked(self._settings.value('run/bbTwoStar', False, type = bool))
        self._until_maxed.setChecked(self._settings.value('run/untilMaxed', False, type = bool))
        minutes = self._settings.value('run/minutes', 15, type = int)
        if 1 <= minutes <= 999:
            self._minutes_spin.setValue(minutes)

    def _save_choices(self):
        self._settings.setValue('run/villageIndex', self._village_group.checkedId())
        self._settings.setValue('run/strategyId', self._strategy_combo.currentData())
        self._settings.setValue('run/bbStrategyIndex', self._bb_strategy_group.checkedId())
        self._settings.setValue('run/bbPrioritiseIndex', self._bb_prioritise_group.checkedId())
        self._settings.setValue('run/threeStar', self._three_star_toggle.isChecked())
        self._settings.setValue('run/rageSpell', self._rage_spell_toggle.isChecked())
        self._settings.setValue('run/rankedFill', self._ranked.isChecked())
        self._settings.setValue('run/multiRun', self._multi_run.isChecked())
        self._settings.setValue('run/starBonus', self._star_bonus.isChecked())
        self._settings.setValue('run/autoUpgrade', self._get_auto_upgrade_mode())
        self._settings.setValue('run/upgradeWalls', self._upgrade_walls.isChecked())
        self._settings.setValue('run/bbUpgradeWalls', self._bb_upgrade_walls.isChecked())
        self._settings.setValue('run/bbTwoStar', self._bb_two_star_toggle.isChecked())
        self._settings.setValue('run/untilMaxed', self._until_maxed.isChecked())
        self._settings.setValue('run/minutes', self._minutes_spin.value())

    
    def _get_minutes(self):
        return self._minutes_spin.value()

    
    def _multi_run_players_for_start(self):
        if self._is_builder_base() or not self._multi_run.isChecked():  # [recovered: decompiler inverted both halves — multi-run never engaged on Home Village]
            return None
        players = load_players()
        if not any([ p.enabled and p.name.strip() for p in players ]):
            return []
        return players

    
    def start_bot(self):
        if self._controller.is_running():
            return None
        if not check_game_window_aspect_for_start(parent = self.window(), on_configure = (lambda : self._navigate_to('settings'))):
            return None
        builder_base = self._is_builder_base()
        method = self._get_method()
        multi_arg = self._multi_run_players_for_start()
        if not builder_base and self._multi_run.isChecked() and not multi_arg:  # [recovered: decompiler dropped the `not` — the error fired when players DID exist]
            show_error(self.window(), 'Multi-run', 'Enable at least one player with Run and a non-empty name.\nOpen Player list… to edit.')
            return None
        star_bonus = self._star_bonus.isChecked()
        # "Run until maxed" = unlimited duration; single Home Village runs only.
        until_maxed = (not builder_base and not star_bonus and multi_arg is None
                       and self._until_maxed.isChecked())
        if star_bonus:
            mins = 5
        elif until_maxed:
            mins = 0
        else:
            mins = self._get_minutes()
            if mins <= 0 or mins > 999:
                show_error(self.window(), 'Error', 'Invalid time duration. Enter 1-999 minutes.')
                return None
        ranked_fill = False if builder_base else self._ranked.isChecked()
        if ranked_fill:
            confirm_mins = self._get_minutes()
            if not RankedAttackConfirmDialog.ask(self.window(), confirm_mins):
                return None
        if builder_base and self._get_bb_prioritise() == 'elixir' and not self._confirm_bb_elixir_prioritise():  # [recovered: decompiler inverted both conditions]
            return None
        self._save_choices()
        custom_data = self._get_custom_strategy_data()
        self._controller.start(method = method, minutes = mins, star_bonus = star_bonus, ranked_fill = ranked_fill, upgrade_walls = self._bb_upgrade_walls.isChecked() if builder_base else self._upgrade_walls.isChecked(), multi_run_players = multi_arg, builder_base = builder_base, loot_prioritise = self._get_bb_prioritise() if builder_base else 'both', auto_upgrade = 'off' if builder_base else self._get_auto_upgrade_mode(), secondary_troop_template = '', secondary_troop_count = 0, three_star_mode = self.is_three_star_enabled(), rage_spell = self.is_rage_spell_enabled(), two_star_mode = self.is_two_star_enabled() if builder_base else False, custom_strategy_data = custom_data)

    
    def is_star_bonus_enabled(self):
        return self._star_bonus.isChecked()

    
    def request_start_from_taskbar(self):
        if not self._controller.is_running():
            self.start_bot()
            return None


    def apply_autostart(self, minutes, upgrade_walls, auto_upgrade = 'off'):
        '''CLI ``--autostart``: Home Village run with the given duration (``0`` =
        run until maxed), wall toggle, and auto-upgrade mode (off|dry|maxer|rusher).'''
        if self._controller.is_running():
            return None
        self._star_bonus.setChecked(False)
        self._until_maxed.setChecked(minutes <= 0)
        if minutes > 0:
            self._minutes_spin.setValue(minutes)
        self._upgrade_walls.setChecked(bool(upgrade_walls))
        self._set_auto_upgrade_mode(auto_upgrade)
        self.start_bot()

    
    def request_stop_from_taskbar(self):
        if self._controller.is_running():
            self._controller.stop()
            return None

    
    def _on_bot_started(self):
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)

    
    def _on_bot_finished_ui(self, _error):
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    
    def _on_running_changed(self, running):
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)


