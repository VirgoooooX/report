<template>
  <div class="daily-update-page">
    <header class="page-heading">
      <div>
        <h1 class="page-title">{{ t('dailyUpdate.title') }}</h1>
        <p class="page-subtitle">{{ t('dailyUpdate.subtitle') }}</p>
      </div>
      <button class="refresh-btn" @click="loadAll">{{ t('common.refresh') }}</button>
    </header>

    <section class="section">
      <DailyUpdateKpiCards :items="kpiItems" />
    </section>

    <section class="section">
      <DailyIssues :consistency="store.dailyIssuesConsistency" :issues="store.dailyIssues" />
    </section>

    <section class="section">
      <DailyUpdates :daily-data="store.overviewData?.daily_updates" />
    </section>

    <footer class="page-footer">
      <span>{{ t('dashboard.reportDate') }}: {{ store.reportDate || store.dailyIssuesReportDate || '—' }}</span>
      <span>{{ kpiItems.find((item) => item.key === 'wfUpdated')?.value ?? 0 }} {{ t('common.wfs') }}</span>
      <span>{{ store.dailyIssues.length }} {{ t('common.failures') }}</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from '@/i18n/useI18n'
import { useAppStore } from '@/stores/app'
import DailyUpdates from '@/components/DailyUpdates.vue'
import DailyIssues from '@/components/DailyIssues.vue'
import DailyUpdateKpiCards from '@/components/DailyUpdateKpiCards.vue'
import { buildDailyUpdateKpis } from '@/views/dailyUpdateDisplay'

const store = useAppStore()
const { t } = useI18n()

const kpiItems = computed(() => buildDailyUpdateKpis(
  store.overviewData?.daily_updates,
  store.dailyIssues,
  store.dailyIssuesConsistency
))

async function loadAll() {
  await Promise.all([
    store.fetchOverview(),
    store.fetchDailyIssues()
  ])
}

onMounted(async () => {
  try {
    await loadAll()
  } catch (e) {
    store.error = e.message || 'Failed to load daily update'
  }
})
</script>

<style scoped>
.daily-update-page {
  display: flex;
  flex-direction: column;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-muted);
}

.refresh-btn {
  padding: 7px 16px;
  font-size: 12px;
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--accent-steel);
  background: var(--bg-card);
  border: 1px solid var(--accent-steel);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.refresh-btn:hover {
  background: var(--accent-steel);
  color: #fff;
}

.page-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 32px;
  border-top: 1px solid var(--border-light);
  font-size: 13px;
  color: var(--text-muted);
}

@media (max-width: 720px) {
  .page-heading,
  .page-footer {
    flex-direction: column;
  }
}
</style>
