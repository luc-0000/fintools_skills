# Execution State Machines

## Source Anchors

- Source: end_points/get_rule/operations/execution_manager.py
- Source: end_points/get_rule/get_rule_routes.py
- Source: end_points/get_rule/operations/agent_streaming.py
- Source: end_points/get_rule/operations/skill_agent_adapter.py
- Source: end_points/common/utils/trading_agent_sync.py

## 1. Rule Execution Lifecycle

### States

- `pending`
- `running`
- `completed`
- `failed`

### Transition Rules

1. `create_execution(...)` creates an in-memory execution in `pending`
2. `execute_and_capture(...)` moves it to `running`
3. successful exhaustion of the stream function moves it to `completed`
4. any raised exception moves it to `failed`

### Log Semantics

Each execution accumulates timestamped log objects in memory.

Typical emitted types include:

- `start`
- `info`
- `stock_start`
- `stock_complete`
- `stock_error`
- `streaming_text`
- `complete`
- `error`
- final SSE-only `stream_complete`

### Lifetime Constraint

Execution state is memory-resident only.
It is not persisted across backend process restarts.

## 2. SSE Viewer State Machine

### States

- `idle`
- `connecting`
- `streaming`
- `completed`
- `errored`

### Transition Rules

1. log page loads with `execution_id`
2. EventSource connects to the appropriate stream URL
3. incoming messages append visible log lines and update counters/current stock
4. `complete` event or end-of-stream transitions UI to completed
5. EventSource error transitions UI to errored

### Guard Condition

If the page lacks `execution_id`, it does not even attempt streaming and instead surfaces a frontend error.

## 3. Runtime Readiness State Machine

### States

- `uninitialized`
- `token_missing`
- `runtime_ready_no_token`
- `ready`

### Inputs

- explicit token payload
- cached token file
- `FINTOOLS_ACCESS_TOKEN`
- filesystem state for `.runtime/database/*`

### Transition Rules

1. missing `.runtime/` directories are created on first readiness call
2. missing `trading_agent_runs.db` is created during readiness
3. missing `backtests.sqlite3` is bootstrapped during readiness
4. if token is absent and `require_token=false`, state is `runtime_ready_no_token`
5. if token is absent and `require_token=true`, transition is blocked with error
6. if token is found or persisted, state is `ready`

## 4. Trading Signal Synchronization State Machine

### States

- `source_missing`
- `source_loaded`
- `rules_backfilled`
- `derived_rows_upserted`

### Transition Rules

1. if source DB is absent, sync is skipped
2. source schema is backfilled if needed
3. latest daily signals are loaded
4. remote-agent rules are ensured/backfilled
5. normalized rows are upserted into `agent_trading`

### Invariant

The sync machine must never treat `agent_trading` as the authoritative upstream source.

## 5. Simulator Replay State Machine

### States

- `created`
- `running`
- `partially_traded`
- `completed`

### Transition Rules

1. simulator row exists with initial capital state
2. replay loads `agent_trading` signals for the referenced rule
3. each stock enters buy/sell/fail-to-buy/fail-to-sell transitions based on market history
4. `simulator_trading` rows and HTML log lines are emitted as replay side effects
5. aggregate metrics and serialized `earning_info` are written back when replay completes
