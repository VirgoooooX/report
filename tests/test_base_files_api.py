"""
Integration tests for Base file management API endpoints (Task 3.2).

Validates Requirements 2.1, 2.2, 2.3, 2.4:
- POST /api/base-files — upload and parse Base files
- GET /api/base-files — list uploaded files
- DELETE /api/base-files/:filename — remove file and metadata
- Error handling for invalid files
"""
import csv
import io
import json
import os
import tempfile
import unittest

# Set up test DB before importing api
TEST_DB = tempfile.mktemp(suffix='.db')
import db
db.DB_PATH = TEST_DB
db.init_db()

import api


def _ensure_db():
    """Re-initialize DB in case another test module changed DB_PATH."""
    db.DB_PATH = TEST_DB
    db.init_db()


class BaseFilesUploadTests(unittest.TestCase):
    """Test POST /api/base-files endpoint."""

    def setUp(self):
        _ensure_db()
        self.app = api.app.test_client()
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM base_file_meta")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _make_sn_csv(self):
        """Create a minimal SN mapping CSV in memory."""
        output = io.BytesIO()
        wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
        writer = csv.DictWriter(wrapper, fieldnames=['serial_number', 'config', 'Product', 'unit_number', 'start_date', 'wf_id'])
        writer.writeheader()
        writer.writerow({'serial_number': 'SN001', 'config': 'R2CNM', 'Product': 'B529', 'unit_number': 'ER2-1-1', 'start_date': '20260416', 'wf_id': '1'})
        writer.writerow({'serial_number': 'SN002', 'config': 'R1FNF', 'Product': 'B529', 'unit_number': 'ER1-1-1', 'start_date': '20260416', 'wf_id': '2'})
        wrapper.flush()
        wrapper.detach()
        output.seek(0)
        return output

    def _make_cp_csv(self):
        """Create a minimal CP schedule CSV in memory."""
        output = io.BytesIO()
        wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
        fieldnames = ['wf_id', 'wf id_cp', 'wf id_cp total', 'wf id_cp_nci',
                      'wf id_cp total_nci', 'test category', 'rel event cp',
                      'checkin', 'wf test', 'wf test_cp', 'wf test_cp total',
                      'wf id_rel event', 'wf id_rel event_prev', 'wf id_rel event_next']
        writer = csv.DictWriter(wrapper, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({'wf_id': '1', 'wf id_cp': '0', 'rel event cp': 'REL_T0', 'wf test': '0',
                         'wf id_cp total': '', 'wf id_cp_nci': '', 'wf id_cp total_nci': '',
                         'test category': '', 'checkin': '', 'wf test_cp': '', 'wf test_cp total': '',
                         'wf id_rel event': '', 'wf id_rel event_prev': '', 'wf id_rel event_next': ''})
        writer.writerow({'wf_id': '1', 'wf id_cp': '1', 'rel event cp': 'CP_A', 'wf test': '1',
                         'wf id_cp total': '', 'wf id_cp_nci': '', 'wf id_cp total_nci': '',
                         'test category': '', 'checkin': '', 'wf test_cp': '', 'wf test_cp total': '',
                         'wf id_rel event': '', 'wf id_rel event_prev': '', 'wf id_rel event_next': ''})
        wrapper.flush()
        wrapper.detach()
        output.seek(0)
        return output

    def _make_tp_csv(self):
        """Create a minimal Test Plan CSV in memory."""
        output = io.BytesIO()
        wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
        writer = csv.DictWriter(wrapper, fieldnames=['wf id', 'wf test_1', 'wf test_2', 'wf test_3'])
        writer.writeheader()
        writer.writerow({'wf id': '1', 'wf test_1': 'Long Term HS', 'wf test_2': '', 'wf test_3': ''})
        writer.writerow({'wf id': '2', 'wf test_1': 'Altitude', 'wf test_2': 'Rock Tumble', 'wf test_3': ''})
        wrapper.flush()
        wrapper.detach()
        output.seek(0)
        return output

    def test_upload_sn_mapping_by_filename(self):
        """Upload SN mapping CSV — type detected from filename."""
        data = self._make_sn_csv()
        resp = self.app.post('/api/base-files', data={
            'files': (data, 'Serial Numbers EVT FATP.csv'),
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertTrue(result['success'])
        self.assertEqual(result['parsed']['sn_count'], 2)

    def test_upload_sn_mapping_by_explicit_type(self):
        """Upload SN mapping CSV — type specified explicitly."""
        data = self._make_sn_csv()
        resp = self.app.post('/api/base-files', data={
            'files': (data, 'my_custom_file.csv'),
            'file_type': 'sn_mapping',
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertTrue(result['success'])
        self.assertEqual(result['parsed']['sn_count'], 2)

    def test_upload_cp_schedule(self):
        """Upload CP schedule CSV — type detected from filename."""
        data = self._make_cp_csv()
        resp = self.app.post('/api/base-files', data={
            'files': (data, 'WaterfallCheckpointSchedule.csv'),
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertTrue(result['success'])
        self.assertEqual(result['parsed']['wf_count'], 1)
        # CSV has REL_T0 (boundary, filtered) + CP_A. Only CP_A counts.
        self.assertEqual(result['parsed']['cp_count'], 1)

    def test_upload_test_plan(self):
        """Upload Test Plan CSV — type detected from filename."""
        data = self._make_tp_csv()
        resp = self.app.post('/api/base-files', data={
            'files': (data, 'WaterfallTestPlan.csv'),
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertTrue(result['success'])
        self.assertEqual(result['parsed']['wf_count'], 2)

    def test_upload_no_files_returns_400(self):
        """Upload with no files should return 400."""
        resp = self.app.post('/api/base-files', data={}, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertFalse(result['success'])

    def test_upload_unrecognized_filename_returns_400(self):
        """Upload with unrecognized filename and no explicit type returns 400."""
        data = self._make_sn_csv()
        resp = self.app.post('/api/base-files', data={
            'files': (data, 'random_file.csv'),
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertFalse(result['success'])
        self.assertIn('Cannot identify file type', result['error'])

    def test_upload_invalid_file_type_returns_400(self):
        """Upload with invalid explicit file_type returns 400."""
        data = self._make_sn_csv()
        resp = self.app.post('/api/base-files', data={
            'files': (data, 'file.csv'),
            'file_type': 'nonexistent_type',
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertFalse(result['success'])


class BaseFilesListTests(unittest.TestCase):
    """Test GET /api/base-files endpoint."""

    def setUp(self):
        _ensure_db()
        self.app = api.app.test_client()
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM base_file_meta")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_list_empty(self):
        """GET with no uploaded files returns empty list."""
        resp = self.app.get('/api/base-files')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertEqual(result['files'], [])

    def test_list_after_upload(self):
        """GET after uploading a file returns the file metadata."""
        # Upload a file first
        output = io.BytesIO()
        wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
        writer = csv.DictWriter(wrapper, fieldnames=['serial_number', 'config', 'Product', 'unit_number', 'start_date', 'wf_id'])
        writer.writeheader()
        writer.writerow({'serial_number': 'SN001', 'config': 'R2CNM', 'Product': 'B529', 'unit_number': 'ER2-1-1', 'start_date': '20260416', 'wf_id': '1'})
        wrapper.flush()
        wrapper.detach()
        output.seek(0)

        self.app.post('/api/base-files', data={
            'files': (output, 'Serial Numbers EVT.csv'),
        }, content_type='multipart/form-data')

        resp = self.app.get('/api/base-files')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertEqual(len(result['files']), 1)
        file_info = result['files'][0]
        self.assertEqual(file_info['file_type'], 'sn_mapping')
        self.assertIn('uploaded_at', file_info)
        self.assertIn('parsed_summary', file_info)


class BaseFilesDeleteTests(unittest.TestCase):
    """Test DELETE /api/base-files/:filename endpoint."""

    def setUp(self):
        _ensure_db()
        self.app = api.app.test_client()
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM base_file_meta")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_delete_existing_file(self):
        """DELETE an uploaded file removes it."""
        # Upload first
        output = io.BytesIO()
        wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
        writer = csv.DictWriter(wrapper, fieldnames=['serial_number', 'config', 'Product', 'unit_number', 'start_date', 'wf_id'])
        writer.writeheader()
        writer.writerow({'serial_number': 'SN001', 'config': 'R2CNM', 'Product': 'B529', 'unit_number': 'ER2-1-1', 'start_date': '20260416', 'wf_id': '1'})
        wrapper.flush()
        wrapper.detach()
        output.seek(0)

        self.app.post('/api/base-files', data={
            'files': (output, 'Serial Numbers EVT.csv'),
        }, content_type='multipart/form-data')

        # Delete by file_type
        resp = self.app.delete('/api/base-files/sn_mapping')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertTrue(result['success'])

        # Verify it's gone
        resp = self.app.get('/api/base-files')
        result = resp.get_json()
        self.assertEqual(len(result['files']), 0)

    def test_delete_by_filename(self):
        """DELETE by stored filename also works."""
        # Upload first
        output = io.BytesIO()
        wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
        writer = csv.DictWriter(wrapper, fieldnames=['serial_number', 'config', 'Product', 'unit_number', 'start_date', 'wf_id'])
        writer.writeheader()
        writer.writerow({'serial_number': 'SN001', 'config': 'R2CNM', 'Product': 'B529', 'unit_number': 'ER2-1-1', 'start_date': '20260416', 'wf_id': '1'})
        wrapper.flush()
        wrapper.detach()
        output.seek(0)

        self.app.post('/api/base-files', data={
            'files': (output, 'Serial Numbers EVT.csv'),
        }, content_type='multipart/form-data')

        # Delete by stored filename
        resp = self.app.delete('/api/base-files/sn_mapping.csv')
        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertTrue(result['success'])

    def test_delete_nonexistent_returns_404(self):
        """DELETE a file that doesn't exist returns 404."""
        resp = self.app.delete('/api/base-files/nonexistent_file.csv')
        self.assertEqual(resp.status_code, 404)
        result = resp.get_json()
        self.assertFalse(result['success'])


class BaseFileTypeDetectionTests(unittest.TestCase):
    """Test filename-based file type detection."""

    def test_serial_numbers_keyword(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('Serial Numbers EVT FATP.csv'), 'sn_mapping')

    def test_sn_mapping_keyword(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('sn_mapping.csv'), 'sn_mapping')

    def test_waterfall_checkpoint_schedule(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('WaterfallCheckpointSchedule.csv'), 'checkpoint_schedule')

    def test_checkpoint_schedule_keyword(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('checkpoint_schedule.csv'), 'checkpoint_schedule')

    def test_waterfall_test_plan(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('WaterfallTestPlan.csv'), 'test_plan')

    def test_test_plan_keyword(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('test_plan.csv'), 'test_plan')

    def test_test_schedule_keyword(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('Test Schedule.xlsx'), 'test_schedule')

    def test_test_schedule_alt_keyword(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('test_schedule.xlsx'), 'test_schedule')

    def test_unrecognized_returns_none(self):
        from api import _detect_base_file_type
        self.assertIsNone(_detect_base_file_type('random_file.csv'))

    def test_case_insensitive(self):
        from api import _detect_base_file_type
        self.assertEqual(_detect_base_file_type('SERIAL NUMBERS EVT.csv'), 'sn_mapping')
        self.assertEqual(_detect_base_file_type('waterfallcheckpointschedule.csv'), 'checkpoint_schedule')


if __name__ == '__main__':
    unittest.main()
