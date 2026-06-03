from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class _FakeNested:
    value: str


@dataclass
class _FakePipelineResult:
    name: str
    nested: _FakeNested


class _FakeManager:
    def __init__(self) -> None:
        self.pre_market_calls: list[tuple[date, bool]] = []
        self.after_close_calls: list[tuple[date, bool]] = []

    async def run_pre_market(self, *, as_of_date: date, force: bool = False):
        self.pre_market_calls.append((as_of_date, force))
        return type("Report", (), {"ideas": [1, 2], "model_dump": lambda self: {"kind": "report"}})()

    def export_daily_report_html(self, *, report) -> Path:
        return Path("/tmp/daily_report.html")

    async def run_after_close(self, *, as_of_date: date, force: bool = False):
        self.after_close_calls.append((as_of_date, force))
        return type(
            "Result",
            (),
            {"evaluations": [1], "model_dump": lambda self: {"kind": "evaluation"}},
        )()

    def export_evaluation_html(self, *, result) -> Path:
        return Path("/tmp/evaluation.html")


def test_pipeline_service_runs_crawl_and_pipeline_steps(tmp_path: Path, monkeypatch) -> None:
    """PipelineService 应能封装 crawl、pipeline-run 和 pipeline-step。"""
    from src.services.pipeline_service import PipelineService
    from src.common.config import load_app_config
    from types import SimpleNamespace

    calls: dict[str, object] = {}

    async def fake_pipeline(**kwargs):
        calls["pipeline"] = kwargs
        return _FakePipelineResult(name="pipeline", nested=_FakeNested(value="ok"))

    async def fake_run_crawl_to_db(
        config,
        *,
        max_articles: int | None = None,
        force: bool = False,
        progress_callback=None,
    ):
        calls["crawl"] = (config, max_articles, force, progress_callback)
        return ["line-1", "line-2"]

    monkeypatch.setattr("src.services.pipeline_service.run_crawl_to_db", fake_run_crawl_to_db)
    loaded = load_app_config(Path("/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/config/app.yaml"))

    async def fake_load_profile_runtime_config(profile_id: str):
        return SimpleNamespace(
            profile_id=profile_id,
            config=loaded.config,
            base_dir=Path("/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai"),
            profile_snapshot_id="profile-snapshot-default",
        )

    monkeypatch.setattr(
        "src.services.pipeline_service.ConfigProfileService",
        lambda: SimpleNamespace(load_profile_runtime_config=fake_load_profile_runtime_config),
    )
    service = PipelineService(
        pipeline_runner=fake_pipeline,
    )

    crawl_result = asyncio.run(service.crawl(profile_id="default", max_articles=12))
    run_result = asyncio.run(
        service.run_pipeline(
            profile_id="default",
            max_articles=5,
            force=True,
            skip_crawl=False,
            from_step="clean",
            use_db=True,
            retry_failed=True,
            new_version="v2",
        )
    )
    pipeline_call = dict(calls["pipeline"])
    step_result = asyncio.run(
        service.run_pipeline_step(
            step="store",
            profile_id="default",
            max_articles=3,
            force=True,
            use_db=False,
            new_version="v3",
        )
    )
    step_call = dict(calls["pipeline"])

    assert crawl_result.payload["lines"] == ["line-1", "line-2"]
    assert calls["crawl"][1:] == (12, False, None)
    assert run_result.payload["result"]["name"] == "pipeline"
    assert run_result.payload["result"]["nested"]["value"] == "ok"
    assert pipeline_call["from_step"] == "clean"
    assert pipeline_call["retry_failed"] is True
    assert step_result.payload["result"]["nested"]["value"] == "ok"
    assert step_call["from_step"] == "store"
    assert step_call["force"] is True


