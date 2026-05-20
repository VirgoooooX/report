"""Controlled read-only tools for the LLM assistant.

The assistant can only use the functions in this module. Keep these helpers
small, bounded, and JSON-serializable so model answers stay grounded in data.
"""

import json
import os
import re

from app_paths import iter_rawdata_files
from db import (
    build_failure_rate_stats_from_facts,
    get_completion_stats,
    get_completion_stats_from_lifecycle,
    get_conn,
    get_failure_rate_stats,
    get_failure_rate_stats_from_lifecycle,
    get_latest_active_report_id,
    get_previous_active_report_id,
    get_wf_config_progress_from_lifecycle,
    get_latest_wf_config_progress,
    get_wf_names,
)
from fa_matcher import read_fa_tracker


MAX_SNS = 50
DEFAULT_LIMIT = 25
MAX_LIMIT = 100
FA_PATTERN = re.compile(r'M60 EVT REL FA Tracker (\d{8})\.xlsx$')


class ToolValidationError(ValueError):
    """Raised when an assistant tool receives unsafe or invalid arguments."""


def _as_clean_str(value):
    return str(value or '').strip()


def _find_fa_tracker_by_date(date_str):
    fas = []
    for fname, path in iter_rawdata_files():
        if 'FA Tracker' in fname and fname.endswith('.xlsx') and not fname.startswith('~$'):
            match = re.search(r'(\d{8})', fname)
            if match:
                raw = match.group(1)
                df = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
                fas.append((df, path))
    if not fas:
        return None
    fas.sort(key=lambda x: x[0])
    if date_str:
        for d, fp in fas:
            if d == date_str and FA_PATTERN.match(os.path.basename(fp)):
                return fp
    return fas[-1][1]


def _normalize_fa_wf(value):
    text = str(value or '').strip().upper().replace(' ', '')
    if text.startswith('WF'):
        text = text[2:]
    if text.endswith('.0'):
        text = text[:-2]
    return text


def _normalize_fa_text(value):
    return str(value or '').strip().casefold()


def _split_csv_filter(value):
    return {str(item).strip() for item in str(value or '').split(',') if str(item).strip()}


def _limit(value, default=DEFAULT_LIMIT):
    try:
        n = int(value or default)
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, MAX_LIMIT))


def _normalize_sns(value):
    if isinstance(value, str):
        sns = [s.strip() for s in value.split(',') if s.strip()]
    elif isinstance(value, list):
        sns = [str(s).strip() for s in value if str(s).strip()]
    else:
        sns = []
    if not sns:
        raise ToolValidationError('At least one SN is required.')
    if len(sns) > MAX_SNS:
        raise ToolValidationError(f'Provide up to {MAX_SNS} SNs.')
    return sns


def _resolve_unit_to_sn(conn, unit):
    unit = _as_clean_str(unit)
    if not unit:
        return ''
    for table in ('sn_check_state_history', 'sn_cp_results', 'sn_progress'):
        row = conn.execute(f"SELECT sn FROM {table} WHERE unit_num = ? LIMIT 1", (unit,)).fetchone()
        if row:
            return row['sn']
    return ''


def _latest_report(conn):
    rid = get_latest_active_report_id(conn)
    if not rid:
        return None
    return conn.execute(
        "SELECT id, report_date, version, source_file_name FROM reports WHERE id = ?",
        (rid,),
    ).fetchone()


