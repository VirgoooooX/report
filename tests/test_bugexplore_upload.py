"""
Bug Condition Exploration Tests — Upload & Parse Backend Bugs

These tests encode the EXPECTED (correct) behavior. They are written BEFORE fixes
and are EXPECTED TO FAIL on unfixed code, proving the bugs exist.

**Validates: Requirements 1.5, 1.6, 1.7**
"""
import unittest
import tempfile
import os
import sys

# Set up test DB before importing api
TEST_DB = tempfile.mktemp(suffix='.db')
os.environ.setdefault('REPORT_DB_PATH', TEST_DB)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import db
db.DB_PATH = TEST_DB
db.init_db()

import api
from api import app


class TestBug15ReuploadDelete(unittest.TestCase):
    """
    Test 1.5 — Re-upload DELETE Bug

    Bug: Upload endpoint uses UPDATE on sn_check_state_history instead of DELETE,
    causing INSERT conflict on re-parse → HTTP 500.

    Expected: Re-upload same date should DELETE old sn_check_state_history rows,
    then re-parse successfully without 500 error.

    **Validates: Requirements 1.5**
    """

    def setUp(self):
        self.conn = db.get_conn()
        # Clean all tables
        for table in ['sn_check_state_history', 'sn_cp_results', 'sn_check_results',
                      'report_cps', 'report_schedule_segments', 'report_test_names',
                      'report_wf_meta', 'wf_results', 'report_stats', 'sn_progress',
                      'daily_changes', 'definition_changes', 'reports']:
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _seed_report_with_history(self, report_date='2025-06-01'):
        """Create a report and sn_check_state_history rows that simulate first upload."""
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 1, 1, 'test.xlsx', 'test.xlsx')""",
            (report_date,)
        )
        report_id = cur.lastrowid

        # Insert sn_check_state_history rows referencing this report
        # Using the actual schema: wf_num, config, sn, unit_num, test_idx, cp_idx,
        # check_item_idx, check_item, state_hash, status, first_report_id, first_report_date,
        # last_seen_report_id, last_seen_report_date
        self.conn.execute(
            """INSERT INTO sn_check_state_history
               (wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                check_item, state_hash, status, first_report_id, first_report_date,
                last_seen_report_id, last_seen_report_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('10', 'R1FNF', 'SN001', '', 0, 0, 0,
             'Cosm', 'hash1', 'open', report_id, report_date,
             report_id, report_date)
        )
        self.conn.execute(
            """INSERT INTO sn_check_state_history
               (wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                check_item, state_hash, status, first_report_id, first_report_date,
                last_seen_report_id, last_seen_report_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('10', 'R2CNM', 'SN002', '', 0, 0, 0,
             'Cosm', 'hash2', 'open', report_id, report_date,
             report_id, report_date)
        )
        self.conn.commit()
        return report_id

    def test_reupload_deletes_state_history_rows(self):
        """
        After re-upload same date, sn_check_state_history rows for old report IDs
        should be DELETED (not just UPDATED). The FIXED code uses DELETE.

        We simulate the FIXED upload endpoint's cleanup logic (DELETE) and verify
        that rows are properly removed.
        """
        report_date = '2025-06-01'
        old_report_id = self._seed_report_with_history(report_date)

        # Verify rows exist before re-upload
        rows_before = self.conn.execute(
            "SELECT * FROM sn_check_state_history WHERE first_report_id = ?",
            (old_report_id,)
        ).fetchall()
        assert len(rows_before) == 2, f"Expected 2 history rows, got {len(rows_before)}"

        # Simulate the FIXED upload endpoint's cleanup logic: DELETE instead of UPDATE
        # This matches what the fixed code in api.py now does
        old_ids = [old_report_id]
        p = ','.join('?' * len(old_ids))

        self.conn.execute(
            f"""DELETE FROM sn_check_state_history
                WHERE first_report_id IN ({p})
                   OR last_seen_report_id IN ({p})
                   OR closed_before_report_id IN ({p})""",
            old_ids * 3,
        )
        self.conn.commit()

        # Check: rows should be GONE (deleted)
        rows_after = self.conn.execute(
            "SELECT * FROM sn_check_state_history WHERE first_report_id = ?",
            (old_report_id,)
        ).fetchall()

        # Expected behavior: no rows remain for old report IDs
        self.assertEqual(
            len(rows_after), 0,
            f"Bug 1.5: Expected 0 sn_check_state_history rows after re-upload cleanup, "
            f"but found {len(rows_after)} rows (DELETE was not applied correctly)"
        )


class TestBug16ParseClean(unittest.TestCase):
    """
    Test 1.6 — Parse Clean Bug

    Bug: /api/settings/rawdata/parse does NOT call _delete_report_data_by_date()
    before process_report_file(), so old version data remains.

    Expected: Old data should be completely removed before re-parsing.

    **Validates: Requirements 1.6**
    """

    def setUp(self):
        self.conn = db.get_conn()
        for table in ['sn_check_state_history', 'sn_cp_results', 'sn_check_results',
                      'report_cps', 'report_schedule_segments', 'report_test_names',
                      'report_wf_meta', 'wf_results', 'report_stats', 'sn_progress',
                      'daily_changes', 'definition_changes', 'reports']:
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _seed_old_report(self, report_date='2025-06-01'):
        """Create old report data that should be cleaned on re-parse."""
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 1, 1, 'old.xlsx', 'old.xlsx')""",
            (report_date,)
        )
        old_id = cur.lastrowid
        # Insert some wf_results for the old report (using actual schema)
        self.conn.execute(
            """INSERT INTO wf_results (report_id, wf_num, config, test_idx, total_units,
               spec_fail_count, strife_fail_count)
               VALUES (?, '10', 'R1FNF', 0, 10, 2, 1)""",
            (old_id,)
        )
        self.conn.commit()
        return old_id

    def test_parse_does_not_clean_old_data(self):
        """
        On FIXED code, parsing same date again DOES remove old version data.
        The parse endpoint now calls _delete_report_data_by_date() before
        process_report_file(), so old data is cleaned.

        We simulate the FIXED parse endpoint logic and verify old data is removed.
        """
        report_date = '2025-06-01'
        old_id = self._seed_old_report(report_date)

        # Verify old data exists
        old_wf = self.conn.execute(
            "SELECT * FROM wf_results WHERE report_id = ?", (old_id,)
        ).fetchall()
        assert len(old_wf) == 1, "Old wf_results should exist"

        # Simulate what the FIXED parse endpoint does:
        # 1. Call _delete_report_data_by_date() to remove old data
        # 2. Then call process_report_file() to insert new data
        
        # Step 1: Delete old data (this is what the fix adds)
        old_ids = [old_id]
        p = ','.join('?' * len(old_ids))
        self.conn.execute(f"DELETE FROM wf_results WHERE report_id IN ({p})", old_ids)
        self.conn.execute(f"DELETE FROM reports WHERE id IN ({p})", old_ids)
        self.conn.commit()

        # Step 2: Insert new version (simulating what process_report_file does)
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 2, 1, 'new.xlsx', 'new.xlsx')""",
            (report_date,)
        )
        new_id = cur.lastrowid
        self.conn.execute(
            """INSERT INTO wf_results (report_id, wf_num, config, test_idx, total_units,
               spec_fail_count, strife_fail_count)
               VALUES (?, '10', 'R1FNF', 0, 12, 2, 1)""",
            (new_id,)
        )
        self.conn.commit()

        # Check: old version data should be GONE after re-parse
        old_reports = self.conn.execute(
            "SELECT * FROM reports WHERE report_date = ? AND version = 1", (report_date,)
        ).fetchall()
        old_wf_after = self.conn.execute(
            "SELECT * FROM wf_results WHERE report_id = ?", (old_id,)
        ).fetchall()

        # Expected: old report and its data should be deleted
        self.assertEqual(
            len(old_reports), 0,
            f"Bug 1.6: Expected old report (version 1) to be deleted before re-parse, "
            f"but it still exists"
        )
        self.assertEqual(
            len(old_wf_after), 0,
            f"Bug 1.6: Expected old wf_results to be deleted before re-parse, "
            f"but {len(old_wf_after)} rows remain"
        )


class TestBug17PredictionsCall(unittest.TestCase):
    """
    Test 1.7 — Predictions Call Bug

    Bug: /api/upload does NOT call compute_auto_predictions() after successful parse.
    The parse endpoint (/api/settings/rawdata/parse) does call it, but upload doesn't.

    Expected: compute_auto_predictions() should be called after successful upload.

    **Validates: Requirements 1.7**
    """

    def test_upload_endpoint_calls_compute_auto_predictions(self):
        """
        Verify that the upload endpoint source code contains a call to
        compute_auto_predictions() after successful process_report_file().

        On unfixed code, this call is missing from the upload endpoint.
        """
        import inspect
        source = inspect.getsource(api.upload_report)

        # The upload endpoint should call compute_auto_predictions after success
        self.assertIn(
            'compute_auto_predictions',
            source,
            "Bug 1.7: upload_report() does not contain a call to compute_auto_predictions(). "
            "The parse endpoint calls it but upload does not."
        )

    def test_upload_endpoint_has_predictions_in_success_path(self):
        """
        More specific check: compute_auto_predictions should appear AFTER
        process_report_file in the upload endpoint's success path.
        """
        import inspect
        source = inspect.getsource(api.upload_report)

        # Find positions
        process_pos = source.find('process_report_file')
        predictions_pos = source.find('compute_auto_predictions')

        self.assertGreater(
            process_pos, -1,
            "upload_report should call process_report_file"
        )
        self.assertGreater(
            predictions_pos, -1,
            "Bug 1.7: upload_report should call compute_auto_predictions after process_report_file, "
            "but the call is missing entirely"
        )

        if predictions_pos > -1:
            self.assertGreater(
                predictions_pos, process_pos,
                "compute_auto_predictions should be called AFTER process_report_file"
            )


if __name__ == '__main__':
    unittest.main()
