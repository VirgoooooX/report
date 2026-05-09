<template>
  <div class="card ts-wrap">
    <div class="ts-scroll">
      <table class="ts-table">
        <thead>
          <tr>
            <th class="ts-wf-hd" rowspan="2">WF</th>
            <th v-for="cfg in configList" :key="cfg"
                :colspan="maxTests" class="ts-cfg-hd"
                :style="{ color: cfgColor(cfg) }">{{ cfg }}</th>
          </tr>
          <tr>
            <template v-for="cfg in configList" :key="'h2-'+cfg">
              <th v-for="ti in maxTests" :key="ti"
                  class="ts-test-hd">{{ testNames[ti-1] }}</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="wf in sortedWfs" :key="wf.wf">
            <td class="ts-wf-col">
              <span class="ts-wf-num">WF{{ wf.wf }}</span>
            </td>
            <template v-for="cfg in configList" :key="cfg">
              <td v-for="ti in maxTests" :key="ti"
                  :class="cellClass(wf, cfg, ti-1)"
                  @click="onCellClick(wf, cfg, ti-1)">
                {{ cellText(wf, cfg, ti-1) }}
              </td>
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

// Collect configs from all WFs
const configList = computed(() => {
  const set = new Set()
  summaryList.value.forEach(wf => {
    if (wf.configs) Object.keys(wf.configs).forEach(c => set.add(c))
  })
  const ordered = CFG_ORDER.filter(c => set.has(c))
  CFG_ORDER.forEach(c => set.delete(c))
  return [...ordered, ...set]
})

// Max test count across all WFs and configs
const maxTests = computed(() => {
  let max = 0
  summaryList.value.forEach(wf => {
    if (wf.configs) {
      Object.values(wf.configs).forEach(tests => {
        const n = Object.keys(tests).length
        if (n > max) max = n
      })
    }
  })
  return max || 1
})

// Build test names from first WF that has test_names
const testNames = computed(() => {
  const names = []
  for (const wf of summaryList.value) {
    const tn = wf.test_names || []
    tn.forEach((n, i) => { if (n && !names[i]) names[i] = n })
  }
  for (let i = 0; i < maxTests.value; i++) {
    if (!names[i]) names[i] = `Test${i + 1}`
  }
  return names
})

const sortedWfs = computed(() => {
  return [...summaryList.value].sort((a, b) =>
    String(a.wf).localeCompare(String(b.wf), undefined, { numeric: true })
  )
})

function cfgColor(c) { return CFG_COLORS[c] || '#4f6f8f' }

function getTest(wf, cfg, ti) {
  const testName = testNames.value[ti]
  return wf.configs?.[cfg]?.[testName] || null
}

function cellClass(wf, cfg, ti) {
  const t = getTest(wf, cfg, ti)
  if (!t) return 'ts-empty'
  if (t.spec > 0) return 'ts-fail'
  if (t.strife > 0) return 'ts-strife'
  return 'ts-pass'
}

function cellText(wf, cfg, ti) {
  const t = getTest(wf, cfg, ti)
  return t?.result || '—'
}

function onCellClick(wf, cfg, ti) {
  const t = getTest(wf, cfg, ti)
  if (!t || !t.has_failure) return
  const testName = testNames.value[ti]
  emit('cell-click', {
    wf: 'WF' + wf.wf,
    cfg,
    test: testName,
    failureSns: t.failure_sns || []
  })
}
</script>

<style scoped>
.card { background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-card); box-shadow: var(--shadow-card); overflow: hidden; }
.ts-scroll { overflow-x: auto; }
.ts-table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 700px; }

.ts-wf-hd {
  padding: 8px 10px; font-size: 11px; font-weight: 600; text-align: left;
  color: var(--text-muted); background: var(--bg-row-stripe);
  text-transform: uppercase; letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-light);
  position: sticky; left: 0; z-index: 2;
}
.ts-cfg-hd {
  padding: 6px 4px; font-size: 11px; font-weight: 700;
  background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light);
}
.ts-test-hd {
  padding: 5px 4px; font-size: 10px; font-weight: 400;
  color: var(--text-muted); background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light);
  max-width: 60px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.ts-wf-col {
  padding: 8px 10px; text-align: left; font-family: var(--font-mono);
  font-size: 11px; font-weight: 600; color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-card);
  position: sticky; left: 0; z-index: 1;
}
.ts-wf-num { white-space: nowrap; }

td {
  padding: 6px 6px; text-align: center; font-family: var(--font-mono);
  font-size: 11px; font-variant-numeric: tabular-nums;
  border-bottom: 1px solid var(--border-light);
  transition: filter var(--duration-fast);
}

.ts-pass { background: var(--color-success-bg); color: var(--color-success); }
.ts-strife { background: var(--color-warning-bg); color: var(--color-warning); cursor: pointer; }
.ts-fail { background: var(--color-danger-bg); color: var(--color-danger); font-weight: 700; cursor: pointer; }
.ts-empty { color: var(--text-muted); opacity: 0.4; }
.ts-strife:hover, .ts-fail:hover { filter: brightness(0.94); }

tr:nth-child(even) td { background-color: rgba(0,0,0,0.01); }
tr:nth-child(even) td.ts-pass { background: var(--color-success-bg); }
tr:nth-child(even) td.ts-strife { background: var(--color-warning-bg); }
tr:nth-child(even) td.ts-fail { background: var(--color-danger-bg); }
</style>