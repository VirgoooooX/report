"""
Unit tests for store_raw_records function (Task 8.2).

Validates Requirements 6.3, 8.1, 8.2, 8.3, 8.4:
- Store all parsed records in raw_check_item_records after generation
- Create import_batches entry with statistics
- FAIL records: store test_params as JSON
- PASS records: test_params = NULL
"""
import json
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Set up test DB before importing modules that use db
TEST_DB = tempfile.mktemp(suffix='.db')
import db
db.DB_PATH = TEST_DB
db.init_db()

from checkitem_generator import store_raw_records


class TestStoreRawRecords(unittest.TestCase):
    """Tests for store_raw_records function."""

    def setUp(self):
        """Reset DB tables before each test."""
        conn = db.get_conn()
        conn.execute("DELETE FROM raw_check_item_records")
        conn.execute("DELETE FROM import_batches")
        conn.commit()
        conn.close()

    def test_creates_import_batch_entry(self):
        """An import_batches row is created with correct statistics."""
        records = [
            {
                "serial_number": "SN001", "rel_event": "REL_T0",
                "effective_cp": "REL_T0", "item": "FACT", "status": "PASS",
                "end_time": "2026-05-12 08:00:00", "failing_tests": "",
                "station_id": "STATION_01", "version": "1.0.0",
                "test_params": None, "source_file": "test.csv",
            },
        ]
        summary = {"file_count": 2, "record_count": 1, "valid_sn_count": 1}

        batch_id = store_raw_records(records, summary)

        conn = db.get_conn()
        batch = conn.execute(
            "SELECT * FROM import_batches WHERE id = ?", (batch_id,)
        ).fetchone()
        conn.close()

        self.assertIsNotNone(batch)
        self.assertEqual(batch['file_count'], 2)
        self.assertEqual(batch['record_count'], 1)
        self.assertEqual(batch['valid_sn_count'], 1)
        self.assertEqual(batch['status'], 'completed')
        self.assertIsNotNone(batch['import_date'])
        self.assertIsNotNone(batch['created_at'])

    def test_stores_pass_record_with_null_test_params(self):
        """PASS records have test_params = NULL in the database."""
        records = [
            {
                "serial_number": "SN001", "rel_event": "REL_T0",
                "effective_cp": "REL_T0", "item": "ISB", "status": "PASS",
                "end_time": "2026-05-12 08:00:00", "failing_tests": "",
                "station_id": "STATION_01", "version": "1.0.0",
                "test_params": None, "source_file": "isb.csv",
            },
        ]
        summary = {"file_count": 1, "record_count": 1, "valid_sn_count": 1}

        store_raw_records(records, summary)

        conn = db.get_conn()
        row = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE serial_number = 'SN001'"
        ).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertIsNone(row['test_params'])
        self.assertEqual(row['status'], 'PASS')

    def test_stores_fail_record_with_json_test_params(self):
        """FAIL records have test_params stored as JSON string."""
        params = {"SPK_Single Tone_A Weighting": 84.201, "SPK_Sensitivity@2800": -26.685}
        records = [
            {
                "serial_number": "SN002", "rel_event": "BC_CWCB_SHORT_100%",
                "effective_cp": "BC_CWCB_SHORT_100%", "item": "FACT",
                "status": "FAIL", "end_time": "2026-05-13 15:02:28",
                "failing_tests": "SPK_Single Tone_A Weighting",
                "station_id": "JAWX_J03-1FT-REL01_2_DEVELOPMENT11",
                "version": "3.3.7", "test_params": params,
                "source_file": "fact.csv",
            },
        ]
        summary = {"file_count": 1, "record_count": 1, "valid_sn_count": 1}

        store_raw_records(records, summary)

        conn = db.get_conn()
        row = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE serial_number = 'SN002'"
        ).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertIsNotNone(row['test_params'])
        stored_params = json.loads(row['test_params'])
        self.assertAlmostEqual(stored_params["SPK_Single Tone_A Weighting"], 84.201)
        self.assertAlmostEqual(stored_params["SPK_Sensitivity@2800"], -26.685)

    def test_fail_record_without_params_stores_null(self):
        """FAIL records with no test_params (empty dict or None) store NULL."""
        records = [
            {
                "serial_number": "SN003", "rel_event": "CP1",
                "effective_cp": "CP1", "item": "Cosmetic",
                "status": "FAIL", "end_time": "2026-05-14 10:00:00",
                "failing_tests": "SomeTest",
                "station_id": "STATION_02", "version": "2.0.0",
                "test_params": None, "source_file": "cosmetic.csv",
            },
        ]
        summary = {"file_count": 1, "record_count": 1, "valid_sn_count": 1}

        store_raw_records(records, summary)

        conn = db.get_conn()
        row = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE serial_number = 'SN003'"
        ).fetchone()
        conn.close()

        self.assertIsNone(row['test_params'])

    def test_stores_all_record_fields_correctly(self):
        """All fields from the record are stored in the correct columns."""
        records = [
            {
                "serial_number": "SN_FULL", "rel_event": "BC_CWCB_SHORT_140%",
                "effective_cp": "BC_CWCB_SHORT_140%", "item": "BT-OTA",
                "status": "PASS", "end_time": "2026-05-14 21:34:13",
                "failing_tests": "", "station_id": "JAWX_STATION",
                "version": "3.3.7", "test_params": None,
                "source_file": "bt-ota-export.csv",
            },
        ]
        summary = {"file_count": 1, "record_count": 1, "valid_sn_count": 1}

        batch_id = store_raw_records(records, summary)

        conn = db.get_conn()
        row = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE serial_number = 'SN_FULL'"
        ).fetchone()
        conn.close()

        self.assertEqual(row['import_batch_id'], batch_id)
        self.assertEqual(row['serial_number'], 'SN_FULL')
        self.assertEqual(row['rel_event'], 'BC_CWCB_SHORT_140%')
        self.assertEqual(row['effective_cp'], 'BC_CWCB_SHORT_140%')
        self.assertEqual(row['item'], 'BT-OTA')
        self.assertEqual(row['status'], 'PASS')
        self.assertEqual(row['end_time'], '2026-05-14 21:34:13')
        self.assertEqual(row['failing_tests'], '')
        self.assertEqual(row['station_id'], 'JAWX_STATION')
        self.assertEqual(row['version'], '3.3.7')
        self.assertEqual(row['source_file'], 'bt-ota-export.csv')

    def test_multiple_records_stored(self):
        """Multiple records from a single batch are all stored."""
        records = [
            {
                "serial_number": "SN_A", "rel_event": "CP1",
                "effective_cp": "CP1", "item": "FACT", "status": "PASS",
                "end_time": "2026-05-12 08:00:00", "failing_tests": "",
                "station_id": "ST1", "version": "1.0", "test_params": None,
                "source_file": "fact.csv",
            },
            {
                "serial_number": "SN_B", "rel_event": "CP2",
                "effective_cp": "CP2", "item": "ISB", "status": "FAIL",
                "end_time": "2026-05-13 09:00:00",
                "failing_tests": "TestFail",
                "station_id": "ST2", "version": "2.0",
                "test_params": {"param1": 1.5},
                "source_file": "isb.csv",
            },
            {
                "serial_number": "SN_A", "rel_event": "CP2",
                "effective_cp": "CP2", "item": "Charging", "status": "PASS",
                "end_time": "2026-05-14 10:00:00", "failing_tests": "",
                "station_id": "ST1", "version": "1.0", "test_params": None,
                "source_file": "charging.csv",
            },
        ]
        summary = {"file_count": 3, "record_count": 3, "valid_sn_count": 2}

        batch_id = store_raw_records(records, summary)

        conn = db.get_conn()
        rows = conn.execute(
            "SELECT * FROM raw_check_item_records WHERE import_batch_id = ?",
            (batch_id,)
        ).fetchall()
        conn.close()

        self.assertEqual(len(rows), 3)

    def test_batch_id_links_records_to_batch(self):
        """All records in a batch share the same import_batch_id."""
        records = [
            {
                "serial_number": f"SN_{i}", "rel_event": "CP1",
                "effective_cp": "CP1", "item": "FACT", "status": "PASS",
                "end_time": f"2026-05-12 0{i}:00:00", "failing_tests": "",
                "station_id": "ST1", "version": "1.0", "test_params": None,
                "source_file": "fact.csv",
            }
            for i in range(5)
        ]
        summary = {"file_count": 1, "record_count": 5, "valid_sn_count": 5}

        batch_id = store_raw_records(records, summary)

        conn = db.get_conn()
        rows = conn.execute(
            "SELECT DISTINCT import_batch_id FROM raw_check_item_records"
        ).fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['import_batch_id'], batch_id)

    def test_empty_records_creates_batch_with_no_records(self):
        """An empty records list still creates a batch entry but no record rows."""
        summary = {"file_count": 1, "record_count": 0, "valid_sn_count": 0}

        batch_id = store_raw_records([], summary)

        conn = db.get_conn()
        batch = conn.execute(
            "SELECT * FROM import_batches WHERE id = ?", (batch_id,)
        ).fetchone()
        record_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM raw_check_item_records"
        ).fetchone()['cnt']
        conn.close()

        self.assertIsNotNone(batch)
        self.assertEqual(record_count, 0)

    def test_returns_batch_id(self):
        """store_raw_records returns the created batch ID."""
        records = [
            {
                "serial_number": "SN001", "rel_event": "CP1",
                "effective_cp": "CP1", "item": "FACT", "status": "PASS",
                "end_time": "2026-05-12 08:00:00", "failing_tests": "",
                "station_id": "ST1", "version": "1.0", "test_params": None,
                "source_file": "fact.csv",
            },
        ]
        summary = {"file_count": 1, "record_count": 1, "valid_sn_count": 1}

        batch_id = store_raw_records(records, summary)

        self.assertIsInstance(batch_id, int)
        self.assertGreater(batch_id, 0)


if __name__ == '__main__':
    unittest.main()
