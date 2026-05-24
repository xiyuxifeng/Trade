"""盘后评估上下文服务。

职责：
- 为盘后评估统一组装 EvidencePack
- 为风控评估统一构建 AccountSnapshot
- 将 ManagerAgent 中的证据拼装逻辑下沉，减少编排层耦合
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from src.common.logger import get_logger
from src.db.session import session_scope
from src.db.repositories import SignalRepository
from src.evaluation.evidence_pack import EvidencePack, MarketDataSnapshot
from src.risk.account_service import build_account_snapshot
from src.risk.types import AccountSnapshot
from src.schemas.contracts import DailyReport, DataRequest, DataResponseStatus, TradeIdea
from src.strategy_library.schemas import StrategyVersion
from src.strategy_library.service import StrategyLibraryService

if TYPE_CHECKING:
    from src.agents.data_agent.agent import DataAgent
    from src.strategy.signal_version import SignalVersioning

logger = get_logger(__name__)


class EvaluationContextService:
    """盘后评估上下文服务。"""

    def __init__(
        self,
        *,
        data_agent: "DataAgent",
        strategy_library_service: StrategyLibraryService,
        signal_repository: SignalRepository | None = None,
    ) -> None:
        self.data_agent = data_agent
        self.strategy_library_service = strategy_library_service
        self.signal_repository = signal_repository or SignalRepository()

    async def _load_signal_context(self, idea_id) -> object | None:
        """从信号版本存储中读取交易想法上下文。"""
        async with session_scope() as session:
            signal = await self.signal_repository.get_by_signal_id(session, idea_id)
        if signal is None:
            return None
        metadata = signal.signal_metadata or {}
        if isinstance(metadata, dict):
            context = metadata.get("context")
            if context is not None:
                return context
        return None

    async def _fetch_full_market_data(self, symbols: list[str]) -> dict[str, Any]:
        """拉取用于 EvidencePack 的完整市场数据。"""
        if not symbols:
            return {}

        market_data: dict[str, Any] = {}
        for dataset in ("ohlcv_1d", "indicators"):
            req = DataRequest(
                trader_id="manager",
                symbols=symbols,
                dataset=dataset,
                fields=[dataset],
            )
            resp = await self.data_agent.handle(req)
            if resp.status == DataResponseStatus.ok:
                market_data.update(resp.payload)

        return market_data

    async def _load_strategy_version(self, strategy_version_id: str | None) -> StrategyVersion | None:
        """加载完整策略版本。"""
        if not strategy_version_id:
            return None

        async with session_scope() as session:
            return await self.strategy_library_service.get_version(session, strategy_version_id)

    async def generate_evidence_pack(
        self,
        *,
        idea: TradeIdea,
        daily_report: DailyReport | None = None,
        last_prices: dict[str, float],
    ) -> EvidencePack:
        """为单条 TradeIdea 组装 EvidencePack。"""
        _ = daily_report
        signal_context = await self._load_signal_context(idea.idea_id)
        raw_market_data = await self._fetch_full_market_data([idea.symbol])
        ohlcv_1d = raw_market_data.get("ohlcv_1d", {}) or {}
        bars = ohlcv_1d.get(idea.symbol, [])

        market_data = MarketDataSnapshot(
            bars=bars,
            ohlcv_1d=ohlcv_1d,
            indicators=raw_market_data.get("indicators", {}),
            entry_price=float(idea.entry.price) if idea.entry and idea.entry.price else None,
            target_price=float(idea.target_price) if idea.target_price is not None else None,
            stop_loss_price=float(idea.stop_loss_price) if idea.stop_loss_price is not None else None,
            current_price=last_prices.get(idea.symbol),
        )

        strategy_version = await self._load_strategy_version(idea.strategy_version_id)
        rules_snapshot = strategy_version.rules_snapshot if strategy_version else []

        return EvidencePack.from_trade_idea(
            trade_idea=idea,
            signal_context=signal_context,
            market_data=market_data,
            strategy_version=strategy_version,
            strategy_version_snapshot=rules_snapshot,
        )

    async def get_account_snapshot(
        self,
        *,
        trade_idea: TradeIdea | None = None,
        account_id: str = "default",
    ) -> AccountSnapshot:
        """构建账户快照，优先使用 trade_idea 的 trader_id。"""
        if trade_idea and trade_idea.trader_id:
            account_id = str(trade_idea.trader_id)

        try:
            async with session_scope() as session:
                snapshot = await build_account_snapshot(
                    session=session,
                    account_id=account_id,
                )
                logger.debug(
                    "账户快照已构建: account=%s, net_value=%.2f, positions=%d",
                    account_id,
                    snapshot.net_value,
                    len(snapshot.positions),
                )
                return snapshot
        except Exception as exc:  # noqa: BLE001
            logger.warning("真实账户快照构建失败: %s，使用模拟账户 fallback", exc)

        return AccountSnapshot(
            account_id=account_id,
            timestamp=datetime.now(timezone.utc),
            net_value=100000.0,
            cash=50000.0,
            total_position_value=50000.0,
            positions=[],
            daily_pnl=0.0,
            total_pnl=0.0,
        )
