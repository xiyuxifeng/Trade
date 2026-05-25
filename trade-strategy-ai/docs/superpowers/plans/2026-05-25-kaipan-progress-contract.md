# Kaipan Date-Range Progress Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `kaipan-fetch` and `kaipan-normalize` expose real date-range progress through the job contract so the UI can show current date, step, and remaining work.

**Architecture:** Store progress as structured job state in the database, not as a file sidecar. `JobService` becomes the canonical read/write layer for progress, `JobRunner` orchestrates Kaipan range execution, and `KaipanService` remains the single-day execution primitive that the runner can call repeatedly with progress updates. The UI will consume the new optional field later, but this plan only establishes the backend contract.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, pytest, existing Kaipan and Job runtime services.

---

### Task 1: Add persistent job progress contract

**Files:**
- Modify: `src/models/job.py`
- Modify: `src/services/job_service.py`
- Modify: `src/services/job_registry.py`
- Modify: `api/routers/ui/jobs.py`
- Create: `src/db/migrations/versions/<new_migration>_add_job_progress.py`
- Test: `tests/unit/services/test_job_service.py`
- Test: `tests/api/routers/ui/test_jobs.py`

- [x] **Step 1: Write failing tests**
  - Assert `JobRecord` API payload includes `progress: null` for existing jobs.
  - Assert `JobService` serialization includes an empty progress field without breaking existing consumers.
  - Assert a migration-visible `jobs.progress` field can be round-tripped in ORM serialization.

- [x] **Step 2: Run the targeted tests and verify they fail**
  - Run: `pytest tests/unit/services/test_job_service.py tests/api/routers/ui/test_jobs.py -q`
  - Expected: failures about missing `progress` field or serialization mismatch.

- [x] **Step 3: Implement the minimum schema and serialization changes**
  - Add a nullable JSON progress column to `jobs`.
  - Surface `progress` in `_serialize_job()` and list/detail payloads.
  - Keep the field optional so existing jobs continue to deserialize.

- [x] **Step 4: Run the targeted tests again**
  - Run: `pytest tests/unit/services/test_job_service.py tests/api/routers/ui/test_jobs.py -q`
  - Expected: pass.

### Task 2: Wire Kaipan range progress into the job runner

**Files:**
- Modify: `src/services/job_registry.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/services/kaipan_service.py`
- Test: `tests/unit/services/test_job_runner.py`
- Test: `tests/unit/services/test_kaipan_service.py`

- [x] **Step 1: Write failing tests**
  - Assert `kaipan-fetch` and `kaipan-normalize` accept `start_date` and `end_date` in job validation.
  - Assert a date range with the same start and end only processes that single day.
  - Assert range execution emits progress updates with `current`, `total`, `percent`, `remaining`, and current date/slot metadata.

- [x] **Step 2: Run the targeted tests and verify they fail**
  - Run: `pytest tests/unit/services/test_job_runner.py tests/unit/services/test_kaipan_service.py -q`
  - Expected: failures showing range params or progress hooks are not yet implemented.

- [x] **Step 3: Implement the runner and service changes**
  - Extend the Kaipan param schemas with `start_date` and `end_date`.
  - Keep `trade_date` as a compatibility input, but derive the effective range from `start_date/end_date` when present.
  - Update `KaipanService` execution so one job can iterate trade dates and report progress after each day, slot, fetcher, and dataset step.
  - Keep `kaipan-run` on today-only scheduler semantics.

- [x] **Step 4: Run the targeted tests again**
  - Run: `pytest tests/unit/services/test_job_runner.py tests/unit/services/test_kaipan_service.py -q`
  - Expected: pass.

### Task 3: Verify API behavior and close the contract

**Files:**
- Modify: `tests/api/routers/ui/test_jobs.py`
- Modify: `docs/superpowers/specs/2026-05-25-job-progress-coverage-review.md`
- Optional: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md` only if the project decides to track this work there later

- [x] **Step 1: Write failing integration-style assertions**
  - Assert the `/api/ui/v1/jobs` list/detail payloads include the new `progress` field for Kaipan jobs.
  - Assert jobs without progress still return a valid payload with `progress: null`.

- [x] **Step 2: Run the targeted test and verify it fails**
  - Run: `pytest tests/api/routers/ui/test_jobs.py -q`
  - Expected: API contract mismatch until serialization is wired through.

- [x] **Step 3: Finish the contract and document the behavior**
  - Make sure list/detail payloads carry the same progress shape.
  - Update the Kaipan progress spec so the backend contract matches the implemented behavior.

- [x] **Step 4: Run the verification suite**
  - Run: `pytest tests/unit/services/test_job_service.py tests/unit/services/test_job_runner.py tests/unit/services/test_kaipan_service.py tests/api/routers/ui/test_jobs.py -q`
  - Expected: all pass.

---

## Self-Review

- The plan covers the spec requirement that progress must be database-backed and exposed through the job contract.
- The plan keeps `kaipan-run` on the existing today-only scheduler behavior.
- The plan does not add UI work, because `NW-KAIPAN-PROGRESS-002` is a separate task.
- No placeholder steps remain; each task maps to concrete files and tests.
- Verification passed on the targeted suite: `55 passed`.
