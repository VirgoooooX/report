<template>
  <Teleport to="body">
    <div v-if="show" class="cat-overlay" @click.self="close" @keydown.esc="close" tabindex="-1">
      <div class="cat-modal" :class="{ show: visible }">
        <div class="cat-modal-header">
          <h2 class="cat-modal-title">{{ t('categories.manageCategories') }}</h2>
          <button class="cat-close-btn" @click="close">&times;</button>
        </div>

        <!-- Dynamic tabs -->
        <div class="cat-tabs">
          <button v-for="tab in categoryTabs" :key="tab"
                  class="cat-tab" :class="{ active: activeTab === tab }"
                  @click="activeTab = tab">{{ tab }}</button>
        </div>

        <div class="cat-modal-body" v-if="activeTab">
          <!-- Delete category -->
          <div class="cat-delete-row">
            <button class="cat-delete-btn" @click="deleteCategory">{{ t('categories.deleteCategory') }}</button>
          </div>

          <!-- WF table -->
          <table v-if="currentCategoryWfs.length" class="cat-wf-table">
            <thead><tr><th>WF</th><th>{{ t('categories.name') }}</th><th></th></tr></thead>
            <tbody>
              <tr v-for="wf in currentCategoryWfs" :key="wf">
                <td class="cell-wf">{{ wf }}</td>
                <td class="cell-name">{{ wfName(wf) }}</td>
                <td class="cell-action">
                  <button class="cat-chip-remove" @click="removeWf(wf)">&times;</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="cat-empty-wfs">{{ t('categories.noWfs') }}</div>

          <!-- Add WF -->
          <div class="cat-add-area">
            <input v-model="newWfInput" type="text" class="cat-add-input"
                   :placeholder="t('categories.wfPlaceholder')" @keydown.enter="addWf" />
            <button class="cat-add-btn" :disabled="!newWfInput.trim()" @click="addWf">{{ t('categories.addWf') }}</button>
          </div>

          <!-- Divider + New category -->
          <div class="cat-divider"></div>
          <div class="cat-add-cat-area">
            <input v-model="newCatInput" type="text" class="cat-add-input"
                   :placeholder="t('categories.newCatPlaceholder')" @keydown.enter="addCategory" />
            <button class="cat-add-btn" :disabled="!newCatInput.trim()" @click="addCategory">{{ t('categories.newCategory') }}</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'
import { requestJson } from '@/composables/useApi'
import { useI18n } from '@/i18n/useI18n'

const { t } = useI18n()
const props = defineProps({ show: Boolean })
const emit = defineEmits(['close', 'updated'])
const store = useAppStore()

const categories = ref([])
const activeTab = ref('')
const newWfInput = ref('')
const newCatInput = ref('')
const visible = ref(false)
const error = ref('')

const categoryTabs = computed(() => categories.value.map(c => c.name))

const currentCategoryWfs = computed(() => {
  const cat = categories.value.find(c => c.name === activeTab.value)
  return cat ? (cat.wf_nums || []) : []
})

function close() { emit('close') }

function wfName(wfNum) {
  const key = String(wfNum).replace(/^WF/i, '')
  return store.wfNames[key] || ''
}

async function loadCategories() {
  try {
    const d = await requestJson('/api/categories')
    categories.value = d.categories || []
    if (activeTab.value && !categories.value.find(c => c.name === activeTab.value)) {
      activeTab.value = categories.value[0]?.name || ''
    } else if (!activeTab.value) {
      activeTab.value = categories.value[0]?.name || ''
    }
    error.value = ''
  } catch (e) {
    categories.value = []
    error.value = e.message || t('categories.loadFailed')
  }
}

async function addWf() {
  const wfNum = newWfInput.value.trim()
  if (!wfNum || !activeTab.value) return
  await requestJson(`/api/categories/${encodeURIComponent(activeTab.value)}/add-wf`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wf_num: wfNum })
  })
  newWfInput.value = ''
  await loadCategories()
  emit('updated')
}

async function removeWf(wfNum) {
  if (!activeTab.value) return
  await requestJson(`/api/categories/${encodeURIComponent(activeTab.value)}/remove-wf`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wf_num: wfNum })
  })
  await loadCategories()
  emit('updated')
}

async function addCategory() {
  const name = newCatInput.value.trim()
  if (!name) return
  await requestJson('/api/categories', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, display_order: categories.value.length })
  })
  newCatInput.value = ''
  await loadCategories()
  activeTab.value = name
  emit('updated')
}

async function deleteCategory() {
  if (!activeTab.value) return
  if (!confirm(t('categories.deleteConfirm', { name: activeTab.value }))) return
  await requestJson(`/api/categories/${encodeURIComponent(activeTab.value)}`, { method: 'DELETE' })
  await loadCategories()
  emit('updated')
}

