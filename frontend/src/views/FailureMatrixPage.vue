<template>
  <div class="page-container">
    <h1 class="page-title">Failure Analysis</h1>

    <!-- Top N Charts -->
    <a-row :gutter="16" class="chart-row">
      <a-col :span="8">
        <a-card title="Top 10 Test Item Failure Rate" :bordered="false" class="section-card">
          <div v-if="testTopApi.loading" class="loading-wrap"><a-spin /></div>
          <div v-else-if="testTopItems.length" style="height:380px">
            <Bar :data="testTopChartData" :options="barOptions" />
          </div>
          <div v-else class="empty-wrap">No data</div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="Top 10 WF Failure Rate" :bordered="false" class="section-card">
          <div v-if="wfTopApi.loading" class="loading-wrap"><a-spin /></div>
          <div v-else-if="wfTopItems.length" style="height:380px">
            <Bar :data="wfTopChartData" :options="barOptions" />
          </div>
          <div v-else class="empty-wrap">No data</div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="Top 10 Config Failure Rate" :bordered="false" class="section-card">
          <div v-if="configTopApi.loading" class="loading-wrap"><a-spin /></div>
          <div v-else-if="configTopItems.length" style="height:380px">
            <Bar :data="configTopChartData" :options="barOptions" />
          </div>
          <div v-else class="empty-wrap">No data</div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Cross-Analysis Heatmap -->
    <a-card :bordered="false" class="section-card">
      <template #title>
        <div style="display:flex;align-items:center;gap:16px">
          <span>交叉分析热力图</span>
          <span style="font-weight:400;font-size:13px;color:#8c8c8c">维度1:</span>
          <a-select v-model:value="dim1" size="small" style="width:110px" @change="loadCross">
            <a-select-option v-for="d in dimOptions" :key="d.value" :value="d.value" :disabled="d.value===dim2">{{ d.label }}</a-select-option>
          </a-select>
          <span style="font-weight:400;font-size:13px;color:#8c8c8c">维度2:</span>
          <a-select v-model:value="dim2" size="small" style="width:110px" @change="loadCross">
            <a-select-option v-for="d in dimOptions" :key="d.value" :value="d.value" :disabled="d.value===dim1">{{ d.label }}</a-select-option>
          </a-select>
          <a-radio-group v-model:value="displayMode" size="small" button-style="solid">
            <a-radio-button value="spec">Spec.失败率</a-radio-button>
            <a-radio-button value="strife">Strife失败率</a-radio-button>
            <a-radio-button value="total">总失败率</a-radio-button>
          </a-radio-group>
        </div>
      </template>
      <div v-if="crossLoading" class="loading-wrap" style="min-height:300px"><a-spin size="large" /></div>
      <div v-else-if="crossError" class="error-wrap">{{ crossError }}</div>
      <div v-else-if="!crossData?.matrix?.length" class="empty-wrap">No data</div>
      <div v-else class="heatmap-wrap">
        <table class="heatmap-table">
          <thead>
            <tr>
              <th class="corner-th">{{ dimLabel(dim1) }}</th>
              <th v-for="v2 in crossData.dim2Values" :key="'h-'+v2" class="col-th">{{ v2 }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v1 in crossData.dim1Values" :key="v1">
              <td class="row-th">{{ truncate(v1, 25) }}</td>
              <td
                v-for="v2 in crossData.dim2Values"
                :key="v1+'|'+v2"
                :class="['heat-cell', { 'clickable': getCell(v1,v2) }]"
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
      <div class="tt-row"><span>总失败次数:</span><b>{{ hovered.totalCount }}</b></div>
      <div class="tt-row"><span>Spec.失败率:</span><b class="c-red">{{ hovered.specRate }}%</b></div>
      <div class="tt-row"><span>Strife失败率:</span><b class="c-yellow">{{ hovered.strifeRate }}%</b></div>
      <div class="tt-row"><span>占总体比:</span><b class="c-green">{{ hovered.percentage }}%</b></div>
    </div>

    <!-- Detail Popup Modal -->
    <a-modal
      v-model:open="detailVisible"
      :title="detailTitle"
      width="700px"
      :footer="null"
      @cancel="detailVisible = false"
    >
      <div v-if="detailLoading" class="modal-loading"><a-spin /></div>
      <div v-else-if="detailError" class="modal-error">{{ detailError }}</div>
      <div v-else-if="!detailRecords.length" class="modal-empty">No records found</div>
      <a-table
        v-else
        :data-source="detailRecords"
        :columns="detailColumns"
        row-key="id"
        size="small"
        :pagination="false"
        :scroll="{ y: 400 }"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { useApi } from '@/composables/useApi'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

// ── Top Charts ──
const testTopApi = useApi('/api/failures/top')
const wfTopApi = useApi('/api/failures/top')
const configTopApi = useApi('/api/failures/top')

const testTopItems = computed(() => testTopApi.data.value?.items ?? [])
const wfTopItems = computed(() => wfTopApi.data.value?.items ?? [])
const configTopItems = computed(() => configTopApi.data.value?.items ?? [])

function barDataset(items, color) {
  const top = items.slice(0, 10)
  return {
    labels: top.map(i => i.key || i.test || i.name || '-'),
    datasets: [{
      label: 'Failure Rate %',
      data: top.map(i => i.total_rate ?? i.rate ?? 0),
      backgroundColor: color,
      borderRadius: [0, 4, 4, 0],
      barThickness: 24,
      cursor: 'pointer',
    }]
  }
}

const testTopChartData = computed(() => barDataset(testTopItems.value, 'rgba(250, 173, 20, 0.45)'))
const wfTopChartData = computed(() => barDataset(wfTopItems.value, 'rgba(82, 196, 26, 0.45)'))
const configTopChartData = computed(() => barDataset(configTopItems.value, 'rgba(24, 144, 255, 0.45)'))

const barOptions = computed(() => ({
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  onClick: (evt, elements, chart) => {
    if (!elements?.length) return
    const idx = elements[0].index
    let dim, val
    if (chart.canvas === testCanvas.value) {
      dim = 'test'; val = testTopItems.value[idx]?.key
    } else if (chart.canvas === wfCanvas.value) {
      dim = 'wf'; val = wfTopItems.value[idx]?.key
    } else if (chart.canvas === configCanvas.value) {
      dim = 'config'; val = configTopItems.value[idx]?.key
    }
    if (dim && val) openDetail(dim, val)
  },
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: ctx => `${ctx.raw.toFixed(1)}%` } }
  },
  scales: {
    x: { beginAtZero: true, ticks: { callback: v => v + '%' } }
  }
}))

