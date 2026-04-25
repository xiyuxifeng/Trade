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
