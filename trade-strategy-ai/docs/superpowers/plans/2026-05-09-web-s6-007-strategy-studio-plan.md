# Strategy Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a single `Strategy Studio` workspace that lets users browse strategy versions, generate candidate optimization versions, and review the rule pool from one page.

**Architecture:** Add a dedicated UI BFF at `/api/ui/v1/strategy-studio` that adapts existing strategy/optimization/rule-pool services into UI-friendly JSON. On the frontend, build a data-dense three-panel workspace with a compact API client and typed models, then wire the page into the existing router and navigation.

**Tech Stack:** FastAPI, Pydantic, React, React Router, Vitest, TypeScript, existing project `fetchJson` / `fetchRootJson` client helpers.

---

### Task 1: Add the Strategy Studio UI BFF

**Files:**
- Create: `api/routers/ui/strategy_studio.py`
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/app.py`
- Test: `tests/api/routers/ui/test_strategy_studio.py`

- [ ] **Step 1: Write the failing test**

Create tests that assert the new UI router can:
- list versions with filters and pagination
- load a single version detail
- list rules with `status`, `rule_type`, `mapping_status`, `source_type`, `instrument_focus`, `skip_no_mapped`, `skip`, `limit`
- review one rule
- review a batch of rules
- accept a candidate-generation payload without exposing file paths

Run: `pytest tests/api/routers/ui/test_strategy_studio.py -q`
Expected: fail because the router does not exist yet.

- [ ] **Step 2: Run the failing test**

Confirm the test fails for the missing module / missing router path.

- [ ] **Step 3: Write the minimal implementation**

Implement the router with `verify_api_key` protection and service adapters for:
- `GET /api/ui/v1/strategy-studio/versions`
- `GET /api/ui/v1/strategy-studio/versions/{version_id}`
- `POST /api/ui/v1/strategy-studio/optimize/advise-rule-validations`
- `POST /api/ui/v1/strategy-studio/optimize/filter-active-traders`
- `POST /api/ui/v1/strategy-studio/optimize/create-candidate`
- `GET /api/ui/v1/strategy-studio/rule-pool`
- `GET /api/ui/v1/strategy-studio/rule-pool/{rule_id}`
- `POST /api/ui/v1/strategy-studio/rule-pool/{rule_id}/review`
- `POST /api/ui/v1/strategy-studio/rule-pool/review-batch`

Register the router in `api/routers/ui/__init__.py` and `api/app.py`.

- [ ] **Step 4: Run the test again**

Run: `pytest tests/api/routers/ui/test_strategy_studio.py -q`
Expected: PASS.

- [ ] **Step 5: Verify router registration**

Run: `pytest tests/api/routers/ui/test_strategy_studio.py -q && python - <<'PY'
from api.app import app
print(any(getattr(r, 'prefix', '') == '/api/ui/v1/strategy-studio' for r in app.router.routes))
PY`
Expected: test passes and the printed value is `True`.

### Task 2: Add frontend types and API client

**Files:**
- Create: `web/src/types/strategyStudio.ts`
- Create: `web/src/lib/api/strategyStudio.ts`
- Create: `web/src/lib/api/strategyStudio.test.ts`

- [ ] **Step 1: Write the failing test**

Create API client tests that verify:
- version list requests hit `/api/ui/v1/strategy-studio/versions`
- version detail requests hit `/api/ui/v1/strategy-studio/versions/{version_id}`
- candidate creation posts a UI-friendly JSON payload
- rule review posts to the correct rule-pool endpoint
- batch review posts to `/api/ui/v1/strategy-studio/rule-pool/review-batch`

Run: `pnpm test src/lib/api/strategyStudio.test.ts`
Expected: fail because the module does not exist yet.

- [ ] **Step 2: Write the minimal implementation**

Implement typed request/response models and client helpers using the existing `fetchJson` / `fetchRootJson` patterns.

- [ ] **Step 3: Run the API client test again**

Run: `pnpm test src/lib/api/strategyStudio.test.ts`
Expected: PASS.

- [ ] **Step 4: Run typecheck for the new types**

Run: `pnpm typecheck`
Expected: PASS.

### Task 3: Build the Strategy Studio page

**Files:**
- Create: `web/src/features/strategy-studio/strategy-studio.tsx`
- Create: `web/src/pages/strategy-studio/index.tsx`
- Create: `web/src/pages/strategy-studio/index.test.tsx`
- Modify: `web/src/app/router.tsx`

- [ ] **Step 1: Write the failing test**

Add a page test that covers:
- initial empty state for versions and rules
- selecting a version updates the detail panel
- submitting candidate generation shows success feedback
- single rule review works from the rule pool panel
- batch review requires confirmation and then submits

Run: `pnpm test src/pages/strategy-studio/index.test.tsx`
Expected: fail because the page does not exist yet.

- [ ] **Step 2: Implement the page shell**

Build a three-panel workspace:
- left: version list and filters
- middle: selected version detail and optimization actions
- right: rule pool list and review actions

Use the existing dashboard page patterns, `Card`, `Tabs`, `Badge`, `Button`, `Input`, `Select`, `Textarea`, and `Skeleton`.

- [ ] **Step 3: Implement the page behaviors**

Wire the page to the new API client so it can:
- load versions
- load a selected version detail
- generate a candidate version
- list rule-pool entries
- load a rule detail
- review a rule
- batch review rules

- [ ] **Step 4: Run the page test again**

Run: `pnpm test src/pages/strategy-studio/index.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run local verification**

Run:
`pnpm test src/lib/api/strategyStudio.test.ts src/pages/strategy-studio/index.test.tsx && pnpm typecheck`
Expected: PASS.

### Task 4: Wire navigation and cleanup tasklist/docs

**Files:**
- Modify: `web/src/app/navigation.ts`
- Modify: `docs/Web-TaskList.md`
- Modify: `docs/superpowers/plans/2026-05-09-web-s6-007-strategy-studio-plan.md` if the scope changes during implementation

- [ ] **Step 1: Add the navigation entry**

Add a `Strategy Studio` nav item pointing to `/strategy-studio`, or repoint the existing strategy entry if that produces less clutter.

- [ ] **Step 2: Align the task list**

Update `WEB-S6-007` so its output and acceptance text match the new `Strategy Studio` workspace and BFF-backed implementation.

- [ ] **Step 3: Run repo verification**

Run:
`pnpm test src/lib/api/strategyStudio.test.ts src/pages/strategy-studio/index.test.tsx && pnpm typecheck && git diff --check`
Expected: PASS.

---

## Self-Review Checklist

1. Spec coverage:
- Strategy version browsing is covered by Task 1 and Task 3.
- Optimization candidate creation is covered by Task 1, Task 2, and Task 3.
- Rule pool list/detail/review is covered by Task 1, Task 2, and Task 3.
- Navigation and tasklist consistency is covered by Task 4.

2. Placeholder scan:
- No `TBD`, `TODO`, or vague follow-up steps are left in the plan.

3. Type consistency:
- `strategyStudio` is used consistently for the client, types, page, and router names.
- The BFF route prefix is consistently `/api/ui/v1/strategy-studio`.
