"""策略版本 CLI 命令（S7-006）。

子命令：
- strategy build：构建策略版本
- strategy list：列出策略版本
"""

from __future__ import annotations

from datetime import date as Date
from pathlib import Path

import typer

from src.common.logger import get_logger

app = typer.Typer(add_completion=False, help="策略版本相关命令")

logger = get_logger(__name__)


# ============================================================================
# strategy build
# ============================================================================

@app.command("build")
def strategy_build(
    trader: str = typer.Option(..., "--trader", "-t", help="交易员 ID"),
    date: str = typer.Option(..., "--date", "-d", help="策略日期 YYYY-MM-DD"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重建"),
    config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
):
    """构建交易员策略版本（draft）。

    示例：
      python -m cli.main strategy build --trader trader_a --date 2026-04-29
      python -m cli.main strategy build --trader trader_a --date 2026-04-29 --force
    """
    from src.common.config import load_app_config
    from src.pipeline.tasks.strategy_version_tasks import handle_build_trader_strategy_version

    # 解析日期
    try:
        strategy_date = Date.fromisoformat(date)
    except ValueError:
        typer.secho(f"无效日期格式: {date}，请使用 YYYY-MM-DD", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 加载配置
    loaded = load_app_config(config)

    async def _run():
        details = {
            "trader_id": trader,
            "strategy_date": date,
            "force": force,
        }
        try:
            await handle_build_trader_strategy_version(details, config=loaded.config)
            return True, None
        except Exception as exc:
            logger.warning(f"策略版本构建失败: {exc}")
            return False, str(exc)

    import asyncio
    success, error = asyncio.run(_run())

    if success:
        typer.echo(f"\n=== 策略版本构建完成 ===")
        typer.echo(f"  trader={trader}")
        typer.echo(f"  date={date}")
        typer.echo(f"  status=draft")
    else:
        typer.secho(f"\n策略版本构建失败: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


# ============================================================================
# strategy list
# ============================================================================

@app.command("list")
def strategy_list(
    trader: str | None = typer.Option(None, "--trader", "-t", help="交易员 ID（可选）"),
    status: str = typer.Option("all", "--status", "-s",
                               help="状态过滤：all / released / draft / candidate"),
    limit: int = typer.Option(50, "--limit", "-l", help="返回数量限制"),
    config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
):
    """列出策略版本。

    示例：
      python -m cli.main strategy list
      python -m cli.main strategy list --trader trader_a --status released
    """
    from src.common.config import load_app_config
    from src.db.session import session_scope
    from src.models.trader_strategy_version import TraderStrategyVersion
    from sqlalchemy import select

    # 参数校验
    valid_statuses = {"all", "released", "draft", "candidate"}
    if status not in valid_statuses:
        typer.secho(f"无效状态: {status}，可选值：{', '.join(valid_statuses)}",
                    fg=typer.colors.RED)
        raise typer.Exit(code=1)

    loaded = load_app_config(config)

    async def _run():
        async with session_scope() as session:
            conditions = []
            if trader:
                conditions.append(TraderStrategyVersion.trader_id == trader)
            if status != "all":
                conditions.append(TraderStrategyVersion.status == status)

            stmt = select(TraderStrategyVersion).where(*conditions).order_by(
                TraderStrategyVersion.strategy_date.desc(),
                TraderStrategyVersion.version_name,
            ).limit(limit)

            result = await session.execute(stmt)
            rows = result.scalars().all()
            return rows

    import asyncio
    rows = asyncio.run(_run())

    if not rows:
        typer.echo("未找到策略版本")
        return

    typer.echo(f"\n=== 策略版本列表（共 {len(rows)} 条）===")
    for row in rows:
        typer.echo(
            f"  {row.version_name} | {row.trader_id} | {row.strategy_date} | "
            f"status={row.status} | type={getattr(row, 'version_type', 'manual')}"
        )


if __name__ == "__main__":
    app()
