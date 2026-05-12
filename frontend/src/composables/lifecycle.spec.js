// Node-only test file (mirrors the project's existing .spec.js convention).
import assert from 'node:assert/strict'
import { normalizeCp, normalizeTimeline, normalizeByWf, groupMultiSnByWf }
  from './useLifecycle.js'

// normalizeCp marks has_data correctly
{
  const cp = normalizeCp({ cp_idx: 0, cp_name: 'T0', status: 'pass', pass_count: 4, total_count: 4 })
  assert.equal(cp.has_data, true)
  assert.equal(cp.pass_count, 4)
}

// groupMultiSnByWf groups by WF and unions CP columns
{
  const normalized = [
    { sn: 'A', wfs: [{ wf_num: '10', config: 'R1FNF', total_cps: 5, current_cp_idx: 4,
        checkItems: ['C1'], cpList: [
          normalizeCp({ cp_idx: 0, cp_name: 'T0', status: 'pass', pass_count: 1, total_count: 1 }),
          normalizeCp({ cp_idx: 4, cp_name: 'D40', status: 'fail', pass_count: 0, total_count: 1 }),
        ]}]},
    { sn: 'B', wfs: [{ wf_num: '10', config: 'R3', total_cps: 5, current_cp_idx: 1,
        checkItems: ['C1'], cpList: [
          normalizeCp({ cp_idx: 0, cp_name: 'T0', status: 'pass', pass_count: 1, total_count: 1 }),
          normalizeCp({ cp_idx: 1, cp_name: 'D10', status: 'pass', pass_count: 1, total_count: 1 }),
        ]}]},
  ]
  const groups = groupMultiSnByWf(normalized)
  assert.equal(groups.length, 1)
  assert.equal(groups[0].wf_num, '10')
  assert.deepEqual(groups[0].cpColumns.map(c => c.cp_idx), [0, 1, 4])
  assert.equal(groups[0].sns.length, 2)
  // SN B has no data for cp_idx=4 → cpByIdx lookup returns undefined.
  assert.equal(groups[0].sns[1].cpByIdx[4], undefined)
}

// normalizeTimeline passes items through
{
  const payload = { results: [{ sn: 'A', wfs: [{ wf_num: '10', config: 'R1FNF',
      total_cps: 1, current_cp_idx: 0, cps: [
        { cp_idx: 0, cp_name: 'T0', status: 'pass', pass_count: 1, total_count: 1,
          items: [{ name: 'Cosm', status: 'pass' }] },
      ]}]}]}
  const n = normalizeTimeline(payload)
  assert.equal(n[0].wfs[0].cpList[0].checkItems[0].name, 'Cosm')
}

console.log('useLifecycle.js tests passed')
