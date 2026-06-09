# Profile-Only Web Config Strong Receipt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Web use `Profile` as the only正式配置语义 after import, while keeping `config/app.yaml` and `config/app.template.yaml` only as import sources and preserving CLI `config_path` for debugging.

**Architecture:** Web pages and API payloads should prefer `profile_id`/`profile_snapshot_id` everywhere. The backend should resolve runtime config from Profile snapshots first, fall back to `config_path` only in CLI/debug compatibility paths, and expose clear payloads so the UI can avoid ambiguous config-path language. `config/app.yaml` and `config/app.template.yaml` remain valid import inputs, but once imported the persisted identity is `config_profiles.profile_id` plus its snapshots.

**Tech Stack:** Python/FastAPI/SQLAlchemy on the backend, React/TypeScript on the web, pytest/vitest for tests, Markdown docs in `docs/`.

---

### Task 1: Lock the backend contract around Profile as the primary runtime identity

**Files:**
- Modify: `src/services/job_runner.py`
- Modify: `src/services/config_profile_service.py`
- Modify: `src/services/job_service.py`
- Modify: `src/services/runtime_config.py`
- Modify: `src/services/config_service.py`
- Modify: `src/services/defaults.py`
- Test: `tests/unit/services/test_job_runner.py`
- Test: `tests/unit/services/test_config_profile_service.py`
- Test: `tests/unit/services/test_workflow_run_service.py`
- Test: `tests/unit/services/test_article_pipeline_schedule_service.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_profile_id_is_preferred_over_config_path(monkeypatch):
    # job_runner should resolve profile_id first and only use config_path as fallback
    ...

def test_profile_import_supports_template_sources(tmp_path):
    # importing config/app.template.yaml should create a Profile and snapshot
    ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/services/test_job_runner.py tests/unit/services/test_config_profile_service.py -v`
Expected: FAIL because the strong profile-only contract is not fully enforced yet.

- [ ] **Step 3: Implement the minimal backend changes**

```python
# in job_runner.py
def _resolve_profile_config_path(...):
    # prefer profile_id; accept config_path only for CLI/debug compatibility
    ...

# in config_profile_service.py
def resolve_profile_config_path(...):
    # resolve from latest profile snapshot first, then fall back only for compatibility
    ...
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/unit/services/test_job_runner.py tests/unit/services/test_config_profile_service.py tests/unit/services/test_workflow_run_service.py tests/unit/services/test_article_pipeline_schedule_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/job_runner.py src/services/config_profile_service.py src/services/job_service.py src/services/runtime_config.py src/services/config_service.py src/services/defaults.py tests/unit/services/test_job_runner.py tests/unit/services/test_config_profile_service.py tests/unit/services/test_workflow_run_service.py tests/unit/services/test_article_pipeline_schedule_service.py
git commit -m "feat(profile): make profile the primary web runtime config"
```

### Task 2: Make the Web UI profile-first and remove config-path ambiguity

**Files:**
- Modify: `web/src/features/workflows/workflow-presets.ts`
- Modify: `web/src/features/workflows/workflow-form-utils.ts`
- Modify: `web/src/features/workflows/workflow-parameter-form.tsx`
- Modify: `web/src/features/workflows/workflow-center.tsx`
- Modify: `web/src/features/backtest/backtest-center.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-shell.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`
- Modify: `web/src/features/system-management/system-management-workspace.tsx`
- Modify: `web/src/pages/profiles/ProfileImportPage.tsx`
- Modify: `web/src/pages/profiles/ProfileDetailPage.tsx`
- Modify: `web/src/pages/profiles/ProfileSnapshotPage.tsx`
- Modify: `web/src/pages/jobs/JobDetailPage.tsx`
- Modify: `web/src/pages/articles/ArticlePipelinePage.tsx`
- Modify: `web/src/pages/backtest/index.tsx`
- Modify: `web/src/pages/backtest/RegimeBacktestReportPage.tsx`
- Modify: `web/src/lib/api/jobs.ts`
- Modify: `web/src/lib/api/workflows.ts`
- Modify: `web/src/lib/api/market.ts`
- Modify: `web/src/lib/api/profiles.ts`
- Modify: `web/src/components/profiles/ConfigSnapshotPanel.tsx`
- Modify: `web/src/components/jobs/JobProgress.tsx`
- Modify: `web/src/components/jobs/StepTimeline.tsx`
- Test: `web/src/pages/profiles/ProfileImportPage.test.tsx`
- Test: `web/src/pages/profiles/ProfileSnapshotPage.test.tsx`
- Test: `web/src/pages/jobs/JobDetailPage.test.tsx`
- Test: `web/src/pages/articles/index.test.tsx`
- Test: `web/src/pages/backtest/index.test.tsx`
- Test: `web/src/features/workflows/workflow-parameter-form.test.tsx`
- Test: `web/src/features/system-management/system-management-workspace.test.tsx`

