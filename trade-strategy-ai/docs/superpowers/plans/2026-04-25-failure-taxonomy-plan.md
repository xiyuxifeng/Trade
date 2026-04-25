# NTL-S5-002 失败归因分类 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `src/evaluation/failure_taxonomy.py` 中实现多维度失败归因分类体系，提供 StrEnum 标签定义和解析函数。

**Architecture:** 采用多维度标签组合（根因必选 + 交易阶段可选 + 规则类型可选），通过 StrEnum 严格管控标签定义，扩展需代码评审。

**Tech Stack:** Python 标准库（enum.StrEnum、dataclass），无额外依赖。

---

## 文件结构

```
src/evaluation/
    __init__.py                        # 更新：导出新增的类型和函数
    evidence_pack.py                    # NTL-S5-001（已有）
    failure_taxonomy.py                 # NTL-S5-002（新增）

tests/unit/evaluation/                  # NTL-S5-002（新增）
    __init__.py
    test_failure_taxonomy.py
```

---

## Task 1: 创建 failure_taxonomy.py 基本结构

**Files:**
- Create: `src/evaluation/failure_taxonomy.py`
- Test: `tests/unit/evaluation/test_failure_taxonomy.py::test_root_cause_values`

- [ ] **Step 1: 写失败测试**

```python
"""failure_taxonomy 测试。"""

from src.evaluation.failure_taxonomy import (
    FailureRootCause,
    FailureStage,
    FailureRuleType,
)


class TestFailureRootCause:
    """失败根因标签枚举。"""

    def test_status_values(self):
        """9 个根因标签值正确。"""
        assert FailureRootCause.RULE_PRECONDITION_FAILED.value == "rule_precondition_failed"
        assert FailureRootCause.SIGNAL_QUALITY_LOW.value == "signal_quality_low"
        assert FailureRootCause.ENTRY_TIMING_POOR.value == "entry_timing_poor"
        assert FailureRootCause.EXIT_TIMING_POOR.value == "exit_timing_poor"
        assert FailureRootCause.POSITION_SIZE_MISMATCH.value == "position_size_mismatch"
        assert FailureRootCause.MARKET_MISMATCH.value == "market_mismatch"
        assert FailureRootCause.EXTERNAL_EVENT.value == "external_event"
        assert FailureRootCause.SYMBOL_SELECTION_SUBOPTIMAL.value == "symbol_selection_suboptimal"
        assert FailureRootCause.DATA_QUALITY_ISSUE.value == "data_quality_issue"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestFailureRootCause::test_status_values -v`
Expected: FAIL with "No module named 'src.evaluation.failure_taxonomy'"

- [ ] **Step 3: 创建 failure_taxonomy.py**

```python
"""失败归因分类定义（NTL-S5-002）。

职责：
- 定义失败归因的标准化标签体系（根因 + 交易阶段 + 规则类型）
- 提供标签解析函数
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FailureRootCause(StrEnum):
    """失败根因标签（必选，至少 1 个）。

    用于描述交易失败的根本原因。
    """
    RULE_PRECONDITION_FAILED = "rule_precondition_failed"
    SIGNAL_QUALITY_LOW = "signal_quality_low"
    ENTRY_TIMING_POOR = "entry_timing_poor"
    EXIT_TIMING_POOR = "exit_timing_poor"
    POSITION_SIZE_MISMATCH = "position_size_mismatch"
    MARKET_MISMATCH = "market_mismatch"
    EXTERNAL_EVENT = "external_event"
    SYMBOL_SELECTION_SUBOPTIMAL = "symbol_selection_suboptimal"
    DATA_QUALITY_ISSUE = "data_quality_issue"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestFailureRootCause::test_status_values -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/failure_taxonomy.py tests/unit/evaluation/__init__.py tests/unit/evaluation/test_failure_taxonomy.py
git commit -m "feat(NTL-S5-002): add FailureRootCause enum"
```

---

## Task 2: 添加 FailureStage 和 FailureRuleType 枚举

**Files:**
- Modify: `src/evaluation/failure_taxonomy.py`
- Test: `tests/unit/evaluation/test_failure_taxonomy.py::test_stage_and_rule_type_values`

- [ ] **Step 1: 写失败测试**

