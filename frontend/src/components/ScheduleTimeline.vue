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
              :class="{ sunday: column.isSunday, today: isTodayColumn(column) }"
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
                  v-for="segment in planSegmentsOnDate(row, column.date)"
                  :key="`${rowKey(row)}-${column.date}-plan-${segment.test_idx}`"
                  class="plan-progress-rail"
                  :class="{
                    'plan-progress-start': isTestStartDate(segment, column.date),
                    'plan-progress-end': isTestEndDate(segment, column.date)
                  }"
                ></span>

                <span
                  v-for="segment in actualSegmentsOnDate(row, column.date)"
                  :key="`${rowKey(row)}-${column.date}-actual-${segment.test_idx}`"
                  class="actual-progress-rail"
                  :class="{
                    'actual-progress-start': isActualSegmentStartDate(segment, column.date),
                    'actual-progress-end': isActualSegmentEndDate(segment, row, column.date),
                    'actual-progress-tip': isActualProgressEndDate(row, column.date)
                  }"
                ></span>

                <span
                  v-if="edgeMarkerOnDate(row, column.date)"
                  class="edge-marker"
                  :class="`edge-marker-${edgeMarkerOnDate(row, column.date).type}`"
                >{{ edgeMarkerOnDate(row, column.date).label }}</span>

                <span
                  v-for="(cp, index) in displayCpsOnDate(row, column.date)"
                  :key="`${rowKey(row)}-${column.date}-${cp.test_idx}-${cp.cp_idx}`"
                  class="cp-text"
                  :class="cpMarkerClass(row, cp)"
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

function testStartDate(test) {
  return test.planned_start_date || test.days?.[0] || ''
}

function testEndDate(test) {
  return test.planned_end_date || test.days?.[test.days.length - 1] || ''
}

function isTestInRange(test, date) {
  const start = testStartDate(test)
  const end = testEndDate(test)
  return start && end && date >= start && date <= end
}

function isTestStartDate(test, date) {
  return testStartDate(test) === date
}

function isTestEndDate(test, date) {
  return testEndDate(test) === date
}

function planSegmentsOnDate(row, date) {
  return laneTests(row).filter((test) => isTestInRange(test, date))
}

function actualSegmentEndDate(test, row) {
  const progressEnd = row.actual_progress?.end_date
  if (!progressEnd || progressEnd < testStartDate(test)) return ''

  const days = test.days?.length
    ? test.days.filter((day) => day <= progressEnd)
    : [testStartDate(test), testEndDate(test)].filter((day) => day && day <= progressEnd)
  return days[days.length - 1] || ''
}

function actualSegmentsOnDate(row, date) {
  return laneTests(row).filter((test) => {
    const end = actualSegmentEndDate(test, row)
    return end && isTestInRange(test, date) && date <= end
  })
}

function actualProgressEndDate(row) {
  const endDates = laneTests(row)
    .map((test) => actualSegmentEndDate(test, row))
    .filter(Boolean)
    .sort()
  return endDates[endDates.length - 1] || ''
}

function isActualSegmentStartDate(test, date) {
  return testStartDate(test) === date
}

function isActualSegmentEndDate(test, row, date) {
  return actualSegmentEndDate(test, row) === date
}

function isDateInRange(row, date) {
  return planSegmentsOnDate(row, date).length > 0
}

function cellClass(row, column) {
  const onDay = testsOnDate(row, column.date).length > 0
  const active = onDay || (column.isSunday && isDateInRange(row, column.date))
  return {
    sunday: column.isSunday,
    today: isTodayColumn(column),
    active,
    'actual-progress': actualSegmentsOnDate(row, column.date).length > 0,
    hasEdgeMarker: Boolean(edgeMarkerOnDate(row, column.date)),
    start: startCount(row, column.date) > 0,
    end: endCount(row, column.date) > 0
  }
}

function cellTitle(row, column) {
  const tests = testsOnDate(row, column.date).map((test) => test.test_name).join(' / ')
  const details = [column.date]
  if (tests) details.push(tests || row.test_name)
  if (isActualProgressEndDate(row, column.date)) {
    details.push(`Completed: ${row.actual_progress?.current_cp_name || `CP${row.actual_progress?.current_cp_idx ?? ''}`}`)
  }
  return details.filter(Boolean).join('\n')
}

function cellStyle(row, column) {
  return {}
}

