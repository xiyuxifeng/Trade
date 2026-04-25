"""Ranking Service：盘后 ranking 多级排序服务。

职责：
  - 接收 postmortem 结果，生成 ranking 条目并持久化
  - 支持批量生成 ranking（计算组内 rank）
  - 支持 postmortem 修正后的同步更新（update_entry）
  - 提供嵌套视图和扁平视图两种输出格式

NTL-S5-004
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from uuid import UUID

if TYPE_CHECKING:
    from src.evaluation.postmortem_service import PostmortemResult
    from src.evaluation.evidence_pack import EvidencePack


@dataclass
class RankingEntry:
    """单条 ranking 条目（内存结构，对应 RankingEntryRecord）。

    排序规则：
      1. 先按 return_pct 降序
      2. return_pct 相同时按 (mfe - mae) 降序（赔率优选）
      3. return_pct 为 None 的排在最后，组内按赔率排序
    """
    entry_id: UUID
    trade_date: str
    trader_id: str
    strategy_version_id: str
    symbol: str

    # 排序指标
    return_pct: float | None
    mfe: float | None
    mae: float | None

    # 复合分（用于调试和对账）
    composite_score: float | None

    # 排序结果（generate_ranking 时填充）
    rank: int | None

    # 版本状态
    is_latest: bool

    # 来源追踪
    idea_id: UUID | None
    attribution_source: str

    extra: dict = field(default_factory=dict)

    @classmethod
    def from_record(cls, record) -> "RankingEntry":
        """从 ORM record 构建内存 dataclass。"""
        return cls(
            entry_id=record.entry_id,
            trade_date=record.trade_date,
            trader_id=record.trader_id,
            strategy_version_id=record.strategy_version_id,
            symbol=record.symbol,
            return_pct=record.return_pct,
            mfe=record.mfe,
            mae=record.mae,
            composite_score=record.composite_score,
            rank=record.rank,
            is_latest=record.is_latest,
            idea_id=record.idea_id,
            attribution_source=record.attribution_source,
            extra=record.extra or {},
        )


def _compute_composite(return_pct: float | None, mfe: float | None, mae: float | None) -> float | None:
    """计算复合分。用于调试和对账，不影响排序逻辑（排序用 return_pct + 赔率直接计算）。"""
    if return_pct is None:
        return None
    odds_bonus = max(0.0, (mfe or 0) - (mae or 0))
    return return_pct + odds_bonus


def _sort_key(entry: RankingEntry) -> tuple:
    """返回用于排序的 key tuple。"""
    if entry.return_pct is None:
        # None 排最后，组内按赔率排序
        odds = max(0.0, (entry.mfe or 0) - (entry.mae or 0))
        return (1, -odds)  # (1, ...) 表示 None 排在后面
    else:
        odds = max(0.0, (entry.mfe or 0) - (entry.mae or 0))
        return (0, -entry.return_pct, -odds)  # (0, return_pct desc, odds desc)