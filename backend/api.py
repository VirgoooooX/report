"""
M60 EVT REL — Dashboard API Server
Enhanced Flask backend with progress tracking, predictions, and analytics.
Usage: python backend/api.py
Access: http://localhost:5050
"""
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os, sys, json, io, csv, datetime, re, logging, shutil
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
from app_paths import RAWDATA_DIR, PARSED_DIR, ensure_runtime_dirs, iter_rawdata_files
from custom_rules import DEFAULT_RULES, load_rules, save_rules, get_location_canonical
from engine import (
    analyze, build_summary_table, build_failure_detail,
    RawDataValidationError, validate_daily_report,
)
from schedule_builder import build_schedule_segments
from fa_matcher import read_fa_tracker, match as fa_match, summary as fa_summary
import fa_analysis
from db import (
    init_db, save_report, save_sn_progress, get_changes, get_trend,
    get_all_reports, get_latest_report, get_report_stats, get_conn,
    get_sn_history, get_daily_changes_by_cp, get_completion_stats,
    get_completion_stats_from_lifecycle,
    get_failure_rate_stats, get_failure_rate_stats_from_lifecycle,
    get_predictions, update_prediction,
    init_categories, get_category_wfs, export_sn_records,
    wf_sort_key, get_wf_names, get_wf_cps,
    get_wf_config_progress_from_lifecycle,
    get_sn_fact_history, get_sn_lifecycle_history, get_sn_check_details,
    get_latest_wf_config_progress, get_failure_rate_stats_from_facts,
    build_failure_rate_stats_from_facts,
    get_latest_active_report_id, get_previous_active_report_id,
    get_cell_failures,
    get_current_schedule_segments,
    get_report_test_names, get_current_wf_definitions, get_current_test_definitions,
    get_current_cp_definitions,
    get_real_cp_ordinal,
)
from processor import process_newest, process_report_file, compute_auto_predictions, REPORT_PATTERN, FA_PATTERN

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
VUE_STATIC = os.path.join(BASE_DIR, 'static')
VUE_INDEX = os.path.join(VUE_STATIC, 'index.html')

app = Flask(__name__, static_folder=None)
logger = logging.getLogger(__name__)

# ── Init ────────────────────────────────────────────────────────────────
ensure_runtime_dirs()
init_db()
init_categories()


def _rawdata_relpath(path):
    return os.path.relpath(path, RAWDATA_DIR).replace('\\', '/')


def _format_validation_error(errors):
    if not errors:
        return 'Rawdata validation failed'
    first = errors[0]
    failed_cells = ', '.join(
        f"{c.get('cell')}={c.get('value')}" for c in first.get('failed_cells', []) if c.get('cell')
    )
    later_cells = ', '.join(
        f"{c.get('cell')}={c.get('value')}" for c in first.get('later_cells', []) if c.get('cell')
    )
    return (
        "Rawdata validation failed: "
        f"{first.get('sheet', '')} row {first.get('row', '')} SN {first.get('sn', '')}, "
        f"{first.get('failed_cp', '')} has failure"
        f"{f' ({failed_cells})' if failed_cells else ''}, "
        f"but later CP {first.get('later_cp', '')} has data"
        f"{f' ({later_cells})' if later_cells else ''}."
    )


def _validation_response(errors, status=400):
    return jsonify({
        'success': False,
        'error': _format_validation_error(errors),
        'validation_errors': errors or [],
    }), status


def _resolve_rawdata_path(relpath):
    rel = str(relpath or '').replace('\\', '/').lstrip('/')
    if not rel:
        raise ValueError('Missing rawdata path')
    full = os.path.abspath(os.path.join(RAWDATA_DIR, rel))
    root = os.path.abspath(RAWDATA_DIR)
    if os.path.commonpath([root, full]) != root:
        raise ValueError('Invalid rawdata path')
    return full


def _classify_rawdata_file(fname):
    if REPORT_PATTERN.match(fname):
        return 'daily_report'
    if FA_PATTERN.match(fname):
        return 'fa_tracker'
    return 'other'


def _rawdata_date(fname):
    for pattern in (REPORT_PATTERN, FA_PATTERN):
        match = pattern.match(fname)
        if match:
            raw = match.group(1)
            return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return ''


def _delete_report_data_by_date(report_date):
    conn = get_conn()
    rows = conn.execute("SELECT id FROM reports WHERE report_date = ?", (report_date,)).fetchall()
    ids = [row['id'] for row in rows]
    if not ids:
        conn.close()
        return 0

    placeholders = ','.join('?' * len(ids))
    for table in [
        'wf_results', 'report_stats', 'daily_changes', 'sn_progress',
        'report_wf_meta', 'report_test_names', 'report_cps',
        'report_schedule_segments', 'definition_changes',
    ]:
        conn.execute(f"DELETE FROM {table} WHERE report_id IN ({placeholders})", ids)
    for table in ['sn_cp_results', 'sn_check_results']:
        conn.execute(f"DELETE FROM {table} WHERE report_id IN ({placeholders})", ids)
    for table in [
        'current_schedule_segments', 'current_wf_definitions',
        'current_test_definitions', 'current_cp_definitions',
    ]:
        conn.execute(f"DELETE FROM {table} WHERE updated_run_id IN ({placeholders})", ids)
    conn.execute(
        f"""DELETE FROM sn_check_state_history
            WHERE first_report_id IN ({placeholders})
               OR last_seen_report_id IN ({placeholders})
               OR closed_before_report_id IN ({placeholders})""",
        ids * 3,
    )
    conn.execute(f"DELETE FROM reports WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()
    return len(ids)

# ── Daily Issue helpers ─────────────────────────────────────────────────

def _normalize_wf(val):
    """Unify WF number format: strip WF prefix, handle int/float/string.
    Preserve decimal WF numbers like 15.2, 15.3."""
    if val is None:
        return ''
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).strip()
    for prefix in ('WF', 'Wf', 'wf'):
        if s.upper().startswith(prefix.upper()):
            s = s[len(prefix):].strip()
            break
    return s.strip()


def _normalize_wf_token(val):
    s = _normalize_wf(val)
    if not s:
        return ''
    # Keep decimals like 14.1; reject non-numeric WF tokens.
    if not re.match(r'^\d+(\.\d+)?$', s):
        return ''
    return f"WF{s}"


def _normalize_category_name(name):
    return str(name or '').strip()


def _normalize_failure_type(ft):
    """Normalize to 'spec' / 'strife' / other."""
    s = str(ft or '').strip().lower()
    if 'spec' in s:
        return 'spec'
    if 'strife' in s:
        return 'strife'
    return s if s else 'unknown'


def _parse_date_value(val):
    """Parse cell value to 'YYYY-MM-DD' date string. Returns None on failure."""
    if isinstance(val, datetime.datetime):
        return val.strftime('%Y-%m-%d')
    if isinstance(val, datetime.date):
        return val.strftime('%Y-%m-%d')
    if isinstance(val, str):
        val = val.strip()
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%m/%d/%y'):
            try:
                return datetime.datetime.strptime(val[:10], fmt).strftime('%Y-%m-%d')
            except ValueError:
                pass
    return None


def _find_fa_tracker_by_date(date_str):
    """Find FA Tracker file matching the given date, or the latest available."""
    fas = []
    for fname, path in iter_rawdata_files():
        if 'FA Tracker' in fname and fname.endswith('.xlsx') and not fname.startswith('~$'):
            m = re.search(r'(\d{8})', fname)
            if m:
                raw = m.group(1)
                df = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
                fas.append((df, path))
    if not fas:
        return None
    fas.sort(key=lambda x: x[0])
    if date_str:
        for d, fp in fas:
            if d == date_str:
                return fp
    return fas[-1][1]  # fallback to latest


def _fa_field(issue, hint):
    """Fuzzy-match a field in FA Tracker issue dict by looking for a key that contains hint (case-insensitive).
    Returns the value, or empty string if not found."""
    wanted = hint.strip().lower()
    for key, value in issue.items():
        if wanted in str(key).strip().lower():
            return value
    return ''


# ── Serve Vue SPA assets ────────────────────────────────────────────────
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(VUE_STATIC, 'assets'), filename)

@app.route('/favicon.svg')
def serve_favicon():
    path = os.path.join(VUE_STATIC, 'favicon.svg')
    if os.path.exists(path):
        return send_file(path)
    return '', 404

# ── SPA Catch-all (serve Vue index.html for all non-API routes) ─────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def spa_catchall(path):
    # Skip API routes
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    # Skip static assets
    if path.startswith('assets/') or path.startswith('favicon'):
        return '', 404
    # Serve Vue SPA
    if os.path.exists(VUE_INDEX):
        return send_file(VUE_INDEX)
    # Fallback to Flask templates
    return render_template('dashboard.html')


# ═══════════════════════════════════════════════════════════════════════
#  API: Data Version (for frontend cache invalidation)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/version')
def api_version():
    """Return a version token that changes when the database is updated.
    The frontend uses this to decide whether to invalidate cached API responses."""
    conn = get_conn()
    row = conn.execute(
        """SELECT id, report_date, version, source_file_name
           FROM reports
           WHERE is_active = 1
           ORDER BY report_date DESC, version DESC
           LIMIT 1"""
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'version': 'empty'})
    return jsonify({
        'version': f"{row['report_date']}-r{row['id']}-v{row['version']}",
        'active_report': {
            'id': row['id'],
            'report_date': row['report_date'],
            'report_version': row['version'],
            'source_file_name': row['source_file_name'] or '',
        },
    })


# ═══════════════════════════════════════════════════════════════════════
#  API: Dashboard Overview
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/dashboard/overview')
def api_overview():
    """Dashboard overview: completion, daily updates, failure summary."""
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    if not rid:
        conn.close()
        return jsonify({'error': 'No data'}), 404
    
    # Completion stats (lifecycle first)
    completion = get_completion_stats_from_lifecycle(rid)
    if not completion.get('by_config'):
        completion = get_completion_stats(rid)
    
    # Daily CP changes — 比较前后两天的 max(current_cp_idx) per WF+Config
    prev_rid = get_previous_active_report_id(conn, rid)
    today_progress = get_wf_config_progress_from_lifecycle(conn, rid)
    if not today_progress:
        today_progress = get_latest_wf_config_progress(conn, rid)

    if prev_rid:
        today_map = {
            (r['wf_num'], r['config']): r['max_cp_idx']
            for r in today_progress
        }
        previous_progress = get_wf_config_progress_from_lifecycle(conn, prev_rid)
        if not previous_progress:
            previous_progress = get_latest_wf_config_progress(conn, prev_rid)
        yesterday_map = {
            (r['wf_num'], r['config']): r['max_cp_idx']
            for r in previous_progress
        }
    else:
        today_map = {}
        yesterday_map = {}
    
    # 获取今天各 WF+Config 的 latest CP 信息
    cp_info_rows = today_progress
    
    # 构建每日更新：每个 WF+Config，cp_delta = 今天 max_cp - 昨天 max_cp
    wf_updates = {}
    for row in cp_info_rows:
        wfn = row['wf_num']
        cfg = row['config']
        today_cp = today_map.get((wfn, cfg), row['max_cp_idx'] or 0)
        yesterday_cp = yesterday_map.get((wfn, cfg), -1)
        delta = today_cp - yesterday_cp if yesterday_cp >= 0 else 0
        
        if delta > 0:
            if wfn not in wf_updates:
                wf_updates[wfn] = {'wf': wfn, 'configs': {}}
            wf_updates[wfn]['configs'][cfg] = {
                'cp_delta': delta,
                'sn_count': row['sn_count'] or 0,
                'latest_cp': row['cp_name'] or '',
                'latest_cp_idx': today_cp,
                'total_cps': row.get('total_cps') or 0,
            }
    
    # WF names mapping
    wf_names = get_wf_names()
    display_rules = load_rules().get('display', {})
    for wf, alias in display_rules.get('wf_aliases', {}).items():
        entry = wf_names.setdefault(wf, {'name': '', 'test_names': []})
        entry['name'] = alias
    
    # Build sorted wf_updates_list
    wf_updates_list = []
    for wfn in sorted(wf_updates.keys(), key=wf_sort_key):
        u = wf_updates[wfn]
        configs_list = []
        for cfg in ['R1FNF', 'R2CNM', 'R3', 'R4']:
            if cfg in u['configs']:
                item = dict(u['configs'][cfg])
                item['config'] = cfg
                configs_list.append(item)
        if configs_list:
            wf_updates_list.append({'wf': wfn, 'configs': configs_list})
    
    # Failure stats (lifecycle first)
    fail_stats = get_failure_rate_stats_from_lifecycle(rid)
    if not fail_stats.get('by_config'):
        fail_stats = build_failure_rate_stats_from_facts(rid)
    if not fail_stats.get('by_config'):
        fail_stats = get_failure_rate_stats(rid)
    
    # Latest report date and source_file_name for project name extraction
    rpt = conn.execute("SELECT id, report_date, version, source_file_name FROM reports WHERE id = ?", (rid,)).fetchone()
    report_date = rpt['report_date'] if rpt else ''
    
    project_name = 'M60 EVT REL'
    if rpt and rpt['source_file_name']:
        import re
        m = re.match(r'^(.*?)\s*Daily Report_', rpt['source_file_name'], re.IGNORECASE)
        if m:
            project_name = m.group(1).upper()
    if display_rules.get('project_name'):
        project_name = display_rules['project_name']
    
    # Historical trend data — one entry per date (latest version only)
    reports = conn.execute(
        """SELECT r.id, r.report_date
           FROM reports r
           INNER JOIN (
               SELECT report_date, MAX(id) AS max_id
               FROM reports
               WHERE is_active = 1
               GROUP BY report_date
           ) latest ON r.id = latest.max_id
           ORDER BY r.report_date ASC"""
    ).fetchall()
    trend_data = []
    seen_dates = set()
    for r in reports:
        if r['report_date'] in seen_dates:
            continue
        stats = conn.execute(
            "SELECT total_spec_fails, total_strife_fails FROM report_stats WHERE report_id=?",
            (r['id'],)
        ).fetchone()
        if stats:
            seen_dates.add(r['report_date'])
            trend_data.append({
                'date': r['report_date'],
                'spec': stats['total_spec_fails'] or 0,
                'strife': stats['total_strife_fails'] or 0,
            })
    
    conn.close()
    
    return jsonify({
        'project_name': project_name,
        'report_date': report_date,
        'active_report': {
            'id': rpt['id'] if rpt else rid,
            'report_date': report_date,
            'report_version': rpt['version'] if rpt else '',
            'source_file_name': rpt['source_file_name'] if rpt else '',
        },
        'completion': completion,
        'daily_updates': {
            'total_changes': len(wf_updates_list),
            'wf_updates': wf_updates_list,
        },
        'failures': fail_stats,
        'wf_names': wf_names,
        'trend': trend_data,
    })


