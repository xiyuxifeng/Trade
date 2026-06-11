---
name: refactor-orchestrator
description: >
  Orchestrate staged software refactors with a GPT-5.5 parent agent and
  GPT-5.4 mini subagents. Use for repository audits, staged plans,
  bounded implementation task cards, dependency-aware delegation,
  mechanical verification, semantic review, migration control, and
  final stage acceptance.
---

# Refactor Orchestrator

## Purpose

Coordinate a staged refactor without placing architecture decisions,
implementation, testing, and acceptance into one long agent context.

Default execution model:

```text
GPT-5.5 parent agent
├── refactor_explorer_mini: optional read-only investigation
├── refactor_executor_mini: bounded implementation + tests
└── GPT-5.5 parent: semantic review + stage acceptance
```

This Skill is project-agnostic. Project-specific paths, task lists, contracts,
test commands, and acceptance criteria must be discovered from the target
repository or explicitly provided by the user.

## Required inputs

Before planning, identify:

- repository root
- repository instructions, including `AGENTS.md` or equivalent
- source task list, issue, specification, or requested stage
- current branch and baseline commit
- project test, lint, typecheck, migration, and build commands
- applicable architecture or product documents
- previous stage handoff, if any

If no formal task list exists, create a temporary stage plan from the user's
request and current repository evidence.

## Agent bootstrap

Before spawning subagents:

1. Verify these project-level agent files exist:
   - `.codex/agents/refactor-explorer-mini.toml`
   - `.codex/agents/refactor-executor-mini.toml`
2. Verify both explicitly declare `model = "gpt-5.4-mini"`.
3. Verify Explorer defaults to `read-only`.
4. Verify Executor defaults to `workspace-write`.
5. Confirm the parent session was started with GPT-5.5 when that model policy is required.
   If the active parent model cannot be verified, state the assumption and do not claim
   that the GPT-5.5 + mini policy is enforced.
6. Do not silently replace either subagent with the parent model.
7. Keep subagent depth at 1. Do not allow subagents to create subagents.
8. Treat sandbox settings in custom-agent TOML as defaults. Runtime permission overrides
   on the parent session may supersede them. For strict read-only investigation, confirm
   the spawned Explorer's effective permissions and do not run the parent with unrestricted
   write permissions such as a full-access/yolo mode.

If the files are missing, report the missing bootstrap configuration and create
them only when the current task authorizes repository file changes.

## Explicit delegation rule

The parent agent must:

```text
Choose and explicitly spawn the configured custom subagents according
to this Skill's delegation rules.
Do not rely on implicit delegation.
Use the minimum viable number of agents.
```

This does not require spawning subagents for every task. When the minimum
viable number is zero, the parent should complete the local task directly.
When delegation is appropriate, the parent must explicitly spawn the named
custom agent rather than merely suggesting that a subagent could be used.

## Parent-agent responsibilities

The GPT-5.5 parent agent owns:

- scope interpretation
- repository-level investigation strategy
- architecture and source-of-truth decisions
- domain, API, data, version, migration, and rollback contracts
- dependency graph and execution batches
- task risk classification
- deciding which tasks may be delegated
- review of actual code diff and verification output
- stage exit decision
- updating the authoritative task list only after acceptance

The parent must not delegate unresolved architecture decisions to mini.

## Subagent responsibilities

### `refactor_explorer_mini`

Use only when meaningful repository investigation is needed.

Good uses:
- locate current routes, APIs, models, jobs, workflows, schemas, prompts, tests
- trace call and data flow
- find legacy or duplicate paths
- identify current source-of-truth
- inspect migration history
- inspect affected references before deletion

Avoid spawning Explorer when:
- the exact files and call chain are already known
- the task is a small, isolated edit
- the parent can answer by reading a few files directly

### `refactor_executor_mini`

Use only after the task has a frozen boundary.

