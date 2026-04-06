from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.agents.trader_agent.agent import TraderAgent
from src.common.config import TraderConfig
from src.schemas.contracts import DataResponse, DataResponseStatus
from src.trader_profile.schemas import SymbolStat, TraderProfile
from src.trader_memory.schemas import TraderMemoryItem, TraderMemoryType
from src.trader_memory.service import TraderMemoryStore


@pytest.mark.asyncio
async def test_generate_trade_ideas_includes_memory_hint(tmp_path: Path) -> None:
    store = TraderMemoryStore(path=tmp_path / "trader_memory.jsonl")
    store.append(
        TraderMemoryItem(
            trader_id="trader_a",
            memory_type=TraderMemoryType.failure_case,
            as_of_date=date(2026, 4, 5),
            symbol="000001.SZ",
            title="previous loss",
            content="gap down",
            created_at=datetime.now(UTC),
        )
    )

    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        watchlist=["000001.SZ"],
        default_target_pct=0.05,
        default_stop_pct=0.03,
    )
    agent = TraderAgent(trader=trader, memory_store=store)

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"000001.SZ": 10.0}},
            )
        )
    )

    ideas = await agent.generate_trade_ideas(as_of_date=date(2026, 4, 6), data_agent=data_agent)

    assert len(ideas) == 1
    assert "memory summary" in (ideas[0].rationale or "")
    assert "previous loss" in (ideas[0].rationale or "")


@pytest.mark.asyncio
async def test_generate_trade_ideas_uses_profile_symbols_when_watchlist_empty(tmp_path: Path) -> None:
    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        watchlist=[],
        default_target_pct=0.05,
        default_stop_pct=0.03,
    )
    profile = TraderProfile(
        trader_id="trader_a",
        top_symbols=[SymbolStat(symbol="510300.SH", mentions=4)],
        concept_tags=["ETF", "trend"],
        style_cluster_ids=["trader_a:etf:v0"],
    )
    agent = TraderAgent(trader=trader, trader_profile=profile)

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"510300.SH": 3.5}},
            )
        )
    )

    ideas = await agent.generate_trade_ideas(as_of_date=date(2026, 4, 6), data_agent=data_agent)

    assert len(ideas) == 1
    assert ideas[0].symbol == "510300.SH"
    assert "profile symbols" in (ideas[0].rationale or "")
    assert "memory mix" not in (ideas[0].rationale or "")
    assert (ideas[0].confidence or 0.0) > 0.3
