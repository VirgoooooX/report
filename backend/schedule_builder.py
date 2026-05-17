"""Authoritative schedule payload builder.

This module turns test-level schedule segments into CP-level schedule data. The
input dates come from Test Schedule parsing; CP dates and actual overlay are
derived here from CP definitions and progress.
"""
import datetime


def wf_sort_key(wf_num):
    try:
        return [int(part) for part in str(wf_num).split('.')]
    except ValueError:
        return [9999, str(wf_num)]


def normalize_wf(wf_num):
    text = str(wf_num or '').strip()
    return text[2:] if text.upper().startswith('WF') else text


def parse_iso_date(value):
    try:
        year, month, day = [int(part) for part in str(value or '').split('-')]
        return datetime.date(year, month, day)
    except (TypeError, ValueError):
        return None


def to_iso_date(value):
    return value.isoformat()


def enumerate_schedule_days(start_date, end_date):
    start = parse_iso_date(start_date)
    end = parse_iso_date(end_date)
    if not start or not end or start > end:
        return []

    days = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() != 6:
            days.append(to_iso_date(cursor))
        cursor += datetime.timedelta(days=1)
    return days


def next_schedule_date_after(date_value):
    parsed = parse_iso_date(date_value)
    if not parsed:
        return ''

    next_day = parsed + datetime.timedelta(days=1)
    while next_day.weekday() == 6:
        next_day += datetime.timedelta(days=1)
    return to_iso_date(next_day)


def distribute_test_cp_labels(cps, start_date, end_date, exclude_start_date=False, exclude_end_date=False):
    """Place CPs onto working days using a deterministic formula.

    Let ``D = len(enumerate_schedule_days(start_date, end_date))`` and
    ``N = len(cps)``. With ``D >= 1`` and ``N >= 1``, the i-th CP (1-based)
    is mapped to working day
    ``clamp(ceil(i * D / N) - 1, 0, D - 1)``. When ``D < N``, multiple CPs
    stack onto the same working day; the last CP always lands on the last
    placement day.

    REL_T0 / REL_TFINAL handling:
        On the Test Schedule sheet, ``T0`` (REL_T0) marks the day **before**
        the WF actually begins, and ``End`` (REL_TFINAL) marks the day
        **after** it ends. Both columns are pure boundary markers, not CP
        slots. Callers therefore pass:

        - ``exclude_start_date=True`` for the lane's **first** test (its
          ``planned_start_date`` equals the T0 marker date);
        - ``exclude_end_date=True`` for the lane's **last** test (its
          ``planned_end_date`` equals the End marker date).

        These flags drop the matching boundary day from the placement
        domain so CPs land in ``(start, end)`` (with appropriate side
        exclusion). The lane bar still extends through both boundary
        columns for visual closure without overlapping the first/last CP.

        For non-first / non-last tests in a multi-test lane, the relevant
        boundary IS the test's own real working day (not a marker), so
        the corresponding flag MUST stay ``False`` — otherwise CPs would
        be squeezed into a too-short domain.

    Returns an empty list when ``D == 0`` or ``N == 0``.
    """
    working_days = enumerate_schedule_days(start_date, end_date)
    placement_days = list(working_days)
    if exclude_end_date and placement_days and placement_days[-1] == end_date:
        # Drop the trailing day when it coincides with end_date so placement
        # is bounded above by the working day strictly before End/REL_TFINAL.
        placement_days.pop()
    if exclude_start_date and placement_days and placement_days[0] == start_date:
        # Drop the leading day when it coincides with start_date so placement
        # starts on the working day strictly after T0/REL_T0.
        placement_days.pop(0)
    # Defensive: a degenerate range (start == end with both flags set, or a
    # single-day domain that gets fully eaten by exclusion) leaves an empty
    # placement domain. Fall back to a single-day domain so a lone CP still
    # has somewhere to land instead of being silently dropped.
    if not placement_days and working_days:
        placement_days = [working_days[0]]

    D = len(placement_days)
    N = len(cps)
    if D == 0 or N == 0:
        return []

    sorted_cps = sorted(cps, key=lambda cp: int(cp.get('cp_idx') or 0))
    last_day_index = D - 1
    result = []
    for i in range(1, N + 1):
        # ceil(i * D / N) using integer arithmetic, then convert to 0-index
        day_index = (i * D + N - 1) // N - 1
        if day_index < 0:
            day_index = 0
        elif day_index > last_day_index:
            day_index = last_day_index
        result.append({
            **sorted_cps[i - 1],
            'planned_date': placement_days[day_index],
            'display_cp_idx': i,
            'visible': True,
        })
    return result


