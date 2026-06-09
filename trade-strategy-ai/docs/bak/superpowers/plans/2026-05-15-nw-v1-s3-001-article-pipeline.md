# NW-V1-S3-001 Article Pipeline Spec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single canonical `article_pipeline` spec file with stable core fields and explicit extension points, and expose it through the existing runtime catalog bridge.

**Architecture:** Keep `article_pipeline` as one canonical spec in `src/pipelines/article_pipeline_spec.py`. Model the spec with frozen dataclasses so the core fields stay stable, while `extensions` surfaces stay explicit for later use by `NW-V1-S3-002/003`. Extend `runtime_registry_bridge` to list and load pipeline contracts from that same source of truth.

**Tech Stack:** Python dataclasses, existing runtime registry bridge, pytest

---

### Task 1: Define canonical pipeline spec module

**Files:**
- Create: `trade-strategy-ai/src/pipelines/__init__.py`
- Create: `trade-strategy-ai/src/pipelines/article_pipeline_spec.py`
- Test: `trade-strategy-ai/tests/pipelines/test_article_pipeline_spec.py`

- [ ] **Step 1: Write the failing test**

```python
def test_article_pipeline_spec_exports_core_fields():
    from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPEC

    assert ARTICLE_PIPELINE_SPEC.pipeline_id == "article_pipeline"
    assert ARTICLE_PIPELINE_SPEC.workflow_id == "pipeline"
    assert ARTICLE_PIPELINE_SPEC.ui_page == "/articles"
    assert "UI-V1-010" in ARTICLE_PIPELINE_SPEC.ui_task_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/pipelines/test_article_pipeline_spec.py -v`
Expected: FAIL because the module does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PipelineOutputArtifactSpec:
    kind: str
    title: str
    description: str
    previewable: bool = False
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineStepSpec:
    step_id: str
    title: str
    description: str
    job_type: str
    depends_on: tuple[str, ...] = ()
    output_artifacts: tuple[str, ...] = ()
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineSpec:
    pipeline_id: str
    title: str
    description: str
    required_profile_sections: tuple[str, ...]
    input_schema: dict[str, Any]
    output_artifacts: tuple[PipelineOutputArtifactSpec, ...]
    workflow_id: str
    job_types: tuple[str, ...]
    steps: tuple[PipelineStepSpec, ...]
    user_visible_success_criteria: tuple[str, ...]
    ui_page: str
    ui_task_ids: tuple[str, ...]
    extensions: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/pipelines/test_article_pipeline_spec.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/pipelines/__init__.py trade-strategy-ai/src/pipelines/article_pipeline_spec.py trade-strategy-ai/tests/pipelines/test_article_pipeline_spec.py
git commit -m "feat: add article pipeline spec"
```

### Task 2: Expose pipeline catalog bridge

**Files:**
- Modify: `trade-strategy-ai/src/services/runtime_registry_bridge.py`
- Test: `trade-strategy-ai/tests/unit/services/test_runtime_registry_bridge.py`

- [ ] **Step 1: Write the failing test**

```python
def test_runtime_registry_bridge_normalizes_pipeline_spec():
    from src.services.runtime_registry_bridge import get_pipeline_contract, list_pipeline_contracts

    contracts = list_pipeline_contracts()
    contract = get_pipeline_contract("article_pipeline")

    assert contracts
    assert contract is not None
    assert contract["pipeline_id"] == "article_pipeline"
    assert contract["workflow_id"] == "pipeline"
    assert contract["ui_page"] == "/articles"
    assert "UI-V1-010" in contract["ui_task_ids"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/services/test_runtime_registry_bridge.py -v`
Expected: FAIL because pipeline bridge functions do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPEC


def list_pipeline_contracts() -> list[dict[str, Any]]:
    return [ARTICLE_PIPELINE_SPEC.summary()]


def get_pipeline_contract(pipeline_id: str) -> dict[str, Any] | None:
    if pipeline_id == ARTICLE_PIPELINE_SPEC.pipeline_id:
        return ARTICLE_PIPELINE_SPEC.summary()
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/services/test_runtime_registry_bridge.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add trade-strategy-ai/src/services/runtime_registry_bridge.py trade-strategy-ai/tests/unit/services/test_runtime_registry_bridge.py
git commit -m "feat: expose article pipeline catalog"
```

### Task 3: Sync TaskList and verify

**Files:**
- Modify: `trade-strategy-ai/docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`

- [ ] **Step 1: Mark NW-V1-S3-001 according to Definition of Done**
- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/pipelines/test_article_pipeline_spec.py tests/unit/services/test_runtime_registry_bridge.py -v`
Expected: PASS.

- [ ] **Step 3: Commit TaskList sync**

```bash
git add trade-strategy-ai/docs/New-Web-Linked-TaskLists/New-Web-TaskList.md
git commit -m "docs: sync nw-v1-s3-001 progress"
```

