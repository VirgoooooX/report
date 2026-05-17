"""Audit second-cut SQLite index removals on a temporary database copy."""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import time
from pathlib import Path


CANDIDATE_DROP_INDEXES = (
    "idx_sn_lifecycle_current_progress",
    "idx_sn_lifecycle_current_failure",
    "idx_sn_check_hist_point",
)

REQUIRED_KEEP_INDEXES = (
    "idx_sn_lifecycle_open_point",
    "idx_sn_lifecycle_sn",
    "idx_sn_lifecycle_window",
    "idx_sn_check_hist_failures",
)

QUERY_BUDGETS_MS = {
    "save_open_rows_select": 300.0,
    "sn_timeline": 50.0,
    "query_by_wf_distinct_sns": 50.0,
    "query_by_wf_cp_summary": 50.0,
    "check_details_active_at_report": 50.0,
    "failure_rollup": 75.0,
    "active_failures": 75.0,
    "current_progress_direct": 75.0,
}


def size_mib(path: Path) -> float:
    return path.stat().st_size / 1024 / 1024


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def sample_values(conn: sqlite3.Connection) -> dict[str, object]:
    rid_row = conn.execute(
        """SELECT id FROM reports
           WHERE is_active = 1
           ORDER BY report_date DESC, version DESC
           LIMIT 1"""
    ).fetchone()
    if not rid_row:
        raise RuntimeError("No active report found")

    sample = conn.execute(
        """SELECT wf_num, config, sn, cp_idx
           FROM sn_check_state_history
           WHERE closed_before_report_id IS NULL
           LIMIT 1"""
    ).fetchone()
    if not sample:
        raise RuntimeError("No open lifecycle rows found")

    return {
        "rid": rid_row["id"],
        "wf": sample["wf_num"],
        "config": sample["config"],
        "sn": sample["sn"],
        "cp_idx": sample["cp_idx"],
    }


def query_suite(values: dict[str, object]) -> list[tuple[str, str, tuple]]:
    rid = values["rid"]
    wf = values["wf"]
    config = values["config"]
    sn = values["sn"]
    cp_idx = values["cp_idx"]
    return [
        (
            "save_open_rows_select",
            """SELECT id, wf_num, config, sn, cp_idx, check_item_idx, state_hash, first_report_id
               FROM sn_check_state_history
               WHERE closed_before_report_id IS NULL""",
            (),
        ),
        (
            "sn_timeline",
            """SELECT wf_num, config, unit_num, cp_idx, check_item_idx, check_item,
                      status, failure_type, raw_value, first_report_date
               FROM sn_check_state_history
               WHERE sn = ? AND first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
               ORDER BY CAST(wf_num AS REAL), cp_idx, check_item_idx""",
            (sn, rid, rid),
        ),
        (
            "query_by_wf_distinct_sns",
            """SELECT DISTINCT sn, config, COALESCE(unit_num, '') AS unit_num
               FROM sn_check_state_history
               WHERE wf_num = ? AND first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
               ORDER BY config, sn""",
            (wf, rid, rid),
        ),
        (
            "query_by_wf_cp_summary",
            """SELECT cp_idx,
                      COUNT(*) as item_count,
                      SUM(CASE WHEN status='pass' THEN 1 ELSE 0 END) as pass_count,
                      SUM(CASE WHEN failure_type IS NOT NULL THEN 1 ELSE 0 END) as fail_count,
                      SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending_count,
                      MIN(first_report_date) as date
               FROM sn_check_state_history
               WHERE sn=? AND wf_num=? AND config=?
                 AND first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
               GROUP BY cp_idx ORDER BY cp_idx""",
            (sn, wf, config, rid, rid),
        ),
        (
            "check_details_active_at_report",
            """SELECT check_item_idx, check_item, raw_value, normalized_value,
                      status, failure_type, fill_color, font_color
               FROM sn_check_state_history
               WHERE wf_num=? AND config=? AND sn=? AND cp_idx=?
                 AND first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
               ORDER BY check_item_idx""",
            (wf, config, sn, cp_idx, rid, rid),
        ),
        (
            "failure_rollup",
            """SELECT wf_num, config, test_idx,
                      COUNT(DISTINCT CASE WHEN failure_type='spec' THEN sn END) spec,
                      COUNT(DISTINCT CASE WHEN failure_type='strife' THEN sn END) strife,
                      COUNT(DISTINCT sn) total
               FROM sn_check_state_history
               WHERE first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
               GROUP BY wf_num, config, test_idx""",
            (rid, rid),
        ),
        (
            "active_failures",
            """SELECT wf_num, config, test_idx, failure_type, sn
               FROM sn_check_state_history
               WHERE first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
                 AND failure_type IS NOT NULL
               ORDER BY CAST(wf_num AS REAL), config, sn, cp_idx, check_item_idx""",
            (rid, rid),
        ),
        (
            "current_progress_direct",
            """SELECT wf_num, config, sn, MAX(cp_idx) as max_cp_idx
               FROM sn_check_state_history
               WHERE closed_before_report_id IS NULL
                 AND status NOT IN ('pending', '')
               GROUP BY wf_num, config, sn""",
            (),
        ),
    ]


