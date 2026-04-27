"""NTL-S6-006: 快照与历史版本离线读取

职责：
- 只读历史快照和历史策略版本，不调用实时 provider
- 提供 market_context 加载
- 提供 strategy_version 加载
- 支持 compatibility_fallback（SignalVersioning/EvidencePack）
"""

from __future__ import annotations

import inspect
import warnings
from datetime import date
from typing import TYPE_CHECKING, Any

from src.common.logger import get_logger

if TYPE_CHECKING:
    from src.backtest.schemas import MarketContextSnapshot

logger = get_logger(__name__)


class SnapshotLoader:
    """快照加载器。

    加载历史快照和市场数据，用于离线回测。
    禁止在 use_snapshot_only=True 时调用实时 provider。

    Attributes:
        snapshot_service: 快照服务（必须实现 load 方法）
        strategy_repo: 策略版本 Repository（必须实现 get_released_by_trader_and_date）
        use_evidence_pack_fallback: 当快照缺失时是否用 EvidencePack 补洞
        use_snapshot_only: 是否禁止实时取数（默认 True）
    """

    def __init__(
        self,
        snapshot_service: Any = None,
        strategy_repo: Any = None,
        use_evidence_pack_fallback: bool = False,
        use_snapshot_only: bool = True,
    ) -> None:
        self.snapshot_service = snapshot_service
        self.strategy_repo = strategy_repo
        self.use_evidence_pack_fallback = use_evidence_pack_fallback
        self.use_snapshot_only = use_snapshot_only

    async def _load_snapshot(self, trade_date: date, slot: str) -> Any:
        """兼容同步/异步 snapshot_service.load 调用。"""
        if self.snapshot_service is None:
            return None
        loader = self.snapshot_service.load
        if inspect.iscoroutinefunction(loader):
            return await loader(trade_date.isoformat(), slot=slot)
        return loader(trade_date.isoformat(), slot=slot)

    async def load_market_context(
        self, trade_date: date, symbols: list[str]
    ) -> MarketContextSnapshot:
        """加载市场上下文快照。

        加载优先级：
        1. market_universe 快照
        2. ohlcv_1d bars（从标准化历史数据）
        3. topic 快照
        4. 兜底：EvidencePack / SignalVersioning（标记 compatibility_fallback）

        Args:
            trade_date: 交易日期
            symbols: 标的列表（空列表表示全部）

        Returns:
            MarketContextSnapshot 字典
        """
        compatibility_fallback = False

        # 默认值（snapshot_service 为 None 时使用）
        bars_by_symbol: dict[str, list[dict]] = {}
        indicators_by_symbol: dict[str, dict[str, Any]] = {}
        listing_dates: dict[str, str] = {}

        # 尝试加载 market_universe 快照
        market_universe = None
        if self.snapshot_service is not None:
            try:
                market_universe = await self._load_snapshot(trade_date, "market_universe")
                if market_universe is not None:
                    logger.debug(
                        "快照加载成功: slot=market_universe, date=%s",
                        trade_date,
                    )
            except Exception as e:
                logger.warning(
                    "快照加载失败: slot=market_universe, date=%s, error=%s",
                    trade_date,
                    e,
                )
                market_universe = None

            # 尝试加载 ohlcv_1d bars
            bars_by_symbol = {}
            try:
                bars_data = await self._load_snapshot(trade_date, "ohlcv_1d")
                if bars_data and isinstance(bars_data, list):
                    symbol_filter = set(symbols) if symbols else None
                    # 按 symbol 归类
                    for bar in bars_data:
                        symbol = bar.get("symbol") or bar.get("code") or ""
                        if symbol and (symbol_filter is None or symbol in symbol_filter):
                            if symbol not in bars_by_symbol:
                                bars_by_symbol[symbol] = []
                            bars_by_symbol[symbol].append(bar)
                    # 按日期升序排列，保证 _calc_t1_return 取 i+1 一定是 T+1 次日
                    for symbol in bars_by_symbol:
                        bars_by_symbol[symbol].sort(
                            key=lambda b: str(b.get("date") or b.get("Date") or ""),
                        )
                    logger.debug(
                        "快照加载成功: slot=ohlcv_1d, date=%s, symbols=%d",
                        trade_date,
                        len(bars_by_symbol),
                    )
            except Exception as e:
                logger.warning(
                    "快照加载失败: slot=ohlcv_1d, date=%s, error=%s",
                    trade_date,
                    e,
                )
                bars_by_symbol = {}

            # 尝试加载 indicators
            indicators_by_symbol = {}
            try:
                indicators_data = await self._load_snapshot(trade_date, "indicators")
                if indicators_data and isinstance(indicators_data, dict):
                    symbol_filter = set(symbols) if symbols else None
                    # indicators_data 格式: {"000001.SZ": {"rsi": 65.0, "ma5": 10.2}, ...}
                    for symbol, ind_fields in indicators_data.items():
                        if isinstance(ind_fields, dict) and (
                            symbol_filter is None or str(symbol) in symbol_filter
                        ):
                            indicators_by_symbol[str(symbol)] = ind_fields
            except Exception as e:
                logger.warning(
                    "快照加载失败: slot=indicators, date=%s, error=%s",
                    trade_date,
                    e,
                )
                indicators_by_symbol = {}

            # 尝试加载 listing_dates（用于新股判断）
            listing_dates = {}
            try:
                listing_data = await self._load_snapshot(trade_date, "listing_dates")
                if listing_data and isinstance(listing_data, dict):
                    symbol_filter = set(symbols) if symbols else None
                    for symbol, listing_date in listing_data.items():
                        if symbol_filter is None or str(symbol) in symbol_filter:
                            listing_dates[str(symbol)] = str(listing_date)
            except Exception as e:
                logger.warning(
                    "快照加载失败: slot=listing_dates, date=%s, error=%s",
                    trade_date,
                    e,
                )
                listing_dates = {}

        # 如果快照缺失且启用兜底，标记 compatibility_fallback
        if market_universe is None and self.use_evidence_pack_fallback:
            compatibility_fallback = True
            logger.info(
                "compatibility_fallback 触发: trader=%s, date=%s, market_universe 快照缺失",
                None,
                trade_date,
            )
            # 兜底：从 EvidencePack 补洞（未来 NTL-S6-006 完整实现）
            market_universe = None

        # 构建返回结构（符合 MarketContextSnapshot 类型约束）
        result: MarketContextSnapshot = {
            "trade_date": trade_date.isoformat(),
            "bars_by_symbol": bars_by_symbol,
            "indicators_by_symbol": indicators_by_symbol,
            "market_universe": market_universe,
            "topic_snapshot": None,
            "source_refs": [],
            "compatibility_fallback": compatibility_fallback,
            "listing_dates": listing_dates,
        }

        return result

    async def load_version_for_date(
        self,
        trader_id: str,
        trade_date: date,
    ) -> Any | None:
        """加载指定日期的已发布策略版本。

        Args:
            trader_id: 交易员 ID
            trade_date: 策略日期

        Returns:
            StrategyVersion 或 None（无版本时）
        """
        if self.strategy_repo is None:
            return None

        try:
            versions = await self.strategy_repo.get_released_by_trader_and_date(
                trader_id=trader_id,
                strategy_date=trade_date,
            )
            if not versions:
                return None
            # 取最新发布的版本
            return sorted(versions, key=lambda v: v.released_at or date.min, reverse=True)[0]
        except Exception as e:
            logger.warning(
                "strategy_repo 异常: trader=%s, date=%s, error=%s",
                trader_id,
                trade_date,
                e,
            )
            warnings.warn(
                f"SnapshotLoader.load_version_for_date failed for trader={trader_id}, date={trade_date}: "
                "strategy_repo raised an exception. Returning None.",
                UserWarning,
            )
            return None
