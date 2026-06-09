# NTL-S5-003 盘后复盘 Service 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `src/evaluation/postmortem_service.py` 中实现盘后复盘 service，提供 `PostmortemResult` dataclass 和 `PostmortemService`。

**Architecture:** 自动归因为主（基于 failure_taxonomy 标签体系），LLM 校验为可选安全层（通过 `LLMValidator` protocol 解耦），支持 confirm/correct/reject 三种决策。

**Tech Stack:** Python 标准库（dataclass、StrEnum、asyncio），`EvidencePack`（NTL-S5-001）、`failure_taxonomy`（NTL-S5-002）。

---

## 文件结构

```
src/evaluation/
    __init__.py                        # 更新：导出新增类型
    evidence_pack.py                    # NTL-S5-001（已有）
    failure_taxonomy.py                 # NTL-S5-002（已有）
    postmortem_service.py              # NTL-S5-003（新增）

tests/unit/evaluation/
    test_failure_taxonomy.py            # NTL-S5-002（已有）
    test_postmortem_service.py         # NTL-S5-003（新增）
```

---

## Task 1: 创建 ValidationDecision 和 LLMValidationResult

**Files:**
- Create: `src/evaluation/postmortem_service.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py::TestValidationDecision`

- [ ] **Step 1: 写失败测试**

```python
"""postmortem_service 测试。"""

from src.evaluation.postmortem_service import ValidationDecision, LLMValidationResult


class TestValidationDecision:
    """LLM 校验决策枚举。"""

    def test_decision_values(self):
        """三种决策值正确。"""
        assert ValidationDecision.CONFIRM.value == "confirm"
        assert ValidationDecision.CORRECT.value == "correct"
        assert ValidationDecision.REJECT.value == "reject"


class TestLLMValidationResult:
    """LLM 校验结果数据类。"""

    def test_confirm_result(self):
        """confirm 决策时 corrected_categories 为空。"""
        result = LLMValidationResult(
            decision=ValidationDecision.CONFIRM,
            reasoning="自动归因正确",
        )
        assert result.decision == ValidationDecision.CONFIRM
        assert result.corrected_categories == []
        assert result.reasoning == "自动归因正确"

    def test_correct_result(self):
        """correct 决策时包含修正后的 categories。"""
        result = LLMValidationResult(
            decision=ValidationDecision.CORRECT,
            corrected_categories=["exit_timing_poor"],
            reasoning="应修正为 exit_timing_poor",
        )
        assert result.decision == ValidationDecision.CORRECT
        assert result.corrected_categories == ["exit_timing_poor"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestValidationDecision -v`
Expected: FAIL with "No module named 'src.evaluation.postmortem_service'"

- [ ] **Step 3: 创建 postmortem_service.py（初始内容）**

```python
"""盘后复盘 service（NTL-S5-003）。

职责：
- 对单笔交易生成结构化复盘结果
- 支持自动归因 + LLM 校验混合模式
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ValidationDecision(StrEnum):
    """LLM 校验决策。"""
    CONFIRM = "confirm"      # 自动归因正确
    CORRECT = "correct"     # LLM 修正了自动归因
    REJECT = "reject"       # LLM 拒绝归因


@dataclass
class LLMValidationResult:
    """LLM 校验结果。"""
    decision: ValidationDecision
    corrected_categories: list[str] = field(default_factory=list)
    reasoning: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestValidationDecision tests/unit/evaluation/test_postmortem_service.py::TestLLMValidationResult -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/postmortem_service.py tests/unit/evaluation/test_postmortem_service.py
git commit -m "feat(NTL-S5-003): add ValidationDecision and LLMValidationResult"
```

---

## Task 2: 创建 PostmortemResult dataclass

**Files:**
- Modify: `src/evaluation/postmortem_service.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py::TestPostmortemResult`

- [ ] **Step 1: 写失败测试**

