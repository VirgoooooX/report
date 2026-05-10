# Dashboard 增强 — 执行计划

> 日期: 2025-05-10
> 状态: 待审批

## 目标

对 Dashboard 首页进行两项增强：
1. **替换 Top Failures 图表** → 简化版 Cross-Analysis Heatmap
2. **新增 SN Lookup 快捷入口** 于 Dashboard 底部
3. **移除 NavBar 中的 SN Lookup 导航项**

---

## 变更概览

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/DashboardHeatmap.vue` | **[NEW]** | 简化版 Heatmap 组件 |
| `frontend/src/components/SnQuickSearch.vue` | **[NEW]** | SN 快捷搜索组件 |
| `frontend/src/views/Dashboard.vue` | **[MODIFY]** | 替换 TopFailChart → DashboardHeatmap，新增 SnQuickSearch |
| `frontend/src/components/NavBar.vue` | **[MODIFY]** | 移除 SN Lookup 导航链接 |
| `frontend/src/i18n/messages.js` | **[MODIFY]** | 新增 dashboard.crossAnalysis / dashboard.snQuickSearch 等 i18n key |
| `frontend/src/stores/app.js` | **[MODIFY]** | 新增 `fetchFaCross()` action |

**不需要修改后端** — 所有 API 已存在。

---

## 详细执行步骤

### Step 1: 在 Store 中新增 `fetchFaCross()` action

**文件**: `frontend/src/stores/app.js`

在 store 中新增 cross-analysis 数据获取能力，供 Dashboard 使用。

```javascript
// 新增 state
const crossData = ref(null)

