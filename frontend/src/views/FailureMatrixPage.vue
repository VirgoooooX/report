<template>
  <div class="page-container">
    <h1 class="page-title">{{ t('failureAnalysis.title') }}</h1>

    <div class="kpi-grid">
      <div class="card kpi-card">
        <div class="kpi-content">
          <div class="kpi-title"><CalendarOutlined class="kpi-icon blue" /> {{ t('failureAnalysis.newToday') }}</div>
          <div class="kpi-value">{{ summary.todayCount ?? 0 }}</div>
          <div class="kpi-foot">
            <span class="spec-text">{{ summary.todaySpecCount ?? 0 }}F</span>
            <span class="strife-text">{{ summary.todayStrifeCount ?? 0 }}SF</span>
          </div>
        </div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-content">
          <div class="kpi-title"><BugOutlined class="kpi-icon blue" /> {{ t('failureAnalysis.totalIssues') }}</div>
          <div class="kpi-value">{{ summary.totalIssues ?? 0 }}</div>
          <div class="kpi-foot">
            <span class="spec-text">{{ summary.specIssues ?? 0 }}F</span>
            <span class="strife-text">{{ summary.strifeIssues ?? 0 }}SF</span>
          </div>
        </div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-content">
          <div class="kpi-title"><WarningOutlined class="kpi-icon amber" /> {{ t('failureAnalysis.symptomTypes') }}</div>
          <div class="kpi-value">{{ summary.uniqueSymptoms ?? 0 }}</div>
          <div class="kpi-foot muted">{{ summary.uniqueSymptoms ?? 0 }} {{ t('failureAnalysis.uniqueSymptoms') }}</div>
        </div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-content">
          <div class="kpi-title"><ExperimentOutlined class="kpi-icon green" /> {{ t('failureAnalysis.wfCount') }}</div>
          <div class="kpi-value">{{ summary.uniqueWFs ?? 0 }}</div>
          <div class="kpi-foot muted">{{ summary.uniqueWFs ?? 0 }} {{ t('failureAnalysis.uniqueWfs') }}</div>
        </div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-content">
          <div class="kpi-title"><SettingOutlined class="kpi-icon red" /> {{ t('failureAnalysis.specFailureRate') }}</div>
          <div class="kpi-value">{{ displayedFailurePercent }}<span class="percent-sign">%</span></div>
          <div class="kpi-foot">
            <span class="spec-text">{{ overviewFailureText }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Top 10 Charts -->
    <a-row :gutter="16" class="chart-row">
      <a-col :span="8">
        <a-card :title="t('failureAnalysis.top10Symptom')" :bordered="false" class="section-card">
          <div v-if="loading" class="loading-wrap"><a-spin /></div>
          <div v-else-if="error" class="error-wrap">{{ error }}</div>
          <div v-else-if="!overviewData?.topSymptom?.length" class="empty-wrap">
            <a-empty :description="t('common.noData')" />
          </div>
          <div v-else class="chart-frame chart-frame-md">
            <Bar :data="symptomChartData" :options="barOptions" :plugins="[datalabelsPlugin, fixedValueLabelsPlugin]" />
          </div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card :title="t('failureAnalysis.top10Wf')" :bordered="false" class="section-card">
          <div v-if="loading" class="loading-wrap"><a-spin /></div>
          <div v-else-if="!overviewData?.topWf?.length" class="empty-wrap">
            <a-empty :description="t('common.noData')" />
          </div>
          <div v-else class="chart-frame chart-frame-md">
            <Bar :data="wfChartData" :options="barOptions" :plugins="[datalabelsPlugin, fixedValueLabelsPlugin]" />
          </div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card :title="t('failureAnalysis.top10Test')" :bordered="false" class="section-card">
          <div v-if="loading" class="loading-wrap"><a-spin /></div>
          <div v-else-if="!overviewData?.topFailedTest?.length" class="empty-wrap">
            <a-empty :description="t('common.noData')" />
          </div>
          <div v-else class="chart-frame chart-frame-md">
            <Bar :data="testChartData" :options="barOptions" :plugins="[datalabelsPlugin, fixedValueLabelsPlugin]" />
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Cross-Analysis Heatmap -->
    <a-card :bordered="false" class="section-card">
      <template #title>
        <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
          <span>{{ t('failureAnalysis.crossAnalysis') }}</span>
          <span class="control-label">{{ t('failureAnalysis.dim1') }}</span>
          <a-select v-model:value="dim1" size="small" style="width:130px" @change="loadCross">
            <a-select-option v-for="d in dimOptions" :key="d.value" :value="d.value" :disabled="d.value===dim2">{{ d.label }}</a-select-option>
          </a-select>
          <span class="control-label">{{ t('failureAnalysis.dim2') }}</span>
          <a-select v-model:value="dim2" size="small" style="width:130px" @change="loadCross">
            <a-select-option v-for="d in dimOptions" :key="d.value" :value="d.value" :disabled="d.value===dim1">{{ d.label }}</a-select-option>
          </a-select>
          <a-radio-group v-model:value="displayMode" size="small" button-style="solid">
            <a-radio-button value="spec">{{ t('failureAnalysis.spec') }}</a-radio-button>
            <a-radio-button value="strife">{{ t('failureAnalysis.strife') }}</a-radio-button>
            <a-radio-button value="total">{{ t('failureAnalysis.total') }}</a-radio-button>
          </a-radio-group>
        </div>
      </template>
      <div v-if="crossLoading" class="loading-wrap loading-wrap-lg"><a-spin size="large" /></div>
      <div v-else-if="crossError" class="error-wrap">{{ crossError }}</div>
          <div v-else-if="!crossData?.matrix?.length" class="empty-wrap">
            <a-empty :description="t('common.noData')" />
          </div>
      <div v-else class="heatmap-wrap">
        <table class="heatmap-table">
          <thead>
            <tr>
              <th class="corner-th">{{ dimLabel(dim1) }}</th>
              <th v-for="v2 in crossData.dim2Values" :key="'h-'+v2" class="col-th">{{ truncate(v2, 20) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v1 in crossData.dim1Values" :key="v1">
              <td class="row-th">{{ truncate(v1, 25) }}</td>
              <td
                v-for="v2 in crossData.dim2Values"
                :key="v1+'|'+v2"
                :class="['heat-cell', { clickable: getCell(v1,v2) }]"
                :style="{ backgroundColor: cellBg(v1,v2) }"
                @click="onCellClick(v1, v2)"
                @mouseenter="onCellHover($event, v1, v2)"
                @mouseleave="hovered = null"
              >
                {{ cellDisplay(v1, v2) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </a-card>

    <!-- Tooltip -->
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

    <!-- Detail Popup -->
    <a-modal v-model:open="detailVisible" :title="detailTitle" width="850px" :footer="null" @cancel="detailVisible=false">
      <div v-if="detailLoading" class="modal-loading"><a-spin /></div>
      <div v-else-if="detailError" class="modal-error">{{ detailError }}</div>
      <div v-else-if="!detailRecords.length" class="modal-empty">{{ t('failureAnalysis.noRecordsFound') }}</div>
      <a-table v-else :data-source="detailRecords" :columns="detailColumns" row-key="fa_num" size="small" :pagination="false" :scroll="{ y: 400 }" />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { Bar } from 'vue-chartjs'
import { useI18n } from '@/i18n/useI18n'
import { useAppStore } from '@/stores/app'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import ChartDataLabels from 'chartjs-plugin-datalabels'
import { requestJson } from '@/composables/useApi'
import AEmpty from 'ant-design-vue/es/empty'
import ACard from 'ant-design-vue/es/card'
import ARow from 'ant-design-vue/es/row'
import ACol from 'ant-design-vue/es/col'
import ASpin from 'ant-design-vue/es/spin'
import ASelect from 'ant-design-vue/es/select'
import ARadio from 'ant-design-vue/es/radio'
import AModal from 'ant-design-vue/es/modal'
import ATable from 'ant-design-vue/es/table'
import BugOutlined from '@ant-design/icons-vue/es/icons/BugOutlined'
import CalendarOutlined from '@ant-design/icons-vue/es/icons/CalendarOutlined'
import ExperimentOutlined from '@ant-design/icons-vue/es/icons/ExperimentOutlined'
import SettingOutlined from '@ant-design/icons-vue/es/icons/SettingOutlined'
import WarningOutlined from '@ant-design/icons-vue/es/icons/WarningOutlined'
import {
  chartMetricValue,
  failureMetricDisplay,
  formatPpmTick,
  getClampedTooltipPosition,
  heatmapCellDisplay,
  oneLineLabel,
  overviewFailureDisplay,
} from './failureDisplay'
import { getFailureTheme } from './failureTheme'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)
const datalabelsPlugin = ChartDataLabels
const store = useAppStore()
const { t } = useI18n()
const ASelectOption = ASelect.Option
const ARadioGroup = ARadio.Group
const ARadioButton = ARadio.Button
const theme = computed(() => getFailureTheme(store.theme))
const fixedValueLabelsPlugin = computed(() => ({
  id: 'fixedValueLabels',
  afterDatasetsDraw(chart) {
    const dataset = chart.data.datasets?.[0]
    const meta = chart.getDatasetMeta(0)
    if (!dataset || !meta?.data?.length) return

    const { ctx, chartArea } = chart
    const palette = theme.value
    ctx.save()
    ctx.textBaseline = 'middle'
    ctx.font = '700 11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'

    meta.data.forEach((bar, index) => {
      const text = dataset.displayData?.[index]
      if (!text) return
      const y = bar.y
      const x = chartArea.right + 8
      const width = Math.ceil(ctx.measureText(text).width) + 12
      const height = 20
      const radius = 4
      const top = y - height / 2

      ctx.fillStyle = palette.labelBadgeBg
      ctx.strokeStyle = palette.labelBadgeBorder
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x + radius, top)
      ctx.lineTo(x + width - radius, top)
      ctx.quadraticCurveTo(x + width, top, x + width, top + radius)
      ctx.lineTo(x + width, top + height - radius)
      ctx.quadraticCurveTo(x + width, top + height, x + width - radius, top + height)
      ctx.lineTo(x + radius, top + height)
      ctx.quadraticCurveTo(x, top + height, x, top + height - radius)
      ctx.lineTo(x, top + radius)
      ctx.quadraticCurveTo(x, top, x + radius, top)
      ctx.closePath()
      ctx.fill()
      ctx.stroke()

      ctx.fillStyle = palette.labelBadgeText
      ctx.fillText(text, x + 6, y)
    })

    ctx.restore()
  },
}))

// ── Overview data ──
const overviewData = ref(null)
const loading = ref(false)
const error = ref(null)
const summary = computed(() => overviewData.value?.summary ?? {})
const overviewFailureText = computed(() => overviewFailureDisplay(summary.value))
const displayedFailurePercent = computed(() => {
  const s = summary.value
  const hasSpec = Number(s.specSNCount || 0) > 0
  const value = hasSpec ? s.specFailurePercent : s.strifeFailurePercent
  return Number(value || 0).toFixed(2)
})

async function loadOverview() {
  loading.value = true
  error.value = null
  try {
    overviewData.value = await requestJson('/api/fa/overview')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function barData(items, color) {
  const top = items.slice(0, 10)
  return {
    labels: top.map(i => oneLineLabel(i.label || i.key)),
    datasets: [{
      data: top.map(i => chartMetricValue(i)),
      backgroundColor: color,
      borderRadius: [0, 4, 4, 0],
      barThickness: 24,
      labelData: top.map(i => oneLineLabel(i.label || i.key)),
      displayData: top.map(i => failureMetricDisplay(i)),
      specRateData: top.map(i => i.specRate),
    }]
  }
}

const symptomChartData = computed(() => barData(overviewData.value?.topSymptom ?? [], 'rgba(24, 144, 255, 0.45)'))
const wfChartData = computed(() => barData(overviewData.value?.topWf ?? [], 'rgba(82, 196, 26, 0.45)'))
const testChartData = computed(() => barData(overviewData.value?.topFailedTest ?? [], 'rgba(250, 173, 20, 0.45)'))

const barOptions = computed(() => {
  const palette = theme.value
  return {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    onClick: () => {},
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: palette.tooltipBg,
        titleColor: palette.heatmapText,
        bodyColor: palette.tooltipText,
        borderColor: palette.tooltipBorder,
        borderWidth: 1,
        callbacks: {
          label: (ctx) => {
            const display = ctx.dataset.displayData?.[ctx.dataIndex]
            const rate = ctx.dataset.specRateData?.[ctx.dataIndex]
            return rate !== undefined ? `${display} (${t('common.spec')} ${Number(rate || 0).toFixed(2)}%)` : (display || ctx.raw)
          }
        }
      },
      datalabels: {
        labels: {
          name: {
            anchor: 'start',
            align: 'right',
            offset: 10,
            clamp: true,
            clip: true,
            color: palette.labelText,
            font: { weight: '500', size: 11 },
            formatter: (value, ctx) => truncate(oneLineLabel(ctx.dataset.labelData?.[ctx.dataIndex] || ''), 44),
          },
        },
      }
    },
    layout: {
      padding: { right: 78 },
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: {
          precision: 0,
          color: palette.axisText,
          callback: function(value) {
            return formatPpmTick(value)
          }
        },
        grid: { color: palette.gridColor },
        border: { color: palette.gridColor },
      },
      y: {
        ticks: { display: false, autoSkip: false, color: palette.axisText },
        grid: { color: palette.gridColor, borderDash: [2, 3] },
        border: { display: false },
      }
    }
  }
})

// ── Cross-analysis ──
const crossData = ref(null)
const crossLoading = ref(false)
const crossError = ref(null)

const dimOptions = [
  { label: t('failureMatrix.dimSymptom'), value: 'symptom' },
  { label: t('failureMatrix.dimLocation'), value: 'location' },
  { label: t('failureMatrix.dimTest'), value: 'failed_test' },
  { label: t('failureMatrix.dimWf'), value: 'wf' },
  { label: t('failureMatrix.dimConfig'), value: 'config' },
]

const dim1 = ref('location')
const dim2 = ref('config')
const displayMode = ref('spec')

function dimLabel(d) {
  return dimOptions.find(o => o.value === d)?.label || d
}

const matrixMap = computed(() => {
  const map = {}
  if (crossData.value?.matrix) {
    for (const m of crossData.value.matrix) {
      map[`${m.dim1Value}|${m.dim2Value}`] = m
    }
  }
  return map
})

const maxTotal = computed(() => Math.max(...(crossData.value?.matrix ?? []).map(m => m.totalCount), 1))

function getCell(v1, v2) {
  return matrixMap.value[`${v1}|${v2}`] || null
}

function cellBg(v1, v2) {
  const d = getCell(v1, v2)
  if (!d || !d.totalCount) return theme.value.heatmapEmptyBg
  const ratio = d.totalCount / maxTotal.value
  const colorsByMode = theme.value.heatmapColors
  let colors
  if (displayMode.value === 'spec' && d.specSnCount > 0) {
    colors = colorsByMode.spec
  } else if ((displayMode.value === 'spec' && d.specSnCount === 0 && d.strifeSnCount > 0) || displayMode.value === 'strife') {
    colors = colorsByMode.strife
  } else {
    colors = colorsByMode.total
  }
  const idx = ratio < 0.33 ? 0 : ratio < 0.66 ? 1 : 2
  return colors[idx]
}

function cellDisplay(v1, v2) {
  const d = getCell(v1, v2)
  return heatmapCellDisplay(d, displayMode.value)
}

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.substring(0, n - 1) + '...' : s
}

async function loadCross() {
  crossLoading.value = true
  crossError.value = null
  try {
    crossData.value = await requestJson(`/api/fa/cross?dim1=${dim1.value}&dim2=${dim2.value}`)
  } catch (e) {
    crossError.value = e.message
  } finally {
    crossLoading.value = false
  }
}

// ── Hover tooltip ──
const hovered = ref(null)
const tooltipPos = reactive({ x: 0, y: 0 })

function onCellHover(e, v1, v2) {
  const d = getCell(v1, v2)
  if (!d) { hovered.value = null; return }
  hovered.value = d
  const nextPosition = getClampedTooltipPosition(
    { x: e.clientX, y: e.clientY },
    { width: window.innerWidth, height: window.innerHeight }
  )
  tooltipPos.x = nextPosition.left
  tooltipPos.y = nextPosition.top
}

// ── Detail Popup ──
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
  { title: t('failureMatrix.colType'), dataIndex: 'failure_type', width: 60 },
  { title: t('failureMatrix.colSymptom'), dataIndex: 'symptom', width: 110, ellipsis: true },
  { title: t('failureMatrix.colLocation'), dataIndex: 'location', width: 90 },
  { title: t('failureMatrix.colFaStatus'), dataIndex: 'fa_status', width: 90 },
]

