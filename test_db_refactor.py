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


if __name__ == '__main__':
    unittest.main()
