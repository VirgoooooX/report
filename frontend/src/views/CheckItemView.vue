<template>
  <div class="page-container checkitem-page">
    <header class="page-heading">
      <div>
        <h1 class="page-title">{{ t('checkitem.title') }}</h1>
        <p class="page-subtitle">{{ t('checkitem.subtitle') }}</p>
      </div>
    </header>

    <!-- Section 1: Base Data Configuration -->
    <section class="section">
      <div class="card section-card">
        <div class="section-header">
          <h2 class="section-title">{{ t('checkitem.baseDataTitle') }}</h2>
          <p class="section-desc">{{ t('checkitem.baseDataDesc') }}</p>
        </div>
        <div class="base-file-grid">
          <div
            v-for="ft in fileTypes"
            :key="ft.key"
            class="base-file-item"
          >
            <div class="base-file-info">
              <span class="base-file-label">{{ ft.label }}</span>
              <span
                v-if="getFileStatus(ft.key)"
                class="base-file-status status-uploaded"
              >
                ✅ {{ t('checkitem.uploaded') }} {{ formatDate(getFileStatus(ft.key).uploaded_at) }}
              </span>
              <span v-else class="base-file-status status-pending">
                ⚠️ {{ t('checkitem.notUploaded') }}
              </span>
            </div>
            <div v-if="getFileStatus(ft.key)" class="base-file-stats">
              {{ formatStats(ft.key, getFileStatus(ft.key).parsed_summary) }}
            </div>
            <div v-else class="base-file-upload-prompt">
              {{ ft.uploadHint }}
            </div>
            <div class="base-file-actions">
              <button
                class="btn-replace"
                :disabled="uploading === ft.key"
                @click="triggerUpload(ft.key)"
              >
                {{ uploading === ft.key ? '...' : t('checkitem.replace') }}
              </button>
              <input
                :ref="el => setFileInputRef(ft.key, el)"
                type="file"
                :accept="ft.accept"
                style="display: none"
                @change="handleFileChange($event, ft.key)"
              >
            </div>
          </div>
        </div>
        <div v-if="uploadError" class="base-file-error">
          {{ uploadError }}
        </div>
      </div>
    </section>

    <!-- Section 2: Generate Daily Report from CSV -->
    <section class="section">
      <div class="card section-card">
        <div class="section-header">
          <h2 class="section-title">{{ t('checkitem.generateTitle') }}</h2>
          <p class="section-desc">{{ t('checkitem.generateDesc') }}</p>
        </div>
        <div
          class="upload-drop-zone"
          :class="{ 'drop-zone-active': isDragOver }"
          @dragover.prevent="onDragOver"
          @dragleave.prevent="onDragLeave"
          @drop.prevent="onDrop"
          @click="triggerCsvSelect"
        >
          <div class="drop-zone-content">
            <span class="drop-zone-icon">📂</span>
            <p class="drop-zone-text">
              {{ isDragOver ? t('checkitem.dropActive') : t('checkitem.dropZoneText') }}
            </p>
            <p class="drop-zone-hint">{{ t('checkitem.dropZoneHint') }}</p>
          </div>
          <input
            ref="csvFileInput"
            type="file"
            accept=".csv"
            multiple
            style="display: none"
            @change="onCsvFileSelect"
          >
        </div>

        <!-- File list -->
        <div v-if="csvFiles.length > 0" class="csv-file-list">
          <div class="csv-file-list-header">
            <span class="csv-file-count">{{ t('checkitem.csvFileCount', { count: csvFiles.length }) }}</span>
          </div>
          <div
            v-for="(file, idx) in csvFiles"
            :key="idx"
            class="csv-file-item"
          >
            <div class="csv-file-info">
              <span class="csv-file-name">{{ file.name }}</span>
              <span
                v-if="file.itemType"
                class="csv-type-badge"
                :class="'badge-' + file.itemType.toLowerCase().replace(/[^a-z]/g, '')"
              >{{ file.itemType }}</span>
              <span v-else class="csv-type-badge badge-unknown">{{ t('checkitem.unknownType') }}</span>
            </div>
            <button class="btn-remove" @click.stop="removeCsvFile(idx)">{{ t('checkitem.removeFile') }}</button>
          </div>
        </div>

        <!-- Error display -->
        <div v-if="generateError" class="generate-error">
          {{ generateError }}
        </div>

        <div class="generate-actions">
          <button
            class="btn-primary"
            :disabled="csvFiles.length === 0 || generating"
            @click="handleGenerate"
          >
            {{ generating ? t('checkitem.generating') : t('checkitem.generateBtn') }}
          </button>
        </div>
      </div>
    </section>

    <!-- Section 3: Upload Corrected Report -->
    <section class="section">
      <div class="card section-card">
        <div class="section-header">
          <h2 class="section-title">{{ t('checkitem.uploadCorrectedTitle') }}</h2>
          <p class="section-desc">{{ t('checkitem.uploadCorrectedDesc') }}</p>
        </div>
        <div class="placeholder-content">
          <p class="placeholder-text">{{ t('checkitem.uploadCorrectedPlaceholder') }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from '@/i18n/useI18n'
import { identifyCsvType, formatStats, formatDate } from './CheckItemDisplay.js'

const { t } = useI18n()

// --- State ---
const baseFiles = ref([])
const loading = ref(false)
const uploading = ref(null) // which file_type is currently uploading
const uploadError = ref(null)

// CSV Upload state
const csvFiles = ref([])
const isDragOver = ref(false)
const generating = ref(false)
const generateError = ref(null)
const csvFileInput = ref(null)

// File input refs stored by key
const fileInputRefs = {}
function setFileInputRef(key, el) {
  if (el) fileInputRefs[key] = el
}

// --- File type definitions ---
const fileTypes = [
  {
    key: 'sn_mapping',
    label: t('checkitem.snMapping'),
    accept: '.csv',
    uploadHint: 'Upload SN mapping CSV to get started'
  },
  {
    key: 'checkpoint_schedule',
    label: t('checkitem.cpSchedule'),
    accept: '.csv',
    uploadHint: 'Upload Checkpoint Schedule CSV'
  },
  {
    key: 'test_plan',
    label: t('checkitem.testPlan'),
    accept: '.csv',
    uploadHint: 'Upload Test Plan CSV'
  },
  {
    key: 'test_schedule',
    label: t('checkitem.testSchedule'),
    accept: '.xlsx,.xls',
    uploadHint: 'Upload Test Schedule Excel'
  }
]

// identifyCsvType imported from CheckItemDisplay.js

// --- Drag and drop handlers ---
function onDragOver() {
  isDragOver.value = true
}

function onDragLeave() {
  isDragOver.value = false
}

function onDrop(event) {
  isDragOver.value = false
  const files = event.dataTransfer?.files
  if (files) {
    addCsvFiles(files)
  }
}

function triggerCsvSelect() {
  if (csvFileInput.value) {
    csvFileInput.value.value = ''
    csvFileInput.value.click()
  }
}

function onCsvFileSelect(event) {
  const files = event.target.files
  if (files) {
    addCsvFiles(files)
  }
}

function addCsvFiles(fileList) {
  generateError.value = null
  for (const file of fileList) {
    if (!file.name.toLowerCase().endsWith('.csv')) continue
    // Avoid duplicates by name
    if (csvFiles.value.some(f => f.name === file.name)) continue
    csvFiles.value.push({
      file,
      name: file.name,
      itemType: identifyCsvType(file.name)
    })
  }
}

function removeCsvFile(index) {
  csvFiles.value.splice(index, 1)
}

// --- Generate & Download ---
async function handleGenerate() {
  if (csvFiles.value.length === 0) return

  generating.value = true
  generateError.value = null

  try {
    const formData = new FormData()
    for (const entry of csvFiles.value) {
      formData.append('files', entry.file)
    }

    const resp = await fetch('/api/checkitem/generate', {
      method: 'POST',
      body: formData
    })

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.error || `HTTP ${resp.status}`)
    }

    // Extract filename from Content-Disposition header
    const disposition = resp.headers.get('Content-Disposition') || ''
    let filename = 'Daily_Report.xlsx'
    const match = disposition.match(/filename[^;=\n]*=["']?([^"';\n]+)/)
    if (match && match[1]) {
      filename = decodeURIComponent(match[1])
    }

    // Trigger browser download
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)

    // Clear files after successful generation
    csvFiles.value = []
  } catch (e) {
    generateError.value = e.message
  } finally {
    generating.value = false
  }
}

