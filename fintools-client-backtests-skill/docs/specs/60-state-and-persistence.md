# State And Persistence

## Source

- Source: config.json
- Source: scripts/run_agent_client.py
- Source: scripts/trading_run_store.py
- Source: database/trading_agent_database.py
- Source: backtests/backend/db/sqlite/bootstrap.py
- Source: backtests/backend/end_points/common/utils/runtime_readiness.py
- Source: backtests/backend/end_points/common/utils/trading_agent_sync.py
- Source: backtests/backend/end_points/init_global.py

## Persistent State Inventory

### 1. Repository-Local Runtime Root

- Path: `.runtime/`
- Owner: repository-local runtime preparation
- Created by:
  - `scripts/run_agent_client.py`
  - `scripts/trading_run_store.py`
  - `backtests` readiness/bootstrap logic

### 2. Local Python Environment

- Path: `.runtime/env/`
- Owner: `scripts/run_agent_client.py`
- Purpose:
  - stable isolated Python runtime for copied-skill execution
- Mutation rules:
  - create if missing
  - update when `requirements.txt` fingerprint changes

### 3. Install State Metadata

- Path: `.runtime/install-state.json`
- Owner: `scripts/run_agent_client.py`
- Purpose:
  - cache installation fingerprint and runtime bootstrap metadata

### 4. Parent Runs Directory

- Path: `.runtime/runs/` by default
- Owner: `scripts/run_agent_client.py`
- Contents:
  - token cache file
  - child run directories
  - run logs and summaries

### 5. Token Cache

- Path: `.runtime/runs/.fintools_access_token`
- Writers:
  - `scripts/run_agent_client.py`
  - `backtests/backend/end_points/common/utils/runtime_readiness.py`
- Readers:
  - `scripts/run_agent_client.py`
  - `backtests` readiness/execution adapter

### 6. Trading Run Source Database

- Path: `.runtime/database/trading_agent_runs.db`
- Owner: `scripts/trading_run_store.py`
- Role:
  - source of truth for normalized local trading-agent decisions

### 7. Backtests Product Database

- Path by default: `.runtime/database/backtests.sqlite3`
- Owner:
  - `config.json`
  - `backtests/backend/end_points/init_global.py`
  - `backtests/backend/db/sqlite/bootstrap.py`
- Role:
  - main product database for pools, rules, stocks, simulator records, and derived `agent_trading`

## Database Separation Rules

### `trading_agent_runs.db`

This database stores normalized execution outputs from the local runner.

Key columns:

- `run_id`
- `stock_code`
- `action`
- `created_at`
- `updated_at`
- `raw_result`
- `mode`
- `agent_id`
- `agent_name`

Rules:

- trading decisions must be one of `buy`, `sell`, `hold`
- stock codes are normalized to the base code without suffix
- every row must have unique `run_id`

### `backtests.sqlite3`

This database stores product-facing entities such as:

- `pool`
- `pool_stock`
- `rule`
- `rule_pool`
- `agent_trading`
- `simulator`
- `simulator_trading`
- `simulator_config`

Rules:

- it may be bootstrapped from checked-in JSON seed exports
- `agent_trading` is not the first-write target of remote-agent execution
- remote-agent rule records may be auto-created during synchronization

## Run Directory Contract

Each agent execution gets a unique child run directory under the parent runs directory.

Expected artifacts include:

- `summary.json`
- `run.log`
- `downloaded_reports/`

For public skill downloads, a run directory may instead contain:

- `downloaded_skills/`
- `summary.json`
- `run.log`

## Derived-State Contract

### What Is Canonical

- canonical raw trading result store:
  - `.runtime/database/trading_agent_runs.db`
- canonical product view store:
  - `.runtime/database/backtests.sqlite3`

### What Is Derived

- `backtests.agent_trading`
- auto-created backtests `remote_agent` rule records inferred from source runs
- agent id/name backfills synthesized from run summaries

### Replication Rule

A clean-room implementation must preserve this direction:

1. execute and normalize local run output
2. write into `trading_agent_runs.db`
3. synchronize into backtests derived state

It must not reverse that direction by treating `agent_trading` as the original run ledger.

## State That Is Safe To Delete

These are runtime byproducts and are not repository source artifacts:

- child run directories under `.runtime/runs/`
- `run.log`
- downloaded reports
- downloaded skill archives
- copied-install runtimes in other directories

## State That Must Be Reconstructable

A replication is incomplete unless it can reconstruct all of the following:

- `.runtime/env`
- `.runtime/runs/.fintools_access_token`
- `.runtime/database/trading_agent_runs.db`
- `.runtime/database/backtests.sqlite3`
- unique run directories with `summary.json` and `run.log`
