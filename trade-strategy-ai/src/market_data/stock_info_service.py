"""
股票基本信息服务 - 从 AKShare 获取股票列表并存储到数据库

功能：
1. 获取 A 股股票列表（沪深北交所）
2. 存储到 stock_info 表
3. 提供名称→代码映射查询
"""
from __future__ import annotations

import akshare as ak
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from src.db.session import session_scope
from src.models.stock_info import StockInfo


# 股票类型映射（AKShare 返回的 security_type）
_SECURITY_TYPE_MAP: dict[str, str] = {
    "A股": "stock",
    "沪市主板": "stock",
    "深市主板": "stock",
    "创业板": "stock",
    "科创板": "stock",
    "北交所": "stock",
    "ETF": "etf",
    "LOF": "fund",
    "封闭式基金": "fund",
    "债券": "bond",
}


def _infer_market(code: str) -> str:
    """根据股票代码推断交易所"""
    if code.startswith(("000", "001", "002", "003", "300", "400")):
        return "SZ"
    elif code.startswith(("600", "601", "603", "605", "688", "900")):
        return "SH"
    elif code.startswith(("430", "830", "870")):
        return "BJ"
    return "SZ"  # 默认深圳


def _build_symbol(code: str, market: str) -> str:
    """构建标准代码格式，如 000001.SZ"""
    return f"{code}.{market}"


async def fetch_and_store_stock_list() -> dict[str, Any]:
    """从 AKShare 获取 A 股股票列表并存储到数据库

    使用 stock_info_a_code_name 获取所有 A 股数据（沪深北交所）
    返回格式：{'code': '000001', 'name': '平安银行'}

    Returns:
        统计信息，包含新增、更新、跳过的数量
    """
    stats = {"total": 0, "inserted": 0, "updated": 0, "skipped": 0}

    try:
        df = ak.stock_info_a_code_name()
    except Exception as exc:
        raise RuntimeError(f"AKShare 获取股票列表失败: {exc}") from exc

    if df is None or df.empty:
        raise RuntimeError("AKShare 返回空数据")

    records: list[dict[str, Any]] = []
    now = datetime.now(UTC)

    for _, row in df.iterrows():
        try:
            code = str(row.get("code") or row.get("证券代码") or "")
            name = str(row.get("name") or row.get("证券简称") or "")

            if not code or not name or len(code) != 6:
                continue

            code = code.strip()
            name = name.strip()
            market = _infer_market(code)
            symbol = _build_symbol(code, market)

            records.append({
                "symbol": symbol,
                "code": code,
                "market": market,
                "name": name,
                "security_type": "stock",
                "updated_at": now,
            })
        except Exception:
            continue

    if not records:
        raise RuntimeError("未能从 AKShare 数据中提取任何有效股票记录")

    stats["total"] = len(records)

    # 使用 upsert 写入数据库（PostgreSQL INSERT ON CONFLICT DO UPDATE）
    async with session_scope() as session:
        for record in records:
            # 先查询是否存在
            stmt = select(StockInfo).where(StockInfo.symbol == record["symbol"])
            existing = await session.scalar(stmt)

            if existing:
                # 更新已有记录
                existing.name = record["name"]
                existing.market = record["market"]
                existing.security_type = record["security_type"]
                existing.updated_at = record["updated_at"]
                stats["updated"] += 1
            else:
                # 插入新记录
                session.add(StockInfo(**record))
                stats["inserted"] += 1

    return stats


async def get_stock_info_by_name(name: str) -> StockInfo | None:
    """根据股票名称查询股票信息"""
    async with session_scope() as session:
        stmt = select(StockInfo).where(StockInfo.name == name.strip())
        result = await session.scalar(stmt)
        return result


async def get_stock_info_by_symbol(symbol: str) -> StockInfo | None:
    """根据标准代码查询股票信息"""
    async with session_scope() as session:
        stmt = select(StockInfo).where(StockInfo.symbol == symbol.upper())
        result = await session.scalar(stmt)
        return result


async def get_stock_infos_by_names(names: list[str]) -> dict[str, StockInfo]:
    """根据股票名称列表批量查询

    Returns:
        dict[名称, StockInfo]，只返回找到的
    """
    if not names:
        return {}

    async with session_scope() as session:
        stmt = select(StockInfo).where(StockInfo.name.in_([n.strip() for n in names]))
        result = await session.scalars(stmt)
        return {info.name: info for info in result.all()}


async def get_all_stock_names() -> set[str]:
    """获取所有股票名称（用于快速查找）"""
    async with session_scope() as session:
        stmt = select(StockInfo.name)
        result = await session.scalars(stmt)
        return set(result.all())


async def get_stock_name_to_symbol_map() -> dict[str, str]:
    """获取所有股票名称→标准代码的映射字典

    用于批量快速映射
    """
    async with session_scope() as session:
        stmt = select(StockInfo.name, StockInfo.symbol)
        result = await session.execute(stmt)
        return {name: symbol for name, symbol in result.all()}


async def is_stock_list_fresh(max_age_days: int = 7) -> bool:
    """检查股票列表是否足够新

    Args:
        max_age_days: 最大允许的天数

    Returns:
        True if there's at least one record updated within max_age_days
    """
    from datetime import timedelta

    async with session_scope() as session:
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        stmt = select(StockInfo).where(StockInfo.updated_at >= cutoff).limit(1)
        result = await session.scalar(stmt)
        return result is not None
