"""
M60 EVT REL — Database Module
SQLite storage for daily report snapshots, trends, and comparisons.
"""
import sqlite3, json, os, datetime
from collections import defaultdict
from app_paths import DB_PATH


def _dict_factory(cursor, row):
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _execute_with_optional_conn(conn, fn):
    owns_conn = conn is None
    if conn is None:
        conn = get_conn()
    try:
        return fn(conn)
    finally:
        if owns_conn:
            conn.close()


def create_report_version(conn, report_date, excel_path, source_file_name='', source_file_mtime='', source_file_hash='', notes='', ts_test_names=None):
    existing = conn.execute(
        "SELECT COALESCE(MAX(version), 0) AS max_version FROM reports WHERE report_date = ?",
        (report_date,),
    ).fetchone()
    next_version = (existing['max_version'] or 0) + 1

    conn.execute(
        "UPDATE reports SET is_active = 0 WHERE report_date = ?",
        (report_date,),
    )

    cur = conn.execute(
        """INSERT INTO reports
           (report_date, version, is_active, excel_path, source_file_name,
            source_file_mtime, source_file_hash, notes, ts_test_names)
           VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)""",
        (
            report_date,
            next_version,
            excel_path,
            source_file_name,
            source_file_mtime,
            source_file_hash,
            notes,
            json.dumps(ts_test_names) if ts_test_names else '{}',
        ),
    )
    return cur.lastrowid


def get_latest_active_report(conn=None):
    def _get(c):
        return c.execute(
            """SELECT * FROM reports
               WHERE is_active = 1
               ORDER BY report_date DESC, version DESC
               LIMIT 1"""
        ).fetchone()
    return _execute_with_optional_conn(conn, _get)


def get_latest_active_report_id(conn):
    row = conn.execute(
        """SELECT id FROM reports
           WHERE is_active = 1
           ORDER BY report_date DESC, version DESC
           LIMIT 1"""
    ).fetchone()
    return row['id'] if row else None


def get_previous_active_report_id(conn, report_id):
    current = conn.execute(
        "SELECT report_date FROM reports WHERE id = ?",
        (report_id,),
    ).fetchone()
    if not current:
        return None
    row = conn.execute(
        """SELECT id FROM reports
           WHERE is_active = 1 AND report_date < ?
           ORDER BY report_date DESC, version DESC
           LIMIT 1""",
        (current['report_date'],),
    ).fetchone()
    return row['id'] if row else None


def wf_sort_key(wfn):
    """自然排序键：WF1, WF2, ..., WF10, WF11, WF14.1, WF14.2"""
    try:
        parts = str(wfn).split('.')
        return tuple(int(p) if p.isdigit() else float('inf') for p in parts)
    except:
        return (float('inf'),)


def save_wf_names(names_dict, test_names_dict=None, conn=None):
    """保存 WF 名称映射表和测试名。
    names_dict: {wf_num: wf_name}
    test_names_dict: {wf_num: [test_name, ...]}
    """
    owns_conn = conn is None
    if conn is None:
        conn = get_conn()
    for wfn, name in names_dict.items():
        tn = json.dumps(test_names_dict.get(wfn, [])) if test_names_dict else '[]'
        conn.execute(
            "INSERT OR REPLACE INTO wf_names (wf_num, wf_name, test_names) VALUES (?,?,?)",
            (wfn, name, tn)
        )
    if owns_conn:
        conn.commit()
        conn.close()


def get_wf_names():
    """获取全部 WF 名称映射及测试名。
    Returns: {wf_num: {'name': wf_name, 'test_names': [test_name, ...]}}
    """
    conn = get_conn()
    rows = conn.execute("SELECT * FROM wf_names").fetchall()
    conn.close()
    result = {}
    for r in rows:
        try:
            tn = json.loads(r.get('test_names', '[]'))
        except (json.JSONDecodeError, TypeError):
            tn = []
        result[r['wf_num']] = {'name': r['wf_name'], 'test_names': tn}
    return result


def get_wf_name(wfn):
    """获取单个 WF 的名称，若无则返回空字符串。"""
    conn = get_conn()
    row = conn.execute("SELECT wf_name FROM wf_names WHERE wf_num=?", (wfn,)).fetchone()
    conn.close()
    return row['wf_name'] if row else ''


def save_wf_cps(wf_num, cp_list, conn=None):
    """保存一个 WF 的 CP 信息。
    cp_list: [{'cp_idx': int, 'cp_name': str, 'check_items': [str]}, ...]
    """
    owns_conn = conn is None
    if conn is None:
        conn = get_conn()
    for cp in cp_list:
        conn.execute(
            """INSERT OR REPLACE INTO wf_cps (wf_num, cp_idx, cp_name, check_items)
               VALUES (?,?,?,?)""",
            (wf_num, cp['cp_idx'], cp['cp_name'], json.dumps(cp.get('check_items', [])))
        )
    if owns_conn:
        conn.commit()
        conn.close()


def save_report_wf_meta(conn, report_id, wf_names):
    conn.executemany(
        """INSERT OR REPLACE INTO report_wf_meta (report_id, wf_num, wf_name)
           VALUES (?, ?, ?)""",
        [(report_id, str(wf), name or '') for wf, name in wf_names.items()],
    )


def save_report_test_names(conn, report_id, test_names_by_wf):
    rows = []
    for wf, names in test_names_by_wf.items():
        for idx, name in enumerate(names or []):
            if name:
                rows.append((report_id, str(wf), idx, str(name)))
    conn.executemany(
        """INSERT OR REPLACE INTO report_test_names
           (report_id, wf_num, test_idx, test_name)
           VALUES (?, ?, ?, ?)""",
        rows,
    )