function barColor(config) {
  return props.configColors[config] || props.configColors.overall || '#4f6f8f'
}

function badgeStyle(config) {
  return {}
}

function laneTests(row) {
  return row.tests?.length ? row.tests : [row]
}

function testsOnDate(row, date) {
  return planSegmentsOnDate(row, date)
}

function startsOnDate(row, date) {
  return laneTests(row).filter((test) => isTestStartDate(test, date))
}

function endsOnDate(row, date) {
  return laneTests(row).filter((test) => isTestEndDate(test, date))
}

function startCount(row, date) {
  return startsOnDate(row, date).length
}

function endCount(row, date) {
  return endsOnDate(row, date).length
}

function isActualProgressEndDate(row, date) {
  return actualProgressEndDate(row) === date
}

function localIsoDate(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function isTodayColumn(column) {
  return column.date === localIsoDate()
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

function cpMarkerClass(row, cp) {
  const progress = row.actual_progress
  if (!progress || progress.current_cp_idx == null) {
    return { 'cp-completed': false, 'cp-pending': true }
  }
  if (progress.is_complete) {
    return { 'cp-completed': true, 'cp-pending': false }
  }
  const completed = cp.cp_idx <= progress.current_cp_idx
  return { 'cp-completed': completed, 'cp-pending': !completed }
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
  --plan-color: var(--accent-steel);
  --actual-color: var(--chart-r2cnm);
  --today-color: var(--color-danger);

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
  background: var(--bg-card);
  border-top: 1px solid var(--border-card);
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
  background: var(--bg-card);
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
  border: 1px solid var(--border-card);
  background: transparent;
  color: var(--text-primary);
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
  background: color-mix(in srgb, var(--text-muted) 4%, var(--bg-card));
  border-width: 1px;
  border-color: transparent;
  position: relative;
}

.day-head.sunday {
  background: color-mix(in srgb, var(--text-muted) 8%, var(--bg-card));
  color: var(--text-muted);
}

.day-head.today {
  color: var(--today-color);
  font-weight: 700;
}

.day-cell.today::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 2px;
  transform: translateX(-50%);
  background: var(--today-color);
  z-index: 2;
  pointer-events: none;
}

.day-cell.active {
  background: color-mix(in srgb, var(--text-muted) 4%, var(--bg-card));
}

.day-cell.actual-progress {
  background: color-mix(in srgb, var(--text-muted) 4%, var(--bg-card));
}

.plan-progress-rail {
  position: absolute;
  top: 4px;
  left: -1px;
  right: -1px;
  z-index: 1;
  height: 28px;
  background: color-mix(in srgb, var(--plan-color) 42%, var(--bg-card));
  pointer-events: none;
}

.plan-progress-start {
  left: 7px;
  border-top-left-radius: 999px;
  border-bottom-left-radius: 999px;
}

.plan-progress-end {
  right: 7px;
  border-top-right-radius: 999px;
  border-bottom-right-radius: 999px;
}

.actual-progress-rail {
  position: absolute;
  top: 4px;
  left: -1px;
  right: -1px;
  z-index: 2;
  height: 28px;
  background: color-mix(in srgb, var(--actual-color) 10%, var(--bg-card));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--actual-color) 24%, var(--bg-card));
  pointer-events: none;
}

.actual-progress-start {
  left: 7px;
  border-top-left-radius: 999px;
  border-bottom-left-radius: 999px;
}

.actual-progress-end {
  right: 7px;
  border-top-right-radius: 999px;
  border-bottom-right-radius: 999px;
}

.actual-progress-tip::after {
  content: '';
  position: absolute;
  top: 50%;
  right: -4px;
  z-index: 4;
  width: 11px;
  height: 11px;
  border: 2px solid var(--bg-card);
  border-radius: 50%;
  background: color-mix(in srgb, var(--actual-color) 72%, var(--bg-card));
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--actual-color) 24%, var(--bg-card));
  transform: translateY(-50%);
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
  background: color-mix(in srgb, var(--plan-color) 16%, var(--bg-card));
  color: var(--plan-color);
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
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  cursor: help;
}

.cp-text.cp-pending {
  background: var(--plan-color);
  color: #ffffff;
  opacity: 1;
}

.cp-text.cp-completed {
  background: transparent;
  border: 1px solid var(--plan-color);
  color: var(--plan-color);
  opacity: 0.6;
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
