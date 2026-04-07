"""行为标签化模块 — P2-009。

从 TradeLog 分类为 BehaviorLabel。
模块化设计：BehaviorClassifier 接口 + RuleBasedClassifier 实现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import yaml
from src.persona.behavior import BehaviorLabel, BehaviorPattern


class ContextBuilder:
    """从 TradeLog 和 MarketData 构建分类所需的上下文特征。

    计算派生字段（从原始 OHLCV 推导），供规则引擎使用。
    设计支持多周期，但当前仅用日线数据计算。

     派生字段：
      - price_vs_ma: 交易价格 / MA20
      - volume_ratio: 成交量 / 20日均量
      - ma_slope: MA5 斜率（相对于 MA20）
      - distance_from_high: 距离 N 日高点百分比
      - distance_from_low: 距离 N 日低点百分比
      - hour: 交易小时
      - gap_ratio: 跳空比率（今日开盘 vs 昨日收盘）
      - high_breakout_ratio: 突破日高点的幅度
      - low_breakout_ratio: 跌破日低点的幅度
      - price_volatility: 最近5日价格波动率（std/mean）
      - atr_ratio: ATR/收盘价（波动率归一化）
      - close_position: 收盘在当日振幅中的位置（0=低点，1=高点）
    """

    def build(self, trade: Any, bars: list) -> dict:
        """构建分类上下文。

        Args:
            trade: 交易记录（TradeLog）
            bars: 同一标的的日线数据（按 traded_at 升序）

        Returns:
            包含 features（派生字段字典）和 meta 的上下文
        """
        if not bars:
            features = self._default_features()
        else:
            features = self._compute_features(trade, bars)

        return {
            "trade": trade,
            "bars": bars,
            "features": features,
        }

    def _compute_features(self, trade: Any, bars: list) -> dict:
        """计算派生特征。"""
        import statistics

        closes = [float(b.close) for b in bars[-20:]]  # 最近20日
        volumes = [float(b.volume) for b in bars[-20:]]
        highs = [float(b.high) for b in bars[-20:]]
        lows = [float(b.low) for b in bars[-20:]]

        ma20 = sum(closes) / len(closes) if closes else 0
        avg_volume = sum(volumes) / len(volumes) if volumes else 0

        trade_price = float(trade.price)
        volume = float(trade.quantity)

        features = {}

        # 价格 vs MA20
        features["price_vs_ma"] = trade_price / ma20 if ma20 > 0 else 1.0

        # 成交量比（单笔交易量 vs 日均量）
        features["volume_ratio"] = volume / avg_volume if avg_volume > 0 else 1.0

        # MA5 斜率（简化：最近5日 vs 前5日）
        if len(closes) >= 10:
            ma5_recent = sum(closes[-5:]) / 5
            ma5_past = sum(closes[-10:-5]) / 5
            features["ma_slope"] = (ma5_recent - ma5_past) / ma5_past if ma5_past > 0 else 0.0
        else:
            features["ma_slope"] = 0.0

        # 距离 N 日高点
        high_n = max(highs) if highs else trade_price
        features["distance_from_high"] = (high_n - trade_price) / high_n if high_n > 0 else 0.0

        # 距离 N 日低点
        low_n = min(lows) if lows else trade_price
        features["distance_from_low"] = (trade_price - low_n) / low_n if low_n > 0 else 0.0

        # 交易小时
        features["hour"] = trade.executed_at.hour

        # ===== 新增特征 =====

        # 跳空比率（今日开盘 vs 昨日收盘）
        if len(closes) >= 2:
            prev_close = closes[-2]  # 昨日收盘
            today_open = float(bars[-1].open)  # 今日开盘（用最近一根 bar 的 open）
            features["gap_ratio"] = (today_open - prev_close) / prev_close if prev_close > 0 else 0.0
        else:
            features["gap_ratio"] = 0.0

        # 突破日高点比率
        if highs and highs[-1] > 0:
            features["high_breakout_ratio"] = (trade_price - highs[-1]) / highs[-1]
        else:
            features["high_breakout_ratio"] = 0.0

        # 跌破日低点比率
        if lows and lows[-1] > 0:
            features["low_breakout_ratio"] = (lows[-1] - trade_price) / lows[-1]
        else:
            features["low_breakout_ratio"] = 0.0

        # 价格波动率（最近5日收盘价 std/mean）
        recent_closes = closes[-5:] if len(closes) >= 5 else closes
        if len(recent_closes) >= 2:
            mean_close = sum(recent_closes) / len(recent_closes)
            if mean_close > 0:
                features["price_volatility"] = statistics.stdev(recent_closes) / mean_close
            else:
                features["price_volatility"] = 0.0
        else:
            features["price_volatility"] = 0.0

        # ATR（简化为日内振幅均值）/ 收盘价
        if len(bars) >= 14:
            tr_list = []
            for i in range(1, min(15, len(bars))):
                high = float(bars[-i].high)
                low = float(bars[-i].low)
                prev_close = float(bars[-i - 1].close)
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                tr_list.append(tr)
            atr = sum(tr_list) / len(tr_list)
            last_close = float(bars[-1].close)
            features["atr_ratio"] = atr / last_close if last_close > 0 else 0.0
        else:
            features["atr_ratio"] = 0.0

        # 收盘位置（当日振幅中收盘在什么位置，0=低点，1=高点）
        if highs and lows:
            bar_high = float(bars[-1].high)
            bar_low = float(bars[-1].low)
            bar_close = float(bars[-1].close)
            day_range = bar_high - bar_low
            features["close_position"] = (bar_close - bar_low) / day_range if day_range > 0 else 0.5
        else:
            features["close_position"] = 0.5

        return features

    def _default_features(self) -> dict:
        """K线不足时返回默认值。"""
        return {
            "price_vs_ma": 1.0,
            "volume_ratio": 1.0,
            "ma_slope": 0.0,
            "distance_from_high": 0.0,
            "distance_from_low": 0.0,
            "hour": 0,
            "gap_ratio": 0.0,
            "high_breakout_ratio": 0.0,
            "low_breakout_ratio": 0.0,
            "price_volatility": 0.0,
            "atr_ratio": 0.0,
            "close_position": 0.5,
        }


class RuleCondition:
    """单条规则条件。

    支持的比较操作符：gt, lt, ge, le, eq

    Attributes:
        field: 上下文中的字段名（如 price_vs_ma）
        op: 比较操作符
        value: 比较阈值
    """

    def __init__(self, field: str, op: str, value: Any) -> None:
        self.field = field
        self.op = op
        self.value = value

    def evaluate(self, context: dict) -> bool:
        """评估条件是否满足。

        Args:
            context: 包含 features 的上下文字典

        Returns:
            True 如果满足条件
        """
        features = context.get("features", {})
        actual = features.get(self.field)

        if actual is None:
            return False

        if self.op == "gt":
            return actual > self.value
        elif self.op == "lt":
            return actual < self.value
        elif self.op == "ge":
            return actual >= self.value
        elif self.op == "le":
            return actual <= self.value
        elif self.op == "eq":
            return actual == self.value
        return False


@dataclass
class Rule:
    """单条行为分类规则。

    包含多个条件，所有条件都满足时触发。

    Attributes:
        label: 匹配的行为标签
        description: 规则描述
        conditions: 条件列表（AND 关系）
        signals: 触发信号列表
    """

    label: BehaviorLabel
    description: str = ""
    conditions: list[RuleCondition] = None
    signals: list[str] = None

    def __post_init__(self) -> None:
        if self.conditions is None:
            self.conditions = []
        if self.signals is None:
            self.signals = []

    def matches(self, context: dict) -> bool:
        """所有条件都满足时返回 True（AND 逻辑）。"""
        return all(cond.evaluate(context) for cond in self.conditions)


class RuleBasedClassifier:
    """基于 YAML 规则配置的分类器。

    从 YAML 文件加载规则，遍历规则列表，
    返回第一个完全匹配的 BehaviorPattern。
    无匹配时返回 UNKNOWN。

    Attributes:
        rules: 规则列表（按优先级排序）
    """

    def __init__(self, rules_path: str) -> None:
        self.rules = self._load_rules(rules_path)

    def _load_rules(self, rules_path: str) -> list[Rule]:
        """从 YAML 文件加载规则配置。"""
        with open(rules_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        rules = []
        for rule_dict in config.get("rules", []):
            conditions = [
                RuleCondition(
                    field=c["field"],
                    op=c["op"],
                    value=c["value"],
                )
                for c in rule_dict.get("conditions", [])
            ]
            rules.append(Rule(
                label=BehaviorLabel(rule_dict["label"]),
                description=rule_dict.get("description", ""),
                conditions=conditions,
                signals=rule_dict.get("signals", []),
            ))
        return rules

    def classify(self, context: dict) -> BehaviorPattern:
        """对给定上下文进行行为分类。

        Args:
            context: ContextBuilder.build() 返回的上下文

        Returns:
            BehaviorPattern，匹配规则时带对应 label，无匹配时 label=UNKNOWN
        """
        for rule in self.rules:
            if rule.matches(context):
                return BehaviorPattern(
                    label=rule.label,
                    confidence=0.9,  # 规则置信度固定为 0.9
                    signals=rule.signals,
                    context=rule.description,
                )

        # 无匹配
        return BehaviorPattern(
            label=BehaviorLabel.UNKNOWN,
            confidence=0.0,
            signals=[],
            context=None,
        )


class BehaviorLabeler:
    """行为标签化入口类。

    提供统一的高层接口，封装 ContextBuilder 和分类器。

    Example:
        labeler = BehaviorLabeler()
        pattern = labeler.label(trade, daily_bars)
    """

    def __init__(self, rules_path: str | None = None) -> None:
        """初始化 BehaviorLabeler。

        Args:
            rules_path: YAML 规则文件路径，
                        默认为 config/rules/behavior_rules.yaml
        """
        if rules_path is None:
            rules_path = "config/rules/behavior_rules.yaml"
        self.context_builder = ContextBuilder()
        self.classifier = RuleBasedClassifier(rules_path)

    def label(
        self,
        trade: Any,
        market_bars: list,
    ) -> BehaviorPattern:
        """对单笔交易进行行为标签化。

        Args:
            trade: 交易记录（TradeLog）
            market_bars: 同一标的的日线数据（支持多周期预留）

        Returns:
            BehaviorPattern，包含标签、置信度、信号
        """
        context = self.context_builder.build(trade, market_bars)
        return self.classifier.classify(context)
