# M60 EVT REL Dashboard — 方法论与系统文档

## 一、项目概述

M60 EVT REL Dashboard 是一个内部工程工具，用于追踪硬件验证测试（EVT Reliability）在多个 Workflow、Config 和 SN 维度下的进度与失败分析。

**核心能力**：
- 自动解析 Daily Report Excel 文件，提取 SN 级测试结果
- 基于单元格填充色判定 Pass/Spec Fail/Strife Fail 状态
- CP-to-Test 智能映射算法，将数十个 Checkpoint 归属到 Test Summary 的 Test1/2/3
- 失败分析（FA）交叉验证，关联 FA Tracker 记录
- 完成率预测、排程时间线、每日变更追踪
- 全功能 Web Dashboard（Vue 3 SPA + Flask API）

**技术栈**：Python 3.12 / Flask / SQLite WAL / Vue 3 / Ant Design Vue / Vite / Docker

---

## 二、开发历程

项目从 2026-05-08 首次提交至 2026-05-14 发布 v1.0.10，经历了以下主要阶段：

### Phase 1：前端 SPA 迁移（05-08 ~ 05-09 上午）

- 从零搭建 Vue 3 SPA，完成精密工业风格设计
- 实现 Dashboard 总览、Category 分组、Predictions 预测、DailyUpdates 每日更新等核心页面
- 对齐前端组件 props 与后端 API 字段名
- 实现 Category CRUD、WF 自然排序、Test Summary 矩阵视图

### Phase 2：数据分析引擎完善（05-09 日间）

- 从 Test Summary sheet 获取测试名和 CP 结构
- 重构预测视图为按 WF 分组展示
- 新增失败分析独立页面与交叉分析热力图
- 新增 FA Tracker 独立分析模块
- 实现 per-SN failure type/location 提取
- 新增 Daily Issues 每日新增失败追踪

### Phase 3：数据库重构 — 事实表架构（05-09 晚 ~ 05-10）

- 引入报告版本管理（`reports` 表 + version + is_active）
- 新增报告定义快照表（`report_wf_meta`, `report_test_names`, `report_cps`）
- 新增 SN 级事实表（`sn_cp_results`, `sn_check_results`）
- 实现 double-write 迁移策略，API 逐步切换到事实表查询
- 添加事实一致性校验测试

### Phase 4：UI/UX 现代化（05-10 下午）

- 引入 CSS Design Token 体系
- 现代化 Category Cards、Failure KPI、Heatmap 等组件
- 统一页面布局节奏，改善加载/空/错误状态
- 接入 Ant Design 主题 Token，减少 deep override
- 响应式导航菜单

### Phase 5：Check Item 状态历史模型（05-10 晚）

- 从每日全量快照切换到状态历史段（`sn_check_state_history`）
- 同一检查项状态不变时只延长区间，状态变化时关闭旧段、新增新段
- 大幅减少重复 pass/pending/skip 存储

### Phase 6：排程与上传功能（05-10 ~ 05-11）

- 新增测试排程视图（Schedule Timeline）
- 从 Excel 提取计划日期段，支持 marker 匹配与置信度标注
- 新增报告上传功能（前端上传 → 后端解析入库）
- 优化 CP 表头检测逻辑

### Phase 7：生命周期表重构与项目结构化（05-11 ~ 05-12）

- 重构生命周期表，优化 Excel 解析与 API 查询逻辑
- 核心查询改用生命周期表并添加兼容降级
- 重构项目目录结构（统一 `backend/` 布局）
- 配置 GitHub CI（多架构 Docker 镜像推送 GHCR）
- 发布 v1.0.1 ~ v1.0.5（Gunicorn 部署、构建优化）

### Phase 8：查询中心与高级功能（05-12 ~ 05-13）

- 新增 Query Center 统一查询页面（3 种模式：WF 查询、SN 时间线、Check Item 明细）
- 实现 SN Lifecycle 时间线组件（CP 展开 + Check Item 过滤）
- 集成 FA Tracker 失效信息查询
- 新增 Settings 页面与自定义规则管理
- 新增原始数据验证机制（异常检测）
- 发布 v1.0.6 ~ v1.0.9

### Phase 9：稳定化与优化（05-14）

- Gunicorn 超时参数调整（200s）
- 重构文件存储逻辑
- 发布 v1.0.10

