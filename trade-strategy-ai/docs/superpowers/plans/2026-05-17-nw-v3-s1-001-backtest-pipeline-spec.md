# NW-V3-S1-001 Backtest Pipeline Spec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define a canonical Web-first backtest pipeline and workflow contract that reuses the existing backtest engine, exposes the backtest entry through the registry bridge, and makes backtest jobs runnable through the Job/Workflow runtime without adding new CLI-first paths.

**Architecture:** Keep `src/backtest/*` as the execution engine and `BacktestService` as the shared application service. Add a canonical `PipelineSpec` for backtest, wire it into the runtime registry, and teach `JobRunner` to execute the existing backtest job types so the Web product can trigger them through the normal Job/Workflow path. Backtest artifacts stay file-backed and are surfaced as `result.json`, `report.md`, and `records.csv` so `ArtifactService` can index them without a second storage model.

**Tech Stack:** Python, Pydantic, Pytest, existing FastAPI service layer, existing Job/Workflow/Artifact services.

---

### Task 1: Lock the canonical backtest contract in tests first

**Files:**
- Create: `tests/pipelines/test_backtest_pipeline_spec.py`
- Modify: `tests/unit/services/test_runtime_registry_bridge.py`
- Modify: `tests/unit/services/test_job_registry.py`

- [ ] **Step 1: Write the failing tests**

Add assertions that fail until the backtest pipeline exists:

```python
def test_backtest_pipeline_spec_exports_core_fields():
    from src.pipelines.backtest_pipeline_spec import BACKTEST_PIPELINE_SPEC

    assert BACKTEST_PIPELINE_SPEC.pipeline_id == "backtest"
    assert BACKTEST_PIPELINE_SPEC.workflow_id == "backtest"
    assert BACKTEST_PIPELINE_SPEC.ui_page == "/backtest"
    assert "UI-V3-001" in BACKTEST_PIPELINE_SPEC.ui_task_ids
    assert "backtest-run" in BACKTEST_PIPELINE_SPEC.job_types
    assert "backtest-validate-rules" in BACKTEST_PIPELINE_SPEC.job_types
    assert "backtest-reproducibility-check" in BACKTEST_PIPELINE_SPEC.job_types
```

Add registry coverage:

```python
def test_runtime_registry_bridge_exposes_backtest_pipeline():
    from src.services.runtime_registry_bridge import get_pipeline_contract

    contract = get_pipeline_contract("backtest")
    assert contract is not None
    assert contract["pipeline_id"] == "backtest"
```

Add job registry coverage that will fail until the backtest jobs are marked runnable and schema-aligned:

```python
def test_job_registry_marks_backtest_jobs_runnable():
    from src.services.job_registry import get_job_definition

    assert get_job_definition("backtest-run").runnable is True
    assert get_job_definition("backtest-validate-rules").runnable is True
    assert get_job_definition("backtest-reproducibility-check").runnable is True
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
python -m pytest tests/pipelines/test_backtest_pipeline_spec.py tests/unit/services/test_runtime_registry_bridge.py tests/unit/services/test_job_registry.py -q
```

Expected:

- Fail with missing `backtest_pipeline_spec`
- Fail with missing `backtest` pipeline contract
- Fail with backtest jobs still marked non-runnable

---

### Task 2: Add the canonical backtest pipeline spec and expose it through the registry

**Files:**
- Create: `src/pipelines/backtest_pipeline_spec.py`
- Modify: `src/pipelines/__init__.py`
- Modify: `src/services/runtime_registry_bridge.py`
- Modify: `src/services/job_registry.py`
- Modify: `src/services/workflow_service.py`
- Modify: `tests/unit/services/test_job_registry.py`

- [ ] **Step 1: Write the minimal implementation**

Add a new `PipelineSpec` that mirrors the backtest product contract:

```python
BACKTEST_PIPELINE_SPEC = PipelineSpec(
    pipeline_id="backtest",
    title="回测中心",
    description="把回测、规则验真和可复现性检查收敛为正式 Web 回测入口。",
    required_profile_sections=("trader", "strategy", "market"),
    input_schema={...},
    output_artifacts=(...),
    workflow_id="backtest",
    job_types=("backtest-run", "backtest-validate-rules", "backtest-reproducibility-check"),
    steps=(...),
    user_visible_success_criteria=(
        "用户可以通过 Web 运行回测。",
        "用户可以查看回测结果、报告和 fingerprint。",
        "回测结果通过 Job / Workflow / Artifact 体系回溯。",
    ),
    ui_page="/backtest",
    ui_task_ids=("UI-V3-001",),
)
```

Align the job registry with the existing `BacktestRequest` contract:

```python
param_schema=_schema(
    "回测参数",
    {
        "trader_id": _string("交易员 ID", required=True),
        "date_from": _date_field("开始日期", required=True),
        "date_to": _date_field("结束日期", required=True),
        "strategy_version_id": _string("策略版本 ID"),
        "symbols": _array_field("标的列表", default=[]),
        "mode": _string("回测模式", default="full"),
        "use_snapshot_only": _boolean("仅使用快照数据", default=True),
        "scoring_profile": _string("评分配置", default="stage5"),
        "config_path": _path_field("配置文件路径"),
    },
)
```

