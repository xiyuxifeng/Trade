"""NTL-S6-008: 回测 CLI 入口

提供以下子命令：
- backtest run：运行回测
- backtest report：生成回测报告
- backtest validate-rules：规则验真
- backtest reproducibility-check：复现验证
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path

import typer

from src.backtest.engine import BacktestEngine
from src.backtest.reporting import render_backtest_json, render_backtest_markdown
from src.backtest.schemas import BacktestRequest

app = typer.Typer(add_completion=False, help="回测相关命令")


def _parse_date(value: str) -> date:
    """解析 YYYY-MM-DD 格式日期"""
    return datetime.strptime(value, "%Y-%m-%d").date()  # noqa: DTZ007


@app.command("run")
def run_backtest(
    trader: str = typer.Option(..., "--trader", help="交易员 ID"),
    from_date: str = typer.Option(..., "--from", help="回测开始日期 YYYY-MM-DD"),
    to_date: str = typer.Option(..., "--to", help="回测结束日期 YYYY-MM-DD"),
    strategy_version_id: str | None = typer.Option(None, "--strategy-version", help="策略版本 ID（可选）"),
    mode: str = typer.Option("full", "--mode", help="运行模式：full / replay / rule_validation"),
    output: Path | None = typer.Option(None, "--output", help="结果输出路径（默认打印到 stdout）"),
    format: str = typer.Option("markdown", "--format", help="输出格式：markdown / json"),
) -> None:
    """运行离线回测。

    示例：
        python -m cli.main backtest run --trader trader_a --from 2026-04-01 --to 2026-04-10
        python -m cli.main backtest run --trader trader_a --from 2026-04-01 --to 2026-04-20 --mode replay
    """
    date_from = _parse_date(from_date)
    date_to = _parse_date(to_date)

    request = BacktestRequest(
        trader_id=trader,
        date_from=date_from,
        date_to=date_to,
        strategy_version_id=strategy_version_id,
        mode=mode,  # type: ignore[arg-type]
    )

    engine = BacktestEngine()
    result = engine.run_sync(request)

    if format == "json":
        output_str = render_backtest_json(result)
    else:
        output_str = render_backtest_markdown(result)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(output_str, encoding="utf-8")
        typer.echo(f"结果已写入: {output}")
    else:
        typer.echo(output_str)


@app.command("report")
def backtest_report(
    trader: str = typer.Option(..., "--trader", help="交易员 ID"),
    from_date: str = typer.Option(..., "--from", help="回测开始日期 YYYY-MM-DD"),
    to_date: str = typer.Option(..., "--to", help="回测结束日期 YYYY-MM-DD"),
    result_file: Path = typer.Option(..., "--result-file", help="回测结果 JSON 文件路径"),
    output: Path | None = typer.Option(None, "--output", help="报告输出路径"),
    format: str = typer.Option("markdown", "--format", help="输出格式：markdown / json"),
) -> None:
    """基于已有回测结果文件生成报告。

    示例：
        python -m cli.main backtest report --trader trader_a --from 2026-04-01 --to 2026-04-10 --result-file data/processed/backtest/result.json
    """
    import json

    if not result_file.exists():
        typer.echo(f"结果文件不存在: {result_file}")
        raise typer.Exit(code=1)

    data = json.loads(result_file.read_text(encoding="utf-8"))
    from src.backtest.schemas import BacktestResult

    result = BacktestResult(
        request_trader_id=data["request_trader_id"],
        request_date_from=date.fromisoformat(data["request_date_from"]),
        request_date_to=date.fromisoformat(data["request_date_to"]),
        records=[],  # type: ignore[arg-type]
        summary=None,
    )

    if format == "json":
        output_str = render_backtest_json(result)
    else:
        output_str = render_backtest_markdown(result)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(output_str, encoding="utf-8")
        typer.echo(f"报告已写入: {output}")
    else:
        typer.echo(output_str)


@app.command("validate-rules")
def validate_rules(
    trader: str = typer.Option(..., "--trader", help="交易员 ID"),
    from_date: str = typer.Option(..., "--from", help="验真开始日期 YYYY-MM-DD"),
    to_date: str = typer.Option(..., "--to", help="验真结束日期 YYYY-MM-DD"),
    output: Path | None = typer.Option(None, "--output", help="结果输出路径"),
) -> None:
    """对策略版本中的高频规则做命中验证。

    示例：
        python -m cli.main backtest validate-rules --trader trader_a --from 2026-04-01 --to 2026-04-10
    """
    date_from = _parse_date(from_date)
    date_to = _parse_date(to_date)

    from src.backtest.engine import validate_rules_for_trader
    from src.backtest.reporting import render_rule_validation_markdown
    from src.backtest.snapshot_loader import SnapshotLoader

    # 创建 SnapshotLoader（strategy_repo 需外部注入，当前为 stub）
    loader = SnapshotLoader()
    rule_results = asyncio.run(
        validate_rules_for_trader(trader_id=trader, date_from=date_from, date_to=date_to, loader=loader)
    )

    report = render_rule_validation_markdown(rule_results)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        typer.echo(f"规则验真报告已写入: {output}")
    else:
        typer.echo(report)


@app.command("reproducibility-check")
def reproducibility_check(
    trader: str = typer.Option(..., "--trader", help="交易员 ID"),
    from_date: str = typer.Option(..., "--from", help="回测开始日期 YYYY-MM-DD"),
    to_date: str = typer.Option(..., "--to", help="回测结束日期 YYYY-MM-DD"),
) -> None:
    """验证回测结果可复现（相同请求运行两次，对比 hash）。

    示例：
        python -m cli.main backtest reproducibility-check --trader trader_a --from 2026-04-01 --to 2026-04-10
    """
    date_from = _parse_date(from_date)
    date_to = _parse_date(to_date)

    request = BacktestRequest(
        trader_id=trader,
        date_from=date_from,
        date_to=date_to,
    )

    engine = BacktestEngine()

    result_a = engine.run_sync(request)
    result_b = engine.run_sync(request)

    # 比较两次结果的 JSON 序列化
    json_a = render_backtest_json(result_a)
    json_b = render_backtest_json(result_b)

    if json_a == json_b:
        typer.secho("✅ Reproducibility Check PASSED: 两次运行结果一致", fg=typer.colors.GREEN)
    else:
        typer.secho("❌ Reproducibility Check FAILED: 两次运行结果不一致", fg=typer.colors.RED)
        typer.echo("差异可能来源：快照缺失补齐、输出排序不稳定、浮点 round 不一致")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
