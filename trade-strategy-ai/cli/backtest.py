"""NTL-S6-008: 回测 CLI 入口。"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path

import typer

from src.common.logger import get_logger
from src.services.backtest_service import BacktestService

logger = get_logger(__name__)

app = typer.Typer(add_completion=False, help="回测相关命令")


def _parse_date(value: str) -> date:
    """解析 YYYY-MM-DD 格式日期。"""
    return datetime.strptime(value, "%Y-%m-%d").date()  # noqa: DTZ007


def _run_async(coro):
    """在同步上下文中执行异步任务，并在完成后优雅关闭数据库连接池。"""
    from config.database import run_async_with_cleanup

    try:
        return run_async_with_cleanup(coro)
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)


@app.command("run")
def run_backtest(
    trader: str = typer.Option(..., "--trader", help="交易员 ID"),
    from_date: str = typer.Option(..., "--from", help="回测开始日期 YYYY-MM-DD"),
    to_date: str = typer.Option(..., "--to", help="回测结束日期 YYYY-MM-DD"),
    strategy_version_id: str | None = typer.Option(None, "--strategy-version", help="策略版本 ID（可选）"),
    mode: str = typer.Option("full", "--mode", help="运行模式：full / replay / rule_validation"),
    output: Path | None = typer.Option(None, "--output", help="结果输出路径（默认打印到 stdout）"),
    format: str = typer.Option("markdown", "--format", help="输出格式：markdown / json"),
    config: Path | None = typer.Option(None, "--config", help="应用配置文件路径（YAML）"),
) -> None:
    """运行离线回测。"""
    date_from = _parse_date(from_date)
    date_to = _parse_date(to_date)
    service = BacktestService()

    logger.info(
        "CLI 回测命令: trader=%s, date_from=%s, date_to=%s, mode=%s",
        trader,
        date_from,
        date_to,
        mode,
    )
    result = service.run_backtest(
        trader_id=trader,
        date_from=date_from,
        date_to=date_to,
        strategy_version_id=strategy_version_id,
        mode=mode,
        config_path=config,
    )

    traded = sum(1 for r in result.payload["result"]["records"] if r["status"] == "traded")
    skipped = sum(1 for r in result.payload["result"]["records"] if r["status"] == "skipped")
    logger.info(
        "CLI 回测结果: trader=%s, total=%d, traded=%d, skipped=%d",
        trader,
        len(result.payload["result"]["records"]),
        traded,
        skipped,
    )

    rendered = service.render_backtest_report(result.payload["result"], format=format)
    output_str = rendered.payload["content"]

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
    """基于已有回测结果文件生成报告。"""
    service = BacktestService()

    if not result_file.exists():
        typer.echo(f"结果文件不存在: {result_file}")
        raise typer.Exit(code=1)

    loaded = service.load_backtest_result(result_file=result_file)
    rendered = service.render_backtest_report(loaded.payload["result"], format=format)
    output_str = rendered.payload["content"]

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
    config: Path | None = typer.Option(None, "--config", help="应用配置文件路径（YAML）"),
) -> None:
    """对策略版本中的高频规则做命中验证。"""
    date_from = _parse_date(from_date)
    date_to = _parse_date(to_date)
    service = BacktestService()

    result = _run_async(
        service.validate_rules(
            trader_id=trader,
            date_from=date_from,
            date_to=date_to,
            config_path=config,
        )
    )

    logger.info(
        "CLI 规则验真完成: trader=%s, date_from=%s, date_to=%s, total_rules=%d",
        trader,
        date_from,
        date_to,
        len(result.payload["results"]),
    )

    report = result.payload["report"]
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
    config: Path | None = typer.Option(None, "--config", help="应用配置文件路径（YAML）"),
) -> None:
    """验证回测结果可复现。"""
    date_from = _parse_date(from_date)
    date_to = _parse_date(to_date)
    service = BacktestService()

    result = service.reproducibility_check(
        trader_id=trader,
        date_from=date_from,
        date_to=date_to,
        config_path=config,
    )

    logger.info(
        "CLI Reproducibility Check: trader=%s, date_from=%s, date_to=%s",
        trader,
        date_from,
        date_to,
    )
    if result.payload["matches"]:
        typer.secho("✅ Reproducibility Check PASSED: 两次运行结果一致", fg=typer.colors.GREEN)
    else:
        typer.secho("❌ Reproducibility Check FAILED: 两次运行结果不一致", fg=typer.colors.RED)
        typer.echo("差异可能来源：快照缺失补齐、输出排序不稳定、浮点 round 不一致")
        raise typer.Exit(code=1)


@app.command("rule-pool-run")
def rule_pool_run(
    start_date: str = typer.Option(..., "--start-date", help="回测开始日期 YYYY-MM-DD"),
    end_date: str = typer.Option(..., "--end-date", help="回测结束日期 YYYY-MM-DD"),
    rule_ids: str | None = typer.Option(None, "--rule-ids", help="规则 ID 列表（逗号分隔，不传则回测全部审核通过的规则）"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", help="最小置信度阈值"),
    config: Path | None = typer.Option(None, "--config", help="应用配置文件路径（YAML）"),
) -> None:
    """对规则池中的规则执行回测。"""
    date_from = _parse_date(start_date)
    date_to = _parse_date(end_date)
    parsed_rule_ids: list[str] | None = None
    if rule_ids:
        parsed_rule_ids = [rid.strip() for rid in rule_ids.split(",") if rid.strip()]

    service = BacktestService()
    result = _run_async(
        service.run_rule_pool_backtest(
            start_date=date_from,
            end_date=date_to,
            rule_ids=parsed_rule_ids,
            min_confidence=min_confidence,
            config_path=config,
        )
    )

    summary = result.payload["summary"]
    if summary is None:
        typer.echo("规则池回测结果为空（未找到符合条件的规则）")
        return

    typer.echo("=" * 60)
    typer.echo("规则池回测汇总")
    typer.echo("=" * 60)
    typer.echo(f"  总交易日:   {summary['total_days']}")
    typer.echo(f"  总交易数:   {summary['total_trades']}")
    typer.echo(f"  有效交易:   {summary['valid_trades']}")
    typer.echo(f"  跳过交易:   {summary['skipped_trades']}")
    typer.echo(f"  胜率:       {summary['win_rate'] or 0:.2%}")
    typer.echo(f"  平均收益率: {summary['avg_return_pct'] or 0:.4%}")
    typer.echo(f"  规则数:     {len(result.payload['result']['records'])}")

    if result.payload["result"]["records"]:
        typer.echo("")
        typer.echo("各规则结果:")
        for rec in result.payload["result"]["records"][:20]:
            typer.echo(f"  {rec['strategy_version_id']}: return={rec['return_pct'] or 0:+.4%}")
        if len(result.payload["result"]["records"]) > 20:
            typer.echo(f"  ... 还有 {len(result.payload['result']['records']) - 20} 条未显示")


if __name__ == "__main__":
    app()