Mark the backtest job types runnable in `src/services/job_registry.py` so they can enter the worker white list, but keep `rule-pool-backtest` and optimization jobs out of this task.

Expose the new pipeline through:

- `src/pipelines/__init__.py`
- `src/services/runtime_registry_bridge.py`

Update `src/services/workflow_service.py` only if a workflow summary helper needs to expose the backtest workflow contract in a cleaner way.

- [ ] **Step 2: Run the focused tests to verify it passes**

Run:

```bash
python -m pytest tests/pipelines/test_backtest_pipeline_spec.py tests/unit/services/test_runtime_registry_bridge.py tests/unit/services/test_job_registry.py -q
```

Expected:

- Backtest pipeline contract is visible in the registry bridge
- Backtest job types are marked runnable
- The pipeline summary is stable and serializable

---

### Task 3: Make backtest execution Web-runnable and expose report / JSON / CSV artifacts

**Files:**
- Modify: `src/services/backtest_service.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/backtest/reporting.py`
- Modify: `tests/unit/services/test_backtest_service.py`
- Modify: `tests/unit/services/test_job_runner.py`

- [ ] **Step 1: Write the failing tests**

Add a service test that requires backtest execution to accept the full Web contract and return reproducibility data:

```python
result = service.run_backtest(
    trader_id="trader_a",
    date_from=date(2026, 4, 1),
    date_to=date(2026, 4, 3),
    strategy_version_id="sv-001",
    mode="full",
    config_path="config/app.yaml",
    symbols=["000001.SZ"],
    use_snapshot_only=True,
    scoring_profile="stage5",
)
assert result.payload["request"]["symbols"] == ["000001.SZ"]
assert result.payload["request"]["use_snapshot_only"] is True
assert result.payload["request"]["scoring_profile"] == "stage5"
```

Add report helpers for a CSV artifact:

```python
def test_render_backtest_csv_contains_header_and_records():
    from src.backtest.reporting import render_backtest_csv

    csv_text = render_backtest_csv(_sample_result())
    assert "trade_date,trader_id,strategy_version_id" in csv_text
    assert "000001.SZ" in csv_text
```

Add JobRunner coverage that backtest jobs create file-backed artifacts:

```python
assert any(item["kind"] == "report-markdown" for item in loaded.payload["job"]["artifacts"])
assert any(item["kind"] == "records-csv" for item in loaded.payload["job"]["artifacts"])
assert loaded.payload["job"]["result"]["payload"]["fingerprint"] == "<stable fingerprint>"
```

- [ ] **Step 2: Implement the Web-runnable backtest path**

Extend `BacktestService` so `run_backtest()` and `reproducibility_check()` accept the full Web contract and pass the options through to the engine request:

- `symbols`
- `use_snapshot_only`
- `scoring_profile`

Add a CSV renderer in `src/backtest/reporting.py` that serializes `BacktestResult.records` into a stable header + row format.

Teach `JobRunner` to handle:

- `backtest-run`
- `backtest-validate-rules`
- `backtest-reproducibility-check`

The handler should:

1. Call `BacktestService`
2. Write a backtest `result.json`
3. Write a markdown report file
4. Write a CSV record file for `backtest-run`
5. Bind the files as artifacts using `JobService.bind_artifact`

Keep the implementation file-backed and deterministic. Do not introduce a second storage model or a CLI-only fallback.

- [ ] **Step 3: Run the focused tests to verify it passes**

Run:

```bash
python -m pytest tests/unit/services/test_backtest_service.py tests/unit/services/test_job_runner.py tests/unit/backtest/test_reporting.py -q
```

Expected:

- Backtest service accepts the full Web contract
- Backtest CSV rendering is stable
- Worker execution binds backtest artifacts

---

### Task 4: Final verification for NW-V3-S1-001

**Files:**
- Modify: `tests/unit/services/test_runtime_registry_bridge.py`
- Modify: `tests/unit/services/test_job_registry.py`
- Modify: `tests/unit/services/test_backtest_service.py`
- Modify: `tests/unit/services/test_job_runner.py`

- [ ] **Step 1: Run the backtest-specific regression slice**

Run:

```bash
python -m pytest tests/pipelines/test_backtest_pipeline_spec.py tests/unit/services/test_runtime_registry_bridge.py tests/unit/services/test_job_registry.py tests/unit/services/test_backtest_service.py tests/unit/services/test_job_runner.py tests/unit/backtest/test_reporting.py -q
```

Expected:

- All backtest contract tests pass
- The backtest pipeline is visible in the registry
- The runnable job types line up with the worker path
- The artifact surface includes JSON, Markdown, and CSV

- [ ] **Step 2: Run the contract sweep**

Run:

```bash
python -m pytest tests/api/test_ui_openapi_contract.py -q
```

Expected:

- The existing UI contract remains intact
- No new CLI-first dependency is introduced

- [ ] **Step 3: Review the result against the task acceptance criteria**

Confirm that `NW-V3-S1-001` is only marked complete when all of the following are true:

- Backtest is represented as a canonical pipeline spec
- Backtest jobs are runnable through the worker path
- Backtest result artifacts are available as JSON, Markdown, and CSV
- Fingerprint/reproducibility output is available in the backtest result payload
- No CLI-only or temporary path was added to satisfy the task

