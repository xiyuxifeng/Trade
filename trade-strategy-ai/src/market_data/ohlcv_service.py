# src/market_data/ohlcv_service.py
"""OHLCV 数据服务 - 抓取并存储日线行情数据"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.ohlcv_bar import OHLCVBar
from src.common.logger import get_logger

logger = get_logger(__name__)


class OHLCVService:
    """ohlcv 数据服务。

    职责：
    - 从 AkShare 批量抓取日线数据
    - 存储到数据库（upsert 模式）
    - 提供按日期/标的查询接口
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def crawl_bars(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, int]:
        """抓取并存储 ohlcv 数据。

        Args:
            symbols: 股票代码列表
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            dict[symbol, count] 抓取成功的记录数
        """
        from src.providers.akshare_provider import AkshareProvider

        provider = AkshareProvider()
        results: dict[str, int] = {}

        for symbol in symbols:
            try:
                df = provider.fetch_ohlcv_1d(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )
                count = await self._upsert_bars(symbol, df)
                results[symbol] = count
                logger.info(f"抓取成功: {symbol}, {count} 条记录")
            except Exception as e:
                logger.warning(f"抓取失败: {symbol}, error={e}")
                results[symbol] = 0

        return results

    async def _upsert_bars(self, symbol: str, df: pd.DataFrame) -> int:
        """批量 upsert bars 到数据库"""
        if df is None or df.empty:
            return 0

        async with self._factory() as session:
            count = 0
            for _, row in df.iterrows():
                trade_date = row.get("date")
                if trade_date is None:
                    continue

                # 检查是否已存在
                stmt = select(OHLCVBar).where(
                    OHLCVBar.symbol == symbol,
                    OHLCVBar.trade_date == trade_date,
                )
                existing = await session.scalar(stmt)

                if existing:
                    # 更新
                    existing.open = float(row.get("open", 0))
                    existing.high = float(row.get("high", 0))
                    existing.low = float(row.get("low", 0))
                    existing.close = float(row.get("close", 0))
                    existing.volume = float(row.get("volume", 0))
                    existing.turnover = float(row.get("turnover")) if row.get("turnover") else None
                else:
                    # 插入
                    bar = OHLCVBar(
                        symbol=symbol,
                        trade_date=trade_date,
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=float(row.get("volume", 0)),
                        turnover=float(row.get("turnover")) if row.get("turnover") else None,
                    )
                    session.add(bar)
                count += 1

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
