"""NTL-S6-004: 回测引擎

职责：
- 编排 loader / replayer / executor / scoring
- 按 trader / 日期区间执行完整回测
- 聚合为 BacktestResult
"""

from __future__ import annotations

import asyncio
import operator
import re
import statistics
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Callable

from src.backtest.execution import classify_rules_snapshot_gap, replay_candidates
from src.backtest.rule_registry import RuleMeta
from src.backtest.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    BacktestTradeRecord,
    MarketContextSnapshot,
    RuleValidationResult,
)
from src.common.logger import get_logger

if TYPE_CHECKING:
    from src.backtest.snapshot_loader import SnapshotLoader
    from src.backtest.scoring import score_backtest_trade

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 简单数值条件解析（如 "rsi < 30"）
# ---------------------------------------------------------------------------
_CONDITION_PATTERN = re.compile(
    r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([<>!=]+)\s*([+-]?\d+(?:\.\d+)?)\s*$"
)

_COMPARISON_OPS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


def _evaluate_simple_condition(condition_text: str, indicators: dict[str, Any]) -> bool | None:
    """评估简单数值条件，如 'rsi < 30'。

    Returns:
        True: 条件满足
        False: 条件不满足或字段不存在
        None: 无法解析该条件文本（非简单数值比较）
    """
    match = _CONDITION_PATTERN.match(condition_text.strip())
    if not match:
        return None

    field_name, op_str, value_str = match.groups()
    if field_name not in indicators:
        return False

    op_func = _COMPARISON_OPS.get(op_str)
    if op_func is None:
        return None

    try:
        indicator_value = float(indicators[field_name])
        threshold = float(value_str)
        return op_func(indicator_value, threshold)
    except (ValueError, TypeError):
        return False


def _calc_t1_return(context: MarketContextSnapshot, symbol: str) -> float | None:
    """计算某标的在 context 交易日的次日收益率（后验收益）"""
    bars = context.get("bars_by_symbol", {}).get(symbol, [])
    if len(bars) < 2:
        return None

    trade_date = context.get("trade_date", "")
    for i, bar in enumerate(bars):
        if str(bar.get("date")) == trade_date:
            if i + 1 < len(bars):
                curr_close = bar.get("close")
                next_close = bars[i + 1].get("close")
                if curr_close and next_close and curr_close != 0:
                    return (next_close - curr_close) / curr_close
            break
    return None


# ---------------------------------------------------------------------------
# A股交易日历（支持 akshare 加载或外部注入节假日）
# ---------------------------------------------------------------------------
class TradeCalendar:
    """A股交易日历（支持外部注入节假日或从 akshare 加载）"""

    _holidays: set[str] = set()
    _trade_dates: set[str] | None = None
    _loaded: bool = False

    @classmethod
    def set_holidays(cls, holidays: set[str]) -> None:
        """手动设置节假日（用于测试或外部日历源）"""
        cls._holidays = holidays

    @classmethod
    def load_from_akshare(cls) -> None:
        """从 akshare 加载交易日历"""
        if cls._loaded:
            return
        try:
            import akshare as ak

            df = ak.tool_trade_date_hist_sina()
            cls._trade_dates = set(df["trade_date"].astype(str))
        except Exception:
            # 失败时回退为 None，继续使用手动 holidays 逻辑
            cls._trade_dates = None
        cls._loaded = True

    @classmethod
    def is_trade_date(cls, d: date) -> bool:
        """判断是否为交易日（跳过周末和法定节假日）"""
        if cls._trade_dates is None and not cls._loaded:
            cls.load_from_akshare()
        if d.weekday() >= 5:
            return False
        if cls._trade_dates is not None:
            return d.strftime("%Y-%m-%d") in cls._trade_dates
        return d.isoformat() not in cls._holidays


def is_trade_date(d: date) -> bool:
    """判断是否为 A 股交易日（跳过周末和法定节假日）"""
    return TradeCalendar.is_trade_date(d)


def iter_trade_dates(date_from: date, date_to: date) -> list[date]:
    """按日期迭代器，跳过非交易日，返回所有交易日。

    Args:
        date_from: 开始日期（包含）
        date_to: 结束日期（包含）

    Returns:
        交易日列表
    """
    result = []
    current = date_from
    while current <= date_to:
        if is_trade_date(current):
            result.append(current)
        current += timedelta(days=1)
    return result


