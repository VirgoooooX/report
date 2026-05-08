# M60 EVT REL Dashboard — 前端重设计规范

## 1. 设计哲学

**精密工业 (Precision Industrial)** — 以工程终端的克制与精确为基调，融合现代数据仪表盘的可读性。冷调灰白基底上，纯白卡片承载数据，Conic 环形进度作为视觉锚点，等宽字体点缀赋予代码级可追溯感。一切服务于数据的清晰呈现与快速对比。

核心原则：
- **数据优先** — 装饰服务于信息层级，不为装饰牺牲可读性
- **克制色彩** — 大面积中性色，功能色仅在需要时出现（成功/失败/警告）
- **精确动效** — 动画快速且目的明确，不拖慢操作节奏
- **工程质感** — 细线分隔、等宽数字、代码风格 SN 标识

---

## 2. 设计系统

### 2.1 色彩体系

#### 背景层级
| Token | 色值 | 用途 |
|-------|------|------|
| `--bg-root` | `#f5f7fa` | 页面根背景 |
| `--bg-card` | `#ffffff` | 卡片/表格/面板背景 |
| `--bg-card-hover` | `#fafbfc` | 卡片悬停 |
| `--bg-nav` | `#ffffff` | 导航栏背景 |
| `--bg-input` | `#f5f7fa` | 输入框背景 |
| `--bg-overlay` | `rgba(26, 35, 50, 0.4)` | 弹窗遮罩 |
| `--bg-row-stripe` | `#fafbfc` | 表格斑马纹 |
| `--bg-row-hover` | `#f0f4f8` | 表格行悬停 |
| `--bg-tag` | `#f0f2f5` | 标签/芯片背景 |
| `--bg-progress-track` | `#e8ecf2` | 进度条轨道 |

#### 文字层级
| Token | 色值 | 用途 |
|-------|------|------|
| `--text-primary` | `#1a2332` | 标题、正文、高优先级数据 |
| `--text-secondary` | `#4a5568` | 次级信息、描述文字 |
| `--text-muted` | `#8e99a8` | 辅助文字、占位符、表头 |
| `--text-inverse` | `#ffffff` | 深色背景上的文字 |

#### 边框 & 分割
| Token | 色值 | 用途 |
|-------|------|------|
| `--border-card` | `#e2e6ed` | 卡片边框 |
| `--border-light` | `#edf0f4` | 表格内部分割线、轻分割 |
| `--border-input` | `#d1d5db` | 输入框边框 |
| `--border-focus` | `#4f6f8f` | 聚焦态边框 |

#### 功能色
| Token | 色值 | 用途 |
|-------|------|------|
| `--color-success` | `#22c55e` | 通过/完成/正向趋势 |
| `--color-warning` | `#f59e0b` | 警告/延期/注意 |
| `--color-danger` | `#ef4444` | 失败/错误/严重 |
| `--color-info` | `#4f6f8f` | 信息/主进度/链接 |
| `--color-success-bg` | `#f0fdf4` | 成功态背景 |
| `--color-warning-bg` | `#fffbeb` | 警告态背景 |
| `--color-danger-bg` | `#fef2f2` | 失败态背景 |
| `--color-info-bg` | `#f0f4f8` | 信息态背景 |

#### 品牌 & 图表色
| Token | 色值 | 用途 |
|-------|------|------|
| `--accent-steel` | `#4f6f8f` | 主进度环、强调 |
| `--accent-slate` | `#64748b` | 次级元素 |
| `--chart-r1fnf` | `#4f6f8f` | R1FNF 标识色 |
| `--chart-r2cnm` | `#0891b2` | R2CNM 标识色 |
| `--chart-r3` | `#d97706` | R3 标识色 |
| `--chart-r4` | `#059669` | R4 标识色 |
| `--chart-spec` | `#ef4444` | Spec 失败趋势线 |
| `--chart-strife` | `#f59e0b` | Strife 失败趋势线 |
| `--cat-drop` | `#ef4444` | Drop 分类色 |
| `--cat-ingress` | `#4f6f8f` | Ingress 分类色 |
| `--cat-environmental` | `#22c55e` | Environmental 分类色 |
| `--cat-mechanical` | `#d97706` | Mechanical 分类色 |