Good uses:
- bounded CRUD and API implementation
- UI components and pages based on an approved contract
- ORM and migration implementation after design approval
- deterministic scripts
- tests, fixtures, lint, type checks, and local mechanical fixes
- reference cleanup after deletion has been approved
- documentation updates tied to completed behavior

Do not delegate:
- unresolved domain modeling
- source-of-truth selection
- public contract redesign
- migration policy decisions
- security or authorization policy decisions
- algorithm semantics that are not fully specified
- final acceptance

## Risk classification

Classify each task:

### M1 — mini-led

Use when:
- goal and files are clear
- contract is stable
- change is local and reversible
- test command is known

Flow:
`Executor mini → parent batch review`

### M2 — parent design, mini implementation

Use when:
- implementation is mechanical after a contract decision
- change crosses layers but interfaces can be frozen first

Flow:
`Parent contract → Executor mini → parent semantic review`

### M3 — parent-led

Use when:
- architecture, migration, security, time semantics, source-of-truth,
  or irreversible deletion is involved
- failure could corrupt data or create duplicate official systems

Flow:
`Parent implementation/review`, with mini only for tightly bounded support.

## Stage workflow

### Phase 1 — Understand

1. Read the selected stage or request.
2. Read repository rules.
3. Inspect the current branch and uncommitted changes.
4. Identify existing implementation and facts.
5. Spawn 0–3 Explorer mini agents only for independent, non-overlapping
   investigations.
6. Wait for all explorers in the current investigation batch.
7. Consolidate verified evidence.

### Phase 2 — Decide and freeze

The parent defines:

- target behavior
- retained, migrated, merged, and retired paths
- official source-of-truth
- approved public contracts
- data and version relationships
- migration, rollback, and compatibility rules
- dependency order
- acceptance evidence

Write durable decisions to a contract or stage-plan file when the work spans
multiple subagents.

### Phase 3 — Create task cards

Every delegated task card must include:

- task ID and title
- risk level
- single objective
- prerequisites and dependency IDs
- baseline commit or upstream handoff
- required reading
- approved contracts
- allowed paths
- forbidden paths
- implementation requirements
- test, lint, build, and migration commands
- acceptance criteria
- escalation conditions
- required structured handoff

Do not spawn a subagent with only a broad instruction such as
"implement this stage".

### Phase 4 — Execute by dependency batch

1. Spawn only tasks whose prerequisites are complete.
2. Parallelize only tasks that do not change the same files or contracts.
3. Limit normal batches to 1–3 Executor agents.
4. Wait for every agent in the batch.
5. Inspect the shared workspace and actual diff.
6. Resolve conflicts before starting the next batch.
7. Do not rely solely on an agent's completion claim.

### Phase 5 — Review

The GPT-5.5 parent reviews:

- behavior against the original requirement
- frontend/backend/database/runtime contract consistency
- migration and rollback correctness, when persistent data or durable contracts are affected
- source-of-truth uniqueness
- traceability and reproducibility
- error and partial-state handling
- test quality, not only test pass status
- legacy retirement conditions
- unrelated changes and scope drift

Classify findings:
- BLOCKER
- HIGH
- MEDIUM
- LOW

Clear BLOCKER and required HIGH findings before stage acceptance.

### Phase 6 — Stage acceptance

A stage is complete only when:

- the externally observable user or system flow works
- all relevant layers agree
- required tests actually ran and passed
- migration/compatibility behavior is verified when applicable
- no unexplained blocker remains
- no duplicate official entry point/schema/source-of-truth was introduced
- documentation and handoff are updated
- the result is reviewable and reproducible

Do not mark a stage complete merely because implementation tasks returned
`completed`.

## Synchronization model

Agents synchronize through:

1. Parent-to-child task messages.
2. Shared repository files and Git diff.
3. Durable stage plan, contract, task card, and handoff files.
4. Structured child result messages.
5. Parent-controlled dependency batches.

Subagents do not automatically share the parent's full reasoning context.
Always pass the necessary approved facts and file references explicitly.

Use the parent as the coordination hub:

