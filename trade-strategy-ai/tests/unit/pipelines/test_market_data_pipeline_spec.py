from __future__ import annotations

from src.pipelines import MARKET_DATA_PIPELINE_SPEC


def test_market_data_pipeline_spec_summary() -> None:
    summary = MARKET_DATA_PIPELINE_SPEC.summary()

    assert summary["pipeline_id"] == "market_data"
    assert summary["title"] == "市场数据链路"
    assert summary["workflow_id"] == "scheduler"
    assert summary["ui_page"] == "/market"
    assert summary["ui_task_ids"] == ["UI-V2-005", "UI-V2-007"]
    assert summary["required_profile_sections"] == ["market", "profile", "provider"]
    assert "kaipan-fetch" in summary["job_types"]
    assert "snapshot-build" in summary["job_types"]
    assert any(item["kind"] == "market-state-json" for item in summary["output_artifacts"])
    assert any(step["job_type"] == "snapshot-build" for step in summary["steps"])
