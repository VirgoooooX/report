<template>
  <div class="page-container ts-page">
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <TestSummary v-else :summary-data="store.summaryData" @cell-click="onCellClick" />

    <FAModal :show="showFAModal" :wf="faWf" :cfg="faCfg" :test="faTest"
             :test-idx="faTestIdx" :title="faTitle" :sns="faSns" :cell-detail="faCellDetail"
             @close="showFAModal = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'
import TestSummary from '@/components/TestSummary.vue'
import FAModal from '@/components/FAModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'

const store = useAppStore()
const { t } = useI18n()
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
const faCfg = ref('')
const faTest = ref('')
const faTestIdx = ref(null)
const faTitle = ref('')
const faSns = ref([])
const faCellDetail = ref(null)

function onCellClick(payload) {
  if (!payload) return
  faWf.value = payload.wf || ''
  faCfg.value = payload.cfg || ''
  faTest.value = payload.test || ''
  faTestIdx.value = payload.testIdx ?? null
  faTitle.value = `${payload.wf || ''} / ${payload.cfg || ''} / ${payload.test || ''}`
  faSns.value = payload.failureSns || []
  faCellDetail.value = {
    result: payload.result || '',
    spec: payload.spec || 0,
    strife: payload.strife || 0,
    total: payload.total || 0,
    status: payload.status || ''
  }
  showFAModal.value = true
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
.page-container {
  color: var(--text-primary);
}
</style>
