<template>
  <div class="lifecycle-wrap">
    <div v-if="!cpList.length" class="lifecycle-empty">—</div>
    <div v-else class="lifecycle-scroll" ref="scrollRef">
      <table class="lifecycle-table" :class="{ compact }">
        <thead>
          <tr>
            <th
              v-for="cp in cpList"
              :key="cp.cp_idx"
              class="cp-th"
              :class="[
                cp.has_data ? 'clickable' : '',
                expandedCp === cp.cp_idx ? 'expanded' : '',
              ]"
              :colspan="expandedCp === cp.cp_idx ? Math.max(1, visibleCheckItemCount) : 1"
              @click="cp.has_data && !checkItemFilter && toggleCp(cp.cp_idx)"
            >
              <div class="cp-name">{{ cp.cp_name }}</div>
              <div class="cp-date" v-if="cp.date">{{ formatDate(cp.date) }}</div>
              <div v-if="expandedCp === cp.cp_idx" class="cp-expand-indicator" aria-hidden="true">▼</div>
            </th>
          </tr>
          <tr v-if="expandedCp !== null && !checkItemFilter">
            <template v-for="cp in cpList" :key="'sub-' + cp.cp_idx">
              <template v-if="expandedCp === cp.cp_idx">
                <th
                  v-for="name in displayCheckItems(cp)"
                  :key="cp.cp_idx + '-' + name"
                  class="ci-th"
                >{{ name }}</th>
              </template>
              <th v-else class="cp-th-placeholder"></th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr class="result-row">
            <template v-for="cp in cpList" :key="'cell-' + cp.cp_idx">
              <!-- Check-item filtered view: single cell per CP showing that item's status -->
              <td
                v-if="checkItemFilter"
                class="cp-cell"
                :class="ciFilteredCellClass(cp)"
              >{{ ciFilteredCellText(cp) }}</td>

              <!-- Collapsed CP view -->
              <td
                v-else-if="expandedCp !== cp.cp_idx"
                class="cp-cell"
                :class="cpCellClass(cp)"
              >
                <span class="cell-count" v-if="cp.has_data">{{ cp.pass_count }}/{{ cp.total_check_items }}</span>
                <span class="cell-count" v-else>/</span>
                <span class="cell-status">{{ statusLabel(cp) }}</span>
              </td>

              <!-- Expanded CP: one cell per check item -->
              <template v-else>
                <td
                  v-for="name in displayCheckItems(cp)"
                  :key="cp.cp_idx + '-ci-' + name"
                  class="ci-cell"
                  :class="ciCellClass(cp, name)"
                >{{ ciCellText(cp, name) }}</td>
              </template>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  cpList: { type: Array, default: () => [] },
  // Distinct check-item names for this WF (used when expanding CP and for filter label lookup).
  checkItems: { type: Array, default: () => [] },
  // When non-null, suppress CP expand and show one cell per CP for this specific check item.
  checkItemFilter: { type: String, default: null },
  // Optional async (cpIdx) => { check_items: [{check_item, status, failure_type}, ...] }
  lazyLoadChecks: { type: Function, default: null },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['cp-expand'])

const expandedCp = ref(null)
// Per-CP loaded check items, keyed by cp_idx.
const loadedByCp = ref({})

const visibleCheckItemCount = computed(() => props.checkItems.length || 1)

function checkItemsForCp(cp) {
  if (Array.isArray(cp.checkItems)) return cp.checkItems
  return loadedByCp.value[cp.cp_idx] || null
}

function displayCheckItems(cp) {
  // Prefer the ordered names from CP definition; fall back to whatever the cell has.
  if (props.checkItems.length) return props.checkItems
  const items = checkItemsForCp(cp) || []
  return items.map(i => i.name)
}

function toggleCp(cpIdx) {
  if (expandedCp.value === cpIdx) {
    expandedCp.value = null
    return
  }
  expandedCp.value = cpIdx
  emit('cp-expand', cpIdx)
  const cp = props.cpList.find(c => c.cp_idx === cpIdx)
  if (cp && !Array.isArray(cp.checkItems) && !loadedByCp.value[cpIdx] && props.lazyLoadChecks) {
    Promise.resolve(props.lazyLoadChecks(cpIdx)).then(res => {
      loadedByCp.value[cpIdx] = (res?.check_items || []).map(i => ({
        name: i.check_item || i.name,
        status: i.status,
        failure_type: i.failure_type || null,
      }))
    }).catch(() => { /* swallow: user can retry by closing/opening */ })
  }
}

function findCheckItem(cp, name) {
  const items = checkItemsForCp(cp) || []
  return items.find(i => (i.name || i.check_item) === name) || null
}

function cpCellClass(cp) {
  if (!cp.has_data) return 'cell-skip'
  if (cp.status === 'fail' || cp.failure_type === 'spec') return 'cell-fail'
  if (cp.failure_type === 'strife') return 'cell-strife'
  return 'cell-pass'
}

