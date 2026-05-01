"""tests/unit/rule_pool/test_mapper.py - DSL 映射工具单元测试"""

import pytest
from src.rule_pool.mapper import (
    OPERATORS,
    STANDARD_FIELDS,
    MAPPING_RULES,
    suggest_mapping,
    validate_mapped_condition,
    build_and_condition,
    build_or_condition,
    build_cmp_condition,
    build_cross_condition,
    build_in_condition,
    build_not_condition,
)


class TestSuggestMapping:
    """测试 suggest_mapping 函数"""

    def test_suggest放量(self):
        """测试放量建议"""
        suggestions = suggest_mapping("放量上涨")
        assert len(suggestions) > 0
        vol_suggest = next((s for s in suggestions if s["pattern"] == "放量"), None)
        assert vol_suggest is not None
        assert vol_suggest["confidence"] == 0.9
        assert vol_suggest["suggestion"]["op"] == "gt"
        assert vol_suggest["suggestion"]["field"] == "volume_ratio"

    def test_suggest缩量(self):
        """测试缩量建议"""
        suggestions = suggest_mapping("缩量调整")
        assert len(suggestions) > 0
        vol_suggest = next((s for s in suggestions if s["pattern"] == "缩量"), None)
        assert vol_suggest is not None
        assert vol_suggest["confidence"] == 0.9
        assert vol_suggest["suggestion"]["op"] == "lt"

    def test_suggest超卖(self):
        """测试超卖建议"""
        suggestions = suggest_mapping("RSI超卖")
        assert len(suggestions) > 0
        rsi_suggest = next((s for s in suggestions if s["pattern"] == "RSI超卖"), None)
        assert rsi_suggest is not None
        assert rsi_suggest["confidence"] == 0.9
        assert rsi_suggest["suggestion"]["op"] == "lt"
        assert rsi_suggest["suggestion"]["field"] == "rsi6"

    def test_suggest超买(self):
        """测试超买建议"""
        suggestions = suggest_mapping("超买信号")
        assert len(suggestions) > 0
        # 优先匹配"超买"模式
        rsi_suggest = next((s for s in suggestions if s["pattern"] == "超买"), None)
        assert rsi_suggest is not None
        assert rsi_suggest["suggestion"]["op"] == "gt"

    def test_suggest金叉(self):
        """测试金叉建议"""
        suggestions = suggest_mapping("MACD金叉")
        assert len(suggestions) > 0
        cross_suggest = next((s for s in suggestions if s["pattern"] == "金叉"), None)
        assert cross_suggest is not None
        assert cross_suggest["suggestion"]["op"] == "cross_above"
        assert cross_suggest["requires_context"] is True

    def test_suggest死叉(self):
        """测试死叉建议"""
        suggestions = suggest_mapping("死叉形成")
        assert len(suggestions) > 0
        cross_suggest = next((s for s in suggestions if s["pattern"] == "死叉"), None)
        assert cross_suggest is not None
        assert cross_suggest["suggestion"]["op"] == "cross_below"

    def test_suggest_ma金叉(self):
        """测试 MA 金叉建议"""
        suggestions = suggest_mapping("ma5金叉ma10")
        assert len(suggestions) > 0

    def test_suggest_无匹配(self):
        """测试无匹配时返回空列表"""
        suggestions = suggest_mapping("这是一个无意义的文本")
        assert len(suggestions) == 0

    def test_suggest_突破(self):
        """测试突破建议"""
        suggestions = suggest_mapping("突破前期高点")
        assert len(suggestions) > 0
        break_suggest = next((s for s in suggestions if s["pattern"] == "突破"), None)
        assert break_suggest is not None
        assert break_suggest["requires_context"] is True


