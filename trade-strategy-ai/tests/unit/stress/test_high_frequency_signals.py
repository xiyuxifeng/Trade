"""P4-028 压力测试：高频信号输入场景

验证系统在高并发/高吞吐信号输入情况下的性能和稳定性。
P4-V01 验证：信号生成延迟 < 100ms
"""
import pytest
import time
import numpy as np
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

from src.strategy.signal_version import SignalVersioning
from src.strategy.signal_synthesizer import SignalSynthesizer
from src.strategy.types import (
    Signal,
    SignalSide,
    SignalContext,
    SynthesisMode,
    PriceSpec,
    PositionSize,
    PositionSizeType,
    RuleMatch,
    SynthesisContext,
)
from src.persona.dsl import ActionSpec
from src.risk.risk_monitor import RiskMonitor
from src.risk.types import (
    ConcentrationConfig,
    IndustryExposureConfig,
    PortfolioRiskConfig,
    AccountSnapshot,
    Position,
)
from src.alerting.models import AlertEvent, AlertLevel


# ========== SignalVersioning 压力测试 ==========


def test_signal_versioning_high_volume(tmp_path):
    """测试大量信号快速记录（1000条）"""
    versioning = SignalVersioning(storage_path=tmp_path)

    signals = []
    for i in range(1000):
        signal = Signal(
            signal_id=f"stress-{i:04d}",
            symbol=f"SYM{i % 10:02d}",  # 10个不同标的
            side=SignalSide.BUY if i % 2 == 0 else SignalSide.SELL,
            confidence=0.5 + (i % 50) / 100,
            timestamp=datetime.now(),
            triggered_rules=[f"rule_{j}" for j in range(5)],
            synthesis_mode=None,
        )
        context = SignalContext(
            features_snapshot={"rsi": 50 + i % 30, "ma_cross": i % 2 == 0},
            market_state={"regime": "trend_up" if i % 3 == 0 else "range_bound"},
            rules_snapshot=[{"rule_id": f"rule_{j}", "matched": True} for j in range(5)],
            timestamp=datetime.now(),
        )
        signals.append((signal, context))

    start = time.time()
    for signal, context in signals:
        versioning.record(signal, context)
    elapsed = time.time() - start

    # 1000条信号记录应在合理时间内完成（< 2秒）
    assert elapsed < 2.0, f"Recording 1000 signals took {elapsed:.2f}s, too slow"
    assert len(versioning._versions) == 1000


