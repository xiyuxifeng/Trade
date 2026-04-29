from __future__ import annotations

from datetime import date, datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

import pytest

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import AppConfig, DataConfig, Stage4Config, StorageConfig, TraderConfig
from src.market_universe.schemas import MarketUniverse, HotTopicsPayload, HotTopic
from src.schemas.contracts import DailyReport, TradeEntry, TradeIdea
from src.strategy_library.schemas import StrategyRecommendation, StrategyVersion, StrategyVersionStatus
from src.trader_memory.schemas import TraderMemoryType
from src.trader_memory.service import TraderMemoryStore
from src.strategy.types import SignalSide, SynthesisMode, RawSignal, Signal


def _make_config() -> AppConfig:
    return AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.0}),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )

@asynccontextmanager
async def _mock_session_scope():
    """避免单元测试连接真实数据库。"""
    yield MagicMock()


@pytest.mark.asyncio
async def test_manager_writes_memory_and_reuses_it(tmp_path: Path) -> None:
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 6)

    report = DailyReport(
        as_of_date=day,
        ideas=[
            TradeIdea(
                trader_id="trader_a",
                as_of_date=day,
                symbol="000001.SZ",
                entry=TradeEntry(type="limit", price=10.0),
                target_price=10.5,
                stop_loss_price=9.7,
            )
        ],
        highlights=["seed"],
    )
    manager._daily_report_path(day).write_text(report.model_dump_json(indent=2), encoding="utf-8")

    with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope), \
        patch("src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"), \
        patch("src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"):
        result = await manager.run_after_close(as_of_date=day, force=True)
    # NTL-S5-013: Phase 0 (no bars) now correctly returns "fallback" status
    assert result.evaluations[0].status == "fallback"
    assert result.evaluations[0].partial_data is False
    assert result.evaluations[0].fallback_reason == "no_bars_data"
    assert "reason=no_bars_data" in result.evaluations[0].notes[0]

    # Mock memory store to verify memory was written
    mock_store = MagicMock(spec=TraderMemoryStore)
    mock_store.list_recent = AsyncMock(return_value=[
        MagicMock(symbol="000001.SZ", content="test memory")
    ])
    manager.memory_store = mock_store

    rerun_report = await manager.run_pre_market(as_of_date=day, force=True)
    assert "memory summary" in (rerun_report.ideas[0].rationale or "")
    assert "success case" in (rerun_report.ideas[0].rationale or "")


@pytest.mark.asyncio
async def test_manager_creates_structured_review_task_and_review_note(tmp_path: Path) -> None:
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 9.0}),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 6)

    report = DailyReport(
        as_of_date=day,
        ideas=[
            TradeIdea(
                trader_id="trader_a",
                as_of_date=day,
                symbol="000001.SZ",
                entry=TradeEntry(type="limit", price=10.0),
                target_price=10.5,
                stop_loss_price=9.7,
            )
        ],
        highlights=["seed"],
    )
    manager._daily_report_path(day).write_text(report.model_dump_json(indent=2), encoding="utf-8")

    with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope), \
        patch("src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"), \
        patch("src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"):
        result = await manager.run_after_close(as_of_date=day, force=True)
    # NTL-S5-013: Phase 0 (no bars) now correctly returns "fallback" status
    assert result.evaluations[0].status == "fallback"

    tasks = manager.tasks_path.read_text(encoding="utf-8").splitlines()
    review_tasks = [json.loads(line) for line in tasks if json.loads(line)["type"] == "trader_review"]
    assert len(review_tasks) == 1
    details = review_tasks[0]["details"]
    assert details["review_type"] == "trader_review"
    assert details["trigger_reason"] == "loss"
    assert details["evaluation_snapshot"]["threshold"] == 0.0

    # Mock memory store to verify review note was written
    mock_store = MagicMock(spec=TraderMemoryStore)
    mock_store.list_recent = AsyncMock(return_value=[
        MagicMock(symbol="000001.SZ", memory_type=TraderMemoryType.review_note)
    ])
    manager.memory_store = mock_store


