<template>
  <Teleport to="body">
    <div v-if="visible" class="upload-overlay" @click.self="$emit('close')">
      <div class="upload-dialog">
        <div class="upload-header">
          <h2>{{ t('upload.title') }}</h2>
        </div>

        <div class="upload-field">
          <label class="upload-label">
            {{ t('upload.dailyReport') }}
            <span class="upload-req">* {{ t('upload.dailyReportRequired') }}</span>
          </label>
          <div
            class="upload-zone"
            :class="{ 'has-file': dailyFile, 'drag-over': dailyDragOver }"
            @click="dailyInput?.click()"
            @dragover.prevent="dailyDragOver = true"
            @dragleave.prevent="dailyDragOver = false"
            @drop.prevent="onDropDaily"
          >
            <input ref="dailyInput" type="file" accept=".xlsx" class="upload-hidden" @change="onDailyChange" />
            <span v-if="dailyFile" class="upload-fname">{{ dailyFile.name }}</span>
            <span v-else class="upload-hint">{{ t('upload.dailyReportHint') }}</span>
          </div>
        </div>

        <div class="upload-field">
          <label class="upload-label">
            {{ t('upload.faTracker') }}
            <span class="upload-opt">{{ t('upload.faTrackerOptional') }}</span>
          </label>
          <div
            class="upload-zone"
            :class="{ 'has-file': faFile, 'drag-over': faDragOver }"
            @click="faInput?.click()"
            @dragover.prevent="faDragOver = true"
            @dragleave.prevent="faDragOver = false"
            @drop.prevent="onDropFa"
          >
            <input ref="faInput" type="file" accept=".xlsx" class="upload-hidden" @change="onFaChange" />
            <span v-if="faFile" class="upload-fname">{{ faFile.name }}</span>
            <span v-else class="upload-hint">{{ t('upload.faTrackerHint') }}</span>
          </div>
        </div>

        <div class="upload-actions">
          <button class="btn-cancel" @click="$emit('close')">{{ t('upload.cancel') }}</button>
          <button class="btn-confirm" :disabled="!dailyFile" @click="onConfirm">
            {{ t('upload.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

defineProps({ visible: Boolean })
const emit = defineEmits(['close', 'done'])

const dailyInput = ref(null)
const faInput = ref(null)
const dailyFile = ref(null)
const faFile = ref(null)
const dailyDragOver = ref(false)
const faDragOver = ref(false)

function onDailyChange(e) { dailyFile.value = e.target.files[0] || null }
function onFaChange(e) { faFile.value = e.target.files[0] || null }

function onDropDaily(e) {
  dailyDragOver.value = false
  const f = e.dataTransfer.files[0]
  if (f && f.name.endsWith('.xlsx')) dailyFile.value = f
}

function onDropFa(e) {
  faDragOver.value = false
  const f = e.dataTransfer.files[0]
  if (f && f.name.endsWith('.xlsx')) faFile.value = f
}

function onConfirm() {
  if (!dailyFile.value) return
  const fd = new FormData()
  fd.append('daily_report', dailyFile.value)
  if (faFile.value) fd.append('fa_tracker', faFile.value)
  emit('done', fd)
  dailyFile.value = null
  faFile.value = null
}
</script>

<style scoped>
.upload-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
}
.upload-dialog {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-modal);
  width: 480px; max-width: 90vw;
  padding: 24px;
}
.upload-header h2 {
  margin: 0 0 20px 0; font-size: 1.1rem; font-weight: 600;
  color: var(--text-primary);
}
.upload-field { margin-bottom: 16px; }
.upload-label {
  display: block; font-size: 0.85rem; font-weight: 500;
  color: var(--text-secondary); margin-bottom: 6px;
}
.upload-req { color: #e53e3e; font-size: 0.75rem; font-weight: 400; }
.upload-opt { color: var(--text-muted); font-size: 0.75rem; font-weight: 400; }
.upload-zone {
  border: 2px dashed var(--border-input);
  border-radius: var(--radius-md); padding: 20px;
  text-align: center; cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.upload-zone:hover, .upload-zone.drag-over {
  border-color: var(--text-primary); background: var(--bg-row-hover);
}
.upload-zone.has-file { border-color: #059669; background: rgba(5,150,105,0.06); }
.upload-hidden { display: none; }
.upload-fname {
  font-size: 0.9rem; color: var(--text-primary);
  font-family: 'Source Code Pro', monospace;
}
.upload-hint { font-size: 0.85rem; color: var(--text-muted); }
.upload-actions {
  display: flex; gap: 10px; justify-content: flex-end; margin-top: 24px;
}
.btn-cancel, .btn-confirm {
  padding: 8px 20px; border-radius: var(--radius-sm);
  font-size: 0.85rem; font-weight: 500; cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}
.btn-cancel {
  border: 1px solid var(--border-input);
  background: var(--bg-card); color: var(--text-primary);
}
.btn-cancel:hover { background: var(--bg-row-hover); }
.btn-confirm {
  background: var(--text-primary); color: var(--text-inverse);
  border: 1px solid var(--text-primary);
}
.btn-confirm:hover { opacity: 0.85; }
.btn-confirm:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
