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
    return {
      ...segment,
      days,
      duration_days: days.length,
      scheduled_cps: scheduledCps,
      visible_cps: scheduledCps.filter((cp) => cp.visible)
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
      const tests = [...lane.tests].sort((a, b) => {
        const byStart = String(a.planned_start_date || '').localeCompare(String(b.planned_start_date || ''))
        if (byStart) return byStart
        return Number(a.test_idx || 0) - Number(b.test_idx || 0)
      })
      const plannedStart = minDate(tests.map((test) => test.planned_start_date))
      const plannedEnd = maxDate(tests.map((test) => test.planned_end_date))
      const days = enumerateScheduleDays(plannedStart, plannedEnd)
      const scheduledCps = tests.flatMap((test) => test.scheduled_cps || [])
      const visibleCps = tests.flatMap((test) => test.visible_cps || [])
      const testNames = [...new Set(tests.map((test) => test.test_name).filter(Boolean))]
      const scheduleItems = [...new Set(tests.map((test) => test.schedule_test_item).filter(Boolean))]

      return {
        ...lane,
        tests,
        test_count: tests.length,
        test_name: lane.wf_name || scheduleItems[0] || lane.test_name,
        test_names: testNames,
        schedule_items: scheduleItems,
        planned_start_date: plannedStart,
        planned_end_date: plannedEnd,
        days,
        duration_days: days.length,
        scheduled_cps: scheduledCps,
        visible_cps: visibleCps
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

  return enumerateScheduleDays(starts[0], ends[ends.length - 1]).map((date) => {
    const parsed = parseIsoDate(date)
    return {
      date,
      monthDay: date.slice(5),
      weekday: parsed
        ? ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][parsed.getUTCDay()]
        : '',
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
  return [...groups.values()].sort((a, b) => Number(a.wf_num) - Number(b.wf_num))
}
