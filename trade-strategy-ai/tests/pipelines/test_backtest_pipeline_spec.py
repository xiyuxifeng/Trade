from __future__ import annotations


def test_backtest_pipeline_spec_exports_core_fields() -> None:
    """backtest_pipeline spec 应暴露稳定核心字段。"""
    from src.pipelines.backtest_pipeline_spec import BACKTEST_PIPELINE_SPEC

    assert BACKTEST_PIPELINE_SPEC.pipeline_id == "backtest"
    assert BACKTEST_PIPELINE_SPEC.workflow_id == "backtest"
    assert BACKTEST_PIPELINE_SPEC.ui_page == "/backtest"
    assert "UI-V3-001" in BACKTEST_PIPELINE_SPEC.ui_task_ids
    assert "backtest-run" in BACKTEST_PIPELINE_SPEC.job_types
    assert "backtest-validate-rules" in BACKTEST_PIPELINE_SPEC.job_types
    assert "backtest-reproducibility-check" in BACKTEST_PIPELINE_SPEC.job_types
    assert BACKTEST_PIPELINE_SPEC.input_schema["fields"]["trader_id"]["required"] is True
    assert BACKTEST_PIPELINE_SPEC.input_schema["fields"]["use_snapshot_only"]["default"] is True
    assert BACKTEST_PIPELINE_SPEC.input_schema["fields"]["scoring_profile"]["default"] == "stage5"


def test_backtest_pipeline_spec_summary_is_catalog_friendly() -> None:
    """summary() 应返回可直接供 catalog / API 使用的平面结构。"""
    from src.pipelines.backtest_pipeline_spec import BACKTEST_PIPELINE_SPEC

    summary = BACKTEST_PIPELINE_SPEC.summary()

    assert summary["pipeline_id"] == "backtest"
    assert summary["workflow_id"] == "backtest"
    assert summary["ui_page"] == "/backtest"
    assert "UI-V3-001" in summary["ui_task_ids"]
    assert summary["output_artifacts"][0]["kind"] == "result-json"
    assert summary["steps"][0]["job_type"] == "backtest-run"
    assert summary["steps"][1]["depends_on"] == ["backtest-run"]
    assert summary["steps"][2]["extensions"]["permission"] == "admin"
