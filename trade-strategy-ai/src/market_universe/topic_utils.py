"""Topic 相关工具函数。

职责：
- 解析 source_topic_ids 编码格式
- 构建 canonical tags
"""

from __future__ import annotations

from typing import Any


def build_topic_tags(
    idea_source_topic_ids: list[str] | None,
    market_universe_snapshot: dict[str, Any] | None,
) -> tuple[list[str], str | None, dict[str, list[str]] | None]:
    """从 source_topic_ids 构建 canonical tags。

    source_topic_ids 编码格式："topic_name|kind"（编码字符串）
    直接解析编码字符串生成 canonical tag，不依赖 hot_topics 查表。

    Args:
        idea_source_topic_ids: TradeIdea.source_topic_ids
        market_universe_snapshot: market_universe 快照 dict

    Returns:
        tuple of (canonical_tags, topic_source, raw_topic_ids)
        - canonical_tags: ["kaipan:{kind}:{topic_name}", ...]
        - topic_source: provider 名称，如 "kaipan"（有 tags 时才返回）
        - raw_topic_ids: {provider: [raw_topic_id, ...]}
    """
    if not idea_source_topic_ids or not market_universe_snapshot:
        return [], None, None

    # source_topic_ids 格式："topic_name|kind"（编码字符串）
    # 直接解析生成 canonical tags，不查 hot_topics
    canonical_tags = []
    raw_ids: dict[str, list[str]] = {}

    for encoded in idea_source_topic_ids:
        if "|" not in encoded:
            continue
        parts = encoded.rsplit("|", 1)
        if len(parts) != 2:
            continue
        topic_name, kind = parts
        if topic_name and kind:
            canonical_tags.append(f"kaipan:{kind}:{topic_name}")
            raw_ids.setdefault("kaipan", []).append(encoded)

    return canonical_tags, "kaipan" if canonical_tags else None, raw_ids or None
