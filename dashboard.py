"""
M60 EVT REL — Web Dashboard v2
Flask app + SQLite DB for daily snapshots, trends, and comparison.
Usage: python dashboard.py
Access: http://localhost:5050
"""
from flask import Flask, render_template, request, jsonify
import os, sys

sys.path.insert(0, os.path.dirname(__file__))
from engine import analyze, read_test_summary, build_summary_table, build_failure_detail
from fa_matcher import read_fa_tracker, match as fa_match, summary as fa_summary
from db import init_db, save_report, get_changes, get_trend, get_all_reports, get_latest_report, get_report_stats

app = Flask(__name__)

# ── Load & cache data ──────────────────────────────────────────────────

DR = os.path.join(os.path.dirname(__file__), 'data', 'M60 EVT Rel Daily Report_20260508.xlsx')
FA = os.path.join(os.path.dirname(__file__), 'data', 'M60 EVT REL FA Tracker 20260508.xlsx')

print("Loading Daily Report...")
results = analyze(DR)
ts_data, ts_qty, ts_names, _ = read_test_summary(DR)
rows = build_summary_table(results, ts_data)
failures = build_failure_detail(results)

print("Loading FA Tracker...")
fa_records = read_fa_tracker(FA)
fa_matched = fa_match(fa_records, results)
fa_stats = fa_summary(fa_matched)

print("Init DB & save snapshot...")
init_db()
save_report('2026-05-08', results, fa_stats, DR)

# Build SN/Failure index
sn_index = {}
for f in failures:
    sn = f['sn']
    sn_index.setdefault(sn, []).append(f)

fa_sn_index = {}
for f in fa_matched:
    sn = str(f.get('SN', '')).strip()
    fa_sn_index.setdefault(sn, []).append(f)

total_spec = sum(1 for f in failures if f['type'] == 'spec')
total_strife = sum(1 for f in failures if f['type'] == 'strife')
wfs_with_fails = len(set(f['wf'] for f in failures))
changes = get_changes()
new_failures = [c for c in changes if c['change_type'] == 'new_failure']
completed = sum(1 for r in rows if r['is_match'] is True)

print(f"Ready — {len(rows)} entries, {len(failures)} failures, {len(changes)} changes")

# ── Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    wf_f = request.args.get('wf', '').strip()
    cfg_f = request.args.get('cfg', '').strip()
    search = request.args.get('search', '').strip().lower()

    r = rows
    if wf_f: r = [x for x in r if x['wf'] == wf_f]
    if cfg_f: r = [x for x in r if x['cfg'] == cfg_f]
    if search: r = [x for x in r if search in str(x.get('test_name','')).lower()
                    or search in x['wf'] or search in x['cfg'].lower() or search in x['raw'].lower()]

    # Historical trend for overview charts (last 14 reports)
    history = []
    for rep in get_all_reports()[:14]:
        st = get_report_stats(rep['id']) or {}
        history.append({
            'date': rep['report_date'][5:] if len(rep['report_date']) > 5 else rep['report_date'],
            'spec': st.get('total_spec_fails', 0) or 0,
            'strife': st.get('total_strife_fails', 0) or 0,
            'wfs': st.get('wfs_with_fails', 0) or 0,
            'fa_rate': round(st.get('fa_matched', 0) / st.get('fa_total', 1) * 100) if st.get('fa_total') else 0
        })
    history.reverse()

    return render_template('index.html',
        rows=r, total_spec=total_spec, total_strife=total_strife,
        fa_matched=fa_stats['matched'], fa_total=fa_stats['total'],
        wfs_with_fails=wfs_with_fails, changes=changes[:30],
        new_failure_count=len(new_failures), history=history)


@app.route('/wf/<wfid>')
def wf_detail(wfid):
    if wfid not in results:
        return f"WF{wfid} not found", 404

    wf_data = results[wfid]
    wf_ts = ts_names.get(wfid, [])
    wf_fails = [f for f in failures if f['wf'] == wfid]
    wf_fa = [f for f in fa_matched if str(f.get('WF','')).strip() == wfid]
    wf_rows = [r for r in rows if r['wf'] == wfid]

    return render_template('wf.html', wfid=wfid, results=wf_data, ts_names=wf_ts,
                          failures=wf_fails, fa_records=wf_fa, wf_rows=wf_rows)


@app.route('/wf/<wfid>/trend')
def wf_trend(wfid):
    """Render a trend chart page for a specific WF."""
    cfg = request.args.get('cfg', 'R1FNF')
    ti = int(request.args.get('test', 0))
    data = get_trend(wfid, cfg, ti, limit=20)
    return render_template('trend.html', wfid=wfid, cfg=cfg, ti=ti,
                          trend_data=data, ts_names=ts_names.get(wfid, []))


@app.route('/api/trend/<wfid>/<cfg>/<ti>')
def api_trend(wfid, cfg, ti):
    """JSON API for trend chart data."""
    data = get_trend(wfid, cfg, int(ti), limit=20)
    dates = [r['report_date'] for r in data]
    spec = [r['spec_fail_count'] for r in data]
    strife = [r['strife_fail_count'] for r in data]
    total = [r['total_units'] for r in data]
    return jsonify({'dates': dates, 'spec': spec, 'strife': strife, 'total': total})


@app.route('/fa')
def fa_view():
    status_f = request.args.get('status', '').strip()
    wf_f = request.args.get('wf', '').strip()

    fas = fa_matched
    if status_f:
        fas = [f for f in fas if str(f.get('FA Status','')).strip() == status_f]
    if wf_f:
        fas = [f for f in fas if str(f.get('WF','')).strip() == wf_f]

    return render_template('fa.html', fas=fas, fa_stats=fa_stats)


@app.route('/sn/<sn>')
def sn_lookup(sn):
    return render_template('sn.html', sn=sn,
                          failures=sn_index.get(sn, []),
                          fa_records=fa_sn_index.get(sn, []))


@app.route('/api/stats')
def api_stats():
    return jsonify({
        'total_entries': len(rows), 'total_failures': len(failures),
        'spec_failures': total_spec, 'strife_failures': total_strife,
        'fa_matched': fa_stats['matched'], 'fa_total': fa_stats['total'],
        'wfs_with_fails': wfs_with_fails, 'changes': len(changes),
        'new_failures': len(new_failures), 'completed_matched': completed,
    })


@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip().lower()
    if not q: return jsonify([])
    out = []
    for sn, fails in sn_index.items():
        if q in sn.lower():
            out.append({'type': 'sn', 'id': sn, 'label': f'SN: {sn} ({len(fails)} failures)'})
    for wfn in ts_names:
        if q in wfn:
            out.append({'type': 'wf', 'id': wfn, 'label': f'WF{wfn}'})
    return jsonify(out[:20])


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5050)