// --- Helpers ---
function getFileStatus(fileType) {
  return baseFiles.value.find(f => f.file_type === fileType) || null
}

// formatDate and formatStats imported from CheckItemDisplay.js

// --- API calls ---
async function fetchBaseFiles() {
  loading.value = true
  try {
    const resp = await fetch('/api/base-files')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    baseFiles.value = data.files || []
  } catch (e) {
    console.error('Failed to fetch base files:', e)
  } finally {
    loading.value = false
  }
}

function triggerUpload(fileType) {
  uploadError.value = null
  const input = fileInputRefs[fileType]
  if (input) {
    input.value = ''
    input.click()
  }
}

async function handleFileChange(event, fileType) {
  const file = event.target.files?.[0]
  if (!file) return

  uploading.value = fileType
  uploadError.value = null

  try {
    const formData = new FormData()
    formData.append('files', file)
    formData.append('file_type', fileType)

    const resp = await fetch('/api/base-files', {
      method: 'POST',
      body: formData
    })

    const data = await resp.json()
    if (!resp.ok) {
      throw new Error(data.error || `Upload failed (HTTP ${resp.status})`)
    }

    // Refresh the file list
    await fetchBaseFiles()
  } catch (e) {
    uploadError.value = e.message
  } finally {
    uploading.value = null
  }
}