// Track canvas refs for click routing
const testCanvas = ref(null)
const wfCanvas = ref(null)
const configCanvas = ref(null)

// ── Cross-Analysis Heatmap ──
const crossApi = useApi('/api/failures/cross')
const crossLoading = ref(false)
const crossError = ref(null)

const dimOptions = [
  { label: 'Config', value: 'config' },
  { label: 'WF', value: 'wf' },
  { label: 'Test', value: 'test' },
]

const dim1 = ref('config')
const dim2 = ref('wf')
const displayMode = ref('spec')

const crossData = computed(() => crossApi.data.value)
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

function dimLabel(d) {
  const opt = dimOptions.find(o => o.value === d)
  return opt ? opt.label : d
}

function getCell(v1, v2) {
  return matrixMap.value[`${v1}|${v2}`] || null
}

function cellBg(v1, v2) {
  const d = getCell(v1, v2)
  if (!d || !d.totalCount) return '#ffffff'
  const ratio = d.totalCount / maxTotal.value
  const displayingSpec = displayMode.value === 'spec' && d.specCount > 0
  const displayingStrife = (displayMode.value === 'spec' && d.specCount === 0 && d.strifeCount > 0) || displayMode.value === 'strife'

  let colors
  if (displayingSpec) {
    colors = ['#fce8e6', '#f4b5af', '#e8959b']
  } else if (displayingStrife) {
    colors = ['#fffae6', '#fff2b3', '#ffe680']
  } else {
    colors = ['#e6f4fa', '#b3e0f2', '#80cce8']
  }
  const idx = ratio < 0.33 ? 0 : ratio < 0.66 ? 1 : 2
  return colors[idx]
}

function cellDisplay(v1, v2) {
  const d = getCell(v1, v2)
  if (!d) return '-'
  if (displayMode.value === 'spec') {
    return d.specCount === 0 && d.strifeCount > 0 ? `${d.strifeRate}%` : `${d.specRate}%`
  }
  if (displayMode.value === 'strife') return `${d.strifeRate}%`
  return `${d.totalCount}F/${d.totalUnits}T`
}

function truncate(s, n) { return s && s.length > n ? s.substring(0, n-1)+'...' : s }

// ── Hover tooltip ──
const hovered = ref(null)
const tooltipPos = ref({ x: 0, y: 0 })

function onCellHover(e, v1, v2) {
  const d = getCell(v1, v2)
  if (!d) { hovered.value = null; return }
  hovered.value = d
  const rect = e.target.getBoundingClientRect()
  tooltipPos.value = { x: rect.left + 10, y: rect.top - 170 }
}

// ── Detail Popup ──
const detailVisible = ref(false)
const detailTitle = ref('')
const detailLoading = ref(false)
const detailError = ref(null)
const detailRecords = ref([])

const detailColumns = [
  { title: 'WF', dataIndex: 'wf_num', width: 70 },
  { title: 'Config', dataIndex: 'config', width: 80 },
  { title: 'Test', dataIndex: 'test_name', width: 120 },
  { title: 'Spec Fail', dataIndex: 'spec_fail_count', width: 80, align: 'center' },
  { title: 'Strife Fail', dataIndex: 'strife_fail_count', width: 80, align: 'center' },
  { title: 'Total Units', dataIndex: 'total_units', width: 90, align: 'center' },
  { title: 'Failure SNs', dataIndex: 'failure_sns', ellipsis: true,
    customRender: ({ text }) => Array.isArray(text) ? text.join(', ') : '' },
]

