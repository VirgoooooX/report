<template>
  <div class="dashboard-heatmap">
    <div v-if="!crossData" class="loading-wrap loading-wrap-lg">
      <a-spin size="large" />
    </div>
    <div v-else-if="!crossData.matrix?.length" class="empty-wrap">
      <a-empty :description="t('common.noData')" />
    </div>
    <div v-else class="heatmap-wrap">
      <table class="heatmap-table">
        <thead>
          <tr>
            <th class="corner-th">{{ dim1Label }}</th>
            <th
              v-for="value in crossData.dim2Values"
              :key="'h-' + value"
              class="col-th"
            >
              {{ truncate(value, 20) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="value1 in crossData.dim1Values" :key="value1">
            <td class="row-th">{{ truncate(value1, 25) }}</td>
            <td
              v-for="value2 in crossData.dim2Values"
              :key="value1 + '|' + value2"
              :class="['heat-cell', { clickable: getCell(value1, value2) }]"
              :style="{ backgroundColor: cellBg(value1, value2) }"
              @click="onCellClick(value1, value2)"
              @mouseenter="onCellHover($event, value1, value2)"
              @mouseleave="hovered = null"
            >
              {{ cellDisplay(value1, value2) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="hovered"
      class="heat-tooltip"
      :style="{ left: tooltipPos.x + 'px', top: tooltipPos.y + 'px' }"
    >
      <div class="tt-row"><span>{{ t('failureAnalysis.totalFailures') }}</span><b>{{ hovered.totalCount }}</b></div>
      <div class="tt-row"><span>{{ t('failureAnalysis.specFailureRateLabel') }}</span><b class="c-red">{{ hovered.specRate.toFixed(2) }}%</b></div>
      <div class="tt-row"><span>{{ t('failureAnalysis.strifeFailureRateLabel') }}</span><b class="c-yellow">{{ hovered.strifeRate.toFixed(2) }}%</b></div>
      <div class="tt-row"><span>{{ t('failureAnalysis.percentage') }}</span><b class="c-green">{{ hovered.percentage.toFixed(2) }}%</b></div>
    </div>

    <a-modal
      v-model:open="detailVisible"
      :title="detailTitle"
      width="900px"
      :footer="null"
      @cancel="detailVisible = false"
    >
      <div v-if="detailLoading" class="modal-loading"><a-spin /></div>
      <div v-else-if="detailError" class="modal-error">{{ detailError }}</div>
      <div v-else-if="!detailRecords.length" class="modal-empty">{{ t('failureAnalysis.noRecordsFound') }}</div>
      <a-table
        v-else
        :data-source="sortedDetailRecords"
        :columns="detailColumns"
        row-key="fa_num"
        size="small"
        :pagination="false"
        :scroll="{ y: detailScrollHeight }"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, h, reactive, ref } from 'vue'
import AEmpty from 'ant-design-vue/es/empty'
import AModal from 'ant-design-vue/es/modal'
import ASpin from 'ant-design-vue/es/spin'
import ATable from 'ant-design-vue/es/table'
import ATag from 'ant-design-vue/es/tag'
import { requestJson } from '@/composables/useApi'
import { useI18n } from '@/i18n/useI18n'
import {
  getClampedTooltipPosition,
  heatmapBackgroundColor,
  heatmapCellDisplay,
} from '@/views/failureDisplay'
import { getFailureTheme } from '@/views/failureTheme'

const props = defineProps({
  crossData: { type: Object, default: null }
})

const { t } = useI18n()

const dim1Label = t('failureMatrix.dimLocation')
const dim2Label = t('failureMatrix.dimConfig')
const displayMode = 'spec'
const theme = computed(() => document.documentElement.dataset.theme || 'light')
const failureTheme = computed(() => getFailureTheme(theme.value))

const hovered = ref(null)
const tooltipPos = reactive({ x: 0, y: 0 })

const detailVisible = ref(false)
const detailTitle = ref('')
const detailLoading = ref(false)
const detailError = ref(null)
const detailRecords = ref([])

const detailColumns = [
  { title: t('failureMatrix.colFaNum'), dataIndex: 'fa_num', width: 50 },
  { title: t('failureMatrix.colSn'), dataIndex: 'sn', width: 110 },
  { title: t('failureMatrix.colWf'), dataIndex: 'wf', width: 50 },
  { title: t('failureMatrix.colConfig'), dataIndex: 'config', width: 70 },
  { title: t('failureMatrix.colTest'), dataIndex: 'failed_test', width: 140, ellipsis: true },
  {
    title: t('failureMatrix.colType'),
    dataIndex: 'failure_type',
    width: 80,
    customRender: ({ text }) => {
      const val = (text || '').toLowerCase()
      let color = 'default'
      if (val.includes('spec')) color = 'red'
      else if (val.includes('strife')) color = 'orange'
      return h(ATag, { color, style: 'margin:0;font-weight:600' }, () => text || '-')
    },
  },
  { title: t('failureMatrix.colSymptom'), dataIndex: 'symptom', width: 110, ellipsis: true },
  { title: t('failureMatrix.colLocation'), dataIndex: 'location', width: 90 },
  { title: t('failureMatrix.colFaStatus'), dataIndex: 'fa_status', width: 90 },
]

// Sort detail records: spec first, then strife, then others
const sortedDetailRecords = computed(() => {
  const records = [...detailRecords.value]
  const typeOrder = (type) => {
    const val = (type || '').toLowerCase()
    if (val.includes('spec')) return 0
    if (val.includes('strife')) return 1
    return 2
  }
  records.sort((a, b) => typeOrder(a.failure_type) - typeOrder(b.failure_type))
  return records
})

// Smart modal height based on record count
const detailScrollHeight = computed(() => {
  const count = detailRecords.value.length
  const rowHeight = 40
  const minHeight = 200
  const maxHeight = Math.min(600, Math.round(window.innerHeight * 0.6))
  const calculated = count * rowHeight
  return Math.max(minHeight, Math.min(calculated, maxHeight))
})

const matrixMap = computed(() => {
  const map = {}
  if (props.crossData?.matrix) {
    for (const cell of props.crossData.matrix) {
      map[`${cell.dim1Value}|${cell.dim2Value}`] = cell
    }
  }
  return map
})

const maxTotal = computed(() => Math.max(...(props.crossData?.matrix ?? []).map(cell => cell.totalCount), 1))

function getCell(value1, value2) {
  return matrixMap.value[`${value1}|${value2}`] || null
}

function cellDisplay(value1, value2) {
  return heatmapCellDisplay(getCell(value1, value2), displayMode)
}

function cellBg(value1, value2) {
  return heatmapBackgroundColor(
    getCell(value1, value2),
    displayMode,
    maxTotal.value,
    failureTheme.value,
  )
}

function truncate(value, maxLength) {
  if (!value) return ''
  return value.length > maxLength ? value.substring(0, maxLength - 1) + '...' : value
}

function onCellHover(event, value1, value2) {
  const cell = getCell(value1, value2)
  if (!cell) {
    hovered.value = null
    return
  }

  hovered.value = cell
  const nextPosition = getClampedTooltipPosition(
    { x: event.clientX, y: event.clientY },
    { width: window.innerWidth, height: window.innerHeight },
  )
  tooltipPos.x = nextPosition.left
  tooltipPos.y = nextPosition.top
}

async function openDetail(filters) {
  detailVisible.value = true
  detailLoading.value = true
  detailError.value = null
  detailRecords.value = []

  const params = new URLSearchParams(filters).toString()
  try {
    const data = await requestJson(`/api/fa/detail?${params}`)
    detailRecords.value = data.records || []
  } catch (error) {
    detailError.value = error.message
  } finally {
    detailLoading.value = false
  }
}

function onCellClick(value1, value2) {
  if (!getCell(value1, value2)) return

  detailTitle.value = `${dim1Label}: ${truncate(value1, 30)} x ${dim2Label}: ${truncate(value2, 30)}`
  openDetail({ location: value1, config: value2 })
}
</script>

<style scoped>
.dashboard-heatmap {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 100%;
}

.loading-wrap,
.empty-wrap {
  min-height: 320px;
  display: grid;
  place-items: center;
  padding: var(--space-xl);
  color: var(--text-muted);
}

.loading-wrap-lg {
  min-height: 360px;
}

.heatmap-wrap {
  flex: 1;
  min-height: 320px;
  overflow: auto;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.heatmap-table {
  border-collapse: separate;
  border-spacing: 0;
  width: max-content;
  min-width: 100%;
  font-size: 13px;
  font-family: var(--font-display);
  background: var(--bg-card);
}

.heatmap-table thead th {
  position: sticky;
  top: 0;
  z-index: 5;
}

.heatmap-table th,
.heatmap-table td {
  border: 1px solid var(--border-light);
  padding: 10px 8px;
  text-align: center;
  white-space: nowrap;
}

.corner-th,
.row-th {
  position: sticky;
  left: 0;
}

.corner-th {
  z-index: 7;
  min-width: 160px;
  background: var(--bg-row-hover);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 800;
}

.col-th {
  min-width: 88px;
  background: var(--bg-row-stripe);
  color: var(--text-secondary);
  font-weight: 700;
}

.row-th {
  z-index: 4;
  min-width: 160px;
  max-width: 300px;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  background: var(--bg-row-stripe);
  color: var(--text-primary);
  font-weight: 700;
}

.heat-cell {
  min-width: 80px;
  font-weight: 600;
  font-size: 12px;
  transition: all 0.2s ease;
  color: var(--text-primary);
  cursor: default;
}

.heat-cell.clickable {
  cursor: pointer;
}

.heat-cell.clickable:hover {
  border-radius: 3px;
  box-shadow:
    inset 0 0 0 2px var(--border-focus),
    0 0 0 3px color-mix(in srgb, var(--border-focus) 18%, transparent);
}

.heat-tooltip {
  position: fixed;
  z-index: 1000;
  min-width: 220px;
  max-width: min(320px, calc(100vw - 28px));
  padding: 14px 18px;
  pointer-events: none;
  background: var(--bg-card);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-modal);
  color: var(--text-primary);
  font-size: 12px;
}

.tt-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.tt-row:last-child {
  margin-bottom: 0;
}

.tt-row span {
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 13px;
}

.tt-row b {
  font-weight: 700;
  font-size: 14px;
  color: var(--accent-steel);
}

.c-red {
  color: #e84c3d !important;
}

.c-yellow {
  color: #faad14 !important;
}

.c-green {
  color: #52c41a !important;
}

.modal-loading,
.modal-error,
.modal-empty {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}

.dashboard-heatmap :deep(.ant-table-tbody > tr.ant-table-row:hover > td) {
  background: var(--bg-row-hover) !important;
}
</style>
