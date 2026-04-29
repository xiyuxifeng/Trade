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
from src.common.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer(add_completion=False, help="回测相关命令")


def _parse_date(value: str) -> date:
    """解析 YYYY-MM-DD 格式日期"""
    return datetime.strptime(value, "%Y-%m-%d").date()  # noqa: DTZ007


def _create_engine_from_config(config_path: str | None) -> BacktestEngine:
    """从配置创建 BacktestEngine（带依赖注入）。

    若未提供配置或配置中未定义回测依赖，则返回无 loader 的引擎（所有记录为 skipped）。
    """
    if config_path is None:
        return BacktestEngine()

    from src.common.config import load_app_config

    try:
        loaded = load_app_config(config_path)
    except Exception as exc:
        typer.secho(f"配置加载失败: {exc}", fg=typer.colors.YELLOW)
        return BacktestEngine()

    # 初始化 SnapshotService
    from src.market_universe.snapshot_service import SnapshotService

    snapshot_service = SnapshotService(
        base_dir="data/market_universe/snapshots"
    )

    # 初始化 StrategyRepoAdapter
    from src.market_data.strategy_repo_adapter import StrategyRepoAdapter

    strategy_repo_adapter = StrategyRepoAdapter()

    from src.backtest.snapshot_loader import SnapshotLoader

    loader = SnapshotLoader(
        snapshot_service=snapshot_service,
        strategy_repo=strategy_repo_adapter,
    )
    return BacktestEngine(loader=loader, strategy_loader=loader)



def _run_async(coro):
    """在同步上下文中执行异步任务，兼容已有事件循环。"""
    try:
        return asyncio.run(coro)
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

    logger.info(
        "CLI 回测命令: trader=%s, date_from=%s, date_to=%s, mode=%s",
        trader,
        date_from,
        date_to,
        mode,
    )
    engine = _create_engine_from_config(str(config) if config else None)
    result = engine.run_sync(request)

    # 结果摘要
    traded = sum(1 for r in result.records if r.status == "traded")
    skipped = sum(1 for r in result.records if r.status == "skipped")
    logger.info(
        "CLI 回测结果: trader=%s, total=%d, traded=%d, skipped=%d",
        trader,
        len(result.records),
        traded,
        skipped,
    )

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
    from src.backtest.schemas import BacktestResult, BacktestSummary, BacktestTradeRecord

    records = []
    for record in data.get("records", []):
        records.append(
            BacktestTradeRecord(
                trade_date=date.fromisoformat(record["trade_date"]),
                trader_id=record.get("trader_id", ""),
                strategy_version_id=record.get("strategy_version_id", ""),
                symbol=record.get("symbol", ""),
                status=record.get("status", "skipped"),
                entry_price=record.get("entry_price"),
                exit_price=record.get("exit_price"),
                entry_date=record.get("entry_date"),
                exit_date=record.get("exit_date"),
                return_pct=record.get("return_pct"),
                mfe=record.get("mfe"),
                mae=record.get("mae"),
                volume=record.get("volume"),
                is_valid_lot_size=record.get("is_valid_lot_size"),
                skip_reason=record.get("skip_reason"),
                evidence_refs=record.get("evidence_refs", []),
            )
        )

    summary_data = data.get("summary")
    summary = None
    if summary_data:
        summary = BacktestSummary(
            total_days=summary_data.get("total_days", 0),
            total_trades=summary_data.get("total_trades", 0),
            valid_trades=summary_data.get("valid_trades", 0),
            skipped_trades=summary_data.get("skipped_trades", 0),
            win_rate=summary_data.get("win_rate"),
            avg_return_pct=summary_data.get("avg_return_pct"),
        )

    result = BacktestResult(
        request_trader_id=data["request_trader_id"],
        request_date_from=date.fromisoformat(data["request_date_from"]),
        request_date_to=date.fromisoformat(data["request_date_to"]),
        records=records,
        summary=summary,
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
    config: Path | None = typer.Option(None, "--config", help="应用配置文件路径（YAML）"),
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

    engine = _create_engine_from_config(str(config) if config else None)
    # validate_rules_for_trader 需要 SnapshotLoader，取 engine.strategy_loader（亦为 SnapshotLoader）
    loader = engine.loader if isinstance(engine.loader, SnapshotLoader) else SnapshotLoader()
    rule_results = _run_async(
        validate_rules_for_trader(trader_id=trader, date_from=date_from, date_to=date_to, loader=loader)
    )

    logger.info(
        "CLI 规则验真完成: trader=%s, date_from=%s, date_to=%s, total_rules=%d",
        trader,
        date_from,
        date_to,
        len(rule_results),
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
    config: Path | None = typer.Option(None, "--config", help="应用配置文件路径（YAML）"),
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

    engine = _create_engine_from_config(str(config) if config else None)

    result_a = engine.run_sync(request)
    result_b = engine.run_sync(request)

    # 比较两次结果的 JSON 序列化
    json_a = render_backtest_json(result_a)
    json_b = render_backtest_json(result_b)

    logger.info(
        "CLI Reproducibility Check: trader=%s, date_from=%s, date_to=%s",
        trader,
        date_from,
        date_to,
    )
    if json_a == json_b:
        typer.secho("✅ Reproducibility Check PASSED: 两次运行结果一致", fg=typer.colors.GREEN)
    else:
        typer.secho("❌ Reproducibility Check FAILED: 两次运行结果不一致", fg=typer.colors.RED)
        typer.echo("差异可能来源：快照缺失补齐、输出排序不稳定、浮点 round 不一致")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
