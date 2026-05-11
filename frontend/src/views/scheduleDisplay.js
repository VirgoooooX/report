function parseIsoDate(value) {
  const [year, month, day] = String(value || '').split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(Date.UTC(year, month - 1, day))
}

function toIsoDate(date) {
  return date.toISOString().slice(0, 10)
}

function addDays(date, days) {
  const next = new Date(date)
  next.setUTCDate(next.getUTCDate() + days)
  return next
}

export function enumerateScheduleDays(startDate, endDate) {
  const start = parseIsoDate(startDate)
  const end = parseIsoDate(endDate)
  if (!start || !end || start > end) return []

  const days = []
  for (let cursor = start; cursor <= end; cursor = addDays(cursor, 1)) {
    if (cursor.getUTCDay() !== 0) {
      days.push(toIsoDate(cursor))
    }
  }
  return days
}

export function enumerateCalendarDays(startDate, endDate) {
  const start = parseIsoDate(startDate)
  const end = parseIsoDate(endDate)
  if (!start || !end || start > end) return []

  const days = []
  for (let cursor = start; cursor <= end; cursor = addDays(cursor, 1)) {
    days.push(toIsoDate(cursor))
  }
  return days
}

export function distributeCpsAcrossDays(cps = [], startDate, endDate, maxVisible = 6) {
  const days = enumerateScheduleDays(startDate, endDate)
  const placementDays = days.length ? days : [startDate].filter(Boolean)
  if (!placementDays.length) return []

  const sortedCps = [...cps].sort((a, b) => Number(a.cp_idx) - Number(b.cp_idx))
  const visibleIndexes = sampleIndexes(sortedCps.length, maxVisible)
  const lastCpIndex = Math.max(0, sortedCps.length - 1)
  const lastDayIndex = Math.max(0, placementDays.length - 1)

  return sortedCps.map((cp, index) => {
    const dayIndex = lastCpIndex === 0
      ? 0
      : Math.round((index * lastDayIndex) / lastCpIndex)
    return {
      ...cp,
      planned_date: placementDays[dayIndex],
      visible: visibleIndexes.has(index)
    }
  })
}

export function distributeDailyCpLabels(cps = [], startDate, endDate) {
  const workDays = enumerateScheduleDays(startDate, endDate)
  const placementDays = workDays.length > 2 ? workDays.slice(1, -1) : workDays
  if (!placementDays.length || !cps.length) return []

  const sortedCps = [...cps].sort((a, b) => Number(a.cp_idx) - Number(b.cp_idx))
  if (sortedCps.length >= placementDays.length) {
    return placementDays.map((day, index) => {
      const cpIndex = Math.min(
        sortedCps.length - 1,
        Math.ceil(((index + 1) * sortedCps.length) / placementDays.length) - 1
      )
      return {
        ...sortedCps[cpIndex],
        planned_date: day,
        display_day_idx: index
      }
    })
  }

  const lastCpIndex = Math.max(0, sortedCps.length - 1)
  const lastDayIndex = Math.max(0, placementDays.length - 1)
  return sortedCps.map((cp, index) => {
    const dayIndex = lastCpIndex === 0
      ? Math.round(lastDayIndex / 2)
      : Math.round((index * lastDayIndex) / lastCpIndex)
    return {
      ...cp,
      planned_date: placementDays[dayIndex],
      display_day_idx: dayIndex
    }
  })
}

function previousScheduleDay(days, targetDate) {
  if (!days.length) return ''
  const targetIndex = days.indexOf(targetDate)
  if (targetIndex > 0) return days[targetIndex - 1]
  if (targetIndex === 0) return days[0]
  return days[days.length - 1]
}

export function distributeTestCpLabels(cps = [], startDate, endDate, maxVisible = 6, options = {}) {
  const allDays = enumerateScheduleDays(startDate, endDate)
  if (!allDays.length || !cps.length) return []

  const sortedCps = [...cps].sort((a, b) => Number(a.cp_idx) - Number(b.cp_idx))
  const targetDate = options.avoidEndDate
    ? previousScheduleDay(allDays, endDate)
    : (allDays.includes(endDate) ? endDate : allDays[allDays.length - 1])
  const targetIndex = Math.max(0, allDays.indexOf(targetDate))
  const startOffset = options.avoidStartDate && sortedCps.length > 1 && targetIndex > 0 ? 1 : 0
  const placementDays = allDays.slice(startOffset, targetIndex + 1)
  if (!placementDays.length) return []

  const lastCpIndex = Math.max(0, sortedCps.length - 1)
  const lastDayIndex = Math.max(0, placementDays.length - 1)

  return sortedCps.map((cp, index) => {
    const dayIndex = lastCpIndex === 0
      ? lastDayIndex
      : Math.ceil(((index + 1) * placementDays.length) / sortedCps.length) - 1
    return {
      ...cp,
      planned_date: placementDays[Math.min(lastDayIndex, Math.max(0, dayIndex))],
      display_cp_idx: index + 1,
      visible: true
    }
  })
}

