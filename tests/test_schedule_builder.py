import unittest

from schedule_builder import build_actual_progress, build_schedule_segments, distribute_test_cp_labels


class ScheduleBuilderTests(unittest.TestCase):
    def test_cp_dates_exclude_sunday_and_use_display_index(self):
        cps = [
            {'cp_idx': 0, 'cp_name': 'CP0'},
            {'cp_idx': 1, 'cp_name': 'CP1'},
            {'cp_idx': 2, 'cp_name': 'CP2'},
            {'cp_idx': 3, 'cp_name': 'CP3'},
            {'cp_idx': 4, 'cp_name': 'CP4'},
        ]

        scheduled = distribute_test_cp_labels(cps, '2026-05-01', '2026-05-05')

        self.assertEqual([cp['display_cp_idx'] for cp in scheduled], [1, 2, 3, 4, 5])
        self.assertNotIn('2026-05-03', [cp['planned_date'] for cp in scheduled])
        # Default behaviour (exclude_end_date=False): the last CP lands on
        # end_date itself. This applies to non-last tests in a multi-test
        # lane, where end_date IS the test's real last working day.
        self.assertEqual(scheduled[-1]['planned_date'], '2026-05-05')

    def test_cp_dates_exclude_end_date_for_last_test(self):
        """Last test in a lane: end_date is REL_TFINAL, exclude it from placement."""
        cps = [
            {'cp_idx': 0, 'cp_name': 'CP0'},
            {'cp_idx': 1, 'cp_name': 'CP1'},
            {'cp_idx': 2, 'cp_name': 'CP2'},
            {'cp_idx': 3, 'cp_name': 'CP3'},
            {'cp_idx': 4, 'cp_name': 'CP4'},
        ]

        scheduled = distribute_test_cp_labels(
            cps, '2026-05-01', '2026-05-05', exclude_end_date=True,
        )

        # 2026-05-05 (Tuesday) is REL_TFINAL — the last CP must land on
        # 2026-05-04 (Monday), the working day strictly before end_date.
        self.assertNotIn('2026-05-05', [cp['planned_date'] for cp in scheduled])
        self.assertEqual(scheduled[-1]['planned_date'], '2026-05-04')

    def test_cp_dates_exclude_start_date_for_first_test(self):
        """First test in a lane: start_date is REL_T0, exclude it from placement."""
        cps = [
            {'cp_idx': 0, 'cp_name': 'CP0'},
            {'cp_idx': 1, 'cp_name': 'CP1'},
            {'cp_idx': 2, 'cp_name': 'CP2'},
            {'cp_idx': 3, 'cp_name': 'CP3'},
            {'cp_idx': 4, 'cp_name': 'CP4'},
        ]

        scheduled = distribute_test_cp_labels(
            cps, '2026-05-01', '2026-05-05', exclude_start_date=True,
        )

        # 2026-05-01 (Friday) is REL_T0 — the first CP must land on a
        # working day strictly after start_date.
        self.assertNotIn('2026-05-01', [cp['planned_date'] for cp in scheduled])
        self.assertEqual(scheduled[-1]['planned_date'], '2026-05-05')

    def test_cp_dates_exclude_both_for_single_test_lane(self):
        """Single-test lane: exclude both T0 and End boundary markers."""
        cps = [
            {'cp_idx': 0, 'cp_name': 'CP0'},
            {'cp_idx': 1, 'cp_name': 'CP1'},
            {'cp_idx': 2, 'cp_name': 'CP2'},
        ]

        scheduled = distribute_test_cp_labels(
            cps, '2026-05-01', '2026-05-05',
            exclude_start_date=True, exclude_end_date=True,
        )

        dates = [cp['planned_date'] for cp in scheduled]
        # Both boundary days excluded — CPs land in (start, end).
        self.assertNotIn('2026-05-01', dates)
        self.assertNotIn('2026-05-05', dates)

    def test_actual_progress_uses_planned_cp_date_until_complete(self):
        cps = [
            {'cp_idx': 0, 'cp_name': 'CP0', 'planned_date': '2026-06-01'},
            {'cp_idx': 1, 'cp_name': 'CP1', 'planned_date': '2026-06-02'},
            {'cp_idx': 2, 'cp_name': 'CP2', 'planned_date': '2026-06-03'},
        ]

        actual = build_actual_progress(
            cps,
            {'current_cp_idx': 1, 'current_cp_name': 'CP1', 'total_cps': 3, 'sn_count': 2},
            '2026-06-05',
        )

        self.assertEqual(actual['end_date'], '2026-06-02')
        self.assertFalse(actual['is_complete'])
        self.assertEqual(actual['sn_count'], 2)

    def test_actual_progress_complete_uses_planned_end_date(self):
        cps = [
            {'cp_idx': 0, 'cp_name': 'CP0', 'planned_date': '2026-06-01'},
            {'cp_idx': 1, 'cp_name': 'CP1', 'planned_date': '2026-06-02'},
        ]

        actual = build_actual_progress(
            cps,
            {'current_cp_idx': 1, 'current_cp_name': 'CP1', 'total_cps': 2},
            '2026-06-05',
        )

        self.assertEqual(actual['end_date'], '2026-06-05')
        self.assertTrue(actual['is_complete'])

    def test_build_segments_returns_authoritative_cp_dates_and_flags(self):
        segments = [
            {
                'wf_num': '14.2',
                'config': 'R1FNF',
                'test_idx': 0,
                'test_name': 'HS',
                'schedule_test_item': 'Drop',
                'planned_start_date': '2026-04-17',
                'planned_end_date': '2026-04-24',
            },
            {
                'wf_num': '14.2',
                'config': 'R1FNF',
                'test_idx': 1,
                'test_name': 'Main Drop',
                'schedule_test_item': 'Drop',
                'planned_start_date': '2026-04-25',
                'planned_end_date': '2026-05-01',
            },
        ]
        cps_by_key = {
            ('14.2', 0): [{'cp_idx': 0, 'cp_name': 'REL_T0'}, {'cp_idx': 1, 'cp_name': 'HS_72HRS'}],
            ('14.2', 1): [{'cp_idx': 2, 'cp_name': 'DROP_3'}, {'cp_idx': 3, 'cp_name': 'DROP_18'}],
        }

        payload = build_schedule_segments(
            segments,
            wf_meta={'14.2': 'Drop WF'},
            cps_by_key=cps_by_key,
            progress_by_key={('14.2', 'R1FNF'): {'current_cp_idx': 2, 'current_cp_name': 'DROP_3', 'total_cps': 4}},
        )

        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]['wf_name'], 'Drop WF')
        self.assertEqual(payload[0]['cps'][0]['display_cp_idx'], 1)
        self.assertIn('planned_date', payload[1]['cps'][0])
        self.assertTrue(payload[1]['cps'][0]['is_current'])
        self.assertEqual(payload[1]['actual_progress']['end_date'], payload[1]['cps'][0]['planned_date'])


if __name__ == '__main__':
    unittest.main()
