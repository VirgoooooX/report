<template>
  <div class="page-container">
    <!-- Breadcrumb -->
    <div class="breadcrumb">
      <router-link to="/">{{ t('nav.dashboard') }}</router-link>
      <span class="sep">/</span>
      <strong>{{ categoryName }}</strong>
    </div>

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ categoryName }} {{ t('categories.detail') }}</h1>
        <p class="page-subtitle">{{ t('categories.completionBreakdown') }}</p>
      </div>
      <router-link to="/" class="back-btn">&larr; {{ t('common.back') }} {{ t('nav.dashboard') }}</router-link>
    </div>

    <!-- Loading / Error -->
    <LoadingState v-if="loading" :label="t('categories.loadingCategory')" />
    <ErrorState
      v-else-if="error"
      :message="error"
      @retry="load(true)"
    />

    <template v-if="store.categoryDetail">
      <!-- Compact Stat Banner -->
      <section class="section">
        <div class="stat-banner">
          <div class="stat-overall">
            <span class="stat-overall-pct">{{ overallPct.toFixed(1) }}%</span>
            <span class="stat-overall-label">{{ overallCompleted }} / {{ overallTotal }} {{ t('categories.cpsCompleted') }}</span>
          </div>
          <div class="stat-configs">
            <div v-for="(cfg, idx) in configs" :key="cfg.name" class="stat-cfg">
              <span class="stat-cfg-dot" :style="{ background: cfgColor(idx) }"></span>
              <span class="stat-cfg-name">{{ cfg.name }}</span>
              <div class="stat-cfg-bar">
                <div class="stat-cfg-fill" :style="{ width: cfg.pct + '%', background: cfgColor(idx) }"></div>
              </div>
              <span class="stat-cfg-pct">{{ cfg.pct }}%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- WF Accordion -->
      <section class="section">
        <div class="section-header">
          <h2>{{ t('categories.waterfalls') }}</h2>
          <div class="divider"></div>
          <span class="wf-count">{{ sortedWfs.length }} {{ t('common.wfs') }}</span>
        </div>

        <div v-if="!sortedWfs.length" class="empty-state">{{ t('categories.noWaterfallData') }}</div>

        <div v-for="wf in sortedWfs" :key="wf.name" class="card wf-card">
          <div class="wf-row" @click="toggleWf(wf.name)">
            <span class="chevron" :class="{ open: expandedWfs[wf.name] }">▶</span>
            <span class="wf-pill">WF{{ wf.display }}</span>
            <span class="wf-desc">{{ wfName(wf.name) }}</span>
            <span class="wf-pct-label">{{ wfPct(wf) }}%</span>
          </div>
          <div v-show="expandedWfs[wf.name]" class="wf-body">
            <div
              v-for="cfg in wf.configs"
              :key="cfg.name"
              class="cfg-subrow"
            >
              <span class="cfg-label" :style="{ color: configColor(cfg.name) }">{{ cfg.name }}</span>
              <div class="cfg-progress-track">
                <div
                  class="cfg-progress-fill"
                  :style="{ width: cfg.pct + '%', background: configColor(cfg.name) }"
                ></div>
              </div>
              <span class="cfg-pct">{{ cfg.pct }}%</span>
              <span class="cfg-meta">CP:{{ cfg.cp_count ?? 0 }} / S:{{ cfg.sn_count ?? 0 }}</span>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '@/i18n/useI18n'
import { useAppStore } from '@/stores/app'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const store = useAppStore()
const route = useRoute()
const { t } = useI18n()

const categoryName = computed(() => route.params.name || 'Unknown')
const expandedWfs = ref({})
const CONFIG_ORDER = ['R1FNF', 'R2CNM', 'R3', 'R4']
const CONFIG_COLORS = ['#4f6f8f', '#0891b2', '#d97706', '#059669']

function toggleWf(name) { expandedWfs.value[name] = !expandedWfs.value[name] }
function cfgColor(idx) { return CONFIG_COLORS[idx] || '#4f6f8f' }
function configColor(name) {
  const idx = CONFIG_ORDER.indexOf(name)
  return idx >= 0 ? CONFIG_COLORS[idx] : '#4f6f8f'
}

// API returns flat array: [{wf, config, total_cps, completed_cps, pct, sn_count, wf_name}, ...]
const wfs = computed(() => store.categoryDetail?.wfs ?? [])
const wfNames = computed(() => store.categoryDetail?.wf_names ?? {})

// Overall sums
const overallCompleted = computed(() => wfs.value.reduce((s, w) => s + (w.completed_cps || 0), 0))
const overallTotal = computed(() => wfs.value.reduce((s, w) => s + (w.total_cps || 0), 0))
const overallPct = computed(() => overallTotal.value > 0 ? (overallCompleted.value / overallTotal.value * 100) : 0)

