"""
M60 EVT REL — Batch Processor
Processes all Daily Reports, stores data in SQLite.
Usage: python processor.py [--rebuild]

功能：
  - process_all()     处理所有 Daily Report，重建完整数据库
  - process_newest()  处理最新的 Daily Report（增量更新）
  - compute_auto_predictions()  自动计算所有 WF/Config/Test 的预测完成时间
"""
import os
import sys
import re
import datetime
import math
import statistics
import argparse
import logging

sys.path.insert(0, os.path.dirname(__file__))
from engine import analyze, extract_sn_progress, extract_sn_fact_rows, build_failure_detail, read_test_schedule, read_test_summary, extract_all_cp_structures, attach_test_idx_to_cps, extract_test_schedule_segments
from fa_matcher import read_fa_tracker, match as fa_match, summary as fa_summary
from db import (
    init_db, save_report, save_sn_progress, save_wf_names, save_wf_cps, get_completion_stats,
    get_failure_rate_stats, get_daily_changes_by_cp,
    save_predictions, init_categories, get_conn,
    create_report_version, save_report_wf_meta, save_report_test_names,
    save_report_cps, save_report_schedule_segments, save_sn_cp_results, save_sn_check_state_history,
    detect_definition_changes, save_definition_changes
)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
REPORT_PATTERN = re.compile(r'M60 EVT Rel Daily Report_(\d{8})\.xlsx$')
FA_PATTERN = re.compile(r'M60 EVT REL FA Tracker (\d{8})\.xlsx$')
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Helper — 文件扫描
# ═══════════════════════════════════════════════════════════════════════

def _find_daily_reports():
    """扫描 data/ 下所有 Daily Report，返回按日期升序的 (date_str, filepath) 列表。"""
    reports = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith('~$'): continue  # skip Office temp files
        m = REPORT_PATTERN.search(fname)
        if m:
            raw = m.group(1)
            date_fmt = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
            reports.append((date_fmt, os.path.join(DATA_DIR, fname)))
    reports.sort(key=lambda x: x[0])
    return reports


def _find_fa_tracker(date_str=None):
    """
    查找 FA Tracker 文件。
    如果指定日期，优先找对应日期的文件；找不到则使用最新的 FA Tracker。
    返回 (filepath, date_str) 或 (None, None)。
    """
    fas = []
    for fname in os.listdir(DATA_DIR):
        m = FA_PATTERN.search(fname)
        if m:
            raw = m.group(1)
            df = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
            fas.append((df, os.path.join(DATA_DIR, fname)))
    if not fas:
        return None, None
    fas.sort(key=lambda x: x[0])
    # 精确匹配
    if date_str:
        for d, fp in fas:
            if d == date_str:
                return fp, d
    # 返回最新的
    return fas[-1][1], fas[-1][0]


def save_report_definitions(conn, report_id, daily_path):
    wf_names = read_test_schedule(daily_path)
    _, _, ts_test_names, _ = read_test_summary(daily_path)
    cp_structures = extract_all_cp_structures(daily_path)
    mapped_cps = attach_test_idx_to_cps(cp_structures, ts_test_names)
    schedule_segments = extract_test_schedule_segments(daily_path, ts_test_names, mapped_cps)

    save_report_wf_meta(conn, report_id, wf_names)
    save_report_test_names(conn, report_id, ts_test_names)
    save_report_cps(conn, report_id, mapped_cps)
    save_report_schedule_segments(conn, report_id, schedule_segments)

    # Keep latest/global caches for existing category and compatibility views.
    if wf_names:
        save_wf_names(wf_names, ts_test_names, conn=conn)
    for wfn, cp_list in cp_structures.items():
        save_wf_cps(wfn, cp_list, conn=conn)

    return wf_names, ts_test_names, mapped_cps, schedule_segments


# ═══════════════════════════════════════════════════════════════════════
#  process_all — 完整批次处理
# ═══════════════════════════════════════════════════════════════════════

