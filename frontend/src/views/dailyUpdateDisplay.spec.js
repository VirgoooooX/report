import assert from 'node:assert/strict'
import { buildDailyUpdateKpis } from './dailyUpdateDisplay.js'

const kpis = buildDailyUpdateKpis(
  {
    wf_updates: [
      { wf: '1', configs: [{ cp_delta: 2 }, { cp_delta: 1 }] },
      { wf: '2', configs: [{ cp_delta: 3 }] }
    ]
  },
  [{ sn: 'A' }, { sn: 'B' }],
  { is_consistent: false, only_daily_report: 1, only_fa_tracker: 2 }
)

assert.equal(kpis.find((k) => k.key === 'wfUpdated').value, 2)
assert.equal(kpis.find((k) => k.key === 'cpAdvanced').value, 6)
assert.equal(kpis.find((k) => k.key === 'newIssues').value, 2)
assert.equal(kpis.find((k) => k.key === 'consistency').value, 3)
assert.equal(kpis.find((k) => k.key === 'consistency').tone, 'danger')

const okKpis = buildDailyUpdateKpis({}, [], { is_consistent: true })
assert.equal(okKpis.find((k) => k.key === 'consistency').value, 'OK')
assert.equal(okKpis.find((k) => k.key === 'newIssues').tone, 'success')

console.log('dailyUpdateDisplay KPI tests passed')
