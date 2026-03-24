# Execution Workflows

## Source

- Source: scripts/discover_public_site.py
- Source: scripts/site_entry.py
- Source: scripts/run_agent_client.py
- Source: backtests/backend/end_points/get_rule/get_rule_routes.py
- Source: backtests/backend/end_points/get_rule/operations/skill_agent_adapter.py
- Source: backtests/backend/end_points/get_rule/operations/agent_streaming.py
- Source: backtests/backend/end_points/get_rule/operations/execution_manager.py
- Source: backtests/frontend/src/pages/Rules/components/RuleList.tsx
- Source: backtests/frontend/src/pages/AgentLog/index.tsx

## Workflow 1: Public Resource Discovery

### Purpose

Provide a stable entrypoint for listing public FinTools resources without binding callers to hard-coded endpoint URLs.

### Steps

1. `discover_public_site.py` validates that `--site-url` is absolute HTTP(S).
2. It fetches `/api/v1/public/info`.
3. It rewrites any relative or service-scoped URLs into absolute URLs under the requested site origin.
4. For non-`resources` subjects, it resolves the concrete endpoint from the discovery document.
5. It performs the final GET and returns normalized JSON.

### Outputs

- discovery document for `info`/`resources`
- list/detail payloads for agents, skills, stocks, candles, news, user, thoughts

### Failure Modes

- invalid `site_url`
- missing required selector args such as `repo_id`, `ticker`, or `author`
- HTTP/URL errors from the public site

## Workflow 2: `prepare-agent`

### Purpose

Prepare the backtests system so a discovered remote agent can be managed in the UI before any explicit run is launched.

### Steps

1. `site_entry.py prepare-agent` resolves the target agent by id, exact name, or unique partial match.
2. It checks backtests backend health.
3. It calls `POST /get_rule/runtime_ready`.
4. If an access token is available from CLI or environment, it is forwarded in that call.
5. The backend readiness flow ensures local runtime prerequisites exist.
6. `prepare-agent` then calls `POST /get_rule/rule/ensure_remote_agent`.
7. It fetches current pool assignments via `GET /get_rule/rule/agent/{agent_id}/pools`.
8. It returns a single JSON payload that combines:
   - backend health
   - runtime readiness
   - discovered agent identity
   - ensured rule record
   - pool assignment state

### Why This Exists

This command keeps “open the UI for this agent” from requiring the operator to manually create rules or guess local state first.

## Workflow 3: `run-agent`

### Purpose

Execute one discovered public agent directly through the local wrapper, without going through the backtests UI.

### Steps

1. `site_entry.py run-agent` resolves the agent from public discovery.
2. It infers or accepts the agent type.
3. It builds the full `run_agent_client.py` command.
4. It forwards optional `--access-token`, `--work-dir`, and `--task-id`.
5. It executes the wrapper as a subprocess.
6. It returns a small JSON payload with agent identity plus subprocess exit code.

### Canonical Execution Rule

No direct host code should reimplement the underlying streaming/polling dispatch.
All direct execution flows should adapt into `run_agent_client.py`.

## Workflow 4: Direct Local Agent Run via `run_agent_client.py`

### Purpose

Run a remote trading or deep-research agent through a reusable, skill-local runtime and produce inspectable artifacts.

### Steps

1. Validate the bundled layout (`agents_client/`, `requirements.txt`).
2. Parse and validate required flags.
3. Normalize `mode`.
4. Resolve the parent run directory.
5. Resolve the access token and cache it when a parent directory is known.
6. Create a unique child run directory.
7. Create or update `.runtime/env` if needed.
8. Re-exec into the local runtime with runtime metadata env vars.
9. Dispatch to one of four agent/mode handlers.
10. Mirror stdout/stderr into `run.log`.
11. Write `summary.json`.
12. For trading runs, persist normalized decisions into `trading_agent_runs.db`.

### Branches

- `trading + streaming`
- `trading + polling`
- `deep_research + streaming`
- `deep_research + polling`

### Observable Outputs

- `summary.json`
- `run.log`
- optional `downloaded_reports/`
- optional `downloaded_skills/`
- trading rows in `.runtime/database/trading_agent_runs.db`

## Workflow 5: Backtests UI Rule Run

### Purpose

Run all stocks in the pools assigned to one remote-agent rule and stream logs in a separate log page.

### Steps

1. The Rules page loads rule list and stock-progress data.
2. When the operator clicks `Run Today`, the frontend first calls `GET /api/v1/get_rule/runtime_ready`.
3. If token/runtime prerequisites are missing, the frontend stops before opening the log window.
4. If ready, the frontend opens a placeholder popup immediately.
5. It calls `POST /api/v1/get_rule/rule/{rule_id}/start`.
6. The backend calls `ensure_runtime_ready(require_token=True)`.
7. It creates an execution record through `execution_manager`.
8. It starts a background thread that calls `stream_agent_execution`.
9. That execution path eventually bridges into `skill_agent_adapter.py`, which runs `scripts/run_agent_client.py`.
10. The popup navigates to `/agent-log/{rule_id}?execution_id=...`.
11. The log page opens an SSE stream against `/api/v1/get_rule/rule/{rule_id}/stream`.

### Important Ordering Constraint

The popup must open only after readiness passes, but before waiting on a long-running backend start response long enough for browsers to treat it as a blocked async popup.

## Workflow 6: Backtests UI Single-Stock Run

This matches Workflow 5 except:

- frontend target is the per-stock Run action
- backend start endpoint is `POST /rule/{rule_id}/stock/{stock_code}/start`
- log route becomes `/agent-log/{ruleId}/{stockCode}?execution_id=...`
- SSE route becomes `/rule/{rule_id}/stock/{stock_code}/stream`

## Workflow 7: Backtests Readiness

### Purpose

Prepare runtime state required by both UI entry and execution entry.

### Steps

1. Resolve token from:
   - explicit payload
   - cached `.runtime/runs/.fintools_access_token`
   - `FINTOOLS_ACCESS_TOKEN`
2. Persist the token back into `.runtime/runs/.fintools_access_token` when it came from explicit payload or environment.
3. Ensure `.runtime/database/trading_agent_runs.db` and schema exist.
4. Ensure `.runtime/database/backtests.sqlite3` exists and is bootstrapped.
5. Return readiness metadata including token path and both database paths.

### Failure Modes

- placeholder token values
- execution-time token missing
- unexpected database bootstrap errors

## Workflow 8: Derived-State Synchronization

### Purpose

Keep the backtests product view aligned with the canonical trading-run source database.

### Steps

1. Load rows from `.runtime/database/trading_agent_runs.db`.
2. Backfill missing `agent_id` / `agent_name` from run summaries when needed.
3. Convert each daily latest signal into `TradingAgentSignal`.
4. Ensure matching `remote_agent` rules exist in backtests.
5. Upsert normalized rows into backtests `agent_trading`.

### Rule

`agent_trading` is derived state.
It must be rebuildable from `trading_agent_runs.db` plus run summaries and remote-agent rule metadata.
