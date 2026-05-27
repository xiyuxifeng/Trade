from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.agents.trader_agent.agent import TraderAgent
from src.common.config import TraderConfig
from src.market_universe.schemas import MarketUniverse, StrongSymbol, StrongSymbolsPayload
from src.schemas.contracts import DataResponse, DataResponseStatus
from src.strategy_library.schemas import StrategyRecommendation, StrategyVersion, StrategyVersionStatus
from src.trader_profile.schemas import SymbolStat, TraderProfile
from src.trader_memory.schemas import TraderMemorySummary, TraderMemoryType


@pytest.mark.asyncio
async def test_generate_trade_ideas_includes_memory_hint(tmp_path: Path) -> None:
    store = SimpleNamespace(
        summarize_context=AsyncMock(
            return_value=TraderMemorySummary(
                trader_id="trader_a",
                symbol="000001.SZ",
                total_items=1,
                total_symbol_items=1,
                by_type={TraderMemoryType.failure_case.value: 1},
                recent_titles=["previous loss"],
                symbol_titles=["previous loss"],
            )
        )
    )

    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        default_target_pct=0.05,
        default_stop_pct=0.03,
    )
    agent = TraderAgent(trader=trader, memory_store=store)

    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-06:released:v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 6),
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="000001.SZ", decision="buy", confidence=0.72),
        ],
        released_at=datetime.now(UTC),
    )

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"000001.SZ": 10.0}},
            )
        )
    )

    ideas = await agent.generate_trade_ideas(
        as_of_date=date(2026, 4, 6),
        data_agent=data_agent,
        strategy_version=strategy_version,
    )

    assert len(ideas) == 1
    assert "memory summary" in (ideas[0].rationale or "")
    assert "previous loss" in (ideas[0].rationale or "")


@pytest.mark.asyncio
async def test_generate_trade_ideas_uses_postmortem_and_adjustment_memory() -> None:
    """盘后复盘和策略调整记忆应进入后续盘前推荐上下文。"""
    memory_store = SimpleNamespace(
        summarize_context=AsyncMock(
            return_value=TraderMemorySummary(
                trader_id="trader_a",
                symbol="000001.SZ",
                total_items=2,
                total_symbol_items=2,
                by_type={
                    TraderMemoryType.postmortem.value: 1,
                    TraderMemoryType.strategy_adjustment.value: 1,
                },
                postmortem_notes=["昨日追高失败，回撤超阈值"],
                strategy_adjustments=["降低开仓仓位并等待放量确认"],
            )
        )
    )
    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        default_target_pct=0.05,
        default_stop_pct=0.03,
    )
    agent = TraderAgent(trader=trader, memory_store=memory_store)
    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-06:released:v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 6),
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="000001.SZ", decision="buy", confidence=0.72),
        ],
        released_at=datetime.now(UTC),
    )
    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"000001.SZ": 10.0}},
            )
        )
    )

    ideas = await agent.generate_trade_ideas(
        as_of_date=date(2026, 4, 6),
        data_agent=data_agent,
        strategy_version=strategy_version,
    )

    assert len(ideas) == 1
    assert "postmortem" in (ideas[0].rationale or "")
    assert "strategy_adjustment" in (ideas[0].rationale or "")


@pytest.mark.asyncio
async def test_generate_trade_ideas_uses_profile_symbols_as_context(tmp_path: Path) -> None:
    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
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
    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-06:released:v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 6),
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="510300.SH", decision="buy", confidence=0.72),
        ],
        released_at=datetime.now(UTC),
    )

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"510300.SH": 3.5}},
            )
        )
    )

    ideas = await agent.generate_trade_ideas(
        as_of_date=date(2026, 4, 6),
        data_agent=data_agent,
        strategy_version=strategy_version,
    )

    assert len(ideas) == 1
    assert ideas[0].symbol == "510300.SH"
    assert "profile symbols" in (ideas[0].rationale or "")
    assert "memory mix" not in (ideas[0].rationale or "")
    assert ideas[0].confidence == 0.72


