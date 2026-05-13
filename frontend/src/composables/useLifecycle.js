// frontend/src/composables/useLifecycle.js
// Pure adapter functions — no Vue imports required.

/**
 * Normalize one CP object from either /api/query/by-wf or /api/query/sn-timeline
 * into a shape consumed by the compare view.
 */
export function normalizeCp(cp) {
  if (!cp || typeof cp !== 'object') return null
  const hasData = cp.status && cp.status !== 'pending'
  return {
    cp_idx: cp.cp_idx,
    cp_name: cp.cp_name || `CP${cp.cp_idx + 1}`,
    date: cp.date || '',
    status: cp.status || 'pending',
    failure_type: cp.fail_type || cp.failure_type || null,
    pass_count: cp.pass_count ?? 0,
    total_check_items: cp.total_count ?? cp.total_check_items ?? 0,
    has_data: hasData,
    // Inline items available from sn-timeline; null from by-wf (load lazily).
    checkItems: Array.isArray(cp.items)
      ? cp.items.map(i => ({
          name: i.name || i.check_item,
          status: i.status,
          failure_type: i.failure_type || null,
        }))
      : null,
  }
}

/**
 * /api/query/sn-timeline → per-SN grouped by WF.
 * Returns: [{sn, unit_num, wfs: [{wf_num, config, total_cps, current_cp_idx, cpList, checkItems}]}]
 */
export function normalizeTimeline(payload) {
  const results = payload?.results || []
  return results.map(r => ({
    sn: r.sn,
    unit_num: r.unit_num || '',
    wfs: (r.wfs || []).map(w => ({
      wf_num: w.wf_num,
      config: w.config,
      total_cps: w.total_cps,
      current_cp_idx: w.current_cp_idx,
      test_name: w.test_name || '',
      // Distinct check item names seen across this WF (for global filter dropdown).
      checkItems: deriveCheckItemNames(w.cps),
      cpList: (w.cps || []).map(normalizeCp),
    })),
  }))
}

/**
 * /api/query/by-wf → flat SN list plus WF-level metadata.
 * Returns: {wf_num, wf_name, config_filter, total_cps, check_items, summary, sns: [...]}
 */
export function normalizeByWf(payload) {
  if (!payload) return { sns: [], check_items: [], summary: {} }
  return {
    wf_num: payload.wf_num,
    wf_name: payload.wf_name,
    config_filter: payload.config_filter,
    total_cps: payload.total_cps,
    check_items: payload.check_items || [],
    summary: payload.summary || {},
    sns: (payload.sns || []).map(s => ({
      sn: s.sn,
      unit_num: s.unit_num || '',
      config: s.config,
      current_cp_idx: s.current_cp_idx,
      total_cps: s.total_cps,
      cpList: (s.cps || []).map(normalizeCp),
    })),
  }
}

/**
 * Group multi-SN results by WF only (not by WF+Config) — CP columns are defined
 * by the WF, so this guarantees every row in a group has matching CP columns.
 * SNs in the same WF under different configs still share the same CP structure.
 */
export function groupMultiSnByWf(normalized) {
  const groups = new Map()
  for (const sn of normalized) {
    for (const wf of sn.wfs) {
      const key = wf.wf_num
      if (!groups.has(key)) {
        groups.set(key, {
          wf_num: wf.wf_num,
          test_name: wf.test_name,
          check_items: wf.checkItems,
          total_cps: wf.total_cps,
          // Union of all cp_idx values any SN in this WF has reached.
          _cpColMap: new Map(),
          sns: [],
        })
      }
      const g = groups.get(key)
      for (const cp of wf.cpList) {
        if (!g._cpColMap.has(cp.cp_idx)) {
          g._cpColMap.set(cp.cp_idx, { cp_idx: cp.cp_idx, cp_name: cp.cp_name })
        }
      }
      g.sns.push({
        sn: sn.sn,
        unit_num: sn.unit_num || '',
        config: wf.config,
        current_cp_idx: wf.current_cp_idx,
        cpList: wf.cpList,
        cpByIdx: Object.fromEntries(wf.cpList.map(c => [c.cp_idx, c])),
      })
    }
  }
  // Sort CP columns ascending; attach as plain array.
  return [...groups.values()].map(g => ({
    ...g,
    cpColumns: [...g._cpColMap.values()].sort((a, b) => a.cp_idx - b.cp_idx),
  }))
}

function deriveCheckItemNames(cps) {
  const names = new Set()
  for (const cp of cps || []) {
    for (const it of cp.items || []) {
      const label = it.name || it.check_item
      if (label) names.add(label)
    }
  }
  return [...names]
}
