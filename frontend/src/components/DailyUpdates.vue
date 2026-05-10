<template>
  <div class="card daily-card">
    <div class="daily-header" @click="toggle">
      <span class="chevron" :class="{ open: expanded }">▶</span>
      <span class="daily-title">CP Changes Today</span>
      <span class="daily-count">{{ wfCount }} WF(s) updated</span>
      <button class="toggle-btn" @click.stop="toggle">{{ expanded ? 'Collapse' : 'Expand' }}</button>
    </div>
    <div class="daily-body" :class="{ collapsed: !expanded }">
      <div v-if="!wfUpdates.length" class="daily-empty">{{ t('common.empty') }}</div>
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
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

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
.flow-list { padding: 0 20px 16px; }
.flow-block {
  padding: 12px 0 12px 14px; border-left: 3px solid transparent;
  transition: border-color var(--duration-fast);
}
.flow-block:hover { border-left-color: var(--border-card); }
.flow-block + .flow-block { border-top: 1px solid var(--border-light); }

.flow-label { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.flow-pill {
  padding: 3px 10px; background: #1a2332; color: #fff;
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  border-radius: var(--radius-sm); flex-shrink: 0; letter-spacing: 0.3px;
}
.flow-name {
  font-size: 14px; color: var(--text-primary); font-weight: 600;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Config rows */
.flow-configs { display: flex; flex-direction: column; gap: 2px; padding-left: 6px; }
.flow-cfg {
  display: flex; align-items: center; gap: 10px;
  padding: 3px 6px; border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}
.flow-cfg:hover { background: var(--bg-root); }

.cfg-badge {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  padding: 1px 8px; border-radius: 3px; border: 1px solid;
  flex-shrink: 0; min-width: 54px; text-align: center;
}
.cfg-delta {
  font-family: var(--font-mono); font-size: 11px; font-weight: 700;
  color: #fff; background: var(--color-success);
  padding: 2px 8px; border-radius: var(--radius-sm);
  flex-shrink: 0; white-space: nowrap;
}

.cfg-progress-bar { flex: 1; min-width: 50px; }
.cfg-bar-track { height: 3px; background: var(--bg-progress-track); border-radius: 2px; overflow: hidden; }
.cfg-bar-fill { height: 100%; border-radius: 2px; opacity: 0.45; transition: width 0.8s var(--ease-out); }

.cfg-end {
  font-family: var(--font-mono); font-size: 13px; font-weight: 700;
  color: var(--text-primary); flex-shrink: 0; min-width: 44px; white-space: nowrap;
}
.cfg-idx {
  font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);
  flex-shrink: 0; min-width: 36px; text-align: right;
}
</style>