def index_present(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def run_queries(conn: sqlite3.Connection) -> dict[str, dict[str, object]]:
    values = sample_values(conn)
    results: dict[str, dict[str, object]] = {}
    for name, sql, params in query_suite(values):
        plan = [
            " | ".join(str(value) for value in tuple(row))
            for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params)
        ]
        start = time.perf_counter()
        rows = conn.execute(sql, params).fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        results[name] = {
            "rows": len(rows),
            "elapsed_ms": elapsed_ms,
            "plan": plan,
        }
    return results


def print_results(label: str, results: dict[str, dict[str, object]]) -> None:
    print(f"## {label}")
    for name, data in results.items():
        elapsed = float(data["elapsed_ms"])
        print(f"{name}: rows={data['rows']} elapsed_ms={elapsed:.2f}")
        for line in data["plan"]:
            print(f"  plan: {line}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(Path("db") / "report.db"))
    parser.add_argument("--work-db", default=str(Path("db") / "index-audit-second-cut.db"))
    args = parser.parse_args()

    source = Path(args.db)
    work_db = Path(args.work_db)
    if not source.exists():
        print(f"Database not found: {source}")
        return 2

    if work_db.exists():
        work_db.unlink()
    shutil.copy2(source, work_db)

    baseline_conn = connect(source)
    try:
        baseline = run_queries(baseline_conn)
    finally:
        baseline_conn.close()

    candidate_conn = connect(work_db)
    try:
        for index_name in CANDIDATE_DROP_INDEXES:
            candidate_conn.execute(f"DROP INDEX IF EXISTS {index_name}")
        candidate_conn.commit()

        for index_name in CANDIDATE_DROP_INDEXES:
            if index_present(candidate_conn, index_name):
                print(f"Candidate index still present: {index_name}")
                return 1
        for index_name in REQUIRED_KEEP_INDEXES:
            if not index_present(candidate_conn, index_name):
                print(f"Required index missing: {index_name}")
                return 1

        candidate = run_queries(candidate_conn)
        candidate_conn.execute("VACUUM")
    finally:
        candidate_conn.close()

    print_results("baseline", baseline)
    print_results("candidate", candidate)
    print(f"source_size_mib={size_mib(source):.2f}")
    print(f"candidate_size_mib={size_mib(work_db):.2f}")
    print(f"estimated_savings_mib={size_mib(source) - size_mib(work_db):.2f}")

    failed = False
    for name, budget in QUERY_BUDGETS_MS.items():
        elapsed = float(candidate[name]["elapsed_ms"])
        delta = elapsed - float(baseline[name]["elapsed_ms"])
        if elapsed > budget:
            print(f"FAIL {name}: {elapsed:.2f}ms exceeds budget {budget:.2f}ms")
            failed = True
        if delta > 25.0 and elapsed > float(baseline[name]["elapsed_ms"]) * 2:
            print(f"FAIL {name}: delta {delta:.2f}ms is too large")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
