<template>
  <div class="card daily-card">
    <div class="daily-header" @click="toggle">
      <span class="chevron" :class="{ open: expanded }">▶</span>
      <span class="daily-title">CP Changes Today</span>
      <span class="daily-count">{{ wfCount }} WF(s) updated</span>
      <button class="toggle-btn">{{ expanded ? 'Collapse' : 'Expand' }}</button>
    </div>
    <div class="daily-body" :class="{ collapsed: !expanded }">
      <div v-if="!wfUpdates.length" class="daily-empty">No updates today</div>
      <div v-for="wf in wfUpdates" :key="wf.wf" class="wf-group">
        <div class="wf-row">
          <span class="wf-pill">{{ wf.wf }}</span>
          <span class="wf-name">{{ wfName(wf.wf) }}</span>
        </div>
        <div v-for="cfg in wf.configs" :key="cfg.config" class="cfg-row">
          <span class="cfg-name" :style="{ color: `var(${cfgColor(cfg.config)})` }">{{ cfg.config }}</span>
          <span class="cfg-count">+{{ cfg.cp_delta }} CPs</span>
          <span class="cfg-latest">{{ cfg.latest_cp }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'

const props = defineProps({
  dailyData: { type: Object, default: () => ({}) }
})

const store = useAppStore()
const expanded = ref(true)

const toggle = () => { expanded.value = !expanded.value }

const wfUpdates = computed(() => props.dailyData?.wf_updates ?? [])
const wfCount = computed(() => wfUpdates.value.length)

function wfName(key) {
  return store.wfNames[key] || key
}

function cfgColor(name) {
  const map = {
    R1FNF: '--chart-r1fnf',
    R2CNM: '--chart-r2cnm',
    R3: '--chart-r3',
    R4: '--chart-r4'
  }
  return map[name] || '--accent-steel'
}
</script>

<style scoped>
.daily-card {
  overflow: hidden;
}

.daily-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
}

.chevron {
  font-size: 10px;
  color: var(--text-muted);
  transition: transform var(--duration-fast) var(--ease-in-out);
}

.chevron.open {
  transform: rotate(90deg);
}

.daily-title {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.daily-count {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.toggle-btn {
  margin-left: auto;
  padding: 4px 12px;
  font-size: 12px;
  font-family: var(--font-display);
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-in-out);
}

.toggle-btn:hover {
  background: var(--bg-row-stripe);
}

.daily-body {
  max-height: 1000px;
  overflow: hidden;
  transition: max-height var(--duration-normal) var(--ease-in-out);
  padding: 0 20px 14px;
}

.daily-body.collapsed {
  max-height: 0;
  padding: 0 20px;
}

.daily-empty {
  padding: 20px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.wf-group {
  margin-bottom: 10px;
}

.wf-group:last-child {
  margin-bottom: 0;
}

.wf-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.wf-pill {
  display: inline-block;
  padding: 2px 8px;
  background: #1a2332;
  color: #ffffff;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
}

.wf-name {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--text-muted);
}

.cfg-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-left: 24px;
  margin-top: 3px;
}

.cfg-name {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  min-width: 60px;
}

.cfg-count {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--color-success);
}

.cfg-latest {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
}
</style>
