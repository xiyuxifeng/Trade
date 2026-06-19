---
name: refactor-orchestrator
description: >
  Orchestrate staged software refactors with a parent agent and bounded custom
  subagents. Use for repository audits, contract freezing, dependency-aware
  task cards, cost-aware delegation, mechanical verification, semantic review,
  migration control, and final stage acceptance.
---

# Refactor Orchestrator

## Purpose

Coordinate complex refactors without forcing architecture, implementation,
verification, and acceptance into one long parent context.

```text
Parent agent
├── optional refactor-explorer-mini: bounded read-only investigation
├── optional refactor-executor-mini: bounded implementation and tests
└── Parent agent: semantic review and acceptance
```

This Skill is project-agnostic. Project paths, task IDs, domain contracts,
commands, and acceptance criteria must come from the target repository or the
user.

The Skill optimizes for total project cost and correctness, not for maximizing
subagent count. A delegated workflow can consume more tokens than a comparable
single-agent task, so delegation must be justified.

## Required inputs

Before planning, identify:

- repository root and applicable `AGENTS.md` files
- source task list, issue, specification, or requested stage
- current branch, baseline commit, and dirty worktree
- applicable architecture, product, migration, and compatibility documents
- test, lint, typecheck, build, migration, and E2E commands
- previous handoff or review evidence, when present

If no formal task list exists, create a temporary bounded plan from the user
request and repository evidence.

## Explicit delegation decision

The Parent must explicitly decide whether delegation is justified.

```text
Explicitly decide whether delegation is justified under this Skill.
If justified, explicitly spawn the selected configured subagent or subagents.
If not justified, proceed with the Parent only and record that zero subagents
were selected.
Do not rely on implicit delegation.
```

Zero subagents is a valid deliberate decision. Do not spawn an agent merely
because the Skill is active.

## Delegation eligibility gate

Before delegating an implementation task, all of these must be true:

- the objective and expected output are bounded
- allowed and forbidden paths can be stated
- dependencies are complete
- public contracts are frozen, or the task is read-only investigation
- verification commands and escalation conditions are known

Do not delegate unresolved architecture, source-of-truth selection, migration
policy, authorization policy, or unspecified algorithm semantics.

## Delegation benefit gate

After eligibility is satisfied, delegate only when at least one benefit is
material and the expected benefit exceeds coordination and context-transfer
cost:

1. substantial read-heavy context can be isolated from the Parent
2. bounded routine work can be performed by a lower-cost agent
3. independent work can safely run in parallel with non-overlapping write sets
4. delegation materially reduces high-cost rework risk

If no benefit condition is satisfied, the Parent performs the task directly.

## Agent bootstrap

Before the first delegated task in a repository, and after relevant Codex or
configuration changes:

1. verify these files exist:
   - `.codex/agents/refactor-explorer-mini.toml`
   - `.codex/agents/refactor-executor-mini.toml`
2. verify their declared model and default permissions
3. keep subagent depth at 1
4. do not silently substitute the Parent model for a configured child
5. treat TOML permissions as intent; runtime overrides may supersede them

Missing bootstrap files should be reported and created only when repository
changes are authorized.

## Runtime truth policy

Evidence is mandatory for:

- commands and tests that are reported as executed
- diffs and files reported as changed
- migrations reported as applied or verified
- acceptance criteria reported as satisfied
- task or stage completion

Runtime metadata is different:

- report exact model identity, effective permissions, or spawning details only
  when runtime evidence supports the claim
- otherwise omit the detail or mark it `unknown`/`not independently verified`
- inability to verify optional runtime metadata does not by itself block a
  normal task

Use single-controller fallback only when native spawning is unavailable, child
creation fails, or a required permission boundary cannot be guaranteed. Merely
failing to confirm an exact child model name does not require fallback if the
child actually ran; report the model as unverified.

For strict read-only work, if effective read-only permission cannot be trusted,
do not spawn that Explorer. Perform the investigation in the Parent or use an
approved alternative.

## Parent responsibilities

The Parent owns:

- scope interpretation and repository investigation strategy
- architecture and official source-of-truth decisions
- domain, API, schema, version, migration, rollback, and compatibility contracts
- risk classification and dependency batches
- the delegation decision and budget justification
- Task Cards
- inspection of the actual shared worktree and combined diff
- semantic review and final task/stage acceptance
- authoritative status updates only after acceptance

The Parent must not delegate final acceptance.

## Explorer responsibilities

Use `refactor-explorer-mini` only for meaningful read-heavy investigation:

- locate routes, APIs, models, jobs, workflows, schemas, prompts, and tests
- trace call and data flow
- find legacy or duplicate paths
- inspect migration history or deletion references
- classify test failures or large logs

Avoid Explorer when exact files and call chains are already known or the Parent
can answer by reading a few files.

Explorer reads:

- its Task Card
- applicable repository instructions
- explicitly scoped files and tests

It should not reread unrelated global documents unless the Task Card requires
it or a contradiction must be escalated.

## Executor responsibilities

Use `refactor-executor-mini` only after the task boundary is frozen.

Good uses:

- bounded CRUD, API, UI, scripts, fixtures, and tests
- mechanical migration implementation after Parent design approval
- reference cleanup after deletion approval
- documentation tied to completed behavior

Executor reads:

