<template>
  <div class="category-grid">
    <div
      v-for="cat in categories"
      :key="cat.name"
      class="card cat-card card-clickable"
      @click="emit('category-click', cat.name)"
    >
      <div class="cat-name" :style="{ color: `var(${cat.colorVar})` }">{{ cat.name }}</div>
      <div
        class="progress-track"
        :style="{ background: `var(${cat.trackVar})` }"
      >
        <div
          class="progress-fill"
          :class="{ 'is-active': cat.pct > 0 && cat.pct < 100 }"
          :style="{
            width: cat.pct + '%',
            background: `linear-gradient(90deg, var(${cat.startVar}), var(${cat.endVar}))`
          }"
        ></div>
      </div>
      <div class="cat-stats">
        <span class="cat-pct">{{ cat.pct }}%</span>
        <span class="cat-cps">{{ cat.completed }} / {{ cat.total }} CPs</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const emit = defineEmits(['category-click'])

const CATEGORY_META = [
  {
    name: 'Drop',
    colorVar: '--cat-drop',
    startVar: '--cat-drop-start',
    endVar: '--cat-drop-end',
    trackVar: '--cat-drop-track'
  },
  {
    name: 'Ingress',
    colorVar: '--cat-ingress',
    startVar: '--cat-ingress-start',
    endVar: '--cat-ingress-end',
    trackVar: '--cat-ingress-track'
  },
  {
    name: 'Environmental',
    colorVar: '--cat-environmental',
    startVar: '--cat-environmental-start',
    endVar: '--cat-environmental-end',
    trackVar: '--cat-environmental-track'
  },
  {
    name: 'Mechanical',
    colorVar: '--cat-mechanical',
    startVar: '--cat-mechanical-start',
    endVar: '--cat-mechanical-end',
    trackVar: '--cat-mechanical-track'
  }
]

const categories = computed(() => {
  const byCat = store.overviewData?.completion?.by_category ?? {}
  return CATEGORY_META.map(meta => {
    const data = byCat[meta.name] ?? {}
    const total = data.total_cps ?? 0
    const completed = data.completed_cps ?? 0
    const pct = total > 0 ? Math.round((completed / total) * 1000) / 10 : 0
    return { ...meta, total, completed, pct }
  })
})
</script>

<style scoped>
.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.cat-card {
  min-width: 0;
  padding: 18px 20px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cat-name {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.progress-track {
  height: 8px;
  background: var(--bg-progress-track);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  position: relative;
  height: 100%;
  border-radius: var(--radius-full);
  overflow: hidden;
  transition: width var(--duration-slow) var(--ease-out);
}

.progress-fill.is-active::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: linear-gradient(
    120deg,
    transparent 0,
    transparent 42%,
    rgba(255,255,255,0.22) 50%,
    transparent 58%,
    transparent 100%
  );
  background-size: 32px 100%;
  animation: progress-sheen 2.8s linear infinite;
  opacity: 0.55;
}

@keyframes progress-sheen {
  from { background-position: -32px 0; }
  to { background-position: 32px 0; }
}

@media (prefers-reduced-motion: reduce) {
  .progress-fill.is-active::after {
    animation: none;
  }
}

.cat-stats {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.cat-pct {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.cat-cps {
  font-family: var(--font-display);
  font-size: 12px;
  color: var(--text-muted);
  overflow-wrap: anywhere;
}
</style>
