from __future__ import annotations


def test_cli_registers_job_worker_start_command() -> None:
    """生产启动入口应暴露 job-worker-start 命令。"""
    from cli.main import app
    from typer.main import get_command

    click_app = get_command(app)
    assert "job-worker-start" in click_app.commands


def test_cli_registers_dev_debug_commands() -> None:
    """CLI 应保留 dev 调试入口，正式用户路径应转向 Web。"""
    from cli.main import app
    from typer.main import get_command

    click_app = get_command(app)
    assert "dev" in click_app.commands
    dev_app = click_app.commands["dev"]
    assert "run-step" in dev_app.commands
    assert "run-workflow" in dev_app.commands
    assert "list-workflows" in dev_app.commands
    assert "config-migrate" in dev_app.commands
