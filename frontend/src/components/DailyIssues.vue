<template>
  <div class="card daily-card">
    <div class="daily-header" @click="toggle">
      <span class="chevron" :class="{ open: expanded }">▶</span>
      <span class="daily-title">{{ t('dailyUpdate.issues') }}</span>
      <span class="daily-count">{{ issues.length }} {{ t('dailyUpdate.issueCount') }}</span>
      <button class="toggle-btn" @click.stop="toggle">{{ expanded ? t('dailyUpdate.collapse') : t('dailyUpdate.expand') }}</button>
    </div>
    <div class="daily-body" :class="{ collapsed: !expanded }">
      <!-- Warning / Confirmation Banner -->
      <div v-if="!consistency?.is_consistent && issues.length" class="banner banner-warn">
        <span class="banner-icon">⚠️</span>
        <div class="banner-text">
          <strong>{{ t('dailyIssues.dataInconsistent') }}</strong>
          <span>{{ t('dailyIssues.onlyInDaily', { count: consistency.only_daily_report }) }}, {{ t('dailyIssues.onlyInFa', { count: consistency.only_fa_tracker }) }}</span>
        </div>
      </div>
      <div v-else-if="consistency?.is_consistent && issues.length" class="banner banner-ok">
        <span class="banner-icon">✅</span>
        <div class="banner-text">
          <strong>{{ t('dailyIssues.dataConsistent') }}</strong>
          <span>{{ t('dailyIssues.allConfirmed', { count: issues.length }) }}</span>
        </div>
      </div>
      <div v-if="!issues.length" class="daily-empty">{{ t('common.empty') }}</div>

      <!-- Issue Table -->
      <div v-if="issues.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>SN</th>
              <th>WF</th>
              <th>Config</th>
              <th>Failed Test</th>
              <th>Failed Cycle</th>
              <th>Type</th>
              <th>Symptom</th>
              <th>Location</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(row, i) in issues" :key="i">
              <tr
                :class="{
                  'row-warn': row.source !== 'matched',
                  'row-expandable': row.source === 'matched',
                  'row-expanded': expandedRows.has(i),
                }"
                @click="row.source === 'matched' && toggleRow(i)"
              >
                <td>
                  <span v-if="row.source === 'matched'" class="expand-icon" :class="{ open: expandedRows.has(i) }">▶</span>
                  <span v-else>{{ i + 1 }}</span>
                </td>
                <td class="mono">{{ row.sn }}</td>
                <td>WF{{ row.wf }}</td>
                <td>{{ row.config }}</td>
                <td>{{ row.failed_test }}</td>
                <td :title="row.failed_cycle">{{ row.failed_cycle }}</td>
                <td>
                  <span :class="row.type === 'spec' ? 'type-spec' : row.type === 'strife' ? 'type-strife' : ''">
                    {{ row.type === 'spec' ? 'Spec' : row.type === 'strife' ? 'Strife' : row.type }}
                  </span>
                </td>
                <td :title="row.symptom">{{ row.symptom }}</td>
                <td>{{ row.location }}</td>
                <td>
                  <span class="source-badge" :class="'source-' + row.source">
                    {{ sourceLabel(row.source) }}
                  </span>
                </td>
              </tr>
              <!-- Expanded detail rows for matched issues -->
              <tr v-if="row.source === 'matched' && expandedRows.has(i)" class="detail-row">
                <td colspan="10">
                  <div class="detail-grid">
                    <div class="detail-source">
                      <span class="detail-label">📄 {{ t('dailyIssues.dailyReportLabel') }}</span>
                      <div class="detail-fields">
                        <span class="detail-field"><b>Location:</b> {{ row.detail?.daily_report?.location }}</span>
                        <span class="detail-field"><b>Failed Cycle:</b> {{ row.detail?.daily_report?.failed_cycle }}</span>
                      </div>
                    </div>
                    <div class="detail-source">
                      <span class="detail-label">📊 {{ t('dailyIssues.faTrackerLabel') }}</span>
                      <div class="detail-fields">
                        <span class="detail-field"><b>Location:</b> {{ row.detail?.fa_tracker?.location }}</span>
                        <span class="detail-field"><b>Failed Test:</b> {{ row.detail?.fa_tracker?.failed_test }}</span>
                        <span class="detail-field"><b>Failed Cycle:</b> {{ row.detail?.fa_tracker?.failed_cycle }}</span>
                        <span class="detail-field"><b>Symptom:</b> {{ row.detail?.fa_tracker?.symptom }}</span>
                        <span v-if="row.detail?.fa_tracker?.fa_num" class="detail-field"><b>FA#:</b> {{ row.detail?.fa_tracker?.fa_num }}</span>
                        <span v-if="row.detail?.fa_tracker?.fa_status" class="detail-field"><b>Status:</b> {{ row.detail?.fa_tracker?.fa_status }}</span>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