@pytest.mark.asyncio
async def test_manager_marks_partial_data_when_bars_are_incomplete(tmp_path: Path) -> None:
    """当只有部分 bars 时，应标记 partial_data 并保留结构化说明。"""
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 6)

    report = DailyReport(
        as_of_date=day,
        ideas=[
            TradeIdea(
                trader_id="trader_a",
                as_of_date=day,
                symbol="000001.SZ",
                entry=TradeEntry(type="limit", price=10.0),
                target_price=10.5,
                stop_loss_price=9.7,
            )
        ],
        highlights=["seed"],
    )
    manager._daily_report_path(day).write_text(report.model_dump_json(indent=2), encoding="utf-8")

    partial_pack = None
    from src.evaluation.evidence_pack import EvidencePack, MarketDataSnapshot

    partial_pack = EvidencePack(
        idea_id=report.ideas[0].idea_id,
        trade_date=str(day),
        trade_idea=report.ideas[0],
        signal_context=None,
        market_data=MarketDataSnapshot(
            bars=[
                {"date": "2026-04-06", "open": 10.0, "high": 10.2, "low": 9.8, "close": 10.1},
            ],
            entry_price=10.0,
            target_price=10.5,
            stop_loss_price=9.7,
        ),
    )

    with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope), \
        patch("src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"), \
        patch("src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"), \
        patch.object(manager, "_generate_evidence_pack", new_callable=AsyncMock, return_value=partial_pack):
        result = await manager.run_after_close(as_of_date=day, force=True)

    evaluation = result.evaluations[0]
    assert evaluation.status == "partial"
    assert evaluation.partial_data is True
    assert evaluation.fallback_reason is None
    assert "[partial]" in evaluation.notes[0]


@pytest.mark.asyncio
async def test_run_after_close_writes_canonical_topic_tags(tmp_path: Path) -> None:
    """验证 run_after_close 使用 source_topic_ids 生成 canonical topic tags。"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.0}),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 6)

    report = DailyReport(
        as_of_date=day,
        ideas=[
            TradeIdea(
                trader_id="trader_a",
                as_of_date=day,
                symbol="000001.SZ",
                entry=TradeEntry(type="limit", price=10.0),
                source_topic_ids=["AI算力|concept"],
            )
        ],
        highlights=["seed"],
        market_universe_snapshot={"provider": "kaipan"},
    )
    manager._daily_report_path(day).write_text(report.model_dump_json(indent=2), encoding="utf-8")

    # Mock memory store to verify topic tags were written
    mock_store = MagicMock(spec=TraderMemoryStore)
    mock_memories = [
        MagicMock(
            tags=["kaipan:concept:AI算力"],
            topic_source="kaipan",
            raw_topic_ids={"kaipan": ["AI算力|concept"]},
        )
    ]
    mock_store.list_recent = AsyncMock(return_value=mock_memories)
    manager.memory_store = mock_store

    with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope), \
        patch("src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"), \
        patch("src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"):
        await manager.run_after_close(as_of_date=day, force=True)

    # Verify memory store was called
    mock_store.list_recent.assert_called_once()


@pytest.mark.asyncio
async def test_manager_records_ideas_as_signals(tmp_path: Path) -> None:
    """P4-025: 验证 ManagerAgent 将交易想法记录为信号版本"""
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 9)

    # 运行 pre_market，ideas 会被记录为信号
    report = await manager.run_pre_market(as_of_date=day, force=True)

    # 验证生成了 ideas
    assert len(report.ideas) == 1

    # 验证信号已被记录
    idea = report.ideas[0]
    signal_id = f"idea_{idea.idea_id}"

    # 从 SignalVersioning 获取信号
    stored = manager.signal_versioning.get_version(signal_id)
    assert stored is not None
    assert stored.signal.signal_id == signal_id
    assert stored.signal.symbol == "000001.SZ"
    assert stored.signal.side == SignalSide.BUY  # NTL-S4-002: side 来自 idea.side（默认 "buy"）
    assert stored.signal.confidence > 0
    assert stored.signal.metadata["trader_id"] == "trader_a"
    assert stored.signal.metadata["target_price"] == 12.6  # 12.0 * 1.05
    assert stored.signal.metadata["stop_loss_price"] == 11.64  # 12.0 * 0.97


@pytest.mark.asyncio
async def test_list_signals_filters_by_symbol(tmp_path: Path) -> None:
    """P4-025: 验证 list_signals 支持按标的过滤"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.0, "600000.SH": 8.0}),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ", "600000.SH"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 9)

    await manager.run_pre_market(as_of_date=day, force=True)

    # 过滤 000001.SZ
    versions_sz = manager.signal_versioning.list_versions(symbol="000001.SZ", limit=100)
    assert all(v.signal.symbol == "000001.SZ" for v in versions_sz)

    # 过滤 600000.SH
    versions_sh = manager.signal_versioning.list_versions(symbol="600000.SH", limit=100)
    assert all(v.signal.symbol == "600000.SH" for v in versions_sh)


