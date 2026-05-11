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
          <span v-if="uploadState === 'uploading'" class="upload-spinner"></span>
          <template v-if="uploadState === 'done'">&#10003; {{ t('upload.done') }}</template>
          <template v-else-if="uploadState === 'uploading'">{{ t('upload.uploading') }}</template>
          <template v-else>{{ t('upload.idle') }}</template>
        </button>
      </div>
      <div class="nav-controls">
        <button
          class="lang-toggle-btn"
          :title="store.language === 'zh-CN' ? 'Switch to English' : '切换到中文'"
          :aria-label="store.language === 'zh-CN' ? 'Switch to English' : '切换到中文'"
          @click="toggleLanguage"
        >
          <span class="lang-icon" aria-hidden="true">{{ store.language === 'zh-CN' ? '中' : 'EN' }}</span>
        </button>
        <button
          class="theme-btn"
          :title="store.theme === 'dark' ? '切换到浅色模式' : 'Switch to dark mode'"
          :aria-label="store.theme === 'dark' ? '切换到浅色模式' : 'Switch to dark mode'"
          @click="store.toggleTheme()"
        >
          <span class="theme-icon" aria-hidden="true">{{ store.theme === 'dark' ? '☀' : '☾' }}</span>
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

// Upload
const uploadState = ref('idle')
const showUploadDialog = ref(false)
let doneTimer = null

async function onUploadDone(formData) {
  showUploadDialog.value = false
  uploadState.value = 'uploading'
  try {
    await store.uploadReport(formData)
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
.nav-upload-btn {
  height: 32px;
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.82rem; font-weight: 500;
  cursor: pointer;
  transition: color var(--duration-fast), background var(--duration-fast), border-color var(--duration-fast);
  margin-left: 8px;
}
.nav-upload-btn:hover {
  color: var(--text-primary);
  background: var(--bg-card-hover);
}
.nav-upload-btn.uploading {
  color: var(--text-muted); cursor: default;
}
.nav-upload-btn.done {
  color: #059669; border-color: #059669;
}
.upload-spinner {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid var(--border-input);
  border-top-color: var(--text-secondary); border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.nav-controls {
  display: flex; align-items: center; gap: 8px;
}
.lang-toggle-btn,
.theme-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  line-height: 1;
  transition: color var(--duration-fast), background var(--duration-fast), border-color var(--duration-fast);
}
.lang-toggle-btn {
  font-size: 11px;
  font-family: var(--font-display);
  font-weight: 600;
}
.lang-icon,
.theme-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}
.lang-icon {
  min-width: 1.5em;
  font-size: 11px;
  letter-spacing: 0;
  transform: translateY(-0.5px);
}
.theme-icon {
  font-size: 15px;
  transform: translateY(-0.5px);
}
.lang-toggle-btn:hover,
.theme-btn:hover {
  color: var(--text-primary);
  background: var(--bg-card-hover);
}
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