### 2.2 字体系统

```css
--font-display: 'Work Sans', system-ui, -apple-system, sans-serif;
--font-mono: 'Source Code Pro', 'JetBrains Mono', 'Cascadia Code', monospace;
```

| 层级 | 字号 | 字重 | 字体 | 用途 |
|------|------|------|------|------|
| `text-display` | `28px` | `700` | Work Sans | 概览大数字 |
| `text-h1` | `22px` | `700` | Work Sans | 页面标题 |
| `text-h2` | `16px` | `600` | Work Sans | Section 标题 |
| `text-h3` | `14px` | `600` | Work Sans | 卡片内标题 |
| `text-body` | `14px` | `400` | Work Sans | 正文、表格内容 |
| `text-body-sm` | `13px` | `400` | Work Sans | 次级表格 |
| `text-caption` | `11px` | `500` | Work Sans | 标签、徽标、表头 |
| `text-caption-mono` | `11px` | `500` | Source Code Pro | SN、WF编号、CP索引 |
| `text-code` | `12px` | `400` | Source Code Pro | 代码片段、数据标识符 |
| `text-overline` | `10px` | `600` | Work Sans | 小标题大写、tracking |

**字体加载策略**：Google Fonts CDN 加载 `Work Sans:wght@400;500;600;700` 和 `Source Code Pro:wght@400;500;600`，配合 `font-display: swap`。

### 2.3 间距系统

基于 4px 栅格：

| Token | 值 | 用途 |
|-------|-----|------|
| `--space-xs` | `4px` | 图标与文字间隙、紧凑间距 |
| `--space-sm` | `8px` | 同类元素间距 |
| `--space-md` | `12px` | 卡片内 padding 子级 |
| `--space-lg` | `16px` | 卡片间距、section 内间距 |
| `--space-xl` | `24px` | 卡片 padding、大区块间距 |
| `--space-2xl` | `32px` | Section 间距 |
| `--space-3xl` | `40px` | 页面级间距 |

### 2.4 圆角

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | `4px` | 标签、徽标、小按钮 |
| `--radius-md` | `8px` | 卡片、面板、输入框 |
| `--radius-lg` | `12px` | 弹窗、大面板 |
| `--radius-full` | `9999px` | 药丸按钮、芯片 |

### 2.5 阴影

| Token | 值 | 用途 |
|-------|-----|------|
| `--shadow-card` | `0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)` | 卡片默认 |
| `--shadow-card-hover` | `0 4px 12px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)` | 卡片悬停（仅可点击卡片） |
| `--shadow-modal` | `0 20px 60px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.05)` | 弹窗 |
| `--shadow-nav` | `0 1px 0 rgba(0,0,0,0.05)` | 导航栏底部 |

### 2.6 动效令牌

| Token | 值 | 用途 |
|-------|-----|------|
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | 出现/展开动画 |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | 过渡/变换 |
| `--duration-fast` | `150ms` | hover 状态、微交互 |
| `--duration-normal` | `250ms` | 展开/折叠、tab 切换 |
| `--duration-slow` | `500ms` | 环形进度初始动画 |
| `--duration-page` | `1200ms` | 环形进度 dashoffset |

---

## 3. 布局架构

### 3.1 整体结构

```
App.vue
├── NavBar.vue          (sticky, h=56px)
└── <router-view>       (max-width=1440px, mx-auto, px=32px, py=24px)
    ├── Dashboard.vue
    ├── CategoryDetail.vue
    ├── SnLookup.vue
    ├── PredictionsView.vue
    └── ExportView.vue
```

### 3.2 导航栏 (NavBar.vue)

- 高度 56px，sticky top，背景白色 + 底部分割线
- 左：品牌名 "M60 EVT REL"（Work Sans 700 14px） + "Dashboard" 灰色标签
- 中：导航链接 — 深色实心药丸按钮（当前页） / 浅灰文字（其他页）
  - Dashboard / Categories / SN / Predictions / Export
  - `router-link-active` 时：`bg: #1a2332, color: #fff, radius: 6px`
  - 非活跃时：`color: #8e99a8`，hover 时 `color: #1a2332`
