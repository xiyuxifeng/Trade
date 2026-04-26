"""NTL-S6-009: 规则白名单单元测试"""

from __future__ import annotations

import pytest


class TestRuleMeta:
    """RuleMeta 数据结构测试"""

    def test_rule_meta_fields(self):
        """RuleMeta 应包含所有必要字段"""
        from src.backtest.rule_registry import RuleMeta

        meta = RuleMeta(
            rule_id="r1",
            rule_text="RSI < 30",
            required_fields=["rsi"],
            programmatic_level="fully_programmable",
        )
        assert meta.rule_id == "r1"
        assert meta.rule_text == "RSI < 30"
        assert meta.required_fields == ["rsi"]
        assert meta.programmatic_level == "fully_programmable"

    def test_rule_meta_programmatic_levels(self):
        """programmatic_level 必须为合法字面量"""
        from src.backtest.rule_registry import RuleMeta

        for level in ["fully_programmable", "partially_programmable", "descriptive_only", "unsupported"]:
            meta = RuleMeta(
                rule_id="r1",
                rule_text="test",
                required_fields=[],
                programmatic_level=level,
            )
            assert meta.programmatic_level == level


class TestClassifyRule:
    """规则分类器测试"""

    def test_rsi_rule_is_fully_programmable(self):
        """包含 RSI 的规则应标记为 fully_programmable"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"rule_id": "r1", "condition": "rsi < 30"})
        assert meta.programmatic_level == "fully_programmable"
        assert "rsi" in meta.required_fields

    def test_ma_rule_is_fully_programmable(self):
        """包含 MA 的规则应标记为 fully_programmable"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"rule_id": "r2", "condition": "ma5_cross_ma20"})
        assert meta.programmatic_level == "fully_programmable"
        assert "ma" in meta.required_fields

    def test_macd_rule_is_fully_programmable(self):
        """MACD 规则"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"rule_id": "r3", "condition": "macd_signal_cross"})
        assert meta.programmatic_level == "fully_programmable"

    def test_volume_rule_is_fully_programmable(self):
        """成交量规则"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"rule_id": "r4", "condition": "volume > ma_volume * 1.5"})
        assert meta.programmatic_level == "fully_programmable"

    def test_unsupported_rule_when_no_known_indicator(self):
        """无已知技术指标时标记为 unsupported"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"rule_id": "r5", "condition": "市场出现大幅波动"})
        assert meta.programmatic_level == "unsupported"

    def test_descriptive_rule(self):
        """纯描述性规则"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"rule_id": "r6", "condition": "关注市场情绪变化"})
        assert meta.programmatic_level in ("descriptive_only", "unsupported")

    def test_classify_rule_extracts_rule_id(self):
        """分类器应从规则中提取 rule_id"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"rule_id": "custom_rule_001", "condition": "rsi < 30"})
        assert meta.rule_id == "custom_rule_001"

    def test_classify_rule_with_missing_rule_id(self):
        """规则无 rule_id 时应使用空字符串"""
        from src.backtest.rule_registry import classify_rule

        meta = classify_rule({"condition": "rsi < 30"})
        assert meta.rule_id == ""

    def test_classify_rule_returns_rule_meta(self):
        """classify_rule 应返回 RuleMeta 实例"""
        from src.backtest.rule_registry import RuleMeta, classify_rule

        meta = classify_rule({"rule_id": "r1", "condition": "rsi < 30"})
        assert isinstance(meta, RuleMeta)