// 新增 action
async function fetchFaCross(dim1 = 'location', dim2 = 'config') {
  try {
    crossData.value = await requestJson(`/api/fa/cross?dim1=${dim1}&dim2=${dim2}`)
    return crossData.value
  } catch (e) {
    error.value = e.message
    throw e
  }
}
```

在 return 语句中导出: `crossData, fetchFaCross`

---

### Step 2: 新建 `DashboardHeatmap.vue` 组件

**文件**: `frontend/src/components/DashboardHeatmap.vue`

#### 设计要点

- **固定维度**: Dim1 = `location`, Dim2 = `config`（无维度选择器）
- **固定显示模式**: `spec` 模式
- **数据源**: 调用 `/api/fa/cross?dim1=location&dim2=config`
- **简化交互**: 
  - Hover 显示 tooltip（复用 FailureMatrixPage 的 tooltip 逻辑）
  - **点击单元格** → 跳转到 `/failure-analysis` 页面（不弹 modal）
- **标题栏**: 显示 "Cross-Analysis Heatmap"，右侧有一个 "View Full →" 链接指向 `/failure-analysis`

#### 数据格式（API 返回）

```json
{
  "dim1Values": ["BT-OTA", "Charging", "FACT", ...],
  "dim2Values": ["R1FNF", "R2CNM", "R3", "R4"],
  "matrix": [
    {
      "dim1Value": "BT-OTA",
      "dim2Value": "R1FNF",
      "totalCount": 5,
      "specSnCount": 5,
      "strifeSnCount": 0,
      "specRate": 1.64,
      "strifeRate": 0,
      "percentage": 10.2,
      "totalSamples": 304
    },
    ...
  ]
}
```

#### 复用逻辑

以下逻辑直接从现有文件导入，无需重写：
- `failureDisplay.js` → `heatmapCellDisplay()`, `getClampedTooltipPosition()`
- `failureTheme.js` → `getFailureTheme()`

#### Template 结构

```html
<template>
  <div class="dashboard-heatmap">
    <!-- Loading / Error / Empty states -->
    <div v-if="loading" class="heatmap-loading">加载中...</div>
    <div v-else-if="!crossData?.matrix?.length" class="heatmap-empty">暂无数据</div>
    
    <!-- Heatmap table -->
    <div v-else class="heatmap-scroll">
      <table class="hm-table">
        <thead>
          <tr>
            <th class="hm-corner">FAILED LOCATION</th>
            <th v-for="v2 in crossData.dim2Values" :key="v2" class="hm-col-th">{{ v2 }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v1 in crossData.dim1Values" :key="v1">
            <td class="hm-row-th">{{ v1 }}</td>
            <td
              v-for="v2 in crossData.dim2Values"
              :key="v1+'|'+v2"
              class="hm-cell"
              :class="{ 'has-data': getCell(v1, v2) }"
              :style="{ backgroundColor: cellBg(v1, v2) }"
              @mouseenter="onHover($event, v1, v2)"
              @mouseleave="hovered = null"
              @click="goToAnalysis"
            >
              {{ cellDisplay(v1, v2) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Hover tooltip (fixed position) -->
    <div v-if="hovered" class="hm-tooltip" :style="tooltipStyle">
      <div class="tt-row"><span>总失效数:</span><b>{{ hovered.totalCount }}</b></div>
      <div class="tt-row"><span>Spec 失效率:</span><b class="c-red">{{ hovered.specRate.toFixed(2) }}%</b></div>
      <div class="tt-row"><span>Strife 失效率:</span><b class="c-yellow">{{ hovered.strifeRate.toFixed(2) }}%</b></div>
    </div>
  </div>
</template>
```

#### CSS 要点

- 与现有 card 样式融合，不需要额外 card 包裹（因为 Dashboard.vue 已有 `.card` wrapper）
- 表格紧凑：`padding: 6px 8px`，字号 `12px`
- 使用 `max-height: 360px; overflow-y: auto` 限制高度
- 复用 `failureTheme.js` 中的颜色方案，确保 dark mode 兼容
- Sticky header (`thead th { position: sticky; top: 0 }`)
- Sticky 左侧 row header (`td:first-child { position: sticky; left: 0 }`)

---

### Step 3: 新建 `SnQuickSearch.vue` 组件

**文件**: `frontend/src/components/SnQuickSearch.vue`

#### 设计要点

- 一个搜索框 + 自动补全下拉
- 使用已有 API: `GET /api/sn/search?q=xxx` → 返回 `[{sn: "xxx"}, ...]`
- 输入 ≥ 2 字符时触发搜索（带 debounce 300ms）
- 下拉列表显示匹配的 SN
- 选中一个 SN → `router.push({ name: 'sn', query: { q: selectedSn } })`
- 也支持直接回车 → 跳转到 SN 页面

#### Template 结构

```html
<template>
  <div class="sn-quick-search card">
    <div class="sn-search-header">
      <span class="sn-search-icon">🔍</span>
      <span class="sn-search-title">{{ t('dashboard.snQuickSearch') }}</span>
    </div>
    <div class="sn-search-body">
      <div class="sn-input-wrap">
        <input
          v-model="query"
          class="sn-input"
          :placeholder="t('snLookup.placeholder')"
          @input="onInput"
          @keydown.enter="onEnter"
        />
      </div>
      <!-- Dropdown -->
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
```

#### Script 逻辑

```javascript
import { ref } from 'vue'
import { useRouter } from 'vue-router'
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
    } catch { suggestions.value = [] }
    finally { searching.value = false }
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
```

#### CSS 要点

- 搜索框使用现有 design token: `var(--bg-input)`, `var(--border-input)`, `var(--border-focus)`
- 下拉列表: 绝对定位，`max-height: 200px; overflow-y: auto`
- 下拉项 hover 高亮: `var(--bg-row-hover)`
- 整体宽度: 充满其网格列

---

### Step 4: 修改 `Dashboard.vue` 页面

**文件**: `frontend/src/views/Dashboard.vue`

#### 4.1 新增 import

```javascript
// 删除
import TopFailChart from '@/components/TopFailChart.vue'

// 新增
import DashboardHeatmap from '@/components/DashboardHeatmap.vue'
import SnQuickSearch from '@/components/SnQuickSearch.vue'
```

#### 4.2 新增数据加载

在 `loadAll()` 中新增 cross data 加载:

```javascript
async function loadAll() {
  await Promise.all([
    store.fetchOverview(),
    store.fetchFaCross('location', 'config')  // 新增
  ])
}
```

#### 4.3 新增 computed

```javascript
const crossData = computed(() => store.crossData)
```

#### 4.4 修改 Template

**替换 Charts Row**: 将右侧的 TopFailChart 替换为 DashboardHeatmap

```html
<!-- 3. Charts row: Trend + Cross-Analysis Heatmap -->
<section class="section">
  <div class="chart-row">
    <div class="chart-col card">
      <div class="chart-col-header">{{ t('dashboard.failureTrend') }}</div>
      <TrendChart :trend-data="trendData" />
    </div>
    <div class="chart-col card">
      <div class="chart-col-header">
        {{ t('dashboard.crossAnalysis') }}
        <router-link to="/failure-analysis" class="view-more-link">
          {{ t('common.details') }} →
        </router-link>
      </div>
      <DashboardHeatmap :cross-data="crossData" />
    </div>
  </div>
</section>
```

**新增 SN Quick Search section**（在 Charts Row 和 Footer 之间）:

```html
<!-- 4. SN Quick Search -->
<section class="section">
  <SnQuickSearch />
</section>
```

#### 4.5 新增 CSS

```css
.chart-col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  /* 保留原有样式 */
}

.view-more-link {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-steel);
  text-decoration: none;
  opacity: 0.7;
  transition: opacity var(--duration-fast);
}

