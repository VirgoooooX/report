<template>
  <div class="compare-wrap">
    <div v-for="g in sortedGroups" :key="g.wf_num" class="card compare-group">
      <div class="group-header">
        <span class="wf-pill">WF{{ g.wf_num }}</span>
        <span class="wf-name">{{ wfNames[g.wf_num] || g.test_name || '' }}</span>
        <span class="sn-count">· {{ g.sns.length }} {{ t('queryCenter.snsCount') }}</span>
      </div>

      <!-- Lifecycle mode: full CP matrix -->
      <div class="compare-matrix">
        <div class="matrix-head">
          <div class="sn-col-head">
            <span>SN</span>
            <span>MARK</span>
            <span>CFG</span>
          </div>
          <div class="cp-col-head-wrap" :style="gridStyle(g)">
            <div
              v-for="col in g.cpColumns"
              :key="col.cp_idx"
              class="cp-col-head"
              :class="{
                clickable: canExpand(g, col.cp_idx) && !checkItemFilter,
                active: active.kind === 'group' && active.wf === g.wf_num && active.cpIdx === col.cp_idx,
              }"
              :title="col.cp_name"
              @click="canExpand(g, col.cp_idx) && !checkItemFilter && openGroupPopover(g, col.cp_idx, $event)"
            >
              <span class="cp-idx">{{ col.cp_idx + 1 }}</span>
              <span class="cp-name">{{ col.cp_name }}</span>
            </div>
          </div>
        </div>

        <div v-for="sn in g.sns" :key="sn.sn + '_' + sn.config" class="matrix-row">
          <div class="sn-col" @click="emit('open-sn', sn.sn)">
            <span class="sn-label">{{ sn.sn }}</span>
            <span v-if="sn.unit_num" class="sn-mark-badge">{{ sn.unit_num }}</span>
            <span v-else class="sn-mark-badge placeholder" aria-hidden="true"></span>
            <span class="sn-config-chip">{{ sn.config }}</span>
          </div>
          <div class="cp-row-cells" :style="gridStyle(g)">
            <div
              v-for="col in g.cpColumns"
              :key="sn.sn + '_' + col.cp_idx"
              class="cp-cell"
              :class="[cellClass(sn, col.cp_idx), { 'clickable-cell': canClickRowCell(sn, col.cp_idx), 'row-active': isActiveRowCell(g, sn, col.cp_idx) }]"
              :title="cellTitle(sn, col.cp_idx)"
              @click.stop="canClickRowCell(sn, col.cp_idx) && openRowPopover(g, sn, col.cp_idx, $event)"
            >
              <template v-if="checkItemFilter">
                <span class="cell-symbol">{{ filteredSymbol(sn, col.cp_idx) }}</span>
              </template>
              <template v-else-if="getCp(sn, col.cp_idx)">
                <span class="cell-label">{{ cellLabel(sn, col.cp_idx) }}</span>
              </template>
              <template v-else><span class="cell-dash">—</span></template>
            </div>
          </div>
        </div>
      </div>

    </div>

    <CheckItemPopover
      :visible="active.kind !== null"
      :anchor="active.anchor"
      :title="popoverTitle"
      :subtitle="popoverSubtitle"
      :loading="popoverLoading"
      :mode="active.kind === 'group' ? 'matrix' : 'chips'"
      :items="popoverItems"
      :checkItemNames="popoverCheckItemNames"
      :matrixRows="popoverMatrixRows"
      :loadingText="t('common.loading')"
      :emptyText="t('common.noData')"
      @close="closePopover"
    />
  </div>
</template>

<script setup>
import { ref, computed, reactive, nextTick } from 'vue'
import { useI18n } from '@/i18n/useI18n'
import CheckItemPopover from './CheckItemPopover.vue'

const props = defineProps({
  groups: { type: Array, required: true },
  checkItemFilter: { type: String, default: null },
  wfNames: { type: Object, default: () => ({}) },
  sortByMark: { type: Boolean, default: false },
})

const emit = defineEmits(['open-sn', 'request-ci'])

const { t } = useI18n()

// Natural sort for mark numbers like ER1-10-3 → [1, 10, 3]
function parseMarkSort(mark) {
  if (!mark) return [Infinity]
  const nums = String(mark).replace(/^ER/i, '').split(/[-_]/).map(s => {
    const n = parseInt(s, 10)
    return isNaN(n) ? Infinity : n
  })
  return nums
}

function compareMarks(a, b) {
  const ka = parseMarkSort(a)
  const kb = parseMarkSort(b)
  for (let i = 0; i < Math.max(ka.length, kb.length); i++) {
    const va = ka[i] ?? 0, vb = kb[i] ?? 0
    if (va !== vb) return va - vb
  }
  return 0
}