async function openDetail(filters) {
  detailVisible.value = true
  detailTitle.value = t('failureAnalysis.failureDetail')
  detailLoading.value = true
  detailError.value = null
  detailRecords.value = []

  const params = new URLSearchParams(filters).toString()
  try {
    const d = await requestJson(`/api/fa/detail?${params}`)
    detailRecords.value = d.records || []
  } catch (e) {
    detailError.value = e.message
  } finally {
    detailLoading.value = false
  }
}

function onCellClick(v1, v2) {
  if (!getCell(v1, v2)) return
  detailTitle.value = `${dimLabel(dim1.value)}: ${truncate(v1, 30)} x ${dimLabel(dim2.value)}: ${truncate(v2, 30)}`
  const filters = {}
  filters[dim1.value] = v1
  filters[dim2.value] = v2
  openDetail(filters)
}

// ── Init ──
onMounted(async () => {
  if (!overviewData.value) await loadOverview()
  if (!crossData.value) loadCross()
})

watch([dim1, dim2], loadCross)

watch(() => store.refreshCounter, () => { loadOverview(); loadCross() })
</script>

<style scoped>
.page-container { color: var(--text-primary); }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.kpi-card,
.section-card { background: var(--bg-card); color: var(--text-primary); }
.kpi-card {
  height: 112px;
  padding: 16px 18px;
}
.kpi-content { height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
.kpi-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; color: var(--text-secondary); white-space: nowrap; }
.kpi-icon { font-size: 15px; }
.kpi-icon.blue { color: var(--color-info); }
.kpi-icon.amber { color: var(--color-warning); }
.kpi-icon.green { color: var(--color-success); }
.kpi-icon.red { color: var(--color-danger); }
.kpi-value { text-align: center; font-size: 34px; line-height: 1; font-weight: 700; color: var(--text-primary); font-variant-numeric: tabular-nums; }
.percent-sign { font-size: 20px; font-weight: 600; margin-left: 2px; }
.kpi-foot { min-height: 18px; display: flex; justify-content: center; gap: 12px; font-size: 12px; font-weight: 600; }
.kpi-foot.muted { color: var(--text-muted); font-weight: 500; }
.spec-text { color: var(--color-danger); }
.strife-text { color: var(--color-warning); }
.chart-row { margin-bottom: 24px; }
.section-card {
  margin-bottom: 24px;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card), var(--ring-card);
}

