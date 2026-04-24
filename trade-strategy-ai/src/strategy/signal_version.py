"""信号版本控制 - P4-005"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.strategy.types import Signal, SignalContext, SignalWithContext


class SignalVersioning:
    """信号版本控制

    记录信号生成过程中的所有输入和决策，支持回放和审计。
    """

    def __init__(self, storage_path: Path | None = None):
        self._storage_path = storage_path or Path("data/signals")
        self._versions: dict[str, SignalWithContext] = {}

    def record(self, signal: Signal, context: SignalContext) -> str:
        """记录信号及其上下文

        Args:
            signal: 信号
            context: 上下文

        Returns:
            版本 ID
        """
        version_id = signal.signal_id

        # 内存存储
        self._versions[version_id] = SignalWithContext(
            signal=signal,
            context=context,
        )

        # 持久化到文件
        if self._storage_path:
            self._storage_path.mkdir(parents=True, exist_ok=True)
            file_path = self._storage_path / f"{version_id}.json"
            data = {
                "signal": self._signal_to_dict(signal),
                "context": self._context_to_dict(context),
            }
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

        return version_id

    def get_version(self, signal_id: str) -> SignalWithContext | None:
        """获取信号完整版本

        Args:
            signal_id: 信号 ID

        Returns:
            SignalWithContext 或 None
        """
        # 优先从内存获取
        if signal_id in self._versions:
            return self._versions[signal_id]

        # 从文件加载
        if self._storage_path:
            file_path = self._storage_path / f"{signal_id}.json"
            if file_path.exists():
                with open(file_path) as f:
                    data = json.load(f)
                return SignalWithContext(
                    signal=self._dict_to_signal(data["signal"]),
                    context=self._dict_to_context(data["context"]),
                )

        return None

    def list_versions(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SignalWithContext]:
        """列出信号版本

        Args:
            symbol: 按标的过滤
            since: 按时间过滤
            limit: 返回数量限制

        Returns:
            SignalWithContext 列表
        """
        results = []

        # 从内存过滤
        for v in self._versions.values():
            if symbol and v.signal.symbol != symbol:
                continue
            if since and v.context.timestamp < since:
                continue
            results.append(v)

        # 按时间倒序
        results.sort(key=lambda x: x.context.timestamp, reverse=True)

        return results[:limit]

    def _signal_to_dict(self, signal: Signal) -> dict[str, Any]:
        """信号转字典"""
        return {
            "signal_id": signal.signal_id,
            "symbol": signal.symbol,
            "side": signal.side.value if hasattr(signal.side, "value") else signal.side,
            "confidence": signal.confidence,
            "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
            "triggered_rules": signal.triggered_rules,
            "synthesis_mode": signal.synthesis_mode.value if signal.synthesis_mode else None,
            "entry_price": {
                "type": signal.entry_price.type if signal.entry_price else None,
                "value": signal.entry_price.value if signal.entry_price else None,
            } if signal.entry_price else None,
            "position_size": {
                "type": signal.position_size.type.value if signal.position_size else None,
                "value": signal.position_size.value if signal.position_size else None,
            } if signal.position_size else None,
            "version": signal.version,
            "strategy_version_id": signal.strategy_version_id,  # NTL-S4-004
            "metadata": signal.metadata,
        }

    def _context_to_dict(self, context: SignalContext) -> dict[str, Any]:
        """上下文转字典"""
        return {
            "features_snapshot": context.features_snapshot,
            "market_state": context.market_state,
            "rules_snapshot": context.rules_snapshot,
            "timestamp": context.timestamp.isoformat() if context.timestamp else None,
            "strategy_version_id": context.strategy_version_id,  # NTL-S4-004
            "market_universe_snapshot": context.market_universe_snapshot,  # NTL-S4-004
            "topic_source_ids": context.topic_source_ids,  # NTL-S4-004
        }

    def _dict_to_signal(self, data: dict) -> Signal:
        """字典转信号"""
        from src.strategy.types import SignalSide, SynthesisMode, PriceSpec, PositionSize, PositionSizeType

        return Signal(
            signal_id=data["signal_id"],
            symbol=data["symbol"],
            side=SignalSide(data["side"]) if data["side"] else SignalSide.HOLD,
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data["timestamp"] else datetime.now(),
            triggered_rules=data["triggered_rules"],
            synthesis_mode=SynthesisMode(data["synthesis_mode"]) if data["synthesis_mode"] else None,
            entry_price=PriceSpec(**data["entry_price"]) if data["entry_price"] else None,
            position_size=PositionSize(**data["position_size"]) if data["position_size"] else None,
            version=data.get("version", "v1"),
            strategy_version_id=data.get("strategy_version_id"),  # NTL-S4-004
            metadata=data.get("metadata", {}),
        )

    def _dict_to_context(self, data: dict) -> SignalContext:
        """字典转上下文"""
        return SignalContext(
            features_snapshot=data["features_snapshot"],
            market_state=data["market_state"],
            rules_snapshot=data["rules_snapshot"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data["timestamp"] else datetime.now(),
            strategy_version_id=data.get("strategy_version_id"),  # NTL-S4-004
            market_universe_snapshot=data.get("market_universe_snapshot"),  # NTL-S4-004
            topic_source_ids=data.get("topic_source_ids", []),  # NTL-S4-004
        )