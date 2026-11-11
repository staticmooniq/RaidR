import math
import time
import random
import json
import cv2
from pathlib import Path
from typing import Any, List, Optional, Tuple
from app.services.input import InputService
from app.services.vision import VisionService
from app.config import ASPECT_16_9, Config
from app.utils.common import get_template_path
from app.utils.logger import setup_logger
from app.utils.profile_settings_store import EARTHQUAKE_METHOD_CURVE, EARTHQUAKE_METHOD_RANDOM
logger = setup_logger('Strategies')
_EARTHQUAKE_REGION_ARC_SAMPLES = 49
_EARTHQUAKE_RANDOM_LINE_FROM_BOTTOM = (4, 10)
_EDRAG_COUNT = 12
_EDRAG_DELAY = 0.2
_EDRAG_CORNER_MARGIN = 100
_DIAMOND_EDGES = (('left', 'top'), ('top', 'right'))
# Per-hero random wait between deploy and its first ability click, so abilities
# don't fire back-to-back with the deploy taps.
_HERO_ABILITY_DELAY_MIN = 5
_HERO_ABILITY_DELAY_MAX = 8
_DEPLOY_ZONES_FILE = Path(__file__).parent.parent.parent / 'deploy_zones.json'
_DEPLOY_ZONES_CACHE = None

def _load_deploy_zones():
    '''Load custom deployment zone sets from deploy_zones.json if present.
Returns a list of sets (each set is a list of [ref_x, ref_y] pairs), or None
if the file doesn't exist — in which case the original drag deploy runs instead.'''
    global _DEPLOY_ZONES_CACHE
    if _DEPLOY_ZONES_CACHE is not None:
        return _DEPLOY_ZONES_CACHE
    if not _DEPLOY_ZONES_FILE.exists():
        return None
    try:
        data = json.loads(_DEPLOY_ZONES_FILE.read_text())
        _DEPLOY_ZONES_CACHE = data.get('sets')
        logger.info('Loaded %d custom deploy zone sets from %s', len(_DEPLOY_ZONES_CACHE), _DEPLOY_ZONES_FILE.name)
        return _DEPLOY_ZONES_CACHE
    except Exception as e:
        logger.warning('Failed to load deploy_zones.json: %s — falling back to default deploy', e)
        return None

