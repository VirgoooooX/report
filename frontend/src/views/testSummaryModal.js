export const CELL_ISSUE_COLUMNS = [
  { key: 'sn', label: 'SN' },
  { key: 'type', label: 'Type' },
  { key: 'failed_test', label: 'Failed Test' },
  { key: 'failed_cycle', label: 'Cycle' },
  { key: 'symptom', label: 'Symptom' },
  { key: 'location', label: 'Location' },
  { key: 'source', label: 'Source' },
]

export function buildFaListUrl({ wf, cfg, test, sns = [], includeTest = true } = {}) {
  const params = new URLSearchParams()
  if (wf) params.set('wf', wf)
  if (cfg) params.set('config', cfg)
  if (includeTest && test) params.set('failed_test', test)

  const cleanSns = sns.map(sn => String(sn).trim()).filter(Boolean)
  if (cleanSns.length) params.set('sns', cleanSns.join(','))

  const query = params.toString()
  return query ? `/api/fa/list?${query}` : '/api/fa/list'
}

export function buildCellFailuresUrl({ wf, cfg, testIdx, sns = [] } = {}) {
  const params = new URLSearchParams()
  if (wf) params.set('wf', wf)
  if (cfg) params.set('config', cfg)
  if (testIdx !== undefined && testIdx !== null) params.set('test_idx', testIdx)

  const cleanSns = sns.map(sn => String(sn).trim()).filter(Boolean)
  if (cleanSns.length) params.set('sns', cleanSns.join(','))

  const query = params.toString()
  return query ? `/api/cell-failures?${query}` : '/api/cell-failures'
}

function getField(record, candidates) {
  for (const key of candidates) {
    if (record?.[key] !== undefined && record?.[key] !== null && String(record[key]).trim()) {
      return String(record[key]).trim()
    }
  }
  const lowered = new Map(Object.entries(record || {}).map(([key, value]) => [key.toLowerCase(), value]))
  for (const key of candidates) {
    const value = lowered.get(key.toLowerCase())
    if (value !== undefined && value !== null && String(value).trim()) return String(value).trim()
  }
  return ''
}

function normalizeType(value) {
  const text = String(value || '').toLowerCase()
  if (text.includes('spec')) return 'spec'
  if (text.includes('strife')) return 'strife'
  return String(value || '').trim()
}

function normalizeTestName(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[–—]/g, '-')
    .replace(/\s*-\s*/g, '-')
    .replace(/[^a-z0-9]+/g, '')
}

function buildFaRecordMap(faRecords, testName) {
  const targetTest = normalizeTestName(testName)
  const faBySn = new Map()

  for (const record of faRecords) {
    const sn = getField(record, ['SN', 'sn'])
    if (!sn) continue
    if (!faBySn.has(sn)) faBySn.set(sn, [])
    faBySn.get(sn).push(record)
  }

  const selected = new Map()
  for (const [sn, records] of faBySn.entries()) {
    const matched = targetTest
      ? records.find(record => normalizeTestName(getField(record, ['Failed Test'])) === targetTest)
      : null
    selected.set(sn, matched || records[0])
  }

  return selected
}

export function buildCellIssueRows({ cellFailures = [], faRecords = [], testName = '' } = {}) {
  const faBySn = buildFaRecordMap(faRecords, testName)
  const dailyReportSns = new Set()
  const rows = []

  for (const snFailure of cellFailures) {
    const sn = String(snFailure?.sn || '').trim()
    if (!sn) continue
    dailyReportSns.add(sn)

    const faRecord = faBySn.get(sn)
    const cps = Array.isArray(snFailure?.cps) ? snFailure.cps : []
    for (const cp of cps) {
      const checkItems = Array.isArray(cp?.check_items) ? cp.check_items : []
      for (const item of checkItems) {
        rows.push({
          sn,
          cp_name: cp?.cp_name || '',
          check_item: item?.check_item || '',
          value: item?.raw_value || item?.normalized_value || '',
          type: normalizeType(item?.failure_type || getField(faRecord, ['Failure Type  (Spec. or Strife)', 'Failure Type'])),
          failed_test: getField(faRecord, ['Failed Test']),
          symptom: getField(faRecord, ['Failure Symptom / Failure Message', 'Failure Symptom', 'Symptom']),
          location: getField(faRecord, ['Failed Location', 'Location']),
          failed_cycle: getField(faRecord, ['Failed Cycle Count', 'Failed Cycle']),
          source: faRecord ? 'matched' : 'only_daily_report',
        })
      }
    }
  }

  for (const record of faRecords) {
    const sn = getField(record, ['SN', 'sn'])
    if (!sn || dailyReportSns.has(sn)) continue
    rows.push({
      sn,
      cp_name: '',
      check_item: '',
      value: '',
      type: normalizeType(getField(record, ['Failure Type  (Spec. or Strife)', 'Failure Type'])),
      failed_test: getField(record, ['Failed Test']),
      symptom: getField(record, ['Failure Symptom / Failure Message', 'Failure Symptom', 'Symptom']),
      location: getField(record, ['Failed Location', 'Location']),
      failed_cycle: getField(record, ['Failed Cycle Count', 'Failed Cycle']),
      source: 'only_fa_tracker',
    })
  }

  return rows
}
