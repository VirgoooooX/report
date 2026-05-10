import { testSummaryCellClass } from './testSummaryDisplay.js'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

// not-started
assert(testSummaryCellClass(null) === 'ts-not-started', 'null → ts-not-started')
assert(testSummaryCellClass({ status: 'not_started' }) === 'ts-not-started', 'not_started → ts-not-started')

// in-progress
assert(testSummaryCellClass({ status: 'in_progress' }) === 'ts-in-progress', 'in_progress → ts-in-progress')
assert(
  testSummaryCellClass({ status: 'in_progress', spec: 1, strife: 0 }) === 'ts-in-progress ts-fail-text',
  'in_progress spec → blue background with red text'
)
assert(
  testSummaryCellClass({ status: 'in_progress', spec: 0, strife: 1 }) === 'ts-in-progress ts-strife-text',
  'in_progress strife → blue background with yellow text'
)

// spec
assert(testSummaryCellClass({ status: 'complete', spec: 1, strife: 0 }) === 'ts-fail', 'spec → ts-fail')

// strife
assert(testSummaryCellClass({ status: 'complete', spec: 0, strife: 1 }) === 'ts-strife', 'strife → ts-strife')

// pass
assert(testSummaryCellClass({ status: 'complete', spec: 0, strife: 0 }) === 'ts-pass', 'pass → ts-pass')

console.log('testSummaryDisplay tests passed')
