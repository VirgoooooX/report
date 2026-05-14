<template>
  <div class="schedule-page">
    <header class="page-heading">
      <div class="header-tools">
        <section class="compact-filter">
          <input
            v-model="filterWf"
            class="wf-filter"
            :aria-label="t('schedule.filterWf')"
            :placeholder="t('schedule.filterWfPlaceholder')"
          />
          <select v-model="filterConfig" class="config-filter" :aria-label="t('schedule.filterConfig')">
              <option value="">{{ t('schedule.allConfigs') }}</option>
              <option v-for="config in store.CONFIG_ORDER" :key="config" :value="config">{{ config }}</option>
          </select>
          <button class="clear-btn" @click="clearFilters">{{ t('schedule.clear') }}</button>
        </section>
      </div>
    </header>

    <LoadingState v-if="loading && !store.scheduleData" />
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
import { computed, onMounted, ref, watch } from 'vue'
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

function clearFilters() {
  filterWf.value = ''
  filterConfig.value = ''
}

async function loadData(force = false) {
  if (!force && store.scheduleData) return
  loading.value = true
  try {
    await Promise.all([
      store.fetchOverview(force),
      store.fetchSchedule(force)
    ])
  } catch (e) {
    store.error = e.message || t('common.error')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

watch(() => store.refreshCounter, () => { loadData(true) })
</script>

<style scoped>
:global(html:has(.schedule-page)) {
  overflow: hidden;
  scrollbar-gutter: auto;
}

:global(body:has(.schedule-page)) {
  overflow: hidden;
  height: 100vh;
}

:global(.main:has(.schedule-page)) {
  width: 100%;
  height: calc(100vh - 56px);
  max-width: none;
  padding: 4px 5px 8px;
  overflow: hidden;
}

.schedule-page {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.page-heading {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex: 0 0 auto;
  height: 31px;
}

.header-tools {
  display: flex;
  align-items: center;
  min-width: 0;
}

.compact-filter {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.compact-filter input,
.compact-filter select {
  width: 118px;
  height: 27px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  padding: 0 8px;
  font-family: var(--font-display);
  font-size: 12px;
}

.compact-filter select {
  width: 132px;
}

.clear-btn {
  height: 27px;
  padding: 0 10px;
  border: 1px solid var(--accent-steel);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent-steel);
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.clear-btn:hover {
  background: var(--accent-steel);
  color: #fff;
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
  .header-tools,
  .compact-filter {
    flex-direction: column;
    align-items: stretch;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .compact-filter input,
  .compact-filter select {
    width: 100%;
  }
}
</style>
