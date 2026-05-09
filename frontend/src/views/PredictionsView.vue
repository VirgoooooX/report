<template>
  <div class="page-container">
    <h1 class="page-title">Predictions</h1>

    <!-- Stats cards row -->
    <div class="stats-row">
      <div class="card stat-card">
        <span class="stat-label">Total</span>
        <span class="stat-value">{{ totalCount }}</span>
      </div>
      <div class="card stat-card">
        <span class="stat-label">Manual</span>
        <span class="stat-value">{{ manualCount }}</span>
      </div>
      <div class="card stat-card stat-overdue">
        <span class="stat-label">Overdue</span>
        <span class="stat-value">{{ overdueCount }}</span>
      </div>
      <div class="card stat-card stat-completed">
        <span class="stat-label">Completed</span>
        <span class="stat-value">{{ completedCount }}</span>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="card filter-card">
      <div class="filter-row">
        <div class="filter-group">
          <label class="filter-label">WF</label>
          <input v-model="filterWf" class="filter-input" placeholder="e.g. 1.1" />
        </div>
        <div class="filter-group">
          <label class="filter-label">Config</label>
          <select v-model="filterConfig" class="filter-select">
            <option value="">All Configs</option>
            <option v-for="c in configOptions" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <button class="refresh-btn" :disabled="store.loading" @click="loadData">
          {{ store.loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <LoadingState v-if="store.loading && !store.predictions.length" />

    <!-- Predictions table -->
    <div v-if="store.predictions.length" class="card table-wrap">
      <table>
        <thead>
          <tr>
            <th class="sortable col-wf" @click="sortBy('wf_num')">WF</th>
            <th class="sortable col-config" @click="sortBy('config')">Config</th>
            <th class="sortable col-test" @click="sortBy('test_idx')">Test</th>
            <th class="col-progress">Progress</th>
            <th class="sortable col-num" @click="sortBy('daily_rate')">Daily Rate</th>
            <th class="sortable col-num" @click="sortBy('remaining_days')">Rem. Days</th>
            <th class="sortable col-date" @click="sortBy('predicted_date')">Pred. Date</th>
            <th class="col-type">Type</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in sortedRows" :key="idx">
            <td class="cell-wf"><span class="wf-num">WF{{ row.wf_num }}</span><span class="wf-name" :title="wfName(row.wf_num)">{{ wfName(row.wf_num) }}</span></td>
            <td class="cell-mono col-config">{{ row.config }}</td>
            <td class="col-test cell-test-name">{{ row.test_name || 'Test' + ((row.test_idx || 0) + 1) }}</td>
            <td class="col-progress">
              <div class="progress-inline">
                <div class="progress-track-sm">
                  <div class="progress-fill-sm" :style="{ width: predProgress(row) + '%' }"></div>
                </div>
                <span class="progress-label">{{ predProgress(row).toFixed(1) }}%</span>
              </div>
            </td>
            <td class="cell-num col-num">{{ row.daily_rate != null ? Number(row.daily_rate).toFixed(1) : '—' }}</td>
            <td class="cell-num col-num">{{ row.remaining_days != null ? Number(row.remaining_days).toFixed(1) : '—' }}</td>
            <td class="col-date"><span class="editable-date" @click="openEdit(row)">{{ row.predicted_date || '—' }}</span></td>
            <td class="col-type"><StatusBadge :type="row.is_manual == 1 ? 'manual' : 'auto'" /></td>
          </tr>
          <tr v-if="!store.predictions.length">
            <td colspan="8" class="empty-row">No predictions found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Edit Date Modal -->
    <div v-if="editModal" class="modal-overlay" @click.self="editModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Edit Predicted Date</h3>
          <button class="modal-close" @click="editModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="modal-field">
            <strong>Test:</strong> WF{{ editRow?.wf_num }} / {{ editRow?.config }} / Test{{ (editRow?.test_idx || 0) + 1 }}
          </div>
          <div class="modal-field">
            <label class="field-label">Date</label>
            <input v-model="editDate" type="date" class="date-input" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="editModal = false">Cancel</button>
          <button class="btn-primary" @click="saveEdit">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import StatusBadge from '@/components/StatusBadge.vue'
import LoadingState from '@/components/LoadingState.vue'

const store = useAppStore()
const filterWf = ref('')
const filterConfig = ref('')
const sortField = ref('wf_num')
const sortDir = ref('asc')
const editModal = ref(false)
const editRow = ref(null)
const editDate = ref('')

const configOptions = ['R1FNF', 'R2CNM', 'R3', 'R4']

const totalCount = computed(() => store.predictions.length)
const manualCount = computed(() => store.predictions.filter(p => p.is_manual == 1).length)
const overdueCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  return store.predictions.filter(p => p.predicted_date && p.predicted_date < today && p.remaining_days > 0).length
})
const completedCount = computed(() => store.predictions.filter(p => (p.remaining_days ?? 1) <= 0).length)

