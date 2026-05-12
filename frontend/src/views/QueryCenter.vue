<template>
  <div class="page-container page-shell">
    <h1 class="page-title">{{ t('queryCenter.title') }}</h1>

    <div class="mode-tabs" role="tablist">
      <button
        v-for="m in modes"
        :key="m.key"
        class="mode-tab"
        :class="{ active: activeMode === m.key }"
        role="tab"
        :aria-selected="activeMode === m.key"
        @click="activeMode = m.key"
      >{{ t(m.i18n) }}</button>
    </div>

    <!-- Global check-item filter (only meaningful when a query has returned data). -->
    <div v-if="availableCheckItems.length" class="filter-bar">
      <label class="filter-label">{{ t('queryCenter.checkItem') }}:</label>
      <select v-model="checkItemFilter" class="filter-select">
        <option :value="null">{{ t('queryCenter.allCpLevel') }}</option>
        <option v-for="ci in availableCheckItems" :key="ci" :value="ci">{{ ci }}</option>
      </select>
    </div>

    <!-- Single SN -->
    <div v-if="activeMode === 'single'" class="mode-content">
      <div class="card search-card">
        <div class="search-row">
          <input
            v-model="singleQuery"
            type="text"
            class="search-input"
            :placeholder="t('queryCenter.snOrMarkPlaceholder')"
            @input="onSingleInput"
            @keydown.enter="doSingleSearch"
          />
          <button
            class="search-btn"
            :disabled="!singleQuery.trim() || loading"
            @click="doSingleSearch"
          >{{ loading ? t('common.loading') : t('actions.search') }}</button>
        </div>
        <div v-if="singleSuggestions.length" class="suggestions">
          <span
            v-for="s in singleSuggestions"
            :key="s.sn + '|' + s.unit_num"
            class="suggestion-chip"
            @click="selectSuggestion(s)"
          >
            <span class="chip-sn">{{ s.sn }}</span>
            <span v-if="s.unit_num" class="chip-mark">{{ s.unit_num }}</span>
          </span>
        </div>
        <ErrorState v-if="singleError" :message="singleError" @retry="doSingleSearch" />
      </div>

      <LoadingState v-if="loading && !singleResult.length" />

      <div v-if="singleResult.length" class="sn-result">
        <div class="sn-header" :class="{ 'has-failures': singleHasFailures }">
          <h2 class="sn-title">SN: {{ resolvedSn }}</h2>
          <span v-if="singleMark" class="sn-mark">{{ singleMark }}</span>
          <span v-if="singleHasFailures" class="fail-warning">
            {{ singleFailCount }} {{ t('snLookup.failures') }}
          </span>
        </div>

        <div
          v-for="g in singleResult"
          :key="g.wf_num + '_' + g.config"
          class="card lifecycle-card"
        >
          <div class="lifecycle-card-header">
            <span class="wf-pill">WF{{ g.wf_num }}</span>
            <span class="wf-config">{{ g.config }}</span>
            <span class="wf-test-name">{{ g.test_name || wfDisplayName(g.wf_num) }}</span>
          </div>
          <SnLifecycle
            :cpList="g.cpList"
            :checkItems="g.checkItems"
            :checkItemFilter="checkItemFilter"
            :lazyLoadChecks="(cpIdx) => store.fetchSnCheckDetails(resolvedSn, g.wf_num, g.config, cpIdx)"
          />
        </div>
      </div>
    </div>

    <!-- WF & Config -->
    <div v-if="activeMode === 'wcfg'" class="mode-content">
      <div class="card wcfg-filters">
        <label class="filter-label">{{ t('queryCenter.wf') }}:</label>
        <select v-model="wcfgSelectedWf" class="filter-select" @change="onWfChange">
          <option value="">{{ t('queryCenter.selectWf') }}</option>
          <option v-for="wf in wfOptions" :key="wf.wf_num" :value="wf.wf_num">
            WF{{ wf.wf_num }} — {{ wf.wf_name }}
          </option>
        </select>
        <label class="filter-label">{{ t('queryCenter.config') }}:</label>
        <select v-model="wcfgSelectedConfig" class="filter-select" @change="doWfCfgSearch">
          <option value="">{{ t('queryCenter.allConfigs') }}</option>
          <option v-for="c in configOptions" :key="c" :value="c">{{ c }}</option>
        </select>
        <button
          class="search-btn"
          :disabled="!wcfgSelectedWf || loading"
          @click="doWfCfgSearch"
        >{{ loading ? t('common.loading') : t('actions.search') }}</button>
        <ErrorState v-if="wcfgError" :message="wcfgError" @retry="doWfCfgSearch" />
      </div>

      <LoadingState v-if="loading && !wcfgData" />

      <template v-if="wcfgData">
        <div class="card wcfg-summary">
          <div class="summary-grid">
            <div class="summary-item">
              <span class="sum-label">{{ t('queryCenter.totalSn') }}</span>
              <span class="sum-val">{{ wcfgData.summary.total_sns || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="sum-label">{{ t('common.completed') }}</span>
              <span class="sum-val pass">{{ wcfgData.summary.completed || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="sum-label">Spec</span>
              <span class="sum-val fail">{{ wcfgData.summary.spec_fails || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="sum-label">Strife</span>
              <span class="sum-val strife">{{ wcfgData.summary.strife_fails || 0 }}</span>
            </div>
          </div>
        </div>

        <div class="sn-list">
          <div v-for="sn in wcfgData.sns" :key="sn.sn + '_' + sn.config" class="card sn-list-item">
            <div class="sn-list-header" @click="toggleWcfgSn(sn.sn + '_' + sn.config)">
              <span class="chevron" :class="{ open: wcfgExpanded[sn.sn + '_' + sn.config] }">▶</span>
              <span class="sn-list-name">{{ sn.sn }}</span>
              <span class="sn-list-config">{{ sn.config }}</span>
              <span class="sn-list-progress">{{ progressPct(sn) }}%</span>
              <span class="sn-list-cp">
                {{ (sn.current_cp_idx ?? -1) + 1 }}/{{ sn.total_cps }}
              </span>
            </div>
            <div v-show="wcfgExpanded[sn.sn + '_' + sn.config]" class="sn-list-body">
              <SnLifecycle
                :cpList="sn.cpList"
                :checkItems="wcfgData.check_items"
                :checkItemFilter="checkItemFilter"
                :compact="true"
                :lazyLoadChecks="(cpIdx) => store.fetchSnCheckDetails(sn.sn, wcfgData.wf_num, sn.config, cpIdx)"
              />
            </div>
          </div>
          <div v-if="!wcfgData.sns.length" class="empty-result">{{ t('common.noData') }}</div>
        </div>
      </template>
    </div>

    <!-- Multi-SN -->
    <div v-if="activeMode === 'multi'" class="mode-content">
      <div class="card multisn-input">
        <div class="multisn-tags">
          <span v-for="(s, i) in multiTags" :key="s + '_' + i" class="multisn-tag">
            {{ s }}
            <button class="tag-remove" @click="removeMultiTag(i)" aria-label="remove">×</button>
          </span>
          <input
            v-model="multiInput"
            class="multisn-input-field"
            :placeholder="multiTags.length ? '' : t('queryCenter.multiSnPlaceholder')"
            @keydown.enter.prevent="addMultiTag"
            @keydown="onMultiKeydown"
          />
        </div>
        <button
          class="search-btn"
          :disabled="!multiTags.length || loading"
          @click="doMultiSearch"
        >{{ loading ? t('common.loading') : t('actions.search') }}</button>
        <ErrorState v-if="multiError" :message="multiError" @retry="doMultiSearch" />
      </div>

      <LoadingState v-if="loading && !multiGroups.length" />

      <template v-if="multiGroups.length">
        <div v-for="g in multiGroups" :key="g.wf_num" class="card multisn-group">
          <div class="lifecycle-card-header">
            <span class="wf-pill">WF{{ g.wf_num }}</span>
            <span class="wf-test-name">{{ wfDisplayName(g.wf_num) }}</span>
            <span class="sn-list-config">({{ g.sns.length }} SNs)</span>
          </div>

          <div class="lifecycle-scroll">
            <table class="multisn-table">
              <thead>
                <tr>
                  <th class="multisn-sn-th">SN</th>
                  <th class="multisn-cfg-th">Config</th>
                  <th
                    v-for="col in g.cpColumns"
                    :key="col.cp_idx"
                    class="cp-th clickable"
                    :class="{ expanded: multiExpandedCp[g.wf_num] === col.cp_idx }"
                    :colspan="multiExpandedCp[g.wf_num] === col.cp_idx ? Math.max(1, g.check_items.length) : 1"
                    @click="toggleMultiCp(g, col.cp_idx)"
                  >
                    <div class="cp-name">{{ col.cp_name }}</div>
                  </th>
                </tr>
                <tr v-if="multiExpandedCp[g.wf_num] !== undefined && !checkItemFilter">
                  <th class="multisn-sn-th"></th>
                  <th class="multisn-cfg-th"></th>
                  <template v-for="col in g.cpColumns" :key="'sub-' + col.cp_idx">
                    <template v-if="multiExpandedCp[g.wf_num] === col.cp_idx">
                      <th
                        v-for="ci in g.check_items"
                        :key="col.cp_idx + '-' + ci"
                        class="ci-th"
                      >{{ ci }}</th>
                    </template>
                    <th v-else class="cp-th-placeholder"></th>
                  </template>
                </tr>
              </thead>
              <tbody>
                <tr v-for="sn in g.sns" :key="sn.sn + '_' + sn.config" class="multisn-row">
                  <td class="multisn-sn-cell" @click="openSingle(sn.sn)">{{ sn.sn }}</td>
                  <td class="multisn-cfg-cell">{{ sn.config }}</td>
                  <template v-for="col in g.cpColumns" :key="sn.sn + '_' + col.cp_idx">
                    <!-- Check-item filtered -->
                    <td
                      v-if="checkItemFilter"
                      class="cp-cell"
                      :class="multiFilteredCellClass(sn, col.cp_idx)"
                    >{{ multiFilteredCellText(sn, col.cp_idx) }}</td>

                    <!-- Expanded (no filter) -->
                    <template v-else-if="multiExpandedCp[g.wf_num] === col.cp_idx">
                      <td
                        v-for="ci in g.check_items"
                        :key="sn.sn + '_' + col.cp_idx + '_' + ci"
                        class="ci-cell"
                        :class="multiCiCellClass(g, sn, col.cp_idx, ci)"
                      >{{ multiCiCellText(g, sn, col.cp_idx, ci) }}</td>
                    </template>

                    <!-- Collapsed -->
                    <td
                      v-else
                      class="cp-cell"
                      :class="multiCpCellClass(sn, col.cp_idx)"
                    >
                      <span v-if="getCp(sn, col.cp_idx)">{{ getCp(sn, col.cp_idx).pass_count }}/{{ getCp(sn, col.cp_idx).total_check_items }}</span>
                      <span v-else>/</span>
                    </td>
                  </template>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
      <div v-if="!multiGroups.length && !loading && multiTags.length" class="empty-result">{{ t('common.noData') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'
import { groupMultiSnByWf } from '@/composables/useLifecycle'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import SnLifecycle from '@/components/SnLifecycle.vue'

const store = useAppStore()
const route = useRoute()
const { t } = useI18n()

const modes = [
  { key: 'single', i18n: 'queryCenter.singleSn' },
  { key: 'wcfg', i18n: 'queryCenter.wfCfg' },
  { key: 'multi', i18n: 'queryCenter.multiSn' },
]
const activeMode = ref('single')

const loading = computed(() => store.loading)

const checkItemFilter = ref(null)
const availableCheckItems = ref([])

watch(activeMode, () => { checkItemFilter.value = null; availableCheckItems.value = [] })

// -- Single SN / mark mode --
const singleQuery = ref('')
const singleSuggestions = ref([])
const singleError = ref('')
const singleResult = ref([])
const resolvedSn = ref('')
const singleMark = ref('')
let singleDebounce = null

const singleHasFailures = computed(() =>
  singleResult.value.some(g => g.cpList.some(cp => cp.status === 'fail' || cp.failure_type))
)
const singleFailCount = computed(() => {
  let n = 0
  for (const g of singleResult.value)
    for (const cp of g.cpList)
      if (cp.status === 'fail' || cp.failure_type) n++
  return n
})

function isMarkLike(s) { return /^ER\d/i.test(String(s).trim()) }

function onSingleInput() {
  clearTimeout(singleDebounce)
  const q = singleQuery.value.trim()
  if (q.length < 2) { singleSuggestions.value = []; return }
  singleDebounce = setTimeout(async () => {
    try { singleSuggestions.value = await store.searchSn(q) }
    catch { singleSuggestions.value = [] }
  }, 300)
}

function selectSuggestion(s) {
  singleQuery.value = s.sn
  singleSuggestions.value = []
  doSingleSearch()
}

async function doSingleSearch() {
  const q = singleQuery.value.trim()
  if (!q) return
  singleError.value = ''
  singleSuggestions.value = []

  let targetSn = q
  let targetMark = ''
  if (isMarkLike(q)) {
    const sn = await store.resolveMark(q)
    if (!sn) {
      singleError.value = t('queryCenter.markNotFound')
      singleResult.value = []
      availableCheckItems.value = []
      return
    }
    targetSn = sn
    targetMark = q
  }

  try {
    const normalized = await store.fetchSnTimeline(targetSn)
    resolvedSn.value = targetSn
    singleMark.value = targetMark
    singleResult.value = normalized[0]?.wfs || []
    const ciSet = new Set()
    for (const g of singleResult.value) for (const n of g.checkItems) ciSet.add(n)
    availableCheckItems.value = [...ciSet]
  } catch (e) {
    singleError.value = e.message || t('common.error')
    singleResult.value = []
    availableCheckItems.value = []
  }
}

function wfDisplayName(wf) { return store.wfNames[wf] || '' }

// -- WF & Config mode --
const wcfgSelectedWf = ref('')
const wcfgSelectedConfig = ref('')
const wcfgError = ref('')
const wcfgData = ref(null)
const wcfgExpanded = ref({})

const wfOptions = computed(() => store.queryWfList?.wfs || [])
const configOptions = computed(() => store.queryWfList?.configs || [])

function onWfChange() {
  wcfgSelectedConfig.value = ''
  wcfgData.value = null
}

async function doWfCfgSearch() {
  if (!wcfgSelectedWf.value) return
  wcfgError.value = ''
  try {
    const data = await store.fetchQueryByWf(wcfgSelectedWf.value, wcfgSelectedConfig.value || '')
    wcfgData.value = data
    availableCheckItems.value = data.check_items || []
    wcfgExpanded.value = {}
    ;(data.sns || []).slice(0, 3).forEach(s => {
      wcfgExpanded.value[s.sn + '_' + s.config] = true
    })
  } catch (e) {
    wcfgError.value = e.message || t('common.error')
    wcfgData.value = null
  }
}

function toggleWcfgSn(key) { wcfgExpanded.value[key] = !wcfgExpanded.value[key] }

function progressPct(sn) {
  if (!sn.total_cps) return 0
  return (((sn.current_cp_idx ?? -1) + 1) / sn.total_cps * 100).toFixed(1)
}

// -- Multi-SN mode --
const multiTags = ref([])
const multiInput = ref('')
const multiError = ref('')
const multiNormalized = ref([])
const multiGroups = computed(() => groupMultiSnByWf(multiNormalized.value))
const multiExpandedCp = ref({})
const multiCheckCache = ref({})

function onMultiKeydown(e) {
  if (e.key === ',' || e.key === '，') { e.preventDefault(); addMultiTag() }
  else if (e.key === 'Backspace' && !multiInput.value && multiTags.value.length) {
    multiTags.value.pop()
  }
}

function addMultiTag() {
  const tokens = multiInput.value.trim().split(/[\s,，]+/).filter(Boolean)
  for (const tok of tokens) {
    if (!multiTags.value.includes(tok)) multiTags.value.push(tok)
  }
  multiInput.value = ''
}

function removeMultiTag(i) { multiTags.value.splice(i, 1) }

async function doMultiSearch() {
  if (!multiTags.value.length) return
  if (multiTags.value.length > 50) {
    multiError.value = t('queryCenter.tooManySns')
    return
  }
  multiError.value = ''
  multiExpandedCp.value = {}
  multiCheckCache.value = {}

  const resolved = []
  for (const tok of multiTags.value) {
    if (isMarkLike(tok)) {
      const sn = await store.resolveMark(tok)
      if (sn) resolved.push(sn)
    } else {
      resolved.push(tok)
    }
  }
  if (!resolved.length) {
    multiError.value = t('queryCenter.noResolved')
    multiNormalized.value = []
    availableCheckItems.value = []
    return
  }

  try {
    const normalized = await store.fetchSnTimeline(resolved)
    multiNormalized.value = normalized
    const ciSet = new Set()
    for (const sn of normalized) for (const wf of sn.wfs) for (const ci of wf.checkItems) ciSet.add(ci)
    availableCheckItems.value = [...ciSet]
  } catch (e) {
    multiError.value = e.message || t('common.error')
    multiNormalized.value = []
    availableCheckItems.value = []
  }
}

function getCp(sn, cpIdx) { return sn.cpByIdx[cpIdx] }

function multiCpCellClass(sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp || !cp.has_data) return 'cell-skip'
  if (cp.status === 'fail' || cp.failure_type === 'spec') return 'cell-fail'
  if (cp.failure_type === 'strife') return 'cell-strife'
  return 'cell-pass'
}

function multiFilteredCellClass(sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp || !cp.has_data) return 'cell-skip'
  const name = checkItemFilter.value
  const items = Array.isArray(cp.checkItems) ? cp.checkItems : []
  const ci = items.find(i => i.name === name)
  if (!ci) return 'cell-skip'
  if (ci.status === 'pass') return 'cell-pass'
  if (ci.status === 'fail' || ci.failure_type === 'spec') return 'cell-fail'
  if (ci.failure_type === 'strife') return 'cell-strife'
  return 'cell-skip'
}

function multiFilteredCellText(sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (!cp || !cp.has_data) return '/'
  const name = checkItemFilter.value
  const items = Array.isArray(cp.checkItems) ? cp.checkItems : []
  const ci = items.find(i => i.name === name)
  if (!ci) return '—'
  if (ci.status === 'pass') return '✓'
  if (ci.status === 'fail' || ci.failure_type) return '✗'
  return '—'
}

async function toggleMultiCp(group, cpIdx) {
  if (multiExpandedCp.value[group.wf_num] === cpIdx) {
    delete multiExpandedCp.value[group.wf_num]
    return
  }
  multiExpandedCp.value[group.wf_num] = cpIdx

  const toFetch = []
  for (const sn of group.sns) {
    const cp = getCp(sn, cpIdx)
    if (!cp) continue
    if (Array.isArray(cp.checkItems)) continue
    const key = `${group.wf_num}_${sn.config}_${sn.sn}_${cpIdx}`
    if (multiCheckCache.value[key]) continue
    toFetch.push({ sn, key })
  }

  await Promise.all(toFetch.map(async ({ sn, key }) => {
    try {
      const res = await store.fetchSnCheckDetails(sn.sn, group.wf_num, sn.config, cpIdx)
      multiCheckCache.value[key] = (res?.check_items || []).map(i => ({
        name: i.check_item || i.name,
        status: i.status,
        failure_type: i.failure_type || null,
      }))
    } catch {
      multiCheckCache.value[key] = []
    }
  }))
}

function resolveCheckItems(group, sn, cpIdx) {
  const cp = getCp(sn, cpIdx)
  if (cp && Array.isArray(cp.checkItems)) return cp.checkItems
  const key = `${group.wf_num}_${sn.config}_${sn.sn}_${cpIdx}`
  return multiCheckCache.value[key] || []
}

function multiCiCellClass(group, sn, cpIdx, ciName) {
  const items = resolveCheckItems(group, sn, cpIdx)
  const ci = items.find(i => i.name === ciName)
  if (!ci) return 'ci-skip'
  if (ci.status === 'pass') return 'ci-pass'
  if (ci.status === 'fail' || ci.failure_type === 'spec') return 'ci-fail'
  if (ci.failure_type === 'strife') return 'ci-strife'
  return 'ci-skip'
}

function multiCiCellText(group, sn, cpIdx, ciName) {
  const items = resolveCheckItems(group, sn, cpIdx)
  const ci = items.find(i => i.name === ciName)
  if (!ci) return '—'
  if (ci.status === 'pass') return '✓'
  if (ci.status === 'fail' || ci.failure_type) return '✗'
  return '—'
}

function openSingle(sn) {
  singleQuery.value = sn
  activeMode.value = 'single'
  doSingleSearch()
}

// -- Init --
onMounted(async () => {
  await store.fetchWfList().catch(() => { /* non-fatal */ })
  const q = route.query.q
  if (q) { singleQuery.value = String(q); doSingleSearch() }
})
</script>

<style scoped>
.page-container { max-width: 1440px; margin: 0 auto; padding: 24px 32px 40px; }
.page-title {
  font-family: var(--font-display);
  font-size: 22px; font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 24px;
}

.mode-tabs {
  display: flex; gap: 4px; margin-bottom: 20px;
  border-bottom: 2px solid var(--border-light);
}
.mode-tab {
  padding: 10px 20px;
  font-size: 14px; font-weight: 500;
  color: var(--text-muted);
  background: none; border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: color var(--duration-fast), border-color var(--duration-fast);
}
.mode-tab:hover { color: var(--text-primary); }
.mode-tab.active { color: var(--accent-steel); border-bottom-color: var(--accent-steel); }

.filter-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.filter-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.filter-select {
  padding: 6px 10px; font-size: 13px;
  border: 1px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg-input); color: var(--text-primary);
}

.search-card, .wcfg-filters, .multisn-input { padding: 20px 24px; margin-bottom: 16px; }
.search-row { display: flex; gap: 12px; }
.search-input {
  flex: 1; padding: 10px 14px;
  font-family: 'Source Code Pro', monospace; font-size: 15px;
  border: 1px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg-input); color: var(--text-primary); outline: none;
}
.search-input:focus { border-color: var(--border-focus); }
.search-btn {
  padding: 10px 24px; font-size: 14px; font-weight: 500;
  color: #fff; background: var(--accent-steel);
  border: none; border-radius: var(--radius-md);
  cursor: pointer; white-space: nowrap;
}
.search-btn:hover:not(:disabled) { opacity: 0.9; }
.search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.suggestions { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 4px 0; }
.suggestion-chip {
  display: inline-flex; gap: 6px;
  padding: 4px 12px;
  font-family: var(--font-mono); font-size: 12px;
  background: var(--bg-tag);
  border: 1px solid var(--border-light); border-radius: var(--radius-full);
  color: var(--text-secondary); cursor: pointer;
}
.suggestion-chip:hover { background: var(--accent-steel); color: #fff; border-color: var(--accent-steel); }
.chip-sn { font-weight: 600; }
.chip-mark { opacity: 0.75; font-size: 11px; }

.sn-header {
  padding: 14px 20px; margin-bottom: 12px;
  background: var(--bg-card); border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  display: flex; align-items: center; gap: 16px;
}
.sn-header.has-failures { border-left: 4px solid var(--color-danger); }
.sn-title { font-family: var(--font-mono); font-size: 18px; font-weight: 700; color: var(--text-primary); }
.sn-mark {
  padding: 2px 10px; border-radius: var(--radius-sm);
  background: var(--bg-tag); color: var(--text-secondary);
  font-family: var(--font-mono); font-size: 12px;
}
.fail-warning {
  padding: 2px 10px;
  background: var(--color-danger-bg); color: var(--color-danger);
  font-size: 12px; font-weight: 600;
  border-radius: var(--radius-sm);
}

.lifecycle-card { margin-bottom: 12px; overflow: hidden; }
.lifecycle-card-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px;
  background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light);
}
.wf-pill {
  padding: 2px 8px;
  background: var(--text-primary); color: var(--bg-card);
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  border-radius: var(--radius-sm);
}
.wf-config { font-family: var(--font-mono); font-size: 12px; color: var(--text-primary); }
.wf-test-name { font-size: 12px; color: var(--text-muted); }

/* WF&Cfg summary */
.wcfg-summary { padding: 14px 20px; margin-bottom: 16px; }
.summary-grid { display: flex; gap: 24px; }
.summary-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.sum-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; }
.sum-val {
  font-size: 18px; font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.sum-val.pass   { color: var(--color-pass); }
.sum-val.fail   { color: var(--color-danger); }
.sum-val.strife { color: var(--color-warning); }

.sn-list { display: flex; flex-direction: column; gap: 6px; }
.sn-list-item { overflow: hidden; }
.sn-list-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; cursor: pointer; user-select: none;
}
.sn-list-header:hover { background: var(--bg-row-hover); }
.chevron {
  font-size: 10px; color: var(--text-muted);
  transition: transform var(--duration-fast); flex-shrink: 0;
}
.chevron.open { transform: rotate(90deg); }
.sn-list-name { font-family: var(--font-mono); font-size: 13px; font-weight: 600; color: var(--text-primary); flex: 1; }
.sn-list-config { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); }
.sn-list-progress { font-size: 12px; font-weight: 600; color: var(--text-primary); min-width: 40px; text-align: right; }
.sn-list-cp { font-size: 11px; color: var(--text-muted); min-width: 60px; text-align: right; }
.sn-list-body { border-top: 1px solid var(--border-light); padding: 8px; }

/* Multi-SN */
.multisn-input { display: flex; gap: 10px; align-items: flex-start; }
.multisn-tags {
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  flex: 1; padding: 4px;
  border: 1px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg-input); min-height: 38px;
}
.multisn-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px;
  background: var(--accent-steel); color: #fff;
  font-family: var(--font-mono); font-size: 12px;
  border-radius: var(--radius-sm);
}
.tag-remove {
  background: none; border: none; color: #fff; cursor: pointer;
  font-size: 14px; padding: 0 2px; line-height: 1; opacity: 0.7;
}
.tag-remove:hover { opacity: 1; }
.multisn-input-field {
  border: none; outline: none; background: transparent;
  color: var(--text-primary);
  font-family: var(--font-mono); font-size: 14px;
  min-width: 120px; flex: 1; padding: 4px;
}