async function openDetail(dim, value) {
  detailVisible.value = true
  detailTitle.value = `${dimLabel(dim)}: ${value}`
  detailLoading.value = true
  detailError.value = null
  detailRecords.value = []

  const params = new URLSearchParams()
  if (dim === 'config') params.set('config', value)
  else if (dim === 'wf') params.set('wf', value)
  else if (dim === 'test') params.set('test_idx', value)

  try {
    const r = await fetch(`/api/failures/detail?${params}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const d = await r.json()
    detailRecords.value = d.records || []
  } catch (e) {
    detailError.value = e.message
  } finally {
    detailLoading.value = false
  }
}

function onCellClick(v1, v2) {
  const d = getCell(v1, v2)
  if (!d) return
  detailVisible.value = true
  detailTitle.value = `${dimLabel(dim1.value)}: ${v1} × ${dimLabel(dim2.value)}: ${v2}`

  // Fetch detail for both dimensions
  ;(async () => {
    detailLoading.value = true
    detailError.value = null
    detailRecords.value = []
    const params = new URLSearchParams()
    if (dim1.value === 'config') params.set('config', v1)
    else if (dim1.value === 'wf') params.set('wf', v1)

    if (dim2.value === 'config') params.set('config', v2)
    else if (dim2.value === 'wf') params.set('wf', v2)

    try {
      const r = await fetch(`/api/failures/detail?${params}`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const d = await r.json()
      detailRecords.value = d.records || []
    } catch (e) {
      detailError.value = e.message
    } finally {
      detailLoading.value = false
    }
  })()
}

function loadCross() {
  crossLoading.value = true
  crossError.value = null
  crossApi.fetch({ dim1: dim1.value, dim2: dim2.value }).catch(e => {
    crossError.value = e.message
  }).finally(() => {
    crossLoading.value = false
  })
}

// ── Init ──
onMounted(async () => {
  await Promise.all([
    testTopApi.fetch({ by: 'test', limit: 10 }),
    wfTopApi.fetch({ by: 'wf', limit: 10 }),
    configTopApi.fetch({ by: 'config', limit: 10 }),
  ])
  loadCross()
})

watch([dim1, dim2], loadCross)
</script>

<style scoped>
.page-container { max-width: 1440px; margin: 0 auto; padding: 24px 32px 40px; }
.page-title { font-family: 'Work Sans', sans-serif; font-weight: 700; font-size: 20px; color: #1a2332; margin-bottom: 24px; }

.chart-row { margin-bottom: 24px; }

.section-card {
  border-radius: 8px; margin-bottom: 24px;
  border: 1px solid var(--border-card, #e8ecf1);
  box-shadow: var(--shadow-card, 0 1px 3px rgba(0,0,0,0.06));
}
.section-card :deep(.ant-card-head) { border-bottom: 1px solid var(--border-light, #f0f0f0); }

.loading-wrap, .error-wrap, .empty-wrap {
  display: flex; align-items: center; justify-content: center;
  min-height: 120px; color: var(--text-muted, #8c8c8c);
}

/* ── Heatmap ── */
.heatmap-wrap { overflow-x: auto; }
.heatmap-table {
  border-collapse: collapse; width: 100%; font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  border-radius: 8px; overflow: hidden;
}
.heatmap-table th, .heatmap-table td {
  border: 1px solid #e8e8e8; padding: 12px 8px; text-align: center; white-space: nowrap;
}
.corner-th { background: #f0f0f0; color: #262626; font-weight: 800; font-size: 13px; min-width: 140px; }
.col-th { background: #f0f0f0; color: #262626; font-weight: 800; font-size: 13px; min-width: 100px; }
.row-th {
  background: #f8f8f8; font-weight: 700; color: #262626; min-width: 140px; max-width: 220px;
  word-break: break-word; font-size: 13px;
}
.heat-cell {
  min-width: 110px; font-weight: 600; font-size: 13px; transition: all 0.2s ease;
  color: #262626; cursor: default; position: relative;
}
.heat-cell.clickable { cursor: pointer; }
.heat-cell.clickable:hover { box-shadow: inset 0 0 0 1px #1890ff, 0 0 6px rgba(24,144,255,0.3); border-radius: 4px; }

/* Tooltip */
.heat-tooltip {
  position: fixed; z-index: 1000; background: #fff; padding: 14px 18px;
  border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); font-size: 12px;
  min-width: 220px; pointer-events: none; border: 1px solid #f0f0f0;
}
.tt-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tt-row:last-child { margin-bottom: 0; }
.tt-row span { color: #595959; font-weight: 500; font-size: 13px; }
.tt-row b { font-weight: 700; font-size: 15px; color: #1890ff; }
.c-red { color: #e84c3d !important; }
.c-yellow { color: #faad14 !important; }
.c-green { color: #52c41a !important; }

/* Modal */
.modal-loading, .modal-error, .modal-empty {
  text-align: center; padding: 40px; color: #8c8c8c;
}
</style>