@pytest.mark.asyncio
async def test_generate_trade_ideas_uses_strategy_version_when_provided() -> None:
    """Stage 4 路径：候选标的来自 strategy_version.recommendations"""
    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        watchlist=["000001.SZ"],  # 不应该被使用
        default_target_pct=0.05,
        default_stop_pct=0.03,
    )
    agent = TraderAgent(trader=trader)

    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-24:draft:v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 24),
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="600000.SH", decision="buy", confidence=0.72),
            StrategyRecommendation(symbol="600001.SH", decision="hold", confidence=0.65),
            StrategyRecommendation(symbol="600002.SH", decision="sell", confidence=0.5),  # 应该被过滤
        ],
        released_at=datetime.now(UTC),
    )

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"600000.SH": 10.0, "600001.SH": 8.5, "600002.SH": 12.0}},
            )
        )
    )

    ideas = await agent.generate_trade_ideas(
        as_of_date=date(2026, 4, 24),
        data_agent=data_agent,
        strategy_version=strategy_version,
    )

    # 三类决策都输出（buy / hold / sell）
    assert len(ideas) == 3
    symbols = {idea.symbol for idea in ideas}
    assert symbols == {"600000.SH", "600001.SH", "600002.SH"}

    # 决策来自 strategy_version
    buy_idea = next(i for i in ideas if i.symbol == "600000.SH")
    assert buy_idea.side == "buy"
    assert buy_idea.confidence == 0.72

    hold_idea = next(i for i in ideas if i.symbol == "600001.SH")
    assert hold_idea.side == "hold"

    sell_idea = next(i for i in ideas if i.symbol == "600002.SH")
    assert sell_idea.side == "sell"
    assert sell_idea.confidence == 0.5

    # strategy_version_id 被填充
    assert all(idea.strategy_version_id == strategy_version.version_id for idea in ideas)

    # rationale 包含 strategy 版本标识
    assert "Stage4" in (buy_idea.rationale or "")
    assert strategy_version.version_id in (buy_idea.rationale or "")


@pytest.mark.asyncio
async def test_generate_trade_ideas_includes_strong_symbol_hint() -> None:
    """Stage 4 路径：market_universe.strong_symbols 提供强势评分上下文"""
    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        watchlist=[],
        default_target_pct=0.05,
        default_stop_pct=0.03,
    )
    agent = TraderAgent(trader=trader)

    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-24:draft:v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 24),
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="600000.SH", decision="buy", confidence=0.72),
        ],
        released_at=datetime.now(UTC),
    )

    market_universe = MarketUniverse(
        trade_date="2026-04-24",
        slot="09-25",
        strong_symbols=StrongSymbolsPayload(
            trade_date="2026-04-24",
            slot="09-25",
            symbols=[
                StrongSymbol(
                    kind="strong_fengkou",
                    symbol="600000.SH",
                    name="浦发银行",
                    strength_score=8.5,
                    change_pct=5.2,
                    turnover=1200000.0,
                    topic_tags="银行,普涨",
                ),
            ],
        ),
    )

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"600000.SH": 10.0}},
            )
        )
    )

    ideas = await agent.generate_trade_ideas(
        as_of_date=date(2026, 4, 24),
        data_agent=data_agent,
        strategy_version=strategy_version,
        market_universe=market_universe,
    )

    assert len(ideas) == 1
    assert "strong_symbol" in (ideas[0].rationale or "")
    assert "strength=8.5" in (ideas[0].rationale or "")
    assert "change=5.2%" in (ideas[0].rationale or "")


@pytest.mark.asyncio
async def test_generate_trade_ideas_requires_strategy_version() -> None:
    """严格模式：未传入 strategy_version 时直接报错。"""
    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        default_target_pct=0.05,
        default_stop_pct=0.03,
    )
    agent = TraderAgent(trader=trader)

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"000001.SZ": 10.0}},
            )
        )
    )

    with pytest.raises(ValueError, match="requires a released strategy_version"):
        await agent.generate_trade_ideas(
            as_of_date=date(2026, 4, 24),
            data_agent=data_agent,
        )


@pytest.mark.asyncio
async def test_sell_decision_mirrors_target_and_stop() -> None:
    """NTL-S4-TD001: sell 决策时 target 在 entry 下方，stop 在 entry 上方"""
    trader = TraderConfig(
        trader_id="trader_a",
        display_name="Trader A",
        watchlist=["600000.SH"],
        default_target_pct=0.05,   # 5%
        default_stop_pct=0.03,     # 3%
    )
    agent = TraderAgent(trader=trader)

    data_agent = SimpleNamespace(
        handle=AsyncMock(
            return_value=DataResponse(
                request_id="00000000-0000-0000-0000-000000000000",
                status=DataResponseStatus.ok,
                payload={"last_price": {"600000.SH": 10.0}},
            )
        )
    )

    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-24:draft:v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 24),
        status=StrategyVersionStatus.draft,
        recommendations=[
            # decision="sell"，entry=10.0
            # target 应在下方: 10.0 * (1 - 0.05) = 9.5
            # stop 应在上方:   10.0 * (1 + 0.03) = 10.3
            StrategyRecommendation(symbol="600000.SH", decision="sell", confidence=0.65),
        ],
    )

    ideas = await agent.generate_trade_ideas(
        as_of_date=date(2026, 4, 24),
        data_agent=data_agent,
        strategy_version=strategy_version,
    )

    assert len(ideas) == 1
    idea = ideas[0]
    assert idea.side == "sell"
    assert idea.entry.price == 10.0
    assert idea.target_price == 9.5    # 10.0 * (1 - 0.05)
    assert idea.stop_loss_price == 10.3  # 10.0 * (1 + 0.03)
