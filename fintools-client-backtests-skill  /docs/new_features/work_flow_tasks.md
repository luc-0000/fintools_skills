# Trading Agent Backtests Workflow Tasks

## Purpose

This document turns the workflow spec into an implementation checklist for this repository.

Primary references:

- `docs/new_features/work_flow_spec.md`
- `docs/new_features/backtest_spec.md`

## Task Groups

## 1. First-Run Initialization Audit

Goal:

- confirm what already exists for `.runtime/env` bootstrap and access-token handling

Tasks:

- inspect current runtime bootstrap path for `.runtime/env`
- inspect current token prompt, cache, and reuse flow
- document which parts are already implemented and which parts are missing
- ensure backtests reuses existing token/runtime logic instead of duplicating it

Suggested code areas:

- `scripts/`
- `SKILL.md`
- current runtime helper modules

## 2. Agent Resolution And Rule Auto-Provision

Goal:

- when a user asks to run a trading agent, the system must resolve `agent_id`, check for an existing rule, and create one if missing

Tasks:

- define the canonical input path for `agent_id`
- add a pre-run check for `rule.agent_id`
- create `remote_agent` rule automatically when missing
- ensure rule creation populates `name`, `description`, `info`, and `agent_id`
- prevent duplicate rules for the same `agent_id`

Suggested code areas:

- `backtests/backend/end_points/get_rule/operations/`
- `backtests/backend/end_points/common/utils/trading_agent_sync.py`

## 3. Pool-Assignment Decision Flow

Goal:

- support the two required paths after rule existence is guaranteed

Tasks:

- detect whether the target rule already has an assigned pool
- if a pool already exists, run the full pool directly
- if no pool exists, return a clear next-step response instead of silently creating a pool
- support both command-driven pool assignment and UI-driven pool assignment

Suggested code areas:

- `backtests/backend/end_points/get_rule/operations/`
- `backtests/frontend/src/pages/Rules/`
- `backtests/frontend/src/pages/Pools/`

## 4. CLI/API Operating Path

Goal:

- make command-based operation stable and predictable for agents and scripts

Tasks:

- verify that existing API routes cover rule creation, pool creation, stock assignment, rule-pool binding, rule execution, simulator creation, and simulator execution
- normalize any gaps in endpoint behavior or error messages
- ensure command-driven flow can be completed without direct database edits
- align API responses with the workflow order defined in `work_flow_spec.md`

Suggested code areas:

- `backtests/backend/end_points/get_rule/`
- `backtests/backend/end_points/get_pool/`
- `backtests/backend/end_points/get_stock/`
- `backtests/backend/end_points/get_simulator/`

## 5. UI Operating Path

Goal:

- make the frontend a first-class route for pool assignment and backtest execution

Tasks:

- verify the Rules page clearly exposes agent execution status and run actions
- verify the Pools page supports creating pools and managing pool stocks
- verify the Simulators page supports creating and running simulators against remote-agent rules
- make sure the UI path matches the workflow spec instead of assuming hidden DB setup

Suggested code areas:

- `backtests/frontend/src/pages/Rules/`
- `backtests/frontend/src/pages/Pools/`
- `backtests/frontend/src/pages/Simulators/`
- `backtests/frontend/src/services/`

## 6. Documentation Sync

Goal:

- keep human and machine docs aligned with actual implementation

Tasks:

- maintain `backtests/README.md` as the human quick-start and usage guide
- maintain `backtests/LLM_OPERATIONS.md` as the strict machine manual
- update docs when startup commands, config paths, mutation boundaries, or workflow behavior change

## 7. Safety And Mutation Boundaries

Goal:

- enforce the rule that derived results come from real execution, not manual fabrication

Tasks:

- preserve API/UI as the default mutation surface
- avoid direct inserts into `agent_trading`, `simulator_trading`, `stock_rule_earn`, and `pool_rule_earn`
- ensure pool stock counts and derived simulator outputs are maintained by backend logic
- add guardrails or code comments where the current code makes unsafe edits easy

Suggested code areas:

- `backtests/backend/end_points/get_rule/operations/agent_utils.py`
- `backtests/backend/end_points/get_simulator/operations/`
- `backtests/backend/end_points/get_stock/operations/get_stock_opts.py`

## 8. Verification

Goal:

- prove the workflow works end to end

Tasks:

- add or update tests for rule auto-provision by `agent_id`
- add or update tests for pool-exists vs pool-missing branching
- add or update tests for simulator creation/run after agent execution
- verify docs reference real existing paths and routes

Suggested evidence:

- backend API tests
- smoke tests against local backend
- inspected generated DB state in `.runtime/database/backtests.sqlite3`

## Recommended Execution Order

1. audit first-run bootstrap and token reuse
2. implement or confirm rule auto-provision
3. implement pool-assignment branching
4. verify CLI/API path
5. verify UI path
6. add tests
7. sync docs

## Exit Criteria

This task set is complete when:

- a user can request a trading agent by `agent_id`
- the system auto-creates the corresponding `remote_agent` rule when absent
- the system branches correctly based on whether a pool is already assigned
- both CLI/API and UI flows are usable
- docs accurately describe the behavior
- no derived runtime outputs need to be manually fabricated
