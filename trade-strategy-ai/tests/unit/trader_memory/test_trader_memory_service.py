from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from src.trader_memory.schemas import TraderMemoryItem, TraderMemoryType
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
