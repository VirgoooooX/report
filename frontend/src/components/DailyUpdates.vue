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
      <div class="wf-grid" v-else>
        <div v-for="wf in wfUpdates" :key="wf.wf" class="wf-card">
          <div class="wf-head">
            <span class="wf-pill">WF{{ wf.wf }}</span>
            <span class="wf-name">{{ wfName(wf.wf) }}</span>
          </div>
          <div class="cfg-list">
            <div v-for="cfg in wf.configs" :key="cfg.config" class="cfg-item">
              <span class="cfg-tag" :style="cfgStyle(cfg.config)">{{ cfg.config }}</span>
              <span class="cfg-delta">+{{ cfg.cp_delta }} CP</span>
              <span class="cfg-info">{{ cfg.latest_cp }} <span class="cfg-progress">({{ cfg.latest_cp_idx != null ? cfg.latest_cp_idx + 1 : '—' }}/{{ cfg.total_cps }})</span></span>
            </div>
          </div>
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

function wfName(key) { return store.wfNames[key] || '' }

const CFG_COLORS = { R1FNF: '#4f6f8f', R2CNM: '#0891b2', R3: '#d97706', R4: '#059669' }
function cfgStyle(name) {
  const c = CFG_COLORS[name] || '#4f6f8f'
  return { background: c + '14', color: c, borderColor: c + '30' }
}
</script>

<style scoped>
.daily-card { overflow: hidden; }
.daily-header {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 20px; cursor: pointer; user-select: none;
  border-bottom: 1px solid transparent;
  transition: border-color var(--duration-fast);
}
.daily-card:has(.daily-body:not(.collapsed)) .daily-header {
  border-bottom-color: var(--border-light);
}

.chevron {
  font-size: 10px; color: var(--text-muted);
  transition: transform var(--duration-fast) var(--ease-in-out);
}
.chevron.open { transform: rotate(90deg); }
.daily-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.daily-count { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }
.toggle-btn {
  margin-left: auto; padding: 4px 12px; font-size: 12px;
  color: var(--text-secondary); background: transparent;
  border: 1px solid var(--border-input); border-radius: var(--radius-sm);
  cursor: pointer; transition: background var(--duration-fast);
}
.toggle-btn:hover { background: var(--bg-row-stripe); }

.daily-body { max-height: 6000px; overflow: hidden; transition: max-height var(--duration-normal) var(--ease-in-out); }
.daily-body.collapsed { max-height: 0; }
.daily-empty { padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px; }

/* WF Grid */
.wf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 1px;
  background: var(--border-light);
}
.wf-card {
  background: var(--bg-card);
  padding: 12px 16px;
}
.wf-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 6px;
}
.wf-pill {
  padding: 2px 8px; background: #1a2332; color: #fff;
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  border-radius: var(--radius-sm); flex-shrink: 0;
}
.wf-name {
  font-size: 13px; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  flex: 1; min-width: 0;
}

/* Config list */
.cfg-list { display: flex; flex-direction: column; gap: 2px; }
.cfg-item {
  display: flex; align-items: center; gap: 8px;
  padding: 2px 0; font-size: 12px;
}
.cfg-tag {
  padding: 0 6px; font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; border-radius: 3px; border: 1px solid;
  flex-shrink: 0;
}
.cfg-delta {
  font-family: var(--font-mono); font-weight: 600;
  color: var(--color-success); flex-shrink: 0; min-width: 52px;
}
.cfg-info { color: var(--text-secondary); font-size: 12px; }
.cfg-progress { color: var(--text-muted); font-size: 11px; }
</style>