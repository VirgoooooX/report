"""LLM provider adapters for the dashboard assistant."""

import json
import os
import re
import urllib.error
import urllib.request

from assistant_tools import SN_RE, TOOL_SCHEMAS, run_assistant_tool
from llm_config import load_llm_config


SYSTEM_INSTRUCTIONS = """You are an assistant for an engineering reliability dashboard.
Answer in concise Chinese by default. Ground every factual answer in tool results.
If the user asks a vague question and the page context does not contain the needed
SN, WF, config, or FA filter, ask for the missing detail instead of guessing.
Never claim data that did not come from a tool result."""

LOCAL_MODEL_INSTRUCTIONS = SYSTEM_INSTRUCTIONS + """
Do not output chain-of-thought, hidden reasoning, or reasoning_content.
Put the final user-facing answer in message.content only.
If the model supports thinking mode, disable it."""


class LLMProviderError(RuntimeError):
    """Provider configuration or transport error."""


def _safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _tool_names(tool_schemas=None):
    return {
        schema.get('name')
        for schema in (tool_schemas or TOOL_SCHEMAS)
        if isinstance(schema, dict) and schema.get('name')
    }


def _extract_json_object(text):
    text = str(text or '').strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        value = json.loads(text[start:end + 1])
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _normalize_tool_plan(plan, tool_schemas=None):
    if not isinstance(plan, dict):
        return '', {}
    if str(plan.get('action') or '').casefold() in {'none', 'no_tool', 'answer'}:
        return '', {}

    name = str(plan.get('tool') or plan.get('name') or '').strip()
    if name not in _tool_names(tool_schemas):
        return '', {}
    args = plan.get('arguments') or plan.get('args') or {}
    if not isinstance(args, dict):
        args = {}
    return name, _clean_args(args)


def _extract_sn_candidates(text):
    ignored = {'WF', 'R1FNF', 'R2CNM', 'R3', 'R4', 'REL_T0'}
    matches = []
    for match in SN_RE.findall(text or ''):
        token = match.strip().upper()
        if token in ignored or token.startswith('WF'):
            continue
        if token not in matches:
            matches.append(token)
    return matches[:10]


def _extract_wf(text):
    match = re.search(r'\bWF\s*([0-9]+(?:\.[0-9]+)?)\b', text or '', re.IGNORECASE)
    if match:
        return match.group(1)
    return ''


def _extract_config(text):
    match = re.search(r'\b(R1FNF|R2CNM|R3|R4)\b', text or '', re.IGNORECASE)
    return match.group(1).upper() if match else ''


def _extract_check_item(text):
    lower = (text or '').casefold()
    checks = [
        ('BT-OTA', ('bt-ota', 'bt ota', 'ota')),
        ('Touch-CAL-Post', ('touch-cal-post', 'touch cal post')),
        ('Charging', ('charging', 'charge', '充电')),
        ('Cosmetic', ('cosmetic', '外观')),
        ('FACT', ('fact',)),
        ('ISB', ('isb',)),
    ]
    for item, aliases in checks:
        if any(alias in lower for alias in aliases):
            return item
    return ''


def _first_page_value(page_context, *keys):
    query = {}
    if isinstance(page_context, dict):
        query = page_context.get('query') or {}
    for key in keys:
        value = query.get(key)
        if value:
            return value
    return ''