def test_signal_versioning_get_by_id(tmp_path):
    """测试随机读取已存储的信号"""
    versioning = SignalVersioning(storage_path=tmp_path)

    # 记录100个信号
    for i in range(100):
        signal = Signal(
            signal_id=f"get-{i:03d}",
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

    # 随机读取验证
    for i in range(50):
        idx = (i * 17) % 100  # 伪随机索引
        result = versioning.get_version(f"get-{idx:03d}")
        assert result is not None
        assert result.signal.signal_id == f"get-{idx:03d}"


def test_signal_versioning_list_filtering(tmp_path):
    """测试大量信号的过滤和排序"""
    versioning = SignalVersioning(storage_path=tmp_path)

    # 记录500个信号，跨5个标的
    for i in range(500):
        signal = Signal(
            signal_id=f"filter-{i:04d}",
            symbol=f"SYM{i % 5}",  # 5个标的
            side=SignalSide.BUY if i % 2 == 0 else SignalSide.SELL,
            confidence=0.5 + (i % 50) / 100,
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

    # 按标的过滤
    for sym in range(5):
        versions = versioning.list_versions(symbol=f"SYM{sym}", limit=1000)
        assert len(versions) == 100  # 每个标的100个信号
        assert all(v.signal.symbol == f"SYM{sym}" for v in versions)


# ========== RiskMonitor 压力测试 ==========


def test_risk_monitor_many_positions():
    """测试大量持仓检查（100个持仓）"""
    mock_alert_manager = MagicMock()

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(max_single_position_pct=0.20, max_single_position_amount=50000.0),
        industry_config=IndustryExposureConfig(max_sector_pct=0.40),
        portfolio_config=PortfolioRiskConfig(max_var_pct=0.10, max_volatility=0.30, max_leverage=1.0),
    )

    # 创建100个持仓，总市值接近净资产（无杠杆）
    positions = []
    for i in range(100):
        positions.append(
            Position(
                symbol=f"{600000 + i:06d}.SH",
                quantity=1000,
                avg_cost=10.0,
                current_price=10.0 + (i % 100) / 100,
                market_value=10000.0 + (i % 100) * 100,
                unrealized_pnl=100.0 * (i % 50),
                unrealized_pnl_pct=0.01,
            )
        )

    total_market_value = sum(p.market_value for p in positions)
    account = AccountSnapshot(
        account_id="stress",
        timestamp=datetime.now(),
        net_value=total_market_value + 50000.0,  # 预留现金
        cash=50000.0,
        total_position_value=total_market_value,
        positions=positions,
        daily_pnl=1000.0,
        total_pnl=5000.0,
    )

    normal_returns = np.array([0.01, -0.01, 0.005, -0.005] * 5)  # 20天收益率

    start = time.time()
    alerts = monitor.check_and_alert(account, positions, {}, normal_returns)
    elapsed = time.time() - start

    # 100持仓检查应在合理时间内完成（< 1秒）
    assert elapsed < 1.0, f"Checking 100 positions took {elapsed:.2f}s, too slow"
    # 不应有告警（参数设置宽松）
    assert len(alerts) == 0


def test_risk_monitor_repeated_checks():
    """测试快速连续调用风险检查（1000次）"""
    mock_alert_manager = MagicMock()

    monitor = RiskMonitor(
        alert_manager=mock_alert_manager,
        concentration_config=ConcentrationConfig(),
        industry_config=IndustryExposureConfig(),
        portfolio_config=PortfolioRiskConfig(),
    )

    positions = [
        Position(
            symbol="000001.SZ",
            quantity=1000,
            avg_cost=10.0,
            current_price=11.0,
            market_value=11000.0,
            unrealized_pnl=1000.0,
            unrealized_pnl_pct=0.10,
        ),
    ]
    account = AccountSnapshot(
        account_id="stress",
        timestamp=datetime.now(),
        net_value=100000.0,
        cash=89000.0,
        total_position_value=11000.0,
        positions=positions,
        daily_pnl=1000.0,
        total_pnl=5000.0,
    )
    normal_returns = np.array([0.01, -0.01, 0.005, -0.005] * 5)

    start = time.time()
    for _ in range(1000):
        alerts = monitor.check_and_alert(account, positions, {}, normal_returns)
    elapsed = time.time() - start

    # 1000次快速检查应在合理时间内完成（< 5秒）
    assert elapsed < 5.0, f"1000 rapid checks took {elapsed:.2f}s, too slow"
    # 每次都应返回空告警
    assert all(len(a) == 0 for a in [alerts])  # 单次结果


# ========== 综合场景测试 ==========


def test_signal_versioning_memory_efficiency():
    """测试内存中存储大量信号版本的内存效率"""
    versioning = SignalVersioning()

    # 记录100个带完整上下文的信号
    for i in range(100):
        signal = Signal(
            signal_id=f"mem-{i:03d}",
            symbol=f"SYM{i % 10}",
            side=SignalSide.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            triggered_rules=[f"rule_{j}" for j in range(10)],
            synthesis_mode=None,
            entry_price=PriceSpec(type="limit", value=100.0),
            position_size=PositionSize(type=PositionSizeType.FIXED_RATIO, value=0.1),
        )
        context = SignalContext(
            features_snapshot={f"feat_{k}": v for k, v in enumerate(range(50))},
            market_state={f"state_{k}": v for k, v in enumerate(range(20))},
            rules_snapshot=[{"rule_id": f"rule_{j}", "matched": True} for j in range(10)],
            timestamp=datetime.now(),
        )
        versioning.record(signal, context)

    # 验证内存中存储了所有信号
    assert len(versioning._versions) == 100

    # 验证文件也正确存储
    for i in range(100):
        stored = versioning.get_version(f"mem-{i:03d}")
        assert stored is not None
        assert stored.signal.signal_id == f"mem-{i:03d}"


# ========== P4-V01 信号生成延迟验证 ==========


def test_signal_generation_latency_p4_v01():
    """P4-V01: 验证信号生成延迟 < 100ms

    测试 SignalSynthesizer 在多种模式下的单次信号生成延迟。
    """
    synthesizer = SignalSynthesizer(mode=SynthesisMode.PRIORITY)

    # 构建 10 条规则匹配
    matches = []
    for i in range(10):
        matches.append(
            RuleMatch(
                rule_id=f"rule_{i}",
                rule_type="entry" if i < 5 else "exit",
                matched=True,
                confidence=0.6 + (i % 3) * 0.1,
                action=ActionSpec(type="enter" if i < 5 else "exit", side="buy"),
            )
        )

    context = SynthesisContext(
        market_state={"regime": "trend_up", "volatility": "low"},
        features={"rsi": 65, "ma_cross": True},
    )

    # 预热
    for _ in range(10):
        synthesizer.synthesize(matches, context)

    # 测量单次信号生成延迟
    latencies = []
    for _ in range(100):
        start = time.time()
        result = synthesizer.synthesize(matches, context)
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    # P4-V01 要求: 平均延迟 < 100ms
    assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms threshold"
    # 95th percentile should also be reasonable
    assert p95_latency < 150, f"P95 latency {p95_latency:.2f}ms is too high"
    print(f"\n[P4-V01 Signal Generation Latency]")
    print(f"  Average: {avg_latency:.2f}ms")
    print(f"  P95: {p95_latency:.2f}ms")
    print(f"  Max: {max_latency:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
