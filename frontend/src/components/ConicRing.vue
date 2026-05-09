<template>
  <div
    class="conic-ring"
    :style="{ '--size': `${size}px`, '--p': displayPct, '--ring-color': color }"
  >
    <div class="conic-ring-inner">
      <span class="conic-ring-value">{{ displayPct.toFixed(1) }}%</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  pct: { type: Number, default: 0 },
  size: { type: Number, default: 80 },
  color: { type: String, default: 'var(--accent-steel)' }
})

const displayPct = ref(0)

watch(() => props.pct, (value) => {
  displayPct.value = Math.max(0, Math.min(Number(value) || 0, 100))
}, {
  immediate: true
})
</script>

<style scoped>
@property --p {
  syntax: '<number>';
  inherits: false;
  initial-value: 0;
}
.conic-ring {
  width: var(--size);
  height: var(--size);
  border-radius: 50%;
  background: conic-gradient(
    var(--ring-color) calc(var(--p) * 3.6deg),
    var(--bg-progress-track) 0deg
  );
  transition: --p 0.7s var(--ease-out);
  display: flex;
  align-items: center;
  justify-content: center;
}
.conic-ring-inner {
  width: calc(var(--size) - 12px);
  height: calc(var(--size) - 12px);
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
}
.conic-ring-value {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: calc(var(--size) * 0.3);
  color: var(--text-primary);
}
</style>
