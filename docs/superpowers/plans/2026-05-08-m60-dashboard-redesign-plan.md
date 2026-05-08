# M60 EVT REL Dashboard 前端重设计 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 5 个 Flask HTML 模板迁移为 Vue 3 SPA，视觉从深色主题改为精密工业浅色风格，创建 18 个组件并统一设计系统。

**Architecture:** Vue 3 + Vite SPA，通过 Vite proxy 连接 Flask API (:5050)。Pinia 管理全局状态，vue-chartjs 渲染图表，CSS Variables 管理设计令牌。所有组件使用 scoped CSS。

**Tech Stack:** Vue 3.4, Vite 5, Pinia 2.1, Vue Router 4.3, Chart.js 4.4, vue-chartjs 5.3

**Design Spec:** `docs/superpowers/specs/2026-05-08-m60-dashboard-redesign.md`

---

## File Map

| 文件 | 操作 | 职责 |
|------|------|------|
| `frontend/index.html` | 修改 | 添加 Google Fonts CDN |
| `frontend/src/assets/styles/variables.css` | 重写 | 完整设计令牌（60+ 变量） |
| `frontend/src/assets/styles/global.css` | 重写 | 全局样式、布局类 |
| `frontend/src/main.js` | 不变 | 已正确配置 |
| `frontend/src/App.vue` | 不变 | 已正确配置 |
| `frontend/src/router/index.js` | 不变 | 路由已定义 |
| `frontend/src/stores/app.js` | 扩展 | 新增 actions 和状态 |
| `frontend/src/composables/useApi.js` | 新建 | API 请求封装 |
| `frontend/src/components/NavBar.vue` | 重写 | 浅色主题导航 |
| `frontend/src/components/RingProgress.vue` | 重写 | 浅色环形进度 |
| `frontend/src/components/ConicRing.vue` | 新建 | Conic 环形图 |
| `frontend/src/components/LoadingState.vue` | 新建 | 统一加载态 |
| `frontend/src/components/ErrorState.vue` | 新建 | 统一错误态 |
| `frontend/src/components/EmptyState.vue` | 新建 | 统一空数据态 |
| `frontend/src/components/StatusBadge.vue` | 新建 | 状态徽标 |
| `frontend/src/components/OverviewCards.vue` | 新建 | 概览环形卡片组 |
| `frontend/src/components/CategoryCards.vue` | 新建 | 分类进度卡片 |
| `frontend/src/components/TrendChart.vue` | 新建 | 趋势折线图 |
| `frontend/src/components/TopFailChart.vue` | 新建 | Top 5 失败柱状图 |
| `frontend/src/components/DailyUpdates.vue` | 新建 | 每日 CP 更新 |
| `frontend/src/components/FailureAnalysis.vue` | 新建 | 失败分析表格 |
| `frontend/src/components/TestSummary.vue` | 新建 | 测试摘要矩阵表 |
| `frontend/src/components/FAModal.vue` | 新建 | FA 记录弹窗 |
| `frontend/src/components/CatManageModal.vue` | 新建 | 分类管理弹窗 |
| `frontend/src/views/Dashboard.vue` | 新建 | 主仪表盘页面 |
| `frontend/src/views/CategoryDetail.vue` | 新建 | 分类详情页面 |
| `frontend/src/views/SnLookup.vue` | 新建 | SN 查询页面 |
| `frontend/src/views/PredictionsView.vue` | 新建 | 预测管理页面 |
| `frontend/src/views/ExportView.vue` | 新建 | 批量导出页面 |

---

### Task 1: 基础设计系统 — CSS 变量

**Files:**
- Rewrite: `frontend/src/assets/styles/variables.css`

- [ ] **Step 1: 写入完整 CSS 变量文件**

```css
/* ═══════════════════════════════════════════
   M60 EVT REL — Precision Industrial Design Tokens
   ═══════════════════════════════════════════ */

:root {
  /* ── Background ── */
  --bg-root: #f5f7fa;
  --bg-card: #ffffff;
  --bg-card-hover: #fafbfc;
  --bg-nav: #ffffff;
  --bg-input: #f5f7fa;
  --bg-overlay: rgba(26, 35, 50, 0.4);
  --bg-row-stripe: #fafbfc;
  --bg-row-hover: #f0f4f8;
  --bg-tag: #f0f2f5;
  --bg-progress-track: #e8ecf2;

  /* ── Text ── */
  --text-primary: #1a2332;
  --text-secondary: #4a5568;
  --text-muted: #8e99a8;
  --text-inverse: #ffffff;

  /* ── Borders ── */
  --border-card: #e2e6ed;
  --border-light: #edf0f4;
  --border-input: #d1d5db;
  --border-focus: #4f6f8f;

  /* ── Functional Colors ── */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-info: #4f6f8f;
  --color-success-bg: #f0fdf4;
  --color-warning-bg: #fffbeb;
  --color-danger-bg: #fef2f2;
  --color-info-bg: #f0f4f8;

  /* ── Brand & Chart ── */
  --accent-steel: #4f6f8f;
  --accent-slate: #64748b;
  --chart-r1fnf: #4f6f8f;
  --chart-r2cnm: #0891b2;
  --chart-r3: #d97706;
  --chart-r4: #059669;
  --chart-spec: #ef4444;
  --chart-strife: #f59e0b;
  --cat-drop: #ef4444;
  --cat-ingress: #4f6f8f;
  --cat-environmental: #22c55e;
  --cat-mechanical: #d97706;

  /* ── Typography ── */
  --font-display: 'Work Sans', system-ui, -apple-system, sans-serif;
  --font-mono: 'Source Code Pro', 'JetBrains Mono', 'Cascadia Code', monospace;

  /* ── Spacing (4px grid) ── */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 24px;
  --space-2xl: 32px;
  --space-3xl: 40px;

  /* ── Radii ── */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;

  /* ── Shadows ── */
  --shadow-card: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
  --shadow-card-hover: 0 4px 12px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-modal: 0 20px 60px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05);
  --shadow-nav: 0 1px 0 rgba(0,0,0,0.05);

  /* ── Motion ── */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 500ms;
  --duration-page: 1200ms;
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/assets/styles/variables.css
git commit -m "refactor: replace dark theme CSS variables with precision industrial light theme"
```

---

### Task 2: 全局样式 + Google Fonts

**Files:**
- Modify: `frontend/index.html`
- Rewrite: `frontend/src/assets/styles/global.css`

- [ ] **Step 1: 更新 index.html，添加 Google Fonts**

`frontend/index.html` 的 `<head>` 中插入以下两行（在 `<title>` 之前）：

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;500;600&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
```

- [ ] **Step 2: 重写 global.css**

```css
/* ═══════════════════════════════════════════
   M60 EVT REL — Global Styles
   ═══════════════════════════════════════════ */

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; scroll-behavior: smooth; }
body {
  font-family: var(--font-display);
  background: var(--bg-root);
  color: var(--text-primary);
  min-height: 100vh;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

/* Layout */
.main {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-2xl) var(--space-3xl);
}

/* Card base */
.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-card);
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--duration-fast) var(--ease-in-out);
}
.card:hover { box-shadow: var(--shadow-card-hover); }
.card-clickable {
  cursor: pointer;
  transition: box-shadow var(--duration-fast) var(--ease-in-out),
              transform var(--duration-fast) var(--ease-in-out),
              border-color var(--duration-fast) var(--ease-in-out);
}
.card-clickable:hover {
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-2px);
  border-color: var(--border-card);
}

/* Section */
.section { margin-bottom: var(--space-2xl); }
.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  margin-bottom: 18px;
}
.section-header h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.2px;
  white-space: nowrap;
}
.section-header .divider {
  flex: 1;
  height: 1px;
  background: var(--border-light);
}
.section-header .subtitle {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
}

/* Tables */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  text-align: left;
  padding: 10px 14px;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-row-stripe);
}
.data-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-light);
  font-variant-numeric: tabular-nums;
}
.data-table tbody tr { transition: background var(--duration-fast); cursor: pointer; }
.data-table tbody tr:nth-child(even) { background: var(--bg-row-stripe); }
.data-table tbody tr:hover { background: var(--bg-row-hover); }
.data-table .num { text-align: right; }
.data-table .rank-col { width: 40px; text-align: center; color: var(--text-muted); }
.data-table .rate-high { color: var(--color-danger); font-weight: 600; }

/* Badges */
.badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
}
.badge-pass { background: var(--color-success-bg); color: var(--color-success); }
.badge-spec { background: var(--color-danger-bg); color: var(--color-danger); }
.badge-strife { background: var(--color-warning-bg); color: var(--color-warning); }
.badge-pending { background: var(--color-info-bg); color: var(--color-info); }
.badge-auto { background: var(--color-info-bg); color: var(--color-info); }
.badge-manual { background: var(--color-warning-bg); color: var(--color-warning); }
.badge-done { background: var(--color-success-bg); color: var(--color-success); }

/* Modal shared */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: var(--bg-overlay);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 300ms var(--ease-out);
}
.modal-overlay.open {
  opacity: 1;
  pointer-events: auto;
}
.modal {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-modal);
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transform: translateY(20px) scale(0.97);
  transition: transform 300ms var(--ease-out);
}
.modal-overlay.open .modal {
  transform: translateY(0) scale(1);
}
.modal-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: 18px 24px;
  border-bottom: 1px solid var(--border-light);
}
.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}
.modal-header .close-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 24px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  line-height: 1;
  transition: all var(--duration-fast);
}
.modal-header .close-btn:hover {
  background: var(--bg-row-hover);
  color: var(--text-primary);
}
.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

/* Animations */
@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (max-width: 1200px) {
  .main { padding: var(--space-lg); }
}
@media (max-width: 768px) {
  .main { padding: var(--space-lg) var(--space-lg) var(--space-xl); }
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/index.html frontend/src/assets/styles/global.css
git commit -m "feat: add Google Fonts and rewrite global styles for light theme"
```

---

### Task 3: 工具组件 — LoadingState, ErrorState, EmptyState, StatusBadge

**Files:**
- Create: `frontend/src/components/LoadingState.vue`
- Create: `frontend/src/components/ErrorState.vue`
- Create: `frontend/src/components/EmptyState.vue`
- Create: `frontend/src/components/StatusBadge.vue`

- [ ] **Step 1: 创建 LoadingState.vue**

```vue
<template>
  <div class="loading-state">
    <div class="spinner"></div>
    <span class="loading-text">{{ text }}</span>
  </div>
</template>

<script setup>
defineProps({ text: { type: String, default: 'Loading...' } })
</script>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: var(--space-md);
}
.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-card);
  border-top-color: var(--accent-steel);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.loading-text {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
```

- [ ] **Step 2: 创建 ErrorState.vue**

```vue
<template>
  <div class="error-state">
    <span class="error-icon">!</span>
    <span class="error-msg">{{ message }}</span>
    <button v-if="retry" class="retry-btn" @click="retry">Retry</button>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: 'Failed to load data' },
  retry: { type: Function, default: null }
})
</script>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: var(--space-sm);
  text-align: center;
}
.error-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-danger-bg);
  color: var(--color-danger);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}
.error-msg { font-size: 13px; color: var(--color-danger); }
.retry-btn {
  margin-top: var(--space-sm);
  padding: 8px 20px;
  background: var(--color-danger);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  font-family: var(--font-display);
  transition: opacity var(--duration-fast);
}
.retry-btn:hover { opacity: 0.9; }
</style>
```

- [ ] **Step 3: 创建 EmptyState.vue**

```vue
<template>
  <div class="empty-state">
    <span>{{ text }}</span>
  </div>
</template>

