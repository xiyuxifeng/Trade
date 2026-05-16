from __future__ import annotations

from datetime import UTC, datetime


def test_runtime_contract_round_trip_and_error_classification() -> None:
    """Runtime Contract 应支持 JSON 兼容序列化与反序列化。"""
    from src.services.runtime_contracts import (
        ArtifactRef,
        ConfigSnapshotRef,
        ProfileSnapshotRef,
        RunContext,
        StepError,
        StepErrorType,
        StepInput,
        StepResult,
        StorageRef,
        UserContext,
        WorkflowRunContext,
    )

    snapshot = ConfigSnapshotRef(
        config_snapshot_id="cfg-001",
        config_source="config/app.yaml",
        config_hash="hash-001",
        masked_snapshot={"secret_token": "***"},
    )
    profile_snapshot = ProfileSnapshotRef(
        profile_snapshot_id="profile-snapshot-001",
        profile_id="profile-001",
        profile_hash="profile-hash-001",
        masked_sections={"llm": {"api_key": "***"}},
    )
    artifact = ArtifactRef(
        artifact_id="artifact-001",
        job_id="job-001",
        workflow_id="workflow-001",
        step_id="step-001",
        kind="report",
        title="日报",
        summary="生成后的日报",
        safe_download_url="/api/ui/v1/artifacts/artifact-001/download",
        size_bytes=128,
        visibility="internal",
        metadata={"format": "html"},
        storage_ref=StorageRef(source="file", logical_id="artifact-001", relative_path="jobs/job-001/report.html"),
        config_snapshot_ref=snapshot,
    )
    error = StepError(
        type=StepErrorType.permission,
        message="permission denied",
        detail="operator role required",
        request_id="req-001",
    )
    step_input = StepInput(step_name="compile", payload={"date": "2026-05-14"})
    step_result = StepResult(step_name="compile", payload={"ok": True}, artifacts=[artifact])
    run_context = RunContext(
        run_id="run-001",
        job_id="job-001",
        workflow_id="workflow-001",
        created_at=datetime(2026, 5, 14, 9, 30, tzinfo=UTC),
    )
    user_context = UserContext(user_id="user-001", username="alice", roles=["viewer", "operator"])
    workflow_run = WorkflowRunContext(
        run_context=run_context,
        user_context=user_context,
        step_inputs=[step_input],
        step_results=[step_result],
        errors=[error],
    )

    payload = workflow_run.model_dump(mode="json")
    restored = WorkflowRunContext.model_validate(payload)

    assert payload["run_context"]["job_id"] == "job-001"
    assert payload["step_results"][0]["artifacts"][0]["config_snapshot_ref"]["config_hash"] == "hash-001"
    assert payload["step_results"][0]["artifacts"][0]["storage_ref"]["relative_path"] == "jobs/job-001/report.html"
    assert payload["errors"][0]["type"] == "permission"
    assert restored.run_context.workflow_id == "workflow-001"
    assert restored.errors[0].type == StepErrorType.permission

    profile_payload = profile_snapshot.model_dump(mode="json")
    restored_profile = ProfileSnapshotRef.model_validate(profile_payload)
    assert restored_profile.profile_hash == "profile-hash-001"
    assert restored_profile.masked_sections["llm"]["api_key"] == "***"


def test_runtime_contract_rejects_absolute_storage_paths() -> None:
    """StorageRef 不应保存服务器绝对路径。"""
    from src.services.runtime_contracts import StorageRef

    storage = StorageRef(source="file", logical_id="artifact-002", relative_path="jobs/job-002/report.csv")

    assert storage.relative_path == "jobs/job-002/report.csv"
    assert not storage.relative_path.startswith("/")
