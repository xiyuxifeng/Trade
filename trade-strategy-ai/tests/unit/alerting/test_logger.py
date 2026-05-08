from __future__ import annotations

from pathlib import Path

from src.common.paths import project_root


def test_alert_file_logger_defaults_to_project_root() -> None:
    """告警日志默认应落到 trade-strategy-ai/data/logs。"""
    from src.alerting.logger_ import AlertFileLogger

    logger = AlertFileLogger()

    assert logger.log_path == project_root() / "data" / "logs" / "alert.log"
    assert logger.log_path.exists()

    # 这里不删除目录，避免干扰后续测试；只清掉文件内容即可。
    logger.log_path.write_text("", encoding="utf-8")
