<template>
  <span :class="`badge badge-${type}`">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()

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

const label = computed(() => {
  const raw = labelMap[props.type] || props.type
  if (raw === 'Pending') return t('common.pending')
  if (raw === 'PASS') return t('common.pass')
  if (raw === 'SPEC FAIL') return t('common.spec')
  if (raw === 'STRIFE') return t('common.strife')
  if (raw === 'Auto') return 'Auto'
  if (raw === 'Manual') return 'Manual'
  if (raw === 'Done') return t('common.done')
  return raw
})
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
  background: var(--color-success-bg);
  color: var(--color-success);
}
.badge-spec_fail {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}
.badge-strife_fail {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}
.badge-auto {
  background: var(--color-info-bg);
  color: var(--color-info);
}
.badge-manual {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}
.badge-done {
  background: var(--color-success-bg);
  color: var(--color-success);
}
.badge-pending {
  background: var(--color-info-bg);
  color: var(--color-info);
}
</style>
