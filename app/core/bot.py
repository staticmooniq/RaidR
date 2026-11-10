import collections
import time
from app.core.battle_rewards import BattleRewards
import cv2
import numpy as np
import random
import threading
from typing import Callable, List, Optional, Tuple
from app.config import ASPECT_16_10, ASPECT_16_9, Config
from app.core.strategies import AttackStrategy, EdragStrategy, TroopSpamStrategy, _EDRAG_DELAY
from app.core.upgrader import AUTO_UPGRADE_MODES, LIVE_UPGRADE_MODES, MODE_OFF, UpgradeAdvisor
from app.core.village_state import read_hud_triplet_stable, read_village_state, read_village_state_stable
from app.services.input import InputService
from app.services.loot_ocr import LootOCR
from app.services.vision import BOTTOM_HALF_BOT_TEMPLATES, TOP_HALF_BOT_TEMPLATES, VisionService
from app.services.window import WindowService
from app.utils.common import get_template_path
from app.utils.logger import setup_logger
from app.utils.player_list_store import PlayerEntry
from app.utils.profile_settings_store import EARTHQUAKE_METHOD_CURVE
logger = setup_logger('BotCore')
_HOME_VILLAGE_BUILDER_TEMPLATES = ('builder.png', 'gbuilder.png')
_WALL_OCR_RETRY_DRAG_BASELINE: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    ASPECT_16_9: ((1300, 280), (1300, 830)),
    ASPECT_16_10: ((1300, 280), (1300, 980)) }
_BB_BABY_DRAGON_RECLICK_WAIT = 10
_BB_RETURN_HOME_TEMPLATE = 'breturnhome.png'
_BB_RETURN_HOME_TEMPLATE_1080P = 'breturnhome1920.png'
_BB_1080P_CAPTURE_SIZE = (1920, 1080)
_BB_1080P_SIZE_TOLERANCE = 40
_BB_TEMPLATE_SUPPRESS_PAD = 0.1
_BB_COPTER_ABILITY_INTERVAL = 20
_BB_HUMAN_CAMERA = True          # random zoom-in / look around / zoom-out before deploying in Builder Base
_BB_CAMERA_LOOKS = (1, 2, 2, 3)  # how many off-centre "looks" to do (picked at random)
_BB_CAMERA_ZOOM_IN = (2, 5)      # wheel notches per look
_BB_CAMERA_OUT_MARGIN = 3        # extra zoom-out notches so the view always ends fully zoomed out
_BB_ELIXIR_CART_COLLECT_EVERY = 10
_BB_FULL_ELIXIR_CART_TEMPLATES = ('fullecart.png', 'fullecart2.png', 'fullecart3.png')
_BB_COLLECT_TEMPLATE = 'collect.png'
_BB_STAR_BONUS_TEMPLATE = 'bstar.png'
_BB_BATTLE_STAR_TEMPLATE = 'bbstar.png'
_BB_BATTLE_MACHINE_TEMPLATE = 'battlemachine.png'
_BB_FLYING_MACHINE_TEMPLATE = 'flyingmachine.png'
_BB_GOLD_PRIORITISE_MIN_STARS = 3
_BB_TWO_STAR_THRESHOLD = 2        # Extras -> "2 Star": end the battle at this many stars
_BB_SEARCH_CLOUD_TEMPLATES = ('clouds.png', 'bbsearching.png')
_BB_CLOUD_CLEAR_SECONDS = 2.0     # "searching for opponents" clouds must be gone this long before deploying
_ANTI_INACTIVITY_ZOOM_INTERVAL_SECONDS = 120.0  # strictly zoom in/out every 2 minutes
_BB_WALL_SCAN_INTERVAL_SECONDS = 45
_BB_WALL_FAILED_RETRY_SECONDS = 15
_BB_WALL_ADD_TEMPLATE = 'bbwalladd.png'          # enabled "Add Wall" (+1) button in the wall bar
_BB_WALL_REMOVE_TEMPLATE = 'bbwallremove.png'    # "Remove Wall" button in the wall bar
_BB_WALL_GOLD_TEMPLATE = 'bbwallgold.png'        # Builder Gold coin inside the gold Upgrade button
_BB_WALL_ELIXIR_TEMPLATE = 'bbwallelixir.png'    # Builder Elixir drop inside the elixir Upgrade button
_BB_WALL_ADD_CLICK_SECONDS = 0.7                 # settle after each Add Wall tap (cost text redraws)
_BB_WALL_REMOVE_CLICK_SECONDS = 0.45             # settle after the single Remove Wall tap
_BB_WALL_UPGRADE_CLICK_SECONDS = 0.35            # settle before the Upgrade Walls dialog appears
_BB_WALL_PRICE_READ_SETTLE_SECONDS = 0.35        # between two price reads of the same bar
_BB_WALL_OKAY_TIMEOUT_SECONDS = 6.0              # Upgrade Walls dialog -> Okay
_WALL_PRICE_RED_SHARE = 0.2                       # red share of a price box that means "cannot pay"
_BB_WALL_PANEL_SCROLL_STEPS = 16
_BB_WALL_PANEL_WHEEL_CLICKS = 1
_BB_WALL_BATCH_MAX_ADDS = 24  # Add Wall taps per pass before giving up on both-red (a long stretch of cheap walls)
_BB_WALL_ANCHOR_THRESHOLD = 0.62  # live window renders the bar icons at 0.72-0.78; 0.75 missed them
_BB_WALL_REMOVE_OFFSET_FRAC = 0.162  # Add Wall (lime +1) x minus this = Remove Wall x (same bar row)
_BB_RETURN_HOME_END_BATTLE_RETRIES = 5
# False = hands-off in the HOME VILLAGE ONLY: the bot never taps End Battle / Surrender there.
# It deploys, then waits for that battle to finish (timer, 100%, or you ending it by hand) before
# returning home. Builder Base is untouched. This also fully skips the 1-star post-battle delay
# below, since there's nothing left for it to time -- the bot isn't the one ending the battle.
_AUTO_END_BATTLE = False
_MANUAL_BATTLE_WAIT_SECONDS = 420
_STAR_BONUS_THRESHOLD = 0.75
_TROOP_FAILURE_LIMIT = 4
_TROOP_RETRY_WAIT_SECONDS = 15  # training is instant since the Mar 2025 "Clash Anytime" update — this only lets the UI settle
_RELOAD_GRACE_SECONDS = 180  # let a quick phone check finish before reconnecting over it
_WALL_BATCH_MAX_ADDS = 15
_WALL_MENU_SCROLL_STEPS = 8  # OCR positions polled: as-opened + 7 wheel nudges down the list
_WALL_MENU_WHEEL_CLICKS = 2  # ~3-4 rows per nudge; the OCR band spans the whole popup so a nudge cannot jump the Wall row past it
_WALL_ROW_STABLE_TOL = 30  # ref px: max y drift between consecutive frames before the row is trusted for a click
_AUTO_UPGRADE_SCAN_INTERVAL_SECONDS = 600  # full popup scan is OCR-heavy (~15-25s); keep it rare vs the ~35s attack cycle
_IDLE_RECHECK_SECONDS = 300  # while idling (storages full, nothing startable): wake, recover the screen, re-read state
# Loot-tracker plausibility caps per snapshot interval (one battle): a raid tops out
# well under these even with boosts — anything larger is an OCR misread that slipped
# past the ≥0 filter (live repro: "+15.5M elixir" in one battle).
_LOOT_DELTA_MAX_MAIN = 3000000
_LOOT_DELTA_MAX_DARK = 50000
_WALL_MENU_SCROLL_BASELINE: dict[str, tuple[int, int]] = {
    ASPECT_16_9: (1305, 605),
    ASPECT_16_10: (1305, 672) }

