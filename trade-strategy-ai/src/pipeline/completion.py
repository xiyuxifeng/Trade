from __future__ import annotations

from datetime import date

from src.common.config import AppConfig
from src.common.logger import get_logger
from src.pipeline.tasks.ohlcv_crawl_task import handle_ohlcv_crawl
from src.pipeline.tasks.snapshot_tasks import (
    handle_hot_topics_snapshot,
    handle_strong_symbols_snapshot,
    handle_topic_constituents_snapshot,
)

_logger = get_logger(__name__)


async def run_incremental_data_completion(*, config: AppConfig, as_of_date: date, force: bool = False) -> None:
    """
    执行增量数据补全任务，确保盘后分析所需的数据是完整的。

    Args:
        config: 应用配置。
        as_of_date: 补全数据的目标日期。
        force: 是否强制执行，即使数据已存在。
    """
    _logger.info("开始执行盘后增量数据补全...")

    # 1. 补全 OHLCV 数据
    try:
        _logger.info("正在补全 OHLCV 行情数据...")
        await handle_ohlcv_crawl({"as_of_date": as_of_date.isoformat(), "force": force}, config=config)
        _logger.info("OHLCV 行情数据补全完成。")
    except Exception:
        _logger.error("补全 OHLCV 数据时出错", exc_info=True)
        # 根据策略决定是否继续，这里选择记录错误并继续

    # 2. 补全市场快照数据
    snapshot_tasks = {
        "热门板块快照": handle_hot_topics_snapshot,
        "板块成分股快照": handle_topic_constituents_snapshot,
        "强势股快照": handle_strong_symbols_snapshot,
    }

    for name, handler in snapshot_tasks.items():
        try:
            _logger.info(f"正在生成 {name}...")
            await handler({"as_of_date": as_of_date.isoformat(), "force": force}, config=config)
            _logger.info(f"{name} 生成完成。")
        except Exception:
            _logger.error(f"生成 {name} 时出错", exc_info=True)

    _logger.info("盘后增量数据补全流程结束。")
