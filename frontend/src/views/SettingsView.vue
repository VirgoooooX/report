<template>
  <div class="page-container settings-page">
    <div class="page-head">
      <div>
        <h1 class="page-title">设置</h1>
        <p class="page-subtitle">Rawdata、解析入口和自定义规则集中管理。</p>
      </div>
      <button class="icon-btn" :disabled="loading" title="刷新" aria-label="刷新" @click="loadAll">
        <ReloadOutlined />
      </button>
    </div>

    <div class="settings-tabs" role="tablist">
      <button :class="{ active: tab === 'rawdata' }" @click="tab = 'rawdata'">Rawdata</button>
      <button :class="{ active: tab === 'rules' }" @click="tab = 'rules'">自定义规则</button>
      <button :class="{ active: tab === 'ideas' }" @click="tab = 'ideas'">Brainstorm</button>
    </div>

    <section v-if="tab === 'rawdata'" class="settings-grid">
      <div class="panel parse-panel">
        <div class="panel-title">
          <PlayCircleOutlined />
          <span>手动解析</span>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>Daily Report</span>
            <select v-model="selectedDaily">
              <option value="">选择文件</option>
              <option v-for="file in dailyFiles" :key="file.path" :value="file.path">
                {{ file.date || 'no date' }} · {{ file.name }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>FA Tracker</span>
            <select v-model="selectedFa">
              <option value="">自动匹配</option>
              <option v-for="file in faFiles" :key="file.path" :value="file.path">
                {{ file.date || 'no date' }} · {{ file.name }}
              </option>
            </select>
          </label>
        </div>
        <div class="action-row">
          <button class="btn-primary" :disabled="!selectedDaily || parsing" @click="parseSelected">
            <PlayCircleOutlined />
            <span>{{ parsing ? '解析中...' : '解析选中文件' }}</span>
          </button>
          <span class="status-text" :class="{ error: statusType === 'error' }">{{ statusText }}</span>
        </div>
      </div>

      <div class="panel rawdata-panel">
        <div class="panel-title">
          <FileExcelOutlined />
          <span>Rawdata 文件</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>类型</th>
                <th>日期</th>
                <th>文件</th>
                <th>大小</th>
                <th>修改时间</th>
                <th>操作</th>
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
                      title="解析这份数据"
                      aria-label="解析这份数据"
                      @click="parseFile(file)"
                    >
                      <PlayCircleOutlined />
                    </button>
                    <button class="icon-btn small danger" title="删除文件" aria-label="删除文件" @click="deleteFile(file)">
                      <DeleteOutlined />
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!files.length">
                <td colspan="6" class="empty-row">暂无 rawdata 文件</td>
              </tr>
            </tbody>
          </table>
        </div>
        <label class="purge-toggle">
          <input v-model="purgeDbOnDelete" type="checkbox" />
          <span>删除 Daily Report 时同步清理对应数据库记录</span>
        </label>
      </div>

      <div class="panel reports-panel">
        <div class="panel-title">
          <DatabaseOutlined />
          <span>已导入版本</span>
        </div>
        <div class="report-list">
          <div v-for="report in reports" :key="report.id" class="report-row">
            <span class="mono">{{ report.report_date }}</span>
            <span>v{{ report.version }}</span>
            <span class="report-file">{{ report.source_file_name }}</span>
            <span class="active-pill" :class="{ muted: !report.is_active }">
              {{ report.is_active ? 'Active' : 'History' }}
            </span>
          </div>
          <div v-if="!reports.length" class="empty-row">暂无导入记录</div>
        </div>
      </div>
    </section>

    <section v-else-if="tab === 'rules'" class="rules-grid">
      <div class="panel">
        <div class="panel-title">
          <SettingOutlined />
          <span>解析规则</span>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>Spec 填充色</span>
            <input v-model="ruleDraft.parse.spec_fill_colors_text" placeholder="FF0000, C00000" />
          </label>
          <label class="field">
            <span>Strife 填充色</span>
            <input v-model="ruleDraft.parse.strife_fill_colors_text" placeholder="FFFF00" />
          </label>
          <label class="field">
            <span>Spec 字体色</span>
            <input v-model="ruleDraft.parse.spec_font_colors_text" placeholder="FF9C0006" />
          </label>
          <label class="field">
            <span>忽略 WF</span>
            <input v-model="ruleDraft.parse.ignore_wfs_text" placeholder="1.1, 14.2" />
          </label>
        </div>
        <label class="field full">
          <span>Config 别名</span>
          <textarea v-model="ruleDraft.parse.config_aliases_text" rows="4" placeholder="R1=R1FNF&#10;R2=R2CNM"></textarea>
        </label>
      </div>

      <div class="panel">
        <div class="panel-title">
          <EyeOutlined />
          <span>显示规则</span>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>项目名</span>
            <input v-model="ruleDraft.display.project_name" placeholder="M60 EVT REL" />
          </label>
          <label class="field">
            <span>Config 排序</span>
            <input v-model="ruleDraft.display.config_order_text" placeholder="R1FNF, R2CNM, R3, R4" />
          </label>
          <label class="field">
            <span>隐藏 WF</span>
            <input v-model="ruleDraft.display.hidden_wfs_text" placeholder="MLB, 1.2" />
          </label>
        </div>
        <label class="field full">
          <span>WF 显示别名</span>
          <textarea v-model="ruleDraft.display.wf_aliases_text" rows="5" placeholder="16.1=Drop Sequence&#10;20=Button Cycling"></textarea>
        </label>
      </div>

      <div class="panel rules-actions-panel">
        <div class="panel-title">
          <CodeOutlined />
          <span>规则预览</span>
        </div>
        <pre class="rules-preview">{{ previewRules }}</pre>
        <div class="action-row">
          <button class="btn-primary" :disabled="savingRules" @click="saveRules">
            <SaveOutlined />
            <span>{{ savingRules ? '保存中...' : '保存规则' }}</span>
          </button>
          <button class="btn-secondary" :disabled="savingRules" @click="resetRules">
            <UndoOutlined />
            <span>恢复默认</span>
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
  ReloadOutlined,
  SaveOutlined,
  SettingOutlined,
  UndoOutlined,
} from '@ant-design/icons-vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
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
})