- 右：报告日期（等宽字体 13px，浅灰背景圆角标签）

### 3.3 页面容器

```css
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 32px 40px;
}
```

### 3.4 Section 组件

每个 Section 由标题行 + 内容区组成：

```
┌─ Section Header ─────────────────────────────┐
│  ● H2 Title          ──── divider ──  subtitle│
└───────────────────────────────────────────────┘
┌─ Section Content ────────────────────────────┐
│                                               │
└───────────────────────────────────────────────┘
```

- H2：16px Work Sans 600 `--text-primary`
- divider：flex:1, height:1px, `--border-light`
- subtitle：13px Work Sans 400 `--text-muted`
- Section 间距：32px

---

## 4. 组件库规范

### 4.1 RingProgress.vue

**用途**：环形进度指示器（已实现，需调整样式）

**Props：**
- `pct: Number` (0-100)
- `color: String` (默认 `#4f6f8f`)
- `label: String` (显示在百分比下方)
- `sublabel: String` (可选，显示在最下方)
- `size: String` (`'large' | 'medium' | 'small'`)

**尺寸配置（保持不变）：**
| size | vb | r | sw | 用途 |
|------|-----|----|----|------|
| large | 140 | 58 | 10 | Overall 概览 |
| medium | 120 | 48 | 8 | Category 概览 |
| small | 90 | 35 | 7 | Config 小卡片 |

**行为**：mounted 时 `stroke-dashoffset` 从 `circ` (0%) 动画到目标值，duration 1.2s，ease-out。

### 4.2 ConicRing.vue (新组件)

**用途**：Conic 渐变环形图，用于 Dashboard Overview 主卡片（区别于普通环形）

**Props：**
- `pct: Number`
- `size: Number` (默认 80，px)

**视觉规格**：
- 外环：conic-gradient 从 `#4f6f8f` 到 `#e8ecf2`，根据 pct 计算角度
- 内圆：白色填充，居中显示百分比数字
- 数字字体：Work Sans 700，字号 24px（80px 外环下）

**行为**：CSS `@property` 驱动或 JS requestAnimationFrame 完成 conic-gradient 角度动画。

### 4.3 OverviewCards.vue

**用途**：Dashboard 顶部的概览环形卡片组

**布局**：`grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; gap: 16px`

**卡片规格：**
- 白底 + 1px `--border-card` + `--radius-md` + `--shadow-card`
- padding: 20px 16px
- 内容居中排列

**Overall 卡片 (grid-col 1, 大号)：**
- ConicRing (80px) 作为主视觉
- 下方 label: "Overall Completion"
- sublabel: "1,247 / 1,450 CPs" (等宽数字)

**Config 卡片 (grid-col 2-5, 小号)：**
- RingProgress (small) 作为主视觉
- 下方 label: Config 名 (R1FNF/R2CNM/R3/R4)
- sublabel: "x,xxx / x,xxx CPs"

**加载态**：骨架屏 — 灰色占位圆环 + 两行文字占位条
**错误态**：环形区域显示 "—"，文字显示 "Failed to load"
**空数据**：环形 0%，文字显示 "No data"

### 4.4 CategoryCards.vue

**用途**：4 个分类的进度卡片

**布局**：`grid-template-columns: repeat(4, 1fr); gap: 16px`

**卡片规格：**
- 白底 + 1px `--border-card` + `--radius-md` + `--shadow-card`
- 左侧 4px 彩色竖条（分类色）
- overflow: hidden（让竖条圆角贴合卡片）
- hover: `--shadow-card-hover` + translateY(-2px)（可点击跳转）
- cursor: pointer

**内容：**
- 分类名（14px Work Sans 600，分类色）
- 进度条：高 8px，灰色轨道 + 分类色填充，圆角 4px
- 统计行：左 "XX.X%"（16px 700），右 "completed / total CPs"（12px muted）

**加载态**：占位卡片，进度条宽度为 0
**空分类**：进度 0%，统计显示 "—"

### 4.5 TrendChart.vue

**用途**：Spec/Strife 失败率趋势折线图

**技术**：`vue-chartjs` 的 `<Line>` 组件

