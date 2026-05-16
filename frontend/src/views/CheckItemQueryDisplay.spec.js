import assert from 'node:assert/strict'
import {
  parseTestParams,
  formatEndTime,
  isFailRecord,
  getRecordStatusClass,
} from './CheckItemQueryDisplay.js'

// ============================================================
// parseTestParams tests
// ============================================================

// null / undefined / empty string → null
assert.equal(parseTestParams(null), null)
assert.equal(parseTestParams(undefined), null)
assert.equal(parseTestParams(''), null)
assert.equal(parseTestParams(0), null)

// Object input → returned as-is
const obj = { 'SPK_Single Tone_A Weighting': 84.201, 'SPK_Sensitivity@2800': -26.685 }
assert.deepEqual(parseTestParams(obj), obj)

// Valid JSON string → parsed object
const jsonStr = '{"param1": 1.5, "param2": "value"}'
assert.deepEqual(parseTestParams(jsonStr), { param1: 1.5, param2: 'value' })

// Invalid JSON string → null
assert.equal(parseTestParams('not valid json'), null)
assert.equal(parseTestParams('{broken'), null)
assert.equal(parseTestParams('undefined'), null)

// Empty object
assert.deepEqual(parseTestParams({}), {})

// Nested JSON string
const nested = '{"a": {"b": 1}}'
assert.deepEqual(parseTestParams(nested), { a: { b: 1 } })

// ============================================================
// formatEndTime tests
// ============================================================

// Valid timestamp with time
assert.equal(formatEndTime('2026-05-14 21:34:13'), '2026-05-14 21:34')

// Valid ISO timestamp
assert.equal(formatEndTime('2026-01-01T00:00:00'), '2026-01-01 00:00')

// Midnight edge case
assert.equal(formatEndTime('2026-12-31 23:59:59'), '2026-12-31 23:59')

// null / undefined / empty → empty string
assert.equal(formatEndTime(null), '')
assert.equal(formatEndTime(undefined), '')
assert.equal(formatEndTime(''), '')

// Invalid date string → returns original string
assert.equal(formatEndTime('not-a-date'), 'not-a-date')
assert.equal(formatEndTime('abc123'), 'abc123')

// ============================================================
// isFailRecord tests
// ============================================================

// FAIL record
assert.equal(isFailRecord({ status: 'FAIL', item: 'FACT' }), true)

// PASS record
assert.equal(isFailRecord({ status: 'PASS', item: 'ISB' }), false)

// null / undefined / non-object
assert.equal(isFailRecord(null), false)
assert.equal(isFailRecord(undefined), false)
assert.equal(isFailRecord('FAIL'), false)

// Missing status field
assert.equal(isFailRecord({}), false)
assert.equal(isFailRecord({ item: 'FACT' }), false)

// Case sensitivity — only exact 'FAIL' matches
assert.equal(isFailRecord({ status: 'fail' }), false)
assert.equal(isFailRecord({ status: 'Fail' }), false)

// ============================================================
// getRecordStatusClass tests
// ============================================================

// PASS → badge-pass
assert.equal(getRecordStatusClass('PASS'), 'badge-pass')

// FAIL → badge-fail
assert.equal(getRecordStatusClass('FAIL'), 'badge-fail')

// Unknown/empty → empty string
assert.equal(getRecordStatusClass(''), '')
assert.equal(getRecordStatusClass(null), '')
assert.equal(getRecordStatusClass(undefined), '')
assert.equal(getRecordStatusClass('UNKNOWN'), '')

// Case sensitivity
assert.equal(getRecordStatusClass('pass'), '')
assert.equal(getRecordStatusClass('fail'), '')

console.log('CheckItemQueryDisplay tests passed')
