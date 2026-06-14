"""Schema ↔ ORM 转换层。

设计原则（TD-003-b 明确路径）：
1. dataclass/pydantic Schema 定义内存结构（in-memory），不绑定数据库
2. ORM 模型负责持久化
3. 两者之间通过 converters 显式转换，不在服务代码中散落

转换分类：

| 场景 | 存储方式 | 说明 |
|------|----------|------|
| 标量字段（str/float/int/UUID） | ORM 列直写 | signal_id, symbol, side 等 |
| 复杂嵌套结构（PriceSpec/PositionSize） | JSONB 列 | entry_price, position_size 等 |
| 列表字段（rules_snapshot, triggered_rules） | JSONB 列 | 直接序列化 |
| 完整聚合对象（SignalContext, EvidencePack） | JSONB 列 + ID 引用 | 保留完整结构供回放 |
| 策略版本（StrategyVersion） | JSONB 列 | 存完整 payload，通过 ORM ID 引用 |

使用场景：
- 写入：Schema → ORM：schema_to_signal(), schema_to_trader_strategy_version()
- 读取：ORM → Schema：orm_to_signal(), orm_to_trader_strategy_version()
- 跨服务传输：Schema → dict：schema.to_dict()（JSON 持久化或 RPC）

NTL-S5-001 / TD-003-b
"""

from __future__ import annotations

from dataclasses import is_dataclass
from datetime import datetime
from typing import Any, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.strategy.types import Signal, SignalContext
    from src.strategy_library.schemas import StrategyVersion
    from src.schemas.contracts import TradeIdea
    from src.evaluation.evidence_pack import EvidencePack


# -------------------------------------------------
# 工具函数
# -------------------------------------------------

