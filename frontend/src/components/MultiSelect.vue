<template>
  <div class="multi-select" :class="{ open }" ref="wrapRef">
    <div class="ms-box" @click="focusInput">
      <span v-for="val in modelValue" :key="val" class="ms-tag">
        <span class="ms-tag-text">{{ val }}</span>
        <button class="ms-tag-remove" @click.stop="remove(val)">×</button>
      </span>
      <input
        ref="inputRef"
        v-model="search"
        class="ms-input"
        :placeholder="modelValue.length ? '' : placeholder"
        @focus="open = true"
        @input="open = true"
        @keydown.backspace="onBackspace"
        @keydown.enter.prevent="selectFirst"
        @keydown.escape="open = false"
      />
      <span class="ms-arrow" @click.stop="open = !open">▾</span>
    </div>
    <div v-if="open && filteredOptions.length" class="ms-dropdown">
      <div
        v-for="opt in filteredOptions"
        :key="opt"
        class="ms-option"
        :class="{ selected: modelValue.includes(opt) }"
        @mousedown.prevent="toggle(opt)"
      >
        <span class="ms-option-text">{{ opt }}</span>
        <span v-if="modelValue.includes(opt)" class="ms-check">✓</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Select...' },
})

const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const search = ref('')
const wrapRef = ref(null)
const inputRef = ref(null)

const filteredOptions = computed(() => {
  if (!search.value) return props.options
  const q = search.value.toLowerCase()
  return props.options.filter(o => o.toLowerCase().includes(q))
})

function focusInput() { inputRef.value?.focus() }

function toggle(opt) {
  const arr = [...props.modelValue]
  const idx = arr.indexOf(opt)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(opt)
  emit('update:modelValue', arr)
  search.value = ''
}

function remove(val) {
  emit('update:modelValue', props.modelValue.filter(v => v !== val))
}

function selectFirst() {
  if (filteredOptions.value.length) {
    toggle(filteredOptions.value[0])
  }
}

function onBackspace() {
  if (!search.value && props.modelValue.length) {
    emit('update:modelValue', props.modelValue.slice(0, -1))
  }
}

function onDocClick(e) {
  if (wrapRef.value && !wrapRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onDocClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<style scoped>
.multi-select { position: relative; min-width: 120px; }

.ms-box {
  display: flex; flex-wrap: wrap; align-items: center; gap: 4px;
  min-height: 40px; padding: 4px 8px;
  border: 1px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg-input); cursor: text;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}
.multi-select.open .ms-box,
.ms-box:focus-within {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--border-focus) 12%, transparent);
}

.ms-tag {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 6px;
  background: var(--bg-tag); color: var(--text-primary);
  font-size: 11px; font-family: var(--font-mono);
  border-radius: var(--radius-sm); white-space: nowrap;
  max-width: 140px;
}
.ms-tag-text { overflow: hidden; text-overflow: ellipsis; }
.ms-tag-remove {
  background: none; border: none; color: var(--text-muted);
  font-size: 13px; cursor: pointer; line-height: 1; padding: 0 1px;
}
.ms-tag-remove:hover { color: var(--color-danger); }

.ms-input {
  flex: 1; min-width: 60px; border: none; outline: none;
  background: transparent; color: var(--text-primary);
  font-size: 12px; padding: 2px 0;
}
.ms-input::placeholder { color: var(--text-muted); }

.ms-arrow {
  flex-shrink: 0; font-size: 11px; color: var(--text-muted);
  cursor: pointer; padding: 0 2px;
}

.ms-dropdown {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0;
  z-index: 200;
  background: var(--bg-card); border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card-hover);
  max-height: 220px; overflow-y: auto;
}

.ms-option {
  display: flex; align-items: center; justify-content: space-between;
  padding: 7px 12px; cursor: pointer;
  font-size: 12px; color: var(--text-primary);
  transition: background var(--duration-fast);
}
.ms-option:hover { background: var(--bg-row-hover); }
.ms-option.selected { background: color-mix(in srgb, var(--accent-steel) 8%, var(--bg-card)); }
.ms-option-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ms-check { color: var(--accent-steel); font-size: 12px; font-weight: 700; flex-shrink: 0; }
</style>
