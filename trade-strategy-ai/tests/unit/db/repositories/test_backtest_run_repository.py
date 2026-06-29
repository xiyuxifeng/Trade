from __future__ import annotations

from pathlib import Path


def test_market_state_lookup_is_point_in_time_not_latest_substitution() -> None:
    source = (
        Path(__file__).parents[4]
        / "src/db/repositories/backtest_run_repository.py"
    ).read_text(encoding="utf-8")

    method_source = source.split("async def list_market_states_for_run", maxsplit=1)[1].split(
        "async def list_formal_samples_for_run",
        maxsplit=1,
    )[0]

    assert "MarketRegimeRecord.available_at" in method_source
    assert "MarketSnapshot.available_at <= MarketRegimeRecord.available_at" in method_source
    assert "candidate.available_at <= decision_time" in method_source
    assert "MarketRegimeRecord.available_at.desc()" in method_source
    assert "limit(1)" not in method_source


def test_dataset_snapshot_lookup_does_not_select_future_snapshot_for_backtest_end_date() -> None:
    source = (
        Path(__file__).parents[4]
        / "src/db/repositories/backtest_run_repository.py"
    ).read_text(encoding="utf-8")

    method_source = source.split("async def find_dataset_snapshot", maxsplit=1)[1].split(
        "async def list_market_snapshots",
        maxsplit=1,
    )[0]

    assert "DatasetSnapshot.date_to <= date_to" in method_source
    assert "DatasetSnapshot.date_to.desc()" in method_source
