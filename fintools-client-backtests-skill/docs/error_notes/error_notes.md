# Error Notes

## 2026-03-19

### 1. Agent-only boundary was written too narrowly

- Symptom: the skill started telling the host that it could only call agents and could not download skills.
- Root cause: wrapper/docs were mistakenly narrowed to an agent-only contract.
- Fix: restore dual capability at the repository level, then split entrypoints so agent execution stays in `scripts/run_agent_client.py` and skill downloads move to `scripts/download_skill.py`.

### 2. Agent and skill download responsibilities were mixed in one script

- Symptom: `run_agent_client.py` name and contract no longer matched the combined behavior.
- Root cause: skill download logic was added directly into the agent runner.
- Fix: move public skill archive download into `scripts/download_skill.py`, keep `run_agent_client.py` agent-only, and split tests/docs accordingly.

### 3. Layout validation was too broad for the download entrypoint

- Symptom: download flow reused a layout check that required `agents_client/`, even though downloading a public skill does not depend on it.
- Root cause: `validate_skill_layout()` represented agent runtime needs, not shared bundle needs.
- Fix: rename the agent-side check to `validate_agent_layout()` and add `validate_download_layout()` in `scripts/download_skill.py` that only requires `requirements.txt`.

### 4. Download filename parsing was incorrect

- Symptom: downloaded archive names could include raw `Content-Disposition` header fragments instead of a clean filename.
- Root cause: filename parsing used manual string splitting on `filename=` and did not properly handle standard header forms such as `filename*=` or more complex parameter layouts.
- Fix: parse `Content-Disposition` via `email.message.Message.get_filename()` and fall back to `skill-<id>.zip` only when no usable filename is provided.

### 5. Download path expectation vs. actual path

- Observation: a run was written under `/private/tmp/...`.
- Verified behavior: `scripts/download_skill.py` still defaults to `skill_root/.runtime/runs/` when `--work-dir` is not provided, because it uses `ensure_work_dir(args.work_dir)`.
- Interpretation: the `/private/tmp/...` path is consistent with an explicit or host-provided `--work-dir`, not with a broken default path implementation.

## 2026-03-23

### 1. Create Agent failed because backend allowed blank description at schema layer but not at DB layer

- Symptom: the Agents page `Create` action appeared to do nothing, and direct backend `POST /api/v1/get_rule/rule_list` returned `{"code":"FAILURE","id":"2209","errMsg":"2209"}`.
- Root cause: `RuleCreateArgs` normalized blank `description` to `None`, but `rule.description` in SQLite is `NOT NULL`, so insert failed with `sqlite3.IntegrityError: NOT NULL constraint failed: rule.description`.
- Fix: in `backtests/backend/end_points/get_rule/operations/get_rule_opts.py`, normalize missing `description` to `''` before insert. Frontend-side blank descriptions are still allowed.
- Verification:
  - direct backend create request to `127.0.0.1:8888` succeeded after the fix
  - proxied create request through `127.0.0.1:8000/api/v1/...` also succeeded

### 2. Create Simulator previously failed because initial log writing broke the whole creation flow

- Symptom: simulator creation returned failure even when payload itself was otherwise valid.
- Root cause:
  - simulator creation path wrote an initial HTML log file under `end_points/get_simulator/operations/sim_logs/`
  - log helpers did not ensure the directory existed
  - `write_sim_log()` / `read_sim_log()` closed `file` unconditionally in `finally`, which caused secondary errors when open failed
  - simulator creation treated this log-writing problem as a full creation failure
- Fix:
  - make simulator log helpers create the log directory automatically
  - guard `file.close()` behind `file is not None`
  - keep log errors from aborting simulator creation
- Verification:
  - direct backend create request to `127.0.0.1:8888/api/v1/get_simulator/simulator_list` succeeded
  - proxied create request through `127.0.0.1:8000/api/v1/get_simulator/simulator_list` also succeeded

### 3. Preferred triage order for frontend actions that "do nothing"

- Rule adopted: do not start with browser-side guessing.
- Correct order:
  - first test the backend endpoint directly with a minimal real payload
  - if backend fails, inspect backend traceback/logs and fix that first
  - only after backend passes, test the frontend-to-backend API path through the frontend proxy
  - only after both API layers pass, investigate browser click/submit behavior

### 4. Backtests remote-agent execution must not fall back to `.env` or environment token lookup

- Symptom: `backtests` remote agent execution still failed with `401 Unauthorized` when fetching `/.well-known/agent-card.json`, even after the execution path was switched to the shared skill adapter.
- Root cause:
  - `backtests` adapter reused `scripts/run_agent_client.py::resolve_access_token()`
  - that helper intentionally supports `CLI -> environment variable -> cached token file`
  - for `backtests`, this was too broad: it allowed accidental fallback to non-runtime sources and made placeholder values easy to leak into execution
  - the cached token file at `.runtime/runs/.fintools_access_token` contained the example value `your-fintools-access-token`
