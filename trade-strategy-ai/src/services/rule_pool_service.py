from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select

from src.services.base import BaseService, ServiceResult
from src.rule_pool.repository import RulePoolRepository
from src.rule_pool.models import RulePool
from src.rule_pool.schemas import MappingStatus, ReviewStatus, RuleSourceType


def _to_plain(value: Any) -> Any:
    """把 ORM / dataclass / 容器值转成可序列化结构。"""
    if hasattr(value, "model_dump"):
        return _to_plain(value.model_dump())
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dict__"):
        return _to_plain(vars(value))
    return value


class RulePoolService(BaseService):
    """规则池查询与审核共享服务。"""

    service_name = "rule_pool"

    def __init__(
        self,
        *,
        repo_factory: Callable[[Any], RulePoolRepository] = RulePoolRepository,
        session_scope_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._repo_factory = repo_factory
        self._session_scope_factory = session_scope_factory

    def _ensure_session_factory(self) -> Callable[[], Any]:
        """确保具备 session_scope 工厂。"""
        if self._session_scope_factory is not None:
            return self._session_scope_factory
        from src.db.session import session_scope

        self._session_scope_factory = session_scope
        return session_scope

    @staticmethod
    def _merge_with_defaults(values: list[str], defaults: list[str]) -> list[str]:
        """将数据库结果与默认枚举值合并，保持去重与稳定顺序。"""
        merged: list[str] = []
        for item in [*defaults, *values]:
            if item and item not in merged:
                merged.append(item)
        return merged

    @staticmethod
    def _unique_preserve_order(values: list[str]) -> list[str]:
        """对数据库查询结果做稳定去重，避免下拉选项重复。"""
        unique: list[str] = []
        for item in values:
            if item and item not in unique:
                unique.append(item)
        return unique

    async def list_filter_options(self) -> ServiceResult:
        """列出规则池筛选下拉选项。"""
        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            review_statuses = list(
                (await session.execute(select(RulePool.review_status).distinct().order_by(RulePool.review_status.asc()))).scalars().all()
            )
            mapping_statuses = list(
                (await session.execute(select(RulePool.mapping_status).distinct().order_by(RulePool.mapping_status.asc()))).scalars().all()
            )
            source_types = list(
                (await session.execute(select(RulePool.source_type).distinct().order_by(RulePool.source_type.asc()))).scalars().all()
            )
            rule_types = list(
                (await session.execute(select(RulePool.rule_type).distinct().order_by(RulePool.rule_type.asc()))).scalars().all()
            )
            instrument_focuses = list(
                (await session.execute(select(RulePool.instrument_focus).distinct().order_by(RulePool.instrument_focus.asc()))).scalars().all()
            )

        payload = {
            "review_statuses": self._merge_with_defaults(review_statuses, [item.value for item in ReviewStatus]),
            "mapping_statuses": self._merge_with_defaults(mapping_statuses, [item.value for item in MappingStatus]),
            "source_types": self._merge_with_defaults(source_types, [item.value for item in RuleSourceType]),
            "rule_types": self._unique_preserve_order([str(item) for item in rule_types if item]),
            "instrument_focuses": self._unique_preserve_order([str(item) for item in instrument_focuses if item]),
        }
        return ServiceResult(status="ok", message="rule pool filter options loaded", payload=payload)

    async def list_rules(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        rule_type: str | None = None,
        skip_no_mapped: bool = False,
    ) -> ServiceResult:
        """列出规则池中的规则。"""
        review_filter = None
        if status:
            review_filter = ReviewStatus(status.lower())

        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory(session)
            rules = await repo.get_rules_by_status(review_status=review_filter, limit=limit)

        if rule_type:
            rules = [rule for rule in rules if getattr(rule, "rule_type", None) == rule_type]
        if skip_no_mapped:
            rules = [rule for rule in rules if (getattr(rule, "extraction_layer", None) or {}).get("mapped_condition")]

        payload_rules = []
        for rule in rules:
            confidence = getattr(rule, "validated_confidence", None) or getattr(rule, "initial_confidence", None)
            payload_rules.append(
                {
                    "rule_id": getattr(rule, "rule_id", ""),
                    "rule_type": getattr(rule, "rule_type", ""),
                    "source_type": getattr(rule, "source_type", ""),
                    "confidence": confidence,
                    "review_status": getattr(rule, "review_status", ""),
                    "mapping_status": getattr(rule, "mapping_status", ""),
                    "mapped": bool((getattr(rule, "extraction_layer", None) or {}).get("mapped_condition")),
                }
            )

        return ServiceResult(status="ok", message="rule pool listed", payload={"rules": payload_rules, "count": len(payload_rules)})

    async def show_rule(self, rule_id: str) -> ServiceResult:
        """查看单条规则完整详情。"""
        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory(session)
            rule = await repo.get_rule_by_id(rule_id)
        if rule is None:
            return ServiceResult(status="partial", message="rule not found", payload={"rule_id": rule_id})

        return ServiceResult(status="ok", message="rule shown", payload={"rule": _to_plain(rule)})

    async def review_rule(
        self,
        rule_id: str,
        *,
        decision: str,
        force: bool = False,
        reviewed_by: str = "cli_user",
    ) -> ServiceResult:
        return ServiceResult(
            status="error",
            message="legacy rule-pool review is compatibility-only",
            payload={
                "rule_id": rule_id,
                "status": "compatibility_only",
                "message": "历史规则池入口不能再写入正式规则生命周期，请使用 Stage 4 正式生命周期入口。",
                "decision": decision,
                "force": force,
                "reviewed_by": reviewed_by,
            },
        )

    async def review_batch(
        self,
        *,
        decision: str,
        status: str = "pending",
        limit: int = 50,
        force: bool = False,
        reviewed_by: str = "cli_user",
    ) -> ServiceResult:
        return ServiceResult(
            status="error",
            message="legacy rule-pool batch review is compatibility-only",
            payload={
                "decision": decision,
                "status": "compatibility_only",
                "message": "历史规则池入口不能再写入正式规则生命周期，请使用 Stage 4 正式生命周期入口。",
                "filter_status": status,
                "updated_count": 0,
                "reviewed_by": reviewed_by,
                "limit": limit,
                "force": force,
            },
        )
