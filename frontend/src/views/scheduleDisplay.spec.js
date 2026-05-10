import assert from 'node:assert/strict'
import {
  buildScheduleDateColumns,
  buildScheduleLanes,
  buildScheduleRows,
  distributeCpsAcrossDays,
  enumerateScheduleDays,
  sampleIndexes
} from './scheduleDisplay.js'

assert.deepEqual(
  enumerateScheduleDays('2026-05-01', '2026-05-04'),
  ['2026-05-01', '2026-05-02', '2026-05-04']
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

const sampled = sampleIndexes(10, 4)
assert.deepEqual([...sampled].sort((a, b) => a - b), [0, 3, 6, 9])

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
    cps: [{ cp_idx: 0, cp_name: 'T0' }]
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
    cps: [{ cp_idx: 1, cp_name: 'End' }]
  }
], 2))
assert.equal(lanes.length, 1)
assert.equal(lanes[0].test_count, 2)
assert.equal(lanes[0].planned_start_date, '2026-04-20')
assert.equal(lanes[0].planned_end_date, '2026-04-25')
assert.deepEqual(lanes[0].tests.map((test) => test.test_name), ['Altitude', 'Rock Tumble'])
assert.deepEqual(lanes[0].test_names, ['Altitude', 'Rock Tumble'])

const columns = buildScheduleDateColumns([
  { planned_start_date: '2026-05-01', planned_end_date: '2026-05-04' },
  { planned_start_date: '2026-05-02', planned_end_date: '2026-05-05' }
])
assert.deepEqual(columns.map((column) => column.date), [
  '2026-05-01',
  '2026-05-02',
  '2026-05-04',
  '2026-05-05'
])
assert.equal(columns.some((column) => column.date === '2026-05-03'), false)
assert.equal(columns.find((column) => column.date === '2026-05-02').isSaturday, true)

console.log('scheduleDisplay tests passed')