**数据**：来自 `overviewData.trend`

**规格：**
- 高度 280px，responsive: true, maintainAspectRatio: false
- X 轴：日期（MM-DD），字体 10px `--text-muted`
- Y 轴：失败数量，从 0 开始
- 两条线：Spec（`#ef4444`，2px）+ Strife（`#f59e0b`，2px）
- tension: 0.3，pointRadius: 3，fill: true（透明度 0.08）
- 图例：底部，字体 11px
- Tooltip：深色背景 `#1a2332`，白字，8px 圆角

**加载态**：灰色矩形占位 280px
**无数据**：占位区域显示 "No trend data"

### 4.6 TopFailChart.vue

**用途**：Top 5 失败项水平柱状图

**技术**：`vue-chartjs` 的 `<Bar>` 组件

**数据**：来自 `overviewData.failures.top_failures`

**规格：**
- 高度 280px，indexAxis: 'y'
- 标签：`WF{wf} {wf_name} {config} {test}`（截断超过 30 字符）
- 柱色：rate > 50% 红色、> 20% 橙色、其他钢蓝色
- 柱高 16px，圆角 4px
- Tooltip 显示精确百分比

### 4.7 DailyUpdates.vue

**用途**：每日 CP 更新可折叠列表

**结构：**
- 外层卡片（白底 + 边框 + 阴影）
- Header 栏（可点击折叠）：chevron 图标 + 标题 + 更新计数 + Toggle 按钮
- Body 区域（可折叠）：WF 分组 → Config 行

**Header 栏：**
- Chevron: `▶` 初始态，展开时旋转 90°（transition 250ms）
- 标题: "CP Changes Today"，14px 600
- 计数: "X WF(s) updated"，12px muted
- Toggle 按钮: 浅灰底边框按钮，12px

**WF 行：**
- 深色药丸 WF 编号: `bg: #1a2332, color: #fff, font: Source Code Pro 11px 600`
- WF 名称（如有）: 13px `--text-secondary`
- 右侧: Config 数标签

**Config 行（缩进显示）：**
- Config 名: 12px Source Code Pro `--color-info` 500
- Delta: "+X CPs"（绿色 600）
- Latest CP 信息: 12px muted

**行为：**
- 点击 Header 展开/折叠 Body
- 初始默认展开
- Body `max-height` 动画过渡（400ms）

**空数据**：Header 显示 "No CP updates today"（灰色居中）

### 4.8 FailureAnalysis.vue

**用途**：失败率分析多维度表格

**结构：**
- 外层卡片（白底 + 边框）
- Tab 栏（无边框下划线式）
- 表格内容区

**Tab 栏：**
- 平铺按钮: "By Test Item" / "By Config" / "By WF" / "Top N"
- 默认 tab: "By Test Item"
- 活跃 tab: `color: #1a2332, font-weight: 600, border-bottom: 2px solid #4f6f8f`
- 非活跃 tab: `color: #8e99a8`，hover 时 `color: #4a5568`
- Tab 切换时内容淡入（opacity 过渡 250ms）

**表格：**
- 列: # (序号) | Dimension | Spec Fail | Strife Fail | Total | Failure Rate
- 表头: 10px 大写 `--text-muted`，背景 `--bg-row-stripe`
- 行: 斑马纹，hover 高亮
- 失败行: 左侧 3px `--color-danger` 色条
- 失败率列: 红色加粗数字（rate > 0）
- 数字列右对齐，tabular-nums
- 行可点击 → 打开 FAModal

### 4.9 TestSummary.vue

**用途**：全量测试摘要矩阵表

**结构：**
- 外层卡片（白底 + 无 padding，内滚动）
- 水平滚动容器
- 双层表头矩阵表

**表头行 1：** WF | Config1 (colspan=N) | Config2 (colspan=N) | ...
- Config 名用对应图表色显示

**表头行 2：** # | Test1 | Test2 | ... | Test1 | Test2 | ...

