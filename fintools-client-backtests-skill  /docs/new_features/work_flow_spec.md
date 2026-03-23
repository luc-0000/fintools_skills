# Trading Agent Backtests Workflow Spec

## Purpose

This document converts `docs/new_features/work_flow.md` into an executable product and interaction spec.

It defines the required workflow for combining:

- remote agent execution and skill download capabilities already provided by this repository
- the `backtests` system used to manage pools and run trading-agent backtests

This spec focuses on workflow, orchestration, and documentation requirements.
Detailed backtests data-sync and database rules remain governed by:

- `docs/new_features/backtest_spec.md`

## Scope

This workflow spec covers:

- first-run initialization behavior
- user interaction when asking to run a trading agent
- rule existence checks by `agent_id`
- pool assignment flow
- CLI and UI as two supported operator entrypoints
- behavior when an agent already has an assigned pool
- documentation requirements for humans and for LLM operators

This workflow spec does not replace:

- the existing remote agent client runtime contract
- the existing backtests data synchronization contract
- simulator-specific result generation rules already enforced elsewhere

## Product Model

The repository is treated as one skill with two coordinated capabilities:

1. remote agent execution and remote skill download
2. trading-agent backtests management and execution

The workflow must present these two capabilities as one coherent user-facing system rather than two unrelated tools.

## Primary User Intent

The primary workflow begins when a user asks to run a trading agent.

Typical requests include:

- run a specific trading agent
- assign stocks or a pool to a trading agent
- open the backtests UI to manage the agent
- run the existing assigned pool for an agent

The system should interpret these requests into a deterministic flow instead of requiring the user to know internal table structure or backend details.

## First-Run Initialization Requirements

On the first invocation of the skill in a fresh runtime, the system must ensure that baseline prerequisites are ready before attempting trading-agent or backtests operations.

### Required first-run checks

The system must verify:

- a Python runtime is installed under `.runtime/env`
- the access token required for remote agent execution is available

### Initialization behavior

If `.runtime/env` is missing or incomplete:

- the system must prepare the Python environment under `.runtime/env`

If the access token is missing:

- the system must explicitly ask the user for the token or guide the user through the existing token acquisition flow

### Verification requirement

Because the current repository likely already implements most of this behavior, implementation work must begin by confirming whether:

- `.runtime/env` bootstrap already exists
- token prompting, caching, and reuse already exist

The workflow must reuse existing implementations where possible rather than reimplementing them inside `backtests`.

## Trading Agent Execution Workflow

When the user asks to run a trading agent, the system must execute the following control flow.

### Step 1: identify target agent

The system must resolve the target trading agent by `agent_id` or equivalent unique identifier supplied by the user or upstream configuration.

### Step 2: check whether the agent exists in rule storage

The system must check whether a corresponding rule already exists for that `agent_id`.

The existence check is based on:

- presence of a rule mapped to the requested `agent_id`

### Step 3: create missing rule when needed

If no rule exists for the requested `agent_id`:

- the system must create a new rule for that agent before continuing

The detailed required fields and rule semantics must follow:

- `docs/new_features/backtest_spec.md`

This workflow spec requires the create-if-missing behavior but defers exact schema rules to the backtests spec.

### Step 4: determine how pool assignment will be handled

After rule existence is guaranteed, the system must determine whether the user wants to manage pool assignment via:

- command-line interaction
- graphical backtests UI

The system must support both modes as first-class flows.

## Pool Assignment Workflow

Once the target agent exists in rules, the next decision is whether a pool is already assigned.

### Case A: agent already has an assigned pool

If the target agent already has an assigned pool:

- the system must directly run all stocks in that assigned pool
- the user should not be forced through pool selection again unless they explicitly ask to modify it

This is the default fast path for repeat usage.

### Case B: agent does not yet have an assigned pool

If the target agent does not have an assigned pool:

- the system must ask the user how they want to assign the pool

Supported options:

- assign pool through commands
- open the backtests UI and let the user configure it there

The system must not silently create or assign an arbitrary pool without user intent.

## Dual Interaction Modes

The backtests system must remain operable through two equivalent operator surfaces.

### CLI mode

In CLI mode, the user can:

- assign a pool to an agent
- add or manage stocks through approved commands
- trigger backtest-related execution from the command line

CLI behavior must be deterministic and constrained by a strict machine-readable operating guide.

### UI mode

In UI mode, the system opens or directs the user to the backtests frontend/backend interface so they can:

- inspect agent state
- assign pools
- manage stocks through the graphical workflow
- trigger or inspect backtest operations supported by the UI

The UI path is not optional decoration. It is a required workflow entrypoint equal in status to CLI mode.

## Documentation Requirements

This workflow requires two separate documentation layers.

### Human-facing README

File required:

- `backtests/README.md`

Purpose:

- explain the backtests system in plain language
- help users understand common tasks
- provide lightweight guidance even when nothing is wrong
- provide troubleshooting-oriented guidance when users are blocked

The README should optimize for fast human comprehension, not database completeness.

### LLM-facing strict operating manual

A second document must be written for machine operators.

Purpose:

- define exactly how an LLM may operate the backtests system through commands
- prevent unsafe or invalid database edits
- clarify which objects may be created or modified directly
- clarify which outputs must only be produced by running the simulator or other execution engines

This machine manual must be stricter than the human README and should function as an operational guardrail.

## Machine-Operator Constraints

The strict operating manual must explicitly define at least the following constraints.

### Database mutation boundary

The document must clearly distinguish:

- records that may be created or updated directly by approved management commands
- records that must never be fabricated manually
- records that must only arise from runtime execution such as simulator-produced results

### Pool management boundary

The document must clarify:

- whether new pools may be added directly
- how stocks may be added to pools
- which pool-related fields are user-managed versus runtime-derived

### Result generation boundary

The document must state that execution results, simulation outputs, and other derived artifacts must not be manually inserted just to satisfy workflow expectations when those artifacts are supposed to be produced by real runs.

## Reuse Requirements

This workflow must reuse existing repository capabilities whenever possible.

In particular:

- token acquisition should reuse current token flows
- remote agent invocation should reuse current client mechanisms
- backtests orchestration should call into existing stable interfaces rather than duplicating low-level implementations

## Acceptance Criteria

This workflow is satisfied when all of the following are true:

1. A first-time user can initialize runtime prerequisites without manually reverse-engineering the repository.
2. A request to run a trading agent causes the system to check for rule existence by `agent_id`.
3. A missing rule is created automatically before continuing.
4. If the agent already has an assigned pool, the system runs that pool directly.
5. If the agent lacks an assigned pool, the user is offered both CLI and UI assignment paths.
6. `backtests/README.md` exists and is written for humans.
7. A separate strict operating manual exists for LLM command-based operation.
8. The machine manual clearly defines database, pool, and simulator-result mutation boundaries.

## Deliverables

The work implied by this spec should produce or update at least:

- `docs/new_features/work_flow_spec.md`
- `backtests/README.md`
- one LLM-oriented strict operating guide for backtests command usage

## Open Implementation Questions

Before implementation is considered complete, the following must be confirmed against code:

- where `.runtime/env` bootstrap currently lives
- how access token prompting and caching currently behave
- how `agent_id` is resolved from user requests
- how pool assignment is represented in current backtests storage
- how the UI entrypoint is started or exposed in this repository
- what exact command set the LLM operating guide should allow
