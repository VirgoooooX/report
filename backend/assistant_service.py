"""Conversation orchestration for the dashboard assistant."""

import datetime
import time
import uuid

from assistant_tools import TOOL_SCHEMAS, ToolValidationError, run_assistant_tool
from llm_providers import LLMProviderError, create_provider


DEFAULT_TTL_SECONDS = 600


def _utc_iso(epoch_seconds):
    return (
        datetime.datetime.fromtimestamp(epoch_seconds, tz=datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace('+00:00', 'Z')
    )


class AssistantSessionStore:
    def __init__(self, now_func=None, ttl_seconds=DEFAULT_TTL_SECONDS):
        self.now_func = now_func or time.time
        self.ttl_seconds = ttl_seconds
        self._sessions = {}

    def _new_session(self):
        now = self.now_func()
        session_id = uuid.uuid4().hex
        session = {
            'session_id': session_id,
            'messages': [],
            'last_seen': now,
            'expires_at': now + self.ttl_seconds,
        }
        self._sessions[session_id] = session
        return session

    def get_or_create(self, session_id):
        now = self.now_func()
        session = self._sessions.get(str(session_id or ''))
        if not session or now - float(session.get('last_seen') or 0) > self.ttl_seconds:
            return self._new_session()
        session['last_seen'] = now
        session['expires_at'] = now + self.ttl_seconds
        return session

    def append(self, session_id, role, content):
        session = self._sessions.get(session_id)
        if not session:
            session = self.get_or_create(None)
        session['messages'].append({'role': role, 'content': str(content or '')})
        session['messages'] = session['messages'][-12:]
        now = self.now_func()
        session['last_seen'] = now
        session['expires_at'] = now + self.ttl_seconds
        return session

    def expires_at_iso(self, session_id):
        session = self._sessions.get(session_id)
        return _utc_iso(session['expires_at']) if session else _utc_iso(self.now_func() + self.ttl_seconds)


class AssistantService:
    def __init__(self, session_store=None, provider_factory=None, tool_runner=None):
        self.session_store = session_store or AssistantSessionStore()
        self.provider_factory = provider_factory or create_provider
        self.tool_runner = tool_runner or run_assistant_tool

    def chat(self, message, session_id=None, page_context=None):
        message = str(message or '').strip()
        if not message:
            raise ToolValidationError('message is required.')
        if page_context is None:
            page_context = {}
        if not isinstance(page_context, dict):
            page_context = {}

        session = self.session_store.get_or_create(session_id)
        session = self.session_store.append(session['session_id'], 'user', message)

        provider = self.provider_factory()
        result = provider.chat(
            session['messages'],
            page_context=page_context,
            tool_schemas=TOOL_SCHEMAS,
            tool_runner=self.tool_runner,
        )
        answer = str(result.get('answer') or '').strip() or '没有生成可用回答。'
        session = self.session_store.append(session['session_id'], 'assistant', answer)
        return {
            'answer': answer,
            'session_id': session['session_id'],
            'tool_calls': _summarize_trace(result.get('tool_calls') or []),
            'expires_at': self.session_store.expires_at_iso(session['session_id']),
        }


def _summarize_trace(tool_calls):
    trace = []
    for call in tool_calls[:6]:
        result = call.get('result') if isinstance(call, dict) else None
        summary = ''
        if isinstance(result, dict):
            if 'count' in result:
                summary = f"{result.get('count')} records"
            elif result.get('kind') == 'sn_timeline':
                summary = f"{len(result.get('results', []))} SNs"
            elif result.get('kind') == 'overview':
                summary = f"report {result.get('report_date', '')}"
        trace.append({
            'name': call.get('name', ''),
            'arguments': call.get('arguments', {}),
            'summary': summary,
        })
    return trace


__all__ = [
    'AssistantService',
    'AssistantSessionStore',
    'DEFAULT_TTL_SECONDS',
    'LLMProviderError',
    'ToolValidationError',
]
