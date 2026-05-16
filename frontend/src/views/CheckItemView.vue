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
          <span class="step-badge">1</span>
          <h2 class="section-title">{{ t('checkitem.baseDataTitle') }}</h2>
          <p class="section-desc">{{ t('checkitem.baseDataDesc') }}</p>
        </div>
        <div class="workflow-note" :class="{ ready: baseReadyForGeneration }">
          {{ baseReadyForGeneration ? t('checkitem.baseReadyNote') : t('checkitem.baseMissingNote', { files: missingRequiredLabels.join(', ') }) }}
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
                ⚠️ {{ t('checkitem.notUploaded') }}{{ ft.required ? '' : ` · ${t('checkitem.optional')}` }}
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
        <p v-else class="section-footnote">{{ t('checkitem.baseEffectNote') }}</p>
      </div>
    </section>

    <!-- Section 2: Generate Daily Report from CSV -->
    <section class="section">
      <div class="card section-card">
        <div class="section-header">
          <span class="step-badge">2</span>
          <h2 class="section-title">{{ t('checkitem.generateTitle') }}</h2>
          <p class="section-desc">{{ t('checkitem.generateDesc') }}</p>
        </div>
        <div v-if="!baseReadyForGeneration" class="generate-error">
          {{ t('checkitem.generateBlocked', { files: missingRequiredLabels.join(', ') }) }}
        </div>
        <div
          class="upload-drop-zone"
          :class="{ 'drop-zone-active': isDragOver, disabled: !baseReadyForGeneration }"
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
            :disabled="!baseReadyForGeneration || csvFiles.length === 0 || generating"
            @click="handleGenerate"
          >
            {{ generating ? t('checkitem.generating') : t('checkitem.generateBtn') }}
          </button>
        </div>
        <div v-if="generateStatus" class="success-note">
          {{ generateStatus }}
          <button class="link-btn" @click="store.fetchRawdataSettings()">{{ t('checkitem.refreshRawdata') }}</button>
        </div>
      </div>
    </section>

    <!-- Section 3: Rawdata Management -->
    <section class="section">
      <div class="card section-card">
        <div class="section-header">
          <span class="step-badge">3</span>
          <h2 class="section-title">{{ t('checkitem.importTitle') }}</h2>
          <p class="section-desc">{{ t('checkitem.importDesc') }}</p>
        </div>

        <!-- Parse panel -->
        <div class="rawdata-panel-group">
          <div class="panel parse-panel">
            <div class="panel-title">
              <PlayCircleOutlined />
              <span>{{ t('checkitem.importGeneratedTitle') }}</span>
            </div>
            <div class="inline-upload-card">
              <div class="inline-upload-copy">
                <strong>{{ t('checkitem.uploadDailyReportTitle') }}</strong>
                <span>{{ t('checkitem.uploadDailyReportDesc') }}</span>
              </div>
              <div class="inline-upload-grid">
                <button class="file-pick-card" type="button" @click="triggerDailyReportSelect">
                  <FileExcelOutlined />
                  <span>{{ dailyUploadFile?.name || t('checkitem.chooseDailyReport') }}</span>
                </button>
                <input
                  ref="dailyReportInput"
                  type="file"
                  accept=".xlsx"
                  style="display: none"
                  @change="onDailyReportChange"
                >
                <button class="file-pick-card optional" type="button" @click="triggerFaTrackerSelect">
                  <FileExcelOutlined />
                  <span>{{ faUploadFile?.name || t('checkitem.chooseFaTracker') }}</span>
                </button>
                <input
                  ref="faTrackerInput"
                  type="file"
                  accept=".xlsx"
                  style="display: none"
                  @change="onFaTrackerChange"
                >
              </div>
              <div class="inline-upload-actions">
                <button
                  class="btn-secondary"
                  :disabled="!dailyUploadFile || uploadState === 'uploading'"
                  @click="uploadRawdataFiles"
                >
                  <template v-if="uploadState === 'done'">✓ {{ t('upload.done') }}</template>
                  <template v-else-if="uploadState === 'uploading'">{{ t('upload.uploading') }}</template>
                  <template v-else>{{ t('checkitem.uploadDailyReportBtn') }}</template>
                </button>
                <span class="status-text" :class="{ error: uploadStatusType === 'error' }">{{ uploadStatusText }}</span>
              </div>
            </div>
            <div class="field-grid">
              <label class="field">
                <span>{{ t('settings.dailyReport') }}</span>
                <select v-model="selectedDaily">
                  <option value="">{{ t('settings.selectFile') }}</option>
                  <option v-for="file in dailyFiles" :key="file.path" :value="file.path">
                    {{ file.date || t('settings.noDate') }} · {{ file.name }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span>{{ t('settings.faTracker') }}</span>
                <select v-model="selectedFa">
                  <option value="">{{ t('settings.autoMatch') }}</option>
                  <option v-for="file in faFiles" :key="file.path" :value="file.path">
                    {{ file.date || t('settings.noDate') }} · {{ file.name }}
                  </option>
                </select>
              </label>
            </div>
            <details class="advanced-options">
              <summary>{{ t('checkitem.advancedImportOptions') }}</summary>
              <label class="toggle-switch" :class="{ active: skipValidation }">
                <input type="checkbox" v-model="skipValidation" />
                <span class="toggle-track"><span class="toggle-thumb"></span></span>
                <span class="toggle-label">{{ t('checkitem.skipValidationAdvanced') }}</span>
              </label>
            </details>
            <div class="action-row">
              <button class="btn-primary" :disabled="!selectedDaily || parsing" @click="parseSelected">
                <PlayCircleOutlined />
                <span>{{ parsing ? t('settings.parsing') : t('checkitem.importSelected') }}</span>
              </button>
              <span class="status-text" :class="{ error: rawdataStatusType === 'error' }">{{ rawdataStatusText }}</span>
            </div>
          </div>

          <!-- Rawdata file list -->
          <div class="panel rawdata-panel">
            <div class="panel-title">
              <FileExcelOutlined />
              <span>{{ t('settings.rawdataFiles') }}</span>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>{{ t('settings.kind') }}</th>
                    <th>{{ t('settings.date') }}</th>
                    <th>{{ t('settings.file') }}</th>
                    <th>{{ t('settings.size') }}</th>
                    <th>{{ t('settings.modifiedAt') }}</th>
                    <th>{{ t('settings.actions') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="file in rawdataFiles" :key="file.path">
                    <td><span class="kind-badge" :class="file.kind">{{ kindLabel(file.kind) }}</span></td>
                    <td class="mono">{{ file.date || '-' }}</td>
                    <td class="file-name" :title="file.path">{{ file.name }}</td>
                    <td class="mono">{{ formatSize(file.size) }}</td>
                    <td class="mono">{{ formatDateTime(file.modified_at) }}</td>
                    <td>
                      <div class="row-actions">
                        <button
                          v-if="file.kind === 'daily_report'"
                          class="icon-btn small"
                          :title="t('settings.parseFile')"
                          :aria-label="t('settings.parseFile')"
                          @click="parseFile(file)"
                        >
                          <PlayCircleOutlined />
                        </button>
                        <button class="icon-btn small danger" :title="t('settings.deleteFile')" :aria-label="t('settings.deleteFile')" @click="deleteFile(file)">
                          <DeleteOutlined />
                        </button>
                      </div>
                    </td>
                  </tr>
                  <tr v-if="!rawdataFiles.length">
                    <td colspan="6" class="empty-row">{{ t('settings.noRawdataFiles') }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <label class="purge-toggle">
              <input v-model="purgeDbOnDelete" type="checkbox" />
              <span>{{ t('settings.purgeDb') }}</span>
            </label>
          </div>

          <!-- Imported reports -->
          <div class="panel reports-panel">
            <div class="panel-title">
              <DatabaseOutlined />
              <span>{{ t('settings.importedReports') }}</span>
            </div>
            <div class="report-list">
              <div v-for="report in rawdataReports" :key="report.id" class="report-row">
                <span class="mono">{{ report.report_date }}</span>
                <span>v{{ report.version }}</span>
                <span class="report-file">{{ report.source_file_name }}</span>
                <span class="mono imported-at">{{ formatDateTime(report.imported_at) }}</span>
                <span class="active-pill" :class="{ muted: !report.is_active }">
                  {{ report.is_active ? t('settings.active') : t('settings.history') }}
                </span>
              </div>
              <div v-if="!rawdataReports.length" class="empty-row">{{ t('settings.noImportedReports') }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import {
  DatabaseOutlined,
  DeleteOutlined,
  FileExcelOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons-vue'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'
import {
  identifyCsvType,
  formatStats,
  formatDate,
  getBaseStatusMap,
  getMissingRequiredBaseFiles,
  isBaseReadyForGeneration,
} from './CheckItemDisplay.js'

const { t } = useI18n()
const store = useAppStore()

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
const generateStatus = ref('')
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
    uploadHint: t('checkitem.snMappingHint'),
    required: true
  },
  {
    key: 'checkpoint_schedule',
    label: t('checkitem.cpSchedule'),
    accept: '.csv',
    uploadHint: t('checkitem.cpScheduleHint'),
    required: true
  },
  {
    key: 'test_plan',
    label: t('checkitem.testPlan'),
    accept: '.csv',
    uploadHint: t('checkitem.testPlanHint'),
    required: true
  },
  {
    key: 'test_schedule',
    label: t('checkitem.testSchedule'),
    accept: '.xlsx,.xls',
    uploadHint: t('checkitem.testScheduleHint'),
    required: false
  }
]

const baseStatusMap = computed(() => getBaseStatusMap(baseFiles.value))
const missingRequiredBaseFiles = computed(() => getMissingRequiredBaseFiles(baseFiles.value))
const baseReadyForGeneration = computed(() => isBaseReadyForGeneration(baseFiles.value))
const missingRequiredLabels = computed(() => missingRequiredBaseFiles.value.map((key) => fileTypes.find((ft) => ft.key === key)?.label || key))

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
  if (!baseReadyForGeneration.value) return
  const files = event.dataTransfer?.files
  if (files) {
    addCsvFiles(files)
  }
}

function triggerCsvSelect() {
  if (!baseReadyForGeneration.value) return
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
  generateStatus.value = ''
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
  if (!baseReadyForGeneration.value || csvFiles.value.length === 0) return

  generating.value = true
  generateError.value = null
  generateStatus.value = ''

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
    generateStatus.value = t('checkitem.generateDoneNext')
    await store.fetchRawdataSettings().catch(() => {})
  } catch (e) {
    generateError.value = e.message
  } finally {
    generating.value = false
  }
}

// --- Helpers ---
function getFileStatus(fileType) {
  return baseStatusMap.value[fileType] || null
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
    generateStatus.value = ''
  } catch (e) {
    uploadError.value = e.message
  } finally {
    uploading.value = null
  }
}

// --- Upload Daily Report files into the RawData file list ---
const uploadState = ref('idle')
const uploadStatusText = ref('')
const uploadStatusType = ref('')
const dailyReportInput = ref(null)
const faTrackerInput = ref(null)
const dailyUploadFile = ref(null)
const faUploadFile = ref(null)

function triggerDailyReportSelect() {
  if (dailyReportInput.value) {
    dailyReportInput.value.value = ''
    dailyReportInput.value.click()
  }
}

function triggerFaTrackerSelect() {
  if (faTrackerInput.value) {
    faTrackerInput.value.value = ''
    faTrackerInput.value.click()
  }
}

function onDailyReportChange(event) {
  dailyUploadFile.value = event.target.files?.[0] || null
  uploadStatusText.value = ''
  uploadStatusType.value = ''
}

function onFaTrackerChange(event) {
  faUploadFile.value = event.target.files?.[0] || null
  uploadStatusText.value = ''
  uploadStatusType.value = ''
}

async function uploadRawdataFiles() {
  if (!dailyUploadFile.value) return
  uploadState.value = 'uploading'
  uploadStatusText.value = ''
  uploadStatusType.value = ''
  try {
    const formData = new FormData()
    formData.append('daily_report', dailyUploadFile.value)
    if (faUploadFile.value) formData.append('fa_tracker', faUploadFile.value)
    const result = await store.uploadRawdataFiles(formData)
    uploadState.value = 'done'
    uploadStatusText.value = t('checkitem.uploadDailyReportDone')
    await store.fetchRawdataSettings()
    selectedDaily.value = result.daily_report?.path || selectedDaily.value
    selectedFa.value = result.fa_tracker?.path || selectedFa.value
    dailyUploadFile.value = null
    faUploadFile.value = null
    setTimeout(() => { uploadState.value = 'idle' }, 3000)
  } catch (e) {
    uploadState.value = 'idle'
    uploadStatusType.value = 'error'
    uploadStatusText.value = e.message || t('upload.uploadFailed')
  }
}

// --- Rawdata Management ---
const selectedDaily = ref('')
const selectedFa = ref('')
const purgeDbOnDelete = ref(false)
const parsing = ref(false)
const skipValidation = ref(false)
const rawdataStatusText = ref('')
const rawdataStatusType = ref('')

const rawdataFiles = computed(() => store.settingsRawdata.files || [])
const rawdataReports = computed(() => store.settingsRawdata.reports || [])
const dailyFiles = computed(() => rawdataFiles.value.filter(file => file.kind === 'daily_report'))
const faFiles = computed(() => rawdataFiles.value.filter(file => file.kind === 'fa_tracker'))

function showRawdataStatus(message, type = '') {
  rawdataStatusText.value = message
  rawdataStatusType.value = type
}

async function parseSelected() {
  if (!selectedDaily.value) return
  parsing.value = true
  showRawdataStatus('')
  try {
    const result = await store.parseRawdata(selectedDaily.value, selectedFa.value, { skipValidation: skipValidation.value })
    const warnings = Array.isArray(result.warnings) && result.warnings.length
      ? ` ${t('checkitem.importWarnings', { count: result.warnings.length })}`
      : ''
    showRawdataStatus(t('settings.parseDone', { date: result.report_date, count: result.wf_count }) + warnings)
    store.triggerRefresh()
  } catch (e) {
    showRawdataStatus(e.message || t('settings.parseFailed'), 'error')
  } finally {
    parsing.value = false
  }
}

function parseFile(file) {
  selectedDaily.value = file.path
  const sameDateFa = faFiles.value.find(item => item.date && item.date === file.date)
  selectedFa.value = sameDateFa?.path || ''
  parseSelected()
}

async function deleteFile(file) {
  const suffix = purgeDbOnDelete.value && file.kind === 'daily_report' ? t('settings.deleteConfirmSuffix') : ''
  if (!window.confirm(t('settings.deleteConfirm', { name: file.name, suffix }))) return
  try {
    await store.deleteRawdataFile(file.path, purgeDbOnDelete.value && file.kind === 'daily_report')
    showRawdataStatus(t('settings.deleteDone', { name: file.name }))
    if (selectedDaily.value === file.path) selectedDaily.value = ''
    if (selectedFa.value === file.path) selectedFa.value = ''
  } catch (e) {
    showRawdataStatus(e.message || t('settings.deleteFailed'), 'error')
  }
}

function kindLabel(kind) {
  return kind === 'daily_report' ? t('settings.kindDaily') : kind === 'fa_tracker' ? t('settings.kindFa') : t('settings.kindOther')
}

function formatSize(size) {
  if (!Number.isFinite(size)) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 16)
}

