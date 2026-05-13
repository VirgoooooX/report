<template>
  <div class="page-container">
    <!-- Mode switch + global check-item filter on same row -->
    <div class="mode-row">
      <div class="mode-tabs" role="tablist">
        <button
          v-for="m in modes"
          :key="m.key"
          class="mode-tab"
          :class="{ active: activeMode === m.key }"
          role="tab"
          :aria-selected="activeMode === m.key"
          @click="switchMode(m.key)"
        >{{ t(m.i18n) }}</button>
      </div>
      <div v-if="availableCheckItems.length" class="filter-bar">
        <label class="filter-label">{{ t('queryCenter.checkItem') }}:</label>
        <select v-model="checkItemFilter" class="filter-select">
          <option :value="null">{{ t('queryCenter.allCpLevel') }}</option>
          <option v-for="ci in availableCheckItems" :key="ci" :value="ci">{{ ci }}</option>
        </select>
      </div>
    </div>

    <!-- ═══════════ Lookup mode ═══════════ -->
    <div v-if="activeMode === 'lookup'" class="mode-content">
      <div class="card search-card">
        <div class="tag-input-row">
          <div class="tag-input-box" @click="focusTagInput">
            <span v-for="(tag, i) in lookupTags" :key="tag + '_' + i" class="input-tag">
              <span class="tag-label">{{ tag }}</span>
              <button class="tag-remove" @click.stop="removeTag(i)" aria-label="remove">×</button>
            </span>
            <input
              ref="tagInputRef"
              v-model="lookupInput"
              type="text"
              class="tag-input-field"
              :placeholder="lookupTags.length ? '' : t('queryCenter.snOrMarkPlaceholder')"
              @input="onLookupInput"
              @keydown="onLookupKeydown"
            />
          </div>
          <button
            class="search-btn primary"
            :disabled="loading || (!lookupTags.length && !lookupInput.trim())"
            @click="doLookup"
          >{{ loading ? t('common.loading') : t('actions.search') }}</button>
        </div>

        <div v-if="lookupSuggestions.length" class="suggestions">
          <span
            v-for="s in lookupSuggestions"
            :key="s.sn + '|' + s.unit_num"
            class="suggestion-chip"
            @click="selectSuggestion(s)"
          >
            <span class="chip-sn">{{ s.sn }}</span>
            <span v-if="s.unit_num" class="chip-mark">{{ s.unit_num }}</span>
          </span>
        </div>

        <ErrorState v-if="lookupError" :message="lookupError" @retry="doLookup" />
      </div>

      <LoadingState v-if="loading && !lookupResults.length" />

      <template v-if="lookupResults.length">
        <div class="multi-summary-bar">
          <span class="multi-summary-count">
            {{ lookupResults.length }} {{ t('queryCenter.snsMatched') }}
          </span>
        </div>
        <CompareView
          :groups="lookupGroups"
          :checkItemFilter="checkItemFilter"
          :wfNames="store.wfNames"
          @open-sn="goToSingleSn"
          @request-ci="handleRequestCi"
        />
      </template>
    </div>

    <!-- ═══════════ WF & Config mode ═══════════ -->
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
          class="search-btn primary"
          :disabled="!wcfgSelectedWf || loading"
          @click="doWfCfgSearch"
        >{{ loading ? t('common.loading') : t('actions.search') }}</button>
        <ErrorState v-if="wcfgError" :message="wcfgError" @retry="doWfCfgSearch" />
      </div>

      <LoadingState v-if="loading && !wcfgData" />

      <template v-if="wcfgData">
        <!-- Visual summary: progress bar + colored chips -->
        <div class="wcfg-summary-card">
          <div class="summary-header">
            <div class="summary-title">
              <span class="wf-pill-lg">WF{{ wcfgData.wf_num }}</span>
              <span class="summary-wfname">{{ wcfgData.wf_name || '' }}</span>
              <span v-if="wcfgData.config_filter && wcfgData.config_filter !== 'All'" class="summary-cfg">
                {{ wcfgData.config_filter }}
              </span>
            </div>
            <div class="summary-total">
              <span class="total-num">{{ wcfgData.summary.total_sns || 0 }}</span>
              <span class="total-label">{{ t('queryCenter.totalSn') }}</span>
            </div>
          </div>

          <div class="summary-progress">
            <div
              v-for="seg in summarySegments"
              :key="seg.kind"
              class="progress-seg"
              :class="`seg-${seg.kind}`"
              :style="{ flex: seg.value }"
              :title="`${seg.label}: ${seg.value}`"
            />
          </div>

          <div class="summary-chips">
            <div class="chip-stat chip-pass" :class="{ empty: !wcfgData.summary.completed }">
              <span class="chip-dot" />
              <span class="chip-num">{{ wcfgData.summary.completed || 0 }}</span>
              <span class="chip-label">{{ t('common.completed') }}</span>
            </div>
            <div class="chip-stat chip-fail" :class="{ empty: !wcfgData.summary.spec_fails }">
              <span class="chip-dot" />
              <span class="chip-num">{{ wcfgData.summary.spec_fails || 0 }}</span>
              <span class="chip-label">Spec</span>
            </div>
            <div class="chip-stat chip-strife" :class="{ empty: !wcfgData.summary.strife_fails }">
              <span class="chip-dot" />
              <span class="chip-num">{{ wcfgData.summary.strife_fails || 0 }}</span>
              <span class="chip-label">Strife</span>
            </div>
            <div class="chip-stat chip-progress">
              <span class="chip-dot" />
              <span class="chip-num">{{ inProgressCount }}</span>
              <span class="chip-label">{{ t('common.inProgress') }}</span>
            </div>
          </div>
        </div>

        <CompareView
          v-if="wcfgGroups.length"
          :groups="wcfgGroups"
          :checkItemFilter="checkItemFilter"
          :wfNames="store.wfNames"
          @open-sn="goToSingleSn"
          @request-ci="handleRequestCi"
        />
        <div v-else class="empty-result">{{ t('common.noData') }}</div>
      </template>
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

