from __future__ import annotations

from typer.testing import CliRunner

from src.services.base import ServiceResult


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


def test_cli_dev_commands_fail_on_service_error(monkeypatch) -> None:
    """dev 命令在服务失败时应返回非零退出码。"""
    from cli.main import app

    runner = CliRunner()

    async def fake_run_workflow(self, **kwargs):  # noqa: ANN001
        return ServiceResult(status="partial", message="workflow not found", payload={"workflow_id": kwargs["workflow_id"]})

    monkeypatch.setattr("cli.main.WorkflowService.run_workflow", fake_run_workflow)
    result = runner.invoke(app, ["dev", "run-workflow", "missing-workflow"])
    assert result.exit_code == 1
    assert "workflow not found" in result.output

    async def fake_migrate(self, *args, **kwargs):  # noqa: ANN001
        return ServiceResult(status="error", message="snapshot failed", payload={"profile_id": "app"})

    monkeypatch.setattr(
        "cli.main.ConfigMigrationService.preview_migration",
        lambda *args, **kwargs: ServiceResult(
            status="ok",
            message="preview",
            payload={
                "profile_id": "app",
                "profile_name": "app",
                "environment": "default",
                "validation_status": "validated",
            },
        ),
    )
    monkeypatch.setattr("cli.main.ConfigMigrationService.migrate_config_path", fake_migrate)
    result = runner.invoke(app, ["dev", "config-migrate", "--config", "config/app.yaml"])
    assert result.exit_code == 1
    assert "snapshot failed" in result.output

    async def fake_run_step(self, **kwargs):  # noqa: ANN001
        return ServiceResult(status="error", message="step failed", payload={"step": kwargs["step"]})

    monkeypatch.setattr("cli.main.PipelineService.run_pipeline_step", fake_run_step)
    result = runner.invoke(app, ["dev", "run-step", "crawl"])
    assert result.exit_code == 1
    assert "step failed" in result.output
