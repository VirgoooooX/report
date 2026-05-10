export function buildDailyUpdateKpis(dailyUpdates = {}, issues = [], consistency = {}) {
  const wfUpdates = dailyUpdates?.wf_updates ?? []
  const cpAdvanced = wfUpdates.reduce((sum, wf) => {
    return sum + (wf.configs ?? []).reduce((cfgSum, cfg) => cfgSum + (Number(cfg.cp_delta) || 0), 0)
  }, 0)
  const mismatchCount = (Number(consistency.only_daily_report) || 0) + (Number(consistency.only_fa_tracker) || 0)

  return [
    { key: 'wfUpdated', labelKey: 'dailyUpdate.kpiWfUpdated', value: wfUpdates.length, sublabelKey: 'dailyUpdate.kpiWfUpdatedSub', tone: 'info' },
    { key: 'cpAdvanced', labelKey: 'dailyUpdate.kpiCpAdvanced', value: cpAdvanced, sublabelKey: 'dailyUpdate.kpiCpAdvancedSub', tone: 'success' },
    { key: 'newIssues', labelKey: 'dailyUpdate.kpiNewIssues', value: issues.length, sublabelKey: 'dailyUpdate.kpiNewIssuesSub', tone: issues.length ? 'warning' : 'success' },
    {
      key: 'consistency',
      labelKey: 'dailyUpdate.kpiConsistency',
      value: consistency.is_consistent ? 'OK' : mismatchCount,
      sublabelKey: consistency.is_consistent ? 'dailyUpdate.kpiConsistencyOk' : 'dailyUpdate.kpiConsistencyMismatch',
      tone: consistency.is_consistent ? 'success' : 'danger'
    }
  ]
}
