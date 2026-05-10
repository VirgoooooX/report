<template>
  <div class="card ts-wrap">
    <div class="ts-scroll">
      <table class="ts-table">
        <thead>
          <tr>
            <th class="ts-wf-hd" rowspan="2">WF</th>
            <template v-for="ti in maxTestSlots" :key="ti">
              <th class="ts-test-hd" :class="{ 'ts-test-hd--with-divider': ti < maxTestSlots }" :colspan="5">Test{{ ti }}</th>
              <th v-if="ti < maxTestSlots" class="ts-gap" aria-hidden="true"></th>
            </template>
          </tr>
          <tr>
            <template v-for="ti in maxTestSlots" :key="'sub-'+ti">
              <th class="ts-tn-sub" :class="{ 'ts-tn-sub--with-divider': ti < maxTestSlots }">Name</th>
              <th v-for="cfg in configList" :key="cfg" class="ts-cfg-sub"
                  :style="{ color: cfgColor(cfg) }">{{ cfg }}</th>
              <th v-if="ti < maxTestSlots" class="ts-gap" aria-hidden="true"></th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(wf, rowIndex) in sortedWfs" :key="wf.wf" :class="{ 'ts-row-alt': rowIndex % 2 === 1 }">
            <td class="ts-wf-col">WF{{ wf.wf }}</td>
            <template v-for="ti in maxTestSlots" :key="ti">
              <td class="ts-tn-col" :class="{ 'ts-tn-col--with-divider': ti < maxTestSlots }">{{ wfTestName(wf, ti - 1) }}</td>
              <td v-for="cfg in configList" :key="cfg"
                  :class="[cellClass(wf, cfg, ti - 1), { 'ts-cell-group-end': cfg === configList[configList.length - 1] && ti < maxTestSlots }]"
                  @click="onCellClick(wf, cfg, ti - 1)">
                {{ cellText(wf, cfg, ti - 1) }}
              </td>
              <td v-if="ti < maxTestSlots" class="ts-gap" aria-hidden="true"></td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { testSummaryCellClass } from '@/views/testSummaryDisplay.js'

const props = defineProps({ summaryData: { type: Object, default: () => ({}) } })
const emit = defineEmits(['cell-click'])

const CFG_ORDER = ['R1FNF', 'R2CNM', 'R3', 'R4']
const CFG_COLORS = { R1FNF: '#4f6f8f', R2CNM: '#0891b2', R3: '#d97706', R4: '#059669' }

const summaryList = computed(() => props.summaryData?.summary ?? [])

const configList = computed(() => {
  const set = new Set()
  summaryList.value.forEach(wf => {
    if (wf.config_results) Object.keys(wf.config_results).forEach(c => set.add(c))
    if (wf.configs) Object.keys(wf.configs).forEach(c => set.add(c))
  })
  const ordered = CFG_ORDER.filter(c => set.has(c))
  CFG_ORDER.forEach(c => set.delete(c))
  return [...ordered, ...set]
})

// Max number of test slots across all WFs
const maxTestSlots = computed(() => {
  let max = 0
  summaryList.value.forEach(wf => {
    const tn = wf.test_names
    if (tn && tn.length > max) max = tn.length
    // Also check config data for test keys like Test1, Test2, etc.
    if (wf.configs) {
      Object.values(wf.configs).forEach(tests => {
        const n = Object.keys(tests).length
        if (n > max) max = n
      })
    }
  })
  return max || 1
})

const sortedWfs = computed(() => {
  return [...summaryList.value].sort((a, b) =>
    String(a.wf).localeCompare(String(b.wf), undefined, { numeric: true })
  )
})

// Get this WF's test name for a given slot index
function wfTestName(wf, slotIdx) {
  const tn = wf.test_names
  if (tn && tn[slotIdx]) return tn[slotIdx]
  return '—'
}

// Get the test name key for this WF's slot - used to look up config results
function wfTestKey(wf, slotIdx) {
  const tn = wf.test_names
  if (tn && tn[slotIdx]) return tn[slotIdx]
  return `Test${slotIdx + 1}`
}

function cfgColor(c) { return CFG_COLORS[c] || '#4f6f8f' }

function getResult(wf, cfg, slotIdx) {
  const indexed = wf.config_results?.[cfg]
  if (Array.isArray(indexed) && indexed[slotIdx]) return indexed[slotIdx]
  const key = wfTestKey(wf, slotIdx)
  return wf.configs?.[cfg]?.[key] || null
}

function cellClass(wf, cfg, slotIdx) {
  const r = getResult(wf, cfg, slotIdx)
  return testSummaryCellClass(r)
}

function cellText(wf, cfg, slotIdx) {
  const r = getResult(wf, cfg, slotIdx)
  return r?.result || '—'
}