---

## 三、输入文件

| 文件 | 用途 |
|---|---|
| `M60 EVT Rel Daily Report_*.xlsx` | 每日报告，含 Test Summary 和每个 WF 的详细 sheet |
| `M60 EVT REL FA Tracker_*.xlsx` | 失效分析追踪表 |

### 3.1 Daily Report 结构

**Test Summary sheet**：
- 数据从 B 列开始，A 列为空
- 第 10 行：`System`（系统级测试标记）
- 第 11 行：Config 表头
- 第 12 行：`Waterfall | Quantity×4 | Test1 | Results×4 | Test2 | Results×4 | Test3 | Results×4`
- 第 14 行起：每个 WF 一行
- 测试结果格式：
  - `xF/nT` = Spec Failure（红底）
  - `xSF/nT` = Strife Failure（黄底，Margin）
  - `日期` = 进行中（蓝底）
  - `空` = 未开始（白底）

**WF 详细 Sheet（Sys WF{n}_xxx）**：
- 每个 WF 一个 sheet，前 7 行为头部概要区域
- 第 8 行起为数据区：
  - **表头行**（col1=`%`, col3=`Config`, col4=`Unit #`）：列出所有 CP 名称
  - **子表头行**：每个 CP 下的检查项（Cosmetic, ISB, FACT, BT-OTA 等）
  - **数据行**：每行一个 SN，含 Config、Unit #、S/N、T0 及各 CP 的测试结果
- 列结构：`% | Completion | Config | Unit# | S/N | T0 | 【CP1...CPn】| Comments | Overall Result`
- 每个 CP 占据的列数不固定：Drop 类测试 6 列，Spill 类 2 列，根据表头中相邻 CP 的起始列确定

**Test Schedule sheet**：
- 包含每个 WF/Config/Test 的计划开始和结束日期
- 用于排程时间线展示和进度对比

### 3.2 FA Tracker 结构

**System TF sheet**：
- 第 7 行为表头
- 每行一个 FA 记录，含 FA#、SN、WF、Config、Failed Test、Failure Type、FA Status 等

---

## 四、核心概念

### 4.1 Checkpoint (CP)

CP 是表头中的**合并列或独立列**，代表一个测试阶段。每个 CP 下有一个或多个子检查项（Cosmetic、ISB、FACT、BT-OTA 等）。

**CP 列数判定**：当前 CP 的起始列到下一个 CP 的起始列 − 1。

例如 WF10：
- HS 65/90/72：col 12→17（6 列）
- Random Drop 1m PB-Drop10：col 18→23（6 列）
- Random Drop 1m PB-Drop300：col 282→287（6 列）

例如 WF25（Spill）：
- Spill After 1hr：col 12→13（2 列：Cosmetic + Button User）
- Spill HS After 72hr：col 18→23（6 列）

### 4.2 填充色 = 失败标记

失败判断不依赖单元格的文本值，只依赖**单元格的填充色**：

| 填充色 RGB | 含义 | 代码中标记 |
|---|---|---|
| `FF0000`（红色） | Spec Failure | `spec` |
| `FFFF00`（黄色） | Strife Failure（Margin） | `strife` |
| 其他/无填充 | PASS | `pass` |

**可配置**：通过 Settings 页面的自定义规则，用户可以修改 spec/strife 的判定颜色列表，以及添加字体颜色判定（如深红字体 `9C0006`）。

**技术细节**：填充色通过 openpyxl 的 `cell.fill.fgColor.rgb` 读取。Conditional Formatting 规则被 openpyxl 丢弃，但已手动应用的直接填充色可正常读取。

### 4.3 结果格式

遵循 Test Summary 的逻辑：
- 若有 Spec Failure → `xF/nT`
- 若无 Spec 但有 Strife Failure → `xSF/nT`
- 若都没有 → `0F/nT`

**Spec 优先于 Strife**：即一个 unit 的 CP 中同时出现红色和黄色，计为 Spec。

---

## 五、"最后一个实际 CP" 判定

### 5.1 算法

```
对每个 unit（SN），从右向左扫描所有 CP：
  FOR 每个 CP：
    检查该 CP 内的所有子列
    IF 所有子列的值都是 "/"：
      → 此 CP 未测试，继续扫描更左边
    IF 至少有一个子列的值不是 "/"：
      → 此 CP 为该 unit 的"最后一个实际 CP"，停止
  END FOR
```

