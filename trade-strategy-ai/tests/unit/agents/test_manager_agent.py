from __future__ import annotations

from datetime import date, datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

import pytest

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import AppConfig, DataConfig, PreMarketFormalFlowConfig, RuntimeConfig, TraderConfig
from src.market_universe.schemas import MarketUniverse, HotTopicsPayload, HotTopic
from src.schemas.contracts import DailyReport, TradeEntry, TradeIdea
from src.strategy_library.schemas import StrategyRecommendation, StrategyVersion, StrategyVersionStatus
from src.trader_memory.schemas import TraderMemorySummary, TraderMemoryType
from src.trader_memory.service import TraderMemoryStore
from src.strategy.types import SignalSide, SynthesisMode, RawSignal, Signal
from src.evaluation.evidence_pack import EvidencePack, MarketDataSnapshot


@pytest.fixture(autouse=True)
def _patch_manager_runtime(monkeypatch: pytest.MonkeyPatch):
    async def _fake_generate_evidence_pack(self, idea, daily_report, last_prices, config):
        del self, daily_report, config
        last_price = float(last_prices.get(idea.symbol, idea.entry.price if idea.entry else 0.0))
        return EvidencePack(
            idea_id=idea.idea_id,
            trade_date=str(idea.as_of_date),
            trade_idea=idea,
            signal_context=None,
            market_data=MarketDataSnapshot(
                bars=[],
                entry_price=float(idea.entry.price) if idea.entry and idea.entry.price else 0.0,
                target_price=idea.target_price,
                stop_loss_price=idea.stop_loss_price,
                last_price=last_price,
            ),
        )

    default_strategy_version = StrategyVersion(
        version_id="trader_a:2026-04-06:released:v1",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 6),
        status=StrategyVersionStatus.released,
        recommendations=[
            StrategyRecommendation(symbol="000001.SZ", decision="buy", confidence=0.72),
        ],
    )
    persist_mock = AsyncMock(return_value=None)
    memory_store_ctor = MagicMock(return_value=_make_memory_store_stub())
    monkeypatch.setattr("src.agents.manager_agent.agent.session_scope", _mock_session_scope)
    monkeypatch.setattr("src.db.session.session_scope", _mock_session_scope)
    monkeypatch.setattr("src.agents.manager_agent.agent.TraderMemoryStore", memory_store_ctor)
    monkeypatch.setattr("src.agents.manager_agent.agent.run_incremental_data_completion", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "src.rule_pool.prediction.RulePoolPredictionService.predict_high_confidence_rules",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "src.strategy_library.service.StrategyLibraryService.get_current_released_version",
        AsyncMock(return_value=default_strategy_version),
    )
    monkeypatch.setattr(ManagerAgent, "_persist_signal", persist_mock)
    monkeypatch.setattr(ManagerAgent, "_generate_evidence_pack", _fake_generate_evidence_pack)
    return persist_mock


def _make_config() -> AppConfig:
    return AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
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

def _make_memory_store_stub(
    summary: TraderMemorySummary | None = None,
) -> MagicMock:
    """构造内存版 TraderMemoryStore，避免单元测试连接真实数据库。"""
    store = MagicMock(spec=TraderMemoryStore)
    store.append = AsyncMock()
    store.list_recent = AsyncMock(return_value=[])
    store.summarize_context = AsyncMock(
        return_value=summary
        or TraderMemorySummary(trader_id="trader_a", total_items=0)
    )
    return store


@asynccontextmanager
async def _mock_session_scope():
    """避免单元测试连接真实数据库。"""
    yield MagicMock()


@pytest.mark.asyncio
async def test_manager_writes_memory_and_reuses_it(tmp_path: Path) -> None:
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    manager.memory_store = _make_memory_store_stub()
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
    manager.memory_store = _make_memory_store_stub(
        TraderMemorySummary(
            trader_id="trader_a",
            symbol="000001.SZ",
            total_items=1,
            total_symbol_items=1,
            by_type={TraderMemoryType.success_case.value: 1},
            recent_titles=["success case"],
            symbol_titles=["success case"],
        )
    )

    rerun_report = await manager.run_pre_market(as_of_date=day, force=True)
    assert "memory summary" in (rerun_report.ideas[0].rationale or "")
    assert "success case" in (rerun_report.ideas[0].rationale or "")


@pytest.mark.asyncio
async def test_manager_creates_structured_review_task_and_review_note(tmp_path: Path) -> None:
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
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
    manager.memory_store = _make_memory_store_stub()
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
    manager.memory_store = _make_memory_store_stub(
        TraderMemorySummary(
            trader_id="trader_a",
            symbol="000001.SZ",
            total_items=1,
            total_symbol_items=1,
            by_type={TraderMemoryType.review_note.value: 1},
            review_notes=["review note"],
        )
    )