def _tool_lookup_sn_timeline(args):
    sns = _normalize_sns(args.get('sns') or args.get('identifiers'))
    limit = _limit(args.get('limit'), default=MAX_SNS)
    conn = get_conn()
    try:
        rid = get_latest_active_report_id(conn)
        if not rid:
            return {'kind': 'sn_timeline', 'results': [], 'truncated': False, 'note': 'No active report.'}

        results = []
        for raw_sn in sns[:limit]:
            sn = raw_sn
            rows = conn.execute(
                """SELECT wf_num, config, unit_num, cp_idx, check_item_idx, check_item,
                          status, failure_type, raw_value, first_report_date
                   FROM sn_check_state_history
                   WHERE sn = ? AND first_report_id <= ?
                     AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
                   ORDER BY CAST(wf_num AS REAL), cp_idx, check_item_idx""",
                (sn, rid, rid),
            ).fetchall()
            if not rows:
                resolved = _resolve_unit_to_sn(conn, sn)
                if resolved:
                    sn = resolved
                    rows = conn.execute(
                        """SELECT wf_num, config, unit_num, cp_idx, check_item_idx, check_item,
                                  status, failure_type, raw_value, first_report_date
                           FROM sn_check_state_history
                           WHERE sn = ? AND first_report_id <= ?
                             AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
                           ORDER BY CAST(wf_num AS REAL), cp_idx, check_item_idx""",
                        (sn, rid, rid),
                    ).fetchall()

            by_wf = {}
            unit_num = ''
            for row in rows:
                if row['unit_num']:
                    unit_num = row['unit_num']
                wf = row['wf_num']
                entry = by_wf.setdefault(wf, {
                    'wf_num': wf,
                    'config': row['config'],
                    'unit_num': row['unit_num'] or '',
                    'current_cp_idx': -1,
                    'current_cp_name': '',
                    'fail_count': 0,
                    'spec_fail_count': 0,
                    'strife_fail_count': 0,
                    'failed_items': [],
                    'latest_date': row['first_report_date'],
                })
                if row['status'] != 'pending' and int(row['cp_idx'] or 0) >= entry['current_cp_idx']:
                    entry['current_cp_idx'] = int(row['cp_idx'] or 0)
                    entry['latest_date'] = row['first_report_date']
                if row['failure_type']:
                    entry['fail_count'] += 1
                    if row['failure_type'] == 'spec':
                        entry['spec_fail_count'] += 1
                    elif row['failure_type'] == 'strife':
                        entry['strife_fail_count'] += 1
                    entry['failed_items'].append({
                        'cp_idx': row['cp_idx'],
                        'check_item': row['check_item'],
                        'failure_type': row['failure_type'],
                        'value': row['raw_value'],
                    })

            for wf, entry in by_wf.items():
                cp_row = conn.execute(
                    """SELECT cp_name FROM current_cp_definitions
                       WHERE wf_num = ? AND cp_idx = ?""",
                    (wf, entry['current_cp_idx']),
                ).fetchone()
                entry['current_cp_name'] = cp_row['cp_name'] if cp_row else ''

            results.append({
                'sn': sn,
                'unit_num': unit_num,
                'found': bool(rows),
                'wfs': list(by_wf.values()),
            })
        return {
            'kind': 'sn_timeline',
            'results': results,
            'truncated': len(sns) > limit,
        }
    finally:
        conn.close()


def _tool_query_wf_config(args):
    wf = _as_clean_str(args.get('wf'))
    config = _as_clean_str(args.get('config'))
    limit = _limit(args.get('limit'))
    if not wf:
        raise ToolValidationError('wf is required.')
    if wf.upper().startswith('WF'):
        wf = wf[2:]

    conn = get_conn()
    try:
        rid = get_latest_active_report_id(conn)
        if not rid:
            return {'kind': 'wf_config', 'wf_num': wf, 'config': config or 'All', 'sns': [], 'summary': {}}

        params = [wf, rid, rid]
        where_config = ''
        if config:
            where_config = ' AND config = ?'
            params.append(config)
        rows = conn.execute(
            f"""SELECT sn, config, COALESCE(unit_num, '') AS unit_num,
                       MAX(cp_idx) AS current_cp_idx,
                       SUM(CASE WHEN failure_type = 'spec' THEN 1 ELSE 0 END) AS spec_fails,
                       SUM(CASE WHEN failure_type = 'strife' THEN 1 ELSE 0 END) AS strife_fails
                FROM sn_check_state_history
                WHERE wf_num = ? AND first_report_id <= ?
                  AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
                  {where_config}
                GROUP BY sn, config, unit_num
                ORDER BY config, sn
                LIMIT ?""",
            params + [limit],
        ).fetchall()
        count_row = conn.execute(
            f"""SELECT COUNT(DISTINCT sn) AS c
                FROM sn_check_state_history
                WHERE wf_num = ? AND first_report_id <= ?
                  AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
                  {where_config}""",
            params,
        ).fetchone()
        total_cps_row = conn.execute(
            "SELECT COUNT(*) AS c FROM current_cp_definitions WHERE wf_num = ? AND is_boundary = 0",
            (wf,),
        ).fetchone()
        wf_names = get_wf_names()
        sns = []
        for row in rows:
            sns.append({
                'sn': row['sn'],
                'unit_num': row['unit_num'],
                'config': row['config'],
                'current_cp_idx': row['current_cp_idx'],
                'spec_fails': row['spec_fails'] or 0,
                'strife_fails': row['strife_fails'] or 0,
            })
        return {
            'kind': 'wf_config',
            'wf_num': wf,
            'wf_name': wf_names.get(wf, {}).get('name', ''),
            'config': config or 'All',
            'summary': {
                'total_sns': count_row['c'] if count_row else 0,
                'returned_sns': len(sns),
                'total_cps': total_cps_row['c'] if total_cps_row else 0,
            },
            'sns': sns,
            'truncated': (count_row['c'] if count_row else 0) > len(sns),
        }
    finally:
        conn.close()


