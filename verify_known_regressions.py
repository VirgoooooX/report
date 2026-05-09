from db import get_conn


def main():
    conn = get_conn()
    report = conn.execute(
        "SELECT id FROM reports WHERE is_active = 1 ORDER BY report_date DESC LIMIT 1"
    ).fetchone()
    if not report:
        raise SystemExit('No active report')
    rid = report['id']

    cp = conn.execute(
        """SELECT c.cp_name
           FROM sn_cp_results f
           JOIN report_cps c
             ON c.report_id = f.report_id
            AND c.wf_num = f.wf_num
            AND c.cp_idx = f.cp_idx
           WHERE f.report_id = ?
             AND f.wf_num = '16.1'
             AND f.config = 'R3'
             AND f.is_current_cp = 1
           GROUP BY c.cp_name
           ORDER BY COUNT(*) DESC
           LIMIT 1""",
        (rid,),
    ).fetchone()
    assert cp and cp['cp_name'] == 'Bottom Surface After 450Cyc', cp

    expected = {
        '14.1': '18 Sided Drop 1m PB SeqA- Margin',
        '14.2': '18 Sided Drop 1m PB SeqB- Margin',
        '14.3': '18 Sided Drop 1m PB SeqC- Margin',
        '15.1': '18 Sided Drop 1m Granite SeqA- Margin',
        '15.2': '18 Sided Drop 1m Granite SeqB- Margin',
        '15.3': '18 Sided Drop 1m Granite SeqC- Margin',
    }
    for wf, name in expected.items():
        row = conn.execute(
            """SELECT test_name FROM report_test_names
               WHERE report_id = ? AND wf_num = ? AND test_idx = 2""",
            (rid, wf),
        ).fetchone()
        assert row and row['test_name'] == name, (wf, row)

    conn.close()
    print('Known regressions OK')


if __name__ == '__main__':
    main()