const ruleDraft = reactive(emptyRules())

const files = computed(() => store.settingsRawdata.files || [])
const reports = computed(() => store.settingsRawdata.reports || [])
const dailyFiles = computed(() => files.value.filter(file => file.kind === 'daily_report'))
const faFiles = computed(() => files.value.filter(file => file.kind === 'fa_tracker'))

const previewRules = computed(() => JSON.stringify(serializeRules(), null, 2))

const ideas = [
  {
    title: '解析 Dry Run',
    body: '手动解析前先跑一遍预检查，输出将要写入的报告日期、WF 数、失败颜色命中和可能被忽略的 sheet。',
  },
  {
    title: '规则命中模拟器',
    body: '上传或选择一小段样本单元格，页面直接展示当前规则会判定为 pass、spec、strife 还是 pending。',
  },
  {
    title: '数据血缘与回滚',
    body: '每次解析生成一份审计记录，支持把 active report 回滚到某个历史 version。',
  },
  {
    title: '自动匹配提醒',
    body: 'Daily Report 和 FA Tracker 日期不一致时给出醒目的提醒，并显示当前采用的是精确匹配还是 fallback。',
  },
  {
    title: '规则模板',
    body: '把常见项目阶段的颜色、WF 别名、隐藏项和 Config 顺序保存成模板，一键切换。',
  },
  {
    title: '异常数据收件箱',
    body: '把无法识别的 WF、未知 Config、空 SN、重复 SN 聚合成待处理队列，设置页里逐条处理。',
  },
]

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
    showStatus(e.message || '加载设置失败', 'error')
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
  ruleDraft.parse.spec_fill_colors_text = (parse.spec_fill_colors || []).join(', ')
  ruleDraft.parse.strife_fill_colors_text = (parse.strife_fill_colors || []).join(', ')
  ruleDraft.parse.spec_font_colors_text = (parse.spec_font_colors || []).join(', ')
  ruleDraft.parse.ignore_wfs_text = (parse.ignore_wfs || []).join(', ')
  ruleDraft.parse.config_aliases_text = stringifyMap(parse.config_aliases)
  ruleDraft.display.project_name = display.project_name || ''
  ruleDraft.display.hidden_wfs_text = (display.hidden_wfs || []).join(', ')
  ruleDraft.display.wf_aliases_text = stringifyMap(display.wf_aliases)
  ruleDraft.display.config_order_text = (display.config_order || []).join(', ')
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
  }
}

async function parseSelected() {
  if (!selectedDaily.value) return
  parsing.value = true
  showStatus('')
  try {
    const result = await store.parseRawdata(selectedDaily.value, selectedFa.value)
    showStatus(`解析完成：${result.report_date}，${result.wf_count} 个 WF`)
    store.triggerRefresh()
  } catch (e) {
    showStatus(e.message || '解析失败', 'error')
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
  const suffix = purgeDbOnDelete.value && file.kind === 'daily_report' ? '，并清理对应数据库记录' : ''
  if (!window.confirm(`确认删除 ${file.name}${suffix}？`)) return
  try {
    await store.deleteRawdataFile(file.path, purgeDbOnDelete.value && file.kind === 'daily_report')
    showStatus(`已删除：${file.name}`)
    if (selectedDaily.value === file.path) selectedDaily.value = ''
    if (selectedFa.value === file.path) selectedFa.value = ''
  } catch (e) {
    showStatus(e.message || '删除失败', 'error')
  }
}

async function saveRules() {
  savingRules.value = true
  try {
    const saved = await store.saveSettingsRules(serializeRules())
    hydrateRules(saved)
    showStatus('规则已保存，下一次解析会使用新规则')
  } catch (e) {
    showStatus(e.message || '保存失败', 'error')
  } finally {
    savingRules.value = false
  }
}

async function resetRules() {
  if (!window.confirm('确认恢复默认规则？')) return
  savingRules.value = true
  try {
    const saved = await store.resetSettingsRules()
    hydrateRules(saved)
    showStatus('已恢复默认规则')
  } catch (e) {
    showStatus(e.message || '恢复失败', 'error')
  } finally {
    savingRules.value = false
  }
}

function kindLabel(kind) {
  return kind === 'daily_report' ? 'Daily' : kind === 'fa_tracker' ? 'FA' : 'Other'
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
  grid-template-columns: 110px 52px minmax(0, 1fr) 78px;
  align-items: center;
  gap: 12px;
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
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