async def validate_rules_for_trader(
    trader_id: str,
    date_from: date,
    date_to: date,
    loader: SnapshotLoader,
) -> list[RuleValidationResult]:
    """对某交易员在日期区间内做规则验真。

    流程：
    1. 遍历日期区间内每个交易日
    2. 加载策略版本，提取 rules_snapshot
    3. 加载市场上下文（indicators）
    4. 对每条规则用 classify_rule 分类
    5. 对 fully_programmable 规则调用 validate_rule_hits

    Args:
        trader_id: 交易员 ID
        date_from: 开始日期
        date_to: 结束日期
        loader: SnapshotLoader 实例（需配置 strategy_repo）

    Returns:
        RuleValidationResult 列表
    """
    from src.backtest.rule_registry import classify_rule

    logger.info(
        "规则验真开始: trader=%s, date_from=%s, date_to=%s",
        trader_id,
        date_from,
        date_to,
    )
    trade_dates = iter_trade_dates(date_from, date_to)
    all_contexts: list[MarketContextSnapshot] = []
    # rule_map: rule_id -> (rule_dict, strategy_version_id)
    rule_map: dict[str, tuple[dict, str]] = {}

    for trade_date in trade_dates:
        # 加载市场上下文（收集 indicators）
        ctx = await loader.load_market_context(trade_date=trade_date, symbols=[])
        if ctx:
            all_contexts.append(ctx)

        # 加载策略版本
        version = await loader.load_version_for_date(trader_id=trader_id, trade_date=trade_date)
        if version is None:
            continue

        # 提取规则（同时记录版本 ID）
        for rule_dict in (version.rules_snapshot or []):
            rule_id = str(rule_dict.get("rule_id", ""))
            if rule_id and rule_id not in rule_map:
                rule_map[rule_id] = (rule_dict, version.version_id)

    # 对每条规则分类并验真
    results: list[RuleValidationResult] = []
    for rule_id, (rule_dict, version_id) in rule_map.items():
        rule_meta = classify_rule(rule_dict)
        validation_result = validate_rule_hits(
            rule_meta, all_contexts, trader_id=trader_id, strategy_version_id=version_id
        )
        results.append(validation_result)

    logger.info(
        "规则验真结束: trader=%s, total_rules=%d, supported=%d, unsupported=%d",
        trader_id,
        len(results),
        sum(1 for r in results if r.programmatic_level == "fully_programmable"),
        sum(1 for r in results if r.programmatic_level == "unsupported"),
    )
    return results


