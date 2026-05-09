<template>
  <div class="page-container">
    <h1 class="page-title">M60 EVT REL — Test Progress Dashboard</h1>

    <!-- 1. Overview Cards -->
    <section class="section">
      <OverviewCards :overview-data="overviewCompletion" />
    </section>

    <!-- 2. Category Cards + Edit button -->
    <section class="section">
      <div class="section-header">
        <h2>Categories</h2>
        <div class="divider"></div>
        <button class="edit-btn" @click="showCatModal = true">Edit</button>
      </div>
      <CategoryCards
        :completion-data="overviewCompletion"
        @category-click="goCategory"
      />
    </section>

    <!-- 3. Charts row: Trend + Top Failures -->
    <section class="section">
      <div class="chart-row">
        <div class="chart-col card">
          <div class="chart-col-header">Failure Trend</div>
          <TrendChart :trend-data="trendData" />
        </div>
        <div class="chart-col card">
          <div class="chart-col-header">Top Failures</div>
          <TopFailChart :top-failures="topFailData" />
        </div>
      </div>
    </section>

    <!-- 4. Daily Updates -->
    <section class="section">
      <div class="section-header">
        <h2>Daily Updates</h2>
        <div class="divider"></div>
      </div>
      <DailyUpdates :daily-data="store.overviewData?.daily_updates" />
    </section>

    <!-- 5. Failure Analysis -->
    <section class="section">
      <div class="section-header">
        <h2>Failure Analysis</h2>
        <div class="divider"></div>
      </div>
      <FailureAnalysis
        :failures-data="store.overviewData?.failures"
        @drill-down="onFailDrillDown"
      />
    </section>

    <!-- 6. Test Summary matrix -->
    <section class="section">
      <div class="section-header">
        <h2>Test Summary</h2>
        <div class="divider"></div>
      </div>
      <TestSummary
        :summary-data="store.summaryData"
        @cell-click="onCellClick"
      />
    </section>

    <!-- Footer -->
    <footer class="page-footer">
      <span>Report Date: {{ store.reportDate || '—' }}</span>
      <span>{{ configCount }} Configs</span>
      <span>{{ wfCount }} WFs</span>
      <span>{{ failureCount }} Failures</span>
    </footer>

    <!-- FA Modal -->
    <div v-if="showFAModal" class="modal-overlay" @click.self="showFAModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ faTitle || 'Failure Analysis' }}</h3>
          <button class="modal-close" @click="showFAModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="modal-field"><strong>WF:</strong> {{ faWf || '—' }}</div>
          <div class="modal-field"><strong>SNs:</strong> {{ faSns?.length || 0 }} affected</div>
          <ul v-if="faSns?.length" class="sns-list">
            <li v-for="sn in faSns" :key="sn">{{ sn }}</li>
          </ul>
          <div v-else class="modal-empty">No detailed SN data available</div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showFAModal = false">Close</button>
        </div>
      </div>
    </div>

    <!-- CatManage Modal -->
    <div v-if="showCatModal" class="modal-overlay" @click.self="showCatModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Manage Categories</h3>
          <button class="modal-close" @click="showCatModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="modal-empty">Category management coming soon.</p>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCatModal = false">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import OverviewCards from '@/components/OverviewCards.vue'
import CategoryCards from '@/components/CategoryCards.vue'
import TrendChart from '@/components/TrendChart.vue'
import TopFailChart from '@/components/TopFailChart.vue'
import DailyUpdates from '@/components/DailyUpdates.vue'
import FailureAnalysis from '@/components/FailureAnalysis.vue'
import TestSummary from '@/components/TestSummary.vue'

const store = useAppStore()
const router = useRouter()

const showFAModal = ref(false)
const faWf = ref('')
const faTitle = ref('')
const faSns = ref([])
const showCatModal = ref(false)

const trendData = computed(() => {
  return store.overviewData?.trend ?? []
})

const topFailData = computed(() => {
  return store.overviewData?.failures?.top_failures ?? []
})

const overviewCompletion = computed(() => {
  return store.overviewData?.completion ?? {}
})

const configCount = computed(() => {
  if (!store.overviewData?.by_config) return 0
  return Object.keys(store.overviewData.by_config).length
})

const wfCount = computed(() => {
  if (!store.overviewData?.wf_names && !store.wfNames) return 0
  return Object.keys(store.wfNames || store.overviewData.wf_names || {}).length
})

const failureCount = computed(() => {
  return store.summaryData?.total_failures ?? store.summaryData?.total_fail ?? 0
})

function goCategory(name) {
  router.push({ name: 'category', params: { name } })
}

function onFailDrillDown(payload) {
  if (!payload) return
  showFAModal.value = true
  faWf.value = payload.wf || ''
  faTitle.value = payload.test || payload.dim || 'Failure Detail'
  faSns.value = []
}

function onCellClick(payload) {
  if (!payload) return
  showFAModal.value = true
  faWf.value = payload.wf || ''
  faTitle.value = `${payload.wf || ''} / ${payload.cfg || ''} / ${payload.test || ''}`
  faSns.value = payload.failureSns || []
}

onMounted(async () => {
  try {
    await store.fetchOverview()
  } catch {
    // silently handle - error state shown by components
  }
  try {
    await store.fetchSummary()
  } catch {
    // silently handle
  }
})
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
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-col {
  padding: 18px 20px;
}

.chart-col-header {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
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
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
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
  overflow-y: auto;
  flex: 1;
}

.modal-field {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.modal-field strong {
  color: var(--text-primary);
}

.sns-list {
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sns-list li {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 4px 10px;
  background: var(--bg-tag);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
}

.modal-empty {
  font-size: 13px;
  color: var(--text-muted);
  padding: 24px 0;
  text-align: center;
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

@media (max-width: 900px) {
  .chart-row {
    grid-template-columns: 1fr;
  }
  .page-footer {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>
