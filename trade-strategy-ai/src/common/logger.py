from __future__ import annotations

from contextlib import contextmanager
import logging
import sys
from contextvars import ContextVar, Token
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterator

from src.common.paths import resolve_project_path

# 日志目录，默认在项目根目录的 logs 文件夹
_LOG_DIR = resolve_project_path("logs")
_LOG_DIR.mkdir(exist_ok=True, parents=True)

# 默认日志文件路径
_DEFAULT_LOG_FILE = _LOG_DIR / "app.log"

# 日志格式
_FILE_FORMAT = (
    "%(asctime)s %(levelname)-8s %(name)s "
    "[request_id=%(request_id)s job_id=%(job_id)s job_type=%(job_type)s profile_id=%(profile_id)s config_path=%(config_path)s]: %(message)s"
)
_CONSOLE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s [request_id=%(request_id)s job_id=%(job_id)s profile_id=%(profile_id)s]: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_CONSOLE_DATE_FORMAT = "%H:%M:%S"

# 默认轮转大小：10MB
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5

# 全局是否已配置
_configured = False

_LOG_CONTEXT_FIELDS = ("request_id", "job_id", "job_type", "profile_id", "config_path")
_LOG_CONTEXT: dict[str, ContextVar[str | None]] = {
    field: ContextVar(f"log_{field}", default=None) for field in _LOG_CONTEXT_FIELDS
}
_OLD_LOG_RECORD_FACTORY = logging.getLogRecordFactory()


def _install_log_record_factory() -> None:
    """为所有日志记录注入默认上下文字段。"""
    def _record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = _OLD_LOG_RECORD_FACTORY(*args, **kwargs)
        for field, context_var in _LOG_CONTEXT.items():
            value = context_var.get()
            setattr(record, field, value if value is not None else "-")
        return record

    logging.setLogRecordFactory(_record_factory)


_install_log_record_factory()


@contextmanager
def bind_log_context(**kwargs: str | None) -> Iterator[None]:
    """临时绑定日志上下文，退出时自动恢复。"""
    tokens: list[tuple[str, Token[str | None]]] = []
    try:
        for field, value in kwargs.items():
            if field not in _LOG_CONTEXT:
                continue
            tokens.append((field, _LOG_CONTEXT[field].set(value)))
        yield
    finally:
        for field, token in reversed(tokens):
            _LOG_CONTEXT[field].reset(token)


def get_log_context() -> dict[str, str | None]:
    """返回当前线程/协程的日志上下文。"""
    return {field: context_var.get() for field, context_var in _LOG_CONTEXT.items()}


def set_log_context(**kwargs: str | None) -> None:
    """直接设置当前上下文字段。"""
    for field, value in kwargs.items():
        if field not in _LOG_CONTEXT:
            continue
        _LOG_CONTEXT[field].set(value)


def configure_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    backup_count: int = _DEFAULT_BACKUP_COUNT,
    force: bool = False,
) -> None:
    """
    配置项目统一的日志系统。

    分流规则：
    - DEBUG 级别 → 只写入文件（控制台不显示）
    - INFO/WARNING/ERROR → 同时写入控制台和文件

    Args:
        level: 最低日志级别（默认 INFO）
        log_file: 日志文件路径，默认 logs/app.log
        max_bytes: 单个日志文件最大字节数，默认 10MB
        backup_count: 保留的旧日志文件数量，默认 5
        force: 强制重新配置（清除现有 handlers）
    """
    global _configured

    if _configured and not force:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根 logger 捕获所有级别，由 handler 过滤

    # 避免重复添加 handlers
    if force:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    elif root_logger.handlers:
        # 已有 handlers 且非 force，不再重复配置
        _configured = True
        return

    log_path = resolve_project_path(log_file) if log_file else _DEFAULT_LOG_FILE
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 文件 handler：捕获所有级别（DEBUG + INFO + WARNING + ERROR）
    file_handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT))

    # 控制台 handler：只捕获 INFO 及以上
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT, datefmt=_CONSOLE_DATE_FORMAT))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger。

    规范：每个模块使用 get_logger(__name__) 获取 logger，
    日志输出自动带有模块路径前缀，便于定位。
    """
    return logging.getLogger(name)


def set_log_level(logger_name: str, level: str) -> None:
    """动态设置指定 logger 的日志级别。"""
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def add_file_handler(
    logger_name: str | None,
    log_file: str | Path,
    level: str = "DEBUG",
    max_bytes: int = _DEFAULT_MAX_BYTES,
    backup_count: int = _DEFAULT_BACKUP_COUNT,
) -> None:
    """
    为指定 logger（或 root logger）追加一个文件 handler。

    用于需要单独输出日志文件的场景，如回测结果、告警记录等。
    """
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT))
    logger.addHandler(handler)
