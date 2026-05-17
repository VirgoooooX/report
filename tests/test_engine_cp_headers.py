import unittest

from engine import is_cp_header_label
from schedule_parser import (
    DAILY_RESULT_BOUNDARY_LABELS,
    SCHEDULE_BOUNDARY_LABELS,
)


class EngineCpHeaderTests(unittest.TestCase):
    def test_t0_headers_are_not_cp_labels(self):
        for label in ['T0', 't0', 'T 0', ' T0 ']:
            with self.subTest(label=label):
                self.assertFalse(is_cp_header_label(label))

    def test_real_cleaning_cp_headers_are_kept(self):
        for label in ['1st A 18hrs', 'Cycle1', 'Chemical Sensitivity_after HS 24hrs']:
            with self.subTest(label=label):
                self.assertTrue(is_cp_header_label(label))


class DailyResultBoundaryWhitelistTests(unittest.TestCase):
    """Batch B step 3.3 — only REL_T0 is allowed through when
    ``allow_result_boundaries=True``; other schedule boundaries stay
    rejected so daily ingest doesn't accidentally pull in REL_TFINAL/End/
    TFinal/T0 columns.

    See docs/plans/2026-05-17-rel-t0-daily-report-second-cut.md.
    """

    def test_whitelist_is_just_relt0(self):
        """Lock the whitelist literal so adding members forces a code change
        (and a corresponding decision recorded in the steering doc)."""
        self.assertEqual(DAILY_RESULT_BOUNDARY_LABELS, frozenset({'relt0'}))

    def test_whitelist_is_subset_of_schedule_boundaries(self):
        self.assertTrue(
            DAILY_RESULT_BOUNDARY_LABELS.issubset(SCHEDULE_BOUNDARY_LABELS)
        )


class IsCpHeaderLabelAllowResultBoundariesTests(unittest.TestCase):
    """Cover the two-flag matrix for is_cp_header_label."""

    def test_rel_t0_dropped_by_default(self):
        for label in ['REL_T0', 'rel_t0', 'REL T0', 'rel-t0']:
            with self.subTest(label=label):
                self.assertFalse(is_cp_header_label(label))

    def test_rel_t0_kept_when_allow_result_boundaries(self):
        for label in ['REL_T0', 'rel_t0', 'REL T0', 'rel-t0']:
            with self.subTest(label=label):
                self.assertTrue(
                    is_cp_header_label(label, allow_result_boundaries=True),
                )

    def test_t0_still_dropped_even_when_allow_result_boundaries(self):
        """T0 (without REL_ prefix) is NOT in DAILY_RESULT_BOUNDARY_LABELS."""
        for label in ['T0', 't0', 'T 0']:
            with self.subTest(label=label):
                self.assertFalse(
                    is_cp_header_label(label, allow_result_boundaries=True),
                )

    def test_rel_tfinal_still_dropped_even_when_allow_result_boundaries(self):
        for label in ['REL_TFINAL', 'rel_tfinal', 'REL TFINAL', 'rel-tfinal']:
            with self.subTest(label=label):
                self.assertFalse(
                    is_cp_header_label(label, allow_result_boundaries=True),
                )

    def test_end_and_tfinal_still_dropped_even_when_allow_result_boundaries(self):
        for label in ['End', 'end', 'TFinal', 'tfinal']:
            with self.subTest(label=label):
                self.assertFalse(
                    is_cp_header_label(label, allow_result_boundaries=True),
                )

    def test_real_cp_labels_kept_under_either_flag(self):
        """Sanity: regular CP names pass under both flag values."""
        for label in ['CP_A', 'TC_100CYCLES', 'RBI_15CM', '1st A 18hrs']:
            with self.subTest(label=label):
                self.assertTrue(is_cp_header_label(label))
                self.assertTrue(
                    is_cp_header_label(label, allow_result_boundaries=True),
                )


if __name__ == '__main__':
    unittest.main()
