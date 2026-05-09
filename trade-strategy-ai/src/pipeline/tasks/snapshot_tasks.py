"""候选池快照 pipeline tasks（NTL-S2-020 ~ NTL-S2-022）。

提供三个 pipeline handler：
- handle_hot_topics_snapshot: 热点快照构建与保存
- handle_topic_constituents_snapshot: 题材成分快照构建与保存
- handle_strong_symbols_snapshot: 强势池快照构建与保存
"""
from __future__ import annotations

from datetime import date
from typing import Any

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.common.paths import resolve_project_path
from src.market_universe.hot_topics_builder import HotTopicsBuilder
from src.market_universe.constituents_resolver import ConstituentsResolver
from src.market_universe.strong_symbols_selector import StrongSymbolsSelector
from src.market_universe.snapshot_service import SnapshotService
from src.market_universe.schemas import MarketUniverse

logger = get_logger(__name__)


def _build_provider(config: AppConfig, *, offline: bool = False):
    """构建 KaipanProvider 实例（懒加载）。

    offline 模式下不要求 kaipan 配置存在，因为不需要发起网络请求。
    """
    kaipan_cfg = getattr(config, "kaipan", None)
    if kaipan_cfg is None and not offline:
        return None

    from src.providers.kaipan_provider import KaipanAuth, KaipanProvider

    data_root = resolve_project_path("data/kaipan")
    auth = KaipanAuth()
    try:
        return KaipanProvider(
            auth=auth,
            raw_dir=data_root / "raw",
            normalized_dir=data_root / "snapshots",
            snapshots_dir=data_root / "snapshots",
            kaipan_config=kaipan_cfg,
        )
    except Exception:  # noqa: BLE001
        return None


