from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from src.trader_memory.schemas import TraderMemoryFilter, TraderMemoryItem, TraderMemoryType
from src.trader_memory.service import TraderMemoryStore


def test_memory_store_append_and_list_recent(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "trader_memory.jsonl")
    now = datetime.now(UTC)
    older = now - timedelta(days=1)

    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.failure_case,
            as_of_date=date(2026, 4, 5),
            symbol="000001.SZ",
            title="loss",
            content="gap down",
            created_at=older,
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.success_case,
            as_of_date=date(2026, 4, 6),
            symbol="000001.SZ",
            title="win",
            content="breakout",
            created_at=now,
        )
    )

    recent = store.list_recent(trader_id="trader_a", limit=1)
    assert len(recent) == 1
    assert recent[0].title == "win"


def test_memory_store_search_by_symbol(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "trader_memory.jsonl")
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 6),
            symbol="510300.SH",
            title="note",
            content="index ETF",
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 6),
            symbol="000001.SZ",
            title="other",
            content="stock",
        )
    )

    results = store.search_by_symbol(trader_id="trader_a", symbol="510300.SH")
    assert len(results) == 1
    assert results[0].title == "note"


def test_memory_store_summarize_context(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "trader_memory.jsonl")
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.success_case,
            as_of_date=date(2026, 4, 5),
            symbol="000001.SZ",
            title="win",
            content="good entry",
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 6),
            symbol="000001.SZ",
            title="review",
            content="take profit earlier",
        )
    )

    summary = store.summarize_context(trader_id="trader_a", symbol="000001.SZ", limit=5)
    assert summary.total_items == 2
    assert summary.total_symbol_items == 2
    assert summary.by_type["success_case"] == 1
    assert summary.by_type["review_note"] == 1
    assert "take profit earlier" in summary.review_notes[0]


# ---------------------------------------------------------------------------
# P2-103 / P2-109D: archive / restore / hard_delete
# ---------------------------------------------------------------------------

def test_archive_and_restore(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    memory = TraderMemoryItem(
        trader_id="trader_a",
        memory_type=TraderMemoryType.failure_case,
        as_of_date=date(2026, 4, 5),
        symbol="000001.SZ",
        title="loss",
        content="gap down",
    )
    store.append(memory)
    assert len(store.list_recent(trader_id="trader_a")) == 1

    # archive
    found = store.archive(memory.memory_id)
    assert found is True
    # gone from default query
    assert len(store.list_recent(trader_id="trader_a")) == 0
    # visible when including archived
    assert len(store.list_filtered(TraderMemoryFilter(trader_id="trader_a", include_archived=True))) == 1

    # restore
    restored = store.restore(memory.memory_id)
    assert restored is True
    assert len(store.list_recent(trader_id="trader_a")) == 1


def test_hard_delete(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    memory = TraderMemoryItem(
        trader_id="trader_a",
        memory_type=TraderMemoryType.success_case,
        as_of_date=date(2026, 4, 6),
        symbol="000001.SZ",
        title="win",
        content="breakout",
    )
    store.append(memory)
    assert len(store.list_recent(trader_id="trader_a")) == 1

    deleted = store.hard_delete(memory.memory_id)
    assert deleted is True
    assert len(store.list_recent(trader_id="trader_a")) == 0


def test_archive_not_found(tmp_path: Path) -> None:
    from uuid import uuid4
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    assert store.archive(uuid4()) is False


# ---------------------------------------------------------------------------
# P2-103: list_filtered with various criteria
# ---------------------------------------------------------------------------

def _seed_memories(store: TraderMemoryStore) -> list[TraderMemoryItem]:
    items = [
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.success_case,
            as_of_date=date(2026, 4, 1),
            symbol="000001.SZ",
            title="win breakout",
            content="price broke 20d high",
        ),
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.failure_case,
            as_of_date=date(2026, 4, 3),
            symbol="000001.SZ",
            title="loss",
            content="gap down stop out",
        ),
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.review_note,
            as_of_date=date(2026, 4, 5),
            symbol="510300.SH",
            title="ETF note",
            content="index ETF position reviewed",
        ),
        TraderMemoryItem(
            trader_id="trader_b",
            memory_type=TraderMemoryType.success_case,
            as_of_date=date(2026, 4, 2),
            symbol="600000.SH",
            title="bank win",
            content="low volatility entry",
        ),
    ]
    for item in items:
        store.append(item)
    return items


