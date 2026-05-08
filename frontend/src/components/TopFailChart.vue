<template>
  <div class="chart-container">
    <Bar
      v-if="chartData"
      :data="chartData"
      :options="chartOptions"
      :height="280"
    />
    <div v-else class="empty-state">No failure data</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const props = defineProps({
  topFailures: { type: Array, default: () => [] }
})

function truncateLabel(label, max = 30) {
  return label.length > max ? label.slice(0, max) + '...' : label
}

function barColor(rate) {
  if (rate > 50) return { bg: 'rgba(239,68,68,0.7)', border: '#ef4444' }
  if (rate > 20) return { bg: 'rgba(245,158,11,0.7)', border: '#f59e0b' }
  return { bg: 'rgba(79,111,143,0.6)', border: '#4f6f8f' }
}

const chartData = computed(() => {
  const items = props.topFailures ?? []
  if (items.length === 0) return null

  const top5 = items.slice(0, 5)
  const colors = top5.map(d => barColor(d.rate ?? 0))

  return {
    labels: top5.map(d =>
      truncateLabel(`WF${d.wf ?? ''} ${d.cfg ?? ''} ${d.test ?? ''}`)
    ),
    datasets: [
      {
        label: 'Failure Rate',
        data: top5.map(d => d.rate ?? 0),
        backgroundColor: colors.map(c => c.bg),
        borderColor: colors.map(c => c.border),
        borderWidth: 1,
        borderRadius: 4,
        barThickness: 16
      }
    ]
  }
})

const chartOptions = computed(() => ({
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1a2332',
      titleColor: '#e8eaf0',
      bodyColor: '#9ca3b8',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 8,
      titleFont: { size: 12 },
      bodyFont: { size: 12 },
      callbacks: {
        label: function (ctx) {
          return `${ctx.parsed.x}%`
        }
      }
    }
  },
  scales: {
    x: {
      min: 0,
      max: 100,
      ticks: {
        font: { size: 10 },
        color: '#8e99a8',
        callback: function (value) {
          return value + '%'
        }
      },
      grid: {
        color: 'rgba(0,0,0,0.04)'
      }
    },
    y: {
      ticks: {
        font: { size: 10 },
        color: '#4a5568'
      },
      grid: {
        color: 'rgba(0,0,0,0.04)'
      }
    }
  }
}))
</script>

<style scoped>
.chart-container {
  position: relative;
  min-height: 280px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 280px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
