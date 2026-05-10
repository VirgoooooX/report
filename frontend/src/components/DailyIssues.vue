<template>
  <div class="card daily-card">
    <div class="daily-header" @click="toggle">
      <span class="chevron" :class="{ open: expanded }">▶</span>
      <span class="daily-title">Daily Issues</span>
      <span class="daily-count">{{ issues.length }} issue(s)</span>
      <button class="toggle-btn" @click.stop="toggle">{{ expanded ? 'Collapse' : 'Expand' }}</button>
    </div>
    <div class="daily-body" :class="{ collapsed: !expanded }">
      <!-- Warning / Confirmation Banner -->
      <div v-if="!consistency?.is_consistent && issues.length" class="banner banner-warn">
        <span class="banner-icon">⚠️</span>
        <div class="banner-text">
          <strong>Data Inconsistency Detected</strong>
          <span>{{ consistency.only_daily_report }} item(s) only in Daily Report, {{ consistency.only_fa_tracker }} item(s) only in FA Tracker</span>
        </div>
      </div>
      <div v-else-if="consistency?.is_consistent && issues.length" class="banner banner-ok">
        <span class="banner-icon">✅</span>
        <div class="banner-text">
          <strong>Data Consistent</strong>
          <span>All {{ issues.length }} issue(s) confirmed in both sources</span>
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
            <tr
              v-for="(row, i) in issues"
              :key="i"
              :class="{ 'row-warn': row.source !== 'matched' }"
            >
              <td>{{ i + 1 }}</td>
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
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

defineProps({
  consistency: { type: Object, default: () => ({}) },
  issues: { type: Array, default: () => [] },
})

const expanded = ref(true)
const toggle = () => { expanded.value = !expanded.value }

function sourceLabel(s) {
  const map = {
    matched: 'Consistent',
    only_daily_report: 'Daily Report only',
    only_fa_tracker: 'FA Tracker only',
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

.type-spec { color: var(--color-danger); font-weight: 600; }
.type-strife { color: #d97706; font-weight: 600; }

.source-badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 500; white-space: nowrap;
}
.source-matched { background: #d4edda; color: #155724; }
.source-only_daily_report { background: #fff3cd; color: #856404; }
.source-only_fa_tracker { background: #f8d7da; color: #721c24; }
</style>
