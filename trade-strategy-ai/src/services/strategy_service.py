from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Awaitable, Callable

from sqlalchemy import func, select

from src.common.config import load_app_config
from src.db.session import session_scope
from src.models.trader_strategy_version import TraderStrategyVersion
from src.pipeline.tasks.strategy_version_tasks import handle_build_trader_strategy_version
from src.services.base import BaseService, ServiceResult
from src.services.runtime_config import resolve_runtime_config


def _project_base_dir(config_path: Path) -> Path:
    """根据配置文件推导项目根目录。"""
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


def _serialize_strategy_version(row: TraderStrategyVersion) -> dict[str, Any]:
    """将 ORM 行转换为前端友好的结构。"""
    strategy_payload = getattr(row, "strategy_payload", None) or {}
    version_name = getattr(row, "version_name", None) or getattr(row, "version_id", None)
    return {
        "version_id": version_name,
        "trader_id": row.trader_id,
        "strategy_date": str(row.strategy_date),
        "status": row.status,
        "version_type": getattr(row, "version_type", "manual"),
        "released_at": row.released_at.isoformat() if row.released_at else None,
        "rules_snapshot": strategy_payload.get("rules_snapshot", getattr(row, "rules_snapshot", [])),
        "regime_selection": strategy_payload.get("regime_selection", getattr(row, "regime_selection", {})),
        "recommendations": strategy_payload.get("recommendations", getattr(row, "recommendations", [])),
        "notes": row.notes,
        "source_article_ids": row.source_article_ids or [],
        "evidence_refs": row.evidence_refs or [],
        "parent_version_id": getattr(row, "parent_version_id", None),
    }


class StrategyService(BaseService):
    """策略版本构建、列表、详情和下载的共享服务。"""

    service_name = "strategy"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] = session_scope,
        build_handler: Callable[..., Awaitable[None]] = handle_build_trader_strategy_version,
    ) -> None:
        self._session_scope_factory = session_scope_factory
        self._build_handler = build_handler

    async def build_strategy_version(
        self,
        *,
        config_path: str | Path | None = None,
        profile_id: str | None = None,
        trader_id: str,
        strategy_date: str,
        force: bool = False,
        regime_selection: dict[str, Any] | None = None,
        snapshot_id: str | None = None,
        market_regime_version: str | None = None,
        source_feature_version: str | None = None,
        applicability_profile_version: str | None = None,
        selected_by: str | None = None,
    ) -> ServiceResult:
        """构建指定交易员的策略版本。"""
        runtime_config = resolve_runtime_config({"profile_id": profile_id, "config_path": config_path})
        config_file = Path(runtime_config.config_path or "config/app.yaml").expanduser().resolve()
        loaded = load_app_config(config_file)
        base_dir = _project_base_dir(loaded.config_path)
        regime_selection_payload = regime_selection or {}
        if not regime_selection_payload and any(
            value is not None
            for value in (snapshot_id, market_regime_version, source_feature_version, applicability_profile_version, selected_by)
        ):
            regime_selection_payload = {
                "snapshot_id": snapshot_id,
                "market_regime_version": market_regime_version,
                "source_feature_version": source_feature_version,
                "applicability_profile_version": applicability_profile_version,
                "selected_by": selected_by,
            }
        details = {
            "trader_id": trader_id,
            "strategy_date": strategy_date,
            "force": force,
            "regime_selection": regime_selection_payload or None,
            "selection_context": {
                "snapshot_id": snapshot_id,
                "market_regime_version": market_regime_version,
                "source_feature_version": source_feature_version,
                "applicability_profile_version": applicability_profile_version,
                "selected_by": selected_by,
            }
            if any(
                value is not None
                for value in (snapshot_id, market_regime_version, source_feature_version, applicability_profile_version, selected_by)
            )
            else None,
        }
        await self._build_handler(details, config=loaded.config)
        return ServiceResult(
            status="ok",
            message="strategy version build completed",
            payload={
                "config_path": str(config_file),
                "base_dir": str(base_dir),
                "profile_id": runtime_config.profile_id,
                "trader_id": trader_id,
                "strategy_date": strategy_date,
                "force": force,
                "regime_selection": regime_selection_payload or None,
                "status": "draft",
            },
        )

    async def list_strategy_versions(
        self,
        *,
        trader_id: str | None = None,
        status: str = "all",
        date_from: str | None = None,
        date_to: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> ServiceResult:
        """列出策略版本。"""
        conditions = []
        if trader_id:
            conditions.append(TraderStrategyVersion.trader_id == trader_id)
        if status != "all":
            conditions.append(TraderStrategyVersion.status == status)
        if date_from:
            conditions.append(TraderStrategyVersion.strategy_date >= date.fromisoformat(date_from))
        if date_to:
            conditions.append(TraderStrategyVersion.strategy_date <= date.fromisoformat(date_to))

        async with self._session_scope_factory() as session:
            count_stmt = select(func.count()).select_from(TraderStrategyVersion)
            for condition in conditions:
                count_stmt = count_stmt.where(condition)
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(TraderStrategyVersion)
                .where(*conditions)
                .order_by(TraderStrategyVersion.strategy_date.desc(), TraderStrategyVersion.version_name)
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        items = [_serialize_strategy_version(row) for row in rows]
        return ServiceResult(
            status="ok",
            message="strategy versions listed",
            payload={
                "count": len(items),
                "total": total,
                "skip": skip,
                "limit": limit,
                "items": items,
            },
        )

    async def get_strategy_version(self, version_id: str) -> ServiceResult:
        """获取单个策略版本详情。"""
        async with self._session_scope_factory() as session:
            stmt = select(TraderStrategyVersion).where(
                TraderStrategyVersion.version_name == version_id,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

        if row is None:
            return ServiceResult(status="error", message="strategy version not found", payload={"item": None})

        return ServiceResult(
            status="ok",
            message="strategy version loaded",
            payload={"item": _serialize_strategy_version(row)},
        )

    async def download_strategy_version(self, version_id: str) -> ServiceResult:
        """获取可下载的策略版本 JSON。"""
        detail = await self.get_strategy_version(version_id)
        if detail.status != "ok":
            return detail
        return ServiceResult(
            status="ok",
            message="strategy version download prepared",
            payload={
                "file_name": f"strategy_version_{version_id}.json",
                "item": detail.payload["item"],
                "content": json.dumps(detail.payload["item"], ensure_ascii=False, indent=2),
            },
        )