def _tool_lookup_fa_records(args):
    limit = _limit(args.get('limit'))
    fa_path = _find_fa_tracker_by_date(None)
    if not fa_path:
        return {'kind': 'fa_records', 'records': [], 'count': 0, 'error': 'FA Tracker not found'}
    records = read_fa_tracker(fa_path)

    wf = _as_clean_str(args.get('wf'))
    config = _as_clean_str(args.get('config'))
    failed_test = _as_clean_str(args.get('failed_test'))
    status = _as_clean_str(args.get('status'))
    sns = set(_normalize_sns(args.get('sns'))) if args.get('sns') else _split_csv_filter(args.get('sns', ''))

    if wf:
        target_wf = _normalize_fa_wf(wf)
        records = [r for r in records if _normalize_fa_wf(r.get('WF', '')) == target_wf]
    if config:
        target_config = _normalize_fa_text(config)
        records = [r for r in records if _normalize_fa_text(r.get('Config', '')) == target_config]
    if failed_test:
        target_test = _normalize_fa_text(failed_test)
        records = [r for r in records if _normalize_fa_text(r.get('Failed Test', '')) == target_test]
    if sns:
        records = [r for r in records if _as_clean_str(r.get('SN')) in sns]
    if status:
        records = [r for r in records if _as_clean_str(r.get('FA Status')) == status]

    clean = []
    for record in records[:limit]:
        clean.append({k: (str(v).strip() if v is not None else '') for k, v in record.items() if not str(k).startswith('_')})
    return {
        'kind': 'fa_records',
        'records': clean,
        'count': len(records),
        'truncated': len(records) > len(clean),
    }


def _tool_lookup_raw_history(args):
    sn = _as_clean_str(args.get('sn'))
    unit = _as_clean_str(args.get('unit'))
    item_filter = _as_clean_str(args.get('item'))
    date_from = _as_clean_str(args.get('from'))
    date_to = _as_clean_str(args.get('to'))
    limit = _limit(args.get('limit'))
    if not sn and not unit:
        raise ToolValidationError('sn or unit is required.')

    conn = get_conn()
    try:
        if not sn and unit:
            sn = _resolve_unit_to_sn(conn, unit)
        if not sn:
            return {'kind': 'raw_history', 'sn': '', 'records': [], 'count': 0, 'error': 'SN not found for unit.'}

        sql = """SELECT id, end_time, rel_event, effective_cp, item, status,
                        version, station_id, failing_tests, test_params
                 FROM raw_check_item_records
                 WHERE serial_number = ?"""
        params = [sn]
        if item_filter:
            sql += " AND item = ?"
            params.append(item_filter)
        if date_from:
            sql += " AND end_time >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND end_time <= ?"
            params.append(date_to + ' 23:59:59')
        count_row = conn.execute(f"SELECT COUNT(*) AS c FROM ({sql})", params).fetchone()
        sql += " ORDER BY end_time DESC LIMIT ?"
        rows = conn.execute(sql, params + [limit]).fetchall()
        records = []
        for row in rows:
            params_value = None
            if row['test_params']:
                try:
                    params_value = json.loads(row['test_params'])
                except (TypeError, json.JSONDecodeError):
                    params_value = row['test_params']
            records.append({
                'end_time': row['end_time'],
                'rel_event': row['rel_event'],
                'effective_cp': row['effective_cp'],
                'item': row['item'],
                'status': row['status'],
                'version': row['version'],
                'station_id': row['station_id'],
                'failing_tests': row['failing_tests'] or '',
                'test_params': params_value,
            })
        count = count_row['c'] if count_row else 0
        return {
            'kind': 'raw_history',
            'sn': sn,
            'records': records,
            'count': count,
            'truncated': count > len(records),
        }
    finally:
        conn.close()