watch(() => props.show, async (val) => {
  if (val) {
    await nextTick()
    visible.value = true
    newWfInput.value = ''
    newCatInput.value = ''
    await loadCategories()
  } else {
    visible.value = false
  }
})
</script>

<style scoped>
.cat-overlay {
  position: fixed; inset: 0; z-index: 1000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(26, 35, 50, 0.4); backdrop-filter: blur(2px);
}
.cat-modal {
  background: #fff; border-radius: 12px;
  box-shadow: var(--shadow-modal);
  width: 90%; max-width: 560px; max-height: 80vh;
  display: flex; flex-direction: column;
  opacity: 0; transform: scale(0.97) translateY(20px);
  transition: opacity 300ms ease-out, transform 300ms ease-out;
}
.cat-modal.show { opacity: 1; transform: scale(1) translateY(0); }
.cat-modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px; border-bottom: 1px solid var(--border-light); flex-shrink: 0;
}
.cat-modal-title {
  font-family: var(--font-display); font-size: 16px; font-weight: 600; color: #1a2332; margin: 0;
}
.cat-close-btn {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  background: none; border: none; font-size: 22px; color: var(--text-muted);
  cursor: pointer; border-radius: var(--radius-sm);
  transition: background var(--duration-fast), color var(--duration-fast);
}
.cat-close-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }

/* Tabs */
.cat-tabs {
  display: flex; gap: 0; border-bottom: 1px solid var(--border-light);
  padding: 0 24px; flex-shrink: 0; overflow-x: auto;
}
.cat-tab {
  padding: 12px 16px; font-family: var(--font-display); font-size: 13px; font-weight: 500;
  color: var(--text-muted); background: none; border: none;
  border-bottom: 2px solid transparent; cursor: pointer; white-space: nowrap;
  transition: color var(--duration-fast), border-color var(--duration-fast);
}
.cat-tab:hover { color: var(--text-primary); }
.cat-tab.active { color: var(--text-primary); border-bottom-color: var(--accent-steel); }

/* Body */
.cat-modal-body {
  padding: 20px 24px; overflow-y: auto; flex: 1;
  display: flex; flex-direction: column; gap: 16px;
}

/* Delete row */
.cat-delete-row { display: flex; justify-content: flex-end; }
.cat-delete-btn {
  padding: 4px 12px; font-size: 12px; font-family: var(--font-display);
  color: var(--color-danger); background: transparent;
  border: 1px solid var(--color-danger); border-radius: var(--radius-sm);
  cursor: pointer; transition: all var(--duration-fast);
}
.cat-delete-btn:hover { background: var(--color-danger); color: #fff; }

/* WF table */
.cat-wf-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.cat-wf-table th {
  text-align: left; padding: 6px 10px; font-size: 11px; font-weight: 600;
  color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-light);
}
.cat-wf-table td { padding: 6px 10px; border-bottom: 1px solid var(--border-light); }
.cell-wf { font-family: var(--font-mono); font-weight: 600; color: var(--text-primary); }
.cell-name { color: var(--text-secondary); }
.cell-action { text-align: right; width: 32px; }

.cat-empty-wfs { font-size: 13px; color: var(--text-muted); text-align: center; }

/* Add WF */
.cat-add-area { display: flex; gap: 8px; }
.cat-add-input {
  flex: 1; padding: 8px 12px; border: 1px solid var(--border-input);
  border-radius: var(--radius-sm); font-size: 14px; font-family: var(--font-mono);
  color: var(--text-primary); background: var(--bg-input); outline: none;
  transition: border-color var(--duration-fast);
}
.cat-add-input::placeholder { color: var(--text-muted); font-family: var(--font-display); }
.cat-add-input:focus { border-color: var(--border-focus); }
.cat-add-btn {
  padding: 8px 18px; background: #4f6f8f; color: #fff; border: none;
  border-radius: var(--radius-sm); font-size: 13px; font-family: var(--font-display);
  font-weight: 500; cursor: pointer; white-space: nowrap;
  transition: opacity var(--duration-fast);
}
.cat-add-btn:hover:not(:disabled) { opacity: 0.9; }
.cat-add-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Divider */
.cat-divider { height: 1px; background: var(--border-light); }

/* Add category */
.cat-add-cat-area { display: flex; gap: 8px; }

.cat-chip-remove {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; background: none; border: none;
  font-size: 16px; line-height: 1; color: var(--text-muted);
  cursor: pointer; padding: 0; border-radius: 50%;
  transition: color var(--duration-fast), background var(--duration-fast);
}
.cat-chip-remove:hover { color: var(--color-danger); background: var(--color-danger-bg); }
</style>
