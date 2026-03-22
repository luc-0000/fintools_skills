# Backtests 功能需求

## 目标

本文档用于记录这个 skill 仓库中 `backtests` 集成的目标需求行为。

核心目标有两个：

- 保持 `backtests` 展示层和上层调用方式稳定
- 让数据库后端选择与 agent 结果同步逻辑明确、可配置、可重复执行

## 总体架构

这个 skill 目前有两个主要功能，它们需要协同工作：

1. `agentclient`
2. `backtests`

### agentclient 功能

`agentclient` 负责调用远程 agent，并把原始执行结果写入：

- `.runtime/database/trading_agent.db`

这个数据库是上游 agent 结果的运行时存储。

### backtests 功能

`backtests` 负责展示回测侧的数据。

每次 `backtests` 被唤醒、初始化，或者被要求展示数据时，都必须先把：

- `.runtime/database/trading_agent.db`

里的数据同步到 `backtests` 自己数据库中的：

- `agent_trading`

这不是一次性的迁移动作，而是 `backtests` 每次被唤醒时都要执行的运行时同步行为。

## 数据库后端要求

### 配置驱动的后端选择

`backtests` 的上层业务逻辑不能硬绑定 MySQL 或 SQLite。

数据库后端必须通过 skill 根目录配置文件控制：

- `config.json`

同时，配置文件需要为未来的其他配置预留空间，不能只为数据库单独平铺。

### 配置结构要求

数据库配置必须统一收在：

- `database`

下面。

在 `database` 下，SQLite 和 MySQL 的配置必须分开存放：

- `database.backend`
- `database.common`
- `database.sqlite`
- `database.mysql`

当前选择的数据库后端由以下字段决定：

- `database.backend`

### 默认后端

默认数据库后端必须是：

- `sqlite`

### SQLite 要求

当 `database.backend = "sqlite"` 时：

- `backtests` 必须使用本地 SQLite 数据库
- 数据库文件必须放在 `.runtime/database` 下面
- 当前默认路径是 `.runtime/database/backtests.sqlite3`

### MySQL 要求

当 `database.backend = "mysql"` 时：

- `backtests` 必须通过配置切换到 MySQL
- 从 SQLite 切换到 MySQL 时，不允许改上层业务逻辑
- MySQL 所需连接信息必须全部来自 `config.json`

## Backtests 唤醒时的同步要求

每次 `backtests` 被唤醒时，在展示任何回测数据之前，都必须先执行一次同步。

这一步同步必须完成以下事情：

1. 从 `.runtime/database/trading_agent.db` 读取数据
2. 把数据转换成 `backtests` 需要的格式
3. 将转换后的结果追加写入 `backtests` 数据库的 `agent_trading` 表

这一步属于 `backtests` 的正常初始化/展示前置流程，不是人工手动维护任务。

## 数据转换规则

从 `trading_agent.db` 转换到 `backtests.agent_trading` 时，交易结果映射规则必须是：

- `buy` 映射为 `indicating`
- 其他任何结果一律映射为 `not_indicating`

这个映射发生在同步过程中，在写入 `backtests.agent_trading` 之前完成。

## 去重与“当天最后一条”规则

`trading_agent.db` 中，同一天可能会有多次运行结果。

但 `backtests.agent_trading` 的目标是每天只保留一条有效记录。

因此，同步逻辑必须满足以下规则：

- 对于 `trading_agent.db` 中同一天的重复运行结果，只取当天最后一条记录进行转换并写入 `backtests.agent_trading`

换句话说：

- 如果上游 agent 在同一天运行了多次，`backtests` 在同步时必须忽略当天较早的记录，只使用当天最后一次运行结果

## 数据归属边界

数据职责划分应该是：

- `trading_agent.db` 保存上游 agent 的原始运行结果
- `backtests.agent_trading` 保存面向回测展示的、已经归一化后的日级信号记录

因此，从 `backtests` 的视角看，`agent_trading` 是一个派生表，它的内容应该在每次 `backtests` 唤醒时，通过同步上游运行时数据库来更新。

## 当前归属策略

同步到 `agent_trading` 时，仍然需要确定这些记录属于哪一条 `rule_id`。

当前实现约定是：

- 将 `trading_agent.db` 同步结果归属到 `backtests` 中的 `remote_agent` 规则
- 如果当前只有一条 `remote_agent` 规则，则直接写入该规则
- 如果当前存在多条 `remote_agent` 规则，则默认使用 `id` 最小的那一条，并记录告警日志

这个策略保证当前 skill 可以直接运行，同时不影响后续继续把归属逻辑配置化。

## 目标实现流程

目标稳定行为应该是：

1. 远程 agent 通过 `agentclient` 运行
2. 原始结果写入 `trading_agent.db`
3. `backtests` 被唤醒
4. `backtests` 从 `trading_agent.db` 执行同步
5. 同一天重复结果按“当天最后一条”规则折叠
6. `buy` 映射为 `indicating`
7. 其他结果映射为 `not_indicating`
8. 归一化后的记录追加写入 `backtests.agent_trading`
9. `backtests` 基于自己的数据库进行展示

## 验收要求

只有当以下条件全部满足时，这个需求才算完成：

- `backtests` 的数据库后端选择完全由配置驱动
- 默认后端是 SQLite
- SQLite 和 MySQL 配置在 `config.json` 的 `database` 下分开存放
- 切换到 MySQL 时只需要改配置，不需要改业务代码
- `backtests` 在每次唤醒/初始化/展示前都会执行 `trading_agent.db` 同步
- 同步结果写入 `backtests.agent_trading`
- `buy -> indicating` 的转换规则被严格执行
- 非 `buy` 结果统一映射为 `not_indicating`
- 对于同一天多次运行，只导入当天最后一条记录进入 `agent_trading`
