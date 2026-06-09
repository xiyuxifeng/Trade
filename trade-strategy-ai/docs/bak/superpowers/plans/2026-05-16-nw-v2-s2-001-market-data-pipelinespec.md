# Market Data PipelineSpec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the canonical `market_data` PipelineSpec so V2 market workflows have a single, explicit contract for jobs, artifacts, input schema, and UI bindings.

**Architecture:** Keep this task read-only on runtime behavior. Add one canonical pipeline spec module under `src/pipelines/` and expose it through the package export so later UI and docs can consume a stable catalog. Reuse the existing `job_registry` and `workflow_service` definitions as the runtime source of truth; this task only formalizes the market pipeline contract and its discoverability.

**Tech Stack:** Python dataclasses, pytest, existing `PipelineSpec` / `PipelineStepSpec` / `PipelineOutputArtifactSpec`, markdown docs.

---

### Task 1: Add the canonical market_data PipelineSpec module

**Files:**
- Create: `src/pipelines/market_data_pipeline_spec.py`
- Modify: `src/pipelines/__init__.py`
- Create: `tests/unit/pipelines/test_market_data_pipeline_spec.py`

- [ ] **Step 1: Write the failing test**

```python
from src.pipelines import MARKET_DATA_PIPELINE_SPEC


def test_market_data_pipeline_spec_summary():
    summary = MARKET_DATA_PIPELINE_SPEC.summary()

    assert summary["pipeline_id"] == "market_data"
    assert summary["title"] == "市场数据链路"
    assert summary["workflow_id"] == "scheduler"
    assert summary["ui_page"] == "/market"
    assert summary["ui_task_ids"] == ["UI-V2-005", "UI-V2-007"]
    assert summary["required_profile_sections"] == ["market", "profile", "provider"]
    assert "kaipan-fetch" in summary["job_types"]
    assert "snapshot-build" in summary["job_types"]
    assert any(item["kind"] == "market-state-json" for item in summary["output_artifacts"])
    assert any(step["job_type"] == "snapshot-build" for step in summary["steps"])
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `../.venv/bin/python -m pytest tests/unit/pipelines/test_market_data_pipeline_spec.py -v`
Expected: fail with import error or missing `MARKET_DATA_PIPELINE_SPEC`.

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations

from src.pipelines.article_pipeline_spec import PipelineOutputArtifactSpec, PipelineSpec, PipelineStepSpec

MARKET_DATA_PIPELINE_SPEC = PipelineSpec(
    pipeline_id="market_data",
    title="市场数据链路",
    description="把 Kaipan、OHLCV、市场状态和快照构建收敛成单一市场数据管线。",
    required_profile_sections=("market", "profile", "provider"),
    input_schema={
        "description": "Market Data Pipeline 参数",
        "allow_additional_fields": False,
        "fields": {
            "config_path": {"type": "path", "description": "配置文件路径", "required": True, "default": None, "enum": []},
            "profile_id": {"type": "string", "description": "Profile ID", "required": False, "default": "default", "enum": []},
            "trade_date": {"type": "date", "description": "交易日期", "required": False, "default": None, "enum": []},
            "start_date": {"type": "date", "description": "开始日期", "required": False, "default": None, "enum": []},
            "end_date": {"type": "date", "description": "结束日期", "required": False, "default": None, "enum": []},
            "symbols": {"type": "array", "description": "标的列表", "required": False, "default": [], "enum": []},
            "limit": {"type": "integer", "description": "最多处理标的数", "required": False, "default": 100, "enum": []},
            "force": {"type": "boolean", "description": "是否强制执行", "required": False, "default": False, "enum": []},
            "offline": {"type": "boolean", "description": "是否离线模式", "required": False, "default": False, "enum": []},
        },
    },
    output_artifacts=(
        PipelineOutputArtifactSpec(kind="raw-json", title="原始数据 JSON", description="Kaipan 抓取的原始数据，供后续归一化与追踪。", previewable=True, extensions={"required": False}),
        PipelineOutputArtifactSpec(kind="normalized-json", title="归一化 JSON", description="标准化后的市场数据结果，供 Job Detail 和下游消费。", previewable=True, extensions={"required": False}),
        PipelineOutputArtifactSpec(kind="ohlcv-bundle", title="OHLCV 数据包", description="OHLCV 行情结果摘要。", previewable=True, extensions={"required": False}),
        PipelineOutputArtifactSpec(kind="market-state-json", title="市场状态 JSON", description="Market State 输出。", previewable=True, extensions={"required": False}),
        PipelineOutputArtifactSpec(kind="snapshot-json", title="市场快照 JSON", description="snapshot-build 的输出结果。", previewable=True, extensions={"required": False}),
    ),
    workflow_id="scheduler",
    job_types=("kaipan-fetch", "kaipan-normalize", "kaipan-run", "ohlcv-crawl", "market-state-build", "snapshot-build"),
    steps=(
        PipelineStepSpec(step_id="kaipan-fetch", title="Kaipan 抓取", description="抓取原始市场数据。", job_type="kaipan-fetch", output_artifacts=("raw-json",)),
        PipelineStepSpec(step_id="kaipan-normalize", title="Kaipan 归一化", description="把原始数据转换成标准结构。", job_type="kaipan-normalize", depends_on=("kaipan-fetch",), output_artifacts=("normalized-json",)),
        PipelineStepSpec(step_id="kaipan-run", title="Kaipan 一键运行", description="生成调度计划或启动调度器。", job_type="kaipan-run", depends_on=("kaipan-normalize",), output_artifacts=("normalized-json",)),
        PipelineStepSpec(step_id="ohlcv-crawl", title="抓取 OHLCV", description="抓取并回灌日线行情。", job_type="ohlcv-crawl", output_artifacts=("ohlcv-bundle",)),
        PipelineStepSpec(step_id="market-state-build", title="构建市场状态", description="构建市场状态上下文。", job_type="market-state-build", depends_on=("ohlcv-crawl",), output_artifacts=("market-state-json",)),
        PipelineStepSpec(step_id="snapshot-build", title="构建快照", description="构建市场快照和候选池快照。", job_type="snapshot-build", depends_on=("market-state-build",), output_artifacts=("snapshot-json",)),
    ),
    user_visible_success_criteria=(
        "用户可以把市场数据工作流理解成一个正式 Pipeline。",
        "Job Detail 和 UI 可以复用同一份输入 schema。",
        "每个步骤都能映射到已有 job_type 和 artifact kind。",
    ),
    ui_page="/market",
    ui_task_ids=("UI-V2-005", "UI-V2-007"),
    extensions={
        "supported_input_modes": ("config_path", "profile"),
        "migration_target": "profile",
        "ui_note": "市场数据工作台后续只读此 spec，不再拼接临时入口。",
    },
)
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `../.venv/bin/python -m pytest tests/unit/pipelines/test_market_data_pipeline_spec.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pipelines/market_data_pipeline_spec.py src/pipelines/__init__.py tests/unit/pipelines/test_market_data_pipeline_spec.py
git commit -m "feat(pipeline): add market data pipeline spec"
```

### Task 2: Add the contract note and traceability updates

**Files:**
- Create: `docs/New-Web-Market-PipelineSpec.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `daily-sessions/2026-05-16.md`

