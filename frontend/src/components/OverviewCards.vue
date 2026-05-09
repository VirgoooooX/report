<template>
  <div class="overview-grid">
    <!-- Overall card -->
    <div class="card overall-card">
      <div class="overall-left">
        <ConicRing :pct="overallPct" :size="80" />
      </div>
      <div class="overall-right">
        <div class="overall-label">Overall Completion</div>
        <div class="overall-sublabel">{{ completed }}/{{ total }} CPs</div>
      </div>
    </div>
    <!-- Config cards -->
    <div
      v-for="(cfg, idx) in configs"
      :key="cfg.key"
      class="card config-card"
    >
      <RingProgress
        :pct="cfg.pct"
        :color="`var(${cfgColorVar(idx)})`"
        :label="cfg.key"
        :sublabel="cfg.sublabel"
        size="small"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ConicRing from '@/components/ConicRing.vue'
import RingProgress from '@/components/RingProgress.vue'

const props = defineProps({
  overviewData: { type: Object, default: () => ({}) }
})

const overallPct = computed(() => {
  if (total.value === 0) return 0
  return (completed.value / total.value) * 100
})
const completed = computed(() => {
  const byCfg = props.overviewData?.by_config ?? {}
  return Object.values(byCfg).reduce((s, c) => s + (c.completed_cps || 0), 0)
})
const total = computed(() => {
  const byCfg = props.overviewData?.by_config ?? {}
  return Object.values(byCfg).reduce((s, c) => s + (c.total_cps || 0), 0)
})

const configs = computed(() => {
  const raw = props.overviewData?.by_config ?? {}
  return ['R1FNF', 'R2CNM', 'R3', 'R4'].map(key => ({
    key,
    pct: raw[key]?.pct ?? 0,
    sublabel: `${raw[key]?.completed ?? 0}/${raw[key]?.total ?? 0}`
  }))
})

const cfgColorVar = (idx) => {
  const vars = ['--chart-r1fnf', '--chart-r2cnm', '--chart-r3', '--chart-r4']
  return vars[idx] ?? '--accent-steel'
}
</script>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr;
  gap: 16px;
}

.overall-card {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 20px 24px;
}

.overall-left {
  flex-shrink: 0;
}

.overall-right {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.overall-label {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.overall-sublabel {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.config-card {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 8px;
}
</style>