```python
class TestFailureStage:
    """失败交易阶段标签枚举。"""

    def test_status_values(self):
        """3 个阶段标签值正确。"""
        assert FailureStage.ENTRY.value == "stage:entry"
        assert FailureStage.EXIT.value == "stage:exit"
        assert FailureStage.HOLDING.value == "stage:holding"


class TestFailureRuleType:
    """失败规则类型标签枚举。"""

    def test_status_values(self):
        """4 个规则类型标签值正确。"""
        assert FailureRuleType.ENTRY.value == "rule_type:entry"
        assert FailureRuleType.EXIT.value == "rule_type:exit"
        assert FailureRuleType.FILTER.value == "rule_type:filter"
        assert FailureRuleType.SIZING.value == "rule_type:sizing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestFailureStage::test_status_values tests/unit/evaluation/test_failure_taxonomy.py::TestFailureRuleType::test_status_values -v`
Expected: FAIL with "FailureStage not defined"

- [ ] **Step 3: 添加枚举定义**

在 `failure_taxonomy.py` 中 `FailureRootCause` 之后添加：

```python
class FailureStage(StrEnum):
    """失败发生的交易阶段（可选，最多 1 个）。

    用于标注失败发生在交易的哪个阶段。
    """
    ENTRY = "stage:entry"
    EXIT = "stage:exit"
    HOLDING = "stage:holding"


class FailureRuleType(StrEnum):
    """涉及的规则类型（可选，最多 1 个）。

    用于标注失败涉及哪类策略规则。
    """
    ENTRY = "rule_type:entry"
    EXIT = "rule_type:exit"
    FILTER = "rule_type:filter"
    SIZING = "rule_type:sizing"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestFailureStage::test_status_values tests/unit/evaluation/test_failure_taxonomy.py::TestFailureRuleType::test_status_values -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/failure_taxonomy.py
git commit -m "feat(NTL-S5-002): add FailureStage and FailureRuleType enums"
```

---

## Task 3: 添加 FailureAttribution 数据类和 parse_failure_categories 函数

**Files:**
- Modify: `src/evaluation/failure_taxonomy.py`
- Test: `tests/unit/evaluation/test_failure_taxonomy.py::TestFailureAttribution`

- [ ] **Step 1: 写失败测试**

```python
class TestFailureAttribution:
    """结构化失败归因数据类。"""

    def test_creation_with_all_fields(self):
        """所有字段可正确创建。"""
        from src.evaluation.failure_taxonomy import FailureAttribution

        attr = FailureAttribution(
            root_causes=["entry_timing_poor", "signal_quality_low"],
            stage="stage:entry",
            rule_type="rule_type:entry",
        )
        assert attr.root_causes == ["entry_timing_poor", "signal_quality_low"]
        assert attr.stage == "stage:entry"
        assert attr.rule_type == "rule_type:entry"

    def test_creation_optional_fields_none(self):
        """可选字段默认为 None。"""
        from src.evaluation.failure_taxonomy import FailureAttribution

        attr = FailureAttribution(root_causes=["market_mismatch"])
        assert attr.root_causes == ["market_mismatch"]
        assert attr.stage is None
        assert attr.rule_type is None


class TestParseFailureCategories:
    """标签列表解析函数。"""

    def test_parse_with_all_dimensions(self):
        """解析包含所有维度的标签列表。"""
        from src.evaluation.failure_taxonomy import parse_failure_categories

        tags = ["entry_timing_poor", "stage:entry", "rule_type:entry"]
        result = parse_failure_categories(tags)
        assert result.root_causes == ["entry_timing_poor"]
        assert result.stage == "stage:entry"
        assert result.rule_type == "rule_type:entry"

    def test_parse_multiple_root_causes(self):
        """解析多个根因标签。"""
        from src.evaluation.failure_taxonomy import parse_failure_categories

        tags = ["entry_timing_poor", "signal_quality_low", "stage:exit"]
        result = parse_failure_categories(tags)
        assert result.root_causes == ["entry_timing_poor", "signal_quality_low"]
        assert result.stage == "stage:exit"
        assert result.rule_type is None

    def test_parse_empty_tags(self):
        """空标签列表解析。"""
        from src.evaluation.failure_taxonomy import parse_failure_categories

        result = parse_failure_categories([])
        assert result.root_causes == []
        assert result.stage is None
        assert result.rule_type is None

    def test_parse_unknown_tags_ignored(self):
        """未知标签被忽略（只保留已知维度）。"""
        from src.evaluation.failure_taxonomy import parse_failure_categories

        tags = ["entry_timing_poor", "unknown:custom", "stage:exit"]
        result = parse_failure_categories(tags)
        assert result.root_causes == ["entry_timing_poor"]
        assert result.stage == "stage:exit"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestFailureAttribution tests/unit/evaluation/test_failure_taxonomy.py::TestParseFailureCategories -v`