- Fix:
  - keep `agents_client/` unchanged
  - narrow token resolution only in `backtests` adapter
  - allow only:
    - explicit token passed into the adapter
    - or the skill-cached token file `.runtime/runs/.fintools_access_token`
  - reject placeholder/example token values early with a clear local error instead of letting the request reach the remote agent and fail as `401`
- Verification:
  - direct adapter call now raises `Invalid FINTOOLS access token cache ...`
  - real backend SSE execution now emits the same local error immediately and no longer reaches remote `agent-card.json` lookup with a placeholder token

### 5. Simulator could finish with no `simulator_trading` rows even when `agent_trading` had signals

- Symptom: running simulator such as `simulator 4` returned without useful trading output, and `simulator_trading` stayed empty even though the linked `remote_agent` already had signal rows in `agent_trading`.
- Root cause:
  - `trading_agent_runs -> agent_trading` sync used the runtime execution date directly
  - recent synced signal dates such as `2026-03-21` were Saturdays, not market dates
  - simulator matching logic required exact date matches against market data, so weekend signals were silently skipped
  - in addition, simulator trade records were being inserted with ISO datetime strings like `2026-03-23T00:00:00`, which SQLite `DateTime` columns reject
- Fix:
  - in `backtests/backend/end_points/get_simulator/operations/get_simulator_utils.py`, align non-trading signal dates to the next available market date before generating simulator trades
  - normalize string / pandas timestamp trade dates to real Python `datetime` objects before inserting `simulator_trading`
- Verification:
  - regression test `tests/test_backtests_simulator_run.py` now covers:
    - weekend signal date -> next trading day alignment
    - `run_sim_agent()` producing `simulator_trading` rows from a weekend signal
  - related suite passes:
    - `tests.test_backtests_simulator_run`
    - `tests.test_backtests_simulator_create`

### 6. Current network can still block real Tushare-backed simulator runs

- Observation: under the current network, real `runSimulator()` may still fail while fetching行情数据 from Tushare.
- Verified behavior:
  - one real `simulator 4` run hit `requests.exceptions.ReadTimeout` against `api.waditu.com`
  - after that timeout, `stockDataFrameFromTushare()` returned data without the expected OHLC columns, which then caused follow-on simulator failure
- Interpretation:
  - this is an upstream network/data-source issue in the current environment, not the local simulator date-alignment / SQLite insert bug above
  - the local simulator bug was fixed independently and covered by regression tests

## 2026-03-24

### 1. Remote-agent run page could fail to open logs because the browser blocked the popup

- Symptom: clicking `Run Today` or the single-stock `Run` button on the remote-agent page could show `popup window blocked`, and the log page would not open.
- Root cause:
  - the frontend awaited the backend start request first
  - only after that async boundary returned did it call `window.open(...)`
  - browsers may treat that as an async popup instead of a direct user-gesture popup
- Fix:
  - open a placeholder log window synchronously inside the original click handler
  - wait for the backend to return `execution_id`
  - navigate the already-open window to the real `/agent-log/...` route
  - if startup fails or no `execution_id` is returned, close the placeholder window and surface the error
- Files involved:
  - `backtests/frontend/src/pages/Rules/components/RuleList.tsx`

### 2. Backtests UI readiness and agent-run readiness had drifted apart

- Symptom:
  - immediately after skill install, opening the backtests UI could show a runnable page even though remote-agent runtime was not actually ready
  - if the access token only existed in host memory and had not yet been persisted to `.runtime/runs/.fintools_access_token`, clicking `Run` or `Run Today` could fail after the UI opened, which users perceived as the run page flashing and aborting
  - in a fresh install, opening the backtests UI could also leave `.runtime/database/backtests.sqlite3` missing, so backend endpoints such as `GET /api/v1/get_pool/pool_list` failed before the page could render pool data
- Root cause:
  - UI-entry preparation and remote-agent execution preparation were not using the same code path
  - `runtime_readiness.py` had only been ensuring token cache and `trading_agent_runs.db`
  - it was not also bootstrapping the main `backtests.sqlite3` database that the UI list endpoints depend on
- Fix:
  - move token resolution and persistence into `backtests/backend/end_points/common/utils/runtime_readiness.py` as the single source of truth
  - let both the backtests readiness endpoint and the actual execution path reuse that same token-resolution function
  - add `POST /api/v1/get_rule/runtime_ready` so callers such as `scripts/site_entry.py prepare-agent` can pass an explicit in-memory token and persist it before the UI opens
  - extend that same readiness step to bootstrap `.runtime/database/backtests.sqlite3` before the UI opens, so pool-list and other backtests endpoints have their primary database ready
- Verification:
  - regression suite now covers explicit-token persistence, check-only runtime readiness, creation of `backtests.sqlite3`, POST runtime readiness, and `site_entry.py prepare-agent` runtime bootstrap behavior

### 3. Trading-agent execution path did not persist to `trading_agent_runs.db` before derived-table updates