@pytest.mark.asyncio
async def test_evaluate_signal_success(tmp_path: Path) -> None:
    """P4-024: 验证 evaluate_signal 成功调用 StrategyAgent 和 RiskAgent"""
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)

    trade_idea = MagicMock()
    trade_idea.symbol = "000001"
    trade_idea.idea_id = uuid4()

    market_data = {"last_price": 10.0, "volume": 1000000}

    # Mock StrategyAgent
    with patch.object(manager.strategy_agent, 'generate_raw_signal', return_value=RawSignal(
        signal_id="test",
        symbol="000001",
        side=SignalSide.BUY,
        confidence=0.75,
        triggered_rules=[],
        synthesis_mode=SynthesisMode.PRIORITY,
        entry_price=None,
        position_size=None,
        timestamp=datetime.now(timezone.utc),
        metadata={}
    )):
        # Mock RiskAgent
        with patch.object(manager.risk_agent, 'check', return_value=Signal(
            signal_id="test",
            symbol="000001",
            side=SignalSide.BUY,
            confidence=0.75,
            timestamp=datetime.now(timezone.utc),
            triggered_rules=[],
            synthesis_mode=SynthesisMode.PRIORITY,
            entry_price=None,
            position_size=None,
            stop_loss=None,
            take_profit=None,
            metadata={}
        )):
            result = await manager.evaluate_signal(trade_idea, market_data)
            assert result is not None
            assert result.side == SignalSide.BUY


# === NTL-S4-011: 盘前链路回归测试 ===

@pytest.mark.asyncio
async def test_stage4_path_with_strategy_version(tmp_path: Path) -> None:
    """NTL-S4-011: Stage 4 路径下，TraderAgent 接收 strategy_version 并派生候选标的"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0, "600001.SH": 8.0}),
        stage4=Stage4Config(enable=True, allow_phase0_fallback=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],  # Phase 0 候选
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 20)

    # 构造一个 strategy_version（含 recommendations）
    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-20:draft:v1",
        trader_id="trader_a",
        strategy_date=day,
        status=StrategyVersionStatus.draft,
        recommendations=[
            StrategyRecommendation(symbol="600000.SH", decision="buy", confidence=0.72),
            StrategyRecommendation(symbol="600001.SH", decision="hold", confidence=0.65),
        ],
    )

    # Mock StrategyLibraryService.get_current_released_version
    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(return_value=strategy_version)

    report = await manager.run_pre_market(as_of_date=day, force=True)

    # Stage 4 路径：候选来自 strategy_version.recommendations，不是 watchlist
    symbols = {idea.symbol for idea in report.ideas}
    assert symbols == {"600000.SH", "600001.SH"}
    # watchlist 中的 000001.SZ 不在候选中
    assert "000001.SZ" not in symbols


@pytest.mark.asyncio
async def test_phase0_fallback_when_no_strategy_version(tmp_path: Path) -> None:
    """NTL-S4-011: Phase 0 降级路径：strategy_version 不可用时使用 watchlist"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.0}),
        stage4=Stage4Config(enable=True, allow_phase0_fallback=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 20)

    # Mock StrategyLibraryService 抛出异常（模拟 DB 不可用）
    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(side_effect=RuntimeError("DB unavailable"))

    # 不应抛出异常，降级到 Phase 0
    report = await manager.run_pre_market(as_of_date=day, force=True)

    # Phase 0 路径：候选来自 watchlist
    assert len(report.ideas) == 1
    assert report.ideas[0].symbol == "000001.SZ"
    assert report.ideas[0].strategy_version_id is None