const store = useAppStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const modes = [
  { key: 'lookup', i18n: 'queryCenter.lookupMode' },
  { key: 'wcfg', i18n: 'queryCenter.wfCfg' },
]
const activeMode = ref('lookup')

const loading = computed(() => store.loading)

const checkItemFilter = ref(null)
const availableCheckItems = ref([])

// ── Lookup mode state ───────────────────────────────────────────────
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
  suggestDebounce = setTimeout(async () => {
    try { lookupSuggestions.value = (await store.searchSn(q)).slice(0, 10) }
    catch { lookupSuggestions.value = [] }
  }, 300)
}

function onLookupKeydown(e) {
  if (e.key === 'Enter') {
    if (lookupInput.value.trim()) addTagsFromInput()
    else submitLookup()
    e.preventDefault()
  } else if (e.key === ',' || e.key === '，' || e.key === ' ') {
    if (lookupInput.value.trim()) { addTagsFromInput(); e.preventDefault() }
  } else if (e.key === 'Backspace' && !lookupInput.value && lookupTags.value.length) {
    lookupTags.value.pop()
  }
}

function addTagsFromInput() {
  const tokens = lookupInput.value.trim().split(/[\s,，]+/).filter(Boolean)
  for (const tok of tokens) {
    if (!lookupTags.value.includes(tok)) lookupTags.value.push(tok)
  }
  lookupInput.value = ''
  lookupSuggestions.value = []
}

function removeTag(i) { lookupTags.value.splice(i, 1) }

function selectSuggestion(s) {
  if (!lookupTags.value.includes(s.sn)) lookupTags.value.push(s.sn)
  lookupInput.value = ''
  lookupSuggestions.value = []
  nextTick(() => focusTagInput())
}

