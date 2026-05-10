# M60 EVT REL Dashboard

工程验证测试（EVT）报告仪表盘，用于可视化追踪 M60 项目的每日测试进度、故障分析和完成预测。

---

## 架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  processor.py │────▶│  SQLite 事实表  │◀────│    api.py     │
│  (数据导入)   │     │  (report.db)  │     │  (Flask API)  │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                          ┌──────▼───────┐
                                          │  frontend/    │
                                          │  Vue 3 + Vite │
                                          └──────────────┘
```

- **processor.py** — 将 Excel Daily Report 导入 SQLite 事实表
- **api.py** — Flask REST API，同时提供前端静态文件服务
- **db.py** — SQLite 封装层，支持快照、趋势和预测
- **frontend/** — Vue 3 SPA，使用 Ant Design Vue + Chart.js

---

## 目录结构

| 路径 | 说明 |
|------|------|
| `api.py` | Flask API 服务入口 |
| `processor.py` | Excel 数据批量导入脚本 |
| `db.py` | SQLite 数据库模块 |
| `engine.py` | Excel 解析与分析引擎 |
| `fa_analysis.py` | 故障分析模块 |
| `fa_matcher.py` | FA Tracker 匹配模块 |
| `frontend/` | Vue 3 + Vite 前端 SPA |
| `data/` | 待导入的 Daily Report Excel 文件 |
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

将 Daily Report Excel 文件放入 `data/` 目录，然后运行：

```powershell
python processor.py --all --rebuild
```

处理所有报告并重建完整 SQLite 数据库。增量更新请使用 `python processor.py`（不带参数）。

---

## 运行后端和前端

打开两个终端：

**终端 1 — 后端 API**（默认监听 `http://localhost:5050`）：

```powershell
python api.py
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
python -m unittest discover -v
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

> **注意：** 需要先创建 `Dockerfile` 和 `docker-compose.yml`（参考项目模板或根据架构自行编写）。

---

## GitHub Actions

通过 `.github/workflows/` 下的 workflow 文件配置 CI/CD，支持：

- 每次推送自动运行 Python 单元测试和前端构建检查
- 数据导入脚本的回归验证
- Docker 镜像构建与推送

> **注意：** 需要先在仓库中创建 `.github/workflows/` 及对应的 workflow 定义文件。

---

## 版本化推送脚本

`push_version.ps1`（或等效脚本）用于将本地验证通过的数据与代码一并推送到远端，典型流程：

1. 运行 `python processor.py --all --rebuild` 确保数据最新
2. 运行全部测试确认无回归
3. 提交代码并推送

> **注意：** 该脚本需在项目根目录创建，可根据团队工作流自定义。

---

## 故障排除

| 问题 | 原因与解决 |
|------|-----------|
| `pip install` 失败 | 确认已激活虚拟环境（`.\.venv\Scripts\Activate.ps1`） |
| `npm ci` 报错 | 检查 Node.js 版本 ≥ 18，删除 `node_modules` 后重试 |
| `processor.py` 找不到 Excel 文件 | 确认 `data/` 目录下存在 `.xlsx` 文件 |
| 后端端口被占用 | 设置环境变量 `FLASK_RUN_PORT=5060` 或修改 `api.py` |
| 前端无法代理 API | 确认后端已在 `localhost:5050` 运行 |
| `report.db` 损坏 | 删除后重新运行 `python processor.py --all --rebuild` |
