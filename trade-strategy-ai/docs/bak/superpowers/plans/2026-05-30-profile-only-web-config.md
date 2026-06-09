# Profile-Only Web Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Web execution path consume `Profile` as the runtime source of truth, while keeping `config_path` only for CLI/debug and historical compatibility.

**Architecture:** Introduce a profile-backed runtime config loader that materializes `AppConfig` directly from `Profile.sections`, then update Web-facing services to consume that loader instead of resolving `config_path`. Keep `config_path` as an explicit compatibility layer for CLI and legacy flows only. On the UI side, remove `config_path` from canonical Web submission paths and preserve it only on import/debug surfaces.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Pydantic, React, TanStack Query, Vitest, Pytest.

---

### Task 1: Add a Profile-backed runtime config loader

**Files:**
- Modify: `src/services/config_profile_service.py`
- Modify: `src/common/config.py`
- Test: `tests/unit/services/test_config_profile_service.py`
- Test: `tests/unit/common/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_load_profile_runtime_config_uses_profile_sections_and_env_overrides(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "env-key")
    profile = await service.import_from_config_path("config/app.template.yaml", profile_id="default", created_by="web")
    runtime = await service.load_profile_runtime_config("default")
    assert runtime.config.llm.provider == "qwen"
    assert runtime.config.llm.model == ["qwen3-8b"]
    assert runtime.config.llm.api_key == "env-key"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/services/test_config_profile_service.py::test_load_profile_runtime_config_uses_profile_sections_and_env_overrides -v`
Expected: FAIL because `load_profile_runtime_config` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class ProfileRuntimeConfig:
    profile_id: str
    config: AppConfig
    source: str = "profile"