# ═══════════════════════════════════════════════════════════════════════
#  API: Completion
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/completion/by-config')
def api_completion_config():
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    stats = get_completion_stats_from_lifecycle(rid)
    if not stats.get('by_config'):
        stats = get_completion_stats(rid)
    conn.close()
    return jsonify(stats.get('by_config', {}))


@app.route('/api/completion/by-category')
def api_completion_category():
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    stats = get_completion_stats_from_lifecycle(rid)
    if not stats.get('by_category'):
        stats = get_completion_stats(rid)
    conn.close()
    return jsonify(stats.get('by_category', {}))


@app.route('/api/completion/category/<name>')
def api_category_wf_detail(name):
    """Per-WF completion detail within a category. CP 按 WF/Config 维度取最远 CP。"""
    wfs = get_category_wfs(name)
    if not wfs:
        return jsonify({'error': f'Category {name} not found'}), 404
    
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    
    wf_details = []
    for wf in wfs:
        # strip 'WF' prefix — DB stores wf_num without prefix
        wf_key = wf[2:] if wf.upper().startswith('WF') else wf
        # 按 WF+Config 聚合，取最远 CP
        rows = conn.execute(
            """SELECT config,
                      MAX(total_cps) as total_cps,
                      MAX(current_cp_idx) as max_cp,
                      COUNT(*) as sn_count
               FROM sn_progress WHERE report_id = ? AND wf_num = ?
               GROUP BY config""",
            (rid, wf_key)
        ).fetchall()
        
        for row in rows:
            total = row['total_cps'] or 0
            completed = (row['max_cp'] or 0) + 1
            wf_details.append({
                'wf': wf_key, 'config': row['config'],
                'total_cps': total,
                'completed_cps': completed,
                'pct': round(completed / total * 100, 1) if total else 0,
                'sn_count': row['sn_count'] or 0,
            })
    
    # Add WF names
    wf_names = get_wf_names()
    for d in wf_details:
        d['wf_name'] = wf_names.get(d['wf'], {}).get('name', '')
    
    conn.close()
    return jsonify({'category': name, 'wfs': wf_details, 'wf_names': wf_names})


@app.route('/api/completion/wf/<wfn>')
def api_wf_completion(wfn):
    """Per-WF completion detail across configs."""
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    
    rows = conn.execute(
        """SELECT config, total_cps, cp_results_json
           FROM sn_progress WHERE report_id = ? AND wf_num = ?""",
        (rid, wfn)
    ).fetchall()
    conn.close()
    
    by_cfg = {}
    for row in rows:
        cfg = row['config']
        if cfg not in by_cfg:
            by_cfg[cfg] = {'total': 0, 'completed': 0, 'sn_count': 0, 'pass': 0, 'spec': 0, 'strife': 0}
        by_cfg[cfg]['sn_count'] += 1
        cp_list = json.loads(row['cp_results_json'])
        for cp in cp_list:
            by_cfg[cfg]['total'] += 1
            if cp['status'] in ('pass', 'spec_fail', 'strife_fail'):
                by_cfg[cfg]['completed'] += 1
            if cp['status'] == 'pass':
                by_cfg[cfg]['pass'] += 1
            elif cp['status'] == 'spec_fail':
                by_cfg[cfg]['spec'] += 1
            elif cp['status'] == 'strife_fail':
                by_cfg[cfg]['strife'] += 1
    
    result = {}
    for cfg, d in by_cfg.items():
        result[cfg] = {
            'total_cps': d['total'],
            'completed_cps': d['completed'],
            'pct': round(d['completed']/d['total']*100, 1) if d['total'] else 0,
            'sn_count': d['sn_count'],
            'pass': d['pass'], 'spec': d['spec'], 'strife': d['strife'],
        }
    
    return jsonify({'wf': wfn, 'configs': result})


# ═══════════════════════════════════════════════════════════════════════
#  API: Categories (CRUD for custom WF classification)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/categories')
def api_categories_list():
    """获取所有分类及包含的 WF。"""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM wf_categories ORDER BY display_order").fetchall()
    conn.close()
    result = []
    for r in rows:
        wfs = [w.strip() for w in r['wf_nums'].split(',') if w.strip()]
        result.append({
            'name': r['category_name'],
            'wf_nums': wfs,
            'display_order': r['display_order'],
        })
    return jsonify({'categories': result})


@app.route('/api/categories/<name>/wfs', methods=['PUT'])
def api_category_update_wfs(name):
    """更新某个分类下的 WF 列表。Body: {wf_nums: ['WF10','WF11',...]}"""
    name = _normalize_category_name(name)
    if not name:
        return jsonify({'error': 'Invalid category name'}), 400
    data = request.get_json()
    if not data or 'wf_nums' not in data:
        return jsonify({'error': 'Missing wf_nums'}), 400
    normalized = []
    for wf in data['wf_nums']:
        token = _normalize_wf_token(wf)
        if not token:
            return jsonify({'error': f'Invalid wf_num: {wf}'}), 400
        normalized.append(token)
    wf_nums_str = ','.join(normalized)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO wf_categories (category_name, wf_nums, display_order) VALUES (?,?,COALESCE((SELECT display_order FROM wf_categories WHERE category_name=?),0))",
        (name, wf_nums_str, name)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/categories/<name>/add-wf', methods=['POST'])
def api_category_add_wf(name):
    """向分类添加一个 WF。Body: {wf_num: 'WF10'}"""
    name = _normalize_category_name(name)
    if not name:
        return jsonify({'error': 'Invalid category name'}), 400
    data = request.get_json()
    if not data or 'wf_num' not in data:
        return jsonify({'error': 'Missing wf_num'}), 400
    wf_num = _normalize_wf_token(data['wf_num'])
    if not wf_num:
        return jsonify({'error': 'Invalid wf_num'}), 400
    conn = get_conn()
    row = conn.execute("SELECT wf_nums FROM wf_categories WHERE category_name=?", (name,)).fetchone()
    if not row:
        conn.execute("INSERT INTO wf_categories (category_name, wf_nums, display_order) VALUES (?,?,0)", (name, wf_num))
    else:
        wfs = [w.strip() for w in row['wf_nums'].split(',') if w.strip()]
        if wf_num not in wfs:
            wfs.append(wf_num)
        conn.execute("UPDATE wf_categories SET wf_nums=? WHERE category_name=?", (','.join(wfs), name))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/categories/<name>/remove-wf', methods=['POST'])
def api_category_remove_wf(name):
    """从分类移除一个 WF。Body: {wf_num: 'WF10'}"""
    name = _normalize_category_name(name)
    if not name:
        return jsonify({'error': 'Invalid category name'}), 400
    data = request.get_json()
    if not data or 'wf_num' not in data:
        return jsonify({'error': 'Missing wf_num'}), 400
    wf_num = _normalize_wf_token(data['wf_num'])
    if not wf_num:
        return jsonify({'error': 'Invalid wf_num'}), 400
    conn = get_conn()
    row = conn.execute("SELECT wf_nums FROM wf_categories WHERE category_name=?", (name,)).fetchone()
    if row:
        wfs = [w.strip() for w in row['wf_nums'].split(',') if w.strip() if w.strip() != wf_num]
        conn.execute("UPDATE wf_categories SET wf_nums=? WHERE category_name=?", (','.join(wfs), name))
        conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/categories/<name>', methods=['DELETE'])