**关键**："全部列为 `/`"才跳过；"至少有一列非 `/`"即判定为有数据。

`"/"` 的含义：测试步骤未执行或测试已停止。例如一个 unit 在 Drop50 失败后，Drop60 及之后所有列都填 `"/"`。

### 5.2 示例

WF10 R1FNF unit "DQLW9J6DVH"：
```
从右向左扫描：
  Drop300 (cols 282-287): 6/6 列是 "/" → 跳过
  Drop280 (cols 276-281): 6/6 列是 "/" → 跳过
  Drop260 (cols 270-275): 6/6 列是 "/" → 跳过
  Drop240 (cols 264-269): 0/6 列是 "/"，有实际值 → ✅ 最后实际 CP
```

---

## 六、CP-to-Test 映射

### 6.1 目标

将 WF sheet 中的多个 CP 映射到 Test Summary 中的 Test1、Test2、Test3。

每个 Test 可能包含多个 CP（例如 "Random Drop 1m PB" 包含 Drop10～Drop300 共 45 个 CP）。

### 6.2 映射算法

**Step 1：CP 分组**（基于名称相似度）

```
初始化 group 0
FOR i = 1 TO N-1 (每对相邻 CP):
  检查边界条件（按优先级）:
    1. "2nd"/"3rd" 前缀出现 → 新 group
    2. "margin" 关键词新出现 → 新 group
    3. 百分比从 ≤100% 跳变到 ≥120% (Button Cycling) → 新 group
    4. "ltos" 消失 (LTOS → 非LTOS, WF42) → 新 group
    5. "ltos" 重现 (非LTOS → LTOS, WF42) → 新 group
    6. 与上一个 CP 名称无共同词 → 新 group
    7. 否则 → 同 group
```

**Step 2：Group-to-Test 匹配**（词重叠打分）

```
对每个 group：
  计算该 group 内所有 CP 名称与每个 TS Test 名称的词重叠量
  每个重叠词计 1 分，TS Test 名称是 CP 名称的子串额外加 10 分
  选择得分最高的 Test（阈值为 ≥2 分）
```

**Step 3：去重**

```
若两个 group 匹配到同一个 Test → 保留第一个匹配，移除后续重复
```

**Step 4：补全**

```
对未匹配的 group，按位置递增分配 Test：
  从已匹配的 group 向右 → 每个未匹配 group 分配到下一个 Test
  向左回溯 → 分配到上一个 Test
```

**Step 5：强制分裂**（groups < tests 时的补偿）

```
若 group 数 < TS test 数：
  将 CP 按数量均分到各个 Test
```

### 6.3 特殊规则

| WF 系列 | 规则 | 说明 |
|---|---|---|
| WF6/7/8/9（Button Cycling）| 百分比 ≤100% → Test 非 Margin，≥120% → Test Margin | 例：BVPM-100% → Test2，BVPM-120% → Test3 |
| WF14.1–15.3（18 Sided Drop）| "2nd" 前缀 → Test Margin | 第 2 轮 Drop → Test3 |
| WF42（Battery Swap Acc）| LTOS 消失/重现 → 分界 | LTOS→非LTOS→LTOS 三段 |
| WF16.1/16.2（THC + HSD）| 首位 CP "THC" → Test1，剩余 → Test2 | THC 与 Surface 无共同词自动分界 |

---

## 七、分析主流程

```
1. 读取 Test Summary → 获取每个 WF 的 Test 名称和现有结果
2. 遍历所有 WF Sheet：
   a. 解析表头 → 获取所有 CP 的列范围和检查项名称
   b. 执行 CP-to-Test 映射 → 每个 CP 归属到 Test1/2/3
   c. 遍历所有数据行（按 SN）：
      i.   找到该 unit 的"最后一个实际 CP"
      ii.  确定该 CP 属于哪个 Test
      iii. 检查该 CP 所有列的填充色
      iv.  若红色 → 该 unit 在此 Test 中 Spec Fail
      v.   若黄色（无红色）→ Strife Fail
      vi.  记录到 per-config-per-test 的 failure 列表中
3. 汇总 per-config-per-test 结果 → xF/nT 或 xSF/nT 格式
4. 与 Test Summary 逐项对比 → 标记差异
5. 提取 SN 级事实行（CP 结果 + Check Item 状态）→ 写入数据库
6. 提取排程段 → 写入 schedule 表
7. 计算完成率预测 → 写入 predictions 表
```

