"""
M60 EVT REL — Dashboard API Server
Enhanced Flask backend with progress tracking, predictions, and analytics.
Usage: python backend/api.py
Access: http://localhost:5050
"""
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os, sys, json, io, csv, datetime, re, logging

sys.path.insert(0, os.path.dirname(__file__))
from app_paths import RAWDATA_DIR, UPLOAD_DIR, ensure_runtime_dirs, iter_rawdata_files, find_rawdata_file
from engine import analyze, build_summary_table, build_failure_detail, extract_test_schedule_segments
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
    wf_sort_key, get_wf_names, get_wf_cps, get_wf_config_progress_rows,
    get_wf_config_progress_from_lifecycle,
    get_sn_fact_history, get_sn_lifecycle_history, get_sn_check_details,
    get_latest_wf_config_progress, get_failure_rate_stats_from_facts,
    build_failure_rate_stats_from_facts,
    get_latest_active_report_id, get_previous_active_report_id,
    get_cell_failures, get_report_schedule_segments, save_report_schedule_segments,
    get_current_schedule_segments, save_current_schedule_segments,
    get_report_test_names, get_current_wf_definitions, get_current_test_definitions,
)
from processor import process_newest, compute_auto_predictions, REPORT_PATTERN, FA_PATTERN

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
VUE_STATIC = os.path.join(BASE_DIR, 'static')
VUE_INDEX = os.path.join(VUE_STATIC, 'index.html')

app = Flask(__name__, static_folder=VUE_STATIC, static_url_path='')
DATA_DIR = RAWDATA_DIR
logger = logging.getLogger(__name__)

