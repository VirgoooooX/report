<template>
  <section class="schedule-sheet">
    <div ref="sheetScroll" class="sheet-scroll">
      <table>
        <thead>
          <tr>
            <th class="sticky-col test-col">Config</th>
            <th
              v-for="column in dateColumns"
              :key="column.date"
              class="day-head"
              :class="{ sunday: column.isSunday }"
              :data-date="column.date"
            >
              <span>{{ column.monthDay }}</span>
              <small>{{ column.weekday }}</small>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in groups" :key="group.wf_num">
            <tr class="wf-row">
              <td class="sticky-col wf-cell">
                <button type="button" class="wf-toggle" @click="toggleWf(group.wf_num)">
                  <svg class="chevron" :class="{ closed: !isOpen(group.wf_num) }" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                  <span class="wf-pill">WF{{ group.wf_num }}</span>
                  <span class="wf-name">{{ group.wf_name }}</span>
                  <span class="wf-count">{{ group.rows.length }} configs</span>
                </button>
              </td>
              <td class="wf-fill" :colspan="dateColumns.length"></td>
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
                  <small>→ {{ row.planned_end_date }}</small>
                </div>
              </td>

              <td
                v-for="column in dateColumns"
                :key="`${rowKey(row)}-${column.date}`"
                class="day-cell"
                :style="cellStyle(row, column)"
                :class="cellClass(row, column)"
                :title="cellTitle(row, column)"
                :data-date="column.date"
              >
                <span
                  v-if="edgeMarkerOnDate(row, column.date)"
                  class="edge-marker"
                  :class="`edge-marker-${edgeMarkerOnDate(row, column.date).type}`"
                >{{ edgeMarkerOnDate(row, column.date).label }}</span>

                <span
                  v-for="(cp, index) in displayCpsOnDate(row, column.date)"
                  :key="`${rowKey(row)}-${column.date}-${cp.test_idx}-${cp.cp_idx}`"
                  class="cp-text"
                  :style="cpDotStyle(index, displayCpsOnDate(row, column.date).length)"
                  :title="cp.cp_title || cp.cp_name"
                >{{ cp.display_cp_idx ?? cp.cp_idx }}</span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref, watch } from 'vue'
import { summarizeDailyCpMarkers } from '@/views/scheduleDisplay'

const props = defineProps({
  groups: { type: Array, default: () => [] },
  dateColumns: { type: Array, default: () => [] },
  configColors: { type: Object, default: () => ({}) }
})

const expandedWfs = reactive({})
const sheetScroll = ref(null)

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

function displayCpsOnDate(row, date) {
  return summarizeDailyCpMarkers(cpsOnDate(row, date))
}

function edgeMarkerOnDate(row, date) {
  return (row.edge_markers || []).find((marker) => marker.date === date) || null
}

function isDateInRange(row, date) {
  return laneTests(row).some((test) => {
    const start = test.planned_start_date || test.days?.[0]
    const end = test.planned_end_date || test.days?.[test.days.length - 1]
    return start && end && date >= start && date <= end
  })
}

function cellClass(row, column) {
  const onDay = testsOnDate(row, column.date).length > 0
  const active = onDay || (column.isSunday && isDateInRange(row, column.date))
  return {
    sunday: column.isSunday,
    active,
    'actual-progress': isActualProgressDate(row, column.date),
    hasEdgeMarker: Boolean(edgeMarkerOnDate(row, column.date)),
    start: startCount(row, column.date) > 0,
    end: endCount(row, column.date) > 0
  }
}

function cellTitle(row, column) {
  const tests = testsOnDate(row, column.date).map((test) => test.test_name).join(' / ')
  if (!tests) return column.date
  return `${column.date} · ${tests || row.test_name}`
}

function cellStyle(row, column) {
  const onDay = testsOnDate(row, column.date).length > 0
  const inRange = onDay || isActualProgressDate(row, column.date) || (column.isSunday && isDateInRange(row, column.date))
  if (!inRange) return {}
  const color = barColor(row.config)
  return {
    '--schedule-color': color,
    '--schedule-soft': `${color}22`,
    '--actual-progress-soft': `${color}33`
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

function isActualProgressDate(row, date) {
  const progressEnd = row.actual_progress?.end_date
  if (!row.planned_start_date || !progressEnd) return false
  return date >= row.planned_start_date && date <= progressEnd
}

function localIsoDate(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

async function scrollTodayIntoView() {
  await nextTick()
  const container = sheetScroll.value
  if (!container) return

  const today = localIsoDate()
  const target = container.querySelector(`.day-head[data-date="${today}"]`)
  if (!target) return

  const targetCenter = target.offsetLeft + target.offsetWidth / 2
  container.scrollLeft = Math.max(0, targetCenter - container.clientWidth / 2)
}

function cpDotStyle(index, total) {
  if (total <= 3) {
    const textWidth = 18
    const gap = 4
    const totalWidth = total * textWidth + (total - 1) * gap
    const offset = (68 - totalWidth) / 2 + index * (textWidth + gap)
    return { left: `${Math.max(2, offset)}px` }
  }

  const columns = Math.min(4, Math.ceil(Math.sqrt(total)))
  const cellWidth = 16
  const cellHeight = 15
  const gapX = 1
  const gapY = 1
  const row = Math.floor(index / columns)
  const column = index % columns
  const rows = Math.ceil(total / columns)
  const totalWidth = columns * cellWidth + (columns - 1) * gapX
  const totalHeight = rows * cellHeight + (rows - 1) * gapY
  return {
    left: `${Math.max(1, (68 - totalWidth) / 2 + column * (cellWidth + gapX))}px`,
    top: `${Math.max(1, (36 - totalHeight) / 2 + row * (cellHeight + gapY))}px`,
    transform: 'none'
  }
}

onMounted(scrollTodayIntoView)
watch(() => props.dateColumns.map((column) => column.date).join('|'), scrollTodayIntoView)
</script>

<style scoped>
.schedule-sheet {
  min-height: 0;
  flex: 1;
  overflow: hidden;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-sm);
  background: var(--bg-card);
}

.sheet-scroll {
  height: 100%;
  overflow-x: auto;
  overflow-y: auto;
  scrollbar-gutter: stable both-edges;
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
}

.sheet-scroll:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.sheet-scroll::-webkit-scrollbar {
  width: 6px;
  height: 0;
}

.sheet-scroll:hover::-webkit-scrollbar {
  height: 6px;
}

.sheet-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.sheet-scroll::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 3px;
}

.sheet-scroll:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.sheet-scroll:hover::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
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
  height: 36px;
  padding: 2px 6px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  text-align: center;
  vertical-align: middle;
  box-shadow: 0 1px 0 var(--border-card);
}