function onCellClick(wf, cfg, slotIdx) {
  const r = getResult(wf, cfg, slotIdx)
  if (!r || !r.has_failure) return
  emit('cell-click', {
    wf: 'WF' + wf.wf, cfg,
    test: wfTestName(wf, slotIdx),
    failureSns: r.failure_sns || []
  })
}
</script>

<style scoped>
.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-card);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.ts-wrap {
  width: 100%;
}

.ts-scroll {
  overflow-x: auto;
  scrollbar-color: var(--border-input) transparent;
}

.ts-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
  min-width: 1080px;
}

.ts-wf-hd {
  padding: 8px 8px;
  font-size: 10px;
  font-weight: 700;
  text-align: left;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: color-mix(in srgb, var(--bg-row-hover) 70%, var(--bg-card));
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  left: 0;
  z-index: 4;
  box-shadow: 1px 0 0 var(--border-light);
}
.ts-test-hd {
  padding: 8px 10px 6px;
  font-size: 11px;
  font-weight: 700;
  text-align: left;
  color: var(--text-primary);
  background: color-mix(in srgb, var(--bg-row-hover) 70%, var(--bg-card));
  border-bottom: 1px solid var(--border-light);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}
.ts-test-hd--with-divider {
  box-shadow: inset -1px 0 0 var(--border-light);
}
.ts-tn-sub {
  padding: 6px 6px;
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  text-align: left;
  background: color-mix(in srgb, var(--bg-row-stripe) 82%, var(--bg-card));
  border-bottom: 1px solid var(--border-light);
  min-width: 72px;
  max-width: 152px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ts-tn-sub--with-divider {
  box-shadow: inset -1px 0 0 var(--border-light);
}
.ts-cfg-sub {
  padding: 6px 6px;
  font-size: 10px;
  font-weight: 700;
  text-align: center;
  background: color-mix(in srgb, var(--bg-row-stripe) 82%, var(--bg-card));
  border-bottom: 1px solid var(--border-light);
}
.ts-gap {
  width: 10px;
  min-width: 10px;
  background: color-mix(in srgb, var(--bg-root) 55%, var(--bg-card));
  padding: 0 !important;
  border-bottom: 1px solid var(--border-light);
  border-left: 1px solid var(--border-light);
  border-right: 1px solid var(--border-light);
}

.ts-wf-col {
  padding: 7px 8px;
  text-align: left;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-card);
  position: sticky; left: 0; z-index: 1; white-space: nowrap;
  box-shadow: 1px 0 0 var(--border-light);
}
.ts-tn-col {
  padding: 7px 8px;
  text-align: left;
  font-size: 11px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-card);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 156px;
  font-weight: 500;
}
.ts-tn-col--with-divider,
.ts-cell-group-end {
  box-shadow: inset -1px 0 0 var(--border-light);
}

td {
  padding: 6px 4px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  border-bottom: 1px solid var(--border-light);
  transition: filter var(--duration-fast), background var(--duration-fast), color var(--duration-fast);
  white-space: nowrap;
}

.ts-pass { background: var(--color-success-bg); color: var(--color-success); }
.ts-strife { background: var(--color-warning-bg); color: var(--color-warning); cursor: pointer; }
.ts-fail { background: var(--color-danger-bg); color: var(--color-danger); font-weight: 700; cursor: pointer; }
.ts-in-progress {
  background: var(--color-in-progress-bg);
  color: var(--color-in-progress);
  font-weight: 600;
}
.ts-fail-text { color: var(--color-danger); font-weight: 700; cursor: pointer; }
.ts-strife-text { color: var(--color-warning); font-weight: 700; cursor: pointer; }

.ts-not-started {
  background: color-mix(in srgb, var(--color-not-started-bg) 82%, var(--bg-card));
  color: var(--text-muted);
  opacity: 0.65;
}

.ts-empty { color: var(--text-muted); opacity: 0.28; }
.ts-strife:hover, .ts-fail:hover { filter: brightness(0.94); }

.ts-row-alt .ts-tn-col,
.ts-row-alt .ts-wf-col {
  background: color-mix(in srgb, var(--bg-row-stripe) 40%, var(--bg-card));
}

.ts-row-alt .ts-not-started {
  background: color-mix(in srgb, var(--bg-row-stripe) 48%, var(--color-not-started-bg));
}

.ts-row-alt .ts-empty {
  background: color-mix(in srgb, var(--bg-row-stripe) 48%, var(--bg-card));
}

tbody tr:hover .ts-wf-col,
tbody tr:hover .ts-tn-col,
tbody tr:hover .ts-empty,
tbody tr:hover .ts-not-started {
  background: var(--bg-row-hover);
}

@media (max-width: 900px) {
  .ts-table {
    min-width: 960px;
  }

  .ts-gap {
    width: 8px;
    min-width: 8px;
  }
}
</style>
