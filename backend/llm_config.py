"""Persistent LLM provider configuration for the dashboard assistant.

Uses a flat configuration structure with preset shortcuts for common providers.
All non-mock providers use the OpenAI-compatible chat completions API.
"""

import json
import os
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime

from app_paths import DB_DIR

LLM_CONFIG_PATH = os.environ.get('REPORT_LLM_CONFIG_PATH') or os.path.join(DB_DIR, 'llm_config.json')

# ── Presets ──────────────────────────────────────────────────────────────────

PRESETS = {
    'openai':     {'base_url': 'https://api.openai.com',  'model': 'gpt-4.1-mini'},
    'deepseek':   {'base_url': 'https://api.deepseek.com', 'model': 'deepseek-v4-flash'},
    'openrouter': {'base_url': 'https://openrouter.ai/api', 'model': 'openai/gpt-4.1-mini'},
    'gemini':     {'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai', 'model': 'gemini-2.5-flash'},
    'lmstudio':   {'base_url': 'http://127.0.0.1:11235', 'model': 'local-model'},
    'llama_cpp':  {'base_url': 'http://127.0.0.1:8080',  'model': 'local-model'},
    'custom':     {'base_url': '', 'model': ''},
}

VALID_PRESETS = tuple(PRESETS.keys())

DEFAULT_LLM_CONFIG = {
    'provider': 'mock',           # 'mock' | 'openai_compatible'
    'preset': 'openai',
    'base_url': 'https://api.openai.com',
    'api_key': '',
    'model': 'gpt-4.1-mini',
    'timeout': 120,
    'max_tokens': 4096,
}

_CACHE = None
_CACHE_MTIME = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_int(value, default, lo=1, hi=99999):
    try:
        v = int(value)
        return max(lo, min(hi, v))
    except (TypeError, ValueError):
        return default


def _mask_api_key(key):
    """API Key 脱敏：长度>4 显示 ****+后4位，否则显示 ****。"""
    s = str(key or '')
    if len(s) > 4:
        return '****' + s[-4:]
    if s:
        return '****'
    return ''


def _migrate_legacy(raw):
    """一次性迁移旧格式（嵌套 openai/lmstudio/llama_cpp）到新扁平格式。"""
    if not isinstance(raw, dict):
        return raw
    # 检测旧格式特征：有 openai/lmstudio/llama_cpp 嵌套 dict，且无 preset 字段
    has_nested = any(isinstance(raw.get(k), dict) for k in ('openai', 'lmstudio', 'llama_cpp'))
    if not has_nested or 'preset' in raw:
        return raw

    old_provider = str(raw.get('provider', 'mock')).strip().lower()
    migrated = {'provider': 'mock', 'preset': 'openai'}

    section_map = {
        'openai': 'openai',
        'lmstudio': 'lmstudio',
        'lm_studio': 'lmstudio',
        'llama_cpp': 'llama_cpp',
        'llamacpp': 'llama_cpp',
    }

    preset = section_map.get(old_provider)
    if preset:
        section = raw.get(preset, {})
        migrated['provider'] = 'openai_compatible'
        migrated['preset'] = preset
        migrated['base_url'] = section.get('base_url', PRESETS.get(preset, {}).get('base_url', ''))
        migrated['api_key'] = section.get('api_key', '')
        migrated['model'] = section.get('model', PRESETS.get(preset, {}).get('model', ''))
        migrated['timeout'] = section.get('timeout', 120)
        migrated['max_tokens'] = section.get('max_tokens', 4096)
    elif old_provider == 'mock':
        migrated['provider'] = 'mock'
    return migrated


# ── Core ─────────────────────────────────────────────────────────────────────

def normalize_llm_config(value):
    """校验并规范化配置，合并默认值。"""
    raw = _migrate_legacy(value) if isinstance(value, dict) else {}

    cfg = deepcopy(DEFAULT_LLM_CONFIG)

    # Provider
    provider = str(raw.get('provider', 'mock')).strip().lower()
    cfg['provider'] = provider if provider in ('mock', 'openai_compatible') else 'mock'

    # Preset
    preset = str(raw.get('preset', 'openai')).strip().lower()
    cfg['preset'] = preset if preset in VALID_PRESETS else 'openai'

    # Connection fields
    base_url = str(raw.get('base_url', '')).strip().rstrip('/')
    cfg['base_url'] = base_url or DEFAULT_LLM_CONFIG['base_url']
    cfg['api_key'] = str(raw.get('api_key', '')).strip()
    cfg['model'] = str(raw.get('model', '')).strip() or DEFAULT_LLM_CONFIG['model']
    cfg['timeout'] = _safe_int(raw.get('timeout'), 120, 10, 600)
    cfg['max_tokens'] = _safe_int(raw.get('max_tokens'), 4096, 64, 65536)

    return cfg


def load_llm_config():
    """从文件读取 LLM 配置，带文件修改时间缓存。"""
    global _CACHE, _CACHE_MTIME
    try:
        mtime = os.path.getmtime(LLM_CONFIG_PATH)
    except OSError:
        mtime = None
    if _CACHE is not None and _CACHE_MTIME == mtime:
        return deepcopy(_CACHE)
    try:
        with open(LLM_CONFIG_PATH, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        data = {}
    cfg = normalize_llm_config(data)
    _CACHE = cfg
    _CACHE_MTIME = mtime
    return deepcopy(cfg)


def save_llm_config(value):
    """校验 + 写入配置文件，更新缓存。"""
    global _CACHE, _CACHE_MTIME
    os.makedirs(os.path.dirname(LLM_CONFIG_PATH), exist_ok=True)
    cfg = normalize_llm_config(value)
    payload = {
        **cfg,
        'updated_at': datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    }
    with open(LLM_CONFIG_PATH, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    try:
        _CACHE_MTIME = os.path.getmtime(LLM_CONFIG_PATH)
    except OSError:
        _CACHE_MTIME = None
    _CACHE = normalize_llm_config(payload)
    return deepcopy(_CACHE)


def get_safe_llm_config():
    """返回脱敏配置 + 预设列表，供前端使用。"""
    cfg = load_llm_config()
    cfg['api_key'] = _mask_api_key(cfg.get('api_key'))
    cfg['presets'] = deepcopy(PRESETS)
    return cfg


def get_presets():
    """返回预设列表。"""
    return deepcopy(PRESETS)


def fetch_models(base_url, api_key='', timeout=10):
    """调用 OpenAI 兼容端点 /v1/models 获取可用模型列表。"""
    base = str(base_url or '').strip().rstrip('/')
    if not base:
        return []
    url = f'{base}/v1/models' if not base.endswith('/v1') else f'{base}/models'
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f'获取模型列表失败: {exc}') from exc

    models = []
    for item in body.get('data', []):
        model_id = item.get('id') or ''
        if model_id:
            models.append(model_id)
    models.sort()
    return models
