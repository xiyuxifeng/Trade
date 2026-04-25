"""Evidence Pack：盘后评估的证据容器。

职责：
- 将盘前生成的 TradeIdea 与其完整上下文（SignalContext、市场快照、策略版本）
  聚合到同一个结构中，供盘后评估、失败归因和 ranking 使用
- Evidence Pack 在盘后评估时生成，作为 EvaluationResult 的 evidence_pack_refs 引用

NTL-S5-001
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from src.schemas.contracts import TradeIdea
    from src.strategy.types import SignalContext
    from src.strategy_library.schemas import StrategyVersion


@dataclass
class MarketDataSnapshot:
    """市场数据快照（结构化 schema）。

    统一 EvidencePack 中的市场数据字段，避免下游多处分支判断。
    字段说明：
        bars: 标准化后的 OHLCV bar 列表（供 MFE/MAE 计算使用）
        ohlcv_1d: 原始日线数据（symbol -> bar list）
        indicators: 技术指标快照
        entry_price: 入场价格
        target_price: 止盈价格
        stop_loss_price: 止损价格
        current_price: 盘后评估时的最新价格
        last_price: fallback 价格（与 current_price 语义等价，保留兼容）
    """

    bars: list[dict[str, Any]] = field(default_factory=list)
    ohlcv_1d: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    indicators: dict[str, Any] = field(default_factory=dict)
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss_price: float | None = None
    current_price: float | None = None
    last_price: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "bars": self.bars,
            "ohlcv_1d": self.ohlcv_1d,
            "indicators": self.indicators,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_loss_price": self.stop_loss_price,
            "current_price": self.current_price,
            "last_price": self.last_price,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MarketDataSnapshot:
        """从字典反序列化。"""
        return cls(
            bars=data.get("bars", []),
            ohlcv_1d=data.get("ohlcv_1d", {}),
            indicators=data.get("indicators", {}),
            entry_price=data.get("entry_price"),
            target_price=data.get("target_price"),
            stop_loss_price=data.get("stop_loss_price"),
            current_price=data.get("current_price"),
            last_price=data.get("last_price"),
        )


@dataclass(frozen=True)
class EvidencePack:
    """盘后评估的证据容器（不可变）。

    在盘后阶段生成，聚合：
    1. 盘前 TradeIdea —— 原始交易想法
    2. SignalContext —— 信号生成时的完整上下文（版本 ID、市场快照、主题 ID）
    3. MarketDataSnapshot —— 评估时的市场数据快照
    4. StrategyVersion —— 引用（完整对象在策略库，不内嵌）

    对应 EvaluationResult.evidence_pack_refs 字段（存储 pack_id 列表）。

    属性：
        pack_id: 唯一标识，用于跨 JSON 持久化和引用
        idea_id: 对应 TradeIdea.idea_id，跨系统关联
        trade_date: 交易日期（从 TradeIdea.as_of_date 派生）
        created_at: 生成时间
        trade_idea: 盘前交易想法（原始引用）
        signal_context: 信号上下文快照（可为 None，表示盘前上下文缺失）
        market_data: 市场数据快照（结构化 MarketDataSnapshot）
        strategy_version_id: 关联的策略版本 ID（NTL-S4-008 追溯链路）
        strategy_version_snapshot: 策略版本快照（rules_snapshot 等，供归因分析）
        extra: 扩展字段（保留给后续 Stage 使用）
    """

    pack_id: UUID = field(default_factory=uuid4)
    idea_id: UUID | None = None

    # 交易日期（从 TradeIdea.as_of_date 派生）
    trade_date: str = ""

    # 证据内容
    trade_idea: TradeIdea | None = None  # TYPE_CHECKING 下使用，运行时为 dict
    signal_context: SignalContext | None = None  # TYPE_CHECKING 下使用，运行时为 dict

    # 市场数据快照（结构化 schema，替代原来的 dict[str, Any]）
    market_data: MarketDataSnapshot = field(default_factory=MarketDataSnapshot)

    # 策略版本追溯
    strategy_version_id: str | None = None
    strategy_version_snapshot: list[dict] = field(default_factory=list)  # rules_snapshot

    # 时间戳
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # 扩展字段
    extra: dict[str, Any] = field(default_factory=dict)

    # -------------------------------------------------
    # 工厂方法：从已有数据构建 EvidencePack
    # -------------------------------------------------

    @classmethod
    def from_trade_idea(
        cls,
        trade_idea: TradeIdea,
        signal_context: SignalContext | None,
        market_data: MarketDataSnapshot | dict[str, Any],
        strategy_version: StrategyVersion | None = None,
        strategy_version_snapshot: list[dict] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> EvidencePack:
        """从盘前输出构建 EvidencePack。

        Args:
            trade_idea: 盘前生成的 TradeIdea
            signal_context: 信号生成上下文（可为 None，表示 Phase 0 降级路径）
            market_data: 市场数据快照（MarketDataSnapshot 或兼容的 dict）
            strategy_version: 关联的策略版本（可选，用于提取 version_id 和 rules_snapshot）
            strategy_version_snapshot: 策略版本快照（可直接传入 rules_snapshot 列表）
            extra: 扩展字段
        """

        # 提取 strategy_version_id 和 rules_snapshot
        sv_id: str | None = None
        sv_snapshot: list[dict] = []

        if strategy_version is not None:
            sv_id = strategy_version.version_id
            sv_snapshot = strategy_version.rules_snapshot
        elif strategy_version_snapshot is not None:
            sv_snapshot = strategy_version_snapshot

        # 兼容 dict 入参（测试中仍可直接传 dict）
        if isinstance(market_data, dict):
            market_data = MarketDataSnapshot.from_dict(market_data)

        return cls(
            idea_id=trade_idea.idea_id,
            trade_date=str(trade_idea.as_of_date),
            trade_idea=trade_idea,
            signal_context=signal_context,
            market_data=market_data,
            strategy_version_id=sv_id,
            strategy_version_snapshot=sv_snapshot,
            extra=extra or {},
        )

    # -------------------------------------------------
    # 序列化方法
    # -------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典，供 JSON 持久化或跨服务传输。"""
        return {
            "pack_id": str(self.pack_id),
            "idea_id": str(self.idea_id) if self.idea_id else None,
            "trade_date": self.trade_date,
            "trade_idea": _trade_idea_to_dict(self.trade_idea) if self.trade_idea else None,
            "signal_context": _signal_context_to_dict(self.signal_context) if self.signal_context else None,
            "market_data": self.market_data.to_dict(),
            "strategy_version_id": self.strategy_version_id,
            "strategy_version_snapshot": self.strategy_version_snapshot,
            "created_at": self.created_at.isoformat(),
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidencePack:
        """从字典反序列化。"""
        from src.schemas.contracts import TradeIdea
        from src.strategy.types import SignalContext

        trade_idea: TradeIdea | None = None
        if data.get("trade_idea"):
            trade_idea = TradeIdea.model_validate(data["trade_idea"])

        signal_context: SignalContext | None = None
        if data.get("signal_context"):
            signal_context = SignalContext(**data["signal_context"])

        market_data = MarketDataSnapshot.from_dict(data.get("market_data", {}))

        return cls(
            pack_id=UUID(data["pack_id"]) if data.get("pack_id") else uuid4(),
            idea_id=UUID(data["idea_id"]) if data.get("idea_id") else None,
            trade_date=data.get("trade_date", ""),
            trade_idea=trade_idea,
            signal_context=signal_context,
            market_data=market_data,
            strategy_version_id=data.get("strategy_version_id"),
            strategy_version_snapshot=data.get("strategy_version_snapshot", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(UTC),
            extra=data.get("extra", {}),
        )


# -------------------------------------------------
# 内部序列化工具（避免在 TYPE_CHECKING 块外引用 pydantic/dataclass 类型）
# -------------------------------------------------

def _trade_idea_to_dict(idea: TradeIdea) -> dict[str, Any]:
    """TradeIdea -> dict（支持 pydantic model）。"""
    if hasattr(idea, "model_dump"):
        return idea.model_dump(mode="json")
    return dict(idea)


def _signal_context_to_dict(ctx: SignalContext) -> dict[str, Any]:
    """SignalContext -> dict（支持 dataclass）。"""
    if hasattr(ctx, "__dataclass_fields__"):
        import dataclasses
        return dataclasses.asdict(ctx)
    return dict(ctx)
