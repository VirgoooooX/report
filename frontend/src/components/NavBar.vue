<template>
  <nav class="nav">
    <div class="nav-inner">
      <div class="nav-brand">
        {{ store.projectName || 'M60 EVT REL' }}
      </div>
      <div class="nav-links">
        <router-link to="/">{{ t('nav.dashboard') }}</router-link>
        <router-link to="/daily-update">{{ t('nav.dailyUpdate') }}</router-link>
        <router-link to="/test-summary">{{ t('nav.testSummary') }}</router-link>
        <router-link to="/failure-analysis">{{ t('nav.failureAnalysis') }}</router-link>
        <router-link to="/predictions">{{ t('nav.predictions') }}</router-link>
        <router-link to="/schedule">{{ t('nav.schedule') }}</router-link>
        <router-link to="/export">{{ t('nav.export') }}</router-link>
        <button
          class="nav-upload-btn"
          :class="{ uploading: uploadState === 'uploading', done: uploadState === 'done' }"
          :disabled="uploadState === 'uploading'"
          @click="showUploadDialog = true"
        >
          <span class="upload-icon" aria-hidden="true">
            <span v-if="uploadState === 'uploading'" class="upload-spinner"></span>
            <template v-else-if="uploadState === 'done'">&#10003;</template>
            <template v-else>↑</template>
          </span>
          <span class="upload-label">
            <template v-if="uploadState === 'done'">{{ t('upload.done') }}</template>
            <template v-else-if="uploadState === 'uploading'">{{ t('upload.uploading') }}</template>
            <template v-else>{{ t('upload.idle') }}</template>
          </span>
        </button>
      </div>
      <div class="nav-controls">
        <button
          class="nav-icon-btn"
          :title="t('common.refresh')"
          :aria-label="t('common.refresh')"
          :disabled="refreshing"
          @click="onRefresh"
        >
          <span class="icon-symbol" :class="{ spinning: refreshing }" aria-hidden="true">↻</span>
        </button>
        <button
          class="nav-icon-btn"
          :title="store.language === 'zh-CN' ? 'Switch to English' : '切换到中文'"
          :aria-label="store.language === 'zh-CN' ? 'Switch to English' : '切换到中文'"
          @click="toggleLanguage"
        >
          <span class="icon-symbol lang-symbol" aria-hidden="true">{{ store.language === 'zh-CN' ? '中' : 'EN' }}</span>
        </button>
        <button
          class="nav-icon-btn"
          :title="store.theme === 'dark' ? '切换到浅色模式' : 'Switch to dark mode'"
          :aria-label="store.theme === 'dark' ? '切换到浅色模式' : 'Switch to dark mode'"
          @click="store.toggleTheme()"
        >
          <span class="icon-symbol theme-symbol" aria-hidden="true">{{ store.theme === 'dark' ? '☀' : '☾' }}</span>
        </button>
        <button
          class="nav-menu-btn"
          type="button"
          :aria-expanded="mobileOpen"
          aria-controls="mobile-nav"
          @click="mobileOpen = !mobileOpen"
        >
          <MenuOutlined />
        </button>
      </div>
      <div class="nav-date">{{ store.reportDate || t('nav.loading') }}</div>
    </div>
    <div id="mobile-nav" class="mobile-nav" :class="{ open: mobileOpen }">
      <router-link
        v-for="link in navLinks"
        :key="link.to"
        :to="link.to"
        class="mobile-nav-link"
        @click="mobileOpen = false"
      >
        {{ link.label }}
      </router-link>
    </div>
  </nav>
  <UploadDialog :visible="showUploadDialog" @close="showUploadDialog = false" @done="onUploadDone" />
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'
import { MenuOutlined } from '@ant-design/icons-vue'
import UploadDialog from '@/components/UploadDialog.vue'

const store = useAppStore()
const { t } = useI18n()
const mobileOpen = ref(false)
const refreshing = ref(false)

function onRefresh() {
  refreshing.value = true
  store.triggerRefresh()
  setTimeout(() => { refreshing.value = false }, 600)
}

// Upload
const uploadState = ref('idle')
const showUploadDialog = ref(false)
let doneTimer = null

async function onUploadDone(formData) {
  showUploadDialog.value = false
  uploadState.value = 'uploading'
  try {
    await store.uploadReport(formData)
    store.invalidateCache()
    store.checkVersion()
    uploadState.value = 'done'
    doneTimer = setTimeout(() => { uploadState.value = 'idle' }, 3000)
  } catch (e) {
    uploadState.value = 'idle'
    alert(e.message)
  }
}

onUnmounted(() => { if (doneTimer) clearTimeout(doneTimer) })

const navLinks = [
  { to: '/', label: t('nav.dashboard') },
  { to: '/daily-update', label: t('nav.dailyUpdate') },
  { to: '/test-summary', label: t('nav.testSummary') },
  { to: '/failure-analysis', label: t('nav.failureAnalysis') },
  { to: '/predictions', label: t('nav.predictions') },
  { to: '/schedule', label: t('nav.schedule') },
  { to: '/export', label: t('nav.export') },
]

