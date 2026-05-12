import unittest

from engine import is_cp_header_label


class EngineCpHeaderTests(unittest.TestCase):
    def test_t0_headers_are_not_cp_labels(self):
        for label in ['T0', 't0', 'T 0', ' T0 ']:
            with self.subTest(label=label):
                self.assertFalse(is_cp_header_label(label))

    def test_real_cleaning_cp_headers_are_kept(self):
        for label in ['1st A 18hrs', 'Cycle1', 'Chemical Sensitivity_after HS 24hrs']:
            with self.subTest(label=label):
                self.assertTrue(is_cp_header_label(label))


if __name__ == '__main__':
    unittest.main()
