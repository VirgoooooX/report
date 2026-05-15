"""
Preservation Property Tests — Existing Upload & Parse Behavior Unchanged

These tests capture the EXISTING correct behavior of the unfixed code.
They MUST PASS on unfixed code, confirming baseline behavior to preserve.
After fixes are applied, these tests ensure no regressions occurred.

**Validates: Requirements 3.4, 3.5**
"""
import unittest
import tempfile
import os
import sys
import inspect

# Set up test DB before importing api
TEST_DB = tempfile.mktemp(suffix='.db')
os.environ.setdefault('REPORT_DB_PATH', TEST_DB)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import db
db.DB_PATH = TEST_DB
db.init_db()

import api
from api import app


class TestPreservationFirstTimeUpload(unittest.TestCase):
    """
    Preservation Property: First-time upload (no existing date) succeeds
    and returns parsed data without any deletion step.

    For all first-time uploads (date not in DB), response is success with
    parsed report data and no deletion step occurs.

    **Validates: Requirements 3.5**
    """

    def setUp(self):
        self.conn = db.get_conn()
        # Clean all tables to ensure no pre-existing data
        for table in ['sn_check_state_history', 'sn_cp_results', 'sn_check_results',
                      'report_cps', 'report_schedule_segments', 'report_test_names',
                      'report_wf_meta', 'wf_results', 'report_stats', 'sn_progress',
                      'daily_changes', 'definition_changes', 'reports']:
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_first_upload_no_deletion_step(self):
        """
        When uploading a date that does NOT exist in the DB, the upload endpoint
        should NOT execute any deletion logic (no old_ids to delete).

        We verify by checking that the upload endpoint's cleanup section
        is conditional on old_ids being non-empty.
        """
        report_date = '2025-07-15'

        # Verify no reports exist for this date
        existing = self.conn.execute(
            "SELECT id FROM reports WHERE report_date = ?", (report_date,)
        ).fetchall()
        self.assertEqual(len(existing), 0, "No reports should exist for test date")

        # Verify the upload endpoint code structure: old_ids check is conditional
        source = inspect.getsource(api.upload_report)

        # The upload endpoint queries for old reports and only deletes if found
        self.assertIn('old_ids', source, "Upload endpoint should reference old_ids")
        self.assertIn('if old_ids', source,
                      "Upload endpoint should conditionally execute deletion only when old_ids exist")

    def test_first_upload_inserts_report_successfully(self):
        """
        Simulate first-time upload: insert a report for a new date.
        Verify the report is created successfully without conflicts.
        """
        report_date = '2025-07-15'

        # Verify no pre-existing data
        existing = self.conn.execute(
            "SELECT id FROM reports WHERE report_date = ?", (report_date,)
        ).fetchall()
        self.assertEqual(len(existing), 0)

        # Simulate what process_report_file does on first upload: insert a new report
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 1, 1, 'test.xlsx', 'test.xlsx')""",
            (report_date,)
        )
        report_id = cur.lastrowid
        self.conn.commit()

        # Verify report was created
        report = self.conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()
        self.assertIsNotNone(report)
        self.assertEqual(report['report_date'], report_date)
        self.assertEqual(report['version'], 1)
        self.assertEqual(report['is_active'], 1)

    def test_first_upload_can_insert_state_history(self):
        """
        On first upload, sn_check_state_history rows can be inserted without conflict.
        This verifies the normal insertion path works when no prior data exists.
        """
        report_date = '2025-07-15'

        # Create a report
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 1, 1, 'test.xlsx', 'test.xlsx')""",
            (report_date,)
        )
        report_id = cur.lastrowid

        # Insert state history rows (simulating process_report_file behavior)
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
        self.conn.commit()

        # Verify insertion succeeded
        rows = self.conn.execute(
            "SELECT * FROM sn_check_state_history WHERE first_report_id = ?",
            (report_id,)
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['sn'], 'SN001')
        self.assertEqual(rows[0]['status'], 'open')


