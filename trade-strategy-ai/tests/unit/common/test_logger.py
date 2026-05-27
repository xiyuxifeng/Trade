from __future__ import annotations

import logging

from src.common.logger import bind_log_context, get_log_context


def test_bind_log_context_injects_fields_into_records(caplog) -> None:
    """日志上下文应自动注入到记录字段中。"""
    logger = logging.getLogger("tests.logger.context")

    with caplog.at_level(logging.INFO):
        logger.info("outside context")

    assert caplog.records[-1].request_id == "-"
    assert caplog.records[-1].job_id == "-"
    assert caplog.records[-1].profile_id == "-"

    with bind_log_context(
        request_id="req-001",
        job_id="job-001",
        job_type="crawl",
        profile_id="profile-default",
        config_path="config/app.yaml",
    ):
        with caplog.at_level(logging.INFO):
            logger.info("inside context")

    record = caplog.records[-1]
    assert record.request_id == "req-001"
    assert record.job_id == "job-001"
    assert record.job_type == "crawl"
    assert record.profile_id == "profile-default"
    assert record.config_path == "config/app.yaml"


def test_get_log_context_returns_current_values() -> None:
    """当前上下文应该可被显式读取。"""
    with bind_log_context(request_id="req-ctx", job_id="job-ctx"):
        context = get_log_context()

    assert context["request_id"] == "req-ctx"
    assert context["job_id"] == "job-ctx"
