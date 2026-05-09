<template>
  <div class="page-container">
    <h1 class="page-title">SN Lookup</h1>

    <!-- Search Card -->
    <div class="card search-card">
      <div class="search-row">
        <input
          v-model="query"
          type="text"
          class="search-input"
          placeholder="Enter SN..."
          :class="{ 'has-chips': suggestions.length }"
          @input="onInput"
          @keydown.enter="doSearch"
        />
        <button class="search-btn" :disabled="!query.trim() || store.loading" @click="doSearch">
          {{ store.loading ? 'Searching...' : 'Search' }}
        </button>
      </div>
      <!-- Auto-complete chips -->
      <div v-if="suggestions.length" class="suggestions">
        <span
          v-for="s in suggestions"
          :key="s"
          class="suggestion-chip"
          @click="selectSuggestion(s)"
        >
          {{ s }}
        </span>
      </div>
    </div>

    <!-- Loading -->
    <LoadingState v-if="store.loading && !store.snResult" />

    <!-- Error -->
    <ErrorState
      v-if="errorMsg"
      :message="errorMsg"
      :retry="doSearch"
    />

    <!-- Result -->
    <div v-if="store.snResult" class="result-area">
      <!-- SN header -->
      <div class="sn-header" :class="{ 'has-failures': hasFailures }">
        <div class="sn-title-row">
          <h2 class="sn-title">SN: {{ store.snResult.sn || query }}</h2>
          <span v-if="hasFailures" class="fail-warning">{{ failureCount }} failure(s)</span>
        </div>
        <div class="sn-meta">
          <span v-if="store.snResult.unit" class="meta-item">Unit: {{ store.snResult.unit }}</span>
          <span v-if="store.snResult.model" class="meta-item">Model: {{ store.snResult.model }}</span>
        </div>
      </div>

      <!-- WF Grouped data -->
      <div v-for="group in wfGroups" :key="group.wf" class="card wf-group-card">
        <div class="wf-group-header" @click="toggleGroup(group.wf)">
          <span class="chevron" :class="{ open: expanded[group.wf] }">▶</span>
          <span class="wf-pill">WF{{ group.display }}</span>
          <span class="wf-group-name">{{ groupName(group.wf) }}</span>
          <span class="wf-group-config">{{ group.config }}</span>
          <span class="wf-group-date">{{ group.latest_date || '—' }}</span>
          <span class="wf-group-progress">{{ group.pct }}%</span>
          <StatusBadge v-if="group.cp_status" :type="group.cp_status" />
        </div>
        <div v-show="expanded[group.wf]" class="wf-group-body">
          <table class="history-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>CP</th>
                <th>Progress</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in group.history" :key="row.cp">
                <td>{{ row.date || '—' }}</td>
                <td class="cell-mono">{{ row.cp || '—' }}</td>
                <td>
                  <div class="inline-progress">
                    <div class="inline-track">
                      <div class="inline-fill" :style="{ width: (row.pct ?? 0) + '%' }"></div>
                    </div>
                    <span class="inline-label">{{ row.pct ?? 0 }}%</span>
                  </div>
                </td>
                <td>
                  <StatusBadge :type="row.status || 'pending'" />
                </td>
              </tr>
              <tr v-if="!group.history?.length">
                <td colspan="4" class="empty-row">No history available</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="!wfGroups.length" class="empty-result">No work-flow data found for this SN</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import StatusBadge from '@/components/StatusBadge.vue'

const store = useAppStore()
const query = ref('')
const suggestions = ref([])
const errorMsg = ref('')
const expanded = ref({})
let debounceTimer = null

const hasFailures = computed(() => {
  return (store.snResult?.failures?.length ?? 0) > 0
})

const failureCount = computed(() => {
  return store.snResult?.failures?.length ?? 0
})

const wfGroups = computed(() => {
  const byWf = store.snResult?.by_wf ?? []
  if (!Array.isArray(byWf)) return []
  return byWf.map(w => {
    const latest = w.latest || {}
    return {
      wf: w.wf || '',
      display: (w.wf || '').replace(/^WF/i, ''),
      config: latest.config || '',
      latest_date: latest.date || '',
      pct: latest.total_cps > 0 ? ((latest.cp_idx || 0) + 1) / latest.total_cps * 100 : 0,
      cp_status: '',
      history: (w.history || []).map(h => ({
        date: h.date || '',
        cp: h.current_cp || '',
        pct: h.total_cps > 0 ? ((h.cp_idx || 0) + 1) / h.total_cps * 100 : 0,
        status: 'pending'
      }))
    }
  })
})

