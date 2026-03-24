# System Composition

## Identity

This repository is a bundled skill that combines four implementation surfaces into one runnable unit:

1. a public-site discovery wrapper
2. a local isolated agent-runner wrapper
3. a persistent local runtime and results store
4. a backtests product composed of FastAPI backend plus React frontend

## Source

- Source: SKILL.md
- Source: scripts/discover_public_site.py
- Source: scripts/site_entry.py
- Source: scripts/run_agent_client.py
- Source: scripts/trading_run_store.py
- Source: database/trading_agent_database.py
- Source: config.json
- Source: backtests/backend/end_points/main.py
- Source: backtests/backend/end_points/init_global.py
- Source: backtests/backend/end_points/common/utils/runtime_readiness.py
- Source: backtests/backend/end_points/common/utils/trading_agent_sync.py
- Source: backtests/backend/end_points/get_rule/operations/skill_agent_adapter.py
- Source: backtests/frontend/src/router/index.tsx

## Top-Level Modules

### Public Discovery Layer

- `scripts/discover_public_site.py` is the only generic public-site discovery client.
- It discovers public resources from `/api/v1/public/info`.
- It rewrites relative and service URLs so all downstream callers can treat the discovered API catalog as absolute URLs.
- It is read-only: no runtime mutation or local persistence happens here.

### Skill Entry Layer

- `scripts/site_entry.py` is the human/agent-facing command shell for this skill.
- It exposes:
  - `resources`
  - `agents`
  - `skills`
  - `stocks`
  - `prepare-agent`
  - `run-agent`
- `prepare-agent` is the bridge from public discovery into the local backtests system.
- `run-agent` is the bridge from public discovery into `scripts/run_agent_client.py`.

### Agent Execution Layer

- `scripts/run_agent_client.py` is the canonical local execution wrapper.
- It is responsible for:
  - validating copied skill completeness
  - choosing or creating `.runtime/env`
  - resolving access token
  - creating run directories
  - dispatching to `agents_client/streaming/*` or `agents_client/db_polling/*`
  - writing `summary.json`
  - mirroring `run.log`
  - persisting trading results into `trading_agent_runs.db`

### Local Persistence Layer

- `scripts/trading_run_store.py` owns the schema and write path for `.runtime/database/trading_agent_runs.db`.
- `database/trading_agent_database.py` reads that same source-of-truth database for reporting and tests.
- `config.json` controls the main backtests database backend, defaulting to `.runtime/database/backtests.sqlite3`.

### Backtests Product Layer

- `backtests/backend` is a FastAPI application with SQLite/MySQL-configurable persistence.
- `backtests/frontend` is a Vite + React application proxying `/api` to the backend.
- The backend does not implement an independent remote-agent runtime.
  It adapts into the canonical skill runner via `skill_agent_adapter.py`.

## Canonical Boundaries

### Single Source of Truth Boundaries

- Public discovery:
  - canonical implementation is `scripts/discover_public_site.py`
- Local remote-agent execution:
  - canonical implementation is `scripts/run_agent_client.py`
- Trading run persistence:
  - canonical implementation is `scripts/trading_run_store.py`
- Backtests runtime readiness:
  - canonical implementation is `backtests/backend/end_points/common/utils/runtime_readiness.py`
- Derived backtests agent trading state:
  - canonical sync path is `backtests/backend/end_points/common/utils/trading_agent_sync.py`

### Protected Upstream Boundary

- `agents_client/` is treated as the upstream execution engine.
- Wrapper and backtests code should adapt into it instead of forking business logic into multiple parallel implementations.

## Composition Rules

### Why `site_entry.py` Exists

`site_entry.py` prevents callers from having to manually compose:

- public-site discovery
- agent identity resolution
- backtests rule creation
- runtime preparation
- CLI argument construction

Without it, callers would need to know multiple internal APIs and local filesystem rules.

### Why `runtime_readiness.py` Exists

The backtests UI and backtests run endpoints both depend on shared runtime state:

- `.runtime/runs/`
- `.runtime/runs/.fintools_access_token`
- `.runtime/database/trading_agent_runs.db`
- `.runtime/database/backtests.sqlite3`

`runtime_readiness.py` centralizes preparation of those dependencies so UI-entry preparation and execution-entry preparation do not drift.

### Why `trading_agent_sync.py` Exists

The backtests database contains derived state used for listing signals and simulator replay.

That derived state is not the first-write target of real remote-agent runs.
Instead:

1. raw local run output is written into `trading_agent_runs.db`
2. `trading_agent_sync.py` loads and normalizes those rows
3. the backtests DB receives synchronized `agent_trading` rows and remote-agent rule backfills

## External Dependencies

### Remote HTTP Dependencies

- Public FinTools discovery and list endpoints
- Public skill download endpoint
- Remote A2A agent endpoints resolved from discovered agent metadata

### Local Runtime Dependencies

- Python 3.10+ or conda for runtime creation
- Node/npm for the frontend dev server
- SQLite by default for both runtime databases

## Non-Standard Elements Worth Calling Out

### Skill-Copy Portability

The repository is explicitly designed to keep working after being copied into another directory as a bundled skill, as long as required bundled files remain present.

That portability requirement explains why:

- most path resolution is relative to `SKILL_ROOT`
- runtime state lives under repository-local `.runtime/`
- wrapper validation fails early if bundled assets are missing

### Split Spec Topology

This repository already contains subsystem specs inside:

- `backtests/backend/docs/specs/`
- `backtests/frontend/docs/specs/`

This top-level bundle does not replace those.
It documents the repository-level orchestration that those subsystem bundles do not cover.
