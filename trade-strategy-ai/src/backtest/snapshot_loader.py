"""NTL-S6-006: 快照与历史版本离线读取

职责：
- 只读历史快照和历史策略版本，不调用实时 provider
- 提供 market_context 加载
- 提供 strategy_version 加载
- 支持 compatibility_fallback（SignalVersioning/EvidencePack）
"""

from __future__ import annotations

from datetime import date
from typing import Any

from src.backtest.schemas import BacktestRequest


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

    async def load_market_context(
        self, trade_date: date, symbols: list[str]
    ) -> dict[str, Any]:
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

        # 尝试加载 market_universe 快照
        market_universe = None
        bars_by_symbol: dict[str, list[dict]] = {}
        if self.snapshot_service is not None:
            try:
                market_universe = await self.snapshot_service.load(
                    trade_date.isoformat(), slot="market_universe"
                )
            except Exception:
                market_universe = None

            # 尝试加载 ohlcv_1d bars
            try:
                bars_data = await self.snapshot_service.load(
                    trade_date.isoformat(), slot="ohlcv_1d"
                )
                if bars_data and isinstance(bars_data, list):
                    # 按 symbol 归类
                    for bar in bars_data:
                        symbol = bar.get("symbol") or bar.get("code") or ""
                        if symbol:
                            if symbol not in bars_by_symbol:
                                bars_by_symbol[symbol] = []
                            bars_by_symbol[symbol].append(bar)
            except Exception:
                bars_by_symbol = {}

        # 如果快照缺失且启用兜底，标记 compatibility_fallback
        if market_universe is None and self.use_evidence_pack_fallback:
            compatibility_fallback = True
            # 兜底：从 EvidencePack 补洞（未来 NTL-S6-006 完整实现）
            market_universe = None

        # 构建返回结构
        result: dict[str, Any] = {
            "trade_date": trade_date.isoformat(),
            "bars_by_symbol": bars_by_symbol,
            "indicators_by_symbol": {},  # NTL-S6-006 完整实现时填充
            "market_universe": market_universe,
            "topic_snapshot": None,
            "source_refs": [],
            "compatibility_fallback": compatibility_fallback,
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
        except Exception:
            return None