def _tool_get_overview(_args):
    conn = get_conn()
    try:
        report = _latest_report(conn)
        if not report:
            return {'kind': 'overview', 'report_date': '', 'completion': {}, 'failures': {}, 'daily_updates': {}}
        rid = report['id']
        completion = get_completion_stats_from_lifecycle(rid)
        if not completion.get('by_config'):
            completion = get_completion_stats(rid)

        failures = get_failure_rate_stats_from_lifecycle(rid)
        if not failures.get('by_config'):
            failures = build_failure_rate_stats_from_facts(rid)
        if not failures.get('by_config'):
            failures = get_failure_rate_stats(rid)

        prev_rid = get_previous_active_report_id(conn, rid)
        today_progress = get_wf_config_progress_from_lifecycle(conn, rid) or get_latest_wf_config_progress(conn, rid)
        previous_progress = []
        if prev_rid:
            previous_progress = get_wf_config_progress_from_lifecycle(conn, prev_rid) or get_latest_wf_config_progress(conn, prev_rid)
        previous = {(r['wf_num'], r['config']): r['max_cp_idx'] for r in previous_progress}
        updates = []
        for row in today_progress:
            delta = (row['max_cp_idx'] or 0) - previous.get((row['wf_num'], row['config']), row['max_cp_idx'] or 0)
            if delta > 0:
                updates.append({
                    'wf_num': row['wf_num'],
                    'config': row['config'],
                    'cp_delta': delta,
                    'latest_cp': row['cp_name'] or '',
                    'sn_count': row['sn_count'] or 0,
                })

        return {
            'kind': 'overview',
            'report_date': report['report_date'],
            'active_report': dict(report),
            'completion': completion,
            'failures': {
                'by_config': failures.get('by_config', {}),
                'by_wf': failures.get('by_wf', {}),
                'top_failures': failures.get('top_failures', [])[:10],
            },
            'daily_updates': {
                'total_changes': len(updates),
                'updates': updates[:20],
                'truncated': len(updates) > 20,
            },
        }
    finally:
        conn.close()


def _normalize_check_item(value):
    text = _as_clean_str(value)
    folded = text.casefold()
    aliases = {
        'ota': 'BT-OTA',
        'bt-ota': 'BT-OTA',
        'bt ota': 'BT-OTA',
        'touch-cal-post': 'Touch-CAL-Post',
        'touch cal post': 'Touch-CAL-Post',
        'charging': 'Charging',
        'fact': 'FACT',
        'isb': 'ISB',
        'cosmetic': 'Cosmetic',
    }
    return aliases.get(folded, text)


def _tool_analyze_check_item_failure_rate(args):
    item = _normalize_check_item(args.get('item') or 'BT-OTA')
    dimension = _as_clean_str(args.get('dimension') or 'config').casefold()
    if dimension not in {'config', 'wf', 'item'}:
        raise ToolValidationError('dimension must be config, wf, or item.')
    limit = _limit(args.get('limit'), default=10)
    try:
        min_total = max(1, int(args.get('min_total') or 1))
    except (TypeError, ValueError):
        min_total = 1

    conn = get_conn()
    try:
        key_expr = {
            'config': "COALESCE(NULLIF(sn_map.config, ''), 'Unknown')",
            'wf': "COALESCE(NULLIF(sn_map.wf_num, ''), 'Unknown')",
            'item': "r.item",
        }[dimension]
        rows = conn.execute(
            f"""WITH sn_map AS (
                    SELECT sn, MIN(config) AS config, MIN(wf_num) AS wf_num
                    FROM sn_check_state_history
                    WHERE closed_before_report_id IS NULL
                    GROUP BY sn
                )
                SELECT {key_expr} AS key,
                       COUNT(*) AS total_count,
                       SUM(CASE WHEN UPPER(COALESCE(r.status, '')) = 'FAIL' THEN 1 ELSE 0 END) AS failure_count,
                       SUM(CASE WHEN UPPER(COALESCE(r.status, '')) = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
                       COUNT(DISTINCT r.serial_number) AS sn_count
                FROM raw_check_item_records r
                LEFT JOIN sn_map ON sn_map.sn = r.serial_number
                WHERE UPPER(r.item) = UPPER(?)
                  AND COALESCE(TRIM(r.status), '') <> ''
                GROUP BY key
                HAVING COUNT(*) >= ?
                ORDER BY (SUM(CASE WHEN UPPER(COALESCE(r.status, '')) = 'FAIL' THEN 1 ELSE 0 END) * 1.0 / COUNT(*)) DESC,
                         failure_count DESC,
                         total_count DESC
                LIMIT ?""",
            (item, min_total, limit),
        ).fetchall()
        source = 'raw_check_item_records'

        if not rows and dimension in {'config', 'wf'}:
            lifecycle_key = 'config' if dimension == 'config' else 'wf_num'
            rows = conn.execute(
                f"""SELECT {lifecycle_key} AS key,
                           COUNT(DISTINCT sn) AS total_count,
                           COUNT(DISTINCT CASE
                               WHEN failure_type IS NOT NULL
                                 OR LOWER(COALESCE(status, '')) IN ('fail', 'spec_fail', 'strife_fail')
                               THEN sn END) AS failure_count,
                           COUNT(DISTINCT CASE
                               WHEN failure_type IS NULL
                                AND LOWER(COALESCE(status, '')) IN ('pass', 'PASS')
                               THEN sn END) AS pass_count,
                           COUNT(DISTINCT sn) AS sn_count
                    FROM sn_check_state_history
                    WHERE UPPER(check_item) = UPPER(?)
                      AND closed_before_report_id IS NULL
                    GROUP BY {lifecycle_key}
                    HAVING COUNT(DISTINCT sn) >= ?
                    ORDER BY (COUNT(DISTINCT CASE
                                  WHEN failure_type IS NOT NULL
                                    OR LOWER(COALESCE(status, '')) IN ('fail', 'spec_fail', 'strife_fail')
                                  THEN sn END) * 1.0 / COUNT(DISTINCT sn)) DESC,
                             failure_count DESC,
                             total_count DESC
                    LIMIT ?""",
                (item, min_total, limit),
            ).fetchall()
            source = 'sn_check_state_history'

        clean_rows = []
        for row in rows:
            total = row['total_count'] or 0
            failures = row['failure_count'] or 0
            clean_rows.append({
                'key': row['key'] or 'Unknown',
                'failure_count': failures,
                'pass_count': row['pass_count'] or 0,
                'total_count': total,
                'sn_count': row['sn_count'] or 0,
                'failure_rate': round(failures / total * 100, 1) if total else 0,
            })

        return {
            'kind': 'check_item_failure_rate',
            'item': item,
            'dimension': dimension,
            'source': source,
            'min_total': min_total,
            'rows': clean_rows,
            'count': len(clean_rows),
            'truncated': len(clean_rows) >= limit,
        }
    finally:
        conn.close()


