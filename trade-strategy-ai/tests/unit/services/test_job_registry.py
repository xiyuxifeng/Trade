from __future__ import annotations

import pytest

from src.services.job_registry import (
    JobParamField,
    JobParamSchema,
    JobFieldType,
    get_job_definition,
    get_runnable_job_types,
    list_job_definitions,
    validate_job_submission,
)


def test_job_registry_covers_user_manual_long_tasks() -> None:
    """Job 注册表应覆盖 UserManual 中的长任务白名单。"""
    expected = {
        "db-migrate",
        "init-project",
        "seed-data",
        "backup-data",
        "restore-data",
        "crawl",
        "import-trade-logs",
        "pipeline-run",
        "pipeline-step",
        "migrate-crawl-state",
        "clusters-build",
        "e2e-regression",
        "run-pre-market",
        "run-after-close",
        "persona-init-sample",
        "market-state-build",
        "snapshot-build",
        "strategy-build",
        "ohlcv-crawl",
        "backtest-run",
        "backtest-validate-rules",
        "backtest-reproducibility-check",
        "rule-pool-backtest",
        "optimize-create-candidate",
        "candidate-review",
        "rule-review",
        "kaipan-fetch",
        "kaipan-normalize",
        "kaipan-run",
    }

    actual = {definition.job_type for definition in list_job_definitions()}
    assert actual == expected


def test_job_registry_marks_only_connected_jobs_runnable() -> None:
    """只有已接通 handler 的 job type 才能进入 runner 白名单。"""
    assert get_runnable_job_types() == [
        "backup-data",
        "restore-data",
        "pipeline-run",
        "pipeline-step",
        "run-pre-market",
        "run-after-close",
        "market-state-build",
        "snapshot-build",
        "strategy-build",
        "ohlcv-crawl",
        "backtest-run",
        "backtest-validate-rules",
        "backtest-reproducibility-check",
        "rule-pool-backtest",
        "candidate-review",
        "kaipan-fetch",
        "kaipan-normalize",
        "kaipan-run",
    ]


def test_validate_job_submission_enforces_schema() -> None:
    """提交校验应拒绝未知 job type、非 runnable job type 和缺失参数。"""
    unknown = validate_job_submission(job_type="unknown-job", params={}, created_by="web")
    assert unknown.status == "error"

    not_runnable = validate_job_submission(job_type="seed-data", params={"config_path": "config/app.yaml"}, created_by="web")
    assert not_runnable.status == "error"

    confirmed = validate_job_submission(
        job_type="init-project",
        params={"config_path": "config/app.yaml"},
        created_by="web",
        confirmed=True,
    )
    assert confirmed.status == "ok"
    assert confirmed.payload["params"]["config_path"] == "config/app.yaml"

    ok = validate_job_submission(
        job_type="run-pre-market",
        params={"profile_id": "default", "as_of_date": "2026-05-09", "force": True, "export_html": False},
        created_by="web",
    )
    assert ok.status == "ok"
    assert ok.payload["params"]["profile_id"] == "default"
    assert ok.payload["params"]["as_of_date"] == "2026-05-09"

    after_close = validate_job_submission(
        job_type="run-after-close",
        params={"profile_id": "default", "as_of_date": "2026-05-09", "force": False, "export_html": True},
        created_by="web",
    )
    assert after_close.status == "ok"
    assert after_close.payload["params"]["profile_id"] == "default"
    assert after_close.payload["params"]["as_of_date"] == "2026-05-09"

    backtest = validate_job_submission(
        job_type="backtest-run",
        params={
            "trader_id": "trader_a",
            "date_from": "2026-04-01",
            "date_to": "2026-04-03",
            "symbols": ["000001.SZ"],
        },
        created_by="web",
    )
    assert backtest.status == "ok"
    assert backtest.payload["params"]["symbols"] == ["000001.SZ"]

    rule_pool = validate_job_submission(
        job_type="rule-pool-backtest",
        params={"rule_id": "rule-001", "start_date": "2026-04-01", "end_date": "2026-04-03"},
        created_by="web",
        confirmed=True,
    )
    assert rule_pool.status == "ok"
    assert rule_pool.payload["params"]["market_regime_version"] == "market-regime-v3"

    market = validate_job_submission(
        job_type="ohlcv-crawl",
        params={"config_path": "config/app.yaml", "symbols": ["000001.SZ"]},
        created_by="web",
    )
    assert market.status == "ok"
    assert market.payload["params"]["symbols"] == ["000001.SZ"]

    market_state = validate_job_submission(
        job_type="market-state-build",
        params={"config_path": "config/app.yaml", "benchmark_symbol": "000300.SH", "as_of": "2026-05-09"},
        created_by="web",
    )
    assert market_state.status == "ok"
    assert market_state.payload["params"]["benchmark_symbol"] == "000300.SH"

    snapshot = validate_job_submission(
        job_type="snapshot-build",
        params={"profile_id": "default", "date": "2026-05-09", "snapshot_type": "all"},
        created_by="web",
    )
    assert snapshot.status == "ok"
    assert snapshot.payload["params"]["profile_id"] == "default"
    assert snapshot.payload["params"]["date"] == "2026-05-09"


def test_job_definition_lookup_exposes_metadata() -> None:
    """Job 定义应能按 job_type 查到元数据。"""
    definition = get_job_definition("pipeline-run")
    assert definition is not None
    assert definition.permission.value == "operator"
    assert definition.risk.value == "medium"
    assert definition.param_schema.fields["config_path"].required is True


def test_job_param_schema_enum_validation() -> None:
    """Job 参数 schema 应正确校验 enum 约束。"""
    schema = JobParamSchema(
        description="enum test",
        fields={
            "mode": JobParamField(
                type=JobFieldType.string,
                description="执行模式",
                required=True,
                enum=["cli", "web"],
            )
        },
    )

    normalized, warnings = schema.validate({"mode": "web"})
    assert normalized["mode"] == "web"
    assert warnings == []

    with pytest.raises(ValueError, match="must be one of"):
        schema.validate({"mode": "unknown"})
