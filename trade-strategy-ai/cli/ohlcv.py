# cli/ohlcv.py
"""OHLCV 数据抓取 CLI 命令

提供以下子命令：
- ohlcv crawl：抓取日线数据并存入数据库
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import typer

from src.common.logger import get_logger

logger = get_logger(__name__)

app = typer.Typer(add_completion=False, help="OHLCV 数据相关命令")


def _parse_date(value: str) -> date:
    """解析 YYYY-MM-DD 格式日期"""
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.command("crawl")
def crawl_ohlcv(
    mode: str = typer.Option("incremental", "--mode", help="full / incremental"),
    symbols_file: Path | None = typer.Option(None, "--symbols-file", help="股票列表文件（每行一个代码）"),
    start_date: str | None = typer.Option(None, "--from", help="起始日期 YYYY-MM-DD"),
    end_date: str | None = typer.Option(None, "--to", help="结束日期 YYYY-MM-DD"),
    limit: int = typer.Option(100, "--limit", help="最多抓取标的数量（full 模式）"),
) -> None:
    """抓取 ohlcv 数据并存入数据库。

    示例：
        python -m cli.main ohlcv crawl --mode incremental
        python -m cli.main ohlcv crawl --mode full --from 2026-01-01 --to 2026-04-28
        python -m cli.main ohlcv crawl --symbols-file symbols.txt
    """
    # 解析日期
    start = _parse_date(start_date) if start_date else None
    end = _parse_date(end_date) if end_date else date.today()

    # 读取标的列表
    symbols = _load_symbols(symbols_file, mode, limit)

    logger.info(
        "CLI ohlcv crawl: mode=%s, symbols=%d, start=%s, end=%s",
        mode,
        len(symbols),
        start,
        end,
    )

    # 执行抓取
    import asyncio
    from config.database import get_session_factory
    from src.market_data.ohlcv_service import OHLCVService

    async def run_crawl():
        factory = get_session_factory()
        service = OHLCVService(session_factory=factory)

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

        return results

    results = asyncio.run(run_crawl())

    # 输出摘要
    success = sum(1 for c in results.values() if c > 0)
    total = sum(results.values())
    typer.echo(f"抓取完成: {success}/{len(symbols)} 标的成功, 共 {total} 条记录")


def _load_symbols(symbols_file: Path | None, mode: str, limit: int) -> list[str]:
    """加载标的列表"""
    if symbols_file:
        if not symbols_file.exists():
            typer.secho(f"文件不存在: {symbols_file}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        return [line.strip() for line in symbols_file.read_text().splitlines() if line.strip()][:limit]

    # 默认：从数据库获取股票列表
    import asyncio
    from sqlalchemy import select
    from src.models.stock_info import StockInfo
    from src.db.session import session_scope

    async def get_symbols():
        symbols = []
        async with session_scope() as session:
            stmt = select(StockInfo.symbol).where(
                StockInfo.security_type == "stock"
            ).limit(limit)
            result = await session.scalars(stmt)
            symbols = list(result.all())
        return symbols

    return asyncio.run(get_symbols())


if __name__ == "__main__":
    app()