def normalize_lane_test_ranges(tests):
    previous_end = ''
    normalized = []
    for test in tests:
        start = test.get('planned_start_date') or ''
        end = test.get('planned_end_date') or ''

        if previous_end and start and start <= previous_end:
            start = next_schedule_date_after(previous_end)
            if end and end < start:
                end = start

        days = enumerate_schedule_days(start, end)
        if end and (not previous_end or end > previous_end):
            previous_end = end

        normalized.append({
            **test,
            'planned_start_date': start,
            'planned_end_date': end,
            'days': days,
            'duration_days': len(days),
        })
    return normalized


def build_actual_progress(scheduled_cps, progress, planned_end_date=''):
    current_raw = progress.get('current_cp_idx') if progress else None
    if current_raw is None or current_raw == '':
        return None
    try:
        current_cp_idx = int(current_raw)
    except (TypeError, ValueError):
        return None

    ordered_cps = sorted(
        [cp for cp in scheduled_cps if cp.get('cp_idx') is not None and cp.get('planned_date')],
        key=lambda cp: int(cp.get('cp_idx') or 0),
    )
    completed = [cp for cp in ordered_cps if int(cp.get('cp_idx') or 0) <= current_cp_idx]
    if not completed:
        return None

    completed_cp = completed[-1]
    last_cp_idx = int(ordered_cps[-1].get('cp_idx') or 0) if ordered_cps else None
    is_complete = last_cp_idx is not None and current_cp_idx >= last_cp_idx
    return {
        'current_cp_idx': current_cp_idx,
        'current_cp_name': progress.get('current_cp_name') or completed_cp.get('cp_name') or '',
        'total_cps': int(progress.get('total_cps') or 0),
        'sn_count': int(progress.get('sn_count') or 0),
        'is_complete': is_complete,
        'end_date': planned_end_date if is_complete and planned_end_date else completed_cp.get('planned_date'),
    }


def apply_cp_progress_flags(cps, actual_progress):
    if not actual_progress or actual_progress.get('current_cp_idx') is None:
        return [
            {**cp, 'is_completed': False, 'is_current': False}
            for cp in cps
        ]

    current_cp_idx = int(actual_progress['current_cp_idx'])
    is_complete = bool(actual_progress.get('is_complete'))
    return [
        {
            **cp,
            'is_completed': is_complete or int(cp.get('cp_idx') or 0) <= current_cp_idx,
            'is_current': (not is_complete) and int(cp.get('cp_idx') or 0) == current_cp_idx,
        }
        for cp in cps
    ]