def api_category_delete(name):
    """删除一个分类。"""
    name = _normalize_category_name(name)
    if not name:
        return jsonify({'error': 'Invalid category name'}), 400
    conn = get_conn()
    conn.execute("DELETE FROM wf_categories WHERE category_name = ?", (name,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/categories', methods=['POST'])
def api_category_create():
    """创建新分类。Body: {name: 'xxx', display_order: N}"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Missing name'}), 400
    name = _normalize_category_name(data['name'])
    if not name:
        return jsonify({'error': 'Invalid category name'}), 400
    display_order = data.get('display_order', 99)
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO wf_categories (category_name, wf_nums, display_order) VALUES (?, '', ?)",
        (name, display_order)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# ═══════════════════════════════════════════════════════════════════════
#  API: Daily Updates
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/daily/updates')
def api_daily_updates():
    """Get CP progress changes for a specific date or the latest."""
    date = request.args.get('date', '')
    conn = get_conn()
    
    if date:
        rpt = conn.execute("SELECT id FROM reports WHERE report_date = ?", (date,)).fetchone()
    else:
        rid = get_latest_active_report_id(conn)
        rpt = {'id': rid} if rid else None
    
    if not rpt or not rpt['id']:
        conn.close()
        return jsonify({'error': 'Report not found'}), 404
    
    rid = rpt['id']
    changes = get_daily_changes_by_cp(rid)
    conn.close()
    
    # Group by WF
    by_wf = {}
    for ch in changes:
        wf = ch['wf']
        if wf not in by_wf:
            by_wf[wf] = {'wf': wf, 'total_delta': 0, 'sns': []}
        by_wf[wf]['total_delta'] += ch['cp_delta']
        by_wf[wf]['sns'].append({
            'config': ch['config'], 'sn': ch['sn'],
            'from_cp': ch['prev_cp'], 'to_cp': ch['new_cp'],
            'delta': ch['cp_delta']
        })
    
    return jsonify({'report_date': date or 'latest', 'by_wf': list(by_wf.values())})


# ═══════════════════════════════════════════════════════════════════════
#  API: Failures
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/failures/stats')
def api_failure_stats():
    """Multi-dimensional failure rate stats."""
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    conn.close()

    if not rid:
        return jsonify({'by_config': {}, 'by_test': {}, 'by_wf': {}, 'top_failures': []})

    stats = get_failure_rate_stats_from_lifecycle(rid)
    if not stats.get('by_config'):
        stats = build_failure_rate_stats_from_facts(rid)
    if not stats.get('by_config'):
        stats = get_failure_rate_stats(rid)
    return jsonify(stats)


@app.route('/api/failures/top')
def api_failure_top():
    """Top N failure items by dimension."""
    limit = request.args.get('limit', 10, type=int)
    by_dim = request.args.get('by', 'test')  # config, wf, test
    
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    stats = get_failure_rate_stats_from_lifecycle(rid)
    if not stats.get('by_config'):
        stats = build_failure_rate_stats_from_facts(rid)
    if not stats.get('by_config'):
        stats = get_failure_rate_stats(rid)
    conn.close()
    
    if by_dim == 'config':
        data = stats.get('by_config', {})
        items = [{'key': k, **v} for k, v in data.items()]
    elif by_dim == 'wf':
        data = stats.get('by_wf', {})
        items = [{'key': k, **v} for k, v in data.items()]
    else:
        items = stats.get('top_failures', [])[:limit]
    
    items.sort(key=lambda x: x.get('total_rate', x.get('rate', 0)), reverse=True)
    
    return jsonify({'dimension': by_dim, 'items': items[:limit]})


@app.route('/api/failures/wf/<wfn>')
def api_wf_failures(wfn):
    """Per-WF failure detail with per-SN information."""
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    
    rows = conn.execute(
        """WITH cp_test_ranges AS (
               SELECT wf_num, test_idx, MIN(cp_idx) AS first_cp, MAX(cp_idx) AS last_cp
               FROM report_cps
               WHERE report_id = ? AND wf_num = ?
               GROUP BY wf_num, test_idx
           ),
           sn_current AS (
               SELECT wf_num, config, sn, cp_idx AS current_cp_idx
               FROM sn_cp_results
               WHERE report_id = ? AND wf_num = ? AND is_current_cp = 1
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
               WHERE cp.report_id = ? AND cp.wf_num = ? AND cp.has_data = 1
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
                      COUNT(DISTINCT CASE WHEN failure_type = 'spec' THEN sn END) AS spec_fail_count,
                      COUNT(DISTINCT CASE WHEN failure_type = 'strife' THEN sn END) AS strife_fail_count
               FROM sn_test_failure
               GROUP BY wf_num, config, test_idx
           )
           SELECT tt.wf_num, tt.config, tt.test_idx,
                  COALESCE(tt.total_units, 0) AS total_units,
                  COALESCE(fa.spec_fail_count, 0) AS spec_fail_count,
                  COALESCE(fa.strife_fail_count, 0) AS strife_fail_count
           FROM test_totals tt
           LEFT JOIN test_fail_agg fa
             ON fa.wf_num = tt.wf_num AND fa.config = tt.config AND fa.test_idx = tt.test_idx
           ORDER BY tt.config, tt.test_idx""",
        (rid, wfn, rid, wfn, rid, rid, wfn, rid),
    ).fetchall()
    
    # Also get per-SN CP detail for failures
    sn_rows = conn.execute(
        """SELECT sn, config, cp_idx AS current_cp_idx, status
           FROM sn_cp_results
           WHERE report_id = ? AND wf_num = ? AND is_current_cp = 1""",
        (rid, wfn)
    ).fetchall()
    conn.close()
    
    return jsonify({
        'wf': wfn,
        'results': [dict(r) for r in rows],
        'sn_details': [dict(r) for r in sn_rows],
    })


# ═══════════════════════════════════════════════════════════════════════
#  API: Predictions
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/predictions')
def api_predictions():
    """Get all predictions, optionally filtered."""
    wf = request.args.get('wf', '')
    cfg = request.args.get('config', '')
    
    preds = get_predictions(wf_num=wf if wf else None, config=cfg if cfg else None)
    if not preds:
        try:
            compute_auto_predictions()
            preds = get_predictions(wf_num=wf if wf else None, config=cfg if cfg else None)
        except Exception:
            logger.exception("Failed to generate lifecycle-backed predictions")
    
    return jsonify({'predictions': [dict(p) for p in preds]})


@app.route('/api/predictions/update', methods=['POST'])
def api_predictions_update():
    """Manual prediction update."""
    data = request.get_json()
    if not data or 'wf_num' not in data or 'config' not in data or 'test_idx' not in data:
        return jsonify({'error': 'Missing required fields: wf_num, config, test_idx'}), 400
    
    update_prediction(
        data['wf_num'], data['config'], data['test_idx'],
        data.get('predicted_date'), is_manual=1
    )
    return jsonify({'status': 'ok'})


# ═══════════════════════════════════════════════════════════════════════
#  API: Schedule
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/schedule')
def api_schedule():
    # Plan layer must be present: require both checkpoint_schedule and test_schedule
    base_status = base_manager.get_base_status()
    available_types = {row.get('file_type') for row in base_status if row.get('file_type')}
    required_types = {'checkpoint_schedule', 'test_schedule'}
    missing_types = sorted(required_types - available_types)
    if missing_types:
        return jsonify({'error': 'base_data_missing', 'missing': missing_types}), 400

    conn = get_conn()
    try:
        segments = [
            segment for segment in get_current_schedule_segments(conn)
            if str(segment.get('wf_num')) not in {'43', '44'}
        ]
        if not segments:
            return jsonify({
                'error': 'base_data_missing',
                'missing': ['test_schedule_segments'],
            }), 400

        # cps_by_key from current_cp_definitions (Plan layer single source).
        # Boundary rows (T0/REL_T0/End/TFinal/REL_TFINAL) are persisted with
        # is_boundary=1 so cp_idx aligns with daily lifecycle rows; they are
        # filtered out here because the schedule view only ever places real
        # test CPs as dots between the lane-bar T0/End anchors.
        # See docs/plans/2026-05-17-rel-t0-daily-report-second-cut.md.
        cp_defs = get_current_cp_definitions(conn)
        cps_by_key = {}
        for wf_num, cp_list in cp_defs.items():
            if str(wf_num) in {'43', '44'}:
                continue
            for cp in cp_list:
                if cp.get('is_boundary'):
                    continue
                key = (str(wf_num), cp.get('test_idx'))
                cps_by_key.setdefault(key, []).append({
                    'cp_idx': cp.get('cp_idx'),
                    'cp_name': cp.get('cp_name'),
                })
        for entries in cps_by_key.values():
            entries.sort(key=lambda c: int(c.get('cp_idx') or 0))

        # Actual layer: optional. No daily report → null progress.
        report = conn.execute(
            """SELECT id, report_date FROM reports
               WHERE is_active = 1
               ORDER BY report_date DESC, version DESC
               LIMIT 1"""
        ).fetchone()
        report_id = report['id'] if report else None
        report_date = report['report_date'] if report else None

        progress_by_key = {}
        if report_id is not None:
            progress_rows = get_wf_config_progress_from_lifecycle(conn, report_id)
            for row in progress_rows:
                normalized_wf = _normalize_wf(row['wf_num'])
                if normalized_wf in {'43', '44'}:
                    continue
                progress_by_key[(normalized_wf, row['config'])] = {
                    'current_cp_idx': row['max_cp_idx'],
                    'current_cp_name': row['cp_name'] or '',
                    'total_cps': row['total_cps'] or 0,
                    'sn_count': row['sn_count'] or 0,
                }

        # WF names: prefer Base-uploaded definitions (Plan layer single source).
        # Fall back to the wf_names cache (populated by daily ingest) so existing
        # WFs keep their display name when only a daily report has been ingested.
        wf_meta = dict(get_current_wf_definitions(conn) or {})
        for wf_num_key, info in (get_wf_names() or {}).items():
            if wf_num_key not in wf_meta:
                wf_meta[wf_num_key] = info
        payload_segments = build_schedule_segments(
            segments,
            wf_meta=wf_meta,
            cps_by_key=cps_by_key,
            progress_by_key=progress_by_key,
        )
        return jsonify({
            'report_id': report_id,
            'report_date': report_date,
            'segments': payload_segments,
        })
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  API: SN Query (enhanced lifecycle timeline)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/query/sn-timeline')
def api_sn_timeline():
    """Get full CP-level timeline with check_item details for one or more SNs."""
    sns_param = request.args.get('sns', '').strip()
    if not sns_param:
        return jsonify({'error': 'Missing sns parameter'}), 400
    sns = [s.strip() for s in sns_param.split(',') if s.strip()]
    if not sns or len(sns) > 50:
        return jsonify({'error': 'Provide 1-50 SNs'}), 400

    conn = get_conn()
    rid = get_latest_active_report_id(conn)

    results = []
    for sn in sns:
        rows = conn.execute(
            """SELECT wf_num, config, unit_num, cp_idx, check_item_idx, check_item,
                      status, failure_type, raw_value, first_report_date
               FROM sn_check_state_history
               WHERE sn = ? AND first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
               ORDER BY CAST(wf_num AS REAL), cp_idx, check_item_idx""",
            (sn, rid, rid),
        ).fetchall()

        sn_unit_num = ''
        by_wf = {}
        for r in rows:
            wf = r['wf_num']
            if not sn_unit_num and r['unit_num']:
                sn_unit_num = r['unit_num']
            if wf not in by_wf:
                by_wf[wf] = {'wf_num': wf, 'config': r['config'], 'cps': {}}
            cp_idx = r['cp_idx']
            if cp_idx not in by_wf[wf]['cps']:
                by_wf[wf]['cps'][cp_idx] = {
                    'cp_idx': cp_idx,
                    'date': r['first_report_date'],
                    'items': [],
                }
            by_wf[wf]['cps'][cp_idx]['items'].append({
                'idx': r['check_item_idx'],
                'name': r['check_item'],
                'status': r['status'],
                'failure_type': r['failure_type'],
                'value': r['raw_value'],
            })

        # Flatten and compute CP-level summary
        sn_wfs = []
        for wf_key in sorted(by_wf.keys(), key=lambda x: float(x) if x.replace('.', '').isdigit() else 999):
            wf_data = by_wf[wf_key]
            cp_list = []
            for cp_idx in sorted(wf_data['cps'].keys()):
                cp = wf_data['cps'][cp_idx]
                items = cp['items']
                total = len(items)
                passed = sum(1 for i in items if i['status'] == 'pass')
                failed = sum(1 for i in items if i['failure_type'])
                pending = sum(1 for i in items if i['status'] == 'pending')
                if failed > 0:
                    cp_status = 'fail'
                elif pending == total:
                    cp_status = 'pending'
                else:
                    cp_status = 'pass'
                fail_item = next((i['name'] for i in items if i['failure_type']), None)
                fail_type = next((i['failure_type'] for i in items if i['failure_type']), None)
                cp_list.append({
                    'cp_idx': cp_idx,
                    'date': cp['date'],
                    'status': cp_status,
                    'pass_count': passed,
                    'total_count': total,
                    'fail_item': fail_item,
                    'fail_type': fail_type,
                    'items': items,
                })
            # Get CP names — keep boundary rows here so REL_T0 lifecycle
            # data resolves to its real name in the timeline.
            cp_names = {}
            cp_defs = conn.execute(
                "SELECT cp_idx, cp_name FROM current_cp_definitions WHERE wf_num = ?",
                (wf_key,),
            ).fetchall()
            for cd in cp_defs:
                cp_names[cd['cp_idx']] = cd['cp_name']
            # total_cps reports non-boundary count (Batch B step 3.4b Class A).
            total_cps_row = conn.execute(
                "SELECT COUNT(*) AS c FROM current_cp_definitions "
                "WHERE wf_num = ? AND is_boundary = 0",
                (wf_key,),
            ).fetchone()
            total_cps = total_cps_row['c'] if total_cps_row else 0

            for cp in cp_list:
                cp['cp_name'] = cp_names.get(cp['cp_idx'], f"CP{cp['cp_idx']}")

            # Determine current CP (last non-pending)
            current_cp_idx = -1
            for cp in cp_list:
                if cp['status'] != 'pending':
                    current_cp_idx = cp['cp_idx']

            sn_wfs.append({
                'wf_num': wf_key,
                'config': wf_data['config'],
                'total_cps': total_cps,
                'current_cp_idx': current_cp_idx,
                'cps': cp_list,
            })

        results.append({'sn': sn, 'unit_num': sn_unit_num, 'wfs': sn_wfs})

    # Get WF names
    wf_names = get_wf_names()
    conn.close()

    return jsonify({'results': results, 'wf_names': {k: v.get('name', '') for k, v in wf_names.items()}})


@app.route('/api/query/by-wf')
def api_query_by_wf():
    """Query all SNs for a given WF, optionally filtered by config."""
    wf = request.args.get('wf', '').strip()
    config = request.args.get('config', '').strip()
    if not wf:
        return jsonify({'error': 'Missing wf parameter'}), 400

    conn = get_conn()
    rid = get_latest_active_report_id(conn)

    # Get all SNs in this WF
    params = [wf, rid, rid]
    config_filter = ""
    if config:
        config_filter = " AND config = ?"
        params.append(config)

    sn_rows = conn.execute(
        f"""SELECT DISTINCT sn, config, COALESCE(unit_num, '') AS unit_num FROM sn_check_state_history
            WHERE wf_num = ? AND first_report_id <= ?
              AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
              {config_filter}
            ORDER BY config, sn""",
        params,
    ).fetchall()

    # Get CP definitions
    cp_defs = conn.execute(
        "SELECT cp_idx, cp_name FROM current_cp_definitions "
        "WHERE wf_num = ? AND is_boundary = 0 ORDER BY cp_idx",
        (wf,),
    ).fetchall()
    cp_names = {cd['cp_idx']: cd['cp_name'] for cd in cp_defs}
    total_cps = len(cp_defs)

    # Get check items list (from first CP definition)
    check_items_list = []
    ci_row = conn.execute(
        "SELECT check_items FROM current_cp_definitions "
        "WHERE wf_num = ? AND is_boundary = 0 LIMIT 1",
        (wf,),
    ).fetchone()
    if ci_row:
        check_items_list = json.loads(ci_row['check_items'] or '[]')

    # For each SN, get CP-level summary
    sns_data = []
    unique_sns = list({r['sn'] for r in sn_rows})

    for sn_row in sn_rows:
        sn = sn_row['sn']
        cfg = sn_row['config']
        cps = conn.execute(
            """SELECT cp_idx,
                      COUNT(*) as item_count,
                      SUM(CASE WHEN status='pass' THEN 1 ELSE 0 END) as pass_count,
                      SUM(CASE WHEN failure_type IS NOT NULL THEN 1 ELSE 0 END) as fail_count,
                      SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending_count,
                      MIN(first_report_date) as date,
                      GROUP_CONCAT(CASE WHEN failure_type IS NOT NULL THEN check_item ELSE NULL END) as fail_items,
                      GROUP_CONCAT(CASE WHEN failure_type IS NOT NULL THEN failure_type ELSE NULL END) as fail_types
               FROM sn_check_state_history
               WHERE sn=? AND wf_num=? AND config=?
                 AND first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
               GROUP BY cp_idx ORDER BY cp_idx""",
            (sn, wf, cfg, rid, rid),
        ).fetchall()

        cp_list = []
        current_cp_idx = -1
        for cp in cps:
            if cp['fail_count'] > 0:
                status = 'fail'
            elif cp['pending_count'] == cp['item_count']:
                status = 'pending'
            else:
                status = 'pass'
            if status != 'pending':
                current_cp_idx = cp['cp_idx']
            cp_list.append({
                'cp_idx': cp['cp_idx'],
                'cp_name': cp_names.get(cp['cp_idx'], f"CP{cp['cp_idx']}"),
                'status': status,
                'pass_count': cp['pass_count'],
                'total_count': cp['item_count'],
                'date': cp['date'],
                'fail_item': cp['fail_items'].split(',')[0] if cp['fail_items'] else None,
                'fail_type': cp['fail_types'].split(',')[0] if cp['fail_types'] else None,
            })

        sns_data.append({
            'sn': sn,
            'unit_num': sn_row['unit_num'] or '',
            'config': cfg,
            'current_cp_idx': current_cp_idx,
            'total_cps': total_cps,
            'cps': cp_list,
        })

    # Summary stats
    total_sns = len(sns_data)
    completed = sum(1 for s in sns_data if s['current_cp_idx'] >= total_cps - 1)
    failed_sns = [s for s in sns_data if any(cp['status'] == 'fail' for cp in s['cps'])]
    spec_fails = sum(1 for s in sns_data if any(cp.get('fail_type') == 'spec' for cp in s['cps']))
    strife_fails = sum(1 for s in sns_data if any(cp.get('fail_type') == 'strife' for cp in s['cps']))

    wf_names = get_wf_names()
    wf_name = wf_names.get(wf, {}).get('name', '')
    conn.close()

    return jsonify({
        'wf_num': wf,
        'wf_name': wf_name,
        'config_filter': config or 'All',
        'total_cps': total_cps,
        'cp_names': cp_names,
        'check_items': check_items_list,
        'summary': {
            'total_sns': total_sns,
            'completed': completed,
            'spec_fails': spec_fails,
            'strife_fails': strife_fails,
        },
        'sns': sns_data,
    })


@app.route('/api/query/wf-list')
def api_query_wf_list():
    """Get available WFs and configs for the query page dropdowns."""
    conn = get_conn()
    wfs = conn.execute(
        "SELECT wf_num, wf_name FROM current_wf_definitions ORDER BY CAST(wf_num AS REAL)"
    ).fetchall()
    configs = conn.execute(
        "SELECT DISTINCT config FROM sn_check_state_history WHERE closed_before_report_id IS NULL ORDER BY config"
    ).fetchall()
    conn.close()
    return jsonify({
        'wfs': [{'wf_num': w['wf_num'], 'wf_name': w['wf_name']} for w in wfs],
        'configs': [c['config'] for c in configs],
    })


# ═══════════════════════════════════════════════════════════════════════
#  API: SN Lookup
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/sn/<sn>')
def api_sn_lookup(sn):
    """Get all test records for an SN across all dates."""
    # Load from lifecycle table first, fall back to fact tables
    history_rows = get_sn_lifecycle_history(sn)
    if not history_rows:
        history_rows = get_sn_fact_history(sn)
    history = []
    for row in history_rows:
        if row['is_current_cp']:
            history.append({
                'date': row['report_date'],
                'wf': row['wf_num'],
                'config': row['config'],
                'sn': row['sn'],
                'unit_num': row['unit_num'],
                'current_cp': row['cp_name'] or f"CP{row['cp_idx'] + 1}",
                'cp_idx': row['cp_idx'],
                'test_idx': row['test_idx'],
                'test_name': row['test_name'] or f"Test{row['test_idx'] + 1}",
                'status': row['status'],
                'failure_type': row['failure_type'],
            })
    
    if not history:
        return jsonify({'sn': sn, 'records': [], 'message': 'SN not found'}), 404
    
    # Pre-compute real-CP ordinals for every distinct (wf, cp_idx) seen in
    # history so the percentage uses the non-boundary rank rather than raw
    # cp_idx+1. Without this, an SN at the first real CP (cp_idx=1, with
    # REL_T0 at cp_idx=0) would show as "2/N" instead of "1/N". See
    # docs/plans/2026-05-17-rel-t0-daily-report-second-cut.md §3.4b Class B.
    ordinal_lookup = {}
    distinct_keys = {(h['wf'], h['cp_idx'] or 0) for h in history}
    if distinct_keys:
        ord_conn = get_conn()
        try:
            for wf_key, cp_idx_key in distinct_keys:
                ordinal_lookup[(wf_key, cp_idx_key)] = get_real_cp_ordinal(
                    ord_conn, wf_key, cp_idx_key,
                )
        finally:
            ord_conn.close()

    # Group by WF for cleaner display
    by_wf = {}
    for h in history:
        wf = h['wf']
        if wf not in by_wf:
            by_wf[wf] = {
                'wf': wf,
                'history': [],
                'latest': None,
            }
        total_cps = h.get('total_cps') or 0
        cp_idx = h['cp_idx'] or 0
        real_ordinal = ordinal_lookup.get((wf, cp_idx), 0)
        entry = {
            'date': h['date'],
            'config': h['config'],
            'unit': h.get('unit_num', ''),
            'current_cp': h['current_cp'],
            'cp_idx': cp_idx,
            'test_idx': h['test_idx'],
            'test_name': h['test_name'],
            'status': h['status'],
            'failure_type': h['failure_type'],
            'total_cps': total_cps,
            'pct': round(real_ordinal / total_cps * 100, 1) if total_cps else 0,
            'cp_status': h['status'],
        }
        by_wf[wf]['history'].append(entry)
        by_wf[wf]['latest'] = entry
    
    # 排序：每个 WF 组内的 history 按日期降序
    for wf_data in by_wf.values():
        wf_data['history'].sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Get failure records
    conn = get_conn()
    fa_rows = conn.execute(
        """SELECT fa.*, r.report_date FROM wf_results fa
           JOIN reports r ON fa.report_id = r.id
           WHERE fa.failure_sns LIKE ?
           ORDER BY r.report_date DESC""",
        (f'%{sn}%',)
    ).fetchall()
    conn.close()
    
    return jsonify({
        'sn': sn,
        'by_wf': list(by_wf.values()),
        'failures': [dict(r) for r in fa_rows],
    })


@app.route('/api/sn/search')
def api_sn_search():
    """Search by SN or unit mark number (unit_num). Returns list of {sn, unit_num} pairs."""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])

    like = f'%{q}%'
    conn = get_conn()
    # Prefer lifecycle table; search both SN and unit_num, return distinct pairs.
    rows = conn.execute(
        """SELECT DISTINCT sn, COALESCE(unit_num, '') AS unit_num
             FROM sn_check_state_history
            WHERE sn LIKE ? OR unit_num LIKE ?
            ORDER BY CASE WHEN sn LIKE ? THEN 0 ELSE 1 END, sn
            LIMIT 30""",
        (like, like, like),
    ).fetchall()
    if not rows:
        rows = conn.execute(
            """SELECT DISTINCT sn, COALESCE(unit_num, '') AS unit_num
                 FROM sn_cp_results
                WHERE sn LIKE ? OR unit_num LIKE ?
                ORDER BY CASE WHEN sn LIKE ? THEN 0 ELSE 1 END, sn
                LIMIT 30""",
            (like, like, like),
        ).fetchall()
    if not rows:
        rows = conn.execute(
            """SELECT DISTINCT sn, COALESCE(unit_num, '') AS unit_num
                 FROM sn_progress
                WHERE sn LIKE ? OR unit_num LIKE ?
                ORDER BY CASE WHEN sn LIKE ? THEN 0 ELSE 1 END, sn
                LIMIT 30""",
            (like, like, like),
        ).fetchall()
    conn.close()

    return jsonify([{'sn': r['sn'], 'unit_num': r['unit_num']} for r in rows])


@app.route('/api/sn/<sn>/checks')
def api_sn_check_details(sn):
    """Check-item details for one CP. Query: wf, config, cp_idx."""
    wf = _normalize_wf(request.args.get('wf', ''))
    config = request.args.get('config', '').strip()
    cp_idx_raw = request.args.get('cp_idx', '').strip()

    if not (wf and config and cp_idx_raw):
        return jsonify({'error': 'wf, config, cp_idx are required'}), 400
    try:
        cp_idx = int(cp_idx_raw)
    except ValueError:
        return jsonify({'error': 'cp_idx must be an integer'}), 400

    conn = get_conn()
    report_id = get_latest_active_report_id(conn)
    conn.close()
    if not report_id:
        return jsonify({'sn': sn, 'wf_num': wf, 'config': config, 'cp_idx': cp_idx, 'check_items': []})

    rows = get_sn_check_details(report_id, wf, config, sn, cp_idx) or []
    return jsonify({
        'sn': sn,
        'wf_num': wf,
        'config': config,
        'cp_idx': cp_idx,
        'check_items': [
            {
                'check_item_idx': r['check_item_idx'],
                'check_item': r['check_item'],
                'status': r['status'],
                'failure_type': r.get('failure_type'),
                'raw_value': r.get('raw_value'),
            }
            for r in rows
        ],
    })


@app.route('/api/sn/resolve-mark')
def api_resolve_mark():
    """Resolve a unit mark number (e.g. ER1-2-4) to its SN. 1:1 mapping expected."""
    mark = request.args.get('mark', '').strip()
    if not mark:
        return jsonify({'error': 'mark parameter required'}), 400

    conn = get_conn()
    row = None
    for table in ['sn_check_state_history', 'sn_cp_results', 'sn_progress']:
        row = conn.execute(
            f"SELECT sn FROM {table} WHERE unit_num = ? LIMIT 1", (mark,)
        ).fetchone()
        if row:
            break
    conn.close()
    if not row:
        return jsonify({'error': 'Mark number not found'}), 404
    return jsonify({'sn': row['sn'], 'unit_num': mark})


@app.route('/api/sn/fa')
def api_sn_fa():
    """Get FA Tracker failure info for one or more SNs, with optional filters.
    Query: sns=SN1,SN2,... (optional — if empty, returns all issues matching filters)
           symptom, location, config, wf, failed_test (all optional, comma-separated for multi-select)
    Returns: {results: {SN: [row_dict, ...]}}
    """
    sns_param = request.args.get('sns', '').strip()
    sns = [s.strip() for s in sns_param.split(',') if s.strip()] if sns_param else []
    if len(sns) > 50:
        return jsonify({'error': 'Provide up to 50 SNs'}), 400

    # Collect filters (comma-separated values → sets for multi-select)
    filter_symptom = {v.strip().lower() for v in request.args.get('symptom', '').split(',') if v.strip()}
    filter_location = {v.strip().lower() for v in request.args.get('location', '').split(',') if v.strip()}
    filter_config = {v.strip().lower() for v in request.args.get('config', '').split(',') if v.strip()}
    filter_wf = {_normalize_wf(v) for v in request.args.get('wf', '').split(',') if v.strip()}
    filter_wf.discard('')
    filter_test = {v.strip().lower() for v in request.args.get('failed_test', '').split(',') if v.strip()}

    fa_path = _find_fa_tracker_by_date(None)
    if not fa_path:
        return jsonify({'results': {}})

    try:
        all_issues = fa_analysis.read_fa_tracker(fa_path)
    except Exception:
        return jsonify({'results': {}})

    sn_set = set(sns) if sns else None
    results = {}
    for issue in all_issues:
        sn = str(issue.get('SN', '')).strip()
        if not sn:
            continue
        # SN filter (if provided)
        if sn_set and sn not in sn_set:
            continue
        # Apply multi-select filters (match ANY of the selected values)
        if filter_symptom:
            val = str(issue.get('Failure Symptom / Failure Message', '') or '').lower()
            if not any(f in val for f in filter_symptom):
                continue
        if filter_location:
            val = str(issue.get('Failed Location', '') or '').lower()
            if not any(f == val or f in val for f in filter_location):
                continue
        if filter_config:
            val = str(issue.get('Config', '') or '').lower()
            if val not in filter_config:
                continue
        if filter_wf:
            val = _normalize_wf(issue.get('WF', ''))
            if val not in filter_wf:
                continue
        if filter_test:
            val = str(issue.get('Failed Test', '') or '').lower()
            if not any(f in val for f in filter_test):
                continue

        # Return all meaningful fields
        entry = {}
        for key, val in issue.items():
            if key.startswith('_'):
                continue
            entry[key] = str(val).strip() if val is not None else ''
        results.setdefault(sn, []).append(entry)

    return jsonify({'results': results})


@app.route('/api/sn/fa/options')
def api_sn_fa_options():
    """Get cascading filter options from FA Tracker.
    Accepts partial filters to narrow down remaining options.
    Query: wf, config, failed_test, symptom, location (all optional, comma-separated)
    Returns: {symptoms: [...], locations: [...], configs: [...], wfs: [...], failed_tests: [...]}
    """
    fa_path = _find_fa_tracker_by_date(None)
    if not fa_path:
        return jsonify({'symptoms': [], 'locations': [], 'configs': [], 'wfs': [], 'failed_tests': []})

    try:
        all_issues = fa_analysis.read_fa_tracker(fa_path)
    except Exception:
        return jsonify({'symptoms': [], 'locations': [], 'configs': [], 'wfs': [], 'failed_tests': []})

    # Parse current selections for cascading
    sel_wf = {_normalize_wf(v) for v in request.args.get('wf', '').split(',') if v.strip()}
    sel_wf.discard('')
    sel_config = {v.strip().lower() for v in request.args.get('config', '').split(',') if v.strip()}
    sel_test = {v.strip().lower() for v in request.args.get('failed_test', '').split(',') if v.strip()}
    sel_symptom = {v.strip().lower() for v in request.args.get('symptom', '').split(',') if v.strip()}
    sel_location = {v.strip().lower() for v in request.args.get('location', '').split(',') if v.strip()}

    # Filter issues by current selections to derive remaining options
    filtered = []
    for issue in all_issues:
        if sel_wf:
            val = _normalize_wf(issue.get('WF', ''))
            if val not in sel_wf:
                continue
        if sel_config:
            val = str(issue.get('Config', '') or '').strip().lower()
            if val not in sel_config:
                continue
        if sel_test:
            val = str(issue.get('Failed Test', '') or '').strip().lower()
            if not any(f in val for f in sel_test):
                continue
        if sel_symptom:
            val = str(issue.get('Failure Symptom / Failure Message', '') or '').strip().lower()
            if not any(f in val for f in sel_symptom):
                continue
        if sel_location:
            val = str(issue.get('Failed Location', '') or '').strip().lower()
            if not any(f == val or f in val for f in sel_location):
                continue
        filtered.append(issue)

    # Derive distinct values from filtered set
    symptoms = set()
    locations = set()
    configs = set()
    wfs = set()
    failed_tests = set()

    for issue in filtered:
        v = str(issue.get('Failure Symptom / Failure Message', '') or '').strip()
        if v: symptoms.add(v)
        v = str(issue.get('Failed Location', '') or '').strip()
        if v: locations.add(v)
        v = str(issue.get('Config', '') or '').strip()
        if v: configs.add(v)
        v = _normalize_wf(issue.get('WF', ''))
        if v: wfs.add(v)
        v = str(issue.get('Failed Test', '') or '').strip()
        if v: failed_tests.add(v)

    return jsonify({
        'symptoms': sorted(symptoms),
        'locations': sorted(locations),
        'configs': sorted(configs),
        'wfs': sorted(wfs, key=lambda x: float(x) if x.replace('.', '').isdigit() else 999),
        'failed_tests': sorted(failed_tests),
    })


# ═══════════════════════════════════════════════════════════════════════
#  API: Export
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/export')
def api_export():
    """Batch export SN test records."""
    wf_f = request.args.get('wf', '').strip()
    cfg_f = request.args.get('config', '').strip()
    sn_f = request.args.get('sn', '').strip()
    fmt = request.args.get('format', 'json')  # json or csv
    
    filters = {}
    if wf_f: filters['wf'] = wf_f
    if cfg_f: filters['config'] = cfg_f
    if sn_f: filters['sn'] = sn_f
    
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    if not rid:
        conn.close()
        return jsonify({'records': [], 'count': 0, 'error': 'No active report'}), 404
    records = export_sn_records(rid, filters if filters else None)
    conn.close()
    
    if fmt == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['SN', 'Unit', 'WF', 'Config', 'Current CP', 'CP Index', 'Total CPs', 'CP Results'])
        for r in records:
            cp_summary = ' | '.join(
                f"{cp['cp_name']}={cp['status']}" for cp in r.get('cp_results', [])
            )
            writer.writerow([
                r['sn'], r.get('unit_num', ''), r['wf_num'], r['config'],
                r['current_cp_name'], r['current_cp_idx'], r['total_cps'],
                cp_summary
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'export_{datetime.date.today()}.csv'
        )
    
    return jsonify({'records': records, 'count': len(records)})


# ═══════════════════════════════════════════════════════════════════════
#  API: Test Summary
# ═══════════════════════════════════════════════════════════════════════

def _test_progress_state(current_cp_idx, first_cp_idx, last_cp_idx):
    if current_cp_idx is None or first_cp_idx is None or last_cp_idx is None:
        return 'not_started'
    if current_cp_idx < first_cp_idx:
        return 'not_started'
    if current_cp_idx < last_cp_idx:
        return 'in_progress'
    return 'complete'


_MONTH_ABBR = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def _short_date(date_str):
    """Convert 'YYYY-MM-DD' to 'd-Mon' format. Returns '' on failure."""
    if not date_str:
        return ''
    try:
        y, m, d = date_str.split('-')
        month_name = _MONTH_ABBR[int(m)]
        return f'{int(d)}-{month_name}'
    except (ValueError, IndexError):
        return ''


@app.route('/api/test-summary')
def api_test_summary():
    """Generate a test summary table similar to Daily Report's Test Summary.

    Failure rate logic:
      1. Only completed tests (current_cp >= last_cp) count toward FR.
      2. For each SN, only the LAST CP within the test's range is considered.
      3. In-progress tests display the schedule plan end date (blue background).
      4. Not-started tests display the schedule plan start date (white background).
    """
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    if not rid:
        conn.close()
        return jsonify({'summary': []})

    report_test_names = get_current_test_definitions(conn)
    if not report_test_names:
        report_test_names = get_report_test_names(conn, rid)
    current_wf_names = get_current_wf_definitions(conn)

    rows = conn.execute(
        """WITH wf_configs AS (
               SELECT DISTINCT wf_num, config
               FROM sn_check_state_history
               WHERE first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
           ),
           test_slots AS (
               SELECT DISTINCT wf_num, test_idx
               FROM current_cp_definitions
               WHERE is_boundary = 0
           ),
           cp_test_ranges AS (
               SELECT wf_num, test_idx, MIN(cp_idx) AS first_cp, MAX(cp_idx) AS last_cp
               FROM current_cp_definitions
               WHERE is_boundary = 0
               GROUP BY wf_num, test_idx
           ),
           sn_current AS (
               SELECT wf_num, config, sn, MAX(cp_idx) AS current_cp_idx
               FROM sn_check_state_history
               WHERE first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
                 AND status NOT IN ('pending', '')
               GROUP BY wf_num, config, sn
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
           -- Only count failures from complete tests: current_cp >= test's last_cp
           -- And only from the LAST CP of the test (not earlier CPs)
           sn_test_failure AS (
               SELECT sc.wf_num, sc.config, sc.sn, tr.test_idx,
                      l.failure_type
               FROM sn_current sc
               JOIN cp_test_ranges tr
                 ON tr.wf_num = sc.wf_num AND sc.current_cp_idx >= tr.last_cp
               JOIN sn_check_state_history l
                 ON l.wf_num = sc.wf_num AND l.config = sc.config AND l.sn = sc.sn
                AND l.cp_idx = tr.last_cp
                AND l.first_report_id <= ?
                AND (l.closed_before_report_id IS NULL OR l.closed_before_report_id > ?)
               WHERE l.failure_type IS NOT NULL
           ),
           test_fail_agg AS (
               SELECT wf_num, config, test_idx,
                      COUNT(DISTINCT CASE WHEN failure_type = 'spec' THEN sn END) AS spec_fail_count,
                      COUNT(DISTINCT CASE WHEN failure_type = 'strife' THEN sn END) AS strife_fail_count,
                      GROUP_CONCAT(DISTINCT sn) AS failure_sns_csv
               FROM sn_test_failure
               GROUP BY wf_num, config, test_idx
           )
           SELECT s.wf_num, c.config, s.test_idx,
                  COALESCE(tt.total_units, 0) AS total_units,
                  COALESCE(fa.spec_fail_count, 0) AS spec_fail_count,
                  COALESCE(fa.strife_fail_count, 0) AS strife_fail_count,
                  fa.failure_sns_csv
           FROM test_slots s
           JOIN wf_configs c
             ON c.wf_num = s.wf_num
           LEFT JOIN test_totals tt
             ON tt.wf_num = s.wf_num AND tt.config = c.config AND tt.test_idx = s.test_idx
           LEFT JOIN test_fail_agg fa
             ON fa.wf_num = s.wf_num AND fa.config = c.config AND fa.test_idx = s.test_idx
           GROUP BY s.wf_num, c.config, s.test_idx
           ORDER BY CAST(s.wf_num AS REAL), c.config, s.test_idx""",
        (rid, rid, rid, rid, rid, rid),
    ).fetchall()

    if not rows:
        rows = conn.execute(
            """WITH wf_configs AS (
                   SELECT DISTINCT wf_num, config
                   FROM sn_cp_results
                   WHERE report_id = ?
               ),
               test_slots AS (
                   SELECT DISTINCT wf_num, test_idx
                   FROM report_cps
                   WHERE report_id = ?
               ),
               cp_test_ranges AS (
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
               -- Only complete tests, last CP of the test only
               sn_test_failure AS (
                   SELECT sc.wf_num, sc.config, sc.sn, tr.test_idx,
                          cp.failure_type
                   FROM sn_current sc
                   JOIN cp_test_ranges tr
                     ON tr.wf_num = sc.wf_num AND sc.current_cp_idx >= tr.last_cp
                   JOIN sn_cp_results cp
                     ON cp.report_id = ?
                    AND cp.wf_num = sc.wf_num AND cp.config = sc.config
                    AND cp.sn = sc.sn AND cp.cp_idx = tr.last_cp
                   WHERE cp.failure_type IS NOT NULL
               ),
               test_fail_agg AS (
                   SELECT wf_num, config, test_idx,
                          COUNT(DISTINCT CASE WHEN failure_type = 'spec' THEN sn END) AS spec_fail_count,
                          COUNT(DISTINCT CASE WHEN failure_type = 'strife' THEN sn END) AS strife_fail_count,
                          GROUP_CONCAT(DISTINCT sn) AS failure_sns_csv
                   FROM sn_test_failure
                   GROUP BY wf_num, config, test_idx
               )
               SELECT s.wf_num, c.config, s.test_idx,
                      COALESCE(tt.total_units, 0) AS total_units,
                      COALESCE(fa.spec_fail_count, 0) AS spec_fail_count,
                      COALESCE(fa.strife_fail_count, 0) AS strife_fail_count,
                      fa.failure_sns_csv
               FROM test_slots s
               JOIN wf_configs c
                 ON c.wf_num = s.wf_num
               LEFT JOIN test_totals tt
                 ON tt.wf_num = s.wf_num AND tt.config = c.config AND tt.test_idx = s.test_idx
               LEFT JOIN test_fail_agg fa
                 ON fa.wf_num = s.wf_num AND fa.config = c.config AND fa.test_idx = s.test_idx
               GROUP BY s.wf_num, c.config, s.test_idx
               ORDER BY CAST(s.wf_num AS REAL), c.config, s.test_idx""",
            (rid, rid, rid, rid, rid),
        ).fetchall()

    # 查询每个 WF/Config/test 的 CP 范围
    cp_ranges = {}
    for row in conn.execute(
        """SELECT wf_num, test_idx, MIN(cp_idx) AS first_cp_idx, MAX(cp_idx) AS last_cp_idx
           FROM current_cp_definitions
           WHERE is_boundary = 0
           GROUP BY wf_num, test_idx""",
    ).fetchall():
        cp_ranges[(row['wf_num'], row['test_idx'])] = {
            'first_cp_idx': row['first_cp_idx'],
            'last_cp_idx': row['last_cp_idx'],
        }
    if not cp_ranges:
        for row in conn.execute(
            """SELECT wf_num, test_idx, MIN(cp_idx) AS first_cp_idx, MAX(cp_idx) AS last_cp_idx
               FROM report_cps
               WHERE report_id = ?
               GROUP BY wf_num, test_idx""",
            (rid,),
        ).fetchall():
            cp_ranges[(row['wf_num'], row['test_idx'])] = {
                'first_cp_idx': row['first_cp_idx'],
                'last_cp_idx': row['last_cp_idx'],
            }

    # 查询每个 WF/Config 的最新 current CP
    current_cps = {}
    for row in conn.execute(
        """SELECT wf_num, config, MAX(cp_idx) AS current_cp_idx
           FROM sn_check_state_history
           WHERE first_report_id <= ?
             AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
             AND status NOT IN ('pending', '')
           GROUP BY wf_num, config""",
        (rid, rid),
    ).fetchall():
        current_cps[(row['wf_num'], row['config'])] = row['current_cp_idx']
    if not current_cps:
        for row in conn.execute(
            """SELECT wf_num, config, MAX(cp_idx) AS current_cp_idx
               FROM sn_cp_results
               WHERE report_id = ? AND is_current_cp = 1
               GROUP BY wf_num, config""",
            (rid,),
        ).fetchall():
            current_cps[(row['wf_num'], row['config'])] = row['current_cp_idx']

    # 加载 schedule segments 用于计划日期显示
    schedule_dates = {}
    for row in conn.execute(
        """SELECT wf_num, config, test_idx,
                  planned_start_date, planned_end_date
           FROM current_schedule_segments""",
    ).fetchall():
        schedule_dates[(row['wf_num'], row['config'], row['test_idx'])] = {
            'planned_start_date': row['planned_start_date'],
            'planned_end_date': row['planned_end_date'],
        }
    if not schedule_dates:
        for row in conn.execute(
            """SELECT wf_num, config, test_idx,
                      planned_start_date, planned_end_date
               FROM report_schedule_segments
               WHERE report_id = ?""",
            (rid,),
        ).fetchall():
            schedule_dates[(row['wf_num'], row['config'], row['test_idx'])] = {
                'planned_start_date': row['planned_start_date'],
                'planned_end_date': row['planned_end_date'],
            }

    conn.close()

    # Load real test names from wf_names table for fallback
    wf_names = get_wf_names()
    for wf_num, wf_name in current_wf_names.items():
        wf_names.setdefault(wf_num, {})['name'] = wf_name

    summary = {}
    for r in rows:
        wf = r['wf_num']
        wf_real_names = report_test_names.get(wf) or wf_names.get(wf, {}).get('test_names', [])
        if wf not in summary:
            summary[wf] = {
                'wf': wf,
                'wf_name': wf_names.get(wf, {}).get('name', ''),
                'configs': {},
                'config_results': {},
                'test_names': list(wf_real_names),
            }

        cfg = r['config']
        ti = r['test_idx']
        sf = r['spec_fail_count']
        stf = r['strife_fail_count']
        t = r['total_units']

        tname = wf_real_names[ti] if ti < len(wf_real_names) else f'Test{ti+1}'

        tn_list = summary[wf]['test_names']
        if ti >= len(tn_list):
            tn_list.extend([''] * (ti - len(tn_list) + 1))
        if not tn_list[ti]:
            tn_list[ti] = tname

        # 计算进度状态
        cp_range = cp_ranges.get((wf, ti))
        current_cp = current_cps.get((wf, cfg))
        first_cp = cp_range['first_cp_idx'] if cp_range else None
        last_cp = cp_range['last_cp_idx'] if cp_range else None
        state = _test_progress_state(current_cp, first_cp, last_cp)

        # 获取 schedule 计划日期
        sched = schedule_dates.get((wf, cfg, ti), {})

        # Build result string based on progress state
        if state == 'complete':
            # Only completed tests show FR
            if sf > 0:
                res = f'{sf}F/{t}T'
            elif stf > 0:
                res = f'{stf}SF/{t}T'
            else:
                res = f'0F/{t}T'
        elif state == 'in_progress':
            # 进行中：显示 schedule 的 plan end date（简短格式），标蓝底
            res = _short_date(sched.get('planned_end_date', '')) or 'Ongoing'
        else:
            # 未开始：显示 schedule 的 plan start date（简短格式），标白底
            res = _short_date(sched.get('planned_start_date', '')) or '—'

        has_fail = (state == 'complete') and (sf > 0 or stf > 0)

        if cfg not in summary[wf]['configs']:
            summary[wf]['configs'][cfg] = {}
        if cfg not in summary[wf]['config_results']:
            summary[wf]['config_results'][cfg] = []

        entry = {
            'result': res,
            'spec': sf,
            'strife': stf,
            'total': t,
            'has_failure': has_fail,
            'failure_sns': [x for x in (r.get('failure_sns_csv') or '').split(',') if x],
            'status': state,
            'current_cp_idx': current_cp,
            'first_cp_idx': first_cp,
            'last_cp_idx': last_cp,
            'planned_start_date': sched.get('planned_start_date', ''),
            'planned_end_date': sched.get('planned_end_date', ''),
        }
        summary[wf]['configs'][cfg][tname] = entry
        indexed_results = summary[wf]['config_results'][cfg]
        if ti >= len(indexed_results):
            indexed_results.extend([None] * (ti - len(indexed_results) + 1))
        indexed_results[ti] = entry

    return jsonify({'summary': list(summary.values())})


# ═══════════════════════════════════════════════════════════════════════
#  API: WF CP Structure
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/wf-cps')
def api_wf_cps():
    """获取 WF 的 CP 结构信息（CP 名称 + check items）。"""
    wf = request.args.get('wf', '').strip()
    cps = get_wf_cps(wf if wf else None)
    return jsonify(cps)


# ═══════════════════════════════════════════════════════════════════════
#  API: FA Tracker Analysis (Issue-focused, separate from db.py)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/fa/overview')
def api_fa_overview():
    """FA Tracker overview: Top 10 Symptom / Location / WF.
    Returns: { topSymptom, topLocation, topWf }
    """
    fa_path = fa_analysis.find_fa_tracker()
    if not fa_path:
        return jsonify({'error': 'FA Tracker not found'}), 404
    issues = fa_analysis.read_fa_tracker(fa_path)
    sample_sizes = fa_analysis.read_sample_sizes(fa_path)
    wf_test_names = fa_analysis.read_wf_test_names(fa_path)
    return jsonify(fa_analysis.compute_overview(issues, sample_sizes, get_wf_names(), wf_test_names))


@app.route('/api/fa/cross')
def api_fa_cross():
    """FA Tracker cross-analysis matrix.
    Query: dim1, dim2 (symptom|location|failed_test|wf|config)
    """
    dim1 = request.args.get('dim1', 'symptom')
    dim2 = request.args.get('dim2', 'location')
    allowed = {'symptom', 'location', 'failed_test', 'wf', 'config'}
    if dim1 not in allowed or dim2 not in allowed or dim1 == dim2:
        return jsonify({'error': 'Invalid dimensions'}), 400

    fa_path = fa_analysis.find_fa_tracker()
    if not fa_path:
        return jsonify({'error': 'FA Tracker not found'}), 404
    issues = fa_analysis.read_fa_tracker(fa_path)
    sample_sizes = fa_analysis.read_sample_sizes(fa_path)
    wf_test_names = fa_analysis.read_wf_test_names(fa_path)
    return jsonify(fa_analysis.compute_cross(issues, sample_sizes, dim1, dim2, wf_test_names))


@app.route('/api/fa/detail')
def api_fa_detail():
    """Filtered FA records for popup display.
    Query: symptom, location, wf, config, failed_test (all optional)
    """
    fa_path = fa_analysis.find_fa_tracker()
    if not fa_path:
        return jsonify({'records': []})
    issues = fa_analysis.read_fa_tracker(fa_path)

    filters = {}
    for key in ('symptom', 'location', 'wf', 'config', 'failed_test'):
        val = request.args.get(key, '')
        if val:
            filters[key] = val

    records = fa_analysis.compute_detail(issues, filters)
    return jsonify({'records': records})


# ═══════════════════════════════════════════════════════════════════════
#  API: FA Tracker (for drill-through)
# ═══════════════════════════════════════════════════════════════════════

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


@app.route('/api/fa/list')
def api_fa_list():
    """Get FA records, optionally filtered by WF or status."""
    wf = request.args.get('wf', '').strip()
    status = request.args.get('status', '').strip()
    
    fa_path = _find_fa_tracker_by_date(None)
    
    if not fa_path:
        return jsonify({'records': [], 'error': 'FA Tracker not found'})
    
    fa_records = read_fa_tracker(fa_path)
    
    # Filter
    config = request.args.get('config', '').strip()
    failed_test = request.args.get('failed_test', '').strip()
    sns = _split_csv_filter(request.args.get('sns', ''))

    if wf:
        target_wf = _normalize_fa_wf(wf)
        fa_records = [f for f in fa_records if _normalize_fa_wf(f.get('WF', '')) == target_wf]
    if config:
        target_config = _normalize_fa_text(config)
        fa_records = [f for f in fa_records if _normalize_fa_text(f.get('Config', '')) == target_config]
    if failed_test:
        target_test = _normalize_fa_text(failed_test)
        fa_records = [f for f in fa_records if _normalize_fa_text(f.get('Failed Test', '')) == target_test]
    if sns:
        fa_records = [f for f in fa_records if str(f.get('SN', '')).strip() in sns]
    if status:
        fa_records = [f for f in fa_records if str(f.get('FA Status', '')).strip() == status]
    
    return jsonify({'records': fa_records, 'count': len(fa_records)})


# ═══════════════════════════════════════════════════════════════════════
#  API: Cell Failures (check-item-level drill-down from Test Summary)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/cell-failures')
def api_cell_failures():
    """Return per-SN, per-CP check-item failure details for a clicked cell."""
    conn = get_conn()
    rid = get_latest_active_report_id(conn)
    conn.close()
    if not rid:
        return jsonify({'failures': []})

    wf = _normalize_fa_wf(request.args.get('wf', ''))
    config = request.args.get('config', '').strip()
    test_idx_str = request.args.get('test_idx', '').strip()
    sns_str = request.args.get('sns', '').strip()

    if not wf or not config or not test_idx_str:
        return jsonify({'failures': []})

    try:
        test_idx = int(test_idx_str)
    except ValueError:
        return jsonify({'failures': []})

    sns = [s.strip() for s in sns_str.split(',') if s.strip()]
    if not sns:
        return jsonify({'failures': []})

    rows = get_cell_failures(rid, wf, config, test_idx, sns)

    # Group: SN → CP → check_item
    result = []
    current_sn = None
    current_cp = None
    sn_entry = None
    cp_entry = None

    for row in rows:
        sn = row['sn']
        cp_idx = row['cp_idx']

        if sn != current_sn:
            current_sn = sn
            current_cp = cp_idx
            sn_entry = {'sn': sn, 'cps': []}
            result.append(sn_entry)
            cp_entry = {'cp_name': row['cp_name'], 'cp_idx': cp_idx, 'check_items': []}
            sn_entry['cps'].append(cp_entry)
        elif cp_idx != current_cp:
            current_cp = cp_idx
            cp_entry = {'cp_name': row['cp_name'], 'cp_idx': cp_idx, 'check_items': []}
            sn_entry['cps'].append(cp_entry)

        cp_entry['check_items'].append({
            'check_item': row['check_item'],
            'raw_value': row['raw_value'],
            'normalized_value': row['normalized_value'],
            'status': row['status'],
            'failure_type': row['failure_type'],
        })

    return jsonify({'failures': result})


# ═══════════════════════════════════════════════════════════════════════
#  API: Daily Issues (cross-referenced from Daily Report + FA Tracker)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/daily/issues')
def api_daily_issues():
    """Get today's defects, cross-referenced between Daily Report DB and FA Tracker."""
    conn = get_conn()

    # 1. Get latest report
    rid = get_latest_active_report_id(conn)
    latest = {'id': rid} if rid else None
    if not latest or not latest['id']:
        conn.close()
        return jsonify({'error': 'No data', 'issues': [], 'consistency': {'is_consistent': True}}), 404
    rid = latest['id']

    rpt = conn.execute("SELECT report_date FROM reports WHERE id = ?", (rid,)).fetchone()
    report_date = rpt['report_date'] if rpt else ''
    
    # Key function for 4-dimension comparison + location with mapping support
    def _key(d, source='daily_report'):
        loc = get_location_canonical(d['location'], source)
        return (d['sn'], d['wf'], d['config'], d['type'], loc)

    def _lifecycle_failure_issues(target_rid):
        """All active failures as of target_rid (for fallback/full list)."""
        rows = conn.execute(
            """SELECT l.sn, l.wf_num, l.config, l.failure_type,
                      l.check_item, l.test_idx, l.cp_idx,
                      c.cp_name, t.test_name
               FROM sn_check_state_history l
               LEFT JOIN current_cp_definitions c
                 ON c.wf_num = l.wf_num AND c.cp_idx = l.cp_idx
               LEFT JOIN current_test_definitions t
                 ON t.wf_num = l.wf_num AND t.test_idx = l.test_idx
               WHERE l.first_report_id <= ?
                 AND (l.closed_before_report_id IS NULL OR l.closed_before_report_id > ?)
                 AND l.failure_type IS NOT NULL
               ORDER BY CAST(l.wf_num AS REAL), l.config, l.sn, l.cp_idx, l.check_item_idx""",
            (target_rid, target_rid),
        ).fetchall()
        issues = []
        seen = set()
        for row in rows:
            item = {
                'sn': str(row['sn'] or '').strip(),
                'wf': row['wf_num'],
                'config': row['config'],
                'type': row['failure_type'] or '',
                'location': row['check_item'] or row['test_name'] or f"Test{(row['test_idx'] or 0) + 1}",
                'failed_cycle': row['cp_name'] or f"CP{(row['cp_idx'] or 0) + 1}",
            }
            key = _key(item)
            if key in seen:
                continue
            seen.add(key)
            issues.append(item)
        return issues

    def _lifecycle_new_failures(target_rid):
        """Only failures first seen in the same report_date as target_rid.

        When a report is re-uploaded, a new report_id is created for the same date.
        Lifecycle rows keep their original first_report_id from the first upload,
        so we match all report_ids sharing the same report_date.
        """
        rows = conn.execute(
            """SELECT l.sn, l.wf_num, l.config, l.failure_type,
                      l.check_item, l.test_idx, l.cp_idx,
                      c.cp_name, t.test_name
               FROM sn_check_state_history l
               LEFT JOIN current_cp_definitions c
                 ON c.wf_num = l.wf_num AND c.cp_idx = l.cp_idx
               LEFT JOIN current_test_definitions t
                 ON t.wf_num = l.wf_num AND t.test_idx = l.test_idx
               WHERE l.first_report_date = (SELECT report_date FROM reports WHERE id = ?)
                 AND l.failure_type IS NOT NULL
               ORDER BY CAST(l.wf_num AS REAL), l.config, l.sn, l.cp_idx, l.check_item_idx""",
            (target_rid,),
        ).fetchall()
        issues = []
        seen = set()
        for row in rows:
            item = {
                'sn': str(row['sn'] or '').strip(),
                'wf': row['wf_num'],
                'config': row['config'],
                'type': row['failure_type'] or '',
                'location': row['check_item'] or row['test_name'] or f"Test{(row['test_idx'] or 0) + 1}",
                'failed_cycle': row['cp_name'] or f"CP{(row['cp_idx'] or 0) + 1}",
            }
            key = _key(item)
            if key in seen:
                continue
            seen.add(key)
            issues.append(item)
        return issues
    
    # Get previous report for diff (Daily Report is cumulative)
    prev_rid = get_previous_active_report_id(conn, rid)
    
    # 2. Get today's NEW failures.
    # Strategy: lifecycle-first — if lifecycle data exists, "new" = first_report_id == current report.
    # Fallback: diff-based (today's failure_details minus yesterday's).
    
    lifecycle_new = _lifecycle_new_failures(rid)
    
    if lifecycle_new is not None and len(lifecycle_new) > 0:
        # Lifecycle data exists and found new failures → use directly
        db_issues = lifecycle_new
    else:
        # Check if lifecycle has ANY data for this report (maybe just no new failures today)
        has_lifecycle = conn.execute(
            """SELECT 1 FROM sn_check_state_history
               WHERE first_report_id <= ?
                 AND (closed_before_report_id IS NULL OR closed_before_report_id > ?)
                 AND failure_type IS NOT NULL
               LIMIT 1""",
            (rid, rid),
        ).fetchone()
        
        if has_lifecycle:
            # Lifecycle exists but no new failures today → empty list
            db_issues = []
        else:
            # No lifecycle data at all → fallback to failure_details diff
            rows = conn.execute(
                """SELECT wf_num, config, test_idx, failure_details
                   FROM wf_results
                   WHERE report_id = ? AND failure_details IS NOT NULL AND failure_details != '[]'""",
                (rid,)
            ).fetchall()
            
            wf_names_map = get_wf_names()
            db_issues = []
            for row in rows:
                wf = row['wf_num']
                cfg = row['config']
                ti = row['test_idx']
                try:
                    details = json.loads(row['failure_details'] or '[]')
                except (json.JSONDecodeError, TypeError):
                    details = []
                
                wf_info = wf_names_map.get(wf, {})
                test_names = wf_info.get('test_names', [])
                fallback_location = test_names[ti] if ti < len(test_names) and test_names[ti] else f'Test{ti + 1}'
                
                for d in details:
                    db_issues.append({
                        'sn': str(d.get('sn', '')).strip(),
                        'wf': wf,
                        'config': cfg,
                        'type': d.get('type', ''),
                        'location': d.get('location', '') or fallback_location,
                        'failed_cycle': d.get('failed_cp', ''),
                    })
            
            # Subtract yesterday's failures (diff-based fallback)
            if prev_rid and db_issues:
                prev_rows = conn.execute(
                    """SELECT wf_num, config, test_idx, failure_details
                       FROM wf_results
                       WHERE report_id = ? AND failure_details IS NOT NULL AND failure_details != '[]'""",
                    (prev_rid,)
                ).fetchall()
                
                yesterday_keys = set()
                for row in prev_rows:
                    pwf = row['wf_num']
                    pcfg = row['config']
                    pti = row['test_idx']
                    try:
                        pdetails = json.loads(row['failure_details'] or '[]')
                    except (json.JSONDecodeError, TypeError):
                        pdetails = []
                    pwf_info = wf_names_map.get(pwf, {})
                    ptest_names = pwf_info.get('test_names', [])
                    pfallback = ptest_names[pti] if pti < len(ptest_names) and ptest_names[pti] else f'Test{pti + 1}'
                    for d in pdetails:
                        yesterday_keys.add(_key({
                            'sn': str(d.get('sn', '')).strip(),
                            'wf': pwf,
                            'config': pcfg,
                            'type': d.get('type', ''),
                            'location': d.get('location', '') or pfallback,
                            'failed_cycle': d.get('failed_cp', ''),
                        }))
                
                db_issues = [d for d in db_issues if _key(d) not in yesterday_keys]

    # 3. Get FA Tracker issues filtered by date
    fa_issues = []
    fa_path = _find_fa_tracker_by_date(report_date)
    if fa_path:
        try:
            all_issues = fa_analysis.read_fa_tracker(fa_path)
            for issue in all_issues:
                # Filter by Open Date
                open_date_raw = issue.get('Open Date', '')
                if open_date_raw:
                    issue_date = _parse_date_value(open_date_raw)
                    if issue_date and issue_date != report_date:
                        continue

                sn = str(issue.get('SN', '')).strip()
                if not sn:
                    continue

                wf_num = _normalize_wf(issue.get('WF', ''))
                cfg = str(issue.get('Config', '')).strip()
                ft = _normalize_failure_type(
                    _fa_field(issue, 'Failure Type')
                )
                loc = str(issue.get('Failed Location', '')).strip()
                failed_cycle = str(issue.get('Failed Cycle Count', '')).strip()
                failed_test = str(issue.get('Failed Test', '')).strip()

                fa_issues.append({
                    'sn': sn,
                    'wf': wf_num,
                    'config': cfg,
                    'type': ft,
                    'location': loc,
                    'failed_cycle': failed_cycle,
                    'failed_test': failed_test,
                    'symptom': str(issue.get('Failure Symptom / Failure Message', '')).strip(),
                    'fa_status': str(issue.get('FA Status', '')).strip(),
                    'fa_num': issue.get('_fa_num', ''),
                })
        except Exception:
            logger.exception("Failed to read FA tracker for daily issues")

    conn.close()

    # 4. Cross-reference by 5-dimension key: (sn, wf, config, type, location) with mapping
    db_map = {_key(d, 'daily_report'): d for d in db_issues}
    fa_map = {_key(f, 'fa_tracker'): f for f in fa_issues}

    matched_keys = set(db_map) & set(fa_map)
    only_db_keys = set(db_map) - set(fa_map)
    only_fa_keys = set(fa_map) - set(db_map)

    issues = []

    for k in matched_keys:
        fa = fa_map[k]
        db = db_map[k]
        issues.append({
            'sn': db['sn'], 'wf': db['wf'], 'config': db['config'],
            'type': db['type'], 'location': fa.get('location', '') or db['location'],
            'failed_test': fa.get('failed_test', ''),
            'failed_cycle': db.get('failed_cycle', '') or fa.get('failed_cycle', ''),
            'symptom': fa.get('symptom', ''),
            'source': 'matched',
            'detail': {
                'daily_report': {
                    'sn': db['sn'], 'wf': db['wf'], 'config': db['config'],
                    'type': db['type'], 'location': db['location'],
                    'failed_cycle': db.get('failed_cycle', ''),
                },
                'fa_tracker': {
                    'sn': fa['sn'], 'wf': fa['wf'], 'config': fa['config'],
                    'type': fa['type'], 'location': fa.get('location', ''),
                    'failed_test': fa.get('failed_test', ''),
                    'failed_cycle': fa.get('failed_cycle', ''),
                    'symptom': fa.get('symptom', ''),
                    'fa_num': fa.get('fa_num', ''),
                    'fa_status': fa.get('fa_status', ''),
                },
            },
        })

    for k in only_db_keys:
        db = db_map[k]
        issues.append({
            'sn': db['sn'], 'wf': db['wf'], 'config': db['config'],
            'type': db['type'], 'location': db['location'],
            'failed_test': '',
            'failed_cycle': db.get('failed_cycle', ''),
            'symptom': '', 'source': 'only_daily_report',
        })

    for k in only_fa_keys:
        fa = fa_map[k]
        issues.append({
            'sn': fa['sn'], 'wf': fa['wf'], 'config': fa['config'],
            'type': fa['type'], 'location': fa['location'],
            'failed_test': fa.get('failed_test', ''),
            'failed_cycle': fa.get('failed_cycle', ''),
            'symptom': fa.get('symptom', ''),
            'source': 'only_fa_tracker',
        })

    return jsonify({
        'report_date': report_date,
        'consistency': {
            'matched': len(matched_keys),
            'only_daily_report': len(only_db_keys),
            'only_fa_tracker': len(only_fa_keys),
            'is_consistent': len(only_db_keys) == 0 and len(only_fa_keys) == 0,
        },
        'issues': sorted(issues, key=lambda x: (x['wf'], x['config'], x['sn'])),
    })


# ═══════════════════════════════════════════════════════════════════════
#  API: Settings / Rawdata / Custom Rules
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/settings/rawdata')
def api_settings_rawdata():
    """List rawdata files and imported report versions for the settings page."""
    files = []
    for fname, path in iter_rawdata_files():
        if fname.startswith('~$'):
            continue
        try:
            stat = os.stat(path)
        except OSError:
            continue
        files.append({
            'path': _rawdata_relpath(path),
            'name': fname,
            'kind': _classify_rawdata_file(fname),
            'date': _rawdata_date(fname),
            'size': stat.st_size,
            'modified_at': datetime.datetime.fromtimestamp(stat.st_mtime, tz=ZoneInfo('Asia/Shanghai')).isoformat(),
        })
    files.sort(key=lambda item: (item.get('date') or '', item['name']), reverse=True)

    conn = get_conn()
    rows = conn.execute(
        """SELECT id, report_date, version, is_active, source_file_name,
                  excel_path, imported_at
           FROM reports
           ORDER BY report_date DESC, version DESC, id DESC"""
    ).fetchall()
    conn.close()

    reports = []
    for row in rows:
        # Convert imported_at from UTC (SQLite CURRENT_TIMESTAMP) to Beijing time (UTC+8)
        imported_at_raw = row['imported_at']
        if imported_at_raw:
            try:
                utc_dt = datetime.datetime.strptime(imported_at_raw, '%Y-%m-%d %H:%M:%S')
                utc_dt = utc_dt.replace(tzinfo=ZoneInfo('UTC'))
                beijing_dt = utc_dt.astimezone(ZoneInfo('Asia/Shanghai'))
                imported_at_raw = beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                pass
        reports.append({
            'id': row['id'],
            'report_date': row['report_date'],
            'version': row['version'],
            'is_active': bool(row['is_active']),
            'source_file_name': row['source_file_name'] or os.path.basename(row['excel_path'] or ''),
            'imported_at': imported_at_raw,
        })

    return jsonify({'files': files, 'reports': reports})


@app.route('/api/settings/rawdata/delete', methods=['POST'])
def api_settings_rawdata_delete():
    data = request.get_json(silent=True) or {}
    relpath = data.get('path')
    try:
        path = _resolve_rawdata_path(relpath)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    if not os.path.isfile(path):
        return jsonify({'error': 'File not found'}), 404

    fname = os.path.basename(path)
    report_date = _rawdata_date(fname)
    os.remove(path)

    deleted_reports = 0
    if data.get('purge_db') and report_date:
        deleted_reports = _delete_report_data_by_date(report_date)

    return jsonify({
        'success': True,
        'deleted': _rawdata_relpath(path),
        'deleted_reports': deleted_reports,
    })


@app.route('/api/settings/rawdata/parse', methods=['POST'])
def api_settings_rawdata_parse():
    data = request.get_json(silent=True) or {}
    try:
        daily_path = _resolve_rawdata_path(data.get('daily_path'))
        fa_rel = data.get('fa_path') or ''
        fa_path = _resolve_rawdata_path(fa_rel) if fa_rel else None
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    daily_name = os.path.basename(daily_path)
    match = REPORT_PATTERN.match(daily_name)
    if not match:
        return jsonify({'success': False, 'error': f'Invalid Daily Report filename: {daily_name}'}), 400
    if fa_path and not FA_PATTERN.match(os.path.basename(fa_path)):
        return jsonify({'success': False, 'error': f'Invalid FA Tracker filename: {os.path.basename(fa_path)}'}), 400

    raw_date = match.group(1)
    report_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    skip_validation = (
        request.args.get('skip_validation', '').lower() in ('1', 'true', 'yes')
        or str(data.get('skip_validation', '')).lower() in ('1', 'true', 'yes')
    )
    _delete_report_data_by_date(report_date)
    result = process_report_file(report_date, daily_path, fa_path=fa_path, skip_validation=skip_validation)
    if result and result.get('validation_failed'):
        return _validation_response(result.get('validation_errors'), 400)
    if not result:
        return jsonify({'success': False, 'error': 'Selected file failed to parse'}), 500

    # Move successfully parsed files to parsed/ folder
    parsed_dir_abs = os.path.abspath(PARSED_DIR)
    if os.path.abspath(os.path.dirname(daily_path)) != parsed_dir_abs:
        shutil.move(daily_path, os.path.join(PARSED_DIR, daily_name))
    if fa_path and os.path.isfile(fa_path):
        if os.path.abspath(os.path.dirname(fa_path)) != parsed_dir_abs:
            shutil.move(fa_path, os.path.join(PARSED_DIR, os.path.basename(fa_path)))

    try:
        compute_auto_predictions()
    except Exception:
        logger.exception("Failed to recompute predictions after manual parse")

    return jsonify({
        'success': True,
        'report_date': result.get('date', report_date),
        'report_id': result.get('report_id'),
        'wf_count': result.get('wfs', 0),
        'daily_path': 'parsed/' + daily_name,
        'fa_path': ('parsed/' + os.path.basename(fa_path)) if fa_path else '',
    })


@app.route('/api/settings/rules')
def api_settings_rules_get():
    return jsonify({'rules': load_rules(), 'defaults': DEFAULT_RULES})


@app.route('/api/settings/rules', methods=['PUT'])
def api_settings_rules_put():
    data = request.get_json(silent=True) or {}
    rules = data.get('rules', data)
    if not isinstance(rules, dict):
        return jsonify({'error': 'Rules must be an object'}), 400
    return jsonify({'rules': save_rules(rules)})


@app.route('/api/settings/rules/reset', methods=['POST'])
def api_settings_rules_reset():
    return jsonify({'rules': save_rules(DEFAULT_RULES)})


# ═══════════════════════════════════════════════════════════════════════
#  Upload
# ═══════════════════════════════════════════════════════════════════════

def _upload_basename(filename):
    return str(filename or '').replace('\\', '/').split('/')[-1].strip()


@app.route('/api/settings/rawdata/upload', methods=['POST'])
def api_settings_rawdata_upload():
    """Upload Daily Report/FA files into rawdata without importing them."""
    daily_file = request.files.get('daily_report')
    if not daily_file or not daily_file.filename:
        return jsonify({'success': False, 'error': 'Missing daily_report file'}), 400

    daily_name = _upload_basename(daily_file.filename)
    if not REPORT_PATTERN.match(daily_name):
        return jsonify({'success': False, 'error': f'Invalid Daily Report filename: {daily_name}'}), 400

    fa_file = request.files.get('fa_tracker')
    fa_name = ''
    if fa_file and fa_file.filename:
        fa_name = _upload_basename(fa_file.filename)
        if not FA_PATTERN.match(fa_name):
            return jsonify({'success': False, 'error': f'Invalid FA Tracker filename: {fa_name}'}), 400

    os.makedirs(RAWDATA_DIR, exist_ok=True)
    daily_path = os.path.join(RAWDATA_DIR, daily_name)
    daily_file.save(daily_path)

    result = {
        'success': True,
        'daily_report': {
            'name': daily_name,
            'path': _rawdata_relpath(daily_path),
            'kind': 'daily_report',
            'date': _rawdata_date(daily_name),
        },
        'fa_tracker': None,
    }

    if fa_file and fa_name:
        fa_path = os.path.join(RAWDATA_DIR, fa_name)
        fa_file.save(fa_path)
        result['fa_tracker'] = {
            'name': fa_name,
            'path': _rawdata_relpath(fa_path),
            'kind': 'fa_tracker',
            'date': _rawdata_date(fa_name),
        }

    return jsonify(result)


@app.route('/api/upload', methods=['POST'])
def upload_report():
    daily_file = request.files.get('daily_report')
    if not daily_file or not daily_file.filename:
        return jsonify({'success': False, 'error': 'Missing daily_report file'}), 400

    daily_name = _upload_basename(daily_file.filename)
    fa_file = request.files.get('fa_tracker')

    # Validate Daily Report filename
    dm = REPORT_PATTERN.match(daily_name)
    if not dm:
        return jsonify({'success': False, 'error': f'Invalid Daily Report filename: {daily_name}'}), 400
    raw_report_date = dm.group(1)
    report_date = f"{raw_report_date[:4]}-{raw_report_date[4:6]}-{raw_report_date[6:]}"

    # Validate FA Tracker filename (optional)
    if fa_file and fa_file.filename:
        fa_name = _upload_basename(fa_file.filename)
        fm = FA_PATTERN.match(fa_name)
        if not fm:
            return jsonify({'success': False, 'error': f'Invalid FA Tracker filename: {fa_name}'}), 400
    else:
        fa_name = ''

    # Save uploaded raw files directly to rawdata/.
    daily_path = os.path.join(RAWDATA_DIR, daily_name)
    daily_file.save(daily_path)

    if fa_file and fa_name:
        fa_path = os.path.join(RAWDATA_DIR, fa_name)
        fa_file.save(fa_path)
    else:
        fa_path = None

    skip_validation = (
        request.args.get('skip_validation', '').lower() in ('1', 'true', 'yes')
    )
    try:
        if not skip_validation:
            validate_daily_report(daily_path, report_date=report_date, source_file_name=daily_name)
    except RawDataValidationError as exc:
        return _validation_response(exc.errors, 400)

    # Overwrite old data for this date
    conn = get_conn()
    old = conn.execute("SELECT id FROM reports WHERE report_date = ?", (report_date,)).fetchall()
    old_ids = [r['id'] for r in old]
    if old_ids:
        p = ','.join('?' * len(old_ids))
        for table in ['wf_results', 'report_stats', 'daily_changes', 'sn_progress',
                      'report_wf_meta', 'report_test_names', 'report_cps',
                      'report_schedule_segments', 'definition_changes']:
            conn.execute(f"DELETE FROM {table} WHERE report_id IN ({p})", old_ids)
        for table in ['sn_cp_results', 'sn_check_results']:
            conn.execute(f"DELETE FROM {table} WHERE report_date = ?", (report_date,))
        # Delete lifecycle rows associated with old reports so they don't conflict on re-import
        conn.execute(
            f"""DELETE FROM sn_check_state_history
                WHERE first_report_id IN ({p})
                   OR last_seen_report_id IN ({p})
                   OR closed_before_report_id IN ({p})""",
            old_ids * 3,
        )
        conn.execute(f"DELETE FROM reports WHERE id IN ({p})", old_ids)
        conn.commit()
    conn.close()

    # Parse
    try:
        result = process_report_file(report_date, daily_path, fa_path=fa_path, skip_validation=skip_validation)
        if result and result.get('validation_failed'):
            return _validation_response(result.get('validation_errors'), 400)
        if not result:
            return jsonify({'success': False, 'error': 'No report file found to process'}), 500

        # Move successfully parsed files to parsed/ folder
        parsed_daily = os.path.join(PARSED_DIR, daily_name)
        shutil.move(daily_path, parsed_daily)
        if fa_path and os.path.isfile(fa_path):
            shutil.move(fa_path, os.path.join(PARSED_DIR, fa_name))

        try:
            compute_auto_predictions()
        except Exception:
            logger.exception("Failed to recompute predictions after upload")

        return jsonify({
            'success': True,
            'report_date': result.get('date', report_date),
            'wf_count': result.get('wfs', 0),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════
#  API: Base File Management
# ═══════════════════════════════════════════════════════════════════════

import base_manager

# Filename keywords → file_type mapping for auto-detection
_BASE_FILE_TYPE_KEYWORDS = [
    (['Serial Numbers', 'sn_mapping'], 'sn_mapping'),
    (['WaterfallCheckpointSchedule', 'checkpoint_schedule'], 'checkpoint_schedule'),
    (['WaterfallTestPlan', 'test_plan'], 'test_plan'),
    (['Test Schedule', 'test_schedule'], 'test_schedule'),
]


def _detect_base_file_type(filename):
    """Detect base file type from filename keywords.

    Returns file_type string or None if unrecognized.
    """
    for keywords, file_type in _BASE_FILE_TYPE_KEYWORDS:
        for kw in keywords:
            if kw.lower() in filename.lower():
                return file_type
    return None


@app.route('/api/base-files', methods=['POST'])
def api_base_files_upload():
    """Upload one or more Base files. Auto-detect type from filename or use file_type field."""
    files = request.files.getlist('files')
    if not files or all(not f.filename for f in files):
        return jsonify({'success': False, 'error': 'No files provided'}), 400

    # Check for explicit file_type in form data
    explicit_file_type = request.form.get('file_type', '').strip()

    results = {}
    errors = []

    for file in files:
        if not file.filename:
            continue

        # Determine file type
        file_type = explicit_file_type or _detect_base_file_type(file.filename)
        if not file_type:
            errors.append(f"Cannot identify file type for: {file.filename}")
            continue

        if file_type not in base_manager.FILE_TYPE_NAMES:
            errors.append(f"Unknown file type '{file_type}' for: {file.filename}")
            continue

        try:
            parsed_summary = base_manager.upload_base_file(file, file_type)
            results[file_type] = parsed_summary
        except (ValueError, Exception) as e:
            errors.append(f"Error parsing {file.filename}: {str(e)}")

    if not results and errors:
        return jsonify({'success': False, 'error': '; '.join(errors)}), 400

    # Build aggregated summary
    parsed = {
        'sn_count': results.get('sn_mapping', {}).get('sn_count', 0),
        'wf_count': (
            results.get('checkpoint_schedule', {}).get('wf_count', 0)
            or results.get('test_plan', {}).get('wf_count', 0)
        ),
        'cp_count': results.get('checkpoint_schedule', {}).get('cp_count', 0),
    }

    response = {'success': True, 'parsed': parsed}
    if errors:
        response['warnings'] = errors
    return jsonify(response)


@app.route('/api/base-files', methods=['GET'])
def api_base_files_list():
    """Return list of uploaded Base files with metadata."""
    files = base_manager.get_base_status()
    return jsonify({'files': files})


@app.route('/api/base-files/<filename>', methods=['DELETE'])
def api_base_files_delete(filename):
    """Delete a Base file by its stored filename."""
    # Find the file in base_file_meta by matching stored_path or file_type
    conn = get_conn()
    try:
        # Try matching by standardized filename in stored_path
        row = conn.execute(
            "SELECT id, file_type, stored_path FROM base_file_meta WHERE stored_path LIKE ?",
            (f'%{filename}%',)
        ).fetchone()

        if not row:
            # Try matching by file_type directly (e.g., 'sn_mapping')
            row = conn.execute(
                "SELECT id, file_type, stored_path FROM base_file_meta WHERE file_type = ?",
                (filename,)
            ).fetchone()

        if not row:
            return jsonify({'success': False, 'error': f'File not found: {filename}'}), 404

        # Delete the physical file
        stored_path = row['stored_path']
        if not os.path.isabs(stored_path):
            stored_path = os.path.join(BASE_DIR, stored_path)
        if os.path.exists(stored_path):
            os.remove(stored_path)

        # Delete metadata from DB
        conn.execute("DELETE FROM base_file_meta WHERE id = ?", (row['id'],))
        conn.commit()
    finally:
        conn.close()

    return jsonify({'success': True})


# ═══════════════════════════════════════════════════════════════════════
#  API: Check Item CSV Import — Generate Daily Report
# ═══════════════════════════════════════════════════════════════════════

import checkitem_generator


@app.route('/api/check-items', methods=['GET'])
def api_check_items():
    """Return the supported check item columns used by generated Daily Reports."""
    return jsonify({'items': list(checkitem_generator.CHECK_ITEMS)})


@app.route('/api/checkitem/generate', methods=['POST'])
def api_checkitem_generate():
    """Generate Daily Report Excel from uploaded CSV files."""
    files = request.files.getlist('files')
    if not files or all(not f.filename for f in files):
        return jsonify({'success': False, 'error': 'No files provided'}), 400

    try:
        excel_bytes, filename, summary = checkitem_generator.generate_daily_report(files)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception("Error generating daily report from CSV")
        return jsonify({'success': False, 'error': f'Internal error: {str(e)}'}), 500

    # Return Excel as downloadable file stream
    output = io.BytesIO(excel_bytes)
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


# ═══════════════════════════════════════════════════════════════════════
#  API: Raw Check Item Records Query
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/raw-records', methods=['GET'])
def api_raw_records():
    """Query raw check item records for a specific SN or unit.

    Query params:
        sn   — serial number (exact match)
        unit — unit number (resolves to SN via SN mapping)
        item — filter by check item type (e.g., FACT, ISB)
        from — start date filter (YYYY-MM-DD), inclusive
        to   — end date filter (YYYY-MM-DD), inclusive

    Returns JSON with SN metadata + records array.
    """
    sn = request.args.get('sn', '').strip()
    unit = request.args.get('unit', '').strip()
    item_filter = request.args.get('item', '').strip()
    date_from = request.args.get('from', '').strip()
    date_to = request.args.get('to', '').strip()

    if not sn and not unit:
        return jsonify({'error': 'Either sn or unit parameter is required'}), 400

    # Load SN mapping for metadata resolution
    sn_data = base_manager.get_sn_mapping_from_db()

    # Resolve unit → SN if needed
    if not sn and unit:
        if not sn_data:
            return jsonify({'error': 'SN mapping not available. Please upload Base files first.'}), 400
        # Find SN by unit_number
        for serial, info in sn_data['sn_mapping'].items():
            if info.get('unit_number') == unit:
                sn = serial
                break
        if not sn:
            return jsonify({'error': f'No SN found for unit number: {unit}'}), 404

    # Get SN metadata
    unit_number = ''
    config = ''
    wf_id = ''
    if sn_data and sn in sn_data['sn_mapping']:
        meta = sn_data['sn_mapping'][sn]
        unit_number = meta.get('unit_number', '')
        config = meta.get('config', '')
        wf_id = meta.get('wf_id', '')

    # Build query
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
        # Include the entire end date (up to end of day)
        sql += " AND end_time <= ?"
        params.append(date_to + ' 23:59:59')

    sql += " ORDER BY end_time DESC"

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    # Format records
    records = []
    for row in rows:
        record = {
            'id': row['id'],
            'end_time': row['end_time'],
            'rel_event': row['rel_event'],
            'effective_cp': row['effective_cp'],
            'item': row['item'],
            'status': row['status'],
            'version': row['version'],
            'station_id': row['station_id'],
            'failing_tests': row['failing_tests'] or None,
            'test_params': None,
        }
        # Parse test_params JSON for FAIL records
        if row['test_params']:
            try:
                record['test_params'] = json.loads(row['test_params'])
            except (json.JSONDecodeError, TypeError):
                record['test_params'] = row['test_params']
        records.append(record)

    return jsonify({
        'sn': sn,
        'unit_number': unit_number,
        'config': config,
        'wf_id': wf_id,
        'records': records,
    })


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("M60 EVT REL Dashboard API Server")
    print("Access: http://localhost:5050")
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5050'))
    app.run(debug=debug, host=host, port=port)