function groupName(key) {
  return store.wfNames[key] || key
}

function toggleGroup(wf) {
  expanded.value[wf] = !expanded.value[wf]
}

function onInput() {
  clearTimeout(debounceTimer)
  if (query.value.length < 3) {
    suggestions.value = []
    return
  }
  debounceTimer = setTimeout(async () => {
    try {
      const results = await store.searchSn(query.value)
      suggestions.value = Array.isArray(results) ? results.slice(0, 8) : []
    } catch {
      suggestions.value = []
    }
  }, 300)
}

function selectSuggestion(sn) {
  query.value = sn
  suggestions.value = []
  doSearch()
}

async function doSearch() {
  const q = query.value.trim()
  if (!q) return
  errorMsg.value = ''
  suggestions.value = []
  try {
    await store.fetchSnResult(q)
  } catch (e) {
    errorMsg.value = e.message || 'SN not found'
    store.snResult = null
  }
}
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

/* Search */
.search-card {
  padding: 20px 24px;
  margin-bottom: 24px;
}

.search-row {
  display: flex;
  gap: 12px;
}

.search-input {
  flex: 1;
  padding: 10px 14px;
  font-family: 'Source Code Pro', monospace;
  font-size: 15px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--duration-fast) var(--ease-in-out);
}

.search-input:focus {
  border-color: var(--border-focus);
}

.search-input.has-chips {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.search-btn {
  padding: 10px 24px;
  font-size: 14px;
  font-family: var(--font-display);
  font-weight: 500;
  color: #fff;
  background: var(--accent-steel);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  white-space: nowrap;
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.search-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.search-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Suggestions */
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 4px 0;
}

.suggestion-chip {
  padding: 4px 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--bg-tag);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-full);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out),
              border-color var(--duration-fast) var(--ease-in-out);
}

.suggestion-chip:hover {
  background: var(--accent-steel);
  color: #fff;
  border-color: var(--accent-steel);
}

/* Result */
.result-area {
  margin-top: 8px;
}

.sn-header {
  padding: 18px 20px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-card);
  box-shadow: var(--shadow-card);
  margin-bottom: 16px;
}

.sn-header.has-failures {
  border-left: 4px solid var(--color-danger);
}

.sn-title-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 6px;
}

.sn-title {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.fail-warning {
  display: inline-block;
  padding: 2px 10px;
  background: var(--color-danger-bg);
  color: var(--color-danger);
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
}

.sn-meta {
  display: flex;
  gap: 20px;
}

.meta-item {
  font-size: 13px;
  color: var(--text-muted);
}

/* WF Group accordion */
.wf-group-card {
  margin-bottom: 8px;
  overflow: hidden;
}

.wf-group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-in-out);
}

.wf-group-header:hover {
  background: var(--bg-row-hover);
}

.chevron {
  font-size: 10px;
  color: var(--text-muted);
  transition: transform var(--duration-fast) var(--ease-in-out);
  flex-shrink: 0;
}

.chevron.open {
  transform: rotate(90deg);
}

.wf-pill {
  display: inline-block;
  padding: 2px 8px;
  background: #1a2332;
  color: #fff;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
}

.wf-group-name {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--text-muted);
  flex: 1;
}

.wf-group-config,
.wf-group-date {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  min-width: 60px;
}

.wf-group-progress {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 40px;
  text-align: right;
}

.wf-group-body {
  border-top: 1px solid var(--border-light);
}

/* History table */
.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.history-table th {
  background: var(--bg-row-stripe);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.history-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}

.history-table tr:hover td {
  background: var(--bg-row-hover);
}

.cell-mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* Inline progress */
.inline-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.inline-track {
  width: 80px;
  height: 6px;
  background: var(--bg-progress-track);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.inline-fill {
  height: 100%;
  background: var(--accent-steel);
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out);
}

.inline-label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.empty-row {
  text-align: center;
  color: var(--text-muted);
  padding: 24px 12px;
}

.empty-result {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 14px;
}
</style>