---

## 八、FA Tracker 交叉验证

FA 记录通过以下字段关联到 WF 原始数据：
- `WF` → WF sheet
- `SN` → 数据行中的 S/N 列
- `Config` → 数据行中的 Config 列
- `Failed Test` → 测试名称（模糊匹配）

验证逻辑：FA 记录的 SN 是否在对应 WF/Config 的 Spec 或 Strife 失败列表中出现。

### FA 分析维度

系统支持多维度 FA 统计：
- **Overview**：总体 Spec/Strife 数量、Open/Closed 比例、按时间趋势
- **Cross Analysis**：任意两个维度的交叉热力图（WF × Config、WF × Failure Type 等）
- **Detail**：按条件过滤的 FA 明细列表

---

## 九、原始数据验证

系统在解析前对 Excel 数据进行异常检测：

- **失败后间隔数据异常**：检测 SN 在某 CP 失败后，后续 CP 仍有数据的情况（阈值可配置）
- **CP 结构一致性**：检查 CP 表头是否符合预期格式
- **Config 推断**：当 Config 列为空时，从 Unit # 推断 Config

---

## 十、数据库架构

### 10.1 表分层

| 层级 | 表 | 说明 |
|---|---|---|
| **元数据** | `reports` | 报告版本管理（日期 + 版本号 + 活跃标记） |
| **定义快照** | `report_wf_meta`, `report_test_names`, `report_cps` | 每个报告的 WF/Test/CP 结构快照 |
| **当前定义** | `current_wf_definitions`, `current_test_definitions`, `current_cp_definitions` | 最新活跃报告的定义（latest-only） |
| **SN 事实** | `sn_cp_results` [已退役] | SN 级 CP 结果（每日快照） |
| **状态历史** | `sn_check_state_history` | Check Item 级状态历史段（主数据源） |
| **排程** | `report_schedule_segments`, `current_schedule_segments` | 计划日期段 |
| **派生缓存** | `wf_results`, `report_stats`, `daily_changes`, `predictions` | 聚合统计与预测 |
| **配置** | `wf_categories`, `wf_names`, `wf_cps` | 分类与命名 |

### 10.2 Check Item 状态历史模型

`sn_check_state_history` 是系统的核心事实表，采用状态历史段设计：

- 同一 `WF + Config + SN + CP + check_item` 的状态若与前一份报告一致，只更新 `last_seen_report_*`
- 若状态发生变化，关闭上一段（设置 `closed_before_report_id`）并新增一段
- 若某检查项在新报告中消失，关闭其开放段
- 查询某个报告日的检查项明细时，按"报告 ID 落在状态段有效区间"还原

**优势**：
- 避免大量 pass/pending/skip 的重复存储
- 保留完整可追溯性（何时出现、何时变化、何时消失）
- 支持高效的"某时刻快照"查询

### 10.3 报告版本管理

- 每个日期可有多个版本（重新上传时 version 递增）
- `is_active = 1` 标记当前有效版本
- 上传新版本时自动将同日期旧版本标记为非活跃

---

## 十一、完成率预测

### 11.1 预测模型

系统根据历史进度数据自动计算每个 WF/Config/Test 的预计完成日期：

1. 收集最近 N 天的每日 CP 推进量（bulk progress）
2. 计算加权日均推进率（近期权重更高）
3. 根据剩余 CP 数和日均率估算剩余工作日
4. 跳过周末计算预计完成日期

### 11.2 预测目标筛选

- 只对"进行中"的测试生成预测（已完成或未开始的跳过）
- 支持手动覆盖预测值（`is_manual = 1`）

---

## 十二、排程时间线

### 12.1 数据提取

从 Daily Report 的 Test Schedule sheet 提取：
- 每个 WF/Config/Test 的计划开始和结束日期
- Marker 标签（CP 名称匹配）
- 置信度评级（high/medium/low）

### 12.2 Marker 匹配算法