@pytest.mark.asyncio
async def test_allow_phase0_false_skips_trader(tmp_path: Path) -> None:
    """NTL-S4-011: allow_phase0_fallback=False 时，strategy_version 不可用则跳过 trader"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.0}),
        stage4=Stage4Config(enable=True, allow_phase0_fallback=False),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=["000001.SZ"],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 20)

    # Mock StrategyLibraryService 抛出异常
    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(side_effect=RuntimeError("DB unavailable"))

    # 不应抛出异常，但 trader 被跳过（无 ideas）
    report = await manager.run_pre_market(as_of_date=day, force=True)
    assert len(report.ideas) == 0


@pytest.mark.asyncio
async def test_daily_report_includes_strategy_version_ids(tmp_path: Path) -> None:
    """NTL-S4-011: DailyReport.strategy_version_ids 包含本次使用的策略版本"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0}),
        stage4=Stage4Config(enable=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=[],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 20)

    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-20:released:v2",
        trader_id="trader_a",
        strategy_date=day,
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="600000.SH", decision="buy", confidence=0.72),
        ],
    )

    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(return_value=strategy_version)

    report = await manager.run_pre_market(as_of_date=day, force=True)

    # strategy_version_ids 应包含本次使用的版本 ID
    assert "trader_a:2026-04-20:released:v2" in report.strategy_version_ids


@pytest.mark.asyncio
async def test_trade_idea_side_reflects_strategy_decision(tmp_path: Path) -> None:
    """NTL-S4-011: StrategyVersion.recommendations 的 decision 正确传递到 TradeIdea.side"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0, "600001.SH": 9.0}),
        stage4=Stage4Config(enable=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=[],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 20)

    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-20:draft:v1",
        trader_id="trader_a",
        strategy_date=day,
        status=StrategyVersionStatus.draft,
        recommendations=[
            StrategyRecommendation(symbol="600000.SH", decision="buy", confidence=0.72),
            StrategyRecommendation(symbol="600001.SH", decision="sell", confidence=0.55),
        ],
    )

    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(return_value=strategy_version)

    report = await manager.run_pre_market(as_of_date=day, force=True)

    buy_idea = next(i for i in report.ideas if i.symbol == "600000.SH")
    assert buy_idea.side == "buy"

    sell_idea = next(i for i in report.ideas if i.symbol == "600001.SH")
    assert sell_idea.side == "sell"


@pytest.mark.asyncio
async def test_market_universe_snapshot_populated_in_signal(tmp_path: Path) -> None:
    """NTL-S4-TD003: SignalContext.market_universe_snapshot 应被实际填充"""
    config = AppConfig(
        storage=StorageConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0}),
        stage4=Stage4Config(enable=True, market_universe_slot="09-25", allow_phase0_fallback=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                watchlist=[],
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 20)

    # 预先保存 market_universe snapshot
    market_universe = MarketUniverse(
        trade_date="2026-04-20",
        slot="09-25",
        hot_topics=HotTopicsPayload(
            trade_date="2026-04-20",
            slot="09-25",
            topics=[HotTopic(kind="concept", topic_id="AI001", topic_name="人工智能", score=85.0)],
            sources=["test"],
        ),
    )
    manager.snapshot_service.save(market_universe)

    strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-20:draft:v1",
        trader_id="trader_a",
        strategy_date=day,
        status=StrategyVersionStatus.draft,
        recommendations=[
            StrategyRecommendation(symbol="600000.SH", decision="buy", confidence=0.72),
        ],
    )
    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(return_value=strategy_version)

    report = await manager.run_pre_market(as_of_date=day, force=True)

    # 验证信号中 market_universe_snapshot 已填充
    idea = report.ideas[0]
    signal_id = f"idea_{idea.idea_id}"
    stored = manager.signal_versioning.get_version(signal_id)
    assert stored is not None
    assert stored.context.market_universe_snapshot is not None
    assert stored.context.market_universe_snapshot["trade_date"] == "2026-04-20"
    assert stored.context.market_universe_snapshot["slot"] == "09-25"
    assert "hot_topics" in stored.context.market_universe_snapshot
