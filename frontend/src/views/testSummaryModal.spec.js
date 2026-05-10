import { CELL_ISSUE_COLUMNS, buildFaListUrl, buildCellFailuresUrl, buildCellIssueRows } from './testSummaryModal.js'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const url = buildFaListUrl({
  wf: 'WF10',
  cfg: 'R3',
  test: 'Drop Test',
  sns: ['SN001', ' ', 'SN002']
})

assert(
  url === '/api/fa/list?wf=WF10&config=R3&failed_test=Drop+Test&sns=SN001%2CSN002',
  `cell FA URL should include wf/config/test/sns, got ${url}`
)

assert(
  buildFaListUrl({}) === '/api/fa/list',
  'empty context should still produce the base FA list URL'
)

const relaxedFaUrl = buildFaListUrl({
  wf: 'WF15.3',
  cfg: 'R3',
  test: '18 Sided Drop 1m Granite SeqC- Margin',
  sns: ['FG7P2T3HX6'],
  includeTest: false,
})

assert(
  relaxedFaUrl === '/api/fa/list?wf=WF15.3&config=R3&sns=FG7P2T3HX6',
  `cell FA URL should be able to omit exact failed_test filtering, got ${relaxedFaUrl}`
)

// Cell failures URL
const cellUrl = buildCellFailuresUrl({
  wf: '37',
  cfg: 'R3',
  testIdx: 0,
  sns: ['SN001', 'SN002']
})

assert(
  cellUrl === '/api/cell-failures?wf=37&config=R3&test_idx=0&sns=SN001%2CSN002',
  `cell failures URL should encode wf/config/test_idx/sns, got ${cellUrl}`
)

assert(
  buildCellFailuresUrl({ wf: '37', cfg: 'R3', testIdx: 0, sns: [] }) === '/api/cell-failures?wf=37&config=R3&test_idx=0',
  'empty sns should still produce the base URL without sns param'
)

const rows = buildCellIssueRows({
  cellFailures: [
    {
      sn: 'SN001',
      cps: [
        {
          cp_name: 'CP1',
          check_items: [
            { check_item: 'FACT', raw_value: '2.5', normalized_value: 'FAIL', failure_type: 'spec' }
          ]
        }
      ]
    },
    {
      sn: 'SN002',
      cps: [
        {
          cp_name: 'CP2',
          check_items: [
            { check_item: 'DROP', raw_value: 'FAIL', normalized_value: 'FAIL', failure_type: 'strife' }
          ]
        }
      ]
    }
  ],
  faRecords: [
    {
      SN: 'SN001',
      'Failed Test': 'Drop Test',
      'Failure Symptom / Failure Message': 'screen crack'
    },
    {
      SN: 'SN003',
      'Failed Test': 'Drop Test',
      'Failure Symptom / Failure Message': 'cannot boot'
    }
  ]
})

assert(rows.length === 3, `merged issue rows should include two Daily Report rows and one FA-only row, got ${rows.length}`)
assert(rows[0].source === 'matched', `SN001 should be matched, got ${rows[0].source}`)
assert(rows[0].failed_test === 'Drop Test', `matched row should include FA failed_test, got ${rows[0].failed_test}`)
assert(rows[1].source === 'only_daily_report', `SN002 should be Daily Report only, got ${rows[1].source}`)
assert(rows[2].source === 'only_fa_tracker', `SN003 should be FA Tracker only, got ${rows[2].source}`)

const looselyMatchedRows = buildCellIssueRows({
  testName: '18 Sided Drop 1m Granite SeqC- Margin',
  cellFailures: [
    {
      sn: 'FG7P2T3HX6',
      cps: [
        {
          cp_name: 'CP1',
          check_items: [
            { check_item: 'DROP', raw_value: 'FAIL', normalized_value: 'FAIL', failure_type: 'strife' }
          ]
        }
      ]
    }
  ],
  faRecords: [
    {
      SN: 'FG7P2T3HX6',
      'Failed Test': '18 Sided Drop 1m Granite SeqC-Margin',
      'Failed Cycle Count': 'SeqC',
      'Failure Symptom / Failure Message': 'corner dent'
    }
  ]
})

assert(
  looselyMatchedRows[0].source === 'matched',
  `test names with punctuation spacing differences should still match, got ${looselyMatchedRows[0].source}`
)
assert(
  looselyMatchedRows[0].symptom === 'corner dent',
  `loosely matched FA details should be copied into the row, got ${looselyMatchedRows[0].symptom}`
)

const columnKeys = CELL_ISSUE_COLUMNS.map(column => column.key)
assert(!columnKeys.includes('cp_name'), 'visible issue table should not include CP column')
assert(!columnKeys.includes('check_item'), 'visible issue table should not include Check Item column')
assert(!columnKeys.includes('value'), 'visible issue table should not include Value column')
assert(
  columnKeys.join(',') === 'sn,type,failed_test,failed_cycle,symptom,location,source',
  `visible issue table should stay compact, got ${columnKeys.join(',')}`
)

console.log('testSummaryModal tests passed')