class AttackStrategy:
    '''Base class for attack strategies.'''
    
    def __init__(self, input_service, vision_service, config, stop_event = None, earthquake_method = EARTHQUAKE_METHOD_CURVE, rage_spell = False):
        self.input = input_service
        self.vision = vision_service
        self.config = config
        self.stop_event = stop_event
        self.earthquake_method = earthquake_method
        self.rage_spell = rage_spell
        self._spell_template = 'rage.png' if rage_spell else 'earthquake.png'
        self.event_handler = None
        self.CORNER_ORDER = [
            'left',
            'top',
            'right',
            'bottom']

    
    def execute(self, frame, stop_event = None):
        raise NotImplementedError

    
    def _expand_loc(self, x, y):
        return (x + random.randint(-10, 10), y + random.randint(-10, 10))

    
    def _sync_frame_size(self, frame):
        self.config.set_target_size_from_frame(frame)

    def _reward_checkpoint(self, frame=None, selected=None, selected_scale_template=True):
        """Clear event overlays before input; reselect a displaced troop/spell.

        Return a current frame and whether a choice interrupted deployment.
        A missing capture or a stuck overlay must stop further battle clicks.
        """
        if self.stop_event and self.stop_event.is_set():
            raise InterruptedError('Bot stopped by user')
        if self.event_handler is None:
            return frame, False
        # Callers may retain a frame from before a previous deployment/choice.
        frame = self.input.window_service.screenshot()
        if frame is None:
            raise RuntimeError('Game capture unavailable during deployment')
        handled = self.event_handler.handle(frame)
        if handled:
            frame = self.input.window_service.screenshot()
            if frame is None:
                raise RuntimeError('Game capture unavailable after event choice')
            self._sync_frame_size(frame)
            if selected:
                roi = self.vision.bottom_half_region(frame)
                x, y = self.vision.find_template(frame, selected, region=roi, scale_template=selected_scale_template)
                if x is None:
                    return None, True  # The previously selected troop is exhausted.
                self.input.click(x, y, pause=0.2, rand=False)
        return frame, handled

    
    def _point(self, key):
        return self.config.get_point(key)

    
    def _scaled_deployment_data(self):
        return { key: self._point(key) for key in self.CORNER_ORDER }
        key = None

    
    def _get_hero_ability_delay(self, hero_name: str) -> Optional[float]:
        """
        Calculate ability trigger delay in seconds for a specific hero based on strategy settings.
        Returns:
            - float: seconds after deployment to trigger ability
            - None: never trigger ability
        """
        abilities_cfg = {}
        if hasattr(self, 'strategy_data') and isinstance(self.strategy_data, dict):
            abilities_cfg = self.strategy_data.get('hero_abilities', {})

        cfg = abilities_cfg.get(hero_name, {})
        mode = cfg.get('mode', 'random')

        if mode == 'never':
            logger.info("Hero '%s' ability is set to 'never' — skipping trigger", hero_name)
            return None
        elif mode == 'custom':
            sec = float(cfg.get('seconds', 15))
            logger.info("Hero '%s' ability scheduled after custom %gs", hero_name, sec)
            return max(0.5, sec)
        else: # 'random'
            delay = random.uniform(_HERO_ABILITY_DELAY_MIN, _HERO_ABILITY_DELAY_MAX)
            logger.info("Hero '%s' ability scheduled after random %.1fs", hero_name, delay)
            return delay

    def deploy_heroes(self, frame):
        frame, _ = self._reward_checkpoint(frame)
        self._sync_frame_size(frame)
        heroes = [
            'queen',
            'warden',
            'RC',
            'king',
            'prince',
            'dragonduke']
        random.shuffle(heroes)
        if not hasattr(self, '_pending_hero_abilities') or self._pending_hero_abilities is None:
            self._pending_hero_abilities = []
        roi = self.vision.bottom_half_region(frame)
        (ix, iy) = self.vision.find_template(frame, 'loglauncher.png', threshold = 0.7, region = roi)
        if not ix:
            (ix, iy) = self.vision.find_template(frame, 'siegebarracks.png', threshold = 0.7, region = roi)
        if ix:
            deploy_point = self._get_hero_deploy_point(frame)
            self.input.click(ix, iy, pause = 0.2, rand = False)
            self.input.click(deploy_point[0], deploy_point[1], pause = 0.15, rand = False)
            self.input.click(deploy_point[0], deploy_point[1], pause = 0.2, rand = False)
        for hero in heroes:
            fresh, interrupted = self._reward_checkpoint()
            if fresh is not None:
                frame = fresh
                roi = self.vision.bottom_half_region(frame)
            if interrupted:
                self._pending_hero_abilities = self._relocate_abilities(self._pending_hero_abilities, frame)
            (bx, by) = self.vision.find_template(frame, f'''{hero}.png''', threshold = 0.7, region = roi)
            if not bx:
                (bx, by) = self.vision.find_template(frame, f'''{hero}.png''', threshold = 0.63, region = roi)
            if not bx:
                continue
            deploy_point = self._get_hero_deploy_point(frame)
            self.input.click(bx, by, pause = 0.2, rand = False)
            self.input.click(deploy_point[0], deploy_point[1], pause = 0.15, rand = False)
            self.input.click(deploy_point[0], deploy_point[1], pause = 0.15, rand = False)

            # Determine ability trigger timing based on hero strategy configuration
            delay = self._get_hero_ability_delay(hero)
            if delay is not None:
                live = self.input.window_service.screenshot() if self.event_handler else frame
                radius = max(8, round(frame.shape[0]*.025))
                tile = None
                if live is not None and bx >= radius and by >= radius:
                    tile = live[by-radius:by+radius, bx-radius:bx+radius].copy()
                ability_ready_at = time.time() + delay
                self._pending_hero_abilities.append((hero, bx, by, tile, ability_ready_at))

            # Refresh frame for next hero scan to prevent using displaced coordinates
            fresh_scr = self.input.window_service.screenshot()
            if fresh_scr is not None:
                frame = fresh_scr
                roi = self.vision.bottom_half_region(frame)

    def trigger_pending_abilities(self, stop_event=None):
        """Wait for and click scheduled hero abilities as their countdown expires."""
        ev = stop_event or self.stop_event
        if not getattr(self, '_pending_hero_abilities', None):
            return

        # Sort so the earliest scheduled ability triggers first
        self._pending_hero_abilities.sort(key=lambda item: item[4])

        while self._pending_hero_abilities:
            if ev and ev.is_set():
                return
            fresh, interrupted = self._reward_checkpoint()
            if interrupted:
                self._pending_hero_abilities = self._relocate_abilities(self._pending_hero_abilities, fresh)
            if not self._pending_hero_abilities:
                break

            hero_name, hx, hy, _, ability_ready_at = self._pending_hero_abilities.pop(0)
            wait_s = ability_ready_at - time.time()
            while wait_s > 0:
                chunk = min(wait_s, 0.5)
                if ev:
                    if ev.wait(chunk):
                        return
                else:
                    time.sleep(chunk)
                wait_s -= chunk

                # Early check if battle ended while waiting
                if wait_s > 1.5:
                    cur_f = self.input.window_service.screenshot()
                    if cur_f is not None:
                        roi = self.vision.bottom_half_region(cur_f)
                        (ox, oy) = self.vision.find_template(cur_f, 'okay.png', region=roi)
                        if ox:
                            logger.info("Battle completed before hero '%s' ability countdown — exiting", hero_name)
                            self._pending_hero_abilities.clear()
                            return

            self.input.click(hx, hy, pause = 0.2, rand = False)
            logger.info("Hero '%s' ability clicked at (%d, %d)", hero_name, hx, hy)
            if ev:
                ev.wait(random.uniform(0.1, 0.2))
            else:
                time.sleep(random.uniform(0.1, 0.2))

    def _relocate_abilities(self, heroes, frame):
        """Match cached live portraits only when an event actually moved slots."""
        if frame is None:
            return []
        top = frame.shape[0]//2
        roi = cv2.cvtColor(frame[top:], cv2.COLOR_BGR2GRAY)
        relocated = []
        for hero_name, x, y, tile, ability_ready_at in heroes:
            if tile is None or not tile.size:
                continue
            gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
            _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(roi, gray, cv2.TM_CCOEFF_NORMED))
            if score >= .65:
                relocated.append((hero_name, loc[0]+tile.shape[1]//2, top+loc[1]+tile.shape[0]//2, tile, ability_ready_at))
            else:
                logger.info("Hero '%s' no longer recognizable after reward; skipping stale slot", hero_name)
        return relocated

    
    def _hero_corner_xy(self, corner):
        '''Corner used when building hero deploy lines; on ``16_9``, ``top`` is nudge-scaled.'''
        (px, py) = self.config.get_point(corner)
        if self.config.aspect_key == ASPECT_16_9 and corner == 'top':
            py -= self.config.scale_scalar(70)
        return (int(px), int(py))

    
    @staticmethod
    def _quantize_deploy_to_frame(px, py, fw, fh):
        '''Clamp to ``[0, fw-1]`` x ``[0, fh-1]``, round to nearest pixels.'''
        if fw <= 0 or fh <= 0:
            return (int(round(px)), int(round(py)))
        cx = max(0, min(float(fw - 1), float(px)))
        cy = max(0, min(float(fh - 1), float(py)))
        return (int(round(cx)), int(round(cy)))

    
    def _get_hero_deploy_point(self, frame = None):
        c_name = random.choice([
            'top',
            'right',
            'left'])
        (c1x, c1y) = self._hero_corner_xy(c_name)
        if c_name in ('left', 'right'):
            (c2x, c2y) = self._hero_corner_xy('top')
        else:
            corner = random.choice([
                'left',
                'right'])
            (c2x, c2y) = self._hero_corner_xy(corner)
        t = random.uniform(0, 1)
        xf = c1x + (c2x - c1x) * t
        yf = c1y + (c2y - c1y) * t
        if frame is not None and getattr(frame, 'size', 0):  # [recovered: decompiler dropped the `not`]
            (fh, fw) = frame.shape[:2]
            return self._quantize_deploy_to_frame(xf, yf, fw, fh)
        return (int(round(xf)), int(round(yf)))

    
    @staticmethod
    def _earthquake_anchor_triplet(data, offset):
        '''Left / top / right drop anchors (same nudge as legacy earthquake logic).'''
        (lx, ly) = data['left']
        lx += int(offset * 1.3)
        (tx, ty) = data['top']
        ty += int(offset)
        (rx, ry) = data['right']
        rx -= int(offset * 1.3)
        return ((float(lx), float(ly)), (float(tx), float(ty)), (float(rx), float(ry)))

    
    @staticmethod
    def _sample_arc_through_three(ltr, n):
        '''
``n`` points along a circular arc from L to R that passes through T.
If L,T,R are collinear, uses a quadratic Bezier with control point chosen so t=0.5 hits T.
'''
        (L, T, R) = ltr
        (ax, ay) = L
        (bx, by) = T
        (cx, cy) = R
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if n < 2:
            return [
                (int(round(L[0])), int(round(L[1])))]
        if abs(d) < 1e-06:
            p1x = 2 * bx - 0.5 * ax - 0.5 * cx
            p1y = 2 * by - 0.5 * ay - 0.5 * cy
            out = []
            for i in range(n):
                t = i / (n - 1)
                u = 1 - t
                x = u * u * ax + 2 * u * t * p1x + t * t * cx
                y = u * u * ay + 2 * u * t * p1y + t * t * cy
                out.append((int(round(x)), int(round(y))))
            return out
        a2 = ax * ax + ay * ay
        b2 = bx * bx + by * by
        c2 = cx * cx + cy * cy
        ox = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / d
        oy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / d
        r = math.hypot(ax - ox, ay - oy)
        
        def ang(p):
            return math.atan2(p[1] - oy, p[0] - ox)

        phi_r = ang(R)
        phi_t = ang(T)
        phi_l = ang(L)
        two_pi = 2 * math.pi
        ccw_span = (phi_r - phi_l) % two_pi
        t_ccw = (phi_t - phi_l) % two_pi
        if t_ccw <= ccw_span:
            sweep = ccw_span
        else:
            sweep = ccw_span - two_pi
        out = []
        for i in range(n):
            t = i / (n - 1)
            phi = phi_l + t * sweep
            x = ox + r * math.cos(phi)
            y = oy + r * math.sin(phi)
            out.append((int(round(x)), int(round(y))))
        return out

    
    @staticmethod
    def _earthquake_horizontal_y(frame_h, from_bottom_num, from_bottom_den):
        '''Row ``y`` for a line ``from_bottom_num/from_bottom_den`` of the way from bottom to top.'''
        if frame_h <= 0:
            return 0
        h = frame_h
        f = from_bottom_num / float(from_bottom_den)
        return int(round((h - 1) * (1 - f)))

    
    @staticmethod
    def _earthquake_fill_polygon(arc_pts, y_line):
        '''Closed polygon: arc polyline (left→right) then segment along ``y=y_line`` back to start.'''
        if len(arc_pts) < 2:
            return list(arc_pts)
        (x0, y0) = arc_pts[0]
        (x1, y1) = arc_pts[-1]
        return list(arc_pts) + [
            (x1, y_line),
            (x0, y_line)]

    
    @staticmethod
    def _polygon_double_area(poly):
        if len(poly) < 3:
            return 0
        a = 0
        n = len(poly)
        for i in range(n):
            (x1, y1) = poly[i]
            (x2, y2) = poly[(i + 1) % n]
            a += x1 * y2 - x2 * y1
        return a

    
    @staticmethod
    def _point_in_polygon(px, py, poly):
        '''Even-odd ray test; ``poly`` closed implicitly (last vertex → first not repeated).'''
        n = len(poly)
        if n < 3:
            return False
        inside = False
        j = n - 1
        for i in range(n):
            (ix, iy) = poly[i]
            (jx, jy) = poly[j]
            if (iy > py) != (jy > py):
                x_at = (jx - ix) * (py - iy) / (jy - iy) + ix
                if px < x_at:
                    inside = not inside
            j = i
        return inside

    
    @staticmethod
    def _random_points_in_polygon(poly, frame_w, frame_h, n_points):
        xs = [ p[0] for p in poly ]
        ys = [ p[1] for p in poly ]
        min_x = max(0, min(xs))
        max_x = min(frame_w - 1, max(xs))
        min_y = max(0, min(ys))
        max_y = min(frame_h - 1, max(ys))
        out = []
        if max_x < min_x or max_y < min_y:
            return out
        for _ in range(n_points):
            for _try in range(1000):
                rx = random.randint(min_x, max_x)
                ry = random.randint(min_y, max_y)
                if not AttackStrategy._point_in_polygon(rx, ry, poly):
                    continue
                out.append((rx, ry))
                break  # [recovered: decompiler dropped this break — every in-polygon sample was appended]
            else:
                (ax, ay) = poly[max(1, len(poly) // 4)]
                out.append((max(0, min(frame_w - 1, ax)), max(0, min(frame_h - 1, ay))))
        return out

    
    def _earthquake_curve_points_with_jitter(self, ltr):
        points = self._sample_arc_through_three(ltr, 11)
        if random.choice((True, False)):
            points.reverse()
        jitter_px = 100
        return [ (cx + random.randint(-jitter_px, jitter_px), cy + random.randint(-jitter_px, jitter_px)) for cx, cy in points ]
        cy = None
        cx = None

    
    def _random_diamond_perimeter_point(self, frame):
        (c1, c2) = random.choice(_DIAMOND_EDGES)
        (x1, y1) = self._point(c1)
        (x2, y2) = self._point(c2)
        edge_len = math.hypot(x2 - x1, y2 - y1)
        if edge_len <= 2 * _EDRAG_CORNER_MARGIN:
            t = 0.5
        else:
            t_min = _EDRAG_CORNER_MARGIN / edge_len
            t_max = 1 - t_min
            t = random.uniform(t_min, t_max)
        xf = x1 + (x2 - x1) * t
        yf = y1 + (y2 - y1) * t
        (fh, fw) = frame.shape[:2]
        return self._quantize_deploy_to_frame(xf, yf, fw, fh)

    def _random_four_edge_point(self, frame):
        """Random point distributed evenly across all four edges of the base perimeter."""
        (fh, fw) = frame.shape[:2]
        edges = [
            ('left', 'top'),
            ('top', 'right'),
            ('right', 'bottom'),
            ('bottom', 'left')
        ]
        c1, c2 = random.choice(edges)
        p1 = self._point(c1)
        p2 = self._point(c2)

        # For bottom corner, clamp y so line doesn't dip into the deploy bar
        y1 = p1[1] if c1 != 'bottom' else int(fh * 0.76)
        y2 = p2[1] if c2 != 'bottom' else int(fh * 0.76)
        # For top corner, clamp y so line doesn't go offscreen
        y1 = max(int(fh * 0.05), y1)
        y2 = max(int(fh * 0.05), y2)

        t = random.uniform(0.15, 0.85)
        px = p1[0] + (p2[0] - p1[0]) * t + random.randint(-15, 15)
        py = y1 + (y2 - y1) * t + random.randint(-15, 15)

        # Final safety clamps: stay away from window edges and deploy bar
        cx = max(int(fw * 0.04), min(int(fw * 0.96), int(round(px))))
        cy = max(int(fh * 0.05), min(int(fh * 0.77), int(round(py))))
        return cx, cy

    
    @staticmethod
    def _point_on_polyline_at_distance(vertices, distance):
        '''Point ``distance`` pixels along a polyline from the first vertex.'''
        if not vertices:
            return (0, 0)
        if len(vertices) == 1:
            return (float(vertices[0][0]), float(vertices[0][1]))
        remaining = max(0, float(distance))
        # [recovered: pycdc reversed every dual-store here, transposing x/y mid-walk — verified against bytecode]
        (x0, y0) = (float(vertices[0][0]), float(vertices[0][1]))
        for i in range(len(vertices) - 1):
            (x1, y1) = (float(vertices[i + 1][0]), float(vertices[i + 1][1]))
            seg_len = math.hypot(x1 - x0, y1 - y0)
            if seg_len <= 0:
                (x0, y0) = (x1, y1)
                continue
            if remaining <= seg_len:
                t = remaining / seg_len
                return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            remaining -= seg_len
            (x0, y0) = (x1, y1)
        return (x0, y0)

    
    def _even_diamond_top_perimeter_points(self, frame, count, *, deviation_frac = 0.1, reserve_top_corner_slot = False):
        '''
Evenly spaced deploy clicks along left→top→right diamond edges (Edrag front),
with ±``deviation_frac`` jitter per slot and corner margin clamping.

When ``reserve_top_corner_slot`` is set, spacing uses ``count + 1`` slots and the
slot nearest the top vertex is left empty (virtual troop at the apex).
'''
        if count <= 0:
            return []
        vertices = [ tuple(self._point(corner)) for corner in ('left', 'top', 'right') ]
        seg_lens = [ math.hypot(vertices[i + 1][0] - vertices[i][0], vertices[i + 1][1] - vertices[i][1]) for i in range(len(vertices) - 1) ]
        total_len = sum(seg_lens)
        margin = float(self.config.scale_scalar(_EDRAG_CORNER_MARGIN))
        start_d = margin
        end_d = total_len - margin
        span = end_d - start_d
        (fh, fw) = frame.shape[:2]
        if span <= 0:
            mid = self._point_on_polyline_at_distance(vertices, total_len / 2)
            return [
                self._quantize_deploy_to_frame(mid[0], mid[1], fw, fh)]
        slot_count = count + 1 if reserve_top_corner_slot else count
        spacing = span / slot_count
        slot_distances = []
        for i in range(slot_count):
            d = start_d + (i + 0.5) * spacing
            d += random.uniform(-deviation_frac, deviation_frac) * spacing
            d = max(start_d, min(end_d, d))
            slot_distances.append(d)
        skip_idx = None
        if reserve_top_corner_slot and slot_count > 1:
            top_d = seg_lens[0]
            skip_idx = min(range(slot_count), key = (lambda i: abs(slot_distances[i] - top_d)))
        out = []
        for i, d in enumerate(slot_distances):
            if i == skip_idx:
                continue
            (xf, yf) = self._point_on_polyline_at_distance(vertices, d)
            out.append(self._quantize_deploy_to_frame(xf, yf, fw, fh))
        return out
        corner = None
        i = None

    
    def _deploy_diamond_perimeter_troop(self, frame, template_name, stop_event = None, *, count = _EDRAG_COUNT, delay = _EDRAG_DELAY):
        '''Select troop in the bottom bar and click ``count`` points on the diamond perimeter.'''
        ev = stop_event or self.stop_event
        frame, _ = self._reward_checkpoint(frame)
        roi = self.vision.bottom_half_region(frame)
        (tx, ty) = self.vision.find_template(frame, template_name, region = roi)
        if tx is None:
            return False
        self.input.click(tx, ty, pause = 0.3, rand = False)
        if ev and ev.wait(0.2):
            return True
        for _ in range(count):
            if ev and ev.is_set():
                range(count)
                return True
            fresh, handled = self._reward_checkpoint(selected=template_name)
            if handled and fresh is None:
                break
            if fresh is not None:
                frame = fresh
            (px, py) = self._random_diamond_perimeter_point(frame)
            self.input.click(px, py, pause = delay, rand = False)
        return True

    
    def deploy_golden_drags_if_present(self, frame, stop_event = None):
        '''Optional Super Dragon deploy after main troops, before heroes.'''
        ev = stop_event or self.stop_event
        if self._deploy_diamond_perimeter_troop(frame, 'goldendrag.png', ev):
            logger.info('Deployed golden dragons')
        return bool(ev and ev.is_set())

    def deploy_secondary_troop(self, frame, stop_event = None):
        """Deploy the configured second troop in a count of perimeter taps."""
        template_path = getattr(self, 'secondary_template', '')
        count = getattr(self, 'secondary_count', 0)
        if not template_path or count <= 0:
            return False
        ev = stop_event or self.stop_event
        frame, _ = self._reward_checkpoint(frame)
        if frame is None:
            return False
        self._sync_frame_size(frame)
        roi = self.vision.bottom_half_region(frame)
        tx, ty = self.vision.find_template(frame, template_path, region=roi, scale_template=False)
        if tx is None:
            logger.warning('Secondary troop image did not match an icon on the troop bar; skipping')
            return False
        self.input.click(tx, ty, pause=0.2, rand=False)
        for _ in range(count):
            if ev and ev.is_set():
                return True
            fresh, handled = self._reward_checkpoint(selected=template_path, selected_scale_template=False)
            if handled and fresh is None:
                return False
            if fresh is not None:
                frame = fresh
            px, py = self._random_diamond_perimeter_point(frame)
            self.input.click(px, py, pause=0.2, rand=False)
        logger.info('Deployed %d secondary troops using the custom troop image', count)
        return True

    
    def deploy_spells(self, frame):
        frame, _ = self._reward_checkpoint(frame)
        self._sync_frame_size(frame)
        roi = self.vision.bottom_half_region(frame)
        (bx, by) = self.vision.find_template(frame, 'earthquake.png', region = roi)
        if bx:  # [recovered: decompiler turned `if` into `while`, causing endless earthquake spam after spells ran out]
            self.input.click(bx, by, pause = 0.2)
            offset = int(self.config.get_scaled('earthquake', 400))
            ltr = self._earthquake_anchor_triplet(self._scaled_deployment_data(), offset)
            (fh, fw) = frame.shape[:2]
            (num, den) = _EARTHQUAKE_RANDOM_LINE_FROM_BOTTOM
            y_line = self._earthquake_horizontal_y(fh, num, den)
            if self.earthquake_method == EARTHQUAKE_METHOD_RANDOM:
                arc_dense = self._sample_arc_through_three(ltr, _EARTHQUAKE_REGION_ARC_SAMPLES)
                if random.choice((True, False)):
                    arc_dense = arc_dense[::-1]
                poly = self._earthquake_fill_polygon(arc_dense, y_line)
                if abs(self._polygon_double_area(poly)) < 2:
                    logger.warning('Earthquake random region degenerate; using curve placement with jitter.')
                    points = self._earthquake_curve_points_with_jitter(ltr)
                else:
                    points = self._random_points_in_polygon(poly, fw, fh, 11)
            else:
                points = self._earthquake_curve_points_with_jitter(ltr)
            for cx, cy in points:
                fresh, handled = self._reward_checkpoint(selected='earthquake.png')
                if handled and fresh is None:
                    break
                jx = max(0, min(fw - 1, cx))
                jy = max(0, min(fh - 1, cy))
                self.input.click_at(jx, jy, rand = False)
                delay = random.uniform(0.1, 0.3)
                if self.stop_event:
                    self.stop_event.wait(delay)
                else:  # [recovered: decompiler dropped the else — both waits ran, doubling every spell delay]
                    time.sleep(delay)
        return None

    def _find_troop_template(self, frame, template_name, is_custom=False, region=None):
        """Find troop template on the deploy bar using multi-threshold fallback."""
        if is_custom:
            for thresh in (0.78, 0.70, 0.62):
                tx, ty = self.vision.find_template(frame, template_name, threshold=thresh, region=region, scale_template=False)
                if tx is not None:
                    return tx, ty
            for thresh in (0.75, 0.65):
                tx, ty = self.vision.find_template(frame, template_name, threshold=thresh, region=region, scale_template=True)
                if tx is not None:
                    return tx, ty
            return None, None
        else:
            tmpl_file = template_name if template_name.endswith('.png') else f"{template_name}.png"
            try:
                candidate = Path(str(tmpl_file))
                if not (candidate.is_absolute() and candidate.is_file()):
                    path = get_template_path(tmpl_file)
                    if not path.is_file():
                        return None, None
            except Exception:
                return None, None
            for thresh in (0.70, 0.63):
                tx, ty = self.vision.find_template(frame, tmpl_file, threshold=thresh, region=region)
                if tx is not None:
                    return tx, ty
            return None, None

    def _get_candidate_troop_templates(self):
        """Collect all troop template filenames or custom images that this strategy could deploy."""
        candidates = []
        if hasattr(self, 'strategy_data') and isinstance(self.strategy_data, dict):
            for t_conf in self.strategy_data.get('troops', []):
                t_tmpl = t_conf.get('template', '')
                if t_tmpl:
                    candidates.append((t_tmpl, t_conf.get('is_custom_image', False)))
        if hasattr(self, 'troop_name') and self.troop_name:
            candidates.append((f"{self.troop_name}.png", False))
        if self.__class__.__name__ == 'EdragStrategy':
            candidates.append(('edrag.png', False))
        sec = getattr(self, 'secondary_template', '')
        if sec:
            candidates.append((sec, False))
        candidates.append(('goldendrag.png', False))
        
        # General troop templates fallback
        for common in ('edrag.png', 'valkyrie.png', 'sneaky.png', 'superminion.png', 'babydragon.png', 'nightwitch.png'):
            candidates.append((common, False))

        seen = set()
        deduped = []
        for tmpl, is_cust in candidates:
            if tmpl not in seen:
                seen.add(tmpl)
                deduped.append((tmpl, is_cust))
        return deduped

    def recheck_and_deploy_remaining(self, stop_event=None, max_passes=2):
        """
        Post-deployment verification sweep:
        Re-scans the bottom deployment bar to ensure no troops, heroes, siege machines,
        or spells were missed or left behind. If any unit is detected still on the bar,
        it selects and deploys it immediately.
        """
        ev = stop_event or self.stop_event
        logger.info("Starting deploy bar verification sweep for leftover units...")

        for pass_idx in range(1, max_passes + 1):
            if ev and ev.is_set():
                return
            frame = self.input.window_service.screenshot()
            if frame is None:
                return
            self._sync_frame_size(frame)
            roi = self.vision.bottom_half_region(frame)

            found_any = False

            # 1. Recheck Siege Machines
            sieges = ['loglauncher.png', 'siegebarracks.png']
            for siege in sieges:
                if ev and ev.is_set():
                    return
                sx, sy = self._find_troop_template(frame, siege, is_custom=False, region=roi)
                if sx is not None:
                    found_any = True
                    logger.info("Deploy bar recheck (pass %d): un-deployed siege '%s' found at (%d, %d)", pass_idx, siege, sx, sy)
                    self.input.click(sx, sy, pause=0.2, rand=False)
                    dp = self._get_hero_deploy_point(frame)
                    self.input.click(dp[0], dp[1], pause=0.15, rand=False)
                    self.input.click(dp[0], dp[1], pause=0.2, rand=False)
                    delay = self._get_hero_ability_delay(hero)
                    if delay is not None:
                        ability_ready_at = time.time() + delay
                        if not hasattr(self, '_pending_hero_abilities') or self._pending_hero_abilities is None:
                            self._pending_hero_abilities = []
                        self._pending_hero_abilities.append((hero, hx, hy, None, ability_ready_at))
                    fresh = self.input.window_service.screenshot()
                    if fresh is not None:
                        frame = fresh
                        roi = self.vision.bottom_half_region(frame)

            # 2. Recheck Heroes
            heroes = ['queen', 'warden', 'RC', 'king', 'prince', 'dragonduke']
            for hero in heroes:
                if ev and ev.is_set():
                    return
                hx, hy = self._find_troop_template(frame, f'{hero}.png', is_custom=False, region=roi)
                if hx is not None:
                    found_any = True
                    logger.info("Deploy bar recheck (pass %d): un-deployed hero '%s' found at (%d, %d) — deploying!", pass_idx, hero, hx, hy)
                    self.input.click(hx, hy, pause=0.2, rand=False)
                    dp = self._get_hero_deploy_point(frame)
                    self.input.click(dp[0], dp[1], pause=0.15, rand=False)
                    self.input.click(dp[0], dp[1], pause=0.2, rand=False)
                    delay = self._get_hero_ability_delay(hero)
                    if delay is not None:
                        ability_ready_at = time.time() + delay
                        if not hasattr(self, '_pending_hero_abilities') or self._pending_hero_abilities is None:
                            self._pending_hero_abilities = []
                        self._pending_hero_abilities.append((hero, hx, hy, None, ability_ready_at))
                    fresh = self.input.window_service.screenshot()
                    if fresh is not None:
                        frame = fresh
                        roi = self.vision.bottom_half_region(frame)

            # 3. Recheck Strategy Troops
            troop_candidates = self._get_candidate_troop_templates()
            for tmpl, is_cust in troop_candidates:
                if ev and ev.is_set():
                    return
                tx, ty = self._find_troop_template(frame, tmpl, is_custom=is_cust, region=roi)
                if tx is not None:
                    found_any = True
                    logger.info("Deploy bar recheck (pass %d): remaining troop '%s' found at (%d, %d) — deploying!", pass_idx, tmpl, tx, ty)
                    self.input.click(tx, ty, pause=0.2, rand=False)
                    # Rapid perimeter taps to deploy remaining stack
                    for _ in range(20):
                        if ev and ev.is_set():
                            return
                        px, py = self._random_four_edge_point(frame)
                        self.input.click(px, py, pause=0.08, rand=False)
                    fresh = self.input.window_service.screenshot()
                    if fresh is not None:
                        frame = fresh
                        roi = self.vision.bottom_half_region(frame)

            # 4. Recheck Spells
            for sp in ('rage.png', 'earthquake.png'):
                if ev and ev.is_set():
                    return
                sx, sy = self._find_troop_template(frame, sp, is_custom=False, region=roi)
                if sx is not None:
                    found_any = True
                    logger.info("Deploy bar recheck (pass %d): un-deployed spell '%s' found at (%d, %d)", pass_idx, sp, sx, sy)
                    self.input.click(sx, sy, pause=0.2, rand=False)
                    (fh, fw) = frame.shape[:2]
                    self.input.click(fw // 2, int(fh * 0.45), pause=0.2, rand=False)
                    fresh = self.input.window_service.screenshot()
                    if fresh is not None:
                        frame = fresh
                        roi = self.vision.bottom_half_region(frame)

            if not found_any:
                logger.info("Deploy bar recheck: all units verified deployed on pass %d.", pass_idx)
                break



class TroopSpamStrategy(AttackStrategy):
    
    def __init__(self, input_service, vision_service, config, stop_event, troop_name, duration, status_callback = None, earthquake_method = EARTHQUAKE_METHOD_CURVE, secondary_template = '', secondary_count = 12, rage_spell = False):
        super().__init__(input_service, vision_service, config, stop_event, earthquake_method = earthquake_method, rage_spell = rage_spell)
        self.troop_name = troop_name
        self.duration = duration
        self.status_callback = status_callback
        self.secondary_template = secondary_template
        self.secondary_count = secondary_count

    
    def execute(self, frame, stop_event = None):
        ev = stop_event or self.stop_event
        frame, _ = self._reward_checkpoint(frame)
        self._sync_frame_size(frame)
        logger.info(f'''Executing {self.troop_name} strategy''')
        roi = self.vision.bottom_half_region(frame)
        (tx, ty) = self.vision.find_template(frame, f'''{self.troop_name}.png''', region = roi)
        if tx is None:
            msg = f'''Troop {self.troop_name} not found!'''
            logger.warning(msg)
            if self.status_callback:
                self.status_callback(msg)
            return False
        self.input.click(tx, ty, pause = 0.3, rand = False)
        if ev and ev.wait(0.2):
            return True

        zone_sets = _load_deploy_zones()
        if zone_sets:
            # Custom zone deploy: pick one set at random, click each of its 5 zones.
            chosen = random.choice(zone_sets)
            (fw, fh) = (frame.shape[1], frame.shape[0])
            ref_w = self.config.ref_width
            ref_h = self.config.ref_height
            sx = fw / ref_w
            sy = fh / ref_h
            logger.info('Custom deploy: using zone set %d', zone_sets.index(chosen) + 1)
            try:
                for (rx, ry) in chosen:
                    if ev and ev.is_set():
                        return True
                    px = int(round(rx * sx)) + random.randint(-8, 8)
                    py = int(round(ry * sy)) + random.randint(-8, 8)
                    px = max(0, min(fw - 1, px))
                    py = max(0, min(fh - 1, py))
                    fresh, handled = self._reward_checkpoint(selected=f'{self.troop_name}.png')
                    if handled and fresh is None:
                        break
                    self.input.click_at(px, py, rand=False)
                    delay = random.uniform(0.15, 0.35)
                    if ev:
                        ev.wait(delay)
                    else:
                        time.sleep(delay)
            except (InterruptedError, RuntimeError):
                return True
            if ev and ev.is_set():
                return True
            frame = self.input.window_service.screenshot()
            if frame is not None:
                self._sync_frame_size(frame)
                self.deploy_secondary_troop(frame, ev)
                if ev and ev.is_set():
                    return True
                frame = self.input.window_service.screenshot()
                if frame is None:
                    return True
                self._sync_frame_size(frame)
                if self.deploy_golden_drags_if_present(frame, ev):
                    return True
                self.deploy_heroes(frame)
                if ev and ev.is_set():
                    return True
                frame = self.input.window_service.screenshot()
                if frame is not None:
                    self._sync_frame_size(frame)
                    self.deploy_spells(frame)
            self.recheck_and_deploy_remaining(ev)
            self.trigger_pending_abilities(ev)
            return True

        # Original drag deploy (runs when deploy_zones.json doesn't exist).
        corners = [
            'top',
            'right',
            'bottom',
            'left']
        if self.config.aspect_key == ASPECT_16_9:
            start_idx = random.choice([
                1,
                3])
        else:
            start_idx = random.choice([
                0,
                1,
                3])
        direction = random.choice([
            1,
            -1])
        ordered_corners = []
        for i in range(5):
            idx = (start_idx + i * direction) % 4
            ordered_corners.append(corners[idx])
        start_corner = ordered_corners[0]
        (curr_x, curr_y) = self._expand_loc(*self._point(start_corner))
        self.input.mouse_down(curr_x, curr_y)
        if ev and ev.wait(0.65):
            self.input.mouse_up(curr_x, curr_y)
            return True
        try:
            total_duration = self.duration
            segment_duration = total_duration / 4
            for i in range(len(ordered_corners) - 1):
                if ev and ev.is_set():
                    break  # [recovered: decompiler dropped this break]
                fresh, handled = self._reward_checkpoint(selected=f'{self.troop_name}.png')
                if handled:
                    if fresh is None:
                        break
                    self.input.mouse_down(curr_x, curr_y)
                next_c = ordered_corners[i + 1]
                (target_x, target_y) = self._expand_loc(*self._point(next_c))
                duration = random.uniform(segment_duration * 0.9, segment_duration * 1.1)
                self.input.human_move(curr_x, curr_y, target_x, target_y, duration = duration)
                curr_y = target_y
                curr_x = target_x
            self.input.mouse_up(curr_x, curr_y)
            if ev and ev.is_set():
                return True
            frame = self.input.window_service.screenshot()
            if not frame is None:
                self._sync_frame_size(frame)
                self.deploy_secondary_troop(frame, ev)
                if ev and ev.is_set():
                    return True
                frame = self.input.window_service.screenshot()
                if frame is None:
                    return True
                self._sync_frame_size(frame)
                if self.deploy_golden_drags_if_present(frame, ev):
                    return True
                self.deploy_heroes(frame)
                if ev and ev.is_set():
                    return True
                frame = self.input.window_service.screenshot()
                if not frame is None:
                    self._sync_frame_size(frame)
                    self.deploy_spells(frame)
            self.recheck_and_deploy_remaining(ev)
            self.trigger_pending_abilities(ev)
            return True
        finally:
            self.input.mouse_up(curr_x, curr_y)




class EdragStrategy(AttackStrategy):
    
    def __init__(self, input_service, vision_service, config, stop_event, status_callback = None, earthquake_method = EARTHQUAKE_METHOD_CURVE, secondary_template = '', secondary_count = 12, rage_spell = False):
        super().__init__(input_service, vision_service, config, stop_event, earthquake_method = earthquake_method)
        self.status_callback = status_callback
        self.secondary_template = secondary_template
        self.secondary_count = secondary_count
        self.troop_name = 'edrag'

    
    def execute(self, frame, stop_event = None):
        ev = stop_event or self.stop_event
        self._sync_frame_size(frame)
        logger.info('Executing edrag strategy')
        if not self._deploy_diamond_perimeter_troop(frame, 'edrag.png', ev):
            msg = 'Troop edrag not found!'
            logger.warning(msg)
            if self.status_callback:
                self.status_callback(msg)
            return False
        if ev and ev.is_set():
            return True
        frame = self.input.window_service.screenshot()
        if not frame is None:
            self._sync_frame_size(frame)
            self.deploy_secondary_troop(frame, ev)
            if ev and ev.is_set():
                return True
            frame = self.input.window_service.screenshot()
            if frame is None:
                return True
            self._sync_frame_size(frame)
            if self.deploy_golden_drags_if_present(frame, ev):
                return True
            self.deploy_heroes(frame)
            if ev and ev.is_set():
                return True
            frame = self.input.window_service.screenshot()
            if not frame is None:
                self._sync_frame_size(frame)
                self.deploy_spells(frame)
        self.recheck_and_deploy_remaining(ev)
        self.trigger_pending_abilities(ev)
        return True


class CustomArmyStrategy(AttackStrategy):
    '''Dynamic multi-troop attack strategy driven by custom user strategy configuration.'''

    def __init__(self, input_service, vision_service, config, stop_event, strategy_data, status_callback = None, earthquake_method = EARTHQUAKE_METHOD_CURVE, rage_spell = False):
        super().__init__(input_service, vision_service, config, stop_event, earthquake_method = earthquake_method, rage_spell = rage_spell)
        self.strategy_data = strategy_data
        self.status_callback = status_callback

    def _find_troop_icon(self, frame, troop_conf):
        """Find the troop icon on the deployment bar with multi-threshold fallback."""
        roi = self.vision.bottom_half_region(frame)
        template = troop_conf.get('template', '')
        is_custom = troop_conf.get('is_custom_image', False)
        
        if is_custom:
            # 1. First try matching directly at 1:1 scale (perfect for real-time game crops)
            for thresh in (0.78, 0.70, 0.62):
                tx, ty = self.vision.find_template(frame, template, threshold=thresh, region=roi, scale_template=False)
                if tx is not None:
                    return tx, ty
            # 2. Fallback with scale template adjustment if resolution changed
            for thresh in (0.75, 0.65):
                tx, ty = self.vision.find_template(frame, template, threshold=thresh, region=roi, scale_template=True)
                if tx is not None:
                    return tx, ty
            return None, None
        else:
            tmpl_name = template if template.endswith('.png') else f"{template}.png"
            return self.vision.find_template(frame, tmpl_name, region = roi)

    def _deploy_single_troop(self, frame, troop_conf, ev):
        troop_name = troop_conf.get('name', 'Custom Troop')
        deploy_style = troop_conf.get('deploy_style', 'four_edge_spam')
        count = int(troop_conf.get('count', 0))
        delay = float(troop_conf.get('delay', 0.15))

        logger.info('Deploying troop %s using style %s (count=%d)', troop_name, deploy_style, count)

        tx, ty = self._find_troop_icon(frame, troop_conf)
        if tx is None:
            msg = f"Troop '{troop_name}' not found on deploy bar!"
            logger.warning(msg)
            if self.status_callback:
                self.status_callback(msg)
            return False

        # Select troop
        self.input.click(tx, ty, pause = 0.3, rand = False)
        if ev and ev.wait(0.2):
            return True

        if deploy_style == 'diamond_perimeter':
            tap_count = count if count > 0 else 18
            for _ in range(tap_count):
                if ev and ev.is_set():
                    return True
                fresh, handled = self._reward_checkpoint()
                if handled and fresh is None:
                    break
                if fresh is not None:
                    frame = fresh
                px, py = self._random_diamond_perimeter_point(frame)
                self.input.click(px, py, pause = max(0.06, delay), rand = False)

        elif deploy_style == 'custom_zones':
            zone_sets = _load_deploy_zones()
            tap_count = count if count > 0 else 25
            if zone_sets:
                chosen = random.choice(zone_sets)
                (fw, fh) = (frame.shape[1], frame.shape[0])
                sx = fw / self.config.ref_width
                sy = fh / self.config.ref_height
                for i in range(tap_count):
                    if ev and ev.is_set():
                        return True
                    fresh, handled = self._reward_checkpoint()
                    if handled and fresh is None:
                        break
                    rx, ry = chosen[i % len(chosen)]
                    px = max(40, min(fw - 40, int(round(rx * sx)) + random.randint(-12, 12)))
                    py = max(60, min(int(fh * 0.78), int(round(ry * sy)) + random.randint(-12, 12)))
                    self.input.click_at(px, py, rand=False)
                    if ev:
                        ev.wait(max(0.06, delay))
                    else:
                        time.sleep(max(0.06, delay))
            else:
                for _ in range(tap_count):
                    if ev and ev.is_set():
                        return True
                    fresh, handled = self._reward_checkpoint()
                    if handled and fresh is None:
                        break
                    if fresh is not None:
                        frame = fresh
                    px, py = self._random_four_edge_point(frame)
                    self.input.click(px, py, pause = max(0.06, delay), rand = False)

        elif deploy_style == 'corner_focus':
            tap_count = count if count > 0 else 20
            (fh, fw) = frame.shape[:2]
            corner_spots = [
                (int(fw * 0.16), int(fh * 0.46)), # Left side
                (int(fw * 0.84), int(fh * 0.46)), # Right side
                (int(fw * 0.35), int(fh * 0.22)), # Top-Left
                (int(fw * 0.65), int(fh * 0.22)), # Top-Right
            ]
            base_x, base_y = random.choice(corner_spots)
            for _ in range(tap_count):
                if ev and ev.is_set():
                    return True
                fresh, handled = self._reward_checkpoint()
                if handled and fresh is None:
                    break
                if fresh is not None:
                    frame = fresh
                cx = max(40, min(fw - 40, base_x + random.randint(-40, 40)))
                cy = max(60, min(int(fh * 0.78), base_y + random.randint(-40, 40)))
                self.input.click(cx, cy, pause = max(0.06, delay), rand = False)

        else:
            # Default 'four_edge_spam' (rapid taps distributed evenly across all 4 edges)
            tap_count = count if count > 0 else 30
            for _ in range(tap_count):
                if ev and ev.is_set():
                    return True
                fresh, handled = self._reward_checkpoint()
                if handled and fresh is None:
                    break
                if fresh is not None:
                    frame = fresh
                px, py = self._random_four_edge_point(frame)
                self.input.click(px, py, pause = max(0.06, delay), rand = False)

        return True

    def execute(self, frame, stop_event = None):
        ev = stop_event or self.stop_event
        self._sync_frame_size(frame)
        name = self.strategy_data.get('name', 'Custom Army')
        logger.info('Executing custom strategy: %s', name)
        if self.status_callback:
            self.status_callback(f"Deploying: {name}")

        troops = self.strategy_data.get('troops', [])
        deployed_any = False

        for troop in troops:
            if ev and ev.is_set():
                return True
            fresh = self.input.window_service.screenshot()
            if fresh is not None:
                frame = fresh
                self._sync_frame_size(frame)

            ok = self._deploy_single_troop(frame, troop, ev)
            if ok:
                deployed_any = True
            if ev and ev.wait(0.3):
                return True

        if not deployed_any and troops:
            msg = f"No troops from custom strategy '{name}' could be found!"
            logger.warning(msg)
            if self.status_callback:
                self.status_callback(msg)
            return False

        # Deploy Heroes if enabled
        if self.strategy_data.get('deploy_heroes', True):
            if ev and ev.is_set():
                return True
            frame = self.input.window_service.screenshot()
            if frame is not None:
                self._sync_frame_size(frame)
                self.deploy_golden_drags_if_present(frame, ev)
                self.deploy_heroes(frame)

        # Deploy Spells if enabled
        if self.strategy_data.get('deploy_spells', True):
            if ev and ev.is_set():
                return True
            frame = self.input.window_service.screenshot()
            if frame is not None:
                self._sync_frame_size(frame)
                self.deploy_spells(frame)

        self.recheck_and_deploy_remaining(ev)
        self.trigger_pending_abilities(ev)
        return True
