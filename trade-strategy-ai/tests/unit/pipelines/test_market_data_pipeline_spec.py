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
    assert summary["extensions"]["permissions_by_job_type"]["kaipan-fetch"] == "admin"
    assert summary["extensions"]["permissions_by_job_type"]["snapshot-build"] == "operator"
    assert "provider unavailable" in summary["extensions"]["error_modes_by_job_type"]["kaipan-fetch"]
    assert "partial snapshot" in summary["extensions"]["error_modes_by_job_type"]["snapshot-build"]
    fetch_step = next(step for step in summary["steps"] if step["job_type"] == "kaipan-fetch")
    snapshot_step = next(step for step in summary["steps"] if step["job_type"] == "snapshot-build")
    assert fetch_step["extensions"]["permission"] == "admin"
    assert "data invalid" in fetch_step["extensions"]["error_modes"]
    assert snapshot_step["extensions"]["permission"] == "operator"
    assert "partial snapshot" in snapshot_step["extensions"]["error_modes"]
