<template>
  <teleport to="body">
    <transition name="pop">
      <div
        v-if="visible"
        ref="popRef"
        class="ci-popover"
        :style="popStyle"
        role="dialog"
        @click.stop
      >
        <div class="pop-arrow" :class="`arrow-${placement}`" :style="arrowStyle" />
        <div class="pop-header">
          <div class="pop-title">
            <strong>{{ title }}</strong>
            <span v-if="subtitle" class="pop-subtitle">{{ subtitle }}</span>
          </div>
          <button class="pop-close" @click="$emit('close')" aria-label="close">×</button>
        </div>
        <div class="pop-body" :class="{ wide: mode === 'matrix' }">
          <!-- Single-SN breakdown: chips -->
          <template v-if="mode === 'chips'">
            <div v-if="loading" class="pop-loading">{{ loadingText }}</div>
            <div v-else-if="!items.length" class="pop-empty">{{ emptyText }}</div>
            <div v-else class="chips-grid">
              <div
                v-for="ci in items"
                :key="ci.name"
                class="ci-chip"
                :class="`ci-${classifyFor(ci)}`"
                :title="titleFor(ci)"
              >
                <span class="ci-chip-icon">{{ symbolFor(ci) }}</span>
                <span class="ci-chip-name">{{ ci.name }}</span>
              </div>
            </div>
          </template>

          <!-- Matrix: rows of SNs × columns of check items -->
          <template v-else-if="mode === 'matrix'">
            <div v-if="loading" class="pop-loading">{{ loadingText }}</div>
            <div v-else-if="!matrixRows.length" class="pop-empty">{{ emptyText }}</div>
            <div v-else class="matrix-wrap">
              <div class="matrix-head" :style="matrixGridStyle">
                <div class="matrix-head-sn">SN</div>
                <div
                  v-for="name in checkItemNames"
                  :key="'h-' + name"
                  class="matrix-head-ci"
                  :title="name"
                >{{ name }}</div>
              </div>
              <div
                v-for="row in matrixRows"
                :key="row.sn + '_' + row.config"
                class="matrix-row"
                :style="matrixGridStyle"
              >
                <div class="matrix-sn-cell">
                  <div class="matrix-sn-top">
                    <span class="matrix-sn-label">{{ row.sn }}</span>
                    <span class="matrix-cfg">{{ row.config }}</span>
                  </div>
                  <span v-if="row.unit_num" class="matrix-mark">{{ row.unit_num }}</span>
                </div>
                <span
                  v-for="name in checkItemNames"
                  :key="row.sn + '_' + name"
                  class="matrix-dot"
                  :class="`ci-${classifyFor(findItem(row.items, name))}`"
                  :title="titleFor(findItem(row.items, name), name)"
                >{{ symbolFor(findItem(row.items, name)) }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  anchor: { type: Object, default: null }, // DOMRect-like {x, y, width, height}
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  // prop default — cannot use t() here (setup-time constraint)
  loadingText: { type: String, default: 'Loading…' },
  // prop default — cannot use t() here (setup-time constraint)
  emptyText: { type: String, default: 'No data' },
  mode: { type: String, default: 'chips' }, // 'chips' | 'matrix'
  // chips mode
  items: { type: Array, default: () => [] },
  // matrix mode
  checkItemNames: { type: Array, default: () => [] },
  matrixRows: { type: Array, default: () => [] },
})

const emit = defineEmits(['close'])

const popRef = ref(null)
const placement = ref('bottom')
const popStyle = ref({ left: '0px', top: '0px', visibility: 'hidden' })
const arrowStyle = ref({ left: '20px' })

const matrixGridStyle = computed(() => ({
  gridTemplateColumns: `minmax(140px, 160px) repeat(${props.checkItemNames.length || 1}, minmax(28px, 1fr))`,
}))

function findItem(list, name) { return (list || []).find(i => i.name === name) || null }

function classifyFor(ci) {
  if (!ci) return 'skip'
  if (ci.status === 'pass') return 'pass'
  if (ci.status === 'fail' || ci.failure_type === 'spec') return 'fail'
  if (ci.failure_type === 'strife') return 'strife'
  return 'skip'
}
function symbolFor(ci) {
  if (!ci) return '—'
  if (ci.status === 'pass') return '✓'
  if (ci.status === 'fail' || ci.failure_type) return '✗'
  return '—'
}
function titleFor(ci, name) {
  if (!ci) return name ? `${name}: n/a` : ''
  return `${ci.name || name}: ${ci.status || 'pending'}${ci.failure_type ? ' (' + ci.failure_type + ')' : ''}`
}

function reposition() {
  if (!props.anchor || !popRef.value) return
  const a = props.anchor
  const pop = popRef.value
  const vw = window.innerWidth
  const vh = window.innerHeight
  const margin = 8

  const rect = pop.getBoundingClientRect()
  const popW = rect.width || pop.offsetWidth || 320
  const popH = rect.height || pop.offsetHeight || 200

  // Decide placement: prefer below, fall back to above
  const spaceBelow = vh - (a.y + a.height)
  const spaceAbove = a.y
  const goAbove = spaceBelow < popH + margin && spaceAbove > spaceBelow
  placement.value = goAbove ? 'top' : 'bottom'

  let top = goAbove ? (a.y - popH - margin) : (a.y + a.height + margin)
  top = Math.max(margin, Math.min(vh - popH - margin, top))

  // Align horizontally to anchor center, clamp to viewport
  const anchorCenter = a.x + a.width / 2
  let left = anchorCenter - popW / 2
  left = Math.max(margin, Math.min(vw - popW - margin, left))

  // Arrow position (relative to popover left)
  const arrowX = Math.max(12, Math.min(popW - 12, anchorCenter - left))
  arrowStyle.value = { left: `${arrowX}px` }

  popStyle.value = { left: `${left}px`, top: `${top}px`, visibility: 'visible' }
}

