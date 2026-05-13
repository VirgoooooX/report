<template>
  <div class="page-container">
    <div class="page-head">
      <h1 class="page-title">{{ t('dashboard.title') }}</h1>
    </div>

    <LoadingState v-if="loading && !store.overviewData" variant="skeleton" />
    <ErrorState
      v-else-if="error && !store.overviewData"
      :message="error"
      :retry-label="t('common.retry')"
      @retry="loadAll"
    />
    <template v-else>
    <!-- 1. Overview Cards -->
    <section class="section">
      <OverviewCards :overview-data="overviewCompletion" />
    </section>

    <!-- 2. Category Cards + Edit button -->
    <section class="section">
      <div class="section-header">
        <h2>{{ t('dashboard.categories') }}</h2>
        <div class="divider"></div>
        <button class="edit-btn" @click="showCatModal = true">{{ t('common.edit') }}</button>
      </div>
      <CategoryCards
        @category-click="goCategory"
      />
    </section>

    <!-- 3. Charts row: Trend + Cross-Analysis Heatmap -->
    <section class="section">
      <div class="chart-row">
        <div class="chart-col card">
          <div class="chart-col-header">{{ t('dashboard.failureTrend') }}</div>
          <div class="chart-col-body">
            <TrendChart class="chart-fill" :trend-data="trendData" />
          </div>
        </div>
        <div class="chart-col card">
          <div class="chart-col-header">
            {{ t('dashboard.crossAnalysis') }}
            <router-link to="/failure-analysis" class="view-more-link">
              {{ t('common.details') }} →
            </router-link>
          </div>
          <div class="chart-col-body">
            <DashboardHeatmap class="chart-fill" :cross-data="crossData" />
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="page-footer">
      <span>{{ t('dashboard.reportDate') }}: {{ store.reportDate || '—' }}</span>
      <span>{{ configCount }} {{ t('common.configs') }}</span>
      <span>{{ wfCount }} {{ t('common.wfs') }}</span>
      <span>{{ failureCount }} {{ t('common.failures') }}</span>
    </footer>
    </template>

    <!-- CatManage Modal -->
    <CatManageModal :show="showCatModal" @close="showCatModal = false" @updated="refresh" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from '@/i18n/useI18n'
import { useAppStore } from '@/stores/app'
import OverviewCards from '@/components/OverviewCards.vue'
import CategoryCards from '@/components/CategoryCards.vue'
import TrendChart from '@/components/TrendChart.vue'
import DashboardHeatmap from '@/components/DashboardHeatmap.vue'
import CatManageModal from '@/components/CatManageModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const store = useAppStore()
const router = useRouter()
const { t } = useI18n()

const showCatModal = ref(false)
const loading = ref(false)
const error = ref(null)

const trendData = computed(() => {
  return store.overviewData?.trend ?? []
})

const crossData = computed(() => store.crossData)

const overviewCompletion = computed(() => {
  return store.overviewData?.completion ?? {}
})

const configCount = computed(() => {
  const byCfg = store.overviewData?.completion?.by_config
  return byCfg ? Object.keys(byCfg).length : 0
})

const wfCount = computed(() => {
  const byWf = store.overviewData?.failures?.by_wf
  return byWf ? Object.keys(byWf).length : 0
})

const failureCount = computed(() => {
  const trend = store.overviewData?.trend ?? []
  if (!trend.length) return 0
  const last = trend[trend.length - 1]
  return (last.spec || 0) + (last.strife || 0)
})

function goCategory(name) {
  router.push({ name: 'category', params: { name } })
}

async function loadAll(force = false) {
  if (!force && store.overviewData && store.crossData) return
  loading.value = true
  error.value = null
  try {
    await Promise.all([
      store.fetchOverview(force),
      store.fetchFaCross('location', 'config', force)
    ])
  } catch (e) {
    error.value = e.message || 'Failed to load dashboard'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAll()
})

watch(() => store.refreshCounter, () => { loadAll(true) })
</script>

<style scoped>
.page-container {
  color: var(--text-primary);
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: var(--space-xl);
}

.page-head .page-title {
  margin-bottom: 0;
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

.edit-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-family: var(--font-display);
  font-weight: 500;
  color: var(--accent-steel);
  background: transparent;
  border: 1px solid var(--accent-steel);
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--duration-fast) var(--ease-in-out),
              color var(--duration-fast) var(--ease-in-out);
}

.edit-btn:hover {
  background: var(--accent-steel);
  color: #fff;
}

/* Charts row */
.chart-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(460px, 100%), 1fr));
  gap: 16px;
  align-items: stretch;
}

.chart-col {
  min-width: 0;
  padding: 18px 20px 20px;
  display: flex;
  flex-direction: column;
  min-height: 420px;
}

.chart-col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.chart-col-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.chart-fill {
  flex: 1;
  min-height: 0;
}

.view-more-link {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-steel);
  text-decoration: none;
  opacity: 0.7;
  transition: opacity var(--duration-fast);
}

.view-more-link:hover {
  opacity: 1;
}

/* Footer */
.page-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 32px;
  border-top: 1px solid var(--border-light);
  font-size: 13px;
  color: var(--text-muted);
}

@media (max-width: 900px) {
  .page-footer {
    flex-wrap: wrap;
    gap: 8px;
  }
}

@media (max-width: 760px) {
  .page-head {
    align-items: stretch;
  }
}
</style>
