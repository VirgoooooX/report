<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="cat-overlay"
      @click.self="close"
      @keydown.esc="close"
      tabindex="-1"
    >
      <div class="cat-modal" :class="{ show: visible }">
        <div class="cat-modal-header">
          <h2 class="cat-modal-title">Manage Categories</h2>
          <button class="cat-close-btn" @click="close">&times;</button>
        </div>

        <div class="cat-tabs">
          <button
            v-for="tab in categoryTabs"
            :key="tab"
            class="cat-tab"
            :class="{ active: activeTab === tab }"
            @click="activeTab = tab"
          >
            {{ tab }}
          </button>
        </div>

        <div class="cat-modal-body">
          <div v-if="currentCategoryWfs.length === 0" class="cat-empty-wfs">
            No WFs in this category
          </div>
          <table v-else class="cat-wf-table">
            <thead>
              <tr><th>WF</th><th>Name</th><th></th></tr>
            </thead>
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

          <div class="cat-add-area">
            <input
              v-model="newWfInput"
              type="text"
              class="cat-add-input"
              placeholder="WFxx"
              @keydown.enter="addWf"
            />
            <button class="cat-add-btn" :disabled="!newWfInput.trim()" @click="addWf">
              Add
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useAppStore } from '@/stores/app'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['close', 'updated'])
const store = useAppStore()

const categoryTabs = ['Drop', 'Ingress', 'Environmental', 'Mechanical']
const activeTab = ref('Drop')
const categories = ref([])
const newWfInput = ref('')
const visible = ref(false)

function close() {
  emit('close')
}

function wfName(wfNum) {
  const key = String(wfNum).replace(/^WF/i, '')
  return store.wfNames[key] || ''
}

const currentCategoryWfs = computed(() => {
  const cat = categories.value.find(c => c.name === activeTab.value)
  return cat ? (cat.wf_nums || []) : []
})

async function loadCategories() {
  try {
    const r = await fetch('/api/categories')
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const d = await r.json()
    categories.value = d.categories || []
  } catch (e) {
    categories.value = []
  }
}

async function addWf() {
  const wfNum = newWfInput.value.trim()
  if (!wfNum) return
  try {
    const r = await fetch(`/api/categories/${activeTab.value}/add-wf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wf_num: wfNum })
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    newWfInput.value = ''
    await loadCategories()
    emit('updated')
  } catch (e) {
    // silently fail for now
  }
}

async function removeWf(wfNum) {
  try {
    const r = await fetch(`/api/categories/${activeTab.value}/remove-wf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wf_num: wfNum })
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    await loadCategories()
    emit('updated')
  } catch (e) {
    // silently fail for now
  }
}

watch(() => props.show, async (val) => {
  if (val) {
    await nextTick()
    visible.value = true
    newWfInput.value = ''
    await loadCategories()
  } else {
    visible.value = false
  }
})
</script>

<style scoped>
.cat-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 35, 50, 0.4);
  backdrop-filter: blur(2px);
}

.cat-modal {
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--shadow-modal);
  width: 90%;
  max-width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  opacity: 0;
  transform: scale(0.97) translateY(20px);
  transition: opacity 300ms ease-out, transform 300ms ease-out;
}

.cat-modal.show {
  opacity: 1;
  transform: scale(1) translateY(0);
}

.cat-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.cat-modal-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: #1a2332;
  margin: 0;
}

.cat-close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  font-size: 22px;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast) var(--ease-in-out),
              color var(--duration-fast) var(--ease-in-out);
}

.cat-close-btn:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}

/* Tabs */
.cat-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-light);
  padding: 0 24px;
  flex-shrink: 0;
}

.cat-tab {
  padding: 12px 16px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-in-out),
              border-color var(--duration-fast) var(--ease-in-out);
}

.cat-tab:hover {
  color: var(--text-primary);
}

.cat-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent-steel);
}

/* Body */
.cat-modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* WF table */
.cat-wf-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.cat-wf-table th {
  text-align: left;
  padding: 6px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-light);
}
.cat-wf-table td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--border-light);
}
.cell-wf {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-primary);
}
.cell-name {
  color: var(--text-secondary);
}
.cell-action {
  text-align: right;
  width: 32px;
}

.cat-chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: none;
  border: none;
  font-size: 14px;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  border-radius: 50%;
  transition: color var(--duration-fast) var(--ease-in-out),
              background var(--duration-fast) var(--ease-in-out);
}

.cat-chip-remove:hover {
  color: var(--color-danger);
  background: var(--color-danger-bg);
}

.cat-empty-wfs {
  font-size: 13px;
  color: var(--text-muted);
  font-family: var(--font-display);
}

/* Add area */
.cat-add-area {
  display: flex;
  gap: 8px;
}

.cat-add-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: var(--font-mono);
  color: var(--text-primary);
  background: var(--bg-input);
  outline: none;
  transition: border-color var(--duration-fast) var(--ease-in-out);
}

.cat-add-input::placeholder {
  color: var(--text-muted);
  font-family: var(--font-display);
}

.cat-add-input:focus {
  border-color: var(--border-focus);
}

.cat-add-btn {
  padding: 8px 18px;
  background: #4f6f8f;
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-family: var(--font-display);
  font-weight: 500;
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-in-out);
  white-space: nowrap;
}

.cat-add-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.cat-add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
