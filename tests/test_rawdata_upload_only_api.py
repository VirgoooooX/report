import io
import os
import tempfile
import unittest
from unittest.mock import patch

import db

TEST_DB = tempfile.mktemp(suffix='.db')
db.DB_PATH = TEST_DB
db.init_db()

import api


class RawdataUploadOnlyApiTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.rawdata_dir = self.tmpdir.name
        self.parsed_dir = os.path.join(self.rawdata_dir, 'parsed')
        os.makedirs(self.parsed_dir, exist_ok=True)
        self.client = api.app.test_client()
        self.conn = db.get_conn()
        self.conn.execute("DELETE FROM reports")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_upload_rawdata_files_saves_without_importing_report(self):
        daily_name = 'M60 EVT Rel Daily Report_20260515.xlsx'
        fa_name = 'M60 EVT REL FA Tracker 20260515.xlsx'

        with patch.object(api, 'RAWDATA_DIR', self.rawdata_dir), patch.object(api, 'PARSED_DIR', self.parsed_dir):
            resp = self.client.post('/api/settings/rawdata/upload', data={
                'daily_report': (io.BytesIO(b'daily bytes'), daily_name),
                'fa_tracker': (io.BytesIO(b'fa bytes'), fa_name),
            }, content_type='multipart/form-data')

        self.assertEqual(resp.status_code, 200)
        result = resp.get_json()
        self.assertTrue(result['success'])
        self.assertEqual(result['daily_report']['name'], daily_name)
        self.assertEqual(result['fa_tracker']['name'], fa_name)
        self.assertTrue(os.path.exists(os.path.join(self.rawdata_dir, daily_name)))
        self.assertTrue(os.path.exists(os.path.join(self.rawdata_dir, fa_name)))
        self.assertFalse(os.path.exists(os.path.join(self.parsed_dir, daily_name)))

        reports = self.conn.execute("SELECT * FROM reports").fetchall()
        self.assertEqual(reports, [])

    def test_upload_rawdata_files_rejects_invalid_daily_report_name(self):
        with patch.object(api, 'RAWDATA_DIR', self.rawdata_dir), patch.object(api, 'PARSED_DIR', self.parsed_dir):
            resp = self.client.post('/api/settings/rawdata/upload', data={
                'daily_report': (io.BytesIO(b'daily bytes'), 'random.xlsx'),
            }, content_type='multipart/form-data')

        self.assertEqual(resp.status_code, 400)
        result = resp.get_json()
        self.assertFalse(result['success'])
        self.assertIn('Invalid Daily Report filename', result['error'])


if __name__ == '__main__':
    unittest.main()