.multisn-group { margin-bottom: 16px; overflow: hidden; }
.multisn-table { border-collapse: separate; border-spacing: 0; font-size: 12px; min-width: 100%; }
.multisn-sn-th, .multisn-cfg-th {
  min-width: 120px; padding: 6px 10px; text-align: left;
  background: var(--bg-row-stripe); border: 1px solid var(--border-light);
  font-weight: 600; color: var(--text-primary);
  position: sticky; left: 0; z-index: 1;
}
.multisn-cfg-th { min-width: 70px; left: 120px; }
.multisn-sn-cell {
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  color: var(--accent-steel); cursor: pointer;
  padding: 6px 10px;
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  position: sticky; left: 0; z-index: 1;
}
.multisn-cfg-cell {
  font-family: var(--font-mono); font-size: 11px;
  color: var(--text-muted);
  padding: 6px 10px;
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  position: sticky; left: 120px; z-index: 1;
}
.multisn-sn-cell:hover { text-decoration: underline; }
.multisn-row:hover td { background: var(--bg-row-hover); }

/* Reuse SnLifecycle tokens */
.cp-th { min-width: 72px; padding: 6px 8px; text-align: center;
  background: var(--bg-row-stripe); border: 1px solid var(--border-light);
  cursor: default; user-select: none; vertical-align: top; }
