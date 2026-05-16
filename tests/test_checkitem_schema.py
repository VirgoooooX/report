"""
Tests for Check Item CSV Import database schema (Requirements 13.1-13.6).

Verifies that init_db() creates the required tables and indexes for:
- base_file_meta
- import_batches
- raw_check_item_records (with 3 indexes)
"""
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


class BaseFileMetaSchemaTests(unittest.TestCase):
    """Requirement 13.1: base_file_meta table with correct columns."""

    def test_base_file_meta_table_exists(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='base_file_meta'"
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            conn.close()
            os.remove(path)

    def test_base_file_meta_has_correct_columns(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            columns = conn.execute("PRAGMA table_info(base_file_meta)").fetchall()
            col_names = [c['name'] for c in columns]
            expected = ['id', 'file_type', 'original_filename', 'stored_path', 'uploaded_at', 'parsed_summary']
            for col in expected:
                self.assertIn(col, col_names, f"Missing column: {col}")
        finally:
            conn.close()
            os.remove(path)

    def test_base_file_meta_insert_and_read(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            conn.execute(
                """INSERT INTO base_file_meta (file_type, original_filename, stored_path, uploaded_at, parsed_summary)
                   VALUES (?, ?, ?, ?, ?)""",
                ('sn_mapping', 'sn_file.csv', 'rawdata/base/sn_mapping.csv', '2026-05-15T10:00:00', '{"sn_count": 200}')
            )
            row = conn.execute("SELECT * FROM base_file_meta").fetchone()
            self.assertEqual(row['file_type'], 'sn_mapping')
            self.assertEqual(row['original_filename'], 'sn_file.csv')
            self.assertEqual(row['stored_path'], 'rawdata/base/sn_mapping.csv')
            self.assertEqual(row['uploaded_at'], '2026-05-15T10:00:00')
            self.assertEqual(row['parsed_summary'], '{"sn_count": 200}')
        finally:
            conn.close()
            os.remove(path)


class ImportBatchesSchemaTests(unittest.TestCase):
    """Requirement 13.3: import_batches table with correct columns."""

    def test_import_batches_table_exists(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='import_batches'"
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            conn.close()
            os.remove(path)

    def test_import_batches_has_correct_columns(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            columns = conn.execute("PRAGMA table_info(import_batches)").fetchall()
            col_names = [c['name'] for c in columns]
            expected = ['id', 'import_date', 'created_at', 'file_count', 'record_count', 'valid_sn_count', 'status']
            for col in expected:
                self.assertIn(col, col_names, f"Missing column: {col}")
        finally:
            conn.close()
            os.remove(path)

    def test_import_batches_default_status(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            conn.execute(
                """INSERT INTO import_batches (import_date, created_at, file_count, record_count, valid_sn_count)
                   VALUES (?, ?, ?, ?, ?)""",
                ('2026-05-15', '2026-05-15T10:00:00', 6, 1200, 180)
            )
            row = conn.execute("SELECT * FROM import_batches").fetchone()
            self.assertEqual(row['import_date'], '2026-05-15')
            self.assertEqual(row['file_count'], 6)
            self.assertEqual(row['record_count'], 1200)
            self.assertEqual(row['valid_sn_count'], 180)
            self.assertEqual(row['status'], 'completed')
        finally:
            conn.close()
            os.remove(path)


class RawCheckItemRecordsSchemaTests(unittest.TestCase):
    """Requirement 13.2: raw_check_item_records table with correct columns."""

    def test_raw_check_item_records_table_exists(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_check_item_records'"
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            conn.close()
            os.remove(path)

    def test_raw_check_item_records_has_correct_columns(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            columns = conn.execute("PRAGMA table_info(raw_check_item_records)").fetchall()
            col_names = [c['name'] for c in columns]
            expected = [
                'id', 'import_batch_id', 'import_date', 'serial_number',
                'rel_event', 'effective_cp', 'item', 'status', 'end_time',
                'failing_tests', 'station_id', 'version', 'test_params', 'source_file'
            ]
            for col in expected:
                self.assertIn(col, col_names, f"Missing column: {col}")
        finally:
            conn.close()
            os.remove(path)

    def test_raw_check_item_records_insert_and_read(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            # Create a batch first
            conn.execute(
                """INSERT INTO import_batches (import_date, created_at, file_count, record_count, valid_sn_count)
                   VALUES (?, ?, ?, ?, ?)""",
                ('2026-05-15', '2026-05-15T10:00:00', 6, 100, 50)
            )
            batch_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']

            conn.execute(
                """INSERT INTO raw_check_item_records
                   (import_batch_id, import_date, serial_number, rel_event, effective_cp,
                    item, status, end_time, failing_tests, station_id, version, test_params, source_file)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (batch_id, '2026-05-15', 'CY21NXH72X', 'BC_CWCB_SHORT_100%', 'BC_CWCB_SHORT_100%',
                 'FACT', 'FAIL', '2026-05-13 15:02:28', 'SPK_Single Tone_A Weighting',
                 'JAWX_J03-1FT-REL01_2_DEVELOPMENT11', '3.3.7',
                 '{"SPK_Single Tone_A Weighting": 84.201}', 'R2-Export-FACT.csv')
            )
            row = conn.execute("SELECT * FROM raw_check_item_records").fetchone()
            self.assertEqual(row['serial_number'], 'CY21NXH72X')
            self.assertEqual(row['rel_event'], 'BC_CWCB_SHORT_100%')
            self.assertEqual(row['effective_cp'], 'BC_CWCB_SHORT_100%')
            self.assertEqual(row['item'], 'FACT')
            self.assertEqual(row['status'], 'FAIL')
            self.assertEqual(row['failing_tests'], 'SPK_Single Tone_A Weighting')
            self.assertEqual(row['station_id'], 'JAWX_J03-1FT-REL01_2_DEVELOPMENT11')
            self.assertEqual(row['version'], '3.3.7')
            self.assertEqual(row['source_file'], 'R2-Export-FACT.csv')
        finally:
            conn.close()
            os.remove(path)


class RawCheckItemRecordsIndexTests(unittest.TestCase):
    """Requirements 13.4, 13.5, 13.6: indexes on raw_check_item_records."""

    def test_idx_raw_records_sn_exists(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_raw_records_sn'"
            ).fetchone()
            self.assertIsNotNone(row, "Index idx_raw_records_sn should exist")
        finally:
            conn.close()
            os.remove(path)

    def test_idx_raw_records_batch_exists(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_raw_records_batch'"
            ).fetchone()
            self.assertIsNotNone(row, "Index idx_raw_records_batch should exist")
        finally:
            conn.close()
            os.remove(path)

    def test_idx_raw_records_cp_exists(self):
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_raw_records_cp'"
            ).fetchone()
            self.assertIsNotNone(row, "Index idx_raw_records_cp should exist")
        finally:
            conn.close()
            os.remove(path)

    def test_idx_raw_records_sn_covers_serial_number(self):
        """Verify the SN index is on the serial_number column."""
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            info = conn.execute("PRAGMA index_info(idx_raw_records_sn)").fetchall()
            col_names = [row['name'] for row in info]
            self.assertIn('serial_number', col_names)
        finally:
            conn.close()
            os.remove(path)

    def test_idx_raw_records_batch_covers_import_batch_id(self):
        """Verify the batch index is on the import_batch_id column."""
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            info = conn.execute("PRAGMA index_info(idx_raw_records_batch)").fetchall()
            col_names = [row['name'] for row in info]
            self.assertIn('import_batch_id', col_names)
        finally:
            conn.close()
            os.remove(path)

    def test_idx_raw_records_cp_is_composite(self):
        """Verify the CP index is a composite on (serial_number, effective_cp, item)."""
        conn, path = temp_conn()
        try:
            db.init_db(conn=conn)
            info = conn.execute("PRAGMA index_info(idx_raw_records_cp)").fetchall()
            col_names = [row['name'] for row in info]
            self.assertEqual(col_names, ['serial_number', 'effective_cp', 'item'])
        finally:
            conn.close()
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