<script setup>
defineProps({ text: { type: String, default: 'No data available' } })
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 14px;
}
</style>
```

- [ ] **Step 4: 创建 StatusBadge.vue**

```vue
<template>
  <span class="badge" :class="'badge-' + type">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  type: {
    type: String,
    required: true,
    validator: v => ['pass','spec_fail','strife_fail','auto','manual','done','pending'].includes(v)
  }
})

const labels = {
  pass: 'Pass', spec_fail: 'Spec Fail', strife_fail: 'Strife Fail',
  auto: 'Auto', manual: 'Manual', done: 'Done', pending: 'Pending'
}
const label = computed(() => labels[props.type] || props.type)
</script>

<style scoped>
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
}
.badge-pass { background: var(--color-success-bg); color: var(--color-success); }
.badge-spec_fail { background: var(--color-danger-bg); color: var(--color-danger); }
.badge-strife_fail { background: var(--color-warning-bg); color: var(--color-warning); }
.badge-auto { background: var(--color-info-bg); color: var(--color-info); }
.badge-manual { background: var(--color-warning-bg); color: var(--color-warning); }
.badge-done { background: var(--color-success-bg); color: var(--color-success); }
.badge-pending { background: var(--bg-tag); color: var(--text-muted); }
</style>
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/LoadingState.vue frontend/src/components/ErrorState.vue frontend/src/components/EmptyState.vue frontend/src/components/StatusBadge.vue
git commit -m "feat: add shared utility components (LoadingState, ErrorState, EmptyState, StatusBadge)"
```

---

### Task 4: API 封装 — useApi composable

**Files:**
- Create: `frontend/src/composables/useApi.js`

- [ ] **Step 1: 创建 useApi.js**

```js
import { ref } from 'vue'

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  async function fetchData(url, options = {}) {
    loading.value = true
    error.value = null
    try {
      const r = await fetch(url, options)
      if (!r.ok) {
        let msg = `HTTP ${r.status}`
        try { const j = await r.json(); if (j.error) msg = j.error } catch (_) {}
        throw new Error(msg)
      }
      return await r.json()
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { loading, error, fetchData }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/composables/useApi.js
git commit -m "feat: add useApi composable for fetch error handling"
```

---

### Task 5: NavBar 重写

**Files:**
- Rewrite: `frontend/src/components/NavBar.vue`

- [ ] **Step 1: 重写 NavBar.vue 为浅色主题**

```vue
<template>
  <nav class="nav">
    <div class="nav-inner">
      <div class="nav-brand">
        <span class="brand-text">M60 EVT REL</span>
        <span class="brand-badge">EVT REL</span>
      </div>
      <div class="nav-links">
        <router-link to="/" exact-active-class="active-link">Dashboard</router-link>
        <router-link to="/category/Drop" active-class="active-link">Categories</router-link>
        <router-link to="/sn" active-class="active-link">SN Lookup</router-link>
        <router-link to="/predictions" active-class="active-link">Predictions</router-link>
        <router-link to="/export" active-class="active-link">Export</router-link>
      </div>
      <div class="nav-date">{{ store.reportDate || '—' }}</div>
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
  background: var(--bg-nav);
  box-shadow: var(--shadow-nav);
  padding: 0 var(--space-2xl);
}
.nav-inner {
  max-width: 1440px; margin: 0 auto;
  display: flex; align-items: center;
  height: 56px; gap: var(--space-xl);
}
.nav-brand {
  display: flex; align-items: center; gap: var(--space-md);
}
.brand-text {
  font-family: var(--font-display);
  font-weight: 700; font-size: 14px;
  color: var(--text-primary);
}
.brand-badge {
  font-size: 10px; font-weight: 600;
  color: var(--text-muted);
  padding: 2px 8px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
}
.nav-links {
  display: flex; gap: var(--space-xs); margin-left: auto; align-items: center;
}
.nav-links a {
  color: var(--text-muted); text-decoration: none;
  padding: 6px 14px; border-radius: var(--radius-sm); font-size: 13px;
  font-weight: 500; font-family: var(--font-display);
  transition: all var(--duration-fast) var(--ease-in-out);
}
.nav-links a:hover { color: var(--text-primary); background: var(--bg-row-hover); }
.nav-links a.active-link {
  color: var(--text-inverse); background: var(--text-primary);
}
.nav-date {
  color: var(--text-secondary); font-size: 13px; font-family: var(--font-mono);
  padding: 4px 12px; background: var(--bg-input);
  border-radius: var(--radius-sm); border: 1px solid var(--border-light);
  white-space: nowrap;
}
@media (max-width: 768px) {
  .nav { padding: 0 var(--space-lg); }
  .nav-links { display: none; }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/NavBar.vue
git commit -m "refactor: rewrite NavBar with light precision industrial theme"
```

---

### Task 6: RingProgress 重写 + ConicRing 创建

**Files:**
- Rewrite: `frontend/src/components/RingProgress.vue`
- Create: `frontend/src/components/ConicRing.vue`

- [ ] **Step 1: 重写 RingProgress.vue**

```vue
<template>
  <svg :viewBox="`0 0 ${c.vb} ${c.vb}`" xmlns="http://www.w3.org/2000/svg"
       :style="{ maxWidth: c.maxWidth + 'px' }" class="ring-svg">
    <circle :cx="c.vb/2" :cy="c.vb/2" :r="c.r" fill="none"
            stroke="var(--bg-progress-track)" :stroke-width="c.sw" />
    <circle :cx="c.vb/2" :cy="c.vb/2" :r="c.r" fill="none"
            :stroke="color" :stroke-width="c.sw" stroke-linecap="round"
            :stroke-dasharray="circ" :stroke-dashoffset="animOffset"
            :transform="`rotate(-90 ${c.vb/2} ${c.vb/2})`"
            class="ring-fill" />
    <text :x="c.vb/2" :y="c.yPct" text-anchor="middle" :fill="textColor"
          :font-size="c.fsPct" font-weight="700" font-family="var(--font-display)">{{ displayPct }}%</text>
    <text v-if="label" :x="c.vb/2" :y="c.yLabel" text-anchor="middle"
          fill="var(--text-secondary)" :font-size="c.fsLabel" font-family="var(--font-display)">{{ label }}</text>
    <text v-if="sublabel" :x="c.vb/2" :y="c.ySub" text-anchor="middle"
          fill="var(--text-muted)" :font-size="c.fsSub" font-family="var(--font-mono)">{{ sublabel }}</text>
  </svg>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'

const props = defineProps({
  pct: { type: Number, default: 0 },
  color: { type: String, default: 'var(--accent-steel)' },
  label: { type: String, default: '' },
  sublabel: { type: String, default: '' },
  size: { type: String, default: 'medium' },
  textColor: { type: String, default: 'var(--text-primary)' },
})

const configs = {
  large:  { vb: 140, r: 58, sw: 10, fsPct: 28, fsLabel: 11, fsSub: 9,  yPct: 62, yLabel: 82, ySub: 96,  maxWidth: 150 },
  medium: { vb: 120, r: 48, sw: 8,  fsPct: 22, fsLabel: 10, fsSub: 8,  yPct: 54, yLabel: 72, ySub: 84,  maxWidth: 130 },
  small:  { vb: 90,  r: 35, sw: 7,  fsPct: 17, fsLabel: 9,  fsSub: 7,  yPct: 40, yLabel: 55, ySub: 65,  maxWidth: 100 },
}

const c = computed(() => configs[props.size] || configs.medium)
const circ = computed(() => 2 * Math.PI * c.value.r)
const displayPct = computed(() => (props.pct || 0).toFixed(1))

const animOffset = ref(circ.value)
onMounted(() => {
  requestAnimationFrame(() => {
    animOffset.value = circ.value * (1 - Math.min(props.pct, 100) / 100)
  })
})
</script>

<style scoped>
.ring-svg { display: block; margin: 0 auto; }
.ring-fill {
  transition: stroke-dashoffset var(--duration-page) var(--ease-out);
}
</style>
```

- [ ] **Step 2: 创建 ConicRing.vue**

```vue
<template>
  <div class="conic-ring" :style="ringStyle" ref="ringRef">
    <div class="conic-inner">
      <span class="conic-pct">{{ displayPct }}%</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  pct: { type: Number, default: 0 },
  size: { type: Number, default: 80 },
})

const displayPct = computed(() => (props.pct || 0).toFixed(1))
const animPct = ref(0)

onMounted(() => {
  const duration = 1200
  const start = performance.now()
  const target = props.pct
  function tick(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animPct.value = target * eased
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
})

const ringStyle = computed(() => {
  const p = animPct.value
  const deg = (p / 100) * 360
  return {
    width: props.size + 'px',
    height: props.size + 'px',
    background: `conic-gradient(var(--accent-steel) 0deg ${deg}deg, var(--bg-progress-track) ${deg}deg 360deg)`,
  }
})
</script>

<style scoped>
.conic-ring {
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
}
.conic-inner {
  width: calc(100% - 12px);
  height: calc(100% - 12px);
  border-radius: 50%;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
}
.conic-pct {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 18px;
  color: var(--text-primary);
}
</style>
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/RingProgress.vue frontend/src/components/ConicRing.vue
git commit -m "refactor: rewrite RingProgress and add ConicRing for light theme"
```

---

### Task 7: OverviewCards 组件

**Files:**
- Create: `frontend/src/components/OverviewCards.vue`

- [ ] **Step 1: 创建 OverviewCards.vue**

```vue
<template>
  <div>
    <LoadingState v-if="loading" text="Loading overview..." />
    <ErrorState v-else-if="error" :message="error" :retry="retry" />
    <div v-else-if="data" class="overview-grid">
      <div class="card overview-card overall">
        <ConicRing :pct="overallPct" :size="80" />
        <div class="ov-label">Overall Completion</div>
        <div class="ov-sub">{{ completedCPs }} / {{ totalCPs }} CPs</div>
      </div>
      <div v-for="cfg in configs" :key="cfg.name"
           class="card overview-card config-card">
        <RingProgress :pct="cfg.pct" :color="cfg.color" :label="cfg.name"
                      :sublabel="`${cfg.completed}/${cfg.total} CPs`" size="small" />
      </div>
    </div>
    <EmptyState v-else text="No completion data" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import RingProgress from './RingProgress.vue'
import ConicRing from './ConicRing.vue'
import LoadingState from './LoadingState.vue'
import ErrorState from './ErrorState.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  retry: { type: Function, default: null },
})

const store = useAppStore()
const CONFIG_ORDER = ['R1FNF', 'R2CNM', 'R3', 'R4']

const configs = computed(() => {
  if (!props.data?.completion?.by_config) return []
  const byConfig = props.data.completion.by_config
  return CONFIG_ORDER.filter(c => byConfig[c]).map(c => ({
    name: c,
    color: store.configColors[c] || 'var(--accent-steel)',
    pct: byConfig[c].pct ?? 0,
    completed: byConfig[c].completed_cps ?? 0,
    total: byConfig[c].total_cps ?? 0,
  }))
})