**表体：**
- WF 列: 70px 宽，左对齐，600，`--text-secondary`
- 单元格: 居中，tab-nums
- cell-pass: 浅绿底 `--color-success-bg`，绿色文字
- cell-strife: 浅黄底 `--color-warning-bg`，橙色文字，cursor:pointer
- cell-fail: 浅红底 `--color-danger-bg`，红色文字，cursor:pointer，font-weight:600
- cell-empty: 灰色 "—"
- 失败单元格点击 → 打开 FAModal（传入该单元格的 failure_sns）

### 4.10 FAModal.vue

**用途**：FA 记录查看弹窗

**行为：**
- 遮罩: `--bg-overlay` + backdrop-blur(4px)
- 弹窗: 白底 + `--radius-lg` + `--shadow-modal`，max-width 700px，max-height 80vh
- 出现: opacity 0→1 + scale(0.97)→1 + translateY(20px)→0（300ms ease-out）
- 关闭: 点击遮罩 / ESC / 点击关闭按钮
- Header: 标题(16px 600) + 关闭按钮(X, 24px)
- Body: 滚动容器，padding 20px 24px

**Body 内容：**
- 受影响 SN 列表（如果有 presetSns）：灰色标签横排
- FA 记录卡片列表：
  - 每条记录一个浅灰底卡片（`--bg-root`），左侧 3px 钢蓝竖条
  - 字段以行内形式展示：`label: value`

**加载态**：Body 内 spinner + "Loading FA records..."
**空数据**："No FA records found" + 受影响 SN 列表
**错误态**：错误信息 + Retry 按钮

### 4.11 CatManageModal.vue

**用途**：分类 WF 管理弹窗

**行为**：同 FAModal 的弹窗行为

**内容：**
- Tab: Drop / Ingress / Environmental / Mechanical（下划线式）
- WF Chip 列表：灰色圆角芯片，右侧 X 移除按钮
  - Chip: `bg: #f0f2f5, border: 1px solid --border-light, radius-full`
  - 移除按钮: hover 变红
- 添加区：输入框 + "Add WF" 按钮（钢蓝色）
  - 输入框支持 Enter 提交

### 4.12 StatusBadge.vue (新组件)

**用途**：统一的状态徽标

**类型**：`pass | spec_fail | strife_fail | auto | manual | done | pending`

**规格**：
- 行内块，padding: 2px 8px，radius: 4px
- 字体：11px 600 Work Sans
- pass: 绿底绿字（`--color-success-bg` + `--color-success`）
- spec_fail: 红底红字
- strife_fail: 黄底黄字
- auto: 蓝底蓝字
- manual: 橙底橙字
- done: 绿底绿字
- pending: 灰底灰字

### 4.13 LoadingState.vue (新组件)

**用途**：统一的加载态

**Props**：`text: String`（默认 "Loading..."）

**规格**：
- 居中 flex 列布局
- Spinner: 24px 圆环，2px `--border-card` 边框 + `--accent-steel` 顶部色，0.8s 线性旋转
- 文字: 13px `--text-muted`，在 spinner 下方 12px

### 4.14 ErrorState.vue (新组件)

**用途**：统一的错误态

**Props**：`message: String`, `retry: Function`

**规格**：
- 居中 flex 列布局
- 错误图标（可选）或红色文字标题
- 消息文字: 13px `--color-danger`
- Retry 按钮: 红底白字，8px 20px padding，6px 圆角

### 4.15 EmptyState.vue (新组件)

**用途**：统一的空数据态

**Props**：`text: String`（默认 "No data available"）

**规格**：
- 居中，灰色文字，padding 40px

---

## 5. 页面规范

### 5.1 Dashboard.vue

**路由**：`/`

**数据依赖**：
- `GET /api/dashboard/overview` → Pinia `overviewData`
- `GET /api/test-summary` → Pinia `summaryData`

**Section 顺序（自上而下）：**

```
1. Completion Overview (OverviewCards)
2. Category Completion (CategoryCards) + 右侧 Edit 按钮
3. Trend Analysis
   ├── Failure Rate Trend (TrendChart)
   └── Top 5 Failures (TopFailChart)
4. Daily CP Updates (DailyUpdates)
5. Failure Rate Analysis (FailureAnalysis)
6. Overall Test Summary (TestSummary)
7. Footer (报告日期、统计汇总)
```

