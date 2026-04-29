"""候选池快照 CLI 命令（S7-006）。

子命令：
- snapshot build：构建热点/题材成分/强势池快照
"""

from __future__ import annotations

from datetime import date as Date
from pathlib import Path

import typer

from src.common.logger import get_logger

app = typer.Typer(add_completion=False, help="快照相关命令")

logger = get_logger(__name__)


@app.command("build")
def snapshot_build(
    date: str = typer.Option(..., "--date", "-d", help="交易日期 YYYY-MM-DD"),
    slot: str = typer.Option("17-30", "--slot", "-s", help="时段（盘后默认 17-30）"),
    snapshot_type: str = typer.Option("all", "--type", "-t",
                                      help="快照类型：all / hot_topics / topic_constituents / strong_symbols"),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖已有快照"),
    config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
):
    """构建候选池快照（热点/题材成分/强势池）。

    示例：
      python -m cli.main snapshot build --date 2026-04-29
      python -m cli.main snapshot build --date 2026-04-29 --type hot_topics --force
    """
    from src.common.config import load_app_config
    from src.pipeline.tasks.snapshot_tasks import (
        handle_hot_topics_snapshot,
        handle_topic_constituents_snapshot,
        handle_strong_symbols_snapshot,
    )

    # 解析日期
    try:
        trade_date = Date.fromisoformat(date)
    except ValueError:
        typer.secho(f"无效日期格式: {date}，请使用 YYYY-MM-DD", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # 加载配置
    loaded = load_app_config(config)

    # 确定要构建的类型
    types_to_build = []
    if snapshot_type == "all":
        types_to_build = ["hot_topics", "topic_constituents", "strong_symbols"]
    elif snapshot_type in ("hot_topics", "topic_constituents", "strong_symbols"):
        types_to_build = [snapshot_type]
    else:
        typer.secho(f"无效类型: {snapshot_type}，可选值：all / hot_topics / topic_constituents / strong_symbols",
                    fg=typer.colors.RED)
        raise typer.Exit(code=1)

    async def _run():
        results = {}
        for stype in types_to_build:
            details = {"trade_date": date, "slot": slot, "force": force}
            try:
                if stype == "hot_topics":
                    await handle_hot_topics_snapshot(details, config=loaded.config)
                    results["hot_topics"] = "✓ 已保存"
                elif stype == "topic_constituents":
                    await handle_topic_constituents_snapshot(details, config=loaded.config)
                    results["topic_constituents"] = "✓ 已保存"
                elif stype == "strong_symbols":
                    await handle_strong_symbols_snapshot(details, config=loaded.config)
                    results["strong_symbols"] = "✓ 已保存"
            except Exception as exc:
                logger.warning(f"快照构建失败 {stype}: {exc}")
                results[stype] = f"✗ 失败: {exc}"

        return results

    import asyncio
    results = asyncio.run(_run())

    typer.echo(f"\n=== 快照构建完成 ===")
    typer.echo(f"  date={date}, slot={slot}")
    for stype, status in results.items():
        typer.echo(f"  {stype}: {status}")


if __name__ == "__main__":
    app()
