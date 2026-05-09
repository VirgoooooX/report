from db import get_conn, get_latest_active_report_id


def main():
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    if not rid:
        conn.close()
        print('No active report')
        return

    # Source-of-truth parity check: current CP marker must be unique per SN record.
    dup_current = conn.execute(
        """SELECT wf_num, config, sn, COUNT(*) AS c
           FROM sn_cp_results
           WHERE report_id = ? AND is_current_cp = 1
           GROUP BY wf_num, config, sn
           HAVING COUNT(*) != 1""",
        (rid,),
    ).fetchall()

    # Fact aggregates used by APIs must exist for latest active report.
    rows = conn.execute(
        """SELECT wf_num, config, test_idx,
                  COUNT(DISTINCT CASE WHEN status IN ('pass', 'spec_fail', 'strife_fail') THEN sn END) AS total
           FROM sn_cp_results
           WHERE report_id = ?
           GROUP BY wf_num, config, test_idx""",
        (rid,),
    ).fetchall()
    conn.close()

    if dup_current:
        print(f'FACT PARITY FAILED: {len(dup_current)} SN records do not have exactly one current CP row')
        raise SystemExit(1)
    if not rows:
        print('FACT PARITY FAILED: no aggregate rows found for active report')
        raise SystemExit(1)

    print(f'Fact parity OK for active report {rid}; aggregate rows={len(rows)}')


if __name__ == '__main__':
    main()
