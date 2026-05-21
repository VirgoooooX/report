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
      <button :class="{ active: tab === 'rules' }" @click="tab = 'rules'">{{ t('settings.tabRules') }}</button>
      <button :class="{ active: tab === 'assistant' }" @click="tab = 'assistant'">{{ t('settings.tabAssistant') }}</button>
      <button :class="{ active: tab === 'ideas' }" @click="tab = 'ideas'">{{ t('settings.tabIdeas') }}</button>
    </div>

    <section v-if="tab === 'rules'" class="rules-grid">
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

    <section v-else-if="tab === 'assistant'" class="rules-grid">
      <div class="panel ai-feature-panel">
        <div>
          <div class="panel-title">
            <RobotOutlined />
            <span>{{ t('settings.aiFeature') }}</span>
          </div>
          <p class="panel-desc">{{ t('settings.aiFeatureDesc') }}</p>
        </div>
        <label class="switch-control">
          <input
            type="checkbox"
            :checked="store.aiEnabled"
            @change="store.setAiEnabled($event.target.checked)"
          />
          <span class="switch-track" aria-hidden="true"></span>
          <span class="switch-label">{{ store.aiEnabled ? t('common.yes') : t('common.no') }}</span>
        </label>
      </div>

      <div v-if="store.aiEnabled" class="panel">
        <div class="panel-title">
          <RobotOutlined />
          <span>{{ t('settings.llmProvider') }}</span>
        </div>
        <p class="panel-desc">{{ t('settings.llmProviderDesc') }}</p>
        <div class="field-grid">
          <label class="field">
            <span>{{ t('settings.providerType') }}</span>
            <select v-model="llmDraft.provider">
              <option value="mock">{{ t('settings.providerMock') }}</option>
              <option value="openai_compatible">{{ t('settings.providerOpenaiCompatible') }}</option>
            </select>
          </label>
        </div>

        <p v-if="llmDraft.provider === 'mock'" class="provider-hint">{{ t('settings.mockDesc') }}</p>

        <div v-else-if="llmDraft.provider === 'openai_compatible'" class="field-grid provider-fields">
          <label class="field">
            <span>{{ t('settings.preset') }}</span>
            <select v-model="llmDraft.preset" @change="onPresetChange">
              <option value="openai">{{ t('settings.presetOpenai') }}</option>
              <option value="deepseek">{{ t('settings.presetDeepseek') }}</option>
              <option value="openrouter">{{ t('settings.presetOpenrouter') }}</option>
              <option value="gemini">{{ t('settings.presetGemini') }}</option>
              <option value="lmstudio">{{ t('settings.presetLmstudio') }}</option>
              <option value="llama_cpp">{{ t('settings.presetLlamaCpp') }}</option>
              <option value="custom">{{ t('settings.presetCustom') }}</option>
            </select>
          </label>

          <label class="field">
            <span>{{ t('settings.baseUrl') }}</span>
            <input 
              v-model="llmDraft.base_url" 
              :placeholder="t('settings.baseUrlPlaceholder')"
              :disabled="llmDraft.preset !== 'custom'"
            />
          </label>

          <label class="field">
            <span>{{ t('settings.apiKey') }}</span>
            <div class="input-with-toggle">
              <input
                v-model="llmDraft.api_key"
                :type="showApiKey ? 'text' : 'password'"
                :placeholder="t('settings.apiKeyPlaceholder')"
                autocomplete="off"
              />
              <button class="toggle-btn" type="button" @click="showApiKey = !showApiKey">
                <EyeOutlined v-if="!showApiKey" />
                <EyeInvisibleOutlined v-else />
              </button>
            </div>
          </label>

          <label class="field">
            <span>{{ t('settings.llmModel') }}</span>
            <div class="model-input-group">
              <select 
                v-if="availableModels.length > 0 && !isCustomModel"
                v-model="llmDraft.model" 
                @change="onModelSelect"
              >
                <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
                <option value="__custom__">✍️ 自定义输入...</option>
              </select>
              <input 
                v-else
                v-model="llmDraft.model" 
                :placeholder="t('settings.llmModelPlaceholder')" 
              />
              <button class="btn-secondary fetch-btn" :disabled="fetchingModels" @click="fetchModels">
                <ReloadOutlined :class="{ 'spin': fetchingModels }" />
                <span>{{ fetchingModels ? t('settings.fetchingModels') : t('settings.fetchModels') }}</span>
              </button>
            </div>
          </label>

          <label class="field">
            <span>{{ t('settings.timeout') }}</span>
            <input v-model.number="llmDraft.timeout" type="number" min="10" max="600" />
          </label>
          <label class="field">
            <span>{{ t('settings.maxTokens') }}</span>
            <input v-model.number="llmDraft.max_tokens" type="number" min="64" max="65536" />
          </label>
        </div>

        <div class="action-row">
          <button class="btn-primary" :disabled="savingLlm" @click="saveLlm">
            <SaveOutlined />
            <span>{{ savingLlm ? t('settings.savingLlm') : t('settings.saveLlm') }}</span>
          </button>
          <span class="status-text" :class="{ error: llmStatusType === 'error' }">{{ llmStatusText }}</span>
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
  DeleteOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
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
const savingRules = ref(false)
const tab = ref('rules')
const statusText = ref('')
const statusType = ref('')
const savingLlm = ref(false)
const llmStatusText = ref('')
const llmStatusType = ref('')
const showApiKey = ref(false)
const availableModels = ref([])
const fetchingModels = ref(false)
const isCustomModel = ref(false)
const llmPresets = ref({})

