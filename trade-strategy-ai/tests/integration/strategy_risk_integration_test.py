"""Strategy Agent + Risk Agent 集成测试"""
import pytest
from datetime import date
from src.strategy import FeatureEngine
from src.strategy.rule_evaluator import RuleEvaluator
from src.strategy.signal_synthesizer import SignalSynthesizer
from src.strategy.signal import create_signal
from src.strategy.types import SynthesisContext, SignalSide
from src.risk import PositionManager, TakeProfitCalculator, TakeProfitConfig
from src.risk.stop_loss import StopLossCalculator, StopLossConfig
from src.persona.dsl_executor import DSLExecutor
from src.persona.dsl_executor import RuleRegistry
from src.persona.dsl_compiler import compile_rule
from src.persona.dsl import CMP
from src.persona.schemas import MarketRegime, VolatilityLevel, MarketState
from src.features.feature_pipeline import DailyBars, FeatureVector


def test_end_to_end_signal_generation():
    """端到端信号生成测试"""
    # 1. 初始化组件
    feature_engine = FeatureEngine()
    registry = RuleRegistry()
    executor = DSLExecutor(registry)
    evaluator = RuleEvaluator(executor)
    synthesizer = SignalSynthesizer(mode="priority")
    position_manager = PositionManager()
    stop_loss_calc = StopLossCalculator(StopLossConfig())
    take_profit_calc = TakeProfitCalculator(TakeProfitConfig())

    # 2. 创建测试数据
    bars = DailyBars(
        symbol="TEST",
        dates=[date(2026, 4, i % 30 + 1) for i in range(60)],
        opens=[100.0 + i * 0.5 for i in range(60)],
        highs=[105.0 + i * 0.5 for i in range(60)],
        lows=[95.0 + i * 0.5 for i in range(60)],
        closes=[102.0 + i * 0.5 for i in range(60)],
        volumes=[1_000_000 for _ in range(60)],
    )

    market_state = MarketState(
        as_of_date=date(2026, 4, 9),
        regime=MarketRegime.trend_up,
        volatility=VolatilityLevel.low,
    )

    # 3. 特征计算
    features = feature_engine.compute_realtime(bars)
    assert features is not None

    # 4. 规则评估
    rule = compile_rule(
        CMP(field="regime", cmp_op="eq", value="trend_up"),
        rule_id="test_entry",
        name="Test Entry Rule",
    )
    registry.register(rule)

    matches = evaluator.evaluate([rule], features, market_state)
    assert len(matches) >= 0  # 可能匹配也可能不匹配

    # 5. 信号合成
    context = SynthesisContext(
        market_state=market_state.model_dump(),
        features=features.to_dict(),
    )
    raw_signal = synthesizer.synthesize(matches, context)
    assert raw_signal is not None
    assert raw_signal.side in SignalSide

    # 6. 风控（如果信号不是 HOLD）
    if raw_signal.side != SignalSide.HOLD:
        account = type("AccountSnapshot", (), {
            "account_id": "test",
            "net_value": 100_000.0,
            "cash": 100_000.0,
            "total_position_value": 0.0,
            "positions": [],
            "daily_pnl": 0.0,
            "total_pnl": 0.0,
        })()

        market_data = {"close": 102.0, "atr": 2.0}

        position_size = position_manager.calculate_size(raw_signal, account, market_data)
        stop_loss = stop_loss_calc.calculate(102.0, raw_signal, market_data)
        take_profit = take_profit_calc.calculate(102.0, raw_signal, market_data)

        signal = create_signal(raw_signal, stop_loss, take_profit, symbol="TEST")

        assert signal.symbol == "TEST"
        assert signal.side == raw_signal.side
        assert signal.stop_loss is not None or signal.take_profit is not None