def _select_tool_call(message, page_context=None):
    """Offline fallback for the mock provider and malformed planner output."""
    lower = (message or '').casefold()
    page_context = page_context or {}

    wf = _extract_wf(message) or _first_page_value(page_context, 'wf')
    config = _extract_config(message) or _first_page_value(page_context, 'config')
    sns = _extract_sn_candidates(message)
    if not sns:
        tags = _first_page_value(page_context, 'tags', 'sns', 'q')
        if tags:
            sns = [s.strip() for s in str(tags).split(',') if s.strip()]

    check_item = _extract_check_item(message) or _first_page_value(page_context, 'item', 'check_item')
    asks_failure_rate = any(k in lower for k in ('failure rate', 'fail rate', '失败率', '失败 rate', 'failure率'))
    asks_rank = any(k in lower for k in ('哪个', '哪個', '最高', '比较高', '較高', 'top', 'rank', '排序'))
    if check_item and (asks_failure_rate or ('fail' in lower and asks_rank) or ('失败' in lower and asks_rank)):
        dimension = 'config'
        if re.search(r'\bwf\b', lower) or '按wf' in lower:
            dimension = 'wf'
        elif 'item' in lower or 'check item' in lower or '测试项' in lower:
            dimension = 'item'
        return 'analyze_check_item_failure_rate', {
            'item': check_item,
            'dimension': dimension,
            'limit': 10,
        }

    if any(k in lower for k in ('overview', '概览', '总览', '失败率', '进度')):
        return 'get_overview', {}
    if any(k in lower for k in ('raw', 'history', '历史', '原始')):
        if sns:
            return 'lookup_raw_history', {'sn': sns[0], 'limit': 10}
        return '', {}
    if 'fa' in lower or 'failure analysis' in lower or 'tracker' in lower:
        if sns or wf or config:
            return 'lookup_fa_records', {'sns': sns, 'wf': wf, 'config': config, 'limit': 20}
        return '', {}
    if wf:
        return 'query_wf_config', {'wf': wf, 'config': config, 'limit': 25}
    if sns:
        return 'lookup_sn_timeline', {'sns': sns}
    return '', {}


def _clean_args(args):
    return {k: v for k, v in (args or {}).items() if v not in ('', [], None)}


def _summarize_tool_result(name, result):
    if name == 'lookup_sn_timeline':
        rows = []
        for item in result.get('results', []):
            if not item.get('found'):
                rows.append(f"{item.get('sn')} 没有查到当前记录")
                continue
            wf_bits = []
            for wf in item.get('wfs', []):
                fail_text = ''
                if wf.get('fail_count'):
                    fail_text = f"，失败 {wf.get('fail_count')} 项（Spec {wf.get('spec_fail_count', 0)} / Strife {wf.get('strife_fail_count', 0)}）"
                wf_bits.append(f"WF{wf.get('wf_num')} {wf.get('config')} 当前到 {wf.get('current_cp_name') or wf.get('current_cp_idx')}{fail_text}")
            rows.append(f"{item.get('sn')}（{item.get('unit_num') or '无 Mark'}）：{'；'.join(wf_bits) if wf_bits else '没有活动 WF'}")
        return "查询了 SN 当前进度：\n" + "\n".join(f"- {r}" for r in rows)

    if name == 'query_wf_config':
        summary = result.get('summary', {})
        failure_sns = [
            s for s in result.get('sns', [])
            if (s.get('spec_fails') or 0) + (s.get('strife_fails') or 0) > 0
        ]
        answer = (
            f"查询了 WF{result.get('wf_num')} {result.get('config')}："
            f"共 {summary.get('total_sns', 0)} 台，返回 {summary.get('returned_sns', 0)} 台，"
            f"总 CP 数 {summary.get('total_cps', 0)}。"
        )
        if failure_sns:
            answer += " 有失败记录的 SN 包括：" + "、".join(s.get('sn', '') for s in failure_sns[:10])
        if result.get('truncated'):
            answer += " 结果已截断，仅展示前几条。"
        return answer

    if name == 'lookup_fa_records':
        records = result.get('records', [])
        if not records:
            return "查询了 FA Tracker，但没有找到匹配记录。"
        lines = []
        for record in records[:8]:
            lines.append(
                f"{record.get('SN', '')} WF{record.get('WF', '')} {record.get('Config', '')} "
                f"{record.get('Failed Test', '')}：{record.get('Failure Symptom / Failure Message', '')}"
            )
        tail = " 结果已截断。" if result.get('truncated') else ''
        return f"查询了 FA Tracker，共 {result.get('count', len(records))} 条匹配记录：\n" + "\n".join(f"- {line}" for line in lines) + tail

    if name == 'lookup_raw_history':
        records = result.get('records', [])
        if not records:
            return f"查询了 {result.get('sn') or '该对象'} 的 Raw History，但没有找到记录。"
        latest = records[0]
        return (
            f"查询了 {result.get('sn')} 的 Raw History，共 {result.get('count', len(records))} 条。"
            f"最新记录：{latest.get('end_time')} {latest.get('item')} {latest.get('status')} "
            f"@ {latest.get('effective_cp') or latest.get('rel_event')}。"
        )

    if name == 'get_overview':
        failures = result.get('failures', {})
        top = failures.get('top_failures') or []
        top_text = ''
        if top:
            first = top[0]
            top_text = f"最高失败项是 WF{first.get('wf')} {first.get('cfg')} {first.get('test')}，失败率 {first.get('rate')}%。"
        return (
            f"查询了最新概览，报告日期 {result.get('report_date') or '未知'}。"
            f"今日推进 {result.get('daily_updates', {}).get('total_changes', 0)} 个 WF/Config。{top_text}"
        )

    if name == 'analyze_check_item_failure_rate':
        rows = result.get('rows') or []
        item = result.get('item') or 'Check Item'
        dimension = result.get('dimension') or 'config'
        dim_label = {'config': 'Config', 'wf': 'WF', 'item': 'Check Item'}.get(dimension, dimension)
        if not rows:
            return f"查询了 {item} 按 {dim_label} 的 Failure Rate，但没有找到可汇总的数据。"
        leader = rows[0]
        lines = [
            f"{r.get('key')}: {r.get('failure_count')}F/{r.get('total_count')}T，{r.get('failure_rate')}%"
            for r in rows[:5]
        ]
        return (
            f"{item} 按 {dim_label} 看，Failure Rate 最高的是 {leader.get('key')}："
            f"{leader.get('failure_count')}F/{leader.get('total_count')}T，{leader.get('failure_rate')}%。\n"
            + "\n".join(f"- {line}" for line in lines)
        )

    return "查询完成。"


