"""
Lark DSL Parser 单元测试 — P4-015。
"""

from __future__ import annotations

import pytest

from src.persona.dsl import ConditionExpr
from src.persona.lark_parser import (
    DSLParser,
    parse_dsl,
    parse_dsl_many,
    get_parser,
)


@pytest.fixture
def parser():
    """创建 Parser 实例。"""
    return DSLParser()


class TestDSLParser:
    """DSL Parser 测试。"""

    def test_parse_true(self, parser):
        """解析 TRUE 常量。"""
        result = parser.parse("TRUE")
        assert result.op == "true"
        assert result.field is None
        assert result.cmp is None
        assert result.value is None

    def test_parse_false(self, parser):
        """解析 FALSE 常量。"""
        result = parser.parse("FALSE")
        assert result.op == "false"

    def test_parse_cmp_eq(self, parser):
        """解析 eq 比较。"""
        result = parser.parse('cmp(regime, eq, trend_up)')
        assert result.op == "cmp"
        assert result.field == "regime"
        assert result.cmp == "eq"
        assert result.value == "trend_up"

    def test_parse_cmp_gt(self, parser):
        """解析 gt 比较。"""
        result = parser.parse("cmp(price, gt, 100.5)")
        assert result.op == "cmp"
        assert result.field == "price"
        assert result.cmp == "gt"
        assert result.value == 100.5

    def test_parse_cmp_lt(self, parser):
        """解析 lt 比较。"""
        result = parser.parse("cmp(volume, lt, 1000000)")
        assert result.op == "cmp"
        assert result.cmp == "lt"

    def test_parse_cmp_in(self, parser):
        """解析 in 操作符。"""
        result = parser.parse("cmp(regime, in, [trend_up, trend_down])")
        assert result.op == "cmp"
        assert result.cmp == "in"
        assert result.value == ["trend_up", "trend_down"]

    def test_parse_and(self, parser):
        """解析 AND 表达式。"""
        result = parser.parse("AND(cmp(regime, eq, trend_up), cmp(volatility, in, [low, mid]))")
        assert result.op == "and"
        assert len(result.args) == 2
        assert all(arg.op == "cmp" for arg in result.args)

    def test_parse_or(self, parser):
        """解析 OR 表达式。"""
        result = parser.parse("OR(cmp(regime, eq, bullish), cmp(regime, eq, neutral))")
        assert result.op == "or"
        assert len(result.args) == 2

    def test_parse_not(self, parser):
        """解析 NOT 表达式。"""
        result = parser.parse("NOT(cmp(regime, eq, bearish))")
        assert result.op == "not"
        assert len(result.args) == 1
        assert result.args[0].op == "cmp"

    def test_parse_nested(self, parser):
        """解析嵌套表达式。"""
        result = parser.parse("AND(NOT(cmp(regime, eq, bearish)), cmp(volume, gt, 1000))")
        assert result.op == "and"
        assert len(result.args) == 2

    def test_parse_cmp_ne(self, parser):
        """解析 ne (not equal) 比较。"""
        result = parser.parse("cmp(regime, ne, trend_up)")
        assert result.op == "cmp"
        assert result.field == "regime"
        assert result.cmp == "ne"
        assert result.value == "trend_up"

    def test_parse_cmp_ge(self, parser):
        """解析 ge (greater than or equal) 比较。"""
        result = parser.parse("cmp(price, ge, 100.0)")
        assert result.op == "cmp"
        assert result.field == "price"
        assert result.cmp == "ge"
        assert result.value == 100.0

    def test_parse_cmp_le(self, parser):
        """解析 le (less than or equal) 比较。"""
        result = parser.parse("cmp(price, le, 50.0)")
        assert result.op == "cmp"
        assert result.field == "price"
        assert result.cmp == "le"
        assert result.value == 50.0

    def test_parse_cmp_not_in(self, parser):
        """解析 not_in 操作符。"""
        result = parser.parse("cmp(regime, not_in, [trend_up, trend_down])")
        assert result.op == "cmp"
        assert result.cmp == "not_in"
        assert result.value == ["trend_up", "trend_down"]

    def test_parse_cmp_string_value(self, parser):
        """解析带字符串值（引号）的比较。"""
        result = parser.parse('cmp(symbol, eq, "BTC/USDT")')
        assert result.op == "cmp"
        assert result.field == "symbol"
        assert result.cmp == "eq"
        assert result.value == "BTC/USDT"

    def test_parse_cmp_boolean_value(self, parser):
        """解析带布尔值的比较。"""
        result = parser.parse("cmp(is_active, eq, true)")
        assert result.op == "cmp"
        assert result.field == "is_active"
        assert result.cmp == "eq"
        assert result.value is True

    def test_parse_deeply_nested(self, parser):
        """解析多层嵌套表达式。"""
        result = parser.parse("AND(OR(cmp(regime, eq, bullish), cmp(regime, eq, neutral)), NOT(cmp(volatility, in, [high])))")
        assert result.op == "and"
        assert result.args[0].op == "or"
        assert result.args[1].op == "not"

    def test_parse_invalid(self, parser):
        """解析无效表达式。"""
        with pytest.raises(ValueError):
            parser.parse("INVALID_SYNTAX")


class TestConvenienceFunctions:
    """便捷函数测试。"""

    def test_parse_dsl(self):
        """测试便捷 parse_dsl 函数。"""
        result = parse_dsl("TRUE")
        assert result.op == "true"

    def test_parse_dsl_many(self):
        """测试批量解析。"""
        texts = ["TRUE", "FALSE", "cmp(regime, eq, trend_up)"]
        results = parse_dsl_many(texts)
        assert len(results) == 3
        assert results[0].op == "true"
        assert results[1].op == "false"
        assert results[2].op == "cmp"

    def test_singleton_parser(self):
        """测试单例 Parser。"""
        parser1 = get_parser()
        parser2 = get_parser()
        assert parser1 is parser2


class TestRoundTrip:
    """解析后回写测试。"""

    def test_simple_condition_roundtrip(self, parser):
        """简单条件解析后回写。"""
        original = 'cmp(regime, eq, trend_up)'
        result = parser.parse(original)
        # 重新解析应该得到相同结果
        result2 = parser.parse(original)
        assert result.op == result2.op
        assert result.field == result2.field
        assert result.cmp == result2.cmp
        assert result.value == result2.value


class TestIntegration:
    """集成测试。"""

    def test_parser_with_existing_compiler(self):
        """测试 Parser 与现有 Compiler 集成。"""
        from src.persona.dsl_compiler import compile_rule

        # 解析 DSL
        dsl_text = "AND(cmp(regime, eq, trend_up), cmp(volatility, in, [low, mid]))"
        expr = parse_dsl(dsl_text)

        # 使用现有 compiler 编译
        compiled = compile_rule(expr)

        # 验证编译结果
        assert compiled.rule_type == "filter"
        assert compiled.matches(state={"regime": "trend_up", "volatility": "low"}, bar={}) is True
        assert compiled.matches(state={"regime": "bearish", "volatility": "low"}, bar={}) is False