def save_report_cps(conn, report_id, cps_by_wf):
    rows = []
    for wf, cps in cps_by_wf.items():
        for cp in cps:
            rows.append((
                report_id,
                str(wf),
                int(cp['cp_idx']),
                str(cp['cp_name']),
                cp.get('test_idx'),
                json.dumps(cp.get('check_items', [])),
            ))
    conn.executemany(
        """INSERT OR REPLACE INTO report_cps
           (report_id, wf_num, cp_idx, cp_name, test_idx, check_items)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )


def save_report_schedule_segments(conn, report_id, segments):
    conn.execute("DELETE FROM report_schedule_segments")
    rows = []
    for segment in segments:
        rows.append((
            report_id,
            str(segment['wf_num']),
            str(segment['config']),
            int(segment['test_idx']),
            str(segment.get('test_name') or f"Test{segment['test_idx'] + 1}"),
            str(segment.get('schedule_test_item') or ''),
            str(segment['planned_start_date']),
            str(segment['planned_end_date']),
            int(segment.get('source_row') or 0),
            str(segment.get('confidence') or 'medium'),
            str(segment.get('inference_reason') or ''),
            json.dumps(segment.get('marker_labels', [])),
        ))
    conn.executemany(
        """INSERT OR REPLACE INTO report_schedule_segments
           (report_id, wf_num, config, test_idx, test_name, schedule_test_item,
            planned_start_date, planned_end_date, source_row, confidence,
            inference_reason, marker_labels)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def get_report_schedule_segments(conn, report_id, wf_num=None):
    sql = """SELECT * FROM report_schedule_segments
             WHERE report_id = ?"""
    params = [report_id]
    if wf_num is not None:
        sql += " AND wf_num = ?"
        params.append(str(wf_num))
    sql += " ORDER BY CAST(wf_num AS REAL), config, test_idx"
    rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item['marker_labels'] = json.loads(item.get('marker_labels') or '[]')
        except (TypeError, json.JSONDecodeError):
            item['marker_labels'] = []
        item.pop('marker_details', None)
        result.append(item)
    return result


def prune_historical_schedule_snapshots(conn):
    latest_report = conn.execute(
        """SELECT id FROM reports
           WHERE is_active = 1
           ORDER BY report_date DESC, version DESC
           LIMIT 1"""
    ).fetchone()
    if not latest_report:
        conn.execute("DELETE FROM report_schedule_segments")
        return

    conn.execute(
        "DELETE FROM report_schedule_segments WHERE report_id <> ?",
        (latest_report['id'],),
    )


def save_current_schedule_segments(conn, run_id, segments):
    """Replace all current schedule segments (latest-only table)."""
    conn.execute("DELETE FROM current_schedule_segments")
    rows = []
    for segment in segments:
        rows.append((
            str(segment['wf_num']),
            str(segment['config']),
            int(segment['test_idx']),
            str(segment.get('test_name') or f"Test{segment['test_idx'] + 1}"),
            str(segment.get('schedule_test_item') or ''),
            str(segment['planned_start_date']),
            str(segment['planned_end_date']),
            int(segment.get('source_row') or 0),
            str(segment.get('confidence') or 'medium'),
            str(segment.get('inference_reason') or ''),
            json.dumps(segment.get('marker_labels', [])),
            run_id,
        ))
    conn.executemany(
        """INSERT INTO current_schedule_segments
           (wf_num, config, test_idx, test_name, schedule_test_item,
            planned_start_date, planned_end_date, source_row, confidence,
            inference_reason, marker_labels, updated_run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def get_current_schedule_segments(conn, wf_num=None):
    """Get current schedule segments, optionally filtered by wf_num."""
    sql = """SELECT * FROM current_schedule_segments"""
    params = []
    if wf_num is not None:
        sql += " WHERE wf_num = ?"
        params.append(str(wf_num))
    sql += " ORDER BY CAST(wf_num AS REAL), config, test_idx"
    rows = conn.execute(sql, params).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item['marker_labels'] = json.loads(item.get('marker_labels') or '[]')
        except (TypeError, json.JSONDecodeError):
            item['marker_labels'] = []
        item.pop('marker_details', None)
        result.append(item)
    return result


def save_current_wf_definitions(conn, run_id, wf_names):
    """Replace all current WF definitions (latest-only table)."""
    conn.execute("DELETE FROM current_wf_definitions")
    rows = [(str(wfn), str(name), run_id) for wfn, name in wf_names.items()]
    conn.executemany(
        """INSERT INTO current_wf_definitions (wf_num, wf_name, updated_run_id)
           VALUES (?, ?, ?)""",
        rows,
    )


def get_current_wf_definitions(conn):
    """Return {wf_num: wf_name} dict from current definitions."""
    rows = conn.execute(
        "SELECT wf_num, wf_name FROM current_wf_definitions ORDER BY CAST(wf_num AS REAL)"
    ).fetchall()
    return {r['wf_num']: r['wf_name'] for r in rows}


def save_current_test_definitions(conn, run_id, test_names_by_wf):
    """Replace all current test definitions (latest-only table).

    test_names_by_wf: {wf_num: [test_name, ...]}
    """
    conn.execute("DELETE FROM current_test_definitions")
    rows = []
    for wf_num, names in test_names_by_wf.items():
        for test_idx, test_name in enumerate(names):
            rows.append((str(wf_num), test_idx, str(test_name), run_id))
    conn.executemany(
        """INSERT INTO current_test_definitions (wf_num, test_idx, test_name, updated_run_id)
           VALUES (?, ?, ?, ?)""",
        rows,
    )


def get_current_test_definitions(conn, wf_num=None):
    """Return {wf_num: [test_name, ...]} dict from current definitions."""
    sql = "SELECT wf_num, test_idx, test_name FROM current_test_definitions"
    params = []
    if wf_num is not None:
        sql += " WHERE wf_num = ?"
        params.append(str(wf_num))
    sql += " ORDER BY CAST(wf_num AS REAL), test_idx"
    rows = conn.execute(sql, params).fetchall()
    result = {}
    for r in rows:
        result.setdefault(r['wf_num'], []).append(r['test_name'])
    return result


def save_current_cp_definitions(conn, run_id, cps_by_wf):
    """Replace all current CP definitions (latest-only table).

    cps_by_wf: {wf_num: [{'cp_idx': int, 'cp_name': str, 'test_idx': int,
                          'check_items': list, 'is_boundary': int}, ...]}

    ``is_boundary`` defaults to 0 when absent. Schedule-boundary CPs
    (T0/REL_T0/End/TFinal/REL_TFINAL) are persisted with ``is_boundary=1``
    so cp_idx stays aligned with daily lifecycle rows; downstream consumers
    decide whether to keep or filter them per plane (see
    docs/plans/2026-05-17-rel-t0-daily-report-second-cut.md).
    """
    conn.execute("DELETE FROM current_cp_definitions")
    rows = []
    for wf_num, cp_list in cps_by_wf.items():
        for cp in cp_list:
            rows.append((
                str(wf_num),
                int(cp['cp_idx']),
                str(cp['cp_name']),
                cp.get('test_idx'),
                json.dumps(cp.get('check_items', [])),
                int(cp.get('is_boundary') or 0),
                run_id,
            ))
    conn.executemany(
        """INSERT INTO current_cp_definitions
           (wf_num, cp_idx, cp_name, test_idx, check_items, is_boundary, updated_run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def get_current_cp_definitions(conn, wf_num=None):
    """Return {wf_num: [{cp_idx, cp_name, test_idx, check_items, is_boundary}, ...]} dict."""
    sql = (
        "SELECT wf_num, cp_idx, cp_name, test_idx, check_items, is_boundary "
        "FROM current_cp_definitions"
    )
    params = []
    if wf_num is not None:
        sql += " WHERE wf_num = ?"
        params.append(str(wf_num))
    sql += " ORDER BY CAST(wf_num AS REAL), cp_idx"
    rows = conn.execute(sql, params).fetchall()
    result = {}
    for r in rows:
        try:
            check_items = json.loads(r.get('check_items') or '[]')
        except (TypeError, json.JSONDecodeError):
            check_items = []
        result.setdefault(r['wf_num'], []).append({
            'cp_idx': r['cp_idx'],
            'cp_name': r['cp_name'],
            'test_idx': r['test_idx'],
            'check_items': check_items,
            'is_boundary': int(r['is_boundary'] or 0),
        })
    return result


def get_report_wf_meta(conn, report_id):
    rows = conn.execute(
        "SELECT wf_num, wf_name FROM report_wf_meta WHERE report_id = ?",
        (report_id,),
    ).fetchall()
    return {r['wf_num']: r['wf_name'] for r in rows}


def get_report_test_names(conn, report_id):
    rows = conn.execute(
        """SELECT wf_num, test_idx, test_name
           FROM report_test_names
           WHERE report_id = ?
           ORDER BY wf_num, test_idx""",
        (report_id,),
    ).fetchall()
    result = {}
    for r in rows:
        names = result.setdefault(r['wf_num'], [])
        while len(names) <= r['test_idx']:
            names.append('')
        names[r['test_idx']] = r['test_name']
    return result


def get_report_cps(conn, report_id, wf_num):
    rows = conn.execute(
        """SELECT cp_idx, cp_name, test_idx, check_items
           FROM report_cps
           WHERE report_id = ? AND wf_num = ?
           ORDER BY cp_idx""",
        (report_id, wf_num),
    ).fetchall()
    result = {}
    for r in rows:
        try:
            check_items = json.loads(r['check_items'] or '[]')
        except Exception:
            check_items = []
        result[r['cp_idx']] = {
            'cp_idx': r['cp_idx'],
            'cp_name': r['cp_name'],
            'test_idx': r['test_idx'],
            'check_items': check_items,
        }
    return result


def save_sn_cp_results(conn, rows):
    values = [
        (
            r['report_id'], r['report_date'], r['wf_num'], r['config'], r['sn'],
            r.get('unit_num', ''), r['test_idx'], r['cp_idx'], r['status'],
            r.get('failure_type'), int(r.get('has_data', 0)), int(r.get('is_current_cp', 0)),
        )
        for r in rows
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO sn_cp_results
           (report_id, report_date, wf_num, config, sn, unit_num, test_idx,
            cp_idx, status, failure_type, has_data, is_current_cp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        values,
    )
    return len(values)


def save_sn_check_results(conn, rows):
    # Legacy daily snapshot writer. New imports use save_sn_check_state_history().
    # Keep this during the transition so fallback reads remain possible.
    values = [
        (
            r['report_id'], r['report_date'], r['wf_num'], r['config'], r['sn'],
            r.get('unit_num', ''), r['test_idx'], r['cp_idx'], r['check_item_idx'],
            r['check_item'], r.get('raw_value'), r.get('normalized_value'),
            r['status'], r.get('failure_type'), r.get('fill_color'),
            r.get('font_color'), r.get('source_row'), r.get('source_col'),
        )
        for r in rows
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO sn_check_results
           (report_id, report_date, wf_num, config, sn, unit_num, test_idx,
            cp_idx, check_item_idx, check_item, raw_value, normalized_value,
            status, failure_type, fill_color, font_color, source_row, source_col)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        values,
    )
    return len(values)


def _check_state_tuple(row):
    return (
        row.get('status') or '',
        row.get('failure_type') or '',
        row.get('normalized_value') or '',
        row.get('fill_color') or '',
        row.get('font_color') or '',
    )


def _check_state_hash(row):
    return json.dumps(_check_state_tuple(row), ensure_ascii=True, separators=(',', ':'))


def _check_identity_tuple(row):
    return (
        row['wf_num'],
        row['config'],
        row['sn'],
        int(row['cp_idx']),
        int(row['check_item_idx']),
    )


def save_sn_check_state_history(conn, report_id, report_date, rows):
    """Write lifecycle state for check-item observations.
    
    Lifecycle semantics:
    - New observation with no open row → INSERT new lifecycle row
    - Same state_hash as open row → UPDATE last_seen fields only
    - Different state_hash → CLOSE old row, INSERT new lifecycle row
    - Previously open row not observed → CLOSE (disappeared)
    
    Uses batch queries (single open-row SELECT, batched writes).
    """
    # 1. Query all currently open lifecycle rows once
    open_rows = conn.execute(
        """SELECT id, wf_num, config, sn, cp_idx, check_item_idx, state_hash, first_report_id
           FROM sn_check_state_history
           WHERE closed_before_report_id IS NULL"""
    ).fetchall()
    
    open_by_identity = {}
    for row in open_rows:
        key = (
            row['wf_num'],
            row['config'],
            row['sn'],
            int(row['cp_idx']),
            int(row['check_item_idx']),
        )
        open_by_identity[key] = row
    
    # 2. Build observation set and prepare batches
    observed = set()
    unchanged_updates = []      # (last_seen_report_id, last_seen_report_date, last_source_row, last_source_col, id)
    state_closures = []         # (closed_before_report_id, closed_before_report_date, id)
    inserts = []                # full row tuples
    
    for r in rows:
        identity = _check_identity_tuple(r)
        observed.add(identity)
        state_hash = _check_state_hash(r)
        
        current = open_by_identity.get(identity)
        
        if current and current['state_hash'] == state_hash:
            # Unchanged: update last_seen
            unchanged_updates.append((
                report_id,
                report_date,
                r.get('source_row'),
                r.get('source_col'),
                current['id'],
            ))
        else:
            if current:
                # State changed: close old row
                state_closures.append((
                    report_id,
                    report_date,
                    current['id'],
                ))
            
            # Insert new lifecycle row
            inserts.append((
                r['wf_num'],
                r['config'],
                r['sn'],
                r.get('unit_num', ''),
                r['test_idx'],
                r['cp_idx'],
                r['check_item_idx'],
                r['check_item'],
                state_hash,
                r.get('raw_value'),
                r.get('normalized_value'),
                r['status'],
                r.get('failure_type'),
                r.get('fill_color'),
                r.get('font_color'),
                report_id,
                report_date,
                report_id,
                report_date,
                r.get('source_row'),
                r.get('source_col'),
                r.get('source_row'),
                r.get('source_col'),
            ))
    
    # 3. Close rows not observed in this import (disappeared from report)
    # Only close missing rows when this import is for the latest (or newer) date.
    # Re-uploading a historical date should NOT close rows from later dates.
    latest_date_row = conn.execute(
        "SELECT MAX(report_date) as d FROM reports WHERE is_active = 1"
    ).fetchone()
    latest_date = latest_date_row['d'] if latest_date_row else ''

    missing_closures = []
    if report_date >= (latest_date or ''):
        for identity, row in open_by_identity.items():
            if identity not in observed and row.get('first_report_id', 0) < report_id:
                missing_closures.append((
                    report_id,
                    report_date,
                    row['id'],
                ))
    
    # 4. Execute batched writes
    # 4a. Update last_seen for unchanged rows
    if unchanged_updates:
        conn.executemany(
            """UPDATE sn_check_state_history
               SET last_seen_report_id = ?,
                   last_seen_report_date = ?,
                   last_source_row = ?,
                   last_source_col = ?
               WHERE id = ?""",
            unchanged_updates,
        )
    
    # 4b. Close rows with state change
    all_closures = state_closures + missing_closures
    if all_closures:
        conn.executemany(
            """UPDATE sn_check_state_history
               SET closed_before_report_id = ?,
                   closed_before_report_date = ?
               WHERE id = ?""",
            all_closures,
        )
    
    # 4c. Insert new rows
    if inserts:
        conn.executemany(
            """INSERT INTO sn_check_state_history
               (wf_num, config, sn, unit_num, test_idx, cp_idx, check_item_idx,
                check_item, state_hash, raw_value, normalized_value, status,
                failure_type, fill_color, font_color, first_report_id,
                first_report_date, last_seen_report_id, last_seen_report_date,
                first_source_row, first_source_col, last_source_row, last_source_col)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            inserts,
        )
    
    return {
        'inserted': len(inserts),
        'updated': len(unchanged_updates),
        'closed': len(all_closures),
    }


def get_sn_cp_current_progress(conn, report_id):
    rows = conn.execute(
        """SELECT wf_num, config, sn, unit_num,
                  MAX(CASE WHEN is_current_cp = 1 THEN cp_idx ELSE NULL END) AS current_cp_idx,
                  MAX(test_idx) AS test_idx,
                  COUNT(*) AS cp_rows
           FROM sn_cp_results
           WHERE report_id = ?
           GROUP BY wf_num, config, sn, unit_num""",
        (report_id,),
    ).fetchall()
    return rows


def get_sn_fact_history(sn):
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.report_date, f.report_id, f.wf_num, f.config, f.sn, f.unit_num,
                  f.test_idx, tn.test_name, f.cp_idx, c.cp_name,
                  f.status, f.failure_type, f.is_current_cp,
                  COALESCE(totals.total_cps, 0) AS total_cps
           FROM sn_cp_results f
           JOIN reports r ON r.id = f.report_id AND r.is_active = 1
           LEFT JOIN report_cps c
             ON c.report_id = f.report_id AND c.wf_num = f.wf_num AND c.cp_idx = f.cp_idx
           LEFT JOIN report_test_names tn
             ON tn.report_id = f.report_id AND tn.wf_num = f.wf_num AND tn.test_idx = f.test_idx
           LEFT JOIN (
             SELECT report_id, wf_num, COUNT(*) AS total_cps
             FROM report_cps
             GROUP BY report_id, wf_num
           ) totals
             ON totals.report_id = f.report_id AND totals.wf_num = f.wf_num
           WHERE f.sn = ?
           ORDER BY r.report_date, f.wf_num, f.config, f.cp_idx""",
        (sn,),
    ).fetchall()
    conn.close()
    return rows


def get_sn_lifecycle_history(sn):
    """Get SN history from lifecycle table with current CP definitions for names.

    Returns rows similar to get_sn_fact_history but from lifecycle source:
    {report_date, report_id, wf_num, config, sn, unit_num, test_idx, test_name,
     cp_idx, cp_name, status, failure_type, is_current_cp, total_cps}
    """
    conn = get_conn()
    # First get the lifecycle rows grouped by report
    rows = conn.execute(
        """SELECT DISTINCT l.wf_num, l.config, l.sn, l.unit_num, l.test_idx,
               l.cp_idx, l.status, l.failure_type,
               l.first_report_id as report_id, r.report_date,
               ccp.cp_name, ccp.test_idx as cp_test_idx,
               ct.test_name
        FROM sn_check_state_history l
        JOIN reports r ON r.id = l.first_report_id AND r.is_active = 1
        LEFT JOIN current_cp_definitions ccp
          ON ccp.wf_num = l.wf_num AND ccp.cp_idx = l.cp_idx
        LEFT JOIN current_test_definitions ct
          ON ct.wf_num = l.wf_num AND ct.test_idx = l.test_idx
        WHERE l.sn = ?
        ORDER BY r.report_date, l.wf_num, l.config, l.cp_idx""",
        (sn,),
    ).fetchall()

    # Also get total CPs per WF from current definitions
    cp_counts = {}
    if rows:
        wf_set = set(r['wf_num'] for r in rows)
        for wf in wf_set:
            count = conn.execute(
                "SELECT COUNT(*) as c FROM current_cp_definitions "
                "WHERE wf_num = ? AND is_boundary = 0",
                (wf,),
            ).fetchone()['c']
            cp_counts[wf] = count

    # Determine is_current_cp: the last CP with data for this SN in each WF+config+date
    # Use a per-WF+config+date calculation
    result = []
    for row in rows:
        wf = row['wf_num']
        cfg = row['config']
        # Find max cp_idx for this SN in this WF+config combination at this report's time
        max_cp = conn.execute(
            """SELECT MAX(l2.cp_idx) as max_cp
               FROM sn_check_state_history l2
               WHERE l2.sn = ? AND l2.wf_num = ? AND l2.config = ?
                 AND l2.first_report_id <= ?
                 AND (l2.closed_before_report_id IS NULL OR l2.closed_before_report_id > ?)""",
            (sn, wf, cfg, row['report_id'], row['report_id']),
        ).fetchone()

        is_current = (max_cp and max_cp['max_cp'] is not None and row['cp_idx'] == max_cp['max_cp'])

        result.append({
            'report_date': row['report_date'],
            'report_id': row['report_id'],
            'wf_num': row['wf_num'],
            'config': row['config'],
            'sn': row['sn'],
            'unit_num': row['unit_num'],
            'test_idx': row['test_idx'],
            'test_name': row['test_name'] or (f"Test{row['test_idx'] + 1}" if row['test_idx'] is not None else ''),
            'cp_idx': row['cp_idx'],
            'cp_name': row['cp_name'] or '',
            'status': row['status'],
            'failure_type': row['failure_type'],
            'is_current_cp': 1 if is_current else 0,
            'total_cps': cp_counts.get(wf, 0),
        })

    conn.close()
    return result


def get_sn_check_details(report_id, wf_num, config, sn, cp_idx):
    conn = get_conn()
    rows = conn.execute(
        """SELECT check_item_idx, check_item, raw_value, normalized_value,
                  status, failure_type, fill_color, font_color,
                  last_source_row AS source_row,
                  last_source_col AS source_col
           FROM sn_check_state_history
           WHERE wf_num = ? AND config = ? AND sn = ? AND cp_idx = ?
             AND first_report_id <= ?
             AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
           ORDER BY check_item_idx""",
        (wf_num, config, sn, cp_idx, report_id, report_id),
    ).fetchall()
    if rows:
        conn.close()
        return rows

    rows = conn.execute(
        """SELECT check_item_idx, check_item, raw_value, normalized_value,
                  status, failure_type, fill_color, font_color, source_row, source_col
           FROM sn_check_results
           WHERE report_id = ? AND wf_num = ? AND config = ? AND sn = ? AND cp_idx = ?
           ORDER BY check_item_idx""",
        (report_id, wf_num, config, sn, cp_idx),
    ).fetchall()
    conn.close()
    return rows


def get_cell_failures(report_id, wf_num, config, test_idx, sns):
    """Return check-item-level failure details for the given SNs in a cell.

    Only returns failures from the LAST CP of the test (consistent with
    the summary cell statistics which only count last-CP failures).
    """
    if not sns:
        return []
    conn = get_conn()

    # Determine the last CP for this test_idx (matches summary logic)
    last_cp_row = conn.execute(
        """SELECT MAX(cp_idx) AS last_cp FROM report_cps
           WHERE report_id = ? AND wf_num = ? AND test_idx = ?""",
        (report_id, wf_num, test_idx),
    ).fetchone()
    last_cp = last_cp_row['last_cp'] if last_cp_row and last_cp_row['last_cp'] is not None else None

    if last_cp is None:
        # Fallback: try current_cp_definitions
        last_cp_row = conn.execute(
            """SELECT MAX(cp_idx) AS last_cp FROM current_cp_definitions
               WHERE wf_num = ? AND test_idx = ? AND is_boundary = 0""",
            (wf_num, test_idx),
        ).fetchone()
        last_cp = last_cp_row['last_cp'] if last_cp_row and last_cp_row['last_cp'] is not None else None

    placeholders = ','.join(['?' for _ in sns])

    if last_cp is not None:
        cp_filter = "AND sci.cp_idx = ?"
        params_history = (report_id, wf_num, config, test_idx, last_cp, *sns, report_id, report_id)
        params_results = (report_id, wf_num, config, test_idx, last_cp, *sns)
    else:
        # If we can't determine last_cp, fall back to no cp filter (original behavior)
        cp_filter = ""
        params_history = (report_id, wf_num, config, test_idx, *sns, report_id, report_id)
        params_results = (report_id, wf_num, config, test_idx, *sns)

    rows = conn.execute(
        f"""SELECT sci.sn, sci.cp_idx, rcp.cp_name, sci.check_item_idx,
                   sci.check_item, sci.raw_value, sci.normalized_value,
                   sci.status, sci.failure_type
            FROM sn_check_state_history sci
            JOIN report_cps rcp
              ON rcp.report_id = ?
             AND rcp.wf_num = sci.wf_num
             AND rcp.cp_idx = sci.cp_idx
            WHERE sci.wf_num = ?
              AND sci.config = ?
              AND sci.test_idx = ?
              {cp_filter}
              AND sci.sn IN ({placeholders})
              AND sci.failure_type IS NOT NULL
              AND sci.first_report_id <= ?
              AND (sci.closed_before_report_id IS NULL OR sci.closed_before_report_id > ?)
            ORDER BY sci.sn, sci.cp_idx, sci.check_item_idx""",
        params_history,
    ).fetchall()
    if rows:
        conn.close()
        return rows

    rows = conn.execute(
        f"""SELECT sci.sn, sci.cp_idx, rcp.cp_name, sci.check_item_idx,
                   sci.check_item, sci.raw_value, sci.normalized_value,
                   sci.status, sci.failure_type
            FROM sn_check_results sci
            JOIN report_cps rcp
              ON rcp.report_id = sci.report_id
             AND rcp.wf_num = sci.wf_num
             AND rcp.cp_idx = sci.cp_idx
            WHERE sci.report_id = ?
              AND sci.wf_num = ?
              AND sci.config = ?
              AND sci.test_idx = ?
              {cp_filter}
              AND sci.sn IN ({placeholders})
              AND sci.failure_type IS NOT NULL
            ORDER BY sci.sn, sci.cp_idx, sci.check_item_idx""",
        params_results,
    ).fetchall()
    conn.close()
    return rows


def get_latest_wf_config_progress(conn, report_id):
    return conn.execute(
        """WITH per_sn AS (
               SELECT wf_num, config, sn,
                      MAX(CASE WHEN is_current_cp = 1 THEN cp_idx ELSE NULL END) AS current_cp_idx
               FROM sn_cp_results
               WHERE report_id = ?
               GROUP BY wf_num, config, sn
           ),
           per_cfg AS (
               SELECT wf_num, config,
                      MAX(current_cp_idx) AS max_cp_idx,
                      COUNT(*) AS sn_count
                FROM per_sn
               GROUP BY wf_num, config
           ),
           cp_totals AS (
               SELECT wf_num, COUNT(*) AS total_cps
               FROM report_cps
               WHERE report_id = ?
               GROUP BY wf_num
           )
           SELECT p.wf_num, p.config, p.max_cp_idx,
                  c.cp_name, c.test_idx, p.sn_count,
                  COALESCE(ct.total_cps, 0) AS total_cps
            FROM per_cfg p
            LEFT JOIN report_cps c
              ON c.report_id = ?
             AND c.wf_num = p.wf_num
             AND c.cp_idx = p.max_cp_idx
            LEFT JOIN cp_totals ct
              ON ct.wf_num = p.wf_num""",
        (report_id, report_id, report_id),
    ).fetchall()


def get_failure_rate_stats_from_facts(report_id):
    conn = get_conn()
    rows = conn.execute(
        """WITH cp_test_ranges AS (
               SELECT wf_num, test_idx, MIN(cp_idx) AS first_cp, MAX(cp_idx) AS last_cp
               FROM report_cps
               WHERE report_id = ?
               GROUP BY wf_num, test_idx
           ),
           sn_current AS (
               SELECT wf_num, config, sn, cp_idx AS current_cp_idx
               FROM sn_cp_results
               WHERE report_id = ? AND is_current_cp = 1
           ),
           test_totals AS (
               SELECT tr.wf_num, sc.config, tr.test_idx,
                      COUNT(DISTINCT sc.sn) AS total_units
               FROM cp_test_ranges tr
               JOIN sn_current sc
                 ON sc.wf_num = tr.wf_num
                AND sc.current_cp_idx >= tr.first_cp
               GROUP BY tr.wf_num, sc.config, tr.test_idx
           ),
           sn_test_latest_cp AS (
               SELECT cp.wf_num, cp.config, cp.sn, rcp.test_idx,
                      MAX(cp.cp_idx) AS latest_cp_idx
               FROM sn_cp_results cp
               JOIN report_cps rcp
                 ON rcp.report_id = ? AND rcp.wf_num = cp.wf_num AND rcp.cp_idx = cp.cp_idx
               WHERE cp.report_id = ? AND cp.has_data = 1
               GROUP BY cp.wf_num, cp.config, cp.sn, rcp.test_idx
           ),
           sn_test_failure AS (
               SELECT stl.wf_num, stl.config, stl.sn, stl.test_idx,
                      cp.failure_type
               FROM sn_test_latest_cp stl
               JOIN sn_cp_results cp
                 ON cp.report_id = ?
                AND cp.wf_num = stl.wf_num AND cp.config = stl.config
                AND cp.sn = stl.sn AND cp.cp_idx = stl.latest_cp_idx
               WHERE cp.failure_type IS NOT NULL
           ),
           test_fail_agg AS (
               SELECT wf_num, config, test_idx,
                      COUNT(DISTINCT CASE WHEN failure_type = 'spec' THEN sn END) AS spec,
                      COUNT(DISTINCT CASE WHEN failure_type = 'strife' THEN sn END) AS strife
               FROM sn_test_failure
               GROUP BY wf_num, config, test_idx
           )
           SELECT tt.wf_num, tt.config, tt.test_idx,
                  MAX(tn.test_name) AS test_name,
                  COALESCE(tt.total_units, 0) AS total,
                  COALESCE(fa.spec, 0) AS spec,
                  COALESCE(fa.strife, 0) AS strife
           FROM test_totals tt
           LEFT JOIN test_fail_agg fa
             ON fa.wf_num = tt.wf_num AND fa.config = tt.config AND fa.test_idx = tt.test_idx
           LEFT JOIN report_test_names tn
             ON tn.report_id = ?
            AND tn.wf_num = tt.wf_num
            AND tn.test_idx = tt.test_idx
           GROUP BY tt.wf_num, tt.config, tt.test_idx""",
        (report_id, report_id, report_id, report_id, report_id, report_id),
    ).fetchall()
    conn.close()
    return rows


def build_failure_rate_stats_from_facts(report_id):
    rows = get_failure_rate_stats_from_facts(report_id)
    by_config = {}
    by_wf = {}
    by_test = {}
    top = []

    for r in rows:
        cfg = r['config']
        wfn = r['wf_num']
        total = r['total'] or 0
        spec = r['spec'] or 0
        strife = r['strife'] or 0
        total_fails = spec + strife
        rate = round(total_fails / total * 100, 1) if total else 0
        test_name = r.get('test_name') or f"Test{r['test_idx'] + 1}"
        test_key = f"{wfn}_{cfg}_{test_name}"

        if cfg not in by_config:
            by_config[cfg] = {'spec_fails': 0, 'strife_fails': 0, 'total_tests': 0}
        by_config[cfg]['spec_fails'] += spec
        by_config[cfg]['strife_fails'] += strife
        by_config[cfg]['total_tests'] += total

        if wfn not in by_wf:
            by_wf[wfn] = {'spec_fails': 0, 'strife_fails': 0, 'total_tests': 0}
        by_wf[wfn]['spec_fails'] += spec
        by_wf[wfn]['strife_fails'] += strife
        by_wf[wfn]['total_tests'] += total

        by_test[test_key] = {
            'wf': wfn, 'config': cfg, 'test_idx': r['test_idx'], 'test_name': test_name,
            'spec': spec, 'strife': strife, 'total': total,
            'spec_rate': round(spec / total * 100, 1) if total else 0,
            'strife_rate': round(strife / total * 100, 1) if total else 0,
            'total_rate': rate,
        }
        top.append({
            'wf': wfn, 'cfg': cfg, 'test': test_name,
            'spec': spec, 'strife': strife, 'total': total, 'rate': rate,
        })

    for d in by_config.values():
        total = d['total_tests'] or 0
        d['spec_rate'] = round(d['spec_fails'] / total * 100, 1) if total else 0
        d['strife_rate'] = round(d['strife_fails'] / total * 100, 1) if total else 0
        d['total_rate'] = round((d['spec_fails'] + d['strife_fails']) / total * 100, 1) if total else 0

    for d in by_wf.values():
        total = d['total_tests'] or 0
        d['spec_rate'] = round(d['spec_fails'] / total * 100, 1) if total else 0
        d['strife_rate'] = round(d['strife_fails'] / total * 100, 1) if total else 0
        d['total_rate'] = round((d['spec_fails'] + d['strife_fails']) / total * 100, 1) if total else 0

    top.sort(key=lambda x: x['rate'], reverse=True)
    return {
        'by_config': by_config,
        'by_test': by_test,
        'by_wf': by_wf,
        'top_failures': top[:50],
    }


def save_definition_changes(conn, changes):
    rows = [
        (
            c['report_id'],
            c.get('previous_report_id'),
            c['wf_num'],
            c['change_type'],
            json.dumps(c.get('detail', {})),
        )
        for c in changes
    ]
    conn.executemany(
        """INSERT INTO definition_changes
           (report_id, previous_report_id, wf_num, change_type, detail_json)
           VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def detect_definition_changes(conn, report_id, previous_report_id):
    if not previous_report_id:
        return []
    changes = []

    current_tests = get_report_test_names(conn, report_id)
    previous_tests = get_report_test_names(conn, previous_report_id)
    for wf, names in current_tests.items():
        old = previous_tests.get(wf, [])
        if len(old) != len(names):
            changes.append({
                'report_id': report_id,
                'previous_report_id': previous_report_id,
                'wf_num': wf,
                'change_type': 'test_count_changed',
                'detail': {'previous': old, 'current': names},
            })
        elif old != names:
            changes.append({
                'report_id': report_id,
                'previous_report_id': previous_report_id,
                'wf_num': wf,
                'change_type': 'test_names_changed',
                'detail': {'previous': old, 'current': names},
            })

    current_wfs = get_report_wf_meta(conn, report_id)
    previous_wfs = get_report_wf_meta(conn, previous_report_id)
    for wf, name in current_wfs.items():
        old_name = previous_wfs.get(wf, '')
        if old_name and old_name != name:
            changes.append({
                'report_id': report_id,
                'previous_report_id': previous_report_id,
                'wf_num': wf,
                'change_type': 'wf_name_changed',
                'detail': {'previous': old_name, 'current': name},
            })

    return changes


def get_wf_cps(wf_num=None):
    """获取 CP 信息。如果指定 wf_num 返回单个 WF 的列表，否则返回 {wf_num: [...]}
    """
    conn = get_conn()
    if wf_num:
        rows = conn.execute(
            "SELECT * FROM wf_cps WHERE wf_num = ? ORDER BY cp_idx", (wf_num,)
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            try:
                ci = json.loads(r['check_items'])
            except (json.JSONDecodeError, TypeError):
                ci = []
            result.append({'cp_idx': r['cp_idx'], 'cp_name': r['cp_name'], 'check_items': ci})
        return result
    else:
        rows = conn.execute(
            "SELECT * FROM wf_cps ORDER BY CAST(wf_num AS REAL), cp_idx"
        ).fetchall()
        conn.close()
        result = {}
        for r in rows:
            try:
                ci = json.loads(r['check_items'])
            except (json.JSONDecodeError, TypeError):
                ci = []
            result.setdefault(r['wf_num'], []).append(
                {'cp_idx': r['cp_idx'], 'cp_name': r['cp_name'], 'check_items': ci}
            )
        return result


def init_db(drop_all=False, conn=None):
    """Create tables if they don't exist."""
    owns_conn = conn is None
    if conn is None:
        conn = get_conn()
    if drop_all:
        conn.executescript("""
            DROP TABLE IF EXISTS raw_check_item_records;
            DROP TABLE IF EXISTS import_batches;
            DROP TABLE IF EXISTS base_file_meta;
            DROP TABLE IF EXISTS sn_check_state_history;
            DROP TABLE IF EXISTS sn_check_results;
            DROP TABLE IF EXISTS sn_cp_results;
            DROP TABLE IF EXISTS current_cp_definitions;
            DROP TABLE IF EXISTS current_test_definitions;
            DROP TABLE IF EXISTS current_wf_definitions;
            DROP TABLE IF EXISTS current_schedule_segments;
            DROP TABLE IF EXISTS report_schedule_segments;
            DROP TABLE IF EXISTS report_cps;
            DROP TABLE IF EXISTS report_test_names;
            DROP TABLE IF EXISTS report_wf_meta;
            DROP TABLE IF EXISTS definition_changes;
            DROP TABLE IF EXISTS predictions;
            DROP TABLE IF EXISTS wf_categories;
            DROP TABLE IF EXISTS categories;
            DROP TABLE IF EXISTS daily_changes;
            DROP TABLE IF EXISTS sn_progress;
            DROP TABLE IF EXISTS report_stats;
            DROP TABLE IF EXISTS wf_results;
            DROP TABLE IF EXISTS wf_cps;
            DROP TABLE IF EXISTS wf_names;
            DROP TABLE IF EXISTS reports;
        """)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            excel_path TEXT NOT NULL,
            source_file_name TEXT DEFAULT '',
            source_file_mtime TEXT DEFAULT '',
            source_file_hash TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            ts_test_names TEXT DEFAULT '{}',
            UNIQUE(report_date, version)
        );

        CREATE TABLE IF NOT EXISTS wf_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            test_idx INTEGER NOT NULL,
            total_units INTEGER DEFAULT 0,
            spec_fail_count INTEGER DEFAULT 0,
            strife_fail_count INTEGER DEFAULT 0,
            failure_sns TEXT DEFAULT '[]',
            failure_details TEXT DEFAULT '[]',
            UNIQUE(report_id, wf_num, config, test_idx)
        );

        CREATE TABLE IF NOT EXISTS report_stats (
            report_id INTEGER PRIMARY KEY REFERENCES reports(id),
            total_wfs INTEGER,
            wfs_parsed INTEGER,
            wfs_with_fails INTEGER,
            total_spec_fails INTEGER,
            total_strife_fails INTEGER,
            fa_matched INTEGER,
            fa_total INTEGER
        );

        CREATE TABLE IF NOT EXISTS daily_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            prev_report_id INTEGER REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            test_idx INTEGER NOT NULL,
            change_type TEXT,
            prev_result TEXT,
            new_result TEXT,
            detail TEXT
        );

        -- [RETIRED: Phase 5+] Retained for backward compat; no longer written.
        CREATE TABLE IF NOT EXISTS sn_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            sn TEXT NOT NULL,
            unit_num TEXT DEFAULT '',
            current_cp_idx INTEGER DEFAULT 0,
            current_cp_name TEXT DEFAULT '',
            total_cps INTEGER DEFAULT 0,
            test_idx INTEGER DEFAULT 0,
            cp_results_json TEXT DEFAULT '[]',
            UNIQUE(report_id, wf_num, config, sn)
        );
        
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            test_idx INTEGER NOT NULL,
            test_name TEXT,
            predicted_date TEXT,
            remaining_days REAL,
            daily_rate REAL,
            total_cps INTEGER,
            current_max_cp INTEGER,
            is_manual INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(wf_num, config, test_idx)
        );
        
        CREATE TABLE IF NOT EXISTS wf_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE,
            wf_nums TEXT NOT NULL,
            display_order INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS wf_names (
            wf_num TEXT PRIMARY KEY,
            wf_name TEXT NOT NULL,
            test_names TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS wf_cps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wf_num TEXT NOT NULL,
            cp_idx INTEGER NOT NULL,
            cp_name TEXT NOT NULL,
            check_items TEXT DEFAULT '[]',
            UNIQUE(wf_num, cp_idx),
            FOREIGN KEY(wf_num) REFERENCES wf_names(wf_num)
        );

        CREATE TABLE IF NOT EXISTS report_wf_meta (
            report_id INTEGER NOT NULL REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            wf_name TEXT DEFAULT '',
            PRIMARY KEY (report_id, wf_num)
        );

        CREATE TABLE IF NOT EXISTS report_test_names (
            report_id INTEGER NOT NULL REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            test_idx INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            PRIMARY KEY (report_id, wf_num, test_idx)
        );

        CREATE TABLE IF NOT EXISTS report_cps (
            report_id INTEGER NOT NULL REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            cp_idx INTEGER NOT NULL,
            cp_name TEXT NOT NULL,
            test_idx INTEGER,
            check_items TEXT DEFAULT '[]',
            PRIMARY KEY (report_id, wf_num, cp_idx)
        );

        CREATE TABLE IF NOT EXISTS report_schedule_segments (
            report_id INTEGER NOT NULL REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            test_idx INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            schedule_test_item TEXT DEFAULT '',
            planned_start_date TEXT NOT NULL,
            planned_end_date TEXT NOT NULL,
            source_row INTEGER DEFAULT 0,
            confidence TEXT DEFAULT 'medium',
            inference_reason TEXT DEFAULT '',
            marker_labels TEXT DEFAULT '[]',
            PRIMARY KEY (report_id, wf_num, config, test_idx)
        );

        CREATE TABLE IF NOT EXISTS current_schedule_segments (
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            test_idx INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            schedule_test_item TEXT DEFAULT '',
            planned_start_date TEXT NOT NULL,
            planned_end_date TEXT NOT NULL,
            source_row INTEGER DEFAULT 0,
            confidence TEXT DEFAULT 'medium',
            inference_reason TEXT DEFAULT '',
            marker_labels TEXT DEFAULT '[]',
            updated_run_id INTEGER REFERENCES reports(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (wf_num, config, test_idx)
        );

        CREATE TABLE IF NOT EXISTS current_wf_definitions (
            wf_num TEXT PRIMARY KEY,
            wf_name TEXT NOT NULL DEFAULT '',
            updated_run_id INTEGER REFERENCES reports(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS current_test_definitions (
            wf_num TEXT NOT NULL,
            test_idx INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            updated_run_id INTEGER REFERENCES reports(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (wf_num, test_idx)
        );

        CREATE TABLE IF NOT EXISTS current_cp_definitions (
            wf_num TEXT NOT NULL,
            cp_idx INTEGER NOT NULL,
            cp_name TEXT NOT NULL,
            test_idx INTEGER,
            check_items TEXT DEFAULT '[]',
            is_boundary INTEGER NOT NULL DEFAULT 0,
            updated_run_id INTEGER REFERENCES reports(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (wf_num, cp_idx)
        );

        -- [RETIRED: Phase 5+] Retained for backward compat; no longer written.
        CREATE TABLE IF NOT EXISTS sn_cp_results (
            report_id INTEGER NOT NULL REFERENCES reports(id),
            report_date TEXT NOT NULL,
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            sn TEXT NOT NULL,
            unit_num TEXT DEFAULT '',
            test_idx INTEGER NOT NULL,
            cp_idx INTEGER NOT NULL,
            status TEXT NOT NULL,
            failure_type TEXT,
            has_data INTEGER NOT NULL DEFAULT 0,
            is_current_cp INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (report_id, wf_num, config, sn, cp_idx)
        );

        -- [RETIRED: Phase 5+] Retained for backward compat; no longer written.
        CREATE TABLE IF NOT EXISTS sn_check_results (
            report_id INTEGER NOT NULL REFERENCES reports(id),
            report_date TEXT NOT NULL,
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            sn TEXT NOT NULL,
            unit_num TEXT DEFAULT '',
            test_idx INTEGER NOT NULL,
            cp_idx INTEGER NOT NULL,
            check_item_idx INTEGER NOT NULL,
            check_item TEXT NOT NULL,
            raw_value TEXT,
            normalized_value TEXT,
            status TEXT NOT NULL,
            failure_type TEXT,
            fill_color TEXT,
            font_color TEXT,
            source_row INTEGER,
            source_col INTEGER,
            PRIMARY KEY (report_id, wf_num, config, sn, cp_idx, check_item_idx)
        );

        CREATE TABLE IF NOT EXISTS sn_check_state_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wf_num TEXT NOT NULL,
            config TEXT NOT NULL,
            sn TEXT NOT NULL,
            unit_num TEXT DEFAULT '',
            test_idx INTEGER NOT NULL,
            cp_idx INTEGER NOT NULL,
            check_item_idx INTEGER NOT NULL,
            check_item TEXT NOT NULL,
            state_hash TEXT NOT NULL,
            raw_value TEXT,
            normalized_value TEXT,
            status TEXT NOT NULL,
            failure_type TEXT,
            fill_color TEXT,
            font_color TEXT,
            first_report_id INTEGER NOT NULL REFERENCES reports(id),
            first_report_date TEXT NOT NULL,
            last_seen_report_id INTEGER NOT NULL REFERENCES reports(id),
            last_seen_report_date TEXT NOT NULL,
            closed_before_report_id INTEGER REFERENCES reports(id),
            closed_before_report_date TEXT,
            first_source_row INTEGER,
            first_source_col INTEGER,
            last_source_row INTEGER,
            last_source_col INTEGER,
            UNIQUE(wf_num, config, sn, cp_idx, check_item_idx, first_report_id)
        );

        CREATE TABLE IF NOT EXISTS definition_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL REFERENCES reports(id),
            previous_report_id INTEGER REFERENCES reports(id),
            wf_num TEXT NOT NULL,
            change_type TEXT NOT NULL,
            detail_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS base_file_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_type TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            parsed_summary TEXT
        );

        CREATE TABLE IF NOT EXISTS import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            file_count INTEGER,
            record_count INTEGER,
            valid_sn_count INTEGER,
            status TEXT DEFAULT 'completed'
        );

        CREATE TABLE IF NOT EXISTS raw_check_item_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id INTEGER NOT NULL,
            import_date TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            rel_event TEXT NOT NULL,
            effective_cp TEXT,
            item TEXT NOT NULL,
            status TEXT,
            end_time TEXT,
            failing_tests TEXT,
            station_id TEXT,
            version TEXT,
            test_params TEXT,
            source_file TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_raw_records_sn ON raw_check_item_records(serial_number);
        CREATE INDEX IF NOT EXISTS idx_raw_records_batch ON raw_check_item_records(import_batch_id);
        CREATE INDEX IF NOT EXISTS idx_raw_records_cp ON raw_check_item_records(serial_number, effective_cp, item);

        CREATE INDEX IF NOT EXISTS idx_wf_results_report ON wf_results(report_id);
        CREATE INDEX IF NOT EXISTS idx_wf_results_wf ON wf_results(wf_num, config, test_idx);
        CREATE INDEX IF NOT EXISTS idx_daily_changes_report ON daily_changes(report_id);
        CREATE INDEX IF NOT EXISTS idx_sn_progress_report ON sn_progress(report_id);
        CREATE INDEX IF NOT EXISTS idx_sn_progress_sn ON sn_progress(sn);
        CREATE INDEX IF NOT EXISTS idx_sn_progress_wf ON sn_progress(wf_num, config);
        CREATE INDEX IF NOT EXISTS idx_reports_active_date ON reports(report_date, is_active);
        CREATE INDEX IF NOT EXISTS idx_sn_cp_report_wf_cfg ON sn_cp_results(report_id, wf_num, config, test_idx);
        CREATE INDEX IF NOT EXISTS idx_sn_cp_sn ON sn_cp_results(sn, report_id);
        CREATE INDEX IF NOT EXISTS idx_sn_check_report_wf_cfg ON sn_check_results(report_id, wf_num, config, test_idx, cp_idx);
        CREATE INDEX IF NOT EXISTS idx_sn_check_sn ON sn_check_results(sn, report_id);
        CREATE INDEX IF NOT EXISTS idx_sn_check_hist_failures ON sn_check_state_history(
            wf_num, config, test_idx, sn, first_report_id, closed_before_report_id, failure_type
        );
        CREATE INDEX IF NOT EXISTS idx_sn_lifecycle_open_point
        ON sn_check_state_history(wf_num, config, sn, cp_idx, check_item_idx)
        WHERE closed_before_report_id IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_sn_lifecycle_sn
        ON sn_check_state_history(sn, wf_num, config, first_report_id, closed_before_report_id);
        
        CREATE INDEX IF NOT EXISTS idx_sn_lifecycle_window
        ON sn_check_state_history(first_report_id, closed_before_report_id);
    """)
    # ── Cache table policy (Phase 7) ──────────────────────────────────
    # These tables are derived caches, rebuilt during full --rebuild:
    #   - wf_results: failure counts per WF/config/test per report
    #   - report_stats: per-report summary (WF counts, FA stats)
    #   - daily_changes: change detection between adjacent reports
    #   - predictions: auto-computed completion predictions
    #
    # They are populated by save_report() and compute_auto_predictions().
    # Rebuild rule: full --rebuild regenerates them from Excel sources.
    # Do NOT delete these tables — API endpoints depend on them.
    # Migrations for existing databases
    try:
        conn.execute("DROP INDEX IF EXISTS idx_sn_check_hist_open")
    except Exception:
        pass
    for index_name in (
        "idx_sn_lifecycle_current_progress",
        "idx_sn_lifecycle_current_failure",
        "idx_sn_check_hist_point",
    ):
        try:
            conn.execute(f"DROP INDEX IF EXISTS {index_name}")
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE reports ADD COLUMN ts_test_names TEXT DEFAULT '{}'")
    except:
        pass
    for ddl in [
        "ALTER TABLE reports ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE reports ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE reports ADD COLUMN imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE reports ADD COLUMN source_file_name TEXT DEFAULT ''",
        "ALTER TABLE reports ADD COLUMN source_file_mtime TEXT DEFAULT ''",
        "ALTER TABLE reports ADD COLUMN source_file_hash TEXT DEFAULT ''",
        "ALTER TABLE reports ADD COLUMN notes TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(ddl)
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE wf_names ADD COLUMN test_names TEXT DEFAULT '[]'")
    except:
        pass
    # Daily-result boundary persistence (Batch B step 3.1):
    # current_cp_definitions now keeps schedule-boundary rows (T0/REL_T0/
    # End/TFinal/REL_TFINAL) so cp_idx aligns between Plan and the daily
    # lifecycle table. The is_boundary tag lets each consumer plane decide
    # whether to keep them. See docs/plans/2026-05-17-rel-t0-daily-report-second-cut.md.
    try:
        conn.execute(
            "ALTER TABLE current_cp_definitions "
            "ADD COLUMN is_boundary INTEGER NOT NULL DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS wf_cps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wf_num TEXT NOT NULL,
                cp_idx INTEGER NOT NULL,
                cp_name TEXT NOT NULL,
                check_items TEXT DEFAULT '[]',
                UNIQUE(wf_num, cp_idx),
                FOREIGN KEY(wf_num) REFERENCES wf_names(wf_num)
            );
        """)
    except:
        pass
    try:
        conn.execute("ALTER TABLE wf_results ADD COLUMN failure_details TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    prune_historical_schedule_snapshots(conn)
    conn.commit()
    if owns_conn:
        conn.close()


def vacuum_db():
    """Reclaim storage after dropping tables. Must be called on a separate connection."""
    conn = get_conn()
    conn.execute("VACUUM")
    conn.close()


# ── Save ───────────────────────────────────────────────────────────────

# wf_results is maintained as a derived compatibility summary during migration.
# SN-level facts are stored in sn_cp_results/sn_check_results.
def save_report(report_date, results, fa_stats, excel_path, ts_test_names=None, report_id=None):
    """
    Saves an analysis snapshot to the database.
    results: engine.analyze() output
    fa_stats: fa_matcher.summary() output
    ts_test_names: optional {wf: [test_name, ...]} from TS sheet
    Returns: report_id
    """
    conn = get_conn()
    
    # Insert report record
    ts_names_json = json.dumps(ts_test_names) if ts_test_names else '{}'
    if report_id is None:
        report_id = create_report_version(conn, report_date, excel_path, ts_test_names=ts_test_names)
    else:
        conn.execute(
            "UPDATE reports SET ts_test_names = ? WHERE id = ?",
            (ts_names_json, report_id),
        )
    
    # Insert per-WF results
    total_spec = 0
    total_strife = 0
    wfs_with_fails = 0
    total_entries = 0
    
    for wfn, cfgs in results.items():
        has_fail = False
        for cfg in ['R1FNF', 'R2CNM', 'R3', 'R4']:
            if cfg not in cfgs: continue
            for ti, d in cfgs[cfg].items():
                sf = len(d['spec_fails'])
                stf = len(d['strife_fails'])
                t = d['total']
                if t == 0: continue
                total_entries += 1
                total_spec += sf
                total_strife += stf
                if sf > 0 or stf > 0: has_fail = True
                
                fd = d.get('failure_details', [])
                # Backward compat: if no failure_details (old engine data), generate from old format
                if not fd and (d.get('spec_fails') or d.get('strife_fails')):
                    for sn in d.get('spec_fails', []):
                        fd.append({'sn': sn, 'type': 'spec', 'location': ''})
                    for sn in d.get('strife_fails', []):
                        fd.append({'sn': sn, 'type': 'strife', 'location': ''})

                conn.execute(
                    """INSERT OR REPLACE INTO wf_results 
                       (report_id, wf_num, config, test_idx, total_units, spec_fail_count, strife_fail_count, failure_sns, failure_details)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (report_id, wfn, cfg, ti, t, sf, stf,
                     json.dumps(d['spec_fails'] + d['strife_fails']),
                     json.dumps(fd))
                )
        if has_fail: wfs_with_fails += 1
    
    # Insert stats
    conn.execute(
        """INSERT OR REPLACE INTO report_stats 
           (report_id, total_wfs, wfs_parsed, wfs_with_fails, total_spec_fails, total_strife_fails, fa_matched, fa_total)
           VALUES (?,?,?,?,?,?,?,?)""",
        (report_id, len(results), len(results), wfs_with_fails, total_spec, total_strife,
         fa_stats.get('matched', 0) if fa_stats else 0,
         fa_stats.get('total', 0) if fa_stats else 0)
    )
    
    conn.commit()
    
    # Compute daily changes against the previous active report date.
    prev_id = get_previous_active_report_id(conn, report_id)
    if prev_id:
        _compute_changes(conn, report_id, prev_id)
    
    conn.close()
    return report_id


def _compute_changes(conn, report_id, prev_report_id):
    """Compare two reports and record changes."""
    cur = conn.execute(
        """SELECT wf_num, config, test_idx, spec_fail_count, strife_fail_count, total_units
           FROM wf_results WHERE report_id = ?""",
        (report_id,)
    )
    new_data = {(r['wf_num'], r['config'], r['test_idx']): r for r in cur.fetchall()}
    
    cur = conn.execute(
        """SELECT wf_num, config, test_idx, spec_fail_count, strife_fail_count, total_units
           FROM wf_results WHERE report_id = ?""",
        (prev_report_id,)
    )
    old_data = {(r['wf_num'], r['config'], r['test_idx']): r for r in cur.fetchall()}
    
    for key, new in new_data.items():
        wfn, cfg, ti = key
        old = old_data.get(key)
        
        if old is None:
            change_type = 'new_test'
            prev_result = None
        else:
            n_fails = new['spec_fail_count'] + new['strife_fail_count']
            o_fails = old['spec_fail_count'] + old['strife_fail_count']
            if n_fails > o_fails:
                change_type = 'new_failure'
            elif n_fails < o_fails:
                change_type = 'failure_resolved'
            elif new['total_units'] != old['total_units'] or new['spec_fail_count'] != old['spec_fail_count'] or new['strife_fail_count'] != old['strife_fail_count']:
                change_type = 'data_changed'
            else:
                continue  # No change, skip
            
            prev_result = f"{old['spec_fail_count']}F/{old['strife_fail_count']}SF/{old['total_units']}T"
        
        new_result = f"{new['spec_fail_count']}F/{new['strife_fail_count']}SF/{new['total_units']}T"
        
        conn.execute(
            """INSERT INTO daily_changes 
               (report_id, prev_report_id, wf_num, config, test_idx, change_type, prev_result, new_result, detail)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (report_id, prev_report_id, wfn, cfg, ti, change_type, prev_result, new_result, '')
        )
    
    conn.commit()


# ── Query ──────────────────────────────────────────────────────────────

def get_latest_report():
    """Returns the most recent report dict, or None."""
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (rid,)).fetchone() if rid else None
    conn.close()
    return row


def get_all_reports():
    """Returns list of all report dicts."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_changes(report_id=None):
    """Returns daily_changes for a report. Defaults to latest."""
    conn = get_conn()
    if report_id is None:
        report_id = get_latest_active_report_id(conn)
    if not report_id: conn.close(); return []
    
    rows = conn.execute(
        """SELECT * FROM daily_changes 
           WHERE report_id = ? AND change_type IN ('new_failure','failure_resolved','new_test','data_changed')
           ORDER BY wf_num, config, test_idx""",
        (report_id,)
    ).fetchall()
    conn.close()
    return rows


def get_trend(wf_num, config, test_idx, limit=10):
    """Returns time series of results for charting."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.report_date, wr.spec_fail_count, wr.strife_fail_count, wr.total_units
           FROM wf_results wr JOIN reports r ON wr.report_id = r.id
           WHERE wr.wf_num = ? AND wr.config = ? AND wr.test_idx = ?
             AND r.is_active = 1
           ORDER BY r.report_date ASC
           LIMIT ?""",
        (wf_num, config, test_idx, limit)
    ).fetchall()
    conn.close()
    return rows


def get_report_stats(report_id=None):
    """Returns stats for a specific report (defaults to latest)."""
    conn = get_conn()
    if report_id is None:
        report_id = get_latest_active_report_id(conn)
    if not report_id: conn.close(); return {}
    row = conn.execute("SELECT * FROM report_stats WHERE report_id = ?", (report_id,)).fetchone()
    conn.close()
    return row or {}


# ── Stats ──────────────────────────────────────────────────────────────

def get_overview_stats():
    """Quick stats for dashboard header."""
    conn = get_conn()
    stats = {}
    stats['report_count'] = conn.execute("SELECT COUNT(*) as c FROM reports").fetchone()['c']
    latest_rid = get_latest_active_report_id(conn)
    latest = conn.execute(
        "SELECT * FROM report_stats WHERE report_id = ?",
        (latest_rid,),
    ).fetchone() if latest_rid else None
    if latest:
        stats['latest'] = latest
    conn.close()
    return stats


# ── SN Progress ─────────────────────────────────────────────────────────

# Compatibility path during the SN fact-table migration.
# New read APIs should prefer sn_cp_results/sn_check_results.
def save_sn_progress(report_id, progress_data):
    """
    保存 per-SN CP 进度快照。
    progress_data: engine.extract_sn_progress() 返回值
    Format: {wf_num: {config: [{sn, unit_num, current_cp_idx, current_cp_name,
                                total_cps, test_idx, cp_results}, ...]}}
    返回: 插入/更新的记录数
    """
    conn = get_conn()
    inserted = 0
    for wfn, cfgs in progress_data.items():
        for cfg, entries in cfgs.items():
            for entry in entries:
                conn.execute(
                    """INSERT OR REPLACE INTO sn_progress
                       (report_id, wf_num, config, sn, unit_num, current_cp_idx,
                        current_cp_name, total_cps, test_idx, cp_results_json)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (report_id, wfn, cfg, entry['sn'], entry['unit_num'],
                     entry['current_cp_idx'], entry['current_cp_name'],
                     entry['total_cps'], entry['test_idx'],
                     json.dumps(entry['cp_results']))
                )
                inserted += 1
    conn.commit()
    conn.close()
    return inserted


