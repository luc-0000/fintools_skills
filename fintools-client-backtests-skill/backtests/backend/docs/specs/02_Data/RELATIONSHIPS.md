# Data Relationships Spec

## Source Anchors

- Source: db/models.py
- Source: db/sqlite/bootstrap.py
- Source: end_points/common/utils/trading_agent_sync.py
- Source: end_points/get_rule/operations/remote_agent_rule_utils.py
- Source: end_points/get_rule/operations/agent_trading_store.py

## Core Relational Graph

### Stock Membership

- `pool.id -> pool_stock.pool_id`
- `stock.code -> pool_stock.stock_code` in normalized form

Meaning:

- pools are named stock collections
- `pool_stock` is the true membership table
- `pool.stocks` is a denormalized count/cache field that code keeps synchronized

### Rule Scope

- `rule.id -> rule_pool.rule_id`
- `pool.id -> rule_pool.pool_id`

Meaning:

- rules do not directly own stocks
- stock scope is inferred through the pool memberships attached to the rule

### Rule Signal State

- `rule.id -> agent_trading.rule_id`
- unique logical key: `(rule_id, stock, trading_date)`

Meaning:

- `agent_trading` is the rule-specific normalized signal ledger used by simulator replay
- multiple rule runs on the same day collapse to the latest normalized row for that key

### Simulator Ownership

- `rule.id -> simulator.rule_id`
- `simulator.id -> simulator_trading.sim_id`

Meaning:

- a simulator belongs to one rule
- `simulator_trading` is a child event log for one replay instance

### Runtime-Only Source Database

Outside the main backtests DB, the backend also depends on:

- `.runtime/database/trading_agent_runs.db`

That source database has logical links into the main DB through synchronization:

- `trading_agent_runs.agent_id` or inferred `agent_url`
- backfilled into `rule.agent_id` and `rule.info`
- then normalized into `agent_trading`

## Derived-State Relationships

### `trading_agent_runs` -> `rule`

`trading_agent_sync.py` may create or backfill a `remote_agent` rule when a source run references an agent not yet present in the main backtests DB.

This is not a foreign-key relationship enforced by SQLite.
It is a synchronization relationship enforced by application logic.

### `trading_agent_runs` -> `agent_trading`

This is the critical source-of-truth relationship:

1. local runner writes canonical decisions into `trading_agent_runs.db`
2. sync converts actions into backtests trading types
3. sync upserts rows into `agent_trading`

The direction must not be reversed.

## Cardinality Rules

- one pool can contain many stocks
- one stock can belong to many pools
- one rule can attach to many pools
- one pool can attach to many rules
- one rule can have many `agent_trading` rows across stocks and days
- one rule can have many simulators over time
- one simulator can have many `simulator_trading` events

## Implicit Constraints

### Remote Agent Identity

For `rule.type == remote_agent`:

- `rule.agent_id` is intended to be unique when present
- `rule.info` carries the remote A2A URL

### Simulator Config Singleton

`simulator_config` is effectively singleton state.
Code convention expects row `id == 1`.

### Run Summary Enrichment

Run summary files under `.runtime/runs/*/summary.json` are secondary enrichment inputs.
They are used to backfill:

- `agent_id`
- `agent_name`
- `agent_description`
- `agent_url`

for synchronization logic when those values are missing from raw source DB rows.
