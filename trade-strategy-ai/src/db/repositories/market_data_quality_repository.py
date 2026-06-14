from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_data_quality_report import MarketDataQualityReport
from src.common.stage2_writer_routing import require_canonical_write


class MarketDataQualityRepository:
    """市场数据质量报告仓储。"""

    async def upsert_report(self, session: AsyncSession, report: MarketDataQualityReport) -> MarketDataQualityReport:
        """按 snapshot_id 写入或更新质量报告。"""
        require_canonical_write("market_snapshot", "MarketDataQualityRepository.upsert_report")
        existing = await session.scalar(
            select(MarketDataQualityReport).where(MarketDataQualityReport.snapshot_id == report.snapshot_id)
        )
        if existing is None:
            session.add(report)
            await session.flush()
            return report

        for field in (
            "overall_status",
            "warning_count",
            "error_count",
            "section_summary_json",
            "report_json",
            "storage_ref",
        ):
            setattr(existing, field, getattr(report, field))
        await session.flush()
        return existing

    async def get_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> MarketDataQualityReport | None:
        """按 snapshot_id 查询质量报告。"""
        return await session.scalar(select(MarketDataQualityReport).where(MarketDataQualityReport.snapshot_id == snapshot_id))