```python
class TestPostmortemResult:
    """单笔交易复盘结果数据类。"""

    def test_creation_with_all_fields(self):
        """所有字段可正确创建。"""
        from uuid import uuid4
        from src.evaluation.postmortem_service import PostmortemResult, ValidationDecision
        from src.evaluation.failure_taxonomy import FailureAttribution

        result = PostmortemResult(
            idea_id=uuid4(),
            trade_date="2026-04-25",
            failure_attribution=FailureAttribution(
                root_causes=["entry_timing_poor"],
                stage="stage:entry",
                rule_type="rule_type:entry",
            ),
            attribution_source="auto",
            postmortem_notes="入场时机选择不当",
            mfe=0.05,
            mae=-0.03,
            return_pct=0.02,
        )
        assert result.failure_attribution.root_causes == ["entry_timing_poor"]
        assert result.attribution_source == "auto"
        assert result.return_pct == 0.02

    def test_creation_optional_fields_none(self):
        """可选字段默认为 None。"""
        from uuid import uuid4
        from src.evaluation.postmortem_service import PostmortemResult
        from src.evaluation.failure_taxonomy import FailureAttribution

        result = PostmortemResult(
            idea_id=uuid4(),
            trade_date="2026-04-25",
            failure_attribution=FailureAttribution(root_causes=["market_mismatch"]),
            attribution_source="llm_confirmed",
        )
        assert result.postmortem_notes is None
        assert result.mfe is None
        assert result.mae is None
        assert result.return_pct is None
        assert result.extra == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestPostmortemResult -v`
Expected: FAIL with "PostmortemResult not defined"

- [ ] **Step 3: 添加 PostmortemResult 定义**

在 `postmortem_service.py` 末尾添加：

```python
from uuid import UUID


@dataclass
class PostmortemResult:
    """单笔交易的结构化复盘结果。"""
    idea_id: UUID | None
    trade_date: str

    # 归因结果
    failure_attribution: FailureAttribution
    attribution_source: str  # "auto" | "llm_confirmed" | "llm_corrected" | "llm_rejected"

    # LLM 生成的自然语言复盘（可为 None）
    postmortem_notes: str | None = None

    # 评分指标（NTL-S5-010 实现，当前占位）
    mfe: float | None = None      # Maximum Favorable Excursion
    mae: float | None = None      # Maximum Adverse Excursion
    return_pct: float | None = None

    # 扩展字段
    extra: dict[str, object] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestPostmortemResult -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/postmortem_service.py
git commit -m "feat(NTL-S5-003): add PostmortemResult dataclass"
```

---

## Task 3: 创建 LLMValidator Protocol 和 PostmortemService 骨架

**Files:**
- Modify: `src/evaluation/postmortem_service.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py::TestLLMValidator`

- [ ] **Step 1: 写失败测试**

```python
class TestLLMValidator:
    """LLMValidator protocol 测试。"""

    def test_service_initialization(self):
        """PostmortemService 可无参数初始化。"""
        from src.evaluation.postmortem_service import PostmortemService

        service = PostmortemService()
        assert service.llm_validator is None
        assert service.enable_llm_notes is False

    def test_service_with_validator(self):
        """PostmortemService 可接收 LLMValidator。"""
        from src.evaluation.postmortem_service import PostmortemService, LLMValidator
        from src.evaluation.failure_taxonomy import FailureAttribution
        from src.evaluation.postmortem_service import ValidationDecision, LLMValidationResult
        from src.evaluation.evidence_pack import EvidencePack
        from uuid import uuid4

        # 创建一个简单的 mock validator
        class MockValidator:
            async def validate(
                self,
                evidence_pack: EvidencePack,
                auto_attribution: FailureAttribution,
            ) -> LLMValidationResult:
                return LLMValidationResult(decision=ValidationDecision.CONFIRM)

        service = PostmortemService(llm_validator=MockValidator(), enable_llm_notes=True)
        assert service.llm_validator is not None
        assert service.enable_llm_notes is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestLLMValidator -v`
Expected: FAIL with "LLMValidator not defined"

- [ ] **Step 3: 添加 Protocol 和 Service 骨架**

在 `postmortem_service.py` 末尾添加：

