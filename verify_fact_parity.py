from db import get_conn


def main():
    conn = get_conn()
    report = conn.execute(
        "SELECT id, report_date FROM reports WHERE is_active = 1 ORDER BY report_date DESC LIMIT 1"
    ).fetchone()
    if not report:
        print('No active report')
        return

    rid = report['id']
    mismatches = []
    rows = conn.execute(
        """SELECT wf_num, config, test_idx, total_units, spec_fail_count, strife_fail_count
           FROM wf_results
           WHERE report_id = ?""",
        (rid,),
    ).fetchall()

    for old in rows:
        new = conn.execute(
            """SELECT COUNT(DISTINCT CASE WHEN status IN ('pass', 'spec_fail', 'strife_fail') THEN sn END) AS total,
                      COUNT(DISTINCT CASE WHEN failure_type = 'spec' THEN sn END) AS spec,
                      COUNT(DISTINCT CASE WHEN failure_type = 'strife' THEN sn END) AS strife
               FROM sn_cp_results
               WHERE report_id = ? AND wf_num = ? AND config = ? AND test_idx = ?""",
            (rid, old['wf_num'], old['config'], old['test_idx']),
        ).fetchone()

        if (old['total_units'], old['spec_fail_count'], old['strife_fail_count']) != (new['total'], new['spec'], new['strife']):
            mismatches.append((old, new))

    conn.close()
    if mismatches:
        print(f'MISMATCHES: {len(mismatches)}')
        for old, new in mismatches[:20]:
            print(old, new)
        raise SystemExit(1)

    print(f'Fact parity OK for report {rid} ({report["report_date"]})')


if __name__ == '__main__':
    main()
