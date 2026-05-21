from __future__ import annotations


def test_article_pipeline_spec_exports_core_fields() -> None:
    """article_pipeline spec 应暴露稳定核心字段。"""
    from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPEC

    assert ARTICLE_PIPELINE_SPEC.pipeline_id == "article_pipeline"
    assert ARTICLE_PIPELINE_SPEC.workflow_id == "pipeline"
    assert ARTICLE_PIPELINE_SPEC.ui_page == "/articles"
    assert "UI-V1-010" in ARTICLE_PIPELINE_SPEC.ui_task_ids
    assert "UI-V1-007" in ARTICLE_PIPELINE_SPEC.ui_task_ids
    assert "profile_id" in ARTICLE_PIPELINE_SPEC.input_schema["fields"]
    assert "result-json" in {item.kind for item in ARTICLE_PIPELINE_SPEC.output_artifacts}
    assert "crawl" in ARTICLE_PIPELINE_SPEC.job_types
    assert ARTICLE_PIPELINE_SPEC.extensions["supported_input_modes"] == ("profile",)


def test_article_pipeline_spec_summary_is_catalog_friendly() -> None:
    """summary() 应返回可直接供 catalog / API 使用的平面结构。"""
    from src.pipelines.article_pipeline_spec import ARTICLE_PIPELINE_SPEC

    summary = ARTICLE_PIPELINE_SPEC.summary()

    assert summary["pipeline_id"] == "article_pipeline"
    assert summary["workflow_id"] == "pipeline"
    assert summary["ui_page"] == "/articles"
    assert "UI-V1-010" in summary["ui_task_ids"]
    assert summary["output_artifacts"][0]["kind"] == "result-json"
    assert summary["steps"][1]["job_type"] == "pipeline-run"
    assert summary["steps"][2]["extensions"]["resume_mode"] is True