// Trigger router push (source of truth) — doLookup fires on route change.
function submitLookup() {
  if (lookupInput.value.trim()) addTagsFromInput()
  if (!lookupTags.value.length) return
  pushState({ mode: 'lookup', tags: lookupTags.value.join(',') })
}

async function doLookup() {
  if (!lookupTags.value.length) {
    lookupResults.value = []
    availableCheckItems.value = []
    return
  }
  if (lookupTags.value.length > 50) {
    lookupError.value = t('queryCenter.tooManySns')
    return
  }
  lookupError.value = ''
  lookupSuggestions.value = []

  // Resolve marks → real SNs
  const resolvedSns = []
  const markMap = {}
  for (const tok of lookupTags.value) {
    if (isMarkLike(tok)) {
      const sn = await store.resolveMark(tok)
      if (sn) { resolvedSns.push(sn); markMap[sn] = tok }
    } else {
      resolvedSns.push(tok)
    }
  }
  if (!resolvedSns.length) {
    lookupError.value = t('queryCenter.noResolved')
    lookupResults.value = []
    availableCheckItems.value = []
    return
  }

  try {
    const normalized = await store.fetchSnTimeline(resolvedSns)
    for (const r of normalized) {
      if (!r.unit_num && markMap[r.sn]) r.unit_num = markMap[r.sn]
    }
    lookupResults.value = normalized
    const ciSet = new Set()
    for (const sn of normalized) for (const wf of sn.wfs) for (const ci of wf.checkItems) ciSet.add(ci)
    availableCheckItems.value = [...ciSet]
  } catch (e) {
    lookupError.value = e.message || t('common.error')
    lookupResults.value = []
    availableCheckItems.value = []
  }
}

// ── WF & Config mode state ──────────────────────────────────────────
const wcfgSelectedWf = ref('')
const wcfgSelectedConfig = ref('')
const wcfgError = ref('')
const wcfgData = ref(null)

const wfOptions = computed(() => store.queryWfList?.wfs || [])
const configOptions = computed(() => store.queryWfList?.configs || [])

const summarySegments = computed(() => {
  const s = wcfgData.value?.summary || {}
  const total = s.total_sns || 0
  const done = s.completed || 0
  const spec = s.spec_fails || 0
  const strife = s.strife_fails || 0
  const inProg = Math.max(0, total - done - spec - strife)
  return [
    { kind: 'pass', value: done, label: 'Completed' },
    { kind: 'fail', value: spec, label: 'Spec' },
    { kind: 'strife', value: strife, label: 'Strife' },
    { kind: 'progress', value: inProg, label: 'In progress' },
  ]
})

const inProgressCount = computed(() => {
  const s = wcfgData.value?.summary || {}
  const total = s.total_sns || 0
  return Math.max(0, total - (s.completed || 0) - (s.spec_fails || 0) - (s.strife_fails || 0))
})

const wcfgGroups = computed(() => {
  if (!wcfgData.value) return []
  const d = wcfgData.value
  const cpColumns = []
  const seen = new Set()
  for (const sn of d.sns) {
    for (const cp of sn.cpList) {
      if (!seen.has(cp.cp_idx)) {
        seen.add(cp.cp_idx)
        cpColumns.push({ cp_idx: cp.cp_idx, cp_name: cp.cp_name })
      }
    }
  }
  cpColumns.sort((a, b) => a.cp_idx - b.cp_idx)
  let checkItems = d.check_items || []
  if (!checkItems.length) {
    const nameSet = new Set()
    for (const sn of d.sns) {
      for (const cp of sn.cpList) {
        for (const ci of cp.checkItems || []) if (ci.name) nameSet.add(ci.name)
      }
    }
    checkItems = [...nameSet]
  }
  return [{
    wf_num: d.wf_num,
    test_name: d.wf_name || '',
    check_items: checkItems,
    total_cps: d.total_cps,
    cpColumns,
    sns: d.sns.map(s => ({
      sn: s.sn,
      unit_num: s.unit_num || '',
      config: s.config,
      current_cp_idx: s.current_cp_idx,
      cpList: s.cpList,
      cpByIdx: Object.fromEntries(s.cpList.map(c => [c.cp_idx, c])),
    })),
  }]
})

