import pytest
from datetime import date

from src.optimization.rolling_evaluator import (
    RollingEvaluator,
    RollingEvaluatorConfig,
    SignalObservation,
    AdjustmentTrigger,
)
from src.optimization.strategy_advisor import RuleAdjustment

# 当前日期 2026-04-28，确保包含在交易日历中
_TODAY = date(2026, 4, 28)

# Mock 交易日历（10 个交易日，包含今天）
_MOCK_TRADING_DAYS = [
    date(2026, 4, 8), date(2026, 4, 9), date(2026, 4, 10),
    date(2026, 4, 15), date(2026, 4, 16), date(2026, 4, 17),
    date(2026, 4, 22), date(2026, 4, 23), date(2026, 4, 24),
    _TODAY,
]


def make_rvr(status: str = "hit_rate_too_low_and_return_negative") -> RuleAdjustment:
    return RuleAdjustment(
        trader_id="T1", rule_id="R1", rule_text="测试规则",
        current_status=status, suggestion="测试建议",
        confidence=0.8, hit_rate=0.05, posterior_return_mean=-0.02,
        posterior_return_median=None,
    )


def inject_observations(ev: RollingEvaluator, dates: list[date], **obs_kwargs):
    """直接向 _observations 注入指定日期的 SignalObservation，绕过 push_adjustment 的 date.today() 限制。"""
    for d in dates:
        ev._observations.append(SignalObservation(
            trader_id=obs_kwargs.get("trader_id", "T1"),
            signal_type=obs_kwargs.get("signal_type", "delete_rule"),
            rule_id=obs_kwargs.get("rule_id", "R1"),
            observation_date=d,
            confidence=obs_kwargs.get("confidence", 0.8),
        ))


class TestRollingEvaluator:
    def test_single_signal_not_stable(self):
        """单日信号不满足稳定性阈值"""
        config = RollingEvaluatorConfig(
            window_days=30, min_signal_frequency=0.5,
            trading_days=_MOCK_TRADING_DAYS,
        )
        ev = RollingEvaluator(config)
        inject_observations(ev, [_MOCK_TRADING_DAYS[0]])
        assert ev.is_signal_stable("T1", "delete_rule", "R1") is False

    def test_signal_stable_at_threshold(self):
        """信号出现比例正好 50% 时应通过"""
        config = RollingEvaluatorConfig(
            window_days=30, min_signal_frequency=0.5,
            trading_days=_MOCK_TRADING_DAYS,
        )
        ev = RollingEvaluator(config)
        # 前 5 个交易日各一条信号 → 5 unique days / 10 window days = 50%
        inject_observations(ev, _MOCK_TRADING_DAYS[:5])
        assert ev.is_signal_stable("T1", "delete_rule", "R1") is True

    def test_insufficient_samples_no_trigger(self):
        """样本量不足时不触发"""
        config = RollingEvaluatorConfig(
            window_days=30, min_signal_frequency=0.5,
            min_sample_trades=10, trading_days=_MOCK_TRADING_DAYS,
        )
        ev = RollingEvaluator(config)
        inject_observations(ev, [_MOCK_TRADING_DAYS[0], _MOCK_TRADING_DAYS[1]])
        assert ev.should_trigger_adjustment("T1", "delete_rule", "R1") is False

    def test_both_conditions_needed(self):
        """信号稳定 + 样本足够 → 触发"""
        config = RollingEvaluatorConfig(
            window_days=30, min_signal_frequency=0.5,
            min_sample_trades=5, trading_days=_MOCK_TRADING_DAYS,
        )
        ev = RollingEvaluator(config)
        # 5 条信号分布在 5 个交易日 → 5/10=50% 稳定，样本量=5
        inject_observations(ev, _MOCK_TRADING_DAYS[:5])
        assert ev.should_trigger_adjustment("T1", "delete_rule", "R1") is True

    def test_no_observation_returns_false(self):
        """无观察记录时返回 False"""
        ev = RollingEvaluator(RollingEvaluatorConfig(trading_days=_MOCK_TRADING_DAYS))
        assert ev.is_signal_stable("T1", "delete_rule", "R1") is False
        assert ev.should_trigger_adjustment("T1", "delete_rule", "R1") is False

    def test_get_trigger_returns_details(self):
        """get_trigger 返回正确详情"""
        config = RollingEvaluatorConfig(
            window_days=30, min_signal_frequency=0.5,
            min_sample_trades=3, trading_days=_MOCK_TRADING_DAYS,
        )
        ev = RollingEvaluator(config)
        inject_observations(ev, _MOCK_TRADING_DAYS[:3])
        trigger = ev.get_trigger("T1", "delete_rule", "R1")
        assert trigger is not None
        assert trigger.trigger_count == 3
        assert trigger.sample_trades == 3
        assert 0.0 <= trigger.signal_frequency <= 1.0

    def test_unknown_status_maps_to_unknown(self):
        """未知 status 映射为 unknown signal_type"""
        config = RollingEvaluatorConfig(trading_days=_MOCK_TRADING_DAYS)
        ev = RollingEvaluator(config)
        # 1 条信号，1 个交易日 / 10 窗口交易日 = 10% < 50% → 不稳定
        inject_observations(ev, [_MOCK_TRADING_DAYS[0]], signal_type="unknown")
        assert ev.is_signal_stable("T1", "unknown", "R1") is False

    def test_has_sufficient_samples(self):
        """has_sufficient_samples 正确判断"""
        config = RollingEvaluatorConfig(
            window_days=30, min_signal_frequency=0.5,
            min_sample_trades=3, trading_days=_MOCK_TRADING_DAYS,
        )
        ev = RollingEvaluator(config)
        assert ev.has_sufficient_samples("T1") is False
        inject_observations(ev, _MOCK_TRADING_DAYS[:3])
        assert ev.has_sufficient_samples("T1") is True

    def test_trading_day_filter(self):
        """observation_count = 有信号的交易日数（去重）"""
        config = RollingEvaluatorConfig(
            window_days=5, min_signal_frequency=0.5,
            trading_days=_MOCK_TRADING_DAYS,
        )
        ev = RollingEvaluator(config)
        # 10 条信号，但分布在 3 个不同交易日
        inject_observations(ev, [
            _MOCK_TRADING_DAYS[0], _MOCK_TRADING_DAYS[0], _MOCK_TRADING_DAYS[0],  # 3条在第1天
            _MOCK_TRADING_DAYS[1], _MOCK_TRADING_DAYS[1],  # 2条在第2天
            _MOCK_TRADING_DAYS[2], _MOCK_TRADING_DAYS[2], _MOCK_TRADING_DAYS[2],  # 3条在第3天
            _MOCK_TRADING_DAYS[3], _MOCK_TRADING_DAYS[3],  # 2条在第4天
        ])
        trigger = ev.get_trigger("T1", "delete_rule", "R1")
        assert trigger is not None
        assert trigger.trigger_count == 10
        assert trigger.observation_count == 4  # 4 个唯一交易日
