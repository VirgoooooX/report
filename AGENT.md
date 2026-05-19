# M60 EVT REL Dashboard Agent Guide

## 项目定位

这是一个内部工程 Dashboard，用于解析 M60 EVT Reliability Daily Report 和 FA Tracker，追踪 WF、Config、SN、CP、Check Item 维度的测试进度、失败分析、排程和完成预测。

## 技术栈

- 后端：Python 3.12、Flask、SQLite WAL、openpyxl
- 前端：Vue 3、Pinia、Vite、Ant Design Vue、Chart.js
- 部署：Docker Compose、Gunicorn、GitHub Actions、GHCR

## 常用命令

```powershell
python backend/processor.py --all --rebuild
python backend/api.py
npm --prefix frontend run dev
python -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run build:check
```

## 核心架构

- `backend/processor.py` 负责从 Excel 解析报告并写入 SQLite。
- `backend/api.py` 是唯一后端 API 入口，同时在生产环境提供前端静态资源。
- `backend/db.py` 封装数据库查询、趋势和预测逻辑。
- `frontend/src/` 是 Vue 3 SPA，页面通过 Pinia 和 `useApi.js` 访问后端。
- `rawdata/` 存放原始 Daily Report 和 FA Tracker。
- `db/report.db` 是默认 SQLite 数据库。

## 数据规则

- 失败判定以 Excel 单元格填充色为准，不信任文本值。
- 红色 `FF0000` 表示 Spec Failure，黄色 `FFFF00` 表示 Strife Failure。
- `reports` 使用 `report_date + version + is_active` 管理同日期多版本，不要用 `MAX(id)` 表达“最新报告”。
- Check Item 主事实源是 `sn_check_state_history` 状态历史段；查询某日报告快照时按报告 ID 落在有效区间还原。
- 指标只能有一个计算路径。新增 API 时优先复用既有事实表和查询 helper，避免从缓存表重复计算同一指标。
- 避免 `INSERT OR REPLACE` 更新部分列；它本质是 DELETE + INSERT，容易丢元数据。优先使用 UPDATE-first。
- 所有 `DELETE FROM` 必须带明确 `WHERE`，并在 review 中单独审计。

## 前端规则

- 页面布局复用 `.main`、`.page-container`、`.page-shell`、`.page-shell-wide` 等全局布局约定。
- 颜色、边框、阴影、字体、间距优先使用 Design Token，不要在组件里散落硬编码色值。
- Ant Design Vue 主题适配优先通过 `ConfigProvider` token，不要新增大段 `:deep(.ant-*)` 覆盖。
- API 请求统一使用 `frontend/src/composables/useApi.js` 的封装，组件内不要裸写分散的 `fetch()` 错误处理。
- 数据密集页面要保持 loading、empty、error 状态完整，避免空白页面。

## 滚动条规范

- 滚动条样式必须统一，并且不能影响整体布局。
- 页面级滚动保留稳定 gutter，避免滚动条出现/消失引发内容宽度跳动。
- 新增任何 `overflow: auto`、`overflow-x: auto`、`overflow-y: auto` 时，必须同步检查滚动条宽度、轨道透明度、hover 状态、Firefox 行为、移动端滚动和深色模式颜色。
- Test Summary、Schedule Timeline、Heatmap、Query Center 表格等内部滚动容器应复用全局滚动条规范或公共工具类，不要各自写一套局部 scrollbar。
- 需要 hover 才显示滚动条时，必须保证容器尺寸不变，sticky 表头/固定列不被遮挡。

## 开发方法

- 大功能遵循 Spec -> Plan -> Execute，先明确业务语义和数据来源，再动代码。
- 数据层重构优先 TDD，新增事实表或查询 helper 时补充回归测试。
- UI 微调先在 DevTools 中调到满意，再一次性落到源码，避免用提交记录试错。
- 修改现有文件前先看当前实现和 git 状态，不要覆盖用户已有改动。

## 验证建议

- 后端改动：运行 `python -m unittest discover -s tests -v`。
- 前端逻辑改动：运行 `npm --prefix frontend test`。
- 前端构建或样式改动：运行 `npm --prefix frontend run build:check`，必要时启动 dev server 做浏览器检查。
- 数据导入逻辑改动：用 `python backend/processor.py --all --rebuild` 验证完整重建。
