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

from sqlalchemy import func, select

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

# 常用 benchmark 指数，供 OHLCV 抓取和回测下拉框复用。
COMMON_MARKET_INDICES: list[dict[str, str]] = [
    {"symbol": "000300.SH", "code": "000300", "market": "SH", "name": "沪深300"},
    {"symbol": "000905.SH", "code": "000905", "market": "SH", "name": "中证500"},
    {"symbol": "000852.SH", "code": "000852", "market": "SH", "name": "中证1000"},
    {"symbol": "000001.SH", "code": "000001", "market": "SH", "name": "上证指数"},
    {"symbol": "399001.SZ", "code": "399001", "market": "SZ", "name": "深证成指"},
    {"symbol": "399006.SZ", "code": "399006", "market": "SZ", "name": "创业板指"},
    {"symbol": "000016.SH", "code": "000016", "market": "SH", "name": "上证50"},
    {"symbol": "000688.SH", "code": "000688", "market": "SH", "name": "科创50"},
    {"symbol": "000906.SH", "code": "000906", "market": "SH", "name": "中证800"},
    {"symbol": "932000.SH", "code": "932000", "market": "SH", "name": "中证2000"},
]


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

    upsert_stats = await _upsert_stock_info_records(records, now=now)
    stats["inserted"] = upsert_stats["inserted"]
    stats["updated"] = upsert_stats["updated"]
    stats["skipped"] = upsert_stats["skipped"]

    return stats


async def seed_common_market_indices() -> dict[str, Any]:
    """将常用 benchmark 指数预置到 stock_info 表。

    这个步骤与普通股票列表独立，避免 stock 列表“过新”时遗漏指数元数据。
    """
    now = datetime.now(UTC)
    records = [
        {
            "symbol": item["symbol"],
            "code": item["code"],
            "market": item["market"],
            "name": item["name"],
            "security_type": "index",
            "updated_at": now,
        }
        for item in COMMON_MARKET_INDICES
    ]
    upsert_stats = await _upsert_stock_info_records(records, now=now)
    return {
        "total": len(records),
        "inserted": upsert_stats["inserted"],
        "updated": upsert_stats["updated"],
        "skipped": upsert_stats["skipped"],
    }


async def _upsert_stock_info_records(
    records: list[dict[str, Any]],
    *,
    now: datetime,
) -> dict[str, int]:
    """批量写入 stock_info，并按 symbol upsert。

    Args:
        records: 待写入记录
        now: 当前时间戳，用于统一更新 updated_at
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    if not records:
        return stats

    async with session_scope() as session:
        for record in records:
            symbol = record.get("symbol")
            if not symbol:
                stats["skipped"] += 1
                continue

            stmt = select(StockInfo).where(StockInfo.symbol == symbol)
            existing = await session.scalar(stmt)

            if existing:
                existing.name = record["name"]
                existing.market = record["market"]
                existing.security_type = record["security_type"]
                existing.updated_at = record.get("updated_at", now)
                stats["updated"] += 1
            else:
                session.add(StockInfo(**record))
                stats["inserted"] += 1

        await session.commit()

    return stats


async def get_stock_info_status(*, max_age_days: int = 7) -> dict[str, Any]:
    """返回 stock_info 的当前状态摘要。"""
    benchmark_symbols = [item["symbol"] for item in COMMON_MARKET_INDICES]
    async with session_scope() as session:
        total = int(await session.scalar(select(func.count()).select_from(StockInfo)) or 0)
        stock_count = int(
            await session.scalar(select(func.count()).select_from(StockInfo).where(StockInfo.security_type == "stock"))
            or 0
        )
        index_count = int(
            await session.scalar(select(func.count()).select_from(StockInfo).where(StockInfo.security_type == "index"))
            or 0
        )
        latest_updated_at = await session.scalar(select(func.max(StockInfo.updated_at)))
        benchmark_rows = await session.scalars(select(StockInfo.symbol).where(StockInfo.symbol.in_(benchmark_symbols)))
        existing_benchmark_symbols = {symbol for symbol in benchmark_rows.all()}

    fresh = await is_stock_list_fresh(max_age_days=max_age_days, security_types=["stock", "index"])
    missing_benchmark_symbols = [symbol for symbol in benchmark_symbols if symbol not in existing_benchmark_symbols]
    benchmark_count = len(existing_benchmark_symbols)
    needs_refresh = not fresh or total == 0 or bool(missing_benchmark_symbols)
    message = "stock_info 已就绪，可直接用于 OHLCV 抓取"
    if total == 0:
        message = "stock_info 为空，请先刷新股票基础信息"
    elif needs_refresh:
        message = "stock_info 已过期或缺少 benchmark，请先刷新股票基础信息"

    return {
        "total": total,
        "stock_count": stock_count,
        "index_count": index_count,
        "benchmark_count": benchmark_count,
        "expected_benchmark_count": len(benchmark_symbols),
        "missing_benchmark_symbols": missing_benchmark_symbols,
        "latest_updated_at": latest_updated_at.isoformat() if latest_updated_at is not None else None,
        "is_fresh": fresh and total > 0 and not missing_benchmark_symbols,
        "needs_refresh": needs_refresh,
        "message": message,
        "max_age_days": max_age_days,
    }


async def refresh_stock_info(*, max_age_days: int = 7) -> dict[str, Any]:
    """强制刷新 stock_info，并返回刷新后的状态摘要。"""
    index_stats = await seed_common_market_indices()
    stock_stats = await fetch_and_store_stock_list()
    status = await get_stock_info_status(max_age_days=max_age_days)
    return {
        "stock_stats": stock_stats,
        "index_stats": index_stats,
        "status": status,
    }


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


async def list_index_stock_infos() -> list[StockInfo]:
    """列出已预置的 benchmark 指数信息。"""
    async with session_scope() as session:
        stmt = select(StockInfo).where(StockInfo.security_type == "index").order_by(StockInfo.code.asc())
        result = await session.scalars(stmt)
        return list(result.all())


async def is_stock_list_fresh(max_age_days: int = 7, *, security_types: list[str] | None = None) -> bool:
    """检查股票列表是否足够新

    Args:
        max_age_days: 最大允许的天数
        security_types: 仅检查这些证券类型，默认只检查普通股票

    Returns:
        True if there's at least one record updated within max_age_days
    """
    from datetime import timedelta

    target_types = security_types or ["stock"]
    async with session_scope() as session:
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        stmt = select(StockInfo).where(
            StockInfo.updated_at >= cutoff,
            StockInfo.security_type.in_(target_types),
        ).limit(1)
        result = await session.scalar(stmt)
        return result is not None