const completedCPs = computed(() => configs.value.reduce((s, c) => s + c.completed, 0))
const totalCPs = computed(() => configs.value.reduce((s, c) => s + c.total, 0))
const overallPct = computed(() =>
  totalCPs.value > 0 ? (completedCPs.value / totalCPs.value) * 100 : 0
)
</script>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr;
  gap: var(--space-lg);
}
.overview-card {
  padding: 20px var(--space-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.overall {
  padding: var(--space-xl) var(--space-lg);
}
.ov-label {
  font-size: 13px; color: var(--text-secondary);
  margin-top: var(--space-md); font-weight: 500;
}
.ov-sub {
  font-size: 12px; color: var(--text-muted);
  margin-top: var(--space-xs); font-family: var(--font-mono);
}
@media (max-width: 1200px) {
  .overview-grid { grid-template-columns: repeat(3, 1fr); }
  .overall { grid-column: 1 / -1; }
}
@media (max-width: 768px) {
  .overview-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/OverviewCards.vue
git commit -m "feat: add OverviewCards component with ConicRing and config cards"
```

---

### Task 8: CategoryCards 组件

**Files:**
- Create: `frontend/src/components/CategoryCards.vue`

- [ ] **Step 1: 创建 CategoryCards.vue**

```vue
<template>
  <div>
    <LoadingState v-if="loading" text="Loading categories..." />
    <ErrorState v-else-if="error" :message="error" :retry="retry" />
    <div v-else-if="categories.length" class="cat-grid">
      <div v-for="cat in categories" :key="cat.name"
           class="card card-clickable cat-card"
           :style="{ '--cat-color': cat.color }"
           @click="$router.push(`/category/${encodeURIComponent(cat.name)}`)">
        <div class="cat-name">{{ cat.name }}</div>
        <div class="cat-bar-track">
          <div class="cat-bar-fill" :style="{ width: cat.pct + '%' }"></div>
        </div>
        <div class="cat-stats">
          <span class="cat-pct">{{ cat.pct.toFixed(1) }}%</span>
          <span class="cat-count">{{ cat.completed || 0 }} / {{ cat.total || 0 }} CPs</span>
        </div>
      </div>
    </div>
    <EmptyState v-else text="No category data" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import LoadingState from './LoadingState.vue'
import ErrorState from './ErrorState.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  retry: { type: Function, default: null },
})

const store = useAppStore()
const CAT_ORDER = ['Drop', 'Ingress', 'Environmental', 'Mechanical']

const categories = computed(() => {
  if (!props.data?.completion?.by_category) return []
  const byCat = props.data.completion.by_category
  return CAT_ORDER.map(name => {
    const d = byCat[name]
    return {
      name,
      color: store.catColors[name] || 'var(--accent-steel)',
      pct: d?.pct ?? 0,
      completed: d?.completed_cps ?? 0,
      total: d?.total_cps ?? 0,
    }
  })
})
</script>

<style scoped>
.cat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-lg);
}
.cat-card {
  position: relative; overflow: hidden;
  padding: 20px 22px;
}
.cat-card::before {
  content: '';
  position: absolute; top: 0; left: 0;
  width: 4px; height: 100%;
  background: var(--cat-color);
}
.cat-name {
  font-size: 14px; font-weight: 600;
  color: var(--cat-color); margin-bottom: var(--space-md);
}
.cat-bar-track {
  width: 100%; height: 8px;
  background: var(--bg-progress-track);
  border-radius: 4px; overflow: hidden;
}
.cat-bar-fill {
  height: 100%; border-radius: 4px;
  background: var(--cat-color);
  transition: width 1s var(--ease-out);
}
.cat-stats {
  display: flex; justify-content: space-between;
  margin-top: var(--space-sm);
}
.cat-pct { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.cat-count { font-size: 12px; color: var(--text-muted); }
@media (max-width: 768px) {
  .cat-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/CategoryCards.vue
git commit -m "feat: add CategoryCards component with color-coded progress"
```

---

### Task 9: 图表组件 — TrendChart + TopFailChart

**Files:**
- Create: `frontend/src/components/TrendChart.vue`
- Create: `frontend/src/components/TopFailChart.vue`

- [ ] **Step 1: 创建 TrendChart.vue**

```vue
<template>
  <div class="chart-card card">
    <h3>Failure Rate Trend</h3>
    <div class="chart-wrapper">
      <LoadingState v-if="loading" text="Loading chart..." />
      <EmptyState v-else-if="!hasData" text="No trend data available" />
      <Line v-else :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler
} from 'chart.js'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const props = defineProps({
  trend: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const hasData = computed(() => props.trend.length > 0)

const chartData = computed(() => ({
  labels: props.trend.map(d => (d.date || '').slice(5)),
  datasets: [
    {
      label: 'Spec Failures',
      data: props.trend.map(d => d.spec || 0),
      borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)',
      fill: true, tension: 0.3, pointRadius: 3, pointHoverRadius: 6,
      pointBackgroundColor: '#ef4444', borderWidth: 2,
    },
    {
      label: 'Strife Failures',
      data: props.trend.map(d => d.strife || 0),
      borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.08)',
      fill: true, tension: 0.3, pointRadius: 3, pointHoverRadius: 6,
      pointBackgroundColor: '#f59e0b', borderWidth: 2,
    },
  ],
}))

const chartOptions = {
  responsive: true, maintainAspectRatio: false,
  interaction: { intersect: false, mode: 'index' },
  plugins: {
    legend: {
      labels: { color: '#8e99a8', font: { size: 11, family: "'Work Sans', sans-serif" }, boxWidth: 12, padding: 12 }
    },
    tooltip: {
      backgroundColor: '#1a2332', titleColor: '#fff', bodyColor: '#9ca3b8',
      borderColor: 'rgba(255,255,255,0.08)', borderWidth: 1, padding: 10, cornerRadius: 8,
    }
  },
  scales: {
    x: { ticks: { color: '#8e99a8', font: { size: 10 } }, grid: { color: '#edf0f4' } },
    y: { beginAtZero: true, ticks: { color: '#8e99a8', font: { size: 10 } }, grid: { color: '#edf0f4' } },
  }
}
</script>

<style scoped>
.chart-card { padding: 20px; }
.chart-card h3 { font-size: 14px; font-weight: 600; margin-bottom: 14px; color: var(--text-primary); }
.chart-wrapper { position: relative; height: 280px; }
</style>
```

- [ ] **Step 2: 创建 TopFailChart.vue**

```vue
<template>
  <div class="chart-card card">
    <h3>Top 5 Failure Items</h3>
    <div class="chart-wrapper">
      <LoadingState v-if="loading" text="Loading chart..." />
      <EmptyState v-else-if="!hasData" text="No failure data" />
      <Bar v-else :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps({
  items: { type: Array, default: () => [] },
  wfNames: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})

const hasData = computed(() => props.items.length > 0)

const top5 = computed(() => props.items.slice(0, 5))

function getColor(rate) {
  if (rate > 50) return 'rgba(239,68,68,0.7)'
  if (rate > 20) return 'rgba(245,158,11,0.7)'
  return 'rgba(79,111,143,0.7)'
}
function getBorder(rate) {
  if (rate > 50) return '#ef4444'
  if (rate > 20) return '#f59e0b'
  return '#4f6f8f'
}

const chartData = computed(() => ({
  labels: top5.value.map(f => {
    const name = f.wf && props.wfNames[f.wf] ? ` ${props.wfNames[f.wf]}` : ''
    return `WF${f.wf || '?'}${name} ${f.cfg || ''} ${f.test || ''}`.trim()
  }),
  datasets: [{
    label: 'Failure Rate %',
    data: top5.value.map(f => f.rate || 0),
    backgroundColor: top5.value.map(f => getColor(f.rate)),
    borderColor: top5.value.map(f => getBorder(f.rate)),
    borderWidth: 1, borderRadius: 4,
  }]
}))

const chartOptions = {
  indexAxis: 'y', responsive: true, maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1a2332', titleColor: '#fff', bodyColor: '#9ca3b8',
      borderColor: 'rgba(255,255,255,0.08)', borderWidth: 1, padding: 10, cornerRadius: 8,
      callbacks: { label: ctx => `${ctx.parsed.x.toFixed(1)}% failure rate` }
    }
  },
  scales: {
    x: {
      beginAtZero: true, max: 100,
      ticks: { color: '#8e99a8', font: { size: 10 }, callback: v => v + '%' },
      grid: { color: '#edf0f4' }
    },
    y: { ticks: { color: '#8e99a8', font: { size: 10 } }, grid: { color: '#edf0f4' } }
  }
}
</script>

<style scoped>
.chart-card { padding: 20px; }
.chart-card h3 { font-size: 14px; font-weight: 600; margin-bottom: 14px; color: var(--text-primary); }
.chart-wrapper { position: relative; height: 280px; }
</style>
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/TrendChart.vue frontend/src/components/TopFailChart.vue
git commit -m "feat: add TrendChart and TopFailChart with vue-chartjs"
```

---

### Task 10: DailyUpdates 组件

**Files:**
- Create: `frontend/src/components/DailyUpdates.vue`

- [ ] **Step 1: 创建 DailyUpdates.vue**

```vue
<template>
  <div class="card daily-card">
    <LoadingState v-if="loading" text="Loading daily updates..." />
    <ErrorState v-else-if="error" :message="error" :retry="retry" />
    <EmptyState v-else-if="!hasData" text="No CP updates today" />
    <template v-else>
      <div class="daily-header" :class="{ open: isOpen }" @click="isOpen = !isOpen">
        <span class="chevron">▶</span>
        <span class="dh-title">CP Changes Today</span>
        <span class="dh-count">{{ totalWFs }} WF(s) updated</span>
        <button class="dh-toggle" @click.stop="isOpen = !isOpen">Toggle</button>
      </div>
      <div class="daily-body" :class="{ open: isOpen }">
        <div class="daily-inner">
          <div v-for="wf in wfList" :key="wf.wf" class="wf-group">
            <div class="wf-row">
              <span class="wf-badge">{{ wf.wf }}</span>
              <span v-if="wf.wfName" class="wf-name">{{ wf.wfName }}</span>
              <span class="wf-config-count">{{ wf.configs.length }} config(s)</span>
            </div>
            <div v-for="cfg in wf.configs" :key="cfg.config" class="cfg-row">
              <span class="cfg-name">{{ cfg.config }}</span>
              <span class="cfg-delta">+{{ cfg.cp_delta }} CPs</span>
              <span class="cfg-latest">latest: {{ cfg.latest_cp }} (CP {{ (cfg.latest_cp_idx || 0) + 1 }}/{{ cfg.total_cps }})</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import LoadingState from './LoadingState.vue'
import ErrorState from './ErrorState.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  wfUpdates: { type: Array, default: () => [] },
  wfNames: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  retry: { type: Function, default: null },
})

const isOpen = ref(true)
const hasData = computed(() => props.wfUpdates.length > 0)
const totalWFs = computed(() => props.wfUpdates.length)

const wfList = computed(() => {
  return [...props.wfUpdates].sort((a, b) => {
    const ka = a.wf, kb = b.wf
    return String(ka).localeCompare(String(kb), undefined, { numeric: true })
  })
})
</script>

