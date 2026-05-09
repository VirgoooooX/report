<template>
  <div class="card ts-wrap">
    <div class="ts-scroll">
      <table class="ts-table">
        <thead>
          <tr>
            <th class="ts-wf-hd" rowspan="2">WF</th>
            <template v-for="(t, ti) in tests" :key="ti">
              <th class="ts-test-hd" :colspan="5">Test{{ ti + 1 }}</th>
              <th v-if="ti < tests.length - 1" class="ts-gap"></th>
            </template>
          </tr>
          <tr>
            <template v-for="(t, ti) in tests" :key="'sub-'+ti">
              <th class="ts-tn-sub">Name</th>
              <th v-for="cfg in configList" :key="cfg" class="ts-cfg-sub"
                  :style="{ color: cfgColor(cfg) }">{{ cfg }}</th>
              <th v-if="ti < tests.length - 1" class="ts-gap"></th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="wf in sortedWfs" :key="wf.wf">
            <td class="ts-wf-col">WF{{ wf.wf }}</td>
            <template v-for="(t, ti) in tests" :key="ti">
              <td class="ts-tn-col">{{ wfTestName(wf, ti) }}</td>
              <td v-for="cfg in configList" :key="cfg"
                  :class="cellClass(wf, cfg, ti)"
                  @click="onCellClick(wf, cfg, ti)">
                {{ cellText(wf, cfg, ti) }}
              </td>
              <td v-if="ti < tests.length - 1" class="ts-gap"></td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ summaryData: { type: Object, default: () => ({}) } })
const emit = defineEmits(['cell-click'])

const CFG_ORDER = ['R1FNF', 'R2CNM', 'R3', 'R4']
const CFG_COLORS = { R1FNF: '#4f6f8f', R2CNM: '#0891b2', R3: '#d97706', R4: '#059669' }

const summaryList = computed(() => props.summaryData?.summary ?? [])

const configList = computed(() => {
  const set = new Set()
  summaryList.value.forEach(wf => {
    if (wf.configs) Object.keys(wf.configs).forEach(c => set.add(c))
  })
  const ordered = CFG_ORDER.filter(c => set.has(c))
  CFG_ORDER.forEach(c => set.delete(c))
  return [...ordered, ...set]
})

const tests = computed(() => {
  const seen = new Set()
  const names = []
  summaryList.value.forEach(wf => {
    if (wf.configs) {
      Object.values(wf.configs).forEach(cfgTests => {
        Object.keys(cfgTests).forEach(t => {
          if (!seen.has(t)) { seen.add(t); names.push(t) }
        })
      })
    }
  })
  summaryList.value.forEach(wf => {
    (wf.test_names || []).forEach(t => {
      if (t && !seen.has(t)) { seen.add(t); names.push(t) }
    })
  })
  return names
})

const sortedWfs = computed(() => {
  return [...summaryList.value].sort((a, b) =>
    String(a.wf).localeCompare(String(b.wf), undefined, { numeric: true })
  )
})

function wfTestName(wf, ti) {
  // Use wf.test_names per slot
  const tn = wf.test_names
  if (tn && tn[ti]) return tn[ti]
  // Fallback: use the global test name for this index
  return tests.value[ti] || '—'
}

function cfgColor(c) { return CFG_COLORS[c] || '#4f6f8f' }

function getResult(wf, cfg, ti) {
  const tname = tests.value[ti]
  if (!tname) return null
  return wf.configs?.[cfg]?.[tname] || null
}

function cellClass(wf, cfg, ti) {
  const r = getResult(wf, cfg, ti)
  if (!r) return 'ts-empty'
  if (r.spec > 0) return 'ts-fail'
  if (r.strife > 0) return 'ts-strife'
  return 'ts-pass'
}

function cellText(wf, cfg, ti) {
  const r = getResult(wf, cfg, ti)
  return r?.result || '—'
}

function onCellClick(wf, cfg, ti) {
  const r = getResult(wf, cfg, ti)
  if (!r || !r.has_failure) return
  emit('cell-click', {
    wf: 'WF' + wf.wf, cfg,
    test: tests.value[ti],
    failureSns: r.failure_sns || []
  })
}
</script>

<style scoped>
.card { background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-card); box-shadow: var(--shadow-card); overflow: hidden; }
.ts-scroll { overflow-x: auto; }
.ts-table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 700px; }

.ts-wf-hd {
  padding: 6px 8px; font-size: 10px; font-weight: 600; text-align: left;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;
  background: var(--bg-row-stripe); border-bottom: 1px solid var(--border-light);
  position: sticky; left: 0; z-index: 3;
}
.ts-test-hd {
  padding: 5px 2px; font-size: 11px; font-weight: 600;
  color: var(--text-primary); background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 120px;
}
.ts-tn-sub {
  padding: 4px 6px; font-size: 10px; font-weight: 400;
  color: var(--text-muted); background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light);
  min-width: 60px; max-width: 140px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ts-cfg-sub {
  padding: 4px 6px; font-size: 10px; font-weight: 600;
  background: var(--bg-row-stripe); border-bottom: 1px solid var(--border-light);
}
.ts-gap { width: 3px; min-width: 3px; background: var(--border-light); padding: 0 !important; border-bottom: 1px solid var(--border-light); }

.ts-wf-col {
  padding: 6px 6px; text-align: left; font-family: var(--font-mono);
  font-size: 11px; font-weight: 600; color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-card);
  position: sticky; left: 0; z-index: 1; white-space: nowrap;
}
.ts-tn-col {
  padding: 5px 6px; text-align: left;
  font-size: 11px; color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-card);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 140px; font-weight: 500;
}

td {
  padding: 5px 4px; text-align: center; font-family: var(--font-mono);
  font-size: 11px; font-variant-numeric: tabular-nums;
  border-bottom: 1px solid var(--border-light);
  transition: filter var(--duration-fast); white-space: nowrap;
}

.ts-pass { background: var(--color-success-bg); color: var(--color-success); }
.ts-strife { background: var(--color-warning-bg); color: var(--color-warning); cursor: pointer; }
.ts-fail { background: var(--color-danger-bg); color: var(--color-danger); font-weight: 700; cursor: pointer; }
.ts-empty { color: var(--text-muted); opacity: 0.35; }
.ts-strife:hover, .ts-fail:hover { filter: brightness(0.94); }
</style>