def test_filter_by_memory_types(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    _seed_memories(store)

    result = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", memory_types=[TraderMemoryType.success_case])
    )
    assert len(result) == 1
    assert result[0].memory_type == TraderMemoryType.success_case


def test_filter_by_date_range(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    _seed_memories(store)

    result = store.list_filtered(
        TraderMemoryFilter(
            trader_id="trader_a",
            date_from=date(2026, 4, 2),
            date_to=date(2026, 4, 4),
        )
    )
    assert len(result) == 1
    assert result[0].as_of_date == date(2026, 4, 3)


def test_filter_by_symbol(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    _seed_memories(store)

    result = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", symbol="000001.SZ")
    )
    assert len(result) == 2


def test_filter_by_keyword(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    _seed_memories(store)

    result = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", keyword="gap")
    )
    assert len(result) == 1
    assert "gap" in result[0].content.lower()


def test_filter_archived_excluded_by_default(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    item = _seed_memories(store)[0]  # success_case
    store.archive(item.memory_id)

    result = store.list_filtered(TraderMemoryFilter(trader_id="trader_a"))
    assert all(not r.archived for r in result)


def test_filter_include_archived(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    item = _seed_memories(store)[0]
    store.archive(item.memory_id)

    result = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", include_archived=True)
    )
    assert len(result) == 3  # 2 active + 1 archived


def test_filter_limit_offset(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    _seed_memories(store)

    page1 = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", limit=1, offset=0)
    )
    page2 = store.list_filtered(
        TraderMemoryFilter(trader_id="trader_a", limit=1, offset=1)
    )
    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0].memory_id != page2[0].memory_id


def test_count_filtered(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    _seed_memories(store)

    count = store.count_filtered(TraderMemoryFilter(trader_id="trader_a"))
    assert count == 3


def test_summarize_excludes_archived(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")
    item = _seed_memories(store)[0]
    store.archive(item.memory_id)

    summary = store.summarize_context(trader_id="trader_a")
    assert summary.total_items == 2  # archived item excluded
    assert summary.archived_items == 1


# ---------------------------------------------------------------------------
# NTL-S5-005: new memory types in summarize_context
# ---------------------------------------------------------------------------

def test_summarize_context_new_memory_types(tmp_path: Path) -> None:
    """验证 summarize_context 正确聚合 postmortem / strategy_adjustment / market_regime_note。"""
    store = TraderMemoryStore(path=tmp_path / "mem.jsonl")

    # 写入各种类型的 memory
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.postmortem,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="postmortem entry timing",
            content="Entry timing poor for SH600519",
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.strategy_adjustment,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="adjust entry tolerance",
            content="Increase entry price tolerance",
        )
    )
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.market_regime_note,
            as_of_date=date(2026, 4, 25),
            symbol="SH600519",
            title="high volatility",
            content="VIX > 30, reduce position size",
        )
    )
    # 验证 summary 正确聚合
    summary = store.summarize_context(trader_id="trader_a", symbol="SH600519", limit=5)
    assert summary.total_items == 3
    assert len(summary.postmortem_notes) == 1
    assert "Entry timing poor" in summary.postmortem_notes[0]
    assert len(summary.strategy_adjustments) == 1
    assert "Increase entry price tolerance" in summary.strategy_adjustments[0]
    assert len(summary.market_regime_notes) == 1
    assert "VIX > 30" in summary.market_regime_notes[0]