async def handle_hot_topics_snapshot(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """热点快照构建与保存。

    details 期望字段：
        trade_date: str（ISO 格式，如 "2026-04-23"）
        slot: str（如 "17-30"）
        force: bool（是否强制覆盖）
    """
    trade_date_str = details.get("trade_date")
    slot = details.get("slot", "17-30")
    force = details.get("force", False)
    offline = details.get("offline", False)

    if not trade_date_str:
        raise ValueError("trade_date is required for hot_topics_snapshot")

    trade_date = date.fromisoformat(trade_date_str)
    provider = _build_provider(config, offline=offline)

    # 如果没有 provider，跳过
    if provider is None:
        logger.warning(
            "热点快照跳过: date=%s, slot=%s, 原因=kaipan配置缺失",
            trade_date_str,
            slot,
        )
        return

    # 加载已有快照，若存在且非 force 则跳过
    snapshot_service = SnapshotService()
    existing = snapshot_service.load(trade_date_str, slot)
    if existing is not None and existing.hot_topics is not None and not force:
        # 已存在，跳过
        logger.debug("热点快照跳过（已存在）: date=%s, slot=%s", trade_date_str, slot)
        return

    try:
        raw_payload = provider.fetch_hot_topics(trade_date=trade_date, slot=slot, offline=offline)
        logger.info(
            "热点快照获取成功: date=%s, slot=%s, topics=%d",
            trade_date_str,
            slot,
            len(raw_payload) if raw_payload else 0,
        )
    except Exception as e:
        logger.warning(
            "热点快照获取失败: date=%s, slot=%s, error=%s",
            trade_date_str,
            slot,
            e,
        )
        raise

    builder = HotTopicsBuilder()
    hot_topics_payload = builder.build(raw_payload)

    # 合并到已有 MarketUniverse 或新建
    if existing is not None:
        mu = MarketUniverse(
            trade_date=trade_date_str,
            slot=slot,
            hot_topics=hot_topics_payload,
            topic_constituents=existing.topic_constituents,
            strong_symbols=existing.strong_symbols,
            metadata=existing.metadata,
        )
    else:
        mu = MarketUniverse(
            trade_date=trade_date_str,
            slot=slot,
            hot_topics=hot_topics_payload,
        )

    snapshot_service.save(mu)
    logger.info(
        "热点快照已保存: date=%s, slot=%s, topics=%d",
        trade_date_str,
        slot,
        len(hot_topics_payload.topics) if hot_topics_payload else 0,
    )


async def handle_topic_constituents_snapshot(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """题材成分快照构建与保存。

    details 期望字段：
        trade_date: str（ISO 格式）
        slot: str（如 "17-30"）
        force: bool（是否强制覆盖）
    """
    trade_date_str = details.get("trade_date")
    slot = details.get("slot", "17-30")
    force = details.get("force", False)
    offline = details.get("offline", False)

    if not trade_date_str:
        raise ValueError("trade_date is required for topic_constituents_snapshot")

    trade_date = date.fromisoformat(trade_date_str)
    provider = _build_provider(config, offline=offline)

    if provider is None:
        logger.warning(
            "题材成分快照跳过: date=%s, slot=%s, 原因=kaipan配置缺失",
            trade_date_str,
            slot,
        )
        return

    snapshot_service = SnapshotService()
    existing = snapshot_service.load(trade_date_str, slot)
    if existing is not None and existing.topic_constituents is not None and not force:
        logger.debug("题材成分快照跳过（已存在）: date=%s, slot=%s", trade_date_str, slot)
        return

    try:
        raw_payload = provider.fetch_topic_constituents(trade_date=trade_date, slot=slot, offline=offline)
        logger.info(
            "题材成分快照获取成功: date=%s, slot=%s, constituents=%d",
            trade_date_str,
            slot,
            len(raw_payload) if raw_payload else 0,
        )
    except Exception as e:
        logger.warning(
            "题材成分快照获取失败: date=%s, slot=%s, error=%s",
            trade_date_str,
            slot,
            e,
        )
        raise

    resolver = ConstituentsResolver()
    constituents_payload = resolver.build(raw_payload)

    if existing is not None:
        mu = MarketUniverse(
            trade_date=trade_date_str,
            slot=slot,
            hot_topics=existing.hot_topics,
            topic_constituents=constituents_payload,
            strong_symbols=existing.strong_symbols,
            metadata=existing.metadata,
        )
    else:
        mu = MarketUniverse(
            trade_date=trade_date_str,
            slot=slot,
            topic_constituents=constituents_payload,
        )

    snapshot_service.save(mu)
    logger.info(
        "题材成分快照已保存: date=%s, slot=%s, constituents=%d",
        trade_date_str,
        slot,
        len(constituents_payload.constituents) if constituents_payload else 0,
    )


async def handle_strong_symbols_snapshot(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """强势池快照构建与保存。

    details 期望字段：
        trade_date: str（ISO 格式）
        slot: str（如 "17-30"）
        force: bool（是否强制覆盖）
    """
    trade_date_str = details.get("trade_date")
    slot = details.get("slot", "17-30")
    force = details.get("force", False)
    offline = details.get("offline", False)

    if not trade_date_str:
        raise ValueError("trade_date is required for strong_symbols_snapshot")

    trade_date = date.fromisoformat(trade_date_str)
    provider = _build_provider(config, offline=offline)

    if provider is None:
        logger.warning(
            "强势池快照跳过: date=%s, slot=%s, 原因=kaipan配置缺失",
            trade_date_str,
            slot,
        )
        return

    snapshot_service = SnapshotService()
    existing = snapshot_service.load(trade_date_str, slot)
    if existing is not None and existing.strong_symbols is not None and not force:
        logger.debug("强势池快照跳过（已存在）: date=%s, slot=%s", trade_date_str, slot)
        return

    try:
        raw_payload = provider.fetch_strong_symbols(trade_date=trade_date, slot=slot, offline=offline)
        logger.info(
            "强势池快照获取成功: date=%s, slot=%s, symbols=%d",
            trade_date_str,
            slot,
            len(raw_payload) if raw_payload else 0,
        )
    except Exception as e:
        logger.warning(
            "强势池快照获取失败: date=%s, slot=%s, error=%s",
            trade_date_str,
            slot,
            e,
        )
        raise

    selector = StrongSymbolsSelector()
    strong_symbols_payload = selector.build(raw_payload)

    if existing is not None:
        mu = MarketUniverse(
            trade_date=trade_date_str,
            slot=slot,
            hot_topics=existing.hot_topics,
            topic_constituents=existing.topic_constituents,
            strong_symbols=strong_symbols_payload,
            metadata=existing.metadata,
        )
    else:
        mu = MarketUniverse(
            trade_date=trade_date_str,
            slot=slot,
            strong_symbols=strong_symbols_payload,
        )

    snapshot_service.save(mu)
    logger.info(
        "强势池快照已保存: date=%s, slot=%s, symbols=%d",
        trade_date_str,
        slot,
        len(strong_symbols_payload.symbols) if strong_symbols_payload else 0,
    )
