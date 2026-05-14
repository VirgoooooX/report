"""Persistent custom parsing/display rules for the dashboard."""

import json
import os
from copy import deepcopy
from datetime import datetime

from app_paths import DB_DIR


RULES_PATH = os.environ.get('REPORT_CUSTOM_RULES_PATH') or os.path.join(DB_DIR, 'custom_rules.json')

DEFAULT_RULES = {
    'parse': {
        'spec_fill_colors': ['FF0000'],
        'strife_fill_colors': ['FFFF00'],
        'spec_font_colors': ['FF9C0006'],
        'ignore_wfs': [],
        'config_aliases': {},
    },
    'display': {
        'project_name': '',
        'wf_aliases': {},
        'hidden_wfs': [],
        'config_order': ['R1FNF', 'R2CNM', 'R3', 'R4'],
        'status_labels': {
            'pass': 'Pass',
            'spec_fail': 'Spec Fail',
            'strife_fail': 'Strife Fail',
            'pending': 'Pending',
            'skip': 'Skip',
        },
    },
    'matching': {
        'location_mappings': [
            {'daily_report': 'Touch-CAL-Post', 'fa_tracker': 'Touch Post', 'mode': 'exact'},
            {'daily_report': 'Cosmetic', 'fa_tracker': 'Home, IR Lens, Power, System, TV, Play, Vol+, Vol-', 'mode': 'multi'},
        ],
    },
}
_CACHE = None
_CACHE_MTIME = None


def _merge(default, value):
    if isinstance(default, dict):
        merged = deepcopy(default)
        if isinstance(value, dict):
            for key, item in value.items():
                merged[key] = _merge(default.get(key), item) if key in default else item
        return merged
    return value if value is not None else deepcopy(default)


def _normalize_color(value):
    color = str(value or '').strip().upper().replace('#', '')
    if len(color) == 6:
        return color
    if len(color) == 8:
        return color[-6:]
    return color


def normalize_rules(value):
    rules = _merge(DEFAULT_RULES, value or {})
    parse = rules.setdefault('parse', {})
    display = rules.setdefault('display', {})
    matching = rules.setdefault('matching', {})

    # Normalize location_mappings
    raw_mappings = matching.get('location_mappings', [])
    normalized_mappings = []
    for m in (raw_mappings if isinstance(raw_mappings, list) else []):
        if not isinstance(m, dict):
            continue
        dr = str(m.get('daily_report', '')).strip()
        fa = str(m.get('fa_tracker', '')).strip()
        mode = str(m.get('mode', 'exact')).strip().lower()
        if mode not in ('exact', 'contains', 'multi'):
            mode = 'exact'
        if dr and fa:
            normalized_mappings.append({'daily_report': dr, 'fa_tracker': fa, 'mode': mode})
    matching['location_mappings'] = normalized_mappings

    for key in ('spec_fill_colors', 'strife_fill_colors', 'spec_font_colors'):
        parse[key] = [
            c for c in (_normalize_color(v) for v in parse.get(key, []))
            if len(c) >= 6
        ]

    parse['ignore_wfs'] = [
        str(v).strip().replace('WF', '').replace('wf', '')
        for v in parse.get('ignore_wfs', [])
        if str(v).strip()
    ]
    parse['config_aliases'] = {
        str(k).strip(): str(v).strip()
        for k, v in dict(parse.get('config_aliases') or {}).items()
        if str(k).strip() and str(v).strip()
    }
    display['wf_aliases'] = {
        str(k).strip().replace('WF', '').replace('wf', ''): str(v).strip()
        for k, v in dict(display.get('wf_aliases') or {}).items()
        if str(k).strip() and str(v).strip()
    }
    display['hidden_wfs'] = [
        str(v).strip().replace('WF', '').replace('wf', '')
        for v in display.get('hidden_wfs', [])
        if str(v).strip()
    ]
    display['config_order'] = [
        str(v).strip()
        for v in display.get('config_order', [])
        if str(v).strip()
    ] or deepcopy(DEFAULT_RULES['display']['config_order'])
    return rules