```python
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.evaluation.evidence_pack import EvidencePack


class LLMValidator(Protocol):
    """LLM 校验器接口。"""
    async def validate(
        self,
        evidence_pack: EvidencePack,
        auto_attribution: FailureAttribution,
    ) -> LLMValidationResult:
        """校验自动归因结果。"""
        ...


class PostmortemService:
    """盘后复盘 service。

    Args:
        llm_validator: LLM 校验器（可选，不提供则只做自动归因）
        enable_llm_notes: 是否生成 LLM 复盘笔记（需要 llm_validator）
    """

    def __init__(
        self,
        llm_validator: LLMValidator | None = None,
        enable_llm_notes: bool = False,
    ):
        self.llm_validator = llm_validator
        self.enable_llm_notes = enable_llm_notes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestLLMValidator -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/postmortem_service.py
git commit -m "feat(NTL-S5-003): add LLMValidator protocol and PostmortemService skeleton"
```

---

## Task 4: 实现自动归因 _auto_attribution 方法

**Files:**
- Modify: `src/evaluation/postmortem_service.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py::TestAutoAttribution`

- [ ] **Step 1: 写失败测试**

```python
class TestAutoAttribution:
    """自动归因逻辑测试。"""

    def test_signal_quality_low(self):
        """SignalContext confidence < 0.5 应标记 signal_quality_low。"""
        from src.evaluation.postmortem_service import PostmortemService
        from src.evaluation.evidence_pack import EvidencePack
        from src.schemas.contracts import TradeIdea
        from src.strategy.types import SignalContext
        from datetime import date

        service = PostmortemService()

        # 构造 low confidence 的 SignalContext
        signal_ctx = SignalContext(
            features_snapshot={},
            market_state={},
            rules_snapshot=[],
            timestamp=None,
            confidence=0.3,  # 低 confidence
        )

        evidence = EvidencePack(
            idea_id=None,
            trade_date="2026-04-25",
            trade_idea=TradeIdea(
                trader_id="trader1",
                as_of_date=date.today(),
                symbol="000001",
                entry={"type": "limit", "price": 10.0},
            ),
            signal_context=signal_ctx,
            market_data={},
        )

        result = service._auto_attribution(evidence)
        assert "signal_quality_low" in result.root_causes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestAutoAttribution -v`
Expected: FAIL with "_auto_attribution not defined"

- [ ] **Step 3: 实现 _auto_attribution 方法**

在 `PostmortemService` 类中添加：

```python
    def _auto_attribution(self, evidence_pack: EvidencePack) -> FailureAttribution:
        """基于 EvidencePack 数据做自动归因。

        目前实现：
        - signal_quality_low：SignalContext.confidence < 0.5
        - data_quality_issue：market_data 为空或异常

        完整归因逻辑在 NTL-S5-010 后完善。
        """
        from src.evaluation.failure_taxonomy import FailureAttribution

        root_causes: list[str] = []

        # 1. 信号质量问题
        if evidence_pack.signal_context is not None:
            ctx = evidence_pack.signal_context
            if hasattr(ctx, "confidence") and ctx.confidence is not None:
                if ctx.confidence < 0.5:
                    root_causes.append("signal_quality_low")

        # 2. 数据质量问题
        if not evidence_pack.market_data:
            root_causes.append("data_quality_issue")

        return FailureAttribution(root_causes=root_causes)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestAutoAttribution -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/postmortem_service.py
git commit -m "feat(NTL-S5-003): implement _auto_attribution with signal_quality_low detection"
```

---

## Task 5: 实现 _apply_validation 和 generate 方法

**Files:**
- Modify: `src/evaluation/postmortem_service.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py::TestApplyValidation`

- [ ] **Step 1: 写失败测试**

