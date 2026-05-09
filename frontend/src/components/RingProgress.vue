<template>
  <svg :viewBox="`0 0 ${vb} ${vb}`" xmlns="http://www.w3.org/2000/svg"
       :style="{ maxWidth: maxWidth + 'px' }">
     <circle :cx="vb/2" :cy="vb/2" :r="r" fill="none"
             stroke="var(--bg-progress-track)" :stroke-width="sw" />
     <circle :cx="vb/2" :cy="vb/2" :r="r" fill="none"
             :stroke="color" :stroke-width="sw" stroke-linecap="round"
             :stroke-dasharray="circ" :stroke-dashoffset="offset"
             :transform="`rotate(-90 ${vb/2} ${vb/2})`"
             class="ring-circle" />
     <text :x="vb/2" :y="pctY" text-anchor="middle" fill="var(--text-primary)"
           :font-size="fsPct" font-weight="700" font-family="var(--font-display)">{{ Number(pct).toFixed(1) }}%</text>
     <text v-if="label" :x="vb/2" :y="yLabel" text-anchor="middle" fill="var(--text-secondary)"
           :font-size="fsLabel" font-family="var(--font-display)">{{ label }}</text>
     <text v-if="sublabel" :x="vb/2" :y="ySub" text-anchor="middle" fill="var(--text-muted)"
           :font-size="fsSub" font-family="var(--font-display)">{{ sublabel }}</text>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  pct: { type: Number, default: 0 },
  color: { type: String, default: 'var(--accent-steel)' },
  label: { type: String, default: '' },
  sublabel: { type: String, default: '' },
  size: { type: String, default: 'medium' } // large / medium / small
})

const configs = {
  large:  { vb: 140, r: 58, sw: 10, fsPct: 28, fsLabel: 11, fsSub: 9, yPct: 62, yLabel: 82, ySub: 96, maxWidth: 150 },
  medium: { vb: 120, r: 48, sw: 8,  fsPct: 22, fsLabel: 10, fsSub: 8,  yPct: 54, yLabel: 72, ySub: 84, maxWidth: 130 },
  small:  { vb: 90,  r: 35, sw: 7,  fsPct: 17, fsLabel: 9,  fsSub: 7,  yPct: 40, yLabel: 55, ySub: 65, maxWidth: 100 },
}

const { vb, r, sw, fsPct, fsLabel, fsSub, yPct, yLabel, ySub, maxWidth } = configs[props.size] || configs.medium
const circ = 2 * Math.PI * r
const offset = computed(() => circ * (1 - Math.min(props.pct, 100) / 100))
const pctY = computed(() => (props.label || props.sublabel) ? yPct : (vb / 2 + fsPct / 3))
</script>

<style scoped>
.ring-circle {
  transition: stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
