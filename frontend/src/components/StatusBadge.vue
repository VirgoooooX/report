<template>
  <span :class="`badge badge-${type}`">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: 'pending' }
})

const labelMap = {
  pass: 'PASS',
  spec_fail: 'SPEC FAIL',
  strife_fail: 'STRIFE',
  auto: 'Auto',
  manual: 'Manual',
  done: 'Done',
  pending: 'Pending'
}

const label = computed(() => labelMap[props.type] || props.type)
</script>

<style scoped>
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.badge-pass {
  background: #e6f7e6;
  color: #2e7d32;
}
.badge-spec_fail {
  background: #fdecea;
  color: #c62828;
}
.badge-strife_fail {
  background: #fff3e0;
  color: #e65100;
}
.badge-auto {
  background: #e3f2fd;
  color: #1565c0;
}
.badge-manual {
  background: #f3e5f5;
  color: #7b1fa2;
}
.badge-done {
  background: #e8f5e9;
  color: #2e7d32;
}
.badge-pending {
  background: #f5f5f5;
  color: #757575;
}
</style>
