<template>
  <div class="conic-ring" :style="`--size:${size}px;--p:${displayPct}`">
    <div class="conic-ring-inner">
      <span class="conic-ring-value">{{ displayPct.toFixed(1) }}%</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  pct: { type: Number, default: 0 },
  size: { type: Number, default: 80 }
})

const displayPct = ref(0)

onMounted(() => {
  setTimeout(() => {
    displayPct.value = props.pct
  }, 50)
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
    var(--accent-steel) calc(var(--p) * 3.6deg),
    var(--bg-progress-track) 0deg
  );
  transition: --p 1.2s var(--ease-out);
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
