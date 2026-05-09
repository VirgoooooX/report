<template>
  <nav class="nav">
    <div class="nav-inner">
      <div class="nav-brand">
        M60 EVT REL
        <span class="nav-badge">Dashboard</span>
      </div>
      <div class="nav-links">
        <router-link to="/">Dashboard</router-link>
        <router-link to="/category/Drop">Categories</router-link>
        <router-link to="/test-summary">Test Summary</router-link>
        <router-link to="/sn">SN Lookup</router-link>
        <router-link to="/predictions">Predictions</router-link>
        <router-link to="/export">Export</router-link>
      </div>
      <div class="nav-date">{{ store.reportDate || 'Loading...' }}</div>
    </div>
  </nav>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
const store = useAppStore()
</script>

<style scoped>
.nav {
  position: sticky; top: 0; z-index: 100;
  background: #ffffff;
  box-shadow: 0 1px 0 rgba(0,0,0,0.05);
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
  color: #1a2332; white-space: nowrap;
}
.nav-badge {
  background: #f0f2f5; color: #8e99a8;
  font-size: 11px; padding: 2px 8px; border-radius: 4px;
  font-weight: 500;
}
.nav-links {
  display: flex; gap: 4px; margin-left: auto; align-items: center;
}
.nav-links a {
  color: #8e99a8; text-decoration: none;
  padding: 6px 14px; border-radius: 6px; font-size: 0.85rem;
  font-weight: 500; transition: background 0.2s, color 0.2s;
}
.nav-links a:hover { color: #1a2332; background: rgba(0,0,0,0.04); }
.nav-links a.router-link-active {
  background: #1a2332; color: #ffffff;
}
.nav-date {
  font-family: 'Source Code Pro', monospace;
  font-size: 13px; color: var(--text-muted);
  padding: 4px 12px; background: #f0f2f5;
  border-radius: 6px; white-space: nowrap;
}
</style>