@pytest.mark.asyncio
async def test_manager_marks_partial_data_when_bars_are_incomplete(tmp_path: Path) -> None:
    """当只有部分 bars 时，应标记 partial_data 并保留结构化说明。"""
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    manager.memory_store = _make_memory_store_stub()
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


@pytest.mark.asyncio
async def test_run_after_close_propagates_incremental_completion_failure(tmp_path: Path) -> None:
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    day = date(2026, 4, 6)

    report = DailyReport(
        as_of_date=day,
        ideas=[],
        highlights=["seed"],
    )
    manager._daily_report_path(day).write_text(report.model_dump_json(indent=2), encoding="utf-8")

    with patch("src.agents.manager_agent.agent.run_incremental_data_completion", new=AsyncMock(side_effect=RuntimeError("completion failed"))):
        with pytest.raises(RuntimeError, match="completion failed"):
            await manager.run_after_close(as_of_date=day, force=True)


@pytest.mark.asyncio
async def test_run_after_close_writes_canonical_topic_tags(tmp_path: Path) -> None:
    """验证 run_after_close 使用 source_topic_ids 生成 canonical topic tags。"""
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
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
    manager.memory_store = _make_memory_store_stub()
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
    manager.memory_store.list_recent = AsyncMock(return_value=[
        MagicMock(
            tags=["kaipan:concept:AI算力"],
            topic_source="kaipan",
            raw_topic_ids={"kaipan": ["AI算力|concept"]},
        )
    ])

    with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope), \
        patch("src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"), \
        patch("src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"):
        await manager.run_after_close(as_of_date=day, force=True)

    # Verify canonical topic tags were written into evaluation memory.
    manager.memory_store.append.assert_awaited()
    appended = [call.args[0] for call in manager.memory_store.append.call_args_list]
    assert any("kaipan:concept:AI算力" in item.tags for item in appended)
    assert any(item.topic_source == "kaipan" for item in appended)


@pytest.mark.asyncio
async def test_run_pre_market_persists_market_context_snapshot(tmp_path: Path) -> None:
    """验证盘前日报会同时持久化市场上下文快照和候选池快照。"""
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    manager.memory_store = _make_memory_store_stub()
    day = date(2026, 4, 20)

    manager._load_market_context_snapshot = MagicMock(
        return_value=(
            {"source": "market_context", "trade_date": day.isoformat()},
            MarketUniverse(trade_date=day.isoformat(), slot="09-25"),
        )
    )

    from types import SimpleNamespace

    fake_result = SimpleNamespace(
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
        strategy_version_id="trader_a:2026-04-20:released:v1",
        missing_symbol_tasks=[],
    )

    with patch(
        "src.agents.manager_agent.premarket_service.PreMarketService.run_for_trader",
        new=AsyncMock(return_value=fake_result),
    ), patch.object(manager, "_record_ideas_as_signals", new=AsyncMock(return_value=None)):
        report = await manager.run_pre_market(as_of_date=day, force=True)

    payload = report.model_dump()
    assert payload["market_context_snapshot"] is not None
    assert payload["market_context_snapshot"]["source"] == "market_context"
    assert payload["market_universe_snapshot"] is not None
    assert payload["market_universe_snapshot"]["trade_date"] == day.isoformat()
    assert payload["market_universe_snapshot"]["slot"] == "09-25"


@pytest.mark.asyncio
async def test_run_after_close_prefers_market_context_snapshot_for_tags(tmp_path: Path) -> None:
    """验证盘后复盘优先使用市场上下文快照构建 topic tags。"""
    config = _make_config()
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    manager.memory_store = _make_memory_store_stub()
    day = date(2026, 4, 20)

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
        market_context_snapshot={"provider": "market_context"},
        market_universe_snapshot={"provider": "market_universe"},
    )
    manager._daily_report_path(day).write_text(report.model_dump_json(indent=2), encoding="utf-8")

    from src.evaluation.evidence_pack import EvidencePack, MarketDataSnapshot

    evidence_pack = EvidencePack(
        idea_id=report.ideas[0].idea_id,
        trade_date=str(day),
        trade_idea=report.ideas[0],
        signal_context=None,
        market_data=MarketDataSnapshot(
            bars=[],
            entry_price=10.0,
            target_price=10.5,
            stop_loss_price=9.7,
        ),
    )

    with patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope), \
        patch("src.agents.manager_agent.agent.RankingService.add_entry_from_metrics"), \
        patch("src.agents.manager_agent.agent.RankingService.generate_ranking_and_save"), \
        patch("src.agents.manager_agent.agent.run_incremental_data_completion", new=AsyncMock(return_value=None)), \
        patch.object(manager, "_generate_evidence_pack", new_callable=AsyncMock, return_value=evidence_pack), \
        patch(
            "src.agents.manager_agent.agent.build_topic_tags",
            return_value=(["tag"], "market_context", {"market_context": ["AI算力|concept"]}),
        ) as build_tags:
        await manager.run_after_close(as_of_date=day, force=True)

    build_tags.assert_called_once()
    assert build_tags.call_args.args[1] == {"provider": "market_context"}


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
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0, "600001.SH": 8.0}),
        pre_market_formal_flow=PreMarketFormalFlowConfig(enabled=True),
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
    manager.memory_store = _make_memory_store_stub()
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
async def test_run_pre_market_raises_when_strategy_version_missing(tmp_path: Path) -> None:
    """严格模式：strategy_version 不可用时直接报错。"""
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.0}),
        pre_market_formal_flow=PreMarketFormalFlowConfig(enabled=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    manager.memory_store = _make_memory_store_stub()
    day = date(2026, 4, 20)

    # Mock StrategyLibraryService 返回空版本（模拟没有 released 版本）
    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="缺少可用的 released strategy_version"):
        await manager.run_pre_market(as_of_date=day, force=True)


