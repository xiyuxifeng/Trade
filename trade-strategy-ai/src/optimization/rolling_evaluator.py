"""S7-004: 滚动评估窗口（RollingEvaluator）。

设计原则：
- 窗口按交易日计算（过滤节假日/周末），默认 30 交易日
- 信号稳定性：窗口内出现比例 >= min_signal_frequency（默认 50%）
- 触发条件：稳定性 + 样本量（>= min_sample_trades）同时满足
- 内存存储，进程重启后清零

ref: docs/superpowers/specs/2026-04-28-stage7-s7-004-design.md
"""

from dataclasses import dataclass
from datetime import date as Date
from typing import TYPE_CHECKING

from src.backtest.engine import is_trade_date as _calendar_is_trade_date
from src.common.logger import get_logger

if TYPE_CHECKING:
    from src.optimization.strategy_advisor import RuleAdjustment

logger = get_logger(__name__)


# signal_type 映射表（RuleAdjustment.current_status → SignalObservation.signal_type）
_SIGNAL_TYPE_MAP = {
    "hit_rate_too_low_and_return_negative": "delete_rule",
    "high_hit_rate_but_negative_return": "review_stop_loss",
    "missed_opportunity": "upgrade_rule",
    "missing_snapshot": "check_snapshot",
    "programmable_but_rarely_hit": "delete_rule",
}


@dataclass
class SignalObservation:
    """窗口内观察到的单条信号。"""
    trader_id: str
    signal_type: str
    rule_id: str
    observation_date: Date
    confidence: float


@dataclass
class AdjustmentTrigger:
    """最终触发的调整信号（S7-004 输出）。"""
    trader_id: str
    signal_type: str
    rule_id: str
    trigger_count: int
    signal_frequency: float
    observation_count: int
    sample_trades: int
    confidence: float


@dataclass
class RollingEvaluatorConfig:
    """滚动评估器配置（S7-004）。

    参数说明：
        window_days: 窗口大小（交易日），默认 30
            — 按交易日计算，过滤节假日/周末
        min_signal_frequency: 信号出现比例阈值（含），默认 0.5
            — 窗口内信号出现比例 >= 此值才算稳定
        min_sample_trades: 最小有效交易样本量（含），默认 10
            — 窗口内有效交易笔数 >= 此值才认为样本足够
        trading_days: 可选的交易日历列表，默认 None
            — 若不注入则按自然日近似（简化实现）
            — 传入后 _is_trading_day() 使用此列表判断
    """
    window_days: int = 30
    min_signal_frequency: float = 0.5
    min_sample_trades: int = 10
    trading_days: list[Date] | None = None


