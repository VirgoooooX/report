import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { requestJson } from '@/composables/useApi'
import { normalizeByWf, normalizeTimeline } from '@/composables/useLifecycle'

export const useAppStore = defineStore('app', () => {
  // Preferences
  const language = ref(localStorage.getItem('dashboard-language') || 'zh-CN')
  const theme = ref(localStorage.getItem('dashboard-theme') || 'light')

  function setLanguage(lang) {
    language.value = lang
    localStorage.setItem('dashboard-language', lang)
    document.documentElement.lang = lang === 'zh-CN' ? 'zh-CN' : 'en-US'
  }

  function setTheme(nextTheme) {
    theme.value = nextTheme
    localStorage.setItem('dashboard-theme', nextTheme)
    document.documentElement.dataset.theme = nextTheme
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  function applyPreferences() {
    document.documentElement.lang = language.value === 'zh-CN' ? 'zh-CN' : 'en-US'
    document.documentElement.dataset.theme = theme.value
  }

  const projectName = ref('')
  const reportDate = ref('')
  const wfNames = ref({})
  const overviewData = ref(null)
  const summaryData = ref(null)
  const lastOverviewFetch = ref(0)
  const lastSummaryFetch = ref(0)
  const dataVersion = ref(localStorage.getItem('data-version') || '')
  const refreshCounter = ref(0)
  const loading = ref(false)
  const dailyIssues = ref([])
  const dailyIssuesConsistency = ref({})
  const dailyIssuesReportDate = ref('')
  const error = ref(null)
  const categories = ref([])
  const categoryDetail = ref(null)
  const predictions = ref([])
  const scheduleData = ref(null)
  const exportData = ref(null)
  const crossData = ref(null)
  const queryByWfData = ref(null)
  const queryByWfKey = ref('')
  const queryMultiSnData = ref(null)
  const queryMultiSnKey = ref('')
  const queryWfList = ref(null)
  const querySingleSnData = ref(null)
  const querySingleSnKey = ref('')
  const lastQueryType = ref('')  // 'lookup' | 'wcfg' | 'failure'
  const faCache = ref({})  // key = sn → [{symptom, failure_mode, ...}]
  const faLastTags = ref('')  // comma-separated last FA query tags
  const configColors = {
    overall: '#4f6f8f',
    R1FNF: '#4f6f8f',
    R2CNM: '#0891b2',
    R3: '#d97706',
    R4: '#059669'
  }

  const catColors = {
    Drop: '#ef4444',
    Ingress: '#4f6f8f',
    Environmental: '#22c55e',
    Mechanical: '#d97706'
  }

  const CONFIG_ORDER = ['R1FNF', 'R2CNM', 'R3', 'R4']
  const CAT_ORDER = ['Drop', 'Ingress', 'Environmental', 'Mechanical']

  async function fetchOverview(force = false) {
    if (!force && overviewData.value) return overviewData.value
    loading.value = true
    error.value = null
    try {
      const data = await requestJson('/api/dashboard/overview')
      overviewData.value = data
      lastOverviewFetch.value = Date.now()
      reportDate.value = data.report_date || ''
      projectName.value = data.project_name || ''
      if (data.wf_names) {
        // Normalize: API returns {wf: {name, test_names}} -> flatten to {wf: name} for compat
        const names = {}
        for (const [k, v] of Object.entries(data.wf_names)) {
          names[k] = typeof v === 'object' ? v.name : v
        }
        wfNames.value = names
      }
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchDailyIssues(force = false) {
    if (!force && dailyIssues.value.length) return { issues: dailyIssues.value, consistency: dailyIssuesConsistency.value, report_date: dailyIssuesReportDate.value }
    try {
      const data = await requestJson('/api/daily/issues')
      dailyIssues.value = data.issues || []
      dailyIssuesConsistency.value = data.consistency || {}
      dailyIssuesReportDate.value = data.report_date || ''
      return data
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function fetchSummary(force = false) {
    if (!force && summaryData.value) return summaryData.value
    try {
      summaryData.value = await requestJson('/api/test-summary')
      lastSummaryFetch.value = Date.now()
      return summaryData.value
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function fetchCategories(force = false) {
    if (!force && categories.value.length) return categories.value
    const d = await requestJson('/api/categories')
    categories.value = d.categories || []
    return categories.value
  }

  const predictionsCacheKey = ref('')

  async function fetchPredictions(wf, cfg, force = false) {
    let url = '/api/predictions'
    const params = []
    if (wf) params.push('wf=' + encodeURIComponent(wf))
    if (cfg) params.push('config=' + encodeURIComponent(cfg))
    if (params.length) url += '?' + params.join('&')
    if (!force && predictionsCacheKey.value === url && predictions.value.length) return predictions.value
    const d = await requestJson(url)
    predictions.value = d.predictions || []
    predictionsCacheKey.value = url
    return predictions.value
  }

  async function fetchSchedule(force = false) {
    if (!force && scheduleData.value) return scheduleData.value
    scheduleData.value = await requestJson('/api/schedule')
    return scheduleData.value
  }

  const categoryDetailName = ref('')

  async function fetchCategoryDetail(name, force = false) {
    if (!force && categoryDetailName.value === name && categoryDetail.value) return categoryDetail.value
    const d = await requestJson(`/api/completion/category/${encodeURIComponent(name)}`)
    categoryDetail.value = d
    categoryDetailName.value = name
    return d
  }

  async function searchSn(q) {
    const data = await requestJson(`/api/sn/search?q=${encodeURIComponent(q)}`)
    return Array.isArray(data) ? data : []
  }

  async function uploadReport(formData) {
    const resp = await fetch('/api/upload', { method: 'POST', body: formData })
    const contentType = resp.headers.get('content-type') || ''
    if (!resp.ok) {
      const text = await resp.text()
      let message = `HTTP ${resp.status}`
      if (contentType.includes('application/json')) {
        try { message = JSON.parse(text).error || message } catch {}
      }
      throw new Error(message)
    }
    const data = contentType.includes('application/json') ? await resp.json() : await resp.text()
    if (!data.success) throw new Error(data.error || 'Upload failed')
    return data
  }

  const exportDataKey = ref('')

  async function fetchExportData(filters, force = false) {
    const p = new URLSearchParams()
    if (filters.wf) p.set('wf', filters.wf)
    if (filters.config) p.set('config', filters.config)
    if (filters.sn) p.set('sn', filters.sn)
    const key = p.toString()
    if (!force && exportDataKey.value === key && exportData.value) return exportData.value
    const d = await requestJson(`/api/export?${key}`)
    exportData.value = d
    exportDataKey.value = key
    return d
  }

  const faCrossDims = ref('')

  async function fetchFaCross(dim1 = 'location', dim2 = 'config', force = false) {
    const dimKey = `${dim1}:${dim2}`
    if (!force && faCrossDims.value === dimKey && crossData.value) return crossData.value
    try {
      crossData.value = await requestJson(`/api/fa/cross?dim1=${dim1}&dim2=${dim2}`)
      faCrossDims.value = dimKey
      return crossData.value
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function fetchWfList(force = false) {
    if (!force && queryWfList.value) return queryWfList.value
    const data = await requestJson('/api/query/wf-list')
    queryWfList.value = data
    return data
  }

  async function fetchQueryByWf(wf, config, force = false) {
    const key = `${wf}|${config || ''}`
    if (!force && queryByWfKey.value === key && queryByWfData.value) return queryByWfData.value
    loading.value = true
    error.value = null
    try {
      const params = new URLSearchParams({ wf })
      if (config) params.set('config', config)
      const raw = await requestJson(`/api/query/by-wf?${params.toString()}`)
      const data = normalizeByWf(raw)
      queryByWfData.value = data
      queryByWfKey.value = key
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchSnTimeline(sns) {
    const list = Array.isArray(sns) ? sns : [sns]
    const key = list.slice().sort().join(',')
    const isSingle = list.length === 1

    if (isSingle && querySingleSnKey.value === key && querySingleSnData.value) {
      return querySingleSnData.value
    }
    if (!isSingle && queryMultiSnKey.value === key && queryMultiSnData.value) {
      return queryMultiSnData.value
    }

    loading.value = true
    error.value = null
    try {
      const raw = await requestJson(`/api/query/sn-timeline?sns=${encodeURIComponent(list.join(','))}`)
      const data = normalizeTimeline(raw)
      if (isSingle) {
        querySingleSnData.value = data
        querySingleSnKey.value = key
      } else {
        queryMultiSnData.value = data
        queryMultiSnKey.value = key
      }
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchSnCheckDetails(sn, wf, config, cpIdx) {
    try {
      const params = new URLSearchParams({ wf, config, cp_idx: String(cpIdx) })
      return await requestJson(`/api/sn/${encodeURIComponent(sn)}/checks?${params.toString()}`)
    } catch {
      return { check_items: [] }
    }
  }

  async function resolveMark(mark) {
    try {
      const data = await requestJson(`/api/sn/resolve-mark?mark=${encodeURIComponent(mark)}`)
      return data.sn
    } catch {
      return null
    }
  }

  async function fetchSnFa(sns, filters = {}) {
    const list = Array.isArray(sns) ? sns : sns ? [sns] : []
    const params = new URLSearchParams()
    if (list.length) params.set('sns', list.join(','))
    if (filters.symptom) params.set('symptom', filters.symptom)
    if (filters.location) params.set('location', filters.location)
    if (filters.config) params.set('config', filters.config)
    if (filters.wf) params.set('wf', filters.wf)
    if (filters.failed_test) params.set('failed_test', filters.failed_test)

    // When filters are used, skip cache (filters change results)
    const hasFilters = Object.values(filters).some(v => !!v)
    if (!hasFilters && list.length) {
      const toFetch = list.filter(sn => !faCache.value[sn])
      if (!toFetch.length) {
        const out = {}
        for (const sn of list) out[sn] = faCache.value[sn] || []
        return out
      }
    }

    try {
      const data = await requestJson(`/api/sn/fa?${params.toString()}`)
      const results = data?.results || {}
      if (!hasFilters) {
        for (const sn of list) faCache.value[sn] = results[sn] || []
      }
      return results
    } catch {
      const out = {}
      for (const sn of list) out[sn] = []
      return out
    }
  }

  const faOptions = ref(null)
  async function fetchFaOptions(filters = {}) {
    const params = new URLSearchParams()
    if (filters.wf) params.set('wf', filters.wf)
    if (filters.config) params.set('config', filters.config)
    if (filters.failed_test) params.set('failed_test', filters.failed_test)
    if (filters.symptom) params.set('symptom', filters.symptom)
    if (filters.location) params.set('location', filters.location)
    try {
      faOptions.value = await requestJson(`/api/sn/fa/options?${params.toString()}`)
    } catch {
      faOptions.value = { symptoms: [], locations: [], configs: [], wfs: [], failed_tests: [] }
    }
    return faOptions.value
  }

  // ── Cache layer ──

  function invalidateCache() {
    overviewData.value = null
    summaryData.value = null
    dailyIssues.value = []
    dailyIssuesConsistency.value = {}
    dailyIssuesReportDate.value = ''
    categories.value = []
    categoryDetail.value = null
    categoryDetailName.value = ''
    predictions.value = []
    predictionsCacheKey.value = ''
    scheduleData.value = null
    exportData.value = null
    exportDataKey.value = ''
    crossData.value = null
    faCrossDims.value = ''
    queryByWfData.value = null
    queryByWfKey.value = ''
    queryMultiSnData.value = null
    queryMultiSnKey.value = ''
    querySingleSnData.value = null
    querySingleSnKey.value = ''
    queryWfList.value = null
    lastQueryType.value = ''
    faCache.value = {}
    lastOverviewFetch.value = 0
    lastSummaryFetch.value = 0
  }

  async function checkVersion() {
    try {
      const { version } = await requestJson('/api/version')
      if (dataVersion.value && dataVersion.value !== version) {
        invalidateCache()
      }
      dataVersion.value = version
      localStorage.setItem('data-version', version)
    } catch { /* allow — version check is advisory */ }
  }

  // Run version check on store creation (survives page reload)
  checkVersion()

  function triggerRefresh() {
    refreshCounter.value++
  }

  function wfSortKey(wfn) {
    try {
      const parts = String(wfn).split('.')
      return parts.map(p => p.match(/^\d+$/) ? parseInt(p) : Infinity)
    } catch { return [Infinity] }
  }

  function sortedWfKeys(list) {
    return [...list].sort((a, b) => {
      const ka = wfSortKey(a), kb = wfSortKey(b)
      for (let i = 0; i < Math.max(ka.length, kb.length); i++) {
        const va = ka[i] ?? 0, vb = kb[i] ?? 0
        if (va !== vb) return va - vb
      }
      return 0
    })
  }

  return {
    language, theme, setLanguage, setTheme, toggleTheme, applyPreferences,
    projectName, reportDate, wfNames, overviewData, summaryData, lastOverviewFetch, lastSummaryFetch, loading, error,
    dailyIssues, dailyIssuesConsistency, dailyIssuesReportDate,
    categories, categoryDetail, predictions, scheduleData, exportData,
    configColors, catColors, CONFIG_ORDER, CAT_ORDER,
    fetchOverview, fetchDailyIssues, fetchSummary, fetchCategories, fetchPredictions, fetchSchedule,
    fetchCategoryDetail, searchSn, fetchExportData, uploadReport, fetchFaCross,
    crossData,
    fetchWfList, fetchQueryByWf, fetchSnTimeline, fetchSnCheckDetails, resolveMark, fetchSnFa, fetchFaOptions,
    queryWfList, queryByWfData, queryMultiSnData, querySingleSnData,
    queryByWfKey, queryMultiSnKey, querySingleSnKey,
    lastQueryType, faCache, faLastTags, faOptions,
    wfSortKey, sortedWfKeys,
    invalidateCache, checkVersion, triggerRefresh, refreshCounter
  }
})
