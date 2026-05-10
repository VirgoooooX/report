<template>
  <section class="card schedule-sheet">
    <div class="sheet-scroll">
      <table>
        <thead>
          <tr>
            <th class="sticky-col test-col">WF / Config / Test</th>
            <th
              v-for="column in dateColumns"
              :key="column.date"
              class="day-head"
              :class="{ saturday: column.isSaturday }"
            >
              <span>{{ column.monthDay }}</span>
              <small>{{ column.weekday }}</small>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in groups" :key="group.wf_num">
            <tr class="wf-row">
              <td class="sticky-col wf-cell" :colspan="1 + dateColumns.length">
                <button type="button" class="wf-toggle" @click="toggleWf(group.wf_num)">
                  <span class="chevron" :class="{ closed: !isOpen(group.wf_num) }">⌄</span>
                  <span class="wf-pill">WF{{ group.wf_num }}</span>
                  <span class="wf-name">{{ group.wf_name }}</span>
                  <span class="wf-count">{{ group.rows.length }} configs</span>
                </button>
              </td>
            </tr>

            <tr
              v-for="row in group.rows"
              v-show="isOpen(group.wf_num)"
              :key="rowKey(row)"
              class="test-row"
            >
              <td class="sticky-col test-cell">
                <span class="cfg-badge" :style="badgeStyle(row.config)">{{ row.config }}</span>
                <div class="test-copy">
                  <strong>{{ summaryLabel(row) }}</strong>
                  <small>{{ row.test_count }} tests · {{ row.planned_start_date }} → {{ row.planned_end_date }}</small>
                </div>
              </td>

              <td
                v-for="column in dateColumns"
                :key="`${rowKey(row)}-${column.date}`"
                class="day-cell"
                :style="cellStyle(row, column)"
                :class="cellClass(row, column)"
                :title="cellTitle(row, column)"
              >
                <span v-if="startCount(row, column.date)" class="edge-flag start-flag">
                  {{ startCount(row, column.date) }}
                </span>
                <span v-if="endCount(row, column.date)" class="edge-flag end-flag">
                  {{ endCount(row, column.date) }}
                </span>
                <span
                  v-for="(cp, index) in visibleCpMarkers(row, column.date)"
                  :key="`${rowKey(row)}-${column.date}-${cp.test_idx}-${cp.cp_idx}`"
                  class="cp-dot"
                  :style="cpDotStyle(index)"
                >
                  <i></i>
                </span>
                <span v-if="hiddenCpCount(row, column.date)" class="cp-more">
                  +{{ hiddenCpCount(row, column.date) }}
                </span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { reactive } from 'vue'

const props = defineProps({
  groups: { type: Array, default: () => [] },
  dateColumns: { type: Array, default: () => [] },
  configColors: { type: Object, default: () => ({}) }
})

const expandedWfs = reactive({})

function rowKey(row) {
  return row.lane_key || `${row.wf_num}-${row.config}-${row.test_idx}`
}

function isOpen(wfNum) {
  return expandedWfs[wfNum] !== false
}

function toggleWf(wfNum) {
  expandedWfs[wfNum] = !isOpen(wfNum)
}

function cpsOnDate(row, date) {
  return laneTests(row).flatMap((test) => (test.visible_cps || [])
    .filter((cp) => cp.planned_date === date)
    .map((cp) => ({ ...cp, test_idx: test.test_idx, test_name: test.test_name })))
}

function cellClass(row, column) {
  const active = testsOnDate(row, column.date).length > 0
  return {
    saturday: column.isSaturday,
    active,
    start: startCount(row, column.date) > 0,
    end: endCount(row, column.date) > 0
  }
}

function cellTitle(row, column) {
  const cps = cpsOnDate(row, column.date).map((cp) => cp.cp_name).join(', ')
  const tests = testsOnDate(row, column.date).map((test) => test.test_name).join(' / ')
  if (!tests && !cps) return column.date
  return `${column.date} · ${tests || row.test_name}${cps ? ` · ${cps}` : ''}`
}

function cellStyle(row, column) {
  if (!testsOnDate(row, column.date).length) return {}
  const color = barColor(row.config)
  return {
    '--schedule-color': color,
    '--schedule-soft': `${color}22`
  }
}

function barColor(config) {
  return props.configColors[config] || props.configColors.overall || '#4f6f8f'
}

function badgeStyle(config) {
  const color = barColor(config)
  return {
    color,
    borderColor: `${color}40`,
    backgroundColor: `${color}12`
  }
}

function laneTests(row) {
  return row.tests?.length ? row.tests : [row]
}

function testsOnDate(row, date) {
  return laneTests(row).filter((test) => (test.days || []).includes(date))
}

function startsOnDate(row, date) {
  return laneTests(row).filter((test) => (test.days?.[0] || test.planned_start_date) === date)
}