function onWfChange() {
  wcfgSelectedConfig.value = ''
  wcfgData.value = null
}

function doWfCfgSearch() {
  if (!wcfgSelectedWf.value) return
  pushState({
    mode: 'wcfg',
    wf: wcfgSelectedWf.value,
    config: wcfgSelectedConfig.value || undefined,
  })
}

async function runWfCfgSearch() {
  if (!wcfgSelectedWf.value) {
    wcfgData.value = null
    availableCheckItems.value = []
    return
  }
  wcfgError.value = ''
  try {
    const data = await store.fetchQueryByWf(wcfgSelectedWf.value, wcfgSelectedConfig.value || '')
    const sns = (data.sns || []).map(s => s.sn)
    const byIdx = {}
    if (sns.length) {
      try {
        const timelineNorm = await store.fetchSnTimeline(sns.slice(0, 50))
        for (const r of timelineNorm) {
          for (const w of r.wfs) {
            if (w.wf_num !== data.wf_num) continue
            for (const cp of w.cpList) {
              byIdx[`${r.sn}|${w.config}|${cp.cp_idx}`] = cp
            }
          }
        }
      } catch { /* non-fatal */ }
    }
    for (const sn of data.sns || []) {
      for (const cp of sn.cpList) {
        const hit = byIdx[`${sn.sn}|${sn.config}|${cp.cp_idx}`]
        if (hit && Array.isArray(hit.checkItems)) cp.checkItems = hit.checkItems
      }
    }
    wcfgData.value = data
    const nameSet = new Set(data.check_items || [])
    for (const key in byIdx) {
      for (const ci of byIdx[key].checkItems || []) nameSet.add(ci.name)
    }
    availableCheckItems.value = [...nameSet]
  } catch (e) {
    wcfgError.value = e.message || t('common.error')
    wcfgData.value = null
  }
}

// ── Routing / state persistence ─────────────────────────────────────
// All search state lives in route query. Navigating away and coming back
// restores via route; Pinia caches persist the actual fetched data so we
// don't re-hit the backend unnecessarily.

function pushState(q) {
  const query = { ...q }
  // Drop empty values
  for (const k of Object.keys(query)) {
    if (query[k] === '' || query[k] == null) delete query[k]
  }
  router.push({ name: 'sn', query })
}

function switchMode(key) {
  if (activeMode.value === key) return
  // Push a route change so tab switching is also in history.
  pushState({ mode: key })
}

function goToSingleSn(sn) {
  pushState({ mode: 'lookup', tags: sn })
}