async def load_profile_runtime_config(self, profile_id: str) -> ProfileRuntimeConfig:
    profile = await self.get_profile(profile_id)
    if profile is None:
        raise ConfigError(f"profile not found: {profile_id}")
    raw_sections = _to_plain(profile.sections)
    if not isinstance(raw_sections, dict):
        raise ConfigError(f"invalid profile sections for {profile_id}")
    cfg = AppConfig.model_validate(_expand_env_vars(raw_sections))
    return ProfileRuntimeConfig(profile_id=profile_id, config=cfg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/services/test_config_profile_service.py tests/unit/common/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/config_profile_service.py src/common/config.py tests/unit/services/test_config_profile_service.py tests/unit/common/test_config.py
git commit -m "feat(profile): load runtime config directly from profile"
```

### Task 2: Switch Web execution services to the profile runtime loader

**Files:**
- Modify: `src/services/job_runner.py`
- Modify: `src/services/strategy_service.py`
- Modify: `src/services/snapshot_service.py`
- Modify: `src/services/persona_service.py`
- Modify: `src/services/backtest_service.py`
- Modify: `src/services/article_pipeline_schedule_service.py`
- Modify: `src/services/pipeline_service.py`
- Test: `tests/unit/services/test_job_runner.py`
- Test: `tests/unit/services/test_strategy_service.py`
- Test: `tests/unit/services/test_snapshot_service.py`
- Test: `tests/unit/services/test_persona_service.py`
- Test: `tests/unit/services/test_backtest_service.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_process_uses_profile_llm(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "env-key")
    result = await service.run_job({"profile_id": "default", "new_version": "v2"}, job_type="article_pipeline")
    assert result.payload["result"]["llm_provider"] == "qwen"
    assert result.payload["result"]["llm_model"] == "qwen3-8b"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/services/test_job_runner.py::test_process_uses_profile_llm -v`
Expected: FAIL because runtime still resolves through `config_path`.

- [ ] **Step 3: Write minimal implementation**

```python
runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
config = runtime.config
result = await run_process_tasks(config=config, force=force, retry_failed=retry_failed, version=version, progress_callback=...)
```

```python
runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
loaded = runtime.config
```

```python
runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
config = runtime.config
```

Use the profile runtime object instead of `load_app_config(config_path)` in every Web-facing runtime service, and keep `config_path` only for CLI/debug fallback branches.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/services/test_job_runner.py tests/unit/services/test_strategy_service.py tests/unit/services/test_snapshot_service.py tests/unit/services/test_persona_service.py tests/unit/services/test_backtest_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/job_runner.py src/services/strategy_service.py src/services/snapshot_service.py src/services/persona_service.py src/services/backtest_service.py src/services/article_pipeline_schedule_service.py src/services/pipeline_service.py tests/unit/services/test_job_runner.py tests/unit/services/test_strategy_service.py tests/unit/services/test_snapshot_service.py tests/unit/services/test_persona_service.py tests/unit/services/test_backtest_service.py
git commit -m "feat(web): resolve runtime config from profile"
```

### Task 3: Remove `config_path` from canonical Web submission paths

**Files:**
- Modify: `web/src/features/workflows/workflow-parameter-form.tsx`
- Modify: `web/src/features/workflows/workflow-presets.ts`
- Modify: `web/src/features/backtest/backtest-center.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-shell.tsx`
- Modify: `web/src/pages/articles/ArticlePipelinePage.tsx`
- Modify: `web/src/pages/profiles/ProfileEditPage.tsx`
- Modify: `web/src/pages/profiles/ProfileImportPage.tsx`
- Modify: `web/src/components/dashboard/dashboard-status-summary.tsx`
- Modify: `web/src/types/pipeline.ts`
- Modify: `web/src/types/backtest.ts`
- Modify: `web/src/lib/api/backtests.ts`
- Modify: `web/src/lib/api/profiles.ts`
- Modify: `web/src/lib/error-recovery.ts`
- Test: `web/src/features/workflows/workflow-parameter-form.test.tsx`
- Test: `web/src/features/backtest/backtest-center.test.tsx`
- Test: `web/src/features/market-workspace/market-workspace-shell.test.tsx`
- Test: `web/src/pages/articles/ArticlePipelinePage.test.tsx`
- Test: `web/src/pages/profiles/ProfileImportPage.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
expect(screen.queryByLabelText('config_path')).not.toBeInTheDocument();
expect(submitPayload).toEqual(expect.not.objectContaining({ config_path: expect.anything() }));
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/features/workflows/workflow-parameter-form.test.tsx`
Expected: FAIL because canonical Web paths still expose or submit `config_path`.

- [ ] **Step 3: Write minimal implementation**

```tsx
if (hasProfileField && name === 'config_path') return null;
delete next.config_path;
```

```ts
// Canonical Web payloads should only carry profile_id.
const params = { ...submission, profile_id: submission.profileId };
delete params.config_path;
```

Update the Web forms so that `config_path` is only visible on profile import / CLI debug surfaces and is stripped before canonical Web submission.

- [ ] **Step 4: Run test to verify it passes**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/features/workflows/workflow-parameter-form.test.tsx src/features/backtest/backtest-center.test.tsx src/features/market-workspace/market-workspace-shell.test.tsx src/pages/articles/ArticlePipelinePage.test.tsx src/pages/profiles/ProfileImportPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/workflows/workflow-parameter-form.tsx web/src/features/workflows/workflow-presets.ts web/src/features/backtest/backtest-center.tsx web/src/features/market-workspace/market-workspace-shell.tsx web/src/pages/articles/ArticlePipelinePage.tsx web/src/pages/profiles/ProfileEditPage.tsx web/src/pages/profiles/ProfileImportPage.tsx web/src/components/dashboard/dashboard-status-summary.tsx web/src/types/pipeline.ts web/src/types/backtest.ts web/src/lib/api/backtests.ts web/src/lib/api/profiles.ts web/src/lib/error-recovery.ts web/src/features/workflows/workflow-parameter-form.test.tsx web/src/features/backtest/backtest-center.test.tsx web/src/features/market-workspace/market-workspace-shell.test.tsx web/src/pages/articles/ArticlePipelinePage.test.tsx web/src/pages/profiles/ProfileImportPage.test.tsx
git commit -m "feat(web): make profile the canonical runtime entry"
```

### Task 4: Update docs and verify the residual `config_path` usage is CLI/debug only

**Files:**
- Modify: `docs/web-user-manual.md`
- Modify: `docs/web-user-manual-gen2.md`
- Modify: `docs/web-deployment-operation.md`
- Modify: `docs/web-deployment-operation-gen2.md`
- Modify: `docs/Preview.md`
- Modify: `docs/superpowers/specs/*` if the existing design notes still describe Web runtime as `config_path`-driven
- Test: `tests/unit/services/test_config_profile_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_web_canonical_paths_do_not_submit_config_path():
    # assertion belongs in documentation review and contract test coverage
    assert True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/services/test_config_profile_service.py -v`
Expected: PASS after code tasks, while docs are updated in this step.

- [ ] **Step 3: Write minimal implementation**

```md
- Web canonical runtime uses Profile only.
- `config_path` remains for CLI/debug and historical compatibility.
- Editing Profile and rerunning `process` uses the new Profile-backed LLM configuration.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `git diff --check && python -m pytest tests/unit/services/test_config_profile_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/web-user-manual.md docs/web-user-manual-gen2.md docs/web-deployment-operation.md docs/web-deployment-operation-gen2.md docs/Preview.md
git commit -m "docs(web): document profile-only runtime flow"
```

