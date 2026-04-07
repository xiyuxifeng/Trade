"""
Pattern Matcher Engine — 在 K 线数据上扫描匹配模式。

给定 OHLCV 数据和 PatternLibrary，输出所有匹配结果。

Schema 版本: v1 (2026-04-07)

设计：
  - 与数据源解耦（支持真实 OHLCV 或 mock 数据）
  - 与模式类型解耦（支持 canonical / article / validated 三种）
  - 条件操作符可扩展
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from src.persona.patterns import (
    ArticlePattern,
    BasePattern,
    CanonicalPattern,
    Condition,
    PatternLibrary,
    PatternType,
    Timeframe,
    ValidatedPattern,
)


# ---------------------------------------------------------------------------
# OHLCV Data Protocol — 数据源抽象
# ---------------------------------------------------------------------------


class OHLCV:
    """一根 K 线的数据。"""

    def __init__(
        self,
        symbol: str,
        date: str | datetime,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        **extra: Any,
    ):
        self.symbol = symbol
        self.date = date if isinstance(date, str) else date.isoformat()
        self.open = float(open)
        self.high = float(high)
        self.low = float(low)
        self.close = float(close)
        self.volume = float(volume)
        self.extra: dict[str, Any] = extra

    def __repr__(self) -> str:
        return f"OHLCV({self.date} {self.symbol} O:{self.open:.2f} H:{self.high:.2f} L:{self.low:.2f} C:{self.close:.2f} V:{self.volume:.0f})"


class OHLCVDataSource(Protocol):
    """K 线数据源抽象。实现此接口即可对接任意数据。"""

    def bars(self, symbol: str, limit: int | None = None) -> list[OHLCV]:
        """Return OHLCV bars for a symbol, oldest first."""
        ...


# ---------------------------------------------------------------------------
# Match Result
# ---------------------------------------------------------------------------


class MatchStatus(StrEnum):
    MATCHED = "matched"
    NO_MATCH = "no_match"
    PARTIAL = "partial"  # 部分条件满足


@dataclass
class ConditionResult:
    """单个条件的匹配结果。"""
    condition: Condition
    status: MatchStatus
    message: str | None = None


@dataclass
class PatternMatch:
    """一个模式的匹配结果。"""
    pattern: BasePattern
    symbol: str
    match_date: str  # 匹配发生的日期（入场信号日）
    match_index: int  # 在 bars 列表中的索引

    # 逐条件结果
    condition_results: list[ConditionResult] = field(default_factory=list)

    # 汇总
    matched_conditions: int = 0
    total_conditions: int = 0
    confidence: float | None = None  # matched_conditions / total_conditions

    # 元数据
    pattern_type: PatternType = PatternType.UNKNOWN
    timeframe: Timeframe = Timeframe.DAILY

    @property
    def status(self) -> MatchStatus:
        if self.matched_conditions == self.total_conditions:
            return MatchStatus.MATCHED
        elif self.matched_conditions > 0:
            return MatchStatus.PARTIAL
        return MatchStatus.NO_MATCH


# ---------------------------------------------------------------------------
# Condition Evaluator
# ---------------------------------------------------------------------------


def _safe_float(val: Any) -> float | None:
    try:
        return float(val)
    except Exception:
        return None


class ConditionEvaluator:
    """根据 OHLCV 数据评估单个 Condition。"""

    def __init__(self, bars: list[OHLCV]):
        self.bars = bars

    def evaluate(self, cond: Condition, at_index: int) -> ConditionResult:
        """Evaluate a single condition at bar `at_index`.

        Returns ConditionResult with MATCHED or NO_MATCH status.
        """
        try:
            result = self._eval(cond, at_index)
        except Exception as e:
            return ConditionResult(
                condition=cond,
                status=MatchStatus.NO_MATCH,
                message=f"eval error: {e}",
            )
        return result

    def _eval(self, cond: Condition, idx: int) -> ConditionResult:
        op = cond.op
        bar = self.bars[idx]

        # ---- Price / Close based ----
        if op == "higher_high":
            if idx < 1:
                return no_match(cond, "insufficient history")
            prev_high = self.bars[idx - 1].high
            matched = bar.high > prev_high
            return ok(cond, matched, f"H={bar.high:.2f} > prev_H={prev_high:.2f}")

        if op == "lower_low":
            if idx < 1:
                return no_match(cond, "insufficient history")
            prev_low = self.bars[idx - 1].low
            matched = bar.low < prev_low
            return ok(cond, matched, f"L={bar.low:.2f} < prev_L={prev_low:.2f}")

        if op == "breakout_up":
            if idx < 1:
                return no_match(cond, "insufficient history")
            prev_close = self.bars[idx - 1].close
            matched = bar.close > prev_close
            return ok(cond, matched, f"C={bar.close:.2f} > prev_C={prev_close:.2f}")

        if op == "breakout_down":
            if idx < 1:
                return no_match(cond, "insufficient history")
            prev_close = self.bars[idx - 1].close
            matched = bar.close < prev_close
            return ok(cond, matched, f"C={bar.close:.2f} < prev_C={prev_close:.2f}")

        # ---- Cross operations ----
        if op == "cross_above":
            value = cond.value
            if idx < 1:
                return no_match(cond, "insufficient history")
            prev = self.bars[idx - 1]
            curr = bar
            if isinstance(value, (int, float)):
                matched = prev.close <= value < curr.close
            elif isinstance(value, str):
                # e.g. "ma20" cross above "ma50"
                ma_curr = self._ma(value, idx)
                ma_prev = self._ma(value, idx - 1) if idx > 0 else None
                if ma_curr is None or ma_prev is None:
                    return no_match(cond, f"MA {value} unavailable")
                matched = prev.close <= ma_prev < ma_curr
            else:
                return no_match(cond, f"invalid value type for cross_above")
            return ok(cond, matched, f"cross_above value={value}")

        if op == "cross_below":
            value = cond.value
            if idx < 1:
                return no_match(cond, "insufficient history")
            prev = self.bars[idx - 1]
            curr = bar
            if isinstance(value, (int, float)):
                matched = prev.close >= value > curr.close
            elif isinstance(value, str):
                ma_curr = self._ma(value, idx)
                ma_prev = self._ma(value, idx - 1) if idx > 0 else None
                if ma_curr is None or ma_prev is None:
                    return no_match(cond, f"MA {value} unavailable")
                matched = prev.close >= ma_prev > ma_curr
            else:
                return no_match(cond, f"invalid value type for cross_below")
            return ok(cond, matched, f"cross_below value={value}")

        # ---- Comparison ----
        if op in ("gt", "lt", "eq"):
            if not isinstance(cond.value, (int, float)):
                return no_match(cond, f"value for {op} must be numeric")
            curr_val = getattr(bar, "close", None) or cond.value
            if op == "gt":
                matched = curr_val > cond.value
            elif op == "lt":
                matched = curr_val < cond.value
            else:
                matched = abs(curr_val - cond.value) < 1e-9
            return ok(cond, matched, f"{op} {cond.value}")

        # ---- Volume ----
        if op == "confirm":
            # Generic confirm: require volume > 0 (always true for valid bars)
            matched = bar.volume > 0
            return ok(cond, matched, f"V={bar.volume:.0f}")

        if op == "increasing":
            if idx < 1:
                return no_match(cond, "insufficient history")
            matched = bar.volume > self.bars[idx - 1].volume
            return ok(cond, matched, f"V={bar.volume:.0f} > prev_V={self.bars[idx-1].volume:.0f}")

        if op == "decreasing":
            if idx < 1:
                return no_match(cond, "insufficient history")
            matched = bar.volume < self.bars[idx - 1].volume
            return ok(cond, matched, f"V={bar.volume:.0f} < prev_V={self.bars[idx-1].volume:.0f}")

        if op == "spike":
            # volume spike: > 3x 20-day average
            if idx < 20:
                return no_match(cond, "insufficient history for avg")
            avg_vol = sum(b.volume for b in self.bars[idx - 20 : idx]) / 20
            matched = bar.volume > avg_vol * 3
            return ok(cond, matched, f"V={bar.volume:.0f} > 3x_avg={avg_vol*3:.0f}")

        if op == "drying_up":
            if idx < 20:
                return no_match(cond, "insufficient history for avg")
            avg_vol = sum(b.volume for b in self.bars[idx - 20 : idx]) / 20
            matched = bar.volume < avg_vol * 0.3
            return ok(cond, matched, f"V={bar.volume:.0f} < 0.3x_avg={avg_vol*0.3:.0f}")

        # ---- Candlestick ----
        if op == "doji":
            body = abs(bar.close - bar.open)
            range_ = bar.high - bar.low
            matched = range_ > 0 and body / range_ < 0.1
            return ok(cond, matched, f"body/range={body/range_:.3f}")

        if op == "small":
            body = abs(bar.close - bar.open)
            range_ = bar.high - bar.low
            matched = range_ > 0 and body / range_ < 0.3
            return ok(cond, matched, f"body/range={body/range_:.3f}")

        if op == "bullish":
            matched = bar.close > bar.open
            return ok(cond, matched, f"C={bar.close:.2f} > O={bar.open:.2f}")

        if op == "bearish":
            matched = bar.close < bar.open
            return ok(cond, matched, f"C={bar.close:.2f} < O={bar.open:.2f}")

        if op == "bullish_long":
            body = bar.close - bar.open
            range_ = bar.high - bar.low
            matched = body > 0 and body / range_ > 0.7
            return ok(cond, matched, f"long bullish body {body/range_:.2f}")

        if op == "bearish_long":
            body = bar.open - bar.close
            range_ = bar.high - bar.low
            matched = body > 0 and body / range_ > 0.7
            return ok(cond, matched, f"long bearish body {body/range_:.2f}")

        if op == "engulf":
            # Simple engulf check: body larger than prev body
            if idx < 1:
                return no_match(cond, "no prev bar")
            prev = self.bars[idx - 1]
            curr_body = abs(bar.close - bar.open)
            prev_body = abs(prev.close - prev.open)
            matched = curr_body > prev_body
            return ok(cond, matched, f"curr_body={curr_body:.2f} > prev_body={prev_body:.2f}")

        if op == "higher_close":
            if idx < 2:
                return no_match(cond, "insufficient history")
            matched = (
                bar.close > self.bars[idx - 1].close and
                self.bars[idx - 1].close > self.bars[idx - 2].close
            )
            return ok(cond, matched, "three consecutive higher closes")

        if op == "lower_close":
            if idx < 2:
                return no_match(cond, "insufficient history")
            matched = (
                bar.close < self.bars[idx - 1].close and
                self.bars[idx - 1].close < self.bars[idx - 2].close
            )
            return ok(cond, matched, "three consecutive lower closes")

        # ---- Consolidations ----
        if op == "consolidation":
            if idx < 5:
                return no_match(cond, "insufficient history")
            recent = self.bars[idx - 5 : idx]
            highs = [b.high for b in recent]
            lows = [b.low for b in recent]
            range_pct = (max(highs) - min(lows)) / max(highs) * 100
            matched = range_pct < 5  # within 5% range
            return ok(cond, matched, f"5d range={range_pct:.2f}%")

        # ---- Bollinger ----
        if op == "narrow":
            if idx < 20:
                return no_match(cond, "insufficient history for BB")
            recent = self.bars[idx - 20 : idx]
            closes = [b.close for b in recent]
            import statistics
            mean = statistics.mean(closes)
            std = statistics.stdev(closes) if len(closes) > 1 else 0
            upper = mean + 2 * std
            lower = mean - 2 * std
            width = (upper - lower) / mean * 100
            matched = width < 5  # narrow BB
            return ok(cond, matched, f"BB_width={width:.2f}%")

        # ---- Unknown op ----
        return no_match(cond, f"unknown op: {op!r}")

    def _ma(self, key: str, idx: int) -> float | None:
        """Compute simple moving average at idx. key e.g. 'ma20', 'ma50'."""
        import statistics
        m = _ma_period(key)
        if m is None or idx < m - 1:
            return None
        closes = [b.close for b in self.bars[idx - m + 1 : idx + 1]]
        return statistics.mean(closes)


def _ma_period(key: str) -> int | None:
    """Extract period from MA key like 'ma20'."""
    if key.lower().startswith("ma"):
        try:
            return int(key[2:])
        except ValueError:
            pass
    return None


def ok(cond: Condition, matched: bool, msg: str) -> ConditionResult:
    return ConditionResult(
        condition=cond,
        status=MatchStatus.MATCHED if matched else MatchStatus.NO_MATCH,
        message=msg if matched else None,
    )


def no_match(cond: Condition, msg: str) -> ConditionResult:
    return ConditionResult(condition=cond, status=MatchStatus.NO_MATCH, message=msg)


# ---------------------------------------------------------------------------
# Pattern Matcher
# ---------------------------------------------------------------------------


@dataclass
class MatcherConfig:
    """匹配引擎配置。"""
    require_all_conditions: bool = True  # True = AND, False = OR
    min_confidence: float = 0.5  # 最低置信度阈值


class PatternMatcher:
    """模式匹配引擎。"""

    def __init__(
        self,
        library: PatternLibrary,
        config: MatcherConfig | None = None,
    ) -> None:
        self.library = library
        self.config = config or MatcherConfig()

    def match_pattern(
        self,
        pattern: BasePattern,
        bars: list[OHLCV],
        at_index: int,
        symbol: str,
    ) -> PatternMatch:
        """Try to match a single pattern at bar `at_index`."""
        evaluator = ConditionEvaluator(bars)
        results = []
        matched = 0

        for cond in pattern.conditions:
            res = evaluator.evaluate(cond, at_index)
            results.append(res)
            if res.status == MatchStatus.MATCHED:
                matched += 1

        total = len(pattern.conditions)
        if total == 0:
            conf = None
        elif self.config.require_all_conditions:
            conf = matched / total
        else:
            conf = matched / total if matched > 0 else 0.0

        if conf is not None and conf < self.config.min_confidence:
            conf = None

        return PatternMatch(
            pattern=pattern,
            symbol=symbol,
            match_date=bars[at_index].date,
            match_index=at_index,
            condition_results=results,
            matched_conditions=matched,
            total_conditions=total,
            confidence=conf,
            pattern_type=pattern.pattern_type,
            timeframe=pattern.timeframe,
        )

    def scan(
        self,
        bars: list[OHLCV],
        symbol: str,
        pattern_types: list[PatternType] | None = None,
    ) -> list[PatternMatch]:
        """Scan all bars for all patterns.

        Returns list of PatternMatch (only fully matched unless config.requires_all_conditions=False).
        """
        results: list[PatternMatch] = []
        all_patterns: list[BasePattern] = []

        # Collect patterns to scan
        if not pattern_types:
            all_patterns = (
                self.library.canonical_patterns
                + self.library.article_patterns
                + self.library.validated_patterns
            )
        else:
            pt_set = set(pattern_types)
            for p in self.library.canonical_patterns:
                if p.pattern_type in pt_set:
                    all_patterns.append(p)
            for p in self.library.article_patterns:
                if p.pattern_type in pt_set:
                    all_patterns.append(p)
            for p in self.library.validated_patterns:
                if p.pattern_type in pt_set:
                    all_patterns.append(p)

        if not all_patterns:
            return []

        for idx in range(len(bars)):
            for pattern in all_patterns:
                match = self.match_pattern(pattern, bars, idx, symbol)
                if match.status == MatchStatus.MATCHED:
                    results.append(match)

        return results

    def scan_latest(
        self,
        bars: list[OHLCV],
        symbol: str,
        pattern_types: list[PatternType] | None = None,
    ) -> list[PatternMatch]:
        """Scan only the latest bar (for real-time scanning)."""
        if not bars:
            return []
        return self.scan(bars[-1:], symbol, pattern_types)
