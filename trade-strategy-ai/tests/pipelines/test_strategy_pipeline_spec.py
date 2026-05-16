from __future__ import annotations


def test_strategy_pipeline_spec_exports_core_fields() -> None:
    """strategy_pipeline spec 应暴露稳定核心字段。"""
    from src.pipelines.strategy_pipeline_spec import STRATEGY_PIPELINE_SPEC

    assert STRATEGY_PIPELINE_SPEC.pipeline_id == "strategy"
    assert STRATEGY_PIPELINE_SPEC.workflow_id == "strategy"
    assert STRATEGY_PIPELINE_SPEC.ui_page == "/strategies"
    assert "UI-V2-006" in STRATEGY_PIPELINE_SPEC.ui_task_ids
    assert "UI-V2-007" in STRATEGY_PIPELINE_SPEC.ui_task_ids
    assert "trader_id" in STRATEGY_PIPELINE_SPEC.input_schema["fields"]
    assert "strategy-build" in STRATEGY_PIPELINE_SPEC.job_types
    assert "strategy-version-json" in {item.kind for item in STRATEGY_PIPELINE_SPEC.output_artifacts}
    assert "pre-market-report-html" in {item.kind for item in STRATEGY_PIPELINE_SPEC.output_artifacts}
    assert STRATEGY_PIPELINE_SPEC.extensions["strategy_actions"] == (
        "strategy-build",
        "run-pre-market",
        "run-after-close",
    )


def test_strategy_pipeline_spec_summary_is_catalog_friendly() -> None:
    """summary() 应返回可直接供 catalog / API 使用的平面结构。"""
    from src.pipelines.strategy_pipeline_spec import STRATEGY_PIPELINE_SPEC

    summary = STRATEGY_PIPELINE_SPEC.summary()

    assert summary["pipeline_id"] == "strategy"
    assert summary["workflow_id"] == "strategy"
    assert summary["ui_page"] == "/strategies"
    assert "UI-V2-006" in summary["ui_task_ids"]
    assert summary["output_artifacts"][0]["kind"] == "strategy-version-json"
    assert summary["steps"][0]["job_type"] == "strategy-build"
    assert summary["steps"][1]["depends_on"] == ["strategy-build"]
    assert summary["steps"][2]["extensions"]["runtime_support"] == "current"
