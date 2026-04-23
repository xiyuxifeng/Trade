from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.kaipan_batch_fetch as kb


def test_build_jobs_defaults_to_eight_core_interfaces() -> None:
    jobs = kb.build_jobs(include_auxiliary=False, morning_pid_types=(0,), max_pages=2)
    assert [job.name for job in jobs] == [
        "board_strength",
        "industry_ranking",
        "concept_fengkou",
        "theme_detail",
        "stock_sector_v2",
        "strong_fengkou",
        "interval_stats_stock",
        "morning_bidding_list_pid0",
    ]


def test_build_jobs_includes_auxiliary_interfaces() -> None:
    jobs = kb.build_jobs(include_auxiliary=True, morning_pid_types=(0, 1), max_pages=3)
    assert [job.name for job in jobs[:9]] == [
        "board_strength",
        "industry_ranking",
        "concept_fengkou",
        "theme_detail",
        "stock_sector_v2",
        "strong_fengkou",
        "interval_stats_stock",
        "morning_bidding_list_pid0",
        "morning_bidding_list_pid1",
    ]
    assert [job.name for job in jobs[-5:]] == [
        "limit_up_reason",
        "pre_market_bid",
        "pre_market_stats",
        "limit_up_info",
        "lhb_list",
    ]


def test_get_recent_trading_dates_falls_back_to_weekdays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(kb, "_load_recent_trading_dates_from_akshare", lambda **kwargs: None)

    dates = kb.get_recent_trading_dates(end_date=date(2026, 4, 22), count=5)

    assert dates == [
        date(2026, 4, 16),
        date(2026, 4, 17),
        date(2026, 4, 20),
        date(2026, 4, 21),
        date(2026, 4, 22),
    ]


def test_run_batch_fetch_dry_run_writes_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class DummyProvider:
        def __init__(self, **kwargs: object) -> None:
            self.raw_dir = Path(kwargs["raw_dir"])
            self.snapshots_dir = Path(kwargs["snapshots_dir"])

    config = SimpleNamespace(kaipan=SimpleNamespace(data_dir="data/kaipan"))
    monkeypatch.setattr(
        kb,
        "load_app_config",
        lambda path: SimpleNamespace(config=config, config_path=Path(path)),
    )
    monkeypatch.setattr(kb, "KaipanProvider", DummyProvider)
    monkeypatch.setattr(
        kb,
        "get_recent_trading_dates",
        lambda **kwargs: [date(2026, 4, 21), date(2026, 4, 22)],
    )

    output_dir = tmp_path / "out"
    summary = kb.run_batch_fetch(
        config_path=tmp_path / "app.yaml",
        end_date=date(2026, 4, 22),
        days=2,
        output_dir=output_dir,
        log_level="INFO",
        theme_id="261",
        stock_id="002726",
        interval_window_days=20,
        morning_pid_types=(0,),
        max_pages=2,
        include_auxiliary=False,
        dry_run=True,
    )

    run_dir = Path(summary["output_dir"])
    summary_path = run_dir / "summary.json"
    assert summary["dry_run"] is True
    assert summary["planned_job_count"] == 8
    assert summary["job_names"] == [
        "board_strength",
        "industry_ranking",
        "concept_fengkou",
        "theme_detail",
        "stock_sector_v2",
        "strong_fengkou",
        "interval_stats_stock",
        "morning_bidding_list_pid0",
    ]
    assert summary_path.exists()

    with summary_path.open("r", encoding="utf-8") as f:
        persisted = json.load(f)
    assert persisted["trading_dates"] == ["2026-04-21", "2026-04-22"]
    assert persisted["planned_job_count"] == 8
