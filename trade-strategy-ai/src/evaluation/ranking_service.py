"""Ranking Service：盘后 ranking 多级排序服务。

职责：
  - 接收 postmortem 结果，生成 ranking 条目并持久化
  - 支持批量生成 ranking（计算组内 rank）
  - 支持 postmortem 修正后的同步更新（update_entry）
  - 提供嵌套视图和扁平视图两种输出格式

NTL-S5-004
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
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


# -------------------------------------------------
# RankingService（add_entry / generate_ranking / update_entry）
# -------------------------------------------------

from uuid import uuid4 as _uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.evaluation.ranking_repository import RankingRepository
from src.models.ranking_entry import RankingEntryRecord


class RankingService:
    """盘后 ranking service。

    职责：
      - 接收 postmortem 结果和 evidence pack，生成 ranking 条目并持久化
      - 支持批量生成 ranking（计算组内 rank）
      - 支持 postmortem 修正后的同步更新
      - 提供嵌套视图和扁平视图两种输出格式
    """

    def __init__(self, session: AsyncSession, output_dir: Path | None = None):
        self.session = session
        self._repo = RankingRepository(session)
        self._output_dir = output_dir or Path(".")

    def _entry_from_postmortem_and_pack(
        self,
        postmortem,
        evidence_pack,
    ):
        """从 postmortem 结果和 evidence pack 构建 RankingEntry。

        从 evidence_pack 提取：
          - trade_date（从 TradeIdea.as_of_date）
          - trader_id（从 signal_context 或 TradeIdea）
          - strategy_version_id
          - symbol（从 TradeIdea）

        从 postmortem 提取：
          - return_pct / mfe / mae
          - attribution_source
        """
        # 从 evidence_pack 提取基本信息
        trade_date = evidence_pack.trade_date
        strategy_version_id = evidence_pack.strategy_version_id or ""
        symbol = ""

        # 从 trade_idea 提取 symbol
        if evidence_pack.trade_idea and hasattr(evidence_pack.trade_idea, "symbol"):
            symbol = evidence_pack.trade_idea.symbol or ""

        # 从 signal_context 提取 trader_id（如果有）
        trader_id = ""
        if evidence_pack.signal_context and hasattr(evidence_pack.signal_context, "trader_id"):
            trader_id = evidence_pack.signal_context.trader_id or ""

        # 如果 signal_context 没有 trader_id，尝试从 trade_idea 提取
        if not trader_id and evidence_pack.trade_idea and hasattr(evidence_pack.trade_idea, "trader_id"):
            trader_id = evidence_pack.trade_idea.trader_id or ""

        # 从 postmortem 提取指标
        return_pct = postmortem.return_pct
        mfe_val = postmortem.mfe
        mae_val = postmortem.mae

        composite = _compute_composite(return_pct, mfe_val, mae_val)

        return RankingEntry(
            entry_id=_uuid4(),
            trade_date=trade_date,
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            symbol=symbol,
            return_pct=return_pct,
            mfe=mfe_val,
            mae=mae_val,
            composite_score=composite,
            rank=None,  # add_entry 时不计算 rank
            is_latest=True,
            idea_id=postmortem.idea_id,
            attribution_source=postmortem.attribution_source,
            extra={},
        )

    async def add_entry(self, postmortem, evidence_pack) -> RankingEntry:
        """接收一个 postmortem 结果，生成并持久化一条 ranking 条目。

        rank 字段在 add_entry 时为 None，由 generate_ranking() 批量计算。
        同一 (trade_date, strategy_version_id, symbol) 已存在时，
        旧 entry 被标记为 is_latest=False，新 entry 的 is_latest=True。

        Args:
            postmortem: 盘后复盘结果
            evidence_pack: 交易证据包

        Returns:
            新建的 RankingEntry
        """
        entry = self._entry_from_postmortem_and_pack(postmortem, evidence_pack)
        record = await self._repo.upsert(entry)
        return RankingEntry.from_record(record)

    async def add_entry_from_metrics(
        self,
        evidence_pack: "EvidencePack",
        mfe: float,
        mae: float,
        return_pct: float,
    ) -> RankingEntry:
        """从 metrics 计算结果生成 ranking 条目（NTL-S5-011）。

        用于 run_after_close 场景：此时没有完整的 PostmortemResult，
        但 ranking 数据（mfe/mae/return_pct）在 EvidencePack 生成时就能算出来。

        attribution_source 固定为 "auto"，因为 run_after_close
        没有 LLM validator 参与归因。

        与 add_entry(postmortem, pack) 的区别：
        - add_entry：需要 PostmortemResult（由 PostmortemService.generate() 产生）
        - add_entry_from_metrics：直接接收 metrics 结果，不需要 PostmortemService

        Args:
            evidence_pack: 当前 idea 的 EvidencePack
            mfe: Maximum Favorable Excursion
            mae: Maximum Adverse Excursion
            return_pct: 收益率（%）

        Returns:
            新建的 RankingEntry
        """
        # 从 evidence_pack 提取基本信息
        trade_date = evidence_pack.trade_date
        strategy_version_id = evidence_pack.strategy_version_id or ""
        symbol = ""
        trader_id = ""

        # 从 trade_idea 提取 symbol 和 trader_id
        if evidence_pack.trade_idea:
            if hasattr(evidence_pack.trade_idea, "symbol"):
                symbol = evidence_pack.trade_idea.symbol or ""
            if hasattr(evidence_pack.trade_idea, "trader_id"):
                trader_id = evidence_pack.trade_idea.trader_id or ""

        # 从 signal_context 提取 trader_id（如果 trade_idea 没有）
        if not trader_id and evidence_pack.signal_context:
            if hasattr(evidence_pack.signal_context, "trader_id"):
                trader_id = evidence_pack.signal_context.trader_id or ""

        composite = _compute_composite(return_pct, mfe, mae)

        entry = RankingEntry(
            entry_id=_uuid4(),
            trade_date=trade_date,
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            symbol=symbol,
            return_pct=return_pct,
            mfe=mfe,
            mae=mae,
            composite_score=composite,
            rank=None,  # add_entry 时不计算 rank
            is_latest=True,
            idea_id=evidence_pack.idea_id,
            attribution_source="auto",  # run_after_close 无 LLM
            extra={},
        )

        record = await self._repo.upsert(entry)
        return RankingEntry.from_record(record)

    async def generate_ranking(
        self,
        trade_date: str,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
        view: Literal["nested", "flat"] = "nested",
    ) -> dict | list:
        """批量生成并更新指定日期的 ranking（计算 rank）。

        调用时机：当日所有 add_entry 完成后（NTL-S5-011 盘后流程末尾）。

        排序规则：
          1. return_pct 降序
          2. return_pct 相同时按 (mfe - mae) 降序
          3. return_pct 为 None 的排在最后，组内按赔率排序

        Args:
            trade_date: 交易日期（YYYY-MM-DD）
            trader_id: 可选，限定 trader
            strategy_version_id: 可选，限定策略版本
            view: "nested"（默认，嵌套字典）| "flat"（扁平列表）

        Returns:
            nested view: {trader_id: {strategy_version_id: [RankingEntry...]}}
            flat view: [RankingEntry...]（先按 trader 分组，组内按 composite_score 排序）
        """
        # 查询所有 latest entry
        records = await self._repo.query_by_date(
            trade_date=trade_date,
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            is_latest_only=True,
        )

        entries = [RankingEntry.from_record(r) for r in records]

        # 按 (trader_id, strategy_version_id) 分组
        groups: dict[str, dict[str, list[RankingEntry]]] = {}
        for entry in entries:
            groups.setdefault(entry.trader_id, {})
            groups[entry.trader_id].setdefault(entry.strategy_version_id, [])
            groups[entry.trader_id][entry.strategy_version_id].append(entry)

        # 在每个组内排序并计算 rank
        all_entries_with_rank: list[RankingEntry] = []
        for trader_id_key, versions in groups.items():
            for version_id, version_entries in versions.items():
                # 排序
                sorted_entries = sorted(version_entries, key=_sort_key)
                # 计算组内 rank（从 1 开始）
                ranked_entries = []
                for rank_idx, e in enumerate(sorted_entries, start=1):
                    e.rank = rank_idx
                    ranked_entries.append(e)
                all_entries_with_rank.extend(ranked_entries)

        # 更新 DB 中的 rank
        if all_entries_with_rank:
            entry_ids = [e.entry_id for e in all_entries_with_rank]
            ranks = [e.rank for e in all_entries_with_rank]
            await self._repo.update_rank(entry_ids, ranks)

        # 生成视图
        if view == "flat":
            # flat view：先按 trader 分组，组内按 composite_score 排序
            flat_list: list[RankingEntry] = []
            for t_id in sorted(groups.keys()):
                trader_entries: list[RankingEntry] = []
                for v_id in sorted(groups[t_id].keys()):
                    trader_entries.extend(sorted(
                        groups[t_id][v_id],
                        key=lambda e: (-(e.composite_score or 0)),
                    ))
                flat_list.extend(trader_entries)
            return flat_list
        else:
            # nested view：{trader_id: {strategy_version_id: [entries...]}}
            return groups

    async def generate_ranking_and_save(
        self,
        trade_date: str,
        trader_id: str | None = None,
        strategy_version_id: str | None = None,
    ) -> dict:
        """生成 ranking 并持久化到文件（NTL-S5-011）。

        调用链路：run_after_close 末尾 -> add_entry_from_metrics() -> 本方法

        文件路径：{output_dir}/rankings/{trade_date}.json

        排序规则（来自 generate_ranking）：
          1. return_pct 降序
          2. return_pct 相同时按 (mfe - mae) 降序
          3. return_pct 为 None 的排在最后

        Args:
            trade_date: 交易日期（YYYY-MM-DD）
            trader_id: 可选，限定 trader
            strategy_version_id: 可选，限定策略版本

        Returns:
            dict: 包含 nested 和 flat 两种视图的完整结果
        """
        # 生成 nested view（generate_ranking 会更新 DB 中的 rank）
        nested = await self.generate_ranking(
            trade_date=trade_date,
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            view="nested",
        )

        # 生成 flat view
        flat = await self.generate_ranking(
            trade_date=trade_date,
            trader_id=trader_id,
            strategy_version_id=strategy_version_id,
            view="flat",
        )

        result = {
            "trade_date": trade_date,
            "generated_at": datetime.now(UTC).isoformat(),
            "nested": nested,
            "flat": flat,
        }

        # 写入文件
        ranking_dir = self._output_dir / "rankings"
        ranking_dir.mkdir(parents=True, exist_ok=True)
        ranking_file = ranking_dir / f"{trade_date}.json"

        with open(ranking_file, "w") as f:
            json.dump(result, f, indent=2, default=str)

        return result

    async def update_entry(self, entry_id: UUID, postmortem) -> RankingEntry | None:
        """当 postmortem 被 LLM 修正时，同步更新对应的 ranking 条目。

        实现逻辑：
          1. 查找 entry_id 对应的 record
          2. 标记旧 entry.is_latest=False
          3. 写入新 entry（is_latest=True，rank=None）

        Args:
            entry_id: 被修正的 entry ID
            postmortem: 更新后的 postmortem 结果

        Returns:
            更新后的 RankingEntry，或 None（未找到）
        """
        # 查找旧 record
        stmt = select(RankingEntryRecord).where(RankingEntryRecord.entry_id == entry_id)
        result = await self.session.execute(stmt)
        old_record = result.scalar_one_or_none()

        if old_record is None:
            return None

        # 标记旧 entry 为非最新
        old_record.is_latest = False

        # 从 postmortem 提取更新的指标
        return_pct = postmortem.return_pct
        mfe_val = postmortem.mfe
        mae_val = postmortem.mae

        # 创建新 entry（基于旧的 key + 更新的指标）
        new_entry = RankingEntry(
            entry_id=_uuid4(),
            trade_date=old_record.trade_date,
            trader_id=old_record.trader_id,
            strategy_version_id=old_record.strategy_version_id,
            symbol=old_record.symbol,
            return_pct=return_pct,
            mfe=mfe_val,
            mae=mae_val,
            composite_score=_compute_composite(return_pct, mfe_val, mae_val),
            rank=None,  # 下次 generate_ranking 重新计算
            is_latest=True,
            idea_id=postmortem.idea_id,
            attribution_source=postmortem.attribution_source,
            extra={"corrected_from": str(entry_id)},
        )

        new_record = await self._repo.upsert(new_entry)
        return RankingEntry.from_record(new_record)

    def get_latest_by_version(self, version_id: str) -> list[RankingEntry]:
        """获取指定策略版本的最新 ranking 条目（is_latest=True）。

        Note: 同步封装（用于不需要 async 的场景）。
        """
        import asyncio
        return asyncio.run(self._repo.get_latest_by_version(version_id))

    def get_by_trader(self, trader_id: str, trade_date: str | None = None) -> list[RankingEntry]:
        """获取指定 trader 的 ranking 条目列表。

        Note: 同步封装。
        """
        import asyncio
        return asyncio.run(
            self._repo.query_by_date(
                trade_date or "", trader_id=trader_id, is_latest_only=True
            )
        )