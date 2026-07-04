from __future__ import annotations

from datetime import UTC, datetime
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


def test_build_post_market_review_trace_returns_truthful_partial_without_prompt_run() -> None:
    service = SystemRunTraceService(session_scope_factory=lambda: None)
    now = datetime(2026, 6, 30, 15, 30, tzinfo=UTC)
    review = SimpleNamespace(
        post_market_review_id="review-1",
        trading_day_plan_id="plan-1",
        created_at=now,
        updated_at=now,
        evidence_json={"actuals": {"available": False}},
    )

    trace = service._build_post_market_review_trace(
        review,
        actor_role="admin",
        market_snapshot=None,
        prompt_run=None,
    )

    assert trace["run_id"] == "post-market-review:review-1"
    assert trace["business_label"] == "生成正式盘后复盘"
    assert trace["status"] == "partial"
    assert trace["prompt_calls"] == []
    assert trace["steps"][0]["output_references"][0]["id"] == "review-1"
    assert trace["admin_diagnostics"]["payload_fingerprints"]["prompt_run_linked"] is False


def test_build_runs_overview_caps_attention_applies_filters_and_paginates_history() -> None:
    service = SystemRunTraceService(session_scope_factory=lambda: None)
    traces = [
        {
            "run_id": "backtest-1",
            "business_label": "执行正式回测",
            "business_type": "backtest",
            "status": "error",
            "started_at": "2026-07-04T09:05:00+00:00",
            "finished_at": "2026-07-04T09:08:00+00:00",
            "happened": "正式回测失败。",
            "reason": "关键回测输入未通过校验。",
            "affected": "无法继续查看这次验证结果。",
            "impact": "阻断规则验证。",
            "blocks_user": True,
            "repair_guidance": "先补齐输入后重新发起回测。",
            "next_action": {"label": "查看规则与回测", "target_path": "/rules/backtests"},
            "safe_next_action": {"label": "查看规则与回测", "target_path": "/rules/backtests"},
            "admin_diagnostics": {"technical_status": "error"},
        },
        {
            "run_id": "data-1",
            "business_label": "补齐缺失数据",
            "business_type": "data",
            "status": "partial",
            "started_at": "2026-07-04T08:30:00+00:00",
            "finished_at": "2026-07-04T08:40:00+00:00",
            "happened": "盘前数据只补齐了一部分。",
            "reason": "部分市场快照仍然缺失。",
            "affected": "今日盘前计划会受到影响。",
            "impact": "限制盘前流程。",
            "blocks_user": True,
            "repair_guidance": "去数据与调度补齐盘前快照。",
            "next_action": {"label": "查看数据与调度", "target_path": "/system/data"},
            "safe_next_action": {"label": "查看数据与调度", "target_path": "/system/data"},
            "admin_diagnostics": {"technical_status": "partial"},
        },
        {
            "run_id": "prompt-1",
            "business_label": "结构化文章提取",
            "business_type": "prompt",
            "status": "degraded",
            "started_at": "2026-07-04T07:30:00+00:00",
            "finished_at": "2026-07-04T07:35:00+00:00",
            "happened": "结构化结果已返回，但仍有字段降级。",
            "reason": "部分字段缺少正式证据。",
            "affected": "研究结果需要人工复核。",
            "impact": "限制研究输出可信度。",
            "blocks_user": False,
            "repair_guidance": "返回研究中心查看待复核项。",
            "next_action": {"label": "查看研究中心", "target_path": "/research/articles"},
            "safe_next_action": {"label": "查看研究中心", "target_path": "/research/articles"},
            "admin_diagnostics": {"technical_status": "degraded"},
        },
        {
            "run_id": "plan-1",
            "business_label": "生成今日交易计划",
            "business_type": "trading-plan",
            "status": "ready",
            "started_at": "2026-07-03T23:30:00+00:00",
            "finished_at": "2026-07-03T23:35:00+00:00",
            "happened": "今日交易计划已生成。",
            "reason": "全部输入已就绪。",
            "affected": "可以继续查看今日计划。",
            "impact": "不阻断用户。",
            "blocks_user": False,
            "repair_guidance": "无需额外处理。",
            "next_action": {"label": "查看今日计划", "target_path": "/daily/pre-market"},
            "safe_next_action": {"label": "查看今日计划", "target_path": "/daily/pre-market"},
            "admin_diagnostics": {"technical_status": "ready"},
        },
    ]

    payload = service._build_runs_overview_payload(
        traces,
        actor_role="viewer",
        status_filter="needs_attention",
        business_type_filter="all",
        cursor=None,
        limit=2,
        date_from=None,
        date_to=None,
    )

    assert payload["summary"]["overall_status"] == "needs_attention"
    assert payload["summary"]["counts"]["needs_attention"] == 3
    assert payload["summary"]["counts"]["ready"] == 1
    assert payload["summary"]["next_action"]["target_path"] == "/rules/backtests"
    assert len(payload["needs_attention"]) == 3
    assert payload["needs_attention"][0]["run_id"] == "backtest-1"
    assert payload["needs_attention"][0]["reason"] == "关键回测输入未通过校验。"
    assert payload["needs_attention"][0]["safe_next_action"]["target_path"] == "/rules/backtests"
    assert payload["history"]["groups"][0]["items"][0]["run_id"] == "backtest-1"
    assert payload["history"]["groups"][0]["items"][1]["run_id"] == "data-1"
    assert payload["history"]["page"]["has_more"] is True
    assert payload["history"]["page"]["next_cursor"] is not None
    assert payload["history"]["page"]["total_filtered"] == 3
    assert payload["history"]["groups"][0]["items"][0]["admin_diagnostics"] is None

    next_payload = service._build_runs_overview_payload(
        traces,
        actor_role="admin",
        status_filter="all",
        business_type_filter="prompt",
        cursor=payload["history"]["page"]["next_cursor"],
        limit=2,
        date_from="2026-07-04",
        date_to="2026-07-04",
    )

    assert next_payload["summary"]["counts"]["total"] == 4
    assert next_payload["history"]["page"]["total_filtered"] == 1
    assert next_payload["history"]["groups"][0]["items"][0]["run_id"] == "prompt-1"
    assert next_payload["history"]["groups"][0]["items"][0]["admin_diagnostics"]["technical_status"] == "degraded"
