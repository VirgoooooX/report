<template>
  <div class="overview-grid">
    <!-- Overall card -->
    <div class="card overall-card" :style="{ '--overall-progress': `${clampedOverallPct}%` }">
      <div class="overall-card-fill" aria-hidden="true"></div>
      <div class="overall-summary">
        <div class="overall-kicker">Overall Completion</div>
        <div class="overall-value">{{ overallPct.toFixed(1) }}%</div>
        <div class="overall-sublabel">{{ completed }}/{{ total }} CPs completed</div>
      </div>

      <div class="overall-breakdown">
        <div class="overall-metric">
          <span class="metric-label">Completed</span>
          <span class="metric-value">{{ completed }}</span>
        </div>
        <div class="overall-metric">
          <span class="metric-label">Remaining</span>
          <span class="metric-value">{{ remaining }}</span>
        </div>
      </div>
    </div>
    <!-- Config cards -->
    <div
      v-for="(cfg, idx) in configs"
      :key="cfg.key"
      class="card config-card"
      :style="{ '--cfg-color': cfg.color }"
    >
      <div class="config-ring-wrap">
        <RingProgress
          :pct="cfg.pct"
          :color="cfg.color"
          label=""
          sublabel=""
          size="small"
        />
      </div>
      <div class="config-meta">
        <div class="config-label">{{ cfg.key }}</div>
        <div class="config-sublabel">{{ cfg.sublabel }} CPs</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import RingProgress from '@/components/RingProgress.vue'

const props = defineProps({
  overviewData: { type: Object, default: () => ({}) }
})

const byConfig = computed(() => props.overviewData?.by_config ?? {})

const fallbackOverall = computed(() => {
  const values = Object.values(byConfig.value)
  const completedCps = values.reduce((s, c) => s + (c.completed_cps || 0), 0)
  const totalCps = values.reduce((s, c) => s + (c.total_cps || 0), 0)
  return {
    completed_cps: completedCps,
    total_cps: totalCps,
    pct: totalCps > 0 ? (completedCps / totalCps) * 100 : 0
  }
})

const overall = computed(() => props.overviewData?.overall ?? fallbackOverall.value)

const overallPct = computed(() => {
  return overall.value?.pct ?? 0
})
const clampedOverallPct = computed(() => Math.max(0, Math.min(Number(overallPct.value) || 0, 100)))
const completed = computed(() => overall.value?.completed_cps ?? 0)
const total = computed(() => overall.value?.total_cps ?? 0)
const remaining = computed(() => Math.max((total.value || 0) - (completed.value || 0), 0))

const cfgColors = ['var(--chart-r1fnf)', 'var(--chart-r2cnm)', 'var(--chart-r3)', 'var(--chart-r4)']

const configs = computed(() => {
  const raw = byConfig.value
  return ['R1FNF', 'R2CNM', 'R3', 'R4'].map((key, idx) => ({
    key,
    pct: raw[key]?.pct ?? 0,
    color: cfgColors[idx] ?? 'var(--accent-steel)',
    sublabel: `${raw[key]?.completed_cps ?? 0}/${raw[key]?.total_cps ?? 0}`
  }))
})
</script>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: minmax(520px, 2.6fr) repeat(4, minmax(140px, 1fr));
  gap: 16px;
}

.overall-card {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(170px, 0.5fr);
  align-items: center;
  gap: 24px;
  min-height: 134px;
  padding: 20px 24px;
  border-color: var(--border-card);
  background: var(--bg-card);
  box-shadow: 0 12px 30px rgba(79, 111, 143, 0.12), var(--shadow-card);
  position: relative;
  overflow: hidden;
}

.overall-card-fill {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--overall-progress);
  min-width: 2px;
  background:
    linear-gradient(90deg,
      color-mix(in srgb, var(--accent-steel) 22%, #fff),
      color-mix(in srgb, var(--chart-r2cnm) 14%, #fff) 82%,
      color-mix(in srgb, var(--chart-r2cnm) 8%, #fff)
    );
  transition: width 0.65s var(--ease-out);
}

.overall-summary,
.overall-breakdown {
  position: relative;
  z-index: 1;
}

.overall-summary {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.overall-kicker {
  width: fit-content;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  background: color-mix(in srgb, var(--accent-steel) 10%, #fff);
  color: var(--accent-steel);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}

.overall-value {
  font-family: var(--font-display);
  font-size: 40px;
  line-height: 1;
  color: var(--text-primary);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.overall-sublabel {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.overall-breakdown {
  display: flex;
  justify-content: flex-end;
  gap: 18px;
}

.overall-metric {
  display: grid;
  gap: 4px;
  min-width: 64px;
}

.metric-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.35px;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 15px;
  font-weight: 800;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.config-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 134px;
  padding: 14px 12px 12px;
  position: relative;
  overflow: hidden;
}

.config-card::before {
  content: none;
}

.config-ring-wrap {
  width: 82px;
  height: 82px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.config-meta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  line-height: 1.2;
}

.config-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}

.config-sublabel {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1100px) {
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .overall-card {
    grid-column: 1 / -1;
    grid-template-columns: minmax(260px, 1fr) minmax(170px, 0.5fr);
  }
}

@media (max-width: 720px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .overall-card {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  .overall-breakdown {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    display: grid;
  }
}
</style>