async function applyRoute() {
  const q = route.query || {}
  const legacyQ = q.q  // backward compat with old /sn?q=XXX links
  const hasMode = !!q.mode
  const hasLookupTags = !!q.tags || !!legacyQ
  const hasWcfg = !!q.wf

  // Determine target mode from URL. If URL is completely bare, keep whatever
  // state the component/store already has (don't clear on navigation back).
  if (!hasMode && !hasLookupTags && !hasWcfg) {
    // Bare /sn URL. Rehydrate from store caches if available.
    if (!lookupTags.value.length && store.querySingleSnKey) {
      const tags = store.querySingleSnKey.split(',').filter(Boolean)
      if (tags.length) {
        lookupTags.value = tags
        await doLookup()
        return
      }
    }
    if (!lookupTags.value.length && store.queryMultiSnKey) {
      const tags = store.queryMultiSnKey.split(',').filter(Boolean)
      if (tags.length) {
        lookupTags.value = tags
        await doLookup()
        return
      }
    }
    if (!wcfgSelectedWf.value && store.queryByWfKey) {
      const [wf, cfg] = store.queryByWfKey.split('|')
      if (wf) {
        activeMode.value = 'wcfg'
        wcfgSelectedWf.value = wf
        wcfgSelectedConfig.value = cfg || ''
        await runWfCfgSearch()
        return
      }
    }
    // Nothing cached: stay on lookup mode with empty state.
    return
  }

  const mode = q.mode || (hasLookupTags ? 'lookup' : 'wcfg')
  activeMode.value = mode === 'wcfg' ? 'wcfg' : 'lookup'

  if (activeMode.value === 'lookup') {
    const tagsParam = q.tags || legacyQ || ''
    const tags = String(tagsParam).split(',').map(s => s.trim()).filter(Boolean)
    const same = tags.length === lookupTags.value.length &&
      tags.every((t, i) => t === lookupTags.value[i])
    if (!same) {
      lookupTags.value = tags
      await doLookup()
    } else if (tags.length && !lookupResults.value.length) {
      await doLookup()
    }
  } else {
    const wf = String(q.wf || '')
    const cfg = String(q.config || '')
    const changed = wf !== wcfgSelectedWf.value || cfg !== wcfgSelectedConfig.value
    wcfgSelectedWf.value = wf
    wcfgSelectedConfig.value = cfg
    if (wf && (changed || !wcfgData.value || wcfgData.value.wf_num !== wf)) {
      await runWfCfgSearch()
    }
  }
}

// ── CompareView delegate: lazy-load check items ─────────────────────
async function handleRequestCi({ group, sn, cpIdx, resolve }) {
  try {
    const res = await store.fetchSnCheckDetails(sn.sn, group.wf_num, sn.config, cpIdx)
    resolve((res?.check_items || []).map(i => ({
      name: i.check_item || i.name,
      status: i.status,
      failure_type: i.failure_type || null,
    })))
  } catch {
    resolve([])
  }
}

// Reset filter when switching modes
watch(activeMode, () => { checkItemFilter.value = null })

// Respond to route changes (back/forward button, programmatic pushes)
watch(() => route.fullPath, () => {
  if (route.name === 'sn') applyRoute()
})

// ── Init ────────────────────────────────────────────────────────────
onMounted(async () => {
  await store.fetchWfList().catch(() => {})
  await applyRoute()
})
</script>

<style scoped>
.page-container { color: var(--text-primary); }

.mode-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  border-bottom: 2px solid var(--border-light);
}

.mode-tabs { display: flex; gap: 4px; }
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

.filter-bar {
  display: flex; align-items: center; gap: 8px;
  padding-bottom: 8px;
}
.filter-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
.filter-select {
  padding: 8px 12px;
  font-size: 13px;
  min-height: 40px;
  border: 1px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg-input); color: var(--text-primary);
  min-width: 160px;
}
.wcfg-filters .filter-select { min-width: 220px; }
.wcfg-filters .search-btn { margin-left: auto; }

.search-card, .wcfg-filters {
  padding: 16px 20px;
  margin-bottom: 16px;
  min-height: 76px;
  display: flex;
  align-items: center;
}
.wcfg-filters {
  gap: 12px;
  flex-wrap: wrap;
}
.search-card { flex-direction: column; align-items: stretch; gap: 10px; }

.tag-input-row { display: flex; gap: 10px; align-items: stretch; }
.tag-input-box {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 42px;
  padding: 6px 10px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  cursor: text;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}
.tag-input-box:focus-within {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--border-focus) 14%, transparent);
}
.input-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: var(--accent-steel); color: #fff;
  font-family: var(--font-mono); font-size: 12px;
  border-radius: var(--radius-sm);
}
.tag-remove {
  background: none; border: none; color: #fff; cursor: pointer;
  font-size: 14px; padding: 0 2px; line-height: 1; opacity: 0.7;
}
.tag-remove:hover { opacity: 1; }
.tag-input-field {
  border: none; outline: none; background: transparent;
  color: var(--text-primary);
  font-family: var(--font-mono); font-size: 14px;
  min-width: 140px; flex: 1; padding: 4px 2px;
}

