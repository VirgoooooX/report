import os
import sqlite3
import tempfile
import unittest

import db


def temp_conn():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = db._dict_factory
    return conn, path


class ReportVersioningTests(unittest.TestCase):
    def test_create_report_version_first_import_is_active_version_one(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)

            report_id = db.create_report_version(
                conn,
                report_date='2026-05-09',
                excel_path='data/M60 EVT Rel Daily Report_20260509.xlsx',
            )

            row = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
            self.assertEqual(row['report_date'], '2026-05-09')
            self.assertEqual(row['version'], 1)
            self.assertEqual(row['is_active'], 1)
        finally:
            conn.close()
            os.remove(path)

    def test_create_report_version_reimport_deactivates_previous_same_date(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)

            first_id = db.create_report_version(conn, '2026-05-09', 'first.xlsx')
            second_id = db.create_report_version(conn, '2026-05-09', 'second.xlsx')

            first = conn.execute('SELECT version, is_active FROM reports WHERE id = ?', (first_id,)).fetchone()
            second = conn.execute('SELECT version, is_active FROM reports WHERE id = ?', (second_id,)).fetchone()

            self.assertEqual(first['version'], 1)
            self.assertEqual(first['is_active'], 0)
            self.assertEqual(second['version'], 2)
            self.assertEqual(second['is_active'], 1)
        finally:
            conn.close()
            os.remove(path)

    def test_get_latest_active_report_returns_latest_active_date(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            db.create_report_version(conn, '2026-05-08', 'old.xlsx')
            latest_id = db.create_report_version(conn, '2026-05-09', 'new.xlsx')

            row = db.get_latest_active_report(conn)

            self.assertEqual(row['id'], latest_id)
            self.assertEqual(row['report_date'], '2026-05-09')
        finally:
            conn.close()
            os.remove(path)

    def test_previous_active_report_skips_inactive_same_date_version(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            older = db.create_report_version(conn, '2026-05-08', 'a.xlsx')
            first = db.create_report_version(conn, '2026-05-09', 'b.xlsx')
            second = db.create_report_version(conn, '2026-05-09', 'b2.xlsx')

            self.assertEqual(db.get_latest_active_report_id(conn), second)
            self.assertEqual(db.get_previous_active_report_id(conn, second), older)
            self.assertNotEqual(db.get_previous_active_report_id(conn, second), first)
        finally:
            conn.close()
            os.remove(path)


class DefinitionSnapshotTests(unittest.TestCase):
    def test_save_and_load_report_definitions(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            report_id = db.create_report_version(conn, '2026-05-09', 'report.xlsx')

            db.save_report_wf_meta(conn, report_id, {'16.1': 'THC X 6 + Repetitive HSD PB'})
            db.save_report_test_names(conn, report_id, {'16.1': ['THC X 6', 'Repetitive HSD PB']})
            db.save_report_cps(conn, report_id, {
                '16.1': [
                    {'cp_idx': 0, 'cp_name': 'THC X 6', 'test_idx': 0, 'check_items': ['Cosmetic', 'ISB']},
                    {'cp_idx': 49, 'cp_name': 'Bottom Surface After 450Cyc', 'test_idx': 1, 'check_items': ['FACT']},
                ]
            })

            wf_meta = db.get_report_wf_meta(conn, report_id)
            tests = db.get_report_test_names(conn, report_id)
            cps = db.get_report_cps(conn, report_id, '16.1')

            self.assertEqual(wf_meta['16.1'], 'THC X 6 + Repetitive HSD PB')
            self.assertEqual(tests['16.1'][1], 'Repetitive HSD PB')
            self.assertEqual(cps[49]['cp_name'], 'Bottom Surface After 450Cyc')
            self.assertEqual(cps[49]['check_items'], ['FACT'])
        finally:
            conn.close()
            os.remove(path)


class SnFactPersistenceTests(unittest.TestCase):
    def test_save_and_query_sn_cp_results(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            report_id = db.create_report_version(conn, '2026-05-09', 'report.xlsx')
            rows = [
                {
                    'report_id': report_id,
                    'report_date': '2026-05-09',
                    'wf_num': '16.1',
                    'config': 'R3',
                    'sn': 'D06P3Q46X0',
                    'unit_num': 'ER3-16.1-6',
                    'test_idx': 1,
                    'cp_idx': 49,
                    'status': 'pass',
                    'failure_type': None,
                    'has_data': 1,
                    'is_current_cp': 1,
                }
            ]

            db.save_sn_cp_results(conn, rows)

            saved = conn.execute('SELECT * FROM sn_cp_results').fetchone()
            self.assertEqual(saved['sn'], 'D06P3Q46X0')
            self.assertEqual(saved['cp_idx'], 49)
            self.assertEqual(saved['status'], 'pass')
            self.assertEqual(saved['is_current_cp'], 1)
        finally:
            conn.close()
            os.remove(path)

    def test_save_and_query_sn_check_results(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            report_id = db.create_report_version(conn, '2026-05-09', 'report.xlsx')
            rows = [
                {
                    'report_id': report_id,
                    'report_date': '2026-05-09',
                    'wf_num': '16.1',
                    'config': 'R3',
                    'sn': 'D06P3Q46X0',
                    'unit_num': 'ER3-16.1-6',
                    'test_idx': 1,
                    'cp_idx': 49,
                    'check_item_idx': 0,
                    'check_item': 'FACT',
                    'raw_value': 'PASS',
                    'normalized_value': 'PASS',
                    'status': 'pass',
                    'failure_type': None,
                    'fill_color': '00000000',
                    'font_color': '',
                    'source_row': 20,
                    'source_col': 42,
                }
            ]

            db.save_sn_check_results(conn, rows)

            saved = conn.execute('SELECT * FROM sn_check_results').fetchone()
            self.assertEqual(saved['check_item'], 'FACT')
            self.assertEqual(saved['source_row'], 20)
            self.assertEqual(saved['status'], 'pass')
        finally:
            conn.close()
            os.remove(path)

    def test_save_sn_check_state_history_compacts_unchanged_rows(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            first_id = db.create_report_version(conn, '2026-05-08', 'r1.xlsx')
            second_id = db.create_report_version(conn, '2026-05-09', 'r2.xlsx')

            base = {
                'wf_num': '16.1',
                'config': 'R3',
                'sn': 'SN001',
                'unit_num': 'U1',
                'test_idx': 0,
                'cp_idx': 3,
                'check_item_idx': 0,
                'check_item': 'FACT',
                'raw_value': 'PASS',
                'normalized_value': 'PASS',
                'status': 'pass',
                'failure_type': None,
                'fill_color': '',
                'font_color': '',
                'source_row': 20,
                'source_col': 10,
            }

            db.save_sn_check_state_history(conn, first_id, '2026-05-08', [dict(base)])
            changed_location = dict(base, source_row=22, source_col=11)
            db.save_sn_check_state_history(conn, second_id, '2026-05-09', [changed_location])

            rows = conn.execute('SELECT * FROM sn_check_state_history').fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['first_report_id'], first_id)
            self.assertEqual(rows[0]['last_seen_report_id'], second_id)
            self.assertIsNone(rows[0]['closed_before_report_id'])
            self.assertEqual(rows[0]['first_source_row'], 20)
            self.assertEqual(rows[0]['last_source_row'], 22)
        finally:
            conn.close()
            os.remove(path)

    def test_save_sn_check_state_history_splits_on_state_change(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            r1 = db.create_report_version(conn, '2026-05-08', 'r1.xlsx')
            r2 = db.create_report_version(conn, '2026-05-09', 'r2.xlsx')
            r3 = db.create_report_version(conn, '2026-05-10', 'r3.xlsx')

            base = {
                'wf_num': '16.1',
                'config': 'R3',
                'sn': 'SN001',
                'unit_num': 'U1',
                'test_idx': 0,
                'cp_idx': 3,
                'check_item_idx': 0,
                'check_item': 'FACT',
                'raw_value': 'PASS',
                'normalized_value': 'PASS',
                'status': 'pass',
                'failure_type': None,
                'fill_color': '',
                'font_color': '',
                'source_row': 20,
                'source_col': 10,
            }

            db.save_sn_check_state_history(conn, r1, '2026-05-08', [dict(base)])
            db.save_sn_check_state_history(conn, r2, '2026-05-09', [
                dict(base, raw_value='FAIL', normalized_value='FAIL',
                     status='spec_fail', failure_type='spec', fill_color='FFFF0000')
            ])
            db.save_sn_check_state_history(conn, r3, '2026-05-10', [dict(base)])

            rows = conn.execute(
                'SELECT status, failure_type, first_report_id, closed_before_report_id '
                'FROM sn_check_state_history ORDER BY first_report_id'
            ).fetchall()
            self.assertEqual([r['status'] for r in rows], ['pass', 'spec_fail', 'pass'])
            self.assertEqual(rows[0]['closed_before_report_id'], r2)
            self.assertEqual(rows[1]['closed_before_report_id'], r3)
            self.assertIsNone(rows[2]['closed_before_report_id'])
        finally:
            conn.close()
            os.remove(path)

    def test_get_sn_check_details_reads_state_active_at_report(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        old_db_path = db.DB_PATH
        db.DB_PATH = path
        try:
            db.init_db()
            conn = db.get_conn()
            r1 = db.create_report_version(conn, '2026-05-08', 'r1.xlsx')
            r2 = db.create_report_version(conn, '2026-05-09', 'r2.xlsx')

            db.save_sn_check_state_history(conn, r1, '2026-05-08', [{
                'wf_num': '16.1', 'config': 'R3', 'sn': 'SN001', 'unit_num': 'U1',
                'test_idx': 0, 'cp_idx': 3, 'check_item_idx': 0, 'check_item': 'FACT',
                'raw_value': 'PASS', 'normalized_value': 'PASS',
                'status': 'pass', 'failure_type': None, 'fill_color': '',
                'font_color': '', 'source_row': 20, 'source_col': 10,
            }])
            db.save_sn_check_state_history(conn, r2, '2026-05-09', [{
                'wf_num': '16.1', 'config': 'R3', 'sn': 'SN001', 'unit_num': 'U1',
                'test_idx': 0, 'cp_idx': 3, 'check_item_idx': 0, 'check_item': 'FACT',
                'raw_value': 'FAIL', 'normalized_value': 'FAIL',
                'status': 'strife_fail', 'failure_type': 'strife', 'fill_color': 'FFFFFF00',
                'font_color': '', 'source_row': 20, 'source_col': 10,
            }])
            conn.commit()

            old_rows = db.get_sn_check_details(r1, '16.1', 'R3', 'SN001', 3)
            new_rows = db.get_sn_check_details(r2, '16.1', 'R3', 'SN001', 3)

            self.assertEqual(old_rows[0]['status'], 'pass')
            self.assertIsNone(old_rows[0]['failure_type'])
            self.assertEqual(new_rows[0]['status'], 'strife_fail')
            self.assertEqual(new_rows[0]['failure_type'], 'strife')
        finally:
            conn.close()
            db.DB_PATH = old_db_path
            os.remove(path)

    def test_save_sn_check_state_history_closes_rows_not_observed(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        old_db_path = db.DB_PATH
        db.DB_PATH = path
        try:
            db.init_db()
            conn = db.get_conn()
            r1 = db.create_report_version(conn, '2026-05-08', 'r1.xlsx')
            r2 = db.create_report_version(conn, '2026-05-09', 'r2.xlsx')

            db.save_sn_check_state_history(conn, r1, '2026-05-08', [{
                'wf_num': '16.1', 'config': 'R3', 'sn': 'SN001', 'unit_num': 'U1',
                'test_idx': 0, 'cp_idx': 3, 'check_item_idx': 0, 'check_item': 'FACT',
                'raw_value': 'PASS', 'normalized_value': 'PASS',
                'status': 'pass', 'failure_type': None, 'fill_color': '',
                'font_color': '', 'source_row': 20, 'source_col': 10,
            }])
            db.save_sn_check_state_history(conn, r2, '2026-05-09', [])

            rows = db.get_sn_check_details(r2, '16.1', 'R3', 'SN001', 3)
            closed = conn.execute('SELECT closed_before_report_id FROM sn_check_state_history').fetchone()

            self.assertEqual(rows, [])
            self.assertEqual(closed['closed_before_report_id'], r2)
        finally:
            conn.close()
            db.DB_PATH = old_db_path
            os.remove(path)


class FactAggregateTests(unittest.TestCase):
    def test_get_sn_cp_current_progress_uses_current_marker(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            report_id = db.create_report_version(conn, '2026-05-09', 'report.xlsx')
            db.save_sn_cp_results(conn, [
                {'report_id': report_id, 'report_date': '2026-05-09', 'wf_num': '16.1', 'config': 'R3', 'sn': 'SN1', 'unit_num': 'U1', 'test_idx': 0, 'cp_idx': 0, 'status': 'pass', 'failure_type': None, 'has_data': 1, 'is_current_cp': 0},
                {'report_id': report_id, 'report_date': '2026-05-09', 'wf_num': '16.1', 'config': 'R3', 'sn': 'SN1', 'unit_num': 'U1', 'test_idx': 1, 'cp_idx': 49, 'status': 'pass', 'failure_type': None, 'has_data': 1, 'is_current_cp': 1},
            ])

            rows = db.get_sn_cp_current_progress(conn, report_id)

            self.assertEqual(rows[0]['current_cp_idx'], 49)
        finally:
            conn.close()
            os.remove(path)


class CurrentDefinitionTests(unittest.TestCase):
    """Tests for current-only definition tables (wf, test, cp)."""

    def _setup_db(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.row_factory = db._dict_factory
        db.init_db(conn=conn)
        return conn, path

    def test_save_and_get_current_wf_definitions(self):
        conn, path = self._setup_db()
        try:
            report_id = db.create_report_version(conn, '2026-05-09', 'test.xlsx')
            db.save_current_wf_definitions(conn, report_id, {'4': 'Altitude', '6': 'Rock Tumble'})

            result = db.get_current_wf_definitions(conn)
            self.assertEqual(len(result), 2)
            self.assertEqual(result['4'], 'Altitude')
            self.assertEqual(result['6'], 'Rock Tumble')
        finally:
            conn.close()
            os.remove(path)

    def test_save_current_wf_definitions_replaces_previous(self):
        conn, path = self._setup_db()
        try:
            report_id = db.create_report_version(conn, '2026-05-08', 'old.xlsx')
            db.save_current_wf_definitions(conn, report_id, {'4': 'Altitude'})

            report_id2 = db.create_report_version(conn, '2026-05-09', 'new.xlsx')
            db.save_current_wf_definitions(conn, report_id2, {'5': 'Thermal'})

            result = db.get_current_wf_definitions(conn)
            self.assertEqual(len(result), 1)
            self.assertNotIn('4', result)
            self.assertEqual(result['5'], 'Thermal')
        finally:
            conn.close()
            os.remove(path)

    def test_save_and_get_current_test_definitions(self):
        conn, path = self._setup_db()
        try:
            report_id = db.create_report_version(conn, '2026-05-09', 'test.xlsx')
            db.save_current_test_definitions(conn, report_id, {
                '4': ['Altitude', 'Rock Tumble'],
                '6': ['Full Scale'],
            })

            result = db.get_current_test_definitions(conn)
            self.assertEqual(len(result), 2)
            self.assertEqual(result['4'], ['Altitude', 'Rock Tumble'])
            self.assertEqual(result['6'], ['Full Scale'])

            filtered = db.get_current_test_definitions(conn, wf_num='4')
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered['4'], ['Altitude', 'Rock Tumble'])
        finally:
            conn.close()
            os.remove(path)

    def test_save_and_get_current_cp_definitions(self):
        conn, path = self._setup_db()
        try:
            report_id = db.create_report_version(conn, '2026-05-09', 'test.xlsx')
            db.save_current_cp_definitions(conn, report_id, {
                '4': [
                    {'cp_idx': 0, 'cp_name': 'HSD', 'test_idx': 0, 'check_items': ['A', 'B']},
                    {'cp_idx': 1, 'cp_name': 'THC', 'test_idx': 0, 'check_items': ['C']},
                ],
                '6': [
                    {'cp_idx': 0, 'cp_name': 'Full Scale', 'test_idx': 0, 'check_items': ['D', 'E']},
                ],
            })

            result = db.get_current_cp_definitions(conn)
            self.assertEqual(len(result), 2)
            self.assertEqual(result['4'][0]['cp_name'], 'HSD')
            self.assertEqual(result['4'][0]['test_idx'], 0)
            self.assertEqual(result['4'][0]['check_items'], ['A', 'B'])
            self.assertEqual(result['4'][1]['cp_name'], 'THC')
            self.assertEqual(result['4'][1]['test_idx'], 0)
            self.assertEqual(result['4'][1]['check_items'], ['C'])

            filtered = db.get_current_cp_definitions(conn, wf_num='6')
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered['6'][0]['cp_name'], 'Full Scale')
            self.assertEqual(filtered['6'][0]['check_items'], ['D', 'E'])
        finally:
            conn.close()
            os.remove(path)

    def test_current_cp_definitions_replaces_previous(self):
        conn, path = self._setup_db()
        try:
            report_id = db.create_report_version(conn, '2026-05-08', 'old.xlsx')
            db.save_current_cp_definitions(conn, report_id, {
                '4': [{'cp_idx': 0, 'cp_name': 'Old HS', 'test_idx': 0, 'check_items': []}],
            })

            report_id2 = db.create_report_version(conn, '2026-05-09', 'new.xlsx')
            db.save_current_cp_definitions(conn, report_id2, {
                '5': [{'cp_idx': 1, 'cp_name': 'New CP', 'test_idx': 1, 'check_items': ['X']}],
            })

            result = db.get_current_cp_definitions(conn)
            self.assertEqual(len(result), 1)
            self.assertNotIn('4', result)
            self.assertEqual(result['5'][0]['cp_name'], 'New CP')
        finally:
            conn.close()
            os.remove(path)


class VacuumTests(unittest.TestCase):
    def test_vacuum_runs_without_error(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        conn = None
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = db._dict_factory
            db.init_db(conn=conn)
            report_id = db.create_report_version(conn, '2026-05-09', 'test.xlsx')
            conn.commit()
            conn.close()
            conn = None
            # Switch to the module's connection for vacuum
            import db as dbmod
            dbmod.DB_PATH = path
            dbmod.vacuum_db()
            # Verify file still exists and is valid
            conn2 = sqlite3.connect(path)
            tables = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            self.assertTrue(len(tables) > 0)
            conn2.close()
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
