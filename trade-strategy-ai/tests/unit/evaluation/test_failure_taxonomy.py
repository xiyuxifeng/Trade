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
        assert result.rule_type is None