- [ ] **Step 1: Write the failing UI contract tests**

```tsx
test('workflow defaults resolve profile_id and do not surface config_path in web primary flows', async () => {
  ...
});

test('import page accepts app.yaml and app.template.yaml and creates a profile', async () => {
  ...
});
```

- [ ] **Step 2: Run the UI tests to verify they fail**

Run: `cd web && pnpm test -- src/pages/profiles/ProfileImportPage.test.tsx src/features/workflows/workflow-parameter-form.test.tsx`
Expected: FAIL because the UI still exposes config_path defaults in several flows.

- [ ] **Step 3: Implement the minimal UI changes**

```tsx
// prefer profileId selection in forms
// hide config_path from primary workflow pages
// keep config_path only on import/debug surfaces
```

- [ ] **Step 4: Run the UI tests to verify they pass**

Run: `cd web && pnpm test -- src/pages/profiles/ProfileImportPage.test.tsx src/features/workflows/workflow-parameter-form.test.tsx src/pages/jobs/JobDetailPage.test.tsx src/pages/backtest/index.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/workflows web/src/features/backtest web/src/features/market-workspace web/src/features/strategy-workspace web/src/features/system-management web/src/pages/profiles web/src/pages/jobs web/src/pages/articles web/src/pages/backtest web/src/lib/api web/src/components/profiles web/src/components/jobs
git commit -m "feat(web): make profile the only primary runtime config"
```

### Task 3: Update user-facing docs and maintenance docs to state the new contract clearly

**Files:**
- Modify: `docs/Preview.md`
- Modify: `docs/web-deployment-operation.md`
- Modify: `docs/web-deployment-operation-gen2.md`
- Modify: `docs/web-user-manual.md`
- Modify: `docs/web-user-manual-gen2.md`
- Modify: `docs/APIReference.md`
- Modify: `docs/Deprecated/使用说明.md`
- Modify: `README.md`
- Modify: `config/app.template.yaml` comments if needed

- [ ] **Step 1: Write the failing doc checks**

```text
Search for "config_path is the primary source" style wording and replace with:
- app.yaml/app.template.yaml are import sources
- Profile is the formal runtime identity
- CLI can still use config_path for debugging
```

- [ ] **Step 2: Review the docs to find all stale wording**

Run: `rg -n "config_path|app\.yaml|app\.template\.yaml|Profile snapshot|正式配置" docs README.md`
Expected: locate the pages that still imply config_path is the main runtime identity.

- [ ] **Step 3: Update the docs**

```markdown
- user docs: explain import -> profile -> profile_snapshot -> jobs
- maintenance docs: explain CLI debug-only config_path compatibility
- preview docs: say the template file may be imported as well
```

- [ ] **Step 4: Run a consistency search**

Run: `rg -n "config_path|app\.yaml|app\.template\.yaml" docs README.md`
Expected: only import/debug/template references remain, not primary runtime-sourcing language.

- [ ] **Step 5: Commit**

```bash
git add docs README.md config/app.template.yaml
git commit -m "docs(profile): clarify profile-only web runtime contract"
```

### Task 4: Clean up the remaining compatibility edges and verify end-to-end behavior

**Files:**
- Modify: `tests/api/routers/test_workflows.py`
- Modify: `tests/api/routers/test_jobs.py`
- Modify: `tests/api/routers/ui/test_ui_profiles.py`
- Modify: `tests/api/test_ui_openapi_contract.py`
- Modify: `tests/unit/cli/test_backtest.py`
- Modify: `tests/unit/cli/test_main.py`
- Modify: `tests/unit/services/test_job_service.py`
- Modify: `tests/unit/services/test_config_profile_service.py`

- [ ] **Step 1: Add regression tests for template imports**

```python
def test_import_accepts_app_template_yaml():
    ...
```

- [ ] **Step 2: Run the targeted regression tests**

Run: `python -m pytest tests/api/routers/test_workflows.py tests/api/routers/test_jobs.py tests/api/test_ui_openapi_contract.py tests/unit/services/test_config_profile_service.py -v`
Expected: PASS.

- [ ] **Step 3: Run the web test slice**

Run: `cd web && pnpm test -- src/pages/profiles/ProfileImportPage.test.tsx src/pages/profiles/ProfileDetailPage.test.tsx src/pages/jobs/JobDetailPage.test.tsx src/features/backtest/index.test.tsx`
Expected: PASS.

- [ ] **Step 4: Final full verification**

Run:
`python -m pytest tests/unit/services/test_job_runner.py tests/unit/services/test_config_profile_service.py tests/unit/services/test_workflow_run_service.py tests/unit/services/test_article_pipeline_schedule_service.py tests/api/routers/test_workflows.py tests/api/routers/test_jobs.py tests/api/test_ui_openapi_contract.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/api/routers tests/api tests/unit/cli tests/unit/services
git commit -m "test(profile): lock profile-only web runtime contract"
```

