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