```text
child reports conflict
→ parent decides
→ parent updates contract/task card
→ parent sends new instruction
```

Avoid direct, uncontrolled contract negotiation between subagents.

## Parallel-safety rules

Parallel execution is allowed only when all are true:

- allowed paths do not overlap, or overlap is explicitly read-only
- tasks do not modify the same public contract
- neither task depends on the other's uncommitted output
- integration order is known
- rollback is possible

Use serial execution for:
- domain model → migration → API/schema
- shared database tables
- shared routing or state stores
- schema and generated clients
- deletions and compatibility removal

## Token-efficiency rules

- Do not spawn an Explorer for a known, local task.
- Combine implementation, tests, and mechanical self-review in Executor.
- Do not send entire repository history to subagents.
- Pass only relevant task cards, contracts, files, and upstream handoffs.
- Keep logs summarized; retain exact failing commands and key errors.
- Use one parent Stage session rather than one permanent project session.
- Use independent GPT-5.5 review for very large or high-risk stages when the
  parent planning session has become too long.
- Prefer 1–3 meaningful subagents over many tiny subagents.

## Required artifacts

For substantial stages, use:

```text
<state-root>/<stage-id>/
├── stage-plan.md
├── manifest.yaml
├── contracts/
├── tasks/
├── handoffs/
└── reviews/
```

Default `<state-root>`:
- `.codex/refactor-state/` for temporary execution records, or
- a project documentation path when records must be versioned.

Use templates bundled with this Skill.


## Minimum viable lanes

Use the fewest agents that can safely complete the work.

Defaults:

```text
Known local task:
0 Explorer
1 Executor

Unknown cross-module task:
1–3 Explorer agents
then 1 Executor by default

Parallel implementation:
only when paths and contracts do not overlap
```

Do not spawn agents merely because subagents are available.

## Runtime probe

Before the first delegated task in a repository or after a Codex upgrade:

1. Run:
   `bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh`
2. Confirm in the active session:
   - parent model is GPT-5.5
   - this Skill is discovered
   - custom agents are discovered
   - native subagent spawning is available
   - spawned agents use GPT-5.4 mini
   - Explorer effective permissions are read-only
3. Record the result using `templates/runtime-probe-report.md`.

A static configuration file is not proof that the runtime used the expected model or permission.

## Fix-round limit

For one delegated task:

```text
Round 1: initial implementation
Round 2: targeted correction
Round 3: final bounded correction
```

After three failed or incomplete rounds:

- stop spawning fixes
- mark the task blocked
- preserve all artifacts
- return control to GPT-5.5 or the user
- do not broaden scope to force completion

The parent may set a lower limit for expensive or risky work.

## Per-round artifacts

For every implementation or fix round, preserve:

```text
artifacts/<task-id>/
├── <task-id>.round-<n>.changes.diff
├── <task-id>.round-<n>.tests.log
├── <task-id>.round-<n>.status.txt
├── <task-id>.round-<n>.result.md
└── <task-id>.round-<n>.review.md
```

Use:

```bash
bash .agents/skills/refactor-orchestrator/scripts/capture-round-artifacts.sh <task-id> <round>
```

Artifacts provide evidence for review and allow work to resume without replaying the full conversation.

## Single-controller fallback

If native subagents are unavailable, custom-agent models cannot be verified,
or runtime permissions cannot be trusted:

1. Keep GPT-5.5 as the only active controller.
2. Produce the same Stage plan, contracts, task cards, and handoffs.
3. Do not pretend that mini subagents were used.
4. Generate explicit commands for manual mini sessions, for example:

```bash
codex -m gpt-5.4-mini
```

5. Execute each task card in a separate mini session or defer execution.
6. Return completed diffs and handoffs to a GPT-5.5 review session.

Fallback preserves the workflow but may reduce automation.

## Runtime truth rule

Never claim:

- a subagent was spawned
- a specific model was used
- a sandbox was enforced
- tests passed
- a task completed

unless runtime evidence exists.
