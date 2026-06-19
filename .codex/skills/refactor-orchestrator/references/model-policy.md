# Model Policy

## GPT-5.5 parent

Use for:
- architecture and source-of-truth decisions
- cross-module planning
- public contract design
- database/version/migration policy
- security and permission semantics
- irreversible deletion
- semantic review
- stage acceptance

## GPT-5.4 mini Explorer

Use for:
- read-only codebase investigation
- call-chain tracing
- current-state inventory
- reference and test discovery

## GPT-5.4 mini Executor

Use for:
- bounded implementation after contract freeze
- tests and fixtures
- lint/type/build verification
- local mechanical fixes
- documentation tied to implemented behavior

## Risk defaults

- M1: local, explicit, reversible
- M2: parent freezes contract, mini implements
- M3: parent owns core implementation and review
