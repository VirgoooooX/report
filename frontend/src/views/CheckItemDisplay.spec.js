import assert from 'node:assert/strict'
import {
  identifyCsvType,
  formatStats,
  formatDate,
  CHECK_ITEM_TYPES,
  REQUIRED_BASE_FILE_TYPES,
  OPTIONAL_BASE_FILE_TYPES,
  getBaseStatusMap,
  getMissingRequiredBaseFiles,
  isBaseReadyForGeneration,
} from './CheckItemDisplay.js'

// ============================================================
// identifyCsvType tests
// ============================================================

// Known keywords — each should return the correct item type
assert.equal(identifyCsvType('REL_BT-OTA_20260515.csv'), 'BT-OTA')
assert.equal(identifyCsvType('ORT-Charging_results.csv'), 'Charging')
assert.equal(identifyCsvType('ORT-FACT_daily_export.csv'), 'FACT')
assert.equal(identifyCsvType('ORT-ISB_20260515.csv'), 'ISB')
assert.equal(identifyCsvType('Touch-Cal-Post_report.csv'), 'Touch-CAL-Post')
assert.equal(identifyCsvType('REL-COSMETIC_data.csv'), 'Cosmetic')

// Case insensitivity
assert.equal(identifyCsvType('BT-OTA_UPPER.csv'), 'BT-OTA')
assert.equal(identifyCsvType('bt-ota_lower.csv'), 'BT-OTA')
assert.equal(identifyCsvType('CHARGING_MIX.csv'), 'Charging')
assert.equal(identifyCsvType('touch-CAL-POST_mixed.csv'), 'Touch-CAL-Post')

// Unrecognized filenames
assert.equal(identifyCsvType('random_data.csv'), null)
assert.equal(identifyCsvType('report_2026.csv'), null)
assert.equal(identifyCsvType(''), null)
assert.equal(identifyCsvType(null), null)
assert.equal(identifyCsvType(undefined), null)

// Priority: first match wins (bt-ota before others)
assert.equal(identifyCsvType('bt-ota_charging_combined.csv'), 'BT-OTA')

// ============================================================
// formatStats tests
// ============================================================

// sn_mapping
assert.equal(
  formatStats('sn_mapping', { sn_count: 200, config_count: 4, wf_count: 42 }),
  '200 SNs, 4 configs, 42 WFs'
)
assert.equal(
  formatStats('sn_mapping', { sn_count: 50 }),
  '50 SNs'
)
assert.equal(
  formatStats('sn_mapping', {}),
  ''
)
assert.equal(
  formatStats('sn_mapping', null),
  ''
)

// checkpoint_schedule
assert.equal(
  formatStats('checkpoint_schedule', { wf_count: 42, cp_count: 287 }),
  '42 WFs, 287 CPs'
)
assert.equal(
  formatStats('checkpoint_schedule', { wf_count: 10 }),
  '10 WFs'
)
assert.equal(
  formatStats('checkpoint_schedule', { cp_count: 100 }),
  '100 CPs'
)

// test_plan
assert.equal(
  formatStats('test_plan', { wf_count: 42, test_count: 126 }),
  '42 WFs, 126 tests'
)
assert.equal(
  formatStats('test_plan', { test_count: 5 }),
  '5 tests'
)

// test_schedule
assert.equal(
  formatStats('test_schedule', { segment_count: 38 }),
  '38 schedule segments'
)
assert.equal(
  formatStats('test_schedule', {}),
  ''
)

// Unknown file type falls back to JSON
assert.equal(
  formatStats('unknown_type', { foo: 'bar' }),
  JSON.stringify({ foo: 'bar' })
)

// ============================================================
// formatDate tests
// ============================================================

// Valid ISO date string
const formatted = formatDate('2026-05-15T10:00:00')
assert.ok(formatted.length > 0, 'Should produce a non-empty string for valid date')
// The exact format depends on locale, but it should not be the raw ISO string
assert.notEqual(formatted, '2026-05-15T10:00:00')

// Valid date-only string
const dateOnly = formatDate('2026-05-15')
assert.ok(dateOnly.length > 0, 'Should produce a non-empty string for date-only input')

// Empty/null/undefined
assert.equal(formatDate(''), '')
assert.equal(formatDate(null), '')
assert.equal(formatDate(undefined), '')

// Invalid date string — returns original string
assert.equal(formatDate('not-a-date'), 'not-a-date')
assert.equal(formatDate('abc123'), 'abc123')

// ============================================================
// Base-first workflow helpers
// ============================================================

assert.deepEqual(CHECK_ITEM_TYPES, ['BT-OTA', 'Charging', 'FACT', 'ISB', 'Touch-CAL-Post', 'Cosmetic'])
assert.deepEqual(REQUIRED_BASE_FILE_TYPES, ['sn_mapping', 'checkpoint_schedule', 'test_plan'])
assert.deepEqual(OPTIONAL_BASE_FILE_TYPES, ['test_schedule'])

const completeBaseFiles = [
  { file_type: 'sn_mapping', uploaded_at: '2026-05-15T10:00:00' },
  { file_type: 'checkpoint_schedule', uploaded_at: '2026-05-15T10:01:00' },
  { file_type: 'test_plan', uploaded_at: '2026-05-15T10:02:00' },
  { file_type: 'test_schedule', uploaded_at: '2026-05-15T10:03:00' },
]

assert.deepEqual(
  Object.keys(getBaseStatusMap(completeBaseFiles)).sort(),
  ['checkpoint_schedule', 'sn_mapping', 'test_plan', 'test_schedule']
)
assert.equal(isBaseReadyForGeneration(completeBaseFiles), true)
assert.deepEqual(getMissingRequiredBaseFiles(completeBaseFiles), [])

const incompleteBaseFiles = [
  { file_type: 'sn_mapping', uploaded_at: '2026-05-15T10:00:00' },
]

assert.equal(isBaseReadyForGeneration(incompleteBaseFiles), false)
assert.deepEqual(
  getMissingRequiredBaseFiles(incompleteBaseFiles),
  ['checkpoint_schedule', 'test_plan']
)
assert.equal(isBaseReadyForGeneration(null), false)
assert.deepEqual(getMissingRequiredBaseFiles(undefined), REQUIRED_BASE_FILE_TYPES)

console.log('CheckItemDisplay tests passed')
