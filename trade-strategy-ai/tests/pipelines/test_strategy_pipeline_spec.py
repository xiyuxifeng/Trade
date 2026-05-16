from __future__ import annotations


def test_strategy_pipeline_spec_exports_core_fields() -> None:
    """strategy_pipeline spec 应暴露稳定核心字段。"""
    from src.pipelines.strategy_pipeline_spec import STRATEGY_PIPELINE_SPEC

    assert STRATEGY_PIPELINE_SPEC.pipeline_id == "strategy"
    assert STRATEGY_PIPELINE_SPEC.workflow_id == "strategy"
    assert STRATEGY_PIPELINE_SPEC.ui_page == "/strategies"
    assert "UI-V2-006" in STRATEGY_PIPELINE_SPEC.ui_task_ids
    assert "UI-V2-007" in STRATEGY_PIPELINE_SPEC.ui_task_ids
    assert STRATEGY_PIPELINE_SPEC.required_profile_sections == (
        "top_symbols",
        "style_cluster_ids",
        "concept_tags",
        "strategy_preference",
        "risk_style",
        "theme_preference",
        "position_bias",
    )
    assert "trader_id" in STRATEGY_PIPELINE_SPEC.input_schema["fields"]
    assert "strategy-build" in STRATEGY_PIPELINE_SPEC.job_types
    assert "result-json" in {item.kind for item in STRATEGY_PIPELINE_SPEC.output_artifacts}
    assert "html" in {item.kind for item in STRATEGY_PIPELINE_SPEC.output_artifacts}
    assert STRATEGY_PIPELINE_SPEC.extensions["strategy_actions"] == (
        "strategy-build",
        "run-pre-market",
        "run-after-close",
    )
    assert STRATEGY_PIPELINE_SPEC.extensions["future_extensions"] == (
        "evidence-pack-json",
        "ranking-report-json",
        "memory-update-json",
    )


def test_strategy_pipeline_spec_summary_is_catalog_friendly() -> None:
    """summary() 应返回可直接供 catalog / API 使用的平面结构。"""
    from src.pipelines.strategy_pipeline_spec import STRATEGY_PIPELINE_SPEC

    summary = STRATEGY_PIPELINE_SPEC.summary()

    assert summary["pipeline_id"] == "strategy"
    assert summary["workflow_id"] == "strategy"
    assert summary["ui_page"] == "/strategies"
    assert "UI-V2-006" in summary["ui_task_ids"]
    assert summary["output_artifacts"][0]["kind"] == "result-json"
    assert summary["output_artifacts"][1]["kind"] == "html"
    assert summary["output_artifacts"][0]["description"].startswith("策略版本构建与运行")
    assert summary["steps"][0]["job_type"] == "strategy-build"
    assert summary["steps"][0]["output_artifacts"] == ["result-json"]
    assert summary["steps"][1]["depends_on"] == ["strategy-build"]
    assert summary["steps"][1]["output_artifacts"] == ["result-json", "html"]
    assert summary["steps"][2]["extensions"]["runtime_support"] == "current"
