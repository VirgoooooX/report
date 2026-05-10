<template>
  <div class="sn-quick-search">
    <div class="sn-search-body">
      <div class="sn-search-shell">
        <SearchOutlined class="sn-search-icon" />
        <input
          v-model="query"
          class="sn-input"
          :placeholder="t('snLookup.placeholder')"
          autocomplete="off"
          @input="onInput"
          @keydown.enter="onEnter"
        />
      </div>
      <ul v-if="suggestions.length" class="sn-suggestions">
        <li
          v-for="s in suggestions"
          :key="s.sn"
          class="sn-suggestion-item"
          @click="goToSn(s.sn)"
        >
          {{ s.sn }}
        </li>
      </ul>
      <div v-if="searching" class="sn-searching">{{ t('snLookup.searching') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import SearchOutlined from '@ant-design/icons-vue/es/icons/SearchOutlined'
import { useI18n } from '@/i18n/useI18n'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const store = useAppStore()
const { t } = useI18n()

const query = ref('')
const suggestions = ref([])
const searching = ref(false)
let debounceTimer = null

function onInput() {
  clearTimeout(debounceTimer)
  const q = query.value.trim()
  if (q.length < 2) {
    suggestions.value = []
    return
  }
  debounceTimer = setTimeout(async () => {
    searching.value = true
    try {
      const data = await store.searchSn(q)
      suggestions.value = (data || []).slice(0, 8)
    } catch {
      suggestions.value = []
    } finally {
      searching.value = false
    }
  }, 300)
}

function goToSn(sn) {
  suggestions.value = []
  query.value = sn
  router.push({ name: 'sn', query: { q: sn } })
}

function onEnter() {
  const q = query.value.trim()
  if (q) {
    suggestions.value = []
    router.push({ name: 'sn', query: { q } })
  }
}
</script>

<style scoped>
.sn-quick-search {
  position: relative;
  width: min(100%, 280px);
}

.sn-search-body {
  position: relative;
}

.sn-search-shell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--border-card, #e2e6ed);
  border-radius: 999px;
  background: color-mix(in srgb, var(--bg-card, #fff) 92%, var(--bg-input, #f5f7fa));
  box-shadow: var(--shadow-card), var(--ring-card);
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast), background-color var(--duration-fast);
}

.sn-search-shell:focus-within {
  border-color: var(--border-focus, #4f6f8f);
  box-shadow:
    var(--shadow-card),
    0 0 0 3px color-mix(in srgb, var(--border-focus, #4f6f8f) 14%, transparent);
}

.sn-search-icon {
  flex: 0 0 auto;
  font-size: 14px;
  color: var(--text-muted, #64748b);
}

.sn-input {
  width: 100%;
  min-width: 0;
  padding: 9px 0;
  border: none;
  background: transparent;
  color: var(--text-primary, #1a2332);
  font-size: 13px;
  outline: none;
}

.sn-input::placeholder {
  color: var(--text-muted, #94a3b8);
}

.sn-suggestions {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 50;
  margin: 0;
  padding: 6px 0;
  list-style: none;
  border: 1px solid var(--border-card, #e2e6ed);
  border-radius: 14px;
  background: var(--bg-card, #fff);
  box-shadow: var(--shadow-card-hover), var(--ring-card);
  max-height: 240px;
  overflow-y: auto;
}

.sn-suggestion-item {
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary, #1a2332);
  transition: background var(--duration-fast);
}

.sn-suggestion-item:hover {
  background: var(--bg-row-hover, #f3f4f6);
}

.sn-searching {
  position: absolute;
  top: calc(100% + 8px);
  left: 12px;
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
}

@media (max-width: 760px) {
  .sn-quick-search {
    width: 100%;
  }
}
</style>
