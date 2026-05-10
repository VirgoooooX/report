<template>
  <div class="daily-kpi-grid">
    <div
      v-for="item in items"
      :key="item.key"
      class="card daily-kpi-card"
      :class="'tone-' + item.tone"
    >
      <div class="kpi-label">{{ t(item.labelKey) }}</div>
      <div class="kpi-value">{{ item.value }}</div>
      <div class="kpi-sub">{{ t(item.sublabelKey) }}</div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from '@/i18n/useI18n'

defineProps({
  items: { type: Array, default: () => [] }
})

const { t } = useI18n()
</script>

<style scoped>
.daily-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.daily-kpi-card {
  min-height: 118px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  border-left: 4px solid var(--accent-steel);
}

.kpi-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
}

.kpi-value {
  font-family: var(--font-display);
  font-size: 34px;
  line-height: 1;
  font-weight: 800;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.kpi-sub {
  font-size: 12px;
  color: var(--text-secondary);
}

.tone-success { border-left-color: var(--color-success); }
.tone-warning { border-left-color: var(--color-warning); }
.tone-danger { border-left-color: var(--color-danger); }
.tone-info { border-left-color: var(--color-info); }

@media (max-width: 1000px) {
  .daily-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .daily-kpi-grid {
    grid-template-columns: 1fr;
  }
}
</style>
