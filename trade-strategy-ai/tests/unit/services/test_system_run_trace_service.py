from __future__ import annotations

from types import SimpleNamespace

from src.services.system_run_trace_service import SystemRunTraceService


def test_build_prompt_call_view_preserves_validation_cost_and_linked_object() -> None:
    service = SystemRunTraceService(session_scope_factory=lambda: None)
    prompt_run = SimpleNamespace(
        prompt_run_id="prompt-1",
        run_id="run-123",
        provider="openai",
        model="gpt-5.4",
        prompt_version="article_analysis_v1",
        schema_version="article_analysis_schema_v1",
        input_hash="hash-1",
        validation_state="valid",
        retry_count=1,
        token_usage={"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200},
        cost_amount=0.42,
        cost_currency="USD",
        started_at=None,
        completed_at=None,
        input_object_type="article_revision",
        input_object_id="article-1",
        input_version_id="revision-2",
    )

    prompt_call = service._build_prompt_call_view(prompt_run)

    assert prompt_call["run_id"] == "run-123"
    assert prompt_call["provider"] == "openai"
    assert prompt_call["prompt_version"] == "article_analysis_v1"
    assert prompt_call["schema_version"] == "article_analysis_schema_v1"
    assert prompt_call["validation_state"] == "valid"
    assert prompt_call["retry_count"] == 1
    assert prompt_call["tokens"]["total_tokens"] == 200
    assert prompt_call["cost"]["amount"] == 0.42
    assert prompt_call["linked_business_object"]["object_type"] == "article_revision"


def test_build_attempt_view_marks_missing_runtime_attempts_as_unavailable() -> None:
    service = SystemRunTraceService(session_scope_factory=lambda: None)

    attempt = service._build_attempt_view(run_id="daily-plan:1", retry_count=None, attempt_id=None)

    assert attempt["attempt_id"] == "daily-plan:1:attempt-unknown"
    assert attempt["retry_count"] is None
    assert attempt["state"] == "unavailable"


def test_build_backtest_view_exposes_rule_and_code_versions() -> None:
    service = SystemRunTraceService(session_scope_factory=lambda: None)
    run = SimpleNamespace(
        dataset_snapshot_id="dataset-1",
        dataset_fingerprint="dataset-fp",
        market_snapshot_fingerprints=["market-fp"],
        rule_version_id="rule-version-1",
        rule_version_no=3,
        rule_version_fingerprint="rule-fp",
        rule_family_id=None,
        rule_family_fingerprint=None,
        market_state_model_version="market-state-v2",
        engine_version="engine-v5",
        decision_time_policy="t+0-close",
        reproducibility_fingerprint="repro-fp",
        coverage_state="ready",
        limitations=["coverage-limited"],
    )

    view = service._build_backtest_view(run, result=None)

    assert view["rule_version"]["rule_version_id"] == "rule-version-1"
    assert view["rule_version"]["rule_version_no"] == 3
    assert view["code_version"] == "engine-v5"


def test_build_system_data_operation_trace_exposes_retry_policy_and_idempotency_to_admins() -> None:
    service = SystemRunTraceService(session_scope_factory=lambda: None)
    job = SimpleNamespace(
        id="job-1",
        status="failed",
        params={
            "action": "repair",
            "target_trade_date": "2026-06-22",
            "steps": [
                {
                    "action": "refresh_pre_market_kaipan",
                    "label": "补齐盘前市场数据",
                    "reason": "盘前数据缺失。",
                    "target_trade_date": "2026-06-22",
                }
            ],
        },
        error={"message": "provider timeout"},
        result={"status": "partial"},
        runtime_state={
            "attempt_history": [{"status": "failed", "error": {"message": "provider timeout"}}],
            "checkpoint": {"completed_steps": []},
            "last_failure_evidence": {"error": {"message": "provider timeout"}},
        },
        idempotency_key="system-data-operation:abc",
        retry_count=2,
        max_retries=3,
        retry_backoff_seconds=300,
        created_at=None,
        updated_at=None,
        started_at=None,
        finished_at=None,
    )

    trace = service._build_system_job_trace(job, actor_role="admin")

    assert trace["business_label"] == "补齐缺失数据"
    assert trace["steps"][0]["business_label"] == "补齐盘前市场数据"
    assert trace["admin_diagnostics"]["payload_fingerprints"]["idempotency_key"] == "system-data-operation:abc"
    assert trace["admin_diagnostics"]["raw_metadata"]["retry_policy"]["max_retries"] == 3
    assert trace["admin_diagnostics"]["raw_metadata"]["failure_evidence"]["error"]["message"] == "provider timeout"