<style scoped>
.daily-card { padding: 0; overflow: hidden; }
.daily-header {
  display: flex; align-items: center; gap: var(--space-lg);
  padding: 16px 20px;
  cursor: pointer; user-select: none;
  transition: background var(--duration-fast);
}
.daily-header:hover { background: var(--bg-card-hover); }
.chevron {
  transition: transform var(--duration-normal) var(--ease-in-out);
  color: var(--text-muted); font-size: 12px; flex-shrink: 0;
}
.daily-header.open .chevron { transform: rotate(90deg); }
.dh-title { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.dh-count { font-size: 12px; color: var(--text-muted); margin-left: auto; }
.dh-toggle {
  background: var(--bg-input); border: 1px solid var(--border-light);
  color: var(--text-secondary); padding: 4px 12px;
  border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;
  font-family: var(--font-display);
  transition: all var(--duration-fast);
}
.dh-toggle:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.daily-body { max-height: 0; overflow: hidden; transition: max-height 400ms var(--ease-out); }
.daily-body.open { max-height: 3000px; }
.daily-inner { padding: 0 20px 16px; }
.wf-group { border-bottom: 1px solid var(--border-light); }
.wf-group:last-child { border-bottom: none; }
.wf-row {
  display: flex; align-items: center; gap: var(--space-md);
  padding: 10px 0;
}
.wf-badge {
  background: var(--text-primary); color: var(--text-inverse);
  font-size: 11px; font-weight: 600; padding: 3px 10px;
  border-radius: var(--radius-sm); font-family: var(--font-mono);
}
.wf-name { font-size: 13px; color: var(--text-secondary); }
.wf-config-count {
  margin-left: auto; font-size: 12px; color: var(--text-muted);
}
.cfg-row {
  display: flex; align-items: center; gap: var(--space-sm);
  padding: 6px 0 6px 36px; font-size: 13px;
}
.cfg-name { color: var(--color-info); font-weight: 600; font-family: var(--font-mono); min-width: 70px; }
.cfg-delta { color: var(--color-success); font-weight: 600; }
.cfg-latest { color: var(--text-muted); font-size: 12px; }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/DailyUpdates.vue
git commit -m "feat: add DailyUpdates collapsible component"
```

---

### Task 11: FailureAnalysis 组件

**Files:**
- Create: `frontend/src/components/FailureAnalysis.vue`

- [ ] **Step 1: 创建 FailureAnalysis.vue**

```vue
<template>
  <div class="card fail-card">
    <LoadingState v-if="loading" text="Loading failure data..." />
    <ErrorState v-else-if="error" :message="error" :retry="retry" />
    <template v-else-if="data">
      <div class="fail-tabs">
        <button v-for="tab in tabs" :key="tab.id"
                class="fail-tab" :class="{ active: activeTab === tab.id }"
                @click="activeTab = tab.id">{{ tab.label }}</button>
      </div>
      <div class="fail-body" :key="activeTab">
        <table class="data-table">
          <thead>
            <tr>
              <th class="rank-col">#</th>
              <th>Dimension</th>
              <th class="num">Spec Fail</th>
              <th class="num">Strife Fail</th>
              <th class="num">Total</th>
              <th class="num">Failure Rate</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in tableRows" :key="idx"
                :class="{ 'fail-row': row.rate > 0 }"
                @click="row.wf ? $emit('select', row) : null"
                :style="{ cursor: row.wf ? 'pointer' : 'default' }">
              <td class="rank-col">{{ idx + 1 }}</td>
              <td>{{ row.dim }}</td>
              <td class="num">{{ fmtNum(row.spec) }}</td>
              <td class="num">{{ fmtNum(row.strife) }}</td>
              <td class="num">{{ fmtNum(row.total) }}</td>
              <td class="num" :class="{ 'rate-high': row.rate > 0 }">{{ row.rate.toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <EmptyState v-else text="No failure data" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import LoadingState from './LoadingState.vue'
import ErrorState from './ErrorState.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  data: { type: Object, default: null },
  wfNames: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  retry: { type: Function, default: null },
})

defineEmits(['select'])

const tabs = [
  { id: 'by_test', label: 'By Test Item' },
  { id: 'by_config', label: 'By Config' },
  { id: 'by_wf', label: 'By WF' },
  { id: 'top_n', label: 'Top N' },
]
const activeTab = ref('by_test')

const tableRows = computed(() => {
  if (!props.data?.failures) return []
  const f = props.data.failures
  let rows = []

  if (activeTab.value === 'by_config') {
    const byCfg = f.by_config || {}
    rows = Object.entries(byCfg).map(([k, v]) => ({
      dim: k, spec: v.spec_fails || 0, strife: v.strife_fails || 0,
      total: v.total_tests || 0, rate: v.total_rate || 0, wf: '', cfg: k
    }))
  } else if (activeTab.value === 'by_wf') {
    const byWf = f.by_wf || {}
    rows = Object.entries(byWf)
      .sort(([a], [b]) => String(a).localeCompare(String(b), undefined, { numeric: true }))
      .map(([k, v]) => {
        const name = props.wfNames[k] ? ` ${props.wfNames[k]}` : ''
        return { dim: `WF${k}${name}`, spec: v.spec_fails || 0, strife: v.strife_fails || 0,
          total: v.total_tests || 0, rate: v.total_rate || 0, wf: k, cfg: '' }
      })
  } else {
    const items = activeTab.value === 'top_n' ? (f.top_failures || []).slice(0, 20) : (f.top_failures || [])
    rows = items.map(item => {
      const name = item.wf && props.wfNames[item.wf] ? ` ${props.wfNames[item.wf]}` : ''
      return {
        dim: `WF${item.wf || '?'}${name} ${item.cfg || ''} ${item.test || ''}`.trim(),
        spec: item.spec || 0, strife: item.strife || 0,
        total: item.total || 0, rate: item.rate || 0,
        wf: item.wf, cfg: item.cfg, test: item.test
      }
    })
  }
  rows.sort((a, b) => b.rate - a.rate)
  return rows
})

function fmtNum(v) {
  return v != null ? Number(v).toLocaleString() : '—'
}
</script>

<style scoped>
.fail-card { padding: 0; overflow: hidden; }
.fail-tabs {
  display: flex; gap: 0;
  border-bottom: 1px solid var(--border-light);
  overflow-x: auto;
}
.fail-tab {
  padding: 12px 22px; font-size: 13px; font-weight: 500;
  color: var(--text-muted); cursor: pointer; white-space: nowrap;
  border: none; border-bottom: 2px solid transparent;
  background: none; font-family: var(--font-display);
  transition: all var(--duration-fast) var(--ease-in-out);
}
.fail-tab:hover { color: var(--text-secondary); }
.fail-tab.active {
  color: var(--text-primary); font-weight: 600;
  border-bottom-color: var(--accent-steel);
}
.fail-body { padding: 16px 20px; }
.fail-row td:first-child { border-left: 3px solid var(--color-danger); }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/FailureAnalysis.vue
git commit -m "feat: add FailureAnalysis component with tabbed views"
```

---

### Task 12: TestSummary 组件

**Files:**
- Create: `frontend/src/components/TestSummary.vue`

- [ ] **Step 1: 创建 TestSummary.vue**

```vue
<template>
  <div class="card summary-card">
    <LoadingState v-if="loading" text="Loading test summary..." />
    <ErrorState v-else-if="error" :message="error" :retry="retry" />
    <template v-else-if="hasData">
      <div class="summary-scroll">
        <table class="summary-table">
          <thead>
            <tr>
              <th class="wf-col" rowspan="2">WF</th>
              <th v-for="cfg in configList" :key="cfg" class="cfg-header"
                  :colspan="maxTests" :style="{ color: configColors[cfg] || 'var(--text-muted)' }">{{ cfg }}</th>
            </tr>
            <tr>
              <template v-for="cfg in configList" :key="'h2-'+cfg">
                <th v-for="t in maxTests" :key="t">{{ testNames[t-1] || 'Test'+t }}</th>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr v-for="wf in sortedSummary" :key="wf.wf">
              <td class="wf-col">{{ wf.wf }}</td>
              <template v-for="cfg in configList" :key="cfg">
                <td v-for="t in maxTests" :key="t"
                    :class="cellClass(wf, cfg, testNames[t-1])"
                    @click="onCellClick(wf, cfg, testNames[t-1])">
                  {{ cellText(wf, cfg, testNames[t-1]) }}
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <EmptyState v-else text="No test summary available" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import LoadingState from './LoadingState.vue'
import ErrorState from './ErrorState.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  summary: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null },
  retry: { type: Function, default: null },
})

const emit = defineEmits(['cell-click'])

const configColors = { R1FNF: '#4f6f8f', R2CNM: '#0891b2', R3: '#d97706', R4: '#059669' }
const CONFIG_ORDER = ['R1FNF', 'R2CNM', 'R3', 'R4']

const configList = computed(() => {
  const all = new Set()
  props.summary.forEach(wf => { if (wf.configs) Object.keys(wf.configs).forEach(c => all.add(c)) })
  const ordered = CONFIG_ORDER.filter(c => all.has(c))
  CONFIG_ORDER.forEach(c => all.delete(c))
  return [...ordered, ...all]
})

const maxTests = computed(() => {
  let max = 0
  props.summary.forEach(wf => {
    if (wf.configs) {
      Object.values(wf.configs).forEach(cfg => {
        const n = Object.keys(cfg).length
        if (n > max) max = n
      })
    }
  })
  return max || 1
})

const testNames = computed(() => {
  const names = []
  for (const wf of props.summary) {
    if (wf.configs) {
      for (const cfg of Object.values(wf.configs)) {
        Object.keys(cfg).forEach(t => {
          const idx = parseInt(t.replace('Test', '')) - 1
          if (!names[idx]) names[idx] = t
        })
      }
    }
  }
  for (let i = 0; i < maxTests.value; i++) {
    if (!names[i]) names[i] = `Test${i + 1}`
  }
  return names
})

const sortedSummary = computed(() => {
  return [...props.summary].sort((a, b) => {
    return String(a.wf).localeCompare(String(b.wf), undefined, { numeric: true })
  })
})

const hasData = computed(() => props.summary.length > 0)

function getCell(wf, cfg, testName) {
  return wf.configs?.[cfg]?.[testName] || null
}

function cellClass(wf, cfg, testName) {
  const cell = getCell(wf, cfg, testName)
  if (!cell) return 'cell-empty'
  if (cell.spec > 0) return 'cell-fail'
  if (cell.strife > 0) return 'cell-strife'
  return 'cell-pass'
}

function cellText(wf, cfg, testName) {
  const cell = getCell(wf, cfg, testName)
  return cell?.result || '—'
}

function onCellClick(wf, cfg, testName) {
  const cell = getCell(wf, cfg, testName)
  if (cell && (cell.spec > 0 || cell.strife > 0)) {
    emit('cell-click', { wf: wf.wf, cfg, test: testName, sns: cell.failure_sns || [] })
  }
}
</script>

<style scoped>
.summary-card { padding: 0; overflow: hidden; }
.summary-scroll { overflow-x: auto; padding: 4px; }
.summary-table {
  width: 100%; border-collapse: collapse;
  font-size: 13px; min-width: 800px;
}
.summary-table th {
  padding: 10px 10px; font-weight: 600; font-size: 10px;
  text-transform: uppercase; letter-spacing: 0.3px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-row-stripe);
  text-align: center; white-space: nowrap;
}
.summary-table th.wf-col { text-align: left; min-width: 70px; }
.summary-table th.cfg-header { color: var(--text-secondary); }
.summary-table td {
  padding: 10px 10px; text-align: center;
  border-bottom: 1px solid var(--border-light);
  font-variant-numeric: tabular-nums;
  transition: filter var(--duration-fast);
}
.summary-table td.wf-col {
  text-align: left; font-weight: 600;
  color: var(--text-secondary); font-family: var(--font-mono);
}
.cell-pass { background: var(--color-success-bg); color: var(--color-success); }
.cell-strife { background: var(--color-warning-bg); color: var(--color-warning); cursor: pointer; }
.cell-fail { background: var(--color-danger-bg); color: var(--color-danger); cursor: pointer; font-weight: 600; }
.cell-empty { color: var(--text-muted); opacity: 0.4; }
.cell-strife:hover, .cell-fail:hover { filter: brightness(0.95); }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/TestSummary.vue
git commit -m "feat: add TestSummary matrix table component"
```

---

### Task 13: 弹窗组件 — FAModal + CatManageModal

**Files:**
- Create: `frontend/src/components/FAModal.vue`
- Create: `frontend/src/components/CatManageModal.vue`

- [ ] **Step 1: 创建 FAModal.vue**

```vue
<template>
  <div class="modal-overlay" :class="{ open: show }" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>
      <div class="modal-body">
        <LoadingState v-if="loading" text="Loading FA records..." />
        <ErrorState v-else-if="error" :message="error" :retry="loadRecords" />
        <template v-else-if="records !== null">
          <div v-if="presetSns.length" class="affected-sns">
            Affected SNs:
            <span v-for="sn in presetSns" :key="sn" class="sn-tag">{{ sn }}</span>
          </div>
          <div v-if="records.length === 0" class="fa-empty">
            <p>No FA records found{{ wf ? ` for WF${wf}` : '' }}.</p>
            <p v-if="presetSns.length" class="sn-hint">Affected SNs: {{ presetSns.join(', ') }}</p>
          </div>
          <div v-for="(rec, i) in records" :key="i" class="fa-record">
            <span v-for="(v, k) in rec" :key="k" class="fa-field">
              <span class="fa-label">{{ k }}:</span> {{ v }}
            </span>
          </div>
          <div v-if="records.length" class="fa-count">{{ records.length }} record(s) found</div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import LoadingState from './LoadingState.vue'
