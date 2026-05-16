"""
Unit tests for /api/raw-records endpoint (Task 11.1).

Validates Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6:
- Query by SN returns all records ordered by end_time DESC
- Query by unit number resolves to SN and returns records
- Item filter returns only matching records
- Date range filter returns only records within range
- FAIL records include failing_tests and parsed test_params JSON
- Response includes SN metadata (unit_number, config, wf_id)
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
import base_manager


def _ensure_db():
    """Re-initialize DB in case another test module changed DB_PATH."""
    db.DB_PATH = TEST_DB
    db.init_db()


def _upload_sn_mapping(app_client):
    """Upload a minimal SN mapping so the endpoint can resolve metadata."""
    output = io.BytesIO()
    wrapper = io.TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.DictWriter(wrapper, fieldnames=[
        'serial_number', 'config', 'Product', 'unit_number', 'start_date', 'wf_id'
    ])
    writer.writeheader()
    writer.writerow({
        'serial_number': 'CY21NXH72X', 'config': 'R2CNM', 'Product': 'B529',
        'unit_number': 'ER2-1-1', 'start_date': '20260416', 'wf_id': '1'
    })
    writer.writerow({
        'serial_number': 'SN_OTHER', 'config': 'R1FNF', 'Product': 'B529',
        'unit_number': 'ER1-2-3', 'start_date': '20260416', 'wf_id': '2'
    })
    wrapper.flush()
    wrapper.detach()
    output.seek(0)

    app_client.post('/api/base-files', data={
        'files': (output, 'Serial Numbers EVT FATP.csv'),
    }, content_type='multipart/form-data')


def _insert_test_records(conn):
    """Insert sample raw_check_item_records for testing."""
    today = '2026-05-15'
    # Create an import batch
    cur = conn.execute(
        """INSERT INTO import_batches
           (import_date, created_at, file_count, record_count, valid_sn_count, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (today, '2026-05-15T10:00:00', 2, 5, 2, 'completed')
    )
    batch_id = cur.lastrowid

    records = [
        (batch_id, today, 'CY21NXH72X', 'BC_CWCB_SHORT_140%', 'BC_CWCB_SHORT_140%',
         'FACT', 'PASS', '2026-05-14 21:34:13', None, 'JAWX_J03-1FT-REL01_2_DEVELOPMENT11',
         '3.3.7', None, 'ORT-FACT_20260514.csv'),
        (batch_id, today, 'CY21NXH72X', 'BC_CWCB_SHORT_100%', 'BC_CWCB_SHORT_100%',
         'FACT', 'FAIL', '2026-05-13 15:02:28', 'SPK_Single Tone_A Weighting',
         'JAWX_J03-1FT-REL01_2_DEVELOPMENT11', '3.3.7',
         json.dumps({'SPK_Single Tone_A Weighting': 84.201, 'SPK_Sensitivity@2800': -26.685}),
         'ORT-FACT_20260513.csv'),
        (batch_id, today, 'CY21NXH72X', 'BC_CWCB_SHORT_100%', 'BC_CWCB_SHORT_100%',
         'ISB', 'PASS', '2026-05-12 08:57:00', None, 'JAWX_J03-1FT-REL01_2_DEVELOPMENT11',
         '1.1.3', None, 'ORT-ISB_20260512.csv'),
        (batch_id, today, 'CY21NXH72X', 'TC_300CYCLES', 'TC_300CYCLES',
         'BT-OTA', 'PASS', '2026-04-30 07:40:00', None, 'JAWX_J03-1FT-REL01_2_DEVELOPMENT11',
         '2.0.1', None, 'BT-OTA_20260430.csv'),
        (batch_id, today, 'SN_OTHER', 'REL_T0', 'REL_T0',
         'FACT', 'PASS', '2026-05-10 09:00:00', None, 'STATION_02',
         '3.3.7', None, 'ORT-FACT_20260510.csv'),
    ]

    conn.executemany(
        """INSERT INTO raw_check_item_records
           (import_batch_id, import_date, serial_number, rel_event, effective_cp,
            item, status, end_time, failing_tests, station_id, version, test_params, source_file)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        records
    )
    conn.commit()


class TestRawRecordsQueryBySN(unittest.TestCase):
    """Test /api/raw-records?sn=... queries."""

    def setUp(self):
        _ensure_db()
        self.app = api.app.test_client()
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM raw_check_item_records")
        self.conn.execute("DELETE FROM import_batches")
        self.conn.execute("DELETE FROM base_file_meta")
        self.conn.commit()
        _upload_sn_mapping(self.app)
        _insert_test_records(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_query_by_sn_returns_records(self):
        """Query by SN returns all records for that SN."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['sn'], 'CY21NXH72X')
        self.assertEqual(len(data['records']), 4)

    def test_query_by_sn_includes_metadata(self):
        """Response includes SN metadata from mapping."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X')
        data = resp.get_json()
        self.assertEqual(data['unit_number'], 'ER2-1-1')
        self.assertEqual(data['config'], 'R2CNM')
        self.assertEqual(data['wf_id'], '1')

    def test_query_by_sn_ordered_by_end_time_desc(self):
        """Records are ordered by end_time descending."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X')
        data = resp.get_json()
        end_times = [r['end_time'] for r in data['records']]
        self.assertEqual(end_times, sorted(end_times, reverse=True))

    def test_fail_record_includes_failing_tests(self):
        """FAIL records include failing_tests string."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X')
        data = resp.get_json()
        fail_records = [r for r in data['records'] if r['status'] == 'FAIL']
        self.assertEqual(len(fail_records), 1)
        self.assertEqual(fail_records[0]['failing_tests'], 'SPK_Single Tone_A Weighting')

    def test_fail_record_includes_parsed_test_params(self):
        """FAIL records include parsed test_params JSON."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X')
        data = resp.get_json()
        fail_records = [r for r in data['records'] if r['status'] == 'FAIL']
        self.assertEqual(len(fail_records), 1)
        params = fail_records[0]['test_params']
        self.assertIsInstance(params, dict)
        self.assertAlmostEqual(params['SPK_Single Tone_A Weighting'], 84.201)
        self.assertAlmostEqual(params['SPK_Sensitivity@2800'], -26.685)

    def test_pass_record_has_null_test_params(self):
        """PASS records have test_params as None."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X')
        data = resp.get_json()
        pass_records = [r for r in data['records'] if r['status'] == 'PASS']
        for rec in pass_records:
            self.assertIsNone(rec['test_params'])

    def test_query_nonexistent_sn_returns_empty(self):
        """Query for a SN with no records returns empty records list."""
        resp = self.app.get('/api/raw-records?sn=NONEXISTENT')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['sn'], 'NONEXISTENT')
        self.assertEqual(data['records'], [])


class TestRawRecordsQueryByUnit(unittest.TestCase):
    """Test /api/raw-records?unit=... queries."""

    def setUp(self):
        _ensure_db()
        self.app = api.app.test_client()
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM raw_check_item_records")
        self.conn.execute("DELETE FROM import_batches")
        self.conn.execute("DELETE FROM base_file_meta")
        self.conn.commit()
        _upload_sn_mapping(self.app)
        _insert_test_records(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_query_by_unit_resolves_to_sn(self):
        """Query by unit number resolves to the correct SN."""
        resp = self.app.get('/api/raw-records?unit=ER2-1-1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['sn'], 'CY21NXH72X')
        self.assertEqual(data['unit_number'], 'ER2-1-1')
        self.assertEqual(len(data['records']), 4)

    def test_query_by_unit_not_found(self):
        """Query by nonexistent unit number returns 404."""
        resp = self.app.get('/api/raw-records?unit=NONEXISTENT')
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertIn('error', data)


class TestRawRecordsFilters(unittest.TestCase):
    """Test item and date range filters."""

    def setUp(self):
        _ensure_db()
        self.app = api.app.test_client()
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM raw_check_item_records")
        self.conn.execute("DELETE FROM import_batches")
        self.conn.execute("DELETE FROM base_file_meta")
        self.conn.commit()
        _upload_sn_mapping(self.app)
        _insert_test_records(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_item_filter(self):
        """Item filter returns only matching records."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X&item=FACT')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data['records']), 2)
        for rec in data['records']:
            self.assertEqual(rec['item'], 'FACT')

    def test_date_from_filter(self):
        """From date filter excludes earlier records."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X&from=2026-05-12')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should include records from 2026-05-12, 2026-05-13, 2026-05-14
        self.assertEqual(len(data['records']), 3)

    def test_date_to_filter(self):
        """To date filter excludes later records."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X&to=2026-05-12')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should include records from 2026-04-30 and 2026-05-12
        self.assertEqual(len(data['records']), 2)

    def test_date_range_filter(self):
        """Combined from/to date filter returns records within range."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X&from=2026-05-12&to=2026-05-13')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should include records from 2026-05-12 and 2026-05-13
        self.assertEqual(len(data['records']), 2)

    def test_combined_item_and_date_filter(self):
        """Combined item + date filter works together."""
        resp = self.app.get('/api/raw-records?sn=CY21NXH72X&item=FACT&from=2026-05-14')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data['records']), 1)
        self.assertEqual(data['records'][0]['item'], 'FACT')
        self.assertEqual(data['records'][0]['status'], 'PASS')


class TestRawRecordsValidation(unittest.TestCase):
    """Test error handling and validation."""

    def setUp(self):
        _ensure_db()
        self.app = api.app.test_client()

    def test_no_params_returns_400(self):
        """Request without sn or unit returns 400."""
        resp = self.app.get('/api/raw-records')
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('error', data)

    def test_empty_params_returns_400(self):
        """Request with empty sn and unit returns 400."""
        resp = self.app.get('/api/raw-records?sn=&unit=')
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()