.search-btn {
  padding: 0 24px;
  min-height: 40px;
  font-size: 14px; font-weight: 500;
  color: #fff;
  background: var(--accent-steel);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  white-space: nowrap;
}
.search-btn:hover:not(:disabled) { opacity: 0.9; }
.search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.suggestions { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 0 0; }
.suggestion-chip {
  display: inline-flex; gap: 6px; align-items: center;
  padding: 4px 12px;
  font-family: var(--font-mono); font-size: 12px;
  background: var(--bg-tag);
  border: 1px solid var(--border-light); border-radius: var(--radius-full);
  color: var(--text-secondary); cursor: pointer;
}
.suggestion-chip:hover { background: var(--accent-steel); color: #fff; border-color: var(--accent-steel); }
.chip-sn { font-weight: 600; }
.chip-mark { opacity: 0.8; font-size: 11px; padding-left: 4px; border-left: 1px solid currentColor; }

.multi-summary-bar {
  padding: 10px 14px; margin-bottom: 10px;
  background: var(--bg-card); border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  font-size: 13px; color: var(--text-secondary);
}
.multi-summary-count { font-weight: 600; color: var(--text-primary); }

/* ── WF&Cfg summary card (richer) ── */
.wcfg-summary-card {
  padding: 14px 18px;
  margin-bottom: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.summary-header {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
}
.summary-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.wf-pill-lg {
  padding: 3px 10px;
  background: var(--text-primary); color: var(--bg-card);
  font-family: var(--font-mono); font-size: 12px; font-weight: 700;
  border-radius: var(--radius-sm);
}
.summary-wfname { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.summary-cfg {
  padding: 2px 8px;
  background: var(--bg-tag); color: var(--text-secondary);
  font-family: var(--font-mono); font-size: 11px;
  border-radius: var(--radius-sm);
}
.summary-total {
  display: flex; align-items: baseline; gap: 6px;
}
.total-num {
  font-size: 24px; font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.total-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.summary-progress {
  display: flex;
  height: 8px;
  width: 100%;
  background: var(--bg-muted);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.progress-seg { transition: flex var(--duration-normal); }
.progress-seg:not([style*="flex: 0"]) { min-width: 2px; }
.seg-pass     { background: var(--color-success); }
.seg-fail     { background: var(--color-danger); }
.seg-strife   { background: var(--color-warning); }
.seg-progress { background: var(--accent-steel); opacity: 0.4; }

.summary-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip-stat {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 13px;
  background: var(--bg-row-stripe);
  border: 1px solid var(--border-light);
  transition: opacity var(--duration-fast);
}
.chip-stat.empty { opacity: 0.55; }
.chip-dot {
  width: 8px; height: 8px; border-radius: 50%;
  flex-shrink: 0;
}
.chip-num {
  font-weight: 700; font-variant-numeric: tabular-nums;
  font-size: 14px; color: var(--text-primary);
}
.chip-label {
  font-size: 12px; color: var(--text-secondary);
}
.chip-pass   .chip-dot { background: var(--color-success); }
.chip-pass   .chip-num { color: var(--color-success); }
.chip-fail   .chip-dot { background: var(--color-danger); }
.chip-fail   .chip-num { color: var(--color-danger); }
.chip-strife .chip-dot { background: var(--color-warning); }
.chip-strife .chip-num { color: var(--color-warning); }
.chip-progress .chip-dot { background: var(--accent-steel); }
.chip-progress .chip-num { color: var(--accent-steel); }

.empty-result { padding: 40px 20px; text-align: center; color: var(--text-muted); font-size: 14px; }
</style>
