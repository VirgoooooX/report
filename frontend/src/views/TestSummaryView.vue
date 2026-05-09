<template>
  <div class="page-container">
    <h1 class="page-title">Test Summary</h1>
    <p class="page-subtitle">{{ summaryList.length }} Waterfalls, {{ configList.length }} Configs, {{ tests.length }} Tests</p>

    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" :retry="load" />
    <TestSummary v-else :summary-data="store.summaryData" @cell-click="onCellClick" />

    <FAModal :show="showFAModal" :wf="faWf" :title="faTitle"
             :preset-sns="faSns" @close="showFAModal = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import TestSummary from '@/components/TestSummary.vue'
import FAModal from '@/components/FAModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const store = useAppStore()
const loading = ref(false)
const error = ref('')

const summaryList = computed(() => store.summaryData?.summary ?? [])
const configList = computed(() => {
  const set = new Set()
  summaryList.value.forEach(wf => {
    if (wf.configs) Object.keys(wf.configs).forEach(c => set.add(c))
  })
  return [...set]
})
const tests = computed(() => {
  const seen = new Set()
  const names = []
  summaryList.value.forEach(wf => {
    if (wf.configs) {
      Object.values(wf.configs).forEach(cfgTests => {
        Object.keys(cfgTests).forEach(t => {
          if (!seen.has(t)) { seen.add(t); names.push(t) }
        })
      })
    }
  })
  return names
})

const showFAModal = ref(false)
const faWf = ref('')
const faTitle = ref('')
const faSns = ref([])

function onCellClick(payload) {
  if (!payload) return
  showFAModal.value = true
  faWf.value = payload.wf || ''
  faTitle.value = `${payload.wf || ''} / ${payload.cfg || ''} / ${payload.test || ''}`
  faSns.value = payload.failureSns || []
}

async function load() {
  loading.value = true; error.value = ''
  try {
    await Promise.all([store.fetchOverview(), store.fetchSummary()])
  } catch { error.value = 'Failed to load data' }
  finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-container { max-width: 100%; margin: 0 auto; padding: 24px 32px 40px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px; }
.page-subtitle { font-size: 14px; color: var(--text-muted); margin-bottom: 24px; }
</style>