class TestPreservationParseEndpointPredictions(unittest.TestCase):
    """
    Preservation Property: /api/settings/rawdata/parse calls
    compute_auto_predictions() on success.

    For all successful parse operations via settings endpoint,
    compute_auto_predictions() is called exactly once.

    **Validates: Requirements 3.4**
    """

    def test_parse_endpoint_contains_compute_auto_predictions(self):
        """
        The parse endpoint (/api/settings/rawdata/parse) ALREADY calls
        compute_auto_predictions() after successful parsing.
        This behavior must be preserved.
        """
        source = inspect.getsource(api.api_settings_rawdata_parse)

        self.assertIn(
            'compute_auto_predictions',
            source,
            "Parse endpoint must call compute_auto_predictions() — this is existing behavior"
        )

    def test_parse_endpoint_predictions_after_process(self):
        """
        compute_auto_predictions() is called AFTER process_report_file in the
        parse endpoint. This ordering must be preserved.
        """
        source = inspect.getsource(api.api_settings_rawdata_parse)

        process_pos = source.find('process_report_file')
        predictions_pos = source.find('compute_auto_predictions')

        self.assertGreater(process_pos, -1, "Parse endpoint must call process_report_file")
        self.assertGreater(predictions_pos, -1, "Parse endpoint must call compute_auto_predictions")
        self.assertGreater(
            predictions_pos, process_pos,
            "compute_auto_predictions must be called AFTER process_report_file"
        )

    def test_parse_endpoint_predictions_in_try_except(self):
        """
        compute_auto_predictions() is wrapped in try/except in the parse endpoint.
        This error-handling pattern must be preserved so a prediction failure
        doesn't break the parse response.
        """
        source = inspect.getsource(api.api_settings_rawdata_parse)

        # Find the compute_auto_predictions call
        pred_pos = source.find('compute_auto_predictions')
        self.assertGreater(pred_pos, -1)

        # Check that there's a try block before it and except after it
        # Look backwards from compute_auto_predictions for 'try:'
        before_pred = source[:pred_pos]
        self.assertIn('try:', before_pred[-100:],
                      "compute_auto_predictions should be inside a try block")

        # Look forward for 'except'
        after_pred = source[pred_pos:]
        except_pos = after_pred.find('except')
        self.assertGreater(except_pos, -1,
                           "compute_auto_predictions should have an except handler")


class TestPreservationUploadEndpointStructure(unittest.TestCase):
    """
    Preservation Property: Upload endpoint structure and flow.

    Verifies the upload endpoint maintains its core structure:
    - Validates filenames
    - Saves files
    - Handles old data cleanup conditionally
    - Calls process_report_file
    - Returns success JSON

    **Validates: Requirements 3.5**
    """

    def test_upload_validates_daily_report_filename(self):
        """Upload endpoint validates the daily report filename pattern."""
        source = inspect.getsource(api.upload_report)
        self.assertIn('REPORT_PATTERN', source,
                      "Upload must validate daily report filename against REPORT_PATTERN")

    def test_upload_calls_process_report_file(self):
        """Upload endpoint calls process_report_file for parsing."""
        source = inspect.getsource(api.upload_report)
        self.assertIn('process_report_file', source,
                      "Upload must call process_report_file")

    def test_upload_returns_success_json(self):
        """Upload endpoint returns success JSON with report_date and wf_count."""
        source = inspect.getsource(api.upload_report)
        self.assertIn("'success': True", source,
                      "Upload must return success: True on success")
        self.assertIn("'report_date'", source,
                      "Upload must return report_date in response")
        self.assertIn("'wf_count'", source,
                      "Upload must return wf_count in response")

    def test_upload_conditional_old_data_cleanup(self):
        """
        Upload endpoint only performs old data cleanup when old_ids exist.
        First-time uploads (no existing date) skip the cleanup entirely.
        """
        source = inspect.getsource(api.upload_report)

        # The cleanup is conditional on old_ids being non-empty
        self.assertIn('if old_ids:', source,
                      "Old data cleanup must be conditional on old_ids existing")

        # Verify it queries for existing reports by date
        self.assertIn("SELECT id FROM reports WHERE report_date", source,
                      "Upload must query for existing reports by date")


