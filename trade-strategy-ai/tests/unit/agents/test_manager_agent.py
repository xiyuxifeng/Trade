from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4
import json

import pytest

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import AppConfig, DataConfig, StorageConfig, TraderConfig
from src.schemas.contracts import DailyReport, TradeEntry, TradeIdea
from src.trader_memory.schemas import TraderMemoryType
from src.trader_memory.service import TraderMemoryStore, default_memory_path
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

    result = await manager.run_after_close(as_of_date=day, force=True)
    assert result.evaluations[0].status == "ok"

    memory_path = default_memory_path(base_dir=tmp_path, config=config)
    store = TraderMemoryStore(path=memory_path)
    memories = store.list_recent(trader_id="trader_a", limit=10)
    assert len(memories) == 1
    assert memories[0].symbol == "000001.SZ"

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

    result = await manager.run_after_close(as_of_date=day, force=True)
    assert result.evaluations[0].status == "ok"

    tasks = manager.tasks_path.read_text(encoding="utf-8").splitlines()
    review_tasks = [json.loads(line) for line in tasks if json.loads(line)["type"] == "trader_review"]
    assert len(review_tasks) == 1
    details = review_tasks[0]["details"]
    assert details["review_type"] == "trader_review"
    assert details["trigger_reason"] == "loss"
    assert details["evaluation_snapshot"]["threshold"] == 0.0

    memory_path = default_memory_path(base_dir=tmp_path, config=config)
    store = TraderMemoryStore(path=memory_path)
    review_notes = store.list_recent(trader_id="trader_a", limit=10, memory_types=[TraderMemoryType.review_note])
    assert len(review_notes) == 1
    assert review_notes[0].symbol == "000001.SZ"


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
    assert stored.signal.side == SignalSide.HOLD
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
        timestamp=datetime.utcnow(),
        metadata={}
    )):
        # Mock RiskAgent
        with patch.object(manager.risk_agent, 'check', return_value=Signal(
            signal_id="test",
            symbol="000001",
            side=SignalSide.BUY,
            confidence=0.75,
            timestamp=datetime.utcnow(),
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
