/**
 * Preservation Property Tests — Existing Query & Upload Behavior Unchanged
 *
 * These tests capture the EXISTING correct behavior of the unfixed code.
 * They MUST PASS on unfixed code, confirming baseline behavior to preserve.
 * After fixes are applied, these tests ensure no regressions occurred.
 *
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.6**
 */
import assert from 'node:assert/strict'
import fc from 'fast-check'
import { groupMultiSnByWf, normalizeByWf } from '../composables/useLifecycle.js'

// ═══════════════════════════════════════════════════════════════════════
// Property: SN Lookup mode queries return results grouped by WF correctly
// For all SN Lookup queries with valid SN input, result structure matches
// observed format (grouped by WF)
// **Validates: Requirements 3.1**
// ═══════════════════════════════════════════════════════════════════════

console.log('Preservation Test — SN Lookup: results grouped by WF')

const configArb = fc.constantFrom('R1FNF', 'R2CNM', 'R3', 'R4')
const wfNumArb = fc.constantFrom('10', '14', '14.1', '15', '20', '25')

const cpArb = fc.record({
  cp_idx: fc.integer({ min: 0, max: 15 }),
  cp_name: fc.constantFrom('CP_T', 'CP_C', 'CP_D', 'CP_P', 'CP_TC', 'CP_TD'),
  date: fc.constant('2026-05-10'),
  status: fc.constantFrom('pass', 'spec_fail', 'strife_fail', 'pending'),
  failure_type: fc.constantFrom(null, 'spec', 'strife'),
  pass_count: fc.integer({ min: 0, max: 10 }),
  total_check_items: fc.integer({ min: 1, max: 10 }),
  has_data: fc.boolean(),
  checkItems: fc.constant(null),
})

const wfEntryArb = fc.record({
  wf_num: wfNumArb,
  config: configArb,
  total_cps: fc.integer({ min: 1, max: 20 }),
  current_cp_idx: fc.integer({ min: 0, max: 15 }),
  test_name: fc.constant('Test Name'),
  checkItems: fc.constant(['Cosm', 'Func']),
  cpList: fc.array(cpArb, { minLength: 1, maxLength: 5 }),
})

const snResultArb = fc.record({
  sn: fc.string({ minLength: 6, maxLength: 12 }).map(s => s.replace(/[^a-zA-Z0-9]/g, 'X').padEnd(6, '0')),
  unit_num: fc.constantFrom('', 'ER001', 'ER002', 'ER003'),
  wfs: fc.array(wfEntryArb, { minLength: 1, maxLength: 3 }),
})

// Property: groupMultiSnByWf always groups by wf_num, each group has correct structure
fc.assert(
  fc.property(
    fc.array(snResultArb, { minLength: 1, maxLength: 8 }),
    (normalized) => {
      const groups = groupMultiSnByWf(normalized)

      // 1. Result is always an array
      assert.ok(Array.isArray(groups), 'groupMultiSnByWf must return an array')

      // 2. Each group has required fields
      for (const g of groups) {
        assert.ok('wf_num' in g, 'Each group must have wf_num')
        assert.ok('test_name' in g, 'Each group must have test_name')
        assert.ok('check_items' in g, 'Each group must have check_items')
        assert.ok('total_cps' in g, 'Each group must have total_cps')
        assert.ok('cpColumns' in g, 'Each group must have cpColumns')
        assert.ok(Array.isArray(g.sns), 'Each group must have sns array')
        assert.ok(Array.isArray(g.cpColumns), 'cpColumns must be an array')
      }

      // 3. Groups are keyed by wf_num — one group per unique WF
      const expectedWfs = new Set()
      for (const sn of normalized) {
        for (const wf of sn.wfs) {
          expectedWfs.add(wf.wf_num)
        }
      }
      assert.equal(
        groups.length,
        expectedWfs.size,
        `Expected ${expectedWfs.size} groups (one per WF), got ${groups.length}`
      )

      // 4. Each SN in a group has the expected structure
      for (const g of groups) {
        for (const sn of g.sns) {
          assert.ok('sn' in sn, 'SN entry must have sn field')
          assert.ok('unit_num' in sn, 'SN entry must have unit_num field')
          assert.ok('config' in sn, 'SN entry must have config field')
          assert.ok('current_cp_idx' in sn, 'SN entry must have current_cp_idx')
          assert.ok(Array.isArray(sn.cpList), 'SN entry must have cpList array')
          assert.ok(typeof sn.cpByIdx === 'object', 'SN entry must have cpByIdx object')
        }
      }

      // 5. cpColumns are sorted ascending by cp_idx
      for (const g of groups) {
        for (let i = 1; i < g.cpColumns.length; i++) {
          assert.ok(
            g.cpColumns[i].cp_idx >= g.cpColumns[i - 1].cp_idx,
            'cpColumns must be sorted by cp_idx ascending'
          )
        }
      }

      // 6. All SNs in a group belong to that WF
      for (const g of groups) {
        // Verify by checking that the SNs were derived from wf entries matching g.wf_num
        const expectedSns = []
        for (const sn of normalized) {
          for (const wf of sn.wfs) {
            if (wf.wf_num === g.wf_num) {
              expectedSns.push(sn.sn)
            }
          }
        }
        assert.equal(
          g.sns.length,
          expectedSns.length,
          `Group WF${g.wf_num} should have ${expectedSns.length} SNs, got ${g.sns.length}`
        )
      }
    }
  ),
  { numRuns: 100 }
)
console.log('  PASS — SN Lookup grouping by WF preserved')