// Sorted groups: when sortByMark, sort SNs within each group by mark number
const sortedGroups = computed(() => {
  if (!props.sortByMark) return props.groups
  return props.groups.map(g => ({
    ...g,
    sns: [...g.sns].sort((a, b) => compareMarks(a.unit_num, b.unit_num)),
  }))
})

// For mark sort display only
function hasFaForGroup() { return false }

// Active popover descriptor. kind: 'row' | 'group' | null
const active = reactive({
  kind: null,
  wf: null,
  cpIdx: null,
  snKey: null, // only for row
  anchor: null, // DOMRect
})

// Cache: key = `${wf}_${config}_${sn}_${cp_idx}` → [{name, status, failure_type}]
const ciCache = ref({})
// Pending request flags
const pending = ref({})

function gridStyle(g) {
  return { gridTemplateColumns: `repeat(${g.cpColumns.length}, minmax(0, 1fr))` }
}

function getCp(sn, cpIdx) { return sn.cpByIdx[cpIdx] }

function canExpand(g, cpIdx) {
  return g.sns.some(sn => {
    const cp = getCp(sn, cpIdx)
    return cp && cp.has_data
  })
}

function canClickRowCell(sn, cpIdx) {
  if (props.checkItemFilter) return false
  const cp = getCp(sn, cpIdx)
  return !!(cp && cp.has_data)
}

function findCpName(g, cpIdx) {
  const col = g.cpColumns.find(c => c.cp_idx === cpIdx)
  return col?.cp_name || `CP${cpIdx + 1}`
}

function ciKey(g, sn, cpIdx) { return `${g.wf_num}_${sn.config}_${sn.sn}_${cpIdx}` }

function resolveCheckItems(g, sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (cp && Array.isArray(cp.checkItems) && cp.checkItems.length) return cp.checkItems
  return ciCache.value[ciKey(g, sn, cpIdx)] || null
}

function ensureCiLoaded(g, sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp || !cp.has_data) return
  if (Array.isArray(cp.checkItems) && cp.checkItems.length) return
  const key = ciKey(g, sn, cpIdx)
  if (ciCache.value[key] || pending.value[key]) return
  pending.value[key] = true
  emit('request-ci', {
    group: g, sn, cpIdx,
    resolve: (items) => {
      ciCache.value[key] = items
      delete pending.value[key]
    },
  })
}

function closePopover() {
  active.kind = null
  active.wf = null
  active.cpIdx = null
  active.snKey = null
  active.anchor = null
}

function rectOf(event) {
  const el = event.currentTarget || event.target
  const r = el.getBoundingClientRect()
  return { x: r.left, y: r.top, width: r.width, height: r.height }
}

function rowKeyOf(sn) { return sn.sn + '|' + sn.config }

function openRowPopover(g, sn, cpIdx, event) {
  // Toggle off if clicking the same cell
  if (
    active.kind === 'row' &&
    active.wf === g.wf_num &&
    active.cpIdx === cpIdx &&
    active.snKey === rowKeyOf(sn)
  ) {
    closePopover()
    return
  }
  active.kind = 'row'
  active.wf = g.wf_num
  active.cpIdx = cpIdx
  active.snKey = rowKeyOf(sn)
  active.anchor = rectOf(event)
  ensureCiLoaded(g, sn, cpIdx)
}

function openGroupPopover(g, cpIdx, event) {
  if (active.kind === 'group' && active.wf === g.wf_num && active.cpIdx === cpIdx) {
    closePopover()
    return
  }
  active.kind = 'group'
  active.wf = g.wf_num
  active.cpIdx = cpIdx
  active.snKey = null
  active.anchor = rectOf(event)
  for (const sn of g.sns) ensureCiLoaded(g, sn, cpIdx)
}

function isActiveRowCell(g, sn, cpIdx) {
  return (
    active.kind === 'row' &&
    active.wf === g.wf_num &&
    active.cpIdx === cpIdx &&
    active.snKey === rowKeyOf(sn)
  )
}

// ── Popover content (derived from `active`) ──────────────────────────
const activeGroup = computed(() => props.groups.find(x => x.wf_num === active.wf) || null)

const activeSn = computed(() => {
  if (active.kind !== 'row' || !activeGroup.value) return null
  return activeGroup.value.sns.find(s => rowKeyOf(s) === active.snKey) || null
})

const popoverTitle = computed(() => {
  if (!active.kind || !activeGroup.value) return ''
  const cpName = findCpName(activeGroup.value, active.cpIdx)
  if (active.kind === 'row' && activeSn.value) {
    return `${cpName}`
  }
  return `${cpName} · WF${activeGroup.value.wf_num}`
})