import ErrorState from './ErrorState.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  show: { type: Boolean, default: false },
  wf: { type: String, default: '' },
  title: { type: String, default: 'FA Records' },
  presetSns: { type: Array, default: () => [] },
})

defineEmits(['close'])

const { loading, error, fetchData } = useApi()
const records = ref(null)

async function loadRecords() {
  records.value = null
  try {
    let url = '/api/fa/list'
    if (props.wf) url += `?wf=${encodeURIComponent(props.wf)}`
    const data = await fetchData(url)
    records.value = data.records || []
  } catch (_) { records.value = [] }
}

watch(() => props.show, (v) => { if (v) loadRecords() })

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && props.show) props.show = false
})
</script>

<style scoped>
.affected-sns { margin-bottom: 14px; font-size: 13px; color: var(--text-muted); }
.sn-tag {
  display: inline-block; margin-left: 4px;
  padding: 2px 8px; background: var(--bg-tag);
  border-radius: var(--radius-sm); font-family: var(--font-mono);
  font-size: 11px; color: var(--text-secondary); font-weight: 500;
}
.fa-empty { text-align: center; padding: 40px 20px; color: var(--text-muted); }
.sn-hint { margin-top: 8px; font-size: 12px; }
.fa-record {
  padding: 12px 16px; background: var(--bg-root);
  border-radius: var(--radius-sm); margin-bottom: 8px;
  border-left: 3px solid var(--accent-steel); font-size: 13px;
}
.fa-field { display: inline-block; margin-right: 16px; margin-bottom: 4px; }
.fa-label { color: var(--text-muted); font-size: 11px; }
.fa-count { margin-top: 12px; font-size: 12px; color: var(--text-muted); }
</style>
```

- [ ] **Step 2: 创建 CatManageModal.vue**

```vue
<template>
  <div class="modal-overlay" :class="{ open: show }" @click.self="$emit('close')">
    <div class="modal" style="max-width:550px">
      <div class="modal-header">
        <h3>Manage Categories</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>
      <div class="modal-body" v-if="activeCat">
        <LoadingState v-if="loading" text="Loading categories..." />
        <ErrorState v-else-if="error" :message="error" :retry="loadData" />
        <template v-else>
          <div class="cat-manage-tabs">
            <button v-for="cat in CAT_ORDER" :key="cat"
                    class="cat-tab" :class="{ active: activeCat === cat }"
                    @click="activeCat = cat">{{ cat }}</button>
          </div>
          <div class="cat-wf-list">
            <span v-if="wfList.length === 0" class="no-wfs">No WFs assigned to {{ activeCat }}</span>
            <span v-for="wfn in wfList" :key="wfn" class="wf-chip">
              WF{{ wfn }}
              <button class="chip-remove" @click="removeWf(wfn)" title="Remove">&times;</button>
            </span>
          </div>
          <div class="cat-add">
            <input type="text" v-model="newWf" placeholder="Enter WF number (e.g. 10)"
                   @keydown.enter="addWf" ref="addInput">
            <button @click="addWf">Add WF</button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import LoadingState from './LoadingState.vue'
import ErrorState from './ErrorState.vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({ show: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'updated'])

const CAT_ORDER = ['Drop', 'Ingress', 'Environmental', 'Mechanical']
const { loading, error, fetchData } = useApi()

const activeCat = ref(CAT_ORDER[0])
const wfList = ref([])
const newWf = ref('')
const addInput = ref(null)

async function loadData() {
  try {
    const data = await fetchData('/api/categories')
    const found = (data.categories || []).find(c => c.name === activeCat.value)
    wfList.value = found?.wf_nums || []
  } catch (_) { wfList.value = [] }
}

watch(() => props.show, (v) => {
  if (v) { activeCat.value = CAT_ORDER[0]; loadData() }
})
watch(activeCat, () => { newWf.value = ''; loadData() })

async function addWf() {
  const wf = newWf.value.trim()
  if (!wf) return
  try {
    await fetchData(`/api/categories/${encodeURIComponent(activeCat.value)}/add-wf`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wf_num: wf })
    })
    newWf.value = ''
    await loadData()
    emit('updated')
  } catch (_) {}
}

async function removeWf(wf) {
  try {
    await fetchData(`/api/categories/${encodeURIComponent(activeCat.value)}/remove-wf`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wf_num: wf })
    })
    await loadData()
    emit('updated')
  } catch (_) {}
}
</script>

<style scoped>
.cat-manage-tabs {
  display: flex; gap: 2px; margin-bottom: var(--space-lg);
  border-bottom: 1px solid var(--border-light);
}
.cat-tab {
  padding: 8px 18px; font-size: 13px; font-weight: 500;
  color: var(--text-muted); cursor: pointer; white-space: nowrap;
  border: none; border-bottom: 2px solid transparent;
  background: none; font-family: var(--font-display);
  transition: all var(--duration-fast);
}
.cat-tab:hover { color: var(--text-secondary); }
.cat-tab.active { color: var(--text-primary); font-weight: 600; border-bottom-color: var(--accent-steel); }
.cat-wf-list { display: flex; flex-wrap: wrap; gap: var(--space-sm); min-height: 50px; padding: var(--space-sm) 0; }
.no-wfs { color: var(--text-muted); font-size: 13px; width: 100%; text-align: center; padding: 12px 0; }
.wf-chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-tag);
  border: 1px solid var(--border-light);
  padding: 4px 10px; border-radius: var(--radius-full);
  font-size: 13px; color: var(--text-primary); font-family: var(--font-mono);
}
.chip-remove {
  background: none; border: none; color: var(--text-muted);
  cursor: pointer; font-size: 16px; padding: 0 2px; line-height: 1;
  transition: color var(--duration-fast);
}
.chip-remove:hover { color: var(--color-danger); }
.cat-add { display: flex; gap: var(--space-sm); margin-top: var(--space-lg); }
.cat-add input {
  flex: 1; padding: 8px 12px;
  background: var(--bg-input); border: 1px solid var(--border-input);
  border-radius: var(--radius-sm); color: var(--text-primary);
  font-size: 13px; font-family: var(--font-display); outline: none;
  transition: border-color var(--duration-fast);
}
.cat-add input:focus { border-color: var(--border-focus); }
.cat-add button {
  padding: 8px 16px;
  background: var(--accent-steel); color: #fff;
  border: none; border-radius: var(--radius-sm); cursor: pointer;
  font-size: 13px; font-family: var(--font-display);
  transition: opacity var(--duration-fast);
}
.cat-add button:hover { opacity: 0.9; }
</style>
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/FAModal.vue frontend/src/components/CatManageModal.vue
git commit -m "feat: add FAModal and CatManageModal components"
```

---

### Task 14: Pinia Store 扩展

**Files:**
- Modify: `frontend/src/stores/app.js`

- [ ] **Step 1: 更新 app.js 添加新 actions**

在现有 store 的 return 语句前添加：

```js
// ── Categories ──────────────────────────────────────────────────────
const categories = ref([])

async function fetchCategories() {
  try {
    const r = await fetch('/api/categories')
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const data = await r.json()
    categories.value = data.categories || []
    return data
  } catch (e) {
    error.value = e.message
    throw e
  }
}

// ── Category Detail ─────────────────────────────────────────────────
const categoryDetail = ref(null)

