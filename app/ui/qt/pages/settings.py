'''Settings page - profile preferences and manual game-window selection.'''
from __future__ import annotations
from typing import List, Optional
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QScrollArea, QSpinBox, QVBoxLayout, QWidget
)
from app import __version__
from app.config import resolve_aspect_key
from app.services.display import DisplayService
from app.services.updater import UpdateCheckerThread, UpdateInfo
from app.services.window import DescendantInfo, WindowCandidate, WindowService
from app.ui.qt.theme import SPACING, TOKENS, THEME_TEMPLATES, apply_theme
from app.ui.qt.update_dialog import UpdateDialog
from app.ui.qt.widgets import Card, PageTitle, SectionTitle, ToggleSwitch, chip_button, danger_button, neutral_button, primary_button
from app.utils.logger import setup_logger
from app.utils.player_list_store import PlayerEntry, load_players, save_players
from app.utils.profile_settings_store import (
    EARTHQUAKE_METHOD_OPTIONS, RESERVE_BUILDERS_MAX, WALL_UPGRADE_THRESHOLD_M_MAX,
    MIN_GOLD_K_MAX, MIN_ELIXIR_K_MAX, MIN_DARK_ELIXIR_MAX, MAX_NEXT_SKIPS_MAX,
    BATTLE_END_DELAY_MAX, ProfileSettings, load_profile_settings, save_profile_settings
)
from app.utils.window_settings_store import clear_window_selection, load_window_selection, save_window_selection

logger = setup_logger('SettingsPage')

