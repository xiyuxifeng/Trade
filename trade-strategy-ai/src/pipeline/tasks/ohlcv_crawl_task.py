# src/pipeline/tasks/ohlcv_crawl_task.py
"""ohlcv_crawl Pipeline Task

Task handler for ohlcv data crawling.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from src.common.config import AppConfig
from src.common.logger import get_logger

logger = get_logger(__name__)


async def handle_ohlcv_crawl(
    details: dict[str, Any],
    *,
    config: AppConfig,
) -> None:
    """Task handler for ohlcv crawl.

    details 期望字段：
        mode: "full" | "incremental"
        symbols: list[str] | None
        start_date: str | None
        end_date: str | None
    """
    from config.database import get_session_factory
    from src.market_data.ohlcv_service import OHLCVService
    from src.services.dataset_snapshot_service import DatasetSnapshotService

    mode = details.get("mode", "incremental")
    symbols = details.get("symbols")
    start_date_str = details.get("start_date")
    end_date_str = details.get("end_date")

    start_date = date.fromisoformat(start_date_str) if start_date_str else None
    end_date = date.fromisoformat(end_date_str) if end_date_str else date.today()

    factory = get_session_factory()
    akshare_cfg = config.akshare
    service = OHLCVService(
        session_factory=factory,
        min_request_interval_seconds=akshare_cfg.min_request_interval_seconds,
        max_retries=akshare_cfg.max_retries,
        retry_backoff_seconds=akshare_cfg.retry_backoff_seconds,
        fallback_enabled=akshare_cfg.fallback_enabled,
    )

    logger.info(
        "ohlcv_crawl task: mode=%s, symbols=%s, start=%s, end=%s",
        mode,
        len(symbols) if symbols else "all",
        start_date,
        end_date,
    )

    if mode == "full":
        if symbols is None:
            # 全量模式需要标的列表
            logger.warning("ohlcv_crawl full 模式需要 symbols 参数，跳过")
            return
        market_kind_by_symbol = None
        results = await service.crawl_bars(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            market_kind_by_symbol=market_kind_by_symbol,
        )
    else:
        # 增量模式：只抓取 end_date 当日
        if symbols is None:
            # 从数据库加载所有股票代码
            from sqlalchemy import select
            from src.models.stock_info import StockInfo

            async with factory() as session:
                stmt = select(StockInfo.symbol, StockInfo.security_type).where(
                    StockInfo.security_type.in_(["stock", "index"])
                )
                result = await session.execute(stmt)
                rows = result.all()
                symbols = [row[0] for row in rows]
                market_kind_by_symbol = {row[0]: row[1] for row in rows}
        else:
            market_kind_by_symbol = None

        results = await service.crawl_bars(
            symbols=symbols,
            start_date=end_date,
            end_date=end_date,
            market_kind_by_symbol=market_kind_by_symbol,
        )

    effective_start = start_date if mode == "full" and start_date is not None else end_date
    effective_end = end_date
    if effective_start is not None and effective_end is not None and any(count > 0 for count in results.values()):
        snapshot = await DatasetSnapshotService(session_factory=factory).freeze_ohlcv_snapshot(
            trade_date=effective_end,
            date_from=effective_start,
            date_to=effective_end,
            market="CN",
        )
        logger.info(
            "ohlcv dataset snapshot frozen: dataset_id=%s fingerprint=%s",
            snapshot.to_dict()["dataset_id"],
            snapshot.content_fingerprint,
        )

    success = sum(1 for c in results.values() if c > 0)
    logger.info(
        "ohlcv_crawl task 完成: %d/%d 标的成功",
        success,
        len(results),
    )
