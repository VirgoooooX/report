import datetime
import os
import tempfile
import unittest

import db
import processor


class PredictionProgressTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.old_db_path = db.DB_PATH
        self.old_populate_test_names = processor._populate_test_names
        db.DB_PATH = self.path
        processor._populate_test_names = lambda: None
        db.init_db()

    def tearDown(self):
        processor._populate_test_names = self.old_populate_test_names
        db.DB_PATH = self.old_db_path
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass

    def _seed_report(self, report_date):
        conn = db.get_conn()
        try:
            report_id = db.create_report_version(conn, report_date, f'{report_date}.xlsx')
            conn.commit()
            return report_id
        finally:
            conn.close()

    def _insert_test_name(self, report_id, test_idx, test_name):
        conn = db.get_conn()
        try:
            conn.execute(
                """INSERT INTO report_test_names (report_id, wf_num, test_idx, test_name)
                   VALUES (?, '14.2', ?, ?)""",
                (report_id, test_idx, test_name),
            )
            conn.commit()
        finally:
            conn.close()

    def _insert_progress(self, report_id, sn, test_idx, current_cp_idx):
        conn = db.get_conn()
        try:
            conn.execute(
                """INSERT INTO sn_progress
                   (report_id, wf_num, config, sn, unit_num, current_cp_idx,
                    current_cp_name, total_cps, test_idx, cp_results_json)
                   VALUES (?, '14.2', 'R3', ?, '', ?, '', 37, ?, '[]')""",
                (report_id, sn, current_cp_idx, test_idx),
            )
            conn.commit()
        finally:
            conn.close()

    def test_auto_predictions_skip_sunday_when_projecting_completion_date(self):
        older_id = self._seed_report('2026-05-08')  # Friday
        latest_id = self._seed_report('2026-05-09')  # Saturday

        for idx in range(1, 5):
            self._insert_progress(older_id, f'SN{idx}', 2, 30)
            self._insert_progress(latest_id, f'SN{idx}', 2, 33)

        generated = processor.compute_auto_predictions(days=14)
        row = next(p for p in generated if p['wf_num'] == '14.2' and p['config'] == 'R3')

        self.assertEqual(row['daily_rate'], 3.0)
        self.assertEqual(row['remaining_days'], 1.0)
        self.assertEqual(row['predicted_date'], '2026-05-11')

    def test_auto_predictions_ignore_slow_sn_test_outlier_for_same_wf_config(self):
        older_id = self._seed_report('2026-05-11')
        latest_id = self._seed_report('2026-05-12')

        for idx in range(1, 4):
            self._insert_progress(older_id, f'SN{idx}', 2, 20)
            self._insert_progress(latest_id, f'SN{idx}', 2, 23)

        self._insert_progress(older_id, 'SLOW_SN', 1, 14)
        self._insert_progress(latest_id, 'SLOW_SN', 1, 15)

        conn = db.get_conn()
        try:
            conn.execute(
                """INSERT INTO predictions
                   (wf_num, config, test_idx, predicted_date, remaining_days, daily_rate,
                    total_cps, current_max_cp, is_manual)
                   VALUES ('14.2', 'R3', 1, '2026-05-30', 20, 1, 37, 15, 0)"""
            )
            conn.commit()
        finally:
            conn.close()

        generated = processor.compute_auto_predictions(days=14)
        rows = db.get_predictions('14.2', 'R3')

        self.assertEqual([p['test_idx'] for p in generated], [2])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['test_idx'], 2)
        self.assertEqual(rows[0]['current_max_cp'], 23)

    def test_auto_predictions_use_75_percent_bulk_cp_not_max_cp(self):
        older_id = self._seed_report('2026-05-08')
        latest_id = self._seed_report('2026-05-09')

        for sn, old_cp, new_cp in [
            ('SN1', 20, 23),
            ('SN2', 20, 23),
            ('SN3', 20, 23),
            ('FAST_SN', 30, 36),
        ]:
            self._insert_progress(older_id, sn, 2, old_cp)
            self._insert_progress(latest_id, sn, 2, new_cp)

        generated = processor.compute_auto_predictions(days=14)
        row = next(p for p in generated if p['wf_num'] == '14.2' and p['config'] == 'R3')

        self.assertEqual(row['test_idx'], 2)
        self.assertEqual(row['current_max_cp'], 23)
        self.assertEqual(row['daily_rate'], 3.0)
        self.assertEqual(row['remaining_days'], 4.3)


class PredictionHelperTests(unittest.TestCase):
    def test_bulk_cp_uses_highest_cp_reached_by_75_percent_of_sns(self):
        self.assertEqual(processor._bulk_cp([15, 23, 23, 23]), 23)
        self.assertEqual(processor._bulk_cp([10, 12, 14, 14]), 12)
        self.assertEqual(processor._bulk_cp([16, 18, 27, 33, 37, 65, 69, 70]), 27)

    def test_prediction_model_for_test_classifies_known_test_types(self):
        self.assertEqual(processor._prediction_model_for_test('Button Cycling - CW')['name'], 'short_cycle')
        self.assertEqual(processor._prediction_model_for_test('Random Drop 1m PB x25')['name'], 'random_or_drop')
        self.assertEqual(processor._prediction_model_for_test('Non Op Storage')['name'], 'long_storage')
        self.assertEqual(processor._prediction_model_for_test('Some New Test')['name'], 'standard')

    def test_workdays_between_excludes_sunday(self):
        start = datetime.date(2026, 5, 9)  # Saturday
        end = datetime.date(2026, 5, 11)    # Monday
        self.assertEqual(processor._workdays_between(start, end), 1)

    def test_add_workdays_skips_sunday(self):
        start = datetime.date(2026, 5, 9)  # Saturday
        self.assertEqual(processor._add_workdays(start, 1), datetime.date(2026, 5, 11))
        self.assertEqual(processor._add_workdays(start, 2), datetime.date(2026, 5, 12))

    def test_weighted_rate_prioritizes_recent_short_cycle_progress(self):
        daily = [
            {'report_date': '2026-05-05', 'bulk_cp': 10},
            {'report_date': '2026-05-06', 'bulk_cp': 11},
            {'report_date': '2026-05-07', 'bulk_cp': 13},
            {'report_date': '2026-05-08', 'bulk_cp': 16},
            {'report_date': '2026-05-09', 'bulk_cp': 20},
        ]
        model = processor.PREDICTION_MODELS['short_cycle']
        self.assertEqual(round(processor._daily_rate_for_model(daily, model), 2), 3.0)

    def test_long_storage_rate_uses_median_nonzero_progress(self):
        daily = [
            {'report_date': '2026-05-01', 'bulk_cp': 1},
            {'report_date': '2026-05-02', 'bulk_cp': 1},
            {'report_date': '2026-05-04', 'bulk_cp': 2},
            {'report_date': '2026-05-05', 'bulk_cp': 2},
            {'report_date': '2026-05-06', 'bulk_cp': 3},
        ]
        model = processor.PREDICTION_MODELS['long_storage']
        self.assertEqual(processor._daily_rate_for_model(daily, model), 1.0)

    def test_random_or_drop_rate_is_conservative(self):
        daily = [
            {'report_date': '2026-05-05', 'bulk_cp': 10},
            {'report_date': '2026-05-06', 'bulk_cp': 16},
            {'report_date': '2026-05-07', 'bulk_cp': 16},
            {'report_date': '2026-05-08', 'bulk_cp': 20},
        ]
        model = processor.PREDICTION_MODELS['random_or_drop']
        self.assertLess(processor._daily_rate_for_model(daily, model), 3.4)


if __name__ == '__main__':
    unittest.main()