def process_all(rebuild=False):
    """处理所有 Daily Report，重建完整数据库。

    Args:
        rebuild: 如果为 True，会删除已有数据库并重建表。

    Returns:
        dict: 处理统计信息。
    """
    # 1. 扫描所有 Daily Report
    reports = _find_daily_reports()
    if not reports:
        print("ERROR: No Daily Report files found")
        return {'files_processed': 0, 'total_wfs': 0,
                'total_sn_records': 0, 'total_failures': 0}

        print(f"[OK] Found {len(reports)} Daily Report files")
    if rebuild:
        print("[OK] Rebuilding database...")

    # 2. 初始化 DB（可选重建）
    init_db(drop_all=rebuild)
    init_categories()

    # 从第一个 Daily Report 读取 WF 名称、TS 测试名和 CP 结构
    if reports:
        first_path = reports[0][1]
        try:
            wf_names = read_test_schedule(first_path)
            if wf_names:
                _, _, ts_test_names, _ = read_test_summary(first_path)
                save_wf_names(wf_names, ts_test_names)
                # Extract and save CP structures
                all_cps = extract_all_cp_structures(first_path)
                cps_saved = 0
                for wfn, cp_list in all_cps.items():
                    save_wf_cps(wfn, cp_list)
                    cps_saved += len(cp_list)
                print(f"[OK] Loaded {len(wf_names)} WF names + {cps_saved} CP records from Test Schedule/TS")
        except Exception as e:
            print(f"[WARN] Could not read WF names: {e}")

    # 3. 按日期升序处理每个文件
    stats = {
        'files_processed': 0,
        'total_wf_set': set(),
        'total_sn_records': 0,
        'total_failures': 0,
        'total_spec_fails': 0,
        'total_strife_fails': 0,
    }

    for i, (date_str, filepath) in enumerate(reports):
        fname = os.path.basename(filepath)
        print(f"\n[{i + 1}/{len(reports)}] 处理: {fname}  (日期: {date_str})")

        try:
            # a. engine.analyze()
            print("   [+] engine.analyze() ...", end=' ')
            results = analyze(filepath)
            if not results:
                print("无 WF 结果，跳过")
                continue
            wf_count = len(results)
            print(f"{wf_count} 个 WF")

            # b. engine.extract_sn_progress()
            print("   [+] engine.extract_sn_progress() ...", end=' ')
            progress_data = extract_sn_progress(filepath)
            sn_count = sum(
                len(entries)
                for cfgs in progress_data.values()
                for entries in cfgs.values()
            )
            print(f"{sn_count} 条 SN 记录")

            # c. FA Tracker
            fa_stats = {'total': 0, 'matched': 0}
            fa_path, fa_date = _find_fa_tracker(date_str)
            if fa_path:
                print(f"   [+] FA Tracker: {os.path.basename(fa_path)}", end=' ')
                try:
                    fa_records = read_fa_tracker(fa_path)
                    fa_matched = fa_match(fa_records, results)
                    fa_stats = fa_summary(fa_matched)
                    print(f"  -> {fa_stats['matched']}/{fa_stats['total']} matched")
                except Exception as e:
                    print(f"WARN: process failed: {e}")
            else:
                print("   [+] FA Tracker: not found")

            # d. 保存到 DB
            _, _, ts_test_names, _ = read_test_summary(filepath)
            conn = get_conn()
            report_id = create_report_version(conn, date_str, filepath, source_file_name=fname, ts_test_names=ts_test_names)
            save_report_definitions(conn, report_id, filepath)
            previous = conn.execute(
                """SELECT id FROM reports
                   WHERE is_active = 1 AND report_date < ?
                   ORDER BY report_date DESC, version DESC
                   LIMIT 1""",
                (date_str,),
            ).fetchone()
            previous_report_id = previous['id'] if previous else None
            changes = detect_definition_changes(conn, report_id, previous_report_id)
            if changes:
                save_definition_changes(conn, changes)
            conn.commit()
            conn.close()

            report_id = save_report(date_str, results, fa_stats, filepath, ts_test_names, report_id=report_id)
            save_sn_progress(report_id, progress_data)

            cp_fact_rows, check_fact_rows = extract_sn_fact_rows(filepath, report_id, date_str)
            conn = get_conn()
            save_sn_cp_results(conn, cp_fact_rows)
            save_sn_check_state_history(conn, report_id, date_str, check_fact_rows)
            conn.commit()
            conn.close()
            print(f"   [+] SN facts: {len(cp_fact_rows)} CP rows, {len(check_fact_rows)} check rows")

            print(f"OK saved (report_id={report_id})")

            # e. 累积统计
            stats['files_processed'] += 1
            stats['total_wf_set'].update(results.keys())
            stats['total_sn_records'] += sn_count
            failures = build_failure_detail(results)
            stats['total_failures'] += len(failures)
            stats['total_spec_fails'] += sum(1 for f in failures if f['type'] == 'spec')
            stats['total_strife_fails'] += sum(1 for f in failures if f['type'] == 'strife')

        except Exception as e:
            print(f"ERROR: process failed: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 4. 计算预测
    if stats['files_processed'] > 0:
        print("\n[OK] Computing auto predictions...")
        try:
            compute_auto_predictions()
            print("[OK] Predictions done")
        except Exception as e:
            print(f"[WARN] Prediction failed: {e}")

    # 5. 最终统计
    stats['total_wfs'] = len(stats['total_wf_set'])
    del stats['total_wf_set']

    print()
    print("=" * 52)
    print("  [STATS] Batch Processing Summary")
    print("=" * 52)
    print(f"    处理文件数:      {stats['files_processed']}")
    print(f"    总 WF 数:        {stats['total_wfs']}")
    print(f"    总 SN 记录数:    {stats['total_sn_records']}")
    print(f"    总 Failure 数:   {stats['total_failures']}")
    print(f"      - Spec:        {stats['total_spec_fails']}")
    print(f"      - Strife:      {stats['total_strife_fails']}")
    print("=" * 52)

    return stats


# ═══════════════════════════════════════════════════════════════════════
#  process_newest — 增量更新
# ═══════════════════════════════════════════════════════════════════════

def process_newest():
    """处理最新的 Daily Report（增量更新）。

    如果该日期的报告已存在于数据库中，则跳过不重复处理。

    Returns:
        dict or None: 处理结果信息。
    """
    reports = _find_daily_reports()
    if not reports:
        print("ERROR: No Daily Report files found")
        return None

    latest_date, latest_path = reports[-1]
    fname = os.path.basename(latest_path)
    print(f"[OK] Newest file: {fname}  (date: {latest_date})")

    # 检查是否已存在
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM reports WHERE report_date = ?", (latest_date,)
    ).fetchone()
    conn.close()

    if existing:
        print(f"   [INFO] Existing active report for {latest_date}; importing as new version")

    # 确保 DB 已初始化
    init_db()
    init_categories()

    print("   [+] Starting process...")
    try:
        results = analyze(latest_path)
        progress_data = extract_sn_progress(latest_path)
        _, _, ts_test_names, _ = read_test_summary(latest_path)

        # FA Tracker
        fa_stats = {'total': 0, 'matched': 0}
        fa_path, fa_date = _find_fa_tracker(latest_date)
        if fa_path:
            try:
                fa_records = read_fa_tracker(fa_path)
                fa_matched = fa_match(fa_records, results)
                fa_stats = fa_summary(fa_matched)
                print(f"   FA: {fa_stats['matched']}/{fa_stats['total']} 匹配")
            except Exception as e:
                print(f"   FA Tracker process failed: {e}")

        conn = get_conn()
        report_id = create_report_version(conn, latest_date, latest_path, source_file_name=fname, ts_test_names=ts_test_names)
        save_report_definitions(conn, report_id, latest_path)
        previous = conn.execute(
            """SELECT id FROM reports
               WHERE is_active = 1 AND report_date < ?
               ORDER BY report_date DESC, version DESC
               LIMIT 1""",
            (latest_date,),
        ).fetchone()
        previous_report_id = previous['id'] if previous else None
        changes = detect_definition_changes(conn, report_id, previous_report_id)
        if changes:
            save_definition_changes(conn, changes)
        conn.commit()
        conn.close()

        report_id = save_report(latest_date, results, fa_stats, latest_path, ts_test_names, report_id=report_id)
        save_sn_progress(report_id, progress_data)

        cp_fact_rows, check_fact_rows = extract_sn_fact_rows(latest_path, report_id, latest_date)
        conn = get_conn()
        save_sn_cp_results(conn, cp_fact_rows)
        save_sn_check_state_history(conn, report_id, latest_date, check_fact_rows)
        conn.commit()
        conn.close()
        print(f"   [+] SN facts: {len(cp_fact_rows)} CP rows, {len(check_fact_rows)} check rows")

        print(f"OK done (report_id={report_id})")
        return {
            'date': latest_date,
            'file': latest_path,
            'report_id': report_id,
            'wfs': len(results),
        }

    except Exception as e:
        print(f"ERROR: process failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════════════════
#  compute_auto_predictions — 预测完成时间
# ═══════════════════════════════════════════════════════════════════════

BULK_PROGRESS_THRESHOLD = 0.75

PREDICTION_MODELS = {
    'short_cycle': {
        'name': 'short_cycle',
        'threshold': 0.75,
        'history_days': 5,
        'rate_strategy': 'weighted',
    },
    'random_or_drop': {
        'name': 'random_or_drop',
        'threshold': 0.80,
        'history_days': 7,
        'rate_strategy': 'weighted_conservative',
    },
    'long_storage': {
        'name': 'long_storage',
        'threshold': 0.75,
        'history_days': 14,
        'rate_strategy': 'median_nonzero',
    },
    'standard': {
        'name': 'standard',
        'threshold': 0.75,
        'history_days': 14,
        'rate_strategy': 'mean',
    },
}


def _bulk_cp(cp_values, threshold=BULK_PROGRESS_THRESHOLD):
    values = sorted(int(v or 0) for v in cp_values)
    if not values:
        return 0
    required_count = max(1, math.ceil(len(values) * threshold))
    return values[len(values) - required_count]


def _prediction_model_for_test(test_name):
    text = str(test_name or '').casefold()
    if any(word in text for word in ('button', 'cycling', 'actuation', 'squeeze', 'pressure')):
        return PREDICTION_MODELS['short_cycle']
    if any(word in text for word in ('drop', 'random', 'granite', 'pb', 'sequence')):
        return PREDICTION_MODELS['random_or_drop']
    if any(word in text for word in ('storage', 'soak', 'aging', 'thermal', 'humidity', 'temperature', 'environmental')):
        return PREDICTION_MODELS['long_storage']
    return PREDICTION_MODELS['standard']


def _workdays_between(start_date, end_date):
    if isinstance(start_date, datetime.datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime.datetime):
        end_date = end_date.date()
    if end_date <= start_date:
        return 0

    days = 0
    cursor = start_date
    while cursor < end_date:
        cursor += datetime.timedelta(days=1)
        if cursor.weekday() != 6:
            days += 1
    return days


def _add_workdays(start_date, workdays):
    if isinstance(start_date, datetime.datetime):
        cursor = start_date.date()
    else:
        cursor = start_date

    remaining = max(0, int(workdays))
    while remaining > 0:
        cursor += datetime.timedelta(days=1)
        if cursor.weekday() != 6:
            remaining -= 1
    if cursor.weekday() == 6:
        cursor += datetime.timedelta(days=1)
    return cursor


def _prediction_daily_bulk_progress(conn, wf_num, config, test_idx, days, threshold=BULK_PROGRESS_THRESHOLD):
    rows = conn.execute("""
        SELECT r.report_date,
               sp.sn,
               sp.current_cp_idx,
               sp.total_cps
        FROM sn_progress sp
        JOIN reports r ON sp.report_id = r.id
        WHERE sp.wf_num = ? AND sp.config = ? AND sp.test_idx = ?
          AND r.is_active = 1
          AND r.report_date IN (
              SELECT report_date
              FROM reports
              WHERE is_active = 1
              ORDER BY report_date DESC, version DESC
              LIMIT ?
          )
        ORDER BY r.report_date DESC
    """, (wf_num, config, test_idx, days)).fetchall()

    by_date = {}
    for row in rows:
        entry = by_date.setdefault(row['report_date'], {'cp_values': [], 'total_cps': 0})
        entry['cp_values'].append(row['current_cp_idx'] or 0)
        entry['total_cps'] = max(entry['total_cps'], row['total_cps'] or 0)

    daily = []
    for report_date, entry in by_date.items():
        daily.append({
            'report_date': report_date,
            'bulk_cp': _bulk_cp(entry['cp_values'], threshold),
            'total_cps': entry['total_cps'],
            'sn_count': len(entry['cp_values']),
        })

    return sorted(daily, key=lambda item: item['report_date'])


def _prediction_test_name(conn, wf_num, test_idx):
    row = conn.execute("""
        SELECT rtn.test_name
        FROM report_test_names rtn
        JOIN reports r ON r.id = rtn.report_id
        WHERE rtn.wf_num = ? AND rtn.test_idx = ? AND r.is_active = 1
        ORDER BY r.report_date DESC, r.version DESC
        LIMIT 1
    """, (wf_num, test_idx)).fetchone()
    if row and row['test_name']:
        return row['test_name']
    return f'Test{test_idx + 1}'


def _daily_rate_samples(daily_data):
    rates = []
    for i in range(1, len(daily_data)):
        prev_date = datetime.datetime.strptime(daily_data[i - 1]['report_date'], '%Y-%m-%d').date()
        curr_date = datetime.datetime.strptime(daily_data[i]['report_date'], '%Y-%m-%d').date()
        workdays = _workdays_between(prev_date, curr_date)
        if workdays <= 0:
            continue
        delta = (daily_data[i]['bulk_cp'] or 0) - (daily_data[i - 1]['bulk_cp'] or 0)
        if delta >= 0:
            rates.append(delta / workdays)
    return rates


def _weighted_daily_rate(rates):
    if not rates:
        return 0
    weights = list(range(1, len(rates) + 1))
    return sum(rate * weight for rate, weight in zip(rates, weights)) / sum(weights)


def _daily_rate_for_model(daily_data, model):
    rates = _daily_rate_samples(daily_data)
    if not rates:
        return 0

    strategy = model.get('rate_strategy')
    if strategy == 'weighted':
        return _weighted_daily_rate(rates)
    if strategy == 'weighted_conservative':
        weighted = _weighted_daily_rate(rates)
        mean = sum(rates) / len(rates)
        return min(weighted, mean)
    if strategy == 'median_nonzero':
        nonzero = sorted(rate for rate in rates if rate > 0)
        if nonzero:
            return statistics.median(nonzero)
        return sum(rates) / len(rates)
    return sum(rates) / len(rates)


def _prediction_targets(conn):
    """Return one representative active test per WF/config from the latest report."""
    rows = conn.execute("""
        WITH latest_report AS (
            SELECT id
            FROM reports
            WHERE is_active = 1
            ORDER BY report_date DESC, version DESC
            LIMIT 1
        )
        SELECT sp.wf_num, sp.config, sp.test_idx, COUNT(*) AS sn_count
        FROM sn_progress sp
        JOIN latest_report lr ON sp.report_id = lr.id
        GROUP BY sp.wf_num, sp.config, sp.test_idx
    """).fetchall()

    if not rows:
        return conn.execute("""
            SELECT DISTINCT wf_num, config, test_idx FROM wf_results
        """).fetchall()

    targets = {}
    for row in rows:
        key = (row['wf_num'], row['config'])
        current = targets.get(key)
        if current is None:
            targets[key] = row
            continue

        row_count = row['sn_count'] or 0
        current_count = current['sn_count'] or 0
        if row_count > current_count:
            targets[key] = row
        elif row_count == current_count and (row['test_idx'] or 0) > (current['test_idx'] or 0):
            targets[key] = row

    return list(targets.values())


def _delete_stale_prediction_tests(targets):
    """Keep only the latest representative test for each WF/config prediction."""
    conn = get_conn()
    try:
        for target in targets:
            conn.execute(
                """DELETE FROM predictions
                   WHERE wf_num = ? AND config = ? AND test_idx <> ?""",
                (target['wf_num'], target['config'], target['test_idx'])
            )
        conn.commit()
    finally:
        conn.close()


def compute_auto_predictions(days=14):
    """自动计算所有 WF/Config/Test 的预测完成时间。

    算法：
      1. 对于每个 wf_config_test 组合，从 DB 获取最近 N 天的 CP 进度
         （取所有 SN 中最高的 current_cp_idx 作为该日的进度）。
      2. 计算每天平均完成的 CP 数（每日 max_cp 的增长速率）。
      3. 剩余 CP = total_cps - 最新 max_cp。
      4. 预测天数 = 剩余 CP / 每日速率。
      5. 预测完成日期 = 最新报告日期 + 预测天数。
      6. 保存到 predictions 表。

    Args:
        days: 用于计算速率的历史天数，默认 14 天。

    Returns:
        list: 预测结果列表。
    """
    conn = get_conn()

    # 获取每个 WF/config 的代表性 active test。个别慢 SN 不应让同一 config 出现多个 test。
    rows = _prediction_targets(conn)

    if not rows:
        print("WARN: No data for prediction")
        conn.close()
        return []

    predictions = []

    for row in rows:
        wfn = row['wf_num']
        cfg = row['config']
        ti = row['test_idx']

        test_name = _prediction_test_name(conn, wfn, ti)
        model = _prediction_model_for_test(test_name)
        daily_data = _prediction_daily_bulk_progress(
            conn, wfn, cfg, ti, model['history_days'], model['threshold'],
        )

        if len(daily_data) < 2:
            continue

        total_cps = daily_data[-1]['total_cps'] or 0
        if total_cps == 0:
            continue

        daily_rate = _daily_rate_for_model(daily_data, model)
        if daily_rate <= 0:
            continue

        current_bulk_cp = daily_data[-1]['bulk_cp'] or 0
        completed_cps = current_bulk_cp + 1
        remaining = total_cps - completed_cps
        if remaining <= 0:
            continue

        remaining_days = remaining / daily_rate

        last_date = datetime.datetime.strptime(
            daily_data[-1]['report_date'], '%Y-%m-%d'
        )
        workdays_needed = max(1, math.ceil(remaining_days))
        predicted_date = _add_workdays(last_date, workdays_needed)

        predictions.append({
            'wf_num': wfn,
            'config': cfg,
            'test_idx': ti,
            'predicted_date': predicted_date.strftime('%Y-%m-%d'),
            'remaining_days': round(remaining_days, 1),
            'daily_rate': round(daily_rate, 2),
            'total_cps': total_cps,
            'current_max_cp': current_bulk_cp,
            'test_name': test_name,
        })

    conn.close()

    if rows:
        _delete_stale_prediction_tests(rows)

    if predictions:
        save_predictions(predictions)
        print(f"OK generated {len(predictions)} predictions")
        # Try to populate real test names from latest report's TS sheet
        _populate_test_names()
    else:
        print("WARN: not enough data to predict")

    return predictions


def _populate_test_names():
    """从最新 Daily Report 的 TS sheet 读取测试名并更新 predictions 表。"""
    from engine import read_test_summary
    reports = _find_daily_reports()
    if not reports: return
    latest_path = reports[-1][1]
    try:
        _, _, ts_test_names, _ = read_test_summary(latest_path)
        if not ts_test_names: return
        conn = get_conn()
        updated = 0
        for wf, names in ts_test_names.items():
            for ti, name in enumerate(names):
                if name:
                    conn.execute(
                        "UPDATE predictions SET test_name = ? WHERE wf_num = ? AND test_idx = ?",
                        (name, wf, ti)
                    )
                    updated += conn.total_changes
        conn.commit()
        conn.close()
        if updated:
            print(f"   [OK] Updated {updated} test names in predictions")
    except Exception:
        logger.exception("Failed to populate prediction test names from Test Summary")


# ═══════════════════════════════════════════════════════════════════════
#  print_db_summary — 数据库汇总
# ═══════════════════════════════════════════════════════════════════════

def print_db_summary():
    """打印数据库中所有数据的汇总统计。"""
    conn = get_conn()

    report_count = conn.execute(
        "SELECT COUNT(*) as c FROM reports"
    ).fetchone()['c']

    wf_count = conn.execute(
        "SELECT COUNT(DISTINCT wf_num) as c FROM wf_results"
    ).fetchone()['c']

    sn_count = conn.execute(
        "SELECT COUNT(*) as c FROM sn_progress"
    ).fetchone()['c']

    fail_entries = conn.execute(
        "SELECT COUNT(*) as c FROM wf_results "
        "WHERE spec_fail_count + strife_fail_count > 0"
    ).fetchone()['c']

    total_spec = conn.execute(
        "SELECT COALESCE(SUM(spec_fail_count), 0) as c FROM wf_results"
    ).fetchone()['c']

    total_strife = conn.execute(
        "SELECT COALESCE(SUM(strife_fail_count), 0) as c FROM wf_results"
    ).fetchone()['c']

    pred_count = conn.execute(
        "SELECT COUNT(*) as c FROM predictions"
    ).fetchone()['c']

    conn.close()

    print()
    print("=" * 52)
    print("  [STATS] Database Summary")
    print("=" * 52)
    print(f"    报告数:             {report_count}")
    print(f"    WF 数:              {wf_count}")
    print(f"    SN 进度记录数:      {sn_count}")
    print(f"    含 Failure 条目数:  {fail_entries}")
    print(f"    Spec Failures:      {total_spec}")
    print(f"    Strife Failures:    {total_strife}")
    print(f"    预测记录数:         {pred_count}")
    print("=" * 52)


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description='M60 EVT REL — Batch Processor 批量处理 Daily Report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python processor.py                    # 增量处理最新文件
  python processor.py --all              # 处理所有文件（增量追加）
  python processor.py --all --rebuild    # 重建数据库并处理所有文件
  python processor.py --predict          # 只重新计算预测
  python processor.py --stats            # 打印数据库汇总
        """,
    )
    parser.add_argument('--all', action='store_true',
                        help='处理所有 Daily Report')
    parser.add_argument('--rebuild', action='store_true',
                        help='重建数据库（删除已有数据并重新初始化）')
    parser.add_argument('--predict', action='store_true',
                        help='只重新计算预测（不处理文件）')
    parser.add_argument('--stats', action='store_true',
                        help='打印数据库汇总统计')

    args = parser.parse_args()

    if args.stats:
        print_db_summary()
        return

    if args.predict:
        compute_auto_predictions()
        return

    if args.all:
        process_all(rebuild=args.rebuild)
    else:
        process_newest()


if __name__ == '__main__':
    main()
