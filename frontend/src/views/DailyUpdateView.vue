<template>
  <div class="page-container daily-update-page">
    <header class="page-heading">
      <div>
        <h1 class="page-title">{{ t('dailyUpdate.title') }}</h1>
        <p class="page-subtitle">{{ t('dailyUpdate.subtitle') }}</p>
      </div>
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
import { computed, ref, onMounted, watch } from 'vue'
import { useI18n } from '@/i18n/useI18n'
import { useAppStore } from '@/stores/app'
import DailyUpdates from '@/components/DailyUpdates.vue'
import DailyIssues from '@/components/DailyIssues.vue'
import DailyUpdateKpiCards from '@/components/DailyUpdateKpiCards.vue'
import { buildDailyUpdateKpis } from '@/views/dailyUpdateDisplay'

const store = useAppStore()
const { t } = useI18n()
const loading = ref(false)

const kpiItems = computed(() => buildDailyUpdateKpis(
  store.overviewData?.daily_updates,
  store.dailyIssues,
  store.dailyIssuesConsistency
))

async function loadAll(force = false) {
  if (!force && store.overviewData && store.dailyIssues.length) return
  loading.value = true
  try {
    await Promise.all([
      store.fetchOverview(force),
      store.fetchDailyIssues(force)
    ])
  } catch (e) {
    store.error = e.message || t('common.error')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadAll()
})

watch(() => store.refreshCounter, () => { loadAll(true) })
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

.page-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-muted);
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
