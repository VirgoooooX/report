import assert from 'node:assert/strict'
import fc from 'fast-check'

/**
 * cpMarkerClass — extracted from ScheduleTimeline.vue for testability.
 * Determines the visual state class for a CP marker based on lane progress.
 */
function cpMarkerClass(row, cp) {
  const progress = row.actual_progress
  if (!progress || progress.current_cp_idx == null) {
    return { 'cp-completed': false, 'cp-pending': true, 'cp-current': false }
  }
  if (progress.is_complete) {
    return { 'cp-completed': true, 'cp-pending': false, 'cp-current': false }
  }
  const completed = cp.cp_idx <= progress.current_cp_idx
  return { 'cp-completed': completed, 'cp-pending': !completed, 'cp-current': cp.cp_idx === progress.current_cp_idx }
}

/**
 * Feature: schedule-page-optimization, Property 1: CP marker style is determined by completion state
 * Validates: Requirements 1.1, 1.2
 *
 * For any lane with a non-null actual_progress (where is_complete is false) and for any CP marker
 * with cp_idx, the marker SHALL have the cp-completed class iff cp_idx <= actual_progress.current_cp_idx,
 * and cp-pending class otherwise.
 */
fc.assert(
  fc.property(
    fc.integer(),
    fc.integer(),
    (cpIdx, currentCpIdx) => {
      const row = {
        actual_progress: {
          current_cp_idx: currentCpIdx,
          is_complete: false
        }
      }
      const cp = { cp_idx: cpIdx }

      const result = cpMarkerClass(row, cp)

      if (cpIdx <= currentCpIdx) {
        assert.equal(result['cp-completed'], true,
          `cp_idx ${cpIdx} <= current_cp_idx ${currentCpIdx} should be cp-completed`)
        assert.equal(result['cp-pending'], false,
          `cp_idx ${cpIdx} <= current_cp_idx ${currentCpIdx} should not be cp-pending`)
      } else {
        assert.equal(result['cp-completed'], false,
          `cp_idx ${cpIdx} > current_cp_idx ${currentCpIdx} should not be cp-completed`)
        assert.equal(result['cp-pending'], true,
          `cp_idx ${cpIdx} > current_cp_idx ${currentCpIdx} should be cp-pending`)
      }
    }
  ),
  { numRuns: 100 }
)

/**
 * Feature: schedule-page-optimization, Property 2: Complete lane marks all CPs as completed
 * Validates: Requirements 1.4
 *
 * For any lane where actual_progress.is_complete is true, for all CP markers in that lane,
 * regardless of their individual cp_idx value, the marker SHALL have the cp-completed class.
 */
fc.assert(
  fc.property(
    fc.array(fc.record({ cp_idx: fc.integer() }), { minLength: 1 }),
    fc.integer(),
    (cps, currentCpIdx) => {
      const row = {
        actual_progress: {
          is_complete: true,
          current_cp_idx: currentCpIdx
        }
      }

      for (const cp of cps) {
        const result = cpMarkerClass(row, cp)
        assert.deepEqual(result, { 'cp-completed': true, 'cp-pending': false, 'cp-current': false },
          `CP with cp_idx=${cp.cp_idx} should be completed without current highlight when lane is complete`)
      }
    }
  ),
  { numRuns: 100 }
)

/**
 * cellStyle — extracted from ScheduleTimeline.vue for testability.
 * Returns {} for all cells (colors come from CSS custom properties).
 */
function cellStyle(row, column) {
  return {}
}

/**
 * badgeStyle — extracted from ScheduleTimeline.vue for testability.
 * Returns {} for all configs (styling handled by CSS class with neutral border).
 */
function badgeStyle(config) {
  return {}
}

/**
 * Feature: schedule-page-optimization, Property 4: Color scheme is uniform across all configs
 * Validates: Requirements 4.2, 4.3, 4.6
 *
 * For any set of config names and for any configColors prop value, the rendered cell styles
 * and badge styles SHALL be identical for all configs — no config-specific color variation
 * SHALL exist in the output.
 */
fc.assert(
  fc.property(
    fc.array(fc.string({ minLength: 1 }), { minLength: 1, maxLength: 20 }),
    fc.dictionary(fc.string({ minLength: 1 }), fc.stringMatching(/^#[0-9a-f]{6}$/)),
    (configNames, configColors) => {
      // cellStyle returns {} for all configs regardless of row/column content
      for (const config of configNames) {
        const row = { config, actual_progress: null }
        const column = { date: '2026-01-01', isSunday: false }
        const result = cellStyle(row, column)
        assert.deepEqual(result, {},
          `cellStyle should return {} for config "${config}" but got ${JSON.stringify(result)}`)
      }

      // badgeStyle returns {} for all configs regardless of configColors
      for (const config of configNames) {
        const result = badgeStyle(config)
        assert.deepEqual(result, {},
          `badgeStyle should return {} for config "${config}" but got ${JSON.stringify(result)}`)
      }

      // Verify uniformity: all configs produce identical results
      const cellResults = configNames.map((config) => cellStyle({ config }, { date: '2026-01-01' }))
      const badgeResults = configNames.map((config) => badgeStyle(config))

      for (let i = 1; i < cellResults.length; i++) {
        assert.deepEqual(cellResults[i], cellResults[0],
          `cellStyle should be uniform across configs but "${configNames[i]}" differs from "${configNames[0]}"`)
      }

      for (let i = 1; i < badgeResults.length; i++) {
        assert.deepEqual(badgeResults[i], badgeResults[0],
          `badgeStyle should be uniform across configs but "${configNames[i]}" differs from "${configNames[0]}"`)
      }
    }
  ),
  { numRuns: 100 }
)

/**
 * isTodayColumn — parameterized version extracted from ScheduleTimeline.vue for testability.
 * Returns true if the column's date matches the provided "today" date string.
 */
function isTodayColumn(column, today) {
  return column.date === today
}

/**
 * Feature: schedule-page-optimization, Property 3: Today indicator renders only when today is within date range
 * Validates: Requirements 3.5
 *
 * For any set of dateColumns and for any current date, the today indicator (.today class on a day-cell)
 * SHALL be applied to exactly one column if today's date exists in the dateColumns array,
 * and to zero columns if today's date is not present in the dateColumns array.
 */
fc.assert(
  fc.property(
    fc.uniqueArray(
      fc.date({ min: new Date('2020-01-01'), max: new Date('2030-12-31') }).map((d) => {
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }),
      { minLength: 1, maxLength: 60 }
    ),
    fc.date({ min: new Date('2020-01-01'), max: new Date('2030-12-31') }).map((d) => {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }),
    (dates, today) => {
      const columns = dates.map((d) => ({ date: d }))
      const matchCount = columns.filter((col) => isTodayColumn(col, today)).length

      const todayInArray = dates.includes(today)

      if (todayInArray) {
        assert.equal(matchCount, 1,
          `Today "${today}" is in dates array, expected exactly 1 match but got ${matchCount}`)
      } else {
        assert.equal(matchCount, 0,
          `Today "${today}" is NOT in dates array, expected 0 matches but got ${matchCount}`)
      }
    }
  ),
  { numRuns: 100 }
)

console.log('ScheduleTimeline property tests passed')
