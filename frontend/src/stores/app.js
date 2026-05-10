import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { requestJson } from '@/composables/useApi'

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
  const loading = ref(false)
  const dailyIssues = ref([])
  const dailyIssuesConsistency = ref({})
  const dailyIssuesReportDate = ref('')
  const error = ref(null)
  const categories = ref([])
  const categoryDetail = ref(null)
  const predictions = ref([])
  const scheduleData = ref(null)
  const snResult = ref(null)
  const exportData = ref(null)
  const crossData = ref(null)
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

  async function fetchOverview() {
    loading.value = true
    error.value = null
    try {
      const data = await requestJson('/api/dashboard/overview')
      overviewData.value = data
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

  async function fetchDailyIssues() {
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

  async function fetchSummary() {
    try {
      summaryData.value = await requestJson('/api/test-summary')
      return summaryData.value
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function fetchCategories() {
    const d = await requestJson('/api/categories')
    categories.value = d.categories || []
    return categories.value
  }

  async function fetchPredictions(wf, cfg) {
    let url = '/api/predictions'
    const params = []
    if (wf) params.push('wf=' + encodeURIComponent(wf))
    if (cfg) params.push('config=' + encodeURIComponent(cfg))
    if (params.length) url += '?' + params.join('&')
    const d = await requestJson(url)
    predictions.value = d.predictions || []
    return predictions.value
  }

  async function fetchSchedule() {
    scheduleData.value = await requestJson('/api/schedule')
    return scheduleData.value
  }

  async function fetchCategoryDetail(name) {
    const d = await requestJson(`/api/completion/category/${encodeURIComponent(name)}`)
    categoryDetail.value = d
    return d
  }

  async function fetchSnResult(sn) {
    snResult.value = await requestJson(`/api/sn/${encodeURIComponent(sn)}`)
    return snResult.value
  }

  async function searchSn(q) {
    return await requestJson(`/api/sn/search?q=${encodeURIComponent(q)}`)
  }

  async function fetchExportData(filters) {
    const p = new URLSearchParams()
    if (filters.wf) p.set('wf', filters.wf)
    if (filters.config) p.set('config', filters.config)
    if (filters.sn) p.set('sn', filters.sn)
    const d = await requestJson(`/api/export?${p}`)
    exportData.value = d
    return d
  }

  async function fetchFaCross(dim1 = 'location', dim2 = 'config') {
    try {
      crossData.value = await requestJson(`/api/fa/cross?dim1=${dim1}&dim2=${dim2}`)
      return crossData.value
    } catch (e) {
      error.value = e.message
      throw e
    }
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
    projectName, reportDate, wfNames, overviewData, summaryData, loading, error,
    dailyIssues, dailyIssuesConsistency, dailyIssuesReportDate,
    categories, categoryDetail, predictions, scheduleData, snResult, exportData,
    configColors, catColors, CONFIG_ORDER, CAT_ORDER,
    fetchOverview, fetchDailyIssues, fetchSummary, fetchCategories, fetchPredictions, fetchSchedule,
    fetchCategoryDetail, fetchSnResult, searchSn, fetchExportData, fetchFaCross,
    crossData,
    wfSortKey, sortedWfKeys
  }
})