class TestValidateMappedCondition:
    """测试 validate_mapped_condition 函数"""

    def test_valid_simple_condition(self):
        """测试有效的简单条件"""
        cond = {"op": "gt", "field": "close", "value": 100.0}
        valid, msg = validate_mapped_condition(cond)
        assert valid is True
        assert msg == ""

    def test_valid_and_condition(self):
        """测试有效的 AND 条件"""
        cond = {
            "op": "and",
            "conditions": [
                {"op": "gt", "field": "close", "value": 100.0},
                {"op": "lt", "field": "volume", "value": 1000000},
            ]
        }
        valid, msg = validate_mapped_condition(cond)
        assert valid is True
        assert msg == ""

    def test_valid_or_condition(self):
        """测试有效的 OR 条件"""
        cond = {
            "op": "or",
            "conditions": [
                {"op": "gt", "field": "rsi6", "value": 70},
                {"op": "lt", "field": "rsi6", "value": 30},
            ]
        }
        valid, msg = validate_mapped_condition(cond)
        assert valid is True

    def test_valid_not_condition(self):
        """测试有效的 NOT 条件"""
        cond = {
            "op": "not",
            "condition": {"op": "gt", "field": "close", "value": 100.0},
        }
        valid, msg = validate_mapped_condition(cond)
        assert valid is True

    def test_valid_in_condition(self):
        """测试有效的 IN 条件"""
        cond = {
            "op": "in",
            "field": "symbol",
            "values": ["600519", "000858"],
        }
        valid, msg = validate_mapped_condition(cond)
        assert valid is True

    def test_valid_not_in_condition(self):
        """测试有效的 NOT_IN 条件"""
        cond = {
            "op": "not_in",
            "field": "symbol",
            "values": ["ST", "*ST"],
        }
        valid, msg = validate_mapped_condition(cond)
        assert valid is True

    def test_invalid_not_dict(self):
        """测试无效类型"""
        valid, msg = validate_mapped_condition("not a dict")
        assert valid is False
        assert "字典类型" in msg

    def test_invalid_missing_op(self):
        """测试缺少 op 字段"""
        cond = {"field": "close", "value": 100.0}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False
        assert "'op'" in msg

    def test_invalid_unknown_op(self):
        """测试未知操作符"""
        cond = {"op": "unknown_op", "field": "close", "value": 100.0}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False
        assert "不支持的操作符" in msg

    def test_invalid_and_missing_conditions(self):
        """测试 AND 缺少 conditions 字段"""
        cond = {"op": "and"}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False
        assert "'and'" in msg

    def test_invalid_and_single_condition(self):
        """测试 AND 只有一个子条件"""
        cond = {"op": "and", "conditions": [{"op": "gt", "field": "close", "value": 100}]}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False
        assert "至少需要2个" in msg

    def test_invalid_not_missing_condition(self):
        """测试 NOT 缺少 condition 字段"""
        cond = {"op": "not"}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False

    def test_invalid_cmp_missing_field(self):
        """测试比较操作符缺少 field"""
        cond = {"op": "gt", "value": 100.0}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False
        assert "'field'" in msg

    def test_invalid_cmp_missing_value(self):
        """测试比较操作符缺少 value"""
        cond = {"op": "gt", "field": "close"}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False
        assert "'value'" in msg

    def test_invalid_in_missing_values(self):
        """测试 IN 缺少 values 字段"""
        cond = {"op": "in", "field": "symbol"}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False

    def test_invalid_in_values_not_list(self):
        """测试 IN values 不是列表"""
        cond = {"op": "in", "field": "symbol", "values": "not a list"}
        valid, msg = validate_mapped_condition(cond)
        assert valid is False


class TestBuildAndCondition:
    """测试 build_and_condition 函数"""

    def test_build_two_conditions(self):
        """测试构建两个条件的 AND"""
        cond1 = {"op": "gt", "field": "close", "value": 100}
        cond2 = {"op": "lt", "field": "volume", "value": 1000000}
        result = build_and_condition(cond1, cond2)
        assert result["op"] == "and"
        assert len(result["conditions"]) == 2

    def test_build_single_condition(self):
        """测试单个条件返回自身"""
        cond = {"op": "gt", "field": "close", "value": 100}
        result = build_and_condition(cond)
        assert result == cond

    def test_build_empty(self):
        """测试空参数返回空字典"""
        result = build_and_condition()
        assert result == {}

    def test_build_filter_none(self):
        """测试过滤 None 值"""
        cond1 = {"op": "gt", "field": "close", "value": 100}
        result = build_and_condition(cond1, None, {})

    def test_build_multiple_conditions(self):
        """测试多个条件"""
        cond1 = {"op": "gt", "field": "close", "value": 100}
        cond2 = {"op": "lt", "field": "volume", "value": 1000000}
        cond3 = {"op": "eq", "field": "status", "value": "active"}
        result = build_and_condition(cond1, cond2, cond3)
        assert result["op"] == "and"
        assert len(result["conditions"]) == 3


