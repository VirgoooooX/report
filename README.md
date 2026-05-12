# M60 EVT REL Dashboard

工程验证测试（EVT）报告仪表盘，用于可视化追踪 M60 项目的每日测试进度、故障分析和完成预测。

---

## 架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ backend/processor.py │─▶│  SQLite 事实表  │◀─│ backend/api.py │
│    (数据导入)        │  │ (db/report.db)│  │  (Flask API)  │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                          ┌──────▼───────┐
                                          │  frontend/    │
                                          │  Vue 3 + Vite │
                                          └──────────────┘
```

- **backend/processor.py** — 将 Excel Daily Report 导入 SQLite 事实表
- **backend/api.py** — Flask REST API，同时提供前端静态文件服务
- **backend/db.py** — SQLite 封装层，支持快照、趋势和预测
- **frontend/** — Vue 3 SPA，使用 Ant Design Vue + Chart.js

---

## 目录结构

| 路径 | 说明 |
|------|------|
| `backend/` | Flask API、导入器、数据库封装和 Excel 解析模块 |
| `tests/` | Python 后端测试 |
| `tools/` | 一次性校验/排查脚本 |
| `frontend/` | Vue 3 + Vite 前端 SPA |
| `rawdata/` | 原始 Excel 文件目录，支持递归扫描 |
| `rawdata/uploads/YYYY-MM-DD/` | 前端上传的 Daily Report / FA Tracker 原始文件 |
| `db/` | SQLite 数据库目录，默认文件为 `db/report.db` |
| `output/` | 导出报告与中间产物 |
| `templates/` | Flask 遗留模板 |
| `static/` | Flask 遗留静态资源 |

---

## 本地设置

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm --prefix frontend ci
```

依赖项会安装在独立的虚拟环境中。前端使用 `npm ci` 确保与 lockfile 一致的依赖版本。

---

## 数据导入

将 Daily Report Excel 文件放入 `rawdata/` 目录，然后运行：

```powershell
python backend/processor.py --all --rebuild
```

处理所有报告并重建完整 SQLite 数据库。增量更新请使用 `python backend/processor.py`（不带参数）。

前端上传的文件会保存到 `rawdata/uploads/YYYY-MM-DD/`，批量导入会递归扫描 `rawdata/`，同一报告日期会优先使用修改时间最新的文件。

---

## 运行后端和前端

打开两个终端：

**终端 1 — 后端 API**（默认监听 `http://localhost:5050`）：

```powershell
python backend/api.py
```

**终端 2 — 前端开发服务器**（默认监听 `http://localhost:5173`，自动代理 API 请求）：

```powershell
npm --prefix frontend run dev
```

前端开发服务器会代理 `/api/*` 和 `/db/*` 请求到后端。生产构建则由后端直接提供前端静态文件。

---

## 测试

**Python 后端测试（unittest）：**

```powershell
python -m unittest discover -s tests -v
```

**前端基本验证：**

```powershell
npm --prefix frontend test
```

**前端构建验证：**

```powershell
npm --prefix frontend run build:check
```

---

## Docker Compose

项目支持通过 Docker Compose 一键部署。确保已安装 Docker Desktop，然后执行：

```powershell
docker compose build
docker compose up -d
```

查看仪表盘日志：

```powershell
docker compose logs -f dashboard
```

停止并移除容器：

```powershell
docker compose down
```

Compose 会把本机 `rawdata/` 挂载到容器 `/app/rawdata`，把本机 `db/` 挂载到容器 `/app/db`，数据库默认保存在 `db/report.db`。

---

## GitHub Actions

通过 `.github/workflows/` 下的 workflow 文件配置 CI/CD，支持：

- 每次推送自动运行 Python 单元测试和前端构建检查
- 数据导入脚本的回归验证
- Docker 镜像构建与推送

> **注意：** 需要先在仓库中创建 `.github/workflows/` 及对应的 workflow 定义文件。

---

## 版本化推送脚本

`scripts/push.ps1` 用于将本地验证通过的数据与代码一并推送到远端，典型流程：

1. 运行 `python backend/processor.py --all --rebuild` 确保数据最新
2. 运行全部测试确认无回归
3. 提交代码并推送

---

## 故障排除

| 问题 | 原因与解决 |
|------|-----------|
| `pip install` 失败 | 确认已激活虚拟环境（`.\.venv\Scripts\Activate.ps1`） |
| `npm ci` 报错 | 检查 Node.js 版本 ≥ 18，删除 `node_modules` 后重试 |
| `backend/processor.py` 找不到 Excel 文件 | 确认 `rawdata/` 目录下存在 `.xlsx` 文件 |
| 后端端口被占用 | 设置环境变量 `FLASK_RUN_PORT=5060` 或修改 `backend/api.py` |
| 前端无法代理 API | 确认后端已在 `localhost:5050` 运行 |
| `db/report.db` 损坏 | 删除后重新运行 `python backend/processor.py --all --rebuild` |