.view-more-link:hover {
  opacity: 1;
}
```

---

### Step 5: 修改 `NavBar.vue` — 移除 SN Lookup

**文件**: `frontend/src/components/NavBar.vue`

#### 5.1 删除 Template 中的链接

```diff
 <div class="nav-links">
   <router-link to="/">{{ t('nav.dashboard') }}</router-link>
   <router-link to="/daily-update">{{ t('nav.dailyUpdate') }}</router-link>
   <router-link to="/test-summary">{{ t('nav.testSummary') }}</router-link>
   <router-link to="/failure-analysis">{{ t('nav.failureAnalysis') }}</router-link>
   <router-link to="/predictions">{{ t('nav.predictions') }}</router-link>
   <router-link to="/category/Drop">{{ t('nav.categories') }}</router-link>
-  <router-link to="/sn">{{ t('nav.snLookup') }}</router-link>
   <router-link to="/export">{{ t('nav.export') }}</router-link>
 </div>
```

#### 5.2 删除 navLinks 数组中的对应项

```diff
 const navLinks = [
   { to: '/', label: t('nav.dashboard') },
   { to: '/daily-update', label: t('nav.dailyUpdate') },
   { to: '/test-summary', label: t('nav.testSummary') },
   { to: '/failure-analysis', label: t('nav.failureAnalysis') },
   { to: '/predictions', label: t('nav.predictions') },
   { to: '/category/Drop', label: t('nav.categories') },
-  { to: '/sn', label: t('nav.snLookup') },
   { to: '/export', label: t('nav.export') },
 ]
```

> **注意**: `/sn` 路由本身在 `router/index.js` 中保留，只是导航栏不显示入口。用户仍然可以通过 Dashboard 的 SN Quick Search 跳转过去。

---

### Step 6: 更新 i18n messages

**文件**: `frontend/src/i18n/messages.js`

在 `dashboard` 分组中新增:

```javascript
// zh-CN
dashboard: {
  // ... 现有 key 保留 ...
  crossAnalysis: '交叉分析热力图',
  snQuickSearch: 'SN 快捷查询',
},