class WindowInfoDialog(QDialog):
    '''Read-only view of every child window/surface under a selected top-level window.'''
    
    def __init__(self, parent, candidate, descendants):
        super().__init__(parent)
        self.setWindowTitle('Window info')
        self.setModal(True)
        self.resize(640, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        layout.setSpacing(SPACING['sm'])
        header = QLabel(f'Top-level: {candidate.title or "(no title)"}\nClass: {candidate.top_class}    hwnd={candidate.top_hwnd}')
        header.setWordWrap(True)
        header.setStyleSheet(f"color: {TOKENS['text']};")
        layout.addWidget(header)
        count = len(descendants)
        surfaces = sum([1 for d in descendants if d.is_surface])
        summary = QLabel(f'{count} child window(s), {surfaces} game surface(s). Surfaces are marked [surface].')
        summary.setStyleSheet(f"color: {TOKENS['text_muted']};")
        layout.addWidget(summary)
        listing = QListWidget()
        listing.setObjectName('WindowInfoList')
        mono = QFont('Consolas')
        mono.setStyleHint(QFont.StyleHint.Monospace)
        listing.setFont(mono)
        if descendants:
            for d in descendants:
                item = QListWidgetItem(d.display_label())
                if d.is_surface:
                    item.setForeground(QColor(TOKENS['primary']))
                listing.addItem(item)
        else:
            listing.addItem(QListWidgetItem('No child windows found under this window.'))
        layout.addWidget(listing, stretch = 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = neutral_button('Close', parent = self)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


class SettingsPage(QWidget):
    
    def __init__(self, parent = None):
        super().__init__(parent)
        self._candidates = []
        self._display = DisplayService()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACING['lg'], SPACING['lg'], SPACING['lg'], SPACING['lg'])
        outer.setSpacing(SPACING['md'])
        outer.addWidget(PageTitle('Settings'))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING['md'])
        layout.addWidget(self._build_theme_card())
        layout.addWidget(self._build_overlay_card())
        layout.addWidget(self._build_players_card())
        layout.addWidget(self._build_earthquake_card())
        layout.addWidget(self._build_loot_filter_card())
        layout.addWidget(self._build_window_card())
        layout.addWidget(self._build_updates_card())
        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _build_theme_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Theme & Color Presets'))
        hint = QLabel('Customize the accent glow and button styling across the entire bot controller UI.')
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(SPACING['md'])
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(list(THEME_TEMPLATES.keys()))
        self._theme_combo.setMinimumWidth(180)

        # Restore saved theme
        settings = QSettings('RaidR', 'UI')
        saved_theme = settings.value('theme/template', 'Electric Blue')
        idx = self._theme_combo.findText(saved_theme)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)

        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        row.addWidget(self._theme_combo)

        self._theme_preview = QLabel('Preset active')
        self._theme_preview.setStyleSheet(f"color: {TOKENS['primary']}; font-weight: 700;")
        row.addWidget(self._theme_preview)
        row.addStretch()

        card.card_layout.addLayout(row)
        return card

    def _build_overlay_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('In-Game Touch Overlay'))
        
        row = QHBoxLayout()
        row.setSpacing(SPACING['md'])
        
        label_col = QVBoxLayout()
        label_col.setSpacing(2)
        title = QLabel('Show touch ripples in game')
        title.setStyleSheet(f"color: {TOKENS['text']}; font-weight: 600; font-size: 13px;")
        desc = QLabel('Displays transparent click-through glow animations on top of Clash of Clans to visualize where the bot clicks and drags.')
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TOKENS['text_muted']}; font-size: 11px;")
        label_col.addWidget(title)
        label_col.addWidget(desc)
        row.addLayout(label_col, stretch=1)

        self._overlay_toggle = ToggleSwitch()
        settings = QSettings('RaidR', 'UI')
        # Enabled by default
        enabled = settings.value('overlay/enabled', True, type=bool)
        self._overlay_toggle.setChecked(enabled)
        self._overlay_toggle.toggled.connect(self._on_overlay_toggled)
        row.addWidget(self._overlay_toggle)

        card.card_layout.addLayout(row)
        return card

    def _on_overlay_toggled(self, checked: bool):
        settings = QSettings('RaidR', 'UI')
        settings.setValue('overlay/enabled', checked)
        self._flash_status_bar(f"Touch overlay {'enabled' if checked else 'disabled'}")

    def _on_theme_changed(self, theme_name: str):
        settings = QSettings('RaidR', 'UI')
        settings.setValue('theme/template', theme_name)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, theme_name)
        # Trigger background redraw on main window
        top_win = self.window()
        if top_win is not None:
            central = top_win.centralWidget()
            if central is not None:
                central.update()
            if hasattr(top_win, '_brand_label'):
                top_win._brand_label.setText(f'''<span style="color:{TOKENS['primary']}">Raid</span><span style="color:{TOKENS['text']}">R</span>''')
        if hasattr(self, '_theme_preview'):
            self._theme_preview.setStyleSheet(f"color: {TOKENS['primary']}; font-weight: 700;")
        self._flash_status_bar(f'Theme updated: {theme_name}')

    def _build_earthquake_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Earthquake placement'))
        self._earthquake = QComboBox()
        self._earthquake.addItems(list(EARTHQUAKE_METHOD_OPTIONS))
        card.card_layout.addWidget(self._earthquake)
        
        card.card_layout.addWidget(SectionTitle('Wall upgrade threshold'))
        wall_hint = QLabel('With "Upgrade walls" on, upgrade as soon as gold or elixir reaches this amount - before storages fill up and raids stop earning. 0 = only upgrade when storages are full.')
        wall_hint.setWordWrap(True)
        wall_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(wall_hint)
        wall_row = QHBoxLayout()
        self._wall_threshold = QSpinBox()
        self._wall_threshold.setRange(0, WALL_UPGRADE_THRESHOLD_M_MAX)
        self._wall_threshold.setSuffix('M')
        self._wall_threshold.setFixedWidth(88)
        wall_row.addWidget(self._wall_threshold)
        wall_unit = QLabel('gold or elixir')
        wall_unit.setStyleSheet(f"color: {TOKENS['text_muted']};")
        wall_row.addWidget(wall_unit)
        wall_row.addStretch()
        card.card_layout.addLayout(wall_row)

        card.card_layout.addWidget(SectionTitle('Upgrade order'))
        order_hint = QLabel('Priciest first soaks full storages into the biggest jobs (best when the bot farms loot faster than builders free up). Dark elixir upgrades (heroes) always get first claim either way.')
        order_hint.setWordWrap(True)
        order_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(order_hint)
        self._upgrade_order = QComboBox()
        self._upgrade_order.addItems(['Priciest first', 'Cheapest first'])
        card.card_layout.addWidget(self._upgrade_order)

        card.card_layout.addWidget(SectionTitle('Reserve builders'))
        reserve_hint = QLabel('With Auto upgrade on, keep this many builders free (the wall flow spends through them). Set 0 when your walls are maxed so every builder is used for upgrades.')
        reserve_hint.setWordWrap(True)
        reserve_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(reserve_hint)
        reserve_row = QHBoxLayout()
        self._reserve_builders = QSpinBox()
        self._reserve_builders.setRange(0, RESERVE_BUILDERS_MAX)
        self._reserve_builders.setFixedWidth(88)
        reserve_row.addWidget(self._reserve_builders)
        reserve_unit = QLabel('builders')
        reserve_unit.setStyleSheet(f"color: {TOKENS['text_muted']};")
        reserve_row.addWidget(reserve_unit)
        reserve_row.addStretch()
        card.card_layout.addLayout(reserve_row)

        save_row = QHBoxLayout()
        save_row.addStretch()
        save_btn = primary_button('Save settings', parent = self)
        save_btn.clicked.connect(self._on_save)
        save_row.addWidget(save_btn)
        card.card_layout.addLayout(save_row)
        return card

    def _build_loot_filter_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Matchmaking & Attack Settings'))
        filter_hint = QLabel('Automatically reads available raid loot during Home Village matchmaking and clicks "Next" until a target meeting your criteria is found. Set amounts to 0 to attack without skipping.')
        filter_hint.setWordWrap(True)
        filter_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(filter_hint)

        grid = QGridLayout()
        grid.setSpacing(SPACING['sm'])

        # Loot Match Condition
        grid.addWidget(QLabel('Match Priority:'), 0, 0)
        self._loot_match_combo = QComboBox()
        self._loot_match_combo.addItem('Match Any (Gold OR Elixir OR DE)', 'any')
        self._loot_match_combo.addItem('Match All (Gold AND Elixir AND DE)', 'all')
        grid.addWidget(self._loot_match_combo, 0, 1)

        # Min Gold
        grid.addWidget(QLabel('Minimum Gold:'), 1, 0)
        self._min_gold_spin = QSpinBox()
        self._min_gold_spin.setRange(0, MIN_GOLD_K_MAX)
        self._min_gold_spin.setSingleStep(50)
        self._min_gold_spin.setSuffix('k')
        self._min_gold_spin.setFixedWidth(100)
        grid.addWidget(self._min_gold_spin, 1, 1)

        # Min Elixir
        grid.addWidget(QLabel('Minimum Elixir:'), 2, 0)
        self._min_elixir_spin = QSpinBox()
        self._min_elixir_spin.setRange(0, MIN_ELIXIR_K_MAX)
        self._min_elixir_spin.setSingleStep(50)
        self._min_elixir_spin.setSuffix('k')
        self._min_elixir_spin.setFixedWidth(100)
        grid.addWidget(self._min_elixir_spin, 2, 1)

        # Min Dark Elixir with Toggle
        grid.addWidget(QLabel('Minimum Dark Elixir:'), 3, 0)
        de_layout = QHBoxLayout()
        self._de_toggle = ToggleSwitch('')
        self._min_dark_elixir_spin = QSpinBox()
        self._min_dark_elixir_spin.setRange(0, MIN_DARK_ELIXIR_MAX)
        self._min_dark_elixir_spin.setSingleStep(500)
        self._min_dark_elixir_spin.setFixedWidth(100)
        self._de_toggle.toggled.connect(lambda checked: self._min_dark_elixir_spin.setEnabled(checked))
        de_layout.addWidget(self._de_toggle)
        de_layout.addWidget(self._min_dark_elixir_spin)
        de_layout.addStretch()
        grid.addLayout(de_layout, 3, 1)

        # Max Next Skips
        grid.addWidget(QLabel('Max Next Skips:'), 4, 0)
        self._max_skips_spin = QSpinBox()
        self._max_skips_spin.setRange(1, MAX_NEXT_SKIPS_MAX)
        self._max_skips_spin.setSingleStep(5)
        self._max_skips_spin.setFixedWidth(100)
        grid.addWidget(self._max_skips_spin, 4, 1)

        # Battle End Delay (Post-1-Star Delay)
        grid.addWidget(QLabel('Post-1-Star Loot Delay:'), 5, 0)
        self._battle_delay_spin = QSpinBox()
        self._battle_delay_spin.setRange(0, BATTLE_END_DELAY_MAX)
        self._battle_delay_spin.setSingleStep(5)
        self._battle_delay_spin.setSuffix('s')
        self._battle_delay_spin.setFixedWidth(100)
        grid.addWidget(self._battle_delay_spin, 5, 1)

        card.card_layout.addLayout(grid)

        delay_hint = QLabel('Post-1-Star Loot Delay: Once 1 Star is scored (End Battle appears), wait this many extra seconds for troops to clean up additional loot before clicking End Battle. Set to 0 to exit instantly upon 1 Star.')
        delay_hint.setWordWrap(True)
        delay_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(delay_hint)

        return card

    def _build_window_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Game window'))
        hint = QLabel('RaidR auto-detects the Clash of Clans window by default. If it attaches to the wrong window, select the game window below and click "Use selected".')
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(hint)
        self._window_status = QLabel('Using auto-detect.')
        self._window_status.setWordWrap(True)
        self._window_status.setStyleSheet(f"color: {TOKENS['primary']};")
        card.card_layout.addWidget(self._window_status)
        self._window_list = QListWidget()
        self._window_list.setObjectName('WindowList')
        self._window_list.itemSelectionChanged.connect(self._update_window_buttons)
        card.card_layout.addWidget(self._window_list)
        btn_row = QHBoxLayout()
        self._btn_refresh = neutral_button('Refresh', parent = card)
        self._btn_refresh.clicked.connect(self._refresh_windows)
        btn_row.addWidget(self._btn_refresh)
        self._btn_test = neutral_button('Test', parent = card)
        self._btn_test.clicked.connect(self._on_test_window)
        btn_row.addWidget(self._btn_test)
        self._btn_info = neutral_button('Info', parent = card)
        self._btn_info.clicked.connect(self._on_window_info)
        btn_row.addWidget(self._btn_info)
        self._btn_use = primary_button('Use selected', parent = card)
        self._btn_use.clicked.connect(self._on_use_window)
        btn_row.addWidget(self._btn_use)
        self._btn_auto = neutral_button('Auto-detect', parent = card)
        self._btn_auto.clicked.connect(self._on_auto_detect)
        btn_row.addWidget(self._btn_auto)
        btn_row.addStretch()
        card.card_layout.addLayout(btn_row)
        disp_title = SectionTitle('Display aspect')
        card.card_layout.addWidget(disp_title)
        disp_hint = QLabel('Ultrawide/21:9 monitors: switch your display to 16:9 so Google Play Games renders in 16:9, fully close and reopen Clash, then restore your display.')
        disp_hint.setWordWrap(True)
        disp_hint.setStyleSheet(f"color: {TOKENS['text_muted']};")
        card.card_layout.addWidget(disp_hint)
        disp_row = QHBoxLayout()
        self._btn_switch_169 = neutral_button('Switch display to 16:9', parent = card)
        self._btn_switch_169.clicked.connect(self._on_switch_display_169)
        disp_row.addWidget(self._btn_switch_169)
        self._btn_restore_disp = neutral_button('Restore my display', parent = card)
        self._btn_restore_disp.clicked.connect(self._on_restore_display)
        disp_row.addWidget(self._btn_restore_disp)
        disp_row.addStretch()
        card.card_layout.addLayout(disp_row)
        return card

    def _build_players_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Multi-Run Player Rotation'))
        hint = QLabel('Add account usernames to automatically rotate through during Multi-Run farming. Order is rotation order (▲▼). Run = farm this account; Skip = ignore.')
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TOKENS['text_muted']}; font-size: 11px;")
        card.card_layout.addWidget(hint)

        self._player_rows = []
        self._player_list_host = QWidget()
        self._player_list_layout = QVBoxLayout(self._player_list_host)
        self._player_list_layout.setContentsMargins(0, 0, 0, 0)
        self._player_list_layout.setSpacing(SPACING['sm'])
        self._player_list_layout.addStretch()
        card.card_layout.addWidget(self._player_list_host)

        btn_row = QHBoxLayout()
        add_btn = neutral_button('+ Add Player', parent=card)
        add_btn.clicked.connect(lambda: self._add_player_row(PlayerEntry(name='', enabled=True)))
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        card.card_layout.addLayout(btn_row)

        self._reload_players()
        return card

    def _reload_players(self):
        while self._player_rows:
            row = self._player_rows.pop()
            self._player_list_layout.removeWidget(row)
            row.deleteLater()
        stretch_idx = self._player_list_layout.count() - 1
        for entry in load_players():
            self._insert_player_row(entry, stretch_idx)
            stretch_idx += 1

    def _insert_player_row(self, entry, before_stretch):
        row_holder = [None]
        def move_up():
            if row_holder[0] is not None:
                self._move_player_row(row_holder[0], -1)
        def move_down():
            if row_holder[0] is not None:
                self._move_player_row(row_holder[0], 1)
        def remove():
            if row_holder[0] is not None:
                self._remove_player_row(row_holder[0])

        from app.ui.qt.pages.players import _PlayerRow
        row = _PlayerRow(entry, on_change=self._save_players, on_move_up=move_up, on_move_down=move_down, on_remove=remove)
        row_holder[0] = row
        self._player_rows.append(row)
        self._player_list_layout.insertWidget(before_stretch, row)

    def _add_player_row(self, entry):
        stretch_idx = max(0, self._player_list_layout.count() - 1)
        self._insert_player_row(entry, stretch_idx)
        self._save_players()

    def _move_player_row(self, row, delta):
        if row not in self._player_rows:
            return
        idx = self._player_rows.index(row)
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self._player_rows):
            return
        self._player_rows[idx], self._player_rows[new_idx] = self._player_rows[new_idx], self._player_rows[idx]
        self._player_list_layout.removeWidget(row)
        self._player_list_layout.insertWidget(new_idx, row)
        self._save_players()

    def _remove_player_row(self, row):
        if row in self._player_rows:
            self._player_rows.remove(row)
        self._player_list_layout.removeWidget(row)
        row.deleteLater()
        self._save_players()

    def _save_players(self):
        players = []
        for row in self._player_rows:
            entry = row.to_entry()
            if entry is not None:
                players.append(entry)
        save_players(players)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, '_player_rows'):
            self._reload_players()
        super().showEvent(event)
        self._reload_earthquake()
        self._refresh_windows()

    def _reload_earthquake(self):
        settings = load_profile_settings()
        idx = self._earthquake.findText(settings.earthquake_method)
        if idx >= 0:
            self._earthquake.setCurrentIndex(idx)
        self._wall_threshold.setValue(settings.wall_upgrade_threshold_m)
        self._reserve_builders.setValue(settings.reserve_builders)
        self._upgrade_order.setCurrentIndex(1 if settings.upgrade_order == 'cheapest' else 0)
        self._min_gold_spin.setValue(settings.min_gold_k)
        self._min_elixir_spin.setValue(settings.min_elixir_k)
        self._min_dark_elixir_spin.setValue(settings.min_dark_elixir)
        de_active = getattr(settings, 'filter_dark_elixir', False) or settings.min_dark_elixir > 0
        self._de_toggle.setChecked(de_active)
        self._min_dark_elixir_spin.setEnabled(de_active)
        self._max_skips_spin.setValue(settings.max_next_skips)
        self._battle_delay_spin.setValue(settings.battle_end_delay_s)
        self._loot_match_combo.setCurrentIndex(1 if getattr(settings, 'loot_match_condition', 'any') == 'all' else 0)

    def _on_save(self):
        save_profile_settings(ProfileSettings(
            earthquake_method = self._earthquake.currentText(),
            wall_upgrade_threshold_m = self._wall_threshold.value(),
            reserve_builders = self._reserve_builders.value(),
            upgrade_order = 'cheapest' if self._upgrade_order.currentIndex() == 1 else 'priciest',
            min_gold_k = self._min_gold_spin.value(),
            min_elixir_k = self._min_elixir_spin.value(),
            min_dark_elixir = self._min_dark_elixir_spin.value() if self._de_toggle.isChecked() else 0,
            filter_dark_elixir = self._de_toggle.isChecked(),
            max_next_skips = self._max_skips_spin.value(),
            battle_end_delay_s = self._battle_delay_spin.value(),
            loot_match_condition = 'all' if self._loot_match_combo.currentIndex() == 1 else 'any' 
        ))
        self._flash_status_bar('Saved')

    def _selected_candidate(self):
        row = self._window_list.currentRow()
        if 0 <= row < len(self._candidates):
            return self._candidates[row]
        return None

    def _update_window_buttons(self):
        cand = self._selected_candidate()
        has_sel = cand is not None
        self._btn_test.setEnabled(has_sel)
        self._btn_use.setEnabled(has_sel)
        self._btn_info.setEnabled(has_sel)

    def _refresh_windows(self):
        try:
            self._candidates = WindowService().enumerate_windows()
            saved = load_window_selection()
            self._window_list.clear()
            selected_row = -1
            for i, cand in enumerate(self._candidates):
                item = QListWidgetItem(cand.display_label())
                if not cand.is_game:
                    item.setForeground(self._muted_brush())
                self._window_list.addItem(item)
                if not saved.is_set():
                    continue
                if not cand.title.strip().lower() == saved.title.strip().lower():
                    continue
                if not saved.top_class and cand.top_class == saved.top_class:
                    continue
                selected_row = i
            if selected_row >= 0:
                self._window_list.setCurrentRow(selected_row)
            if not self._candidates:
                self._window_status.setText('No visible windows found. Open the game, then Refresh.')
            elif saved.is_set():
                self._window_status.setText(f"Pinned window: {saved.title or '(saved)'}")
            else:
                self._window_status.setText('Using auto-detect.')
            self._update_window_buttons()
        except Exception as exc:
            logger.warning(f'Could not enumerate windows: {exc}')
            self._candidates = []

    def _muted_brush(self):
        return QColor(TOKENS['text_muted'])

    @staticmethod
    def _aspect_label(w, h):
        if not w or not h:
            return 'size unavailable'
        aspect = resolve_aspect_key(w, h)
        if aspect is None:
            return f'{w}x{h} (not ~16:9/16:10)'
        pretty = '16:9' if aspect == '16_9' else '16:10'
        return f'{w}x{h} ({pretty})'

    def _on_test_window(self):
        cand = self._selected_candidate()
        if cand is None:
            return None
        if not cand.is_game:
            self._window_status.setText('No Google Play Games surface (CROSVM) under this window - pick the game window.')
            return None
        ws = WindowService()
        surface_size = ws.window_pixel_size(cand.child_hwnd)
        if surface_size is None:
            self._window_status.setText('Could not read the window size. Is the game minimized?')
            return None
        sub_size = None
        try:
            for d in ws.enumerate_descendants(cand.top_hwnd):
                if not d.cls.lower() == 'subwin':
                    continue
                sub_size = (d.width, d.height)
            (sw, sh) = surface_size
            lines = [f'Capture target {cand.child_class}: {self._aspect_label(sw, sh)}']
            if not sub_size is None:
                lines.append(f'Inner subWin: {self._aspect_label(*sub_size)}')
            if resolve_aspect_key(sw, sh) is None:
                lines.append('Surface aspect unsupported - try resizing the game window.')
            else:
                lines.append('Surface OK to use.')
            self._window_status.setText('\n'.join(lines))
        except Exception as exc:
            logger.warning(f'Could not inspect subWin: {exc}')

    def _on_switch_display_169(self):
        (ok, size, reason) = self._display.switch_to_16_9()
        if ok and reason == 'already_16_9':
            self._window_status.setText('Your display is already 16:9 - just (re)launch Clash in Google Play Games and it will render 16:9.')
        elif ok:
            self._window_status.setText(f'Display set to {size[0]}x{size[1]} (16:9). Now FULLY close and reopen Clash in Google Play Games, then click "Restore my display".')
        elif reason == 'no_16_9_mode':
            self._window_status.setText('Your display driver offers no 16:9 mode - use a 16:9 monitor for the game instead.')
        else:
            self._window_status.setText('Could not switch the display resolution.')
        self._flash_status_bar('Display set to 16:9' if ok else 'Display switch failed')

    def _on_restore_display(self):
        (ok, size, reason) = self._display.restore()
        if ok:
            self._window_status.setText(f'Display restored to {size[0]}x{size[1]}. If you relaunched Clash while in 16:9 it stays 16:9 - press Test to confirm, then Start.')
        elif reason == 'nothing_to_restore':
            self._window_status.setText('Nothing to restore - you have not switched your display (or it was already restored).')
        else:
            self._window_status.setText('Could not restore the display. Use Windows Settings -> Display to set it back.')
        self._flash_status_bar('Display restored' if ok else 'Restore failed')

    def _on_window_info(self):
        cand = self._selected_candidate()
        if cand is None:
            return None
        try:
            descendants = WindowService().enumerate_descendants(cand.top_hwnd)
            WindowInfoDialog(self.window(), cand, descendants).exec()
        except Exception as exc:
            logger.warning(f'Could not enumerate descendants: {exc}')

    def _on_use_window(self):
        cand = self._selected_candidate()
        if cand is None:
            return None
        save_window_selection(cand.to_selection())
        self._window_status.setText(f"Pinned: {cand.title or '(no title)'}. Press Test to verify.")
        self._flash_status_bar('Window saved')

    def _on_auto_detect(self):
        clear_window_selection()
        self._window_status.setText('Cleared - using auto-detect.')
        self._flash_status_bar('Auto-detect')
        self._refresh_windows()

    def _flash_status_bar(self, msg):
        win = self.window()
        if isinstance(win, QMainWindow) and win.statusBar() is not None:
            win.statusBar().showMessage(msg, 1500)

    def _build_updates_card(self):
        card = Card()
        card.card_layout.addWidget(SectionTitle('Software Updates'))
        
        row = QHBoxLayout()
        row.setSpacing(SPACING['md'])

        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        lbl_cur = QLabel(f"Installed Version: v{__version__}")
        lbl_cur.setStyleSheet(f"color: {TOKENS['text']}; font-weight: 700; font-size: 13px;")
        self._update_status_lbl = QLabel("Up to date")
        self._update_status_lbl.setStyleSheet(f"color: {TOKENS['text_muted']}; font-size: 12px;")
        vbox.addWidget(lbl_cur)
        vbox.addWidget(self._update_status_lbl)
        row.addLayout(vbox, stretch=1)

        self._pending_update_info: Optional[UpdateInfo] = None

        self._btn_check_updates = chip_button('Check for Updates', parent=self)
        self._btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_check_updates.clicked.connect(self._manual_check_updates)
        row.addWidget(self._btn_check_updates)

        self._btn_install_update = primary_button('Install Update', parent=self)
        self._btn_install_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_install_update.setVisible(False)
        self._btn_install_update.clicked.connect(self._open_update_dialog)
        row.addWidget(self._btn_install_update)

        card.card_layout.addLayout(row)
        return card

    def _manual_check_updates(self):
        self._btn_check_updates.setEnabled(False)
        self._update_status_lbl.setText('Checking GitHub releases...')
        self._update_status_lbl.setStyleSheet(f"color: {TOKENS['text_muted']}; font-size: 12px;")

        self._manual_checker = UpdateCheckerThread(current_version=__version__, parent=self)
        self._manual_checker.updateAvailable.connect(self._on_manual_update_found)
        self._manual_checker.upToDate.connect(self._on_manual_up_to_date)
        self._manual_checker.checkFailed.connect(self._on_manual_check_failed)
        self._manual_checker.start()

    def _on_manual_update_found(self, info: UpdateInfo):
        self._btn_check_updates.setEnabled(True)
        self.notify_update_available(info)
        self._open_update_dialog()

    def _on_manual_up_to_date(self, current_ver: str):
        self._btn_check_updates.setEnabled(True)
        self.notify_up_to_date(current_ver)
        self._flash_status_bar('RaidR is already up to date')

    def _on_manual_check_failed(self, err_msg: str):
        self._btn_check_updates.setEnabled(True)
        self._update_status_lbl.setText(f'Check failed: {err_msg[:30]}')
        self._update_status_lbl.setStyleSheet(f"color: {TOKENS['danger']}; font-size: 12px;")

    def notify_update_available(self, info: UpdateInfo):
        self._pending_update_info = info
        self._update_status_lbl.setText(f"Update available: RaidR v{info.version} ✨")
        self._update_status_lbl.setStyleSheet(f"color: {TOKENS['primary']}; font-size: 12px; font-weight: bold;")
        self._btn_install_update.setVisible(True)

    def notify_up_to_date(self, current_ver: str):
        self._update_status_lbl.setText("You are running the latest version.")
        self._update_status_lbl.setStyleSheet(f"color: {TOKENS['text_muted']}; font-size: 12px;")
        self._btn_install_update.setVisible(False)

    def _open_update_dialog(self):
        if not self._pending_update_info:
            return
        dlg = UpdateDialog(self._pending_update_info, parent=self.window())
        dlg.exec()
