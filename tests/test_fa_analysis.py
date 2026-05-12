import unittest
import fa_analysis


def _issue(sn, wf, config, failed_test, symptom='No power', failure_type='Spec.'):
    return {
        'SN': sn,
        'WF': wf,
        'Config': config,
        'Failed Test': failed_test,
        'Failure Symptom / Failure Message': symptom,
        'Failure Type  (Spec. or Strife)': failure_type,
    }


class FaAnalysisTests(unittest.TestCase):
    def test_failure_type_header_spacing(self):
        self.assertEqual(fa_analysis._failure_type({'Failure Type  (Spec. or Strife)': 'Spec.'}), 'spec')
        self.assertEqual(fa_analysis._failure_type({'Failure Type  (Spec. or Strife)': 'Strife'}), 'strife')

    def test_wf_label_includes_prefix_and_name(self):
        self.assertEqual(fa_analysis._wf_label('10', {'10': {'name': 'KeyCap Wearing'}}), 'WF10 KeyCap Wearing')
        self.assertEqual(fa_analysis._wf_label('WF25', {'25': {'name': 'Sweaty Finger'}}), 'WF25 Sweaty Finger')

    def test_symptom_denominator_uses_overall_sample_size(self):
        issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
        sample_sizes = {
            '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
            '11': {'R1FNF': 5, 'R2CNM': 0, 'R3': 0, 'R4': 0},
        }
        overview = fa_analysis.compute_overview(issues, sample_sizes)
        self.assertEqual(overview['topSymptom'][0]['display'], '1F/25T')
        self.assertEqual(overview['topSymptom'][0]['totalSamples'], 25)

    def test_wf_denominator_uses_whole_wf_sample_size(self):
        issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
        sample_sizes = {
            '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
            '11': {'R1FNF': 5, 'R2CNM': 0, 'R3': 0, 'R4': 0},
        }
        overview = fa_analysis.compute_overview(issues, sample_sizes)
        self.assertEqual(overview['topWf'][0]['display'], '1F/20T')
        self.assertEqual(overview['topWf'][0]['totalSamples'], 20)

    def test_failed_test_denominator_uses_all_wfs_that_contain_test(self):
        issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
        sample_sizes = {
            '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
            '11': {'R1FNF': 5, 'R2CNM': 5, 'R3': 0, 'R4': 0},
            '12': {'R1FNF': 100, 'R2CNM': 0, 'R3': 0, 'R4': 0},
        }
        wf_tests = {'10': ['Drop'], '11': ['Drop'], '12': ['Other']}
        overview = fa_analysis.compute_overview(issues, sample_sizes, wf_test_names=wf_tests)
        self.assertEqual(overview['topFailedTest'][0]['display'], '1F/30T')
        self.assertEqual(overview['topFailedTest'][0]['totalSamples'], 30)

    def test_cross_denominator_follows_second_dimension(self):
        issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
        sample_sizes = {
            '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
            '11': {'R1FNF': 5, 'R2CNM': 0, 'R3': 0, 'R4': 0},
        }
        cross = fa_analysis.compute_cross(issues, sample_sizes, 'symptom', 'config')
        self.assertEqual(cross['matrix'][0]['display'], '1F/13T')
        self.assertEqual(cross['matrix'][0]['totalSamples'], 13)


if __name__ == '__main__':
    unittest.main()