const popoverSubtitle = computed(() => {
  if (active.kind === 'row' && activeSn.value) {
    const parts = [activeSn.value.sn]
    if (activeSn.value.unit_num) parts.push(activeSn.value.unit_num)
    parts.push(activeSn.value.config)
    return parts.join(' · ')
  }
  if (active.kind === 'group' && activeGroup.value) {
    return `${activeGroup.value.sns.length} ${t('queryCenter.snsCount')}`
  }
  return ''
})

const popoverLoading = computed(() => {
  if (!active.kind || !activeGroup.value) return false
  if (active.kind === 'row' && activeSn.value) {
    const key = ciKey(activeGroup.value, activeSn.value, active.cpIdx)
    if (ciCache.value[key]) return false
    const cp = getCp(activeSn.value, active.cpIdx)
    if (cp && Array.isArray(cp.checkItems) && cp.checkItems.length) return false
    return !!pending.value[key]
  }
  if (active.kind === 'group') {
    return activeGroup.value.sns.some(sn => {
      const k = ciKey(activeGroup.value, sn, active.cpIdx)
      if (ciCache.value[k]) return false
      const cp = getCp(sn, active.cpIdx)
      if (cp && Array.isArray(cp.checkItems) && cp.checkItems.length) return false
      return !!pending.value[k]
    })
  }
  return false
})

const popoverItems = computed(() => {
  if (active.kind !== 'row' || !activeGroup.value || !activeSn.value) return []
  const g = activeGroup.value
  const raw = resolveCheckItems(g, activeSn.value, active.cpIdx) || []
  const byName = new Map(raw.map(i => [i.name, i]))
  const names = g.check_items && g.check_items.length
    ? g.check_items
    : raw.map(i => i.name)
  return names.map(n => byName.get(n) || { name: n, status: null, failure_type: null })
})

const popoverCheckItemNames = computed(() => {
  if (active.kind !== 'group' || !activeGroup.value) return []
  const g = activeGroup.value
  if (g.check_items && g.check_items.length) return g.check_items
  // Fallback: union of names across SNs for this CP
  const names = new Set()
  for (const sn of g.sns) {
    const items = resolveCheckItems(g, sn, active.cpIdx) || []
    for (const i of items) if (i.name) names.add(i.name)
  }
  return [...names]
})

const popoverMatrixRows = computed(() => {
  if (active.kind !== 'group' || !activeGroup.value) return []
  const g = activeGroup.value
  return g.sns.map(sn => ({
    sn: sn.sn,
    unit_num: sn.unit_num || '',
    config: sn.config,
    items: resolveCheckItems(g, sn, active.cpIdx) || [],
  }))
})

// ── Cell class / label helpers (unchanged logic) ─────────────────────

function classify(status, failure_type) {
  if (status === 'pass') return 'pass'
  if (status === 'fail' || failure_type === 'spec') return 'fail'
  if (failure_type === 'strife') return 'strife'
  return 'skip'
}

function symbolOf(status, failure_type) {
  if (status === 'pass') return '✓'
  if (status === 'fail' || failure_type) return '✗'
  return '—'
}

function cellClass(sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp || !cp.has_data) return 'cell-skip'
  if (props.checkItemFilter) {
    const items = Array.isArray(cp.checkItems) ? cp.checkItems : []
    const ci = items.find(i => i.name === props.checkItemFilter)
    if (!ci) return 'cell-skip'
    return `cell-${classify(ci.status, ci.failure_type)}`
  }
  return `cell-${classify(cp.status, cp.failure_type)}`
}

function cellLabel(sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp) return ''
  if (cp.status === 'pass') return 'P'
  if (cp.status === 'fail' || cp.failure_type === 'spec') return 'F'
  if (cp.failure_type === 'strife') return 'S'
  if (cp.status === 'pending') return '·'
  return ''
}

function cellTitle(sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp) return 'No data'
  if (!cp.has_data) return `${cp.cp_name}: no data`
  return `${cp.cp_name} · ${cp.status}${cp.failure_type ? ' (' + cp.failure_type + ')' : ''}`
}

function filteredSymbol(sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp || !cp.has_data) return '/'
  const items = Array.isArray(cp.checkItems) ? cp.checkItems : []
  const ci = items.find(i => i.name === props.checkItemFilter)
  if (!ci) return '—'
  return symbolOf(ci.status, ci.failure_type)
}

// When check-item filter toggles on, close any open popover (stale context)
// Expose for parent via v-model-like pattern — simpler: just close on changes.
import { watch } from 'vue'
watch(() => props.checkItemFilter, () => closePopover())
watch(() => props.groups, () => closePopover())
</script>

