# M60 EVT REL 分析逻辑与方法

## 一、概述

本系统从 M60 EVT Rel Daily Report 和 FA Tracker 两个 Excel 文件中自动解析原始测试数据，计算每个 WF（Waterfall）在每个 Config（R1FNF/R2CNM/R3/R4）下的 Failure Rate，并与手工填写的 Test Summary 和 FA Tracker 做交叉验证。

**核心原则**：不信任任何预计算的 summary，一切从原始数据单元格的**填充色**出发重新计算。

---

## 二、输入文件

| 文件 | 用途 |
|---|---|
| `M60 EVT Rel Daily Report_*.xlsx` | 每日报告，含 Test Summary 和每个 WF 的详细 sheet |
| `M60 EVT REL FA Tracker_*.xlsx` | 失效分析追踪表 |

### 2.1 Daily Report 结构

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
  - **表头行**（col1=`%`, col3=`Config`, col4=`Unit #`）：列出所有 Checkpoint（CP）名称
  - **子表头行**：每个 CP 下的检查项（Cosmetic, ISB, FACT, BT-OTA 等）
  - **数据行**：每行一个 SN，含 Config、Unit #、S/N、T0 及各 CP 的测试结果
- 列结构：`% | Completion | Config | Unit# | S/N | T0 | 【CP1...CPn】| Comments | Overall Result`
- 每个 CP 占据的列数不固定：Drop 类测试 6 列，Spill 类 2 列，根据表头中相邻 CP 的起始列确定

### 2.2 FA Tracker 结构

**System TF sheet**：
- 第 7 行为表头
- 每行一个 FA 记录，含 FA#、SN、WF、Config、Failed Test、Failure Type、FA Status 等

---

## 三、核心概念

### 3.1 Checkpoint (CP)

CP 是表头中的**合并列或独立列**，代表一个测试阶段。每个 CP 下有一个或多个子检查项（Cosmetic、ISB、FACT、BT-OTA 等）。

**CP 列数判定**：当前 CP 的起始列到下一个 CP 的起始列 − 1。

例如 WF10：
- HS 65/90/72：col 12→17（6 列）
- Random Drop 1m PB-Drop10：col 18→23（6 列）
- ...
- Random Drop 1m PB-Drop300：col 282→287（6 列）

例如 WF25（Spill）：
- Spill After 1hr：col 12→13（2 列：Cosmetic + Button User）
- Spill HS After 72hr：col 18→23（6 列）

### 3.2 填充色 = 失败标记

失败判断不依赖单元格的文本值（"Fail"/"PASS"），只依赖**单元格的填充色**：

| 填充色 RGB | 含义 | 代码中标记 |
|---|---|---|
| `FFFF0000` | Spec Failure（红色） | `F` |
| `FFFFFF00` | Strife Failure（黄色，Margin） | `SF` |
| 其他/无填充 | PASS | `0F` |

**技术细节**：填充色通过 openpyxl 的 `cell.fill.fgColor.rgb` 读取。Conditional Formatting 规则被 openpyxl 丢弃，但已手动应用的直接填充色可正常读取。

### 3.3 结果格式

遵循 Test Summary 的逻辑：
- 若有 Spec Failure → `xF/nT`
- 若无 Spec 但有 Strife Failure → `xSF/nT`
- 若都没有 → `0F/nT`

**Spec 优先于 Strife**：即一个 unit 的 CP 中同时出现红色和黄色，计为 Spec。

---

## 四、"最后一个实际 CP" 判定

### 4.1 算法

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

### 4.2 示例

WF10 R1FNF unit "DQLW9J6DVH"：
```
从右向左扫描：
  Drop300 (cols 282-287): 6/6 列是 "/" → 跳过
  Drop280 (cols 276-281): 6/6 列是 "/" → 跳过
  Drop260 (cols 270-275): 6/6 列是 "/" → 跳过
  Drop240 (cols 264-269): 0/6 列是 "/"，有实际值 → ✅ 最后实际 CP
```