def load_rules():
    global _CACHE, _CACHE_MTIME
    try:
        mtime = os.path.getmtime(RULES_PATH)
    except OSError:
        mtime = None
    if _CACHE is not None and _CACHE_MTIME == mtime:
        return deepcopy(_CACHE)
    try:
        with open(RULES_PATH, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        data = {}
    rules = normalize_rules(data)
    _CACHE = rules
    _CACHE_MTIME = mtime
    return deepcopy(rules)


def save_rules(value):
    global _CACHE, _CACHE_MTIME
    os.makedirs(os.path.dirname(RULES_PATH), exist_ok=True)
    rules = normalize_rules(value)
    payload = {
        **rules,
        'updated_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    }
    with open(RULES_PATH, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    try:
        _CACHE_MTIME = os.path.getmtime(RULES_PATH)
    except OSError:
        _CACHE_MTIME = None
    _CACHE = normalize_rules(payload)
    return payload


def color_matches(rgb, colors):
    normalized = _normalize_color(rgb)
    return any(_normalize_color(color) in normalized for color in colors)


def failure_type_for_colors(fill_rgb='', font_rgb=''):
    rules = load_rules().get('parse', {})
    if color_matches(fill_rgb, rules.get('spec_fill_colors', [])):
        return 'spec'
    if color_matches(fill_rgb, rules.get('strife_fill_colors', [])):
        return 'strife'
    if color_matches(font_rgb, rules.get('spec_font_colors', [])):
        return 'spec'
    return None


def is_wf_ignored(wf_num):
    ignored = set(load_rules().get('parse', {}).get('ignore_wfs', []))
    return str(wf_num or '').strip().replace('WF', '').replace('wf', '') in ignored


def resolve_config_alias(value):
    text = str(value or '').strip()
    if not text:
        return text
    aliases = load_rules().get('parse', {}).get('config_aliases', {})
    return aliases.get(text, text)


def normalize_location_for_matching(daily_location, fa_location):
    """Check if two location values should be considered a match based on mapping rules.
    Returns True if they match (either exact equality or via mapping rules).
    """
    if daily_location == fa_location:
        return True
    if not daily_location or not fa_location:
        return False
    mappings = load_rules().get('matching', {}).get('location_mappings', [])
    for m in mappings:
        dr = m.get('daily_report', '')
        fa = m.get('fa_tracker', '')
        mode = m.get('mode', 'exact')
        if mode == 'exact':
            if daily_location == dr and fa_location == fa:
                return True
            if daily_location == fa and fa_location == dr:
                return True
        elif mode == 'contains':
            if daily_location == dr and fa_location == fa:
                return True
            if fa_location.lower() in daily_location.lower():
                return True
            if daily_location.lower() in fa_location.lower():
                return True
        elif mode == 'multi':
            fa_values = [v.strip() for v in fa.split(',') if v.strip()]
            if daily_location == dr and fa_location in fa_values:
                return True
    return False


def get_location_canonical(location, source='daily_report'):
    """Get canonical location value for matching key generation.
    Maps location values to a canonical form so both sides produce the same key.
    source: 'daily_report' or 'fa_tracker'
    
    Modes:
    - exact: daily_report value and fa_tracker value are direct equivalents
    - contains: fa_tracker value is a substring of daily_report value (or vice versa)
    - multi: one daily_report value maps to multiple fa_tracker values (comma-separated)
    
    Strategy: For each mapping rule, both sides map to the same canonical value
    (the daily_report side). This ensures the keys match.
    """
    loc = str(location or '').strip()
    if not loc:
        return loc
    mappings = load_rules().get('matching', {}).get('location_mappings', [])
    for m in mappings:
        dr = m.get('daily_report', '')
        fa = m.get('fa_tracker', '')
        mode = m.get('mode', 'exact')
        if mode == 'exact':
            if source == 'daily_report' and loc == dr:
                return dr  # already canonical
            if source == 'fa_tracker' and loc == fa:
                return dr  # map to canonical
        elif mode == 'contains':
            if source == 'daily_report' and loc == dr:
                return dr  # already canonical
            if source == 'fa_tracker' and loc == fa:
                return dr  # map to canonical
            # fa_tracker location is a substring of daily_report value
            if source == 'fa_tracker' and loc.lower() in dr.lower():
                return dr
            if source == 'daily_report' and fa.lower() in loc.lower():
                return loc
        elif mode == 'multi':
            # fa_tracker field contains comma-separated list of values
            fa_values = [v.strip() for v in fa.split(',') if v.strip()]
            if source == 'daily_report' and loc == dr:
                return dr  # already canonical
            if source == 'fa_tracker' and loc in fa_values:
                return dr  # map any of the fa values to canonical
    return loc
