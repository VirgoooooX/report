import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

TEST_DB = tempfile.mktemp(suffix='.db')
os.environ['LLM_PROVIDER'] = 'mock'

import db
db.DB_PATH = TEST_DB
db.init_db()

from assistant_tools import run_assistant_tool
from llm_providers import MockProvider, OpenAICompatibleProvider


class AssistantCheckItemFailureRateTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.get_conn()
        for table in (
            'sn_check_state_history',
            'reports',
            'raw_check_item_records',
            'import_batches',
        ):
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()
        self.report_id = self._seed_report()

    def tearDown(self):
        self.conn.close()

    def _seed_report(self):
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES ('2026-05-20', 1, 1, 'daily.xlsx', 'M60 Daily Report_20260520.xlsx')"""
        )
        rid = cur.lastrowid
        batch = self.conn.execute(
            """INSERT INTO import_batches
               (import_date, created_at, file_count, record_count, valid_sn_count, status)
               VALUES ('2026-05-20', '2026-05-20T00:00:00', 1, 5, 5, 'completed')"""
        ).lastrowid

        config_by_sn = {
            'SN_R1_PASS': 'R1FNF',
            'SN_R1_FAIL': 'R1FNF',
            'SN_R2_FAIL_A': 'R2CNM',
            'SN_R2_FAIL_B': 'R2CNM',
            'SN_R2_FAIL_C': 'R2CNM',
        }
        for sn, config in config_by_sn.items():
            self.conn.execute(
                """INSERT INTO sn_check_state_history
                   (wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                    check_item, state_hash, status, failure_type, raw_value,
                    first_report_id, first_report_date, last_seen_report_id, last_seen_report_date)
                   VALUES ('20', ?, ?, '', 0, 0, 0, 'FACT', ?, 'pass', NULL, 'PASS',
                           ?, '2026-05-20', ?, '2026-05-20')""",
                (config, sn, f'{sn}:{config}', rid, rid),
            )

        raw_rows = [
            ('SN_R1_PASS', 'BT-OTA', 'PASS'),
            ('SN_R1_FAIL', 'BT-OTA', 'FAIL'),
            ('SN_R2_FAIL_A', 'BT-OTA', 'FAIL'),
            ('SN_R2_FAIL_B', 'BT-OTA', 'FAIL'),
            ('SN_R2_FAIL_C', 'BT-OTA', 'FAIL'),
        ]
        self.conn.executemany(
            """INSERT INTO raw_check_item_records
               (import_batch_id, import_date, serial_number, rel_event, effective_cp,
                item, status, end_time, failing_tests, station_id, version,
                test_params, source_file)
               VALUES (?, '2026-05-20', ?, 'REL_T0', 'REL_T0', ?, ?,
                       '2026-05-20 10:00:00', '', 'ST01', '1.0.0', NULL, 'bt-ota.csv')""",
            [(batch, sn, item, status) for sn, item, status in raw_rows],
        )
        self.conn.commit()
        return rid

    def test_check_item_failure_rate_groups_ota_by_config(self):
        data = run_assistant_tool('analyze_check_item_failure_rate', {
            'item': 'BT-OTA',
            'dimension': 'config',
        })

        self.assertEqual(data['kind'], 'check_item_failure_rate')
        self.assertEqual(data['item'], 'BT-OTA')
        self.assertEqual(data['dimension'], 'config')
        self.assertEqual(data['rows'][0]['key'], 'R2CNM')
        self.assertEqual(data['rows'][0]['failure_count'], 3)
        self.assertEqual(data['rows'][0]['total_count'], 3)
        self.assertEqual(data['rows'][0]['failure_rate'], 100.0)
        self.assertEqual(data['rows'][1]['key'], 'R1FNF')
        self.assertEqual(data['rows'][1]['failure_rate'], 50.0)

    def test_mock_provider_routes_ota_failure_rate_to_config_aggregation(self):
        result = MockProvider().chat(
            [{'role': 'user', 'content': '看看哪个Config的 OTA Failure rate比较高'}],
            tool_runner=run_assistant_tool,
        )

        self.assertEqual(result['tool_calls'][0]['name'], 'analyze_check_item_failure_rate')
        self.assertIn('R2CNM', result['answer'])
        self.assertIn('100.0%', result['answer'])
        self.assertIn('数据来源', result['answer'])

    def test_openai_compatible_provider_uses_model_generated_query_plan(self):
        class FakeProvider(OpenAICompatibleProvider):
            def __init__(self):
                super().__init__({'base_url': 'http://local.test', 'model': 'fake-model'})
                self.payloads = []

            def _post(self, payload):
                self.payloads.append(payload)
                if len(self.payloads) == 1:
                    return {
                        'choices': [{
                            'message': {
                                'content': (
                                    '{"tool":"analyze_check_item_failure_rate",'
                                    '"arguments":{"item":"BT-OTA","dimension":"config","limit":10}}'
                                )
                            }
                        }]
                    }
                return {
                    'choices': [{
                        'message': {'content': 'R2CNM 的 BT-OTA Failure Rate 最高：3F/3T，100.0%。'}
                    }]
                }

        calls = []

        def fake_tool_runner(name, args):
            calls.append((name, args))
            self.assertEqual(name, 'analyze_check_item_failure_rate')
            self.assertEqual(args, {'item': 'BT-OTA', 'dimension': 'config', 'limit': 10})
            return {
                'kind': 'check_item_failure_rate',
                'item': 'BT-OTA',
                'dimension': 'config',
                'rows': [{'key': 'R2CNM', 'failure_count': 3, 'total_count': 3, 'failure_rate': 100.0}],
            }

        provider = FakeProvider()
        result = provider.chat(
            [{'role': 'user', 'content': '看看哪个Config的 OTA Failure rate比较高'}],
            tool_runner=fake_tool_runner,
        )

        self.assertIn('query planner', provider.payloads[0]['messages'][-1]['content'])
        self.assertIn('Tool result JSON', provider.payloads[1]['messages'][-1]['content'])
        self.assertEqual(calls, [('analyze_check_item_failure_rate', {
            'item': 'BT-OTA',
            'dimension': 'config',
            'limit': 10,
        })])
        self.assertEqual(result['answer'], 'R2CNM 的 BT-OTA Failure Rate 最高：3F/3T，100.0%。')


if __name__ == '__main__':
    unittest.main()
