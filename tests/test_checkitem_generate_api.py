"""
Integration tests for /api/checkitem/generate endpoint (Task 8.1).

Validates Requirements 6.1, 6.2:
- POST /api/checkitem/generate — accept CSV files, return Excel stream
- Return 400 if Base files not uploaded
- Return 400 if no files provided
- Return 400 if no valid data in CSV files
"""
import csv
import io
import os
import tempfile
import unittest

# Set up test DB before importing api
TEST_DB = tempfile.mktemp(suffix='.db')
import db
db.DB_PATH = TEST_DB
db.init_db()

import api


def _make_sn_csv():
    """Create a minimal SN mapping CSV in memory."""
    output = io.BytesIO()
    wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.DictWriter(wrapper, fieldnames=[
        'serial_number', 'config', 'Product', 'unit_number', 'start_date', 'wf_id'
    ])
    writer.writeheader()
    writer.writerow({
        'serial_number': 'SN001', 'config': 'R2CNM', 'Product': 'B529',
        'unit_number': 'ER2-1-1', 'start_date': '20260416', 'wf_id': '1'
    })
    writer.writerow({
        'serial_number': 'SN002', 'config': 'R1FNF', 'Product': 'B529',
        'unit_number': 'ER1-1-1', 'start_date': '20260416', 'wf_id': '1'
    })
    wrapper.flush()
    wrapper.detach()
    output.seek(0)
    return output


def _make_cp_csv():
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


def _make_tp_csv():
    """Create a minimal Test Plan CSV in memory."""
    output = io.BytesIO()
    wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.DictWriter(wrapper, fieldnames=['wf id', 'wf test_1', 'wf test_2', 'wf test_3'])
    writer.writeheader()
    writer.writerow({'wf id': '1', 'wf test_1': 'Long Term HS', 'wf test_2': '', 'wf test_3': ''})
    wrapper.flush()
    wrapper.detach()
    output.seek(0)
    return output


def _upload_base_files(client):
    """Upload all required Base files to set up the system for generation."""
    # Upload SN mapping
    client.post('/api/base-files', data={
        'files': (_make_sn_csv(), 'Serial Numbers EVT FATP.csv'),
    }, content_type='multipart/form-data')

    # Upload CP schedule
    client.post('/api/base-files', data={
        'files': (_make_cp_csv(), 'WaterfallCheckpointSchedule.csv'),
    }, content_type='multipart/form-data')

    # Upload Test Plan
    client.post('/api/base-files', data={
        'files': (_make_tp_csv(), 'WaterfallTestPlan.csv'),
    }, content_type='multipart/form-data')


def _make_checkitem_csv(item_keyword, serial_numbers, status='PASS'):
    """Create a minimal check item CSV with given SNs and status."""
    output = io.BytesIO()
    wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
    fieldnames = [
        'SerialNumber', 'REL Event', 'Test Pass/Fail Status', 'EndTime',
        'List of Failing Tests', 'Station ID', 'Version',
        'col8', 'col9', 'col10', 'col11', 'col12', 'col13',
        'Param1', 'Param2',
    ]
    writer = csv.DictWriter(wrapper, fieldnames=fieldnames)
    writer.writeheader()
    for sn in serial_numbers:
        row = {
            'SerialNumber': sn,
            'REL Event': 'REL_T0',
            'Test Pass/Fail Status': status,
            'EndTime': '2026-05-15 10:00:00',
            'List of Failing Tests': '' if status == 'PASS' else 'TestA',
            'Station ID': 'STATION_01',
            'Version': '1.0.0',
            'col8': '', 'col9': '', 'col10': '', 'col11': '', 'col12': '', 'col13': '',
            'Param1': '' if status == 'PASS' else '1.5',
            'Param2': '' if status == 'PASS' else '2.5',
        }
        writer.writerow(row)
    wrapper.flush()
    wrapper.detach()
    output.seek(0)
    return output


class CheckitemGenerateNoFilesTests(unittest.TestCase):
    """Test /api/checkitem/generate with no files."""

    def setUp(self):
        db.DB_PATH = TEST_DB
        self.app = api.app.test_client()

    def test_no_files_returns_400(self):
        """POST with no files should return 400."""
        resp = self.app.post('/api/checkitem/generate', data={},
                            content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertFalse(result['success'])
        self.assertIn('No files provided', result['error'])


class CheckitemGenerateNoBaseTests(unittest.TestCase):
    """Test /api/checkitem/generate when Base files not uploaded."""

    def setUp(self):
        db.DB_PATH = TEST_DB
        self.app = api.app.test_client()
        # Clear base file metadata to simulate no Base files
        conn = db.get_conn()
        conn.execute("DELETE FROM base_file_meta")
        conn.commit()
        conn.close()

    def test_no_base_files_returns_400(self):
        """POST when Base files not uploaded should return 400."""
        csv_data = _make_checkitem_csv('FACT', ['SN001'])
        resp = self.app.post('/api/checkitem/generate', data={
            'files': (csv_data, 'ORT-FACT_20260515.csv'),
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertFalse(result['success'])
        # Should mention Base files need to be uploaded
        self.assertIn('Base', result['error'])


class CheckitemGenerateSuccessTests(unittest.TestCase):
    """Test /api/checkitem/generate with valid data."""

    def setUp(self):
        db.DB_PATH = TEST_DB
        self.app = api.app.test_client()
        # Clear base file metadata and re-upload
        conn = db.get_conn()
        conn.execute("DELETE FROM base_file_meta")
        conn.commit()
        conn.close()
        _upload_base_files(self.app)

    def test_generate_returns_excel(self):
        """POST with valid CSV files should return Excel file."""
        csv_data = _make_checkitem_csv('FACT', ['SN001', 'SN002'])
        resp = self.app.post('/api/checkitem/generate', data={
            'files': (csv_data, 'ORT-FACT_20260515.csv'),
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        # Check Content-Type
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resp.content_type
        )
        # Check Content-Disposition header
        content_disp = resp.headers.get('Content-Disposition', '')
        self.assertIn('attachment', content_disp)
        self.assertIn('M60 EVT Rel Daily Report_', content_disp)
        self.assertIn('.xlsx', content_disp)
        # Check response has content (Excel bytes)
        self.assertGreater(len(resp.data), 0)

    def test_generate_multiple_csv_files(self):
        """POST with multiple CSV files should return Excel file."""
        csv_fact = _make_checkitem_csv('FACT', ['SN001', 'SN002'])
        csv_isb = _make_checkitem_csv('ISB', ['SN001', 'SN002'])
        resp = self.app.post('/api/checkitem/generate', data={
            'files': [
                (csv_fact, 'ORT-FACT_20260515.csv'),
                (csv_isb, 'ORT-ISB_20260515.csv'),
            ],
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resp.content_type
        )

    def test_generate_no_valid_data_returns_400(self):
        """POST with CSV containing only invalid SNs should return 400."""
        csv_data = _make_checkitem_csv('FACT', ['INVALID_SN_999'])
        resp = self.app.post('/api/checkitem/generate', data={
            'files': (csv_data, 'ORT-FACT_20260515.csv'),
        }, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertFalse(result['success'])

    def test_generate_unrecognized_file_skipped(self):
        """POST with unrecognized filename should skip it; if no valid files, return 400."""
        csv_data = _make_checkitem_csv('FACT', ['SN001'])
        resp = self.app.post('/api/checkitem/generate', data={
            'files': (csv_data, 'unknown_file_20260515.csv'),
        }, content_type='multipart/form-data')
        # Unrecognized file is skipped → no valid data → 400
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
