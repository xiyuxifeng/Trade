"""S10-003 测试：preconditions 前置条件门槛检查。"""

from src.agents.strategy_agent.agent import StrategyAgent


class TestPreconditionsGate:
    """验证 preconditions 前置条件门槛检查"""

    def setup_method(self):
        """每个测试方法前创建新的 StrategyAgent 实例"""
        self.agent = StrategyAgent()

    def test_rule_without_precondition_is_always_included(self):
        """无前置条件的规则始终参与评估"""
        rules = [
            {"rule_id": "R001", "rule_text": "RSI<30买入"},
            {"rule_id": "R002", "rule_text": "MACD金叉"},
        ]
        market_data = {"market_trend": "bearish", "volume_ratio": 0.8}

        satisfied = self.agent._filter_rules_by_preconditions(rules, market_data)
        assert len(satisfied) == 2
        assert {r["rule_id"] for r in satisfied} == {"R001", "R002"}

    def test_rule_with_satisfied_precondition_is_included(self):
        """前置条件满足的规则应参与评估"""
        rules = [
            {
                "rule_id": "R001",
                "rule_text": "RSI<30买入",
                "preconditions": [
                    {"field": "market_trend", "operator": "==", "value": "bullish"},
                ],
            },
        ]
        market_data = {"market_trend": "bullish"}

        satisfied = self.agent._filter_rules_by_preconditions(rules, market_data)
        assert len(satisfied) == 1
        assert satisfied[0]["rule_id"] == "R001"

    def test_rule_with_unsatisfied_precondition_is_excluded(self):
        """前置条件不满足的规则应被跳过"""
        rules = [
            {
                "rule_id": "R001",
                "rule_text": "RSI<30买入",
                "preconditions": [
                    {"field": "market_trend", "operator": "==", "value": "bullish"},
                ],
            },
        ]
        market_data = {"market_trend": "bearish"}

        satisfied = self.agent._filter_rules_by_preconditions(rules, market_data)
        assert len(satisfied) == 0

    def test_rule_with_multiple_preconditions_all_met(self):
        """多个前置条件都满足时规则参与评估"""
        rules = [
            {
                "rule_id": "R001",
                "rule_text": "RSI<30买入",
                "preconditions": [
                    {"field": "market_trend", "operator": "==", "value": "bullish"},
                    {"field": "volume_ratio", "operator": ">", "value": 1.5},
                ],
            },
        ]
        market_data = {"market_trend": "bullish", "volume_ratio": 2.0}

        satisfied = self.agent._filter_rules_by_preconditions(rules, market_data)
        assert len(satisfied) == 1

    def test_rule_with_multiple_preconditions_one_fails(self):
        """多个前置条件中有一个不满足时规则被跳过"""
        rules = [
            {
                "rule_id": "R001",
                "rule_text": "RSI<30买入",
                "preconditions": [
                    {"field": "market_trend", "operator": "==", "value": "bullish"},
                    {"field": "volume_ratio", "operator": ">", "value": 1.5},
                ],
            },
        ]
        market_data = {"market_trend": "bullish", "volume_ratio": 0.8}

        satisfied = self.agent._filter_rules_by_preconditions(rules, market_data)
        assert len(satisfied) == 0

    def test_rule_with_missing_market_data_field_is_excluded(self):
        """前置条件中引用的字段在 market_data 中不存在时规则被跳过"""
        rules = [
            {
                "rule_id": "R001",
                "rule_text": "RSI<30买入",
                "preconditions": [
                    {"field": "nonexistent_field", "operator": "==", "value": "something"},
                ],
            },
        ]
        market_data = {"market_trend": "bullish"}

        satisfied = self.agent._filter_rules_by_preconditions(rules, market_data)
        assert len(satisfied) == 0

    def test_compare_values_greater_than(self):
        """大于比较操作符"""
        assert self.agent._compare_values(2.0, ">", 1.5) is True
        assert self.agent._compare_values(1.0, ">", 1.5) is False

    def test_compare_values_less_than(self):
        """小于比较操作符"""
        assert self.agent._compare_values(1.0, "<", 1.5) is True
        assert self.agent._compare_values(2.0, "<", 1.5) is False

    def test_compare_values_equal(self):
        """等于比较操作符"""
        assert self.agent._compare_values("bullish", "==", "bullish") is True
        assert self.agent._compare_values("bearish", "==", "bullish") is False

    def test_compare_values_in_list(self):
        """in 操作符"""
        assert self.agent._compare_values("AAPL", "in", ["AAPL", "GOOGL"]) is True
        assert self.agent._compare_values("MSFT", "in", ["AAPL", "GOOGL"]) is False

    def test_compare_values_not_equal(self):
        """不等于比较操作符"""
        assert self.agent._compare_values("bearish", "!=", "bullish") is True
        assert self.agent._compare_values("bullish", "!=", "bullish") is False

    def test_compare_values_greater_than_or_equal(self):
        """大于等于比较操作符"""
        assert self.agent._compare_values(1.5, ">=", 1.5) is True
        assert self.agent._compare_values(1.4, ">=", 1.5) is False

    def test_compare_values_less_than_or_equal(self):
        """小于等于比较操作符"""
        assert self.agent._compare_values(1.5, "<=", 1.5) is True
        assert self.agent._compare_values(1.6, "<=", 1.5) is False

    def test_compare_values_not_in_list(self):
        """not in 操作符"""
        assert self.agent._compare_values("MSFT", "not in", ["AAPL", "GOOGL"]) is True
        assert self.agent._compare_values("AAPL", "not in", ["AAPL", "GOOGL"]) is False

    def test_mixed_rules_with_and_without_preconditions(self):
        """混合场景：部分规则有前置条件，部分没有"""
        rules = [
            {"rule_id": "R001", "rule_text": "无前置条件规则"},
            {
                "rule_id": "R002",
                "rule_text": "有前置条件",
                "preconditions": [{"field": "trend", "operator": "==", "value": "up"}],
            },
            {"rule_id": "R003", "rule_text": "也无前置条件"},
        ]
        market_data = {"trend": "down"}

        satisfied = self.agent._filter_rules_by_preconditions(rules, market_data)
        # 只有 R001 和 R003 通过（无前置条件）
        assert len(satisfied) == 2
        assert {r["rule_id"] for r in satisfied} == {"R001", "R003"}
