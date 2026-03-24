# API Error Semantics

## Source Anchors

- Source: end_points/common/utils/http.py
- Source: end_points/main.py
- Source: end_points/get_pool/operations/get_pool_opts.py
- Source: end_points/get_rule/get_rule_routes.py
- Source: end_points/get_rule/operations/agent_utils.py
- Source: end_points/get_simulator/operations/get_simulator_opts.py

## Error Shapes

### Legacy Service Error Shape

Many operation-layer functions return:

```json
{
  "code": "FAILURE",
  "id": "2201",
  "errMsg": "2201"
}
```

This shape is produced by `APIException.to_dict()`.

Fields:

- `code`
- `id`
- `errMsg`

### FastAPI HTTPException Shape

Route wrappers often raise:

```json
{
  "detail": "..."
}
```

with HTTP status such as:

- `400` for readiness/token validation failure
- `500` for unhandled route-layer failures

### App-Level Fallback Shape

Uncaught exceptions in the FastAPI app are normalized by the global exception handler into a generic failure envelope with status 500.

## Error Sources By Layer

### Operation-Layer Business Errors

Examples:

- pool CRUD uses IDs around `2201`, `2206`, `2207`, `2208`, `2209`
- rule operations return structured failure payloads for conditions like missing pool scope

Behavior:

- DB session rollback
- log traceback
- return legacy `FAILURE` payload instead of raising

### Route-Layer Validation Errors

Examples:

- missing FINTOOLS token during `start`
- malformed explicit readiness payload behavior

Behavior:

- raise `HTTPException`
- caller gets non-200 status

### Streaming/Execution Errors

Examples:

- execution not found
- runtime/process failure during async run
- SSE disconnects

Behavior:

- execution manager appends log entries with `type = error`
- SSE stream emits error events/messages
- frontend log page converts connection break into UI error message

## Important Mixed-Mode Constraint

This backend is not uniformly exception-driven.

Replications must preserve both:

- legacy business-result payloads returned as HTTP 200
- route-level HTTP status failures for newer readiness/start logic

If a rewrite collapses everything into one error style, compatibility will drift.

## High-Value Error Cases

### Missing Runtime Token

- Trigger: execution endpoint called with no usable token
- Current effect: HTTP 400 with `detail` text naming expected cache path

### Missing Pool For Bulk Rule Run

- Trigger: legacy bulk run path invoked for a rule without pool assignment
- Current effect: structured failure payload indicating pool assignment is required for new scope selection

### Missing Execution Id On Log Page

- Trigger: log UI opened without `execution_id`
- Current effect: frontend-side error state, not backend auth failure

### Missing Backtests Main DB Before Readiness

- Historical failure mode:
  - list endpoints such as `pool_list` failed when `backtests.sqlite3` had not been bootstrapped
- Current intended behavior:
  - readiness/bootstrap path should ensure the main DB exists before UI-driven use

## Replication Requirement

A clean-room backend must explicitly document:

- which failures stay in-band as `{"code":"FAILURE"...}`
- which failures become non-200 HTTP errors
- which failures appear only as streamed execution log events
