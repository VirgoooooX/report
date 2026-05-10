import unittest
import tempfile
import os
import json
import sys

# 关键：在导入 api 之前设置 DB_PATH
TEST_DB = tempfile.mktemp(suffix='.db')

# Monkey-patch db.DB_PATH
import db
db.DB_PATH = TEST_DB
db.init_db()

import api


class ApiConsistencyTests(unittest.TestCase):
    """Consistency check: dashboard overview and failure stats use same config totals."""

    def setUp(self):
        """种子数据到测试 DB。"""
        # 清理以前的测试
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM sn_cp_results")
        self.conn.execute("DELETE FROM sn_check_results")
        self.conn.execute("DELETE FROM report_cps")
        self.conn.execute("DELETE FROM report_test_names")
        self.conn.execute("DELETE FROM wf_results")
        self.conn.execute("DELETE FROM report_stats")
        self.conn.execute("DELETE FROM sn_progress")
        self.conn.execute("DELETE FROM reports")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _seed_report(self, report_date='2025-01-01'):
        """创建报告并插入报告级元数据。返回 report_id。"""
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path)
               VALUES (?, 1, 1, 'test.xlsx')""",
            (report_date,),
        )
        rid = cur.lastrowid
        self.conn.commit()
        return rid

    def test_dashboard_and_failure_stats_use_same_config_totals(self):
        """Seed data and verify both endpoints report identical by_config failure stats."""
        rid = self._seed_report()

        # Insert basic sn_cp_results so both endpoints have data
        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN001', '', 0, 0, 'pass', NULL, 1, 1)""",
            (rid,),
        )
        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN002', '', 0, 0, 'spec_fail', 'spec', 1, 1)""",
            (rid,),
        )
        # Also need sn_progress for dashboard overview
        self.conn.execute(
            """INSERT INTO sn_progress
               (report_id, wf_num, config, sn, current_cp_idx)
               VALUES (?, '16.1', 'R3', 'SN001', 0)""",
            (rid,),
        )
        self.conn.execute(
            """INSERT INTO sn_progress
               (report_id, wf_num, config, sn, current_cp_idx)
               VALUES (?, '16.1', 'R3', 'SN002', 0)""",
            (rid,),
        )
        self.conn.commit()

        client = api.app.test_client()
        overview = client.get('/api/dashboard/overview')
        stats = client.get('/api/failures/stats')

        self.assertEqual(overview.status_code, 200)
        self.assertEqual(stats.status_code, 200)

        overview_json = overview.get_json() or {}
        stats_json = stats.get_json() or {}
        self.assertEqual(
            overview_json.get('failures', {}).get('by_config', {}),
            stats_json.get('by_config', {}),
        )

    def test_summary_in_progress(self):
        """WF 16.1, config R3, Test1 CP range 0..1, latest current CP 0 → status 'in_progress'."""
        rid = self._seed_report()

        # 插入 report_cps: Test1=cp0,cp1
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 0, 'CP1', 0)",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 1, 'CP2', 0)",
            (rid,),
        )
        # 插入 sn_cp_results: current CP 0
        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN001', '', 0, 0, 'pass', NULL, 1, 1)""",
            (rid,),
        )
        self.conn.commit()

        client = api.app.test_client()
        resp = client.get('/api/test-summary')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsNotNone(data)

        # 在 summary 中找到 WF 16.1
        summary = data.get('summary', [])
        wf = next((s for s in summary if s['wf'] == '16.1'), None)
        self.assertIsNotNone(wf, 'WF 16.1 should be in summary')

        cfg = wf['configs'].get('R3')
        self.assertIsNotNone(cfg, 'R3 should be in configs')

        # Test1 应该 in_progress
        test_entry = None
        for tname, entry in cfg.items():
            if entry.get('first_cp_idx') == 0 and entry.get('last_cp_idx') == 1:
                test_entry = entry
                break
        self.assertIsNotNone(test_entry, 'Should find Test1 entry')
        self.assertEqual(test_entry['status'], 'in_progress')

    def test_summary_not_started(self):
        """WF 16.1, config R3, Test2 CP range 2..3, latest current CP 0 → status 'not_started'."""
        rid = self._seed_report()

        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 2, 'CP3', 1)",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 3, 'CP4', 1)",
            (rid,),
        )
        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN001', '', 1, 0, 'pass', NULL, 1, 1)""",
            (rid,),
        )
        self.conn.commit()

        client = api.app.test_client()
        resp = client.get('/api/test-summary')
        data = resp.get_json()
        summary = data.get('summary', [])
        wf = next((s for s in summary if s['wf'] == '16.1'), None)
        cfg = wf['configs'].get('R3')

        test_entry = None
        for tname, entry in cfg.items():
            if entry.get('first_cp_idx') == 2:
                test_entry = entry
                break
        self.assertIsNotNone(test_entry)
        self.assertEqual(test_entry['status'], 'not_started')

    def test_summary_complete(self):
        """WF 16.1, config R3, Test1 CP range 0..1, latest current CP 1 → status 'complete' with result '0F/1T'."""
        rid = self._seed_report()

        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 0, 'CP1', 0)",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 1, 'CP2', 0)",
            (rid,),
        )
        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN001', '', 0, 1, 'pass', NULL, 1, 1)""",
            (rid,),
        )
        # 也需要一个 cp_idx=0 的数据行，因为 api 查询需要 total_units
        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN001', '', 0, 0, 'pass', NULL, 1, 0)""",
            (rid,),
        )
        self.conn.commit()

        client = api.app.test_client()
        resp = client.get('/api/test-summary')
        data = resp.get_json()
        summary = data.get('summary', [])
        wf = next((s for s in summary if s['wf'] == '16.1'), None)
        cfg = wf['configs'].get('R3')

        test_entry = None
        for tname, entry in cfg.items():
            if entry.get('first_cp_idx') == 0 and entry.get('last_cp_idx') == 1:
                test_entry = entry
                break
        self.assertIsNotNone(test_entry)
        self.assertEqual(test_entry['status'], 'complete')
        self.assertEqual(test_entry['result'], '0F/1T')


    def test_sn_lookup_returns_wf_group_with_progress(self):
        """/api/sn/SN123 返回一个 WF 组，包含 latest.total_cps、latest.pct、latest.status。"""
        rid = self._seed_report()

        # 插入 report_cps 作为 total_cps 的源
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 0, 'CP1', 0)",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 1, 'CP2', 0)",
            (rid,),
        )

        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN123', 'U1', 0, 0, 'pass', NULL, 1, 1)""",
            (rid,),
        )
        self.conn.commit()

        client = api.app.test_client()
        resp = client.get('/api/sn/SN123')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['sn'], 'SN123')

        by_wf = data.get('by_wf', [])
        self.assertGreater(len(by_wf), 0)
        wf_group = by_wf[0]
        latest = wf_group.get('latest')
        self.assertIsNotNone(latest)
        self.assertIn('total_cps', latest)
        self.assertIn('pct', latest)
        self.assertEqual(wf_group['wf'], '16.1')

        # 检查 history
        history = wf_group.get('history', [])
        self.assertGreater(len(history), 0)
        self.assertIn('total_cps', history[0])
        self.assertIn('pct', history[0])

    def test_sn_search_returns_sns_from_facts(self):
        """/api/sn/search?q=SN1 从 sn_cp_results 返回 SN。"""
        rid = self._seed_report()

        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN100', '', 0, 0, 'pass', NULL, 1, 1)""",
            (rid,),
        )
        self.conn.execute(
            """INSERT INTO sn_cp_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN101', '', 0, 0, 'pass', NULL, 1, 1)""",
            (rid,),
        )
        self.conn.commit()

        client = api.app.test_client()
        resp = client.get('/api/sn/search?q=SN1')
        self.assertEqual(resp.status_code, 200)
        results = resp.get_json()
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn('SN100', results)

    def test_unknown_sn_returns_404(self):
        """/api/sn/UNKNOWN 返回 HTTP 404 和 records: []。"""
        rid = self._seed_report()
        self.conn.commit()

        client = api.app.test_client()
        resp = client.get('/api/sn/UNKNOWN_SN_XYZ')
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertIn('records', data)
        self.assertEqual(data['records'], [])


if __name__ == '__main__':
    unittest.main()
