# Fintools Client Backtests Skill Spec Index

This bundle documents the full skill repository as a replicable engineering system.

It complements two existing lower-level spec bundles that already live under the product subtrees:

- `backtests/backend/docs/specs/` for the FastAPI backend internals
- `backtests/frontend/docs/specs/` for the React UI structure

The documents in this directory describe the skill-level composition that ties those subsystems together with the public-site discovery wrapper, runtime bootstrap logic, isolated agent runner, and shared runtime state.

## Scope

- Included:
  - `scripts/`
  - `agents_client/`
  - `database/`
  - `config.json`
  - `requirements.txt`
  - `backtests/`
  - `tests/`
- Included as referenced implementation detail:
  - `backtests/backend/docs/specs/`
  - `backtests/frontend/docs/specs/`
- Excluded by design:
  - `.runtime/`
  - `node_modules/`
  - generated reports, logs, downloaded archives, and copied-install artifacts

## Reading Order

1. [00-scope-and-baseline.md](./00-scope-and-baseline.md)
2. [40-system-composition.md](./40-system-composition.md)
3. [50-execution-workflows.md](./50-execution-workflows.md)
4. [60-state-and-persistence.md](./60-state-and-persistence.md)
5. [20-runtime-contract.md](./20-runtime-contract.md)
6. [10-capability-matrix.md](./10-capability-matrix.md)
7. [70-replication-guide.md](./70-replication-guide.md)
8. [30-regression-acceptance.md](./30-regression-acceptance.md)

## Documents

- [00-scope-and-baseline.md](./00-scope-and-baseline.md)
  - frozen baseline for wrapper compatibility
- [10-capability-matrix.md](./10-capability-matrix.md)
  - capability inventory and current coverage labels
- [20-runtime-contract.md](./20-runtime-contract.md)
  - narrow compatibility contract for `scripts/run_agent_client.py`
- [30-regression-acceptance.md](./30-regression-acceptance.md)
  - regression expectations for current baseline
- [40-system-composition.md](./40-system-composition.md)
  - repository-level architecture, boundaries, and module responsibilities
- [50-execution-workflows.md](./50-execution-workflows.md)
  - step-by-step execution flows for discovery, preparation, UI runs, and CLI runs
- [60-state-and-persistence.md](./60-state-and-persistence.md)
  - runtime directories, databases, cache files, and derived-state rules
- [70-replication-guide.md](./70-replication-guide.md)
  - implementation checklist for recreating the skill without the original code

## Sub-Spec Bundles

- Backend internals: [backtests/backend/docs/specs/SPEC_INDEX.md](../../backtests/backend/docs/specs/SPEC_INDEX.md)
- Frontend UI bundle: [backtests/frontend/docs/specs/SPEC_INDEX.md](../../backtests/frontend/docs/specs/SPEC_INDEX.md)

## Verification Rule

Any future summary that claims the skill is fully specified should verify all of the following files exist:

- [SPEC_INDEX.md](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/docs/specs/SPEC_INDEX.md)
- [40-system-composition.md](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/docs/specs/40-system-composition.md)
- [50-execution-workflows.md](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/docs/specs/50-execution-workflows.md)
- [60-state-and-persistence.md](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/docs/specs/60-state-and-persistence.md)
- [70-replication-guide.md](/Users/lu/development/fintools_all/fintools_skills/fintools-client-backtests-skill/docs/specs/70-replication-guide.md)
