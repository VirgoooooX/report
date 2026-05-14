<template>
  <div class="page-container">
    <h1 class="page-title">{{ t('export.title') }}</h1>

    <!-- Filter form -->
    <div class="card filter-card">
      <div class="filter-form">
        <div class="filter-group">
          <label class="filter-label">{{ t('export.filterWf') }}</label>
          <input v-model="filters.wf" class="filter-input" :placeholder="t('export.wfPlaceholder')" />
        </div>
        <div class="filter-group">
          <label class="filter-label">{{ t('export.filterConfig') }}</label>
          <select v-model="filters.config" class="filter-select">
            <option value="">{{ t('export.all') }}</option>
            <option v-for="c in configOptions" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="filter-label">{{ t('export.filterSn') }}</label>
          <input v-model="filters.sn" class="filter-input" :placeholder="t('export.serialNumber')" />
        </div>
        <div class="filter-group">
          <label class="filter-label">{{ t('export.filterFormat') }}</label>
          <select v-model="exportFormat" class="filter-select">
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
          </select>
        </div>
      </div>
      <div class="filter-actions">
        <button class="btn-outline" @click="previewData" :disabled="store.loading">
          {{ store.loading ? t('export.loading') : t('export.preview') }}
        </button>
        <button class="btn-primary" @click="downloadCSV" :disabled="!hasData">
          {{ t('export.downloadCsv') }}
        </button>
        <button class="btn-secondary" @click="downloadJSON" :disabled="!hasData">
          {{ t('export.downloadJson') }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <LoadingState v-if="store.loading && !store.exportData" />

    <!-- Preview table -->
    <div v-if="previewRows.length" class="card table-wrap">
      <div class="preview-header">
        <span class="preview-title">{{ t('export.previewRows', { count: previewRows.length }) }}</span>
        <span class="preview-note">{{ t('export.showingUpTo') }}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>{{ t('export.colSn') }}</th>
            <th>{{ t('export.colUnit') }}</th>
            <th>{{ t('export.colWf') }}</th>
            <th>{{ t('export.colConfig') }}</th>
            <th>{{ t('export.colCurrentCp') }}</th>
            <th>{{ t('export.colProgress') }}</th>
            <th>{{ t('export.colCpResults') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in previewRows" :key="idx">
            <td class="cell-mono">{{ row.sn || '—' }}</td>
            <td>{{ row.unit_num || '—' }}</td>
            <td class="cell-mono">WF{{ row.wf_num || '—' }}</td>
            <td class="cell-mono">{{ row.config || '—' }}</td>
            <td class="cell-mono">{{ row.current_cp_name || '—' }}</td>
            <td>
              <div class="progress-inline">
                <div class="progress-track-xs">
                  <div class="progress-fill-xs" :style="{ width: rowProgress(row) + '%' }"></div>
                </div>
                <span class="progress-label-xs">{{ rowProgress(row).toFixed(1) }}%</span>
              </div>
            </td>
            <td>
              <span
                v-for="(r, ri) in cpResults(row)"
                :key="ri"
                class="cp-chip"
                :class="'cp-' + r.status"
              >{{ r.label }}</span>
              <span v-if="!cpResults(row).length" class="text-muted">—</span>
            </td>
          </tr>
          <tr v-if="!previewRows.length">
            <td colspan="7" class="empty-row">{{ t('export.noDataPreview') }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty state -->
    <div v-else-if="!store.loading" class="empty-state">
      <p v-html="t('export.adjustFilters')"></p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'
import { requestJson } from '@/composables/useApi'
import LoadingState from '@/components/LoadingState.vue'

const store = useAppStore()
const { t } = useI18n()
const filters = ref({ wf: '', config: '', sn: '' })
const exportFormat = ref('csv')

const configOptions = ['R1FNF', 'R2CNM', 'R3', 'R4']

const hasData = computed(() => {
  return store.exportData && previewRows.value.length > 0
})

const previewRows = computed(() => {
  const data = store.exportData
  if (!data) return []
  const rows = data.rows ?? data.data ?? data.records ?? data.items ?? []
  if (!Array.isArray(rows)) return []
  return rows.slice(0, 50)
})

function rowProgress(row) {
  if (row.total_cps > 0) return (row.current_cp_idx || 0) / row.total_cps * 100
  return 0
}

function cpResults(row) {
  const results = row.cp_results ?? row.results ?? []
  if (!Array.isArray(results)) return []
  return results.map(r => ({
    label: r.cp ?? r.name ?? '',
    status: r.status === 'pass' ? 'pass' : r.status === 'fail' ? 'fail' : r.status === 'strife' ? 'strife' : 'pending'
  }))
}

async function previewData() {
  try {
    await store.fetchExportData({
      wf: filters.value.wf || null,
      config: filters.value.config || null,
      sn: filters.value.sn || null
    })
  } catch (e) {
    store.error = e.message || t('common.error')
  }
}

function downloadCSV() {
  const data = store.exportData
  if (!data) return

  const params = new URLSearchParams()
  if (filters.value.wf) params.set('wf', filters.value.wf)
  if (filters.value.config) params.set('config', filters.value.config)
  if (filters.value.sn) params.set('sn', filters.value.sn)
  params.set('format', 'csv')

  window.location.href = `/api/export?${params}`
}

async function downloadJSON() {
  const data = store.exportData
  if (!data) return

  const params = new URLSearchParams()
  if (filters.value.wf) params.set('wf', filters.value.wf)
  if (filters.value.config) params.set('config', filters.value.config)
  if (filters.value.sn) params.set('sn', filters.value.sn)
  params.set('format', 'json')

  try {
    const payload = await requestJson(`/api/export?${params}`)
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `export-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    store.error = e.message || t('common.error')
  }
}
</script>

<style scoped>
.page-container {
  color: var(--text-primary);
}

/* Filter card */
.filter-card {
  padding: 20px 24px;
  margin-bottom: 20px;
}

.filter-form {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.filter-input,
.filter-select {
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-mono);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  outline: none;
}

.filter-input:focus,
.filter-select:focus {
  border-color: var(--border-focus);
}

.filter-actions {
  display: flex;
  gap: 10px;
  padding-top: 4px;
}

/* Buttons */
.btn-outline {
  padding: 8px 20px;
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 500;
  color: var(--accent-steel);
  background: transparent;
  border: 1px solid var(--accent-steel);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out),
              color var(--duration-fast) var(--ease-in-out);
}

.btn-outline:hover:not(:disabled) {
  background: var(--accent-steel);
  color: #fff;
}

.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  padding: 8px 20px;
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 500;
  color: #fff;
  background: var(--accent-steel);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 20px;
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-row-stripe);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Preview */
.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-light);
}

.preview-title {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.preview-note {
  font-size: 12px;
  color: var(--text-muted);
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
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

tr:hover td {
  background: var(--bg-row-hover);
}

.cell-mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Progress inline */
.progress-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-track-xs {
  width: 60px;
  height: 5px;
  background: var(--bg-progress-track);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill-xs {
  height: 100%;
  background: var(--accent-steel);
  border-radius: var(--radius-full);
}

.progress-label-xs {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

/* CP chips */
.cp-chip {
  display: inline-block;
  padding: 1px 6px;
  margin: 1px 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  border-radius: 3px;
  letter-spacing: 0.2px;
}

.cp-pass {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.cp-fail {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.cp-strife {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.cp-pending {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.text-muted {
  color: var(--text-muted);
}

.empty-row {
  text-align: center;
  color: var(--text-muted);
  padding: 32px 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
  font-size: 14px;
}

@media (max-width: 700px) {
  .filter-form {
    grid-template-columns: 1fr 1fr;
  }
  .filter-actions {
    flex-direction: column;
  }
}
</style>
