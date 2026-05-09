<template>
  <div class="category-grid">
    <div
      v-for="cat in categories"
      :key="cat.name"
      class="card cat-card"
      :style="{ borderLeft: `4px solid var(${cat.colorVar})` }"
      @click="emit('category-click', cat.name)"
    >
      <div class="cat-name" :style="{ color: `var(${cat.colorVar})` }">{{ cat.name }}</div>
      <div class="progress-track">
        <div
          class="progress-fill"
          :style="{ width: cat.pct + '%', background: `var(${cat.colorVar})` }"
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
  { name: 'Drop', colorVar: '--cat-drop' },
  { name: 'Ingress', colorVar: '--cat-ingress' },
  { name: 'Environmental', colorVar: '--cat-environmental' },
  { name: 'Mechanical', colorVar: '--cat-mechanical' }
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
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.cat-card {
  padding: 18px 20px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-left: 4px solid;
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--duration-fast) var(--ease-in-out);
}

.cat-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.cat-name {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
}

.progress-track {
  height: 8px;
  background: var(--bg-progress-track);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out);
}

.cat-stats {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
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
}
</style>
