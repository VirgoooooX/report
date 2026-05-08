<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fa-overlay"
      @click.self="close"
      @keydown.esc="close"
      tabindex="-1"
    >
      <div class="fa-modal" :class="{ show: visible }">
        <div class="fa-modal-header">
          <h2 class="fa-modal-title">{{ title || 'FA Records' }}</h2>
          <button class="fa-close-btn" @click="close">&times;</button>
        </div>
        <div class="fa-modal-body">
          <!-- Loading -->
          <div v-if="faLoading" class="fa-loading">
            <div class="spinner"></div>
            <span>Loading FA records…</span>
          </div>

          <!-- Error -->
          <div v-else-if="faError" class="fa-error">
            <span class="error-message">{{ faError }}</span>
            <button class="retry-btn" @click="fetchFa">Retry</button>
          </div>

          <!-- Empty -->
          <div v-else-if="faData.length === 0" class="fa-empty">
            <p>No FA records found</p>
            <div v-if="sns.length" class="fa-sns-list">
              <span v-for="sn in sns" :key="sn" class="fa-sn-tag">{{ sn }}</span>
            </div>
          </div>

          <!-- Records -->
          <div v-else class="fa-records">
            <div v-for="(rec, i) in faData" :key="i" class="fa-record-card">
              <div class="fa-record-bar"></div>
              <div class="fa-record-fields">
                <div v-for="(val, key) in rec" :key="key" class="fa-field">
                  <span class="fa-field-label">{{ key }}:</span>
                  <span class="fa-field-value">{{ val }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  show: Boolean,
  wf: String,
  title: String,
  sns: { type: Array, default: () => [] }
})
const emit = defineEmits(['close'])

const faData = ref([])
const faLoading = ref(false)
const faError = ref(null)
const visible = ref(false)

function close() {
  emit('close')
}

async function fetchFa() {
  if (!props.wf) return
  faLoading.value = true
  faError.value = null
  try {
    const r = await fetch(`/api/fa/list?wf=${encodeURIComponent(props.wf)}`)
    if (!r.ok) {
      let msg = `HTTP ${r.status}`
      try { const j = await r.json(); if (j.error) msg = j.error } catch {}
      throw new Error(msg)
    }
    const d = await r.json()
    faData.value = d.records || []
  } catch (e) {
    faError.value = e.message
  } finally {
    faLoading.value = false
  }
}

watch(() => props.show, async (val) => {
  if (val) {
    faData.value = []
    faError.value = null
    await nextTick()
    visible.value = true
    fetchFa()
  } else {
    visible.value = false
  }
})
</script>

<style scoped>
.fa-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 35, 50, 0.4);
  backdrop-filter: blur(2px);
}

.fa-modal {
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--shadow-modal);
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  opacity: 0;
  transform: scale(0.97) translateY(20px);
  transition: opacity 300ms ease-out, transform 300ms ease-out;
}

.fa-modal.show {
  opacity: 1;
  transform: scale(1) translateY(0);
}

.fa-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.fa-modal-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: #1a2332;
  margin: 0;
}

.fa-close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  font-size: 22px;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast) var(--ease-in-out),
              color var(--duration-fast) var(--ease-in-out);
}

.fa-close-btn:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}

.fa-modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

/* Loading */
.fa-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--text-muted);
  font-size: 14px;
  font-family: var(--font-display);
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border-light);
  border-top-color: var(--accent-steel);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error */
.fa-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
}

.error-message {
  font-size: 14px;
  color: var(--color-danger);
  font-family: var(--font-display);
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

/* Empty */
.fa-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  gap: 16px;
}

.fa-empty p {
  font-size: 14px;
  color: var(--text-muted);
  font-family: var(--font-display);
}

.fa-sns-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

.fa-sn-tag {
  display: inline-block;
  padding: 3px 10px;
  background: var(--bg-tag);
  border-radius: var(--radius-full);
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

/* Records */
.fa-records {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fa-record-card {
  display: flex;
  background: #f5f7fa;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.fa-record-bar {
  width: 3px;
  flex-shrink: 0;
  background: #4f6f8f;
}

.fa-record-fields {
  flex: 1;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fa-field {
  display: flex;
  gap: 6px;
  font-size: 13px;
  font-family: var(--font-display);
  line-height: 1.5;
}

.fa-field-label {
  color: var(--text-muted);
  font-weight: 500;
  white-space: nowrap;
  text-transform: capitalize;
}

.fa-field-value {
  color: var(--text-primary);
  word-break: break-word;
}
</style>
