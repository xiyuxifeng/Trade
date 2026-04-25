"""failure_taxonomy 测试。"""

from src.evaluation.failure_taxonomy import FailureRootCause, FailureStage, FailureRuleType


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
