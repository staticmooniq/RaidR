"""Custom strategy data store and management."""
from __future__ import annotations
import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.utils.common import atomic_write_text, get_user_app_data_dir, ensure_dir
from app.utils.logger import setup_logger

logger = setup_logger('CustomStrategiesStore')

STRATEGY_DEPLOY_PRESETS = [
    ('🎯 Custom Deployment (User Drawn)', 'custom_deployment'),
    ('Diamond Perimeter (Edrag style)', 'diamond_perimeter'),
    ('Full Four-Edge Spam (Valkyrie style)', 'four_edge_spam'),
    ('Custom Deploy Zones (Fast 5-Point)', 'custom_zones'),
    ('Single Corner / Side Focus', 'corner_focus'),
]

def sample_line_points(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    count: int = 8,
    min_spacing: float = 40.0,
    existing_points: Optional[List[Tuple[float, float]]] = None,
    max_attempts_per_point: int = 15
) -> List[Tuple[float, float]]:
    """
    Samples points along segment p1->p2.
    Strictly enforces:
    1. Points are distributed along the segment.
    2. No two sampled points are closer than min_spacing.
    3. No sampled point is closer than min_spacing to any point in existing_points.
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    line_len = math.hypot(dx, dy)
    if line_len < 10:
        return []

    # Maximum points that can physically fit along line_len with min_spacing
    max_possible = max(1, int(line_len / max(10.0, min_spacing)) + 1)
    target_k = max(2, min(int(count), max_possible))

    sampled: List[Tuple[float, float]] = []
    all_reference = list(existing_points or [])
    step_frac = 1.0 / (target_k - 1) if target_k > 1 else 0.0

    for i in range(target_k):
        base_t = i / float(target_k - 1) if target_k > 1 else 0.5
        for attempt in range(max_attempts_per_point):
            if attempt == 0:
                max_jitter = 0.20 * step_frac
                jitter = random.uniform(-max_jitter, max_jitter)
                t = max(0.0, min(1.0, base_t + jitter))
            else:
                max_jitter = (0.20 + 0.15 * attempt) * step_frac
                jitter = random.uniform(-max_jitter, max_jitter)
                t = max(0.0, min(1.0, base_t + jitter))

            px = int(round(x1 + t * dx))
            py = int(round(y1 + t * dy))

            too_close = False
            for ex_x, ex_y in all_reference + sampled:
                if math.hypot(px - ex_x, py - ex_y) < min_spacing:
                    too_close = True
                    break

            if not too_close:
                sampled.append((px, py))
                break

    return sampled


def get_default_hero_abilities() -> Dict[str, Dict[str, Any]]:
    return {
        'king': {'mode': 'random', 'seconds': 10},
        'queen': {'mode': 'random', 'seconds': 10},
        'warden': {'mode': 'random', 'seconds': 10},
        'RC': {'mode': 'random', 'seconds': 10},
        'prince': {'mode': 'random', 'seconds': 10},
    }

DEFAULT_STRATEGIES = [
    {
        'id': 'valkyries',
        'name': 'Valkyries',
        'builtin': True,
        'builtin_id': 3,
        'description': 'Four-edge drag deploy surrounding base with Valkyries.',
        'troops': [
            {
                'name': 'Valkyrie',
                'template': 'valkyrie.png',
                'is_custom_image': False,
                'deploy_style': 'four_edge_spam',
                'count': 0, # 0 means spam entire bar
                'delay': 0.15,
            }
        ],
        'deploy_heroes': True,
        'deploy_spells': True,
        'hero_abilities': get_default_hero_abilities(),
    },
    {
        'id': 'sneaky_goblins',
        'name': 'Sneaky Goblins',
        'builtin': True,
        'builtin_id': 1,
        'description': 'Long drag deploy for Sneaky Goblins farming resource collectors.',
        'troops': [
            {
                'name': 'Sneaky Goblin',
                'template': 'sneaky.png',
                'is_custom_image': False,
                'deploy_style': 'four_edge_spam',
                'count': 0,
                'delay': 0.15,
            }
        ],
        'deploy_heroes': True,
        'deploy_spells': True,
        'hero_abilities': get_default_hero_abilities(),
    },
    {
        'id': 'super_minions',
        'name': 'Super Minions',
        'builtin': True,
        'builtin_id': 2,
        'description': 'Rapid four-edge deployment of Super Minions.',
        'troops': [
            {
                'name': 'Super Minion',
                'template': 'superminion.png',
                'is_custom_image': False,
                'deploy_style': 'four_edge_spam',
                'count': 0,
                'delay': 0.15,
            }
        ],
        'deploy_heroes': True,
        'deploy_spells': True,
        'hero_abilities': get_default_hero_abilities(),
    },
    {
        'id': 'edrags',
        'name': 'Edrags',
        'builtin': True,
        'builtin_id': 4,
        'description': 'Even perimeter spacing along top edges for Electro Dragons.',
        'troops': [
            {
                'name': 'Electro Dragon',
                'template': 'edrag.png',
                'is_custom_image': False,
                'deploy_style': 'diamond_perimeter',
                'count': 12,
                'delay': 0.2,
            }
        ],
        'deploy_heroes': True,
        'deploy_spells': True,
        'hero_abilities': get_default_hero_abilities(),
    },
]

def _store_path() -> Path:
    return get_user_app_data_dir() / 'custom_strategies.json'

def get_custom_troops_dir() -> Path:
    d = get_user_app_data_dir() / 'custom_troops'
    ensure_dir(d)
    return d

def load_strategies() -> List[Dict[str, Any]]:
    path = _store_path()
    if not path.is_file():
        save_strategies(DEFAULT_STRATEGIES)
        return list(DEFAULT_STRATEGIES)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, list) and data:
            # Ensure built-ins exist
            existing_ids = {s.get('id') for s in data}
            for b in DEFAULT_STRATEGIES:
                if b['id'] not in existing_ids:
                    data.insert(0, b)
            # Ensure hero abilities exist on all strategies
            for s in data:
                if 'hero_abilities' not in s or not isinstance(s['hero_abilities'], dict):
                    s['hero_abilities'] = get_default_hero_abilities()
            return data
    except Exception as e:
        logger.warning('Failed to load custom strategies from %s: %s', path, e)
    return list(DEFAULT_STRATEGIES)

def save_strategies(strategies: List[Dict[str, Any]]) -> None:
    try:
        path = _store_path()
        atomic_write_text(path, json.dumps(strategies, indent=2), encoding='utf-8')
    except Exception as e:
        logger.error('Failed to save custom strategies to %s: %s', path, e)

def get_strategy_by_id(strategy_id: str) -> Optional[Dict[str, Any]]:
    for s in load_strategies():
        if s.get('id') == strategy_id:
            return s
    return None
