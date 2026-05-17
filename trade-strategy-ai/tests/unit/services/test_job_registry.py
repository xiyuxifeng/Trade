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
        params={"config_path": "config/app.yaml", "force": True, "export_html": False},
        created_by="web",
    )
    assert ok.status == "ok"
    assert ok.payload["params"]["config_path"] == "config/app.yaml"

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

    market = validate_job_submission(
        job_type="ohlcv-crawl",
        params={"config_path": "config/app.yaml", "symbols": ["000001.SZ"]},
        created_by="web",
    )
    assert market.status == "ok"
    assert market.payload["params"]["symbols"] == ["000001.SZ"]


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
