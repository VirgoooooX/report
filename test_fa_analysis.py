import fa_analysis


def test_failure_type_header_spacing():
    assert fa_analysis._failure_type({'Failure Type  (Spec. or Strife)': 'Spec.'}) == 'spec'
    assert fa_analysis._failure_type({'Failure Type  (Spec. or Strife)': 'Strife'}) == 'strife'


def test_wf_label_includes_prefix_and_name():
    assert fa_analysis._wf_label('10', {'10': {'name': 'KeyCap Wearing'}}) == 'WF10 KeyCap Wearing'
    assert fa_analysis._wf_label('WF25', {'25': {'name': 'Sweaty Finger'}}) == 'WF25 Sweaty Finger'


def _issue(sn, wf, config, failed_test, symptom='No power', failure_type='Spec.'):
    return {
        'SN': sn,
        'WF': wf,
        'Config': config,
        'Failed Test': failed_test,
        'Failure Symptom / Failure Message': symptom,
        'Failure Type  (Spec. or Strife)': failure_type,
    }


def test_symptom_denominator_uses_overall_sample_size():
    issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
    sample_sizes = {
        '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
        '11': {'R1FNF': 5, 'R2CNM': 0, 'R3': 0, 'R4': 0},
    }

    overview = fa_analysis.compute_overview(issues, sample_sizes)

    assert overview['topSymptom'][0]['display'] == '1F/25T'
    assert overview['topSymptom'][0]['totalSamples'] == 25


def test_wf_denominator_uses_whole_wf_sample_size():
    issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
    sample_sizes = {
        '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
        '11': {'R1FNF': 5, 'R2CNM': 0, 'R3': 0, 'R4': 0},
    }

    overview = fa_analysis.compute_overview(issues, sample_sizes)

    assert overview['topWf'][0]['display'] == '1F/20T'
    assert overview['topWf'][0]['totalSamples'] == 20


def test_failed_test_denominator_uses_all_wfs_that_contain_test():
    issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
    sample_sizes = {
        '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
        '11': {'R1FNF': 5, 'R2CNM': 5, 'R3': 0, 'R4': 0},
        '12': {'R1FNF': 100, 'R2CNM': 0, 'R3': 0, 'R4': 0},
    }
    wf_tests = {'10': ['Drop'], '11': ['Drop'], '12': ['Other']}

    overview = fa_analysis.compute_overview(issues, sample_sizes, wf_test_names=wf_tests)

    assert overview['topFailedTest'][0]['display'] == '1F/30T'
    assert overview['topFailedTest'][0]['totalSamples'] == 30


def test_cross_denominator_follows_second_dimension():
    issues = [_issue('S1', '10', 'R1FNF', 'Drop')]
    sample_sizes = {
        '10': {'R1FNF': 8, 'R2CNM': 12, 'R3': 0, 'R4': 0},
        '11': {'R1FNF': 5, 'R2CNM': 0, 'R3': 0, 'R4': 0},
    }

    cross = fa_analysis.compute_cross(issues, sample_sizes, 'symptom', 'config')

    assert cross['matrix'][0]['display'] == '1F/13T'
    assert cross['matrix'][0]['totalSamples'] == 13


if __name__ == '__main__':
    test_failure_type_header_spacing()
    test_wf_label_includes_prefix_and_name()
    test_symptom_denominator_uses_overall_sample_size()
    test_wf_denominator_uses_whole_wf_sample_size()
    test_failed_test_denominator_uses_all_wfs_that_contain_test()
    test_cross_denominator_follows_second_dimension()
    print('fa_analysis tests passed')