TOOL_SCHEMAS = [
    {
        'type': 'function',
        'name': 'lookup_sn_timeline',
        'description': 'Look up current lifecycle progress and failures for 1-50 serial numbers.',
        'parameters': {
            'type': 'object',
            'properties': {
                'sns': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': MAX_SNS},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': MAX_SNS},
            },
            'required': ['sns'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'query_wf_config',
        'description': 'Summarize SN progress for a WF, optionally within one config.',
        'parameters': {
            'type': 'object',
            'properties': {
                'wf': {'type': 'string'},
                'config': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': MAX_LIMIT},
            },
            'required': ['wf'],
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'lookup_fa_records',
        'description': 'Search FA Tracker records by SN, WF, config, failed test, or FA status.',
        'parameters': {
            'type': 'object',
            'properties': {
                'sns': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': MAX_SNS},
                'wf': {'type': 'string'},
                'config': {'type': 'string'},
                'failed_test': {'type': 'string'},
                'status': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': MAX_LIMIT},
            },
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'lookup_raw_history',
        'description': 'Look up raw check-item history for a serial number or unit mark.',
        'parameters': {
            'type': 'object',
            'properties': {
                'sn': {'type': 'string'},
                'unit': {'type': 'string'},
                'item': {'type': 'string'},
                'from': {'type': 'string'},
                'to': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': MAX_LIMIT},
            },
            'additionalProperties': False,
        },
    },
    {
        'type': 'function',
        'name': 'get_overview',
        'description': 'Get the latest dashboard overview, completion stats, failure stats, and daily updates.',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False},
    },
    {
        'type': 'function',
        'name': 'analyze_check_item_failure_rate',
        'description': 'Rank check-item failure rate by config, WF, or item from raw check-item records, with lifecycle fallback.',
        'parameters': {
            'type': 'object',
            'properties': {
                'item': {'type': 'string'},
                'dimension': {'type': 'string', 'enum': ['config', 'wf', 'item']},
                'min_total': {'type': 'integer', 'minimum': 1},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': MAX_LIMIT},
            },
            'additionalProperties': False,
        },
    },
]


TOOLS = {
    'lookup_sn_timeline': _tool_lookup_sn_timeline,
    'query_wf_config': _tool_query_wf_config,
    'lookup_fa_records': _tool_lookup_fa_records,
    'lookup_raw_history': _tool_lookup_raw_history,
    'get_overview': _tool_get_overview,
    'analyze_check_item_failure_rate': _tool_analyze_check_item_failure_rate,
}


def run_assistant_tool(name, args=None):
    if name not in TOOLS:
        raise ToolValidationError(f'Unknown tool: {name}')
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ToolValidationError('Tool arguments must be an object.')
    return TOOLS[name](args)


SN_RE = re.compile(r'\b[A-Z]{1,4}[A-Z0-9_-]*\d[A-Z0-9_-]*\b', re.IGNORECASE)
