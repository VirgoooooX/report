<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fa-overlay"
      @click.self="close"
      @keydown.esc="close"
      tabindex="-1"
    >
      <div class="fa-modal" :class="{ show: visible }">
        <div class="fa-modal-header">
          <h2 class="fa-modal-title">{{ title || t('failureAnalysis.title') }}</h2>
          <button class="fa-close-btn" @click="close">&times;</button>
        </div>
        <div class="fa-modal-body">
          <!-- Cross-checked issue table: Daily Report + FA Tracker -->
          <div v-if="issueRows.length" class="fa-cell-failures">
            <div class="fa-cell-detail-title">Cross-checked Failure Table</div>
            <table class="fa-issue-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th v-for="column in issueColumns" :key="column.key">{{ column.label }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, i) in issueRows"
                  :key="`${row.source}-${row.sn}-${i}`"
                  :class="{ 'row-warn': row.source !== 'matched' }"
                >
                  <td>{{ i + 1 }}</td>
                  <td
                    v-for="column in issueColumns"
                    :key="column.key"
                    :class="cellClass(column.key, row)"
                    :title="cellTitle(column.key, row)"
                  >
                    <span
                      v-if="column.key === 'type'"
                      :class="row.type === 'spec' ? 'type-spec' : row.type === 'strife' ? 'type-strife' : ''"
                    >
                      {{ typeLabel(row.type) }}
                    </span>
                    <span
                      v-else-if="column.key === 'source'"
                      class="source-badge"
                      :class="'source-' + row.source"
                    >
                      {{ sourceLabel(row.source) }}
                    </span>
                    <span v-else>{{ row[column.key] || '—' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Loading -->
          <div v-if="isLoading" class="fa-loading">
            <div class="spinner"></div>
            <span>{{ t('common.loading') }}</span>
          </div>

          <!-- Error -->
          <div v-else-if="faError" class="fa-error">
            <span class="error-message">{{ faError }}</span>
            <button class="retry-btn" @click="fetchFa">{{ t('actions.retry') }}</button>
          </div>

          <!-- Empty -->
          <div v-else-if="issueRows.length === 0" class="fa-empty">
            <p>{{ t('failureAnalysis.noRecordsFound') }}</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useI18n } from '@/i18n/useI18n'
import { requestJson } from '@/composables/useApi'
import { CELL_ISSUE_COLUMNS, buildFaListUrl, buildCellFailuresUrl, buildCellIssueRows } from '@/views/testSummaryModal.js'

const { t } = useI18n()

const props = defineProps({
  show: Boolean,
  wf: String,
  cfg: String,
  test: String,
  testIdx: Number,
  title: String,
  sns: { type: Array, default: () => [] },
  cellDetail: { type: Object, default: null }
})
const emit = defineEmits(['close'])

const faData = ref([])
const faLoading = ref(false)
const faError = ref(null)
const visible = ref(false)
const cellFailures = ref([])
const cellFailuresLoading = ref(false)
const issueRows = computed(() => buildCellIssueRows({
  cellFailures: cellFailures.value,
  faRecords: faData.value,
  testName: props.test,
}))
const issueColumns = CELL_ISSUE_COLUMNS
const isLoading = computed(() => faLoading.value || cellFailuresLoading.value)

function close() {
  emit('close')
}

function sourceLabel(s) {
  const map = {
    matched: 'Consistent',
    only_daily_report: 'Daily Report only',
    only_fa_tracker: 'FA Tracker only',
  }
  return map[s] || s
}

function typeLabel(type) {
  if (type === 'spec') return 'Spec'
  if (type === 'strife') return 'Strife'
  return type || '—'
}

function cellClass(key, row) {
  return {
    mono: key === 'sn',
    'cell-symptom': key === 'symptom',
    'cell-cycle': key === 'failed_cycle',
    'cell-source': key === 'source',
  }
}

function cellTitle(key, row) {
  return ['symptom', 'failed_cycle', 'location'].includes(key) ? row[key] : ''
}

async function fetchFa() {
  faLoading.value = true
  faError.value = null
  try {
    const d = await requestJson(buildFaListUrl({
      wf: props.wf,
      cfg: props.cfg,
      test: props.test,
      sns: props.sns,
      includeTest: false
    }))
    faData.value = d.records || []
  } catch (e) {
    faError.value = e.message
  } finally {
    faLoading.value = false
  }
}

async function fetchCellFailures() {
  if (props.testIdx == null || !props.sns.length) return
  cellFailuresLoading.value = true
  try {
    const d = await requestJson(buildCellFailuresUrl({
      wf: props.wf,
      cfg: props.cfg,
      testIdx: props.testIdx,
      sns: props.sns
    }))
    cellFailures.value = d.failures || []
  } catch (e) {
    cellFailures.value = []
  } finally {
    cellFailuresLoading.value = false
  }
}

watch(() => props.show, async (val) => {
  if (val) {
    faData.value = []
    faError.value = null
    cellFailures.value = []
    await nextTick()
    visible.value = true
    fetchFa()
    fetchCellFailures()
  } else {
    visible.value = false
  }
})
</script>

<style scoped>
.fa-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 35, 50, 0.4);
  backdrop-filter: blur(2px);
}