def build_schedule_segments(segments, wf_meta=None, cps_by_key=None, progress_by_key=None):
    """Build authoritative segment payloads for /api/schedule.

    ``cps_by_key`` MUST be supplied by the caller (typically built from
    ``current_cp_definitions`` in ``api_schedule``). This builder does not
    fall back to ``report_cps`` and never reads from the database.

    Boundary CPs (rows with ``is_boundary=1`` in ``current_cp_definitions``,
    e.g. T0 / REL_T0 / End / TFinal / REL_TFINAL) MUST be filtered out by
    the caller. This function assumes every entry in ``cps_by_key`` is a
    placement-eligible test CP. T0/End anchors come from
    ``current_schedule_segments`` (the ``segments`` argument), not from
    ``cps_by_key``. See
    docs/plans/2026-05-17-rel-t0-daily-report-second-cut.md.

    As a defensive guard, this function:

    - skips lanes whose ``wf_num`` normalizes to ``{"43", "44"}`` even if the
      caller failed to filter them upstream, and
    - sorts every ``(wf_num, test_idx)`` bucket ascending by ``cp_idx`` before
      passing it to ``distribute_test_cp_labels``.
    """
    wf_meta = wf_meta or {}
    cps_by_key = cps_by_key or {}
    progress_by_key = progress_by_key or {}

    # Pre-sort each bucket ascending by cp_idx so downstream placement sees a
    # stable, deterministic order regardless of how the caller built the dict.
    sorted_cps_by_key = {
        key: sorted(
            cps,
            key=lambda cp: int(cp.get('cp_idx') or 0),
        )
        for key, cps in cps_by_key.items()
    }

    excluded_wf_nums = {'43', '44'}

    lanes = {}
    for segment in segments:
        wf_num = str(segment.get('wf_num'))
        # Defensively drop phantom workflows that must not appear in the
        # schedule even if they leaked into the segment list upstream.
        if normalize_wf(wf_num) in excluded_wf_nums:
            continue
        config = segment.get('config') or ''
        wf_meta_value = wf_meta.get(wf_num, '')
        if isinstance(wf_meta_value, dict):
            wf_meta_value = wf_meta_value.get('name', '')
        key = (wf_num, config)
        bucket = sorted_cps_by_key.get(
            (wf_num, segment.get('test_idx')),
            segment.get('cps') or [],
        )
        lanes.setdefault(key, []).append({
            **segment,
            'wf_num': wf_num,
            'wf_name': wf_meta_value,
            'config': config,
            'cps': [dict(cp) for cp in bucket],
        })

    payload_segments = []
    for (wf_num, config), lane_tests in lanes.items():
        ordered_tests = sorted(
            lane_tests,
            key=lambda row: (
                str(row.get('planned_start_date') or ''),
                int(row.get('test_idx') or 0),
            ),
        )
        tests = normalize_lane_test_ranges(ordered_tests)
        planned_end = max([test.get('planned_end_date') for test in tests if test.get('planned_end_date')] or [''])

        progress = progress_by_key.get((normalize_wf(wf_num), config), {})
        tests_with_cps = []
        last_test_index = len(tests) - 1
        for test_position, test in enumerate(tests):
            # T0/REL_T0 (lane's first test start) and End/REL_TFINAL (lane's
            # last test end) are pure boundary markers — they sit one column
            # outside the test's actual working-day range, so CPs must not
            # land on them. Earlier/later tests in the lane have real
            # working-day boundaries and use the full [start, end] domain.
            scheduled_cps = distribute_test_cp_labels(
                test.get('cps') or [],
                test.get('planned_start_date'),
                test.get('planned_end_date'),
                exclude_start_date=(test_position == 0),
                exclude_end_date=(test_position == last_test_index),
            )
            tests_with_cps.append({
                **test,
                'cps': scheduled_cps,
                'scheduled_cps': scheduled_cps,
                'visible_cps': scheduled_cps,
            })

        lane_cps = [cp for test in tests_with_cps for cp in test.get('scheduled_cps', [])]
        actual_progress = build_actual_progress(lane_cps, progress, planned_end)

        for test in tests_with_cps:
            flagged_cps = apply_cp_progress_flags(test.get('scheduled_cps') or [], actual_progress)
            payload_segments.append({
                **test,
                'cps': flagged_cps,
                'scheduled_cps': flagged_cps,
                'visible_cps': flagged_cps,
                'actual_progress': actual_progress,
                'current_cp_idx': progress.get('current_cp_idx'),
                'current_cp_name': progress.get('current_cp_name', ''),
                'total_cps': int(progress.get('total_cps') or 0),
                'sn_count': int(progress.get('sn_count') or 0),
            })

    payload_segments.sort(key=lambda row: (
        wf_sort_key(row.get('wf_num')),
        row.get('config') or '',
        int(row.get('test_idx') or 0),
    ))
    return payload_segments
