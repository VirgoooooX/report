"""Batch B step 3.4b Class A — completion math queries must exclude
``current_cp_definitions`` rows tagged ``is_boundary=1``. Boundary rows
exist in the Plan layer purely to align cp_idx with daily lifecycle facts;
they should never inflate ``total_cps`` denominators.

See docs/plans/2026-05-17-rel-t0-daily-report-second-cut.md.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import db


def _temp_conn():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    old_db_path = db.DB_PATH
    db.DB_PATH = path
    conn = db.get_conn()
    db.init_db(conn=conn)
    return conn, path, old_db_path


def _seed_with_boundary(conn):
    """Insert a typical WF with REL_T0 (boundary) + 3 real CPs + REL_TFINAL."""
    db.save_current_cp_definitions(conn, 0, {
        '16.1': [
            {'cp_idx': 0, 'cp_name': 'REL_T0', 'test_idx': 0,
             'check_items': [], 'is_boundary': 1},
            {'cp_idx': 1, 'cp_name': 'CP_A', 'test_idx': 0,
             'check_items': [], 'is_boundary': 0},
            {'cp_idx': 2, 'cp_name': 'CP_B', 'test_idx': 0,
             'check_items': [], 'is_boundary': 0},
            {'cp_idx': 3, 'cp_name': 'CP_C', 'test_idx': 0,
             'check_items': [], 'is_boundary': 0},
            {'cp_idx': 4, 'cp_name': 'REL_TFINAL', 'test_idx': 0,
             'check_items': [], 'is_boundary': 1},
        ],
    })
    conn.commit()


class CompletionMathExcludesBoundaryTests(unittest.TestCase):
    """Each audited query in §3.4b Class A must skip is_boundary=1 rows."""

    def setUp(self):
        self.conn, self.path, self._old_db_path = _temp_conn()

    def tearDown(self):
        self.conn.close()
        db.DB_PATH = self._old_db_path
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_count_per_wf_excludes_boundary(self):
        """SELECT COUNT(*) ... WHERE wf_num=? AND is_boundary=0."""
        _seed_with_boundary(self.conn)
        row = self.conn.execute(
            "SELECT COUNT(*) AS c FROM current_cp_definitions "
            "WHERE wf_num = ? AND is_boundary = 0",
            ('16.1',),
        ).fetchone()
        self.assertEqual(row['c'], 3)

    def test_count_group_by_wf_excludes_boundary(self):
        """SELECT wf_num, COUNT(*) ... GROUP BY wf_num must skip boundaries."""
        _seed_with_boundary(self.conn)
        row = self.conn.execute(
            "SELECT wf_num, COUNT(*) AS total_cps FROM current_cp_definitions "
            "WHERE is_boundary = 0 GROUP BY wf_num"
        ).fetchone()
        self.assertEqual(row['wf_num'], '16.1')
        self.assertEqual(row['total_cps'], 3)

    def test_max_cp_idx_per_test_excludes_boundary(self):
        """MAX(cp_idx) WHERE wf_num=? AND test_idx=? AND is_boundary=0.

        With REL_TFINAL=cp_idx 4 (boundary), the largest non-boundary
        cp_idx is 3 (CP_C). A naive query would return 4 and break
        last-CP attribution.
        """
        _seed_with_boundary(self.conn)
        row = self.conn.execute(
            "SELECT MAX(cp_idx) AS last_cp FROM current_cp_definitions "
            "WHERE wf_num = ? AND test_idx = ? AND is_boundary = 0",
            ('16.1', 0),
        ).fetchone()
        self.assertEqual(row['last_cp'], 3)

    def test_test_slots_distinct_excludes_boundary(self):
        """SELECT DISTINCT wf_num, test_idx ... WHERE is_boundary=0.

        REL_T0/REL_TFINAL share test_idx=0 here; this test still passes
        with one slot, but if a future schema put boundaries on a
        synthetic test_idx the filter prevents leaks.
        """
        _seed_with_boundary(self.conn)
        rows = self.conn.execute(
            "SELECT DISTINCT wf_num, test_idx FROM current_cp_definitions "
            "WHERE is_boundary = 0 ORDER BY wf_num, test_idx"
        ).fetchall()
        self.assertEqual([(r['wf_num'], r['test_idx']) for r in rows], [('16.1', 0)])

    def test_min_max_cp_per_test_excludes_boundary(self):
        """MIN/MAX(cp_idx) range per test must reflect non-boundary CPs."""
        _seed_with_boundary(self.conn)
        row = self.conn.execute(
            """SELECT MIN(cp_idx) AS first_cp, MAX(cp_idx) AS last_cp
               FROM current_cp_definitions
               WHERE wf_num = ? AND test_idx = ? AND is_boundary = 0""",
            ('16.1', 0),
        ).fetchone()
        # Real CPs span cp_idx 1..3; boundary rows at 0 and 4 are excluded.
        self.assertEqual(row['first_cp'], 1)
        self.assertEqual(row['last_cp'], 3)


if __name__ == '__main__':
    unittest.main()
