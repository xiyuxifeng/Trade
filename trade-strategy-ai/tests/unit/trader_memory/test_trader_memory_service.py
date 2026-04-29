"""TraderMemoryStore 数据库实现测试。

迁移自 JSONL 文件存储测试（NTL-S7-000）：
- 所有测试方法改为 async（store 方法已全部 async）
- 不再使用 tmp_path / path 参数（数据库实现忽略此参数）
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from src.trader_memory.schemas import TraderMemoryFilter, TraderMemoryItem, TraderMemoryType


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _make_item(
    *,
    trader_id: str = "trader_a",
    memory_type: TraderMemoryType = TraderMemoryType.failure_case,
    as_of_date: date | None = None,
    symbol: str = "000001.SZ",
    title: str | None = None,
    content: str = "test content",
    **kwargs,
) -> TraderMemoryItem:
    """构造 TraderMemoryItem 的工厂函数，减少重复代码。

    title 默认使用 uuid4 以避免 unique constraint 冲突（测试数据库共享）。
    """
    if as_of_date is None:
        as_of_date = date(2026, 4, 5)
    if title is None:
        title = str(uuid4())
    return TraderMemoryItem(
        trader_id=trader_id,
        memory_type=memory_type,
        as_of_date=as_of_date,
        symbol=symbol,
        title=title,
        content=content,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# P2-103: append / list_recent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_store_append_and_list_recent(store: TraderMemoryStore) -> None:
    now = date(2026, 4, 6)
    older = date(2026, 4, 5)

    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.failure_case,
            as_of_date=older,
            title="loss",
            content="gap down",
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.success_case,
            as_of_date=now,
            title="win",
            content="breakout",
        )
    )

    recent = await store.list_recent(trader_id="trader_a", limit=1)
    assert len(recent) == 1
    assert recent[0].title == "win"


@pytest.mark.asyncio
async def test_memory_store_search_by_symbol(store: TraderMemoryStore) -> None:
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 6),
            symbol="510300.SH",
            title="note",
            content="index ETF",
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 6),
            symbol="000001.SZ",
            title="other",
            content="stock",
        )
    )

    results = await store.search_by_symbol(trader_id="trader_a", symbol="510300.SH")
    assert len(results) == 1
    assert results[0].title == "note"


@pytest.mark.asyncio
async def test_memory_store_summarize_context(store: TraderMemoryStore) -> None:
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.success_case,
            as_of_date=date(2026, 4, 5),
            title="win",
            content="good entry",
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 6),
            title="review",
            content="take profit earlier",
        )
    )

    summary = await store.summarize_context(trader_id="trader_a", symbol="000001.SZ", limit=5)
    assert summary.total_items == 2
    assert summary.total_symbol_items == 2
    assert summary.by_type["success_case"] == 1
    assert summary.by_type["review_note"] == 1
    assert "take profit earlier" in summary.review_notes[0]


# ---------------------------------------------------------------------------
# P2-103 / P2-109D: archive / restore / hard_delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_archive_and_restore(store: TraderMemoryStore) -> None:
    memory = _make_item(
        trader_id="trader_a",
        memory_type=TraderMemoryType.failure_case,
        title="loss",
        content="gap down",
    )
    await store.append(memory)
    assert len(await store.list_recent(trader_id="trader_a")) == 1

    # archive
    found = await store.archive(memory.memory_id)
    assert found is True
    # gone from default query
    assert len(await store.list_recent(trader_id="trader_a")) == 0
    # visible when including archived
    assert (
        len(
            await store.list_filtered(
                TraderMemoryFilter(trader_id="trader_a", include_archived=True)
            )
        )
        == 1
    )

    # restore
    restored = await store.restore(memory.memory_id)
    assert restored is True
    assert len(await store.list_recent(trader_id="trader_a")) == 1


@pytest.mark.asyncio
async def test_hard_delete(store: TraderMemoryStore) -> None:
    memory = _make_item(
        trader_id="trader_a",
        memory_type=TraderMemoryType.success_case,
        as_of_date=date(2026, 4, 6),
        title="win",
        content="breakout",
    )
    await store.append(memory)
    assert len(await store.list_recent(trader_id="trader_a")) == 1

    deleted = await store.hard_delete(memory.memory_id)
    assert deleted is True
    assert len(await store.list_recent(trader_id="trader_a")) == 0


@pytest.mark.asyncio
async def test_archive_not_found(store: TraderMemoryStore) -> None:
    assert await store.archive(uuid4()) is False


# ---------------------------------------------------------------------------
# P2-103: list_filtered with various criteria
# ---------------------------------------------------------------------------

async def _seed_memories(store: TraderMemoryStore) -> list[TraderMemoryItem]:
    items = [
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.success_case,
            as_of_date=date(2026, 4, 1),
            symbol="000001.SZ",
            title="win breakout",
            content="price broke 20d high",
        ),
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.failure_case,
            as_of_date=date(2026, 4, 3),
            symbol="000001.SZ",
            title="loss",
            content="gap down stop out",
        ),
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 5),
            symbol="510300.SH",
            title="ETF note",
            content="index ETF position reviewed",
        ),
        _make_item(
            trader_id="trader_b",
            memory_type=TraderMemoryType.success_case,
            as_of_date=date(2026, 4, 2),
            symbol="600000.SH",
            title="bank win",
            content="low volatility entry",
        ),
    ]
    for item in items:
        await store.append(item)
    return items


@pytest.mark.asyncio
async def test_filter_by_memory_types(store: TraderMemoryStore) -> None:
    await _seed_memories(store)

    result = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", memory_types=[TraderMemoryType.success_case])
    )
    assert len(result) == 1
    assert result[0].memory_type == TraderMemoryType.success_case


@pytest.mark.asyncio
async def test_filter_by_date_range(store: TraderMemoryStore) -> None:
    await _seed_memories(store)

    result = await store.list_filtered(
        TraderMemoryFilter(
            trader_id="trader_a",
            date_from=date(2026, 4, 2),
            date_to=date(2026, 4, 4),
        )
    )
    assert len(result) == 1
    assert result[0].as_of_date == date(2026, 4, 3)


@pytest.mark.asyncio
async def test_filter_by_symbol(store: TraderMemoryStore) -> None:
    await _seed_memories(store)

    result = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", symbol="000001.SZ")
    )
    assert len(result) == 2


@pytest.mark.asyncio
async def test_filter_by_keyword(store: TraderMemoryStore) -> None:
    await _seed_memories(store)

    result = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", keyword="gap")
    )
    assert len(result) == 1
    assert "gap" in result[0].content.lower()


@pytest.mark.asyncio
async def test_filter_archived_excluded_by_default(store: TraderMemoryStore) -> None:
    item = (await _seed_memories(store))[0]  # success_case
    await store.archive(item.memory_id)

    result = await store.list_filtered(TraderMemoryFilter(trader_id="trader_a"))
    assert all(not r.archived for r in result)


@pytest.mark.asyncio
async def test_filter_include_archived(store: TraderMemoryStore) -> None:
    item = (await _seed_memories(store))[0]
    await store.archive(item.memory_id)

    result = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", include_archived=True)
    )
    assert len(result) == 3  # 2 active + 1 archived


@pytest.mark.asyncio
async def test_filter_limit_offset(store: TraderMemoryStore) -> None:
    await _seed_memories(store)

    page1 = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", limit=1, offset=0)
    )
    page2 = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", limit=1, offset=1)
    )
    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0].memory_id != page2[0].memory_id


@pytest.mark.asyncio
async def test_count_filtered(store: TraderMemoryStore) -> None:
    await _seed_memories(store)

    count = await store.count_filtered(TraderMemoryFilter(trader_id="trader_a"))
    assert count == 3


@pytest.mark.asyncio
async def test_summarize_excludes_archived(store: TraderMemoryStore) -> None:
    item = (await _seed_memories(store))[0]
    await store.archive(item.memory_id)

    summary = await store.summarize_context(trader_id="trader_a")
    assert summary.total_items == 2  # archived item excluded
    assert summary.archived_items == 1


# ---------------------------------------------------------------------------
# NTL-S5-005: new memory types in summarize_context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_summarize_context_new_memory_types(store: TraderMemoryStore) -> None:
    """验证 summarize_context 正确聚合 postmortem / strategy_adjustment / market_regime_note。"""
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="postmortem entry timing",
            content="Entry timing poor for SH600519",
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.strategy_adjustment,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="adjust entry tolerance",
            content="Increase entry price tolerance",
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.market_regime_note,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="high volatility",
            content="VIX > 30, reduce position size",
        )
    )
    # 验证 summary 正确聚合
    summary = await store.summarize_context(trader_id="trader_a", symbol="SH600519", limit=5)
    assert summary.total_items == 3
    assert len(summary.postmortem_notes) == 1
    assert "Entry timing poor" in summary.postmortem_notes[0]
    assert len(summary.strategy_adjustments) == 1
    assert "Increase entry price tolerance" in summary.strategy_adjustments[0]
    assert len(summary.market_regime_notes) == 1
    assert "VIX > 30" in summary.market_regime_notes[0]


# ---------------------------------------------------------------------------
# NTL-S5-006: tags and strategy_version_id filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_filter_by_tags(store: TraderMemoryStore) -> None:
    """验证 tags 过滤：匹配任一 tag 即可命中."""
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="AI chip postmortem",
            content="Entry timing poor",
            tags=["AI_chip", "半导体"],
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 24),
            symbol="SH600519",
            title="新能源 postmortem",
            content="Position sizing issue",
            tags=["新能源车"],
        )
    )

    result = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", tags=["AI_chip"])
    )
    assert len(result) == 1
    assert result[0].title == "AI chip postmortem"


@pytest.mark.asyncio
async def test_filter_by_strategy_version(store: TraderMemoryStore) -> None:
    """验证 strategy_version_id 过滤：精确匹配."""
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="v1 postmortem",
            content="Version 1 analysis",
            strategy_version_id="v_2026_04_25",
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 24),
            symbol="SH600519",
            title="v2 postmortem",
            content="Version 2 analysis",
            strategy_version_id="v_2026_04_24",
        )
    )

    result = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", strategy_version_id="v_2026_04_25")
    )
    assert len(result) == 1
    assert result[0].title == "v1 postmortem"


@pytest.mark.asyncio
async def test_filter_by_tags_and_symbol(store: TraderMemoryStore) -> None:
    """验证 tags + symbol 组合过滤."""
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="AI chip SH600519",
            content="Entry timing poor",
            tags=["AI_chip"],
        )
    )
    await store.append(
        _make_item(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="000001.SZ",
            title="AI chip 000001",
            content="Breakout analysis",
            tags=["AI_chip"],
        )
    )

    result = await store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", tags=["AI_chip"], symbol="SH600519")
    )
    assert len(result) == 1
    assert result[0].symbol == "SH600519"


# ---------------------------------------------------------------------------
# NTL-S5-012: extra field
# ---------------------------------------------------------------------------

def test_trader_memory_item_has_extra_field() -> None:
    """TraderMemoryItem 应有 extra 字段（NTL-S5-012）。"""
    item = _make_item(
        trader_id="trader_001",
        memory_type=TraderMemoryType.failure_case,
        title="test",
        content="test content",
    )
    assert hasattr(item, "extra")
    assert item.extra == {}
    item.extra = {"auto_original": {"reason": "test"}}
    assert item.extra["auto_original"]["reason"] == "test"


# ---------------------------------------------------------------------------
# NTL-S5-012: update() method
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_modifies_existing_item(store: TraderMemoryStore) -> None:
    """update() 应原地修改已有条目，不新增。"""
    original = _make_item(
        memory_id=uuid4(),
        trader_id="trader_001",
        memory_type=TraderMemoryType.failure_case,
        as_of_date=date(2026, 4, 25),
        symbol="AAPL",
        title="原始 failure",
        content="原始内容",
    )
    await store.append(original)

    # 更新
    updated = original.model_copy(deep=True)
    updated.content = "更新后内容"
    updated.postmortem_data = {"return_pct": -3.5}

    result = await store.update(original.memory_id, updated)

    assert result is True

    # 验证：只有一条记录
    items = await store.list_filtered(TraderMemoryFilter(trader_id="trader_001"))
    assert len(items) == 1
    assert items[0].content == "更新后内容"
    assert items[0].postmortem_data == {"return_pct": -3.5}


@pytest.mark.asyncio
async def test_update_nonexistent_returns_false(store: TraderMemoryStore) -> None:
    """update() 对不存在的 ID 返回 False。"""
    result = await store.update(uuid4(), _make_item())
    assert result is False