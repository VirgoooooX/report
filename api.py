"""
M60 EVT REL — Dashboard API Server
Enhanced Flask backend with progress tracking, predictions, and analytics.
Usage: python api.py
Access: http://localhost:5050
"""
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os, sys, json, io, csv, datetime, re

sys.path.insert(0, os.path.dirname(__file__))
from engine import analyze, build_summary_table, build_failure_detail
from fa_matcher import read_fa_tracker, match as fa_match, summary as fa_summary
import fa_analysis
from db import (
    init_db, save_report, save_sn_progress, get_changes, get_trend,
    get_all_reports, get_latest_report, get_report_stats, get_conn,
    get_sn_history, get_daily_changes_by_cp, get_completion_stats,
    get_failure_rate_stats, get_predictions, update_prediction,
    init_categories, get_category_wfs, export_sn_records,
    wf_sort_key, get_wf_names, get_wf_cps, get_wf_config_progress_rows
)

BASE_DIR = os.path.dirname(__file__)
VUE_STATIC = os.path.join(BASE_DIR, 'static')
VUE_INDEX = os.path.join(VUE_STATIC, 'index.html')

app = Flask(__name__, static_folder=VUE_STATIC, static_url_path='')
DATA_DIR = os.path.join(BASE_DIR, 'data')

# ── Init ────────────────────────────────────────────────────────────────
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
    for fname in os.listdir(DATA_DIR):
        if 'FA Tracker' in fname and fname.endswith('.xlsx') and not fname.startswith('~$'):
            m = re.search(r'(\d{8})', fname)
            if m:
                raw = m.group(1)
                df = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
                fas.append((df, os.path.join(DATA_DIR, fname)))
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
#  API: Dashboard Overview
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/dashboard/overview')
def api_overview():
    """Dashboard overview: completion, daily updates, failure summary."""
    conn = get_conn()
    latest = conn.execute("SELECT MAX(id) as id FROM reports").fetchone()
    if not latest or not latest['id']:
        conn.close()
        return jsonify({'error': 'No data'}), 404
    rid = latest['id']
    
    # Completion stats
    completion = get_completion_stats(rid)
    
    # Daily CP changes — 比较前后两天的 max(current_cp_idx) per WF+Config
    prev = conn.execute("SELECT id FROM reports WHERE id < ? ORDER BY id DESC LIMIT 1", (rid,)).fetchone()
    if prev:
        prev_rid = prev['id']
        # 今天每个 WF+Config 的最远 CP
        today_max = conn.execute(
            """SELECT wf_num, config, MAX(current_cp_idx) as max_cp_idx
               FROM sn_progress WHERE report_id = ? GROUP BY wf_num, config""", (rid,)
        ).fetchall()
        today_map = {(r['wf_num'], r['config']): r['max_cp_idx'] for r in today_max}
        # 昨天每个 WF+Config 的最远 CP
        yesterday_max = conn.execute(
            """SELECT wf_num, config, MAX(current_cp_idx) as max_cp_idx
               FROM sn_progress WHERE report_id = ? GROUP BY wf_num, config""", (prev_rid,)
        ).fetchall()
        yesterday_map = {(r['wf_num'], r['config']): r['max_cp_idx'] for r in yesterday_max}
    else:
        today_map = {}
        yesterday_map = {}
    
    # 获取今天各 WF+Config 的 latest CP 信息
    cp_info_rows = get_wf_config_progress_rows(conn, rid)
    
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
                'total_cps': row['total_cps'] or 0,
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
    
    # Failure stats
    fail_stats = get_failure_rate_stats(rid)
    
    # Latest report date
    rpt = conn.execute("SELECT report_date FROM reports WHERE id = ?", (rid,)).fetchone()
    report_date = rpt['report_date'] if rpt else ''
    
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
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
    stats = get_completion_stats(rid)
    conn.close()
    return jsonify(stats.get('by_config', {}))


