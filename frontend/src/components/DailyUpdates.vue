<template>
  <div class="card daily-card">
    <div class="daily-header" @click="toggle">
      <span class="chevron" :class="{ open: expanded }">▶</span>
      <span class="daily-title">CP Changes Today</span>
      <span class="daily-count">{{ wfCount }} WF(s) updated</span>
      <button class="toggle-btn" @click.stop="toggle">{{ expanded ? 'Collapse' : 'Expand' }}</button>
    </div>
    <div class="daily-body" :class="{ collapsed: !expanded }">
      <div v-if="!wfUpdates.length" class="daily-empty">No updates today</div>
      <div v-else class="flow-list">
        <div v-for="wf in wfUpdates" :key="wf.wf" class="flow-block">
          <div class="flow-label">
            <span class="flow-pill">WF{{ wf.wf }}</span>
            <span class="flow-name">{{ wfName(wf.wf) }}</span>
          </div>
          <div class="flow-configs">
            <div v-for="cfg in wf.configs" :key="cfg.config" class="flow-cfg">
              <span class="cfg-badge" :style="badgeStyle(cfg.config)">{{ cfg.config }}</span>
              <span class="cfg-delta">+{{ cfg.cp_delta }}</span>
              <div class="cfg-progress-bar">
                <div class="cfg-bar-track">
                  <div class="cfg-bar-fill" :style="{ width: cfgProgress(cfg) + '%', background: barColor(cfg.config) }"></div>
                </div>
              </div>
              <span class="cfg-end">{{ cfg.latest_cp }}</span>
              <span class="cfg-idx">{{ cfg.latest_cp_idx != null ? cfg.latest_cp_idx + 1 : '—' }}/{{ cfg.total_cps }}</span>
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

const props = defineProps({ dailyData: { type: Object, default: () => ({}) } })
const store = useAppStore()
const expanded = ref(true)
const toggle = () => { expanded.value = !expanded.value }

const wfUpdates = computed(() => props.dailyData?.wf_updates ?? [])
const wfCount = computed(() => wfUpdates.value.length)

function wfName(key) { return store.wfNames[key] || '' }

const CFG_COLORS = { R1FNF: '#4f6f8f', R2CNM: '#0891b2', R3: '#d97706', R4: '#059669' }
function barColor(c) { return CFG_COLORS[c] || '#4f6f8f' }
function badgeStyle(c) {
  const color = CFG_COLORS[c] || '#4f6f8f'
  return { color, borderColor: color + '40', backgroundColor: color + '0d' }
}
function cfgProgress(cfg) {
  if (!cfg.total_cps) return 0
  return ((cfg.latest_cp_idx || 0) + 1) / cfg.total_cps * 100
}
</script>

<style scoped>
.daily-card { overflow: hidden; }
.daily-header {
  display: flex; align-items: center; gap: 12px; padding: 14px 20px;
  cursor: pointer; user-select: none;
}
.daily-header:hover { background: var(--bg-card-hover); }
.chevron { font-size: 10px; color: var(--text-muted); transition: transform var(--duration-fast); flex-shrink: 0; }
.chevron.open { transform: rotate(90deg); }
.daily-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.daily-count { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }
.toggle-btn {
  margin-left: auto; padding: 4px 12px; font-size: 12px;
  color: var(--text-secondary); border: 1px solid var(--border-input);
  border-radius: var(--radius-sm); cursor: pointer; background: none;
  transition: background var(--duration-fast);
}
.toggle-btn:hover { background: var(--bg-row-stripe); }

.daily-body { max-height: 8000px; overflow: hidden; transition: max-height var(--duration-normal) var(--ease-in-out); }
.daily-body.collapsed { max-height: 0; }
.daily-empty { padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px; }

/* Flow list */
.flow-list { padding: 8px 20px 16px; }
.flow-block { padding: 10px 0; border-bottom: 1px solid var(--border-light); }
.flow-block:last-child { border-bottom: none; }

.flow-label { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.flow-pill {
  padding: 2px 8px; background: #1a2332; color: #fff;
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  border-radius: var(--radius-sm); flex-shrink: 0;
}
.flow-name {
  font-size: 13px; color: var(--text-secondary); font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Config rows */
.flow-configs { display: flex; flex-direction: column; gap: 4px; padding-left: 4px; }
.flow-cfg {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 8px; border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}
.flow-cfg:hover { background: var(--bg-root); }

.cfg-badge {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  padding: 1px 8px; border-radius: 3px; border: 1px solid;
  flex-shrink: 0; min-width: 54px; text-align: center; white-space: nowrap;
}
.cfg-delta {
  font-family: var(--font-mono); font-size: 12px; font-weight: 700;
  color: var(--color-success); flex-shrink: 0; min-width: 30px;
}

.cfg-progress-bar { flex: 1; min-width: 60px; }
.cfg-bar-track { height: 4px; background: var(--bg-progress-track); border-radius: 2px; overflow: hidden; }
.cfg-bar-fill { height: 100%; border-radius: 2px; transition: width 0.8s var(--ease-out); }

.cfg-end {
  font-family: var(--font-mono); font-size: 12px; color: var(--text-primary);
  font-weight: 500; flex-shrink: 0; min-width: 48px; white-space: nowrap;
}
.cfg-idx {
  font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);
  flex-shrink: 0; min-width: 40px; text-align: right;
}
</style>