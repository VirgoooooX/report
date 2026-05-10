<template>
  <nav class="nav">
    <div class="nav-inner">
      <div class="nav-brand">
        M60 EVT REL
        <span class="nav-badge">Dashboard</span>
      </div>
      <div class="nav-links">
        <router-link to="/">{{ t('nav.dashboard') }}</router-link>
        <router-link to="/category/Drop">{{ t('nav.categories') }}</router-link>
        <router-link to="/test-summary">{{ t('nav.testSummary') }}</router-link>
        <router-link to="/failure-analysis">{{ t('nav.failureAnalysis') }}</router-link>
        <router-link to="/sn">{{ t('nav.snLookup') }}</router-link>
        <router-link to="/predictions">{{ t('nav.predictions') }}</router-link>
        <router-link to="/export">{{ t('nav.export') }}</router-link>
      </div>
      <div class="nav-controls">
        <div class="lang-control">
          <button
            class="lang-btn"
            :class="{ active: store.language === 'zh-CN' }"
            @click="store.setLanguage('zh-CN')"
          >中文</button>
          <button
            class="lang-btn"
            :class="{ active: store.language === 'en-US' }"
            @click="store.setLanguage('en-US')"
          >EN</button>
        </div>
        <button class="theme-btn" @click="store.toggleTheme()">
          <ThunderboltOutlined v-if="store.theme === 'dark'" />
          <ThunderboltFilled v-else />
        </button>
      </div>
      <div class="nav-date">{{ store.reportDate || t('nav.loading') }}</div>
    </div>
  </nav>
</template>

<script setup>
import { ThunderboltOutlined, ThunderboltFilled } from '@ant-design/icons-vue'
import { useAppStore } from '@/stores/app'
import { useI18n } from '@/i18n/useI18n'

const store = useAppStore()
const { t } = useI18n()
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
.lang-control {
  display: flex; border: 1px solid var(--border-input); border-radius: var(--radius-sm); overflow: hidden;
}
.lang-btn {
  padding: 4px 10px; font-size: 12px; font-family: var(--font-display);
  font-weight: 500; background: var(--bg-card); color: var(--text-muted);
  border: none; cursor: pointer; transition: background var(--duration-fast), color var(--duration-fast);
}
.lang-btn:first-child { border-right: 1px solid var(--border-input); }
.lang-btn.active { background: var(--text-primary); color: var(--text-inverse); }
.lang-btn:hover:not(.active) { color: var(--text-primary); }
.theme-btn {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  background: var(--bg-card); border: 1px solid var(--border-input); border-radius: var(--radius-sm);
  color: var(--text-secondary); cursor: pointer; font-size: 16px;
  transition: color var(--duration-fast);
}
.theme-btn:hover { color: var(--text-primary); }
.nav-date {
  font-family: 'Source Code Pro', monospace;
  font-size: 13px; color: var(--text-muted);
  padding: 4px 12px; background: var(--bg-tag);
  border-radius: 6px; white-space: nowrap;
}
</style>