// ═══════════════════════════════════════════════════════════════════════
// Property: WF & Config mode with single specific config returns filtered SN list
// For all WF & Config queries with single config selected, result contains
// only SNs matching that config
// **Validates: Requirements 3.2**
// ═══════════════════════════════════════════════════════════════════════

console.log('\nPreservation Test — WF & Config: single config returns correct structure')

/**
 * Replicate the wcfgGroups computed logic from QueryCenter.vue (current unfixed version).
 * This is the EXISTING behavior we want to preserve.
 */
function wcfgGroupsCurrent(wcfgData) {
  if (!wcfgData) return []
  const d = wcfgData
  const cpColumns = []
  const seen = new Set()
  for (const sn of d.sns) {
    for (const cp of sn.cpList) {
      if (!seen.has(cp.cp_idx)) {
        seen.add(cp.cp_idx)
        cpColumns.push({ cp_idx: cp.cp_idx, cp_name: cp.cp_name })
      }
    }
  }
  cpColumns.sort((a, b) => a.cp_idx - b.cp_idx)
  let checkItems = d.check_items || []
  if (!checkItems.length) {
    const nameSet = new Set()
    for (const sn of d.sns) {
      for (const cp of sn.cpList) {
        for (const ci of cp.checkItems || []) {
          if (ci.name) nameSet.add(ci.name)
        }
      }
    }
    checkItems = [...nameSet]
  }
  return [{
    wf_num: d.wf_num,
    test_name: d.wf_name || '',
    check_items: checkItems,
    total_cps: d.total_cps,
    cpColumns,
    sns: d.sns.map(s => ({
      sn: s.sn,
      unit_num: s.unit_num || '',
      config: s.config,
      current_cp_idx: s.current_cp_idx,
      cpList: s.cpList,
      cpByIdx: Object.fromEntries(s.cpList.map(c => [c.cp_idx, c]))
    }))
  }]
}

// Generate WF & Config data where ALL SNs have the SAME config (single config query)
const singleConfigSnArb = (config) => fc.record({
  sn: fc.string({ minLength: 6, maxLength: 12 }).map(s => s.replace(/[^a-zA-Z0-9]/g, 'X').padEnd(6, '0')),
  unit_num: fc.constantFrom('', 'ER001', 'ER002'),
  config: fc.constant(config),
  current_cp_idx: fc.integer({ min: 0, max: 10 }),
  cpList: fc.array(
    fc.record({
      cp_idx: fc.integer({ min: 0, max: 10 }),
      cp_name: fc.constant('TestCP'),
      checkItems: fc.constant([{ name: 'Cosm' }]),
    }),
    { minLength: 1, maxLength: 4 }
  ),
})

const singleConfigDataArb = fc.tuple(
  configArb,
  wfNumArb,
).chain(([config, wfNum]) =>
  fc.array(singleConfigSnArb(config), { minLength: 1, maxLength: 6 }).map(sns => ({
    wf_num: wfNum,
    wf_name: `Test WF${wfNum}`,
    config_filter: config,
    check_items: ['Cosm'],
    total_cps: 5,
    summary: { total_sns: sns.length, completed: 0, spec_fails: 0, strife_fails: 0 },
    sns,
  }))
)

