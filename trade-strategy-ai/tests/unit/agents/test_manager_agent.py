from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import AppConfig, DataConfig, StorageConfig, TraderConfig
from src.schemas.contracts import DailyReport, TradeEntry, TradeIdea
from src.trader_memory.schemas import TraderMemoryType
from src.trader_memory.service import TraderMemoryStore, default_memory_path


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