async function fetchCategoryDetail(name) {
  loading.value = true; error.value = null
  try {
    const r = await fetch(`/api/completion/category/${encodeURIComponent(name)}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    categoryDetail.value = await r.json()
    return categoryDetail.value
  } catch (e) {
    error.value = e.message
    throw e
  } finally {
    loading.value = false
  }
}

// ── Predictions ─────────────────────────────────────────────────────
const predictions = ref([])

async function fetchPredictions(wf, cfg) {
  loading.value = true; error.value = null
  try {
    const params = new URLSearchParams()
    if (wf) params.set('wf', wf)
    if (cfg) params.set('config', cfg)
    const r = await fetch('/api/predictions?' + params)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const data = await r.json()
    predictions.value = data.predictions || []
    return predictions.value
  } catch (e) {
    error.value = e.message
    throw e
  } finally {
    loading.value = false
  }
}

async function updatePrediction(wfNum, config, testIdx, predictedDate) {
  const r = await fetch('/api/predictions/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ wf_num: wfNum, config, test_idx: testIdx, predicted_date: predictedDate })
  })
  if (!r.ok) {
    const j = await r.json(); throw new Error(j.error || 'Failed to update')
  }
  return r.json()
}

// ── Export ──────────────────────────────────────────────────────────
const exportData = ref(null)

async function fetchExportData(filters = {}) {
  loading.value = true; error.value = null
  try {
    const params = new URLSearchParams()
    if (filters.wf) params.set('wf', filters.wf)
    if (filters.config) params.set('config', filters.config)
    if (filters.sn) params.set('sn', filters.sn)
    const r = await fetch('/api/export?' + params)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    exportData.value = await r.json()
    return exportData.value
  } catch (e) {
    error.value = e.message
    throw e
  } finally {
    loading.value = false
  }
}
```

并在 return 对象中添加：

```js
categories, categoryDetail, predictions, exportData,
fetchCategories, fetchCategoryDetail, fetchPredictions, updatePrediction, fetchExportData,
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/stores/app.js
git commit -m "feat: extend Pinia store with categories, predictions, and export actions"
```

---

### Task 15: Dashboard.vue 主页面

**Files:**
- Create: `frontend/src/views/Dashboard.vue`

- [ ] **Step 1: 创建 Dashboard.vue**

```vue
<template>
  <div class="main">
    <!-- Section 1: Completion Overview -->
    <section class="section">
      <div class="section-header">
        <h2>Completion Overview</h2>
        <div class="divider"></div>
        <span class="subtitle">{{ store.reportDate || '' }}</span>
      </div>
      <OverviewCards :data="store.overviewData" :loading="store.loading"
                     :error="store.error" :retry="loadAll" />
    </section>

    <!-- Section 2: Category Completion -->
    <section class="section">
      <div class="section-header">
        <h2>Category Completion</h2>
        <div class="divider"></div>
        <span class="subtitle">By test category</span>
        <button class="edit-btn" @click="showCatModal = true">Edit</button>
      </div>
      <CategoryCards :data="store.overviewData" :loading="store.loading"
                     :error="store.error" :retry="loadAll" />
    </section>

    <!-- Section 3: Trend Analysis -->
    <section class="section">
      <div class="section-header">
        <h2>Trend Analysis</h2>
        <div class="divider"></div>
      </div>
      <div class="charts-row">
        <TrendChart :trend="store.overviewData?.trend || []" :loading="store.loading" />
        <TopFailChart :items="store.overviewData?.failures?.top_failures || []"
                      :wf-names="store.overviewData?.wf_names || {}" :loading="store.loading" />
      </div>
    </section>

    <!-- Section 4: Daily CP Updates -->
    <section class="section">
      <div class="section-header">
        <h2>Daily CP Updates</h2>
        <div class="divider"></div>
        <span class="subtitle">{{ store.reportDate || '' }}</span>
      </div>
      <DailyUpdates
        :wf-updates="store.overviewData?.daily_updates?.wf_updates || []"
        :wf-names="store.overviewData?.wf_names || {}"
        :loading="store.loading" :error="store.error" :retry="loadAll" />
    </section>

    <!-- Section 5: Failure Rate Analysis -->
    <section class="section">
      <div class="section-header">
        <h2>Failure Rate Analysis</h2>
        <div class="divider"></div>
      </div>
      <FailureAnalysis :data="store.overviewData"
                       :wf-names="store.overviewData?.wf_names || {}"
                       :loading="store.loading" :error="store.error" :retry="loadAll"
                       @select="onFailSelect" />
    </section>

    <!-- Section 6: Overall Test Summary -->
    <section class="section">
      <div class="section-header">
        <h2>Overall Test Summary</h2>
        <div class="divider"></div>
        <span class="subtitle">{{ summaryStats }}</span>
      </div>
      <TestSummary :summary="summaryList" :loading="store.loading"
                   :error="store.error" :retry="loadAll"
                   @cell-click="onSummaryCellClick" />
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-stats">
        <span>Report Date: <strong>{{ store.reportDate || '—' }}</strong></span>
        <span>Configs: <strong>{{ configCount }}</strong></span>
        <span>WFs: <strong>{{ wfCount }}</strong></span>
        <span>Failures: <strong>{{ totalFails }}</strong></span>
      </div>
      <span class="footer-copy">M60 EVT REL Dashboard</span>
    </footer>

    <!-- Modals -->
    <FAModal :show="showFAModal" :wf="faWf" :title="faTitle"
             :preset-sns="faSns" @close="showFAModal = false" />
    <CatManageModal :show="showCatModal" @close="showCatModal = false"
                    @updated="loadAll" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import OverviewCards from '@/components/OverviewCards.vue'
import CategoryCards from '@/components/CategoryCards.vue'
import TrendChart from '@/components/TrendChart.vue'
import TopFailChart from '@/components/TopFailChart.vue'
import DailyUpdates from '@/components/DailyUpdates.vue'
import FailureAnalysis from '@/components/FailureAnalysis.vue'
import TestSummary from '@/components/TestSummary.vue'
import FAModal from '@/components/FAModal.vue'
import CatManageModal from '@/components/CatManageModal.vue'

const store = useAppStore()

const showFAModal = ref(false)
const faWf = ref('')
const faTitle = ref('FA Records')
const faSns = ref([])
const showCatModal = ref(false)

const summaryList = computed(() => store.summaryData?.summary || [])

const summaryStats = computed(() => {
  const n = summaryList.value.length
  return n ? `${n} WF(s)` : ''
})

const configCount = computed(() => {
  return Object.keys(store.overviewData?.completion?.by_config || {}).length || '—'
})
const wfCount = computed(() => {
  return Object.keys(store.overviewData?.failures?.by_wf || {}).length || '—'
})
const totalFails = computed(() => {
  const trend = store.overviewData?.trend || []
  if (!trend.length) return '—'
  const last = trend[trend.length - 1]
  return (last.spec || 0) + (last.strife || 0)
})

function onFailSelect(row) {
  faWf.value = row.wf || ''
  faTitle.value = `FA Records — ${row.dim}`
  faSns.value = row.sns || []
  showFAModal.value = true
}

function onSummaryCellClick({ wf, cfg, test, sns }) {
  faWf.value = wf || ''
  faTitle.value = `FA Records — WF${wf} ${cfg} ${test}`
  faSns.value = sns
  showFAModal.value = true
}

async function loadAll() {
  await Promise.all([store.fetchOverview(), store.fetchSummary()])
}

onMounted(loadAll)
</script>

<style scoped>
.edit-btn {
  background: var(--bg-input); border: 1px solid var(--border-light);
  color: var(--text-secondary); padding: 5px 12px;
  border-radius: var(--radius-sm); font-size: 13px; cursor: pointer;
  font-family: var(--font-display); transition: all var(--duration-fast);
}
.edit-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-lg);
}
.footer {
  margin-top: var(--space-3xl);
  padding: 20px 0 10px;
  border-top: 1px solid var(--border-light);
  display: flex; justify-content: space-between;
  align-items: center; flex-wrap: wrap; gap: var(--space-md);
  font-size: 12px; color: var(--text-muted);
}
.footer-stats { display: flex; gap: var(--space-xl); flex-wrap: wrap; }
.footer-stats strong { color: var(--text-secondary); font-weight: 600; }
.footer-copy { font-size: 12px; }
@media (max-width: 1200px) {
  .charts-row { grid-template-columns: 1fr; }
}
</style>
```

- [ ] **Step 2: 验证 dev server 启动**

```bash
cd l:/Web/report/frontend && npm run dev
```
确认 Vite 启动在 `http://localhost:5173`。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/Dashboard.vue
git commit -m "feat: add Dashboard view composing all component sections"
```

---

### Task 16: 其余页面 — CategoryDetail, SnLookup, PredictionsView, ExportView

**Files:**
- Create: `frontend/src/views/CategoryDetail.vue`
- Create: `frontend/src/views/SnLookup.vue`
- Create: `frontend/src/views/PredictionsView.vue`
- Create: `frontend/src/views/ExportView.vue`

- [ ] **Step 1: 创建 CategoryDetail.vue**

```vue
<template>
  <div class="main">
    <div class="breadcrumb">
      <router-link to="/">Dashboard</router-link> / <strong>{{ name }}</strong>
    </div>
    <h1 class="page-title">{{ name }} Category</h1>
    <p class="subtitle">Per-WF completion detail for {{ name }} tests</p>
    <router-link to="/" class="back-link">&larr; Back to Dashboard</router-link>

    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" :retry="load" />
    <template v-else-if="data">
      <!-- Summary Cards -->
      <div class="sum-grid">
        <div class="sum-card" :style="{ '--cat-color': catColor }">
          <div class="sum-bg" :style="{ width: overallPct + '%', background: catColor + '1a' }"></div>
          <div class="sum-content">
            <div class="sum-label">Overall Completion</div>
            <div class="sum-val" :style="{ color: catColor }">{{ overallPct }}%</div>
            <div class="sum-detail">{{ totalCompleted }} / {{ totalCps }} CPs</div>
          </div>
        </div>
        <div v-for="cfg in cfgStats" :key="cfg.name" class="sum-card">
          <div class="sum-bg" :style="{ width: cfg.pct + '%', background: catColor + '1a' }"></div>
          <div class="sum-content">
            <div class="sum-label">{{ cfg.name }}</div>
            <div class="sum-val-sm">{{ cfg.pct }}%</div>
            <div class="sum-detail">{{ cfg.completed }} / {{ cfg.total }} CPs</div>
          </div>
        </div>
      </div>

      <!-- WF List -->
      <div class="card">
        <h2 class="card-title">WF Completion Detail</h2>
        <div v-for="wf in wfGroups" :key="wf.wf" class="wf-accordion">
          <div class="wf-header" @click="wf.expanded = !wf.expanded">
            <span class="wf-chevron" :class="{ open: wf.expanded }">▶</span>
            <span class="wf-badge" :style="{ background: catColor }">{{ wf.wf }}</span>
            <span class="wf-name">{{ wf.wfName }}</span>
            <span class="wf-pct" :style="{ color: catColor }">{{ wf.pct }}%</span>
          </div>
          <div class="wf-body" v-show="wf.expanded">
            <div v-for="cfg in wf.configs" :key="cfg.config" class="cfg-row">
              <span class="cfg-name">{{ cfg.config }}</span>
              <div class="cfg-bar-track">
                <div class="cfg-bar-fill" :style="{ width: cfg.pct + '%', background: catColor }"></div>
              </div>
              <span class="cfg-pct">{{ cfg.pct }}%</span>
              <span class="cfg-cp">{{ cfg.completed_cps }}/{{ cfg.total_cps }} CPs</span>
              <span class="cfg-sn">{{ cfg.sn_count || '—' }} SN</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { useApi } from '@/composables/useApi'

const route = useRoute()
const name = computed(() => route.params.name)

const catColors = { Drop: '#ef4444', Ingress: '#4f6f8f', Environmental: '#22c55e', Mechanical: '#d97706' }
const catColor = computed(() => catColors[name.value] || '#4f6f8f')
const cfgOrder = ['R1FNF', 'R2CNM', 'R3', 'R4']

const { loading, error, fetchData } = useApi()
const data = ref(null)

const totalCps = computed(() => (data.value?.wfs || []).reduce((s, w) => s + (w.total_cps || 0), 0))
const totalCompleted = computed(() => (data.value?.wfs || []).reduce((s, w) => s + (w.completed_cps || 0), 0))
const overallPct = computed(() => totalCps.value ? (totalCompleted.value / totalCps.value * 100).toFixed(1) : '0.0')

const cfgStats = computed(() => {
  const map = {}
  ;(data.value?.wfs || []).forEach(w => {
    if (!map[w.config]) map[w.config] = { total: 0, completed: 0 }
    map[w.config].total += w.total_cps || 0
    map[w.config].completed += w.completed_cps || 0
  })
  return cfgOrder.filter(c => map[c]).map(c => ({
    name: c, completed: map[c].completed, total: map[c].total,
    pct: map[c].total ? (map[c].completed / map[c].total * 100).toFixed(1) : '0.0'
  }))
})

const wfGroups = reactive([])

function buildWfGroups() {
  const wfs = data.value?.wfs || []
  const wfNames = data.value?.wf_names || {}
  const map = {}
  wfs.forEach(w => {
    if (!map[w.wf]) map[w.wf] = { configs: [], totalCps: 0, completedCps: 0, wfName: '' }
    map[w.wf].configs.push(w)
    map[w.wf].totalCps += w.total_cps || 0
    map[w.wf].completedCps += w.completed_cps || 0
    map[w.wf].wfName = w.wf_name || wfNames[w.wf] || ''
  })
  wfGroups.length = 0
  Object.keys(map).sort((a, b) => parseFloat(a) - parseFloat(b)).forEach(wf => {
    const d = map[wf]
    wfGroups.push({
      wf, wfName: d.wfName, expanded: false,
      pct: d.totalCps ? (d.completedCps / d.totalCps * 100).toFixed(1) : '0.0',
      configs: d.configs.map(c => ({
        ...c,
        pct: c.total_cps ? (c.completed_cps / c.total_cps * 100).toFixed(1) : '0.0'
      }))
    })
  })
}

watch(data, buildWfGroups)

async function load() {
  data.value = await fetchData(`/api/completion/category/${encodeURIComponent(name.value)}`)
}

onMounted(load)
watch(name, load)
</script>

<style scoped>
.breadcrumb { font-size: 13px; color: var(--text-muted); margin-bottom: var(--space-md); }
.breadcrumb a { color: var(--color-info); text-decoration: none; }
.page-title { font-size: 22px; font-weight: 700; margin-bottom: var(--space-xs); }
.subtitle { font-size: 14px; color: var(--text-muted); margin-bottom: var(--space-xl); }
.back-link {
  display: inline-block; padding: 8px 16px;
  background: var(--color-info); color: #fff; border-radius: var(--radius-sm);
  text-decoration: none; font-size: 13px; margin-bottom: var(--space-xl);
  transition: opacity var(--duration-fast);
}
.back-link:hover { opacity: 0.9; }
.sum-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-md); margin-bottom: var(--space-xl);
}
.sum-card {
  position: relative; overflow: hidden;
  background: var(--bg-card); border: 1px solid var(--border-card);
  border-radius: var(--radius-md); padding: 16px 20px;
}
.sum-bg {
  position: absolute; left: 0; top: 0; bottom: 0;
  transition: width 0.8s var(--ease-out);
  border-radius: var(--radius-md) 0 0 var(--radius-md);
}
.sum-content { position: relative; z-index: 1; }
.sum-label { font-size: 11px; color: var(--text-muted); margin-bottom: 6px; }
.sum-val { font-size: 28px; font-weight: 700; }
.sum-val-sm { font-size: 22px; font-weight: 700; color: var(--text-primary); }
.sum-detail { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.card-title { font-size: 16px; font-weight: 600; margin-bottom: var(--space-lg); color: var(--text-primary); }
.wf-accordion { border-bottom: 1px solid var(--border-light); }
.wf-header {
  display: flex; align-items: center; gap: var(--space-md);
  padding: 12px 0; cursor: pointer; transition: background var(--duration-fast);
}
.wf-header:hover { background: var(--bg-card-hover); }
.wf-chevron {
  font-size: 12px; color: var(--text-muted);
  transition: transform var(--duration-normal) var(--ease-in-out);
  width: 16px;
}
.wf-chevron.open { transform: rotate(90deg); }
.wf-badge {
  color: #fff; font-size: 12px; font-weight: 600;
  padding: 3px 10px; border-radius: var(--radius-sm); font-family: var(--font-mono);
}
.wf-name { flex: 1; font-size: 14px; color: var(--text-secondary); font-weight: 500; }
.wf-pct { font-size: 18px; font-weight: 700; }
.wf-body { padding: 0 0 var(--space-lg) 28px; }
.cfg-row {
  display: flex; align-items: center; gap: var(--space-md);
  padding: 8px 12px; font-size: 13px;
  border-bottom: 1px solid var(--border-light);
}
.cfg-name { color: var(--text-muted); min-width: 60px; font-family: var(--font-mono); }
.cfg-bar-track { flex: 1; height: 6px; background: var(--bg-progress-track); border-radius: 3px; overflow: hidden; }
.cfg-bar-fill { height: 100%; border-radius: 3px; transition: width 0.8s var(--ease-out); }
.cfg-pct { font-weight: 600; color: var(--text-primary); min-width: 50px; text-align: right; }
.cfg-cp { color: var(--text-muted); min-width: 80px; text-align: right; }
.cfg-sn { color: var(--text-muted); min-width: 40px; text-align: right; }
</style>
```

- [ ] **Step 2: 创建 SnLookup.vue**

```vue
<template>
  <div class="main">
    <h1 class="page-title">SN Lookup</h1>
    <p class="subtitle">Query test records and progress for any Serial Number</p>

    <div class="card search-card">
      <div class="search-box">
        <input type="text" v-model="query" placeholder="Enter SN (e.g. DQLW9J6DVH)..."
               @keydown.enter="search" class="search-input" ref="searchInput">
        <button @click="search" class="search-btn">Search</button>
      </div>
      <div v-if="suggestions.length" class="suggestions">
        <span v-for="s in suggestions" :key="s" class="suggestion-chip"
              @click="query = s; search()">{{ s }}</span>
      </div>

      <LoadingState v-if="loading" />
      <ErrorState v-else-if="error" :message="error" :retry="search" />
      <template v-else-if="result">
        <h2 class="result-sn">SN: <strong>{{ result.sn }}</strong></h2>
        <div v-if="result.failures?.length" class="fail-alert">
          <strong>Failures Found:</strong> {{ result.failures.length }} records
        </div>
        <div v-if="!result.by_wf?.length" class="empty">No records found</div>
        <div v-else class="wf-list">
          <div v-for="(wf, i) in result.by_wf" :key="i" class="wf-acc">
            <div class="wf-acc-header" @click="wf._open = !wf._open">
              <span class="wf-acc-chevron" :class="{ open: wf._open }">▶</span>
              <span class="wf-acc-badge">{{ wf.wf }}</span>
              <span>{{ wf.latest?.config }}</span>
              <span class="wf-acc-date">{{ wf.latest?.date }}</span>
              <span class="wf-acc-progress">CP {{ (wf.latest?.cp_idx || 0) + 1 }}/{{ wf.latest?.total_cps }}</span>
            </div>
            <div v-show="wf._open" class="wf-acc-body">
              <table>
                <thead><tr><th>Date</th><th>Current CP</th><th>Progress</th></tr></thead>
                <tbody>
                  <tr v-for="h in wf.history" :key="h.date">
                    <td>{{ h.date }}</td><td>{{ h.current_cp }}</td>
                    <td>CP {{ (h.cp_idx || 0) + 1 }}/{{ h.total_cps }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { useApi } from '@/composables/useApi'

const query = ref('')
const suggestions = ref([])
const result = ref(null)
const searchInput = ref(null)
const { loading, error, fetchData } = useApi()

let debounceTimer = null
watch(query, (v) => {
  clearTimeout(debounceTimer)
  if (v.length < 3) { suggestions.value = []; return }
  debounceTimer = setTimeout(async () => {
    try {
      const r = await fetch('/api/sn/search?q=' + encodeURIComponent(v))
      suggestions.value = await r.json()
    } catch (_) { suggestions.value = [] }
  }, 300)
})

async function search() {
  const sn = query.value.trim()
  if (!sn) return
  suggestions.value = []
  result.value = null
  try {
    const data = await fetchData('/api/sn/' + encodeURIComponent(sn))
    data.by_wf?.forEach(w => w._open = false)
    result.value = data
  } catch (_) { result.value = null }
}

onMounted(() => searchInput.value?.focus())
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: var(--space-xs); }
.subtitle { font-size: 14px; color: var(--text-muted); margin-bottom: var(--space-xl); }
.search-card { padding: var(--space-xl); }
.search-box { display: flex; gap: var(--space-md); margin-bottom: var(--space-lg); }
.search-input {
  flex: 1; padding: 12px 16px;
  border: 2px solid var(--border-input); border-radius: var(--radius-md);
  background: var(--bg-input); color: var(--text-primary);
  font-size: 15px; font-family: var(--font-mono); outline: none;
  transition: border-color var(--duration-fast);
}
.search-input:focus { border-color: var(--border-focus); }
.search-btn {
  padding: 12px 24px; background: var(--accent-steel); color: #fff;
  border: none; border-radius: var(--radius-md); font-size: 14px;
  cursor: pointer; font-family: var(--font-display); transition: opacity var(--duration-fast);
}
.search-btn:hover { opacity: 0.9; }
.suggestions { display: flex; flex-wrap: wrap; gap: var(--space-sm); margin-bottom: var(--space-lg); }
.suggestion-chip {
  padding: 6px 12px; background: var(--bg-tag); border-radius: var(--radius-full);
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  font-family: var(--font-mono); transition: all var(--duration-fast);
}
.suggestion-chip:hover { background: var(--accent-steel); color: #fff; }
.result-sn { margin-bottom: var(--space-lg); font-size: 18px; }
.fail-alert {
  padding: 12px; background: var(--color-danger-bg);
  border-radius: var(--radius-md); border-left: 3px solid var(--color-danger);
  margin-bottom: var(--space-lg); font-size: 13px; color: var(--color-danger);
}
.wf-acc { border-bottom: 1px solid var(--border-light); }
.wf-acc-header {
  display: flex; align-items: center; gap: var(--space-md);
  padding: 12px 0; cursor: pointer; font-size: 13px;
  transition: background var(--duration-fast);
}
.wf-acc-header:hover { background: var(--bg-card-hover); }
.wf-acc-chevron { font-size: 12px; color: var(--text-muted); width: 16px; transition: transform var(--duration-normal); }
.wf-acc-chevron.open { transform: rotate(90deg); }
.wf-acc-badge {
  background: var(--text-primary); color: #fff; font-size: 11px;
  font-weight: 600; padding: 2px 8px; border-radius: var(--radius-sm); font-family: var(--font-mono);
}
.wf-acc-date { margin-left: auto; color: var(--text-muted); font-size: 12px; }
.wf-acc-progress { color: var(--text-secondary); font-weight: 600; min-width: 100px; text-align: right; }
.wf-acc-body { padding: 0 0 var(--space-lg) 28px; }
.wf-acc-body table { width: 100%; border-collapse: collapse; font-size: 12px; }
.wf-acc-body th { padding: 8px 12px; text-align: left; color: var(--text-muted); font-size: 10px; text-transform: uppercase; border-bottom: 1px solid var(--border-light); }
.wf-acc-body td { padding: 8px 12px; border-bottom: 1px solid var(--border-light); }
</style>
```

- [ ] **Step 3: 创建 PredictionsView.vue**

```vue
<template>
  <div class="main">
    <h1 class="page-title">Completion Predictions</h1>

    <LoadingState v-if="loading && !preds.length" />
    <ErrorState v-else-if="error" :message="error" :retry="load" />
    <template v-else>
      <div class="stats-row">
        <div class="stat-card"><div class="stat-label">Total</div><div class="stat-val">{{ stats.total }}</div></div>
        <div class="stat-card"><div class="stat-label">Manual</div><div class="stat-val">{{ stats.manual }}</div></div>
        <div class="stat-card"><div class="stat-label">Overdue</div><div class="stat-val" style="color:var(--color-danger)">{{ stats.overdue }}</div></div>
        <div class="stat-card"><div class="stat-label">Completed</div><div class="stat-val" style="color:var(--color-success)">{{ stats.done }}</div></div>
      </div>

      <div class="card">
        <div class="filter-row">
          <input type="text" v-model="filterWf" placeholder="Filter WF..." class="filter-input">
          <select v-model="filterCfg" class="filter-select">
            <option value="">All Configs</option>
            <option>R1FNF</option><option>R2CNM</option><option>R3</option><option>R4</option>
          </select>
          <button @click="load" class="refresh-btn">Refresh</button>
        </div>

        <table class="data-table">
          <thead>
            <tr>
              <th @click="sortBy('wf_num')" style="cursor:pointer">WF</th>
              <th @click="sortBy('config')" style="cursor:pointer">Config</th>
              <th @click="sortBy('test_idx')" style="cursor:pointer">Test</th>
              <th>Progress</th>
              <th @click="sortBy('daily_rate')" style="cursor:pointer">Daily Rate</th>
              <th @click="sortBy('remaining_days')" style="cursor:pointer">Remaining</th>
              <th @click="sortBy('predicted_date')" style="cursor:pointer">Predicted Date</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in filteredPreds" :key="`${p.wf_num}-${p.config}-${p.test_idx}`">
              <td>WF{{ p.wf_num }}</td>
              <td>{{ p.config }}</td>
              <td>Test{{ (p.test_idx || 0) + 1 }}</td>
              <td>
                <div class="mini-bar"><div class="mini-fill" :style="{ width: pct(p) + '%', background: p.remaining_days <= 0 ? 'var(--color-success)' : 'var(--accent-steel)' }"></div></div>
                {{ pct(p) }}% (CP {{ p.current_max_cp }}/{{ p.total_cps }})
              </td>
              <td>{{ (p.daily_rate || 0).toFixed(1) }} CP/day</td>
              <td>
                <span v-if="p.remaining_days <= 0" class="badge badge-done">Done</span>
                <span v-else>{{ (p.remaining_days || 0).toFixed(1) }} d</span>
              </td>
              <td>
                <span class="editable" @click="openEdit(p)"
                      :style="{ color: dateColor(p) }">{{ p.predicted_date || '—' }}</span>
              </td>
              <td><StatusBadge :type="p.is_manual ? 'manual' : 'auto'" /></td>
            </tr>
          </tbody>
        </table>
        <p class="table-info">Showing {{ filteredPreds.length }} of {{ preds.length }} predictions</p>
      </div>
    </template>

    <!-- Edit Modal -->
    <div class="modal-overlay" :class="{ open: showEdit }" @click.self="showEdit = false">
      <div class="modal" style="max-width:400px">
        <div class="modal-header">
          <h3>Edit Prediction</h3>
          <button class="close-btn" @click="showEdit = false">&times;</button>
        </div>
        <div class="modal-body">
          <label style="font-size:13px;color:var(--text-secondary);display:block;margin-bottom:8px">Predicted Date</label>
          <input type="date" v-model="editDate" class="date-input">
          <div style="margin-top:16px;display:flex;gap:8px">
            <button @click="saveEdit" class="save-btn">Save</button>
            <button @click="showEdit = false" class="cancel-btn">Cancel</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useApi } from '@/composables/useApi'

const { loading, error, fetchData } = useApi()
const preds = ref([])
const filterWf = ref('')
const filterCfg = ref('')
const showEdit = ref(false)
const editWf = ref(''); const editCfg = ref(''); const editTi = ref(0)
const editDate = ref('')

const today = new Date().toISOString().slice(0, 10)

const stats = computed(() => ({
  total: preds.value.length,
  manual: preds.value.filter(p => p.is_manual).length,
  overdue: preds.value.filter(p => p.predicted_date && p.predicted_date < today && p.remaining_days > 0).length,
  done: preds.value.filter(p => p.remaining_days <= 0).length,
}))

const filteredPreds = computed(() => {
  let list = [...preds.value]
  if (filterWf.value) list = list.filter(p => String(p.wf_num).toLowerCase().includes(filterWf.value.toLowerCase()))
  if (filterCfg.value) list = list.filter(p => p.config === filterCfg.value)
  list.sort((a, b) => String(a.wf_num).localeCompare(String(b.wf_num), undefined, { numeric: true }))
  return list
})

function pct(p) { return p.total_cps ? (p.current_max_cp / p.total_cps * 100).toFixed(1) : '0.0' }
function dateColor(p) {
  if (p.remaining_days <= 0) return 'var(--color-success)'
  if (p.predicted_date && p.predicted_date < today) return 'var(--color-danger)'
  return 'var(--color-info)'
}

function openEdit(p) {
  editWf.value = p.wf_num; editCfg.value = p.config
  editTi.value = p.test_idx; editDate.value = p.predicted_date || ''
  showEdit.value = true
}

async function saveEdit() {
  try {
    await fetchData('/api/predictions/update', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wf_num: editWf.value, config: editCfg.value, test_idx: editTi.value, predicted_date: editDate.value })
    })
    showEdit.value = false
    await load()
  } catch (_) {}
}