function toggleLanguage() {
  store.setLanguage(store.language === 'zh-CN' ? 'en-US' : 'zh-CN')
}
</script>

<style scoped>
.nav {
  position: sticky; top: 0; z-index: 100;
  background: var(--bg-nav);
  box-shadow: var(--shadow-nav);
  padding: 0 32px;
}
.nav-inner {
  max-width: 1440px; margin: 0 auto;
  display: flex; align-items: center;
  height: 56px; gap: 24px;
}
.nav-brand {
  display: flex; align-items: center; gap: 12px;
  font-family: 'Work Sans', sans-serif;
  font-weight: 700; font-size: 14px;
  color: var(--text-primary); white-space: nowrap;
}
.nav-badge {
  background: var(--bg-tag); color: var(--text-muted);
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
  font-weight: 500;
}
.nav-links {
  display: flex; gap: 4px; margin-left: auto; align-items: center;
}
.nav-links a {
  color: var(--text-muted); text-decoration: none;
  padding: 6px 14px; border-radius: 6px; font-size: 0.85rem;
  font-weight: 500; transition: background 0.2s, color 0.2s;
}
.nav-links a:hover { color: var(--text-primary); background: rgba(0,0,0,0.04); }
.nav-links a.router-link-active {
  background: var(--text-primary); color: var(--text-inverse);
}
/* ── Upload button ── */
.nav-upload-btn {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 16px;
  background: transparent;
  border: 1px dashed var(--border-input);
  border-radius: 20px;
  color: var(--text-secondary);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  margin-left: 8px;
  transition:
    color 0.2s ease,
    background 0.2s ease,
    border-color 0.2s ease,
    border-style 0.2s ease,
    box-shadow 0.2s ease;
}
.nav-upload-btn:hover {
  color: var(--accent-steel);
  background: color-mix(in srgb, var(--accent-steel) 6%, transparent);
  border-color: var(--accent-steel);
  border-style: solid;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-steel) 12%, transparent);
}
.nav-upload-btn.uploading {
  color: var(--text-muted);
  cursor: default;
  border-style: solid;
  box-shadow: none;
}
.nav-upload-btn.uploading:hover {
  background: transparent;
  border-color: var(--border-input);
  box-shadow: none;
}
.nav-upload-btn.done {
  color: #059669;
  border-color: #059669;
  border-style: solid;
  background: color-mix(in srgb, #059669 6%, transparent);
  box-shadow: 0 0 0 3px color-mix(in srgb, #059669 12%, transparent);
}
.upload-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  font-size: 14px;
  line-height: 1;
}
.upload-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--border-input);
  border-top-color: var(--text-muted);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
.upload-label {
  line-height: 1;
}

/* ── Icon bubble buttons ── */
.nav-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-icon-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tag);
  border: 1px solid transparent;
  border-radius: 50%;
  color: var(--text-muted);
  cursor: pointer;
  line-height: 1;
  transition:
    color 0.2s ease,
    background 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}
.nav-icon-btn:hover {
  color: #fff;
  background: var(--accent-steel);
  border-color: var(--accent-steel);
  transform: scale(1.08);
}
.nav-icon-btn:active {
  transform: scale(0.95);
}
.nav-icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}
.nav-icon-btn:disabled:hover {
  color: var(--text-muted);
  background: var(--bg-tag);
  border-color: transparent;
}
.icon-symbol {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
}
.icon-symbol.spinning {
  animation: spin 0.6s linear infinite;
}
.lang-symbol {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
}
.theme-symbol {
  font-size: 15px;
}

@keyframes spin { to { transform: rotate(360deg); } }
.nav-date {
  font-family: 'Source Code Pro', monospace;
  font-size: 13px; color: var(--text-muted);
  padding: 4px 12px; background: var(--bg-tag);
  border-radius: 6px; white-space: nowrap;
}

.nav-menu-btn {
  display: none;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  cursor: pointer;
}

.mobile-nav {
  display: none;
}

@media (max-width: 900px) {
  .nav-links {
    display: none;
  }

  .nav-menu-btn {
    display: inline-flex;
  }

  .mobile-nav {
    display: grid;
    grid-template-columns: 1fr;
    gap: 4px;
    position: absolute;
    left: 12px;
    right: 12px;
    top: calc(100% + 8px);
    padding: 8px;
    border: 1px solid var(--border-card);
    border-radius: var(--radius-md);
    background: var(--bg-card);
    box-shadow: var(--shadow-modal);
    opacity: 0;
    pointer-events: none;
    transform: translateY(-4px);
    transition:
      opacity var(--duration-fast) var(--ease-in-out),
      transform var(--duration-fast) var(--ease-in-out);
    z-index: 50;
  }

  .mobile-nav.open {
    opacity: 1;
    pointer-events: auto;
    transform: translateY(0);
  }

  .mobile-nav-link {
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    text-decoration: none;
  }

  .mobile-nav-link.router-link-active,
  .mobile-nav-link:hover {
    background: var(--bg-row-hover);
  }
}
</style>