**初始化流程：**
1. `onMounted` → Pinia `fetchOverview()` + `fetchSummary()` 并行
2. 加载中：所有 section 显示 LoadingState
3. 成功：各 section 渲染真实数据
4. 失败：显示 ErrorState + retry 重新调用 fetch

**Footer 内容：**
- Report Date / Total Configs / Total WFs / Total Failures
- 版权文字（12px muted）

**弹窗管理：**
- `showFAModal: ref(false)` + `faModalWf: ref('')` + `faModalTitle: ref('')` + `faModalSns: ref([])`
- `showCatModal: ref(false)`
- FAModal 由 FailureAnalysis 表格行点击或 TestSummary 单元格点击触发
- CatManageModal 由 Category Section 的 Edit 按钮触发

### 5.2 CategoryDetail.vue

**路由**：`/category/:name`

**数据依赖**：`GET /api/completion/category/:name`

**布局：**
- 面包屑: Dashboard / Category Name
- 页面标题: "Category Name" (22px 700)
- 副标题说明
- Back to Dashboard 链接按钮

**汇总卡片**（grid 自适应列）：
- Overall 卡片（左侧进度填充 + 大数字 + 分类色）
- 各 Config 卡片（同理，无分类色）

**WF 列表**（手风琴折叠）：
- 每行：chevron + WF 编号药丸 + WF 名称 + 右侧完成百分比
- 展开后：Config 明细行（Config名 + 进度条 + 百分比 + CP数 + SN数）
- 默认全部折叠
- chevron 旋转动画

**加载/错误/空数据**：使用统一组件

### 5.3 SnLookup.vue

**路由**：`/sn`

**数据依赖**：
- `GET /api/sn/search?q=xxx`（自动补全）
- `GET /api/sn/:sn`（查询）

**布局：**
- 页面标题 + 说明
- 搜索框卡片：
  - 输入框（大号 15px，等宽字体）+ Search 按钮（钢蓝色）
  - 自动补全建议条（输入 ≥3 字符时出现）
    - 横向 chips 排列，点击填入搜索框并查询
    - 防抖 300ms
- 结果区：
  - SN 标题 + 失败记录数警告条（红色左边框，如有）
  - WF 分组折叠表格（类似 CategoryDetail 的手风琴）
  - 每行：chevron + WF + Config + 最新日期 + 进度 + CP 状态
  - 展开：历史记录子表（日期 + CP + 进度）

### 5.4 PredictionsView.vue

**路由**：`/predictions`

**数据依赖**：
- `GET /api/predictions`
- `POST /api/predictions/update`

**布局：**
- 统计卡片行（4 列 grid）：
  - Total Predictions / Manual Overrides / Overdue（红色）/ Completed（绿色）
- 过滤栏（卡片内顶部）：
  - WF 输入框 + Config 下拉 + Refresh 按钮
- 预测表格：
  - 列: WF | Config | Test | Progress(进度条) | Daily Rate | Remaining Days | Predicted Date | Type
  - Predicted Date 列：蓝色可编辑链接，点击打开编辑弹窗
  - Type 列：Auto(蓝) / Manual(橙) 徽标
  - 进度条：6px 高，绿色(完成) / 蓝色(进行中)
  - 排序：点击列头排序（WF/Config/Test/Daily Rate/Remaining Days/Predicted Date）

**编辑弹窗：**
- 标题：Edit Prediction
- 日期输入框（type=date）
- Save（绿色）/ Cancel（灰色）按钮
- Save 成功后刷新列表

### 5.5 ExportView.vue

**路由**：`/export`

**数据依赖**：`GET /api/export?wf=&config=&sn=&format=`

**布局：**
- 过滤表单（4 列 grid）：
  - WF 输入框 / Config 下拉 / SN 输入框 / Format 下拉
  - 字段标签在上，输入框在下
- 操作按钮组：
  - Preview（蓝色）/ Download CSV（绿色）/ Download JSON（灰色）
- 结果区：
  - 记录数统计
  - 预览表格（最多 50 行）：
    - 列: SN | Unit | WF | Config | Current CP | Progress | CP Results
    - CP Results: 徽标行内排列，超过 5 个显示 "..."
    - 水平滚动
  - 超过 50 条时底部提示 "Showing 50 of N records. Download for full dataset."

