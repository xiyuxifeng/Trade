"""候选池快照服务。

职责：
- 统一管理 MarketUniverse 快照的写入、读取、列表、删除
- 使用文件系统作为存储后端（data/market_universe/snapshots/）
- 为后续 pipeline 接入提供稳定入口
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from src.common.logger import get_logger
from src.market_universe.schemas import MarketUniverse

logger = get_logger(__name__)


def generate_canonical_topic_tags(
    hot_topics: list[dict],
    topic_constituents: dict[str, list[str]],
    target_symbols: list[str] | None = None,
) -> list[str]:
    """
    统一生成 canonical topic tags。

    双重校验逻辑：
    1. topic_id 必须在 hot_topics 中存在（确保是热点话题）
    2. topic 的 constituents 必须包含至少一个 target_symbol（如果有 target_symbols）

    S10-010: 统一 source_topic_ids tag 生成逻辑

    Args:
        hot_topics: 热点话题列表，每项包含 topic_id
        topic_constituents: 话题成分映射 {topic_id: [symbols]}
        target_symbols: 目标交易标的可选列表

    Returns:
        符合条件的 topic_id 列表
    """
    if not hot_topics:
        return []

    hot_topic_ids = {t["topic_id"] for t in hot_topics if "topic_id" in t}

    canonical_tags = []
    for topic_id, constituents in topic_constituents.items():
        # 校验1: topic_id 必须在 hot_topics 中
        if topic_id not in hot_topic_ids:
            continue

        # 校验2: 如果指定了 target_symbols，必须至少有一个在 constituents 中
        if target_symbols:
            if not any(sym in constituents for sym in target_symbols):
                continue

        canonical_tags.append(topic_id)

    return canonical_tags


class SnapshotService:
    """管理候选池快照的持久化。"""

    def __init__(self, base_dir: str | None = None) -> None:
        """初始化快照服务。

        Args:
            base_dir: 快照存储根目录，默认为 data/market_universe/snapshots/
        """
        if base_dir is None:
            base_dir = "data/market_universe/snapshots"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _snapshot_path(self, trade_date: str, slot: str) -> Path:
        """获取指定日期和时段的快照文件路径。"""
        return self.base_dir / trade_date / f"{slot}.json"

    def _ensure_dir(self, path: Path) -> None:
        """确保目录存在。"""
        path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, market_universe: MarketUniverse) -> None:
        """保存 MarketUniverse 快照。

        Args:
            market_universe: 要保存的 MarketUniverse 实例
        """
        path = self._snapshot_path(market_universe.trade_date, market_universe.slot)
        self._ensure_dir(path)

        # 将 dataclass 转为 dict（dataclass 是 frozen 的，直接转换）
        payload = {
            "trade_date": market_universe.trade_date,
            "slot": market_universe.slot,
            "fetched_at": market_universe.fetched_at.isoformat() if market_universe.fetched_at else None,
            "metadata": market_universe.metadata,
        }

        # 序列化 payload
        data: dict = {
            "trade_date": payload["trade_date"],
            "slot": payload["slot"],
            "fetched_at": payload["fetched_at"],
            "metadata": payload["metadata"],
        }

        if market_universe.hot_topics is not None:
            data["hot_topics"] = {
                "trade_date": market_universe.hot_topics.trade_date,
                "slot": market_universe.hot_topics.slot,
                "sources": market_universe.hot_topics.sources,
                "fetched_at": market_universe.hot_topics.fetched_at.isoformat() if market_universe.hot_topics.fetched_at else None,
                "topics": [
                    {
                        "kind": t.kind,
                        "topic_id": t.topic_id,
                        "topic_name": t.topic_name,
                        "score": t.score,
                        "increase_pct": t.increase_pct,
                        "speed_pct": t.speed_pct,
                        "turnover": t.turnover,
                        "net_inflow": t.net_inflow,
                    }
                    for t in market_universe.hot_topics.topics
                ],
            }

        if market_universe.topic_constituents is not None:
            data["topic_constituents"] = {
                "trade_date": market_universe.topic_constituents.trade_date,
                "slot": market_universe.topic_constituents.slot,
                "sources": market_universe.topic_constituents.sources,
                "fetched_at": market_universe.topic_constituents.fetched_at.isoformat() if market_universe.topic_constituents.fetched_at else None,
                "constituents": [
                    {
                        "kind": c.kind,
                        "topic_id": c.topic_id,
                        "topic_name": c.topic_name,
                        "symbol": c.symbol,
                        "name": c.name,
                        "topic_change_pct": c.topic_change_pct,
                        "leader_symbol": c.leader_symbol,
                        "leader_name": c.leader_name,
                        "leader_change_pct": c.leader_change_pct,
                        "board_num": c.board_num,
                        "net_buy": c.net_buy,
                        "brief_intro": c.brief_intro,
                    }
                    for c in market_universe.topic_constituents.constituents
                ],
            }

        if market_universe.strong_symbols is not None:
            data["strong_symbols"] = {
                "trade_date": market_universe.strong_symbols.trade_date,
                "slot": market_universe.strong_symbols.slot,
                "sources": market_universe.strong_symbols.sources,
                "fetched_at": market_universe.strong_symbols.fetched_at.isoformat() if market_universe.strong_symbols.fetched_at else None,
                "symbols": [
                    {
                        "kind": s.kind,
                        "symbol": s.symbol,
                        "name": s.name,
                        "strength_score": s.strength_score,
                        "change_pct": s.change_pct,
                        "turnover": s.turnover,
                        "turnover_ratio": s.turnover_ratio,
                        "return_pct": s.return_pct,
                        "net_inflow": s.net_inflow,
                        "main_force_buy": s.main_force_buy,
                        "main_force_sell": s.main_force_sell,
                        "rt_change_pct": s.rt_change_pct,
                        "bid_net": s.bid_net,
                        "bid_turnover": s.bid_turnover,
                        "topic_tags": s.topic_tags,
                    }
                    for s in market_universe.strong_symbols.symbols
                ],
            }

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, trade_date: str, slot: str) -> MarketUniverse | None:
        """加载指定日期和时段的快照。

        Args:
            trade_date: 交易日期（ISO 格式）
            slot: 时段标识

        Returns:
            MarketUniverse 实例，若不存在则返回 None
        """
        path = self._snapshot_path(trade_date, slot)
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return self._deserialize(data)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
            logger.warning("快照文件损坏或格式不合法，已跳过读取: path=%s error=%s", path, exc)
            return None

    def _deserialize(self, data: dict) -> MarketUniverse:
        """将 JSON 数据反序列化为 MarketUniverse。"""
        from src.market_universe.schemas import (
            HotTopic, HotTopicsPayload,
            TopicConstituent, TopicConstituentsPayload,
            StrongSymbol, StrongSymbolsPayload,
        )

        hot_topics = None
        if "hot_topics" in data and data["hot_topics"] is not None:
            ht_data = data["hot_topics"]
            hot_topics = HotTopicsPayload(
                trade_date=ht_data["trade_date"],
                slot=ht_data["slot"],
                sources=ht_data.get("sources", []),
                fetched_at=datetime.fromisoformat(ht_data["fetched_at"]) if ht_data.get("fetched_at") else None,
                topics=[
                    HotTopic(
                        kind=t["kind"],
                        topic_id=t["topic_id"],
                        topic_name=t["topic_name"],
                        score=t.get("score"),
                        increase_pct=t.get("increase_pct"),
                        speed_pct=t.get("speed_pct"),
                        turnover=t.get("turnover"),
                        net_inflow=t.get("net_inflow"),
                    )
                    for t in ht_data.get("topics", [])
                ],
            )

        topic_constituents = None
        if "topic_constituents" in data and data["topic_constituents"] is not None:
            tc_data = data["topic_constituents"]
            topic_constituents = TopicConstituentsPayload(
                trade_date=tc_data["trade_date"],
                slot=tc_data["slot"],
                sources=tc_data.get("sources", []),
                fetched_at=datetime.fromisoformat(tc_data["fetched_at"]) if tc_data.get("fetched_at") else None,
                constituents=[
                    TopicConstituent(
                        kind=c["kind"],
                        topic_id=c.get("topic_id"),
                        topic_name=c.get("topic_name"),
                        symbol=c.get("symbol"),
                        name=c.get("name"),
                        topic_change_pct=c.get("topic_change_pct"),
                        leader_symbol=c.get("leader_symbol"),
                        leader_name=c.get("leader_name"),
                        leader_change_pct=c.get("leader_change_pct"),
                        board_num=c.get("board_num"),
                        net_buy=c.get("net_buy"),
                        brief_intro=c.get("brief_intro"),
                    )
                    for c in tc_data.get("constituents", [])
                ],
            )

        strong_symbols = None
        if "strong_symbols" in data and data["strong_symbols"] is not None:
            ss_data = data["strong_symbols"]
            strong_symbols = StrongSymbolsPayload(
                trade_date=ss_data["trade_date"],
                slot=ss_data["slot"],
                sources=ss_data.get("sources", []),
                fetched_at=datetime.fromisoformat(ss_data["fetched_at"]) if ss_data.get("fetched_at") else None,
                symbols=[
                    StrongSymbol(
                        kind=s["kind"],
                        symbol=s.get("symbol"),
                        name=s.get("name"),
                        strength_score=s.get("strength_score"),
                        change_pct=s.get("change_pct"),
                        turnover=s.get("turnover"),
                        turnover_ratio=s.get("turnover_ratio"),
                        return_pct=s.get("return_pct"),
                        net_inflow=s.get("net_inflow"),
                        main_force_buy=s.get("main_force_buy"),
                        main_force_sell=s.get("main_force_sell"),
                        rt_change_pct=s.get("rt_change_pct"),
                        bid_net=s.get("bid_net"),
                        bid_turnover=s.get("bid_turnover"),
                        topic_tags=s.get("topic_tags"),
                    )
                    for s in ss_data.get("symbols", [])
                ],
            )

        return MarketUniverse(
            trade_date=data["trade_date"],
            slot=data["slot"],
            hot_topics=hot_topics,
            topic_constituents=topic_constituents,
            strong_symbols=strong_symbols,
            fetched_at=datetime.fromisoformat(data["fetched_at"]) if data.get("fetched_at") else None,
            metadata=data.get("metadata", {}),
        )

    def list_snapshots(self, trade_date_start: str, trade_date_end: str) -> list[MarketUniverse]:
        """列出指定日期范围内的所有快照。

        Args:
            trade_date_start: 开始日期（包含）
            trade_date_end: 结束日期（包含）

        Returns:
            MarketUniverse 实例列表，按日期排序
        """
        results: list[MarketUniverse] = []

        if not self.base_dir.exists():
            return results

        for date_dir in sorted(self.base_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            trade_date = date_dir.name
            if trade_date < trade_date_start or trade_date > trade_date_end:
                continue

            for slot_file in sorted(date_dir.iterdir()):
                if slot_file.suffix != ".json":
                    continue
                slot = slot_file.stem
                mu = self.load(trade_date, slot)
                if mu is not None:
                    results.append(mu)

        return results

    def delete(self, trade_date: str, slot: str) -> bool:
        """删除指定快照。

        Args:
            trade_date: 交易日期
            slot: 时段标识

        Returns:
            删除成功返回 True，文件不存在返回 False
        """
        path = self._snapshot_path(trade_date, slot)
        if not path.exists():
            return False
        path.unlink()
        # 尝试删除空目录
        try:
            date_dir = path.parent
            if date_dir.exists() and not any(date_dir.iterdir()):
                date_dir.rmdir()
        except OSError:
            pass
        return True
