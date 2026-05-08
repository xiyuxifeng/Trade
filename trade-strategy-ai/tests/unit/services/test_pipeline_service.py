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

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    calls: dict[str, object] = {}

    def fake_crawl(*, config_path: Path, max_articles: int | None = None):
        calls["crawl"] = (config_path, max_articles)
        return ["line-1", "line-2"]

    async def fake_pipeline(**kwargs):
        calls["pipeline"] = kwargs
        return _FakePipelineResult(name="pipeline", nested=_FakeNested(value="ok"))

    service = PipelineService(
        crawl_runner=fake_crawl,
        pipeline_runner=fake_pipeline,
    )

    crawl_result = service.crawl(config_path=config_path, max_articles=12)
    run_result = asyncio.run(
        service.run_pipeline(
            config_path=config_path,
            max_articles=5,
            force=True,
            skip_crawl=False,
            from_step="clean",
            use_db=True,
            new_version="v2",
        )
    )
    pipeline_call = dict(calls["pipeline"])
    step_result = asyncio.run(
        service.run_pipeline_step(
            step="store",
            config_path=config_path,
            max_articles=3,
            force=False,
            use_db=False,
            new_version="v3",
        )
    )
    step_call = dict(calls["pipeline"])

    assert crawl_result.payload["lines"] == ["line-1", "line-2"]
    assert calls["crawl"] == (tmp_path / "config" / "app.yaml", 12)
    assert run_result.payload["result"]["name"] == "pipeline"
    assert run_result.payload["result"]["nested"]["value"] == "ok"
    assert pipeline_call["from_step"] == "clean"
    assert step_result.payload["result"]["nested"]["value"] == "ok"
    assert step_call["from_step"] == "store"


def test_pipeline_service_runs_extract_and_clusters(tmp_path: Path) -> None:
    """PipelineService 应能封装抽取与聚类构建。"""
    from src.services.pipeline_service import PipelineService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    calls: dict[str, object] = {}

    @dataclass
    class _FakeExtractStats:
        scanned: int = 8
        extracted: int = 3
        skipped: int = 2
        failed: int = 1

    async def fake_extract(**kwargs):
        calls["extract"] = kwargs
        return _FakeExtractStats()

    async def fake_build_clusters(**kwargs):
        calls["clusters"] = kwargs
        @dataclass
        class _FakeClustersStats:
            scanned_articles: int = 5
            used_articles: int = 4
            clusters_built: int = 2

        return (Path("/tmp/clusters.json"), _FakeClustersStats())

    service = PipelineService(
        extract_metadata_runner=fake_extract,
        build_clusters_runner=fake_build_clusters,
    )

    extract_result = asyncio.run(
        service.extract_articles(
            config_path=config_path,
            limit=20,
            force=True,
            version="v2",
        )
    )
    clusters_result = asyncio.run(
        service.build_clusters(
            config_path=config_path,
            dest=tmp_path / "clusters.json",
            max_articles=40,
        )
    )

    assert extract_result.payload["stats"]["extracted"] == 3
    assert calls["extract"]["force"] is True
    assert calls["extract"]["version"] == "v2"
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