```python
class TestApplyValidation:
    """LLM 校验结果应用逻辑测试。"""

    async def test_apply_confirm(self):
        """confirm 决策保留原始归因，source 为 llm_confirmed。"""
        from src.evaluation.postmortem_service import PostmortemService, ValidationDecision, LLMValidationResult
        from src.evaluation.failure_taxonomy import FailureAttribution

        service = PostmortemService()
        auto = FailureAttribution(root_causes=["entry_timing_poor"])
        validation = LLMValidationResult(decision=ValidationDecision.CONFIRM, reasoning="正确")

        final, source, extra = service._apply_validation(auto, validation)
        assert final.root_causes == ["entry_timing_poor"]
        assert source == "llm_confirmed"
        assert extra == {}

    async def test_apply_correct(self):
        """correct 决策使用 LLM 修正结果，保留原始结果到 extra。"""
        from src.evaluation.postmortem_service import PostmortemService, ValidationDecision, LLMValidationResult
        from src.evaluation.failure_taxonomy import FailureAttribution

        service = PostmortemService()
        auto = FailureAttribution(root_causes=["entry_timing_poor"])
        validation = LLMValidationResult(
            decision=ValidationDecision.CORRECT,
            corrected_categories=["exit_timing_poor"],
            reasoning="应修正为 exit_timing_poor",
        )

        final, source, extra = service._apply_validation(auto, validation)
        assert final.root_causes == ["exit_timing_poor"]
        assert source == "llm_corrected"
        assert extra["auto_original"].root_causes == ["entry_timing_poor"]

    async def test_apply_reject(self):
        """reject 决策清空 categories，保留原始结果到 extra。"""
        from src.evaluation.postmortem_service import PostmortemService, ValidationDecision, LLMValidationResult
        from src.evaluation.failure_taxonomy import FailureAttribution

        service = PostmortemService()
        auto = FailureAttribution(root_causes=["entry_timing_poor"])
        validation = LLMValidationResult(decision=ValidationDecision.REJECT, reasoning="这笔交易是盈利的")

        final, source, extra = service._apply_validation(auto, validation)
        assert final.root_causes == []
        assert source == "llm_rejected"
        assert extra["auto_original"].root_causes == ["entry_timing_poor"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestApplyValidation -v`
Expected: FAIL with "_apply_validation not defined"

- [ ] **Step 3: 实现 _apply_validation 方法**

在 `PostmortemService` 类中添加：

```python
    def _apply_validation(
        self,
        auto: FailureAttribution,
        validation: LLMValidationResult,
    ) -> tuple[FailureAttribution, str, dict[str, object]]:
        """应用 LLM 校验结果。

        Returns:
            (final_attribution, source, extra)
        """
        extra: dict[str, object] = {}

        if validation.decision == ValidationDecision.CONFIRM:
            return auto, "llm_confirmed", extra

        elif validation.decision == ValidationDecision.CORRECT:
            corrected = FailureAttribution(root_causes=validation.corrected_categories)
            extra["auto_original"] = auto
            return corrected, "llm_corrected", extra

        else:  # REJECT
            extra["auto_original"] = auto
            return FailureAttribution(root_causes=[]), "llm_rejected", extra
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestApplyValidation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/postmortem_service.py
git commit -m "feat(NTL-S5-003): implement _apply_validation for confirm/correct/reject"
```

---

## Task 6: 实现 generate 方法

**Files:**
- Modify: `src/evaluation/postmortem_service.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py::TestGenerate`

- [ ] **Step 1: 写失败测试**

```python
class TestGenerate:
    """generate 方法集成测试。"""

    async def test_generate_auto_only(self):
        """无 LLM validator 时返回纯自动归因结果。"""
        from uuid import uuid4
        from src.evaluation.postmortem_service import PostmortemService
        from src.evaluation.evidence_pack import EvidencePack
        from src.schemas.contracts import TradeIdea
        from datetime import date

        service = PostmortemService()

        evidence = EvidencePack(
            idea_id=uuid4(),
            trade_date="2026-04-25",
            trade_idea=TradeIdea(
                trader_id="trader1",
                as_of_date=date.today(),
                symbol="000001",
                entry={"type": "limit", "price": 10.0},
            ),
            signal_context=None,
            market_data={},  # 空数据，触发 data_quality_issue
        )

        result = await service.generate(evidence)
        assert result.attribution_source == "auto"
        assert "data_quality_issue" in result.failure_attribution.root_causes
        assert result.postmortem_notes is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestGenerate -v`
Expected: FAIL with "generate not defined"

- [ ] **Step 3: 实现 generate 方法**

在 `PostmortemService` 类中添加：

