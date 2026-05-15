<template>
  <div class="page-container settings-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">{{ t('settings.title') }}</h1>
        <p class="page-subtitle">{{ t('settings.subtitle') }}</p>
      </div>
      <button class="icon-btn" :disabled="loading" :title="t('common.refresh')" :aria-label="t('common.refresh')" @click="loadAll">
        <ReloadOutlined />
      </button>
    </div>

    <div class="settings-tabs" role="tablist">
      <button :class="{ active: tab === 'rawdata' }" @click="tab = 'rawdata'">{{ t('settings.tabRawdata') }}</button>
      <button :class="{ active: tab === 'rules' }" @click="tab = 'rules'">{{ t('settings.tabRules') }}</button>
      <button :class="{ active: tab === 'ideas' }" @click="tab = 'ideas'">{{ t('settings.tabIdeas') }}</button>
    </div>

    <section v-if="tab === 'rawdata'" class="settings-grid">
      <div class="panel parse-panel">
        <div class="panel-title">
          <PlayCircleOutlined />
          <span>{{ t('settings.parseSection') }}</span>
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
        <div class="action-row">
          <button class="btn-primary" :disabled="!selectedDaily || parsing" @click="parseSelected">
            <PlayCircleOutlined />
            <span>{{ parsing ? t('settings.parsing') : t('settings.parseSelected') }}</span>
          </button>
          <span class="status-text" :class="{ error: statusType === 'error' }">{{ statusText }}</span>
        </div>
      </div>

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
              <tr v-for="file in files" :key="file.path">
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
              <tr v-if="!files.length">
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

      <div class="panel reports-panel">
        <div class="panel-title">
          <DatabaseOutlined />
          <span>{{ t('settings.importedReports') }}</span>
        </div>
        <div class="report-list">
          <div v-for="report in reports" :key="report.id" class="report-row">
            <span class="mono">{{ report.report_date }}</span>
            <span>v{{ report.version }}</span>
            <span class="report-file">{{ report.source_file_name }}</span>
            <span class="mono imported-at">{{ formatDateTime(report.imported_at) }}</span>
            <span class="active-pill" :class="{ muted: !report.is_active }">
              {{ report.is_active ? t('settings.active') : t('settings.history') }}
            </span>
          </div>
          <div v-if="!reports.length" class="empty-row">{{ t('settings.noImportedReports') }}</div>
        </div>
      </div>
    </section>

    <section v-else-if="tab === 'rules'" class="rules-grid">
      <div class="panel">
        <div class="panel-title">
          <SettingOutlined />
          <span>{{ t('settings.parseRules') }}</span>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>{{ t('settings.specFillColors') }}</span>
            <input v-model="ruleDraft.parse.spec_fill_colors_text" :placeholder="t('settings.specFillColorsPlaceholder')" />
          </label>
          <label class="field">
            <span>{{ t('settings.strifeFillColors') }}</span>
            <input v-model="ruleDraft.parse.strife_fill_colors_text" :placeholder="t('settings.strifeFillColorsPlaceholder')" />
          </label>
          <label class="field">
            <span>{{ t('settings.specFontColors') }}</span>
            <input v-model="ruleDraft.parse.spec_font_colors_text" :placeholder="t('settings.specFontColorsPlaceholder')" />
          </label>
          <label class="field">
            <span>{{ t('settings.ignoreWfs') }}</span>
            <input v-model="ruleDraft.parse.ignore_wfs_text" :placeholder="t('settings.ignoreWfsPlaceholder')" />
          </label>
        </div>
        <label class="field full">
          <span>{{ t('settings.configAliases') }}</span>
          <textarea
            v-model="ruleDraft.parse.config_aliases_text"
            rows="4"
            :placeholder="t('settings.configAliasesPlaceholder')"
          ></textarea>
        </label>
      </div>

      <div class="panel">
        <div class="panel-title">
          <EyeOutlined />
          <span>{{ t('settings.displayRules') }}</span>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>{{ t('settings.projectName') }}</span>
            <input v-model="ruleDraft.display.project_name" :placeholder="t('settings.projectNamePlaceholder')" />
          </label>
          <label class="field">
            <span>{{ t('settings.configOrder') }}</span>
            <input v-model="ruleDraft.display.config_order_text" :placeholder="t('settings.configOrderPlaceholder')" />
          </label>
          <label class="field">
            <span>{{ t('settings.hiddenWfs') }}</span>
            <input v-model="ruleDraft.display.hidden_wfs_text" :placeholder="t('settings.hiddenWfsPlaceholder')" />
          </label>
        </div>
        <label class="field full">
          <span>{{ t('settings.wfAliases') }}</span>
          <textarea
            v-model="ruleDraft.display.wf_aliases_text"
            rows="5"
            :placeholder="t('settings.wfAliasesPlaceholder')"
          ></textarea>
        </label>
      </div>

      <!-- Location Mapping Panel -->
      <div class="panel location-mapping-panel">
        <div class="panel-title">
          <SwapOutlined />
          <span>{{ t('settings.locationMapping') }}</span>
        </div>
        <p class="panel-desc">{{ t('settings.locationMappingDesc') }}</p>
        <div class="mapping-table-wrap">
          <table class="mapping-table">
            <thead>
              <tr>
                <th>{{ t('settings.colDailyReport') }}</th>
                <th>{{ t('settings.colFaTracker') }}</th>
                <th>{{ t('settings.matchMode') }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in ruleDraft.matching.location_mappings" :key="i">
                <td>
                  <input v-model="row.daily_report" :placeholder="t('settings.dailyReportPlaceholder')" class="mapping-input" />
                </td>
                <td>
                  <input v-model="row.fa_tracker" :placeholder="row.mode === 'multi' ? t('settings.faTrackerPlaceholderMulti') : t('settings.faTrackerPlaceholder')" class="mapping-input" />
                </td>
                <td>
                  <select v-model="row.mode" class="mapping-select">
                    <option value="exact">{{ t('settings.exactMatch') }}</option>
                    <option value="contains">{{ t('settings.containsMatch') }}</option>
                    <option value="multi">{{ t('settings.multiMatch') }}</option>
                  </select>
                </td>
                <td>
                  <button class="icon-btn small danger" :title="t('settings.deleteMapping')" @click="removeMapping(i)">
                    <DeleteOutlined />
                  </button>
                </td>
              </tr>
              <tr v-if="!ruleDraft.matching.location_mappings.length">
                <td colspan="4" class="empty-row">{{ t('settings.noMappings') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="action-row">
          <button class="btn-secondary" @click="addMapping">
            <PlusOutlined />
            <span>{{ t('settings.addMapping') }}</span>
          </button>
        </div>
      </div>

      <div class="panel rules-actions-panel">
        <div class="panel-title">
          <CodeOutlined />
          <span>{{ t('settings.rulePreview') }}</span>
        </div>
        <pre class="rules-preview">{{ previewRules }}</pre>
        <div class="action-row">
          <button class="btn-primary" :disabled="savingRules" @click="saveRules">
            <SaveOutlined />
            <span>{{ savingRules ? t('settings.savingRules') : t('settings.saveRules') }}</span>
          </button>
          <button class="btn-secondary" :disabled="savingRules" @click="resetRules">
            <UndoOutlined />
            <span>{{ t('settings.resetDefaults') }}</span>
          </button>
          <span class="status-text" :class="{ error: statusType === 'error' }">{{ statusText }}</span>
        </div>
      </div>
    </section>

    <section v-else class="ideas-grid">
      <div v-for="idea in ideas" :key="idea.title" class="idea-card">
        <div class="idea-title">{{ idea.title }}</div>
        <p>{{ idea.body }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  CodeOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EyeOutlined,
  FileExcelOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  SettingOutlined,
  SwapOutlined,
  UndoOutlined,
} from '@ant-design/icons-vue'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'

const store = useAppStore()
const { t } = useI18n()
const loading = ref(false)
const parsing = ref(false)
const savingRules = ref(false)
const tab = ref('rawdata')
const selectedDaily = ref('')
const selectedFa = ref('')
const purgeDbOnDelete = ref(false)
const statusText = ref('')
const statusType = ref('')

const emptyRules = () => ({
  parse: {
    spec_fill_colors_text: '',
    strife_fill_colors_text: '',
    spec_font_colors_text: '',
    ignore_wfs_text: '',
    config_aliases_text: '',
  },
  display: {
    project_name: '',
    hidden_wfs_text: '',
    wf_aliases_text: '',
    config_order_text: '',
  },
  matching: {
    location_mappings: [],
  },
})

const ruleDraft = reactive(emptyRules())

const files = computed(() => store.settingsRawdata.files || [])
const reports = computed(() => store.settingsRawdata.reports || [])
const dailyFiles = computed(() => files.value.filter(file => file.kind === 'daily_report'))
const faFiles = computed(() => files.value.filter(file => file.kind === 'fa_tracker'))

const previewRules = computed(() => JSON.stringify(serializeRules(), null, 2))

const ideas = computed(() => [
  {
    title: t('settings.brainstormDryRunTitle'),
    body: t('settings.brainstormDryRunBody'),
  },
  {
    title: t('settings.brainstormSimulatorTitle'),
    body: t('settings.brainstormSimulatorBody'),
  },
  {
    title: t('settings.brainstormLineageTitle'),
    body: t('settings.brainstormLineageBody'),
  },
  {
    title: t('settings.brainstormReminderTitle'),
    body: t('settings.brainstormReminderBody'),
  },
  {
    title: t('settings.brainstormTemplateTitle'),
    body: t('settings.brainstormTemplateBody'),
  },
  {
    title: t('settings.brainstormInboxTitle'),
    body: t('settings.brainstormInboxBody'),
  },
])

async function loadAll() {
  loading.value = true
  statusText.value = ''
  try {
    await Promise.all([
      store.fetchRawdataSettings(),
      store.fetchSettingsRules(),
    ])
    hydrateRules(store.settingsRules)
    if (!selectedDaily.value && dailyFiles.value.length) {
      selectedDaily.value = dailyFiles.value[0].path
    }
  } catch (e) {
    showStatus(e.message || t('settings.loadFailed'), 'error')
  } finally {
    loading.value = false
  }
}

function showStatus(message, type = '') {
  statusText.value = message
  statusType.value = type
}

function parseList(text) {
  return String(text || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function parseMap(text) {
  const out = {}
  for (const line of String(text || '').split('\n')) {
    const idx = line.indexOf('=')
    if (idx <= 0) continue
    const key = line.slice(0, idx).trim()
    const value = line.slice(idx + 1).trim()
    if (key && value) out[key] = value
  }
  return out
}

function stringifyMap(value) {
  return Object.entries(value || {})
    .map(([key, val]) => `${key}=${val}`)
    .join('\n')
}

function hydrateRules(rules) {
  const parse = rules?.parse || {}
  const display = rules?.display || {}
  const matching = rules?.matching || {}
  ruleDraft.parse.spec_fill_colors_text = (parse.spec_fill_colors || []).join(', ')
  ruleDraft.parse.strife_fill_colors_text = (parse.strife_fill_colors || []).join(', ')
  ruleDraft.parse.spec_font_colors_text = (parse.spec_font_colors || []).join(', ')
  ruleDraft.parse.ignore_wfs_text = (parse.ignore_wfs || []).join(', ')
  ruleDraft.parse.config_aliases_text = stringifyMap(parse.config_aliases)
  ruleDraft.display.project_name = display.project_name || ''
  ruleDraft.display.hidden_wfs_text = (display.hidden_wfs || []).join(', ')
  ruleDraft.display.wf_aliases_text = stringifyMap(display.wf_aliases)
  ruleDraft.display.config_order_text = (display.config_order || []).join(', ')
  ruleDraft.matching.location_mappings = (matching.location_mappings || []).map(m => ({
    daily_report: m.daily_report || '',
    fa_tracker: m.fa_tracker || '',
    mode: m.mode || 'exact',
  }))
}

function serializeRules() {
  return {
    parse: {
      spec_fill_colors: parseList(ruleDraft.parse.spec_fill_colors_text),
      strife_fill_colors: parseList(ruleDraft.parse.strife_fill_colors_text),
      spec_font_colors: parseList(ruleDraft.parse.spec_font_colors_text),
      ignore_wfs: parseList(ruleDraft.parse.ignore_wfs_text),
      config_aliases: parseMap(ruleDraft.parse.config_aliases_text),
    },
    display: {
      project_name: ruleDraft.display.project_name.trim(),
      hidden_wfs: parseList(ruleDraft.display.hidden_wfs_text),
      wf_aliases: parseMap(ruleDraft.display.wf_aliases_text),
      config_order: parseList(ruleDraft.display.config_order_text),
    },
    matching: {
      location_mappings: ruleDraft.matching.location_mappings
        .filter(m => m.daily_report.trim() && m.fa_tracker.trim())
        .map(m => ({
          daily_report: m.daily_report.trim(),
          fa_tracker: m.fa_tracker.trim(),
          mode: m.mode || 'exact',
        })),
    },
  }
}

async function parseSelected() {
  if (!selectedDaily.value) return
  parsing.value = true
  showStatus('')
  try {
    const result = await store.parseRawdata(selectedDaily.value, selectedFa.value)
    showStatus(t('settings.parseDone', { date: result.report_date, count: result.wf_count }))
    store.triggerRefresh()
  } catch (e) {
    showStatus(e.message || t('settings.parseFailed'), 'error')
  } finally {
    parsing.value = false
  }
}

function addMapping() {
  ruleDraft.matching.location_mappings.push({ daily_report: '', fa_tracker: '', mode: 'exact' })
}

function removeMapping(index) {
  ruleDraft.matching.location_mappings.splice(index, 1)
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
    showStatus(t('settings.deleteDone', { name: file.name }))
    if (selectedDaily.value === file.path) selectedDaily.value = ''
    if (selectedFa.value === file.path) selectedFa.value = ''
  } catch (e) {
    showStatus(e.message || t('settings.deleteFailed'), 'error')
  }
}

async function saveRules() {
  savingRules.value = true
  try {
    const saved = await store.saveSettingsRules(serializeRules())
    hydrateRules(saved)
    showStatus(t('settings.rulesSaved'))
  } catch (e) {
    showStatus(e.message || t('settings.saveFailed'), 'error')
  } finally {
    savingRules.value = false
  }
}

async function resetRules() {
  if (!window.confirm(t('settings.resetConfirm'))) return
  savingRules.value = true
  try {
    const saved = await store.resetSettingsRules()
    hydrateRules(saved)
    showStatus(t('settings.resetDone'))
  } catch (e) {
    showStatus(e.message || t('settings.resetFailed'), 'error')
  } finally {
    savingRules.value = false
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

onMounted(loadAll)
</script>

<style scoped>
.settings-page {
  color: var(--text-primary);
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: var(--space-lg);
}

.page-title {
  margin-bottom: 6px;
}

.page-subtitle {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}

.settings-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 18px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-muted);
}

.settings-tabs button {
  min-width: 116px;
  height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.settings-tabs button.active {
  background: var(--bg-card);
  color: var(--accent-steel);
  box-shadow: var(--shadow-card);
}

.settings-grid,
.rules-grid {
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

.field.full {
  margin-top: 14px;
}

.field span {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.field input,
.field select,
.field textarea {
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

.field textarea {
  resize: vertical;
  line-height: 1.5;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: var(--border-focus);
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.btn-primary,
.btn-secondary,
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border-radius: var(--radius-sm);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--duration-fast), background var(--duration-fast), color var(--duration-fast);
}

.btn-primary,
.btn-secondary {
  height: 36px;
  padding: 0 14px;
}

.btn-primary {
  border: 1px solid var(--accent-steel);
  background: var(--accent-steel);
  color: #fff;
}

.btn-secondary {
  border: 1px solid var(--border-input);
  background: transparent;
  color: var(--text-secondary);
}

.icon-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-input);
  background: var(--bg-card);
  color: var(--text-secondary);
}

.icon-btn.small {
  width: 30px;
  height: 30px;
  font-size: 12px;
}

.icon-btn.danger {
  color: var(--color-danger);
}

.btn-primary:disabled,
.btn-secondary:disabled,
.icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.btn-primary:hover:not(:disabled),
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

.rules-actions-panel {
  grid-column: 1 / -1;
}

.location-mapping-panel {
  grid-column: 1 / -1;
}

.panel-desc {
  margin: 0 0 14px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.mapping-table-wrap {
  overflow-x: auto;
}

.mapping-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.mapping-table th {
  background: var(--bg-row-stripe);
  padding: 8px 10px;
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}

.mapping-table td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--border-light);
  vertical-align: middle;
}

.mapping-input {
  width: 100%;
  min-width: 140px;
  height: 32px;
  padding: 4px 8px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 12px;
  outline: none;
}

.mapping-input:focus {
  border-color: var(--border-focus);
}

.mapping-select {
  height: 32px;
  padding: 4px 8px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}

.rules-preview {
  max-height: 320px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
}

.ideas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
  gap: 14px;
}

.idea-card {
  padding: 16px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.idea-title {
  margin-bottom: 8px;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 700;
}

.idea-card p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.empty-row {
  padding: 24px 12px;
  color: var(--text-muted);
  text-align: center;
}

@media (min-width: 1100px) {
  .rules-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .settings-tabs {
    display: grid;
    grid-template-columns: 1fr;
    width: 100%;
  }

  .settings-tabs button {
    width: 100%;
  }

  .report-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }
}
</style>