- [ ] **Step 1: Write the documentation test**

```markdown
# docs/New-Web-Market-PipelineSpec.md

## Canonical Contract

- pipeline_id: `market_data`
- ui_page: `/market`
- ui_task_ids: `UI-V2-005`, `UI-V2-007`
- workflow_id: `scheduler`
- job_types: `kaipan-fetch`, `kaipan-normalize`, `kaipan-run`, `ohlcv-crawl`, `market-state-build`, `snapshot-build`
- required_profile_sections: `market`, `profile`, `provider`

## Success Criteria

- The market workspace consumes this spec as the single source of truth.
- The UI never hardcodes provider-private fields or filesystem paths.
```

- [ ] **Step 2: Run the documentation update**

Add a short note under `NW-V2-S2-001` that points to `docs/New-Web-Market-PipelineSpec.md` and records the canonical UI binding.

- [ ] **Step 3: Run the session update**

Record the new resume point in `daily-sessions/2026-05-16.md` after verification is complete.

- [ ] **Step 4: Validate the docs sync**

Run: `git diff --check`
Expected: PASS with no whitespace or patch-format errors.

### Task 3: Verify the contract and finish the branch step

**Files:**
- Review: `src/pipelines/market_data_pipeline_spec.py`
- Review: `tests/unit/pipelines/test_market_data_pipeline_spec.py`
- Review: `docs/New-Web-Market-PipelineSpec.md`

- [ ] **Step 1: Run the focused tests**

Run: `../.venv/bin/python -m pytest tests/unit/pipelines/test_market_data_pipeline_spec.py -v`
Expected: PASS.

- [ ] **Step 2: Re-run diff hygiene**

Run: `git diff --check`
Expected: PASS.

- [ ] **Step 3: Review against the acceptance criteria**

Confirm the spec includes:

```python
assert summary["pipeline_id"] == "market_data"
assert summary["ui_page"] == "/market"
assert summary["ui_task_ids"] == ["UI-V2-005", "UI-V2-007"]
assert "snapshot-build" in summary["job_types"]
```

- [ ] **Step 4: Mark the TaskList status only after review**

Update `NW-V2-S2-001` to `[-]` while implementation is active, then to `[x]` only after tests, docs, and review are all done.

---

## Spec Coverage Check

- The spec definition is covered by Task 1.
- UI binding and traceability are covered by Task 2.
- Verification and acceptance are covered by Task 3.
- No task introduces a second runtime source of truth or a new CLI entry.

## Risks

- The market pipeline already has runtime jobs, so the spec must stay aligned with existing `job_type` names.
- `NW-V2-S2-001` is an architecture-boundary task; any contract drift would affect later UI tasks.
- If the team later wants a richer market catalog, that should be a follow-up task, not part of this spec definition.

