<template>
  <div class="loading-state" :class="`loading-state-${variant}`">
    <template v-if="variant === 'skeleton'">
      <div class="skeleton-line skeleton-line-wide"></div>
      <div class="skeleton-block"></div>
      <div class="skeleton-line"></div>
    </template>
    <template v-else>
      <div class="spinner"></div>
      <span>{{ label }}</span>
    </template>
  </div>
</template>

<script setup>
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

defineProps({
  label: {
    type: String,
    default: 'Loading...'
  },
  variant: {
    type: String,
    default: 'spinner'
  }
})
</script>

<style scoped>
.loading-state {
  min-height: 180px;
  display: grid;
  place-items: center;
  gap: 12px;
  padding: var(--space-xl);
  color: var(--text-muted);
}

.loading-state-skeleton {
  place-items: stretch;
}

.skeleton-line,
.skeleton-block {
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    var(--bg-row-stripe),
    var(--bg-row-hover),
    var(--bg-row-stripe)
  );
  background-size: 180% 100%;
  animation: skeleton-shimmer 1.4s ease-in-out infinite;
}

.skeleton-line {
  width: 46%;
  height: 14px;
}

.skeleton-line-wide {
  width: 68%;
}

.skeleton-block {
  height: 140px;
}

@keyframes skeleton-shimmer {
  from { background-position: 100% 0; }
  to { background-position: -80% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-line,
  .skeleton-block {
    animation: none;
  }
}
</style>
