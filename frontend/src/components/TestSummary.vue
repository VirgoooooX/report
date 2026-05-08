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
          <td class="wf-header">{{ wf }}</td>
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

const configs = computed(() => {
  return props.summaryData?.configs ?? ['R1FNF', 'R2CNM', 'R3', 'R4']
})

const wfs = computed(() => {
  return props.summaryData?.wfs ?? []
})

function cellStatus(wf, cfg) {
  const matrix = props.summaryData?.matrix ?? {}
  const cell = matrix[wf]?.[cfg]
  if (!cell) return 'empty'
  if (cell.fail_count > 0) return 'fail'
  if (cell.strife_count > 0) return 'strife'
  if (cell.pass_count > 0) return 'pass'
  return 'empty'
}

function cellText(wf, cfg) {
  const matrix = props.summaryData?.matrix ?? {}
  const cell = matrix[wf]?.[cfg]
  if (!cell) return '—'

  const parts = []
  if (cell.fail_count > 0) parts.push(cell.fail_count)
  if (cell.strife_count > 0) parts.push(`S${cell.strife_count}`)
  if (cell.pass_count > 0 && cell.fail_count === 0 && cell.strife_count === 0) {
    return cell.pass_count
  }
  return parts.join('/') || '—'
}

function cellClass(wf, cfg) {
  return `cell-${cellStatus(wf, cfg)}`
}

function onCellClick(wf, cfg) {
  const status = cellStatus(wf, cfg)
  if (status !== 'fail') return

  const matrix = props.summaryData?.matrix ?? {}
  const cell = matrix[wf]?.[cfg]
  if (!cell) return

  emit('cell-click', {
    wf,
    cfg,
    test: cell.test ?? '',
    failureSns: cell.failure_sns ?? []
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