watch(dailyFiles, (next) => {
  if (!selectedDaily.value && next.length) selectedDaily.value = next[0].path
})

// --- Lifecycle ---
onMounted(() => {
  fetchBaseFiles()
  store.fetchRawdataSettings().then(() => {
    if (!selectedDaily.value && dailyFiles.value.length) {
      selectedDaily.value = dailyFiles.value[0].path
    }
  })
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
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.step-badge {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: var(--accent-steel);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.section-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  flex-basis: 100%;
  padding-left: 34px;
}

.workflow-note,
.success-note,
.section-footnote {
  margin: 0 0 16px;
  font-size: 12px;
  color: var(--text-secondary, var(--text-muted));
  background: var(--bg-row-stripe);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.workflow-note.ready,
.success-note {
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 8%, var(--bg-card));
  border-color: color-mix(in srgb, var(--color-success) 25%, var(--border-light));
}

.section-footnote {
  margin: 14px 0 0;
}

.link-btn {
  margin-left: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent-steel);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
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

.upload-drop-zone.disabled,
.upload-drop-zone.disabled:hover {
  opacity: 0.55;
  cursor: not-allowed;
  border-color: var(--border-light);
  background: transparent;
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

.advanced-options {
  margin: 12px 0;
  padding: 10px 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg-row-stripe);
}

.advanced-options summary {
  cursor: pointer;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
}

.advanced-options .toggle-switch {
  margin-top: 10px;
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

/* Rawdata panels */
.rawdata-panel-group {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.panel {
  padding: 18px 20px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  box-shadow: var(--shadow-card);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  color: var(--text-secondary);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
}

.inline-upload-card {
  display: grid;
  gap: 14px;
  margin-bottom: 18px;
  padding: 16px;
  border: 1px solid color-mix(in srgb, var(--accent-steel) 18%, var(--border-light));
  border-radius: var(--radius-md);
  background:
    radial-gradient(circle at 0 0, color-mix(in srgb, var(--accent-steel) 10%, transparent), transparent 34%),
    var(--bg-card);
}

.inline-upload-copy {
  display: grid;
  gap: 4px;
}

.inline-upload-copy strong {
  font-size: 13px;
  color: var(--text-primary);
}

.inline-upload-copy span {
  font-size: 12px;
  color: var(--text-muted);
}

.inline-upload-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.file-pick-card {
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border: 1px dashed color-mix(in srgb, var(--accent-steel) 32%, var(--border-input));
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--accent-steel) 5%, transparent);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}

.file-pick-card:hover {
  border-color: var(--accent-steel);
  background: color-mix(in srgb, var(--accent-steel) 10%, transparent);
  transform: translateY(-1px);
}

.file-pick-card.optional {
  border-color: var(--border-input);
  background: var(--bg-muted);
}

.file-pick-card span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.inline-upload-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.field select {
  width: 100%;
  min-height: 36px;
  padding: 8px 10px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;
}

.field select:focus {
  border-color: var(--border-focus);
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

/* Toggle switch */
.toggle-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.toggle-switch input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-track {
  position: relative;
  width: 36px;
  height: 20px;
  background: var(--border-input, #d9d9d9);
  border-radius: 10px;
  transition: background var(--duration-fast, 0.2s) var(--ease-in-out, ease);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  transition: transform var(--duration-fast, 0.2s) var(--ease-in-out, ease);
}

.toggle-switch.active .toggle-track {
  background: var(--accent-steel, #4a90d9);
}

.toggle-switch.active .toggle-thumb {
  transform: translateX(16px);
}

.toggle-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary, #666);
  transition: color var(--duration-fast, 0.2s) var(--ease-in-out, ease);
}

.toggle-switch.active .toggle-label {
  color: var(--text-primary, #333);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--duration-fast), background var(--duration-fast), color var(--duration-fast);
}

.btn-secondary:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: opacity var(--duration-fast), background var(--duration-fast), color var(--duration-fast);
}

.icon-btn.small {
  width: 30px;
  height: 30px;
  font-size: 12px;
}

.icon-btn.danger {
  color: var(--color-danger);
}

.icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.icon-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.status-text {
  color: var(--text-muted);
  font-size: 13px;
}

.status-text.error {
  color: var(--color-danger);
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  text-align: left;
  vertical-align: middle;
}

th {
  color: var(--text-muted);
  background: var(--bg-row-stripe);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

tr:hover td {
  background: var(--bg-row-hover);
}

.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.file-name,
.report-file {
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kind-badge,
.active-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  height: 24px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 700;
}

.kind-badge.daily_report {
  color: var(--accent-steel);
  background: color-mix(in srgb, var(--accent-steel) 10%, transparent);
}

.kind-badge.fa_tracker {
  color: var(--color-success);
  background: var(--color-success-bg);
}

.kind-badge.other {
  color: var(--text-muted);
  background: var(--bg-tag);
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.purge-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.report-list {
  display: grid;
  gap: 8px;
}

.report-row {
  display: grid;
  grid-template-columns: 110px 52px minmax(0, 1fr) 130px 78px;
  align-items: center;
  gap: 12px;
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
}

.imported-at {
  color: var(--text-muted);
  font-size: 12px;
}

.active-pill {
  color: #fff;
  background: var(--accent-steel);
}

.active-pill.muted {
  color: var(--text-muted);
  background: var(--bg-tag);
}

.empty-row {
  padding: 24px 12px;
  color: var(--text-muted);
  text-align: center;
}

@media (max-width: 700px) {
  .inline-upload-grid {
    grid-template-columns: 1fr;
  }

  .base-file-grid {
    grid-template-columns: 1fr;
  }

  .report-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }
}
</style>
