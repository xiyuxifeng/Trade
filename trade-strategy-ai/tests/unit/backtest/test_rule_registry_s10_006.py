"""S10-006 测试：规则可执行性评分与淘汰。"""

from src.backtest.rule_registry import (
    RuleMeta,
    RuleRegistry,
    classify_rule,
)


class TestRuleProgrammability:
    """验证规则可执行性评分"""

    def test_classify_rule_fully_programmable_with_indicator(self):
        """基于明确指标阈值的规则应标记为 fully_programmable

        注意：中文句子中的指标可能无法被 \b 单词边界匹配
        """
        # 使用英文句子确保能匹配
        rule = {
            "rule_id": "R001",
            "rule_text": "Buy when RSI < 30",
        }
        meta = classify_rule(rule)
        assert meta.programmatic_level == "fully_programmable"
        assert "rsi" in meta.required_fields

    def test_classify_rule_fully_programmable_with_macd(self):
        """MACD 相关规则应标记为 fully_programmable"""
        rule = {
            "rule_id": "R002",
            "rule_text": "MACD金叉买入",
        }
        meta = classify_rule(rule)
        assert meta.programmatic_level == "fully_programmable"
        assert "macd" in meta.required_fields

    def test_classify_rule_partially_programmable(self):
        """提到指标但无明确阈值的规则应标记为 descriptive_only"""
        rule = {
            "rule_id": "R003",
            "rule_text": "观察RSI指标",
        }
        meta = classify_rule(rule)
        # 提到指标但没有明确阈值，是 descriptive_only
        assert meta.programmatic_level == "descriptive_only"

    def test_classify_rule_unsupported(self):
        """无指标引用的规则应标记为 unsupported"""
        rule = {
            "rule_id": "R004",
            "rule_text": "关注公司基本面",
        }
        meta = classify_rule(rule)
        assert meta.programmatic_level == "descriptive_only"  # 包含"关注"关键词

    def test_classify_rule_fully_programmatic_with_price(self):
        """价格相关规则应标记为 fully_programmable"""
        rule = {
            "rule_id": "R005",
            "text": "收盘价突破20日均线买入",
        }
        meta = classify_rule(rule)
        assert meta.programmatic_level == "fully_programmable"

    def test_classify_rule_condition_field(self):
        """规则可以从 condition 字段获取 rule_text"""
        rule = {
            "rule_id": "R006",
            "condition": "RSI < 30",
        }
        meta = classify_rule(rule)
        assert meta.rule_text == "RSI < 30"
        assert meta.programmatic_level == "fully_programmable"


class TestRuleRegistry:
    """验证 RuleRegistry 可执行性过滤"""

    def setup_method(self):
        """每个测试前创建新的 RuleRegistry"""
        self.registry = RuleRegistry()

    def test_register_rule(self):
        """RuleRegistry 可以注册规则"""
        rule_meta = RuleMeta(
            rule_id="R001",
            rule_text="RSI<30买入",
            programmatic_level="fully_programmable",
        )
        self.registry.register_rule(rule_meta)
        assert "R001" in self.registry._rules

    def test_list_programmable_rules_filters_by_level(self):
        """list_programmable_rules 应过滤出可执行性 >= min_level 的规则"""
        # 注册多个规则
        self.registry.register_rule(RuleMeta(
            rule_id="R001",
            rule_text="RSI<30买入",
            programmatic_level="fully_programmable",
        ))
        self.registry.register_rule(RuleMeta(
            rule_id="R002",
            rule_text="观察RSI",
            programmatic_level="descriptive_only",
        ))
        self.registry.register_rule(RuleMeta(
            rule_id="R003",
            rule_text="MACD金叉",
            programmatic_level="fully_programmable",
        ))

        # 默认只返回 fully_programmable
        programmable = self.registry.list_programmable_rules()
        assert len(programmable) == 2
        assert {r.rule_id for r in programmable} == {"R001", "R003"}

    def test_list_programmable_rules_with_min_level_descriptive(self):
        """可以设置 min_level 为 descriptive_only 以包含更多规则"""
        self.registry.register_rule(RuleMeta(
            rule_id="R001",
            rule_text="RSI<30买入",
            programmatic_level="fully_programmable",
        ))
        self.registry.register_rule(RuleMeta(
            rule_id="R002",
            rule_text="观察RSI",
            programmatic_level="descriptive_only",
        ))

        # 设置 min_level 为 descriptive_only
        rules = self.registry.list_programmable_rules(min_level="descriptive_only")
        assert len(rules) == 2

    def test_list_programmable_rules_empty_registry(self):
        """空的 registry 返回空列表"""
        rules = self.registry.list_programmable_rules()
        assert rules == []