# ── Init ────────────────────────────────────────────────────────────────
ensure_runtime_dirs()
init_db()
init_categories()

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
        """SELECT id, report_date, version FROM reports
           WHERE is_active = 1
           ORDER BY report_date DESC, version DESC
           LIMIT 1"""
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'version': 'empty'})
    return jsonify({
        'version': f"{row['report_date']}-r{row['id']}-v{row['version']}"
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
    rpt = conn.execute("SELECT report_date, source_file_name FROM reports WHERE id = ?", (rid,)).fetchone()
    report_date = rpt['report_date'] if rpt else ''
    
    project_name = 'M60 EVT REL'
    if rpt and rpt['source_file_name']:
        import re
        m = re.match(r'^(.*?)\s*Daily Report_', rpt['source_file_name'], re.IGNORECASE)
        if m:
            project_name = m.group(1).upper()
    
    # Historical trend data
    reports = conn.execute("SELECT id, report_date FROM reports ORDER BY id ASC").fetchall()
    trend_data = []
    for r in reports:
        stats = conn.execute(
            "SELECT total_spec_fails, total_strife_fails FROM report_stats WHERE report_id=?",
            (r['id'],)
        ).fetchone()
        if stats:
            trend_data.append({
                'date': r['report_date'],
                'spec': stats['total_spec_fails'] or 0,
                'strife': stats['total_strife_fails'] or 0,
            })
    
    conn.close()
    
    return jsonify({
        'project_name': project_name,
        'report_date': report_date,
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

def _schedule_wf_sort_key(wf_num):
    try:
        return [int(part) for part in str(wf_num).split('.')]
    except ValueError:
        return [9999, str(wf_num)]


def _find_report_excel_path(report):
    candidates = []
    if report and report.get('excel_path'):
        candidates.append(report['excel_path'])
    if report and report.get('source_file_name'):
        candidates.append(os.path.join(DATA_DIR, report['source_file_name']))
        candidates.append(find_rawdata_file(report['source_file_name']))
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _load_or_build_schedule_segments(conn, report):
    # Try current schedule first
    segments = get_current_schedule_segments(conn)
    if segments:
        return segments

    # Fall back to old report_schedule_segments lazy-load logic
    report_id = report['id']
    segments = get_report_schedule_segments(conn, report_id)
    if segments:
        return segments

    excel_path = _find_report_excel_path(report)
    if not excel_path:
        return []

    test_names = get_report_test_names(conn, report_id)
    cp_rows = conn.execute(
        """SELECT wf_num, cp_idx, cp_name, test_idx, check_items
           FROM report_cps
           WHERE report_id = ?
           ORDER BY CAST(wf_num AS REAL), cp_idx""",
        (report_id,),
    ).fetchall()
    cps_by_wf = {}
    for row in cp_rows:
        try:
            check_items = json.loads(row.get('check_items') or '[]')
        except (TypeError, json.JSONDecodeError):
            check_items = []
        cps_by_wf.setdefault(row['wf_num'], []).append({
            'cp_idx': row['cp_idx'],
            'cp_name': row['cp_name'],
            'test_idx': row['test_idx'],
            'check_items': check_items,
        })

    segments = extract_test_schedule_segments(excel_path, test_names, cps_by_wf)
    save_report_schedule_segments(conn, report_id, segments)
    # Also save to current schedule on first build
    save_current_schedule_segments(conn, report_id, segments)
    conn.commit()
    return get_report_schedule_segments(conn, report_id)


@app.route('/api/schedule')
def api_schedule():
    conn = get_conn()
    try:
        report = conn.execute(
            """SELECT * FROM reports
               WHERE is_active = 1
               ORDER BY report_date DESC, version DESC
               LIMIT 1"""
        ).fetchone()
        if not report:
            return jsonify({'report_id': None, 'report_date': None, 'segments': []})

        segments = [
            segment for segment in _load_or_build_schedule_segments(conn, report)
            if segment['wf_num'] not in {'43', '44'}
        ]
        wf_meta = get_wf_names()
        cp_rows = conn.execute(
            """SELECT wf_num, cp_idx, cp_name, test_idx
               FROM report_cps
               WHERE report_id = ?
               ORDER BY CAST(wf_num AS REAL), cp_idx""",
            (report['id'],),
        ).fetchall()
        cps_by_key = {}
        for row in cp_rows:
            if row['wf_num'] in {'43', '44'}:
                continue
            key = (row['wf_num'], row['test_idx'])
            cps_by_key.setdefault(key, []).append({
                'cp_idx': row['cp_idx'],
                'cp_name': row['cp_name'],
            })
        progress_by_key = {}
        progress_rows = get_wf_config_progress_from_lifecycle(conn, report['id'])
        if not progress_rows:
            progress_rows = get_wf_config_progress_rows(conn, report['id'])
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

        payload_segments = []
        for segment in segments:
            wf_meta_value = wf_meta.get(segment['wf_num'], '')
            if isinstance(wf_meta_value, dict):
                wf_meta_value = wf_meta_value.get('name', '')
            progress = progress_by_key.get((_normalize_wf(segment['wf_num']), segment['config']), {})
            payload_segments.append({
                'wf_num': segment['wf_num'],
                'wf_name': wf_meta_value,
                'config': segment['config'],
                'test_idx': segment['test_idx'],
                'test_name': segment['test_name'],
                'schedule_test_item': segment.get('schedule_test_item', ''),
                'planned_start_date': segment['planned_start_date'],
                'planned_end_date': segment['planned_end_date'],
                'confidence': segment.get('confidence', ''),
                'inference_reason': segment.get('inference_reason', ''),
                'marker_labels': segment.get('marker_labels', []),
                'cps': cps_by_key.get((segment['wf_num'], segment['test_idx']), []),
                'current_cp_idx': progress.get('current_cp_idx'),
                'current_cp_name': progress.get('current_cp_name', ''),
                'total_cps': progress.get('total_cps', 0),
                'sn_count': progress.get('sn_count', 0),
            })

        payload_segments.sort(key=lambda row: (
            _schedule_wf_sort_key(row['wf_num']),
            row['config'],
            row['test_idx'],
        ))
        return jsonify({
            'report_id': report['id'],
            'report_date': report['report_date'],
            'segments': payload_segments,
        })
    finally:
        conn.close()


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
            'pct': round((cp_idx + 1) / total_cps * 100, 1) if total_cps else 0,
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
    """Search SNs by partial match."""
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])
    
    conn = get_conn()
    # Try lifecycle table first
    rows = conn.execute(
        "SELECT DISTINCT sn FROM sn_check_state_history WHERE sn LIKE ? ORDER BY sn LIMIT 30",
        (f'%{q}%',)
    ).fetchall()
    if not rows:
        # Fall back to old tables
        rows = conn.execute(
            "SELECT DISTINCT sn FROM sn_cp_results WHERE sn LIKE ? ORDER BY sn LIMIT 30",
            (f'%{q}%',)
        ).fetchall()
    if not rows:
        rows = conn.execute(
            "SELECT DISTINCT sn FROM sn_progress WHERE sn LIKE ? LIMIT 30",
            (f'%{q}%',)
        ).fetchall()
    conn.close()
    
    return jsonify([r['sn'] for r in rows])


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
           ),
           cp_test_ranges AS (
               SELECT wf_num, test_idx, MIN(cp_idx) AS first_cp, MAX(cp_idx) AS last_cp
               FROM current_cp_definitions
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
    
    # Key function for 5-dimension comparison (cycle is display-only)
    def _key(d):
        return (d['sn'], d['wf'], d['config'], d['type'], d['location'])

    def _lifecycle_failure_issues(target_rid):
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
    
    # Get previous report for diff (Daily Report is cumulative)
    prev_rid = get_previous_active_report_id(conn, rid)
    
    # 2. Get today's failure_details from DB
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

    if not db_issues:
        db_issues = _lifecycle_failure_issues(rid)
    
    # 2b. Filter to only NEW failures (not present in previous report)
    if prev_rid:
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

        if not yesterday_keys:
            yesterday_keys = {_key(item) for item in _lifecycle_failure_issues(prev_rid)}
        
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

    # 4. Cross-reference by 5-dimension key: (sn, wf, config, type, location)
    db_map = {_key(d): d for d in db_issues}
    fa_map = {_key(f): f for f in fa_issues}

    matched_keys = set(db_map) & set(fa_map)
    only_db_keys = set(db_map) - set(fa_map)
    only_fa_keys = set(fa_map) - set(db_map)

    issues = []

    for k in matched_keys:
        fa = fa_map[k]
        db = db_map[k]
        issues.append({
            'sn': db['sn'], 'wf': db['wf'], 'config': db['config'],
            'type': db['type'], 'location': db['location'],
            'failed_test': fa.get('failed_test', ''),
            'failed_cycle': db.get('failed_cycle', '') or fa.get('failed_cycle', ''),
            'symptom': fa.get('symptom', ''),
            'source': 'matched',
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
#  Upload
# ═══════════════════════════════════════════════════════════════════════

def _upload_basename(filename):
    return str(filename or '').replace('\\', '/').split('/')[-1].strip()


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
    report_date = dm.group(1)

    # Validate FA Tracker filename (optional)
    if fa_file and fa_file.filename:
        fa_name = _upload_basename(fa_file.filename)
        fm = FA_PATTERN.match(fa_name)
        if not fm:
            return jsonify({'success': False, 'error': f'Invalid FA Tracker filename: {fa_name}'}), 400
    else:
        fa_name = ''

    # Save uploaded raw files by report date under rawdata/uploads/.
    upload_date = f"{report_date[:4]}-{report_date[4:6]}-{report_date[6:]}"
    upload_dir = os.path.join(UPLOAD_DIR, upload_date)
    os.makedirs(upload_dir, exist_ok=True)

    daily_path = os.path.join(upload_dir, daily_name)
    daily_file.save(daily_path)

    if fa_file and fa_name:
        fa_path = os.path.join(upload_dir, fa_name)
        fa_file.save(fa_path)

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
        # Close lifecycle rows introduced by old reports so they don't leak into the new import
        conn.execute(
            f"UPDATE sn_check_state_history SET closed_before_report_id = first_report_id, closed_before_report_date = ? WHERE first_report_id IN ({p})",
            (report_date,),
        )
        conn.execute(f"DELETE FROM reports WHERE id IN ({p})", old_ids)
        conn.commit()
    conn.close()

    # Parse
    try:
        result = process_newest()
        if not result:
            return jsonify({'success': False, 'error': 'No report file found to process'}), 500

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
#  Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("M60 EVT REL Dashboard API Server")
    print("Access: http://localhost:5050")
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5050'))
    app.run(debug=debug, host=host, port=port)
