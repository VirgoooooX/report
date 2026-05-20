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

import api
from assistant_service import AssistantSessionStore
from assistant_tools import ToolValidationError, run_assistant_tool


class AssistantToolTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.get_conn()
        for table in (
            'sn_check_state_history',
            'sn_cp_results',
            'sn_check_results',
            'reports',
            'current_cp_definitions',
            'current_wf_definitions',
            'report_stats',
            'wf_results',
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
        self.conn.execute(
            """INSERT INTO current_wf_definitions (wf_num, wf_name, updated_run_id)
               VALUES ('10', 'Drop Test', ?)""",
            (rid,),
        )
        for cp_idx, cp_name in [(0, 'REL_T0'), (1, 'Drop20')]:
            self.conn.execute(
                """INSERT INTO current_cp_definitions
                   (wf_num, cp_idx, cp_name, test_idx, check_items, is_boundary, updated_run_id)
                   VALUES ('10', ?, ?, 0, '["FACT"]', ?, ?)""",
                (cp_idx, cp_name, 1 if cp_idx == 0 else 0, rid),
            )
        self.conn.execute(
            """INSERT INTO sn_check_state_history
               (wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                check_item, state_hash, status, failure_type, raw_value,
                first_report_id, first_report_date, last_seen_report_id, last_seen_report_date)
               VALUES ('10', 'R3', 'SN100', 'ER1-1', 0, 1, 0,
                       'FACT', '["fail","spec","FAIL","",""]', 'fail', 'spec', 'FAIL',
                       ?, '2026-05-20', ?, '2026-05-20')""",
            (rid, rid),
        )
        self.conn.execute(
            """INSERT INTO report_stats (report_id, total_spec_fails, total_strife_fails)
               VALUES (?, 1, 0)""",
            (rid,),
        )
        self.conn.execute(
            """INSERT INTO raw_check_item_records
               (serial_number, rel_event, effective_cp, item, status, end_time,
                failing_tests, station_id, version, test_params, source_file)
               VALUES ('SN100', 'Drop20', 'Drop20', 'FACT', 'FAIL',
                       '2026-05-20 10:00:00', 'drop_fail', 'ST01', '1.0.0',
                       '{"voltage": 3.1}', 'raw.csv')"""
        )
        self.conn.commit()
        return rid

    def test_tool_rejects_too_many_sns(self):
        with self.assertRaises(ToolValidationError):
            run_assistant_tool('lookup_sn_timeline', {'sns': [f'SN{i}' for i in range(51)]})

    def test_sn_tool_returns_stable_summary_shape(self):
        data = run_assistant_tool('lookup_sn_timeline', {'sns': ['SN100']})

        self.assertEqual(data['kind'], 'sn_timeline')
        self.assertFalse(data['truncated'])
        self.assertEqual(data['results'][0]['sn'], 'SN100')
        self.assertEqual(data['results'][0]['wfs'][0]['wf_num'], '10')
        self.assertEqual(data['results'][0]['wfs'][0]['fail_count'], 1)

    def test_raw_history_tool_limits_rows(self):
        data = run_assistant_tool('lookup_raw_history', {'sn': 'SN100', 'limit': 1})

        self.assertEqual(data['kind'], 'raw_history')
        self.assertEqual(data['sn'], 'SN100')
        self.assertEqual(len(data['records']), 1)
        self.assertIn('failing_tests', data['records'][0])

    def test_overview_tool_combines_overview_and_failure_stats(self):
        data = run_assistant_tool('get_overview', {})

        self.assertEqual(data['kind'], 'overview')
        self.assertEqual(data['report_date'], '2026-05-20')
        self.assertIn('failures', data)
        self.assertIn('top_failures', data['failures'])


class AssistantSessionTests(unittest.TestCase):
    def test_session_expires_after_idle_timeout(self):
        now = [1000.0]
        store = AssistantSessionStore(now_func=lambda: now[0], ttl_seconds=600)

        first = store.get_or_create(None)
        first_id = first['session_id']
        store.append(first_id, 'user', '查 SN100')

        now[0] += 599
        same = store.get_or_create(first_id)
        self.assertEqual(same['session_id'], first_id)
        self.assertEqual(len(same['messages']), 1)

        now[0] += 2
        fresh = store.get_or_create(first_id)
        self.assertNotEqual(fresh['session_id'], first_id)
        self.assertEqual(fresh['messages'], [])


class AssistantApiTests(unittest.TestCase):
    def test_chat_endpoint_uses_mock_provider_and_returns_tool_trace(self):
        client = api.app.test_client()

        resp = client.post('/api/assistant/chat', json={
            'message': '帮我查一下 SN100 的情况',
            'page_context': {'route': 'sn', 'query': {'mode': 'lookup'}},
        })

        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertIn('answer', payload)
        self.assertIn('session_id', payload)
        self.assertIn('expires_at', payload)
        self.assertEqual(payload['tool_calls'][0]['name'], 'lookup_sn_timeline')


if __name__ == '__main__':
    unittest.main()
