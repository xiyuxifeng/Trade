"""SignalVersioning 单元测试"""
import pytest
from datetime import date, datetime
from src.strategy.signal_version import SignalVersioning
from src.strategy.types import Signal, SignalSide, SignalContext


def test_record_and_get():
    """测试记录和获取"""
    versioning = SignalVersioning()

    signal = Signal(
        signal_id="test-001",
        symbol="TEST",
        side=SignalSide.BUY,
        confidence=0.8,
        timestamp=datetime.now(),
        triggered_rules=["rule1"],
        synthesis_mode=None,
    )
    context = SignalContext(
        features_snapshot={"rsi": 70},
        market_state={"regime": "trend_up"},
        rules_snapshot=[],
        timestamp=datetime.now(),
    )

    version_id = versioning.record(signal, context)
    assert version_id is not None

    result = versioning.get_version(version_id)
    assert result is not None
    assert result.signal.signal_id == "test-001"


def test_list_versions():
    """测试列出版本"""
    versioning = SignalVersioning()

    for i in range(5):
        signal = Signal(
            signal_id=f"test-{i:03d}",
            symbol="TEST",
            side=SignalSide.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            triggered_rules=[],
            synthesis_mode=None,
        )
        context = SignalContext(
            features_snapshot={},
            market_state={},
            rules_snapshot=[],
            timestamp=datetime.now(),
        )
        versioning.record(signal, context)

    versions = versioning.list_versions(symbol="TEST", limit=10)
    assert len(versions) == 5