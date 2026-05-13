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
        self.conn.execute("DELETE FROM sn_check_state_history")
        self.conn.execute("DELETE FROM sn_check_results")
        self.conn.execute("DELETE FROM report_cps")
        self.conn.execute("DELETE FROM report_schedule_segments")
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

        # Insert report_cps for CP-to-test mapping
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', 0, 'CP0', 0)",
            (rid,),
        )

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

    def test_failure_stats_only_count_latest_cp_check_items(self):
        """Failures on any CP in a test are counted, not just the current CP."""
        rid = self._seed_report()

        # Need report_cps to define CP-to-test mapping
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '37', 0, 'CP0', 0)",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '37', 1, 'CP1', 0)",
            (rid,),
        )

        rows = [
            (rid, 'SN001', 0, 'spec_fail', 'spec', 0),
            (rid, 'SN001', 1, 'pass', None, 1),
            (rid, 'SN002', 0, 'pass', None, 0),
            (rid, 'SN002', 1, 'strife_fail', 'strife', 1),
        ]
        for report_id, sn, cp_idx, status, failure_type, is_current in rows:
            self.conn.execute(
                """INSERT INTO sn_cp_results
                   (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
                   VALUES (?, '2025-01-01', '37', 'R1FNF', ?, '', 0, ?, ?, ?, 1, ?)""",
                (report_id, sn, cp_idx, status, failure_type, is_current),
            )
            self.conn.execute(
                """INSERT INTO sn_check_results
                   (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                    check_item, raw_value, normalized_value, status, failure_type)
                   VALUES (?, '2025-01-01', '37', 'R1FNF', ?, '', 0, ?, 0, 'FACT', ?, ?, ?, ?)""",
                (report_id, sn, cp_idx, status, status, status, failure_type),
            )
        self.conn.commit()

        client = api.app.test_client()
        stats = client.get('/api/failures/stats').get_json()
        top = stats['top_failures'][0]

        # SN001: CP0=spec_fail but CP1=pass → latest CP in test is CP1 (pass) → not a failure
        # SN002: CP0=pass, CP1=strife_fail → latest CP in test is CP1 (strife_fail) → failure
        self.assertEqual(top['spec'], 0)
        self.assertEqual(top['strife'], 1)
        self.assertEqual(top['total'], 2)
        self.assertEqual(top['rate'], 50.0)

        wf_detail = client.get('/api/failures/wf/37').get_json()
        self.assertEqual(wf_detail['results'][0]['spec_fail_count'], 0)
        self.assertEqual(wf_detail['results'][0]['strife_fail_count'], 1)
        self.assertEqual(wf_detail['results'][0]['total_units'], 2)

    def test_summary_preserves_duplicate_test_name_slots(self):
        """WF37-style duplicate test names should not let later 0T slots overwrite earlier 4T slots."""
        rid = self._seed_report()

        self.conn.execute(
            "INSERT INTO report_test_names (report_id, wf_num, test_idx, test_name) VALUES (?, '37', 0, 'Random Drop')",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_test_names (report_id, wf_num, test_idx, test_name) VALUES (?, '37', 1, 'Battery Swap')",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_test_names (report_id, wf_num, test_idx, test_name) VALUES (?, '37', 2, 'Random Drop')",
            (rid,),
        )
        for cp_idx, test_idx in [(0, 0), (1, 0), (2, 1), (3, 2)]:
            self.conn.execute(
                "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '37', ?, ?, ?)",
                (rid, cp_idx, f'CP{cp_idx}', test_idx),
            )
        for sn in ['SN001', 'SN002', 'SN003', 'SN004']:
            for cp_idx, test_idx, is_current, status in [
                (0, 0, 0, 'pass'),
                (1, 0, 1, 'pass'),
                (2, 1, 0, 'pending'),
                (3, 2, 0, 'pending'),
            ]:
                self.conn.execute(
                    """INSERT INTO sn_cp_results
                       (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
                       VALUES (?, '2025-01-01', '37', 'R1FNF', ?, '', ?, ?, ?, NULL, ?, ?)""",
                    (rid, sn, test_idx, cp_idx, status, int(status != 'pending'), is_current),
                )
                self.conn.execute(
                    """INSERT INTO sn_check_results
                       (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                        check_item, raw_value, normalized_value, status, failure_type)
                       VALUES (?, '2025-01-01', '37', 'R1FNF', ?, '', ?, ?, 0, 'FACT', ?, ?, ?, NULL)""",
                    (rid, sn, test_idx, cp_idx, status, status, status),
                )
        self.conn.commit()

        client = api.app.test_client()
        data = client.get('/api/test-summary').get_json()
        wf = next(s for s in data['summary'] if s['wf'] == '37')

        self.assertEqual(wf['test_names'], ['Random Drop', 'Battery Swap', 'Random Drop'])
        self.assertEqual(wf['config_results']['R1FNF'][0]['result'], '0F/4T')
        # Slot 2 has 0 total units and is not_started → shows '—' (not a fake 0F/0T)
        self.assertEqual(wf['config_results']['R1FNF'][2]['result'], '—')
        self.assertEqual(wf['config_results']['R1FNF'][2]['status'], 'not_started')

    def test_schedule_includes_wf_config_current_progress(self):
        """/api/schedule should include latest WF+config current CP progress per segment."""
        rid = self._seed_report()
        self.conn.execute(
            """INSERT INTO report_schedule_segments
               (report_id, wf_num, config, test_idx, test_name, schedule_test_item,
                planned_start_date, planned_end_date, confidence, inference_reason, marker_labels)
               VALUES (?, '16.1', 'R3', 0, 'Thermal', 'Thermal',
                       '2026-05-01', '2026-05-03', 'high', 'seed', '[]')""",
            (rid,),
        )
        for cp_idx in range(3):
            self.conn.execute(
                "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '16.1', ?, ?, 0)",
                (rid, cp_idx, f'CP{cp_idx + 1}'),
            )
        self.conn.execute(
            """INSERT INTO sn_progress
               (report_id, wf_num, config, sn, current_cp_idx, current_cp_name, total_cps)
               VALUES (?, 'WF16.1', 'R3', 'SN001', 1, 'CP2', 3)""",
            (rid,),
        )
        self.conn.execute(
            """INSERT INTO sn_progress
               (report_id, wf_num, config, sn, current_cp_idx, current_cp_name, total_cps)
               VALUES (?, 'WF16.1', 'R3', 'SN002', 2, 'CP3', 3)""",
            (rid,),
        )
        self.conn.commit()

        data = api.app.test_client().get('/api/schedule').get_json()
        segment = data['segments'][0]

        self.assertEqual(segment['current_cp_idx'], 2)
        self.assertEqual(segment['current_cp_name'], 'CP3')
        self.assertEqual(segment['total_cps'], 3)
        self.assertEqual(segment['sn_count'], 2)

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
        self.conn.execute(
            """INSERT INTO sn_check_results
               (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                check_item, raw_value, normalized_value, status, failure_type)
               VALUES (?, '2025-01-01', '16.1', 'R3', 'SN001', '', 0, 1, 0, 'FACT', 'pass', 'pass', 'pass', NULL)""",
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
        self.assertIn('SN100', [r['sn'] for r in results])

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

    def test_fa_list_filters_by_cell_context(self):
        """FA list should match the clicked Test Summary cell, not only a raw WF string."""
        original_find = api._find_fa_tracker_by_date
        original_read = api.read_fa_tracker
        try:
            api._find_fa_tracker_by_date = lambda _date: 'fake-fa-tracker.xlsx'
            api.read_fa_tracker = lambda _path: [
                {
                    'FA#': 'FA-001',
                    'SN': 'SN001',
                    'WF': 10,
                    'Config': 'R3',
                    'Failed Test': 'Drop Test',
                    'Failure Type  (Spec. or Strife)': 'Spec.',
                },
                {
                    'FA#': 'FA-002',
                    'SN': 'SN002',
                    'WF': 'WF10',
                    'Config': 'R3',
                    'Failed Test': 'Drop Test',
                    'Failure Type  (Spec. or Strife)': 'Strife',
                },
                {
                    'FA#': 'FA-003',
                    'SN': 'SN003',
                    'WF': 'WF11',
                    'Config': 'R3',
                    'Failed Test': 'Drop Test',
                    'Failure Type  (Spec. or Strife)': 'Spec.',
                },
                {
                    'FA#': 'FA-004',
                    'SN': 'SN004',
                    'WF': '10',
                    'Config': 'R4',
                    'Failed Test': 'Drop Test',
                    'Failure Type  (Spec. or Strife)': 'Spec.',
                },
            ]

            client = api.app.test_client()
            resp = client.get('/api/fa/list?wf=WF10&config=R3&failed_test=Drop%20Test&sns=SN001,SN002')

            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertEqual(data['count'], 2)
            self.assertEqual([record['FA#'] for record in data['records']], ['FA-001', 'FA-002'])
        finally:
            api._find_fa_tracker_by_date = original_find
            api.read_fa_tracker = original_read

    def test_cell_failures_returns_check_item_details(self):
        """Clicking a cell should return per-SN, per-CP check-item failure details."""
        rid = self._seed_report()

        # report_cps: map cp_idx to test_idx
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '37', 0, 'CP1', 0)",
            (rid,),
        )
        self.conn.execute(
            "INSERT INTO report_cps (report_id, wf_num, cp_idx, cp_name, test_idx) VALUES (?, '37', 1, 'CP2', 0)",
            (rid,),
        )

        # sn_cp_results for two SNs
        for sn, cp_idx, is_current in [('SN001', 0, 1), ('SN001', 1, 0), ('SN002', 1, 1)]:
            self.conn.execute(
                """INSERT INTO sn_cp_results
                   (report_id, report_date, wf_num, config, sn, unit_num, test_idx, cp_idx, status, failure_type, has_data, is_current_cp)
                   VALUES (?, '2025-01-01', '37', 'R3', ?, '', 0, ?, 'spec_fail', 'spec', 1, ?)""",
                (rid, sn, cp_idx, is_current),
            )

        # check-item failures stored as state history
        db.save_sn_check_state_history(self.conn, rid, '2025-01-01', [
            {
                'wf_num': '37',
                'config': 'R3',
                'sn': 'SN001',
                'unit_num': '',
                'test_idx': 0,
                'cp_idx': 0,
                'check_item_idx': 0,
                'check_item': 'FACT',
                'raw_value': '2.5',
                'normalized_value': 'FAIL',
                'status': 'fail',
                'failure_type': 'spec',
                'fill_color': 'FFFF0000',
                'font_color': '',
                'source_row': 10,
                'source_col': 20,
            },
            {
                'wf_num': '37',
                'config': 'R3',
                'sn': 'SN002',
                'unit_num': '',
                'test_idx': 0,
                'cp_idx': 1,
                'check_item_idx': 0,
                'check_item': 'DROP',
                'raw_value': 'FAIL',
                'normalized_value': 'FAIL',
                'status': 'fail',
                'failure_type': 'strife',
                'fill_color': 'FFFFFF00',
                'font_color': '',
                'source_row': 11,
                'source_col': 21,
            },
        ])
        self.conn.commit()

        client = api.app.test_client()
        resp = client.get('/api/cell-failures?wf=37&config=R3&test_idx=0&sns=SN001,SN002')
        self.assertEqual(resp.status_code, 200)

        data = resp.get_json()
        failures = data.get('failures', [])
        self.assertEqual(len(failures), 2)

        # SN001 should have CP1 with FACT spec fail
        sn1 = next(f for f in failures if f['sn'] == 'SN001')
        self.assertEqual(len(sn1['cps']), 1)
        self.assertEqual(sn1['cps'][0]['cp_name'], 'CP1')
        self.assertEqual(sn1['cps'][0]['check_items'][0]['check_item'], 'FACT')
        self.assertEqual(sn1['cps'][0]['check_items'][0]['failure_type'], 'spec')

        # SN002 should have CP2 with DROP strife fail
        sn2 = next(f for f in failures if f['sn'] == 'SN002')
        self.assertEqual(sn2['cps'][0]['cp_name'], 'CP2')
        self.assertEqual(sn2['cps'][0]['check_items'][0]['check_item'], 'DROP')
        self.assertEqual(sn2['cps'][0]['check_items'][0]['failure_type'], 'strife')

        # Also test WF prefix normalization (WF37 → 37)
        resp2 = client.get('/api/cell-failures?wf=WF37&config=R3&test_idx=0&sns=SN001')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertEqual(len(data2['failures']), 1)
        self.assertEqual(data2['failures'][0]['sn'], 'SN001')


if __name__ == '__main__':
    unittest.main()