function ciCellClass(cp, name) {
  const ci = findCheckItem(cp, name)
  if (!ci) return 'ci-skip'
  if (ci.status === 'pass') return 'ci-pass'
  if (ci.status === 'fail' || ci.failure_type === 'spec') return 'ci-fail'
  if (ci.failure_type === 'strife') return 'ci-strife'
  return 'ci-skip'
}

function ciCellText(cp, name) {
  const ci = findCheckItem(cp, name)
  if (!ci) return '—'
  if (ci.status === 'pass') return '✓'
  if (ci.status === 'fail' || ci.failure_type) return '✗'
  return '—'
}

function ciFilteredCellClass(cp) {
  if (!cp.has_data) return 'cell-skip'
  const ci = findCheckItem(cp, props.checkItemFilter)
  if (!ci) return 'cell-skip'
  if (ci.status === 'pass') return 'cell-pass'
  if (ci.status === 'fail' || ci.failure_type === 'spec') return 'cell-fail'
  if (ci.failure_type === 'strife') return 'cell-strife'
  return 'cell-skip'
}

function ciFilteredCellText(cp) {
  if (!cp.has_data) return '/'
  const ci = findCheckItem(cp, props.checkItemFilter)
  if (!ci) return '—'
  if (ci.status === 'pass') return '✓'
  if (ci.status === 'fail' || ci.failure_type) return '✗'
  return '—'
}

function statusLabel(cp) {
  if (!cp.has_data) return ''
  if (cp.failure_type === 'spec' || cp.status === 'fail') return 'Fail'
  if (cp.failure_type === 'strife') return 'Strife'
  if (cp.status === 'pass') return 'Pass'
  return cp.status || ''
}

function formatDate(d) {
  if (!d) return ''
  const parts = String(d).split('-')
  if (parts.length === 3) return `${parts[1]}/${parts[2]}`
  return d
}

// When filter is set, force-close any expanded CP so layout stays a single row.
watch(() => props.checkItemFilter, () => {
  if (props.checkItemFilter) expandedCp.value = null
})

// When the source cpList changes (new SN / new WF), close expansion to avoid stale state.
watch(() => props.cpList, () => {
  expandedCp.value = null
  loadedByCp.value = {}
})
</script>

<style scoped>
.lifecycle-wrap { width: 100%; }
.lifecycle-empty {
  padding: 12px; color: var(--text-muted); font-size: 12px; text-align: center;
}
.lifecycle-scroll { overflow-x: auto; }

.lifecycle-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  min-width: 100%;
}

.cp-th {
  min-width: 72px;
  max-width: 100px;
  padding: 6px 8px;
  text-align: center;
  background: var(--bg-row-stripe);
  border: 1px solid var(--border-light);
  cursor: default;
  user-select: none;
  vertical-align: top;
}
.cp-th.clickable { cursor: pointer; }
.cp-th.clickable:hover { background: var(--bg-row-hover); }
.cp-th.expanded {
  background: var(--bg-card);
  border-bottom: 2px solid var(--accent-steel);
}

.cp-name {
  font-weight: 600; color: var(--text-primary); font-size: 12px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cp-date { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
.cp-expand-indicator { font-size: 10px; color: var(--accent-steel); margin-top: 2px; }

.ci-th {
  padding: 4px 6px;
  text-align: center;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  min-width: 48px;
}
.cp-th-placeholder {
  border: 1px solid var(--border-light);
  background: var(--bg-row-stripe);
}

.cp-cell {
  padding: 4px 8px;
  text-align: center;
  border: 1px solid var(--border-light);
  font-variant-numeric: tabular-nums;
}
.cell-count { display: block; font-weight: 600; font-size: 13px; }
.cell-status { display: block; font-size: 10px; margin-top: 1px; }

/* Design Token colors — no hardcoded hex */
.cell-pass   { background: var(--color-pass-bg);   color: var(--color-pass); }
.cell-fail   { background: var(--color-danger-bg); color: var(--color-danger); }
.cell-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.cell-skip   { background: var(--bg-muted);        color: var(--text-muted); }

.ci-cell {
  padding: 4px 6px;
  text-align: center;
  border: 1px solid var(--border-light);
  font-size: 13px;
  font-weight: 600;
  min-width: 48px;
}
.ci-pass   { background: var(--color-pass-bg);   color: var(--color-pass); }
.ci-fail   { background: var(--color-danger-bg); color: var(--color-danger); }
.ci-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.ci-skip   { background: var(--bg-muted);        color: var(--text-muted); }

.compact .cp-th { min-width: 56px; padding: 4px 6px; }
.compact .cp-cell { padding: 3px 6px; font-size: 11px; }
.compact .cell-count { font-size: 11px; }
.compact .cell-status { font-size: 9px; }
</style>
