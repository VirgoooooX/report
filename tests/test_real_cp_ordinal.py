"""Batch B step 3.4b Class B — db.get_real_cp_ordinal must compute the
1-based ordinal of a CP within the non-boundary CPs of a WF.

Used by api_sn_lookup to render per-SN percentage as
``real_ordinal / total_cps`` instead of ``(cp_idx + 1) / total_cps``,
which would mis-attribute the first real CP as "2/N" when REL_T0 occupies
``cp_idx = 0``.

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


class GetRealCpOrdinalTests(unittest.TestCase):
    """Canonical layout: REL_T0(boundary) at cp_idx=0,
    CP_A/B/C(real) at cp_idx=1/2/3, REL_TFINAL(boundary) at cp_idx=4."""

    def setUp(self):
        self.conn, self.path, self._old_db_path = _temp_conn()
        db.save_current_cp_definitions(self.conn, 0, {
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
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        db.DB_PATH = self._old_db_path
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_at_rel_t0_returns_zero(self):
        """SN sitting at REL_T0 boundary → 0 of N real CPs done."""
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '16.1', 0), 0)

    def test_at_first_real_cp_returns_one(self):
        """SN at CP_A (cp_idx=1) is the 1st real CP → ordinal 1, not 2."""
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '16.1', 1), 1)

    def test_at_second_real_cp_returns_two(self):
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '16.1', 2), 2)

    def test_at_last_real_cp_returns_three(self):
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '16.1', 3), 3)

    def test_at_rel_tfinal_returns_three(self):
        """REL_TFINAL is a boundary; ordinal counts non-boundary CPs strictly
        before it (here all 3 real CPs are before it, so 3)."""
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '16.1', 4), 3)

    def test_pct_rendering_matches_expectation(self):
        """End-to-end: with total_cps=3 and the canonical layout, the first
        real CP renders as 33.3% — matching what users expect from "1 of 3"."""
        total_cps = 3
        ord1 = db.get_real_cp_ordinal(self.conn, '16.1', 1)
        pct1 = round(ord1 / total_cps * 100, 1)
        self.assertEqual(pct1, 33.3)

        ord3 = db.get_real_cp_ordinal(self.conn, '16.1', 3)
        pct3 = round(ord3 / total_cps * 100, 1)
        self.assertEqual(pct3, 100.0)

        # The pre-fix formula (cp_idx + 1) / total_cps would have given
        # (1 + 1) / 3 = 66.7% for the first real CP — wrong by a whole CP.
        wrong_pct = round((1 + 1) / total_cps * 100, 1)
        self.assertEqual(wrong_pct, 66.7)
        self.assertNotEqual(pct1, wrong_pct)

    def test_unknown_wf_returns_zero(self):
        """Defensive: an unknown WF returns 0 rather than raising."""
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '99', 0), 0)

    def test_no_boundaries_works_unchanged(self):
        """A WF with no boundary rows should behave like cp_idx + 1."""
        self.conn.execute("DELETE FROM current_cp_definitions WHERE wf_num = '16.1'")
        db.save_current_cp_definitions(self.conn, 0, {
            '20': [
                {'cp_idx': 0, 'cp_name': 'CP_A', 'test_idx': 0,
                 'check_items': [], 'is_boundary': 0},
                {'cp_idx': 1, 'cp_name': 'CP_B', 'test_idx': 0,
                 'check_items': [], 'is_boundary': 0},
                {'cp_idx': 2, 'cp_name': 'CP_C', 'test_idx': 0,
                 'check_items': [], 'is_boundary': 0},
            ],
        })
        self.conn.commit()
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '20', 0), 1)
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '20', 1), 2)
        self.assertEqual(db.get_real_cp_ordinal(self.conn, '20', 2), 3)


if __name__ == '__main__':
    unittest.main()
