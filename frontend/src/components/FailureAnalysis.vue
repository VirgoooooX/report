<template>
  <div class="card">
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>{{ t('failureAnalysis.colDimension') }}</th>
            <th>{{ t('failureAnalysis.colSpecFail') }}</th>
            <th>{{ t('failureAnalysis.colStrifeFail') }}</th>
            <th>{{ t('failureAnalysis.colTotal') }}</th>
            <th>{{ t('failureAnalysis.colFailureRate') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in tableData"
            :key="i"
            :class="{ 'row-fail': row.failure_rate > 0 }"
            @click="emit('drill-down', drillPayload(row))"
            class="data-row"
          >
            <td>{{ i + 1 }}</td>
            <td>
              <span class="dim-name">{{ row.dimension }}</span>
            </td>
            <td>{{ row.spec_fail }}</td>
            <td>{{ row.strife_fail }}</td>
            <td>{{ row.total_fail }}</td>
            <td :class="{ 'rate-danger': row.failure_rate > 0 }">
              {{ row.failure_rate > 0 ? row.failure_rate.toFixed(2) + '%' : '0%' }}
            </td>
          </tr>
          <tr v-if="!tableData.length">
            <td colspan="6" class="empty-row">{{ t('common.empty') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

const props = defineProps({
  failuresData: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['drill-down'])

const tabs = [
  { key: 'top_failures', label: t('failureAnalysis.tabByTestItem') },
  { key: 'by_config', label: t('failureAnalysis.tabByConfig') },
  { key: 'by_wf', label: t('failureAnalysis.tabByWf') },
  { key: 'top_n', label: t('failureAnalysis.tabTopN') }
]

const activeTab = ref('top_failures')

const tableData = computed(() => {
  const key = activeTab.value
  const raw = props.failuresData?.[key]
  if (!raw) return []

  // Handle both array and object formats
  let data
  if (Array.isArray(raw)) {
    data = raw
  } else {
    data = Object.entries(raw).map(([name, val]) => ({ name, ...val }))
  }

  if (key === 'top_n') {
    data = data.slice(0, 20)
  }

  return data.map(d => ({
    wf: d.wf ?? d.wf_num ?? '',
    cfg: d.config ?? d.cfg ?? d.name ?? '',
    test: d.test ?? d.test_item ?? '',
    dimension: d.dimension ?? d.name ?? d.test ?? (d.wf ? `WF${d.wf} ${d.config || ''}` : d.name ?? '-'),
    spec_fail: d.spec_fails ?? d.spec ?? d.spec_fail ?? 0,
    strife_fail: d.strife_fails ?? d.strife ?? d.strife_fail ?? 0,
    total_fail: (d.total_tests ?? d.total ?? (d.spec_fails || d.spec || 0) + (d.strife_fails || d.strife || 0)),
    failure_rate: d.total_rate ?? d.rate ?? d.failure_rate ?? 0
  }))
})

function drillPayload(row) {
  return { wf: row.wf, cfg: row.cfg, test: row.test, dim: row.dimension }
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

.tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-light);
  padding: 0 20px;
}

.tab {
  padding: 12px 16px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-in-out),
              border-color var(--duration-fast) var(--ease-in-out);
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent-steel);
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

th {
  background: var(--bg-row-stripe);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}

.data-row {
  cursor: pointer;
}

.data-row:hover td {
  background: var(--bg-row-hover);
}

.data-row:nth-child(even) td {
  background: var(--bg-row-stripe);
}

.data-row:nth-child(even):hover td {
  background: var(--bg-row-hover);
}

.row-fail td:first-child {
  border-left: 3px solid var(--color-danger);
}

.dim-name {
  font-family: var(--font-mono);
  font-size: 12px;
}

.rate-danger {
  color: var(--color-danger);
  font-weight: 700;
}

.empty-row {
  text-align: center;
  color: var(--text-muted);
  padding: 32px 12px;
  font-size: 13px;
}
</style>