const emptyLlmConfig = () => ({
  provider: 'mock',
  preset: 'openai',
  base_url: 'https://api.openai.com',
  api_key: '',
  model: 'gpt-4.1-mini',
  timeout: 120,
  max_tokens: 4096,
})

const llmDraft = reactive(emptyLlmConfig())

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
    const tasks = [store.fetchSettingsRules()]
    if (store.aiEnabled) tasks.push(store.fetchLlmConfig())
    const [, llmData] = await Promise.all(tasks)
    hydrateRules(store.settingsRules)
    if (llmData) hydrateLlm(llmData)
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

function showLlmStatus(message, type = '') {
  llmStatusText.value = message
  llmStatusType.value = type
}

function hydrateLlm(config) {
  if (!config) return
  if (config.presets) {
    llmPresets.value = config.presets
  }
  llmDraft.provider = config.provider || 'mock'
  llmDraft.preset = config.preset || 'openai'
  llmDraft.base_url = config.base_url || ''
  llmDraft.api_key = config.api_key || ''
  llmDraft.model = config.model || ''
  llmDraft.timeout = config.timeout ?? 120
  llmDraft.max_tokens = config.max_tokens ?? 4096
}

function onPresetChange() {
  if (llmDraft.preset !== 'custom' && llmPresets.value[llmDraft.preset]) {
    const p = llmPresets.value[llmDraft.preset]
    llmDraft.base_url = p.base_url
    llmDraft.model = p.model
    
    // 清除上一个 preset 缓存的模型列表，并恢复输入框状态
    availableModels.value = []
    isCustomModel.value = false
  }
}

function onModelSelect(e) {
  if (e.target.value === '__custom__') {
    isCustomModel.value = true
    llmDraft.model = ''
  }
}

function serializeLlm() {
  return {
    provider: llmDraft.provider,
    preset: llmDraft.preset,
    base_url: llmDraft.base_url,
    api_key: llmDraft.api_key,
    model: llmDraft.model,
    timeout: llmDraft.timeout,
    max_tokens: llmDraft.max_tokens,
  }
}

async function saveLlm() {
  savingLlm.value = true
  try {
    const saved = await store.saveLlmConfig(serializeLlm())
    hydrateLlm(saved)
    showLlmStatus(t('settings.llmSaved'), 'success')
  } catch (e) {
    showLlmStatus(e.message || t('settings.llmSaveFailed'), 'error')
  } finally {
    savingLlm.value = false
  }
}

async function fetchModels() {
  fetchingModels.value = true
  try {
    const models = await store.fetchLlmModels(llmDraft.base_url, llmDraft.api_key)
    
    if (llmDraft.model && llmDraft.model !== '__custom__' && !models.includes(llmDraft.model)) {
      models.unshift(llmDraft.model)
    }
    
    availableModels.value = models
    isCustomModel.value = false
    
    showLlmStatus(t('settings.fetchModelsSuccess'), 'success')
    if (models.length > 0 && !llmDraft.model) {
      llmDraft.model = models[0]
    }
  } catch (e) {
    showLlmStatus(e.message || t('settings.fetchModelsFailed'), 'error')
  } finally {
    fetchingModels.value = false
  }
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

function addMapping() {
  ruleDraft.matching.location_mappings.push({ daily_report: '', fa_tracker: '', mode: 'exact' })
}

function removeMapping(index) {
  ruleDraft.matching.location_mappings.splice(index, 1)
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

watch(() => store.aiEnabled, async (enabled) => {
  if (enabled && !store.llmConfig) {
    try {
      hydrateLlm(await store.fetchLlmConfig())
    } catch (e) {
      showLlmStatus(e.message || t('settings.llmLoadFailed'), 'error')
    }
  }
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

.ai-feature-panel {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.ai-feature-panel .panel-title {
  margin-bottom: 6px;
}

.switch-control {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.switch-control input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.switch-track {
  position: relative;
  width: 44px;
  height: 24px;
  flex: 0 0 auto;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-full);
  background: var(--bg-muted);
  transition: background var(--duration-fast), border-color var(--duration-fast);
}

.switch-track::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: transform var(--duration-fast), background var(--duration-fast);
}

.switch-control input:checked + .switch-track {
  border-color: var(--accent-steel);
  background: var(--accent-steel);
}

.switch-control input:checked + .switch-track::after {
  background: #fff;
  transform: translateX(20px);
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

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
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
}

.provider-hint {
  margin: 14px 0 0;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.provider-fields {
  margin-top: 14px;
}

.input-with-toggle {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-toggle input {
  flex: 1;
  padding-right: 36px;
}

.toggle-btn {
  position: absolute;
  right: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
}

.toggle-btn:hover {
  color: var(--text-secondary);
}
.model-input-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.model-input-group input, .model-input-group select {
  flex: 1;
}

.fetch-btn {
  white-space: nowrap;
  padding: 0 12px;
  height: 32px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-muted);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-color);
  transition: all 0.2s;
}

.fetch-btn:hover:not(:disabled) {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.fetch-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

.status-text.success {
  color: var(--success-color, #10b981);
}
</style>