<style scoped>
.compare-wrap { display: flex; flex-direction: column; gap: 12px; }
.compare-group { padding: 0; overflow: hidden; }

.group-header {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  padding: 10px 16px;
  background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light);
}
.wf-pill {
  padding: 2px 8px;
  background: var(--text-primary); color: var(--bg-card);
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  border-radius: var(--radius-sm);
}
.wf-name { font-size: 13px; color: var(--text-primary); font-weight: 600; }
.sn-count { font-size: 12px; color: var(--text-muted); }

.compare-matrix { padding: 0 14px 14px; }
.matrix-head {
  display: grid;
  grid-template-columns: minmax(210px, 240px) 1fr;
  gap: 6px;
  padding: 10px 0 6px;
  border-bottom: 1px dashed var(--border-light);
  position: sticky; top: 0; z-index: 1;
  background: var(--bg-card);
}
.sn-col-head {
  display: grid;
  /* SN label grows; mark/config auto-size to badge widths with 6px gaps to mirror .sn-col */
  grid-template-columns: 1fr auto auto;
  gap: 6px;
  align-items: center;
  padding: 6px 6px 2px 4px;
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-weight: 600;
}
.sn-col-head > span:nth-child(2) {
  /* MARK header aligns over sn-mark-badge — reserve equivalent badge padding */
  padding: 0 6px;
  text-align: center;
  min-width: 72px;
}
.sn-col-head > span:nth-child(3) {
  /* CFG header aligns over sn-config-chip */
  padding: 0 6px;
  text-align: center;
  min-width: 52px;
}

.cp-col-head-wrap {
  display: grid;
  gap: 3px;
}
.cp-col-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 4px 2px;
  border-radius: var(--radius-sm);
  background: var(--bg-row-stripe);
  min-width: 0;
  text-align: center;
  overflow: hidden;
}
.cp-col-head.clickable { cursor: pointer; }
.cp-col-head.clickable:hover { background: var(--bg-row-hover); }
.cp-col-head.active {
  background: color-mix(in srgb, var(--accent-steel) 15%, var(--bg-card));
  outline: 1px solid var(--accent-steel);
}
.cp-idx {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 600;
}
.cp-name {
  font-size: 10px;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  max-width: 100%;
}

.matrix-row {
  display: grid;
  grid-template-columns: minmax(210px, 240px) 1fr;
  gap: 6px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-light);
}
.matrix-row:last-child { border-bottom: none; }

.sn-col {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 6px;
  align-items: center;
  padding: 4px 6px 4px 4px;
  min-width: 0;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}
.sn-col:hover { background: var(--bg-row-hover); }

.sn-label {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-steel);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.sn-col:hover .sn-label { text-decoration: underline; }
.sn-config-chip {
  padding: 1px 6px;
  background: var(--bg-tag);
  color: var(--text-secondary);
  font-size: 10px;
  font-family: var(--font-mono);
  border-radius: var(--radius-sm);
  font-weight: 600;
  text-align: center;
  min-width: 52px;
}
.sn-mark-badge {
  padding: 1px 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-info);
  background: var(--color-info-bg);
  border-radius: var(--radius-sm);
  text-align: center;
  min-width: 72px;
}
.sn-mark-badge.placeholder {
  background: transparent;
  color: transparent;
  pointer-events: none;
}

.cp-row-cells {
  display: grid;
  gap: 3px;
  align-items: stretch;
}
.cp-cell {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-width: 0;
  min-height: 28px;
  padding: 6px 2px;
  border-radius: var(--radius-sm);
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.1;
  transition: transform var(--duration-fast);
  overflow: hidden;
}
.cp-cell.clickable-cell { cursor: pointer; }
.cp-cell.clickable-cell:hover {
  transform: scale(1.05);
  z-index: 1;
}
.cp-cell.row-active {
  outline: 2px solid var(--accent-steel);
  outline-offset: -2px;
}
.cell-label { white-space: nowrap; font-size: 12px; letter-spacing: 0.3px; }
.cell-symbol { font-size: 12px; font-weight: 700; }
.cell-dash { color: var(--text-muted); font-size: 12px; }

.cell-pass   { background: var(--color-pass-bg);    color: var(--color-pass); }
.cell-fail   { background: var(--color-danger-bg);  color: var(--color-danger); }
.cell-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.cell-skip   { background: var(--bg-muted);         color: var(--text-muted); }

@media (max-width: 900px) {
  .matrix-head, .matrix-row {
    grid-template-columns: minmax(180px, 220px) 1fr;
  }
}

/* Failures-only and FA styles removed — now in separate Failure tab */
</style>