def _asdict_if_dataclass(obj: Any) -> Any:
    """如果是 dataclass 实例，递归转为 dict；否则原样返回。"""
    if is_dataclass(obj):
        import dataclasses
        return {k: _asdict_if_dataclass(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _asdict_if_dataclass(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_asdict_if_dataclass(i) for i in obj]
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _serialize_complex(obj: Any) -> Any:
    """序列化复杂对象（dataclass/pydantic/UUID/datetime）为 JSON 兼容结构。"""
    if hasattr(obj, "model_dump"):
        # Pydantic BaseModel
        return obj.model_dump(mode="json")
    return _asdict_if_dataclass(obj)


# -------------------------------------------------
# Signal 转换
# -------------------------------------------------

def schema_to_signal_orm(
    schema: Signal,
    orm_signal: "Signal",
) -> "Signal":
    """将 Signal dataclass 的字段写入已创建的 ORM Signal 实例。

    复杂字段（entry_price, position_size, stop_loss, take_profit, metadata）
    序列化为 JSONB。
    """
    orm_signal.signal_id = schema.signal_id
    orm_signal.symbol = schema.symbol
    orm_signal.side = schema.side.value if hasattr(schema.side, "value") else schema.side
    orm_signal.confidence = schema.confidence
    orm_signal.triggered_rules = schema.triggered_rules
    orm_signal.synthesis_mode = schema.synthesis_mode.value if hasattr(schema.synthesis_mode, "value") else schema.synthesis_mode
    orm_signal.entry_price = _serialize_complex(schema.entry_price)
    orm_signal.position_size = _serialize_complex(schema.position_size)
    orm_signal.stop_loss = _serialize_complex(schema.stop_loss)
    orm_signal.take_profit = _serialize_complex(schema.take_profit)
    orm_signal.version = schema.version
    raw_strategy_version_id = schema.strategy_version_id
    try:
        orm_signal.strategy_version_id = UUID(str(raw_strategy_version_id)) if raw_strategy_version_id else None
        orm_signal.legacy_strategy_version_id = None
    except ValueError:
        orm_signal.strategy_version_id = None
        orm_signal.legacy_strategy_version_id = raw_strategy_version_id
    orm_signal.signal_metadata = _serialize_complex(schema.metadata)
    return orm_signal


def orm_to_schema_signal(orm_signal: "Signal") -> "Signal":
    """从 ORM Signal 重建 Signal dataclass。"""
    from src.strategy.types import Signal, SignalSide, SynthesisMode

    return Signal(
        signal_id=orm_signal.signal_id,
        symbol=orm_signal.symbol,
        side=SignalSide(orm_signal.side) if orm_signal.side else SignalSide.HOLD,
        confidence=orm_signal.confidence or 0.0,
        timestamp=orm_signal.created_at or datetime.utcnow(),
        triggered_rules=orm_signal.triggered_rules or [],
        synthesis_mode=SynthesisMode(orm_signal.synthesis_mode) if orm_signal.synthesis_mode else SynthesisMode.WEIGHTED_SCORE,
        entry_price=orm_signal.entry_price,
        position_size=orm_signal.position_size,
        stop_loss=orm_signal.stop_loss,
        take_profit=orm_signal.take_profit,
        version=orm_signal.version or "v1",
        strategy_version_id=orm_signal.strategy_version_id or orm_signal.legacy_strategy_version_id,
        metadata=orm_signal.signal_metadata or {},
    )


# -------------------------------------------------
# SignalContext 转换
# -------------------------------------------------

def schema_to_signal_context_orm(
    schema: SignalContext,
) -> dict[str, Any]:
    """将 SignalContext dataclass 序列化为 dict，供 JSONB 存储。

    Returns:
        JSON 兼容的 dict，可直接存入 ORM JSONB 列或 JSON 文件。
    """
    return {
        "features_snapshot": _serialize_complex(schema.features_snapshot),
        "market_state": _serialize_complex(schema.market_state),
        "rules_snapshot": _serialize_complex(schema.rules_snapshot),
        "timestamp": schema.timestamp.isoformat() if isinstance(schema.timestamp, datetime) else schema.timestamp,
        "strategy_version_id": schema.strategy_version_id,
        "market_universe_snapshot": _serialize_complex(schema.market_universe_snapshot),
        "topic_source_ids": schema.topic_source_ids,
    }


def orm_to_schema_signal_context(data: dict[str, Any]) -> "SignalContext":
    """从 dict 重建 SignalContext dataclass。"""
    from src.strategy.types import SignalContext

    ts = data.get("timestamp")
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)

    return SignalContext(
        features_snapshot=data.get("features_snapshot", {}),
        market_state=data.get("market_state", {}),
        rules_snapshot=data.get("rules_snapshot", []),
        timestamp=ts or datetime.utcnow(),
        strategy_version_id=data.get("strategy_version_id"),
        market_universe_snapshot=data.get("market_universe_snapshot"),
        topic_source_ids=data.get("topic_source_ids", []),
    )


# -------------------------------------------------
# StrategyVersion 转换（TraderStrategyVersion ORM）
# -------------------------------------------------

def schema_to_trader_strategy_version_orm(
    schema: StrategyVersion,
    orm_record: "TraderStrategyVersion",
) -> "TraderStrategyVersion":
    """将 StrategyVersion dataclass 写入 TraderStrategyVersion ORM 实例。

    完整 payload 存入 strategy_payload JSONB 列，ORM 列保留关键索引字段。
    """
    orm_record.trader_id = schema.trader_id
    orm_record.strategy_date = schema.strategy_date
    orm_record.version_name = schema.version_id  # version_id 作为 version_name
    orm_record.status = schema.status.value if hasattr(schema.status, "value") else schema.status
    orm_record.released_at = schema.released_at
    orm_record.source_article_ids = schema.source_article_ids
    orm_record.evidence_refs = schema.evidence_refs
    orm_record.notes = schema.notes
    orm_record.strategy_payload = {
        "version_id": schema.version_id,
        "recommendations": _serialize_complex(schema.recommendations),
        "rules_snapshot": _serialize_complex(schema.rules_snapshot),
    }
    return orm_record


def orm_to_schema_strategy_version(orm_record: "TraderStrategyVersion") -> "StrategyVersion":
    """从 TraderStrategyVersion ORM 实例重建 StrategyVersion dataclass。"""
    from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus

    payload = orm_record.strategy_payload or {}
    return StrategyVersion(
        version_id=payload.get("version_id", orm_record.version_name),
        trader_id=orm_record.trader_id,
        strategy_date=orm_record.strategy_date,
        status=StrategyVersionStatus(orm_record.status),
        recommendations=payload.get("recommendations", []),
        source_article_ids=orm_record.source_article_ids or [],
        evidence_refs=orm_record.evidence_refs or [],
        notes=orm_record.notes,
        released_at=orm_record.released_at,
        rules_snapshot=payload.get("rules_snapshot", []),
    )


# -------------------------------------------------
# EvidencePack 转换
# -------------------------------------------------

def schema_to_evidence_pack_dict(schema: EvidencePack) -> dict[str, Any]:
    """将 EvidencePack dataclass 序列化为 dict，供 JSONB 存储或文件持久化。

    对应 EvidencePack.to_dict()，保留完整结构供回放。
    """
    return schema.to_dict()


def orm_to_schema_evidence_pack(data: dict[str, Any]) -> "EvidencePack":
    """从 dict 重建 EvidencePack dataclass。"""
    from src.evaluation.evidence_pack import EvidencePack
    return EvidencePack.from_dict(data)
