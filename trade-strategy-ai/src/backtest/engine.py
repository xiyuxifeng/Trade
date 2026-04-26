"""NTL-S6-004: 回测引擎

职责：
- 编排 loader / replayer / executor / scoring
- 按 trader / 日期区间执行完整回测
- 聚合为 BacktestResult
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from src.backtest.execution import classify_rules_snapshot_gap, replay_candidates
from src.backtest.rule_registry import RuleMeta
from src.backtest.schemas import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    BacktestTradeRecord,
    RuleValidationResult,
)

if TYPE_CHECKING:
    from src.backtest.snapshot_loader import SnapshotLoader
    from src.backtest.scoring import score_backtest_trade


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

    trade_dates = iter_trade_dates(date_from, date_to)
    all_contexts: list[dict] = []
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
        for rule_dict in version.rules_snapshot:
            rule_id = str(rule_dict.get("rule_id", ""))
            if rule_id and rule_id not in rule_map:
                rule_map[rule_id] = (rule_dict, version.version_id)

    # 对每条规则分类并验真
    results: list[RuleValidationResult] = []
    for rule_id, (rule_dict, version_id) in rule_map.items():
        rule_meta = classify_rule(rule_dict)
        validation_result = validate_rule_hits(rule_meta, all_contexts)
        validation_result.trader_id = trader_id
        validation_result.strategy_version_id = version_id
        results.append(validation_result)

    return results


# A股交易日：跳过周六(5)和周日(6)
def is_trade_date(d: date) -> bool:
    """判断是否为 A 股交易日（跳过周末）"""
    return d.weekday() < 5


def iter_trade_dates(date_from: date, date_to: date) -> list[date]:
    """按日期迭代器，跳过周末，返回所有交易日。

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
        trade_dates = iter_trade_dates(request.date_from, request.date_to)
        records: list[BacktestTradeRecord] = []

        for trade_date in trade_dates:
            record = await self._process_single_day(trade_date, request)
            records.append(record)

        summary = self._build_summary(records, len(trade_dates))

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
        return asyncio.run(self.run(request))

    async def _process_single_day(
        self, trade_date: date, request: BacktestRequest
    ) -> BacktestTradeRecord:
        """处理单日回测。

        编排：SnapshotLoader → StrategyReplayer → Scoring → BacktestTradeRecord
        """
        # 如果没有 loader，返回 skipped 记录
        if self.loader is None:
            return BacktestTradeRecord(
                trade_date=trade_date,
                trader_id=request.trader_id,
                strategy_version_id=request.strategy_version_id or "",
                symbol="",
                status="skipped",
                skip_reason="no_loader_configured",
            )

        # 加载市场上下文
        market_context = await self.loader.load_market_context(
            trade_date=trade_date,
            symbols=request.symbols,
        )

        # 规则验真模式：暂不处理交易评分
        if request.mode == "rule_validation":
            return BacktestTradeRecord(
                trade_date=trade_date,
                trader_id=request.trader_id,
                strategy_version_id=request.strategy_version_id or "",
                symbol="",
                status="skipped",
                skip_reason="rule_validation_mode",
            )

        # 如果没有 strategy_loader，返回 skipped
        if self.strategy_loader is None:
            return BacktestTradeRecord(
                trade_date=trade_date,
                trader_id=request.trader_id,
                strategy_version_id=request.strategy_version_id or "",
                symbol="",
                status="skipped",
                skip_reason="no_strategy_loader",
            )

        # 加载策略版本
        strategy_version = await self.strategy_loader.load_version_for_date(
            trader_id=request.trader_id,
            trade_date=trade_date,
        )

        if strategy_version is None:
            return BacktestTradeRecord(
                trade_date=trade_date,
                trader_id=request.trader_id,
                strategy_version_id=request.strategy_version_id or "",
                symbol="",
                status="skipped",
                skip_reason="no_strategy_version",
            )

        # 获取 replay candidates
        candidates = replay_candidates(strategy_version, market_context)

        if not candidates:
            return BacktestTradeRecord(
                trade_date=trade_date,
                trader_id=request.trader_id,
                strategy_version_id=strategy_version.version_id,
                symbol="",
                status="skipped",
                skip_reason="no_candidates",
            )

        # 取第一个 candidate 进行评分（单日单标的模式）
        candidate = candidates[0]
        bars = market_context.get("bars_by_symbol", {}).get(candidate["symbol"], [])

        if not bars:
            return BacktestTradeRecord(
                trade_date=trade_date,
                trader_id=request.trader_id,
                strategy_version_id=strategy_version.version_id,
                symbol=candidate["symbol"],
                status="skipped",
                skip_reason="no_bars",
            )

        # 评分
        scoring_func = self.scoring_func
        if scoring_func is None:
            from src.backtest.scoring import score_backtest_trade
            scoring_func = score_backtest_trade

        score_result = scoring_func(
            bars=bars,
            entry_price=candidate["entry_price"] or 0.0,
            entry_date=trade_date.isoformat(),
            target_price=candidate.get("target_price"),
            stop_loss_price=candidate.get("stop_loss_price"),
            symbol=candidate["symbol"],
        )

        # 从 bars 中查找 exit_date 对应的收盘价作为 exit_price
        exit_price = None
        exit_date_str = score_result.get("exit_date")
        if exit_date_str and bars:
            for bar in bars:
                if str(bar.get("date")) == exit_date_str:
                    exit_price = bar.get("close")
                    break

        return BacktestTradeRecord(
            trade_date=trade_date,
            trader_id=request.trader_id,
            strategy_version_id=strategy_version.version_id,
            symbol=candidate["symbol"],
            status="closed",
            entry_price=candidate["entry_price"],
            exit_price=exit_price,
            entry_date=trade_date.isoformat(),
            exit_date=exit_date_str,
            return_pct=score_result.get("return_pct"),
            mfe=score_result.get("mfe"),
            mae=score_result.get("mae"),
        )

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


def validate_rule_hits(rule_meta: RuleMeta, contexts: list[dict]) -> RuleValidationResult:
    """对单条规则在多个市场快照上做命中验证。

    Args:
        rule_meta: 规则元数据（含 required_fields 和 programmatic_level）
        contexts: 市场上下文快照列表（load_market_context 的返回值列表）

    Returns:
        RuleValidationResult
    """
    # 非完全可程序化规则：直接标记 unsupported
    if rule_meta.programmatic_level != "fully_programmable":
        return RuleValidationResult(
            trader_id="",
            strategy_version_id="",
            rule_id=rule_meta.rule_id,
            rule_text=rule_meta.rule_text,
            programmable=False,
            validation_status="unsupported_rule",
            hit_count=0,
            sample_count=len(contexts),
            hit_rate=None,
        )

    # 完全可程序化规则：逐快照检查 required_fields 是否存在
    hit_count = 0
    for ctx in contexts:
        indicators = ctx.get("indicators_by_symbol") or {}
        # 至少有一个 required_field 在 indicators 中出现
        found = False
        for symbol_indicators in indicators.values():
            if isinstance(symbol_indicators, dict):
                for field in rule_meta.required_fields:
                    if field in symbol_indicators:
                        found = True
                        break
            if found:
                break
        if found:
            hit_count += 1

    sample_count = len(contexts)
    hit_rate = hit_count / sample_count if sample_count > 0 else None

    return RuleValidationResult(
        trader_id="",
        strategy_version_id="",
        rule_id=rule_meta.rule_id,
        rule_text=rule_meta.rule_text,
        programmable=True,
        validation_status="validated",
        hit_count=hit_count,
        sample_count=sample_count,
        hit_rate=hit_rate,
    )
