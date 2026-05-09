<template>
  <div class="card table-wrap">
    <table>
      <thead>
        <tr>
          <th class="corner-cell"></th>
          <th v-for="cfg in configs" :key="cfg" class="cfg-header">{{ cfg }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="wf in wfs" :key="wf">
          <td class="wf-header">WF{{ wf }}</td>
          <td
            v-for="cfg in configs"
            :key="cfg"
            class="result-cell"
            :class="cellClass(wf, cfg)"
            @click="onCellClick(wf, cfg)"
          >
            {{ cellText(wf, cfg) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summaryData: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['cell-click'])

const CFG_ORDER = ['R1FNF', 'R2CNM', 'R3', 'R4']

const summaryList = computed(() => props.summaryData?.summary ?? [])

// Collect all configs from data
const configs = computed(() => {
  const cfgSet = new Set()
  summaryList.value.forEach(wf => {
    if (wf.configs) Object.keys(wf.configs).forEach(c => cfgSet.add(c))
  })
  const ordered = CFG_ORDER.filter(c => cfgSet.has(c))
  CFG_ORDER.forEach(c => cfgSet.delete(c))
  return [...ordered, ...cfgSet]
})

const wfs = computed(() => {
  return summaryList.value.map(w => w.wf).sort((a, b) =>
    String(a).localeCompare(String(b), undefined, { numeric: true })
  )
})

// Build normalized matrix from API data
const matrix = computed(() => {
  const m = {}
  summaryList.value.forEach(wf => {
    const wfKey = wf.wf
    if (!m[wfKey]) m[wfKey] = {}
    if (wf.configs) {
      Object.entries(wf.configs).forEach(([cfg, tests]) => {
        let passCount = 0, specCount = 0, strifeCount = 0, totalCount = 0
        let hasFail = false
        let failureSns = []

        Object.values(tests).forEach(test => {
          totalCount++
          if (test.spec > 0) { specCount++; hasFail = true; if (test.failure_sns) failureSns = failureSns.concat(test.failure_sns) }
          else if (test.strife > 0) { strifeCount++ }
          else { passCount++ }
        })

        m[wfKey][cfg] = { passCount, specCount, strifeCount, totalCount, hasFail, failureSns }
      })
    }
  })
  return m
})

function getCell(wf, cfg) {
  return matrix.value[wf]?.[cfg] || null
}

function cellStatus(wf, cfg) {
  const cell = getCell(wf, cfg)
  if (!cell) return 'empty'
  if (cell.specCount > 0) return 'fail'
  if (cell.strifeCount > 0) return 'strife'
  if (cell.passCount > 0) return 'pass'
  return 'empty'
}

function cellText(wf, cfg) {
  const cell = getCell(wf, cfg)
  if (!cell) return '—'
  const parts = []
  if (cell.specCount > 0) parts.push(cell.specCount + 'F')
  if (cell.strifeCount > 0) parts.push('S' + cell.strifeCount)
  if (cell.passCount > 0 && cell.specCount === 0 && cell.strifeCount === 0) {
    return cell.passCount + 'P'
  }
  return parts.join('/') || '—'
}

function cellClass(wf, cfg) {
  return `cell-${cellStatus(wf, cfg)}`
}

function onCellClick(wf, cfg) {
  const status = cellStatus(wf, cfg)
  if (status !== 'fail' && status !== 'strife') return

  const cell = getCell(wf, cfg)
  if (!cell) return

  emit('cell-click', {
    wf: 'WF' + wf,
    cfg,
    test: '',
    failureSns: cell.failureSns || []
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

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

th, td {
  padding: 8px 10px;
  text-align: center;
  border-bottom: 1px solid var(--border-light);
}

.corner-cell {
  min-width: 70px;
  width: 70px;
}

.cfg-header {
  background: var(--bg-row-stripe);
  font-weight: 600;
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  min-width: 80px;
}

.wf-header {
  background: var(--bg-row-stripe);
  font-weight: 600;
  font-size: 11px;
  color: var(--text-primary);
  text-align: left;
  font-family: var(--font-mono);
  width: 70px;
  min-width: 70px;
}

.result-cell {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
}

.cell-pass {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.cell-strife {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  cursor: pointer;
}

.cell-fail {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  font-weight: 600;
  cursor: pointer;
}

.cell-empty {
  color: var(--text-muted);
}

.result-cell:hover {
  filter: brightness(0.96);
}
</style>