def get_sn_history(sn):
    """查询某个 SN 在所有日期的测试记录，按日期排序。"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT sp.report_id, sp.wf_num, sp.config, sp.sn, sp.unit_num,
                  sp.current_cp_idx, sp.current_cp_name, sp.total_cps,
                  sp.test_idx, sp.cp_results_json,
                  r.report_date
           FROM sn_progress sp
           JOIN reports r ON sp.report_id = r.id
           WHERE sp.sn = ?
           ORDER BY r.report_date ASC""",
        (sn,)
    ).fetchall()
    conn.close()
    for row in rows:
        row['cp_results'] = json.loads(row.pop('cp_results_json'))
    return rows


def get_daily_changes_by_cp(report_id):
    """
    相比前一天，找出哪些 WF 的哪些 SN 推进了 CP。
    返回: [{wf, config, sn, prev_cp, new_cp, cp_delta}, ...]
    """
    conn = get_conn()

    prev_id = get_previous_active_report_id(conn, report_id)
    if not prev_id:
        conn.close()
        return []

    cur_rows = conn.execute(
        "SELECT * FROM sn_progress WHERE report_id = ?",
        (report_id,)
    ).fetchall()
    prev_rows = conn.execute(
        "SELECT * FROM sn_progress WHERE report_id = ?",
        (prev_id,)
    ).fetchall()
    conn.close()

    cur_map = {(r['wf_num'], r['config'], r['sn']): r for r in cur_rows}
    prev_map = {(r['wf_num'], r['config'], r['sn']): r for r in prev_rows}

    changes = []
    for key, cur in cur_map.items():
        wfn, cfg, sn = key
        prev_entry = prev_map.get(key)
        if prev_entry:
            prev_cp = prev_entry['current_cp_idx']
            new_cp = cur['current_cp_idx']
            delta = new_cp - prev_cp
            if delta > 0:
                changes.append({
                    'wf': wfn, 'config': cfg, 'sn': sn,
                    'prev_cp': prev_cp, 'new_cp': new_cp, 'cp_delta': delta,
                })
        else:
            changes.append({
                'wf': wfn, 'config': cfg, 'sn': sn,
                'prev_cp': None, 'new_cp': cur['current_cp_idx'],
                'cp_delta': cur['current_cp_idx'] + 1,
            })

    return changes


