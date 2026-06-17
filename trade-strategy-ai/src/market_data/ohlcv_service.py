# src/market_data/ohlcv_service.py
"""OHLCV 数据服务 - 抓取并存储日线行情数据"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any, Callable
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.indicator import Indicator
from src.models.ohlcv_bar import OHLCVBar
from src.models.stock_info import StockInfo
from src.common.logger import get_logger

logger = get_logger(__name__)
SHANGHAI = ZoneInfo("Asia/Shanghai")
SUPPORTED_ADJUSTMENT_POLICIES = {"unadjusted", "forward_adjusted", "backward_adjusted"}


@dataclass(frozen=True)
class _UpsertOutcome:
    count: int
    earliest_changed_trade_date: date | None
    latest_changed_trade_date: date | None


class OHLCVService:
    """ohlcv 数据服务。

    职责：
    - 从 AkShare 批量抓取日线数据
    - 存储到数据库（upsert 模式）
    - 提供按日期/标的查询接口
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        min_request_interval_seconds: float = 1.0,
        max_retries: int = 2,
        retry_backoff_seconds: list[float] | None = None,
        fallback_enabled: bool = True,
    ) -> None:
        self._factory = session_factory
        # 限速参数，传递给 AkshareProvider
        self._min_request_interval_seconds = min_request_interval_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds or [1.0, 3.0]
        # fallback 开关：东方财富失败后是否尝试新浪源
        self._fallback_enabled = fallback_enabled

    async def crawl_bars(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
        market_kind_by_symbol: dict[str, str] | None = None,
        adjustment_policy_by_symbol: dict[str, str] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        runtime_state: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """抓取并存储 ohlcv 数据。

        Args:
            symbols: 标的代码列表（支持股票/指数）
            start_date: 起始日期
            end_date: 结束日期
            market_kind_by_symbol: 可选的标的类型映射，用于避免按 symbol 重新推断

        Returns:
            dict[symbol, count] 抓取成功的记录数
        """
        from src.providers.akshare_provider import AkshareProvider

        provider = AkshareProvider(
            min_request_interval_seconds=self._min_request_interval_seconds,
            max_retries=self._max_retries,
            retry_backoff_seconds=self._retry_backoff_seconds,
            fallback_enabled=self._fallback_enabled,
        )
        runtime_state_payload = runtime_state if isinstance(runtime_state, dict) else {}
        checkpoint = runtime_state_payload.get("checkpoint") if isinstance(runtime_state_payload.get("checkpoint"), dict) else {}
        start_index = int(checkpoint.get("symbol_index") or 0)
        results: dict[str, int] = dict(checkpoint.get("results") or {})
        kind_map = market_kind_by_symbol or {}
        adjustment_map = adjustment_policy_by_symbol or {}
        total = len(symbols)

        for index, symbol in enumerate(symbols, start=1):
            if index <= start_index:
                continue
            try:
                market_kind = kind_map.get(symbol)
                if not market_kind:
                    market_kind = await self._resolve_market_kind(symbol)
                adjustment_policy = adjustment_map.get(symbol) or "unadjusted"
                self._validate_adjustment_policy(adjustment_policy)
                df = provider.fetch_ohlcv_1d(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    market_kind=market_kind,
                )
                outcome = await self._upsert_bars(
                    symbol,
                    df,
                    market_kind=market_kind,
                    adjustment_policy=adjustment_policy,
                )
                count = outcome.count
                if outcome.earliest_changed_trade_date is not None:
                    await self._invalidate_indicators(
                        symbol=symbol,
                        start_date=outcome.earliest_changed_trade_date,
                    )
                results[symbol] = count
                logger.info(f"抓取成功: {symbol}, {count} 条记录")
            except Exception as e:
                logger.exception(
                    "ohlcv 抓取失败: symbol=%s, start=%s, end=%s, market_kind=%s, error=%s",
                    symbol,
                    start_date,
                    end_date,
                    kind_map.get(symbol) or "auto",
                    e,
                )
                if isinstance(e, ValueError):
                    raise
                results[symbol] = 0
            if progress_callback is not None:
                runtime_state_update = {
                    "schema_version": 1,
                    "checkpoint": {
                        "symbol_index": index,
                        "results": results,
                    },
                }
                progress_callback(
                    {
                        "job_type": "ohlcv-crawl",
                        "stage": "crawl",
                        "current": index,
                        "total": total,
                        "percent": round((index / total) * 100, 2) if total else 0.0,
                        "remaining": max(total - index, 0),
                        "current_step": f"crawl:{symbol}",
                        "current_fetcher": symbol,
                        "current_trade_date": start_date.isoformat() if start_date else None,
                        "status": "success" if results.get(symbol, 0) > 0 else "partial",
                        "error": None if results.get(symbol, 0) > 0 else f"failed to crawl {symbol}",
                        "runtime_state": runtime_state_update,
                    }
                )

        return results

    async def _resolve_market_kind(self, symbol: str) -> str:
        """根据 stock_info 表推断标的类型，未命中时回退到股票。"""
        async with self._factory() as session:
            stmt = select(StockInfo.security_type).where(StockInfo.symbol == symbol).limit(1)
            security_type = await session.scalar(stmt)
        if security_type == "index":
            return "index"
        if security_type == "etf":
            return "etf"
        return "stock"

    def _validate_adjustment_policy(self, value: str) -> None:
        if value not in SUPPORTED_ADJUSTMENT_POLICIES:
            raise ValueError(f"unknown adjustment policy: {value}")

    def _infer_exchange(self, symbol: str) -> str:
        if "." in symbol:
            return symbol.rsplit(".", 1)[-1]
        return "UNKNOWN"

    def _event_time_for_trade_date(self, trade_date: date) -> datetime:
        return datetime.combine(trade_date, time(hour=15, minute=0), SHANGHAI).astimezone(UTC)

    def _available_at_for_trade_date(self, trade_date: date) -> datetime:
        return datetime.combine(trade_date, time(hour=17, minute=0), SHANGHAI).astimezone(UTC)

    def _normalize_trade_date(self, value: Any) -> date | None:
        if value is None or value == "" or pd.isna(value):
            return None
        if isinstance(value, date):
            return value
        if hasattr(value, "date"):
            normalized = value.date()
            if isinstance(normalized, date):
                return normalized
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()

    def _normalize_required_float(self, value: Any, *, field_name: str) -> float:
        if value is None or value == "" or pd.isna(value):
            raise ValueError(f"missing numeric field: {field_name}")
        return float(value)

    def _fingerprint_row(self, *, symbol: str, trade_date: date, normalized: dict[str, Any]) -> str:
        payload = {
            "symbol": symbol,
            "trade_date": trade_date.isoformat(),
            **normalized,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        ).hexdigest()

    def _dedupe_records(self, symbol: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[date, dict[str, Any]] = {}
        for row in records:
            trade_date = self._normalize_trade_date(row.get("date"))
            if trade_date is None:
                continue
            normalized = {
                "open": self._normalize_required_float(row.get("open"), field_name="open"),
                "high": self._normalize_required_float(row.get("high"), field_name="high"),
                "low": self._normalize_required_float(row.get("low"), field_name="low"),
                "close": self._normalize_required_float(row.get("close"), field_name="close"),
                "volume": self._normalize_required_float(row.get("volume"), field_name="volume"),
                "turnover": None if row.get("turnover") is None or row.get("turnover") == "" or pd.isna(row.get("turnover")) else float(row.get("turnover")),
            }
            fingerprint = self._fingerprint_row(symbol=symbol, trade_date=trade_date, normalized=normalized)
            existing = deduped.get(trade_date)
            candidate = {
                "trade_date": trade_date,
                "normalized": normalized,
                "fingerprint": fingerprint,
            }
            if existing is None:
                deduped[trade_date] = candidate
                continue
            if existing["fingerprint"] != fingerprint:
                raise ValueError(f"conflicting provider rows for {symbol} on {trade_date.isoformat()}")
        return list(deduped.values())

    async def _upsert_bars(
        self,
        symbol: str,
        df: pd.DataFrame,
        *,
        market_kind: str,
        adjustment_policy: str,
    ) -> _UpsertOutcome:
        """批量 upsert bars 到数据库。

        先按 symbol 一次性加载目标区间内已有记录，再在内存中区分
        更新与新增，避免逐行 `SELECT + UPDATE/INSERT` 带来的放大开销。
        """
        if df is None or df.empty:
            return _UpsertOutcome(count=0, earliest_changed_trade_date=None, latest_changed_trade_date=None)

        records = self._dedupe_records(symbol, df.to_dict(orient="records"))
        trade_dates = [row["trade_date"] for row in records]
        if not trade_dates:
            return _UpsertOutcome(count=0, earliest_changed_trade_date=None, latest_changed_trade_date=None)

        min_trade_date = min(trade_dates)
        max_trade_date = max(trade_dates)
        exchange = self._infer_exchange(symbol)
        asset_type = "etf" if market_kind == "etf" else "index" if market_kind == "index" else "stock"
        captured_at = datetime.now(UTC)

        async with self._factory() as session:
            stmt = select(OHLCVBar).where(
                OHLCVBar.symbol == symbol,
                OHLCVBar.exchange == exchange,
                OHLCVBar.asset_type == asset_type,
                OHLCVBar.frequency == "1d",
                OHLCVBar.adjustment_policy == adjustment_policy,
                OHLCVBar.trade_date >= min_trade_date,
                OHLCVBar.trade_date <= max_trade_date,
            )
            existing_rows = await session.scalars(stmt)
            existing_by_trade_date = {row.trade_date: row for row in existing_rows.all()}

            new_rows: list[OHLCVBar] = []
            count = 0
            changed_trade_dates: list[date] = []
            for row in records:
                trade_date = row["trade_date"]
                normalized = row["normalized"]
                ingested_at = datetime.now(UTC)
                available_at = self._available_at_for_trade_date(trade_date)
                fingerprint = row["fingerprint"]

                existing = existing_by_trade_date.get(trade_date)
                if existing is not None:
                    if existing.source_payload_fingerprint == fingerprint:
                        continue
                    existing.open = normalized["open"]
                    existing.high = normalized["high"]
                    existing.low = normalized["low"]
                    existing.close = normalized["close"]
                    existing.volume = normalized["volume"]
                    existing.turnover = normalized["turnover"]
                    existing.source_payload_fingerprint = fingerprint
                    existing.source = "akshare"
                    existing.source_symbol = symbol
                    existing.captured_at = captured_at
                    existing.ingested_at = ingested_at
                    existing.event_time = self._event_time_for_trade_date(trade_date)
                    existing.available_at = available_at
                    existing.source_time = None
                    existing.source_time_reason = "provider_time_unavailable"
                    changed_trade_dates.append(trade_date)
                else:
                    new_rows.append(
                        OHLCVBar(
                            symbol=symbol,
                            source_symbol=symbol,
                            exchange=exchange,
                            asset_type=asset_type,
                            frequency="1d",
                            adjustment_policy=adjustment_policy,
                            source="akshare",
                            source_payload_fingerprint=fingerprint,
                            trade_date=trade_date,
                            open=normalized["open"],
                            high=normalized["high"],
                            low=normalized["low"],
                            close=normalized["close"],
                            volume=normalized["volume"],
                            turnover=normalized["turnover"],
                            event_time=self._event_time_for_trade_date(trade_date),
                            source_time=None,
                            source_time_reason="provider_time_unavailable",
                            captured_at=captured_at,
                            ingested_at=ingested_at,
                            available_at=available_at,
                        )
                    )
                    changed_trade_dates.append(trade_date)
                count += 1

            if new_rows:
                session.add_all(new_rows)

            await session.commit()
            if not changed_trade_dates:
                return _UpsertOutcome(count=0, earliest_changed_trade_date=None, latest_changed_trade_date=None)
            return _UpsertOutcome(
                count=count,
                earliest_changed_trade_date=min(changed_trade_dates),
                latest_changed_trade_date=max(changed_trade_dates),
            )

    async def _invalidate_indicators(self, *, symbol: str, start_date: date) -> int:
        """当 OHLCV 被修复后，删除受影响日期及之后的指标缓存。"""
        async with self._factory() as session:
            result = await session.execute(
                delete(Indicator).where(
                    Indicator.symbol == symbol,
                    Indicator.trade_date >= start_date,
                )
            )
            await session.commit()
        deleted = int(result.rowcount or 0)
        logger.info(
            "指标缓存失效: symbol=%s, start_date=%s, deleted=%s",
            symbol,
            start_date,
            deleted,
        )
        return deleted

    async def get_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[OHLCVBar]:
        """查询指定区间 ohlcv 数据"""
        async with self._factory() as session:
            stmt = select(OHLCVBar).where(
                OHLCVBar.symbol == symbol,
                OHLCVBar.trade_date >= start_date,
                OHLCVBar.trade_date <= end_date,
            ).order_by(OHLCVBar.trade_date)
            result = await session.scalars(stmt)
            return list(result.all())

    async def plan_trade_date_coverage(
        self,
        *,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, list[date]]:
        requested_trade_dates: list[date] = []
        skipped_non_trading_dates: list[date] = []
        from src.backtest.engine import TradeCalendar
        current = start_date
        while current <= end_date:
            if TradeCalendar.is_trade_date(current):
                requested_trade_dates.append(current)
            else:
                skipped_non_trading_dates.append(current)
            current = current.fromordinal(current.toordinal() + 1)

        async with self._factory() as session:
            result = await session.scalars(
                select(OHLCVBar.trade_date).where(
                    OHLCVBar.symbol == symbol,
                    OHLCVBar.trade_date >= start_date,
                    OHLCVBar.trade_date <= end_date,
                )
            )
            present = set(result.all())

        missing_trade_dates = [trade_date for trade_date in requested_trade_dates if trade_date not in present]
        return {
            "requested_trade_dates": requested_trade_dates,
            "skipped_non_trading_dates": skipped_non_trading_dates,
            "missing_trade_dates": missing_trade_dates,
        }

    async def repair_bars(
        self,
        *,
        symbols: list[str],
        start_date: date,
        end_date: date,
        market_kind_by_symbol: dict[str, str] | None = None,
        adjustment_policy_by_symbol: dict[str, str] | None = None,
    ) -> dict[str, int]:
        return await self.crawl_bars(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            market_kind_by_symbol=market_kind_by_symbol,
            adjustment_policy_by_symbol=adjustment_policy_by_symbol,
        )

    async def get_latest_close(self, symbol: str) -> float | None:
        """获取某标的最新收盘价。

        Returns:
            最新收盘价（float），如果不存在返回 None
        """
        async with self._factory() as session:
            stmt = (
                select(OHLCVBar.close)
                .where(OHLCVBar.symbol == symbol)
                .order_by(OHLCVBar.trade_date.desc())
                .limit(1)
            )
            result = await session.scalar(stmt)
            return float(result) if result is not None else None

    def get_latest_close_sync(self, symbol: str) -> float | None:
        """同步版本的 get_latest_close，供无法使用 async 的场景调用。

        内部使用 asyncio.run() 包装，勿在已有 async 上下文中调用。

        Returns:
            最新收盘价（float），如果不存在返回 None
        """
        import asyncio
        return asyncio.run(self.get_latest_close(symbol))

    async def get_bars_as_df(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """查询指定区间 ohlcv 数据并返回 DataFrame。

        返回的 DataFrame 包含 date, close 列（与 classify_market_state 兼容）。

        Returns:
            pd.DataFrame，带 date, close 列
        """
        bars = await self.get_bars(symbol, start_date, end_date)
        if not bars:
            return pd.DataFrame(columns=["date", "close"])
        return pd.DataFrame([
            {"date": bar.trade_date, "close": bar.close}
            for bar in bars
        ])
