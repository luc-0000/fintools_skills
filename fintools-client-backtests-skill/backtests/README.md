# Backtests

`backtests/` 是这个 skill 里的交易 agent 回测系统。

它和仓库里的远程 agent client 配合使用，解决两件事：

- 管理 `remote_agent` rule、pool、stocks、simulator
- 让用户通过 UI 或命令/API 运行交易 agent 并查看回测结果

## 你可以用它做什么

常见任务包括：

- 给某个 trading agent 建立或检查对应的 rule
- 先列出当前有哪些 pool，再用语言指定把某个 pool 绑定给某个 agent
- 给 agent 绑定一个或多个股票池
- 为股票池增删股票
- 运行某个 agent 的今日股票池
- 为某个 rule 创建 simulator 并执行回测
- 在前端页面查看规则、股票池、交易记录和回测结果

## 目录

```text
backtests/
├── backend/   # FastAPI 后端与数据库初始化脚本
├── frontend/  # React 前端
└── README.md
```

## 关键约定

- 这里只支持 `remote_agent` 规则，不再面向本地 agent。
- 默认数据库后端由根目录 [`config.json`](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/config.json) 控制。
- 默认 SQLite 文件在 `.runtime/database/backtests.sqlite3`。
- `backtests` 启动时会按仓库配置初始化数据库连接；数据库种子数据默认来自 `backtests/backend/backups/.../json_export`。
- 交易 agent 的执行结果会进入 `agent_trading`，回测执行结果会进入 `simulator` / `simulator_trading`。

## 启动前提

- Python 3.11+ 或可用的项目 Python 运行环境
- Node.js 16+
- 可访问的远程 trading agent
- 可用的访问 token

如果你是第一次使用整个 skill，建议先确认仓库级运行环境已经准备好，包括 `.runtime/env` 和 access token。

对 access token，当前最简单可行的顺序是：

- 显式传入
- 已缓存的 token 文件
- 环境变量 `FINTOOLS_ACCESS_TOKEN`

如果第一次是通过显式传入或环境变量拿到真实 token，系统应把它写入：

- `.runtime/runs/.fintools_access_token`

后续优先复用这个缓存，不再重复向用户索要。

Rules 页面发起运行前，后端现在会先做一次 runtime readiness 检查：

- 自动确保 `.runtime/runs/` 存在
- 自动确保 `.runtime/database/trading_agent_runs.db` 和 schema 已初始化
- 如果没有可用 token，则阻止运行并明确提示 token 文件位置

## 快速开始

### 1. 初始化数据库

```bash
cd backtests/backend
./scripts/init_db.sh
```

默认会创建：

- `.runtime/database/backtests.sqlite3`

首次运行 agent 前的 readiness 检查还会补齐：

- `.runtime/database/trading_agent_runs.db`

### 2. 启动后端

```bash
cd backtests/backend
pip install -r requirements.txt
python manage.py
```

或：

```bash
cd backtests/backend
uv sync
uv run python manage.py
```

默认后端地址：

- `http://127.0.0.1:8888`

健康检查：

- `GET /health`
- `GET /docs`

### 3. 启动前端

```bash
cd backtests/frontend
npm install
npm run dev -- --host 127.0.0.1
```

默认前端地址：

- `http://127.0.0.1:8000`

## 推荐使用流程

### 流程 A: 已经知道 agent，要开始跑回测

1. 启动后端和前端。
2. 确认目标 agent 是否已经有对应 rule。
3. 如果没有，创建一个 `remote_agent` rule。
4. 确认这个 rule 是否已经绑定 pool。
5. 如果还没绑定 pool，就新建 pool 并加入股票。
6. 把 pool 绑定到 rule。
7. 在 Rules 页面运行 agent。
8. 在 Simulators 页面创建 simulator 并执行回测。

如果是第一次让某个 agent 开始跑，推荐把流程拆成两步：

1. 先确保这个 agent 已经进入 `remote_agent` rule。
2. 再问用户这次是：
   - 直接给一个股票代码先跑
   - 还是先打开 UI 给这个 agent 配 pool

如果用户选择 UI，给用户的说明保持最短即可：

1. 打开 `Pools` 页面，新建一个 pool。
2. 进入这个 pool，把股票代码加进去。
3. 打开 `Rules` 页面，找到对应 agent，把这个 pool assign 给它。
4. 回到 `Rules` 页面，整池用 `Run Today`，单股用 `Run`。

### 流程 B: agent 已经存在且已有 pool

1. 打开 Rules 页面。
2. 找到对应的 `remote_agent` rule。
3. 直接运行这个 rule 关联 pool 中的全部股票。
4. 到 Simulators 页面查看或创建回测。

## UI 里主要看哪里

- `Rules` 页面：查看 rule、绑定 pool、执行 agent、看 agent trading
- `Pools` 页面：创建股票池、查看股票池、为股票池加减股票
- `Simulators` 页面：创建回测、运行回测、查看回测交易明细
- `AgentLog` 页面：查看 agent 执行日志

## 常用后端对象

- `rule`：一个 agent 规则，当前重点是 `remote_agent`
- `pool`：股票池
- `pool_stock`：股票和股票池的关系
- `rule_pool`：rule 和 pool 的绑定关系
- `agent_trading`：agent 运行后产生的日级交易信号
- `simulator`：一次回测任务
- `simulator_trading`：回测过程中生成的交易明细

## API 入口

后端 FastAPI 文档：

- `http://127.0.0.1:8888/docs`

常见接口前缀：

- `/api/v1/get_rule`
- `/api/v1/get_pool`
- `/api/v1/get_stock`
- `/api/v1/get_simulator`

和语言绑定 pool 最相关的接口有：

- `POST /api/v1/get_rule/rule/ensure_remote_agent`
- `GET /api/v1/get_rule/rule/agent/{agent_id}/pools`
- `POST /api/v1/get_rule/rule/agent/{agent_id}/assign_pool`

## 常见问题

### 页面打开了，但没有数据

优先检查后端：

```bash
curl -sS http://127.0.0.1:8888/health
```

如果后端不健康，先修后端，再看前端。

### 找不到数据库文件

先检查根目录 [`config.json`](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/config.json) 的 `database.backend` 和 `database.sqlite.path`。

默认 SQLite 路径是：

- `.runtime/database/backtests.sqlite3`

### 想直接改数据库表可以吗

不建议。普通使用请优先走 UI 或后端 API。

尤其不要手工伪造：

- `agent_trading`
- `simulator`
- `simulator_trading`
- 聚合收益结果表

这些表里有一部分数据应由 agent 执行或 simulator 运行产生。

## 给 LLM/自动化操作的补充

如果你是让 LLM 或脚本来操作 backtests，不要只看这个 README。请同时遵循：

- [`backtests/LLM_OPERATIONS.md`](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/backtests/LLM_OPERATIONS.md)

那份文档定义了更严格的可改边界、推荐接口、禁止操作和执行顺序。
