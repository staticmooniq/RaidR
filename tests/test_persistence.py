import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.utils.player_list_store import PlayerEntry, load_players, save_players
from app.utils.profile_settings_store import (
    EARTHQUAKE_METHOD_RANDOM, LOOT_MATCH_ALL, UPGRADE_ORDER_CHEAPEST,
    ProfileSettings, load_profile_settings, save_profile_settings,
)
from app.utils.window_settings_store import (
    WindowSelection, load_window_selection, save_window_selection,
)


class PersistenceStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._app_dir = Path(self._tmp.name)
        self._patches = [
            patch('app.utils.player_list_store.get_user_app_data_dir', return_value=self._app_dir),
            patch('app.utils.profile_settings_store.get_user_app_data_dir', return_value=self._app_dir),
            patch('app.utils.window_settings_store.get_user_app_data_dir', return_value=self._app_dir),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def test_player_list_round_trip_and_corrupt_recovery(self):
        entries = [
            PlayerEntry(name='MainAccount', enabled=True),
            PlayerEntry(name='  AltBase  ', enabled=False),
            PlayerEntry(name='   ', enabled=True),
        ]
        save_players(entries)
        loaded = load_players()
        self.assertEqual(loaded, [
            PlayerEntry(name='MainAccount', enabled=True),
            PlayerEntry(name='AltBase', enabled=False),
        ])

        (self._app_dir / 'player_list.json').write_text('{bad json', encoding='utf-8')
        self.assertEqual(load_players(), [])

    def test_profile_settings_round_trip(self):
        cfg = ProfileSettings(
            earthquake_method=EARTHQUAKE_METHOD_RANDOM,
            wall_upgrade_threshold_m=7,
            reserve_builders=2,
            upgrade_order=UPGRADE_ORDER_CHEAPEST,
            min_gold_k=650,
            min_elixir_k=500,
            min_dark_elixir=4500,
            max_next_skips=35,
            battle_end_delay_s=12,
            loot_match_condition=LOOT_MATCH_ALL,
            filter_dark_elixir=False,
        )
        save_profile_settings(cfg)
        loaded = load_profile_settings()
        self.assertEqual(loaded, cfg)

    def test_window_selection_round_trip_and_corrupt_recovery(self):
        sel = WindowSelection(title='Clash of Clans', top_class='TopCls', child_class='CROSVM')
        save_window_selection(sel)
        self.assertEqual(load_window_selection(), sel)

        (self._app_dir / 'window.json').write_text('{bad json', encoding='utf-8')
        self.assertEqual(load_window_selection(), WindowSelection())


class UIPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._qapp = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._app_dir = Path(self._tmp.name)
        self._qsettings_scope = f'RaidR_UnitTest_{os.getpid()}'
        self._real_qsettings = QSettings

        def test_qsettings(*args, **kwargs):
            if len(args) >= 2 and args[0] == 'RaidR':
                return self._real_qsettings(self._qsettings_scope, args[1])
            return self._real_qsettings(*args, **kwargs)

        self._patches = [
            patch('app.utils.player_list_store.get_user_app_data_dir', return_value=self._app_dir),
            patch('app.utils.profile_settings_store.get_user_app_data_dir', return_value=self._app_dir),
            patch('app.utils.window_settings_store.get_user_app_data_dir', return_value=self._app_dir),
            patch('app.utils.custom_strategy_store.get_user_app_data_dir', return_value=self._app_dir),
            patch('app.ui.qt.pages.settings.QSettings', side_effect=test_qsettings),
            patch('app.ui.qt.pages.run.QSettings', side_effect=test_qsettings),
            patch('app.ui.qt.pages.settings.WindowService.enumerate_windows', return_value=[]),
        ]
        for p in self._patches:
            p.start()

        s = self._real_qsettings(self._qsettings_scope, 'UI')
        s.clear()
        s.sync()

    def tearDown(self):
        s = self._real_qsettings(self._qsettings_scope, 'UI')
        s.clear()
        s.sync()
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def test_settings_page_autosaves_players_and_values_across_relaunch(self):
        from app.ui.qt.pages.settings import SettingsPage

        page1 = SettingsPage()
        page1._add_player_row(PlayerEntry(name='', enabled=True))
        page1._player_rows[0]._name.setText('AccountOne')
        page1._player_rows[0]._name.textEdited.emit('AccountOne')
        page1._add_player_row(PlayerEntry(name='', enabled=True))
        page1._player_rows[1]._name.setText('AccountTwo')
        page1._player_rows[1]._name.textEdited.emit('AccountTwo')
        page1._player_rows[1]._toggle_mode()

        # Modify profile settings without clicking any Save button
        page1._wall_threshold.setValue(6)
        page1._reserve_builders.setValue(2)
        page1._upgrade_order.setCurrentIndex(1)
        page1._loot_match_combo.setCurrentIndex(1)
        page1._min_gold_spin.setValue(450)
        page1._min_elixir_spin.setValue(350)
        page1._de_toggle.setChecked(True)
        page1._min_dark_elixir_spin.setValue(3000)
        page1._max_skips_spin.setValue(25)
        page1._battle_delay_spin.setValue(10)

        # Simulate relaunch with a brand new SettingsPage
        page2 = SettingsPage()
        self.assertEqual([r.to_entry() for r in page2._player_rows], [
            PlayerEntry(name='AccountOne', enabled=True),
            PlayerEntry(name='AccountTwo', enabled=False),
        ])
        self.assertEqual(page2._wall_threshold.value(), 6)
        self.assertEqual(page2._reserve_builders.value(), 2)
        self.assertEqual(page2._upgrade_order.currentIndex(), 1)
        self.assertEqual(page2._loot_match_combo.currentIndex(), 1)
        self.assertEqual(page2._min_gold_spin.value(), 450)
        self.assertEqual(page2._min_elixir_spin.value(), 350)
        self.assertTrue(page2._de_toggle.isChecked())
        self.assertEqual(page2._min_dark_elixir_spin.value(), 3000)
        self.assertEqual(page2._max_skips_spin.value(), 25)
        self.assertEqual(page2._battle_delay_spin.value(), 10)

    def test_players_page_move_row_preserves_order(self):
        from app.ui.qt.pages.players import PlayersPage

        save_players([PlayerEntry('First', True), PlayerEntry('Second', True)])
        page = PlayersPage()
        page._reload()
        page._move_row(page._rows[0], 1)
        self.assertEqual([p.name for p in load_players()], ['Second', 'First'])

    def test_run_page_autosaves_choices_across_relaunch(self):
        from app.ui.qt.pages.run import RunPage
        from unittest.mock import MagicMock

        ctrl = MagicMock()
        page1 = RunPage(ctrl, lambda _p: None)
        page1._minutes_spin.setValue(45)
        page1._upgrade_walls.setChecked(True)
        page1._hv_wall_slider_row.setValue(8)
        page1._multi_run.setChecked(True)
        page1._three_star_toggle.setChecked(False)
        page1._rage_spell_toggle.setChecked(True)
        page1._auto_upgrade_group.button(2).click()

        page2 = RunPage(ctrl, lambda _p: None)
        self.assertEqual(page2._minutes_spin.value(), 45)
        self.assertTrue(page2._upgrade_walls.isChecked())
        self.assertEqual(page2._hv_wall_slider_row.value(), 8)
        self.assertTrue(page2._multi_run.isChecked())
        self.assertFalse(page2._three_star_toggle.isChecked())
        self.assertTrue(page2._rage_spell_toggle.isChecked())
        self.assertEqual(page2._get_auto_upgrade_mode(), 'maxer')


if __name__ == '__main__':
    unittest.main()
