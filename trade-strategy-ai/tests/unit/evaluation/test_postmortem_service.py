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


class TestPostmortemResult:
    """单笔交易复盘结果数据类。"""

    def test_creation_with_all_fields(self):
        """所有字段可正确创建。"""
        from uuid import uuid4
        from src.evaluation.postmortem_service import PostmortemResult
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
        from src.evaluation.postmortem_service import PostmortemService, LLMValidator, ValidationDecision, LLMValidationResult
        from src.evaluation.failure_taxonomy import FailureAttribution
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


class TestAutoAttribution:
    """自动归因逻辑测试。"""

    def test_data_quality_issue(self):
        """market_data 为空应标记 data_quality_issue。"""
        from src.evaluation.postmortem_service import PostmortemService
        from src.evaluation.evidence_pack import EvidencePack
        from src.schemas.contracts import TradeIdea
        from datetime import date

        service = PostmortemService()

        evidence = EvidencePack(
            idea_id=None,
            trade_date="2026-04-25",
            trade_idea=TradeIdea(
                trader_id="trader1",
                as_of_date=date.today(),
                symbol="000001",
                entry={"type": "limit", "price": 10.0},
            ),
            signal_context=None,
            market_data={},  # 空数据
        )

        result = service._auto_attribution(evidence)
        assert "data_quality_issue" in result.root_causes

    def test_no_issue_when_data_present(self):
        """market_data 非空且 signal_context 为 None 时应返回空归因。"""
        from src.evaluation.postmortem_service import PostmortemService
        from src.evaluation.evidence_pack import EvidencePack
        from src.schemas.contracts import TradeIdea
        from datetime import date

        service = PostmortemService()

        evidence = EvidencePack(
            idea_id=None,
            trade_date="2026-04-25",
            trade_idea=TradeIdea(
                trader_id="trader1",
                as_of_date=date.today(),
                symbol="000001",
                entry={"type": "limit", "price": 10.0},
            ),
            signal_context=None,
            market_data={"000001": {"close": 10.5}},  # 非空数据
        )

        result = service._auto_attribution(evidence)
        assert result.root_causes == []


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

    async def test_generate_with_validator_confirm(self):
        """有 LLM validator 且 confirm 时返回 llm_confirmed source。"""
        from uuid import uuid4
        from src.evaluation.postmortem_service import PostmortemService, ValidationDecision, LLMValidationResult
        from src.evaluation.evidence_pack import EvidencePack
        from src.schemas.contracts import TradeIdea
        from src.evaluation.failure_taxonomy import FailureAttribution
        from datetime import date

        class MockValidator:
            async def validate(self, evidence_pack, auto_attribution):
                return LLMValidationResult(decision=ValidationDecision.CONFIRM, reasoning="正确")

        service = PostmortemService(llm_validator=MockValidator())

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
            market_data={"000001": {"close": 10.5}},
        )

        result = await service.generate(evidence)
        assert result.attribution_source == "llm_confirmed"
        assert result.failure_attribution.root_causes == []


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
        from dataclasses import fields
        field_names = [f.name for f in fields(PostmortemResult)]
        assert "idea_id" in field_names
        assert hasattr(PostmortemService, "generate")
        assert hasattr(ValidationDecision, "CONFIRM")
