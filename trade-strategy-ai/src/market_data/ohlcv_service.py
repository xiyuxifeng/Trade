# src/market_data/ohlcv_service.py
"""OHLCV 数据服务 - 抓取并存储日线行情数据"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.ohlcv_bar import OHLCVBar
from src.models.stock_info import StockInfo
from src.common.logger import get_logger

logger = get_logger(__name__)


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
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
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
        results: dict[str, int] = {}
        kind_map = market_kind_by_symbol or {}
        total = len(symbols)

        for index, symbol in enumerate(symbols, start=1):
            try:
                market_kind = kind_map.get(symbol)
                if not market_kind:
                    market_kind = await self._resolve_market_kind(symbol)
                df = provider.fetch_ohlcv_1d(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    market_kind=market_kind,
                )
                count = await self._upsert_bars(symbol, df)
                results[symbol] = count
                logger.info(f"抓取成功: {symbol}, {count} 条记录")
            except Exception as e:
                logger.warning(f"抓取失败: {symbol}, error={e}")
                results[symbol] = 0
            if progress_callback is not None:
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

    async def _upsert_bars(self, symbol: str, df: pd.DataFrame) -> int:
        """批量 upsert bars 到数据库。

        先按 symbol 一次性加载目标区间内已有记录，再在内存中区分
        更新与新增，避免逐行 `SELECT + UPDATE/INSERT` 带来的放大开销。
        """
        if df is None or df.empty:
            return 0

        records = df.to_dict(orient="records")

        def _normalize_trade_date(value: Any) -> date | None:
            """把 DataFrame 里的日期值统一成 Python `date`。"""
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

        def _to_float(value: Any, *, default: float = 0.0) -> float:
            """把数值列统一转成 float，空值回退到默认值。"""
            if value is None or value == "" or pd.isna(value):
                return default
            return float(value)

        trade_dates = [normalized for row in records if (normalized := _normalize_trade_date(row.get("date"))) is not None]
        if not trade_dates:
            return 0

        min_trade_date = min(trade_dates)
        max_trade_date = max(trade_dates)

        async with self._factory() as session:
            stmt = select(OHLCVBar).where(
                OHLCVBar.symbol == symbol,
                OHLCVBar.trade_date >= min_trade_date,
                OHLCVBar.trade_date <= max_trade_date,
            )
            existing_rows = await session.scalars(stmt)
            existing_by_trade_date = {row.trade_date: row for row in existing_rows.all()}

            new_rows: list[OHLCVBar] = []
            count = 0
            for row in records:
                trade_date = _normalize_trade_date(row.get("date"))
                if trade_date is None:
                    continue

                open_value = _to_float(row.get("open"))
                high_value = _to_float(row.get("high"))
                low_value = _to_float(row.get("low"))
                close_value = _to_float(row.get("close"))
                volume_value = _to_float(row.get("volume"))
                turnover_raw = row.get("turnover")
                turnover_value = None if turnover_raw is None or turnover_raw == "" or pd.isna(turnover_raw) else float(turnover_raw)

                existing = existing_by_trade_date.get(trade_date)
                if existing is not None:
                    existing.open = open_value
                    existing.high = high_value
                    existing.low = low_value
                    existing.close = close_value
                    existing.volume = volume_value
                    existing.turnover = turnover_value
                else:
                    new_rows.append(
                        OHLCVBar(
                            symbol=symbol,
                            trade_date=trade_date,
                            open=open_value,
                            high=high_value,
                            low=low_value,
                            close=close_value,
                            volume=volume_value,
                            turnover=turnover_value,
                        )
                    )
                count += 1

            if new_rows:
                session.add_all(new_rows)

            await session.commit()
            return count

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