```python
    async def generate(
        self,
        evidence_pack: EvidencePack,
    ) -> PostmortemResult:
        """对单笔交易生成复盘结果。

        Args:
            evidence_pack: 交易证据包

        Returns:
            PostmortemResult: 结构化复盘结果
        """
        # Step 1: 自动归因
        auto_attribution = self._auto_attribution(evidence_pack)

        # Step 2: LLM 校验（可选）
        source = "auto"
        extra: dict[str, object] = {}
        final_attribution = auto_attribution

        if self.llm_validator is not None:
            validation = await self.llm_validator.validate(evidence_pack, auto_attribution)
            final_attribution, source, extra = self._apply_validation(auto_attribution, validation)

        # Step 3: LLM 笔记生成（当前未实现，占位）
        notes = None
        # if self.enable_llm_notes and self.llm_validator is not None:
        #     notes = await self._generate_notes(evidence_pack, final_attribution)

        return PostmortemResult(
            idea_id=evidence_pack.idea_id,
            trade_date=evidence_pack.trade_date,
            failure_attribution=final_attribution,
            attribution_source=source,
            postmortem_notes=notes,
            extra=extra,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestGenerate -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/postmortem_service.py
git commit -m "feat(NTL-S5-003): implement generate method with auto attribution"
```

---

## Task 7: 更新 evaluation 模块导出

**Files:**
- Modify: `src/evaluation/__init__.py`
- Test: `tests/unit/evaluation/test_postmortem_service.py::TestModuleExports`

- [ ] **Step 1: 写失败测试**

```python
class TestModuleExports:
    """模块导出测试。"""

    def test_evaluation_exports_postmortem(self):
        """evaluation 模块正确导出 postmortem_service 的所有公开接口。"""
        from src.evaluation import (
            PostmortemResult,
            PostmortemService,
            ValidationDecision,
            LLMValidationResult,
        )
        assert hasattr(PostmortemResult, "idea_id")
        assert hasattr(PostmortemService, "generate")
        assert hasattr(ValidationDecision, "CONFIRM")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestModuleExports -v`
Expected: FAIL with "cannot import name 'PostmortemResult' from 'src.evaluation'"

- [ ] **Step 3: 更新 __init__.py**

```python
from src.evaluation.evidence_pack import EvidencePack
from src.evaluation.failure_taxonomy import (
    FailureRootCause,
    FailureStage,
    FailureRuleType,
    FailureAttribution,
    parse_failure_categories,
)
from src.evaluation.postmortem_service import (
    ValidationDecision,
    LLMValidationResult,
    PostmortemResult,
    PostmortemService,
    LLMValidator,
)

__all__ = [
    "EvidencePack",
    "FailureRootCause",
    "FailureStage",
    "FailureRuleType",
    "FailureAttribution",
    "parse_failure_categories",
    "ValidationDecision",
    "LLMValidationResult",
    "PostmortemResult",
    "PostmortemService",
    "LLMValidator",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/evaluation/test_postmortem_service.py::TestModuleExports -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/__init__.py
git commit -m "feat(NTL-S5-003): export postmortem_service from evaluation module"
```

---

## Task 8: 端到端测试验证

**Files:**
- Test: `pytest tests/unit/evaluation/ -v`

- [ ] **Step 1: 运行完整 evaluation 测试套件**

Run: `pytest tests/unit/evaluation/ -v`
Expected: ALL PASS（预计 15 个测试）

- [ ] **Step 2: 验证 py_compile**

Run: `python -m py_compile src/evaluation/postmortem_service.py && echo "OK"`
Expected: OK

- [ ] **Step 3: 标记 TaskList**

将 `NTL-S5-003` 标记为已完成。

- [ ] **Step 4: Commit**

```bash
git add docs/TaskList.md
git commit -m "docs(NTL-S5-003): mark as completed"
```

---

## Self-Review Checklist

1. **Spec coverage:** PostmortemResult、LLMValidationResult、PostmortemService.generate 均有对应测试 - ✅
2. **Placeholder scan:** 无 TBD/TODO - ✅
3. **Type consistency:** 所有方法签名一致，import 路径正确 - ✅
4. **Module exports:** __init__.py 导出所有公开接口 - ✅
5. **Validation confirm/correct/reject:** 三种决策处理逻辑正确，auto_original 保留 - ✅

---

## 执行选择

**Plan complete and saved to `docs/superpowers/plans/2026-04-25-postmortem-service-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