.cp-th.clickable { cursor: pointer; }
.cp-th.clickable:hover { background: var(--bg-row-hover); }
.cp-th.expanded { background: var(--bg-card); border-bottom: 2px solid var(--accent-steel); }
.cp-name { font-weight: 600; color: var(--text-primary); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ci-th { padding: 4px 6px; text-align: center; font-size: 11px; font-weight: 500;
  color: var(--text-secondary); background: var(--bg-card);
  border: 1px solid var(--border-light); min-width: 48px; }
.cp-th-placeholder { border: 1px solid var(--border-light); background: var(--bg-row-stripe); }

.cp-cell { padding: 4px 8px; text-align: center; border: 1px solid var(--border-light); font-variant-numeric: tabular-nums; }
.cell-pass   { background: var(--color-pass-bg);    color: var(--color-pass); }
.cell-fail   { background: var(--color-danger-bg);  color: var(--color-danger); }
.cell-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.cell-skip   { background: var(--bg-muted);         color: var(--text-muted); }

.ci-cell { padding: 4px 6px; text-align: center; border: 1px solid var(--border-light); font-size: 13px; font-weight: 600; min-width: 48px; }
.ci-pass   { background: var(--color-pass-bg);    color: var(--color-pass); }
.ci-fail   { background: var(--color-danger-bg);  color: var(--color-danger); }
.ci-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.ci-skip   { background: var(--bg-muted);         color: var(--text-muted); }

.empty-result { padding: 40px 20px; text-align: center; color: var(--text-muted); font-size: 14px; }
</style>