class TestBuildOrCondition:
    """测试 build_or_condition 函数"""

    def test_build_two_conditions(self):
        """测试构建两个条件的 OR"""
        cond1 = {"op": "gt", "field": "rsi6", "value": 70}
        cond2 = {"op": "lt", "field": "rsi6", "value": 30}
        result = build_or_condition(cond1, cond2)
        assert result["op"] == "or"
        assert len(result["conditions"]) == 2

    def test_build_single_condition(self):
        """测试单个条件返回自身"""
        cond = {"op": "gt", "field": "close", "value": 100}
        result = build_or_condition(cond)
        assert result == cond

    def test_build_empty(self):
        """测试空参数返回空字典"""
        result = build_or_condition()
        assert result == {}


class TestBuildCmpCondition:
    """测试 build_cmp_condition 函数"""

    def test_build_gt(self):
        """测试构建 gt 条件"""
        result = build_cmp_condition("close", "gt", 100.0)
        assert result["op"] == "gt"
        assert result["field"] == "close"
        assert result["value"] == 100.0

    def test_build_lt(self):
        """测试构建 lt 条件"""
        result = build_cmp_condition("volume", "lt", 1000000)
        assert result["op"] == "lt"

    def test_build_eq(self):
        """测试构建 eq 条件"""
        result = build_cmp_condition("status", "eq", "active")
        assert result["op"] == "eq"

    def test_build_invalid_op(self):
        """测试无效操作符"""
        with pytest.raises(ValueError, match="不支持的操作符"):
            build_cmp_condition("close", "invalid_op", 100)


class TestBuildCrossCondition:
    """测试 build_cross_condition 函数"""

    def test_build_cross_above(self):
        """测试构建 cross_above 条件"""
        result = build_cross_condition("ma5", "cross_above", "ma10")
        assert result["op"] == "cross_above"
        assert result["field"] == "ma5"
        assert result["other_field"] == "ma10"

    def test_build_cross_below(self):
        """测试构建 cross_below 条件"""
        result = build_cross_condition("macd", "cross_below")
        assert result["op"] == "cross_below"
        assert result["field"] == "macd"
        assert "other_field" not in result

    def test_build_invalid_op(self):
        """测试无效交叉操作符"""
        with pytest.raises(ValueError, match="不支持的交叉操作符"):
            build_cross_condition("ma5", "invalid", "ma10")


class TestBuildInCondition:
    """测试 build_in_condition 函数"""

    def test_build_in(self):
        """测试构建 IN 条件"""
        result = build_in_condition("symbol", ["600519", "000858"])
        assert result["op"] == "in"
        assert result["field"] == "symbol"
        assert result["values"] == ["600519", "000858"]

    def test_build_not_in(self):
        """测试构建 NOT_IN 条件"""
        result = build_in_condition("symbol", ["ST", "*ST"], not_in=True)
        assert result["op"] == "not_in"


class TestBuildNotCondition:
    """测试 build_not_condition 函数"""

    def test_build_not(self):
        """测试构建 NOT 条件"""
        inner_cond = {"op": "gt", "field": "close", "value": 100}
        result = build_not_condition(inner_cond)
        assert result["op"] == "not"
        assert result["condition"] == inner_cond


class TestOperatorsAndFields:
    """测试常量定义"""

    def test_operators_contain_all_expected(self):
        """测试操作符列表包含所有预期操作符"""
        expected = ["and", "or", "not", "gt", "lt", "eq", "gte", "lte", "in", "not_in", "cross_above", "cross_below", "cmp"]
        for op in expected:
            assert op in OPERATORS

    def test_standard_fields_contain_price_fields(self):
        """测试标准字段包含价格字段"""
        price_fields = ["close", "open", "high", "low", "volume"]
        for field in price_fields:
            assert field in STANDARD_FIELDS

    def test_standard_fields_contain_ma_fields(self):
        """测试标准字段包含 MA 字段"""
        ma_fields = ["ma5", "ma10", "ma20", "ma60"]
        for field in ma_fields:
            assert field in STANDARD_FIELDS

    def test_standard_fields_contain_rsi_fields(self):
        """测试标准字段包含 RSI 字段"""
        rsi_fields = ["rsi6", "rsi12", "rsi24"]
        for field in rsi_fields:
            assert field in STANDARD_FIELDS

    def test_mapping_rules_has_expected_patterns(self):
        """测试映射规则包含预期模式"""
        assert ("放量", "volume_ratio_above") in MAPPING_RULES
        assert ("缩量", "volume_ratio_below") in MAPPING_RULES
        assert ("超卖", "rsi_below") in MAPPING_RULES
        assert ("超买", "rsi_above") in MAPPING_RULES