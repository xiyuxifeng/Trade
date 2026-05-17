from __future__ import annotations


def test_optimize_rule_pool_pipeline_spec_exports_core_fields() -> None:
    """optimize-rule-pool spec 应暴露稳定核心字段。"""
    from src.pipelines.optimize_rule_pool_pipeline_spec import OPTIMIZE_RULE_POOL_PIPELINE_SPEC

    assert OPTIMIZE_RULE_POOL_PIPELINE_SPEC.pipeline_id == "optimize-rule-pool"
    assert OPTIMIZE_RULE_POOL_PIPELINE_SPEC.workflow_id == "optimize-rule-pool"
    assert OPTIMIZE_RULE_POOL_PIPELINE_SPEC.ui_page == "/rule-pool"
    assert "UI-V3-002" in OPTIMIZE_RULE_POOL_PIPELINE_SPEC.ui_task_ids
    assert "UI-V3-003" in OPTIMIZE_RULE_POOL_PIPELINE_SPEC.ui_task_ids
    assert "optimize-create-candidate" in OPTIMIZE_RULE_POOL_PIPELINE_SPEC.job_types
    assert "rule-pool-backtest" in OPTIMIZE_RULE_POOL_PIPELINE_SPEC.job_types
    assert "candidate-review" in OPTIMIZE_RULE_POOL_PIPELINE_SPEC.job_types
    assert "rule-review" in OPTIMIZE_RULE_POOL_PIPELINE_SPEC.job_types
    assert OPTIMIZE_RULE_POOL_PIPELINE_SPEC.input_schema["fields"]["parent_version_id"]["required"] is True
    assert OPTIMIZE_RULE_POOL_PIPELINE_SPEC.input_schema["fields"]["review_decision"]["default"] == "pending"


def test_optimize_rule_pool_pipeline_spec_summary_is_catalog_friendly() -> None:
    """summary() 应返回可直接供 catalog / API 使用的平面结构。"""
    from src.pipelines.optimize_rule_pool_pipeline_spec import OPTIMIZE_RULE_POOL_PIPELINE_SPEC

    summary = OPTIMIZE_RULE_POOL_PIPELINE_SPEC.summary()

    assert summary["pipeline_id"] == "optimize-rule-pool"
    assert summary["workflow_id"] == "optimize-rule-pool"
    assert summary["ui_page"] == "/rule-pool"
    assert "UI-V3-002" in summary["ui_task_ids"]
    assert summary["output_artifacts"][0]["kind"] == "candidate-json"
    assert summary["steps"][0]["job_type"] == "optimize-create-candidate"
    assert summary["steps"][1]["depends_on"] == ["optimize-create-candidate"]
    assert summary["steps"][2]["job_type"] == "candidate-review"