class RollingEvaluator:
    """滚动评估器（S7-004）。

    判断调整信号是否在窗口内持续出现，避免单日噪声触发过拟合调整。
    """

    def __init__(self, config: RollingEvaluatorConfig | None = None):
        self.config = config or RollingEvaluatorConfig()
        self._observations: list[SignalObservation] = []
        self._trading_days_set: set | None = None
        if self.config.trading_days:
            self._trading_days_set = set(self.config.trading_days)

    def _is_trading_day(self, d) -> bool:
        """判断是否为交易日。

        若未注入 trading_days，则 fallback 到 A 股日历（TradeCalendar）判断。
        """
        if self._trading_days_set is None:
            return _calendar_is_trade_date(d)
        return d in self._trading_days_set

    def _get_sorted_trading_days(self) -> list:
        """获取排序后的交易日列表（用于窗口计算）。"""
        if self._trading_days_set:
            return sorted(self._trading_days_set)
        return []

    def _prune_old_observations(self) -> None:
        """移除超出 window_days 窗口的旧观察记录。

        窗口按交易日计算：以最后一个观察记录的日期为基准，
        找到倒数第 window_days 个交易日作为窗口起始。
        """
        c = self.config
        if not self._observations:
            return

        sorted_days = self._get_sorted_trading_days()
        if not sorted_days:
            return

        window_start_idx = max(0, len(sorted_days) - c.window_days)
        window_start_date = sorted_days[window_start_idx]

        original_count = len(self._observations)
        self._observations = [
            obs for obs in self._observations
            if obs.observation_date >= window_start_date
        ]
        pruned = original_count - len(self._observations)
        if pruned > 0:
            logger.debug("滚动裁剪: 移除 %d 条旧记录，窗口起始=%s", pruned, window_start_date)

    def push_adjustment(
        self,
        adjustment: "RuleAdjustment",
        observation_date: Date | None = None,
    ) -> None:
        """将 S7-002 的 RuleAdjustment 加入观察窗口。

        每次调用自动裁剪超窗观察记录。

        Args:
            adjustment: S7-002 输出的 RuleAdjustment（可带 trade_date）
            observation_date: 观察日期，优先级最高
                — 次选: adjustment.trade_date（来自历史验真）
                — 默认: Date.today()
        """
        signal_type = _SIGNAL_TYPE_MAP.get(adjustment.current_status, "unknown")
        # 优先级: explicit observation_date > adjustment.trade_date > today
        obs_date = observation_date or adjustment.trade_date or Date.today()
        obs = SignalObservation(
            trader_id=adjustment.trader_id,
            signal_type=signal_type,
            rule_id=adjustment.rule_id,
            observation_date=obs_date,
            confidence=adjustment.confidence,
        )
        self._observations.append(obs)
        self._prune_old_observations()
        logger.debug(
            "Observation added: trader=%s signal=%s rule=%s",
            obs.trader_id, obs.signal_type, obs.rule_id,
        )

    def _get_window_observations(
        self, trader_id: str, signal_type: str, rule_id: str,
    ) -> list[SignalObservation]:
        """获取窗口内匹配的观察记录。"""
        return [
            obs for obs in self._observations
            if obs.trader_id == trader_id
            and obs.signal_type == signal_type
            and obs.rule_id == rule_id
        ]

    def is_signal_stable(
        self, trader_id: str, signal_type: str, rule_id: str,
    ) -> bool:
        """判断信号是否在窗口内持续出现（>= min_signal_frequency）。

        频率 = 窗口内有信号的交易日数 / 窗口内总交易日数。
        """
        c = self.config
        window_obs = self._get_window_observations(trader_id, signal_type, rule_id)
        if not window_obs:
            return False

        # 窗口内总交易日数
        sorted_days = self._get_sorted_trading_days()
        if not sorted_days:
            return False
        window_start_idx = max(0, len(sorted_days) - c.window_days)
        window_trading_days = sorted_days[window_start_idx:]
        total_window_days = len(window_trading_days)

        # 有信号的交易日数（去重）
        unique_days_with_signal = len(set(o.observation_date for o in window_obs))

        if total_window_days == 0:
            return False

        frequency = unique_days_with_signal / total_window_days
        logger.debug(
            "is_signal_stable: trader=%s signal=%s rule=%s freq=%.2f (%d/%d) threshold=%.2f",
            trader_id, signal_type, rule_id,
            frequency, unique_days_with_signal, total_window_days, c.min_signal_frequency,
        )
        return frequency >= c.min_signal_frequency

    def has_sufficient_samples(self, trader_id: str) -> bool:
        """判断窗口内样本量是否足够（>= min_sample_trades）。"""
        c = self.config
        trader_obs = [o for o in self._observations if o.trader_id == trader_id]
        count = len(trader_obs)
        return count >= c.min_sample_trades

    def should_trigger_adjustment(
        self, trader_id: str, signal_type: str, rule_id: str,
    ) -> bool:
        """综合判断是否应触发调整（信号稳定 + 样本足够）。"""
        stable = self.is_signal_stable(trader_id, signal_type, rule_id)
        sufficient = self.has_sufficient_samples(trader_id)
        result = stable and sufficient
        logger.debug(
            "should_trigger: trader=%s signal=%s rule=%s stable=%s sufficient=%s result=%s",
            trader_id, signal_type, rule_id, stable, sufficient, result,
        )
        return result

    def get_trigger(
        self, trader_id: str, signal_type: str, rule_id: str,
    ) -> AdjustmentTrigger | None:
        """获取触发详情（用于日志/报告）。"""
        c = self.config
        window_obs = self._get_window_observations(trader_id, signal_type, rule_id)
        if not window_obs:
            return None

        sorted_days = self._get_sorted_trading_days()
        if sorted_days:
            window_start_idx = max(0, len(sorted_days) - c.window_days)
            window_trading_days = sorted_days[window_start_idx:]
            total_window_days = len(window_trading_days)
        else:
            total_window_days = 0

        unique_days_with_signal = len(set(o.observation_date for o in window_obs))
        avg_confidence = sum(o.confidence for o in window_obs) / len(window_obs)
        trader_obs = [o for o in self._observations if o.trader_id == trader_id]

        return AdjustmentTrigger(
            trader_id=trader_id,
            signal_type=signal_type,
            rule_id=rule_id,
            trigger_count=len(window_obs),
            signal_frequency=unique_days_with_signal / total_window_days if total_window_days else 0.0,
            observation_count=unique_days_with_signal,
            sample_trades=len(trader_obs),
            confidence=avg_confidence,
        )
