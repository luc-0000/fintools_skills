# Coverage Report

## Documented And Verified By Inspection

- App entry and route registration
- Config loading and DB initialization
- Main SQLAlchemy entities and core table semantics
- Main entity relationships and derived-state direction
- Public HTTP route groups for pool, stock, rule, simulator
- Runtime readiness, token resolution, and execution-gating behavior
- Mixed API error styles (`FAILURE` payloads plus HTTP exceptions)
- Rule execution workflow and simulator replay workflow
- Execution manager in-memory state machine and SSE flow
- Local/remote agent integration model
- MCP tool bundle topology
- Maintenance/data-update script inventory

## Documented But Only Partially Verified

- Full request/response schema fields in all Pydantic classes
- Every internal function under `local_agents/fingenius`
- Exact environment variable names required by all LLM/provider adapters
- SQL schema parity between `db_schemas.py` and `db_schema.sql`
- all numeric legacy `APIException` id meanings across every operation file

## Found In Code But Excluded From Canonical Spec Scope

- checked-in database backups
- generated optimization traces under `local_agents/fingenius/apo/pomltrace`
- generated report outputs and images
- `__pycache__` directories

## Replication Confidence

- High confidence for:
  - API shell
  - DB boot model
  - runtime readiness/bootstrap contract
  - rule execution contract
  - simulator event and metric logic
- Medium confidence for:
  - local agent internals
  - MCP server runtime wiring
  - legacy/experimental modules under `fingenius`