function cpOrderValue(cp) {
  return [
    Number(cp.test_idx ?? 0),
    Number(cp.display_cp_idx ?? cp.cp_idx ?? 0),
    Number(cp.cp_idx ?? 0)
  ]
}

export function summarizeDailyCpMarkers(cps = []) {
  if (!cps.length) return []

  const ordered = [...cps].sort((a, b) => {
    const left = cpOrderValue(a)
    const right = cpOrderValue(b)
    for (let index = 0; index < left.length; index += 1) {
      if (left[index] !== right[index]) return left[index] - right[index]
    }
    return 0
  })
  const cpNames = ordered.map((cp) => cp.cp_name).filter(Boolean)
  const lastCp = ordered[ordered.length - 1]

  return [{
    ...lastCp,
    daily_cp_names: cpNames,
    cp_title: cpNames.join('\n')
  }]
}

export function buildActualProgress(scheduledCps = [], progress = {}, plannedEndDate = '') {
  if (progress.current_cp_idx === null || progress.current_cp_idx === undefined || progress.current_cp_idx === '') {
    return null
  }
  const currentCpIdx = Number(progress.current_cp_idx)
  if (!Number.isFinite(currentCpIdx)) return null

  const orderedCps = [...scheduledCps]
    .filter((cp) => Number.isFinite(Number(cp.cp_idx)) && cp.planned_date)
    .sort((a, b) => Number(a.cp_idx) - Number(b.cp_idx))
  const completedCp = orderedCps
    .filter((cp) => Number(cp.cp_idx) <= currentCpIdx)
    .at(-1)

  if (!completedCp) return null
  const lastCpIdx = Number(orderedCps.at(-1)?.cp_idx)
  const isComplete = Number.isFinite(lastCpIdx) && currentCpIdx >= lastCpIdx

  return {
    current_cp_idx: currentCpIdx,
    current_cp_name: progress.current_cp_name || completedCp.cp_name || '',
    total_cps: Number(progress.total_cps) || 0,
    sn_count: Number(progress.sn_count) || 0,
    is_complete: isComplete,
    end_date: isComplete && plannedEndDate ? plannedEndDate : completedCp.planned_date
  }
}

export function sampleIndexes(count, maxVisible = 6) {
  if (count <= 0) return new Set()
  if (count <= maxVisible) return new Set(Array.from({ length: count }, (_, index) => index))

  const result = new Set([0, count - 1])
  const slots = Math.max(2, maxVisible) - 1
  for (let slot = 1; slot < slots; slot += 1) {
    result.add(Math.round((slot * (count - 1)) / slots))
  }
  return result
}

export function buildScheduleRows(segments = [], maxVisibleCps = 6) {
  return segments.map((segment) => {
    const days = enumerateScheduleDays(segment.planned_start_date, segment.planned_end_date)
    const scheduledCps = distributeCpsAcrossDays(
      segment.cps || [],
      segment.planned_start_date,
      segment.planned_end_date,
      maxVisibleCps
    )
    const dailyCps = distributeDailyCpLabels(
      segment.cps || [],
      segment.planned_start_date,
      segment.planned_end_date
    )
    return {
      ...segment,
      days,
      duration_days: days.length,
      scheduled_cps: scheduledCps,
      daily_cps: dailyCps,
      visible_cps: dailyCps
    }
  })
}

function laneKey(row) {
  return [
    row.wf_num,
    row.config || ''
  ].join('||')
}

function minDate(values) {
  return values.filter(Boolean).sort()[0] || ''
}

function maxDate(values) {
  const sorted = values.filter(Boolean).sort()
  return sorted[sorted.length - 1] || ''
}

function nextScheduleDateAfter(date) {
  const parsed = parseIsoDate(date)
  if (!parsed) return ''

  let next = addDays(parsed, 1)
  while (next.getUTCDay() === 0) {
    next = addDays(next, 1)
  }
  return toIsoDate(next)
}

function normalizeLaneTestRanges(tests = []) {
  let previousEnd = ''
  return tests.map((test) => {
    let start = test.planned_start_date || ''
    let end = test.planned_end_date || ''

    if (previousEnd && start && start <= previousEnd) {
      start = nextScheduleDateAfter(previousEnd)
      if (end && end < start) end = start
    }

    const days = enumerateScheduleDays(start, end)
    if (end && (!previousEnd || end > previousEnd)) {
      previousEnd = end
    }

    return {
      ...test,
      planned_start_date: start,
      planned_end_date: end,
      days,
      duration_days: days.length
    }
  })
}

