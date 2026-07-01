from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.backtest.schemas import BacktestResult, BacktestSummary, BacktestTradeRecord


@dataclass
class _FakeSummary:
    total_days: int = 3
    total_trades: int = 6
    valid_trades: int = 4
    skipped_trades: int = 2
    win_rate: float | None = 0.5
    avg_return_pct: float | None = 0.03


class _FakeEngine:
    def __init__(self) -> None:
        self.run_sync_calls: list[object] = []
        self.rule_pool_calls: list[dict[str, object]] = []

    def run_sync(self, request, progress_callback=None, runtime_state=None):
        self.run_sync_calls.append(
            {
                "request": request,
                "progress_callback": progress_callback,
                "runtime_state": runtime_state,
            }
        )
        return BacktestResult(
            request_trader_id=request.trader_id,
            request_date_from=request.date_from,
            request_date_to=request.date_to,
            records=[
                BacktestTradeRecord(
                    trade_date=request.date_from,
                    trader_id=request.trader_id,
                    strategy_version_id="sv-001",
                    symbol="000001.SZ",
                    status="closed",
                    return_pct=0.05,
                    entry_price=10.0,
                    exit_price=10.5,
                    mfe=None,
                    mae=None,
                    skip_reason=None,
                )
            ],
            summary=BacktestSummary(
                total_days=_FakeSummary().total_days,
                total_trades=_FakeSummary().total_trades,
                valid_trades=_FakeSummary().valid_trades,
                skipped_trades=_FakeSummary().skipped_trades,
                win_rate=_FakeSummary().win_rate,
                avg_return_pct=_FakeSummary().avg_return_pct,
            ),
        )

    async def run_rules_backtest(self, **kwargs):
        self.rule_pool_calls.append(kwargs)
        return BacktestResult(
            request_trader_id="rule_pool",
            request_date_from=kwargs["start_date"],
            request_date_to=kwargs["end_date"],
            records=[
                BacktestTradeRecord(
                    trade_date=kwargs["end_date"],
                    trader_id="rule_pool",
                    strategy_version_id="rule-001",
                    symbol="RULE:rule-001",
                    status="closed",
                    return_pct=0.02,
                    entry_price=None,
                    exit_price=None,
                    mfe=None,
                    mae=None,
                    skip_reason=None,
                )
            ],
            summary=BacktestSummary(
                total_days=_FakeSummary().total_days,
                total_trades=_FakeSummary().total_trades,
                valid_trades=_FakeSummary().valid_trades,
                skipped_trades=_FakeSummary().skipped_trades,
                win_rate=_FakeSummary().win_rate,
                avg_return_pct=_FakeSummary().avg_return_pct,
            ),
        )


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False

    async def scalars(self, stmt):
        class _Result:
            def all(self) -> list[object]:
                return []

        return _Result()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.closed = True


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return _FakeSession()


def test_backtest_service_runs_backtest_and_renders_report() -> None:
    """BacktestService 应封装回测执行与报告渲染。"""
    from src.services.backtest_service import BacktestService

    engine = _FakeEngine()
    service = BacktestService(engine_factory=lambda **kwargs: engine)

    run_result = service.run_backtest(
        trader_id="trader_a",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 3),
        strategy_version_id="sv-001",
        symbols=["000001.SZ"],
        benchmark_symbol="000300.SH",
        market_regime_version="market-regime-v1",
        mode="full",
        config_path="config/app.yaml",
        use_snapshot_only=True,
        scoring_profile="stage5",
        runtime_state={"checkpoint": {"trade_date_index": 1, "records": []}},
    )

    rendered = service.render_backtest_report(
        run_result.payload["result"],
        format="markdown",
    )

    assert run_result.status == "ok"
    assert run_result.payload["request"]["trader_id"] == "trader_a"
    assert run_result.payload["request"]["symbols"] == ["000001.SZ"]
    assert run_result.payload["request"]["benchmark_symbol"] == "000300.SH"
    assert run_result.payload["request"]["market_regime_version"] == "market-regime-v1"
    assert run_result.payload["request"]["use_snapshot_only"] is True
    assert run_result.payload["request"]["scoring_profile"] == "stage5"
    assert run_result.payload["result"]["summary"]["total_trades"] == 6
    assert len(run_result.payload["fingerprint"]) == 64
    assert "Backtest Report" in rendered.payload["content"]
    assert len(engine.run_sync_calls) == 1
    assert engine.run_sync_calls[0]["runtime_state"]["checkpoint"]["trade_date_index"] == 1