function wfName(wfNum) {
  const key = String(wfNum).replace(/^WF/i, '')
  return store.wfNames[key] || ''
}

function predProgress(row) {
  if (row.total_cps > 0) return (row.current_max_cp || 0) / row.total_cps * 100
  return 0
}

function sortBy(field) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDir.value = 'asc'
  }
}

function sortIndicator(field) {
  if (sortField.value !== field) return ''
  return sortDir.value === 'asc' ? '▲' : '▼'
}

const sortedRows = computed(() => {
  const rows = [...store.predictions]
  rows.sort((a, b) => {
    let va = a[sortField.value]
    let vb = b[sortField.value]
    if (va == null) va = ''
    if (vb == null) vb = ''
    if (typeof va === 'string' || typeof vb === 'string') {
      const cmp = String(va).localeCompare(String(vb), undefined, { numeric: true, sensitivity: 'base' })
      return sortDir.value === 'asc' ? cmp : -cmp
    }
    return sortDir.value === 'asc' ? va - vb : vb - va
  })
  return rows
})

async function loadData() {
  try {
    await Promise.all([
      store.fetchOverview(),
      store.fetchPredictions(filterWf.value || null, filterConfig.value || null)
    ])
  } catch {
    // silently handle
  }
}

function openEdit(row) {
  editRow.value = row
  editDate.value = row.predicted_date || ''
  editModal.value = true
}

async function saveEdit() {
  if (!editRow.value) return
  try {
    const r = await fetch('/api/predictions/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        wf_num: editRow.value.wf_num,
        config: editRow.value.config,
        test_idx: editRow.value.test_idx,
        predicted_date: editDate.value
      })
    })
    if (!r.ok) throw new Error('Update failed')
    editRow.value.predicted_date = editDate.value
    editModal.value = false
  } catch {
    // silently handle
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 32px 40px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: #1a2332;
  margin-bottom: 24px;
}

/* Stats row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
}

.stat-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-overdue .stat-value {
  color: var(--color-danger);
}

.stat-completed .stat-value {
  color: var(--color-success);
}

/* Filter */
.filter-card {
  padding: 16px 20px;
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
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
  min-width: 160px;
}

.filter-input:focus,
.filter-select:focus {
  border-color: var(--border-focus);
}

.refresh-btn {
  padding: 8px 20px;
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 500;
  color: #fff;
  background: var(--accent-steel);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.refresh-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Table */
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
  white-space: nowrap;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  color: var(--text-primary);
}

.sort-indicator {
  font-size: 9px;
  margin-left: 2px;
}

td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}

tr:hover td {
  background: var(--bg-row-hover);
}

.col-wf { text-align: left !important; min-width: 140px; }
.col-test { text-align: left !important; }
.col-progress { text-align: center !important; min-width: 110px; }
.col-num { text-align: center !important; min-width: 65px; }
.col-date { text-align: center !important; min-width: 85px; }
.col-type { text-align: center !important; min-width: 50px; }
.col-config { text-align: center !important; min-width: 50px; }

.cell-wf { text-align: left; white-space: nowrap; }
.wf-num { font-family: var(--font-mono); font-weight: 600; color: var(--text-primary); }
.wf-name { font-size: 12px; color: var(--text-muted); margin-left: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100px; display: inline-block; vertical-align: bottom; }

.cell-test-name { font-size: 13px; white-space: nowrap; }
.cell-mono { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.cell-num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

/* Progress bar inline */
.progress-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}

.progress-track-sm {
  flex: 1;
  height: 6px;
  background: var(--bg-progress-track);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill-sm {
  height: 100%;
  background: var(--accent-steel);
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out);
}

.progress-label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);
  min-width: 36px;
  text-align: right;
}

/* Editable date */
.editable-date {
  color: var(--accent-steel);
  text-decoration: underline;
  text-decoration-style: dotted;
  cursor: pointer;
}

.editable-date:hover {
  color: #1a2332;
}

.empty-row {
  text-align: center;
  color: var(--text-muted);
  padding: 32px 12px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-modal);
  width: 420px;
  max-width: 90vw;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-light);
}

.modal-header h3 {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  font-size: 22px;
  color: var(--text-muted);
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
}

.modal-close:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}

.modal-body {
  padding: 20px 24px;
}

.modal-field {
  margin-bottom: 14px;
  font-size: 14px;
  color: var(--text-secondary);
}

.modal-field strong {
  color: var(--text-primary);
}

.field-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.date-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  font-family: var(--font-mono);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  outline: none;
}

.date-input:focus {
  border-color: var(--border-focus);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 24px;
  border-top: 1px solid var(--border-light);
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

.btn-secondary:hover {
  background: var(--bg-row-stripe);
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

.btn-primary:hover {
  opacity: 0.9;
}

@media (max-width: 700px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }
  .filter-input,
  .filter-select {
    min-width: auto;
  }
}
</style>