def test_pipeline_service_run_pipeline_step_limits_to_current_step(tmp_path: Path, monkeypatch) -> None:
    """PipelineService 的单步入口应只执行当前 step，不继续后续步骤。"""
    from src.services.pipeline_service import PipelineService
    from src.common.config import load_app_config
    from types import SimpleNamespace

    calls: dict[str, object] = {}

    async def fake_pipeline(**kwargs):
        calls["pipeline"] = kwargs
        return _FakePipelineResult(name="pipeline", nested=_FakeNested(value="ok"))

    loaded = load_app_config(Path("/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/config/app.yaml"))

    async def fake_load_profile_runtime_config(profile_id: str):
        return SimpleNamespace(
            profile_id=profile_id,
            config=loaded.config,
            base_dir=Path("/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai"),
            profile_snapshot_id="profile-snapshot-default",
        )

    monkeypatch.setattr(
        "src.services.pipeline_service.ConfigProfileService",
        lambda: SimpleNamespace(load_profile_runtime_config=fake_load_profile_runtime_config),
    )
    service = PipelineService(
        pipeline_runner=fake_pipeline,
    )

    asyncio.run(
        service.run_pipeline_step(
            step="process",
            profile_id="default",
            max_articles=3,
            force=True,
            use_db=True,
            new_version="v3",
        )
    )

    pipeline_call = dict(calls["pipeline"])
    assert pipeline_call["from_step"] == "process"
    assert pipeline_call["until_step"] == "process"


def test_pipeline_service_runs_clusters_build(tmp_path: Path) -> None:
    """PipelineService 应能封装聚类构建（extract-articles 已合并到 pipeline-step process）。"""
    from src.services.pipeline_service import PipelineService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    calls: dict[str, object] = {}

    async def fake_build_clusters(**kwargs):
        calls["clusters"] = kwargs
        @dataclass
        class _FakeClustersStats:
            scanned_articles: int = 5
            used_articles: int = 4
            clusters_built: int = 2

        return (Path("/tmp/clusters.json"), _FakeClustersStats())

    service = PipelineService(
        build_clusters_runner=fake_build_clusters,
    )

    clusters_result = asyncio.run(
        service.build_clusters(
            config_path=config_path,
            dest=tmp_path / "clusters.json",
            max_articles=40,
        )
    )

    assert clusters_result.payload["dest"] == "/tmp/clusters.json"
    assert calls["clusters"]["dest"] == tmp_path / "clusters.json"
    assert clusters_result.payload["stats"]["clusters_built"] == 2


def test_pipeline_service_runs_e2e_regression(tmp_path: Path) -> None:
    """PipelineService 应能串起 e2e 回归链路。"""
    from src.services.pipeline_service import PipelineService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
timezone: Asia/Shanghai
traders:
  - trader_id: trader_a
    display_name: Trader A
""",
        encoding="utf-8",
    )

    calls: dict[str, object] = {}

    async def fake_pipeline(**kwargs):
        calls["pipeline"] = kwargs
        return _FakePipelineResult(name="pipeline", nested=_FakeNested(value="ok"))

    async def fake_extract(**kwargs):
        calls["extract"] = kwargs
        return type("Stats", (), {"scanned": 1, "extracted": 1, "skipped": 0, "failed": 0})()

    async def fake_build_clusters(**kwargs):
        calls["clusters"] = kwargs
        return (Path("/tmp/clusters.real.json"), type("Stats", (), {"scanned_articles": 2, "used_articles": 2, "clusters_built": 1})())

    async def fake_build_profiles(**kwargs):
        calls["profiles"] = kwargs
        return type("Profiles", (), {"model_dump": lambda self: {"kind": "profiles"}})()

    def fake_write_profiles(*, path, data):
        calls["write_profiles"] = (path, data)
        return path

    service = PipelineService(
        pipeline_runner=fake_pipeline,
        extract_metadata_runner=fake_extract,
        build_clusters_runner=fake_build_clusters,
        build_trader_profiles_runner=fake_build_profiles,
        write_trader_profiles_runner=fake_write_profiles,
        manager_factory=lambda *, config, base_dir: _FakeManager(),
    )

    result = asyncio.run(
        service.e2e_regression(
            config_path=config_path,
            max_articles=10,
            extract_limit=7,
            clusters_dest=tmp_path / "clusters.real.json",
        )
    )

    assert result.status == "ok"
    assert result.payload["clusters_path"] == "/tmp/clusters.real.json"
    assert calls["clusters"]["dest"] == tmp_path / "clusters.real.json"
    assert result.payload["daily_report"]["kind"] == "report"
    assert result.payload["evaluation"]["kind"] == "evaluation"
    assert calls["pipeline"]["max_articles"] == 10
    assert calls["extract"]["total_limit"] == 7
    assert calls["profiles"]["max_articles_per_trader"] == 7