function onDocClick(e) {
  if (!props.visible) return
  if (popRef.value && popRef.value.contains(e.target)) return
  emit('close')
}

function onKey(e) {
  if (!props.visible) return
  if (e.key === 'Escape') emit('close')
}

function onWin() { if (props.visible) reposition() }

watch(() => props.visible, async (v) => {
  if (v) {
    popStyle.value = { ...popStyle.value, visibility: 'hidden' }
    await nextTick()
    reposition()
    // One more tick for content that renders async
    setTimeout(reposition, 0)
  }
})

watch(() => [props.anchor, props.items, props.matrixRows, props.checkItemNames, props.loading],
  () => { if (props.visible) nextTick(reposition) })

onMounted(() => {
  document.addEventListener('mousedown', onDocClick, true)
  window.addEventListener('resize', onWin)
  window.addEventListener('scroll', onWin, true)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocClick, true)
  window.removeEventListener('resize', onWin)
  window.removeEventListener('scroll', onWin, true)
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.ci-popover {
  position: fixed;
  z-index: 1200;
  background: var(--bg-card);
  border: 1px solid color-mix(in srgb, var(--accent-steel) 35%, var(--border-card));
  border-radius: var(--radius-lg);
  box-shadow:
    0 0 0 4px color-mix(in srgb, var(--accent-steel) 8%, transparent),
    0 20px 50px rgba(15, 23, 42, 0.25),
    0 4px 10px rgba(15, 23, 42, 0.12);
  min-width: 280px;
  max-width: min(720px, calc(100vw - 24px));
  max-height: calc(100vh - 24px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pop-arrow {
  position: absolute;
  width: 12px; height: 12px;
  border: 1px solid color-mix(in srgb, var(--accent-steel) 35%, var(--border-card));
  transform: rotate(45deg);
}
.pop-arrow.arrow-bottom {
  top: -7px;
  background: color-mix(in srgb, var(--accent-steel) 12%, var(--bg-card));
  border-right: none;
  border-bottom: none;
}
.pop-arrow.arrow-top {
  bottom: -7px;
  background: var(--bg-card);
  border-left: none;
  border-top: none;
}

.pop-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--accent-steel) 20%, var(--border-light));
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--accent-steel) 12%, var(--bg-card)) 0%,
    color-mix(in srgb, var(--accent-steel) 5%, var(--bg-card)) 100%
  );
}
.pop-title { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.pop-title strong {
  font-size: 14px; color: var(--text-primary); font-weight: 700;
}
.pop-subtitle {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pop-close {
  background: none;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  width: 24px; height: 24px;
  font-size: 14px; line-height: 1;
  color: var(--text-muted); cursor: pointer;
}
.pop-close:hover { background: var(--bg-row-hover); color: var(--text-primary); }

.pop-body {
  padding: 12px 14px;
  overflow: auto;
  background: var(--bg-card);
}
.pop-body.wide { padding: 8px 12px 12px; }

.pop-loading, .pop-empty {
  padding: 16px; text-align: center; color: var(--text-muted); font-size: 12px;
}

.chips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 6px;
}
.ci-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
}
.ci-chip-icon { font-weight: 700; font-size: 13px; flex-shrink: 0; }
.ci-chip-name { overflow: hidden; text-overflow: ellipsis; }

.ci-pass   { background: var(--color-pass-bg);    color: var(--color-pass); }
.ci-fail   { background: var(--color-danger-bg);  color: var(--color-danger); }
.ci-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.ci-skip   { background: var(--bg-muted);         color: var(--text-muted); }

/* Matrix mode */
.matrix-wrap {
  display: flex; flex-direction: column; gap: 4px;
}
.matrix-head, .matrix-row {
  display: grid; gap: 3px;
  align-items: center;
}
.matrix-head {
  padding: 6px 6px;
  border-bottom: 1px dashed var(--border-light);
  position: sticky; top: 0; z-index: 1;
  background: var(--bg-card);
}
.matrix-head-sn {
  font-size: 10px; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.4px;
}
.matrix-head-ci {
  font-size: 10px; color: var(--text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  text-align: center;
  padding: 0 2px;
}
.matrix-row {
  padding: 3px 6px;
  border-radius: var(--radius-sm);
}
.matrix-row:hover { background: var(--bg-row-hover); }
.matrix-sn-cell { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.matrix-sn-top { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.matrix-sn-label {
  font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-primary);
}
.matrix-cfg {
  padding: 1px 5px;
  background: var(--bg-tag); color: var(--text-secondary);
  font-size: 9px; font-family: var(--font-mono);
  border-radius: var(--radius-sm); font-weight: 600;
}
.matrix-mark {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-info);
  background: var(--color-info-bg);
  padding: 0 5px;
  border-radius: var(--radius-sm);
  width: fit-content;
}
.matrix-dot {
  display: flex; align-items: center; justify-content: center;
  min-width: 0;
  padding: 3px 2px;
  font-size: 11px; font-weight: 700;
  border-radius: var(--radius-sm);
}

.pop-enter-active, .pop-leave-active {
  transition: opacity var(--duration-fast), transform var(--duration-fast);
}
.pop-enter-from, .pop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}
</style>
