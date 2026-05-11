import assert from 'node:assert/strict'
import {
  buildScheduleDateColumns,
  buildScheduleLanes,
  buildScheduleRows,
  buildActualProgress,
  distributeDailyCpLabels,
  distributeTestCpLabels,
  enumerateCalendarDays,
  distributeCpsAcrossDays,
  enumerateScheduleDays,
  sampleIndexes,
  summarizeDailyCpMarkers
} from './scheduleDisplay.js'

assert.deepEqual(
  enumerateScheduleDays('2026-05-01', '2026-05-04'),
  ['2026-05-01', '2026-05-02', '2026-05-04']
)

assert.deepEqual(
  enumerateCalendarDays('2026-05-01', '2026-05-04'),
  ['2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04']
)

const cpPlacement = distributeCpsAcrossDays(
  Array.from({ length: 5 }, (_, index) => ({ cp_idx: index, cp_name: `CP${index + 1}` })),
  '2026-05-01',
  '2026-05-04',
  3
)
assert.equal(cpPlacement.length, 5)
assert.equal(cpPlacement[0].planned_date, '2026-05-01')
assert.equal(cpPlacement[4].planned_date, '2026-05-04')
assert.ok(cpPlacement.every((cp) => cp.planned_date !== '2026-05-03'))

const dailyCpLabels = distributeDailyCpLabels(
  Array.from({ length: 6 }, (_, index) => ({ cp_idx: index, cp_name: `CP${index + 1}` })),
  '2026-05-01',
  '2026-05-05'
)
assert.deepEqual(dailyCpLabels.map((cp) => cp.planned_date), ['2026-05-02', '2026-05-04'])
assert.deepEqual(dailyCpLabels.map((cp) => cp.cp_name), ['CP3', 'CP6'])

const sampled = sampleIndexes(10, 4)
assert.deepEqual([...sampled].sort((a, b) => a - b), [0, 3, 6, 9])

