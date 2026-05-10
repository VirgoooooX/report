<template>
  <div class="page-container">
    <h1 class="page-title">{{ t('predictions.title') }}</h1>

    <!-- Stats cards row -->
    <div class="stats-row">
      <div class="card stat-card">
        <span class="stat-label">{{ t('predictions.statsTotal') }}</span>
        <span class="stat-value">{{ totalCount }}</span>
      </div>
      <div class="card stat-card">
        <span class="stat-label">{{ t('predictions.statsManual') }}</span>
        <span class="stat-value">{{ manualCount }}</span>
      </div>
      <div class="card stat-card stat-overdue">
        <span class="stat-label">{{ t('predictions.statsOverdue') }}</span>
        <span class="stat-value">{{ overdueCount }}</span>
      </div>
      <div class="card stat-card stat-completed">
        <span class="stat-label">{{ t('predictions.statsCompleted') }}</span>
        <span class="stat-value">{{ completedCount }}</span>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="card filter-card">
      <div class="filter-row">
        <div class="filter-group">
          <label class="filter-label">{{ t('predictions.filterWf') }}</label>
          <input v-model="filterWf" class="filter-input" :placeholder="t('predictions.filterWfPlaceholder')" />
        </div>
        <div class="filter-group">
          <label class="filter-label">{{ t('predictions.filterConfig') }}</label>
          <select v-model="filterConfig" class="filter-select">
            <option value="">{{ t('predictions.allConfigs') }}</option>
            <option v-for="c in configOptions" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <button class="refresh-btn" :disabled="store.loading" @click="loadData">
          {{ store.loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <LoadingState v-if="store.loading && !store.predictions.length" />

    <!-- Predictions by WF -->
    <div v-if="store.predictions.length" class="card pred-card">
      <div class="pred-header">
        <span class="pred-title">{{ t('predictions.byWorkflow') }}</span>
        <span class="pred-count">{{ groupedWfs.length }} WF(s), {{ totalCount }} {{ t('predictions.countTests') }}</span>
      </div>
      <div class="flow-list">
        <!-- Global column headers — same flex structure as data rows -->
        <div class="test-row test-row-hdr">
          <span class="col-cfg">{{ t('predictions.colConfig') }}</span>
          <span class="test-name">{{ t('predictions.colTest') }}</span>
          <div class="test-progress">{{ t('predictions.colProgress') }}</div>
          <span class="test-rate">{{ t('predictions.colRate') }}</span>
          <span class="test-remaining">{{ t('predictions.colRemaining') }}</span>
          <span class="test-date">{{ t('predictions.colPredDate') }}</span>
          <span class="col-type">{{ t('predictions.colType') }}</span>
        </div>
        <div v-for="wf in groupedWfs" :key="wf.wfNum" class="flow-block">
          <!-- WF label -->
          <div class="flow-label" @click="toggleWf(wf.wfNum)">
            <span class="chevron" :class="{ open: expandedWfs[wf.wfNum] }">▶</span>
            <span class="flow-pill">WF{{ wf.wfNum }}</span>
            <span class="flow-name">{{ wfName(wf.wfNum) }}</span>
            <span class="flow-count">{{ wf.tests.length }} {{ t('predictions.countTests') }}</span>
          </div>

          <!-- WF body -->
          <div class="flow-body" :class="{ collapsed: !expandedWfs[wf.wfNum] }">
            <div v-for="cfg in ['R1FNF','R2CNM','R3','R4']" :key="cfg">
              <template v-if="wf.byConfig[cfg]?.length">
                <div v-for="row in wf.byConfig[cfg]" :key="row.test_idx" class="test-row" @click="openEdit(row)">
                  <span class="col-cfg"><span class="cfg-badge" :style="badgeStyle(cfg)">{{ cfg }}</span></span>
                  <span class="test-name">{{ row.test_name || 'Test' + ((row.test_idx || 0) + 1) }}</span>
                  <div class="test-progress">
                    <div class="test-bar-track">
                      <div class="test-bar-fill" :style="{ width: predProgress(row) + '%' }"></div>
                    </div>
                    <span class="test-pct">{{ predProgress(row).toFixed(0) }}%</span>
                  </div>
                  <span class="test-rate">{{ row.daily_rate != null ? Number(row.daily_rate).toFixed(1) + '/d' : '—' }}</span>
                  <span class="test-remaining" :class="{ overdue: isOverdue(row) }">
                    {{ row.remaining_days != null ? Number(row.remaining_days).toFixed(0) + 'd' : '—' }}
                  </span>
                  <span class="test-date editable-date">{{ row.predicted_date || '—' }}</span>
                  <StatusBadge :type="row.is_manual == 1 ? 'manual' : 'auto'" />
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Date Modal -->
    <div v-if="editModal" class="modal-overlay" @click.self="editModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ t('predictions.editTitle') }}</h3>
          <button class="modal-close" @click="editModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="modal-field">
            <strong>{{ t('predictions.editTest') }}</strong> WF{{ editRow?.wf_num }} / {{ editRow?.config }} / {{ editRow?.test_name || 'Test' + ((editRow?.test_idx || 0) + 1) }}
          </div>
          <div class="modal-field">
            <label class="field-label">{{ t('predictions.editDate') }}</label>
            <input v-model="editDate" type="date" class="date-input" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="editModal = false">{{ t('common.cancel') }}</button>
          <button class="btn-primary" @click="saveEdit">{{ t('common.save') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'
import { requestJson } from '@/composables/useApi'
import StatusBadge from '@/components/StatusBadge.vue'
import LoadingState from '@/components/LoadingState.vue'

const store = useAppStore()
const { t } = useI18n()
const filterWf = ref('')
const filterConfig = ref('')
const editModal = ref(false)
const editRow = ref(null)
const editDate = ref('')
const expandedWfs = reactive({})

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

function isOverdue(row) {
  const today = new Date().toISOString().slice(0, 10)
  return row.predicted_date && row.predicted_date < today && row.remaining_days > 0
}

// Group predictions by WF → Config → tests
const groupedWfs = computed(() => {
  const map = {}
  for (const row of store.predictions) {
    const wf = String(row.wf_num)
    if (!map[wf]) {
      map[wf] = { wfNum: wf, byConfig: {}, tests: [] }
    }
    const cfg = row.config
    if (!map[wf].byConfig[cfg]) map[wf].byConfig[cfg] = []
    map[wf].byConfig[cfg].push(row)
    map[wf].tests.push(row)
  }
  // Auto-expand all
  for (const wf of Object.keys(map)) {
    if (expandedWfs[wf] === undefined) expandedWfs[wf] = true
  }
  return Object.values(map).sort((a, b) => {
    const na = parseFloat(a.wfNum)
    const nb = parseFloat(b.wfNum)
    if (!isNaN(na) && !isNaN(nb)) return na - nb
    return String(a.wfNum).localeCompare(String(b.wfNum), undefined, { numeric: true })
  })
})

function toggleWf(wfNum) {
  expandedWfs[wfNum] = !expandedWfs[wfNum]
}

const CFG_COLORS = { R1FNF: '#4f6f8f', R2CNM: '#0891b2', R3: '#d97706', R4: '#059669' }
function badgeStyle(c) {
  const color = CFG_COLORS[c] || '#4f6f8f'
  return { color, borderColor: color + '40', backgroundColor: color + '0d' }
}

async function loadData() {
  try {
    await Promise.all([
      store.fetchOverview(),
      store.fetchPredictions(filterWf.value || null, filterConfig.value || null)
    ])
  } catch (e) {
    store.error = e.message || 'Failed to load predictions'
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
    await requestJson('/api/predictions/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        wf_num: editRow.value.wf_num,
        config: editRow.value.config,
        test_idx: editRow.value.test_idx,
        predicted_date: editDate.value
      })
    })
    await loadData()
    editModal.value = false
  } catch (e) {
    store.error = e.message || 'Update failed'
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 32px 40px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
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

.stat-overdue .stat-value { color: var(--color-danger); }
.stat-completed .stat-value { color: var(--color-success); }

/* Filter */
.filter-card { padding: 16px 20px; margin-bottom: 16px; }
.filter-row { display: flex; align-items: flex-end; gap: 16px; }
.filter-group { display: flex; flex-direction: column; gap: 4px; }
.filter-label {
  font-size: 11px; font-weight: 500; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.4px;
}
.filter-input, .filter-select {
  padding: 8px 12px; font-size: 13px; font-family: var(--font-mono);
  border: 1px solid var(--border-input); border-radius: var(--radius-sm);
  background: var(--bg-input); color: var(--text-primary); outline: none; min-width: 160px;
}
.filter-input:focus, .filter-select:focus { border-color: var(--border-focus); }
.refresh-btn {
  padding: 8px 20px; font-size: 13px; font-family: var(--font-display);
  font-weight: 500; color: #fff; background: var(--accent-steel);
  border: none; border-radius: var(--radius-sm); cursor: pointer; white-space: nowrap;
}
.refresh-btn:hover:not(:disabled) { opacity: 0.9; }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Predictions card */
.pred-card { overflow: hidden; }
.pred-header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 20px; border-bottom: 1px solid var(--border-light);
}
.pred-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.pred-count { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }

/* Flow list (by WF) */
.flow-list { padding: 0 20px 16px; }
.flow-block {
  padding: 10px 0 10px 14px; border-left: 3px solid transparent;
  transition: border-color var(--duration-fast);
}
.flow-block:hover { border-left-color: var(--border-card); }
.flow-block + .flow-block { border-top: 1px solid var(--border-light); }

.flow-label {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 8px; cursor: pointer; user-select: none;
}
.chevron { font-size: 10px; color: var(--text-muted); transition: transform var(--duration-fast); flex-shrink: 0; }
.chevron.open { transform: rotate(90deg); }
.flow-pill {
  padding: 3px 10px; background: #1a2332; color: #fff;
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  border-radius: var(--radius-sm); flex-shrink: 0; letter-spacing: 0.3px;
}
.flow-name {
  font-size: 14px; color: var(--text-primary); font-weight: 600;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.flow-count {
  font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);
  margin-left: auto; flex-shrink: 0;
}

/* Collapsible body */
.flow-body { max-height: 4000px; overflow: hidden; transition: max-height var(--duration-normal); }
.flow-body.collapsed { max-height: 0; }

/* Header row — same flex as test-row */
.test-row-hdr {
  cursor: default; pointer-events: none;
  padding: 8px 8px 6px;
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.4px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-row-stripe);
  border-radius: 0;
}

/* Test rows (data + header) */
.test-row {
  display: flex; align-items: center; gap: 12px;
  padding: 5px 8px; border-radius: var(--radius-sm);
  cursor: pointer; transition: background var(--duration-fast);
}
.test-row:hover:not(.test-row-hdr) { background: var(--bg-root); }

.col-cfg { flex: 0 0 58px; text-align: center; }
.col-type { flex: 0 0 50px; text-align: center; }
.cfg-badge {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  padding: 2px 8px; border-radius: 3px; border: 1px solid;
}
.test-name {
  font-size: 13px; color: var(--text-primary); font-weight: 500;
  flex: 0 0 160px; min-width: 80px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.test-progress { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 100px; justify-content: center; }
.test-bar-track { flex: 1; height: 4px; background: var(--bg-progress-track); border-radius: 2px; overflow: hidden; }
.test-bar-fill { height: 100%; background: var(--accent-steel); border-radius: 2px; opacity: 0.5; transition: width 0.8s var(--ease-out); }
.test-pct { font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); min-width: 28px; text-align: right; }

.test-rate {
  font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);
  flex: 0 0 50px; text-align: center;
}
.test-remaining {
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  color: var(--text-primary); flex: 0 0 56px; text-align: center;
}
.test-remaining.overdue { color: var(--color-danger); }
.test-date {
  font-family: var(--font-mono); font-size: 12px;
  color: var(--accent-steel); flex: 0 0 72px; text-align: center;
}
.editable-date {
  text-decoration: underline; text-decoration-style: dotted; cursor: pointer;
}
.editable-date:hover { color: #1a2332; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: var(--bg-overlay);
  display: flex; align-items: center; justify-content: center;
}
.modal-card {
  background: var(--bg-card); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-modal); width: 420px; max-width: 90vw;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 24px; border-bottom: 1px solid var(--border-light);
}
.modal-header h3 { font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--text-primary); }
.modal-close {
  background: none; border: none; font-size: 22px; color: var(--text-muted);
  cursor: pointer; width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center; border-radius: var(--radius-sm);
}
.modal-close:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.modal-body { padding: 20px 24px; }
.modal-field { margin-bottom: 14px; font-size: 14px; color: var(--text-secondary); }
.modal-field strong { color: var(--text-primary); }
.field-label { display: block; font-size: 12px; font-weight: 500; color: var(--text-muted); margin-bottom: 4px; }
.date-input {
  width: 100%; padding: 8px 12px; font-size: 14px; font-family: var(--font-mono);
  border: 1px solid var(--border-input); border-radius: var(--radius-sm);
  background: var(--bg-input); color: var(--text-primary); outline: none;
}
.date-input:focus { border-color: var(--border-focus); }
.modal-footer {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 14px 24px; border-top: 1px solid var(--border-light);
}
.btn-secondary {
  padding: 8px 20px; font-size: 13px; font-family: var(--font-display);
  font-weight: 500; color: var(--text-secondary); background: transparent;
  border: 1px solid var(--border-input); border-radius: var(--radius-sm); cursor: pointer;
}
.btn-secondary:hover { background: var(--bg-row-stripe); }
.btn-primary {
  padding: 8px 20px; font-size: 13px; font-family: var(--font-display);
  font-weight: 500; color: #fff; background: var(--accent-steel);
  border: none; border-radius: var(--radius-sm); cursor: pointer;
}
.btn-primary:hover { opacity: 0.9; }

@media (max-width: 700px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .filter-row { flex-direction: column; align-items: stretch; }
  .filter-input, .filter-select { min-width: auto; }
  .cfg-row { flex-direction: column; gap: 4px; }
  .test-row { flex-wrap: wrap; gap: 6px; }
}
</style>