export function buildScheduleLanes(rows = []) {
  const lanes = new Map()

  for (const row of rows) {
    const key = laneKey(row)
    if (!lanes.has(key)) {
      lanes.set(key, {
        ...row,
        lane_key: key,
        tests: []
      })
    }
    lanes.get(key).tests.push(row)
  }

  return [...lanes.values()]
    .map((lane) => {
      const tests = normalizeLaneTestRanges([...lane.tests].sort((a, b) => {
        const byStart = String(a.planned_start_date || '').localeCompare(String(b.planned_start_date || ''))
        if (byStart) return byStart
        return Number(a.test_idx || 0) - Number(b.test_idx || 0)
      }))
      const plannedStart = minDate(tests.map((test) => test.planned_start_date))
      const plannedEnd = maxDate(tests.map((test) => test.planned_end_date))
      const days = enumerateScheduleDays(plannedStart, plannedEnd)
      const testsWithLaneLabels = tests.map((test) => {
        const visibleCps = distributeTestCpLabels(
          test.cps || [],
          test.planned_start_date,
          test.planned_end_date,
          6,
          {
            avoidStartDate: test.planned_start_date === plannedStart,
            avoidEndDate: test.planned_end_date === plannedEnd
          }
        )
        return {
          ...test,
          visible_cps: visibleCps,
          scheduled_cps: visibleCps
        }
      })
      const scheduledCps = testsWithLaneLabels.flatMap((test) => test.scheduled_cps || [])
      const visibleCps = testsWithLaneLabels.flatMap((test) => test.visible_cps || [])
      const progressSource = tests.find((test) => test.current_cp_idx !== undefined) || {}
      const actualProgress = buildActualProgress(scheduledCps, progressSource, plannedEnd)
      const testNames = [...new Set(tests.map((test) => test.test_name).filter(Boolean))]
      const scheduleItems = [...new Set(tests.map((test) => test.schedule_test_item).filter(Boolean))]

      return {
        ...lane,
        tests: testsWithLaneLabels,
        test_count: tests.length,
        test_name: lane.wf_name || scheduleItems[0] || lane.test_name,
        test_names: testNames,
        schedule_items: scheduleItems,
        planned_start_date: plannedStart,
        planned_end_date: plannedEnd,
        edge_markers: [
          plannedStart ? { date: plannedStart, label: 'T0', type: 'start' } : null,
          plannedEnd ? { date: plannedEnd, label: 'END', type: 'end' } : null
        ].filter(Boolean),
        days,
        duration_days: days.length,
        scheduled_cps: scheduledCps,
        visible_cps: visibleCps,
        actual_progress: actualProgress
      }
    })
    .sort((a, b) => {
      const byWf = Number(a.wf_num) - Number(b.wf_num)
      if (byWf) return byWf
      const byStart = String(a.planned_start_date || '').localeCompare(String(b.planned_start_date || ''))
      if (byStart) return byStart
      return String(a.config || '').localeCompare(String(b.config || ''))
    })
}

export function buildScheduleDateColumns(rows = []) {
  if (!rows.length) return []

  const starts = rows.map((row) => row.planned_start_date).filter(Boolean).sort()
  const ends = rows.map((row) => row.planned_end_date).filter(Boolean).sort()
  if (!starts.length || !ends.length) return []

  return enumerateCalendarDays(starts[0], ends[ends.length - 1]).map((date) => {
    const parsed = parseIsoDate(date)
    return {
      date,
      monthDay: date.slice(5),
      weekday: parsed
        ? ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][parsed.getUTCDay()]
        : '',
      isSunday: parsed ? parsed.getUTCDay() === 0 : false,
      isSaturday: parsed ? parsed.getUTCDay() === 6 : false
    }
  })
}

export function groupScheduleByWf(rows = []) {
  const groups = new Map()
  for (const row of rows) {
    const wf = String(row.wf_num)
    if (!groups.has(wf)) {
      groups.set(wf, { wf_num: wf, wf_name: row.wf_name || '', rows: [] })
    }
    groups.get(wf).rows.push(row)
  }
  for (const group of groups.values()) {
    const starts = group.rows.map(r => r.planned_start_date).filter(Boolean).sort()
    const ends = group.rows.map(r => r.planned_end_date).filter(Boolean).sort()
    group.planned_start_date = starts[0]
    group.planned_end_date = ends[ends.length - 1]
  }
  return [...groups.values()].sort((a, b) => Number(a.wf_num) - Number(b.wf_num))
}