.day-head {
  width: 68px;
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
  box-shadow: 1px 0 0 var(--border-card), 8px 0 14px rgba(15, 23, 42, 0.06);
}

thead .sticky-col {
  z-index: 7;
  box-shadow: 1px 0 0 var(--border-card), 8px 0 14px rgba(15, 23, 42, 0.06), 0 1px 0 var(--border-card);
}

.test-col {
  width: 160px;
  min-width: 160px;
  padding: 0 10px;
  text-align: center;
  background: var(--bg-card);
}

.wf-row td {
  height: 34px;
  background: color-mix(in srgb, var(--border-card) 40%, var(--bg-card));
}

.wf-cell {
  padding: 0;
  overflow: visible;
}

.wf-fill {
  padding: 0;
}

.wf-toggle {
  position: absolute;
  left: 0;
  top: 0;
  z-index: 1;
  width: max-content;
  min-width: 100%;
  height: 34px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 0;
  background: color-mix(in srgb, var(--border-card) 40%, var(--bg-card));
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
}

.chevron {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
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
  height: 20px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

.wf-pill {
  min-width: 52px;
  height: 22px;
  background: var(--accent-steel);
  color: #fff;
  font-size: 11px;
}

.wf-name {
  white-space: nowrap;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}

.wf-count {
  height: 18px;
  display: inline-flex;
  align-items: center;
  padding: 0 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 10px;
}

.test-row {
  height: 36px;
}

.test-cell {
  width: 160px;
  min-width: 160px;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 2px 8px;
  background: var(--bg-card);
}

.cfg-badge {
  min-width: 46px;
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
  width: 68px;
  height: 36px;
  padding: 0;
  vertical-align: middle;
  background: var(--bg-card);
  position: relative;
}

.day-head.sunday,
.day-cell.sunday {
  background: color-mix(in srgb, var(--text-muted) 8%, var(--bg-card));
  color: var(--text-muted);
}

.day-cell.active {
  background:
    linear-gradient(to bottom, transparent 4px, var(--schedule-soft) 4px, var(--schedule-soft) 32px, transparent 32px),
    var(--bg-card);
}

.day-cell.active.sunday {
  background:
    linear-gradient(to bottom, transparent 4px, var(--schedule-soft) 4px, var(--schedule-soft) 32px, transparent 32px),
    color-mix(in srgb, var(--text-muted) 8%, var(--bg-card));
}

.day-cell.actual-progress {
  background:
    linear-gradient(to bottom, transparent 8px, var(--actual-progress-soft) 8px, var(--actual-progress-soft) 28px, transparent 28px),
    linear-gradient(to bottom, transparent 4px, var(--schedule-soft) 4px, var(--schedule-soft) 32px, transparent 32px),
    var(--bg-card);
}

.day-cell.actual-progress.sunday {
  background:
    linear-gradient(to bottom, transparent 8px, var(--actual-progress-soft) 8px, var(--actual-progress-soft) 28px, transparent 28px),
    linear-gradient(to bottom, transparent 4px, var(--schedule-soft) 4px, var(--schedule-soft) 32px, transparent 32px),
    color-mix(in srgb, var(--text-muted) 8%, var(--bg-card));
}

.day-cell.start {
  box-shadow: inset 3px 0 0 var(--schedule-color);
}

.day-cell.end {
  box-shadow: inset -3px 0 0 var(--schedule-color);
}

.edge-marker {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  min-width: 36px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--schedule-color) 16%, var(--bg-card));
  color: var(--schedule-color);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  pointer-events: none;
}

.edge-marker-start {
  background: #ede9fe;
  color: #5b21b6;
}

.edge-marker-end {
  background: #dcfce7;
  color: #166534;
}

.cp-text {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: color-mix(in srgb, var(--schedule-color) 24%, var(--bg-card));
  color: var(--schedule-color);
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  cursor: help;
}
.cp-text:hover {
  transform: translateY(-50%) scale(1.16);
}

.cp-text[style*="transform: none"]:hover {
  transform: scale(1.16) !important;
}

@media (max-width: 720px) {
  .sheet-scroll {
    max-height: none;
  }

  .test-col,
  .test-cell {
    width: 130px;
    min-width: 130px;
  }
}
</style>