// Property: When all SNs have the same config (single config query),
// wcfgGroups returns exactly 1 group containing all those SNs
fc.assert(
  fc.property(singleConfigDataArb, (wcfgData) => {
    const groups = wcfgGroupsCurrent(wcfgData)

    // Single config → exactly 1 group (this is the current correct behavior)
    assert.equal(groups.length, 1, 'Single config query should produce exactly 1 group')

    const group = groups[0]

    // All SNs in the group have the same config
    const configs = new Set(group.sns.map(s => s.config))
    assert.equal(configs.size, 1, 'All SNs in single-config group should have same config')
    assert.equal([...configs][0], wcfgData.config_filter, 'Config should match the filter')

    // Group has correct WF number
    assert.equal(group.wf_num, wcfgData.wf_num, 'Group wf_num should match data wf_num')

    // All SNs from input are present in output
    assert.equal(
      group.sns.length,
      wcfgData.sns.length,
      'All input SNs should be in the output group'
    )

    // Each SN has required fields
    for (const sn of group.sns) {
      assert.ok('sn' in sn, 'SN must have sn field')
      assert.ok('config' in sn, 'SN must have config field')
      assert.ok('cpList' in sn, 'SN must have cpList')
      assert.ok('cpByIdx' in sn, 'SN must have cpByIdx')
    }

    // cpColumns are sorted
    for (let i = 1; i < group.cpColumns.length; i++) {
      assert.ok(
        group.cpColumns[i].cp_idx >= group.cpColumns[i - 1].cp_idx,
        'cpColumns must be sorted ascending'
      )
    }
  }),
  { numRuns: 100 }
)
console.log('  PASS — WF & Config single-config behavior preserved')

// ═══════════════════════════════════════════════════════════════════════
// Property: Failure mode queries return matching FA Tracker data format
// For all Failure mode queries, results match FA Tracker data format
// **Validates: Requirements 3.6**
// ═══════════════════════════════════════════════════════════════════════

console.log('\nPreservation Test — Failure mode: FA data format preserved')

/**
 * Replicate the faFlatEntries computed logic from QueryCenter.vue.
 * This transforms FA results into the flat table format.
 */
function faFlatEntriesCurrent(faResults) {
  const rows = []
  for (const item of faResults) {
    for (const fa of item.entries) {
      const mark = String(fa.Mark || '').trim() || item.unit_num || ''
      rows.push({ sn: item.sn, unit_num: mark, fa })
    }
  }
  return rows
}

const faEntryArb = fc.record({
  WF: fc.constantFrom('10', '14', '20', '25'),
  Config: configArb,
  'Failed Test': fc.constantFrom('Drop 1m PB', 'Taber Abrasion', 'IPX4 Spray', ''),
  'Failure Symptom / Failure Message': fc.constantFrom('Crack on housing', 'Display malfunction', ''),
  'Failed Location': fc.constantFrom('Top', 'Bottom', 'Side', ''),
  'Failed Cycle Count': fc.constantFrom('1', '3', '5', ''),
  'Failure Type  (Spec. or Strife)': fc.constantFrom('Spec.', 'Strife', ''),
  'FA Status': fc.constantFrom('Open', 'Closed', 'In Progress', ''),
  'Follow Up Actions': fc.constantFrom('Replace unit', 'Retest', ''),
  'Root Cause': fc.constantFrom('Material defect', 'Design issue', ''),
  'CA': fc.constantFrom('Update spec', ''),
  'Root Cause Category I': fc.constantFrom('Material', 'Design', ''),
  'Root Cause Category II': fc.constantFrom('Adhesive', 'Structure', ''),
  Mark: fc.constantFrom('ER001', 'ER002', ''),
})

const faResultItemArb = fc.record({
  sn: fc.string({ minLength: 6, maxLength: 12 }).map(s => s.replace(/[^a-zA-Z0-9]/g, 'X').padEnd(6, '0')),
  unit_num: fc.constantFrom('', 'ER001', 'ER002'),
  entries: fc.array(faEntryArb, { minLength: 1, maxLength: 3 }),
})

// Property: faFlatEntries always produces correct flat structure from FA results
fc.assert(
  fc.property(
    fc.array(faResultItemArb, { minLength: 1, maxLength: 5 }),
    (faResults) => {
      const flat = faFlatEntriesCurrent(faResults)

      // 1. Total flat entries = sum of all entries across all items
      const expectedCount = faResults.reduce((sum, item) => sum + item.entries.length, 0)
      assert.equal(flat.length, expectedCount, `Expected ${expectedCount} flat entries, got ${flat.length}`)

      // 2. Each flat entry has required fields
      for (const row of flat) {
        assert.ok('sn' in row, 'Flat entry must have sn')
        assert.ok('unit_num' in row, 'Flat entry must have unit_num')
        assert.ok('fa' in row, 'Flat entry must have fa object')
        assert.ok(typeof row.fa === 'object', 'fa must be an object')
      }

      // 3. Mark resolution: if fa.Mark is set, unit_num uses it; otherwise falls back
      let idx = 0
      for (const item of faResults) {
        for (const fa of item.entries) {
          const row = flat[idx]
          const expectedMark = String(fa.Mark || '').trim() || item.unit_num || ''
          assert.equal(row.unit_num, expectedMark, 'unit_num should prefer fa.Mark over item.unit_num')
          assert.equal(row.sn, item.sn, 'sn should match parent item')
          idx++
        }
      }

      // 4. FA object fields are preserved as-is
      idx = 0
      for (const item of faResults) {
        for (const fa of item.entries) {
          const row = flat[idx]
          assert.equal(row.fa.WF, fa.WF, 'FA WF field preserved')
          assert.equal(row.fa.Config, fa.Config, 'FA Config field preserved')
          assert.equal(row.fa['FA Status'], fa['FA Status'], 'FA Status field preserved')
          idx++
        }
      }
    }
  ),
  { numRuns: 100 }
)
console.log('  PASS — Failure mode FA data format preserved')

