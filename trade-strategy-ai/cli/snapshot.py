"""候选池快照 CLI 命令（S7-006）。

子命令：
- snapshot build：构建热点/题材成分/强势池快照
"""

from __future__ import annotations

import re
from datetime import date as Date
from pathlib import Path

import typer

from src.common.logger import get_logger

app = typer.Typer(add_completion=False, help="快照相关命令")

logger = get_logger(__name__)

# 匹配 raw 数据目录名：YYYY-MM-DD_HH-MM
_RAW_DIR_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2})$")


def _discover_raw_dirs(raw_base: Path, slot_filter: str | None = None) -> list[tuple[str, str]]:
    """扫描 raw 数据目录，返回 (date_str, slot) 列表，按日期排序去重。

    Args:
        raw_base: data/kaipan/raw/ 目录
        slot_filter: 可选，只匹配指定时段
    """
    combos: set[tuple[str, str]] = set()
    if not raw_base.exists():
        return []

    for dataset_dir in raw_base.iterdir():
        if not dataset_dir.is_dir():
            continue
        for date_dir in dataset_dir.iterdir():
            if not date_dir.is_dir():
                continue
            m = _RAW_DIR_PATTERN.match(date_dir.name)
            if not m:
                continue
            date_str = m.group(1)
            slot = m.group(2)
            if slot_filter and slot != slot_filter:
                continue
            combos.add((date_str, slot))

    return sorted(combos, key=lambda x: (x[0], x[1]))


@app.command("build")
def snapshot_build(
    date: str | None = typer.Option(None, "--date", "-d", help="交易日期 YYYY-MM-DD（离线模式不指定则处理 raw 目录下所有日期）"),
    slot: str = typer.Option("17-30", "--slot", "-s", help="时段（盘后默认 17-30）"),
    snapshot_type: str = typer.Option("all", "--type", "-t",
                                      help="快照类型：all / hot_topics / topic_constituents / strong_symbols"),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖已有快照"),
    offline: bool = typer.Option(False, "--offline", "-o", help="离线模式：从 data/kaipan/raw/ 读取已有数据，跳过网络请求"),
    config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
):
    """构建候选池快照（热点/题材成分/强势池）。

    示例：
      python -m cli.main snapshot build --date 2026-04-29
      python -m cli.main snapshot build --date 2026-04-29 --type hot_topics --force
      python -m cli.main snapshot build --date 2026-04-29 --offline
      python -m cli.main snapshot build --offline          # 离线模式处理所有已缓存的日期
    """
    from src.common.config import load_app_config
    from src.pipeline.tasks.snapshot_tasks import (
        handle_hot_topics_snapshot,
        handle_topic_constituents_snapshot,
        handle_strong_symbols_snapshot,
    )

    # 离线模式且未指定 date：扫描 raw 目录获取所有日期
    if offline and date is None:
        raw_base = Path("data/kaipan/raw")
        date_slots = _discover_raw_dirs(raw_base)
        if not date_slots:
            typer.secho("离线模式: data/kaipan/raw/ 下未找到任何 raw 数据目录", fg=typer.colors.YELLOW)
            raise typer.Exit(code=0)
        typer.echo(f"离线模式: 发现 {len(date_slots)} 个日期/时段组合")
    elif date is None:
        typer.secho("在线模式必须指定 --date", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    else:
        # 单日期模式
        try:
            Date.fromisoformat(date)
        except ValueError:
            typer.secho(f"无效日期格式: {date}，请使用 YYYY-MM-DD", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        date_slots = [(date, slot)]

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

    async def _run_single(d: str, s: str) -> dict[str, str]:
        """处理单个日期/时段组合。"""
        results: dict[str, str] = {}
        for stype in types_to_build:
            details = {"trade_date": d, "slot": s, "force": force, "offline": offline}
            try:
                if stype == "hot_topics":
                    await handle_hot_topics_snapshot(details, config=loaded.config)
                    results["hot_topics"] = "✓"
                elif stype == "topic_constituents":
                    await handle_topic_constituents_snapshot(details, config=loaded.config)
                    results["topic_constituents"] = "✓"
                elif stype == "strong_symbols":
                    await handle_strong_symbols_snapshot(details, config=loaded.config)
                    results["strong_symbols"] = "✓"
            except Exception as exc:
                logger.warning(f"快照构建失败 {stype} date={d} slot={s}: {exc}")
                results[stype] = f"✗ {exc}"
        return results

    from config.database import run_async_with_cleanup

    mode_label = " (离线)" if offline else ""
    total_ok = 0
    total_fail = 0

    for idx, (d, s) in enumerate(date_slots):
        if len(date_slots) > 1:
            typer.echo(f"\n[{idx + 1}/{len(date_slots)}] date={d} slot={s}")

        results = run_async_with_cleanup(_run_single(d, s))

        ok_count = sum(1 for v in results.values() if v == "✓")
        fail_count = len(results) - ok_count
        total_ok += ok_count
        total_fail += fail_count

        if len(date_slots) == 1:
            typer.echo(f"\n=== 快照构建完成{mode_label} ===")
            typer.echo(f"  date={d}, slot={s}")
            for stype, status in results.items():
                typer.echo(f"  {stype}: {'已保存' if status == '✓' else status}")

    if len(date_slots) > 1:
        typer.echo(f"\n=== 批量快照构建完成{mode_label} ===")
        typer.echo(f"  共 {len(date_slots)} 个日期/时段，{total_ok} 成功，{total_fail} 失败")


if __name__ == "__main__":
    app()