class Bot:
    '''Main Bot Logic.'''
    
    def __init__(self):
        self.config = Config()
        self.window = WindowService()
        self.stop_event = threading.Event()
        self.input = InputService(self.window, self.stop_event)
        self.vision = VisionService()
        self._battle_rewards = BattleRewards(self.window, self.input, self.stop_event)
        self.loot_ocr = LootOCR()
        self.running = False
        self._earthquake_method = EARTHQUAKE_METHOD_CURVE
        self._loot_totals = (0, 0, 0)
        self._loot_prev_resources = None
        self._loot_session_start_mono = 0
        self._loot_callback = None
        self._suppress_loot_negative_error_once = False

    
    def start(self, method, run_time_minutes, star_bonus = False, status_callback = None, loot_callback = None, multi_run_players = None, ranked_fill = False, upgrade_walls = False, earthquake_method = EARTHQUAKE_METHOD_CURVE, builder_base = False, loot_prioritise = 'both', wall_upgrade_threshold = 0, auto_upgrade = MODE_OFF, reserve_builders = 1, state_callback = None, upgrade_order = None, min_gold = 0, min_elixir = 0, min_dark_elixir = 0, max_next_skips = 50, battle_end_delay = 20, loot_match_condition = 'any', secondary_troop_template = '', secondary_troop_count = 12, two_star_mode = False, custom_strategy_data = None):
        '''Starts the bot loop. With ``multi_run_players``, runs a full session per enabled player.
        ``run_time_minutes <= 0`` (single Home Village runs only) means UNLIMITED — farm,
        upgrade and idle until the user stops the bot ("run until maxed").'''
        self._status_callback = status_callback
        self._loot_callback = loot_callback
        self._state_callback = state_callback
        self._earthquake_method = earthquake_method
        self._custom_strategy_data = custom_strategy_data
        if not self.window.find_window():
            raise RuntimeError('Clash of Clans window not found. Please ensure the game is open.')
        self._reset_loot_session()
        self._emit_loot_update()
        self.running = True
        self.stop_event.clear()
        unlimited = not star_bonus and multi_run_players is None and not builder_base and int(run_time_minutes or 0) <= 0
        duration = 900 if star_bonus else (0 if unlimited else max(1, int(run_time_minutes)) * 60)
        mr = multi_run_players is not None
        self._builder_base = builder_base
        self._loot_prioritise = loot_prioritise
        self._bb_two_star_mode = bool(two_star_mode)
        self._wall_upgrade_threshold = max(0, int(wall_upgrade_threshold or 0))
        self._auto_upgrade_mode = auto_upgrade if auto_upgrade in AUTO_UPGRADE_MODES else MODE_OFF
        self._auto_upgrade_last_scan = 0
        # Pretend the last wall pass ran an interval ago so the very first pass always fires
        # (monotonic() is seconds-since-boot on Windows, so a fresh boot used to skip it).
        self._bb_wall_last_scan = time.monotonic() - _BB_WALL_SCAN_INTERVAL_SECONDS
        self._reserve_builders = max(0, int(reserve_builders or 0))
        self._upgrade_order = upgrade_order
        self._advisor = None  # one UpgradeAdvisor per session (it holds execution cooldowns)
        self._min_gold = max(0, int(min_gold or 0))
        self._min_elixir = max(0, int(min_elixir or 0))
        self._min_dark_elixir = max(0, int(min_dark_elixir or 0))
        self._max_next_skips = max(1, int(max_next_skips or 50))
        self._battle_end_delay = max(0, int(battle_end_delay if battle_end_delay is not None else 20))
        self._loot_match_condition = str(loot_match_condition or 'any').strip().lower()
        self._secondary_troop_template = str(secondary_troop_template or '').strip()
        self._secondary_troop_count = max(1, min(100, int(secondary_troop_count or 12)))
        logger.info(f'''Bot started. Method: {method}, Time: {'unlimited' if unlimited else f'{run_time_minutes}m'}, StarBonus: {star_bonus}, MultiRun: {mr}, RankedFill: {ranked_fill}, UpgradeWalls: {upgrade_walls}, WallThreshold: {self._wall_upgrade_threshold}, AutoUpgrade: {self._auto_upgrade_mode}, ReserveBuilders: {self._reserve_builders}, MinGold: {self._min_gold:,}, MinElixir: {self._min_elixir:,}, MinDE: {self._min_dark_elixir:,}, MaxSkips: {self._max_next_skips}, MatchMode: {self._loot_match_condition}, Delay: {self._battle_end_delay}s, Earthquake: {earthquake_method}, BuilderBase: {builder_base}, LootPrioritise: {loot_prioritise}, BBTwoStarMode: {self._bb_two_star_mode}''')

        try:

            if not multi_run_players is None:
                self._ensure_correct_village(builder_base = False)
                queue = [ p for p in multi_run_players if p.enabled ]
                if not queue:
                    raise RuntimeError('Multi-run: no players marked Run')
                for player in queue:
                    self._check_stop()
                    self._switch_account_and_load_home(player.name)
                    self._check_stop()
                    self._run_loop(method, duration, star_bonus, ranked_fill, upgrade_walls)
                    self._check_stop()
                    self._multi_run_builder_base_after_session()
                    self._check_stop()
            elif self._builder_base:  # [recovered: decompiler nested this single-run block inside the multi-run `if`]
                self._ensure_correct_village(builder_base = True)
                self._run_builder_base_loop(duration, star_bonus = star_bonus, upgrade_walls = upgrade_walls)

            else:
                self._ensure_correct_village(builder_base = False)
                self._run_loop(method, duration, star_bonus, ranked_fill, upgrade_walls)
        except InterruptedError:
            logger.info('Bot stopped by user.')
        except Exception as e:
            logger.error(f'''Bot crashed: {e}''', exc_info = True)
            raise
        finally:
            self.running = False
            self._earthquake_method = EARTHQUAKE_METHOD_CURVE
            logger.info('Bot stopped.')

    
    def stop(self):
        '''Signals the bot to stop.'''
        self.running = False
        self.stop_event.set()

    
    def _reset_loot_session(self):
        '''Reset counters for a new :meth:`start` — no disk persistence.'''
        self._loot_totals = (0, 0, 0)
        self._loot_prev_resources = None
        self._loot_session_start_mono = time.monotonic()
        self._suppress_loot_negative_error_once = False
        self._last_hud_triplet = None
        self._gold_pinned = False
        self._elixir_pinned = False

    
    def _emit_loot_update(self):
        cb = self._loot_callback
        if not cb:
            return None
        (g, el, de) = self._loot_totals
        elapsed = max(0, time.monotonic() - float(self._loot_session_start_mono))
        cb(g, el, de, elapsed)

    
    def _loot_snapshot_before_attack(self):
        '''
On home: OCR top‑right HUD, diff vs previous snapshot, accumulate non‑negative deltas,
refresh the baseline.

Called before wall upgrades (when storages full) **and** immediately before tapping
Attack so post‑raid gains are recorded **before** wall spend can make the next snapshot
look like a decrease on every resource vs that baseline (which would skip the add).

When deltas vs the previous snapshot are not all non-negative, session totals are not
incremented unless ``_suppress_loot_negative_error_once`` suppresses one skip (set after
wall upgrades for the first pre-Attack snapshot that would otherwise count as an error).
'''
        # Consecutive-frame agreement: single HUD reads get corrupted by animations
        # (live repro: elixir "115M" — an upward misread passes the ≥0 filter and
        # poisons the session totals). No stable read this cycle → just skip.
        triplet = self._read_hud_triplet_stable()
        if triplet is None:
            logger.debug('Loot tracker: no stable HUD read this cycle')
            self._emit_loot_update()
            return None
        self._last_hud_triplet = triplet
        (cur_g, cur_el, cur_de) = triplet
        prev = self._loot_prev_resources
        # Cap detection without TH-specific numbers: at a TRUE cap, consecutive
        # stable pre-attack reads pin to the identical value (raids refill the
        # entry fee back to cap); below cap every battle moves the number. The
        # full-storage icons fire from ~85% up, so they alone must not idle the
        # bot away from real remaining headroom.
        if prev is not None:
            self._gold_pinned = cur_g == prev[0]
            self._elixir_pinned = cur_el == prev[1]
        skipped_due_to_negative_delta = False
        if not prev is None:
            (lg, le, ld) = prev
            dg = cur_g - lg
            d_el = cur_el - le
            d_de = cur_de - ld
            if dg >= 0 and d_el >= 0 and d_de >= 0:
                if dg <= _LOOT_DELTA_MAX_MAIN and d_el <= _LOOT_DELTA_MAX_MAIN and d_de <= _LOOT_DELTA_MAX_DARK:
                    (tg, te, td) = self._loot_totals
                    self._loot_totals = (tg + dg, te + d_el, td + d_de)
                    logger.info('Loot tracker: +%s / +%s / +%s (G/E/DE) → session %s / %s / %s', dg, d_el, d_de, self._loot_totals[0], self._loot_totals[1], self._loot_totals[2])
                else:
                    # One battle cannot earn this much — an OCR misread slipped through.
                    logger.warning('Loot tracker: implausible gain +%s/+%s/+%s discarded (OCR misread); baseline refreshed', dg, d_el, d_de)
            else:
                skipped_due_to_negative_delta = True
                logger.warning('Loot tracker: negative delta — previous gold/elixir/dark=%s/%s/%s current read=%s/%s/%s', lg, le, ld, cur_g, cur_el, cur_de)
        self._loot_prev_resources = triplet
        self._emit_loot_update()
        if skipped_due_to_negative_delta:
            if self._suppress_loot_negative_error_once:
                self._suppress_loot_negative_error_once = False
                return None
            return None
        self._suppress_loot_negative_error_once = False

    
    def reset_inactivity_timer(self):
        """Reset the inactivity keep-alive timer so the 2-minute countdown starts fresh."""
        self._last_anti_inactivity_zoom = time.monotonic()

    def maybe_anti_inactivity_zoom(self, force = False):
        """Strictly zoom in randomly and out every 2 minutes to prevent inactivity timeout.
        
        Paused during battles and troop deployment to prevent camera movements from interfering
        with troop placement or timing.
        """
        if not force:
            if getattr(self, '_in_battle', False) or getattr(self, '_is_deploying', False):
                return
        now = time.monotonic()
        if force or (now - getattr(self, '_last_anti_inactivity_zoom', 0) >= _ANTI_INACTIVITY_ZOOM_INTERVAL_SECONDS):
            try:
                self.input.anti_inactivity_zoom()
            except Exception:
                logger.warning('Anti-inactivity zoom failed', exc_info = True)
            self._last_anti_inactivity_zoom = time.monotonic()


    def _check_stop(self):
        self.maybe_anti_inactivity_zoom()
        if self.stop_event.is_set():
            raise InterruptedError('Bot stopped by user')

    
    def _update_config_size(self, frame):
        '''Reload aspect profile if screenshot size implies a different template folder.'''
        self.config.set_target_size_from_frame(frame)

    
    def _scroll_point(self):
        '''Scroll anchor in authoring space [1000,1000]; scaled to current capture.'''
        (x, y) = self.config.scale_point([
            1000,
            1000])
        return (x, y)

    
    def _nudge_view_to_reveal_attack(self):
        '''Click ``empty`` (``data.json``) and scroll at anchor to nudge village until Attack is findable.'''
        self.input.click(pause = 0.15, *self.config.get_point('empty'))
        self.input.scroll(*self._scroll_point(), 5)

    
    def _find_home_village_builder(self, frame, region):
        for name in _HOME_VILLAGE_BUILDER_TEMPLATES:
            (x, y) = self.vision.find_template(frame, name, region = region)
            if not x:
                continue
            return (x, y)
        return (None, None)

    
    def _wall_menu_drag_to_bottom(self):
        '''Drag the builder upgrade list to its bottom so ``Wall`` (list end) is revealed.

Touch-style swipe up: click low in the list, drag to the top, release — the reverse of
the old wheel scroll. Baseline coords are scaled via :meth:`Config.scale_point`. Dragging
past the bottom is a harmless no-op, so this can be called repeatedly.
'''
        pair = _WALL_OCR_RETRY_DRAG_BASELINE.get(self.config.aspect_key)
        if pair is None:
            logger.warning('wall menu drag: unknown aspect %r; skipping drag', self.config.aspect_key)
            return None
        (top_ref, bottom_ref) = pair
        top = self.config.scale_point([
            top_ref[0],
            top_ref[1]])
        bottom = self.config.scale_point([
            bottom_ref[0],
            bottom_ref[1]])
        (x_top, y_top) = (int(top[0]), int(top[1]))  # [recovered: pycdc reversed STORE_FAST_STORE_FAST pairs]
        (x_bot, y_bot) = (int(bottom[0]), int(bottom[1]))
        self.input.move(x_bot, y_bot)
        self.input.mouse_down(x_bot, y_bot)
        
        try:
            self.input.human_move(x_bot, y_bot, x_top, y_top, duration = 0.5)
            self.input.mouse_up(x_top, y_top)
            return None
        except:
            self.input.mouse_up(x_top, y_top)


    
    def _wall_menu_drag_retry_nudge(self):
        '''Vertical drag in the builder list when ``wall`` OCR misses (~0.5s eased move + hold pause).'''
        pair = _WALL_OCR_RETRY_DRAG_BASELINE.get(self.config.aspect_key)
        if pair is None:
            logger.warning('wall OCR retry drag: unknown aspect %r; skipping drag', self.config.aspect_key)
            return None
        (p1_ref, p2_ref) = pair
        p1 = self.config.scale_point([
            p1_ref[0],
            p1_ref[1]])
        p2 = self.config.scale_point([
            p2_ref[0],
            p2_ref[1]])
        (x1, y1) = (int(p1[0]), int(p1[1]))  # [recovered: pycdc reversed STORE_FAST_STORE_FAST pairs]
        (x2, y2) = (int(p2[0]), int(p2[1]))
        self.input.move(x1, y1)
        self.input.mouse_down(x1, y1)
        
        try:
            self.input.human_move(x1, y1, x2, y2, duration = 0.5)
            if self.stop_event.wait(0.3):
                self.input.mouse_up(x2, y2)
                return None
            self.input.mouse_up(x2, y2)
            return None
        except:
            self.input.mouse_up(x2, y2)


    
    def _find_wall_row_once(self):
        '''One fresh screenshot → Wall label OCR, both polarities (dark popup text first).'''
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        # Blob filter kills the small label glyphs at this capture size (live A/B:
        # 0/83 hits with filter, 14/83 without), keep it off.
        for white in (False, True):
            pt = VisionService.find_wall_labels_top_center_ocr(frame, white_text = white, cc_filter_blobs = False)
            if pt:
                return pt
        return None


    def _wall_menu_scroll_point(self):
        '''Wheel target inside the builder popup body (authoring space, per aspect).'''
        ref = _WALL_MENU_SCROLL_BASELINE.get(self.config.aspect_key)
        if ref is None:
            ref = _WALL_MENU_SCROLL_BASELINE[ASPECT_16_10]
        (x, y) = self.config.scale_point([
            ref[0],
            ref[1]])
        return (int(x), int(y))


    def _should_upgrade_walls(self):
        '''True when a full-storage hero-bar icon shows, or HUD gold/elixir is at/above the configured threshold.'''
        frame = self.window.screenshot()
        if frame is None:
            return False
        self._update_config_size(frame)
        (gx, gy) = VisionService.find_active_hgoldfull(frame)
        (ex, ey) = VisionService.find_active_helixirfull(frame)
        if gx is not None or ex is not None:
            logger.info('Wall upgrades: full-storage icon detected')
            return True
        threshold = int(getattr(self, '_wall_upgrade_threshold', 0) or 0)
        if threshold <= 0:
            return False
        groups = VisionService.extract_top_right_hud_numbers(frame, panel_open = self._panel_docked(frame))
        triplet = VisionService.parse_hud_resources_triplet(groups)
        if triplet is None:
            return False
        (gold, elixir, _) = triplet
        if gold >= threshold or elixir >= threshold:
            logger.info('Wall upgrades: loot gold=%s elixir=%s reached threshold %s', gold, elixir, threshold)
            return True
        return False


    def _deselect_wall_ui(self):
        '''Tap empty ground to close the wall selection bar / gem dialog remnants. The wall
bar has no X button — while it is open, the next tap anywhere is swallowed by the
deselect, which would eat the upcoming Attack click.'''
        self._dismiss_open_popup()
        self.input.click(pause = 0.3, *self.config.get_point('empty'))


    def _maybe_upgrade_walls(self, upgrade_walls):
        '''Upgrade walls on home when enabled and loot is high enough (threshold or full storages).'''
        if not upgrade_walls or not self._should_upgrade_walls():  # [recovered: decompiler dropped the second `not`, so it upgraded only when storages were NOT full]
            return None
        cb = getattr(self, '_status_callback', None)
        if cb:
            cb('Upgrading walls...')
        self._loot_snapshot_before_attack()
        for _ in range(2):
            self._check_stop()
            self._upgrade_walls()
            self._deselect_wall_ui()
        self._suppress_loot_negative_error_once = True


    def _maybe_auto_upgrade(self, force = False):
        '''Interval-gated builder-popup scan + upgrade decision/execution (see
        UpgradeAdvisor). ``force=True`` bypasses the interval (used when storages fill
        up — the idle gate needs a spend attempt NOW, not in 10 minutes). A failure
        here must never take down the farm loop. Returns the PassResult or None.'''
        mode = getattr(self, '_auto_upgrade_mode', MODE_OFF)
        if mode == MODE_OFF:
            return None
        now = time.monotonic()
        if not force and now - getattr(self, '_auto_upgrade_last_scan', 0) < _AUTO_UPGRADE_SCAN_INTERVAL_SECONDS:
            return None
        self._auto_upgrade_last_scan = now
        try:
            if getattr(self, '_advisor', None) is None:
                self._advisor = UpgradeAdvisor(self.window, self.input, self.vision, self.config, self.stop_event)
            result = self._advisor.run_pass(mode, reserve_builders = getattr(self, '_reserve_builders', 1),
                                            order = getattr(self, '_upgrade_order', None))
            cb = getattr(self, '_status_callback', None)
            if cb and result is not None and result.pick is not None:
                cb(f'''Upgrades: {result.note}''')
            self._emit_state(note = result.note if result else None,
                             builders = result.scan.chip if result and result.scan else None)
            return result
        except InterruptedError:
            raise
        except Exception:
            logger.warning('Auto-upgrade pass failed; continuing farm loop', exc_info = True)
            return None

    def _emit_state(self, state = None, builders = None, lab = None, storages = None, note = None):
        '''Push a live-state update to the UI panel (best-effort, never raises).'''
        cb = getattr(self, '_state_callback', None)
        if not cb:
            return None
        try:
            cb({ 'state': state, 'builders': builders, 'lab': lab, 'storages': storages, 'note': note })
        except Exception:
            logger.debug('State callback failed', exc_info = True)

    def _read_state_stable(self, attempts = 3):
        def _capture():
            frame = self.window.screenshot()
            if frame is not None and frame.size:
                self._update_config_size(frame)
            return frame
        return read_village_state_stable(_capture, self.stop_event.wait, attempts)

    def _read_hud_triplet_stable(self):
        def _capture():
            frame = self.window.screenshot()
            if frame is not None and frame.size:
                self._update_config_size(frame)
                # Panel state belongs to the frame itself — the loot tracker's stable-read
                # loop reuses whatever the last captured frame decided.
                self._last_panel_docked = self._panel_docked(frame)
            return frame
        return read_hud_triplet_stable(_capture, self.stop_event.wait, panel_getter = (lambda: getattr(self, '_last_panel_docked', False)))

    @staticmethod
    def _fmt_resource(value):
        value = int(value)
        if value >= 1000000:
            return f'''{value / 1000000:.1f}M'''
        if value >= 10000:
            return f'''{value / 1000:.0f}k'''
        return str(value)

    def _emit_village_state(self, state, mode_label):
        if state is None:
            return None
        # Storages field: real OCR'd amounts (from the last stable loot snapshot) plus
        # the game's bar-fill flags. The flat-swatch "full" templates fire from ~90%
        # up, so they are labeled "~full", never "full".
        flags = []
        if state.gold_full:
            flags.append('gold ~full')
        if state.elixir_full:
            flags.append('elixir ~full')
        triplet = getattr(self, '_last_hud_triplet', None)
        if triplet is not None:
            storages = f'''{self._fmt_resource(triplet[0])} / {self._fmt_resource(triplet[1])} / {self._fmt_resource(triplet[2])}'''
            if flags:
                storages += f''' ({', '.join(flags)})'''
        else:
            storages = ', '.join(flags) if flags else 'filling'
        self._emit_state(state = mode_label, builders = state.builders, lab = state.lab, storages = storages)

    _STATE_CACHE_TTL_SECONDS = 30.0

    def _village_state_for_cycle(self, frame):
        '''Village-state read for the farm cycle (idle gate). ``read_village_state`` is an
        OCR pass over the home HUD chips, and it used to run in full on EVERY cycle right
        after Return Home — a large chunk of the post-battle pause when auto-upgrade is
        enabled. Between two cycles nothing changes in this state unless the upgrader ran,
        so a 30s cache (invalidated whenever ``_auto_upgrade_last_scan`` moves) serves it.'''
        now = time.monotonic()
        key = (now, getattr(self, '_auto_upgrade_last_scan', 0))
        cached = getattr(self, '_village_state_for_cycle_cache', None)
        if cached is not None and (now - cached[0]) < self._STATE_CACHE_TTL_SECONDS and cached[1] == key[1]:
            return cached[2]
        state = read_village_state(frame)
        self._village_state_for_cycle_cache = (now, key[1], state)
        return state

    def _maybe_idle(self, deadline):
        '''The "run until maxed" idle gate. When both main storages are full and a
        forced upgrade pass could not spend anything, attacking earns nothing — wait
        in place (game session kept alive via recovery on each wake) until a builder
        frees up or loot is spent, instead of stopping or attacking pointlessly.

        Dark elixir has no full-storage indicator; while gold/elixir still have room
        the normal farm loop is what fills DE. Pet House state is invisible on the
        home screen (no HUD chip, no builder-popup row — verified live), so pets are
        the user's manual job and never block idling; the status line calls out an
        idle LAB so research (also manual for now) is never silently forgotten.'''
        if getattr(self, '_auto_upgrade_mode', MODE_OFF) not in LIVE_UPGRADE_MODES:
            return None
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        state = self._village_state_for_cycle(frame)
        self._emit_village_state(state, 'farming')
        if state is None:
            return None
        reserve = getattr(self, '_reserve_builders', 1)
        free = state.free_builders
        # Spend eagerly: ANY full storage with a spare builder is money leaking (live
        # pain: Grand Warden started with elixir, then the free builder sat next to a
        # full gold storage for 10 minutes waiting on the interval pass).
        eager = free is not None and free > reserve and (state.gold_full or state.elixir_full)
        if not state.storages_full and not eager:
            return None
        if not state.storages_full:
            # Eager-only trigger: rate-limit so a full-gold stretch with nothing
            # startable does not burn a ~20s scan every battle cycle.
            now = time.monotonic()
            if now - getattr(self, '_eager_spend_last', 0) < 180:
                return None
            self._eager_spend_last = now
        logger.info('Idle gate: spend burst (%s) — forcing upgrade passes', state.summary())
        # Burn through candidates NOW instead of one per 5-minute wake: every failed
        # pick lands on cooldown so each retry reaches the next candidate, and every
        # SUCCESS frees loot but may leave another builder idle — keep going until
        # nothing is pickable or the attempts are spent.
        for _attempt in range(5):
            result = self._maybe_auto_upgrade(force = True)
            if result is None:
                break  # scan preconditions failed
            if result.pick is None and not result.collecting:
                break  # genuinely nothing pickable remains (a collect pass is not a verdict)
        self._village_state_for_cycle_cache = None  # burst may have freed loot — post-burst re-read must be fresh
        state = self._read_state_stable()
        if state is None or not state.storages_full:
            return None
        if not (getattr(self, '_gold_pinned', False) and getattr(self, '_elixir_pinned', False)):
            # Icons say ~full but the values are still moving — real headroom remains
            # (live: idled at 18M/21M gold, wasting ~3M of farmable gold). Keep
            # farming until both numbers pin at their caps.
            logger.info('Idle gate: storages ~full but still filling (gold pinned=%s, elixir pinned=%s) — farming on', getattr(self, '_gold_pinned', False), getattr(self, '_elixir_pinned', False))
            return None
        reserve = getattr(self, '_reserve_builders', 1)
        cb = getattr(self, '_status_callback', None)
        logger.info('Idle gate: nothing startable with storages full (%s) — pausing attacks, rechecking every %ds', state.summary(), _IDLE_RECHECK_SECONDS)
        while True:
            self._check_stop()
            if deadline and time.time() >= deadline:
                return None
            msg = f'''Idling — {state.summary() if state else 'state unreadable'}; recheck in {_IDLE_RECHECK_SECONDS // 60}m'''
            if state is not None and state.lab_idle:
                msg += ' — LAB IS IDLE: start a research!'
            if cb:
                cb(msg)
            self._emit_village_state(state, 'idling')
            if self.stop_event.wait(_IDLE_RECHECK_SECONDS):
                return None
            # The game disconnects after a few idle minutes — recovery clicks Reload
            # (after its own grace period) and walks back to the home screen.
            self._home_screen_recovery()
            state = self._read_state_stable()
            if state is None:
                continue
            if not state.storages_full:
                if state.builders is None:
                    # Unreadable builder chip = probably not a clean home frame (mid-
                    # recovery, reload dialog) — the missing full-icons prove nothing.
                    # Stay idle; the next wake re-reads (live repro: one wake exited on
                    # "builders ? free, storages filling" right after a disconnect).
                    logger.info('Idle: degraded read (%s) — staying idle', state.summary())
                    continue
                logger.info('Idle over: storages have room again (%s)', state.summary())
                break
            free = state.free_builders
            if free is not None and free > reserve:
                logger.info('Idle over: %d builder(s) free (%s)', free, state.summary())
                break
        self._auto_upgrade_last_scan = 0  # resume with an immediate scan so the freed builder is used
        if cb:
            cb('Resuming — ' + state.summary())
        self._emit_village_state(state, 'farming')


    def _upgrade_walls_pick_resource_and_okay(self):
        '''Fresh frame → click an affordable resource slot → Okay. If neither resource can pay, close the popup instead (never confirm a red cost).'''
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        pair = VisionService.upgrade_cost_redness_by_resource_icons(frame)
        for _ in range(2):
            if pair.gold.cost_roi_xywh or pair.elixir.cost_roi_xywh:
                break
            # The popup re-renders for a beat after the last add click and the cost buttons
            # can miss the template match — settle and re-read before giving up.
            if self.stop_event.wait(0.4):
                return None
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            pair = VisionService.upgrade_cost_redness_by_resource_icons(frame)
        picked = False
        # cost_roi_xywh None means the cost text could not be measured — never click a slot
        # on a blind reading (an unaffordable click opens the buy-with-gems dialog).
        # Elixir first: attacking costs GOLD (Find a Match entry fee), so spend elixir on
        # walls whenever it can pay and keep gold for matchmaking.
        if pair.elixir.redness < 0.2 and pair.elixir.cost_roi_xywh and pair.elixir.center:
            logger.info('Wall upgrade: paying with elixir (redness %.2f)', pair.elixir.redness)
            self.input.click(pause = 0.3, *pair.elixir.center)
            picked = True
        elif pair.gold.redness < 0.2 and pair.gold.cost_roi_xywh and pair.gold.center:
            logger.info('Wall upgrade: paying with gold (redness %.2f)', pair.gold.redness)
            self.input.click(pause = 0.3, *pair.gold.center)
            picked = True
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        if not picked:
            logger.info('Wall upgrade: no affordable resource slot (gold %.2f, elixir %.2f) — dismissing without confirming', pair.gold.redness, pair.elixir.redness)
            if not pair.gold.cost_roi_xywh and not pair.elixir.cost_roi_xywh:
                try:
                    import time as _time
                    import cv2 as _cv2
                    from app.utils.common import get_user_app_data_dir
                    dbg = get_user_app_data_dir() / 'debug'
                    dbg.mkdir(parents = True, exist_ok = True)
                    path = dbg / f'''wallfail_{int(_time.time())}.jpg'''
                    _cv2.imwrite(str(path), frame, [_cv2.IMWRITE_JPEG_QUALITY, 88])
                    logger.info('Wall upgrade: confirm-time frame saved to %s', path)
                except Exception:
                    logger.debug('Wall upgrade: debug frame dump failed', exc_info = True)
            self._deselect_wall_ui()
            return None
        (ox, oy) = self.vision.find_template(frame, 'okay.png')
        if not ox:
            # New-UI "Upgrade Walls" dialog (same one Builder Base shows): green Okay.
            (ox, oy) = self.vision.find_template(frame, 'wallokay.png')
        if ox:
            self.input.click(ox, oy, pause = 0.3)
            logger.info('Wall upgrade batch confirmed')

    
    def _upgrade_walls(self):
        '''Open builder menu, scroll to Wall, add walls → remove if both red → Okay.'''
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        top_roi = None  # builder portrait moved to the bottom-right in the new UI — search the whole frame
        home_roi = VisionService.bottom_half_region(frame)
        (hax, hay) = self.vision.find_template(frame, 'attack.png', region = home_roi)
        if not hax:
            logger.info('Wall upgrade: not on the home screen (Attack button missing) — skipping this pass')
            return None
        # New UI: no builder portrait any more — walls are behind the bottom-right Build button's
        # "Buildings & Heroes" panel. Same flow as Builder Base, Home Village resources.
        (nbx, nby) = self.vision.find_template(frame, 'buildbtn.png', threshold = 0.8, region = home_roi)
        if nbx:
            self._upgrade_walls_from_build_panel(village = 'home')
            return None
        (bx, by) = self._find_home_village_builder(frame, top_roi)
        if not bx:
            logger.info('Wall upgrade: builder portrait not found — skipping this pass')
            return None
        self.input.click(bx, by, pause = 0.5)
        # TH15+ overflows the builder popup ('Suggested upgrades' grows and 'Other upgrades'
        # continues past the fold), so the Wall row can start below the visible area. The
        # popup scrolls with the mouse wheel without closing; touch-drags scroll too but
        # overshoot past Wall (it now sits mid-list, not at the end). Poll the OCR at each
        # position and wheel down a notch between misses.
        if self.stop_event.wait(0.3):
            return None
        wall_pt = None
        candidate = None
        scrolls = 0
        for _ in range(_WALL_MENU_SCROLL_STEPS * 2):
            self._check_stop()
            found = self._find_wall_row_once()
            if found:
                if candidate and abs(found[1] - candidate[1]) <= self.config.scale_scalar(_WALL_ROW_STABLE_TOL):
                    wall_pt = found
                    if scrolls:
                        logger.info('Wall upgrade: Wall row found after %d scroll nudge(s)', scrolls)
                    break
                # One agreeing frame is required before clicking — the list keeps easing
                # after a wheel nudge, and a click on stale coordinates lands on whatever
                # row slid underneath (live repro: opened the Blacksmith's Forge).
                candidate = found
                if self.stop_event.wait(0.25):
                    return None
                continue
            candidate = None
            scrolls += 1
            if scrolls >= _WALL_MENU_SCROLL_STEPS:
                break
            self.input.scroll(*self._wall_menu_scroll_point(), _WALL_MENU_WHEEL_CLICKS)
            if self.stop_event.wait(0.5):
                return None
        if not wall_pt:
            logger.info('Wall upgrade: Wall label OCR missed at all scroll positions — skipping this pass')
            return None
        self.input.click(pause = 0.6, *wall_pt)
        # Clicking the Wall row pans the camera to a wall before the selection bar
        # renders (often >1s) — poll for Upgrade More instead of trusting one early
        # frame (live rate before polling: ~1 success in 8 passes).
        (umx, umy) = (None, None)
        frame = None
        for _ in range(8):
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            bot_roi = VisionService.bottom_half_region(frame)
            (umx, umy) = self.vision.find_template(frame, 'upgrademore.png', region = bot_roi)
            if umx:
                break
            if self.stop_event.wait(0.5):
                return None
        if not umx:
            # The Wall click missed (wrong row / a building dialog opened instead) —
            # close whatever came up so it cannot block the next pass or the Attack tap.
            logger.info('Wall upgrade: upgrademore.png not visible after Wall row click — dismissing and skipping this pass')
            if frame is not None:
                try:
                    import time as _time
                    import cv2 as _cv2
                    from app.utils.common import get_user_app_data_dir
                    dbg = get_user_app_data_dir() / 'debug'
                    dbg.mkdir(parents = True, exist_ok = True)
                    path = dbg / f'''wallrow_{int(_time.time())}.jpg'''
                    _cv2.imwrite(str(path), frame, [_cv2.IMWRITE_JPEG_QUALITY, 88])
                    logger.info('Wall upgrade: post-click frame saved to %s', path)
                except Exception:
                    logger.debug('Wall upgrade: wallrow debug dump failed', exc_info = True)
                self._dismiss_okay_or_exit_on_frame(frame)
            return None
        self.input.click(umx, umy, pause = 0.4)
        # Add walls to the batch while at least one resource can still pay the total.
        added = 0
        for _ in range(_WALL_BATCH_MAX_ADDS):
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            pair = VisionService.upgrade_cost_redness_by_resource_icons(frame)
            if not pair.gold.cost_roi_xywh and not pair.elixir.cost_roi_xywh:
                # The cost buttons are the only reliable proof the multi-upgrade popup is
                # actually open — addwall/removewall false-positive on home-screen greens
                # (incl. the Attack button checkmark), so never click blind.
                logger.info('Wall upgrade: cost buttons not visible — popup not open, stopping batch')
                break
            if pair.gold.redness >= 0.2 and pair.elixir.redness >= 0.2:
                break
            # Mid-bottom only: the real Add Wall button sits in the popup's center cluster.
            # A plain bottom-half search grabs the home Attack! button's green checkmark
            # (bottom-left, still visible beside the popup) once +1 greys out.
            (fh, fw) = frame.shape[:2]
            mid_roi = (fw // 4, fh // 2, fw // 2, fh - fh // 2)
            (awx, awy) = VisionService.find_active_addwall(frame, region = mid_roi)
            if not awx:
                break
            self.input.click(awx, awy, pause = 0.3)
            added += 1
        if added == 0:
            self._deselect_wall_ui()
            return None
        self._check_stop()
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        pair = VisionService.upgrade_cost_redness_by_resource_icons(frame)
        (fh, fw) = frame.shape[:2]
        mid_roi = (fw // 4, fh // 2, fw // 2, fh - fh // 2)
        if added and pair.gold.redness >= 0.2 and pair.elixir.redness >= 0.2:
            # Last add pushed the total over both resources — take one back before confirming.
            (rwx, rwy) = VisionService.find_active_removewall(frame, region = mid_roi)
            if rwx:
                self.input.click(rwx, rwy, pause = 0.4)
        elif added > 1 and pair.elixir.redness >= 0.2 and pair.gold.redness < 0.2 and pair.gold.cost_roi_xywh:
            # Gold will pay (elixir can't) — drop one wall so a maxed batch never drains gold
            # to 0. Find a Match costs ~1300 gold; a zeroed gold storage blocks all attacking.
            (rwx, rwy) = VisionService.find_active_removewall(frame, region = mid_roi)
            if rwx:
                logger.info('Wall upgrade: gold is the payer — removing one wall to keep the attack entry fee')
                self.input.click(rwx, rwy, pause = 0.4)
        logger.info('Wall upgrade: %d wall(s) added to batch', added)
        self._upgrade_walls_pick_resource_and_okay()

    
    def _dismiss_okay_or_exit_on_frame(self, frame):
        '''If ``okay.png``, ``exit.png``, or a known dialog-specific control is visible,
        click it. Returns True if dismissed. The Daily Reward popup (blocked the bot a
        whole night) must be CLAIMED before its X works ("Claim reward first!"), so the
        green Claim button outranks its grey X; both have their own art (exit.png does
        not match).'''
        names = ['okay.png', 'exit.png']
        for extra in ('claim_btn.png', 'dailyreward_x.png', 'needgold_x.png'):
            if get_template_path(extra).exists():
                names.append(extra)
        for name in names:
            (x, y) = self.vision.find_template(frame, name)
            if not x:
                continue
            self.input.click(x, y, pause = 0.15)
            return True
        return False

    
    def _wait_for_attack_with_nudge(self, timeout = 10, error = True):
        '''Poll bottom-half ``attack.png``; dismiss ``okay`` / ``exit`` popups first; else empty + scroll.'''
        start = time.time()
        next_capital_scan = 0.0
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return (None, None)
                continue
            self._update_config_size(frame)
            if self._dismiss_okay_or_exit_on_frame(frame):
                if self.stop_event.wait(0.25):
                    return (None, None)
                continue
            now = time.monotonic()
            if now >= next_capital_scan:
                next_capital_scan = now + 1.5
                (chx, chy) = self._find_capital_return_home_button(frame)
                if chx:
                    logger.info('Attack wait: Capital screen detected â€” clicking Return Home')
                    self.input.click(chx, chy, pause = 0.3)
                    if self.stop_event.wait(0.5):
                        return (None, None)
                    continue
            (sx, sy) = self.vision.find_template(frame, 'surrender.png')
            if sx:
                # We are inside a live battle — nudge clicks would deploy troops. Bail out and
                # let _home_screen_recovery surrender/return-home.
                logger.warning('Attack wait: live battle detected (surrender visible) — leaving it to recovery')
                return (None, None)
            search_region = self._search_region_for_template(frame, 'attack.png', None, None, 200)
            (ax, ay) = self.vision.find_template(frame, 'attack.png', region = search_region)
            if ax:
                return (ax, ay)
            self._nudge_view_to_reveal_attack()
            if self.stop_event.wait(0.35):
                return (None, None)
        if error:
            logger.warning('Timeout waiting for attack.png')  # [recovered: decompiler misnested this inside the loop — it spammed once per poll]
        return (None, None)

    
    def _run_loop(self, method_id, duration_seconds, star_bonus = False, ranked_fill = False, upgrade_walls = False):
        start_time = time.time()
        if self.stop_event.wait(1):
            return None
        frame = self.window.screenshot()
        self._update_config_size(frame)
        empty_pt = self.config.get_point('empty')
        self.input.click(pause = 0.2, *empty_pt)
        self.input.scroll(*self._scroll_point(), 20)
        delay = random.uniform(0.1, 0.3)
        if self.stop_event.wait(delay):
            return None
        if star_bonus and self._is_star_bonus_claimed():
            logger.info('Star bonus mode: no star bonus template matched on home — nothing to collect. Finishing without attacks.')
            return None
        # duration_seconds == 0 → unlimited ("run until maxed"): only the user's Stop
        # ends the session; full storages park the loop in _maybe_idle instead.
        deadline = start_time + duration_seconds if duration_seconds else None
        self._maybe_upgrade_walls(upgrade_walls)
        self._maybe_auto_upgrade()
        self._maybe_idle(deadline)
        cb = getattr(self, '_status_callback', None)
        troop_failures = 0
        while deadline is None or time.time() < deadline:
            self._check_stop()
            self._in_battle = True
            try:
                outcome = self._find_match_and_attack(method_id, ranked_fill)
            finally:
                self._in_battle = False
                self.reset_inactivity_timer()
            self._return_home()
            self._home_screen_recovery()
            if outcome == 'ranked_limit':
                return None
            if outcome == 'troop':
                troop_failures += 1
                if troop_failures >= _TROOP_FAILURE_LIMIT:
                    if deadline is None:
                        # Run-until-maxed must never stop on its own: long back-off
                        # instead (a stuck popup / event screen usually clears, and
                        # recovery runs again on the next attempt).
                        msg = f'''Troops not found {troop_failures} times in a row — backing off {_IDLE_RECHECK_SECONDS // 60}m, then retrying (run until maxed).'''
                        logger.warning(msg)
                        if cb:
                            cb(msg)
                        troop_failures = 0
                        if self.stop_event.wait(_IDLE_RECHECK_SECONDS):
                            return None
                        self._home_screen_recovery()
                        continue
                    msg = f'''Troops not found {troop_failures} times in a row — stopping. Check the army / saved recipe.'''
                    logger.warning(msg)
                    if cb:
                        cb(msg)
                    return None
                msg = f'''Troops not found ({troop_failures}/{_TROOP_FAILURE_LIMIT}) — retrying in {_TROOP_RETRY_WAIT_SECONDS}s.'''
                logger.warning(msg)
                if cb:
                    cb(msg)
                # Tap any collect bubbles while we are home — if the failure was really the
                # need-more-gold dialog (entry fee unaffordable), mine gold un-wedges it.
                self._multi_run_collect_home_village_resources()
                if self.stop_event.wait(_TROOP_RETRY_WAIT_SECONDS):
                    return None
            else:
                troop_failures = 0
            self._maybe_upgrade_walls(upgrade_walls)
            self._maybe_auto_upgrade()
            self._maybe_idle(deadline)
            self.input.scroll(*self._scroll_point(), 5)
            if self.stop_event.wait(random.uniform(0.15, 0.25)):
                return None
            if star_bonus and self._is_star_bonus_claimed():
                logger.info('Star bonus claimed (star icons no longer visible). Stopping.')
                return None
        return None

    
    _BB_NIGHT_WITCH_METHOD = 6

    def _recover_stuck_screen(self):
        '''Called when attack.png can't be found (Home Village or Builder Base). Looks for every
button that could be blocking the home screen and clicks whatever is on screen, repeating
until nothing recognizable is left, then taps empty space and resets the view.'''
        from app.utils.common import get_template_path
        recovery_buttons = [
            'breturnhome.png', 'breturnhome1920.png',
            'returnhome.png', 'returnhome2.png',
            'okay.png', 'wallokay.png', 'bbpanelclose.png', 'chestclaim.png', 'chestcontinue.png', 'claim_btn.png',
            'dailyreward_x.png', 'needgold_x.png', 'exit.png',
            'endbattle.png', 'surrender.png',
            'reload.png',
        ]
        for _ in range(6):
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return None
                continue
            self._update_config_size(frame)
            (ax, ay) = self.vision.find_template(frame, 'attack.png')
            if ax:
                return None
            clicked = False
            for tmpl in recovery_buttons:
                # Skip templates that don't exist for this aspect (e.g. returnhome2.png is 16:10 only).
                if not get_template_path(tmpl).is_file():
                    continue
                (x, y) = self.vision.find_template(frame, tmpl)
                if not x:
                    continue
                logger.info('Recovery: attack.png missing — found %s, clicking', tmpl)
                self.input.click(x, y, pause = 0.4)
                if tmpl == 'chestclaim.png':
                    self._tap_empty_until_chest_continue()
                clicked = True
                break
            if not clicked:
                break
            if self.stop_event.wait(1.5):
                return None
        empty_pt = self.config.get_point('empty')
        self.input.click(pause = 0.2, *empty_pt)
        self.input.scroll(*self._scroll_point(), 20)
        self.stop_event.wait(1)

    def _run_builder_base_loop(self, duration_seconds, star_bonus = False, upgrade_walls = False):
        '''Builder Base farming: Attack → Find Now → wait out the search clouds → Baby Dragon deploy →
end battle (2-star / gold / elixir / natural) → Return Home.'''
        start_time = time.time()
        cb = getattr(self, '_status_callback', None)
        if self.stop_event.wait(1):
            return None
        frame = self.window.screenshot()
        if not frame is None:
            self._update_config_size(frame)
        empty_pt = self.config.get_point('empty')
        self.input.click(pause = 0.2, *empty_pt)
        self.input.scroll(*self._scroll_point(), 20)
        if self.stop_event.wait(random.uniform(0.1, 0.3)):
            return None
        if star_bonus and self._is_bb_star_bonus_finished():
            msg = 'Builder Base star bonus: bstar.png not visible — nothing to collect. Finishing without attacks.'
            logger.info(msg)
            if cb:
                cb(msg)
            return None
        battle_count = 0
        while time.time() - start_time < duration_seconds:
            self._check_stop()
            # Spend Builder Gold / Builder Elixir on walls between battles too, not only after
            # one: a battle that ended in surrender or a run that starts with full storages
            # would otherwise sit on loot until the next battle had already happened.
            self._maybe_upgrade_bb_walls(upgrade_walls)
            self.input.scroll(*self._scroll_point(), 20)
            if self.stop_event.wait(random.uniform(0.1, 0.25)):
                return None
            (ax, ay) = self._wait_for_image('attack.png', timeout = 10)
            if not ax:
                logger.warning('Builder Base: attack.png not found — running recovery')
                self._recover_stuck_screen()
                continue
            self.input.click(ax, ay, pause = 0.15)
            (fx, fy) = self._wait_for_image('findnow.png', timeout = 10)
            if not fx:
                logger.warning('Builder Base: findnow.png not found — running recovery')
                self._recover_stuck_screen()
                continue
            self.input.click(fx, fy, pause = 0.15)
            self._in_battle = True
            # Find Now kicks off matchmaking: the cloud screen can sit there for ~20s before the
            # enemy base appears. Never deploy into it — hold until the clouds clear (a base that
            # loads without any clouds only needs the absence to hold for _BB_CLOUD_CLEAR_SECONDS).
            self._bb_wait_for_search_clouds()
            _tmpl = getattr(self, '_bb_troop_template', 'babydragon.png')
            (bx, by) = self._wait_for_image(_tmpl, timeout = 30, error = False)
            if not bx:
                msg = f'Builder Base: {_tmpl} not found after Find Now'
                logger.warning(msg)
                if cb:
                    cb(msg)
                self._in_battle = False
                self.reset_inactivity_timer()
                continue
            frame = self.window.screenshot()
            if frame is None:
                continue
            self._update_config_size(frame)
            (h, w) = frame.shape[:2]
            cy = h // 2
            cx = w // 2
            if _BB_HUMAN_CAMERA:
                if not self._bb_human_camera_nudge(frame):
                    return None
            else:
                self.input.move(cx, cy)
                if self.stop_event.wait(0.05):
                    return None
                self.input.scroll(cx, cy, 4)
                if self.stop_event.wait(0.15):
                    return None
            frame = self.window.screenshot()
            if frame is None:
                continue
            self._update_config_size(frame)
            # The battle screen can still be fading in right after the zoom nudge (no deploy bar yet),
            # so retry with fresh screenshots for a few seconds before giving up.
            deployed = False
            deploy_deadline = time.time() + 12
            while True:
                if self._deploy_bb_baby_dragons(frame):
                    deployed = True
                    break
                if time.time() >= deploy_deadline:
                    break
                if self.stop_event.wait(0.5):
                    return None
                frame = self.window.screenshot()
                if frame is None:
                    continue
                self._update_config_size(frame)
            if not deployed:
                _t = getattr(self, '_bb_troop_template', 'babydragon.png')
                logger.warning('Builder Base: %s still not visible after 12s — deploy failed', _t)
                if frame is not None:
                    self._save_template_miss_snapshot(frame, _t, VisionService.bottom_half_region(frame))
                self._in_battle = False
                self.reset_inactivity_timer()
                continue
            if getattr(self, '_bb_two_star_mode', False):
                self._bb_two_star_end_battle_and_return_home()
            elif self._loot_prioritise == 'elixir':
                self._bb_surrender_and_return_home()
            elif self._loot_prioritise == 'gold':
                self._bb_gold_prioritise_end_battle_and_return_home()
            else:
                self._bb_end_battle_and_return_home()
            self._in_battle = False
            self.reset_inactivity_timer()
            battle_count += 1
            self._maybe_upgrade_bb_walls(upgrade_walls)
            if battle_count % _BB_ELIXIR_CART_COLLECT_EVERY == 0:
                logger.info('Builder Base: battle %d — collecting elixir cart', battle_count)
                self._bb_collect_elixir_cart_after_attack()
            if star_bonus and self._is_bb_star_bonus_finished():
                logger.info('Builder Base star bonus finished (bstar.png no longer visible). Stopping.')
                return None
            if self.stop_event.wait(random.uniform(0.35, 0.6)):
                return None
        return None

    
    def _bb_pan_down_left_from_center(self):
        '''Pan BB view down-left from screen center (~500px) to reveal the boat / elixir cart.'''
        self._check_stop()
        frame = self.window.screenshot()
        if frame is None or frame.size == 0:
            return None
        self._update_config_size(frame)
        (h, w) = frame.shape[:2]
        cx = w // 2 + random.randint(-25, 25)
        cy = h // 2 + random.randint(-25, 25)
        cx = max(8, min(w - 8, cx))
        cy = max(8, min(h - 8, cy))
        self.input.move(cx, cy, 0)
        self.input.mouse_up(cx, cy)
        if self.stop_event.wait(0.06):
            self._check_stop()
        step = 500
        x2 = max(8, min(w - 8, cx - step))
        y2 = max(8, min(h - 8, cy + step))
        self.input.mouse_down(cx, cy)
        self.input.human_move(cx, cy, x2, y2, duration = random.uniform(0.35, 0.55))
        self.input.mouse_up(x2, y2)
        if self.stop_event.wait(0.45):
            self._check_stop()
            return None

    
    def _find_bb_full_elixir_cart(self, attempts = 3):
        '''Up to ``attempts`` screenshots; try fullecart templates in order (top-right quadrant).'''
        empty_pt = self.config.get_point('empty')
        for _ in range(attempts):
            self._check_stop()
            frame = self.window.screenshot()
            if not frame is None:  # [recovered: decompiler turned this `if` into a `while` and made the return unconditional]
                self._update_config_size(frame)
                roi = VisionService.top_right_quadrant_region(frame)
                for template in _BB_FULL_ELIXIR_CART_TEMPLATES:
                    (x, y) = self.vision.find_template(frame, template, threshold = 0.8, region = roi)
                    if x:
                        return (x, y)
            self.input.click(pause = 0.15, *empty_pt)
        return (None, None)

    
    def _bb_collect_elixir_cart_after_attack(self):
        '''After a BB raid: dismiss popups, pan to cart, collect full elixir cart if visible.'''
        if self.stop_event.wait(0.35):
            return None
        self.input.click(pause = 0.15, *self.config.get_point('empty'))
        if self.stop_event.wait(0.15):
            return None
        self._bb_pan_down_left_from_center()
        (cx, cy) = self._find_bb_full_elixir_cart(attempts = 3)
        if cx:
            self.input.click(cx, cy, pause = 0.2)
            (coll_x, coll_y) = self._wait_for_image(_BB_COLLECT_TEMPLATE, timeout = 8, error = False)
            if coll_x:
                self.input.click(coll_x, coll_y, pause = 0.2)
            else:
                logger.warning('Builder Base: collect.png not found after elixir cart')
        else:
            logger.debug('Builder Base: fullecart not visible — skipping cart collect')
        self.input.click(pause = 0.15, *self.config.get_point('empty'))

    
    def _human_cursor_move(self, x0, y0, x1, y1):
        '''Move the (button-up) cursor along a slightly curved, eased path. Returns False if stopped.'''
        import math
        steps = random.randint(10, 18)
        bow = random.uniform(-0.12, 0.12) * math.hypot(x1 - x0, y1 - y0)
        for i in range(1, steps + 1):
            self._check_stop()
            t = i / steps
            e = t * t * (3 - 2 * t)  # smoothstep ease in/out
            px = x0 + (x1 - x0) * e - (y1 - y0) / max(1.0, math.hypot(x1 - x0, y1 - y0)) * bow * math.sin(math.pi * e)
            py = y0 + (y1 - y0) * e + (x1 - x0) / max(1.0, math.hypot(x1 - x0, y1 - y0)) * bow * math.sin(math.pi * e)
            self.input.move(int(px), int(py))
            if self.stop_event.wait(random.uniform(0.012, 0.032)):
                return False
        return True

    def _bb_human_camera_nudge(self, frame):
        '''Before deploying: pause like a person would, zoom in at a few random off-centre spots,
look around, then zoom back out to the full deploy view. Returns False if the bot was stopped.'''
        (h, w) = frame.shape[:2]
        cx, cy = w // 2, h // 2
        if self.stop_event.wait(random.uniform(0.5, 1.6)):
            return False
        cur = getattr(self, '_cursor_xy', (cx, cy))
        total_in = 0
        for _ in range(random.choice(_BB_CAMERA_LOOKS)):
            # Off-centre point inside the map area (stay above the troop bar and below the HUD).
            for _try in range(10):
                px = random.randint(int(w * 0.15), int(w * 0.85))
                py = random.randint(int(h * 0.2), int(h * 0.66))
                if abs(px - cx) > w * 0.12 or abs(py - cy) > h * 0.1:
                    break
            if not self._human_cursor_move(cur[0], cur[1], px, py):
                return False
            cur = (px, py)
            if self.stop_event.wait(random.uniform(0.1, 0.35)):
                return False
            n = random.randint(*_BB_CAMERA_ZOOM_IN)
            self.input.scroll(px, py, n, upward = True)
            total_in += n
            if self.stop_event.wait(random.uniform(0.5, 1.5)):  # "looking" at the base
                return False
        # Drift back toward the middle (not exactly the centre), then zoom all the way out.
        rx = cx + random.randint(-int(w * 0.04), int(w * 0.04))
        ry = cy + random.randint(-int(h * 0.04), int(h * 0.04))
        if not self._human_cursor_move(cur[0], cur[1], rx, ry):
            return False
        self._cursor_xy = (rx, ry)
        if self.stop_event.wait(random.uniform(0.2, 0.5)):
            return False
        # Original nudge was 4 notches out; zoom-out is clamped at the minimum, so the extra
        # margin guarantees we finish in the same fully zoomed-out framing the deploy points expect.
        out_total = total_in + 4 + _BB_CAMERA_OUT_MARGIN
        first = random.randint(1, max(1, out_total - 1))
        self.input.scroll(rx, ry, first)
        if self.stop_event.wait(random.uniform(0.15, 0.4)):
            return False
        self.input.scroll(rx, ry, out_total - first)
        return not self.stop_event.wait(random.uniform(0.4, 0.9))  # let the zoom animation settle

    def _save_template_miss_snapshot(self, frame, template_name, region = None):
        '''Diagnostics: when a template the bot expected is missing, log its best score and save the
exact frame the bot saw, so you can compare it to what the template was cut from.'''
        try:
            import cv2
            from app.utils.common import get_user_app_data_dir
            (score, cx, cy) = VisionService._template_best_match(frame, template_name, region)
            out = get_user_app_data_dir() / f'miss_{template_name.replace(".png", "")}_{int(time.time())}.png'
            cv2.imwrite(str(out), frame)
            logger.warning('Template miss: %s best score %.3f at (%s, %s); frame saved to %s', template_name, float(score or 0), cx, cy, out)
        except Exception as e:
            logger.warning('Template miss snapshot failed: %s', e)

    def _deploy_bb_baby_dragons(self, frame):
        '''Find all Baby Dragon icons, deploy on diamond edges, wait, then re-click saved icons.'''
        self._is_deploying = True
        try:
            strategy = AttackStrategy(self.input, self.vision, self.config, self.stop_event)
            roi = VisionService.bottom_half_region(frame)
            _tmpl = getattr(self, '_bb_troop_template', 'babydragon.png')
            centers = VisionService.find_all_template_centers(frame, _tmpl, region = roi, max_matches = 12, suppress_pad_frac = _BB_TEMPLATE_SUPPRESS_PAD)
            if not centers:
                return False
            deploy_count = len(centers)
            self.input.click(centers[0][0], centers[0][1], pause = 0.3, rand = False)
            if self.stop_event.wait(0.2):
                return True
            for px, py in strategy._even_diamond_top_perimeter_points(frame, deploy_count, reserve_top_corner_slot = True):
                self._check_stop()
                self.input.click(px, py, pause = _EDRAG_DELAY, rand = False)
            self._deploy_bb_battle_or_flying_machine(strategy)
            if self._loot_prioritise != 'elixir':
                if self.stop_event.wait(_BB_BABY_DRAGON_RECLICK_WAIT):
                    return True
                for x, y in centers:
                    self._check_stop()
                    self.input.click(x, y, pause = 0.15, rand = False)
            return True
        finally:
            self._is_deploying = False
            self.reset_inactivity_timer()

    
    def _deploy_bb_battle_or_flying_machine(self, strategy):
        '''One bar lookup: Battle Machine, else Flying Machine; deploy on a random diamond edge.'''
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        roi = VisionService.bottom_half_region(frame)
        (tx, ty) = self.vision.find_template(frame, _BB_BATTLE_MACHINE_TEMPLATE, region = roi)
        if not tx:
            (tx, ty) = self.vision.find_template(frame, _BB_FLYING_MACHINE_TEMPLATE, region = roi)
        if not tx:
            logger.debug('Builder Base: %s / %s not found on troop bar', _BB_BATTLE_MACHINE_TEMPLATE, _BB_FLYING_MACHINE_TEMPLATE)
            return None
        (px, py) = strategy._random_diamond_perimeter_point(frame)
        self.input.click(tx, ty, pause = 0.3, rand = False)
        if self.stop_event.wait(0.2):
            return None
        self.input.click(px, py, pause = _EDRAG_DELAY, rand = False)

    
    def _bb_end_battle_and_return_home(self):
        '''Wait for natural battle end, dismiss Okay, then tap BB Return Home.
Polls (rather than a single blocking wait) so the Flying/Battle Machine ability
can be re-triggered every _BB_COPTER_ABILITY_INTERVAL seconds while waiting.'''
        start = time.time()
        timeout = 90
        copter_last_click = 0
        end_battle_clicked = False
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return None
                continue
            self._update_config_size(frame)
            copter_last_click = self._bb_maybe_use_copter_ability(frame, copter_last_click)
            bot_roi = VisionService.bottom_half_region(frame)
            (ex, ey) = self.vision.find_template(frame, 'endbattle.png', region = bot_roi)
            if ex:
                self.input.click(ex, ey, pause = 0.15)
                end_battle_clicked = True
                break
            if self.stop_event.wait(0.5):
                return None
        if not end_battle_clicked:
            logger.warning('Builder Base: endbattle.png not found')
            return None
        self._bb_dismiss_okay_and_return_home()

    
    def _bb_maybe_use_copter_ability(self, frame, last_click_ts):
        '''Click the deployed Flying Machine / Battle Machine's icon every
_BB_COPTER_ABILITY_INTERVAL seconds, so it keeps re-using its ability throughout the battle.'''
        now = time.time()
        if now - last_click_ts < _BB_COPTER_ABILITY_INTERVAL:
            return last_click_ts
        roi = VisionService.bottom_half_region(frame)
        (cx, cy) = self.vision.find_template(frame, _BB_FLYING_MACHINE_TEMPLATE, region = roi)
        if not cx:
            (cx, cy) = self.vision.find_template(frame, _BB_BATTLE_MACHINE_TEMPLATE, region = roi)
        if cx:
            self.input.click(cx, cy, pause = 0.15, rand = False)
            logger.info('Builder Base: Flying/Battle Machine ability clicked')
            return now
        return last_click_ts

    def _bb_wait_for_natural_end_and_return_home(self):
        '''Let the battle end on its own (timer runs out) instead of tapping End Battle.
Some setups show an Okay/loot-summary screen first, others go straight to breturnhome.png
— watch for whichever one actually shows up, one screenshot per pass. Also keeps the
Flying/Battle Machine ability firing every _BB_COPTER_ABILITY_INTERVAL seconds while it waits.'''
        start = time.time()
        copter_last_click = 0
        while time.time() - start < _MANUAL_BATTLE_WAIT_SECONDS:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return None
                continue
            self._update_config_size(frame)
            copter_last_click = self._bb_maybe_use_copter_ability(frame, copter_last_click)
            (ox, oy) = self.vision.find_template(frame, 'okay.png')
            if ox:
                self.input.click(ox, oy, pause = 0.15)
                break
            (h, w) = frame.shape[:2]
            (rh_template, scale_template) = self._bb_return_home_template_for_screen(w, h)
            search_region = self._search_region_for_template(frame, rh_template, None, None, 200)
            (rx, ry) = self.vision.find_template(frame, rh_template, threshold = 0.8, region = search_region, scale_template = scale_template)
            if rx:
                self.input.click(rx, ry, pause = 0.2)
                return None
            (cx, cy) = self.vision.find_template(frame, 'chestclaim.png')
            if cx:
                logger.info('Builder Base: chestclaim.png (replacing return home); running chest flow')
                self.input.click(cx, cy, pause = 0.2)
                if self.stop_event.wait(0.35):
                    return None
                self._tap_empty_until_chest_continue()
                return None
            if self.stop_event.wait(0.5):
                return None
        else:
            logger.warning('Builder Base: neither okay.png nor breturnhome.png appeared after %ds', _MANUAL_BATTLE_WAIT_SECONDS)
            self._bb_dismiss_okay_and_return_home(max_retries = 1)
            return None
        # Okay got clicked above — now wait for breturnhome.png (or a chest popup in its place).
        (rx, ry, return_home_template) = self._wait_for_bb_return_home(timeout = 15)
        if rx and return_home_template == 'chestclaim.png':
            logger.info('Builder Base: chestclaim.png (replacing return home); running chest flow')
            self.input.click(rx, ry, pause = 0.2)
            if self.stop_event.wait(0.35):
                return None
            self._tap_empty_until_chest_continue()
            return None
        if rx:
            self.input.click(rx, ry, pause = 0.2)
            return None
        logger.warning('Builder Base: breturnhome.png not found — retrying via normal dismiss flow')
        self._bb_dismiss_okay_and_return_home(max_retries = 1)

    def _bb_gold_prioritise_end_battle_and_return_home(self):
        '''Gold prioritise: wait for _BB_GOLD_PRIORITISE_MIN_STARS battle stars, then wait 12-15s,
redeploy everything once more, and let the battle end naturally. If the star threshold is never
reached, skip straight to the same natural-end wait instead of hunting for endbattle.png, which
may already be gone if the battle timer ran out while we were still polling for stars.'''
        start = time.time()
        timeout = 90
        stars_hit = False
        copter_last_click = 0
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return None
                continue
            self._update_config_size(frame)
            copter_last_click = self._bb_maybe_use_copter_ability(frame, copter_last_click)
            stars = self._bb_battle_star_count(frame)
            if stars >= _BB_GOLD_PRIORITISE_MIN_STARS:
                logger.info('Builder Base (gold): %d battle star(s) — waiting 12-15s then redeploying', stars)
                stars_hit = True
                break
            if self.stop_event.wait(0.5):
                return None
        if not stars_hit:
            logger.warning('Builder Base (gold): timed out waiting for %d+ %s — waiting for breturnhome.png instead', _BB_GOLD_PRIORITISE_MIN_STARS, _BB_BATTLE_STAR_TEMPLATE)
            return self._bb_wait_for_natural_end_and_return_home()
        if self.stop_event.wait(random.uniform(12, 15)):
            return None
        frame = self.window.screenshot()
        if frame is not None:
            self._update_config_size(frame)
            if not self._deploy_bb_baby_dragons(frame):
                logger.info('Builder Base (gold): nothing left to redeploy after 3-star')
        self._bb_wait_for_natural_end_and_return_home()

    
    def _bb_return_home_template_for_screen(self, width, height):
        '''Return (template name, scale_template) for Builder Base Return Home.'''
        (tw, th) = _BB_1080P_CAPTURE_SIZE
        tol = _BB_1080P_SIZE_TOLERANCE
        if abs(width - tw) <= tol and abs(height - th) <= tol:
            return (_BB_RETURN_HOME_TEMPLATE_1080P, False)
        return (_BB_RETURN_HOME_TEMPLATE, True)

    
    def _wait_for_bb_return_home(self, timeout = 15):
        '''Wait for BB Return Home, or a chest-reward popup (season reward / trophy milestone)
covering it. Picks 1080p-native template when capture is ~1920x1080.'''
        start = time.time()
        template_name = _BB_RETURN_HOME_TEMPLATE
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                continue
            self._update_config_size(frame)
            (h, w) = frame.shape[:2]
            (template_name, scale_template) = self._bb_return_home_template_for_screen(w, h)
            search_region = self._search_region_for_template(frame, template_name, None, None, 200)
            (x, y) = self.vision.find_template(frame, template_name, threshold = 0.8, region = search_region, scale_template = scale_template)
            if x:
                return (x, y, template_name)
            (cx, cy) = self.vision.find_template(frame, 'chestclaim.png')
            if cx:
                return (cx, cy, 'chestclaim.png')
            if self.stop_event.wait(0.5):
                return (None, None, template_name)
        return (None, None, template_name)

    
    def _bb_dismiss_okay_and_return_home(self, *, retry_battle_template = 'endbattle.png', max_retries = _BB_RETURN_HOME_END_BATTLE_RETRIES):
        '''Dismiss Okay, tap Return Home; retry battle-end + Okay if Return Home stays hidden.'''
        return_home_template = _BB_RETURN_HOME_TEMPLATE
        for attempt in range(max_retries + 1):
            self._check_stop()
            if attempt > 0:
                (bx, by) = self._wait_for_image(retry_battle_template, timeout = 3, error = False)
                if bx:
                    self.input.click(bx, by, pause = 0.15)
                else:
                    logger.debug('Builder Base: %s retry %d/%d — control not visible', retry_battle_template, attempt, max_retries)
            okay_timeout = 10 if attempt == 0 else 5
            (ox, oy) = self._wait_for_image('okay.png', timeout = okay_timeout, error = False)
            if ox:
                self.input.click(ox, oy, pause = 0.15)
            (rx, ry, return_home_template) = self._wait_for_bb_return_home(timeout = 15)
            if rx and return_home_template == 'chestclaim.png':
                logger.info('Builder Base: chestclaim.png (replacing return home); running chest flow')
                self.input.click(rx, ry, pause = 0.2)
                if self.stop_event.wait(0.35):
                    return None
                self._tap_empty_until_chest_continue()
                return None
            if rx:
                self.input.click(rx, ry, pause = 0.2)
                if attempt > 0:
                    logger.info('Builder Base: return home after %d %s retry(ies)', attempt, retry_battle_template)
                return None
            if not attempt < max_retries:
                continue
            logger.info('Builder Base: %s not found — retrying %s + okay (%d/%d)', return_home_template, retry_battle_template, attempt + 1, max_retries)
        logger.warning('Builder Base: %s not found after %d %s retries', return_home_template, max_retries, retry_battle_template)

    
    def _bb_surrender_and_return_home(self):
        '''Elixir prioritise: surrender right after deploy, then Okay + Return Home.'''
        (sx, sy) = self._wait_for_image('surrender.png', timeout = 10, error = False)
        if sx:
            self.input.click(sx, sy, pause = 0.15)
        else:
            logger.warning('Builder Base (elixir): surrender.png not found')
            return None
        self._bb_dismiss_okay_and_return_home(retry_battle_template = 'surrender.png')

    
    def _bb_search_clouds_visible(self, frame = None):
        '''True while the matchmaking cloud screen is up. Two independent markers:
``clouds.png`` (the cloud texture itself) and ``bbsearching.png`` (the magnifier badge),
so a shimmering/animating cloud layer alone can never hide the screen from us.'''
        if frame is None:
            frame = self.window.screenshot()
        if frame is None or frame.size == 0:
            return False
        self._update_config_size(frame)
        for template in _BB_SEARCH_CLOUD_TEMPLATES:
            (x, y) = self.vision.find_template(frame, template, threshold = 0.8)
            if x:
                return True
        return False

    
    def _bb_wait_for_search_clouds(self, village_name: str = 'Builder Base'):
        '''Hold the deploy sequence until the matchmaking search clouds are gone.

The clouds can linger ~20s (or never show at all), so this polls instead of sleeping a
fixed time and only releases once the screen has been cloud-free for
``_BB_CLOUD_CLEAR_SECONDS`` — a single faded frame cannot start a deploy or OCR reading.'''
        start = time.monotonic()
        clear_since = None
        announced = False
        while True:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                clear_since = None
                if self.stop_event.wait(0.5):
                    return None
                continue
            if self._bb_search_clouds_visible(frame):
                clear_since = None
                if not announced:
                    logger.info('%s: search clouds on screen — waiting for the opponent base', village_name)
                    announced = True
            else:
                now = time.monotonic()
                if clear_since is None:
                    clear_since = now
                elif now - clear_since >= _BB_CLOUD_CLEAR_SECONDS:
                    if announced:
                        logger.info('%s: search clouds cleared after %.1fs — continuing', village_name, now - start)
                    return None
            if self.stop_event.wait(0.4):
                return None

    
    def _bb_two_star_end_battle_and_return_home(self):
        '''Extras -> "2 Star": end the battle as soon as two stars show instead of playing
on to 6 stars / 200%. Clicks End Battle, then Okay + Return Home. A battle that already
finished (no End Battle button left) falls through to the natural-end flow.'''
        start = time.time()
        timeout = _MANUAL_BATTLE_WAIT_SECONDS
        stars_hit = False
        copter_last_click = 0
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return None
                continue
            self._update_config_size(frame)
            copter_last_click = self._bb_maybe_use_copter_ability(frame, copter_last_click)
            stars = self._bb_battle_star_count(frame)
            if stars >= _BB_TWO_STAR_THRESHOLD:
                logger.info('Builder Base (2 star mode): %d battle star(s) — ending the battle', stars)
                stars_hit = True
                break
            if self.stop_event.wait(0.5):
                return None
        if not stars_hit:
            logger.info('Builder Base (2 star mode): no %d-star read within %ds — letting the battle finish', _BB_TWO_STAR_THRESHOLD, timeout)
            return self._bb_wait_for_natural_end_and_return_home()
        frame = self.window.screenshot()
        end_region = VisionService.bottom_half_region(frame) if frame is not None else None
        (ex, ey) = self._wait_for_image('endbattle.png', timeout = 5, error = False, region = end_region)
        if not ex:
            logger.info('Builder Base (2 star mode): endbattle.png already gone — battle finished on its own')
            return self._bb_wait_for_natural_end_and_return_home()
        self.input.click(ex, ey, pause = 0.15)

        self._bb_dismiss_okay_and_return_home()

    
    def _bb_battle_star_count(self, frame):
        '''Count awarded Builder Base battle stars across the battle HUD.

The stars are not guaranteed to sit in the lower half at every resolution/UI layout, so
search the full battle frame and let non-overlapping template matches count the indicators.'''
        return len(VisionService.find_all_template_centers(
            frame, _BB_BATTLE_STAR_TEMPLATE, threshold = 0.8,
            region = VisionService.bottom_half_region(frame),
            max_matches = 3, suppress_pad_frac = 0.35))

    
    def _bb_build_panel_region(self, frame):
        '''ROI of the right-hand "Buildings & Heroes" panel (where the upgrade list lives).'''
        (h, w) = frame.shape[:2]
        x0 = int(w * 0.70)
        return (x0, 0, max(1, w - x0), h)

    
    @staticmethod
    def _bb_wall_action_region(frame):
        '''Centered bottom action bar, excluding Build-list prices and builder portraits.'''
        (h, w) = frame.shape[:2]
        return (0, int(h * 0.55), int(w * 0.70), int(h * 0.40))

    
    def _bb_find_wall_rows(self, frame):
        '''Every "Wall" row in the Build panel, top to bottom. White text first (brown rows),

then dark.'''
        region = self._bb_build_panel_region(frame)
        for white in (True, False):
            rows = VisionService.find_wall_row_centers_in_region_ocr(frame, region, white_text = white)
            if rows:
                return rows
        return []

    
    def _bb_find_wall_row(self, frame):
        '''Topmost "Wall" row in the Build panel, or ``None``.'''
        rows = self._bb_find_wall_rows(frame)
        return rows[0] if rows else None

    
    def _bb_wall_click_point(self, candidate):
        '''Click point for a Wall row that is already on screen, or ``None`` when the row is gone.

Returns the **freshest** read rather than insisting the list stands still: while the row was
re-read it could drift, the old confirmation returned False and the caller scrolled again —
which walked the list *past* the walls and left the batch clicking rows further down (or
nothing at all). As long as a Wall row is still in the panel, that row is the answer.'''
        tol = self.config.scale_scalar(_WALL_ROW_STABLE_TOL)
        best = candidate
        for _ in range(3):
            if self.stop_event.wait(0.2):
                return None
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            fresh = self._bb_find_wall_rows(frame)
            if not fresh:
                continue
            # Follow the row that is closest to where we last saw it, so a second wall group
            # sliding into view is never mistaken for the one we meant to click.
            best = min(fresh, key = (lambda r: abs(r[1] - candidate[1])))
            if abs(best[1] - candidate[1]) <= tol:
                return best
            candidate = best
        return best

    
    def _bb_panel_signature(self, frame):
        '''Cheap fingerprint of the Build-panel list, used to notice it stopped scrolling.'''
        (x, y, w, h) = self._bb_build_panel_region(frame)
        crop = frame[y:y + h, x:x + w]
        if crop.size == 0:
            return None
        return cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (48, 96), interpolation = cv2.INTER_AREA)

    
    def _bb_scroll_build_panel(self, frame):
        '''Wheel down inside the Build panel (the list scrolls on the right).'''
        (h, w) = frame.shape[:2]
        self.input.scroll(int(w * 0.86), int(h * 0.55), _BB_WALL_PANEL_WHEEL_CLICKS)

    
    def _should_upgrade_bb_walls(self):
        '''Whether a Builder Base wall pass is worth attempting. The Settings wall threshold
is a soft target here: Builder Gold / Builder Elixir is a different economy from Home
Village loot, and the Settings card documents that number for the Home Village flow. The
pass is attempted while the toggle is on because the batch proves its own affordability —
a red cost button stops the add loop, and a batch nothing can pay for is never confirmed.'''
        threshold = int(getattr(self, '_wall_upgrade_threshold', 0) or 0)
        if threshold <= 0:
            return True
        frame = self.window.screenshot()
        if frame is None:
            return False
        self._update_config_size(frame)
        triplet = VisionService.parse_hud_resources_triplet(VisionService.extract_top_right_hud_numbers(frame, panel_open = self._panel_docked(frame)))
        if triplet is None:
            # An unreadable HUD used to fail the pass silently — the most common reason the
            # toggle did nothing while the storages themselves were full.
            logger.info('Builder Base walls: HUD loot unreadable — attempting the pass anyway')
            return True
        (gold, elixir, _dark) = triplet
        if gold >= threshold or elixir >= threshold:
            logger.info('Builder Base walls: gold=%s elixir=%s reached threshold %s', gold, elixir, threshold)
            return True
        logger.info('Builder Base walls: gold=%s elixir=%s below the %s threshold — trying anyway (it only buys what it can pay for)', gold, elixir, threshold)
        return True

    
    def _maybe_upgrade_bb_walls(self, upgrade_walls):
        '''Builder Base wall upgrades between battles (Modes -> Upgrade walls). Rate-limited:
a pass costs a panel open/close plus OCR, and nothing here should ever add a pass while a
builder is mid-upgrade on the other side of the screen.'''
        if not upgrade_walls:
            return None
        now = time.monotonic()
        if now - getattr(self, '_bb_wall_last_scan', 0) < _BB_WALL_SCAN_INTERVAL_SECONDS:
            return None
        if not self._should_upgrade_bb_walls():
            self._bb_wall_last_scan = time.monotonic() - _BB_WALL_SCAN_INTERVAL_SECONDS + _BB_WALL_FAILED_RETRY_SECONDS
            return None
        cb = getattr(self, '_status_callback', None)
        if cb:
            cb('Upgrading Builder Base walls...')

        upgraded = False
        try:
            upgraded = self._upgrade_walls_from_build_panel(village = 'builder') is True
        except InterruptedError:
            raise
        except Exception:
            logger.warning('Builder Base walls: pass failed; continuing the farm loop', exc_info = True)
        try:
            self._bb_deselect_wall_ui()
            self._bb_close_build_panel()
        except InterruptedError:
            raise
        except Exception:
            logger.warning('Builder Base walls: cleanup failed; continuing the farm loop', exc_info = True)
        now = time.monotonic()
        # Successful batches are rate-limited; failed attempts retry sooner so a transient
        # OCR/template miss does not leave walls untouched for the full interval.
        self._bb_wall_last_scan = now if upgraded else now - _BB_WALL_SCAN_INTERVAL_SECONDS + _BB_WALL_FAILED_RETRY_SECONDS
        if upgraded:
            logger.info('Builder Base walls: batch completed')

    
    def _upgrade_walls_from_build_panel(self, village = 'builder'):
        '''New-UI wall upgrade, one algorithm for both villages: Build → scroll the
right-hand panel to Wall → Upgrade More → add walls while a currency can still pay →
confirm the batch → Okay.'''

        def _cost_pair(frame):
            '''Cost buttons + cost redness for this village's wall bar (bottom bar only, so the
panel rows' own cost icons can never be mistaken for the Upgrade buttons).'''
            # Builder Base reads the same bar through _bb_wall_prices_from_frame, which tries
            # the currency-icon anchors first and falls back to this reader.
            return VisionService.upgrade_cost_redness_by_resource_icons(frame, region = self._bb_wall_action_region(frame))

        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        # A previous failed pass can leave the single-wall "Upgrade to level N?" dialog
        # open on its own; its red X is the always-active dismiss, so clear it before the
        # Build button can be found underneath.
        (dx, dy) = self.vision.find_template(frame, 'bbdialogclose.png', threshold = 0.85)
        if dx:
            logger.info('Wall upgrade: closing a leftover upgrade dialog first')
            self.input.click(dx, dy, pause = 0.4, rand = False)
            if self.stop_event.wait(0.5):
                return None
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
        bot_roi = VisionService.bottom_half_region(frame)
        (bx, by) = self.vision.find_template(frame, 'buildbtn.png', threshold = 0.8, region = bot_roi)
        if not bx:
            # A previous interrupted pass may have left the Build panel open. In that case
            # verify its close control before treating the missing button as a skip.
            (cx, cy) = self.vision.find_template(frame, 'bbpanelclose.png', threshold = 0.8)
            if cx:
                self.input.click(cx, cy, pause = 0.4)
                if self.stop_event.wait(0.4):
                    return False
                frame = self.window.screenshot()
                if frame is None:
                    return False
                self._update_config_size(frame)
                bot_roi = VisionService.bottom_half_region(frame)
                (bx, by) = self.vision.find_template(frame, 'buildbtn.png', threshold = 0.8, region = bot_roi)
            if not bx:
                logger.info('Wall upgrade: Build button not found — skipping this pass')
                return False
        self.input.click(bx, by, pause = 0.5, rand = False)
        if self.stop_event.wait(0.5):
            return None
        # A Wall row that is already visible ends the search *before* any scrolling: the panel
        # lists several wall groups and the loop used to keep wheeling past the first one,
        # hunting for a "better" row that was never needed (and often ending at the list
        # bottom, on building rows, where the click selected the wrong thing).
        row = None
        scrolls = 0
        last_sig = None
        while True:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            rows = self._bb_find_wall_rows(frame)
            if rows:
                row = self._bb_wall_click_point(rows[0])
                if row:
                    if scrolls:
                        logger.info('Wall upgrade: Wall row found after %d panel scroll(s)', scrolls)
                    break
            if scrolls >= _BB_WALL_PANEL_SCROLL_STEPS:
                break
            sig = self._bb_panel_signature(frame)
            if sig is not None and last_sig is not None:
                # Nothing moved after the previous nudge: the list is at its end, so more
                # wheeling cannot reveal anything and only delays the skip.
                if float(np.mean(cv2.absdiff(sig, last_sig))) < 0.5:
                    logger.info('Wall upgrade: Build panel reached its end with no Wall row (after %d scroll(s))', scrolls)
                    break
            last_sig = sig
            self._bb_scroll_build_panel(frame)
            scrolls += 1
            if self.stop_event.wait(0.4):
                return None
        if not row:
            logger.info('Wall upgrade: no Wall row in the Build panel — skipping this pass')
            return False
        self.input.click(pause = 0.6, rand = False, *row)
        (umx, umy) = (None, None)
        frame = None
        for _ in range(12):
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            roi = self._bb_wall_action_region(frame)
            (umx, umy) = self.vision.find_template(frame, 'bbupgrademore.png', threshold = 0.8, region = roi)
            if not umx:
                (umx, umy) = self.vision.find_template(frame, 'upgrademore.png', threshold = 0.8, region = roi)
            if umx:
                break
            if self.stop_event.wait(0.5):
                return None
        if not umx:
            logger.info('Wall upgrade: Upgrade More never showed after the Wall row click — skipping this pass')
            return False
        self.input.click(umx, umy, pause = 0.4, rand = False)
        if village == 'builder':
            return self._bb_wall_batch_sequence()

        # Preserve the Home Village batch policy: stop when either resource can no longer pay,
        # then reduce the batch if needed and confirm through the existing Home Village flow.
        added = 0
        for _ in range(_WALL_BATCH_MAX_ADDS):
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            pair = _cost_pair(frame)
            if not (pair.gold.cost_roi_xywh or pair.elixir.cost_roi_xywh):
                logger.info('Wall upgrade: upgrade cost buttons not visible — stopping the batch')
                break
            affordable = (
                (pair.gold.cost_roi_xywh is not None and pair.gold.redness < 0.2)
                or (pair.elixir.cost_roi_xywh is not None and pair.elixir.redness < 0.2)
            )
            if not affordable:
                break
            roi = self._bb_wall_action_region(frame)
            (awx, awy) = VisionService.find_active_addwall(frame, region = roi)
            if not awx:
                break
            self.input.click(awx, awy, pause = 0.3, rand = False)
            added += 1
        if added == 0:
            self._deselect_wall_ui()
            return None
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        pair = _cost_pair(frame)
        (fh, fw) = frame.shape[:2]
        mid_roi = (fw // 4, fh // 2, fw // 2, fh - fh // 2)
        if pair.gold.redness >= 0.2 and pair.elixir.redness >= 0.2:
            (rwx, rwy) = VisionService.find_active_removewall(frame, region = mid_roi)
            if rwx:
                self.input.click(rwx, rwy, pause = 0.4, rand = False)
        elif added > 1 and pair.elixir.redness >= 0.2 and pair.gold.redness < 0.2 and pair.gold.cost_roi_xywh:
            (rwx, rwy) = VisionService.find_active_removewall(frame, region = mid_roi)
            if rwx:
                logger.info('Wall upgrade: gold is the payer — removing one wall to keep the attack entry fee')
                self.input.click(rwx, rwy, pause = 0.4, rand = False)
        logger.info('Wall upgrade: %d wall(s) added to batch', added)
        self._upgrade_walls_pick_resource_and_okay()
        return True

    
    _WallPrices = collections.namedtuple('_WallPrices', 'found_both both_red gold_center gold_red elixir_center elixir_red')

    
    def _bb_wall_prices_from_frame(self, frame):
        '''Both Upgrade prices of the wall bar, read exactly the way the Home Village batch

does, with a second reader behind the first.

Primary: the two currency icons in the top-right corner of each ``Upgrade`` button — a
fixed anchor whose pixels never change, with the price digits counted for red just left of
it. Fallback: the shipped ``multiupgrade.png`` anchors with the red counted in the box above
each one (the reader the Home Village flow uses). Either way no digits enter a template, so
a price change can never turn a match into a miss.'''
        region = self._bb_wall_action_region(frame)
        pair = VisionService.bb_wall_payment_buttons(frame, gold_template = _BB_WALL_GOLD_TEMPLATE, elixir_template = _BB_WALL_ELIXIR_TEMPLATE, match_threshold = _BB_WALL_ANCHOR_THRESHOLD, region = region)
        if pair.found_both:
            return self._WallPrices(True, pair.both_red, pair.gold.center, pair.gold.price_red, pair.elixir.center, pair.elixir.price_red)
        multi = VisionService.upgrade_cost_redness_by_resource_icons(frame, region = region)
        (gold, elixir) = (multi.gold, multi.elixir)
        found = bool(gold.found and elixir.found and gold.center and elixir.center)
        return self._WallPrices(found, bool(gold.redness >= _WALL_PRICE_RED_SHARE and elixir.redness >= _WALL_PRICE_RED_SHARE), gold.center, bool(gold.redness >= _WALL_PRICE_RED_SHARE), elixir.center, bool(elixir.redness >= _WALL_PRICE_RED_SHARE))

    
    def _bb_wall_read_prices(self, attempts = 3):
        '''Fresh frame plus both wall-bar prices, retried while the bar redraws.'''
        frame = None
        prices = None
        tries = max(1, int(attempts))
        for attempt in range(tries):
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(_BB_WALL_PRICE_READ_SETTLE_SECONDS):
                    return (None, None)
                continue
            self._update_config_size(frame)
            prices = self._bb_wall_prices_from_frame(frame)
            if prices.found_both:
                return (frame, prices)
            if attempt < tries - 1 and self.stop_event.wait(_BB_WALL_PRICE_READ_SETTLE_SECONDS):
                return (None, None)
        return (frame, prices)

    
    def _bb_wall_batch_sequence(self, target_walls = 5):
        """Builder Base wall batch: up to 5 walls per pass."""
        added = 0
        (frame, prices) = self._bb_wall_read_prices(attempts = 6)
        if frame is None or prices is None or not prices.found_both:
            logger.warning('Builder Base walls: the two Upgrade prices were not found in the wall bar - stopping without purchase')
            return False

        # 1 wall is already selected upon entering Upgrade More; add up to target_walls total
        adds_needed = max(0, target_walls - 1)
        for i in range(adds_needed):
            self._check_stop()
            if prices.both_red:
                break
            add = self._bb_wall_add_center(frame)
            if not add:
                logger.warning('Builder Base walls: Add Wall button not found')
                break
            self.input.click(*add, pause = _BB_WALL_ADD_CLICK_SECONDS, rand = False)
            added += 1
            (frame, prices) = self._bb_wall_read_prices()

        # If both prices are red, remove walls until affordable
        while prices and prices.both_red and added > 0:
            self._check_stop()
            logger.info('Builder Base walls: both prices red; removing one wall')
            remove = self._bb_wall_remove_center(frame)
            if not remove:
                break
            self.input.click(*remove, pause = _BB_WALL_REMOVE_CLICK_SECONDS, rand = False)
            added -= 1
            (frame, prices) = self._bb_wall_read_prices()

        if frame is None or prices is None or not prices.found_both:
            logger.warning('Builder Base walls: prices unreadable - stopping without purchase')
            return False

        if prices.both_red:
            logger.warning('Builder Base walls: cannot afford wall upgrade - stopping without purchase')
            return False

        total_walls = 1 + added
        logger.info('Builder Base walls: upgrading batch of %d wall(s)', total_walls)
        return self._bb_wall_pay_and_okay(prices)

    
    def _bb_wall_add_center(self, frame):
        '''Click point of the enabled "Add Wall" (+1) button, or ``None``.

The new-UI bar hides the dedicated template on some layouts, so the lime ``+1``
control (template plus lime color verification) is the dependable fallback.'''
        region = self._bb_wall_action_region(frame)
        add = VisionService.wall_bar_button(frame, _BB_WALL_ADD_TEMPLATE, match_threshold = _BB_WALL_ANCHOR_THRESHOLD, region = region)
        if add.found and add.center:
            return add.center
        # Fallback for a shipment without the new-UI crop: the lime "+1" control.
        (ax, ay) = VisionService.find_active_addwall(frame, region = region)
        return (ax, ay) if ax else None

    
    def _bb_wall_remove_center(self, frame):
        '''Click point of the "Remove Wall" button, or ``None``.

Template first; when no crop exists yet, fall back to the bar's own fixed grid:
Remove Wall sits a constant share of the screen width left of the lime Add Wall
control on the same row (measured live at 1288px: 607 -> 398).'''
        region = self._bb_wall_action_region(frame)
        for template in (_BB_WALL_REMOVE_TEMPLATE, 'removewall.png'):
            remove = VisionService.wall_bar_button(frame, template, match_threshold = _BB_WALL_ANCHOR_THRESHOLD, region = region)
            if remove.found and remove.center:
                return remove.center
        add = self._bb_wall_add_center(frame)
        if not add:
            return None
        (h, w) = frame.shape[:2]
        rx = int(add[0] - w * _BB_WALL_REMOVE_OFFSET_FRAC)
        if rx < 0:
            return None
        return (rx, int(add[1]))

    
    def _bb_wall_pay_and_okay(self, prices):
        '''Click the Upgrade button whose price is not red, then Okay the "Upgrade Walls" dialog.'''
        picked = None
        for (center, red) in ((prices.elixir_center, prices.elixir_red), (prices.gold_center, prices.gold_red)):
            if center and not red:
                picked = center
                break
        if picked is None:
            logger.info('Builder Base walls: neither price is payable — not opening a purchase')
            return False
        logger.info('Builder Base walls: paying with %s', 'Builder Elixir' if picked == prices.elixir_center else 'Builder Gold')
        self.input.click(*picked, pause = _BB_WALL_UPGRADE_CLICK_SECONDS, rand = False)
        (okx, oky) = self._wait_for_image('wallokay.png', timeout = _BB_WALL_OKAY_TIMEOUT_SECONDS, error = False)
        if not okx:
            logger.warning('Builder Base walls: Okay not found after Upgrade — leaving the dialog for recovery')
            return False
        self.input.click(okx, oky, pause = 0.4, rand = False)
        if self.stop_event.wait(0.5):
            return None
        # A red total keeps Okay disabled and the dialog open; do not let that window
        # outlive the pass — close it via its red X and report the batch as not paid.
        frame = self.window.screenshot()
        residue = False
        if frame is not None:
            self._update_config_size(frame)
            (rx, _) = self.vision.find_template(frame, 'wallokay.png', threshold = 0.68)
            residue = bool(rx)
        if residue:
            logger.info('Builder Base walls: Okay left the dialog open — closing via red X')
            (cx, cy) = self.vision.find_template(frame, 'bbdialogclose.png', threshold = 0.85)
            if cx:
                self.input.click(cx, cy, pause = 0.4, rand = False)
        else:
            logger.info('Builder Base walls: batch confirmed')
        return not residue

    
    def _bb_deselect_wall_ui(self):
        '''Dismiss any open dialog first, then tap ground to close the wall selection.

The red ``bbdialogclose.png`` X is checked first: a dialog's Okay can be disabled (a red
total a batch cannot pay for) while its X always works, and the level-9 confirm window the
old hammer clicks used to leave behind has no Okay at all.'''
        for template in ('bbdialogclose.png', 'wallokay.png', 'okay.png', 'exit.png'):
            frame = self.window.screenshot()
            if frame is None:
                break
            self._update_config_size(frame)
            threshold = 0.85 if template == 'bbdialogclose.png' else 0.68
            (x, y) = self.vision.find_template(frame, template, threshold = threshold)
            if not x:
                continue
            self.input.click(x, y, pause = 0.4, rand = False)
            if self.stop_event.wait(0.5):
                return None
        self.input.click(pause = 0.25, *self.config.get_point('empty'))

    
    def _bb_close_build_panel(self):
        '''Close the Build panel by its red X and make sure the home bar is usable again.'''
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        (cx, cy) = self.vision.find_template(frame, 'bbpanelclose.png', threshold = 0.8)
        if not cx:
            logger.info('Wall upgrade: Build panel close control not visible')
            return None
        self.input.click(cx, cy, pause = 0.4)
        if self.stop_event.wait(0.45):
            return None
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        (ax, ay) = self.vision.find_template(frame, 'attack.png', region = VisionService.bottom_half_region(frame))
        if not ax:
            logger.info('Wall upgrade: home bar missing after closing the panel — running recovery')
            self._recover_stuck_screen()

    
    def _find_match_and_attack(self, method_id, ranked_fill = False):
        """One attack cycle. Returns ``'ranked_limit'`` (stop now), ``'troop'`` (troops missing — retry later), or None."""
        battle_template = 'rankedbattle.png' if ranked_fill else 'farmbattle.png'
        (fx, fy) = self._find_template_once(battle_template)
        if fx:
            # A previous cycle left the battle-selection screen open (stolen tap / derail) —
            # use it directly instead of hunting for the home Attack button it covers.
            logger.info('Attack: battle-selection screen already open — continuing from Find a Match')
        else:
            (ax, ay) = self._wait_for_attack_with_nudge()
            if not ax:
                logger.warning('Attack: attack.png not found — running recovery')
                self._recover_stuck_screen()
                return None
            # Home screen confirmed (Attack visible) → the HUD is readable: record the
            # pre-attack loot baseline / accumulate the previous battle's gains.
            # [recovered: this call existed only in the wall path — with walls off the
            # loot tracker never ran (live repro: 3 battles, session totals stuck at 0)]
            self._loot_snapshot_before_attack()
            self.input.click(ax, ay, pause = 0.1)
            (fx, fy) = self._wait_for_image(battle_template)
        if not fx:
            if ranked_fill:
                msg = 'Ranked battle button not found — daily limit may be reached. Stopping.'
                logger.info(msg)
                cb = getattr(self, '_status_callback', None)
                if cb:
                    cb(msg)
                return 'ranked_limit'
            return None
        self.input.click(fx, fy, pause = 0.1)
        # A single tap here is unreliable: event popups (Card Hunt etc.) or a still-animating
        # screen can eat it. Verify the army screen (attack2) actually appeared; while the
        # Find a Match button is still on screen, the tap was stolen — tap again (the first
        # stolen tap also closes whatever popup ate it).
        (a2x, a2y) = self._wait_for_image('attack2.png', timeout = 5, error = False)
        for _ in range(3):
            if a2x:
                break
            (rfx, rfy) = self._find_template_once(battle_template)
            if not rfx:
                break
            logger.info('%s still on screen — click was eaten (popup?); re-clicking', battle_template)
            self.input.click(rfx, rfy, pause = 0.1)
            (a2x, a2y) = self._wait_for_image('attack2.png', timeout = 5, error = False)
        if not a2x:
            (a2x, a2y) = self._wait_for_image('attack2.png')
        if method_id == 3 and not self._ensure_valkyrie_army_from_recipes():
            # Attack anyway with whatever is trained — a partial Valkyrie army still loots, and
            # bailing out here would leave the Find a Match screen open with nothing to recover it.
            msg = 'Valkyrie army not confirmed (slow screen or missing saved recipe) — attacking with current army'
            logger.warning(msg)
            cb = getattr(self, '_status_callback', None)
            if cb:
                cb(msg)
        if a2x:
            self.input.click(a2x, a2y, pause = 0.1)
            if ranked_fill:
                (rx, ry) = self._wait_for_image('rankedattackconfirm.png', timeout = 10)
                if not rx:
                    logger.warning('rankedattackconfirm.png not found after attack2.png')
                else:
                    self.input.click(rx, ry, pause = 0.1)
        skips = 0
        max_skips = getattr(self, '_max_next_skips', 50)
        cb = getattr(self, '_status_callback', None)
        has_loot_filter = not ranked_fill and (getattr(self, '_min_gold', 0) > 0 or getattr(self, '_min_elixir', 0) > 0 or getattr(self, '_min_dark_elixir', 0) > 0)

        # Wait for matchmaking clouds after confirming attack
        self._bb_wait_for_search_clouds(village_name = 'Home Village')

        while True:
            self._wait_for_any_image(('surrender.png', 'endbattle.png'), timeout = 30)
            # Ensure any lingering or transition clouds are completely gone before OCR reads the HUD
            self._bb_wait_for_search_clouds(village_name = 'Home Village')
            frame = self.window.screenshot()
            if frame is None:
                return None
            self._update_config_size(frame)
            if self.stop_event.wait(0.3):
                return None
            frame = self.window.screenshot()
            if frame is None:
                return None
            
            gold, elixir, de = self.loot_ocr.read_battle_loot(frame)
            logger.info(f"Raid loot found: Gold={gold:,}, Elixir={elixir:,}, DE={de:,} (Target: G>={getattr(self, '_min_gold', 0):,}, E>={getattr(self, '_min_elixir', 0):,}, DE>={getattr(self, '_min_dark_elixir', 0):,})")
            if cb:
                cb(f"Loot: G {gold:,} | E {elixir:,} | DE {de:,}")
            
            if not has_loot_filter:
                break
            
            meets_gold = (gold >= self._min_gold) if self._min_gold > 0 else False
            meets_elixir = (elixir >= self._min_elixir) if self._min_elixir > 0 else False
            meets_de = (de >= self._min_dark_elixir) if self._min_dark_elixir > 0 else False
            huge_loot = (gold >= 1500000 or elixir >= 1500000)

            if getattr(self, '_loot_match_condition', 'any') == 'all':
                meets_loot = (self._min_gold <= 0 or meets_gold) and (self._min_elixir <= 0 or meets_elixir) and (self._min_dark_elixir <= 0 or meets_de)
            else:
                meets_loot = meets_gold or meets_elixir or meets_de
            
            if meets_loot or huge_loot:
                logger.info(f"Target accepted! Gold={gold:,}, Elixir={elixir:,}, DE={de:,}")
                if cb:
                    cb(f"Target found: G {gold:,} | E {elixir:,}")
                break
            
            skips += 1
            if skips >= max_skips:
                logger.warning(f"Reached max Next skips limit ({max_skips}). Attacking current base.")
                if cb:
                    cb(f"Max skips ({skips}) reached -> attacking")
                break
            
            logger.info(f"Loot below threshold. Clicking Next... (Skip #{skips}/{max_skips})")
            if cb:
                cb(f"Skipping base ({skips}/{max_skips})...")
            
            (h_f, w_f) = frame.shape[:2]
            next_x = int(0.9135 * w_f)
            next_y = int(0.7185 * h_f)
            self.input.click(next_x, next_y, pause = 0.2)
            
            if self.stop_event.wait(0.8):
                return None
            # Wait for search clouds generated by Next skip to clear before looping
            self._bb_wait_for_search_clouds(village_name = 'Home Village')

        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        (h, w) = frame.shape[:2]
        cy = h // 2
        cx = w // 2
        if _BB_HUMAN_CAMERA:
            if not self._bb_human_camera_nudge(frame):
                return None
        else:
            self.input.move(cx, cy)
            if self.stop_event.wait(0.05):
                return None
            self.input.scroll(cx, cy, 4)
        frame = self.window.screenshot()
        if frame is None:
            return None
        self._update_config_size(frame)
        strategy = self._get_strategy(method_id)
        strategy.event_handler = self._battle_rewards
        self._is_deploying = True
        try:
            result = strategy.execute(frame, self.stop_event)
        finally:
            self._is_deploying = False
            self.reset_inactivity_timer()
        self._wait_for_battle_end(is_sneaky = method_id == 1)
        return 'troop' if result is False else None

    
    def _install_spell_alias(self):
        '''Extras -> "Rage Spell" toggle. The strategies look the spell up as earthquake.png; when rage is on,
every lookup of earthquake.png is answered with rage.png instead. Read live, so the toggle applies per run.'''
        if getattr(self, '_spell_alias_installed', False):
            return
        orig = self.vision.find_template
        bot = self

        def aliased(frame, template_name, *args, **kwargs):
            if template_name == 'earthquake.png' and getattr(bot, '_rage_spell', False):
                if get_template_path('rage.png').is_file():
                    template_name = 'rage.png'
                elif not getattr(bot, '_rage_missing_warned', False):
                    bot._rage_missing_warned = True
                    logger.warning('Rage Spell is ON but templates/<aspect>/rage.png does not exist - using earthquake.png. Run: python tools/make_template.py rage.png')
            return orig(frame, template_name, *args, **kwargs)

        self.vision.find_template = aliased
        self._spell_alias_installed = True

    def _get_strategy(self, method_id):
        rage = getattr(self, '_rage_spell', False)
        self._install_spell_alias()
        cb = getattr(self, '_status_callback', None)
        eq = getattr(self, '_earthquake_method', EARTHQUAKE_METHOD_CURVE)
        secondary = getattr(self, '_secondary_troop_template', '')
        secondary_count = getattr(self, '_secondary_troop_count', 12)
        custom_data = getattr(self, '_custom_strategy_data', None)

        if custom_data:
            from app.core.strategies import CustomArmyStrategy
            return CustomArmyStrategy(self.input, self.vision, self.config, self.stop_event, custom_data, status_callback = cb, earthquake_method = eq, rage_spell = getattr(self, '_rage_spell', False))

        if method_id == 1:
            return TroopSpamStrategy(self.input, self.vision, self.config, self.stop_event, 'sneaky', 15, status_callback = cb, earthquake_method = eq, secondary_template = secondary, secondary_count = secondary_count, rage_spell = rage)
        if method_id == 2:
            return TroopSpamStrategy(self.input, self.vision, self.config, self.stop_event, 'superminion', 3.1, status_callback = cb, earthquake_method = eq, secondary_template = secondary, secondary_count = secondary_count, rage_spell = rage)
        if method_id == 3:
            return TroopSpamStrategy(self.input, self.vision, self.config, self.stop_event, 'valkyrie', 5.5, status_callback = cb, earthquake_method = eq, secondary_template = secondary, secondary_count = secondary_count, rage_spell = rage)
        if method_id == 4:
            return EdragStrategy(self.input, self.vision, self.config, self.stop_event, status_callback = cb, earthquake_method = eq, secondary_template = secondary, secondary_count = secondary_count, rage_spell = rage)
        return TroopSpamStrategy(self.input, self.vision, self.config, self.stop_event, 'sneaky', 15, status_callback = cb, earthquake_method = eq, secondary_template = secondary, secondary_count = secondary_count, rage_spell = rage)

    
    def _wait_for_battle_over(self, timeout = _MANUAL_BATTLE_WAIT_SECONDS):
        '''Hands-off wait: no End Battle / Surrender taps. Returns once neither button has been on screen for ~1.5s.'''
        start = time.time()
        gone_since = None
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return None
                continue
            self._update_config_size(frame)
            (ex, ey) = self.vision.find_template(frame, 'endbattle.png')
            (sx, sy) = self.vision.find_template(frame, 'surrender.png')
            if ex or sx:
                gone_since = None
            elif gone_since is None:
                gone_since = time.time()
            elif time.time() - gone_since >= 1.5:
                return None
            if self.stop_event.wait(1):
                return None
        logger.warning('Battle still live after %ds — giving up the wait (auto-end is off)', timeout)

    
    def _wait_for_battle_end(self, is_sneaky):
        # Extras -> "3 Star" toggle: ON = hands-off, let the battle finish (3 stars / timer);
        # OFF = the original flow below (ends the battle itself after the loot delay).
        if getattr(self, '_three_star_mode', True):
            self._wait_for_battle_over()
            return None
        if is_sneaky:
            if self.stop_event.wait(3):
                return None
            (sx, sy) = self._wait_for_image('surrender.png', timeout = 2, error = False)
            if sx:
                self.input.click(sx, sy, pause = 0.1)
                return None
            (bx, by) = self._wait_for_image('endbattle.png', timeout = 2, error = False)
            if bx:
                self.input.click(bx, by, pause = 0.1)
                return None
            return None

        delay = getattr(self, '_battle_end_delay', 20)
        (bx, by) = self._wait_for_image('endbattle.png', timeout = 60, error = False)
        if bx:
            if delay > 0:
                logger.info(f"1 Star / End Battle active. Waiting {delay}s for troops to clean up additional loot...")
                cb = getattr(self, '_status_callback', None)
                if cb:
                    cb(f"1 Star reached - looting for {delay}s...")
                
                start_delay = time.time()
                while time.time() - start_delay < delay:
                    if self.stop_event.wait(1.0):
                        return None
                    frame = self.window.screenshot()
                    if frame is not None:
                        (ox, oy) = self.vision.find_template(frame, 'okay.png')
                        if ox:
                            logger.info("Battle naturally finished during post-1-star delay.")
                            return None

                frame = self.window.screenshot()
                if frame is not None:
                    (nbx, nby) = self.vision.find_template(frame, 'endbattle.png')
                    if nbx:
                        bx, by = nbx, nby

            self.input.click(bx, by, pause = 0.1)
            return None

        (sx, sy) = self._wait_for_image('surrender.png', timeout = 2, error = False)
        if sx:
            self.input.click(sx, sy, pause = 0.1)
            return None

    
    def _return_home(self):
        '''Dismiss Okay if present, then wait for ``returnhome.png`` (+ ``returnhome2.png`` on 16:10) or ``chestclaim.png`` (mutually exclusive).'''
        (ox, oy) = self._wait_for_image('okay.png', timeout = 10)
        if ox:
            self.input.click(ox, oy, pause = 0.1)
        (kind, hx, hy) = self._wait_for_return_home_or_chest_claim(timeout = 10)
        if kind == 'return' and hx:
            self.input.click(hx, hy, pause = 0.1)
            return ox is not None
        if kind == 'chest' and hx:
            logger.info('Post-battle UI: chestclaim.png (replacing return home); running chest flow')
            self.input.click(hx, hy, pause = 0.2)
            if self.stop_event.wait(0.35):
                return ox is not None
            self._tap_empty_until_chest_continue()
        return ox is not None

    
    def _wait_for_return_home_or_chest_claim(self, timeout = 10):
        '''
Poll one frame for ``returnhome.png`` (+ ``returnhome2.png`` on 16:10 only) then ``chestclaim.png`` (only one should match).
Returns (``"return"`` | ``"chest"``, x, y) or (None, None, None) on timeout.
'''
        start = time.time()
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return (None, None, None)
                continue
            self._update_config_size(frame)
            if self._battle_rewards.handle(frame):
                continue
            (rx, ry) = (None, None)
            returnhome_tpls = ('returnhome.png', 'returnhome2.png') if self.config.aspect_key == ASPECT_16_10 else ('returnhome.png',)
            for tpl in returnhome_tpls:
                (rx, ry) = self.vision.find_template(frame, tpl)
                if rx:
                    break  # [recovered: decompiler dropped this break, letting the last template overwrite a match]
            if rx:
                return ('return', rx, ry)
            (cx, cy) = self.vision.find_template(frame, 'chestclaim.png')
            if cx:
                return ('chest', cx, cy)
            if self.stop_event.wait(0.25):
                return (None, None, None)
            if time.time() - start < timeout:
                continue
        logger.warning('Timeout waiting for returnhome.png / returnhome2.png (16:10) or chestclaim.png')
        return (None, None, None)

    
    def _random_point_chest_tap_through(self):
        '''Random point near center-right of the capture for chest tap-through (±85 px from anchor).'''
        (w, h) = (self.config.width, self.config.height)  # [recovered: pycdc reversed STORE_FAST_STORE_FAST pairs]
        if w <= 1 or h <= 1:
            (w, h) = (self.config.ref_width, self.config.ref_height)
        cx = int(w * 0.75)
        cy = h // 2
        j = 85
        return (max(0, min(w - 1, cx + random.randint(-j, j))), max(0, min(h - 1, cy + random.randint(-j, j))))

    
    def _tap_empty_until_chest_continue(self):
        '''After ``chestclaim`` was clicked: tap center-right (±85px) until ``chestcontinue.png``, then click it (home).'''
        CHEST_TAP_TIMEOUT = 120
        deadline = time.time() + CHEST_TAP_TIMEOUT
        while time.time() < deadline:
            self._check_stop()
            (nx, ny) = self._random_point_chest_tap_through()
            self.input.click_at(nx, ny, rand = False)
            t0 = time.time()
            if self.stop_event.wait(0.15):
                return None
            frame2 = self.window.screenshot()
            if not frame2 is None:
                self._update_config_size(frame2)
                (tx, ty) = self.vision.find_template(frame2, 'chestcontinue.png')
                if tx:
                    logger.info('Chest reward: chestcontinue.png found; clicking (expect home village)')
                    self.input.click(tx, ty, pause = 0.25)
                    return None
            elapsed = time.time() - t0
            to_wait = max(0.05, 0.5 - elapsed)
            if self.stop_event.wait(to_wait):
                return None
        logger.warning(f'''chestcontinue.png not seen within {int(CHEST_TAP_TIMEOUT)}s after chest claim; continuing bot loop''')  # [recovered: decompiler misnested this inside the loop, ending the tap-through after one tap]
        return None

    
    def _is_star_bonus_claimed(self):
        '''True if neither emptystar nor glowstar matches strongly (bonus claimed / not shown).'''
        frame = self.window.screenshot()
        if frame is None:
            return False
        self._update_config_size(frame)
        for template in ('emptystar.png', 'glowstar.png'):
            (_, _, confidence) = self.vision.find_template_with_confidence(frame, template, threshold = 0)  # [recovered + verified against original bytecode]
            if confidence >= _STAR_BONUS_THRESHOLD:
                return False
        return True

    
    def _is_bb_star_bonus_finished(self):
        '''True when ``bstar.png`` is not visible in the bottom half (BB star bonus attacks done).'''
        frame = self.window.screenshot()
        if frame is None:
            return False
        self._update_config_size(frame)
        bot_roi = VisionService.bottom_half_region(frame)
        (_, _, confidence) = self.vision.find_template_with_confidence(frame, _BB_STAR_BONUS_TEMPLATE, threshold = 0.0, region = bot_roi)  # [recovered + verified against original bytecode]
        return confidence < _STAR_BONUS_THRESHOLD

    
    def _home_screen_recovery(self):
        '''Ensures we are back at home screen. Escapes popups, stray screens, live battles, and end screens.'''
        next_capital_scan = 0.0
        for _ in range(20):
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(1):
                    return None
                continue
            self._update_config_size(frame)
            if self._battle_rewards.handle(frame):
                continue
            if self._dismiss_okay_or_exit_on_frame(frame):
                if self.stop_event.wait(0.3):
                    return None
                continue
            # Home check FIRST and before any OCR: this is the common case after
            # Return Home was just clicked, and every template/OCR scan below only
            # wasted time until the screen finished fading in.
            (hx, hy) = self.vision.find_template(frame, 'attack.png', region = VisionService.bottom_half_region(frame))
            if hx or self._home_village_dark_elixir_visible(frame):
                self._reload_first_seen = None
                return None
            now = time.monotonic()
            if now >= next_capital_scan:
                next_capital_scan = now + 1.5
                (chx, chy) = self._find_capital_return_home_button(frame)
                if chx:
                    logger.info('Recovery: Capital screen detected â€” clicking Return Home')
                    self.input.click(chx, chy, pause = 0.3)
                    if self.stop_event.wait(0.5):
                        return None
                    continue
            (sx, sy) = self.vision.find_template(frame, 'surrender.png')
            if sx:
                logger.info('Recovery: live battle — surrendering to get home')
                self.input.click(sx, sy, pause = 0.3)
                if self.stop_event.wait(0.5):
                    return None
                continue
            (rx, ry) = self.vision.find_template(frame, 'returnhome.png')
            if rx:
                logger.info('Recovery: clicking Return Home')
                self.input.click(rx, ry, pause = 0.3)
                if self.stop_event.wait(0.5):
                    return None
                continue
            if get_template_path('reload.png').exists():
                (lx, ly) = self.vision.find_template(frame, 'reload.png')
                if lx:
                    now = time.monotonic()
                    first = getattr(self, '_reload_first_seen', None)
                    if first is None:
                        self._reload_first_seen = now
                        logger.warning('Recovery: connection-lost dialog detected — waiting %ds before reloading (another device may be using the account)', _RELOAD_GRACE_SECONDS)
                    elif now - first >= _RELOAD_GRACE_SECONDS:
                        logger.warning('Recovery: connection-lost dialog persisted — clicking RELOAD')
                        self.input.click(lx, ly, pause = 1.0)
                        self._reload_first_seen = None
                        if self.stop_event.wait(10):
                            return None
                    if self.stop_event.wait(2):
                        return None
                    continue
            if not self.stop_event.wait(0.4):
                continue
        return None

    def _find_capital_return_home_button(self, frame):
        """Locate Capital's distinct lower-left Return Home button from its text."""
        if frame is None or frame.size == 0:
            return (None, None)
        h, w = frame.shape[:2]
        region = (0, int(h * 0.72), max(1, int(w * 0.19)), max(1, int(h * 0.28)))
        words = self.vision.find_words_ocr(
            frame,
            region=region,
            min_confidence=20,
            preprocess=True,
            white_text=False,
            tesseract_config='--psm 11'
        )
        return_words = [word for word in words if 'return' in word.text.lower()]
        home_words = [word for word in words if 'home' in word.text.lower()]
        best = None
        best_distance = float('inf')
        max_line_gap = max(20, int(h * 0.11))
        max_word_gap = max(30, int(w * 0.12))
        for return_word in return_words:
            for home_word in home_words:
                dx = abs(return_word.center[0] - home_word.center[0])
                dy = abs(return_word.center[1] - home_word.center[1])
                if dx > max_word_gap or dy > max_line_gap:
                    continue
                distance = dx + dy
                if distance < best_distance:
                    best = (return_word, home_word)
                    best_distance = distance
        if best is None:
            return (None, None)
        first, second = best
        x = (first.center[0] + second.center[0]) // 2
        y = (first.center[1] + second.center[1]) // 2
        return (x, y)

    
    def _switch_account_and_load_home(self, username):
        '''Open Settings → Change user, OCR-click username, wait for home. Raises on failure.'''
        cb = getattr(self, '_status_callback', None)
        msg = f'''Multi-run: switching to {username!r}'''
        logger.info(msg)
        if cb:
            cb(msg)
        (stx, sty) = self._wait_for_image('settings.png')
        if not stx:
            raise RuntimeError('Multi-run: settings button not found')
        self.input.click(stx, sty, pause = 0.25)
        (cux, cuy) = self._wait_for_image('changeuser.png')
        if not cux:
            raise RuntimeError('Multi-run: change user button not found')
        self.input.click(cux, cuy, pause = 1)
        (ucx, ucy) = self._wait_for_player_name(username, timeout = 25, min_confidence = 70, tesseract_config = '--psm 11', match_alnum_only = True, fuzzy_min_ratio = 0.8, white_text = True)
        if not ucx:
            err = f'''Multi-run: could not find username "{username}" on screen (OCR)'''
            logger.error(err)
            if cb:
                cb(err)
            raise RuntimeError(err)
        self.input.click(ucx, ucy, pause = 0.2)
        if self.stop_event.wait(1):
            self._check_stop()
        (ax, ay) = self._wake_home_and_wait_for_attack(timeout = 30)
        if not ax:
            err = f'''Multi-run: Home Village not ready after loading {username!r} (builder.png|gbuilder.png / attack.png timeout after login / leaving Builder Base)'''
            logger.error(err)
            if cb:
                cb(err)
            raise RuntimeError(err)
        self._loot_prev_resources = None

    
    def _wake_home_and_wait_for_attack(self, timeout = 30):
        '''
After switching accounts: dismiss idle UI, then poll the **top half** for village type
(``mbuilder.png`` = Builder Base; ``builder.png`` or ``gbuilder.png`` = Home Village). If Builder Base,
leave via :meth:`_leave_builder_base_with_nboat`. When Home Village is detected, return
``attack.png`` coordinates from the **bottom half** (battle bar) once visible — same
template as :meth:`_find_match_and_attack` uses to start battles.
Each iteration dismisses ``okay.png`` / ``exit.png`` if present, then village / attack logic; else nudge.
'''
        frame = self.window.screenshot()
        self._update_config_size(frame)
        empty_pt = self.config.get_point('empty')
        self.input.click(pause = 0.2, *empty_pt)
        self.input.scroll(*self._scroll_point(), 20)
        delay = random.uniform(0.1, 0.3)
        if self.stop_event.wait(delay):
            return (None, None)
        start = time.time()
        next_capital_scan = 0.0
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if not frame is None:
                self._update_config_size(frame)
                if self._dismiss_okay_or_exit_on_frame(frame):
                    if self.stop_event.wait(0.25):
                        return (None, None)
                    continue
                now = time.monotonic()
                if now >= next_capital_scan:
                    next_capital_scan = now + 1.5
                    (chx, chy) = self._find_capital_return_home_button(frame)
                    if chx:
                        logger.info('Account load: Capital screen detected â€” clicking Return Home')
                        self.input.click(chx, chy, pause = 0.3)
                        if self.stop_event.wait(0.5):
                            return (None, None)
                        continue
                top_roi = None  # builder portrait moved to the bottom-right in the new UI — search the whole frame
                (mx, my) = self.vision.find_template(frame, 'mbuilder.png', region = top_roi)
                if mx:
                    logger.info('Account loaded in Builder Base (mbuilder.png); leaving to Home Village')
                    cb = getattr(self, '_status_callback', None)
                    if cb:
                        cb('Multi-run: Builder Base on login — leaving (nboat)')
                    self._leave_builder_base_with_nboat(settle_before_drag = False)
                    if self.stop_event.wait(1):
                        return (None, None)
                    continue
                if self._home_village_dark_elixir_visible(frame):
                    bot_roi = VisionService.bottom_half_region(frame)
                    (ax, ay) = self.vision.find_template(frame, 'attack.png', region = bot_roi)
                    if ax:
                        return (ax, ay)
            self._nudge_view_to_reveal_attack()
            if self.stop_event.wait(0.35):
                return (None, None)
        return (None, None)  # [recovered: decompiler put an unconditional return inside the loop, so only one poll ever ran]

    
    def _panel_docked(self, frame):
        '''True when the new-UI "Buildings & Heroes" panel is docked at the right edge.

The panel pushes the resource HUD off its home position at the window edge, so every HUD
read must pick its band from this. ``bbpanelclose.png`` (the X in the panel's top corner)
is the cheap tell; a missing template just means "closed".'''
        if frame is None or frame.size == 0 or not get_template_path('bbpanelclose.png').is_file():
            return False
        (px, _py) = self.vision.find_template(frame, 'bbpanelclose.png', threshold = 0.7)
        return bool(px)

    def _hud_band(self, frame):
        '''HUD numbers/icon band, adapted to whether the Build panel is docked.'''
        (h, w) = frame.shape[:2]
        self._update_config_size(frame)
        return VisionService.numbers_hud_roi_top_right(w, h, panel_open = self._panel_docked(frame))

    def _home_village_dark_elixir_visible(self, frame = None):
        '''True when the Home-Village-only dark elixir HUD icon is on screen.

The new UI dropped the builder portraits the old detection matched, but the HUD still tells
the two villages apart: only the Home Village has a dark elixir row (dark bar + black
droplet); the Builder Base HUD is gold + builder elixir + gems. This reads the *icon*, never
the amount or the bar fill, so an empty storage reads exactly like a full one.'''
        if frame is None:
            frame = self.window.screenshot()
        if frame is None or frame.size == 0:
            return False
        self._update_config_size(frame)
        hud = self._hud_band(frame)
        (dx, _dy) = self.vision.find_template(frame, 'hvdarkelixir.png', threshold = 0.8, region = hud)
        return bool(dx)

    
    def _hud_readable(self, frame):
        '''True when the top-right HUD shows readable gold / elixir / gem numbers.

This is the difference between "no dark elixir, so Builder Base" and "I cannot see the
HUD at all" — a covered or transitioning screen must never be read as Builder Base.'''
        groups = VisionService.extract_top_right_hud_numbers(frame, panel_open = self._panel_docked(frame))
        return bool(groups) and len(groups) >= 2

    
    def _village_signals(self, frame):
        '''Individual village markers for one frame: ``(dark_elixir, boat, builder_portrait, hud_readable)``.'''
        self._update_config_size(frame)
        dark = self._home_village_dark_elixir_visible(frame)
        (bx, _by) = self.vision.find_template(frame, 'boat.png', threshold = 0.8)
        (hx, _hy) = self._find_home_village_builder(frame, None)
        hud = self._hud_readable(frame)
        return (bool(dark), bool(bx), bool(hx), bool(hud))

    
    def _detect_village_type(self, frame = None):
        '''Return ``"home"``, ``"builder"``, or ``None`` when the screen is not readable.

Dark elixir in the top-right HUD is the Home Village marker — it exists nowhere else — and
the docked boat is a second one. Builder Base now needs *positive* evidence: the HUD has to
be readable before a missing dark elixir icon is trusted. Falling back to "builder" on a
missing icon alone was the bug that made the bot farm the Home Village as if it were the
Builder Base (a popup, the Build panel or a fade hides the HUD), so it never took the boat.'''
        if frame is None:
            frame = self.window.screenshot()
        if frame is None or frame.size == 0:
            return None
        (dark, boat, builder_portrait, hud) = self._village_signals(frame)
        if dark:
            return 'home'
        if boat:
            return 'home'
        if builder_portrait:
            return 'home'
        if not hud:
            # Nothing proves Home Village *and* nothing proves Builder Base. Say which marker
            # was missing instead of guessing a village — a wrong guess farms the wrong base.
            logger.info('Village detect: no dark elixir, no boat, HUD unreadable — undecided for this frame')
            return None
        return 'builder'

    
    def _go_to_builder_base_with_boat(self):
        '''Home Village → Builder Base via ``boat.png``, confirming the trip actually landed.

The boat opens a travel confirmation, which is cleared here. Arrival is then confirmed by
the Home Village markers disappearing (no dark elixir row, no docked boat) — the builder
portrait this used to wait for (``mbuilder.png``) is not drawn by the new UI any more, so
that check burned its whole timeout on every single trip.'''
        self._check_stop()
        (bx, by) = self._wait_for_image('boat.png', timeout = 15, error = False)
        if not bx:
            logger.warning('boat.png not found — cannot switch to Builder Base')
            return False
        self.input.click(bx, by, pause = 0.25)
        start = time.time()
        while time.time() - start < 8:
            if self.stop_event.wait(0.5):
                return False
            frame = self.window.screenshot()
            if frame is None:
                continue
            self._update_config_size(frame)
            if self._detect_village_type(frame) == 'builder':
                logger.info('Builder Base reached')
                return True
            if self._dismiss_okay_or_exit_on_frame(frame):
                logger.info('Boat: dismissed the travel confirmation')
        start = time.time()
        while time.time() - start < 20:
            if self.stop_event.wait(0.5):
                return False
            frame = self.window.screenshot()
            if frame is None:
                continue
            self._update_config_size(frame)
            if self._detect_village_type(frame) == 'builder':
                logger.info('Builder Base reached')
                return True
        logger.warning('Still in the Home Village 20s after taking the boat — the trip may not have completed')
        return False

    
    def _ensure_correct_village(self, builder_base):
        '''Before farming: switch villages if the wrong builder portrait is showing.'''
        self._check_stop()
        frame = self.window.screenshot()
        if frame is not None:
            self._update_config_size(frame)
            if self._dismiss_okay_or_exit_on_frame(frame):
                self._home_screen_recovery()
                frame = self.window.screenshot()
                if frame is not None:
                    self._update_config_size(frame)
            (chx, chy) = self._find_capital_return_home_button(frame)
            if chx:
                logger.info('Startup: Capital screen detected â€” returning to Home Village')
                self.input.click(chx, chy, pause = 0.3)
                self._home_screen_recovery()
        self.input.click(pause = 0.15, *self.config.get_point('empty'))
        if self.stop_event.wait(0.2):
            return None
        village = self._detect_village_type()
        for attempt in range(3):
            if village is not None:
                break
            # Unknown usually means a popup or a transition frame is covering the HUD —
            # clear it and look again rather than guessing a village. The first retry is a
            # plain settle (a warp/fade needs ~1s); later ones clear the screen first.
            logger.info('Startup: cannot read which village we are in yet — recovering the screen and retrying (%d/3)', attempt + 1)
            if attempt:
                self._home_screen_recovery()
                self.input.click(pause = 0.15, *self.config.get_point('empty'))
            if self.stop_event.wait(0.6):
                return None
            village = self._detect_village_type()
        if village is None:
            msg = 'Could not tell which village the game is in (a popup or transition is covering the HUD) — clear the screen and start again'
            logger.error(msg)
            raise RuntimeError(msg)
        if builder_base:
            if village == 'builder':
                return None
            logger.info('Startup: in Home Village but Builder Base was selected — taking boat')
            if not self._go_to_builder_base_with_boat():
                msg = 'Could not reach the Builder Base — the boat trip did not complete'
                logger.error(msg)
                raise RuntimeError(msg)
            return None
        if village == 'home':
            return None
        logger.info('Startup: in Builder Base but Home Village was selected — leaving (nboat)')
        self._leave_builder_base_with_nboat()

    
    def _leave_builder_base_with_nboat(self, settle_before_drag = True):
        '''
Pan down-left from screen center (~500px), then click ``nboat.png`` to return to Home Village.
Does not check ``mbuilder.png`` first — call only when a BB→HV trip is intended.

``settle_before_drag``: small delay after prior UI (e.g. collect clicks) before capturing
dimensions and dragging.
'''
        self._check_stop()
        if settle_before_drag and self.stop_event.wait(0.75):
            self._check_stop()
        logger.info('Leaving Builder Base (drag + nboat)')
        cb = getattr(self, '_status_callback', None)
        if cb:
            cb('Multi-run: leaving Builder Base (nboat)')
        self._bb_pan_down_left_from_center()
        (nx, ny) = self._wait_for_image('nboat.png', timeout = 12, error = False)
        if nx:
            self.input.click(nx, ny, pause = 0.25)
            return None
        logger.warning('nboat.png not found after Builder Base drag — may still be in Builder Base')

    
    def _multi_run_collect_home_village_resources(self):
        '''Multi-run: tap Home Village collect bubbles if visible, before taking the boat to Builder Base.'''
        cb = getattr(self, '_status_callback', None)
        logger.info('Multi-run: Home Village collect (hgold, helixir, hdelixir)')
        if cb:
            cb('Multi-run: Home Village collect')
        for tpl in ('hgold.png', 'helixir.png', 'hdelixir.png'):
            self._check_stop()
            (rx, ry) = self._find_template_once(tpl, threshold = 0.7)
            if not rx:
                continue
            self.input.click(rx, ry, pause = 0.15)

    
    def _multi_run_builder_base_after_session(self):
        """
Multi-run only: after an account's farming session, collect Home Village resources if icons
appear, open the secondary base via boat, collect builder resources if icons appear,
optionally run the clock boost chain, then leave Builder Base.
"""
        self._multi_run_collect_home_village_resources()
        cb = getattr(self, '_status_callback', None)
        msg = 'Multi-run: Builder Base (boat → collect)'
        logger.info(msg)
        if cb:
            cb(msg)
        (bx, by) = self._wait_for_image('boat.png', timeout = 15, error = False)
        if not bx:
            logger.warning('Multi-run: boat.png not found — skipping Builder Base step')
            return None
        self.input.click(bx, by, pause = 0.2)
        if self.stop_event.wait(1):
            self._check_stop()
        for tpl in ('bgold.png', 'belixir.png', 'bgem.png'):
            self._check_stop()
            (rx, ry) = self._find_template_once(tpl, threshold = 0.7)
            if not rx:
                continue
            self.input.click(rx, ry, pause = 0.15)
        self._check_stop()
        (cx, cy) = self._wait_for_image('bclock.png', timeout = 2, error = False)
        if cx:
            self.input.click(cx, cy, pause = 0.2)
            if self.stop_event.wait(1):
                self._check_stop()
            (cbx, cby) = self._wait_for_image('clockboost.png', timeout = 10, error = False)
            if cbx:
                self.input.click(cbx, cby, pause = 0.2)
            if self.stop_event.wait(1):
                self._check_stop()
            (bux, buy) = self._wait_for_image('boost.png', timeout = 10, error = False)
            if bux:
                self.input.click(bux, buy, pause = 0.15)
        self._leave_builder_base_with_nboat(settle_before_drag = True)

    
    def _frame_shows_supercell_login_prompt(self, frame):
        """True if OCR sees the Supercell ID login line (list scroll won't help)."""
        if frame is None or frame.size == 0:
            return False
        words = self.vision.find_words_ocr(frame, query = None, min_confidence = 20, preprocess = True, tesseract_config = '--psm 11', white_text = True)
        blob = ' '.join([ w.text for w in words ]).lower()
        if 'supercell id' in blob:
            return True
        if 'log in' in blob and 'supercell' in blob:
            return True
        return False

    
    def _scroll_player_list_with_drag(self, frame):
        '''Drag ~200px upward from lower-right (client coords) to scroll the change-user list.'''
        if frame is None or frame.size == 0:
            return None
        (h, w) = frame.shape[:2]
        x1 = int(w * 0.86) + random.randint(-15, 15)
        x1 = max(int(w * 0.72), min(w - 8, x1))
        y1 = int(h * 0.86) + random.randint(-12, 12)
        y1 = max(int(h * 0.55), min(h - 12, y1))
        y2 = max(int(h * 0.12), y1 - 200)
        x2 = x1
        self.input.mouse_down(x1, y1)
        self.input.human_move(x1, y1, x2, y2, duration = random.uniform(0.28, 0.42))
        self.input.mouse_up(x2, y2)

    
    def _wait_for_player_name(self, text, timeout = 25, error = True, region = None, **ocr_kwargs):
        '''
Like :meth:`_wait_for_text`, but after each failed OCR pass drags upward in the lower-right
to scroll the account list before trying again.

OCR is limited to the right half of the window unless ``region`` is passed explicitly.
'''
        start = time.time()
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return (None, None)
                continue
            self._update_config_size(frame)
            roi = region if not region is None else VisionService.right_half_region(frame)
            (x, y) = self.vision.find_word_on_screen(frame, text, region = roi, **ocr_kwargs)
            if x:
                return (x, y)
            if self._frame_shows_supercell_login_prompt(frame):
                msg = f'''Multi-run: "Log in to Supercell ID" is showing and {text!r} was not found — log in or dismiss that screen, then retry.'''
                logger.warning(msg)
                cb = getattr(self, '_status_callback', None)
                if cb:
                    cb(msg)
                raise RuntimeError(msg)
            self._scroll_player_list_with_drag(frame)
            if self.stop_event.wait(0.45):
                return (None, None)
            if error:
                logger.warning(f'''Timeout waiting for player name OCR match: {text!r}''')
        return (None, None)

    
    def _wait_for_text(self, text, timeout = 10, error = True, region = None, **ocr_kwargs):
        '''Poll screenshots until OCR finds ``text`` (substring match). Returns click center.'''
        start = time.time()
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                if self.stop_event.wait(0.5):
                    return (None, None)
                continue
            self._update_config_size(frame)
            (x, y) = self.vision.find_word_on_screen(frame, text, region = region, **ocr_kwargs)
            if x:
                return (x, y)
            if self.stop_event.wait(0.5):
                return (None, None)
        if error:
            logger.warning(f'''Timeout waiting for OCR text containing {text!r}''')
        return (None, None)

    
    def _dismiss_open_popup(self):
        '''Best-effort close of whatever popup is on screen (okay/exit) so the flow underneath is usable again.'''
        frame = self.window.screenshot()
        if frame is None:
            return False
        self._update_config_size(frame)
        return self._dismiss_okay_or_exit_on_frame(frame)


    def _ensure_valkyrie_army_from_recipes(self):
        '''If Valkyrie army template is missing, load it from Saved Recipes. Returns False on failure.'''
        (vx, vy) = self._wait_for_image('valkarmy.png', timeout = 3, error = False)
        if vx:
            return True
        (sx, sy) = self._wait_for_image('savedrecipes.png')
        if not sx:
            logger.warning('Saved Recipes button not found while ensuring Valkyrie army')
            return False
        self.input.click(sx, sy, pause = 0.2)
        (rx, ry) = self._wait_for_image('valkrecipe.png')
        if not rx:
            logger.warning('Valkyrie recipe template not found')
            self._dismiss_open_popup()  # close the recipes popup we opened
            return False
        (ux, uy) = self._wait_for_image('use.png', y_anchor = ry, y_slop = 200)
        if not ux:
            logger.warning('Use button not found near Valkyrie recipe row')
            self._dismiss_open_popup()  # close the recipes popup we opened
            return False
        self.input.click(ux, uy, pause = 0.2)
        if self.stop_event.wait(0.35):
            return False
        (vx2, _) = self._wait_for_image('valkarmy.png', timeout = 5, error = False)
        if not vx2:
            logger.warning('valkarmy.png still not visible after applying saved recipe')
            return False
        return True

    
    def _search_region_for_template(self, frame, template, region = None, y_anchor = None, y_slop = 200):
        if not region is None:
            return region
        if not y_anchor is None:
            (h, w) = frame.shape[:2]
            y0 = max(0, y_anchor - y_slop)
            y1 = min(h, y_anchor + y_slop)
            return (0, y0, w, y1 - y0)
        if template in TOP_HALF_BOT_TEMPLATES:
            return VisionService.top_half_region(frame)
        if template in BOTTOM_HALF_BOT_TEMPLATES:
            return VisionService.bottom_half_region(frame)

    
    def _find_template_once(self, template, region = None, y_anchor = None, y_slop = 200, threshold = 0.8):
        '''One screenshot; match template or return (None, None). No polling.'''
        self._check_stop()
        frame = self.window.screenshot()
        if frame is None:
            return (None, None)
        self._update_config_size(frame)
        search_region = self._search_region_for_template(frame, template, region, y_anchor, y_slop)
        return self.vision.find_template(frame, template, threshold = threshold, region = search_region)

    
    def _wait_for_any_image(self, templates, timeout = 10, error = True, threshold = 0.8, region = None, region_from_frame = None):
        '''First ordered template match wins (checked left-to-right each frame).'''
        start = time.time()
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                continue
            self._update_config_size(frame)
            if self._battle_rewards.handle(frame):
                continue
            search_region = region
            if search_region is None and region_from_frame is not None:  # [recovered: both conditions were inverted]
                search_region = region_from_frame(frame)
            for template in templates:
                tpl_region = search_region
                if tpl_region is None:
                    tpl_region = self._search_region_for_template(frame, template, None, None, 200)
                (x, y) = self.vision.find_template(frame, template, threshold = threshold, region = tpl_region)
                if x:  # [recovered: was an unconditional `return`, so only the first template was ever checked]
                    return (x, y)
            if self.stop_event.wait(0.5):
                return (None, None)
            if time.time() - start < timeout:
                continue
        if error:
            logger.warning(f'''Timeout waiting for any of {templates}''')
        return (None, None)

    
    def _wait_for_image(self, template, timeout = 10, error = True, region = None, y_anchor = None, y_slop = 200, threshold = 0.8):
        start = time.time()
        while time.time() - start < timeout:
            self._check_stop()
            frame = self.window.screenshot()
            if frame is None:
                continue
            self._update_config_size(frame)
            if self._battle_rewards.handle(frame):
                continue
            search_region = self._search_region_for_template(frame, template, region, y_anchor, y_slop)
            (x, y) = self.vision.find_template(frame, template, threshold = threshold, region = search_region)
            if x:
                return (x, y)
            if self.stop_event.wait(0.5):
                return (None, None)
        if error:
            logger.warning(f'''Timeout waiting for {template}''')
        return (None, None)


