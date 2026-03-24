# Replication Guide

## Goal

Recreate the full skill behavior without access to the original implementation.

## Source

- Source: SKILL.md
- Source: scripts/discover_public_site.py
- Source: scripts/site_entry.py
- Source: scripts/run_agent_client.py
- Source: scripts/trading_run_store.py
- Source: config.json
- Source: backtests/README.md
- Source: backtests/backend/docs/specs/SPEC_INDEX.md
- Source: backtests/frontend/docs/specs/SPEC_INDEX.md
- Source: tests/test_run_agent_client.py
- Source: tests/test_site_entry.py
- Source: tests/test_backtests_runtime_readiness.py
- Source: tests/test_backtests_skill_agent_adapter.py
- Source: tests/test_backtests_trading_agent_sync.py

## Minimal Reimplementation Units

### Unit A: Public Discovery Client

You must implement:

- public discovery fetch from `/api/v1/public/info`
- subject-specific URL resolution
- URL normalization and rewriting
- list/detail read-only responses for agents, skills, and stocks

### Unit B: Skill Entry Shell

You must implement commands equivalent to:

- `resources`
- `agents`
- `skills`
- `stocks`
- `prepare-agent`
- `run-agent`

Required behaviors:

- resolve agents by id, exact name, or unique partial name
- shape outputs as machine-readable JSON
- delegate actual execution to the canonical runner

### Unit C: Agent Runner

You must implement:

- copied-skill layout validation
- runtime bootstrap under `.runtime/env`
- parent and child run directory creation
- token resolution and caching
- streaming/polling dispatch matrix
- `summary.json` and `run.log`
- trading result persistence into `trading_agent_runs.db`

### Unit D: Trading Run Store

You must implement:

- SQLite schema creation
- action normalization
- report/result parsing helpers
- unique run id generation
- insert path for normalized trading decisions

### Unit E: Backtests Product

You must implement:

- backend API and database model for pools, rules, stocks, simulators, agent trading
- frontend UI for pools, rules, simulators, and live run logs
- readiness endpoint that prepares token cache and both runtime databases
- adapter that routes UI-triggered remote runs through the canonical agent runner
- SSE log streaming using execution ids

### Unit F: Synchronization Layer

You must implement:

- read path from `trading_agent_runs.db`
- enrichment from run summaries
- daily-latest signal selection
- remote-agent rule auto-creation/backfill
- upsert into backtests `agent_trading`

## Replication Acceptance Checklist

- Discovery works without local runtime state.
- `prepare-agent` can create or find a backtests rule from a discovered public agent.
- `run-agent` can execute a remote agent through a copied skill directory.
- A missing `.runtime/` directory is created automatically.
- A missing `.runtime/database/trading_agent_runs.db` is created automatically.
- A missing `.runtime/database/backtests.sqlite3` is created automatically.
- An explicit or environment token can be persisted into `.runtime/runs/.fintools_access_token`.
- Backtests UI can list pools from the bootstrapped main database.
- Backtests UI can start a run and open a log page with `execution_id`.
- `agent_trading` can be repopulated from `trading_agent_runs.db`.

## Known Replication Risks

- Remote A2A behavior depends on external services and real tokens.
- Public discovery endpoints may evolve independently of this local skill.
- Frontend UI/UX specs in `backtests/frontend/docs/specs/` intentionally exclude service and domain semantics; use them together with this top-level bundle.
- Backend sub-specs document subsystem internals, but the repository-level coupling between wrapper runtime and backtests runtime is captured mainly in this top-level bundle.

## Verification Path

Use this directory together with existing automated tests:

- wrapper and downloader:
  - `tests/test_run_agent_client.py`
  - `tests/test_download_skill.py`
- skill entry and readiness:
  - `tests/test_site_entry.py`
  - `tests/test_backtests_runtime_readiness.py`
- backtests adapter and synchronization:
  - `tests/test_backtests_skill_agent_adapter.py`
  - `tests/test_backtests_trading_agent_sync.py`
  - `tests/test_backtests_workflow_smoke.py`

If a reimplementation cannot satisfy those behaviors, this spec bundle is incomplete or the implementation diverged.
