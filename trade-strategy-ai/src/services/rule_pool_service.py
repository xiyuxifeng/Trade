from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Callable

from src.services.base import BaseService, ServiceResult
from src.rule_pool.repository import RulePoolRepository
from src.rule_pool.schemas import MappingStatus, ReviewStatus


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
        """审核单条规则。"""
        mapping = {
            "approve": ReviewStatus.APPROVED,
            "reject": ReviewStatus.REJECTED,
            "pending": ReviewStatus.PENDING,
        }
        if decision not in mapping:
            raise ValueError("invalid decision")

        session_scope = self._ensure_session_factory()
        async with session_scope() as session:
            repo = self._repo_factory(session)
            success = await repo.update_review(rule_id, mapping[decision], reviewed_by=reviewed_by, force=force)
        return ServiceResult(
            status="ok" if success else "partial",
            message="rule reviewed" if success else "rule review failed",
            payload={
                "rule_id": rule_id,
                "review_status": mapping[decision].value,
                "force": force,
                "success": success,
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
        """批量审核规则。"""
        decision_map = {
            "approve": ReviewStatus.APPROVED,
            "reject": ReviewStatus.REJECTED,
            "pending": ReviewStatus.PENDING,
        }
        status_map = {
            "pending": ReviewStatus.PENDING,
            "approved": ReviewStatus.APPROVED,
            "rejected": ReviewStatus.REJECTED,
        }
        if decision not in decision_map:
            raise ValueError("invalid decision")
        if status not in status_map:
            raise ValueError("invalid status")

        target_status = decision_map[decision]
        filter_status = status_map[status]

        session_scope = self._ensure_session_factory()
        updated_count = 0
        async with session_scope() as session:
            repo = self._repo_factory(session)
            rules = await repo.get_rules_by_status(review_status=filter_status, limit=limit)
            for rule in rules:
                if force or getattr(rule, "review_status", None) == filter_status.value:
                    ok = await repo.update_review(rule.rule_id, target_status, reviewed_by=reviewed_by, force=force)
                    if ok:
                        updated_count += 1

        return ServiceResult(
            status="ok",
            message="rule batch reviewed",
            payload={
                "decision": decision,
                "filter_status": status,
                "updated_count": updated_count,
                "target_status": target_status.value,
                "reviewed_by": reviewed_by,
            },
        )
