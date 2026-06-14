"""告警历史 DB 持久化（S7-007）。

AlertHistory ORM 模型 + AlertHistoryRepository。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Sequence

from sqlalchemy import DateTime, String, Text, Index, select, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class AlertHistory(Base):
    """告警历史 ORM 模型。"""
    __tablename__ = "alert_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    alert_id: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    aggregated_count: Mapped[int] = mapped_column(default=1, nullable=False)
    aggregation_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aggregation_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alert_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_alert_history_status", "status"),
        Index("idx_alert_history_level", "level"),
        Index("idx_alert_history_created_at", "created_at"),
        Index("idx_alert_history_aggregation_key", "aggregation_key"),
    )


class AlertHistoryRepository:
    """告警历史 Repository。"""

    async def insert(
        self,
        session,
        alert_id: str,
        level: str,
        title: str,
        message: str | None,
        channel: str,
        tags: list[str] | None = None,
        alert_metadata: dict | None = None,
        aggregation_key: str | None = None,
        aggregated_count: int = 1,
        aggregation_window_start: datetime | None = None,
    ) -> AlertHistory:
        """插入新告警历史记录。"""
        record = AlertHistory(
            alert_id=alert_id,
            level=level,
            title=title,
            message=message,
            channel=channel,
            tags=tags or [],
            alert_metadata=alert_metadata or {},
            aggregation_key=aggregation_key,
            aggregated_count=aggregated_count,
            aggregation_window_start=aggregation_window_start,
            status="pending",
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record

    async def update_status(
        self,
        session,
        record_id: uuid.UUID,
        status: str,
        sent_at: datetime | None = None,
        acknowledged_at: datetime | None = None,
        acknowledged_by: str | None = None,
        resolved_at: datetime | None = None,
        resolved_by: str | None = None,
    ) -> AlertHistory | None:
        """更新告警状态。"""
        result = await session.execute(
            select(AlertHistory).where(AlertHistory.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        record.status = status
        if sent_at is not None:
            record.sent_at = sent_at
        if acknowledged_at is not None:
            record.acknowledged_at = acknowledged_at
        if acknowledged_by is not None:
            record.acknowledged_by = acknowledged_by
        if resolved_at is not None:
            record.resolved_at = resolved_at
        if resolved_by is not None:
            record.resolved_by = resolved_by
        await session.flush()
        await session.refresh(record)
        return record

    async def count_history(
        self,
        session,
        status: str | None = None,
        level: str | None = None,
        tag: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        """统计告警历史总数（支持过滤）。"""
        from sqlalchemy import text, func

        conditions = []
        if status:
            conditions.append(AlertHistory.status == status)
        if level:
            conditions.append(AlertHistory.level == level)
        if tag:
            conditions.append(
                text(f"'{tag}' = ANY(SELECT jsonb_array_elements_text(tags))")
            )
        if date_from:
            conditions.append(AlertHistory.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            conditions.append(AlertHistory.created_at <= datetime.fromisoformat(date_to))

        stmt = select(func.count()).select_from(AlertHistory).where(*conditions)
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def list_history(
        self,
        session,
        status: str | None = None,
        level: str | None = None,
        tag: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[AlertHistory]:
        """查询告警历史（支持过滤和分页）。"""
        from sqlalchemy import text

        conditions = []
        if status:
            conditions.append(AlertHistory.status == status)
        if level:
            conditions.append(AlertHistory.level == level)
        if tag:
            conditions.append(
                text(f"'{tag}' = ANY(SELECT jsonb_array_elements_text(tags))")
            )
        if date_from:
            conditions.append(AlertHistory.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            conditions.append(AlertHistory.created_at <= datetime.fromisoformat(date_to))

        stmt = (
            select(AlertHistory)
            .where(*conditions)
            .order_by(AlertHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(
        self, session, record_id: uuid.UUID
    ) -> AlertHistory | None:
        """按 ID 查询告警记录。"""
        result = await session.execute(
            select(AlertHistory).where(AlertHistory.id == record_id)
        )
        return result.scalar_one_or_none()