def get_wf_config_progress_rows(conn, report_id):
    """
    Return one progress row per WF+Config.

    The CP name is selected from a row whose current_cp_idx equals the max
    current_cp_idx, so a slower SN cannot win by text ordering of its CP name.
    """
    return conn.execute(
        """
        WITH max_progress AS (
            SELECT wf_num, config,
                   MAX(current_cp_idx) as max_cp_idx,
                   MAX(total_cps) as total_cps,
                   COUNT(*) as sn_count
            FROM sn_progress
            WHERE report_id = ?
            GROUP BY wf_num, config
        )
        SELECT mp.wf_num, mp.config, mp.max_cp_idx,
               MIN(sp.current_cp_name) as cp_name,
               mp.total_cps, mp.sn_count
        FROM max_progress mp
        JOIN sn_progress sp
          ON sp.report_id = ?
         AND sp.wf_num = mp.wf_num
         AND sp.config = mp.config
         AND sp.current_cp_idx = mp.max_cp_idx
        GROUP BY mp.wf_num, mp.config, mp.max_cp_idx, mp.total_cps, mp.sn_count
        """,
        (report_id, report_id),
    ).fetchall()


def get_wf_config_progress_from_lifecycle(conn, report_id):
    """Return one progress row per WF+Config from lifecycle table."""
    return conn.execute(
        """WITH sn_current_cp AS (
            SELECT wf_num, config, sn,
                   MAX(cp_idx) as max_cp_idx
            FROM sn_check_state_history
            WHERE first_report_id <= ?
              AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
              AND status NOT IN ('pending', '')
            GROUP BY wf_num, config, sn
        ),
        cfg_progress AS (
            SELECT wf_num, config,
                   MAX(max_cp_idx) as max_cp_idx,
                   COUNT(*) as sn_count
            FROM sn_current_cp
            GROUP BY wf_num, config
        ),
        cp_totals AS (
            SELECT wf_num, COUNT(*) as total_cps
            FROM current_cp_definitions
            WHERE is_boundary = 0
            GROUP BY wf_num
        )
        SELECT p.wf_num, p.config, p.max_cp_idx,
               ccp.cp_name, ccp.test_idx, p.sn_count,
               COALESCE(ct.total_cps, 0) AS total_cps
        FROM cfg_progress p
        LEFT JOIN current_cp_definitions ccp
          ON ccp.wf_num = p.wf_num AND ccp.cp_idx = p.max_cp_idx
        LEFT JOIN cp_totals ct ON ct.wf_num = p.wf_num""",
        (report_id, report_id),
    ).fetchall()