class MockProvider:
    """Deterministic provider for local tests and offline development."""

    def chat(self, messages, page_context=None, tool_schemas=None, tool_runner=None):
        latest = messages[-1]['content'] if messages else ''
        tool_runner = tool_runner or run_assistant_tool
        name, args = _select_tool_call(latest, page_context)

        if not name:
            return {
                'answer': '我需要更多条件才能查：请提供 SN/Mark、WF+Config，或者说明要看 FA、Raw History 还是整体概览。',
                'tool_calls': [],
            }

        result = tool_runner(name, _clean_args(args))
        return {
            'answer': _summarize_tool_result(name, result) + f"\n\n数据来源：调用 `{name}`。",
            'tool_calls': [{'name': name, 'arguments': args, 'result': result}],
        }


class OpenAICompatibleProvider:
    """Unified provider for all OpenAI-compatible chat endpoints.

    Works with OpenAI, DeepSeek, OpenRouter, Gemini, LM Studio, llama.cpp,
    and any custom endpoint that supports /v1/chat/completions.

    Tool planning is handled by the model through a small JSON planning prompt,
    then this adapter validates and executes the selected read-only tool.
    """

    def __init__(self, config=None):
        cfg = config or {}
        base_url = str(cfg.get('base_url', 'https://api.openai.com')).strip()
        self.base_url = base_url.rstrip('/')
        self.model = str(cfg.get('model', 'gpt-4.1-mini')).strip() or 'gpt-4.1-mini'
        self.api_key = str(cfg.get('api_key', '')).strip()
        try:
            self.timeout = int(cfg.get('timeout', 120))
        except (ValueError, TypeError):
            self.timeout = 120
        try:
            self.max_tokens = int(cfg.get('max_tokens', 4096))
        except (ValueError, TypeError):
            self.max_tokens = 4096





    @property
    def chat_url(self):
        if self.base_url.endswith('/v1'):
            return f'{self.base_url}/chat/completions'
        return f'{self.base_url}/v1/chat/completions'

    def _post(self, payload):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        req = urllib.request.Request(
            self.chat_url,
            data=_safe_json(payload).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')
            raise LLMProviderError(f'llama.cpp request failed: HTTP {exc.code} {detail}') from exc
        except urllib.error.URLError as exc:
            raise LLMProviderError(f'llama.cpp request failed: {exc.reason}') from exc

    def _plan_tool_call(self, messages, page_context=None, tool_schemas=None):
        latest = messages[-1]['content'] if messages else ''
        planning_prompt = (
            "/no_think\n"
            "You are the query planner for an engineering reliability dashboard assistant.\n"
            "Read the user message and page context, then decide whether one read-only tool is needed.\n"
            "Choose a tool by semantic intent, not by exact keyword matching.\n"
            "Examples of intent mapping:\n"
            "- questions asking which Config/WF/item has higher OTA, BT-OTA, FACT, ISB, Charging, Cosmetic, or Touch-CAL failure rate -> analyze_check_item_failure_rate\n"
            "- questions about one or more SNs/marks -> lookup_sn_timeline\n"
            "- questions about raw station/check-item records -> lookup_raw_history\n"
            "- questions about FA tracker records -> lookup_fa_records\n"
            "- broad dashboard progress/failure overview -> get_overview\n"
            "- a specific WF/Config population summary -> query_wf_config\n"
            "Return JSON only, with this shape: {\"tool\":\"tool_name_or_empty\",\"arguments\":{...}}.\n"
            "Use an empty tool when the user is chatting or when required identifiers are missing.\n\n"
            f"Available tools JSON: {_safe_json(tool_schemas or TOOL_SCHEMAS)}\n"
            f"Page context JSON: {_safe_json(page_context or {})}\n"
            f"Conversation JSON: {_safe_json(messages[-6:])}\n"
            f"Current user message: {latest}\n"
        )
        response = self._post({
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': LOCAL_MODEL_INSTRUCTIONS},
                {'role': 'user', 'content': planning_prompt},
            ],
            'temperature': 0,
            'max_tokens': min(self.max_tokens, 1024),
            'reasoning': {'effort': 'none'},
            'chat_template_kwargs': {'enable_thinking': False},
            'stream': False,
        })
        plan = _extract_json_object(_extract_chat_completion_text(response))
        if plan:
            return _normalize_tool_plan(plan, tool_schemas)
        return _select_tool_call(latest, page_context)

    def chat(self, messages, page_context=None, tool_schemas=None, tool_runner=None):
        latest = messages[-1]['content'] if messages else ''
        tool_runner = tool_runner or run_assistant_tool
        schemas = tool_schemas or TOOL_SCHEMAS
        name, args = self._plan_tool_call(messages, page_context, schemas)

        if not name:
            response = self._post({
                'model': self.model,
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': self.max_tokens,
            })
            answer = _extract_chat_completion_text(response)
            return {
                'answer': answer or '（模型返回了空结果）',
                'tool_calls': [],
            }

        clean_args = _clean_args(args)
        result = tool_runner(name, clean_args)
        prompt = (
            "/no_think\n"
            f"User question: {latest}\n"
            f"Page context JSON: {_safe_json(page_context or {})}\n"
            f"Tool used: {name}\n"
            f"Tool arguments JSON: {_safe_json(clean_args)}\n"
            f"Tool result JSON: {_safe_json(result)}\n\n"
            "请只根据 Tool result JSON 用中文回答。"
            "如果没有数据，请明确说没有查到。"
            "最后用一句话说明数据来源，例如：数据来源：调用 lookup_sn_timeline。"
        )
        response = self._post({
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': LOCAL_MODEL_INSTRUCTIONS},
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.2,
            'max_tokens': self.max_tokens,
            'reasoning': {'effort': 'none'},
            'chat_template_kwargs': {'enable_thinking': False},
            'stream': False,
        })
        answer = _extract_chat_completion_text(response)
        return {
            'answer': answer or (_summarize_tool_result(name, result) + f"\n\n数据来源：调用 `{name}`。"),
            'tool_calls': [{'name': name, 'arguments': clean_args, 'result': result}],
        }





def _extract_chat_completion_text(response):
    choices = response.get('choices') or []
    if not choices:
        return ''
    message = choices[0].get('message') or {}
    content = message.get('content')
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get('text') or item.get('content') or ''))
            else:
                parts.append(str(item))
        return ''.join(parts).strip()
    return ''


def create_provider():
    """Create an LLM provider based on the persisted configuration."""
    cfg = load_llm_config()
    provider = cfg.get('provider', 'mock').strip().lower()
    if provider == 'openai_compatible':
        return OpenAICompatibleProvider(config=cfg)
    # Env-var fallback for backward compatibility
    env_provider = os.environ.get('LLM_PROVIDER', '').strip().lower()
    if env_provider and env_provider not in ('mock', ''):
        return OpenAICompatibleProvider(config=cfg)
    return MockProvider()