@app.route('/api/completion/by-category')
def api_completion_category():
    conn = get_conn()
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
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
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
    
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
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
    
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
    data = request.get_json()
    if not data or 'wf_nums' not in data:
        return jsonify({'error': 'Missing wf_nums'}), 400
    wf_nums_str = ','.join(data['wf_nums'])
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
    data = request.get_json()
    if not data or 'wf_num' not in data:
        return jsonify({'error': 'Missing wf_num'}), 400
    wf_num = data['wf_num'].strip()
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
    data = request.get_json()
    if not data or 'wf_num' not in data:
        return jsonify({'error': 'Missing wf_num'}), 400
    wf_num = data['wf_num'].strip()
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
    name = data['name'].strip()
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
        rpt = conn.execute("SELECT MAX(id) as id FROM reports").fetchone()
    
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
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
    stats = get_failure_rate_stats(rid)
    conn.close()
    return jsonify(stats)


@app.route('/api/failures/top')
def api_failure_top():
    """Top N failure items by dimension."""
    limit = request.args.get('limit', 10, type=int)
    by_dim = request.args.get('by', 'test')  # config, wf, test
    
    conn = get_conn()
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
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
    
    items.sort(key=lambda x: x.get('total_rate', 0), reverse=True)
    
    return jsonify({'dimension': by_dim, 'items': items[:limit]})