async function load() {
  const data = await fetchData('/api/predictions')
  preds.value = data.predictions || []
}

onMounted(load)
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: var(--space-xl); }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-lg); margin-bottom: var(--space-xl); }
.stat-card { background: var(--bg-card); border: 1px solid var(--border-card); border-radius: var(--radius-md); padding: 16px; text-align: center; }
.stat-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.stat-val { font-size: 24px; font-weight: 700; color: var(--color-info); }
.filter-row { display: flex; gap: var(--space-md); padding: 20px; border-bottom: 1px solid var(--border-light); flex-wrap: wrap; }
.filter-input, .filter-select {
  padding: 8px 12px; border: 2px solid var(--border-input); border-radius: var(--radius-sm);
  background: var(--bg-input); color: var(--text-primary); font-size: 13px;
  font-family: var(--font-display); outline: none;
}
.filter-input:focus, .filter-select:focus { border-color: var(--border-focus); }
.refresh-btn {
  padding: 8px 16px; background: var(--accent-steel); color: #fff;
  border: none; border-radius: var(--radius-sm); cursor: pointer; font-size: 13px;
  font-family: var(--font-display);
}
.mini-bar { width: 100%; height: 6px; background: var(--bg-progress-track); border-radius: 3px; overflow: hidden; margin-bottom: 2px; }
.mini-fill { height: 100%; border-radius: 3px; transition: width 0.8s var(--ease-out); }
.editable { cursor: pointer; text-decoration: underline; font-weight: 500; }
.table-info { font-size: 12px; color: var(--text-muted); margin-top: var(--space-sm); padding: 0 20px 12px; }
.date-input { width: 100%; padding: 8px 12px; border: 2px solid var(--border-input); border-radius: var(--radius-sm); background: var(--bg-input); color: var(--text-primary); font-size: 14px; font-family: var(--font-display); outline: none; }
.date-input:focus { border-color: var(--border-focus); }
.save-btn { padding: 10px 20px; background: var(--color-success); color: #fff; border: none; border-radius: var(--radius-sm); cursor: pointer; font-size: 14px; font-family: var(--font-display); }
.cancel-btn { padding: 10px 20px; background: var(--bg-tag); color: var(--text-muted); border: none; border-radius: var(--radius-sm); cursor: pointer; font-size: 14px; font-family: var(--font-display); }
</style>
```

- [ ] **Step 4: 创建 ExportView.vue**

```vue
<template>
  <div class="main">
    <h1 class="page-title">Batch Export</h1>
    <p class="subtitle">Export SN test records with CP progress details</p>

    <div class="card export-card">
      <div class="filter-grid">
        <div><label>WF Number</label><input type="text" v-model="filters.wf" placeholder="e.g. 10"></div>
        <div><label>Config</label><select v-model="filters.config">
          <option value="">All</option><option>R1FNF</option><option>R2CNM</option><option>R3</option><option>R4</option>
        </select></div>
        <div><label>SN (optional)</label><input type="text" v-model="filters.sn" placeholder="e.g. DQLW9..."></div>
        <div><label>Format</label><select v-model="filters.format">
          <option value="json">JSON</option><option value="csv">CSV</option>
        </select></div>
      </div>
      <div class="btn-group">
        <button class="btn-preview" @click="preview">Preview</button>
        <button class="btn-csv" @click="exportData('csv')">Download CSV</button>
        <button class="btn-json" @click="exportData('json')">Download JSON</button>
      </div>

      <LoadingState v-if="loading" />
      <ErrorState v-else-if="error" :message="error" :retry="preview" />
      <template v-else-if="previewData">
        <div class="result-count">Found <strong>{{ previewData.count }}</strong> records</div>
        <div v-if="previewData.records?.length" class="result-table-wrap">
          <table>
            <thead><tr><th>SN</th><th>Unit</th><th>WF</th><th>Config</th><th>Current CP</th><th>Progress</th><th>CP Results</th></tr></thead>
            <tbody>
              <tr v-for="r in previewRows" :key="r.sn + r.wf_num + r.config">
                <td>{{ r.sn }}</td><td>{{ r.unit_num || '—' }}</td>
                <td>WF{{ r.wf_num }}</td><td>{{ r.config }}</td>
                <td>{{ r.current_cp_name }}</td>
                <td>CP {{ (r.current_cp_idx || 0) + 1 }}/{{ r.total_cps }}</td>
                <td>
                  <span v-for="cp in (r.cp_results || []).slice(0,5)" :key="cp.cp_name"
                        class="badge" :class="'badge-' + (cp.status === 'pass' ? 'pass' : cp.status === 'spec_fail' ? 'spec' : cp.status === 'strife_fail' ? 'strife' : 'pending')">
                    {{ cp.cp_name }}={{ cp.status }}
                  </span>
                  <span v-if="(r.cp_results || []).length > 5">...</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="previewData.count > 50" class="truncated-hint">Showing 50 of {{ previewData.count }} records. Download for full dataset.</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import LoadingState from '@/components/LoadingState.vue'
import ErrorState from '@/components/ErrorState.vue'
import { useApi } from '@/composables/useApi'

const { loading, error, fetchData } = useApi()
const filters = reactive({ wf: '', config: '', sn: '', format: 'json' })
const previewData = ref(null)

const previewRows = computed(() => (previewData.value?.records || []).slice(0, 50))

async function preview() {
  previewData.value = null
  const params = new URLSearchParams()
  if (filters.wf) params.set('wf', filters.wf)
  if (filters.config) params.set('config', filters.config)
  if (filters.sn) params.set('sn', filters.sn)
  previewData.value = await fetchData('/api/export?' + params)
}

async function exportData(format) {
  const params = new URLSearchParams()
  if (filters.wf) params.set('wf', filters.wf)
  if (filters.config) params.set('config', filters.config)
  if (filters.sn) params.set('sn', filters.sn)
  params.set('format', format)

  if (format === 'csv') {
    window.location.href = '/api/export?' + params
    return
  }
  const data = await fetchData('/api/export?' + params)
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `export_${new Date().toISOString().slice(0, 10)}.json`
  a.click(); URL.revokeObjectURL(url)
}
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.subtitle { font-size: 14px; color: var(--text-muted); margin-bottom: var(--space-xl); }
.export-card { padding: var(--space-xl); }
.filter-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-md); margin-bottom: var(--space-xl); }
.filter-grid label { font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 4px; }
.filter-grid input, .filter-grid select {
  width: 100%; padding: 10px 12px; border: 2px solid var(--border-input); border-radius: var(--radius-sm);
  background: var(--bg-input); color: var(--text-primary); font-size: 14px;
  font-family: var(--font-display); outline: none;
}
.filter-grid input:focus, .filter-grid select:focus { border-color: var(--border-focus); }
.btn-group { display: flex; gap: var(--space-md); margin-bottom: var(--space-xl); }
.btn-group button { padding: 10px 24px; border: none; border-radius: var(--radius-md); font-size: 14px; cursor: pointer; font-weight: 600; font-family: var(--font-display); transition: opacity var(--duration-fast); }
.btn-group button:hover { opacity: 0.9; }
.btn-preview { background: var(--color-info); color: #fff; }
.btn-csv { background: var(--color-success); color: #fff; }
.btn-json { background: var(--bg-tag); color: var(--text-secondary); }
.result-count { font-size: 13px; color: var(--text-muted); margin-bottom: var(--space-md); }
.result-table-wrap { overflow-x: auto; }
.result-table-wrap table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 800px; }
.result-table-wrap th { padding: 8px 10px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 10px; text-transform: uppercase; border-bottom: 1px solid var(--border-light); background: var(--bg-row-stripe); white-space: nowrap; }
.result-table-wrap td { padding: 8px 10px; border-bottom: 1px solid var(--border-light); white-space: nowrap; }
.result-table-wrap tr:hover td { background: var(--bg-row-hover); }
.truncated-hint { font-size: 12px; color: var(--text-muted); margin-top: var(--space-sm); }
</style>
```

- [ ] **Step 5: 验证所有页面可访问**

启动 dev server 后，手动测试以下路由：
- `http://localhost:5173/` — Dashboard
- `http://localhost:5173/category/Drop` — Category Detail
- `http://localhost:5173/sn` — SN Lookup
- `http://localhost:5173/predictions` — Predictions
- `http://localhost:5173/export` — Export

- [ ] **Step 6: 提交**

```bash
git add frontend/src/views/CategoryDetail.vue frontend/src/views/SnLookup.vue frontend/src/views/PredictionsView.vue frontend/src/views/ExportView.vue
git commit -m "feat: add CategoryDetail, SnLookup, PredictionsView, and ExportView pages"
```

---

### Task 17: 构建验证 & 收尾

- [ ] **Step 1: Vite 构建验证**

```bash
cd l:/Web/report/frontend && npm run build
```
预期：构建成功，输出到 `frontend/../static/` 目录。检查是否有 warning。

- [ ] **Step 2: Flask 静态文件集成验证**

确认 Flask 的 `/` 路由返回 Vue 构建后的 `index.html`。Flask 需要从 `static/` 文件夹 serve 构建产物。检查构建输出中的 `index.html` 的资源引用路径是否正确。

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "chore: finalize frontend build verification"
```

---

## 实施总结

| Phase | Tasks | 新建文件 | 修改文件 |
|-------|-------|----------|----------|
| Foundation | 1-2 | 0 | 3 |
| Utility Components | 3-4 | 5 | 0 |
| Core Components | 5-6 | 2 | 2 |
| Feature Components | 7-13 | 9 | 0 |
| Store | 14 | 0 | 1 |
| Pages | 15-16 | 5 | 0 |
| Verification | 17 | 0 | 0 |
| **Total** | **17** | **21** | **6** |
