"""
stock_info_update Pipeline 步骤

功能：
- 检查 stock_info 表是否需要更新
- 如需要，从 AKShare 获取最新股票列表并存储到数据库
- 为后续的元数据提取步骤提供股票名称→代码映射

在 pipeline 中的位置：store → stock_info_update → process
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.utils import ensure_dir, write_json
from src.market_data.stock_info_service import (
    fetch_and_store_stock_list,
    is_stock_list_fresh,
    seed_common_market_indices,
)


@dataclass(slots=True)
class StockInfoUpdateResult:
    """stock_info_update 步骤的执行结果"""

    updated: bool  # 是否执行了更新
    total: int = 0  # 总股票数
    inserted: int = 0  # 新增数量
    updated_count: int = 0  # 更新数量
    skipped: int = 0  # 跳过数量
    stats_path: Path | None = None


async def run_stock_info_update(
    *,
    base_dir: Path,
    force: bool = False,
    max_age_days: int = 7,
) -> StockInfoUpdateResult:
    """执行股票信息更新步骤

    Args:
        base_dir: 项目根目录
        force: 是否强制更新（忽略是否过期）
        max_age_days: 股票列表最大有效期（天），超过则重新获取

    Returns:
        StockInfoUpdateResult: 更新结果统计
    """
    out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "stock_info")
    stats_path = out_dir / "stock_info_stats.json"

    # 先确保常用指数元数据存在，避免 stock 列表未刷新时漏掉 benchmark 选项
    index_stats = await seed_common_market_indices()

    # 检查是否需要更新
    if not force:
        fresh = await is_stock_list_fresh(max_age_days=max_age_days)
        if fresh:
            # 列表已存在且未过期，跳过更新
            stats = {
                "updated": False,
                "message": f"股票列表未过期（max_age={max_age_days}天），跳过更新",
                "checked_at": datetime.now(UTC).isoformat(),
                "index_total": index_stats["total"],
                "index_inserted": index_stats["inserted"],
                "index_updated": index_stats["updated"],
            }
            write_json(stats_path, stats)
            return StockInfoUpdateResult(updated=False, stats_path=stats_path)

    # 执行更新
    try:
        result = await fetch_and_store_stock_list()
        stats: dict[str, Any] = {
            "updated": True,
            "total": result["total"],
            "inserted": result["inserted"],
            "updated_count": result["updated"],
            "skipped": result["skipped"],
            "index_total": index_stats["total"],
            "index_inserted": index_stats["inserted"],
            "index_updated": index_stats["updated"],
            "checked_at": datetime.now(UTC).isoformat(),
        }
        write_json(stats_path, stats)
        return StockInfoUpdateResult(
            updated=True,
            total=result["total"],
            inserted=result["inserted"],
            updated_count=result["updated"],
            skipped=result["skipped"],
            stats_path=stats_path,
        )
    except Exception as exc:
        stats = {
            "updated": False,
            "error": str(exc),
            "checked_at": datetime.now(UTC).isoformat(),
        }
        write_json(stats_path, stats)
        raise RuntimeError(f"股票信息更新失败: {exc}") from exc
