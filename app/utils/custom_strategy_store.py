"""Custom strategy data store and management."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.utils.common import get_user_app_data_dir, ensure_dir
from app.utils.logger import setup_logger

logger = setup_logger('CustomStrategiesStore')

STRATEGY_DEPLOY_PRESETS = [
    ('Diamond Perimeter (Edrag style)', 'diamond_perimeter'),
    ('Full Four-Edge Spam (Valkyrie style)', 'four_edge_spam'),
    ('Custom Deploy Zones (Fast 5-Point)', 'custom_zones'),
    ('Single Corner / Side Focus', 'corner_focus'),
]

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
        ensure_dir(path.parent)
        path.write_text(json.dumps(strategies, indent=2), encoding='utf-8')
    except Exception as e:
        logger.error('Failed to save custom strategies to %s: %s', path, e)

def get_strategy_by_id(strategy_id: str) -> Optional[Dict[str, Any]]:
    for s in load_strategies():
        if s.get('id') == strategy_id:
            return s
    return None