- Symptom:
  - a real remote-agent run could finish and produce logs or reports
  - but `.runtime/database/trading_agent_runs.db` still had no new row for that run
  - meanwhile, `backtests.sqlite3` could already contain `agent_trading` rows from separate UI execution paths
- Verified behavior:
  - after CLI execution of `agent 69 / stock 000001`, no new `stock_code='000001' AND agent_id='69'` row appeared in `.runtime/database/trading_agent_runs.db`
  - the observed `agent_trading` row in `backtests.sqlite3` predated that CLI run and matched a manual UI execution time
- Root cause:
  - current execution flow does not yet insert run results into `.runtime/database/trading_agent_runs.db`
  - some `backtests` execution paths still call `update_rule_trading(...)` directly and therefore bypass the intended source-of-truth chain
- Required fix direction:
  - `.runtime/database/trading_agent_runs.db` must be the only source of truth for trading-agent execution results
  - every execution must first persist raw result or action there
  - `agent_trading` must only be updated through the sync path from `trading_agent_runs.db`
  - UI, CLI, and backend execution helpers must not directly write `agent_trading`
- Files involved:
  - `scripts/run_agent_client.py`
  - `backtests/backend/end_points/get_rule/operations/agent_utils.py`
  - `backtests/backend/end_points/get_rule/operations/agent_streaming.py`
  - `backtests/backend/end_points/common/utils/trading_agent_sync.py`

### 4. UI `Run` / `Run Today` execution originally bypassed the standard `.runtime/runs` artifact path

- Symptom:
  - the backtests UI log page could stream live output
  - but the same execution did not produce the standard run directory under `.runtime/runs/`
  - therefore no per-run `run.log`, `summary.json`, or aligned run artifact path existed for the UI-triggered execution
- Root cause:
  - the UI backend SSE path called the low-level streaming execution helper directly
  - that path streamed stdout into an in-memory queue for SSE, but did not invoke `scripts/run_agent_client.py`
  - `.runtime/runs/` creation, `run.log`, `summary.json`, report download path, and source-db write all live behind the standard `run_agent_client.py` entrypoint
- Required fix direction:
  - UI `Run` and `Run Today` must reuse the same `scripts/run_agent_client.py` execution entrypoint as CLI
  - SSE should only relay that standard run's output, not create a second parallel execution path
  - every UI-triggered execution must therefore also create a standard run directory under `.runtime/runs/`
- Files involved:
  - `backtests/backend/end_points/get_rule/operations/skill_agent_adapter.py`
  - `backtests/backend/end_points/get_rule/operations/agent_streaming.py`
  - `scripts/run_agent_client.py`

### 5. Pools page could go empty because `pool_list` tried to write `latest_date` during a read

- Symptom:
  - the `Pools` page could suddenly render empty even though pool rows still existed in `.runtime/database/backtests.sqlite3`
  - direct backend call to `GET /api/v1/get_pool/pool_list` returned legacy failure `2201`
- Root cause:
  - `getPoolList()` called `update_latest_date(db)` before returning rows
  - that helper updates `pool.latest_date` and commits the session
  - in environments where the current SQLite handle is effectively read-only, the write failed with `sqlite3.OperationalError: attempt to write a readonly database`
  - the read endpoint then returned failure instead of serving the already-existing pool rows
- Fix:
  - keep the opportunistic `latest_date` refresh
  - but if that write fails, rollback the session, log a warning, and continue returning the current pool list
  - do not let `Pools` page availability depend on a best-effort metadata write
- Verification:
  - regression covers `getPoolList()` returning `SUCCESS` with existing rows when `update_latest_date()` raises during the refresh step

### 6. Vite could show a false `Failed to resolve import "@/layouts/ProLayout"` overlay even when the file exists

- Symptom:
  - the frontend dev overlay reported `Failed to resolve import "@/layouts/ProLayout" from "src/router/index.tsx"`
  - but `backtests/frontend/src/layouts/ProLayout.tsx` was still present on disk and production build still succeeded
- Verified root cause:
  - this was not a missing source file in the checked-in frontend
  - the recurring case came from stale or duplicate Vite dev servers serving inconsistent module state for the copied install under `~/.openclaw/workspace/skills/...`
  - checking the install showed more than one `vite --port 8000` process at the same time while the source tree still contained `src/layouts/ProLayout.tsx`
- Fix / operator action:
  - treat this overlay as a dev-server-state problem first, not a source-tree deletion
  - verify on disk that `src/layouts/ProLayout.tsx` still exists and `vite.config.ts` still maps `@` to `./src`
  - then stop old Vite processes for that install copy and restart a single clean frontend dev server
- Regression coverage:
  - `tests/test_frontend_router_alias.py` now locks the repository-side invariant that:
    - `src/router/index.tsx` imports `@/layouts/ProLayout`
    - `src/layouts/ProLayout.tsx` exists
    - `vite.config.ts` still defines the `@ -> ./src` alias