---

## 五、CP-to-Test 映射

### 5.1 目标

将 WF sheet 中的多个 CP 映射到 Test Summary 中的 Test1、Test2、Test3。

每个 Test 可能包含多个 CP（例如 "Random Drop 1m PB" 包含 Drop10～Drop300 共 45 个 CP）。

### 5.2 映射算法

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

### 5.3 特殊规则

| WF 系列 | 规则 | 说明 |
|---|---|---|
| WF6/7/8/9（Button Cycling）| 百分比 ≤100% → Test 非 Margin，≥120% → Test Margin | 例：BVPM-100% → Test2，BVPM-120% → Test3 |
| WF14.1–15.3（18 Sided Drop）| "2nd" 前缀 → Test Margin | 第 2 轮 Drop → Test3 |
| WF42（Battery Swap Acc）| LTOS 消失/重现 → 分界 | LTOS→非LTOS→LTOS 三段 |
| WF16.1/16.2（THC + HSD）| 首位 CP "THC" → Test1，剩余 → Test2 | THC 与 Surface 无共同词自动分界 |

---

## 六、分析主流程

```
1. 读取 Test Summary → 获取每个 WF 的 Test 名称和现有结果
2. 遍历所有 WF Sheet：
   a. 解析表头 → 获取所有 CP 的列范围
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
5. 输出 Computed Summary Excel + FA Tracker 交叉验证

---

## 七、FA Tracker 交叉验证

FA 记录通过以下字段关联到 WF 原始数据：
- `WF` → WF sheet
- `SN` → 数据行中的 S/N 列（第 5 列，E 列）
- `Config` → 数据行中的 Config 列（第 3 列，C 列）

验证逻辑：FA 记录的 SN 是否在对应 WF/Config 的 Spec 或 Strife 失败列表中出现。

---

## 八、脚本清单

| 文件 | 功能 |
|---|---|
| `generate_summary_v2.py` | 主脚本：解析原始数据、CP-to-Test 映射、生成 Excel |
| `M60_Computed_Summary.xlsx` | 输出：与 Test Summary 同格式的 computed 结果 |
| `cp_to_test_mapping.md` | 输出：每个 WF 的 Test1/2/3 ↔ CP 映射文档 |
| `analyze_v7.py` | 探索过程脚本，输出详细的 step-by-step 分析 |
| `analysis_logic.md` | 本文档之前的版本 |

---

## 九、输出文件使用指南

### Computed Summary Excel

- Sheet 名：`Computed Summary`
- 格式与原始 Test Summary 相同
- 颜色标注：红底=Spec、黄底=Strife、绿底=Pass、蓝底=进行中
- **红色粗体** = 与 TS 不一致的值
- 只有 TS 中定义了该 Test 的 WF 才会填入对应列

### CP-to-Test Mapping 文档

- 每个 WF 列出 TS 中定义的 Test 名称和归属于它的所有 CP
- 用于核对 mapping 是否正确

---

## 十、已知限制

1. **WF34（Accumulation）** 结构特殊，尚未解析
2. **WF33（UV indoor/outdoor）** 结构不同，尚未解析
3. **WF11 R2CNM** 数据块读取存在重叠 bug（应为 16T，显示 32T）
4. **Conditional Formatting 字体颜色变化**（如深红字体 `FF9C0006`）不视为填充色
5. **部分 WF（29.1-29.4）** CP 起始列为 7 而非 12，标题行结构不同

---

## 十一、数据库源表

持久化的真实源表是活跃报告版本及 SN 级事实表：

- `reports` — 报告版本元数据
- `report_wf_meta` — 每个报告的 WF 名称快照
- `report_test_names` — 每个报告的测试名称快照
- `report_cps` — 每个报告的 CP 结构快照
- `sn_cp_results` — SN 级 CP 结果事实表
- `sn_check_results` — SN 级检查项结果事实表

`wf_results` 和 `sn_progress` 在迁移期间作为兼容性/缓存表维护。