将 Schedule sheet 中的标记点与 CP 列表进行匹配：
- 基于 Drop 编号、百分比、Profile 编号等特征签名
- 检测重置点（签名回退 → 新 Test 开始）
- 支持多种 WF 类型的特殊匹配逻辑

---

## 十三、API 端点概览

| 模块 | 端点 | 功能 |
|---|---|---|
| **Dashboard** | `/api/dashboard/overview` | 总览统计 |
| **Completion** | `/api/completion/by-config`, `/by-category`, `/wf/<n>` | 完成率 |
| **Categories** | `/api/categories` (CRUD) | 分类管理 |
| **Daily** | `/api/daily/updates`, `/api/daily/issues` | 每日更新与新增问题 |
| **Failures** | `/api/failures/stats`, `/top`, `/wf/<n>` | 失败统计 |
| **Predictions** | `/api/predictions`, `/update` | 完成预测 |
| **Schedule** | `/api/schedule` | 排程时间线 |
| **Query Center** | `/api/query/sn-timeline`, `/by-wf`, `/wf-list` | 统一查询 |
| **SN Detail** | `/api/sn/<sn>`, `/search`, `/checks`, `/resolve-mark`, `/fa` | SN 明细 |
| **FA Analysis** | `/api/fa/overview`, `/cross`, `/detail`, `/list` | 失败分析 |
| **Test Summary** | `/api/test-summary` | 测试摘要矩阵 |
| **Cell Failures** | `/api/cell-failures` | 单元格级失败明细 |
| **Export** | `/api/export` | 数据导出 |
| **Settings** | `/api/settings/rules`, `/rawdata` | 配置管理 |
| **Upload** | `/api/upload` | 报告上传 |

---

## 十四、前端页面结构

| 页面 | 组件 | 功能 |
|---|---|---|
| Dashboard | `Dashboard.vue` | 总览卡片 + Category 分组 + 热力图 |
| Test Summary | `TestSummaryView.vue` | 与 Excel TS sheet 同构的矩阵视图 |
| Daily Update | `DailyUpdateView.vue` | 每日进度变更时间线 |
| Failure Matrix | `FailureMatrixPage.vue` | FA 交叉分析热力图 + KPI 卡片 |
| Predictions | `PredictionsView.vue` | 按 WF 分组的完成预测表 |
| Schedule | `ScheduleView.vue` | 甘特图式排程时间线 |
| Query Center | `QueryCenter.vue` | 统一查询（WF/SN/Check Item 三模式） |
| Settings | `SettingsView.vue` | 自定义规则 + 原始数据管理 |
| Export | `ExportView.vue` | 数据导出 |

---

## 十五、自定义规则系统

通过 `custom_rules.json` 持久化，支持：

**解析规则**：
- `spec_fill_colors` / `strife_fill_colors`：失败判定颜色
- `spec_font_colors`：字体颜色判定
- `ignore_wfs`：忽略的 WF 列表
- `config_aliases`：Config 名称别名

**显示规则**：
- `project_name`：项目名称
- `wf_aliases`：WF 显示别名
- `hidden_wfs`：隐藏的 WF
- `config_order`：Config 显示顺序
- `status_labels`：状态标签文本

---

## 十六、已知限制

1. **WF34（Accumulation）** 结构特殊，尚未解析
2. **WF33（UV indoor/outdoor）** 结构不同，尚未解析
3. **Conditional Formatting 字体颜色变化**（如深红字体 `FF9C0006`）需通过自定义规则配置
4. **部分 WF（29.1-29.4）** CP 起始列为 7 而非 12，标题行结构不同

---

## 十七、部署与运维

### 17.1 Docker 部署

- 多阶段构建：Node 20 构建前端 → Python 3.12-slim 运行时
- Gunicorn 生产服务器（4 workers，200s timeout）
- SQLite 数据库文件挂载为 volume

### 17.2 CI/CD

- GitHub Actions：后端测试 → 前端测试/构建 → Docker 多架构镜像推送 GHCR
- 版本标签：`v1.0.x` 语义化版本

### 17.3 数据管理

- 报告文件存储在 `rawdata/` 目录
- 数据库文件在 `db/report.db`
- 支持 `--rebuild` 全量重建（从 Excel 源文件重新解析）
- 上传新报告自动触发增量处理