@app.route('/api/failures/wf/<wfn>')
def api_wf_failures(wfn):
    """Per-WF failure detail with per-SN information."""
    conn = get_conn()
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
    
    rows = conn.execute(
        """SELECT wf_num, config, test_idx, spec_fail_count, strife_fail_count,
                  total_units, failure_sns
           FROM wf_results WHERE report_id = ? AND wf_num = ?""",
        (rid, wfn)
    ).fetchall()
    
    # Also get per-SN CP detail for failures
    sn_rows = conn.execute(
        """SELECT sn, config, current_cp_idx, current_cp_name, cp_results_json
           FROM sn_progress WHERE report_id = ? AND wf_num = ?""",
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
#  API: SN Lookup
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/sn/<sn>')
def api_sn_lookup(sn):
    """Get all test records for an SN across all dates."""
    history = get_sn_history(sn)
    
    if not history:
        return jsonify({'sn': sn, 'records': [], 'message': 'SN not found'}), 404
    
    # Group by WF for cleaner display
    by_wf = {}
    for h in history:
        wf = h['wf_num']
        if wf not in by_wf:
            by_wf[wf] = {
                'wf': wf,
                'history': [],
                'latest': None,
            }
        entry = {
            'date': h['report_date'],
            'config': h['config'],
            'unit': h.get('unit_num', ''),
            'current_cp': h['current_cp_name'],
            'cp_idx': h['current_cp_idx'],
            'total_cps': h['total_cps'],
        }
        by_wf[wf]['history'].append(entry)
        by_wf[wf]['latest'] = entry
    
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
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
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

@app.route('/api/test-summary')
def api_test_summary():
    """Generate a test summary table similar to Daily Report's Test Summary."""
    conn = get_conn()
    rid = conn.execute("SELECT MAX(id) FROM reports").fetchone()['MAX(id)']
    report_row = conn.execute(
        "SELECT ts_test_names FROM reports WHERE id = ?",
        (rid,)
    ).fetchone()

    rows = conn.execute(
        """SELECT wf_num, config, test_idx, total_units, spec_fail_count,
                  strife_fail_count, failure_sns
           FROM wf_results WHERE report_id = ?
           ORDER BY CAST(wf_num AS REAL), config, test_idx""",
        (rid,)
    ).fetchall()
    conn.close()

    # Load real test names from wf_names table
    wf_names = get_wf_names()
    report_test_names = {}
    if report_row and report_row.get('ts_test_names'):
        try:
            report_test_names = json.loads(report_row['ts_test_names']) or {}
        except Exception:
            report_test_names = {}

    summary = {}
    for r in rows:
        wf = r['wf_num']
        # Prefer per-report TS names; fallback to wf_names metadata table
        wf_real_names = report_test_names.get(wf) or wf_names.get(wf, {}).get('test_names', [])
        if wf not in summary:
            summary[wf] = {
                'wf': wf,
                'wf_name': wf_names.get(wf, {}).get('name', ''),
                'configs': {},
                'test_names': list(wf_real_names),
            }

        cfg = r['config']
        ti = r['test_idx']
        sf = r['spec_fail_count']
        stf = r['strife_fail_count']
        t = r['total_units']

        # Use real test name if available, fallback to TestN
        tname = wf_real_names[ti] if ti < len(wf_real_names) else f'Test{ti+1}'

        # Ensure test_names array covers this index
        tn_list = summary[wf]['test_names']
        if ti >= len(tn_list):
            tn_list.extend([''] * (ti - len(tn_list) + 1))
        if not tn_list[ti]:
            tn_list[ti] = tname

        # Build result string: xF/nT or xSF/nT or 0F/nT
        if sf > 0:
            res = f'{sf}F/{t}T'
        elif stf > 0:
            res = f'{stf}SF/{t}T'
        else:
            res = f'0F/{t}T'

        has_fail = sf > 0 or stf > 0

        if cfg not in summary[wf]['configs']:
            summary[wf]['configs'][cfg] = {}

        summary[wf]['configs'][cfg][tname] = {
            'result': res,
            'spec': sf,
            'strife': stf,
            'total': t,
            'has_failure': has_fail,
            'failure_sns': json.loads(r['failure_sns']) if r['failure_sns'] else [],
        }

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

@app.route('/api/fa/list')
def api_fa_list():
    """Get FA records, optionally filtered by WF or status."""
    wf = request.args.get('wf', '').strip()
    status = request.args.get('status', '').strip()
    
    fa_path = None
    for fname in os.listdir(DATA_DIR):
        if 'FA Tracker' in fname:
            fa_path = os.path.join(DATA_DIR, fname)
            break
    
    if not fa_path:
        return jsonify({'records': [], 'error': 'FA Tracker not found'})
    
    fa_records = read_fa_tracker(fa_path)
    
    # Filter
    if wf:
        fa_records = [f for f in fa_records if str(f.get('WF', '')).strip() == wf]
    if status:
        fa_records = [f for f in fa_records if str(f.get('FA Status', '')).strip() == status]
    
    return jsonify({'records': fa_records, 'count': len(fa_records)})


# ═══════════════════════════════════════════════════════════════════════
#  API: Daily Issues (cross-referenced from Daily Report + FA Tracker)
# ═══════════════════════════════════════════════════════════════════════

@app.route('/api/daily/issues')
def api_daily_issues():
    """Get today's defects, cross-referenced between Daily Report DB and FA Tracker."""
    conn = get_conn()

    # 1. Get latest report
    latest = conn.execute("SELECT MAX(id) as id FROM reports").fetchone()
    if not latest or not latest['id']:
        conn.close()
        return jsonify({'error': 'No data', 'issues': [], 'consistency': {'is_consistent': True}}), 404
    rid = latest['id']

    rpt = conn.execute("SELECT report_date FROM reports WHERE id = ?", (rid,)).fetchone()
    report_date = rpt['report_date'] if rpt else ''
    
    # Key function for 5-dimension comparison (cycle is display-only)
    def _key(d):
        return (d['sn'], d['wf'], d['config'], d['type'], d['location'])
    
    # Get previous report for diff (Daily Report is cumulative)
    prev = conn.execute("SELECT id FROM reports WHERE id < ? ORDER BY id DESC LIMIT 1", (rid,)).fetchone()
    prev_rid = prev['id'] if prev else None
    
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
            except:
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
            pass  # FA Tracker read failed; db_issues will still be returned

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
#  Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("M60 EVT REL Dashboard API Server")
    print("Access: http://localhost:5050")
    app.run(debug=True, host='0.0.0.0', port=5050)
