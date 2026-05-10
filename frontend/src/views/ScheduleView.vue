<template>
  <div class="schedule-page">
    <header class="page-heading">
      <div>
        <h1 class="page-title">{{ t('schedule.title') }}</h1>
        <p class="page-subtitle">{{ t('schedule.subtitle') }}</p>
      </div>
      <button class="refresh-btn" @click="loadData">{{ t('common.refresh') }}</button>
    </header>

    <section class="metric-grid">
      <div class="card metric-card">
        <span class="metric-label">{{ t('schedule.totalSegments') }}</span>
        <strong>{{ scheduleLanes.length }}</strong>
      </div>
      <div class="card metric-card">
        <span class="metric-label">{{ t('schedule.totalWfs') }}</span>
        <strong>{{ groupedRows.length }}</strong>
      </div>
      <div class="card metric-card">
        <span class="metric-label">{{ t('schedule.dateRange') }}</span>
        <strong>{{ dateRangeLabel }}</strong>
      </div>
      <div class="card metric-card">
        <span class="metric-label">{{ t('schedule.cpLabels') }}</span>
        <strong>{{ visibleCpCount }}</strong>
      </div>
    </section>

    <section class="card filter-card">
      <label>
        <span>{{ t('schedule.filterWf') }}</span>
        <input v-model="filterWf" :placeholder="t('schedule.filterWfPlaceholder')" />
      </label>
      <label>
        <span>{{ t('schedule.filterConfig') }}</span>
        <select v-model="filterConfig">
          <option value="">{{ t('schedule.allConfigs') }}</option>
          <option v-for="config in store.CONFIG_ORDER" :key="config" :value="config">{{ config }}</option>
        </select>
      </label>
      <button class="clear-btn" @click="clearFilters">{{ t('schedule.clear') }}</button>
    </section>

    <LoadingState v-if="loading" />
    <div v-else-if="!scheduleLanes.length" class="card empty-state">{{ t('common.noData') }}</div>

    <ScheduleTimeline
      v-else
      :groups="groupedRows"
      :date-columns="dateColumns"
      :config-colors="store.configColors"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import LoadingState from '@/components/LoadingState.vue'
import ScheduleTimeline from '@/components/ScheduleTimeline.vue'
import { useI18n } from '@/i18n/useI18n'
import { useAppStore } from '@/stores/app'
import { buildScheduleDateColumns, buildScheduleLanes, buildScheduleRows, groupScheduleByWf } from '@/views/scheduleDisplay'

const store = useAppStore()
const { t } = useI18n()
const loading = ref(false)
const filterWf = ref('')
const filterConfig = ref('')

const rows = computed(() => buildScheduleRows(store.scheduleData?.segments || [], 5))

const filteredRows = computed(() => rows.value.filter((row) => {
  const wfOk = !filterWf.value || String(row.wf_num).includes(filterWf.value.trim())
  const configOk = !filterConfig.value || row.config === filterConfig.value
  return wfOk && configOk
}))

const scheduleLanes = computed(() => buildScheduleLanes(filteredRows.value))
const groupedRows = computed(() => groupScheduleByWf(scheduleLanes.value))
const dateColumns = computed(() => buildScheduleDateColumns(scheduleLanes.value))

const visibleCpCount = computed(() => scheduleLanes.value.reduce((sum, row) => sum + row.visible_cps.length, 0))

const dateRangeLabel = computed(() => {
  if (!scheduleLanes.value.length) return '—'
  const starts = scheduleLanes.value.map((row) => row.planned_start_date).sort()
  const ends = scheduleLanes.value.map((row) => row.planned_end_date).sort()
  return `${starts[0]} → ${ends[ends.length - 1]}`
})

function clearFilters() {
  filterWf.value = ''
  filterConfig.value = ''
}

async function loadData() {
  loading.value = true
  try {
    await Promise.all([
      store.fetchOverview(),
      store.fetchSchedule()
    ])
  } catch (e) {
    store.error = e.message || 'Failed to load schedule'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.schedule-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}

.refresh-btn,
.clear-btn {
  height: 34px;
  padding: 0 14px;
  border: 1px solid var(--accent-steel);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--accent-steel);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.refresh-btn:hover,
.clear-btn:hover {
  background: var(--accent-steel);
  color: #fff;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 14px 16px;
  display: grid;
  gap: 4px;
}

.metric-label {
  color: var(--text-muted);
  font-size: 12px;
}

.metric-card strong {
  font-size: 20px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.filter-card {
  padding: 14px;
  display: flex;
  align-items: end;
  gap: 12px;
}

.filter-card label {
  display: grid;
  gap: 6px;
  min-width: 180px;
  color: var(--text-muted);
  font-size: 12px;
}

.filter-card input,
.filter-card select {
  height: 34px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  padding: 0 10px;
  font-family: var(--font-display);
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
}

@media (max-width: 1100px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

}

@media (max-width: 720px) {
  .page-heading,
  .filter-card {
    flex-direction: column;
    align-items: stretch;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .filter-card label {
    min-width: 0;
  }
}
</style>