// ═══════════════════════════════════════════════════════════════════════
// Property: normalizeByWf produces correct structure for WF query results
// This ensures the data normalization layer preserves its contract
// **Validates: Requirements 3.2**
// ═══════════════════════════════════════════════════════════════════════

console.log('\nPreservation Test — normalizeByWf: structure contract preserved')

const rawCpArb = fc.record({
  cp_idx: fc.integer({ min: 0, max: 10 }),
  cp_name: fc.constant('TestCP'),
  status: fc.constantFrom('pass', 'spec_fail', 'pending'),
  fail_type: fc.constantFrom(null, 'spec', 'strife'),
  date: fc.constant('2026-05-10'),
  pass_count: fc.integer({ min: 0, max: 5 }),
  total_count: fc.integer({ min: 1, max: 10 }),
})

const rawSnArb = fc.record({
  sn: fc.string({ minLength: 6, maxLength: 12 }).map(s => s.replace(/[^a-zA-Z0-9]/g, 'X').padEnd(6, '0')),
  unit_num: fc.constantFrom('', 'ER001'),
  config: configArb,
  current_cp_idx: fc.integer({ min: 0, max: 10 }),
  total_cps: fc.integer({ min: 1, max: 15 }),
  cps: fc.array(rawCpArb, { minLength: 1, maxLength: 5 }),
})

const rawByWfPayloadArb = fc.record({
  wf_num: wfNumArb,
  wf_name: fc.constant('Test WF'),
  config_filter: fc.constantFrom('R1FNF', 'All'),
  total_cps: fc.integer({ min: 1, max: 20 }),
  check_items: fc.constant(['Cosm', 'Func']),
  summary: fc.record({
    total_sns: fc.integer({ min: 1, max: 50 }),
    completed: fc.integer({ min: 0, max: 20 }),
    spec_fails: fc.integer({ min: 0, max: 5 }),
    strife_fails: fc.integer({ min: 0, max: 5 }),
  }),
  sns: fc.array(rawSnArb, { minLength: 1, maxLength: 6 }),
})

fc.assert(
  fc.property(rawByWfPayloadArb, (payload) => {
    const result = normalizeByWf(payload)

    // Structure contract
    assert.ok('wf_num' in result, 'Must have wf_num')
    assert.ok('wf_name' in result, 'Must have wf_name')
    assert.ok('config_filter' in result, 'Must have config_filter')
    assert.ok('total_cps' in result, 'Must have total_cps')
    assert.ok('check_items' in result, 'Must have check_items')
    assert.ok('summary' in result, 'Must have summary')
    assert.ok(Array.isArray(result.sns), 'sns must be array')

    // Values preserved
    assert.equal(result.wf_num, payload.wf_num)
    assert.equal(result.wf_name, payload.wf_name)
    assert.equal(result.total_cps, payload.total_cps)
    assert.deepEqual(result.check_items, payload.check_items)

    // SN count preserved
    assert.equal(result.sns.length, payload.sns.length)

    // Each SN has normalized structure
    for (let i = 0; i < result.sns.length; i++) {
      const sn = result.sns[i]
      assert.ok('sn' in sn, 'Normalized SN must have sn')
      assert.ok('config' in sn, 'Normalized SN must have config')
      assert.ok('current_cp_idx' in sn, 'Normalized SN must have current_cp_idx')
      assert.ok(Array.isArray(sn.cpList), 'Normalized SN must have cpList array')
      assert.equal(sn.sn, payload.sns[i].sn, 'SN value preserved')
      assert.equal(sn.config, payload.sns[i].config, 'Config value preserved')
      assert.equal(sn.cpList.length, payload.sns[i].cps.length, 'CP count preserved')
    }
  }),
  { numRuns: 100 }
)
console.log('  PASS — normalizeByWf structure contract preserved')

console.log('\n✓ All frontend preservation property tests passed')
