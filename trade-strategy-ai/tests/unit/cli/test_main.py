from __future__ import annotations


def test_cli_registers_job_worker_start_command() -> None:
    """生产启动入口应暴露 job-worker-start 命令。"""
    from cli.main import app
    from typer.main import get_command

    click_app = get_command(app)
    assert "job-worker-start" in click_app.commands
