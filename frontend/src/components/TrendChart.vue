<template>
  <div class="chart-container">
    <Line
      v-if="chartData"
      :data="chartData"
      :options="chartOptions"
      :height="280"
    />
    <div v-else class="empty-state">No trend data available</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps({
  trendData: { type: Array, default: () => [] }
})

const chartData = computed(() => {
  if (!props.trendData || props.trendData.length === 0) return null
  return {
    labels: props.trendData.map(d => d.date?.slice(5) ?? ''),
    datasets: [
      {
        label: 'Spec',
        data: props.trendData.map(d => d.spec ?? 0),
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,0.08)',
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 3,
        pointBackgroundColor: '#ef4444',
        fill: true
      },
      {
        label: 'Strife',
        data: props.trendData.map(d => d.strife ?? 0),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.08)',
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 3,
        pointBackgroundColor: '#f59e0b',
        fill: true
      }
    ]
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        color: '#4a5568',
        font: { size: 11 },
        boxWidth: 12,
        padding: 12,
        usePointStyle: false
      }
    },
    tooltip: {
      backgroundColor: '#1a2332',
      titleColor: '#e8eaf0',
      bodyColor: '#9ca3b8',
      borderColor: 'rgba(255,255,255,0.08)',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 8,
      titleFont: { size: 12 },
      bodyFont: { size: 12 }
    }
  },
  scales: {
    x: {
      ticks: {
        font: { size: 10 },
        color: '#8e99a8'
      },
      grid: {
        color: 'rgba(0,0,0,0.04)'
      }
    },
    y: {
      beginAtZero: true,
      ticks: {
        font: { size: 10 },
        color: '#8e99a8'
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
