from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler

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


def test_configure_logging_uses_log_level_env(monkeypatch, tmp_path) -> None:
    """部署环境变量 LOG_LEVEL 应该能控制日志级别。"""
    import src.common.logger as logger_module

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_configured = logger_module._configured
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    try:
        logger_module._configured = False
        logger_module.configure_logging(log_file=tmp_path / "app.log", force=True)

        file_handlers = [handler for handler in root_logger.handlers if getattr(handler, "_trade_strategy_ai_handler_kind", None) == "file"]
        console_handlers = [handler for handler in root_logger.handlers if getattr(handler, "_trade_strategy_ai_handler_kind", None) == "console"]

        assert file_handlers
        assert file_handlers[0].level == logging.WARNING
        assert console_handlers
        assert console_handlers[0].level == logging.WARNING
    finally:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()

        for handler in original_handlers:
            root_logger.addHandler(handler)

        logger_module._configured = original_configured


def test_configure_logging_defaults_to_daily_rotation(monkeypatch, tmp_path) -> None:
    """默认日志文件应按天轮转，并保留 5 天。"""
    import src.common.logger as logger_module

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_configured = logger_module._configured
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    try:
        logger_module._configured = False
        logger_module.configure_logging(log_file=tmp_path / "app.log", force=True)

        file_handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, "_trade_strategy_ai_handler_kind", None) == "file"
        ]

        assert file_handlers
        assert isinstance(file_handlers[0], TimedRotatingFileHandler)
        assert file_handlers[0].when.lower() == "midnight"
        assert file_handlers[0].interval == 24 * 60 * 60
        assert file_handlers[0].backupCount == 5
    finally:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()

        for handler in original_handlers:
            root_logger.addHandler(handler)

        logger_module._configured = original_configured
