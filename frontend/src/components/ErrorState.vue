<template>
  <div class="error-placeholder">
    <span class="error-message">{{ message }}</span>
    <button v-if="retry" class="retry-btn" @click="retry">Retry</button>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: 'An error occurred' },
  retry: { type: Function, default: null }
})
</script>

<style scoped>
.error-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
}

.error-message {
  font-family: var(--font-display);
  font-size: 14px;
  color: var(--color-danger);
  text-align: center;
}

.retry-btn {
  padding: 8px 20px;
  background: var(--color-danger);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  font-family: var(--font-display);
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.retry-btn:hover {
  opacity: 0.9;
}
</style>