def validate_rule_hits(
    rule_meta: RuleMeta,
    contexts: list[MarketContextSnapshot],
    trader_id: str = "",
    strategy_version_id: str = "",
) -> RuleValidationResult:
    """对单条规则在多个市场快照上做命中验证。

    Args:
        rule_meta: 规则元数据（含 required_fields 和 programmatic_level）
        contexts: 市场上下文快照列表（load_market_context 的返回值列表）
        trader_id: 交易员 ID（直接传入，避免后续修改 frozen 实例）
        strategy_version_id: 策略版本 ID（直接传入）

    Returns:
        RuleValidationResult
    """
    # 规则文本为空：直接标记 invalid
    if not rule_meta.rule_text.strip():
        return RuleValidationResult(
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            rule_id=rule_meta.rule_id,
            rule_text=rule_meta.rule_text,
            programmable=False,
            validation_status="invalid_rule",
            hit_count=0,
            sample_count=len(contexts),
            hit_rate=None,
        )

    # 非完全可程序化规则：直接标记 unsupported
    if rule_meta.programmatic_level != "fully_programmable":
        return RuleValidationResult(
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            rule_id=rule_meta.rule_id,
            rule_text=rule_meta.rule_text,
            programmable=False,
            validation_status="unsupported_rule",
            hit_count=0,
            sample_count=len(contexts),
            hit_rate=None,
        )

    # 快照缺失：无法验真
    if not contexts:
        return RuleValidationResult(
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            rule_id=rule_meta.rule_id,
            rule_text=rule_meta.rule_text,
            programmable=True,
            validation_status="missing_snapshot",
            hit_count=0,
            sample_count=0,
            hit_rate=None,
        )

    # 缺少指标字段：无法验真
    indicators_present = False
    required_field_present = False
    for ctx in contexts:
        indicators = ctx.get("indicators_by_symbol") or {}
        if indicators:
            indicators_present = True
        for symbol_indicators in indicators.values():
            if isinstance(symbol_indicators, dict):
                if any(field in symbol_indicators for field in rule_meta.required_fields):
                    required_field_present = True
                    break
        if required_field_present:
            break

    if not indicators_present:
        return RuleValidationResult(
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            rule_id=rule_meta.rule_id,
            rule_text=rule_meta.rule_text,
            programmable=True,
            validation_status="missing_snapshot",
            hit_count=0,
            sample_count=len(contexts),
            hit_rate=None,
        )

    if rule_meta.required_fields and not required_field_present:
        return RuleValidationResult(
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            rule_id=rule_meta.rule_id,
            rule_text=rule_meta.rule_text,
            programmable=True,
            validation_status="missing_field",
            hit_count=0,
            sample_count=len(contexts),
            hit_rate=None,
        )

    # 完全可程序化规则：逐快照检查
    hit_count = 0
    hit_returns: list[float] = []
    notes: list[str] = []
    hit_symbols_per_day: list[str] = []  # 每次命中的 {trade_date}:{symbol} 标识
    for ctx in contexts:
        indicators = ctx.get("indicators_by_symbol") or {}
        trade_date = ctx.get("trade_date", "?")
        found = False
        hit_symbol = None
        for symbol, symbol_indicators in indicators.items():
            if isinstance(symbol_indicators, dict):
                # 先尝试真正的数值条件判断
                eval_result = _evaluate_simple_condition(rule_meta.rule_text, symbol_indicators)
                if eval_result is True:
                    found = True
                    hit_symbol = symbol
                    break
                if eval_result is None:
                    # 无法解析时回退到字段存在性检查
                    for field in rule_meta.required_fields:
                        if field in symbol_indicators:
                            found = True
                            hit_symbol = symbol
                            break
            if found:
                break
        if found:
            hit_count += 1
            hit_symbols_per_day.append(f"{trade_date}:{hit_symbol}")
            if hit_symbol:
                t1_ret = _calc_t1_return(ctx, hit_symbol)
                if t1_ret is not None:
                    hit_returns.append(t1_ret)
                else:
                    notes.append(f"t1_return_incomplete: {trade_date} {hit_symbol}")
        else:
            hit_symbols_per_day.append(f"{trade_date}:-")

    sample_count = len(contexts)
    hit_rate = hit_count / sample_count if sample_count > 0 else None

    posterior_mean = statistics.mean(hit_returns) if hit_returns else None
    posterior_median = statistics.median(hit_returns) if hit_returns else None

    return RuleValidationResult(
        trader_id=trader_id,
        strategy_version_id=strategy_version_id,
        rule_id=rule_meta.rule_id,
        rule_text=rule_meta.rule_text,
        programmable=True,
        validation_status="validated",
        hit_count=hit_count,
        sample_count=sample_count,
        hit_rate=hit_rate,
        posterior_return_mean=posterior_mean,
        posterior_return_median=posterior_median,
        notes=notes + ([f"hit_symbols: {','.join(hit_symbols_per_day)}"] if hit_symbols_per_day else []),
    )


