<template>
  <div class="page-container">
    <!-- Breadcrumb -->
    <div class="breadcrumb">
      <router-link to="/">Dashboard</router-link>
      <span class="sep">/</span>
      <strong>{{ categoryName }}</strong>
    </div>

    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ categoryName }} Category</h1>
        <p class="page-subtitle">Completion breakdown by config and work-flow</p>
      </div>
      <router-link to="/" class="back-btn">&larr; Back to Dashboard</router-link>
    </div>

    <!-- Loading / Error -->
    <LoadingState v-if="store.loading && !store.categoryDetail" text="Loading category..." />
    <ErrorState
      v-else-if="store.error && !store.categoryDetail"
      :message="store.error"
    />

    <template v-if="store.categoryDetail">
      <!-- Summary Cards Grid -->
      <section class="section">
        <div class="summary-grid">
          <!-- Overall card -->
          <div class="card summary-card overall-summary">
            <div class="summary-progress">
              <ConicRing :pct="overallPct" :size="72" />
            </div>
            <div class="summary-info">
              <div class="summary-label">Overall</div>
              <div class="summary-pct">{{ overallPct }}%</div>
              <div class="summary-cps">{{ overallCompleted }} / {{ overallTotal }} CPs</div>
            </div>
          </div>
          <!-- Per Config cards -->
          <div
            v-for="(cfg, idx) in configs"
            :key="cfg.name"
            class="card summary-card"
          >
            <div class="summary-config-header">
              <span class="config-dot" :style="{ background: cfgColor(idx) }"></span>
              <span class="summary-config-name">{{ cfg.name }}</span>
            </div>
            <div class="progress-track">
              <div
                class="progress-fill"
                :style="{ width: cfg.pct + '%', background: cfgColor(idx) }"
              ></div>
            </div>
            <div class="summary-cfg-stats">
              <span class="summary-pct-sm">{{ cfg.pct }}%</span>
              <span class="summary-cps-sm">{{ cfg.completed }}/{{ cfg.total }} CPs</span>
            </div>
          </div>
        </div>
      </section>

      <!-- WF Accordion -->
      <section class="section">
        <div class="section-header">
          <h2>Work-Flows</h2>
          <div class="divider"></div>
          <span class="wf-count">{{ sortedWfs.length }} WFs</span>
        </div>

        <div v-if="!sortedWfs.length" class="empty-state">No work-flow data available</div>

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
import { useAppStore } from '@/stores/app'
import ConicRing from '@/components/ConicRing.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const store = useAppStore()
const route = useRoute()

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
  return wfNames.value[key] || ''
}

async function load() {
  await store.fetchCategoryDetail(categoryName.value)
}

onMounted(load)
watch(categoryName, load)
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
  color: #1a2332;
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

/* Summary cards grid */
.summary-grid {
  display: grid;
  grid-template-columns: 1.3fr repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.overall-summary {
  flex-direction: row;
  align-items: center;
  gap: 18px;
}

.summary-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-label {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.summary-pct {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-cps {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}

.summary-config-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.config-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.summary-config-name {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.progress-track {
  height: 8px;
  background: var(--bg-progress-track);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out);
}

.summary-cfg-stats {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.summary-pct-sm {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-cps-sm {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
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
