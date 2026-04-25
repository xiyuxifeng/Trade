"""failure_taxonomy 测试。"""

from src.evaluation.failure_taxonomy import FailureRootCause


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