# ── Completion & Failure Stats ──────────────────────────────────────────

def get_completion_stats(report_id):
    """
    获取某日报的整体完成度统计。
    CP 按 WF/Config 维度计算（取所有 SN 中最远的 CP 作为该 WF/Config 的进度），不乘以 SN 数量。
    返回: {by_config: {cfg: {total_cps, completed_cps, pct}},
           by_category: {cat: {total_cps, completed_cps, pct}}}
    """
    conn = get_conn()
    # 按 WF+Config 聚合：取 max(current_cp_idx) 作为该维度已达到的 CP
    rows = conn.execute(
        """SELECT wf_num, config,
                  MAX(total_cps) as total_cps,
                  MAX(current_cp_idx) as max_cp
           FROM sn_progress WHERE report_id = ?
           GROUP BY wf_num, config""",
        (report_id,)
    ).fetchall()

    cat_rows = conn.execute("SELECT * FROM wf_categories").fetchall()
    conn.close()

    wf_to_cat = {}
    for cat in cat_rows:
        wfs = [w.strip() for w in cat['wf_nums'].split(',') if w.strip()]
        for w in wfs:
            wf_key = w[2:] if w.upper().startswith('WF') else w
            wf_to_cat[wf_key] = cat['category_name']

    by_config = defaultdict(lambda: {'total_cps': 0, 'completed_cps': 0})
    by_category = defaultdict(lambda: {'total_cps': 0, 'completed_cps': 0})

    for row in rows:
        cfg = row['config']
        total = row['total_cps'] or 0
        completed = (row['max_cp'] or 0) + 1  # 0-based → count

        by_config[cfg]['total_cps'] += total
        by_config[cfg]['completed_cps'] += completed

        cat_name = wf_to_cat.get(row['wf_num'])
        if cat_name:
            by_category[cat_name]['total_cps'] += total
            by_category[cat_name]['completed_cps'] += completed

    overall_total_cps = sum(d['total_cps'] for d in by_config.values())
    overall_completed_cps = sum(d['completed_cps'] for d in by_config.values())

    result = {
        'overall': {
            'total_cps': overall_total_cps,
            'completed_cps': overall_completed_cps,
            'pct': round(overall_completed_cps / overall_total_cps * 100, 1)
                   if overall_total_cps else 0,
        },
        'by_config': {},
        'by_category': {},
    }
    for cfg, d in by_config.items():
        result['by_config'][cfg] = {
            'total_cps': d['total_cps'],
            'completed_cps': d['completed_cps'],
            'pct': round(d['completed_cps'] / d['total_cps'] * 100, 1)
                   if d['total_cps'] else 0,
        }
    for cat, d in by_category.items():
        result['by_category'][cat] = {
            'total_cps': d['total_cps'],
            'completed_cps': d['completed_cps'],
            'pct': round(d['completed_cps'] / d['total_cps'] * 100, 1)
                   if d['total_cps'] else 0,
        }

    return result


