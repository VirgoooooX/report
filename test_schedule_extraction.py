import os
import sqlite3
import tempfile
import unittest

import db
import engine


DATA_PATH = os.path.join('data', 'M60 EVT Rel Daily Report_20260509.xlsx')


def build_schedule_segments():
    _, _, ts_test_names, _ = engine.read_test_summary(DATA_PATH)
    cp_structures = engine.extract_all_cp_structures(DATA_PATH)
    mapped_cps = engine.attach_test_idx_to_cps(cp_structures, ts_test_names)
    return engine.extract_test_schedule_segments(DATA_PATH, ts_test_names, mapped_cps)


def find_segment(segments, wf_num, config, test_idx):
    for segment in segments:
        if (
            segment['wf_num'] == wf_num
            and segment['config'] == config
            and segment['test_idx'] == test_idx
        ):
            return segment
    raise AssertionError(f'missing segment wf={wf_num} cfg={config} test={test_idx}')


class ScheduleExtractionTests(unittest.TestCase):
    def test_wf4_splits_altitude_and_rock_tumble(self):
        segments = build_schedule_segments()

        altitude = find_segment(segments, '4', 'R1FNF', 0)
        tumble = find_segment(segments, '4', 'R1FNF', 1)

        self.assertEqual(altitude['planned_start_date'], '2026-04-17')
        self.assertEqual(altitude['planned_end_date'], '2026-04-27')
        self.assertEqual(altitude['test_name'], 'Altitude')

        self.assertEqual(tumble['planned_start_date'], '2026-04-29')
        self.assertEqual(tumble['planned_end_date'], '2026-05-09')
        self.assertEqual(tumble['test_name'], 'Rock Tumble')

    def test_wf6_splits_margin_segment_after_full_scale(self):
        segments = build_schedule_segments()

        hs = find_segment(segments, '6', 'R1FNF', 0)
        main = find_segment(segments, '6', 'R1FNF', 1)
        margin = find_segment(segments, '6', 'R1FNF', 2)

        self.assertEqual(hs['planned_start_date'], '2026-04-17')
        self.assertEqual(hs['planned_end_date'], '2026-04-25')

        self.assertEqual(main['planned_start_date'], '2026-04-27')
        self.assertEqual(main['planned_end_date'], '2026-05-20')

        self.assertEqual(margin['planned_start_date'], '2026-05-23')
        self.assertEqual(margin['planned_end_date'], '2026-05-30')

    def test_wf14_2_uses_repeated_drop_sequence_to_split_main_and_margin(self):
        segments = build_schedule_segments()

        hs = find_segment(segments, '14.2', 'R1FNF', 0)
        main = find_segment(segments, '14.2', 'R1FNF', 1)
        margin = find_segment(segments, '14.2', 'R1FNF', 2)

        self.assertEqual(hs['planned_start_date'], '2026-04-17')
        self.assertEqual(hs['planned_end_date'], '2026-04-24')

        self.assertEqual(main['planned_start_date'], '2026-04-25')
        self.assertEqual(main['planned_end_date'], '2026-05-01')

        self.assertEqual(margin['planned_start_date'], '2026-05-02')
        self.assertEqual(margin['planned_end_date'], '2026-05-09')

    def test_wf39_splits_hsd_then_battery_swap_then_hsd(self):
        segments = build_schedule_segments()

        first_hsd = find_segment(segments, '39', 'R1FNF', 0)
        battery_swap = find_segment(segments, '39', 'R1FNF', 1)
        second_hsd = find_segment(segments, '39', 'R1FNF', 2)

        self.assertEqual(first_hsd['planned_start_date'], '2026-04-17')
        self.assertEqual(first_hsd['planned_end_date'], '2026-05-08')

        self.assertEqual(battery_swap['planned_start_date'], '2026-05-09')
        self.assertEqual(battery_swap['planned_end_date'], '2026-05-09')

        self.assertEqual(second_hsd['planned_start_date'], '2026-05-12')
        self.assertEqual(second_hsd['planned_end_date'], '2026-05-15')

    def test_wf16_1_splits_thc_from_repetitive_hsd(self):
        segments = build_schedule_segments()

        thc = find_segment(segments, '16.1', 'R1FNF', 0)
        hsd = find_segment(segments, '16.1', 'R1FNF', 1)

        self.assertEqual(thc['planned_start_date'], '2026-04-17')
        self.assertEqual(thc['planned_end_date'], '2026-04-24')
        self.assertEqual(thc['confidence'], 'high')

        self.assertEqual(hsd['planned_start_date'], '2026-04-25')
        self.assertEqual(hsd['planned_end_date'], '2026-05-12')
        self.assertEqual(hsd['confidence'], 'high')

    def test_wf17_splits_thc_from_random_vibration_axes(self):
        segments = build_schedule_segments()

        thc = find_segment(segments, '17', 'R1FNF', 0)
        vibration = find_segment(segments, '17', 'R1FNF', 1)

        self.assertEqual(thc['planned_start_date'], '2026-04-17')
        self.assertEqual(thc['planned_end_date'], '2026-04-24')
        self.assertEqual(thc['confidence'], 'high')

        self.assertEqual(vibration['planned_start_date'], '2026-04-27')
        self.assertEqual(vibration['planned_end_date'], '2026-05-02')
        self.assertEqual(vibration['confidence'], 'high')

    def test_wf18_splits_thc_from_squeeze_pressure_loads(self):
        segments = build_schedule_segments()

        thc = find_segment(segments, '18', 'R1FNF', 0)
        squeeze = find_segment(segments, '18', 'R1FNF', 1)

        self.assertEqual(thc['planned_start_date'], '2026-04-17')
        self.assertEqual(thc['planned_end_date'], '2026-04-24')
        self.assertEqual(thc['confidence'], 'high')

        self.assertEqual(squeeze['planned_start_date'], '2026-04-27')
        self.assertEqual(squeeze['planned_end_date'], '2026-05-13')
        self.assertEqual(squeeze['confidence'], 'high')


class SchedulePersistenceTests(unittest.TestCase):
    def test_save_and_load_report_schedule_segments(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.row_factory = db._dict_factory
        try:
            db.init_db(conn=conn)
            report_id = db.create_report_version(conn, '2026-05-09', 'report.xlsx')
            db.save_report_schedule_segments(conn, report_id, [
                {
                    'wf_num': '4',
                    'config': 'R1FNF',
                    'test_idx': 0,
                    'test_name': 'Altitude',
                    'schedule_test_item': 'Altitude + Rock tumble',
                    'planned_start_date': '2026-04-17',
                    'planned_end_date': '2026-04-27',
                    'source_row': 26,
                    'confidence': 'high',
                    'inference_reason': 'marker-sequence',
                    'marker_labels': ['T0', 'Op1', 'Op2', 'Op3', 'Op5'],
                }
            ])

            rows = db.get_report_schedule_segments(conn, report_id)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['test_name'], 'Altitude')
            self.assertEqual(rows[0]['planned_end_date'], '2026-04-27')
            self.assertEqual(rows[0]['marker_labels'], ['T0', 'Op1', 'Op2', 'Op3', 'Op5'])
        finally:
            conn.close()
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
