"""NTL-S6-006: 快照与历史版本离线读取

职责：
- 只读历史快照和历史策略版本，不调用实时 provider
- 提供 market_context 加载（candidate_pool / market_snapshot / ohlcv / indicators）
- 提供 strategy_version 加载
- 支持 compatibility_fallback（EvidencePack）
"""

from __future__ import annotations

import inspect
import warnings
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.common.logger import get_logger
from src.db.repositories.market_regime_repository import MarketRegimeRepository
from src.models.ohlcv_bar import OHLCVBar
from src.services.market_snapshot_service import MarketSnapshotService

if TYPE_CHECKING:
    from src.backtest.schemas import MarketContextSnapshot

logger = get_logger(__name__)


class SnapshotLoader:
    """快照加载器。

    加载历史快照和市场数据，用于离线回测。
    禁止在 use_snapshot_only=True 时调用实时 provider。

    ohlcv_1d 和 indicators 数据从 DB 直读（不再依赖 JSON 快照文件）；
    indicators 首次访问时自动计算并缓存到 indicators 表。

    Attributes:
        snapshot_service: 快照服务（必须实现 load 方法，用于 market_universe）
        strategy_repo: 策略版本 Repository
        indicator_service: 指标服务（可选，None 时跳过指标加载）
        session_factory: DB session factory（用于 ohlcv_bars 查询）
        use_evidence_pack_fallback: 当快照缺失时是否用 EvidencePack 补洞
        use_snapshot_only: 是否禁止实时取数（默认 True）
    """

    def __init__(
        self,
        snapshot_service: Any = None,
        market_snapshot_service: MarketSnapshotService | None = None,
        strategy_repo: Any = None,
        regime_repository: Any = None,
        indicator_service: Any = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        use_evidence_pack_fallback: bool = False,
        use_snapshot_only: bool = True,
        config_path: str | None = None,
        market_universe_slot: str = "09-25",
        market_snapshot_slot: str = "17-30",
    ) -> None:
        self.snapshot_service = snapshot_service
        self.market_snapshot_service = market_snapshot_service
        self.strategy_repo = strategy_repo
        self.regime_repository = regime_repository
        self.indicator_service = indicator_service
        self.session_factory = session_factory
        self.use_evidence_pack_fallback = use_evidence_pack_fallback
        self.use_snapshot_only = use_snapshot_only
        self.config_path = config_path
        self.market_universe_slot = market_universe_slot
        self.market_snapshot_slot = market_snapshot_slot

    async def _load_snapshot(self, trade_date: date, slot: str) -> Any:
        """兼容同步/异步 snapshot_service.load 调用（仅用于 market_universe）。"""
        if self.snapshot_service is None:
            return None
        loader = self.snapshot_service.load
        if inspect.iscoroutinefunction(loader):
            return await loader(trade_date.isoformat(), slot=slot)
        return loader(trade_date.isoformat(), slot=slot)

    async def _load_market_snapshot(self, trade_date: date, slot: str) -> Any:
        """兼容同步/异步 market_snapshot_service.load_market_snapshot 调用。"""
        if self.market_snapshot_service is None or not self.config_path:
            return None
        loader = self.market_snapshot_service.load_market_snapshot
        if inspect.iscoroutinefunction(loader):
            return await loader(config_path=self.config_path, trade_date=trade_date.isoformat(), slot=slot)
        return loader(config_path=self.config_path, trade_date=trade_date.isoformat(), slot=slot)

    async def _load_ohlcv_from_db(
        self, trade_date: date, symbols: list[str]
    ) -> dict[str, list[dict]]:
        """从 ohlcv_bars 表加载 OHLCV 数据（T-60 日范围内），按 symbol 归类。"""
        if self.session_factory is None:
            return {}

        lookback = trade_date - timedelta(days=90)
        bars_by_symbol: dict[str, list[dict]] = {}
        symbol_set = set(symbols) if symbols else None

        async with self.session_factory() as session:
            stmt = (
                select(OHLCVBar)
                .where(OHLCVBar.trade_date >= lookback)
                .where(OHLCVBar.trade_date <= trade_date)
                .order_by(OHLCVBar.trade_date.asc())
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        for r in rows:
            if symbol_set is not None and r.symbol not in symbol_set:
                continue
            if r.symbol not in bars_by_symbol:
                bars_by_symbol[r.symbol] = []
            bars_by_symbol[r.symbol].append({
                "symbol": r.symbol,
                "date": r.trade_date.isoformat(),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            })

        logger.debug(
            "ohlcv_bars DB 加载: date=%s, symbols=%d",
            trade_date,
            len(bars_by_symbol),
        )
        return bars_by_symbol

    async def _load_indicators_from_db(
        self, trade_date: date, symbols: list[str]
    ) -> dict[str, dict[str, Any]]:
        """从 indicators 表加载指标数据（首次访问时自动计算并缓存）。"""
        if self.indicator_service is None:
            return {}

        try:
            result = await self.indicator_service.get_for_date(symbols, trade_date)
            logger.debug(
                "indicators 加载: date=%s, symbols=%d",
                trade_date,
                len(result),
            )
            return result
        except Exception as e:
            logger.exception("indicators 加载失败: date=%s, error=%s", trade_date, e)
            return {}

    async def _load_market_regime_from_db(
        self,
        trade_date: date,
        regime_version: str | None,
    ) -> dict[str, Any] | None:
        """按交易日和版本加载 Market Regime。"""
        if self.session_factory is None or not regime_version:
            return None

        repository = self.regime_repository or MarketRegimeRepository()

        try:
            async with self.session_factory() as session:
                regimes = await repository.list_regimes(
                    session,
                    trade_date=trade_date,
                    regime_version=regime_version,
                    limit=1,
                )
        except Exception as e:
            logger.exception(
                "market_regime 加载失败: date=%s, regime_version=%s, error=%s",
                trade_date,
                regime_version,
                e,
            )
            return None

        if not regimes:
            return None

        regime = regimes[0]
        if hasattr(regime, "to_dict"):
            return regime.to_dict()
        if isinstance(regime, dict):
            return regime
        if hasattr(regime, "__dict__"):
            return dict(vars(regime))
        return None

    async def load_market_context(
        self,
        trade_date: date,
        symbols: list[str],
        regime_version: str | None = None,
        benchmark_symbol: str | None = None,
    ) -> MarketContextSnapshot:
        """加载市场上下文快照。

        加载顺序：
        1. candidate_pool（market_universe，按 market_universe_slot 读取）
        2. market_snapshot（按 market_snapshot_slot 读取）
        3. ohlcv_1d bars（从 DB ohlcv_bars 表）
        4. indicators（从 DB indicators 表，首次计算并缓存）
        5. market_regime（按 trade_date + regime_version 读取，若提供）
        6. 兜底：EvidencePack

        Args:
            trade_date: 交易日期
            symbols: 标的列表（空列表表示全部）
            benchmark_symbol: 回测选择的基准指数代码，会被并入加载列表

        Returns:
            MarketContextSnapshot 字典
        """
        # COMPATIBILITY ONLY:
        # candidate_pool / market_snapshot 是内部过渡字段，
        # 这里只允许作为统一市场上下文的组成部分，不允许再向外拆成新的主入口。
        compatibility_fallback = False
        listing_dates: dict[str, str] = {}
        source_refs: list[str] = []

        # 1. 加载 candidate_pool / market_universe 快照
        # 兼容读取：用于回测上下文与旧数据回放，不再作为独立对外入口。
        market_universe = None
        candidate_pool = None
        if self.snapshot_service is not None:
            try:
                market_universe = await self._load_snapshot(trade_date, self.market_universe_slot)
                candidate_pool = market_universe
                if market_universe is not None:
                    source_refs.append(f"data/market_universe/snapshots/{trade_date.isoformat()}/{self.market_universe_slot}.json")
            except Exception as e:
                logger.exception(
                    "快照加载失败: slot=%s, date=%s, error=%s",
                    self.market_universe_slot,
                    trade_date,
                    e,
                )

        # 2. 加载结构化 market_snapshot
        # 兼容读取：最终对外统一语义仍是“市场上下文快照”。
        market_snapshot = None
        if self.market_snapshot_service is not None and self.config_path:
            try:
                market_snapshot = await self._load_market_snapshot(trade_date, self.market_snapshot_slot)
                if market_snapshot is not None:
                    source_refs.append(
                        f"data/processed/market_snapshot/{trade_date.isoformat()}/{self.market_snapshot_slot}/snapshot.json"
                    )
            except Exception as e:
                logger.exception(
                    "market_snapshot 加载失败: slot=%s, date=%s, error=%s",
                    self.market_snapshot_slot,
                    trade_date,
                    e,
                )

        if candidate_pool is None and market_snapshot is not None:
            metadata = getattr(market_snapshot, "metadata", None)
            if isinstance(metadata, dict):
                derived_candidate_pool = metadata.get("candidate_pool")
                if derived_candidate_pool is not None:
                    candidate_pool = derived_candidate_pool
                    market_universe = derived_candidate_pool
                    source_refs.append("market_snapshot.metadata.candidate_pool")

        load_symbols = list(dict.fromkeys([*symbols, benchmark_symbol] if benchmark_symbol else symbols))

        # 3. 从 DB 加载 ohlcv_1d
        bars_by_symbol = await self._load_ohlcv_from_db(trade_date, load_symbols)

        if benchmark_symbol and benchmark_symbol not in bars_by_symbol:
            raise ValueError(f"benchmark_symbol {benchmark_symbol} has no OHLCV bars in db for trade_date={trade_date}")

        # 4. 从 DB 加载 indicators（首次计算并缓存）
        indicators_by_symbol = await self._load_indicators_from_db(trade_date, load_symbols)

        # 5. 加载指定版本的 Market Regime（若提供）
        market_regime = await self._load_market_regime_from_db(trade_date, regime_version)

        # 6. 兜底：EvidencePack（仅在快照缺失时用于兼容补洞）
        if market_universe is None and self.use_evidence_pack_fallback:
            compatibility_fallback = True
            logger.info(
                "compatibility_fallback 触发: date=%s, market_universe 快照缺失",
                trade_date,
            )

        result: MarketContextSnapshot = {
            "trade_date": trade_date.isoformat(),
            "bars_by_symbol": bars_by_symbol,
            "indicators_by_symbol": indicators_by_symbol,
            "market_universe": market_universe,
            "candidate_pool": candidate_pool,
            "market_snapshot": market_snapshot,
            "benchmark_symbol": benchmark_symbol,
            "topic_snapshot": None,
            "market_regime": market_regime,
            "market_regime_version": regime_version,
            "source_refs": source_refs,
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
            logger.exception(
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