// Per-config aggregation
const configs = computed(() => {
  const map = {}
  wfs.value.forEach(w => {
    if (!map[w.config]) map[w.config] = { completed: 0, total: 0 }
    map[w.config].completed += w.completed_cps || 0
    map[w.config].total += w.total_cps || 0
  })
  return CONFIG_ORDER.filter(c => map[c]).map(c => ({
    name: c,
    completed: map[c].completed,
    total: map[c].total,
    pct: map[c].total > 0 ? Math.round(map[c].completed / map[c].total * 1000) / 10 : 0
  }))
})

// Group by WF
const sortedWfs = computed(() => {
  const groups = {}
  wfs.value.forEach(w => {
    const key = w.wf
    if (!groups[key]) groups[key] = { name: key, display: key.replace(/^WF/i, ''), configs: [], totalCompleted: 0, totalCps: 0 }
    groups[key].configs.push({
      name: w.config,
      pct: w.pct ?? 0,
      cp_count: w.completed_cps || 0,
      sn_count: w.sn_count || 0
    })
    groups[key].totalCompleted += w.completed_cps || 0
    groups[key].totalCps += w.total_cps || 0
  })
  return store.sortedWfKeys(Object.keys(groups)).map(key => groups[key])
})

function wfPct(wf) {
  return wf.totalCps > 0 ? Math.round(wf.totalCompleted / wf.totalCps * 1000) / 10 : 0
}

function wfName(key) {
  const v = wfNames.value[key]
  return typeof v === 'object' ? v?.name || '' : v || ''
}

const loading = ref(false)
const error = ref('')

async function load(force = false) {
  if (!force && store.categoryDetail) return
  loading.value = true
  error.value = ''
  try {
    await store.fetchCategoryDetail(categoryName.value, force)
  } catch (e) {
    error.value = e.message || 'Failed to load category'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(categoryName, () => load())

watch(() => store.refreshCounter, () => { load(true) })
</script>

<style scoped>
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 32px 40px;
}

.breadcrumb {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.breadcrumb a {
  color: var(--accent-steel);
  text-decoration: none;
}

.breadcrumb a:hover {
  text-decoration: underline;
}

.breadcrumb .sep {
  margin: 0 8px;
  color: var(--border-input);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
  gap: 16px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 500;
  color: #fff;
  background: var(--accent-steel);
  border-radius: 6px;
  text-decoration: none;
  white-space: nowrap;
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.back-btn:hover {
  opacity: 0.9;
}

.section {
  margin-bottom: var(--space-2xl);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  margin-bottom: 18px;
}

.section-header h2 {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-header .divider {
  flex: 1;
  height: 1px;
  background: var(--border-light);
}

.wf-count {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
}


/* Compact stat banner */
.stat-banner {
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: 16px 20px;
}
.stat-overall {
  display: flex; align-items: baseline; gap: 12px;
  padding-bottom: 12px; margin-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}
.stat-overall-pct {
  font-family: var(--font-display); font-size: 28px; font-weight: 700;
  color: var(--text-primary); line-height: 1;
}
.stat-overall-label {
  font-size: 13px; color: var(--text-muted); font-family: var(--font-mono);
}
.stat-configs { display: flex; flex-direction: column; gap: 8px; }
.stat-cfg {
  display: flex; align-items: center; gap: 10px;
}
.stat-cfg-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.stat-cfg-name {
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  color: var(--text-secondary); min-width: 54px;
}
.stat-cfg-bar {
  flex: 1; height: 6px; background: var(--bg-progress-track);
  border-radius: 3px; overflow: hidden;
}
.stat-cfg-fill {
  height: 100%; border-radius: 3px;
  transition: width var(--duration-slow) var(--ease-out);
}
.stat-cfg-pct {
  font-family: var(--font-display); font-size: 13px; font-weight: 600;
  color: var(--text-primary); min-width: 38px; text-align: right;
}

/* WF Accordion */
.wf-card {
  margin-bottom: 8px;
  overflow: hidden;
}

.wf-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-in-out);
}

.wf-row:hover {
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

.wf-desc {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--text-muted);
  flex: 1;
}

.wf-pct-label {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.wf-body {
  padding: 0 20px 14px;
  border-top: 1px solid var(--border-light);
}

.cfg-subrow {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  padding-left: 24px;
}

.cfg-label {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  min-width: 56px;
}

.cfg-progress-track {
  flex: 1;
  height: 6px;
  background: var(--bg-progress-track);
  border-radius: var(--radius-full);
  overflow: hidden;
  max-width: 220px;
}

.cfg-progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out);
}

.cfg-pct {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 42px;
  text-align: right;
}

.cfg-meta {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  min-width: 90px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 14px;
}

@media (max-width: 800px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
  .page-header {
    flex-direction: column;
  }
}
</style>