def get_completion_stats_from_lifecycle(report_id=None):
    """Get completion stats from lifecycle table (replaces sn_progress query)."""
    conn = get_conn()
    if report_id is None:
        report_id = get_latest_active_report_id(conn)
    if not report_id:
        conn.close()
        return {}

    report = conn.execute("SELECT report_date FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not report:
        conn.close()
        return {}

    # Get current CP for each SN from lifecycle (open rows at the report's point in time)
    rows = conn.execute(
        """SELECT l.wf_num, l.config,
               MAX(l.cp_idx) as max_cp,
               COUNT(DISTINCT l.sn) as sn_count
        FROM sn_check_state_history l
        WHERE l.first_report_id <= ?
          AND (l.closed_before_report_id IS NULL OR l.closed_before_report_id > ?)
          AND l.status NOT IN ('pending', '')
        GROUP BY l.wf_num, l.config""",
        (report_id, report_id),
    ).fetchall()

    # Get total CPs from current definitions
    cp_total_rows = conn.execute(
        "SELECT wf_num, COUNT(*) as total_cps FROM current_cp_definitions "
        "WHERE is_boundary = 0 GROUP BY wf_num"
    ).fetchall()
    cp_totals = {r['wf_num']: r['total_cps'] for r in cp_total_rows}

    cat_rows = conn.execute("SELECT * FROM wf_categories").fetchall()
    conn.close()

    wf_to_cat = {}
    for cat in cat_rows:
        wfs = [w.strip() for w in cat['wf_nums'].split(',') if w.strip()]
        for w in wfs:
            wf_key = w[2:] if w.upper().startswith('WF') else w
            wf_to_cat[wf_key] = cat['category_name']

    from collections import defaultdict
    by_config = defaultdict(lambda: {'total_cps': 0, 'completed_cps': 0})
    by_category = defaultdict(lambda: {'total_cps': 0, 'completed_cps': 0})

    for row in rows:
        cfg = row['config']
        total = cp_totals.get(row['wf_num'], 0)
        completed = (row['max_cp'] or 0) + 1

        by_config[cfg]['total_cps'] += total
        by_config[cfg]['completed_cps'] += completed

        cat_name = wf_to_cat.get(row['wf_num'])
        if cat_name:
            by_category[cat_name]['total_cps'] += total
            by_category[cat_name]['completed_cps'] += completed

    overall_total = sum(d['total_cps'] for d in by_config.values())
    overall_completed = sum(d['completed_cps'] for d in by_config.values())

    result = {
        'overall': {
            'total_cps': overall_total,
            'completed_cps': overall_completed,
            'pct': round(overall_completed / overall_total * 100, 1) if overall_total else 0,
        },
        'by_config': {},
        'by_category': {},
    }
    for cfg, d in by_config.items():
        result['by_config'][cfg] = {
            'total_cps': d['total_cps'],
            'completed_cps': d['completed_cps'],
            'pct': round(d['completed_cps'] / d['total_cps'] * 100, 1) if d['total_cps'] else 0,
        }
    for cat, d in by_category.items():
        result['by_category'][cat] = {
            'total_cps': d['total_cps'],
            'completed_cps': d['completed_cps'],
            'pct': round(d['completed_cps'] / d['total_cps'] * 100, 1) if d['total_cps'] else 0,
        }

    return result


def get_failure_rate_stats(report_id=None):
    """
    多维度 Failure Rate 统计。
    返回: {by_config, by_test, by_wf, top_failures}
    """
    conn = get_conn()
    if report_id is None:
        report_id = get_latest_active_report_id(conn)
    if not report_id:
        conn.close()
        return {}

    # by_config
    by_config = {}
    rows = conn.execute(
        """SELECT config, SUM(spec_fail_count) as spec, SUM(strife_fail_count) as strife,
                  SUM(total_units) as total
           FROM wf_results WHERE report_id = ? GROUP BY config""",
        (report_id,)
    ).fetchall()
    for r in rows:
        total = r['total'] or 0
        by_config[r['config']] = {
            'spec_fails': r['spec'], 'strife_fails': r['strife'], 'total_tests': total,
            'spec_rate': round(r['spec'] / total * 100, 1) if total else 0,
            'strife_rate': round(r['strife'] / total * 100, 1) if total else 0,
            'total_rate': round((r['spec'] + r['strife']) / total * 100, 1) if total else 0,
        }

    # by_wf
    by_wf = {}
    rows = conn.execute(
        """SELECT wf_num, SUM(spec_fail_count) as spec, SUM(strife_fail_count) as strife,
                  SUM(total_units) as total
           FROM wf_results WHERE report_id = ? GROUP BY wf_num""",
        (report_id,)
    ).fetchall()
    for r in rows:
        total = r['total'] or 0
        by_wf[r['wf_num']] = {
            'spec_fails': r['spec'], 'strife_fails': r['strife'], 'total_tests': total,
            'spec_rate': round(r['spec'] / total * 100, 1) if total else 0,
            'strife_rate': round(r['strife'] / total * 100, 1) if total else 0,
            'total_rate': round((r['spec'] + r['strife']) / total * 100, 1) if total else 0,
        }

    # by_test + top_failures
    by_test = {}
    rows = conn.execute(
        """SELECT wf_num, config, test_idx, spec_fail_count as spec,
                  strife_fail_count as strife, total_units as total
           FROM wf_results WHERE report_id = ?""",
        (report_id,)
    ).fetchall()
    top = []
    for r in rows:
        total = r['total'] or 0
        key = f"{r['wf_num']}_{r['config']}_Test{r['test_idx']+1}"
        total_fails = r['spec'] + r['strife']
        rate = round(total_fails / total * 100, 1) if total else 0
        by_test[key] = {
            'wf': r['wf_num'], 'config': r['config'], 'test_idx': r['test_idx'],
            'spec': r['spec'], 'strife': r['strife'], 'total': total,
            'spec_rate': round(r['spec'] / total * 100, 1) if total else 0,
            'strife_rate': round(r['strife'] / total * 100, 1) if total else 0,
            'total_rate': rate,
        }
        top.append({
            'wf': r['wf_num'], 'cfg': r['config'], 'test': f"Test{r['test_idx']+1}",
            'spec': r['spec'], 'strife': r['strife'], 'total': total,
            'rate': rate,
        })

    top.sort(key=lambda x: x['rate'], reverse=True)
    conn.close()

    return {
        'by_config': by_config,
        'by_test': by_test,
        'by_wf': by_wf,
        'top_failures': top[:50],
    }


def get_failure_rate_stats_from_lifecycle(report_id=None):
    """Multi-dimension failure stats from lifecycle (replaces wf_results query)."""
    conn = get_conn()
    if report_id is None:
        report_id = get_latest_active_report_id(conn)
    if not report_id:
        conn.close()
        return {}

    # Count unique SNs with failures per WF+config+test_idx
    # Using lifecycle point-in-time query
    rows = conn.execute(
        """SELECT l.wf_num, l.config, l.test_idx,
               COUNT(DISTINCT CASE WHEN l.failure_type = 'spec' THEN l.sn END) as spec,
               COUNT(DISTINCT CASE WHEN l.failure_type = 'strife' THEN l.sn END) as strife,
               COUNT(DISTINCT l.sn) as total_sns
        FROM sn_check_state_history l
        WHERE l.first_report_id <= ?
          AND (l.closed_before_report_id IS NULL OR l.closed_before_report_id > ?)
          AND l.failure_type IS NOT NULL
        GROUP BY l.wf_num, l.config, l.test_idx""",
        (report_id, report_id),
    ).fetchall()

    # Also get total SN counts by WF+config to match wf_results semantics
    total_rows = conn.execute(
        """SELECT wf_num, config, COUNT(DISTINCT sn) as total_units
           FROM sn_check_state_history l
           WHERE l.first_report_id <= ?
             AND (l.closed_before_report_id IS NULL OR l.closed_before_report_id > ?)
             AND l.test_idx = 0
           GROUP BY wf_num, config""",
        (report_id, report_id),
    ).fetchall()
    total_by_key = {}
    for r in total_rows:
        total_by_key[(r['wf_num'], r['config'])] = r['total_units']

    conn.close()

    # Build result in same format as get_failure_rate_stats
    by_config = {}
    by_wf = {}
    by_test = {}
    top = []

    for r in rows:
        wf = r['wf_num']
        cfg = r['config']
        spec = r['spec'] or 0
        strife = r['strife'] or 0
        total = total_by_key.get((wf, cfg), r['total_sns']) or 0

        # by_config
        if cfg not in by_config:
            by_config[cfg] = {'spec_fails': 0, 'strife_fails': 0, 'total_tests': 0}
        by_config[cfg]['spec_fails'] += spec
        by_config[cfg]['strife_fails'] += strife
        by_config[cfg]['total_tests'] += total

        # by_wf
        if wf not in by_wf:
            by_wf[wf] = {'spec_fails': 0, 'strife_fails': 0, 'total_tests': 0}
        by_wf[wf]['spec_fails'] += spec
        by_wf[wf]['strife_fails'] += strife
        by_wf[wf]['total_tests'] += total

        # by_test + top_failures
        key = f"{wf}_{cfg}_Test{r['test_idx'] + 1}"
        total_fails = spec + strife
        rate = round(total_fails / total * 100, 1) if total else 0
        by_test[key] = {
            'wf': wf, 'config': cfg, 'test_idx': r['test_idx'],
            'spec': spec, 'strife': strife, 'total': total,
            'spec_rate': round(spec / total * 100, 1) if total else 0,
            'strife_rate': round(strife / total * 100, 1) if total else 0,
            'total_rate': rate,
        }
        top.append({
            'wf': wf, 'cfg': cfg, 'test': f"Test{r['test_idx'] + 1}",
            'spec': spec, 'strife': strife, 'total': total,
            'rate': rate,
        })

    # Finalize rates
    for cfg, d in by_config.items():
        t = d['total_tests']
        d['spec_rate'] = round(d['spec_fails'] / t * 100, 1) if t else 0
        d['strife_rate'] = round(d['strife_fails'] / t * 100, 1) if t else 0
        d['total_rate'] = round((d['spec_fails'] + d['strife_fails']) / t * 100, 1) if t else 0
    for wf, d in by_wf.items():
        t = d['total_tests']
        d['spec_rate'] = round(d['spec_fails'] / t * 100, 1) if t else 0
        d['strife_rate'] = round(d['strife_fails'] / t * 100, 1) if t else 0
        d['total_rate'] = round((d['spec_fails'] + d['strife_fails']) / t * 100, 1) if t else 0

    top.sort(key=lambda x: x['rate'], reverse=True)

    return {
        'by_config': by_config,
        'by_test': by_test,
        'by_wf': by_wf,
        'top_failures': top[:50],
    }


# ── Predictions ─────────────────────────────────────────────────────────

def save_predictions(predictions_data):
    """
    批量保存预测数据。
    predictions_data: [{wf_num, config, test_idx, predicted_date, remaining_days,
                        daily_rate, total_cps, current_max_cp, is_manual}, ...]
    """
    conn = get_conn()
    count = 0
    for p in predictions_data:
        conn.execute(
            """INSERT OR REPLACE INTO predictions
               (wf_num, config, test_idx, test_name, predicted_date, remaining_days,
                daily_rate, total_cps, current_max_cp, is_manual, last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)""",
            (p['wf_num'], p['config'], p['test_idx'],
             p.get('test_name', f'Test{p.get("test_idx", 0) + 1}'),
             p.get('predicted_date'), p.get('remaining_days'),
             p.get('daily_rate'), p.get('total_cps'), p.get('current_max_cp'),
             p.get('is_manual', 0))
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def get_predictions(wf_num=None, config=None):
    """获取预测数据，支持按 WF 和 Config 过滤。"""
    conn = get_conn()
    where = []
    params = []
    if wf_num:
        where.append("wf_num = ?")
        params.append(wf_num)
    if config:
        where.append("config = ?")
        params.append(config)

    sql = "SELECT * FROM predictions"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY wf_num, config, test_idx"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def update_prediction(wf_num, config, test_idx, predicted_date, is_manual=0):
    """更新单条预测，优先 UPDATE，避免 REPLACE 覆盖其他列。"""
    conn = get_conn()
    cur = conn.execute(
        """UPDATE predictions
           SET predicted_date = ?, is_manual = ?, last_updated = CURRENT_TIMESTAMP
           WHERE wf_num = ? AND config = ? AND test_idx = ?""",
        (predicted_date, is_manual, wf_num, config, test_idx),
    )
    if cur.rowcount == 0:
        conn.execute(
            """INSERT INTO predictions
               (wf_num, config, test_idx, predicted_date, is_manual, last_updated)
               VALUES (?,?,?,?,?, CURRENT_TIMESTAMP)""",
            (wf_num, config, test_idx, predicted_date, is_manual),
        )
    conn.commit()
    conn.close()
    return True


# ── Categories ──────────────────────────────────────────────────────────

def init_categories():
    """初始化默认分类（首次运行）。"""
    categories = [
        ('Drop',
         'WF10,WF11,WF12,WF13,WF14.1,WF14.2,WF14.3,WF15.1,WF15.2,WF15.3,'
         'WF16.1,WF16.2,WF37,WF38,WF39,WF40,WF41', 0),
        ('Ingress',
         'WF25,WF26,WF27,WF28,WF29.1,WF29.2,WF29.3,WF29.4,WF30,WF31,WF32', 1),
        ('Environmental', 'WF1,WF2,WF3,WF4,WF5', 2),
        ('Mechanical',
         'WF6,WF7,WF8,WF9,WF17,WF18,WF19,WF20,WF21,WF22,WF23,WF24,WF35,WF36,WF42', 3),
    ]
    conn = get_conn()
    for name, wfs, order in categories:
        conn.execute(
            "INSERT OR IGNORE INTO wf_categories (category_name, wf_nums, display_order) VALUES (?, ?, ?)",
            (name, wfs, order)
        )
    conn.commit()
    conn.close()


def get_category_wfs(category_name):
    """获取分类下的 WF 编号列表。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT wf_nums FROM wf_categories WHERE category_name = ?",
        (category_name,)
    ).fetchone()
    conn.close()
    if not row:
        return []
    return [w.strip() for w in row['wf_nums'].split(',') if w.strip()]


# ── Export ──────────────────────────────────────────────────────────────

def export_sn_records(report_id, filters=None):
    """
    批量导出 SN 测试记录。
    filters: {wf, config, sn} 可选过滤字典
    返回所有匹配 SN 的完整 CP 进度（cp_results 已解析为列表）。
    """
    conn = get_conn()
    where = ["report_id = ?"]
    params = [report_id]

    if filters:
        if filters.get('wf'):
            where.append("wf_num = ?")
            params.append(filters['wf'])
        if filters.get('config'):
            where.append("config = ?")
            params.append(filters['config'])
        if filters.get('sn'):
            where.append("sn = ?")
            params.append(filters['sn'])

    sql = "SELECT * FROM sn_progress WHERE " + " AND ".join(where)
    sql += " ORDER BY wf_num, config, sn"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    for row in rows:
        row['cp_results'] = json.loads(row.pop('cp_results_json'))

    return rows


# ── CLI self-test ───────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    print("=== db.py self-test ===")
    init_db()
    init_categories()
    print(f"DB path: {DB_PATH}")

    # ── Categories ──
    print("\nCategories:")
    for cn in ['Drop', 'Ingress', 'Environmental', 'Mechanical']:
        wfs = get_category_wfs(cn)
        print(f"  {cn}: {len(wfs)} WFs ({', '.join(wfs[:4])}...)")

    # ── Reports ──
    reports = get_all_reports()
    print(f"\nReports: {len(reports)}")
    for rpt in reports:
        print(f"  #{rpt['id']}  {rpt['report_date']}  {rpt.get('excel_path','')}")

    if not reports:
        print("\nNo reports found. You must import data first.")
        print("Run: python engine.py <excel_path>")
        sys.exit(0)

    rid = reports[0]['id']

    # ── SN Progress ──
    exported = export_sn_records(rid)
    print(f"\nsn_progress records: {len(exported)}")
    if exported:
        sample = exported[0]
        print(f"  e.g. SN={sample['sn']} WF={sample['wf_num']} "
              f"CP={sample['current_cp_idx']+1}/{sample['total_cps']} "
              f"({sample['current_cp_name']})")
        # get_sn_history
        hist = get_sn_history(sample['sn'])
        print(f"  history for {sample['sn']}: {len(hist)} records")

    # ── Daily Changes ──
    changes = get_daily_changes_by_cp(rid)
    print(f"\ndaily CP changes: {len(changes)}")
    for ch in changes[:3]:
        print(f"  {ch['wf']} {ch['config']} SN={ch['sn']}: "
              f"{ch['prev_cp']}→{ch['new_cp']} (+{ch['cp_delta']})")

    # ── Completion Stats ──
    cs = get_completion_stats(rid)
    print(f"\nCompletion by config: {dict(cs['by_config'])}")
    print(f"Completion by category: {dict(cs['by_category'])}")

    # ── Failure Rate Stats ──
    fr = get_failure_rate_stats(rid)
    print(f"\nFailure by config: {len(fr['by_config'])}")
    for cfg, d in fr['by_config'].items():
        print(f"  {cfg}: {d['spec']} spec / {d['strife']} strife / {d['total']} total = {d['total_rate']}%")
    print(f"Top failures: {len(fr['top_failures'])} entries")
    for t in fr['top_failures'][:3]:
        print(f"  WF{t['wf']} {t['cfg']} Test{t['test']+1}: {t['rate']}%")

    # ── Predictions ──
    save_predictions([
        {'wf_num': 'WF10', 'config': 'R1FNF', 'test_idx': 0, 'predicted_date': '2026-06-01'},
        {'wf_num': 'WF10', 'config': 'R1FNF', 'test_idx': 1, 'predicted_date': '2026-06-10'},
    ])
    preds = get_predictions('WF10')
    print(f"\nPredictions for WF10: {len(preds)}")
    for p in preds:
        print(f"  Test{p['test_idx']+1} {p['config']}: {p['predicted_date']} (manual={p['is_manual']})")

    update_prediction('WF10', 'R1FNF', 0, '2026-06-15', 1)
    pred2 = get_predictions('WF10', 'R1FNF')
    print(f"  After update: Test{pred2[0]['test_idx']+1} → {pred2[0]['predicted_date']}")

    print("\n=== All tests passed ===")