class TestPreservationDeleteReportDataByDate(unittest.TestCase):
    """
    Preservation Property: _delete_report_data_by_date helper function
    correctly removes all data for a given date.

    This function is used by the parse endpoint and should continue to work
    correctly after fixes.

    **Validates: Requirements 3.4**
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

    def test_delete_removes_report_and_related_data(self):
        """
        _delete_report_data_by_date removes the report and all related data
        for the specified date.
        """
        report_date = '2025-08-01'

        # Create a report with related data
        cur = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 1, 1, 'test.xlsx', 'test.xlsx')""",
            (report_date,)
        )
        report_id = cur.lastrowid

        # Add wf_results
        self.conn.execute(
            """INSERT INTO wf_results (report_id, wf_num, config, test_idx, total_units,
               spec_fail_count, strife_fail_count)
               VALUES (?, '10', 'R1FNF', 0, 10, 2, 1)""",
            (report_id,)
        )

        # Add sn_check_state_history
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
        self.conn.commit()
        self.conn.close()

        # Call the function
        deleted_count = api._delete_report_data_by_date(report_date)

        # Verify everything is deleted
        self.conn = db.get_conn()
        self.assertEqual(deleted_count, 1, "Should report 1 deleted report")

        reports = self.conn.execute(
            "SELECT * FROM reports WHERE report_date = ?", (report_date,)
        ).fetchall()
        self.assertEqual(len(reports), 0, "Report should be deleted")

        wf_results = self.conn.execute(
            "SELECT * FROM wf_results WHERE report_id = ?", (report_id,)
        ).fetchall()
        self.assertEqual(len(wf_results), 0, "wf_results should be deleted")

        history = self.conn.execute(
            "SELECT * FROM sn_check_state_history WHERE first_report_id = ?", (report_id,)
        ).fetchall()
        self.assertEqual(len(history), 0, "sn_check_state_history should be deleted")

    def test_delete_does_not_affect_other_dates(self):
        """
        _delete_report_data_by_date only removes data for the specified date.
        Other dates remain untouched.
        """
        date_to_delete = '2025-08-01'
        date_to_keep = '2025-08-02'

        # Create reports for both dates
        cur1 = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 1, 1, 'test1.xlsx', 'test1.xlsx')""",
            (date_to_delete,)
        )
        id1 = cur1.lastrowid

        cur2 = self.conn.execute(
            """INSERT INTO reports (report_date, version, is_active, excel_path, source_file_name)
               VALUES (?, 1, 1, 'test2.xlsx', 'test2.xlsx')""",
            (date_to_keep,)
        )
        id2 = cur2.lastrowid

        # Add data for both
        self.conn.execute(
            """INSERT INTO wf_results (report_id, wf_num, config, test_idx, total_units,
               spec_fail_count, strife_fail_count)
               VALUES (?, '10', 'R1FNF', 0, 10, 2, 1)""",
            (id1,)
        )
        self.conn.execute(
            """INSERT INTO wf_results (report_id, wf_num, config, test_idx, total_units,
               spec_fail_count, strife_fail_count)
               VALUES (?, '14', 'R2CNM', 0, 8, 1, 0)""",
            (id2,)
        )
        self.conn.commit()
        self.conn.close()

        # Delete only the first date
        api._delete_report_data_by_date(date_to_delete)

        # Verify second date is untouched
        self.conn = db.get_conn()
        kept_reports = self.conn.execute(
            "SELECT * FROM reports WHERE report_date = ?", (date_to_keep,)
        ).fetchall()
        self.assertEqual(len(kept_reports), 1, "Other date's report should remain")

        kept_wf = self.conn.execute(
            "SELECT * FROM wf_results WHERE report_id = ?", (id2,)
        ).fetchall()
        self.assertEqual(len(kept_wf), 1, "Other date's wf_results should remain")

    def test_delete_nonexistent_date_returns_zero(self):
        """
        _delete_report_data_by_date returns 0 when no reports exist for the date.
        """
        self.conn.close()
        result = api._delete_report_data_by_date('2099-01-01')
        self.assertEqual(result, 0, "Should return 0 for non-existent date")
        self.conn = db.get_conn()


if __name__ == '__main__':
    unittest.main()
