"""指标计算与缓存服务。

提供 "首次计算写入 DB，后续读缓存" 的指标获取策略，
回测引擎和 DataAgent 均可直接调用。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.common.logger import get_logger
from src.indicators.pattern_features import PatternFeatureEngine
from src.models.indicator import Indicator
from src.models.ohlcv_bar import OHLCVBar

logger = get_logger(__name__)


class IndicatorService:
    """指标服务：首次回测时按需计算并缓存到 indicators 表。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def get_or_compute(
        self, symbol: str, trade_date: date
    ) -> dict[str, Any] | None:
        """获取单个 symbol+date 的指标数据。

        Returns:
            指标 dict（与 backtest 期望的 indicators_by_symbol[symbol] 格式一致），
            数据不足时返回 None。
        """
        async with self._factory() as session:
            row = await self._find(session, symbol, trade_date)
            if row is not None:
                return self._row_to_dict(row)

        # 未缓存 → 从 ohlcv_bars 取数据 → 计算 → 写入
        return await self._compute_and_save(symbol, trade_date)

    async def batch_get_or_compute(
        self, symbols: list[str], trade_dates: list[date]
    ) -> dict[str, dict[str, Any]]:
        """批量获取指标数据。

        Returns:
            {symbol: {field: value}} 格式，与 backtest 期望的 indicators_by_symbol 兼容。
        """
        result: dict[str, dict[str, Any]] = {}
        missing: list[tuple[str, date]] = []

        # 1. 批量查 DB
        async with self._factory() as session:
            for symbol in symbols:
                for td in trade_dates:
                    row = await self._find(session, symbol, td)
                    if row is not None:
                        result[symbol] = self._row_to_dict(row)
                        break  # 取最新一个有效日期的指标
                    else:
                        missing.append((symbol, td))

        # 2. 缺失的按需计算
        for symbol, td in missing:
            indicators = await self._compute_and_save(symbol, td)
            if indicators is not None and symbol not in result:
                result[symbol] = indicators

        return result

    async def get_for_date(
        self, symbols: list[str], trade_date: date
    ) -> dict[str, dict[str, Any]]:
        """获取指定日期的所有 symbol 指标数据。

        这是回测引擎的主要入口。
        """
        result: dict[str, dict[str, Any]] = {}

        async with self._factory() as session:
            for symbol in symbols:
                row = await self._find(session, symbol, trade_date)
                if row is not None:
                    result[symbol] = self._row_to_dict(row)
                else:
                    break
            else:
                return result  # 全部命中

        # 有 miss → 逐个计算
        for symbol in symbols:
            if symbol not in result:
                indicators = await self._compute_and_save(symbol, trade_date)
                if indicators is not None:
                    result[symbol] = indicators

        return result

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    async def _find(
        self, session: AsyncSession, symbol: str, trade_date: date
    ) -> Indicator | None:
        stmt = (
            select(Indicator)
            .where(Indicator.symbol == symbol)
            .where(Indicator.trade_date == trade_date)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _compute_and_save(
        self, symbol: str, trade_date: date
    ) -> dict[str, Any] | None:
        """从 ohlcv_bars 读取 OHLCV，计算指标，写入 indicators 表。"""
        bars = await self._load_ohlcv_bars(symbol, trade_date)
        if bars is None or len(bars) < 15:
            return None

        engine = PatternFeatureEngine(bars)
        features = engine.compute_all()

        indicator_dict = self._features_to_dict(features)
        await self._upsert(symbol, trade_date, indicator_dict)
        return indicator_dict

    async def _load_ohlcv_bars(
        self, symbol: str, trade_date: date
    ) -> list[dict[str, Any]] | None:
        """加载 symbol 在 trade_date 及之前的 OHLCV 数据（取最近 200 条）。"""
        from datetime import timedelta

        lookback = trade_date - timedelta(days=400)  # 足够覆盖 MA200

        async with self._factory() as session:
            stmt = (
                select(OHLCVBar)
                .where(OHLCVBar.symbol == symbol)
                .where(OHLCVBar.trade_date >= lookback)
                .where(OHLCVBar.trade_date <= trade_date)
                .order_by(OHLCVBar.trade_date.asc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        if not rows:
            return None

        return [
            {
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]

    async def _upsert(
        self, symbol: str, trade_date: date, indicators: dict[str, Any]
    ) -> None:
        """写入或更新 indicators 表。"""
        now = datetime.utcnow()
        values = {
            "symbol": symbol,
            "trade_date": trade_date,
            **{k: indicators.get(k) for k in self._indicator_fields()},
            "computed_at": now,
        }

        stmt = pg_insert(Indicator).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_indicator_symbol_date",
            set_={k: stmt.excluded[k] for k in self._indicator_fields()},
        )

        async with self._factory() as session:
            await session.execute(stmt)
            await session.commit()

    # ------------------------------------------------------------------
    # 转换工具
    # ------------------------------------------------------------------

    @staticmethod
    def _indicator_fields() -> list[str]:
        """indicators 表中除 id/symbol/trade_date/computed_at 外的字段。"""
        return [
            "rsi", "macd_histogram", "bb_width", "cci",
            "ma50", "ma200", "stoch_k", "volume_ratio",
            "price_vs_ma", "atr_ratio", "close_position",
        ]

    @staticmethod
    def _features_to_dict(features) -> dict[str, Any]:
        """将 PatternFeatures 转为 indicators 表字段 dict。

        注意：Indicator 表不存储 stoch_k，回测暂时也不依赖它，
        但 PatternFeatureEngine.compute_all() 返回所有指标。
        """
        def _f(v: float | None) -> float | None:
            if v is None:
                return None
            if np.isnan(v):
                return None
            return float(v)

        return {
            "rsi": _f(features.rsi),
            "macd_histogram": _f(features.macd_histogram),
            "bb_width": _f(features.bb_width),
            "cci": _f(features.cci),
            "ma50": _f(features.ma50),
            "ma200": _f(features.ma200),
            "stoch_k": _f(features.stoch_k),
            "volume_ratio": _f(features.volume_ratio),
            "price_vs_ma": _f(features.price_vs_ma),
            "atr_ratio": _f(features.atr_ratio),
            "close_position": _f(features.close_position),
        }

    @staticmethod
    def _row_to_dict(row: Indicator) -> dict[str, Any]:
        """将 Indicator ORM 行转为回测兼容的 dict。"""
        return {
            "rsi": row.rsi,
            "macd_histogram": row.macd_histogram,
            "bb_width": row.bb_width,
            "cci": row.cci,
            "ma50": row.ma50,
            "ma200": row.ma200,
            "stoch_k": row.stoch_k,
            "volume_ratio": row.volume_ratio,
            "price_vs_ma": row.price_vs_ma,
            "atr_ratio": row.atr_ratio,
            "close_position": row.close_position,
        }
