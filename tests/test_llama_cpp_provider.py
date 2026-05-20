import json
import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import llm_providers


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class LlamaCppProviderTests(unittest.TestCase):
    def test_create_provider_accepts_llama_cpp_alias(self):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'llama.cpp'}, clear=False):
            provider = llm_providers.create_provider()

        self.assertIsInstance(provider, llm_providers.LlamaCppProvider)

    def test_llama_cpp_posts_tool_result_to_chat_completions_endpoint(self):
        captured = {}

        def fake_urlopen(req, timeout):
            captured['url'] = req.full_url
            captured['timeout'] = timeout
            captured['headers'] = dict(req.header_items())
            captured['payload'] = json.loads(req.data.decode('utf-8'))
            return _FakeResponse({
                'choices': [{
                    'message': {
                        'content': '本地模型总结：SN100 当前有 1 个 Spec failure。'
                    }
                }]
            })

        def fake_tool_runner(name, args):
            self.assertEqual(name, 'lookup_sn_timeline')
            self.assertEqual(args, {'sns': ['SN100']})
            return {
                'kind': 'sn_timeline',
                'results': [{
                    'sn': 'SN100',
                    'found': True,
                    'wfs': [{
                        'wf_num': '10',
                        'config': 'R3',
                        'current_cp_name': 'Drop20',
                        'fail_count': 1,
                        'spec_fail_count': 1,
                        'strife_fail_count': 0,
                    }],
                }],
            }

        env = {
            'LLAMA_CPP_BASE_URL': 'http://127.0.0.1:8080',
            'LLAMA_CPP_MODEL': 'local-model',
        }
        with patch.dict(os.environ, env, clear=False), patch('urllib.request.urlopen', fake_urlopen):
            provider = llm_providers.LlamaCppProvider()
            result = provider.chat(
                [{'role': 'user', 'content': '帮我查 SN100'}],
                page_context={'route': 'sn'},
                tool_runner=fake_tool_runner,
            )

        self.assertEqual(captured['url'], 'http://127.0.0.1:8080/v1/chat/completions')
        self.assertEqual(captured['payload']['model'], 'local-model')
        self.assertIn('Tool result JSON', captured['payload']['messages'][-1]['content'])
        self.assertEqual(result['answer'], '本地模型总结：SN100 当前有 1 个 Spec failure。')
        self.assertEqual(result['tool_calls'][0]['name'], 'lookup_sn_timeline')


class LMStudioProviderTests(unittest.TestCase):
    def test_create_provider_accepts_lmstudio_alias(self):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'lmstudio'}, clear=False):
            provider = llm_providers.create_provider()

        self.assertIsInstance(provider, llm_providers.LMStudioProvider)

    def test_lmstudio_defaults_to_screenshot_port_11235(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = llm_providers.LMStudioProvider()

        self.assertEqual(provider.chat_url, 'http://127.0.0.1:11235/v1/chat/completions')

    def test_lmstudio_supports_reachable_network_base_url(self):
        with patch.dict(os.environ, {'LMSTUDIO_BASE_URL': 'http://169.254.83.107:11235'}, clear=True):
            provider = llm_providers.LMStudioProvider()

        self.assertEqual(provider.chat_url, 'http://169.254.83.107:11235/v1/chat/completions')


if __name__ == '__main__':
    unittest.main()