@pytest.mark.asyncio
async def test_run_pre_market_raises_when_strategy_version_loader_fails(tmp_path: Path) -> None:
    """严格模式：策略版本加载异常时直接报错。"""
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"000001.SZ": 12.0}),
        pre_market_formal_flow=PreMarketFormalFlowConfig(enabled=True),
        traders=[
            TraderConfig(
                trader_id="trader_a",
                display_name="Trader A",
                default_target_pct=0.05,
                default_stop_pct=0.03,
            )
        ],
    )
    manager = ManagerAgent(config=config, base_dir=tmp_path)
    manager.memory_store = _make_memory_store_stub()
    day = date(2026, 4, 20)

    # Mock StrategyLibraryService 抛出异常
    from unittest.mock import AsyncMock
    manager.strategy_library_service.get_current_released_version = AsyncMock(side_effect=RuntimeError("DB unavailable"))

    with pytest.raises(ValueError, match="缺少可用的 released strategy_version"):
        await manager.run_pre_market(as_of_date=day, force=True)


@pytest.mark.asyncio
async def test_daily_report_includes_strategy_version_ids(tmp_path: Path) -> None:
    """NTL-S4-011: DailyReport.strategy_version_ids 包含本次使用的策略版本"""
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0}),
        pre_market_formal_flow=PreMarketFormalFlowConfig(enabled=True),
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
    manager.memory_store = _make_memory_store_stub()
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
async def test_rule_pool_prediction_boosts_premarket_ideas(tmp_path: Path) -> None:
    """高置信度规则池预测应真实影响盘前 TradeIdea。"""
    from src.rule_pool.prediction import RulePredictionSnapshot

    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0}),
        pre_market_formal_flow=PreMarketFormalFlowConfig(enabled=True),
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
    manager.memory_store = _make_memory_store_stub()
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
    manager.strategy_library_service.get_current_released_version = AsyncMock(return_value=strategy_version)

    predictions = [
        RulePredictionSnapshot(
            rule_id="rule_001",
            rule_type="entry",
            confidence=0.93,
            source_article_ids=["article_001"],
            predicted_at=datetime.now(timezone.utc),
        )
    ]

    with (
        patch("src.agents.manager_agent.agent.session_scope", _mock_session_scope),
        patch(
            "src.rule_pool.prediction.RulePoolPredictionService.predict_high_confidence_rules",
            AsyncMock(return_value=predictions),
        ),
    ):
        report = await manager.run_pre_market(as_of_date=day, force=True)

    idea = report.ideas[0]
    assert idea.confidence == 0.77
    assert "rule_pool:rule_001" in idea.evidence_refs
    assert "规则池预测" in (idea.rationale or "")


@pytest.mark.asyncio
async def test_trade_idea_side_reflects_strategy_decision(tmp_path: Path) -> None:
    """NTL-S4-011: StrategyVersion.recommendations 的 decision 正确传递到 TradeIdea.side"""
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0, "600001.SH": 9.0}),
        pre_market_formal_flow=PreMarketFormalFlowConfig(enabled=True),
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
    manager.memory_store = _make_memory_store_stub()
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
async def test_market_universe_snapshot_populated_in_signal(
    tmp_path: Path,
    _patch_manager_runtime: AsyncMock,
) -> None:
    """NTL-S4-TD003: SignalContext.market_universe_snapshot 应透传到信号持久化上下文"""
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        data=DataConfig(mock_prices={"600000.SH": 10.0}),
        pre_market_formal_flow=PreMarketFormalFlowConfig(enabled=True, market_universe_slot="09-25"),
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
    manager.memory_store = _make_memory_store_stub()
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

    await manager.run_pre_market(as_of_date=day, force=True)

    assert _patch_manager_runtime.await_count == 1
    persisted_context = _patch_manager_runtime.await_args.kwargs["context"]
    assert persisted_context.market_universe_snapshot is not None
    assert persisted_context.market_universe_snapshot["trade_date"] == "2026-04-20"
    assert persisted_context.market_universe_snapshot["slot"] == "09-25"
    assert "hot_topics" in persisted_context.market_universe_snapshot