- its Task Card
- applicable root and nested `AGENTS.md`
- explicitly scoped implementation files
- directly affected tests and frozen contract references

The Task Card controls scope; current code and tests remain implementation facts.
Contradictions must be escalated to the Parent rather than guessed around.

## Risk and assurance mapping

Classify each task:

### M1 — local and reversible

- clear goal and files
- stable contract
- known tests

Default execution intensity: lean.
Typical flow: Parent direct or one Executor, then Parent review.

### M2 — cross-layer but contractable

- interfaces can be frozen first
- implementation is mechanical after Parent decisions

Default execution intensity: standard.
Typical flow: Parent contract → one Executor by default → Parent semantic review.

### M3 — high-risk or irreversible

- architecture, migration, security, authorization, time semantics,
  source-of-truth, or destructive deletion
- failure could corrupt data or create duplicate official systems

Default execution intensity: assurance.
Typical flow: Parent-led work, with mini only for tightly bounded support.

The Parent may override the default intensity only with a written reason.

## Agent budget

Default soft budget:

```text
Normal task:             0–1 subagent
Independent write work:  up to 2 Executors
Large read-only audit:   up to 3 Explorers
```

Exceeding the default budget requires explicit Parent justification.
This is a soft budget, not a universal hard cap.

Prefer read-heavy delegation before parallel writes. Parallel implementation is
allowed only when paths and public contracts do not overlap.

## Task Card

Every delegated Task Card must include:

- task ID, title, risk level, and single objective
- prerequisites and dependency IDs
- baseline commit or upstream handoff
- applicable instructions and required reading
- approved/frozen contracts
- allowed and forbidden paths
- implementation requirements
- test, lint, build, and migration commands
- acceptance criteria
- escalation conditions
- required structured handoff

Do not send a child only a broad instruction such as `implement this stage`.
Do not require every child to reread the full repository TaskList and all global
design documents.

## Workflow

### 1. Understand

- read the selected task and repository rules
- inspect branch, baseline, dirty changes, and current implementation
- use 0–3 Explorers only for independent investigations that pass the gates
- consolidate verified evidence

### 2. Decide and freeze

The Parent defines target behavior, official facts, retained/migrated/retired
paths, public contracts, data relationships, migration/rollback rules,
dependency order, and acceptance evidence.

Write durable contracts when multiple agents or sessions depend on them.

### 3. Create Task Cards

Create only cards whose boundaries and prerequisites are ready.

### 4. Execute by dependency batch

- start only ready tasks
- parallelize only non-overlapping work
- wait for the batch
- inspect the shared worktree and actual diff
- resolve conflicts before the next batch
- never accept only a child completion message

### 5. Review

The Parent reviews behavior, cross-layer consistency, migrations, source-of-truth
uniqueness, traceability, errors and partial states, test quality, retirement
conditions, unrelated changes, and scope drift.

Classify findings as BLOCKER, HIGH, MEDIUM, or LOW. Clear BLOCKER and required
HIGH findings before acceptance.

### 6. Accept

A task or stage is complete only when the observable flow works, relevant layers
agree, required verification actually ran, migration/compatibility behavior is
verified when applicable, no unexplained blocker remains, no duplicate official
fact source was introduced, and documentation/handoff is current.

## Parallel safety

Parallel execution requires all of:

- allowed paths do not overlap, or overlap is read-only
- public contracts are not modified by multiple tasks
- neither task depends on the other's uncommitted output
- integration order is known
- rollback is possible

Always serialize domain model → migration → API/schema → generated/frontend
types → integration tests, shared routes/state stores, and deletion/compatibility
removal.

## Context and token efficiency

- the Parent reads global instructions and architecture documents
- children receive Task Cards, applicable instructions, frozen contracts,
  scoped files, tests, and upstream handoffs
- do not send full repository history or unrelated global documents to children
- combine implementation, tests, and mechanical self-review in one Executor
- summarize logs while retaining exact failing commands and key errors
- use one Parent session per bounded stage or task group, not one permanent
  project session
- prefer one meaningful child over many tiny children

## Runtime probe

Run before the first delegated task in a repository and after Codex/agent
configuration changes:

```bash
bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh
```

The probe checks expected readiness, not proof of actual child model or effective
permissions. Record only verified runtime facts.

## Fix-round limit

For one delegated task:

```text
Round 1: initial implementation
Round 2: targeted correction
Round 3: final bounded correction
```

After three failed or incomplete rounds, stop, mark the task blocked, preserve
artifacts, and return control to the Parent or user. Do not broaden scope to
force completion.

## Artifacts

For substantial work, use:

```text
.codex/refactor-state/<stage-id>/
├── stage-plan.md
├── manifest.yaml
├── contracts/
├── tasks/
├── handoffs/
├── reviews/
└── artifacts/
```

For every implementation/fix round, preserve diff, tests, status, result, and
review evidence when practical. Use the bundled templates and scripts.

## Single-controller fallback

Use fallback when native subagents are unavailable, child spawning fails, or a
required permission boundary cannot be guaranteed:

1. keep the Parent as the only active controller
2. produce the same plan, contracts, Task Cards, and handoffs
3. do not pretend mini subagents were used
4. execute directly, provide manual mini-session commands, or defer
5. return all diffs and evidence to the Parent for review

Fallback preserves the workflow but reduces automation.
