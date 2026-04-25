"""TraderMemory schemas 单元测试（NTL-S5-005）。"""
import pytest
from datetime import date
from uuid import uuid4

from src.trader_memory.schemas import (
    TraderMemoryType,
    TraderMemoryItem,
    TraderMemorySummary,
)


class TestTraderMemoryType:
    """验证 TraderMemoryType 枚举包含全部 6 种类型。"""

    def test_all_memory_types_present(self):
        assert hasattr(TraderMemoryType, "success_case")
        assert hasattr(TraderMemoryType, "failure_case")
        assert hasattr(TraderMemoryType, "review_note")
        assert hasattr(TraderMemoryType, "postmortem")
        assert hasattr(TraderMemoryType, "strategy_adjustment")
        assert hasattr(TraderMemoryType, "market_regime_note")

    def test_memory_type_values(self):
        assert TraderMemoryType.postmortem.value == "postmortem"
        assert TraderMemoryType.strategy_adjustment.value == "strategy_adjustment"
        assert TraderMemoryType.market_regime_note.value == "market_regime_note"


class TestTraderMemoryItem:
    """验证 TraderMemoryItem 扩展字段。"""

    def test_can_create_with_new_fields(self):
        item = TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            title="Postmortem for SH600519",
            content="Entry timing poor, exit timing ok",
            idea_id=uuid4(),
            strategy_version_id="v_2026_04_25",
            ranking_entry_id=uuid4(),
            postmortem_data={
                "return_pct": 5.2,
                "mfe": 8.0,
                "mae": 2.8,
                "attribution_source": "auto",
                "failure_attribution": {
                    "root_causes": ["entry_timing_poor"],
                    "stage": "stage:entry",
                    "rule_type": "rule_type:entry",
                },
            },
        )
        assert item.memory_type == TraderMemoryType.postmortem
        assert item.postmortem_data["return_pct"] == 5.2
        assert item.idea_id is not None
        assert item.strategy_version_id == "v_2026_04_25"

    def test_can_create_strategy_adjustment(self):
        item = TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.strategy_adjustment,
            as_of_date=date(2026, 4, 25),
            title="Adjust entry rule threshold",
            content="Increase entry price tolerance",
            strategy_adjustment_data={
                "trigger": "postmortem_low_ranking",
                "adjustment_type": "rule_param",
                "target": "entry_price_tolerance",
                "previous_value": 0.02,
                "new_value": 0.03,
                "expected_effect": "reduce false positives",
            },
        )
        assert item.strategy_adjustment_data["trigger"] == "postmortem_low_ranking"
        assert item.strategy_adjustment_data["new_value"] == 0.03

    def test_can_create_market_regime_note(self):
        item = TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.market_regime_note,
            as_of_date=date(2026, 4, 25),
            title="High volatility regime",
            content="VIX > 30, reduce position size",
            market_regime_data={
                "regime_type": "volatile",
                "key_indicators": {"vix": 32.5, "trend_strength": 0.4},
                "note": "Reduce exposure",
            },
        )
        assert item.market_regime_data["regime_type"] == "volatile"


class TestTraderMemorySummary:
    """验证 TraderMemorySummary 扩展字段。"""

    def test_summary_has_new_fields(self):
        summary = TraderMemorySummary(
            trader_id="trader_a",
            postmortem_notes=["Entry timing poor", "Exit timing ok"],
            strategy_adjustments=["Increase entry tolerance"],
            market_regime_notes=["High volatility regime"],
        )
        assert len(summary.postmortem_notes) == 2
        assert len(summary.strategy_adjustments) == 1
        assert len(summary.market_regime_notes) == 1