# Authentication And Runtime Token Spec

## Source Anchors

- Source: end_points/common/utils/runtime_readiness.py
- Source: end_points/get_rule/get_rule_routes.py
- Source: end_points/get_rule/operations/skill_agent_adapter.py
- Source: ../../../../scripts/run_agent_client.py

## Overview

The backend does not expose a general user-auth session system for its CRUD API.

Instead, the critical protected boundary is remote-agent execution.
That boundary depends on a FINTOOLS access token used by the shared skill runner.

## Current Auth Model

### CRUD Surfaces

- pool, stock, rule, and simulator CRUD routes are effectively unauthenticated inside the local backtests service
- there is no route middleware enforcing bearer auth, cookies, or sessions

### Execution Surfaces

These routes are token-gated indirectly through runtime readiness:

- `POST /api/v1/get_rule/rule/{rule_id}/start`
- `POST /api/v1/get_rule/rule/{rule_id}/stock/{stock_code}/start`

They do not parse bearer headers themselves.
They delegate token enforcement to `ensure_runtime_ready(require_token=True)`.

## Token Resolution Order

`runtime_readiness.py` currently resolves token sources in this order:

1. explicit `access_token` passed to readiness
2. cached `.runtime/runs/.fintools_access_token`
3. `FINTOOLS_ACCESS_TOKEN` environment variable

If an explicit token or env token is used, it is persisted back to:

- `.runtime/runs/.fintools_access_token`

## Readiness Endpoints

### `GET /api/v1/get_rule/runtime_ready`

- check-only readiness
- does not require token
- returns token/database state visibility

### `POST /api/v1/get_rule/runtime_ready`

- accepts:
  - `access_token`
  - `require_token`
- can persist an explicit token into the local runtime cache
- can be used by host wrappers before the UI opens

## Placeholder-Token Rejection

The backend rejects obvious placeholder values such as:

- `your-token`
- `your-secret`
- `your-fintools`
- `placeholder`

This validation applies to:

- explicit readiness payload token
- cached token file
- environment token

## Execution Bridge

When the backtests backend executes a remote agent:

1. start endpoint checks readiness
2. `skill_agent_adapter.py` resolves token again via the same canonical readiness/token helper
3. the adapter launches `scripts/run_agent_client.py`
4. that child wrapper exports `FINTOOLS_ACCESS_TOKEN` into the isolated runtime process

This keeps UI execution and direct wrapper execution on one token contract.

## Failure Responses

- missing token at execution time becomes HTTP 400 from the start endpoints
- invalid placeholder token becomes runtime error surfaced through HTTP 400 or host-level startup failure

## Replication Requirement

A clean-room implementation must preserve this exact architectural property:

- local CRUD endpoints may be unauthenticated
- remote-agent execution must be token-gated through one canonical readiness/token-resolution path

It should not introduce a second execution-only token source that bypasses the cache/readiness contract.
