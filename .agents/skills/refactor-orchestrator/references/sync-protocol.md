# Agent Synchronization Protocol

## Canonical synchronization channels

1. Task message from parent to child.
2. Shared working tree.
3. Versioned or temporary execution artifacts.
4. Structured result returned by child.
5. Parent review of actual diff.

## Rules

- The parent is the only architecture decision-maker.
- Children must not depend on unstated parent reasoning.
- Every child receives approved contracts and scope explicitly.
- Dependent tasks run in separate batches.
- A blocked child reports the conflict; it does not redesign around it.
- Parent inspects `git status`, `git diff`, and verification results after each batch.
- Child success messages are evidence, not acceptance decisions.
