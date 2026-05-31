"""告警历史 API 路由（S7-007）。

提供告警历史查询、确认、解决、测试接口。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.common.logger import get_logger
from src.services.config_profile_service import ConfigProfileService

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = get_logger(__name__)


class AlertHistoryItem(BaseModel):
    """告警历史条目响应模型。"""
    id: str
    alert_id: str
    level: str
    title: str
    message: str | None
    channel: str
    tags: list[str]
    status: str
    aggregated_count: int
    aggregation_key: str | None
    sent_at: str | None
    acknowledged_at: str | None
    resolved_at: str | None
    alert_metadata: dict | None
    created_at: str


class PaginatedAlertHistory(BaseModel):
    """告警历史分页响应。"""
    count: int
    total: int
    items: list[AlertHistoryItem]


class AlertAcknowledgeRequest(BaseModel):
    """确认告警请求。"""
    acknowledged_by: str | None = None


class AlertResolveRequest(BaseModel):
    """解决告警请求。"""
    resolved_by: str | None = None


class AlertingStatusResponse(BaseModel):
    """告警配置状态响应。"""
    enabled: bool
    channel: str
    min_level: str
    console_output: bool
    aggregation_window_minutes: int
    aggregation_max_count: int
    webhook_configured: bool
    channel_configured: bool


def _row_to_item(row) -> AlertHistoryItem:
    """将 AlertHistory ORM 行转为 API 响应模型。"""
    return AlertHistoryItem(
        id=str(row.id),
        alert_id=row.alert_id,
        level=row.level,
        title=row.title,
        message=row.message,
        channel=row.channel,
        tags=row.tags or [],
        status=row.status,
        aggregated_count=row.aggregated_count or 1,
        aggregation_key=row.aggregation_key,
        sent_at=row.sent_at.isoformat() if row.sent_at else None,
        acknowledged_at=row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        resolved_at=row.resolved_at.isoformat() if row.resolved_at else None,
        alert_metadata=row.alert_metadata or {},
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


async def _build_alerting_status() -> AlertingStatusResponse:
    """从应用配置构建告警状态。"""
    from src.alerting.config import load_alerting_config
    from src.common.config import load_app_config
    from src.common.paths import resolve_project_path

    profile_id = ConfigProfileService().resolve_runtime_profile_id()
    try:
        runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
        cfg = load_alerting_config(runtime.config.alerting)
    except Exception:
        loaded = load_app_config(resolve_project_path("config/app.yaml"))
        cfg = load_alerting_config(loaded.config.alerting)

    webhook_configured = False
    if cfg.channel == "dingtalk":
        webhook_configured = bool(cfg.dingtalk.webhook_url.strip())
    elif cfg.channel == "feishu":
        webhook_configured = bool(cfg.feishu.webhook_url.strip())
    elif cfg.channel == "wecom":
        webhook_configured = bool(cfg.wecom.webhook_url.strip())

    return AlertingStatusResponse(
        enabled=bool(cfg.enabled),
        channel=cfg.channel,
        min_level=cfg.min_level,
        console_output=bool(cfg.console_output),
        aggregation_window_minutes=int(cfg.aggregation.window_minutes),
        aggregation_max_count=int(cfg.aggregation.max_count),
        webhook_configured=webhook_configured,
        channel_configured=webhook_configured or bool(cfg.console_output),
    )


@router.get("/history", response_model=PaginatedAlertHistory)
async def list_alert_history(
    _key: str = Depends(verify_api_key),
    status: str | None = Query(default=None, description="状态过滤"),
    level: str | None = Query(default=None, description="级别过滤"),
    tag: str | None = Query(default=None, description="标签过滤"),
    date_from: str | None = Query(default=None, description="开始日期 YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="结束日期 YYYY-MM-DD"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedAlertHistory:
    """查询告警历史（支持分页和过滤）。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        total = await repo.count_history(
            session=session,
            status=status,
            level=level,
            tag=tag,
            date_from=date_from,
            date_to=date_to,
        )
        rows = await repo.list_history(
            session=session,
            status=status,
            level=level,
            tag=tag,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )

        items = [_row_to_item(row) for row in rows]
        return PaginatedAlertHistory(count=len(items), total=total, items=items)


@router.get("/status", response_model=AlertingStatusResponse)
async def get_alerting_status(_key: str = Depends(verify_api_key)) -> AlertingStatusResponse:
    """查询当前告警配置状态。"""
    return await _build_alerting_status()


@router.get("/history/{record_id}", response_model=AlertHistoryItem)
async def get_alert_history(record_id: str, _key: str = Depends(verify_api_key)) -> AlertHistoryItem:
    """获取单条告警详情。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        row = await repo.get_by_id(session, uuid.UUID(record_id))

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="告警记录未找到",
            )

        return _row_to_item(row)


@router.post("/{record_id}/acknowledge")
async def acknowledge_alert(
    record_id: str,
    body: AlertAcknowledgeRequest | None = None,
    _key: str = Depends(verify_api_key),
) -> dict:
    """确认告警。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        now = datetime.now(timezone.utc)
        row = await repo.update_status(
            session,
            uuid.UUID(record_id),
            status="acknowledged",
            acknowledged_at=now,
            acknowledged_by=body.acknowledged_by if body else None,
        )

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="告警记录未找到",
            )

        return {"status": "ok", "id": record_id, "new_status": "acknowledged"}


@router.post("/{record_id}/resolve")
async def resolve_alert(
    record_id: str,
    body: AlertResolveRequest | None = None,
    _key: str = Depends(verify_api_key),
) -> dict:
    """解决告警。"""
    from src.db.session import session_scope
    from src.alerting.db import AlertHistoryRepository

    async with session_scope() as session:
        repo = AlertHistoryRepository()
        now = datetime.now(timezone.utc)
        row = await repo.update_status(
            session,
            uuid.UUID(record_id),
            status="resolved",
            resolved_at=now,
            resolved_by=body.resolved_by if body else None,
        )

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="告警记录未找到",
            )

        return {"status": "ok", "id": record_id, "new_status": "resolved"}


@router.post("/test")
async def send_test_alert(_key: str = Depends(verify_api_key)) -> dict:
    """发送测试告警（验证 Webhook 配置）。"""
    from src.alerting.manager import AlertManager

    alerting_status = await _build_alerting_status()
    if not alerting_status.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="告警未启用，请先在配置中设置 alerting.enabled=true",
        )
    if not alerting_status.webhook_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="告警通道未配置 Webhook，无法发送测试告警",
        )

    try:
        profile_id = ConfigProfileService().resolve_runtime_profile_id()
        runtime = await ConfigProfileService().load_profile_runtime_config(profile_id)
        manager = AlertManager(alerting_config=runtime.config.alerting)
        manager.send_test_alert(
            title="[测试] 告警系统连通性验证",
            message="如果你看到这条消息，说明告警 Webhook 配置正确。",
        )
        return {"status": "ok", "message": "测试告警已发送"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"测试告警发送失败: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
