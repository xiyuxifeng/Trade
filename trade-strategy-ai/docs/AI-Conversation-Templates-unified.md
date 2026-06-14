# AI-Conversation-Templates (Unified)

> This document merges:
> - AI-Conversation-Templates.md
> - AI-Conversation-Stage-Gate-Addendum
> - Canonical Writer Runtime Baseline (Stage 2)

---

# 1. Core Execution Principle

All AI-driven execution must follow:

- Deterministic stage progression
- Frozen-contract enforcement per Stage Gate
- No implicit assumption of legacy compatibility after Stage 2 acceptance

---

# 2. Stage Gate Execution Model

## 2.1 Stage Lifecycle

Each Stage follows:

1. Bootstrap
2. Implementation Tasks (RT-SX-XXX)
3. Review Gate
4. Acceptance Decision
5. Handoff

No Stage may proceed without explicit ACCEPTED decision.

---

## 2.2 Gate Rules

A Stage Gate Review MUST:

- Stop on CONTRACT VIOLATION
- Emit ESCALATION_REQUIRED if frozen contract is violated
- NOT auto-fix unless explicitly instructed
- Preserve working tree unless repair stage is triggered

---

## 2.3 Bounded Auto-Repair Rule

If enabled in Addendum context:

- Only fix non-contract-breaking issues
- Never modify frozen schema or contract definitions
- Must re-run full verification after repair

---

# 3. Canonical Writer Runtime Baseline (Stage 2+)

## 3.1 Global Rule

STAGE2_CANONICAL_WRITER_ENABLED is the canonical writer enforcement switch.

### Default behavior (Stage 3+)

- MUST be treated as TRUE in all environments
- MUST NOT be disabled for convenience

---

## 3.2 Prohibited Usage of false

Setting:

```
STAGE2_CANONICAL_WRITER_ENABLED=false
```

is prohibited for:

- test bypass
- legacy compatibility
- partial migration
- development convenience
- failure workaround

---

## 3.3 Allowed Usage of false (strictly limited)

Only allowed when ALL conditions are met:

- Active production incident
- Canonical writer causes system/data corruption
- Explicit operator authorization exists
- Time-bounded rollback window defined
- Recovery plan documented

---

## 3.4 Mandatory Recovery Requirements

If false is used:

- Must log incident context
- Must isolate conflicting writers
- Must define restoration deadline
- Must return to true as soon as possible

---

## 3.5 Stage 12 Retirement Rule

At final Stage:

- Remove environment variable
- Remove false branch
- Remove legacy compatibility writer paths
- Convert enforcement into permanent hard constraint

---

# 4. Stage 2 → Stage 3 Transition Rule

Stage 3 MUST assume:

- Canonical writer is active
- Legacy writer is not authoritative
- No dual-write systems exist

If dual-write exists → BLOCK Stage 3

---

# 5. Contract Integrity Rules

## 5.1 Frozen Contract Rule

Once a Stage contract is ACCEPTED:

- It becomes immutable
- Cannot be modified without explicit escalation

---

## 5.2 Escalation Rule

ESCALATION_REQUIRED must be triggered when:

- schema mismatch detected
- writer mismatch detected
- dual-source-of-truth exists

---

# 6. Review Behavior Rules

- Reviews must be deterministic
- No hidden fixes allowed
- No silent contract modification
- All fixes must be explicit tasks (RT-SX-XXX)

---

# 7. System Architecture Target State

Final target architecture:

Application Service
→ Canonical Repository
→ Canonical Database

No legacy write path.
No feature-flag-dependent correctness.

---

# 8. Summary

- Stage Gates enforce contract immutability
- Canonical writer is mandatory from Stage 3 onward
- Stage 12 removes all transitional mechanisms