class BacktestEngine:
    """回测引擎。

    编排：SnapshotLoader → StrategyReplayer → Executor → Scoring → BacktestResult

    Attributes:
        loader: 快照加载器（必须实现 load_market_context 方法）
        strategy_loader: 策略版本加载器（必须实现 load_version_for_date 方法）
        scoring_func: 评分函数（默认使用 score_backtest_trade）
    """

    def __init__(
        self,
        loader: SnapshotLoader | None = None,
        strategy_loader: Any = None,
        scoring_func: Any = None,
    ) -> None:
        self.loader = loader
        self.strategy_loader = strategy_loader
        self.scoring_func = scoring_func

    async def run(self, request: BacktestRequest) -> BacktestResult:
        """异步运行回测。

        Args:
            request: BacktestRequest

        Returns:
            BacktestResult
        """
        logger.info(
            "回测开始: trader=%s, date_from=%s, date_to=%s, mode=%s",
            request.trader_id,
            request.date_from,
            request.date_to,
            request.mode,
        )
        trade_dates = iter_trade_dates(request.date_from, request.date_to)
        records: list[BacktestTradeRecord] = []

        for trade_date in trade_dates:
            day_records = await self._process_single_day(trade_date, request)
            records.extend(day_records)

        summary = self._build_summary(records, len(trade_dates))
        logger.info(
            "回测结束: trader=%s, date_from=%s, date_to=%s, total_records=%d, skipped=%d, traded=%d",
            request.trader_id,
            request.date_from,
            request.date_to,
            len(records),
            sum(1 for r in records if r.status == "skipped"),
            sum(1 for r in records if r.status == "traded"),
        )

        return BacktestResult(
            request_trader_id=request.trader_id,
            request_date_from=request.date_from,
            request_date_to=request.date_to,
            records=records,
            summary=summary,
        )

    def run_sync(self, request: BacktestRequest) -> BacktestResult:
        """同步运行回测（内部调用 async run）。

        Args:
            request: BacktestRequest

        Returns:
            BacktestResult
        """
        try:
            return asyncio.run(self.run(request))
        except RuntimeError:
            # 已有 event loop（如 Jupyter / pytest-asyncio）时使用现有 loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.run(request))

    async def _process_single_day(
        self, trade_date: date, request: BacktestRequest
    ) -> list[BacktestTradeRecord]:
        """处理单日回测，返回该日所有 candidate 的交易记录。

        编排：SnapshotLoader → StrategyReplayer → Scoring → BacktestTradeRecord
        """
        # 如果没有 loader，返回 skipped 记录
        if self.loader is None:
            logger.debug(
                "跳过交易日期 %s: loader 未配置 (no_loader_configured)",
                trade_date,
            )
            return [
                BacktestTradeRecord(
                    trade_date=trade_date,
                    trader_id=request.trader_id,
                    strategy_version_id=request.strategy_version_id or "",
                    symbol="",
                    status="skipped",
                    skip_reason="no_loader_configured",
                )
            ]

        # 加载市场上下文
        market_context = await self.loader.load_market_context(
            trade_date=trade_date,
            symbols=request.symbols,
        )

        # 规则验真模式：暂不处理交易评分
        if request.mode == "rule_validation":
            logger.debug("跳过交易日期 %s: 规则验真模式", trade_date)
            return [
                BacktestTradeRecord(
                    trade_date=trade_date,
                    trader_id=request.trader_id,
                    strategy_version_id=request.strategy_version_id or "",
                    symbol="",
                    status="skipped",
                    skip_reason="rule_validation_mode",
                )
            ]

        # 如果没有 strategy_loader，返回 skipped
        if self.strategy_loader is None:
            logger.debug(
                "跳过交易日期 %s: strategy_loader 未配置 (no_strategy_loader)",
                trade_date,
            )
            return [
                BacktestTradeRecord(
                    trade_date=trade_date,
                    trader_id=request.trader_id,
                    strategy_version_id=request.strategy_version_id or "",
                    symbol="",
                    status="skipped",
                    skip_reason="no_strategy_loader",
                )
            ]

        # 加载策略版本
        strategy_version = await self.strategy_loader.load_version_for_date(
            trader_id=request.trader_id,
            trade_date=trade_date,
        )

        if strategy_version is None:
            logger.debug(
                "跳过交易日期 %s: 找不到策略版本 (no_strategy_version)",
                trade_date,
            )
            return [
                BacktestTradeRecord(
                    trade_date=trade_date,
                    trader_id=request.trader_id,
                    strategy_version_id=request.strategy_version_id or "",
                    symbol="",
                    status="skipped",
                    skip_reason="no_strategy_version",
                )
            ]

        # 获取 replay candidates
        candidates = replay_candidates(strategy_version, market_context)

        if not candidates:
            logger.debug(
                "跳过交易日期 %s: 无候选交易 (no_candidates)",
                trade_date,
            )
            return [
                BacktestTradeRecord(
                    trade_date=trade_date,
                    trader_id=request.trader_id,
                    strategy_version_id=strategy_version.version_id,
                    symbol="",
                    status="skipped",
                    skip_reason="no_candidates",
                )
            ]

        # 遍历所有 candidates，为每个生成交易记录
        records: list[BacktestTradeRecord] = []
        for candidate in candidates:
            symbol = candidate["symbol"]
            bars = market_context.get("bars_by_symbol", {}).get(symbol, [])

            if not bars:
                logger.debug(
                    "跳过标的 %s (%s): 缺少 bar 数据 (no_bars)",
                    symbol,
                    trade_date,
                )
                records.append(
                    BacktestTradeRecord(
                        trade_date=trade_date,
                        trader_id=request.trader_id,
                        strategy_version_id=strategy_version.version_id,
                        symbol=symbol,
                        status="skipped",
                        skip_reason="no_bars",
                    )
                )
                continue

            # A股最小交易单位校验：买入必须是 100 股整数倍
            volume: int | None = candidate.get("volume")
            is_valid_lot_size: bool | None = None
            if volume is not None and candidate.get("decision") == "buy":
                is_valid_lot_size = volume % 100 == 0

            entry_price = candidate.get("entry_price")
            if entry_price is None or entry_price <= 0:
                records.append(
                    BacktestTradeRecord(
                        trade_date=trade_date,
                        trader_id=request.trader_id,
                        strategy_version_id=strategy_version.version_id,
                        symbol=symbol,
                        status="invalid",
                        entry_price=entry_price,
                        volume=volume,
                        is_valid_lot_size=is_valid_lot_size,
                        skip_reason="missing_entry_price",
                    )
                )
                continue

            # 新股判断：从 market_context 获取上市日期
            listing_dates = market_context.get("listing_dates") or {}
            listing_date_str = listing_dates.get(symbol)
            listing_date = date.fromisoformat(listing_date_str) if listing_date_str else None

            # 构建交易约束（含新股规则）
            from src.evaluation.metrics_calculator import TradeConstraint

            constraint = TradeConstraint(
                trade_date=trade_date,
                listing_date=listing_date,
            )

            # 评分
            scoring_func = self.scoring_func
            if scoring_func is None:
                from src.backtest.scoring import score_backtest_trade
                scoring_func = score_backtest_trade

            score_result = scoring_func(
                bars=bars,
                entry_price=entry_price,
                entry_date=trade_date.isoformat(),
                target_price=candidate.get("target_price"),
                stop_loss_price=candidate.get("stop_loss_price"),
                symbol=symbol,
                constraint=constraint,
            )

            # 从 bars 中查找 exit_date 对应的收盘价作为 exit_price
            exit_price = None
            exit_date_str = score_result.get("exit_date")
            if exit_date_str and bars:
                for bar in bars:
                    if str(bar.get("date")) == exit_date_str:
                        exit_price = bar.get("close")
                        break

            records.append(
                BacktestTradeRecord(
                    trade_date=trade_date,
                    trader_id=request.trader_id,
                    strategy_version_id=strategy_version.version_id,
                    symbol=symbol,
                    status="closed",
                    entry_price=entry_price,
                    exit_price=exit_price,
                    entry_date=trade_date.isoformat(),
                    exit_date=exit_date_str,
                    return_pct=score_result.get("return_pct"),
                    mfe=score_result.get("mfe"),
                    mae=score_result.get("mae"),
                    volume=volume,
                    is_valid_lot_size=is_valid_lot_size,
                )
            )

        return records

    def _build_summary(
        self, records: list[BacktestTradeRecord], total_days: int
    ) -> BacktestSummary:
        """从 records 聚合 summary"""
        total_trades = len(records)
        valid_trades = sum(
            1 for r in records if r.status in ("open", "closed")
        )
        skipped_trades = sum(1 for r in records if r.status == "skipped")

        closed_records = [r for r in records if r.status == "closed" and r.return_pct is not None]
        win_count = sum(1 for r in closed_records if r.return_pct and r.return_pct > 0)
        win_rate = win_count / len(closed_records) if closed_records else None
        avg_return = (
            sum(r.return_pct for r in closed_records if r.return_pct) / len(closed_records)
            if closed_records else None
        )

        return BacktestSummary(
            total_days=total_days,
            total_trades=total_trades,
            valid_trades=valid_trades,
            skipped_trades=skipped_trades,
            win_rate=win_rate,
            avg_return_pct=avg_return,
        )
