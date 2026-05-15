<template>
  <a-config-provider :theme="antTheme">
    <NavBar />
    <div :class="['main', mainClass]">
      <router-view />
    </div>
  </a-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ConfigProvider, theme } from 'ant-design-vue'
import { useAppStore } from '@/stores/app'
import NavBar from '@/components/NavBar.vue'

const store = useAppStore()
const route = useRoute()

const mainClass = computed(() => {
  if (route.name === 'test-summary') return 'main--test-summary'
  if (route.name === 'sn') return 'main--query-center'
  return ''
})

const antTheme = computed(() => ({
  algorithm: store.theme === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
  token: {
    colorPrimary: store.theme === 'dark' ? '#60a5fa' : '#4f6f8f',
    colorBgContainer: store.theme === 'dark' ? '#111827' : '#ffffff',
    colorBgElevated: store.theme === 'dark' ? '#111827' : '#ffffff',
    colorText: store.theme === 'dark' ? '#f8fafc' : '#1a2332',
    colorTextSecondary: store.theme === 'dark' ? '#cbd5e1' : '#4a5568',
    colorTextTertiary: store.theme === 'dark' ? '#94a3b8' : '#64748b',
    colorBorder: store.theme === 'dark' ? '#263244' : '#e2e6ed',
    colorBorderSecondary: store.theme === 'dark' ? '#1f2a3a' : '#edf0f4',
    borderRadius: 8,
    fontFamily: "'Work Sans', system-ui, -apple-system, sans-serif"
  }
}))
</script>

<style>
html {
  scrollbar-gutter: stable;
}
</style>

<style scoped>
.main--test-summary {
  max-width: 1680px;
}
.main--query-center {
  max-width: 1680px;
}
</style>