defineProps({
  consistency: { type: Object, default: () => ({}) },
  issues: { type: Array, default: () => [] },
})

const expanded = ref(true)
const expandedRows = reactive(new Set())

const toggle = () => { expanded.value = !expanded.value }

function toggleRow(index) {
  if (expandedRows.has(index)) {
    expandedRows.delete(index)
  } else {
    expandedRows.add(index)
  }
}

function sourceLabel(s) {
  const map = {
    matched: t('dailyIssues.consistent'),
    only_daily_report: t('dailyIssues.dailyReportOnly'),
    only_fa_tracker: t('dailyIssues.faTrackerOnly'),
  }
  return map[s] || s
}
</script>

<style scoped>
.daily-card { overflow: hidden; }
.daily-header {
  display: flex; align-items: center; gap: 12px; padding: 14px 20px;
  cursor: pointer; user-select: none;
}
.daily-header:hover { background: var(--bg-card-hover); }
.chevron { font-size: 10px; color: var(--text-muted); transition: transform var(--duration-fast); flex-shrink: 0; }
.chevron.open { transform: rotate(90deg); }
.daily-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.daily-count { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }
.toggle-btn {
  margin-left: auto; padding: 4px 12px; font-size: 12px;
  color: var(--text-secondary); border: 1px solid var(--border-input);
  border-radius: var(--radius-sm); cursor: pointer; background: none;
  transition: background var(--duration-fast);
}
.toggle-btn:hover { background: var(--bg-row-stripe); }

.daily-body {
  max-height: 10000px; overflow: hidden;
  transition: max-height var(--duration-normal) var(--ease-in-out);
}
.daily-body.collapsed { max-height: 0; }
.daily-empty { padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px; }

/* Banner */
.banner {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 16px; margin: 0 16px 12px; border-radius: var(--radius-sm);
  font-size: 13px;
}
.banner-warn { background: #fff3cd; border: 1px solid #ffc107; color: #856404; }
.banner-ok { background: #d4edda; border: 1px solid #28a745; color: #155724; }
.banner-icon { font-size: 16px; flex-shrink: 0; line-height: 1.3; }
.banner-text { display: flex; flex-direction: column; gap: 2px; }
.banner-text span { font-size: 12px; }

/* Table */
.table-wrap { overflow-x: auto; padding: 0 16px 16px; }
table {
  width: auto; min-width: 100%; border-collapse: collapse; font-size: 13px;
  font-variant-numeric: tabular-nums; table-layout: auto;
}
th {
  background: var(--bg-row-stripe); padding: 8px 10px;
  text-align: left; font-weight: 600; font-size: 11px;
  color: var(--text-muted); border-bottom: 1px solid var(--border-light);
  text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap;
}
td {
  padding: 8px 10px; border-bottom: 1px solid var(--border-light);
  font-size: 12px; vertical-align: middle; white-space: nowrap;
}
.mono { font-family: var(--font-mono); font-size: 11px; }

.row-warn td { background: #fff9e6; }
.row-expandable { cursor: pointer; }
.row-expandable:hover td { background: var(--bg-row-hover); }
.row-expanded td { background: var(--bg-row-stripe); border-bottom-color: transparent; }

.expand-icon {
  display: inline-block; font-size: 9px; color: var(--text-muted);
  transition: transform var(--duration-fast);
}
.expand-icon.open { transform: rotate(90deg); }

.type-spec { color: var(--color-danger); font-weight: 600; }
.type-strife { color: #d97706; font-weight: 600; }

.source-badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 500; white-space: nowrap;
}
.source-matched { background: #d4edda; color: #155724; }
.source-only_daily_report { background: #fff3cd; color: #856404; }
.source-only_fa_tracker { background: #f8d7da; color: #721c24; }

/* Detail row */
.detail-row td {
  padding: 0; background: var(--bg-muted); border-bottom: 1px solid var(--border-light);
}
.detail-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
  padding: 12px 16px;
}
.detail-source {
  display: flex; flex-direction: column; gap: 6px;
  padding: 10px 14px; border-radius: var(--radius-sm);
  background: var(--bg-card); border: 1px solid var(--border-light);
}
.detail-label {
  font-size: 11px; font-weight: 700; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.3px;
}
.detail-fields {
  display: flex; flex-direction: column; gap: 3px;
}
.detail-field {
  font-size: 12px; color: var(--text-primary); white-space: normal;
}
.detail-field b {
  color: var(--text-muted); font-weight: 600; margin-right: 4px;
}
</style>