const denseDailyCpLabels = distributeTestCpLabels(
  Array.from({ length: 12 }, (_, index) => ({ cp_idx: index, cp_name: `CP${index + 1}` })),
  '2026-06-01',
  '2026-06-09',
  6
)
assert.deepEqual(denseDailyCpLabels.map((cp) => cp.planned_date), [
  '2026-06-01',
  '2026-06-02',
  '2026-06-02',
  '2026-06-03',
  '2026-06-04',
  '2026-06-04',
  '2026-06-05',
  '2026-06-06',
  '2026-06-06',
  '2026-06-08',
  '2026-06-09',
  '2026-06-09'
])
assert.deepEqual(denseDailyCpLabels.map((cp) => cp.display_cp_idx), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

const longCycleCpLabels = distributeTestCpLabels(
  Array.from({ length: 3 }, (_, index) => ({ cp_idx: index, cp_name: `CP${index + 1}` })),
  '2026-06-01',
  '2026-06-22',
  6,
  { avoidStartDate: true }
)
assert.deepEqual(longCycleCpLabels.map((cp) => cp.planned_date), [
  '2026-06-08',
  '2026-06-15',
  '2026-06-22'
])

const dailyMarker = summarizeDailyCpMarkers([
  { test_idx: 1, cp_idx: 1, display_cp_idx: 2, cp_name: 'Thermal checkpoint' },
  { test_idx: 1, cp_idx: 2, display_cp_idx: 3, cp_name: 'Voltage checkpoint' },
  { test_idx: 1, cp_idx: 3, display_cp_idx: 4, cp_name: 'Final measurement' }
])
assert.equal(dailyMarker.length, 1)
assert.equal(dailyMarker[0].display_cp_idx, 4)
assert.equal(dailyMarker[0].cp_title, 'Thermal checkpoint\nVoltage checkpoint\nFinal measurement')

const actualProgress = buildActualProgress(
  [
    { cp_idx: 0, planned_date: '2026-06-01' },
    { cp_idx: 1, planned_date: '2026-06-02' },
    { cp_idx: 2, planned_date: '2026-06-03' },
    { cp_idx: 3, planned_date: '2026-06-04' }
  ],
  {
    current_cp_idx: 2,
    current_cp_name: 'CP3',
    total_cps: 4,
    sn_count: 3
  }
)
assert.deepEqual(actualProgress, {
  current_cp_idx: 2,
  current_cp_name: 'CP3',
  total_cps: 4,
  sn_count: 3,
  end_date: '2026-06-03'
})
assert.equal(
  buildActualProgress([{ cp_idx: 0, planned_date: '2026-06-01' }], { current_cp_idx: null }),
  null
)

const rows = buildScheduleRows([
  {
    wf_num: '17',
    config: 'R1FNF',
    test_idx: 1,
    test_name: '3G RMS Random Vibration',
    planned_start_date: '2026-04-27',
    planned_end_date: '2026-05-02',
    cps: Array.from({ length: 8 }, (_, index) => ({ cp_idx: index, cp_name: `Axis ${index}` }))
  }
], 4)
assert.equal(rows[0].duration_days, 6)
assert.equal(rows[0].scheduled_cps.length, 8)
assert.equal(rows[0].visible_cps.length, 4)

const lanes = buildScheduleLanes(buildScheduleRows([
  {
    wf_num: '4',
    wf_name: 'Altitude + Rock Tumble',
    config: 'R1FNF',
    test_idx: 1,
    test_name: 'Altitude',
    schedule_test_item: 'Altitude',
    planned_start_date: '2026-04-20',
    planned_end_date: '2026-04-22',
    cps: [{ cp_idx: 0, cp_name: 'T0' }, { cp_idx: 1, cp_name: 'Alt CP2' }]
  },
  {
    wf_num: '4',
    wf_name: 'Altitude + Rock Tumble',
    config: 'R1FNF',
    test_idx: 2,
    test_name: 'Rock Tumble',
    schedule_test_item: 'Rock Tumble',
    planned_start_date: '2026-04-23',
    planned_end_date: '2026-04-25',
    cps: [{ cp_idx: 9, cp_name: 'RT CP1' }, { cp_idx: 10, cp_name: 'End' }]
  }
], 2))
assert.equal(lanes.length, 1)
assert.equal(lanes[0].test_count, 2)
assert.equal(lanes[0].planned_start_date, '2026-04-20')
assert.equal(lanes[0].planned_end_date, '2026-04-25')
assert.deepEqual(lanes[0].tests.map((test) => test.test_name), ['Altitude', 'Rock Tumble'])
assert.deepEqual(lanes[0].test_names, ['Altitude', 'Rock Tumble'])
assert.deepEqual(lanes[0].edge_markers, [
  { date: '2026-04-20', label: 'T0', type: 'start' },
  { date: '2026-04-25', label: 'END', type: 'end' }
])
assert.deepEqual(
  lanes[0].tests[0].visible_cps.map((cp) => [cp.cp_idx, cp.display_cp_idx, cp.planned_date]),
  [[0, 1, '2026-04-21'], [1, 2, '2026-04-22']]
)
assert.deepEqual(
  lanes[0].tests[1].visible_cps.map((cp) => [cp.cp_idx, cp.display_cp_idx, cp.planned_date]),
  [[9, 1, '2026-04-23'], [10, 2, '2026-04-24']]
)

const singleCpLane = buildScheduleLanes(buildScheduleRows([
  {
    wf_num: '5',
    wf_name: 'Single CP Test',
    config: 'R3',
    test_idx: 1,
    test_name: 'Functional',
    planned_start_date: '2026-05-04',
    planned_end_date: '2026-05-06',
    cps: [{ cp_idx: 42, cp_name: 'Only CP' }]
  },
  {
    wf_num: '5',
    wf_name: 'Single CP Test',
    config: 'R3',
    test_idx: 2,
    test_name: 'Final',
    planned_start_date: '2026-05-07',
    planned_end_date: '2026-05-09',
    cps: [{ cp_idx: 43, cp_name: 'Final CP' }]
  }
], 2))[0]
assert.equal(singleCpLane.tests[0].visible_cps[0].planned_date, '2026-05-06')
assert.equal(singleCpLane.tests[0].visible_cps[0].display_cp_idx, 1)
assert.equal(singleCpLane.tests[1].visible_cps[0].planned_date, '2026-05-08')
assert.equal(singleCpLane.tests[1].visible_cps[0].display_cp_idx, 1)

const columns = buildScheduleDateColumns([
  { planned_start_date: '2026-05-01', planned_end_date: '2026-05-04' },
  { planned_start_date: '2026-05-02', planned_end_date: '2026-05-05' }
])
assert.deepEqual(columns.map((column) => column.date), [
  '2026-05-01',
  '2026-05-02',
  '2026-05-03',
  '2026-05-04',
  '2026-05-05'
])
assert.equal(columns.find((column) => column.date === '2026-05-02').isSaturday, true)
assert.equal(columns.find((column) => column.date === '2026-05-03').isSunday, true)

console.log('scheduleDisplay tests passed')
