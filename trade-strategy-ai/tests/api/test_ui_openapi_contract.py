"""UI OpenAPI 契约测试。"""

from __future__ import annotations

from api.main import app


def test_ui_openapi_exposes_critical_contract_paths() -> None:
    """UI 层关键路由必须稳定暴露。"""
    paths = app.openapi()["paths"]
    components = app.openapi()["components"]["schemas"]

    expected_methods = {
        "/api/ui/v1/system/status": {"get"},
        "/api/ui/v1/auth/me": {"get"},
        "/api/ui/v1/jobs": {"get", "post"},
        "/api/ui/v1/jobs/{job_id}": {"get"},
        "/api/ui/v1/jobs/{job_id}/logs": {"get"},
        "/api/ui/v1/jobs/{job_id}/timeline": {"get"},
        "/api/ui/v1/jobs/{job_id}/artifacts": {"get"},
        "/api/ui/v1/jobs/{job_id}/cancel": {"post"},
        "/api/ui/v1/jobs/{job_id}/pause": {"post"},
        "/api/ui/v1/jobs/{job_id}/resume": {"post"},
        "/api/ui/v1/jobs/{job_id}/retry": {"post"},
        "/api/ui/v1/job-audits": {"get"},
        "/api/ui/v1/job-audits/{job_id}": {"get"},
        "/api/ui/v1/security/permission-denied": {"get"},
        "/api/ui/v1/security/permission-denied/{event_id}": {"get"},
        "/api/ui/v1/data-audits": {"get"},
        "/api/ui/v1/data-audits/{event_id}": {"get"},
        "/api/ui/v1/optimize/versions": {"get"},
        "/api/ui/v1/optimize/versions/{version_id}": {"get"},
        "/api/ui/v1/optimize/advise-rule-validations": {"post"},
        "/api/ui/v1/optimize/filter-active-traders": {"post"},
        "/api/ui/v1/optimize/create-candidate": {"post"},
        "/api/ui/v1/rule-pool": {"get"},
        "/api/ui/v1/rule-pool/filter-options": {"get"},
        "/api/ui/v1/rule-pool/{rule_id}": {"get"},
        "/api/ui/v1/rule-pool/{rule_id}/review": {"post"},
        "/api/ui/v1/rule-pool/review-batch": {"post"},
        "/api/ui/v1/rules/backtests/dependency-check": {"post"},
        "/api/ui/v1/rules/backtests/runs": {"post"},
        "/api/ui/v1/rules/backtests/runs/{run_id}": {"get"},
        "/api/ui/v1/rules/backtests/runs/{run_id}/execute": {"post"},
        "/api/ui/v1/rules/backtests/runs/{run_id}/result": {"get"},
        "/api/ui/v1/workflows": {"get"},
        "/api/ui/v1/workflows/runs": {"get"},
        "/api/ui/v1/workflows/runs/{workflow_run_id}": {"get"},
        "/api/ui/v1/workflows/runs/{workflow_run_id}/steps": {"get"},
        "/api/ui/v1/workflows/{workflow_id}": {"get"},
        "/api/ui/v1/workflows/{workflow_id}/run": {"post"},
        "/api/ui/v1/profiles": {"get"},
        "/api/ui/v1/profiles/{profile_id}/edit": {"get"},
        "/api/ui/v1/profiles/{profile_id}/validate": {"post"},
        "/api/ui/v1/profiles/{profile_id}": {"get", "put"},
        "/api/ui/v1/profiles/{profile_id}/archive": {"post"},
        "/api/ui/v1/profiles/import": {"post"},
        "/api/ui/v1/profiles/{profile_id}/snapshots/{snapshot_id}": {"get"},
        "/api/ui/v1/pipelines": {"get"},
        "/api/ui/v1/pipelines/article_pipeline": {"get"},
        "/api/ui/v1/pipelines/article_pipeline/run": {"post"},
        "/api/ui/v1/artifacts": {"get"},
        "/api/ui/v1/artifacts/filter-options": {"get"},
        "/api/ui/v1/artifacts/{artifact_id}": {"get"},
        "/api/ui/v1/artifacts/{artifact_id}/download": {"get"},
        "/reports/daily": {"get"},
        "/reports/daily/{date_str}": {"get"},
        "/reports/daily/{date_str}/html": {"get"},
        "/reports/evaluation": {"get"},
        "/reports/evaluation/{date_str}": {"get"},
        "/reports/evaluation/{date_str}/html": {"get"},
        "/api/ui/v1/settings/config": {"get"},
        "/api/ui/v1/settings/schema": {"get"},
        "/api/ui/v1/settings/validate": {"post"},
        "/api/ui/v1/settings/save": {"post"},
        "/api/ui/v1/settings/backups": {"get"},
        "/api/ui/v1/settings/restore": {"post"},
        "/api/ui/v1/ops/backups": {"get"},
        "/api/ui/v1/ops/backup": {"post"},
        "/api/ui/v1/ops/restore": {"post"},
        "/api/ui/v1/ops/recover-stale": {"post"},
        "/api/ui/v1/market/symbols": {"get"},
        "/api/ui/v1/market/ohlcv": {"get"},
        "/api/ui/v1/market/snapshots": {"get"},
        "/api/ui/v1/market/snapshots/{snapshot_id}": {"get"},
        "/api/ui/v1/market/snapshots/{snapshot_id}/sections": {"get"},
        "/api/ui/v1/market/snapshots/{snapshot_id}/sections/{section}": {"get"},
        "/api/ui/v1/market/datasets": {"get"},
        "/api/ui/v1/market/datasets/{dataset_id}": {"get"},
        "/api/ui/v1/market/snapshots/{snapshot_id}/quality": {"get"},
        "/api/ui/v1/market/regimes": {"get"},
        "/api/ui/v1/market/snapshots/{snapshot_id}/regime": {"get"},
    }

    for path, methods in expected_methods.items():
        assert path in paths, path
        assert set(paths[path]) == methods

    artifact_query_params = {param["name"] for param in paths["/api/ui/v1/artifacts"]["get"].get("parameters", [])}
    assert {"job_type", "date"} <= artifact_query_params

    expected_request_refs = {
        ("/api/ui/v1/jobs", "post"): "#/components/schemas/JobSubmissionRequest",
        ("/api/ui/v1/jobs/{job_id}/cancel", "post"): "#/components/schemas/JobCancelRequest",
        ("/api/ui/v1/jobs/{job_id}/pause", "post"): "#/components/schemas/JobControlRequest",
        ("/api/ui/v1/jobs/{job_id}/retry", "post"): "#/components/schemas/JobControlRequest",
        ("/api/ui/v1/optimize/create-candidate", "post"): "#/components/schemas/CandidateCreateRequest",
        ("/api/ui/v1/optimize/filter-active-traders", "post"): "#/components/schemas/ActiveTraderFilterRequest",
        ("/api/ui/v1/rule-pool/filter-options", "get"): None,
        ("/api/ui/v1/rule-pool/{rule_id}/review", "post"): "#/components/schemas/RulePoolReviewRequest",
        ("/api/ui/v1/rule-pool/review-batch", "post"): "#/components/schemas/RulePoolBatchReviewRequest",
        ("/api/ui/v1/rules/backtests/dependency-check", "post"): "#/components/schemas/BacktestSelection",
        ("/api/ui/v1/rules/backtests/runs", "post"): "#/components/schemas/FormalBacktestCreateRequest",
        ("/api/ui/v1/workflows/{workflow_id}/run", "post"): "#/components/schemas/WorkflowRunRequest",
        ("/api/ui/v1/profiles/import", "post"): "#/components/schemas/ProfileImportRequest",
        ("/api/ui/v1/profiles/{profile_id}/validate", "post"): "#/components/schemas/ProfileEditDraftRequest",
        ("/api/ui/v1/profiles/{profile_id}", "put"): "#/components/schemas/ProfileUpdateRequest",
        ("/api/ui/v1/profiles/{profile_id}/archive", "post"): "#/components/schemas/ProfileArchiveRequest",
        ("/api/ui/v1/settings/validate", "post"): "#/components/schemas/SettingsDraftRequest",
        ("/api/ui/v1/settings/save", "post"): "#/components/schemas/SettingsSaveRequest",
        ("/api/ui/v1/settings/restore", "post"): "#/components/schemas/SettingsRestoreRequest",
        ("/api/ui/v1/ops/backup", "post"): "#/components/schemas/OpsBackupRequest",
        ("/api/ui/v1/ops/restore", "post"): "#/components/schemas/OpsRestoreRequest",
        ("/api/ui/v1/ops/recover-stale", "post"): "#/components/schemas/OpsRecoverStaleRequest",
    }

    for (path, method), schema_ref in expected_request_refs.items():
        if schema_ref is None:
            continue
        assert paths[path][method]["requestBody"]["content"]["application/json"]["schema"]["$ref"] == schema_ref

    expected_response_refs = {
        ("/api/ui/v1/artifacts/filter-options", "get"): "#/components/schemas/ArtifactFilterOptionsResponse",
        ("/api/ui/v1/rule-pool/filter-options", "get"): "#/components/schemas/RulePoolFilterOptionsResponse",
        ("/reports/daily", "get"): "#/components/schemas/DailyReportListResponse",
        ("/reports/daily/{date_str}", "get"): "#/components/schemas/DailyReportResponse",
        ("/reports/evaluation", "get"): "#/components/schemas/EvaluationListResponse",
        ("/reports/evaluation/{date_str}", "get"): "#/components/schemas/EvaluationResponse",
    }

    for (path, method), schema_ref in expected_response_refs.items():
        assert paths[path][method]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == schema_ref

    assert set(components["SettingsSaveRequest"]["properties"]) >= {"config_path", "draft", "confirmed"}
    assert components["SettingsSaveRequest"]["properties"]["confirmed"]["default"] is False
    assert set(components["WorkflowRunRequest"]["properties"]) >= {"params", "created_by", "idempotency_key", "confirmed"}
    assert components["WorkflowRunRequest"]["properties"]["confirmed"]["default"] is False
    assert set(components["OpsBackupRequest"]["properties"]) >= {"include_processed"}
    assert components["OpsBackupRequest"]["properties"]["include_processed"]["default"] is True
    assert set(components["OpsRestoreRequest"]["properties"]) >= {"backup_path", "confirmed", "include_processed"}
    assert components["OpsRestoreRequest"]["properties"]["confirmed"]["default"] is False
    assert set(components["OpsRecoverStaleRequest"]["properties"]) >= {"stale_before_minutes"}
    assert components["OpsRecoverStaleRequest"]["properties"]["stale_before_minutes"]["default"] == 10