def test_backtest_service_validates_rules_and_produces_report() -> None:
    """BacktestService 应封装规则验真与报告输出。"""
    from src.services.backtest_service import BacktestService

    engine = _FakeEngine()
    rule_validation_calls: list[dict[str, object]] = []

    async def _rule_validation_runner(**kwargs):
        rule_validation_calls.append(kwargs)
        return [
            SimpleNamespace(
                trader_id="trader_a",
                strategy_version_id="sv-001",
                rule_id="rule-001",
                rule_text="rsi < 30",
                programmable=True,
                validation_status="validated",
                hit_count=2,
                sample_count=4,
                hit_rate=0.5,
                posterior_return_mean=0.02,
                posterior_return_median=0.015,
                notes=[],
            )
        ]

    service = BacktestService(
        engine_factory=lambda **kwargs: engine,
        rule_validation_runner=_rule_validation_runner,
    )

    result = asyncio.run(
        service.validate_rules(
            trader_id="trader_a",
            date_from=date(2026, 4, 1),
            date_to=date(2026, 4, 3),
            runtime_state={"checkpoint": {"trade_date_index": 1}},
        )
    )
    report = service.render_rule_validation_report(result.payload["results"])

    assert result.status == "ok"
    assert result.payload["coverage"]["programmable"] == 1
    assert result.payload["results"][0]["rule_id"] == "rule-001"
    assert "Rule Validation Report" in report.payload["content"]
    assert rule_validation_calls[0]["runtime_state"]["checkpoint"]["trade_date_index"] == 1


def test_backtest_service_reproducibility_and_rule_pool_run(tmp_path: Path) -> None:
    """BacktestService 应支持复现检查和规则池回测。"""
    from src.services.backtest_service import BacktestService

    engine = _FakeEngine()
    session_factory = _FakeSessionFactory()
    service = BacktestService(
        engine_factory=lambda **kwargs: engine,
        session_scope_factory=session_factory,
    )

    reproducibility = service.reproducibility_check(
        trader_id="trader_a",
        date_from=date(2026, 4, 1),
        date_to=date(2026, 4, 3),
        symbols=["000001.SZ"],
        market_regime_version="market-regime-v1",
        config_path=tmp_path / "config" / "app.yaml",
    )

    rule_pool_result = asyncio.run(
        service.run_rule_pool_backtest(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 3),
            rule_ids=["rule-001"],
            min_confidence=0.6,
            runtime_state={"checkpoint": {"rule_index": 1}},
        )
    )

    assert reproducibility.status == "ok"
    assert reproducibility.payload["matches"] is True
    assert reproducibility.payload["fingerprint_a"] == reproducibility.payload["fingerprint_b"]
    assert reproducibility.payload["request"]["symbols"] == ["000001.SZ"]
    assert reproducibility.payload["request"]["market_regime_version"] == "market-regime-v1"
    assert rule_pool_result.status == "ok"
    assert rule_pool_result.payload["summary"]["total_trades"] == 6
    assert session_factory.calls == 2
    assert engine.rule_pool_calls[0]["rule_ids"] == ["rule-001"]
    assert engine.rule_pool_calls[0]["runtime_state"]["checkpoint"]["rule_index"] == 1


def test_default_engine_factory_accepts_runtime_config_without_loaded_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Profile runtime config should not require a LoadedConfig wrapper."""
    from src.services.backtest_service import _default_engine_factory

    captured: dict[str, object] = {}

    class _FakeLoader:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("src.services.backtest_service.apply_database_config_to_env", lambda _config: None)
    monkeypatch.setattr("config.database.get_session_factory", lambda: object())
    monkeypatch.setattr("src.backtest.snapshot_loader.SnapshotLoader", _FakeLoader)
    monkeypatch.setattr("src.indicators.indicator_service.IndicatorService", lambda _session_factory: object())
    monkeypatch.setattr("src.market_data.strategy_repo_adapter.StrategyRepoAdapter", lambda: object())
    monkeypatch.setattr("src.market_universe.snapshot_service.SnapshotService", lambda **_kwargs: object())
    monkeypatch.setattr("src.services.market_snapshot_service.MarketSnapshotService", lambda: object())

    config = SimpleNamespace(
        data=SimpleNamespace(market_universe_snapshot_dir="data/market_universe/snapshots"),
        stage4=SimpleNamespace(market_universe_slot="09-25"),
    )

    engine = _default_engine_factory(config=config, base_dir=tmp_path, use_snapshot_only=True)

    assert engine.loader is engine.strategy_loader
    assert captured["config_path"] is None
    assert str(captured["snapshot_service"]).startswith("<object object")