Expected: FAIL with "FailureAttribution not defined"

- [ ] **Step 3: 添加数据类和解析函数**

在 `failure_taxonomy.py` 末尾添加：

```python
@dataclass
class FailureAttribution:
    """结构化失败归因。"""
    root_causes: list[str]
    stage: str | None = None
    rule_type: str | None = None


def parse_failure_categories(tags: list[str]) -> FailureAttribution:
    """将标签列表解析为结构化归因对象。

    Args:
        tags: 标签列表，如 ["entry_timing_poor", "stage:entry", "rule_type:entry"]

    Returns:
        FailureAttribution: 结构化归因对象
    """
    root_causes = [t for t in tags if t in FailureRootCause]
    stages = [t for t in tags if t in FailureStage]
    rule_types = [t for t in tags if t in FailureRuleType]

    return FailureAttribution(
        root_causes=root_causes,
        stage=stages[0] if stages else None,
        rule_type=rule_types[0] if rule_types else None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestFailureAttribution tests/unit/evaluation/test_failure_taxonomy.py::TestParseFailureCategories -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/failure_taxonomy.py
git commit -m "feat(NTL-S5-002): add FailureAttribution and parse_failure_categories"
```

---

## Task 4: 更新 evaluation 模块导出

**Files:**
- Modify: `src/evaluation/__init__.py`
- Test: `tests/unit/evaluation/test_failure_taxonomy.py::test_module_exports`

- [ ] **Step 1: 写失败测试**

```python
class TestModuleExports:
    """模块导出测试。"""

    def test_evaluation_exports_failure_taxonomy(self):
        """evaluation 模块正确导出 failure_taxonomy 的所有公开接口。"""
        from src.evaluation import (
            FailureRootCause,
            FailureStage,
            FailureRuleType,
            FailureAttribution,
            parse_failure_categories,
        )
        assert hasattr(FailureRootCause, "ENTRY_TIMING_POOR")
        assert hasattr(FailureStage, "ENTRY")
        assert hasattr(FailureRuleType, "ENTRY")
        assert callable(parse_failure_categories)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestModuleExports::test_evaluation_exports_failure_taxonomy -v`
Expected: FAIL with "cannot import name 'FailureRootCause' from 'src.evaluation'"

- [ ] **Step 3: 更新 __init__.py**

```python
"""Evaluation 模块：盘后评估、学习闭环与 ranking。

职责：
- 生成 Evidence Pack（交易想法 + 上下文 + 市场快照）
- 失败归因分类
- 盘后复盘服务
- 策略 ranking
"""

from src.evaluation.evidence_pack import EvidencePack
from src.evaluation.failure_taxonomy import (
    FailureRootCause,
    FailureStage,
    FailureRuleType,
    FailureAttribution,
    parse_failure_categories,
)

__all__ = [
    "EvidencePack",
    "FailureRootCause",
    "FailureStage",
    "FailureRuleType",
    "FailureAttribution",
    "parse_failure_categories",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_failure_taxonomy.py::TestModuleExports::test_evaluation_exports_failure_taxonomy -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/__init__.py
git commit -m "feat(NTL-S5-002): export failure taxonomy from evaluation module"
```

---

## Task 5: 端到端测试验证

**Files:**
- Test: `pytest tests/unit/evaluation/ -v`

- [ ] **Step 1: 运行完整 evaluation 测试套件**

Run: `pytest tests/unit/evaluation/ -v`
Expected: ALL PASS（预计 11 个测试）

- [ ] **Step 2: 验证 py_compile**

Run: `python -m py_compile src/evaluation/failure_taxonomy.py && echo "OK"`
Expected: OK

- [ ] **Step 3: 标记 TaskList**

将 `NTL-S5-002` 标记为已完成。

- [ ] **Step 4: Commit**

```bash
git add docs/TaskList.md
git commit -m "docs(NTL-S5-002): mark as completed"
```

---

## Self-Review Checklist

1. **Spec coverage:** 检查 `docs/superpowers/specs/2026-04-25-failure-taxonomy-design.md` 中每个标签都有对应测试 - ✅
2. **Placeholder scan:** 无 TBD/TODO - ✅
3. **Type consistency:** 所有枚举值与设计文档一致 - ✅
4. **Import completeness:** `parse_failure_categories` 正确处理未知标签 - ✅
5. **Module exports:** `src/evaluation/__init__.py` 导出所有公开接口 - ✅

---

## 执行选择

**Plan complete and saved to `docs/superpowers/plans/2026-04-25-failure-taxonomy-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