// en-US
dashboard: {
  // ... 现有 key 保留 ...
  crossAnalysis: 'Cross-Analysis Heatmap',
  snQuickSearch: 'SN Quick Search',
},
```

---

### Step 7: 更新 `SnLookup.vue` 页面支持 query 参数

**文件**: `frontend/src/views/SnLookup.vue`

在 `onMounted` 中检查 `route.query.q`，如果有值就自动触发搜索:

```javascript
import { useRoute } from 'vue-router'
const route = useRoute()

onMounted(() => {
  const q = route.query.q
  if (q) {
    // 填充搜索框并触发搜索
    searchQuery.value = q
    doSearch()
  }
})
```

> 需要确认 SnLookup.vue 中搜索逻辑的具体变量名，按实际代码适配。

---

## 布局对比

### 修改前

```
┌──────────────────────────────────────────────┐
│  Overview Cards (整体完成度 + 4 Config 环形)  │
├──────────────────────────────────────────────┤
│  Category Cards (Drop / Ingress / Env / Mech)│
├──────────────────────┬───────────────────────┤
│  Failure Trend 📈    │  Top 5 Failures 📊    │
├──────────────────────┴───────────────────────┤
│  Footer (Report Date / Configs / WFs / Fails)│
└──────────────────────────────────────────────┘
```

### 修改后

```
┌──────────────────────────────────────────────┐
│  Overview Cards (整体完成度 + 4 Config 环形)  │
├──────────────────────────────────────────────┤
│  Category Cards (Drop / Ingress / Env / Mech)│
├──────────────────────┬───────────────────────┤
│  Failure Trend 📈    │  Cross-Analysis 🗺️    │
│                      │  Heatmap (Location ×  │
│                      │  Config, Spec mode)   │
├──────────────────────┴───────────────────────┤
│  🔍 SN Quick Search [____________]           │
├──────────────────────────────────────────────┤
│  Footer (Report Date / Configs / WFs / Fails)│
└──────────────────────────────────────────────┘
```

---

## 验证清单

- [ ] `DashboardHeatmap` 正确渲染 Location × Config 表格
- [ ] Heatmap 颜色编码正确（spec 红色系，无数据白色）
- [ ] Heatmap 单元格显示 `5F/304T` 格式
- [ ] Heatmap hover tooltip 显示详情
- [ ] Heatmap 点击 → 跳转到 `/failure-analysis`
- [ ] Heatmap 标题 "View Details →" 链接正常
- [ ] Dark mode 下 Heatmap 颜色正确
- [ ] SN Quick Search 输入 ≥ 2 字符后出现下拉补全
- [ ] 选择补全项 → 跳转到 `/sn?q=xxx`
- [ ] 直接回车 → 跳转到 `/sn?q=xxx`
- [ ] SN Lookup 页面收到 query 参数后自动搜索
- [ ] NavBar 不再显示 SN Lookup 链接
- [ ] Mobile 端 (≤900px) NavBar mobile menu 也不显示 SN Lookup
- [ ] `/sn` 路由仍然可用（手动输入 URL）
- [ ] 中英文 i18n 正常切换
- [ ] `npm run build` 编译无报错

---

## 可删除文件（可选）

编译通过后，如果 `TopFailChart.vue` 不再被其他页面使用，可以考虑删除。但建议先保留，确认全部功能正常后再清理。

检查方法:
```bash
grep -r "TopFailChart" frontend/src/ --include="*.vue" --include="*.js"
```

---

## 风险与注意事项

1. **TopFailChart 复用检查**: 确保没有其他页面引用 `TopFailChart.vue`，再从 Dashboard 中移除
2. **API 可用性**: `/api/fa/cross` 依赖 FA Tracker 文件存在，如果文件缺失会返回 404。DashboardHeatmap 需要优雅处理这种情况（显示 "暂无数据"）
3. **Dark mode**: Heatmap 颜色方案需要测试 dark/light 两种主题
4. **性能**: cross-analysis API 解析 Excel 文件，如果文件很大可能会慢。Dashboard 首次加载需要并行请求以避免阻塞
