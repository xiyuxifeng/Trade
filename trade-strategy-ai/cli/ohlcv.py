# cli/ohlcv.py
"""OHLCV 数据抓取 CLI 命令

提供以下子命令：
- ohlcv crawl：抓取日线数据并存入数据库
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from pathlib import Path

import typer
from sqlalchemy import select

from config.database import get_engine, get_session_factory, run_async_with_cleanup
from src.common.logger import get_logger
from src.db.session import session_scope
from src.market_data.ohlcv_service import OHLCVService
from src.models.stock_info import StockInfo

logger = get_logger(__name__)

app = typer.Typer(add_completion=False, help="OHLCV 数据相关命令")


def _parse_date(value: str) -> date:
    """解析 YYYY-MM-DD 格式日期"""
    return datetime.strptime(value, "%Y-%m-%d").date()


async def _load_symbols_from_db(limit: int) -> list[str]:
    """从数据库加载标的列表"""
    async with session_scope() as session:
        stmt = select(StockInfo.symbol).where(
            StockInfo.security_type == "stock"
        ).limit(limit)
        result = await session.scalars(stmt)
        return list(result.all())


@app.command("crawl")
def crawl_ohlcv(
    mode: str = typer.Option("incremental", "--mode", help="full / incremental"),
    symbols_file: Path | None = typer.Option(None, "--symbols-file", help="股票列表文件（每行一个代码）"),
    start_date: str | None = typer.Option(None, "--from", help="起始日期 YYYY-MM-DD"),
    end_date: str | None = typer.Option(None, "--to", help="结束日期 YYYY-MM-DD"),
    limit: int = typer.Option(100, "--limit", help="最多抓取标的数量（full 模式）"),
    config: Path = typer.Option(Path("config/app.yaml"), help="配置文件路径"),
) -> None:
    """抓取 ohlcv 数据并存入数据库。

    示例：
        python -m cli.main ohlcv crawl --mode incremental
        python -m cli.main ohlcv crawl --mode full --from 2026-01-01 --to 2026-04-28
        python -m cli.main ohlcv crawl --symbols-file symbols.txt
    """
    # 加载配置以获取 akshare 限速参数
    from src.common.config import load_app_config

    loaded = load_app_config(config)
    akshare_cfg = loaded.config.akshare

    # 解析日期
    start = _parse_date(start_date) if start_date else None
    end = _parse_date(end_date) if end_date else date.today()

    # 从文件加载标的列表（同步，不涉及数据库）
    file_symbols: list[str] | None = None
    if symbols_file:
        if not symbols_file.exists():
            typer.secho(f"文件不存在: {symbols_file}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        file_symbols = [line.strip() for line in symbols_file.read_text().splitlines() if line.strip()][:limit]

    # 统一在一个事件循环中完成数据库查询和抓取，避免 "Future attached to a different loop"
    async def _run_all():
        try:
            # 加载标的列表
            if file_symbols is not None:
                symbols = file_symbols
            else:
                symbols = await _load_symbols_from_db(limit)

            logger.info(
                "CLI ohlcv crawl: mode=%s, symbols=%d, start=%s, end=%s",
                mode, len(symbols), start, end,
            )

            # 执行抓取（传入限速配置）
            factory = get_session_factory()
            service = OHLCVService(
                session_factory=factory,
                min_request_interval_seconds=akshare_cfg.min_request_interval_seconds,
                max_retries=akshare_cfg.max_retries,
                retry_backoff_seconds=akshare_cfg.retry_backoff_seconds,
                fallback_enabled=akshare_cfg.fallback_enabled,
            )

            if mode == "full":
                results = await service.crawl_bars(
                    symbols=symbols,
                    start_date=start,
                    end_date=end,
                )
            else:
                # incremental: 只抓取 end 日期的数据
                results = await service.crawl_bars(
                    symbols=symbols,
                    start_date=end,
                    end_date=end,
                )

            return len(symbols), results
        finally:
            # 优雅关闭数据库连接池
            await get_engine().dispose()

    num_symbols, results = run_async_with_cleanup(_run_all())

    # 输出摘要
    success = sum(1 for c in results.values() if c > 0)
    total = sum(results.values())
    typer.echo(f"抓取完成: {success}/{num_symbols} 标的成功, 共 {total} 条记录")


if __name__ == "__main__":
    app()
