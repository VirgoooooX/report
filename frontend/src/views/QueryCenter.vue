<template>
  <div class="page-container">
    <div class="mode-row">
      <div class="mode-tabs" role="tablist">
        <button v-for="m in modes" :key="m.key" class="mode-tab" :class="{ active: activeMode === m.key }" role="tab" :aria-selected="activeMode === m.key" @click="switchMode(m.key)">{{ t(m.i18n) }}</button>
      </div>
      <button class="export-btn top-export" :disabled="!canExport" @click="doExport">↓ {{ t('queryCenter.exportCsv') }}</button>
    </div>

    <!-- ═══════════ SN/Mark Lookup ═══════════ -->
    <div v-if="activeMode === 'lookup'" class="mode-content">
      <div class="card search-card">
        <div class="search-bar">
          <div class="bar-filter-item bar-filter-grow">
            <label>SN / Mark</label>
            <div class="tag-input-box" @click="focusTagInput">
              <span v-for="(tag, i) in lookupTags" :key="tag + '_' + i" class="input-tag"><span class="tag-label">{{ tag }}</span><button class="tag-remove" @click.stop="removeTag(i)" aria-label="remove">×</button></span>
              <input ref="tagInputRef" v-model="lookupInput" type="text" class="tag-input-field" :placeholder="lookupTags.length ? '' : t('queryCenter.snOrMarkPlaceholder')" @input="onLookupInput" @keydown="onLookupKeydown" @paste="onPaste" @blur="flushInput" />
            </div>
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.checkItem') }}</label>
            <select v-model="checkItemFilter" class="filter-select inline-filter" :disabled="!availableCheckItems.length">
              <option :value="null">{{ t('queryCenter.allCpLevel') }}</option>
              <option v-for="ci in availableCheckItems" :key="ci" :value="ci">{{ ci }}</option>
            </select>
          </div>
          <div class="bar-actions">
            <button class="search-btn" :disabled="loading || (!lookupTags.length && !lookupInput.trim())" @click="submitLookup">{{ loading ? t('common.loading') : t('actions.search') }}</button>
            <button v-if="lookupTags.length || lookupResults.length" class="clear-btn" @click="clearLookup" :title="t('queryCenter.clear')">✕</button>
          </div>
        </div>
        <div v-if="lookupSuggestions.length" class="suggestions">
          <span v-for="s in lookupSuggestions" :key="s.sn + '|' + s.unit_num" class="suggestion-chip" @click="selectSuggestion(s)"><span class="chip-sn">{{ s.sn }}</span><span v-if="s.unit_num" class="chip-mark">{{ s.unit_num }}</span></span>
        </div>
        <ErrorState v-if="lookupError" :message="lookupError" @retry="submitLookup" />
      </div>

      <LoadingState v-if="loading && !lookupResults.length" />
      <template v-if="lookupResults.length">
        <div class="result-info"><span class="multi-summary-count">{{ lookupResults.length }} {{ t('queryCenter.snsMatched') }}</span></div>
        <CompareView :groups="lookupGroups" :checkItemFilter="checkItemFilter" :wfNames="store.wfNames" @open-sn="goToSingleSn" @request-ci="handleRequestCi" />
      </template>
    </div>

    <!-- ═══════════ WF & Config ═══════════ -->
    <div v-if="activeMode === 'wcfg'" class="mode-content">
      <div class="card search-card">
        <div class="search-bar">
          <div class="bar-filter-item bar-filter-grow">
            <label>{{ t('queryCenter.wf') }}</label>
            <MultiSelect v-model="wcfgWfSelection" :options="wfDisplayOptions" :placeholder="t('queryCenter.selectWf')" />
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.config') }}</label>
            <MultiSelect v-model="wcfgConfigSelection" :options="configOptions" :placeholder="t('queryCenter.allConfigs')" />
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.checkItem') }}</label>
            <select v-model="checkItemFilter" class="filter-select inline-filter" :disabled="!availableCheckItems.length"><option :value="null">{{ t('queryCenter.allCpLevel') }}</option><option v-for="ci in availableCheckItems" :key="ci" :value="ci">{{ ci }}</option></select>
          </div>
          <div class="bar-actions">
            <button class="search-btn" :disabled="!wcfgWfSelection.length || loading" @click="doWfCfgSearch">{{ loading ? t('common.loading') : t('actions.search') }}</button>
            <button v-if="wcfgData" class="clear-btn" @click="clearWcfg" :title="t('queryCenter.clear')">✕</button>
          </div>
        </div>
        <ErrorState v-if="wcfgError" :message="wcfgError" @retry="doWfCfgSearch" />
      </div>
      <LoadingState v-if="loading && !wcfgData" />
      <template v-if="wcfgData">
        <div class="wcfg-summary-card">
          <div class="summary-header"><div class="summary-title"><span class="wf-pill-lg">WF{{ wcfgData.wf_num }}</span><span class="summary-wfname">{{ wcfgData.wf_name || '' }}</span><span v-if="wcfgData.config_filter && wcfgData.config_filter !== 'All'" class="summary-cfg">{{ wcfgData.config_filter }}</span></div><div class="summary-total"><span class="total-num">{{ wcfgData.summary.total_sns || 0 }}</span><span class="total-label">{{ t('queryCenter.totalSn') }}</span></div></div>
          <div class="summary-progress"><div v-for="seg in summarySegments" :key="seg.kind" class="progress-seg" :class="`seg-${seg.kind}`" :style="{ flex: seg.value }" :title="`${seg.label}: ${seg.value}`" /></div>
          <div class="summary-chips"><div class="chip-stat chip-pass" :class="{ empty: !wcfgData.summary.completed }"><span class="chip-dot" /><span class="chip-num">{{ wcfgData.summary.completed || 0 }}</span><span class="chip-label">{{ t('common.completed') }}</span></div><div class="chip-stat chip-fail" :class="{ empty: !wcfgData.summary.spec_fails }"><span class="chip-dot" /><span class="chip-num">{{ wcfgData.summary.spec_fails || 0 }}</span><span class="chip-label">Spec</span></div><div class="chip-stat chip-strife" :class="{ empty: !wcfgData.summary.strife_fails }"><span class="chip-dot" /><span class="chip-num">{{ wcfgData.summary.strife_fails || 0 }}</span><span class="chip-label">Strife</span></div><div class="chip-stat chip-progress"><span class="chip-dot" /><span class="chip-num">{{ inProgressCount }}</span><span class="chip-label">{{ t('common.inProgress') }}</span></div></div>
        </div>
        <CompareView v-if="wcfgGroups.length" :groups="wcfgGroups" :checkItemFilter="checkItemFilter" :wfNames="store.wfNames" :sortByMark="true" @open-sn="goToSingleSn" @request-ci="handleRequestCi" />
        <div v-else class="empty-result">{{ t('common.noData') }}</div>
      </template>
    </div>

    <!-- ═══════════ Failure 查询 (FA Tracker) ═══════════ -->
    <div v-if="activeMode === 'failure'" class="mode-content">
      <div class="card search-card">
        <div class="search-bar">
          <div class="bar-filter-item bar-filter-grow">
            <label>SN / Mark</label>
            <div class="tag-input-box" @click="focusFaInput">
              <span v-for="(tag, i) in faTags" :key="tag + '_' + i" class="input-tag"><span class="tag-label">{{ tag }}</span><button class="tag-remove" @click.stop="removeFaTag(i)" aria-label="remove">×</button></span>
              <input ref="faInputRef" v-model="faInput" type="text" class="tag-input-field" :placeholder="faTags.length ? '' : t('queryCenter.faPlaceholder')" @keydown="onFaKeydown" @paste="onFaPaste" @blur="flushFaInput" />
            </div>
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.wf') }}</label>
            <MultiSelect v-model="faFilterWf" :options="cascadedOptions.wfs" :placeholder="t('common.all')" />
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.config') }}</label>
            <MultiSelect v-model="faFilterConfig" :options="cascadedOptions.configs" :placeholder="t('common.all')" />
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.failedTest') }}</label>
            <MultiSelect v-model="faFilterTest" :options="cascadedOptions.failed_tests" :placeholder="t('common.all')" />
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.symptom') }}</label>
            <MultiSelect v-model="faFilterSymptom" :options="cascadedOptions.symptoms" :placeholder="t('common.all')" />
          </div>
          <div class="bar-filter-item">
            <label>{{ t('queryCenter.location') }}</label>
            <MultiSelect v-model="faFilterLocation" :options="cascadedOptions.locations" :placeholder="t('common.all')" />
          </div>
          <div class="bar-actions">
            <button class="search-btn" :disabled="faLoading || (!faTags.length && !faInput.trim() && !hasAnyFaFilter)" @click="submitFaSearch">{{ faLoading ? t('common.loading') : t('actions.search') }}</button>
            <button v-if="faTags.length || faResults.length || hasAnyFaFilter" class="clear-btn" @click="clearFa" :title="t('queryCenter.clear')">✕</button>
          </div>
        </div>
        <ErrorState v-if="faError" :message="faError" @retry="submitFaSearch" />
      </div>
      <LoadingState v-if="faLoading && !faResults.length" />
      <div v-if="faFlatEntries.length" class="fa-results">
        <table class="fa-table">
          <thead>
            <tr>
              <th>SN</th>
              <th>Mark</th>
              <th>WF</th>
              <th>Config</th>
              <th>Failed Test</th>
              <th>Symptom</th>
              <th>Location</th>
              <th>Cycle</th>
              <th>Type</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(row, ri) in faFlatEntries" :key="ri">
              <tr class="fa-row" :class="{ expanded: faExpanded[ri] }" @click="toggleFaEntry(ri)">
                <td class="fa-td-sn">{{ row.sn }}</td>
                <td class="fa-td-mark">{{ row.unit_num }}</td>
                <td>{{ row.fa.WF || '' }}</td>
                <td>{{ row.fa.Config || '' }}</td>
                <td>{{ row.fa['Failed Test'] || '' }}</td>
                <td class="fa-td-symptom">{{ row.fa['Failure Symptom / Failure Message'] || '' }}</td>
                <td>{{ row.fa['Failed Location'] || '' }}</td>
                <td>{{ row.fa['Failed Cycle Count'] || '' }}</td>
                <td><span class="fa-type-badge" :class="faTypeBadgeClass(row.fa)">{{ faTypeLabel(row.fa) }}</span></td>
                <td>{{ row.fa['FA Status'] || '' }}</td>
              </tr>
              <tr v-if="faExpanded[ri]" class="fa-detail-row">
                <td colspan="10">
                  <div class="fa-detail-panel">
                    <div class="fa-detail-section fa-action-section">
                      <div class="fa-detail-section-title">Actions & Root Cause</div>
                      <div class="fa-action-grid">
                        <div class="fa-action-item">
                          <span class="fa-action-label">Follow Up Actions</span>
                          <span class="fa-action-val" :class="{ empty: !hasVal(row.fa, 'Follow Up Actions') }">{{ getVal(row.fa, 'Follow Up Actions') }}</span>
                        </div>
                        <div class="fa-action-item">
                          <span class="fa-action-label">Root Cause</span>
                          <span class="fa-action-val" :class="{ empty: !hasVal(row.fa, 'Root Cause') }">{{ getVal(row.fa, 'Root Cause') }}</span>
                        </div>
                        <div class="fa-action-item">
                          <span class="fa-action-label">CA</span>
                          <span class="fa-action-val" :class="{ empty: !hasVal(row.fa, 'CA') }">{{ getVal(row.fa, 'CA') }}</span>
                        </div>
                        <div class="fa-action-item">
                          <span class="fa-action-label">Category I</span>
                          <span class="fa-action-val" :class="{ empty: !hasVal(row.fa, 'Root Cause Category I') }">{{ getVal(row.fa, 'Root Cause Category I') }}</span>
                        </div>
                        <div class="fa-action-item">
                          <span class="fa-action-label">Category II</span>
                          <span class="fa-action-val" :class="{ empty: !hasVal(row.fa, 'Root Cause Category II') }">{{ getVal(row.fa, 'Root Cause Category II') }}</span>
                        </div>
                      </div>
                    </div>
                    <div v-if="Object.keys(otherFaFields(row.fa)).length" class="fa-detail-section fa-other-section">
                      <div class="fa-detail-section-title">Other Info</div>
                      <div class="fa-other-grid">
                        <div v-for="(val, key) in otherFaFields(row.fa)" :key="key" class="fa-other-item">
                          <span class="fa-other-label">{{ key }}</span>
                          <span class="fa-other-val">{{ val }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div v-else-if="!faLoading && faResults.length && !faFlatEntries.length" class="empty-result">{{ t('queryCenter.noFaRecords') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'
import { groupMultiSnByWf } from '@/composables/useLifecycle'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import CompareView from '@/components/QueryCompareView.vue'
import MultiSelect from '@/components/MultiSelect.vue'

const store = useAppStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const modes = [
  { key: 'lookup', i18n: 'queryCenter.lookupMode' },
  { key: 'wcfg', i18n: 'queryCenter.wfCfg' },
  { key: 'failure', i18n: 'queryCenter.failureMode' },
]
const activeMode = ref('lookup')
const loading = computed(() => store.loading)
const checkItemFilter = ref(null)
const availableCheckItems = ref([])

// ── Lookup mode ─────────────────────────────────────────────────────
const lookupTags = ref([])
const lookupInput = ref('')
const lookupSuggestions = ref([])
const lookupError = ref('')
const lookupResults = ref([])
const tagInputRef = ref(null)
let suggestDebounce = null
const lookupGroups = computed(() => groupMultiSnByWf(lookupResults.value))

function isMarkLike(s) { return /^ER\d/i.test(String(s).trim()) }
function focusTagInput() { tagInputRef.value?.focus() }
function onLookupInput() {
  clearTimeout(suggestDebounce)
  const q = lookupInput.value.trim()
  if (q.length < 2) { lookupSuggestions.value = []; return }
  suggestDebounce = setTimeout(async () => { try { lookupSuggestions.value = (await store.searchSn(q)).slice(0, 10) } catch { lookupSuggestions.value = [] } }, 300)
}
function onLookupKeydown(e) {
  if (e.key === 'Enter') { if (lookupInput.value.trim()) flushInput(); else submitLookup(); e.preventDefault() }
  else if (e.key === ',' || e.key === '，') { if (lookupInput.value.trim()) { flushInput(); e.preventDefault() } }
  else if (e.key === 'Backspace' && !lookupInput.value && lookupTags.value.length) { lookupTags.value.pop() }
}
function onPaste(e) { e.preventDefault(); const text = (e.clipboardData || window.clipboardData).getData('text') || ''; const tokens = text.split(/[\s,，\n\r\t]+/).filter(Boolean); for (const tok of tokens) { if (!lookupTags.value.includes(tok)) lookupTags.value.push(tok) }; lookupInput.value = ''; lookupSuggestions.value = [] }
function flushInput() { const tokens = lookupInput.value.trim().split(/[\s,，]+/).filter(Boolean); for (const tok of tokens) { if (!lookupTags.value.includes(tok)) lookupTags.value.push(tok) }; lookupInput.value = ''; lookupSuggestions.value = [] }
function removeTag(i) { lookupTags.value.splice(i, 1) }
function clearLookup() { lookupTags.value = []; lookupInput.value = ''; lookupResults.value = []; lookupError.value = ''; availableCheckItems.value = []; checkItemFilter.value = null; store.clearQueryCache('lookup'); router.replace({ name: 'sn', query: { mode: 'lookup' } }) }
function selectSuggestion(s) { if (!lookupTags.value.includes(s.sn)) lookupTags.value.push(s.sn); lookupInput.value = ''; lookupSuggestions.value = []; nextTick(() => focusTagInput()) }
function submitLookup() { flushInput(); if (!lookupTags.value.length) return; pushState({ mode: 'lookup', tags: lookupTags.value.join(',') }) }

async function doLookup() {
  if (!lookupTags.value.length) { lookupResults.value = []; availableCheckItems.value = []; return }
  if (lookupTags.value.length > 50) { lookupError.value = t('queryCenter.tooManySns'); return }
  lookupError.value = ''; lookupSuggestions.value = []
  const resolvedSns = []; const markMap = {}
  for (const tok of lookupTags.value) { if (isMarkLike(tok)) { const sn = await store.resolveMark(tok); if (sn) { resolvedSns.push(sn); markMap[sn] = tok } } else { resolvedSns.push(tok) } }
  if (!resolvedSns.length) { lookupError.value = t('queryCenter.noResolved'); lookupResults.value = []; availableCheckItems.value = []; return }
  try {
    const normalized = await store.fetchSnTimeline(resolvedSns)
    for (const r of normalized) { if (!r.unit_num && markMap[r.sn]) r.unit_num = markMap[r.sn] }
    lookupResults.value = normalized
    const ciSet = new Set(); for (const sn of normalized) for (const wf of sn.wfs) for (const ci of wf.checkItems) ciSet.add(ci)
    availableCheckItems.value = [...ciSet]
    if (checkItemFilter.value && !availableCheckItems.value.includes(checkItemFilter.value)) checkItemFilter.value = null
    store.lastQueryType = 'lookup'
  } catch (e) { lookupError.value = e.message || t('common.error'); lookupResults.value = []; availableCheckItems.value = [] }
}

// ── WF & Config mode ────────────────────────────────────────────────
const wcfgSelectedWf = ref(''); const wcfgSelectedConfig = ref(''); const wcfgError = ref(''); const wcfgData = ref(null)
const wcfgWfSelection = ref([])
const wcfgConfigSelection = ref([])
const wfOptions = computed(() => store.queryWfList?.wfs || [])
const wfDisplayOptions = computed(() => wfOptions.value.map(w => `WF${w.wf_num} — ${w.wf_name}`))
const configOptions = computed(() => store.queryWfList?.configs || [])
const summarySegments = computed(() => { const s = wcfgData.value?.summary || {}; const total = s.total_sns || 0; const done = s.completed || 0; const spec = s.spec_fails || 0; const strife = s.strife_fails || 0; const inProg = Math.max(0, total - done - spec - strife); return [{ kind: 'pass', value: done, label: 'Completed' }, { kind: 'fail', value: spec, label: 'Spec' }, { kind: 'strife', value: strife, label: 'Strife' }, { kind: 'progress', value: inProg, label: 'In progress' }] })
const inProgressCount = computed(() => { const s = wcfgData.value?.summary || {}; return Math.max(0, (s.total_sns || 0) - (s.completed || 0) - (s.spec_fails || 0) - (s.strife_fails || 0)) })
const wcfgGroups = computed(() => { if (!wcfgData.value) return []; const d = wcfgData.value; const cpColumns = []; const seen = new Set(); for (const sn of d.sns) for (const cp of sn.cpList) { if (!seen.has(cp.cp_idx)) { seen.add(cp.cp_idx); cpColumns.push({ cp_idx: cp.cp_idx, cp_name: cp.cp_name }) } }; cpColumns.sort((a, b) => a.cp_idx - b.cp_idx); let checkItems = d.check_items || []; if (!checkItems.length) { const nameSet = new Set(); for (const sn of d.sns) for (const cp of sn.cpList) for (const ci of cp.checkItems || []) if (ci.name) nameSet.add(ci.name); checkItems = [...nameSet] }; return [{ wf_num: d.wf_num, test_name: d.wf_name || '', check_items: checkItems, total_cps: d.total_cps, cpColumns, sns: d.sns.map(s => ({ sn: s.sn, unit_num: s.unit_num || '', config: s.config, current_cp_idx: s.current_cp_idx, cpList: s.cpList, cpByIdx: Object.fromEntries(s.cpList.map(c => [c.cp_idx, c])) })) }] })
function onWfChange() { wcfgSelectedConfig.value = ''; wcfgData.value = null }
function clearWcfg() { wcfgWfSelection.value = []; wcfgConfigSelection.value = []; wcfgSelectedWf.value = ''; wcfgSelectedConfig.value = ''; wcfgData.value = null; wcfgError.value = ''; availableCheckItems.value = []; checkItemFilter.value = null; store.clearQueryCache('wcfg'); router.replace({ name: 'sn', query: { mode: 'wcfg' } }) }
function doWfCfgSearch() {
  // Extract WF number from display string "WF10 — Drop 1m PB"
  const wfDisplay = wcfgWfSelection.value[0] || ''
  const wfMatch = wfDisplay.match(/^WF([\d.]+)/)
  const wf = wfMatch ? wfMatch[1] : ''
  if (!wf) return
  wcfgSelectedWf.value = wf
  wcfgSelectedConfig.value = wcfgConfigSelection.value.join(',')
  pushState({ mode: 'wcfg', wf, config: wcfgSelectedConfig.value || undefined })
}
async function runWfCfgSearch() { if (!wcfgSelectedWf.value) { wcfgData.value = null; availableCheckItems.value = []; return }; wcfgError.value = ''; const cfgParam = wcfgSelectedConfig.value.split(',')[0] || ''; try { const data = await store.fetchQueryByWf(wcfgSelectedWf.value, cfgParam); const sns = (data.sns || []).map(s => s.sn); const byIdx = {}; if (sns.length) { try { const timelineNorm = await store.fetchSnTimeline(sns.slice(0, 50)); for (const r of timelineNorm) for (const w of r.wfs) { if (w.wf_num !== data.wf_num) continue; for (const cp of w.cpList) byIdx[`${r.sn}|${w.config}|${cp.cp_idx}`] = cp } } catch {} }; for (const sn of data.sns || []) for (const cp of sn.cpList) { const hit = byIdx[`${sn.sn}|${sn.config}|${cp.cp_idx}`]; if (hit && Array.isArray(hit.checkItems)) cp.checkItems = hit.checkItems }; wcfgData.value = data; const nameSet = new Set(data.check_items || []); for (const key in byIdx) for (const ci of byIdx[key].checkItems || []) nameSet.add(ci.name); availableCheckItems.value = [...nameSet]; if (checkItemFilter.value && !availableCheckItems.value.includes(checkItemFilter.value)) checkItemFilter.value = null; store.lastQueryType = 'wcfg' } catch (e) { wcfgError.value = e.message || t('common.error'); wcfgData.value = null } }

// ── Failure mode (FA Tracker) ───────────────────────────────────────
const faTags = ref([]); const faInput = ref(''); const faInputRef = ref(null)
const faLoading = ref(false); const faError = ref(''); const faResults = ref([])
const faFilterSymptom = ref([]); const faFilterLocation = ref([])
const faFilterWf = ref([]); const faFilterConfig = ref([]); const faFilterTest = ref([])
const hasAnyFaFilter = computed(() => !!(faFilterSymptom.value.length || faFilterLocation.value.length || faFilterWf.value.length || faFilterConfig.value.length || faFilterTest.value.length))
const allFaOptions = ref({ symptoms: [], locations: [], configs: [], wfs: [], failed_tests: [] })

// Cascaded options: re-fetch from backend whenever any filter changes
const cascadedOptions = computed(() => allFaOptions.value)
function focusFaInput() { faInputRef.value?.focus() }
function onFaKeydown(e) { if (e.key === 'Enter') { if (faInput.value.trim()) flushFaInput(); else submitFaSearch(); e.preventDefault() } else if (e.key === ',' || e.key === '，') { if (faInput.value.trim()) { flushFaInput(); e.preventDefault() } } else if (e.key === 'Backspace' && !faInput.value && faTags.value.length) { faTags.value.pop() } }
function onFaPaste(e) { e.preventDefault(); const text = (e.clipboardData || window.clipboardData).getData('text') || ''; const tokens = text.split(/[\s,，\n\r\t]+/).filter(Boolean); for (const tok of tokens) { if (!faTags.value.includes(tok)) faTags.value.push(tok) }; faInput.value = '' }
function flushFaInput() { const tokens = faInput.value.trim().split(/[\s,，]+/).filter(Boolean); for (const tok of tokens) { if (!faTags.value.includes(tok)) faTags.value.push(tok) }; faInput.value = '' }
function removeFaTag(i) { faTags.value.splice(i, 1) }
function clearFa() { faTags.value = []; faInput.value = ''; faResults.value = []; faError.value = ''; faExpanded.value = {}; faFilterSymptom.value = []; faFilterLocation.value = []; faFilterWf.value = []; faFilterConfig.value = []; faFilterTest.value = []; store.clearQueryCache('failure'); router.replace({ name: 'sn', query: { mode: 'failure' } }) }

// FA expand state
const faExpanded = ref({})
function toggleFaEntry(ri) {
  faExpanded.value[ri] = !faExpanded.value[ri]
}

// Flatten all FA results into a single list for table display
const faFlatEntries = computed(() => {
  const rows = []
  for (const item of faResults.value) {
    for (const fa of item.entries) {
      // Prefer Mark from FA Tracker record itself; fallback to resolved mark
      const mark = String(fa.Mark || '').trim() || item.unit_num || ''
      rows.push({ sn: item.sn, unit_num: mark, fa })
    }
  }
  return rows
})
function faTypeBadgeClass(fa) {
  const ft = String(fa['Failure Type  (Spec. or Strife)'] || '').toLowerCase()
  if (ft.includes('spec')) return 'badge-spec'
  if (ft.includes('strife')) return 'badge-strife'
  return 'badge-unknown'
}
function faTypeLabel(fa) {
  const ft = String(fa['Failure Type  (Spec. or Strife)'] || '').trim()
  return ft || '—'
}

function hasVal(fa, key) { return !!(fa[key] && String(fa[key]).trim()) }
function getVal(fa, key) { return (fa[key] && String(fa[key]).trim()) || '— N/A' }

function otherFaFields(fa) {
  const skip = new Set([
    'SN', 'Mark', 'WF', 'Config', 'Failed Test',
    'Failure Symptom / Failure Message', 'Failed Location',
    'Failed Cycle Count', 'Failure Type  (Spec. or Strife)', 'FA Status',
    'Follow Up Actions', 'Root Cause', 'CA', 'Root Cause Category I', 'Root Cause Category II',
  ])
  const out = {}
  for (const [key, val] of Object.entries(fa)) {
    if (skip.has(key)) continue
    if (val && String(val).trim()) out[key] = String(val).trim()
  }
  return out
}

// Filter out empty/SN fields for display — show all non-empty FA Tracker columns
// Exclude fields already shown in the summary row
function visibleFaFields(fa) {
  const skip = new Set([
    'SN', 'Mark', 'WF', 'Config', 'Failed Test',
    'Failure Symptom / Failure Message', 'Failed Location',
    'Failed Cycle Count', 'Failure Type  (Spec. or Strife)', 'FA Status',
  ])
  // Always show these action fields (even if empty — mark as "—")
  const actionFields = ['Follow Up Actions', 'Root Cause', 'CA', 'Root Cause Category I', 'Root Cause Category II']
  const out = {}
  for (const key of actionFields) {
    out[key] = (fa[key] && String(fa[key]).trim()) || '—'
  }
  // Then add remaining non-empty fields
  for (const [key, val] of Object.entries(fa)) {
    if (skip.has(key) || actionFields.includes(key)) continue
    if (val && String(val).trim()) out[key] = String(val).trim()
  }
  return out
}
function submitFaSearch() {
  flushFaInput()
  if (!faTags.value.length && !hasAnyFaFilter.value) return
  // If we have tags, push to route (for persistence). If filter-only, just search directly.
  if (faTags.value.length) {
    pushState({ mode: 'failure', tags: faTags.value.join(',') })
  } else {
    doFaSearch()
  }
}

async function doFaSearch() {
  if (!faTags.value.length && !hasAnyFaFilter.value) { faResults.value = []; return }
  faLoading.value = true; faError.value = ''; faExpanded.value = {}

  const filters = {}
  if (faFilterSymptom.value.length) filters.symptom = faFilterSymptom.value.join(',')
  if (faFilterLocation.value.length) filters.location = faFilterLocation.value.join(',')
  if (faFilterWf.value.length) filters.wf = faFilterWf.value.join(',')
  if (faFilterConfig.value.length) filters.config = faFilterConfig.value.join(',')
  if (faFilterTest.value.length) filters.failed_test = faFilterTest.value.join(',')

  // Resolve SN/mark tags (optional — can search with filters only)
  const resolvedSns = []; const markMap = {}
  for (const tok of faTags.value) {
    if (isMarkLike(tok)) { const sn = await store.resolveMark(tok); if (sn) { resolvedSns.push(sn); markMap[sn] = tok } }
    else { resolvedSns.push(tok) }
  }

  try {
    const data = await store.fetchSnFa(resolvedSns.length ? resolvedSns : [], filters)
    const items = []
    for (const [sn, entries] of Object.entries(data)) {
      const mark = markMap[sn] || ''
      items.push({ sn, unit_num: mark, entries })
    }
    faResults.value = items
    store.lastQueryType = 'failure'
    store.faLastTags = faTags.value.join(',')
  } catch (e) { faError.value = e.message || t('common.error'); faResults.value = [] }
  finally { faLoading.value = false }
}

// ── Routing ─────────────────────────────────────────────────────────
function pushState(q) { const query = { ...q }; for (const k of Object.keys(query)) { if (query[k] === '' || query[k] == null) delete query[k] }; router.push({ name: 'sn', query }) }
function switchMode(key) { if (activeMode.value === key) return; pushState({ mode: key }) }
// Load FA filter options when entering failure mode
async function loadFaOptions() {
  const filters = {}
  if (faFilterWf.value.length) filters.wf = faFilterWf.value.join(',')
  if (faFilterConfig.value.length) filters.config = faFilterConfig.value.join(',')
  if (faFilterTest.value.length) filters.failed_test = faFilterTest.value.join(',')
  if (faFilterSymptom.value.length) filters.symptom = faFilterSymptom.value.join(',')
  if (faFilterLocation.value.length) filters.location = faFilterLocation.value.join(',')
  const opts = await store.fetchFaOptions(filters)
  allFaOptions.value = opts
}
watch(activeMode, (m) => { if (m === 'failure') loadFaOptions() })
// Cascade: re-fetch options when any filter changes
watch([faFilterWf, faFilterConfig, faFilterTest, faFilterSymptom, faFilterLocation], () => {
  if (activeMode.value === 'failure') loadFaOptions()
}, { deep: true })
function goToSingleSn(sn) { pushState({ mode: 'lookup', tags: sn }) }

async function applyRoute() {
  const q = route.query || {}; const legacyQ = q.q; const hasMode = !!q.mode; const hasLookupTags = !!q.tags || !!legacyQ; const hasWcfg = !!q.wf
  if (!hasMode && !hasLookupTags && !hasWcfg) {
    const lastType = store.lastQueryType
    if (lastType === 'wcfg' && store.queryByWfKey) { const [wf, cfg] = store.queryByWfKey.split('|'); if (wf) { activeMode.value = 'wcfg'; wcfgSelectedWf.value = wf; wcfgSelectedConfig.value = cfg || ''; await runWfCfgSearch(); return } }
    if (lastType === 'failure') {
      activeMode.value = 'failure'
      if (store.faLastTags) {
        faTags.value = store.faLastTags.split(',').filter(Boolean)
        await doFaSearch()
      }
      return
    }
    if (store.querySingleSnKey) { const tags = store.querySingleSnKey.split(',').filter(Boolean); if (tags.length) { lookupTags.value = tags; await doLookup(); return } }
    if (store.queryMultiSnKey) { const tags = store.queryMultiSnKey.split(',').filter(Boolean); if (tags.length) { lookupTags.value = tags; await doLookup(); return } }
    return
  }
  const mode = q.mode || (hasLookupTags ? 'lookup' : 'wcfg')
  activeMode.value = ['lookup', 'wcfg', 'failure'].includes(mode) ? mode : 'lookup'
  if (activeMode.value === 'lookup') { const tagsParam = q.tags || legacyQ || ''; const tags = String(tagsParam).split(',').map(s => s.trim()).filter(Boolean); const same = tags.length === lookupTags.value.length && tags.every((t2, i) => t2 === lookupTags.value[i]); if (!same) { lookupTags.value = tags; await doLookup() } else if (tags.length && !lookupResults.value.length) { await doLookup() } }
  else if (activeMode.value === 'wcfg') { const wf = String(q.wf || ''); const cfg = String(q.config || ''); const changed = wf !== wcfgSelectedWf.value || cfg !== wcfgSelectedConfig.value; wcfgSelectedWf.value = wf; wcfgSelectedConfig.value = cfg; /* Restore tag selections */ if (wf) { const wfOpt = wfDisplayOptions.value.find(o => o.startsWith(`WF${wf}`)); if (wfOpt && !wcfgWfSelection.value.includes(wfOpt)) wcfgWfSelection.value = [wfOpt] } if (cfg) { wcfgConfigSelection.value = cfg.split(',').filter(Boolean) } if (wf && (changed || !wcfgData.value || wcfgData.value.wf_num !== wf)) await runWfCfgSearch() }
  else if (activeMode.value === 'failure') { const tagsParam = q.tags || ''; const tags = String(tagsParam).split(',').map(s => s.trim()).filter(Boolean); if (tags.length) { faTags.value = tags; await doFaSearch() } }
}

async function handleRequestCi({ group, sn, cpIdx, resolve }) { try { const res = await store.fetchSnCheckDetails(sn.sn, group.wf_num, sn.config, cpIdx); resolve((res?.check_items || []).map(i => ({ name: i.check_item || i.name, status: i.status, failure_type: i.failure_type || null }))) } catch { resolve([]) } }

// ── Export helpers ──────────────────────────────────────────────────
const canExport = computed(() => {
  if (activeMode.value === 'lookup') return lookupResults.value.length > 0
  if (activeMode.value === 'wcfg') return !!(wcfgData.value && wcfgData.value.sns.length)
  if (activeMode.value === 'failure') return faFlatEntries.value.length > 0
  return false
})

function doExport() {
  if (activeMode.value === 'lookup') exportLookup()
  else if (activeMode.value === 'wcfg') exportWcfg()
  else if (activeMode.value === 'failure') exportFa()
}
function downloadCsv(filename, csvContent) {
  const bom = '\uFEFF'
  const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

function escapeCsv(val) {
  const s = String(val ?? '').replace(/"/g, '""')
  return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s}"` : s
}

function exportLookup() {
  const rows = [['SN', 'Mark', 'Config', 'WF', 'CP Index', 'CP Name', 'Status', 'Failure Type', 'Date']]
  for (const sn of lookupResults.value) {
    for (const wf of sn.wfs) {
      for (const cp of wf.cpList) {
        if (!cp) continue
        rows.push([sn.sn, sn.unit_num, wf.config, wf.wf_num, cp.cp_idx, cp.cp_name, cp.status, cp.failure_type || '', cp.date || ''])
      }
    }
  }
  const csv = rows.map(r => r.map(escapeCsv).join(',')).join('\n')
  downloadCsv(`query-sn-lookup-${new Date().toISOString().slice(0,10)}.csv`, csv)
}

function exportWcfg() {
  if (!wcfgData.value) return
  const rows = [['SN', 'Mark', 'Config', 'WF', 'CP Index', 'CP Name', 'Status', 'Failure Type', 'Date']]
  for (const sn of wcfgData.value.sns) {
    for (const cp of sn.cpList) {
      if (!cp) continue
      rows.push([sn.sn, sn.unit_num, sn.config, wcfgData.value.wf_num, cp.cp_idx, cp.cp_name, cp.status, cp.failure_type || '', cp.date || ''])
    }
  }
  const csv = rows.map(r => r.map(escapeCsv).join(',')).join('\n')
  downloadCsv(`query-wf${wcfgData.value.wf_num}-${new Date().toISOString().slice(0,10)}.csv`, csv)
}

function exportFa() {
  const rows = [['SN', 'Mark', 'WF', 'Config', 'Failed Test', 'Symptom', 'Location', 'Cycle Count', 'Type', 'Status', 'Follow Up Actions', 'Root Cause']]
  for (const item of faFlatEntries.value) {
    const fa = item.fa
    rows.push([
      item.sn, item.unit_num, fa.WF || '', fa.Config || '',
      fa['Failed Test'] || '', fa['Failure Symptom / Failure Message'] || '',
      fa['Failed Location'] || '', fa['Failed Cycle Count'] || '',
      fa['Failure Type  (Spec. or Strife)'] || '', fa['FA Status'] || '',
      fa['Follow Up Actions'] || '', fa['Root Cause'] || '',
    ])
  }
  const csv = rows.map(r => r.map(escapeCsv).join(',')).join('\n')
  downloadCsv(`query-failure-${new Date().toISOString().slice(0,10)}.csv`, csv)
}

watch(() => route.fullPath, () => { if (route.name === 'sn') applyRoute() })
onMounted(async () => { await store.fetchWfList().catch(() => {}); await applyRoute(); if (activeMode.value === 'failure') loadFaOptions() })
</script>

<style scoped>
.page-container { color: var(--text-primary); }
.mode-row { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; border-bottom: 2px solid var(--border-light); }
.mode-tabs { display: flex; gap: 4px; }
.mode-tab { padding: 10px 20px; font-size: 14px; font-weight: 500; color: var(--text-muted); background: none; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px; cursor: pointer; transition: color var(--duration-fast), border-color var(--duration-fast); }
.mode-tab:hover { color: var(--text-primary); }
.mode-tab.active { color: var(--accent-steel); border-bottom-color: var(--accent-steel); }

.search-card { padding: 14px 16px; margin-bottom: 12px; }
.search-bar { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }

/* ── Unified filter item layout ── */
.bar-filter-item { display: flex; flex-direction: column; gap: 3px; min-width: 130px; flex: 1; }
.bar-filter-item label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; }
.bar-filter-grow { flex: 2; min-width: 200px; }
.bar-actions { display: flex; gap: 6px; align-items: flex-end; flex-shrink: 0; }

.tag-input-box { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; min-height: 40px; padding: 4px 10px; border: 1px solid var(--border-input); border-radius: var(--radius-md); background: var(--bg-input); cursor: text; transition: border-color var(--duration-fast), box-shadow var(--duration-fast); }
.tag-input-box:focus-within { border-color: var(--border-focus); box-shadow: 0 0 0 3px color-mix(in srgb, var(--border-focus) 14%, transparent); }
.input-tag { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; background: var(--accent-steel); color: #fff; font-family: var(--font-mono); font-size: 12px; border-radius: var(--radius-sm); }
.tag-remove { background: none; border: none; color: #fff; cursor: pointer; font-size: 14px; padding: 0 2px; line-height: 1; opacity: 0.7; }
.tag-remove:hover { opacity: 1; }
.tag-input-field { border: none; outline: none; background: transparent; color: var(--text-primary); font-family: var(--font-mono); font-size: 14px; min-width: 140px; flex: 1; padding: 4px 2px; }
.filter-select { padding: 8px 12px; font-size: 13px; min-height: 40px; border: 1px solid var(--border-input); border-radius: var(--radius-md); background: var(--bg-input); color: var(--text-primary); }
.inline-filter { min-width: 140px; }
.search-btn { padding: 0 24px; min-height: 40px; font-size: 14px; font-weight: 500; color: #fff; background: var(--accent-steel); border: none; border-radius: var(--radius-md); cursor: pointer; white-space: nowrap; }
.search-btn:hover:not(:disabled) { opacity: 0.9; }
.search-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.clear-btn {
  width: 40px; min-height: 40px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 500;
  color: var(--text-muted); background: var(--bg-muted);
  border: 1px solid var(--border-input); border-radius: var(--radius-md);
  cursor: pointer; transition: color var(--duration-fast), background var(--duration-fast);
}
.clear-btn:hover { color: var(--color-danger); background: var(--color-danger-bg); border-color: var(--color-danger); }

.suggestions { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 0 0; }
.suggestion-chip { display: inline-flex; gap: 6px; align-items: center; padding: 4px 12px; font-family: var(--font-mono); font-size: 12px; background: var(--bg-tag); border: 1px solid var(--border-light); border-radius: var(--radius-full); color: var(--text-secondary); cursor: pointer; }
.suggestion-chip:hover { background: var(--accent-steel); color: #fff; border-color: var(--accent-steel); }
.chip-sn { font-weight: 600; }
.chip-mark { opacity: 0.8; font-size: 11px; padding-left: 4px; border-left: 1px solid currentColor; }

.result-info { padding: 6px 0; margin-bottom: 6px; display: flex; align-items: center; gap: 12px; }
.multi-summary-count { font-size: 12px; color: var(--text-muted); font-weight: 600; }
.export-btn {
  padding: 5px 14px;
  font-size: 12px; font-weight: 500;
  color: var(--accent-steel); background: transparent;
  border: 1px solid var(--accent-steel); border-radius: var(--radius-sm);
  cursor: pointer; white-space: nowrap;
  transition: background var(--duration-fast), color var(--duration-fast);
}
.export-btn:hover:not(:disabled) { background: var(--accent-steel); color: #fff; }
.export-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.top-export { margin-left: auto; margin-bottom: 6px; }

/* WF summary */
.wcfg-summary-card { padding: 14px 18px; margin-bottom: 12px; background: var(--bg-card); border: 1px solid var(--border-card); border-radius: var(--radius-md); display: flex; flex-direction: column; gap: 12px; }
.summary-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.summary-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.wf-pill-lg { padding: 3px 10px; background: var(--text-primary); color: var(--bg-card); font-family: var(--font-mono); font-size: 12px; font-weight: 700; border-radius: var(--radius-sm); }
.summary-wfname { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.summary-cfg { padding: 2px 8px; background: var(--bg-tag); color: var(--text-secondary); font-family: var(--font-mono); font-size: 11px; border-radius: var(--radius-sm); }
.summary-total { display: flex; align-items: baseline; gap: 6px; }
.total-num { font-size: 24px; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }
.total-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; }
.summary-progress { display: flex; height: 8px; width: 100%; background: var(--bg-muted); border-radius: var(--radius-full); overflow: hidden; }
.progress-seg { transition: flex var(--duration-normal); }
.progress-seg:not([style*="flex: 0"]) { min-width: 2px; }
.seg-pass { background: var(--color-success); } .seg-fail { background: var(--color-danger); } .seg-strife { background: var(--color-warning); } .seg-progress { background: var(--accent-steel); opacity: 0.4; }
.summary-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip-stat { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: var(--radius-full); font-size: 13px; background: var(--bg-row-stripe); border: 1px solid var(--border-light); }
.chip-stat.empty { opacity: 0.55; }
.chip-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.chip-num { font-weight: 700; font-variant-numeric: tabular-nums; font-size: 14px; color: var(--text-primary); }
.chip-label { font-size: 12px; color: var(--text-secondary); }
.chip-pass .chip-dot { background: var(--color-success); } .chip-pass .chip-num { color: var(--color-success); }
.chip-fail .chip-dot { background: var(--color-danger); } .chip-fail .chip-num { color: var(--color-danger); }
.chip-strife .chip-dot { background: var(--color-warning); } .chip-strife .chip-num { color: var(--color-warning); }
.chip-progress .chip-dot { background: var(--accent-steel); } .chip-progress .chip-num { color: var(--accent-steel); }

/* FA results table */
.fa-results { overflow-x: auto; }
.fa-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
  background: var(--bg-card); border: 1px solid var(--border-card); border-radius: var(--radius-md);
}
.fa-table th {
  padding: 8px 10px; text-align: left; font-size: 11px; font-weight: 600;
  color: var(--text-muted); background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light); text-transform: uppercase; letter-spacing: 0.3px;
  white-space: nowrap;
}
.fa-table td {
  padding: 8px 10px; border-bottom: 1px solid var(--border-light);
  font-size: 12px; color: var(--text-primary); vertical-align: top;
}
.fa-row { cursor: pointer; transition: background var(--duration-fast); }
.fa-row:hover { background: var(--bg-row-hover); }
.fa-row.expanded { background: color-mix(in srgb, var(--accent-steel) 6%, var(--bg-card)); }
.fa-td-sn { font-family: var(--font-mono); font-weight: 700; color: var(--accent-steel); white-space: nowrap; }
.fa-td-mark { font-family: var(--font-mono); font-size: 11px; color: var(--color-info); white-space: nowrap; }
.fa-td-symptom { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fa-type-badge { padding: 2px 6px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 700; text-transform: uppercase; white-space: nowrap; }
.badge-spec { background: var(--color-danger-bg); color: var(--color-danger); }
.badge-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.badge-unknown { background: var(--bg-muted); color: var(--text-muted); }

.fa-detail-row td { padding: 0; }
.fa-detail-panel {
  padding: 14px 20px;
  display: flex; flex-direction: column; gap: 16px;
  background: linear-gradient(180deg, var(--bg-row-stripe) 0%, var(--bg-card) 100%);
  border-top: 2px solid var(--accent-steel);
}
.fa-detail-section { }
.fa-detail-section-title {
  font-size: 11px; font-weight: 700; color: var(--accent-steel);
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 10px; padding-bottom: 6px;
  border-bottom: 1px dashed color-mix(in srgb, var(--accent-steel) 30%, var(--border-light));
}
.fa-action-section {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.fa-action-grid {
  display: grid; grid-template-columns: 1fr; gap: 12px;
}
.fa-action-item {
  display: flex; flex-direction: column; gap: 4px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-light);
}
.fa-action-item:last-child { border-bottom: none; padding-bottom: 0; }
.fa-action-label {
  font-size: 11px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.4px; font-weight: 700;
}
.fa-action-val {
  font-size: 13px; color: var(--text-primary); line-height: 1.6;
  white-space: pre-wrap; word-break: break-word;
}
.fa-action-val.empty { color: var(--text-muted); font-style: italic; font-size: 12px; }

.fa-other-section {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.fa-other-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px;
}
.fa-other-item { display: flex; flex-direction: column; gap: 3px; }
.fa-other-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; }
.fa-other-val { font-size: 12px; color: var(--text-secondary); white-space: pre-wrap; word-break: break-word; }

.empty-result { padding: 40px 20px; text-align: center; color: var(--text-muted); font-size: 14px; }
</style>