.fa-modal {
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--shadow-modal);
  width: min(96vw, 1180px);
  max-width: 1180px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  opacity: 0;
  transform: scale(0.97) translateY(20px);
  transition: opacity 300ms ease-out, transform 300ms ease-out;
}

.fa-modal.show {
  opacity: 1;
  transform: scale(1) translateY(0);
}

.fa-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.fa-modal-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: #1a2332;
  margin: 0;
}

.fa-close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  font-size: 22px;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast) var(--ease-in-out),
              color var(--duration-fast) var(--ease-in-out);
}

.fa-close-btn:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}

.fa-modal-body {
  padding: 16px 18px;
  overflow-y: auto;
  flex: 1;
}

.fa-cell-detail-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 10px;
}

/* Cell failure check-item details */
.fa-cell-failures {
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: 10px;
  background: color-mix(in srgb, var(--bg-row-hover) 50%, #fff);
}

.fa-issue-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: auto;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.fa-issue-table th {
  background: var(--bg-row-stripe);
  padding: 7px 8px;
  text-align: left;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-light);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  white-space: nowrap;
}

.fa-issue-table td {
  padding: 7px 8px;
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
  white-space: normal;
  overflow-wrap: anywhere;
}

.fa-issue-table th:nth-child(1),
.fa-issue-table td:nth-child(1) {
  width: 28px;
}

.fa-issue-table th:nth-child(2),
.fa-issue-table td:nth-child(2) {
  width: 104px;
}

.fa-issue-table th:nth-child(3),
.fa-issue-table td:nth-child(3) {
  width: 64px;
}

.fa-issue-table th:nth-child(4),
.fa-issue-table td:nth-child(4) {
  min-width: 150px;
}

.fa-issue-table th:nth-child(5),
.fa-issue-table td:nth-child(5) {
  min-width: 90px;
}

.cell-symptom {
  min-width: 180px;
}

.cell-cycle {
  min-width: 90px;
}

.cell-source {
  width: 120px;
}

.cell-source,
.mono,
.fa-issue-table td:nth-child(1),
.fa-issue-table td:nth-child(3) {
  white-space: nowrap;
}

.mono {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
}

.row-warn td { background: #fff9e6; }

.type-spec { color: var(--color-danger); font-weight: 600; }
.type-strife { color: #d97706; font-weight: 600; }

.source-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.source-matched { background: #d4edda; color: #155724; }
.source-only_daily_report { background: #fff3cd; color: #856404; }
.source-only_fa_tracker { background: #f8d7da; color: #721c24; }

/* Loading */
.fa-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-muted);
  font-size: 14px;
  font-family: var(--font-display);
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border-light);
  border-top-color: var(--accent-steel);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error */
.fa-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
}

.error-message {
  font-size: 14px;
  color: var(--color-danger);
  font-family: var(--font-display);
  text-align: center;
}

.retry-btn {
  padding: 8px 20px;
  background: var(--color-danger);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  font-family: var(--font-display);
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.retry-btn:hover {
  opacity: 0.9;
}

/* Empty */
.fa-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  gap: 16px;
}

.fa-empty p {
  font-size: 14px;
  color: var(--text-muted);
  font-family: var(--font-display);
}

.fa-sns-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

.fa-sn-tag {
  display: inline-block;
  padding: 3px 10px;
  background: var(--bg-tag);
  border-radius: var(--radius-full);
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

/* Records */
.fa-records {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fa-record-card {
  display: flex;
  background: #f5f7fa;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.fa-record-bar {
  width: 3px;
  flex-shrink: 0;
  background: #4f6f8f;
}

.fa-record-fields {
  flex: 1;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fa-field {
  display: flex;
  gap: 6px;
  font-size: 13px;
  font-family: var(--font-display);
  line-height: 1.5;
}

.fa-field-label {
  color: var(--text-muted);
  font-weight: 500;
  white-space: nowrap;
  text-transform: capitalize;
}

.fa-field-value {
  color: var(--text-primary);
  word-break: break-word;
}
</style>
