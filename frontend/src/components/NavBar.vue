<template>
  <nav class="nav">
    <div class="nav-inner">
      <div class="nav-brand">
        M60 EVT REL
        <span class="nav-badge">Dashboard</span>
      </div>
      <div class="nav-links">
        <router-link to="/">{{ t('nav.dashboard') }}</router-link>
        <router-link to="/daily-update">{{ t('nav.dailyUpdate') }}</router-link>
        <router-link to="/test-summary">{{ t('nav.testSummary') }}</router-link>
        <router-link to="/failure-analysis">{{ t('nav.failureAnalysis') }}</router-link>
        <router-link to="/predictions">{{ t('nav.predictions') }}</router-link>
        <router-link to="/category/Drop">{{ t('nav.categories') }}</router-link>
        <router-link to="/sn">{{ t('nav.snLookup') }}</router-link>
        <router-link to="/export">{{ t('nav.export') }}</router-link>
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
      </div>
      <div class="nav-date">{{ store.reportDate || t('nav.loading') }}</div>
    </div>
  </nav>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'

const store = useAppStore()
const { t } = useI18n()

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
</style>