function endsOnDate(row, date) {
  return laneTests(row).filter((test) => (test.days?.[test.days.length - 1] || test.planned_end_date) === date)
}

function startCount(row, date) {
  return startsOnDate(row, date).length
}

function endCount(row, date) {
  return endsOnDate(row, date).length
}

function visibleCpMarkers(row, date) {
  return cpsOnDate(row, date).slice(0, 2)
}

function hiddenCpCount(row, date) {
  return Math.max(0, cpsOnDate(row, date).length - 2)
}

function cpDotStyle(index) {
  return {
    '--cp-offset': `${8 + index * 11}px`
  }
}

function summaryLabel(row) {
  const names = row.test_names || []
  if (!names.length) return row.test_name
  if (names.length === 1) return names[0]
  if (names.length === 2) return `${names[0]} / ${names[1]}`
  return `${names[0]} / ${names[1]} +${names.length - 2}`
}
</script>

<style scoped>
.schedule-sheet {
  overflow: hidden;
}

.sheet-scroll {
  overflow: auto;
  max-height: calc(100vh - 270px);
}

table {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

th,
td {
  border-right: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
}

thead th {
  position: sticky;
  top: 0;
  z-index: 5;
  height: 48px;
  padding: 4px 6px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  text-align: center;
  vertical-align: middle;
}

.day-head {
  width: 56px;
}

.day-head span,
.day-head small {
  display: block;
  line-height: 1.15;
}

.day-head small {
  margin-top: 3px;
  color: var(--text-muted);
  font-family: var(--font-display);
  font-size: 10px;
}

.sticky-col {
  position: sticky;
  left: 0;
  z-index: 4;
}

thead .sticky-col {
  z-index: 7;
}

.test-col {
  width: 320px;
  min-width: 320px;
  padding: 0 14px;
  text-align: left;
  background: var(--bg-card);
}

.wf-row td {
  height: 40px;
  background: var(--bg-row-stripe);
}

.wf-cell {
  padding: 0;
}

.wf-toggle {
  width: 320px;
  height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 0;
  background: var(--bg-row-stripe);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
}

.chevron {
  width: 14px;
  color: var(--text-muted);
  transition: transform var(--duration-fast);
}

.chevron.closed {
  transform: rotate(-90deg);
}

.wf-pill,
.cfg-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 23px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.wf-pill {
  min-width: 56px;
  background: var(--bg-tag);
  color: var(--text-secondary);
}

.wf-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}

.wf-count {
  color: var(--text-muted);
  font-size: 12px;
}

.test-row {
  height: 58px;
}

.test-cell {
  width: 320px;
  min-width: 320px;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 58px;
  padding: 7px 12px;
  background: var(--bg-card);
}

.cfg-badge {
  min-width: 58px;
  border: 1px solid;
}

.test-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.test-copy strong,
.test-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.test-copy strong {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}

.test-copy small {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
}

.day-cell {
  width: 56px;
  height: 58px;
  padding: 0;
  vertical-align: middle;
  background: var(--bg-card);
  position: relative;
}

.day-head.saturday,
.day-cell.saturday {
  background: color-mix(in srgb, var(--color-warning-bg) 42%, var(--bg-card));
}

.day-cell.active {
  background:
    linear-gradient(to bottom, transparent 22px, var(--schedule-soft) 22px, var(--schedule-soft) 44px, transparent 44px),
    var(--bg-card);
}

.day-cell.active.saturday {
  background:
    linear-gradient(to bottom, transparent 22px, var(--schedule-soft) 22px, var(--schedule-soft) 44px, transparent 44px),
    color-mix(in srgb, var(--color-warning-bg) 42%, var(--bg-card));
}

.day-cell.start {
  box-shadow: inset 3px 0 0 var(--schedule-color);
}

.day-cell.end {
  box-shadow: inset -3px 0 0 var(--schedule-color);
}

.edge-flag {
  position: absolute;
  top: 24px;
  z-index: 2;
  min-width: 14px;
  height: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--schedule-color) 30%, transparent);
  background: var(--bg-card);
  color: var(--schedule-color);
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  pointer-events: none;
}

.start-flag {
  left: 3px;
}

.end-flag {
  right: 3px;
}

.cp-dot,
.cp-more {
  position: absolute;
  z-index: 3;
  pointer-events: none;
}

.cp-dot {
  left: 50%;
  top: var(--cp-offset);
  transform: translateX(-50%);
}

.cp-dot i {
  display: block;
  width: 8px;
  height: 8px;
  border: 1px solid var(--bg-card);
  border-radius: 50%;
  background: var(--schedule-color);
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.16);
}

.cp-more {
  right: 3px;
  top: 5px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 9px;
}

@media (max-width: 720px) {
  .sheet-scroll {
    max-height: none;
  }

  .test-col,
  .test-cell,
  .wf-toggle {
    width: 260px;
    min-width: 260px;
  }
}
</style>
