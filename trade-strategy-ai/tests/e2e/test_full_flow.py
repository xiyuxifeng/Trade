from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cli.main import _e2e_regression_async, e2e_regression
from src.common.config import AppConfig, LoadedConfig, PersonaConfig, RuntimeConfig
from src.schemas.contracts import DailyReport
from src.trader_profile.schemas import TraderProfilesFile


pytestmark = pytest.mark.smoke


def _make_loaded_config(config_path: Path) -> LoadedConfig:
    config = AppConfig(
        runtime=RuntimeConfig(output_dir="data/processed/phase0"),
        persona=PersonaConfig(
            enable=False,
            clusters_path="data/processed/persona/clusters.sample.json",
            top_k=2,
        ),
    )
    return LoadedConfig(config=config, config_path=config_path)


def _make_daily_report(as_of: date) -> DailyReport:
    return DailyReport(
        as_of_date=as_of,
        generated_at=datetime.now(timezone.utc),
        highlights=["generated"],
        risks=[],
        ideas=[],
    )


def test_e2e_regression_delegates_to_smoke_gate_steps(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    config_path = project_root / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\n", encoding="utf-8")

    loaded = _make_loaded_config(config_path)

    async_helper = AsyncMock(return_value=None)

    with (
        patch("cli.main.load_app_config", return_value=loaded),
        patch("cli.main.apply_database_config_to_env") as apply_db,
        patch("cli.main._project_base_dir", return_value=project_root),
        patch("cli.main._alembic_config", return_value=MagicMock()) as alembic_cfg,
        patch("cli.main.command.upgrade") as upgrade,
        patch("cli.main._e2e_regression_async", async_helper),
    ):
        e2e_regression(
            config=config_path,
            max_articles=3,
            extract_limit=2,
            clusters_dest=Path("data/processed/persona/clusters.real.json"),
            log_level="INFO",
        )

    apply_db.assert_called_once_with(loaded.config)
    alembic_cfg.assert_called_once_with(project_root)
    upgrade.assert_called_once_with(alembic_cfg.return_value, "head")
    async_helper.assert_awaited_once()
    kwargs = async_helper.call_args.kwargs
    assert kwargs["config"] == config_path
    assert kwargs["max_articles"] == 3
    assert kwargs["extract_limit"] == 2
    assert kwargs["clusters_dest"] == Path("data/processed/persona/clusters.real.json")
    assert kwargs["base_dir"] == project_root
    assert kwargs["loaded_cfg"] == loaded


@pytest.mark.asyncio
async def test_e2e_regression_async_orchestrates_core_steps(tmp_path: Path) -> None:
    base_dir = tmp_path / "project"
    base_dir.mkdir()
    clusters_dest = Path("data/processed/persona/clusters.real.json")
    loaded = _make_loaded_config(base_dir / "config" / "app.yaml")

    run_pipeline_mock = AsyncMock(return_value=None)
    extract_mock = AsyncMock(return_value=SimpleNamespace(scanned=1, extracted=1, skipped=0, failed=0))
    build_clusters_mock = AsyncMock(return_value=(1, SimpleNamespace(scanned_articles=1, used_articles=1, clusters_built=1)))
    build_profiles_mock = AsyncMock(return_value=TraderProfilesFile())
    write_profiles_mock = MagicMock(return_value=base_dir / "data/processed/phase0/trader_profiles.json")

    manager = MagicMock()
    manager.run_pre_market = AsyncMock(return_value=_make_daily_report(date.today()))
    manager.run_after_close = AsyncMock(return_value=SimpleNamespace(evaluations=[SimpleNamespace(status="ok")]))
    manager.export_daily_report_html.return_value = base_dir / "data/processed/phase0/daily_report.html"
    manager.export_evaluation_html.return_value = base_dir / "data/processed/phase0/evaluation.html"
    manager_cls = MagicMock(return_value=manager)

    with (
        patch("cli.main.run_pipeline", run_pipeline_mock),
        patch("cli.main.extract_and_store_metadata", extract_mock),
        patch("cli.main.build_clusters_from_db", build_clusters_mock),
        patch("cli.main.build_trader_profiles", build_profiles_mock),
        patch("cli.main.write_trader_profiles_file", write_profiles_mock),
        patch("cli.main.ManagerAgent", manager_cls),
    ):
        await _e2e_regression_async(
            config=loaded.config_path,
            max_articles=7,
            extract_limit=4,
            clusters_dest=clusters_dest,
            base_dir=base_dir,
            loaded_cfg=loaded,
        )

    run_pipeline_mock.assert_awaited_once()
    pipeline_kwargs = run_pipeline_mock.call_args.kwargs
    assert pipeline_kwargs["config"] == loaded.config
    assert pipeline_kwargs["base_dir"] == base_dir
    assert pipeline_kwargs["max_articles"] == 7
    assert pipeline_kwargs["force"] is True
    assert pipeline_kwargs["skip_crawl"] is False

    extract_mock.assert_awaited_once_with(config=loaded.config, base_dir=base_dir, total_limit=4)

    full_clusters = base_dir / clusters_dest
    build_clusters_mock.assert_awaited_once_with(config=loaded.config, dest=full_clusters)
    build_profiles_mock.assert_awaited_once()
    write_profiles_mock.assert_called_once()
    manager_cls.assert_called_once()
    manager_kwargs = manager_cls.call_args.kwargs
    assert manager_kwargs["config"].persona.enable is True
    assert manager_kwargs["config"].persona.clusters_path == str(clusters_dest)
    assert manager_kwargs["base_dir"] == base_dir

    manager.run_pre_market.assert_awaited_once()
    pre_market_kwargs = manager.run_pre_market.call_args.kwargs
    assert pre_market_kwargs["as_of_date"] == date.today()
    assert pre_market_kwargs["force"] is True
    manager.export_daily_report_html.assert_called_once()
    manager.run_after_close.assert_awaited_once()
    after_close_kwargs = manager.run_after_close.call_args.kwargs
    assert after_close_kwargs["as_of_date"] == date.today()
    assert after_close_kwargs["force"] is True
    manager.export_evaluation_html.assert_called_once()