// --- Lifecycle ---
onMounted(() => {
  fetchBaseFiles()
})
</script>

<style scoped>
.checkitem-page {
  display: flex;
  flex-direction: column;
}

.page-heading {
  margin-bottom: 24px;
}

.section {
  margin-bottom: 24px;
}

.section-card {
  padding: 24px;
}

.section-header {
  margin-bottom: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.section-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

/* Base file grid */
.base-file-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.base-file-item {
  padding: 16px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg-row-stripe);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.base-file-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.base-file-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.base-file-status {
  font-size: 12px;
  font-weight: 500;
}

.status-pending {
  color: var(--text-muted);
}

.status-uploaded {
  color: var(--color-success);
}

.base-file-stats {
  font-size: 12px;
  color: var(--text-secondary, var(--text-muted));
}

.base-file-upload-prompt {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

.base-file-actions {
  margin-top: 4px;
}

.btn-replace {
  padding: 4px 12px;
  font-size: 12px;
  font-family: var(--font-display);
  font-weight: 500;
  color: var(--accent-steel);
  background: transparent;
  border: 1px solid var(--accent-steel);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out),
              color var(--duration-fast) var(--ease-in-out);
}

.btn-replace:hover:not(:disabled) {
  background: var(--accent-steel);
  color: #fff;
}

.btn-replace:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.base-file-error {
  margin-top: 12px;
  padding: 8px 12px;
  font-size: 12px;
  color: #d32f2f;
  background: #fdecea;
  border-radius: var(--radius-sm);
}

/* Upload drop zone */
.upload-drop-zone {
  border: 2px dashed var(--border-light);
  border-radius: var(--radius-sm);
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-in-out),
              background var(--duration-fast) var(--ease-in-out);
}

.upload-drop-zone:hover {
  border-color: var(--accent-steel);
  background: var(--bg-row-hover);
}

.upload-drop-zone.drop-zone-active {
  border-color: var(--accent-steel);
  background: var(--bg-row-hover);
  border-style: solid;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.drop-zone-icon {
  font-size: 32px;
}

.drop-zone-text {
  font-size: 14px;
  color: var(--text-primary);
  margin: 0;
}

.drop-zone-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

/* CSV file list */
.csv-file-list {
  margin-top: 16px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.csv-file-list-header {
  padding: 8px 12px;
  background: var(--bg-row-stripe);
  border-bottom: 1px solid var(--border-light);
}

.csv-file-count {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
}

.csv-file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
}

.csv-file-item:last-child {
  border-bottom: none;
}

.csv-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.csv-file-name {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.csv-type-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.badge-btota {
  background: #e3f2fd;
  color: #1565c0;
}

.badge-charging {
  background: #fff3e0;
  color: #e65100;
}

.badge-fact {
  background: #e8f5e9;
  color: #2e7d32;
}

.badge-isb {
  background: #f3e5f5;
  color: #6a1b9a;
}

.badge-touchcalpost {
  background: #e0f7fa;
  color: #00695c;
}

.badge-cosmetic {
  background: #fce4ec;
  color: #c62828;
}

.badge-unknown {
  background: var(--bg-row-stripe);
  color: var(--text-muted);
}

.btn-remove {
  padding: 2px 8px;
  font-size: 11px;
  font-family: var(--font-display);
  color: var(--text-muted);
  background: transparent;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-in-out),
              border-color var(--duration-fast) var(--ease-in-out);
}

.btn-remove:hover {
  color: #d32f2f;
  border-color: #d32f2f;
}

/* Generate error */
.generate-error {
  margin-top: 12px;
  padding: 8px 12px;
  font-size: 12px;
  color: #d32f2f;
  background: #fdecea;
  border-radius: var(--radius-sm);
}

/* Generate actions */
.generate-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  padding: 8px 20px;
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 500;
  color: #fff;
  background: var(--accent-steel);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-in-out);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Placeholder content */
.placeholder-content {
  padding: 24px;
  text-align: center;
}

.placeholder-text {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

@media (max-width: 700px) {
  .base-file-grid {
    grid-template-columns: 1fr;
  }
}
</style>