.loading-wrap,
.error-wrap,
.empty-wrap {
  min-height: 180px;
  display: grid;
  place-items: center;
  padding: var(--space-xl);
  color: var(--text-muted);
}
.loading-wrap-lg {
  min-height: 300px;
}
.control-label { font-weight: 400; font-size: 13px; color: var(--text-muted); }

/* Heatmap */
.heatmap-wrap {
  max-height: min(70vh, 720px);
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
.heatmap-table th, .heatmap-table td { border: 1px solid var(--border-light); padding: 10px 8px; text-align: center; white-space: nowrap; }
.corner-th,
.row-th {
  position: sticky;
  left: 0;
}

.corner-th {
  z-index: 7;
}

.row-th {
  z-index: 4;
}

.corner-th {
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
  min-width: 160px;
  max-width: 300px;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  background: var(--bg-row-stripe);
  color: var(--text-primary);
  font-weight: 700;
}
.heat-cell { min-width: 80px; font-weight: 600; font-size: 12px; transition: all 0.2s ease; color: var(--text-primary); cursor: default; }
.heat-cell.clickable { cursor: pointer; }
.heat-cell.clickable:hover {
  border-radius: 3px;
  box-shadow:
    inset 0 0 0 2px var(--border-focus),
    0 0 0 3px color-mix(in srgb, var(--border-focus) 18%, transparent);
}

/* Tooltip */
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
.tt-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tt-row:last-child { margin-bottom: 0; }
.tt-row span { color: var(--text-secondary); font-weight: 500; font-size: 13px; }
.tt-row b { font-weight: 700; font-size: 14px; color: var(--accent-steel); }
.c-red { color: #e84c3d !important; }
.c-yellow { color: #faad14 !important; }
.c-green { color: #52c41a !important; }

/* Modal */
.modal-loading, .modal-error, .modal-empty { text-align: center; padding: 40px; color: var(--text-muted); }

.page-container :deep(.ant-radio-button-wrapper-checked:not(.ant-radio-button-wrapper-disabled)) {
  background: var(--accent-steel);
  border-color: var(--accent-steel) !important;
  color: var(--text-inverse);
}

.page-container :deep(.ant-table-tbody > tr.ant-table-row:hover > td) {
  background: var(--bg-row-hover) !important;
}

@media (max-width: 760px) {
  .page-container { padding: 16px; }
}
</style>