**导出行为：**
- CSV: `window.location` 跳转下载
- JSON: `fetch` + Blob + `createObjectURL` 下载

---

## 6. 数据流

### 6.1 Store (app.js)

已有 store 结构，需补充：

```js
// 新增状态
const categories = ref([])          // GET /api/categories
const categoryDetail = ref(null)    // GET /api/completion/category/:name
const predictions = ref([])         // GET /api/predictions
const snResult = ref(null)          // GET /api/sn/:sn
const exportData = ref(null)        // GET /api/export

// 新增 actions
async function fetchCategories() { ... }
async function fetchCategoryDetail(name) { ... }
async function fetchPredictions() { ... }
async function fetchSnResult(sn) { ... }
async function fetchExportData(filters) { ... }
```

### 6.2 API 代理

Vite 开发环境代理 `/api` → `http://localhost:5050`（已配置）

---

## 7. 响应式断点

| 断点 | 宽度 | 布局变化 |
|------|------|----------|
| Desktop | ≥ 1200px | 完整布局 |
| Tablet | 768–1199px | Overview grid 变 3 列 + Overall 全宽；Category grid 变 2 列；Charts 变单列 |
| Mobile | < 768px | Overview grid 2 列；Category grid 1 列；侧 padding 16px；Summary table 缩小字号 |

非断点下的弹性行为：
- 表格使用 `overflow-x: auto`，不破坏布局
- 卡片 grid 使用 `auto-fill / minmax` 在部分区域自适应

---

## 8. 无障碍

- 所有交互元素可键盘操作（Tab 导航、Enter/Space 激活）
- 图表提供 `aria-label`
- 表格使用正确的 `<thead>` / `<tbody>` 结构
- 弹窗打开时焦点移入，关闭时焦点返回触发元素
- 颜色不是唯一的区分方式（失败同时有左侧色条 + 文字颜色 + 内容）
- 足够的色彩对比度（白色背景上最小 4.5:1）

---

## 9. 文件结构

```
frontend/src/
├── main.js
├── App.vue
├── router/
│   └── index.js
├── stores/
│   └── app.js
├── views/
│   ├── Dashboard.vue
│   ├── CategoryDetail.vue
│   ├── SnLookup.vue
│   ├── PredictionsView.vue
│   └── ExportView.vue
├── components/
│   ├── NavBar.vue              # 修改：新配色
│   ├── RingProgress.vue        # 修改：新配色 + Conic 变体
│   ├── ConicRing.vue           # 新增
│   ├── OverviewCards.vue       # 新增
│   ├── CategoryCards.vue       # 新增
│   ├── TrendChart.vue          # 新增
│   ├── TopFailChart.vue        # 新增
│   ├── DailyUpdates.vue        # 新增
│   ├── FailureAnalysis.vue     # 新增
│   ├── TestSummary.vue         # 新增
│   ├── FAModal.vue             # 新增
│   ├── CatManageModal.vue      # 新增
│   ├── StatusBadge.vue         # 新增
│   ├── LoadingState.vue        # 新增
│   ├── ErrorState.vue          # 新增
│   └── EmptyState.vue          # 新增
├── composables/
│   └── useApi.js               # 新增：API 请求封装（错误处理、重试）
└── assets/
    └── styles/
        ├── variables.css        # 修改：全新设计令牌
        └── global.css           # 修改：匹配新设计系统
```

---

## 10. 技术决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 图表库 | vue-chartjs (Chart.js) | 已安装，声明式 API，轻量 |
| 字体加载 | Google Fonts CDN | 简单可靠，`font-display:swap` 防闪烁 |
| 弹窗 | 手写 Vue 组件 | 不引入第三方 UI 库，保持轻量；需求简单 |
| CSS 方案 | Scoped CSS + CSS Variables | 已使用，无需引入新工具 |
| 日期格式化 | 原生 `Date` / 简单字符串 | 日期来源已是格式化字符串 |
| 数字格式化 | `Intl.NumberFormat` | 浏览器原生，性能好 |
