"""rule_pool Repository：RulePool ORM 与 RulePoolItem schema 的转换与持久化"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.rule_pool.models import RulePool

logger = get_logger(__name__)
from src.rule_pool.schemas import (
    MappingStatus,
    ReviewStatus,
    RuleBacktestResult,
    RulePoolItem,
    RuleSourceType,
)


class RulePoolRepository:
    """规则池仓储，负责 RulePool ORM 模型与 RulePoolItem schema 之间的转换与持久化"""

    def __init__(self, session: AsyncSession):
        """初始化仓储

        Args:
            session: SQLAlchemy AsyncSession 实例
        """
        self.session = session

    async def create_rule(self, rule: RulePoolItem) -> RulePool:
        """创建规则

        Args:
            rule: 规则池条目 schema

        Returns:
            创建的 RulePool ORM 对象
        """
        orm_obj = self._to_orm_model(rule)
        self.session.add(orm_obj)
        await self.session.flush()
        logger.debug("规则入库: rule_id=%s, type=%s, confidence=%.3f", rule.rule_id, rule.rule_type, rule.initial_confidence)
        return orm_obj

    async def get_rule_by_id(self, rule_id: str) -> RulePool | None:
        """根据 rule_id 查询规则

        Args:
            rule_id: 规则 ID

        Returns:
            RulePool ORM 对象或 None（不存在时）
        """
        stmt = select(RulePool).where(RulePool.rule_id == rule_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_rules_by_status(
        self,
        review_status: ReviewStatus | None = None,
        mapping_status: MappingStatus | None = None,
        limit: int = 100,
    ) -> list[RulePool]:
        """根据状态查询规则

        Args:
            review_status: 审核状态过滤条件（可选）
            mapping_status: 映射状态过滤条件（可选）
            limit: 返回结果数量上限

        Returns:
            符合条件的 RulePool ORM 对象列表
        """
        conditions = []
        if review_status is not None:
            conditions.append(RulePool.review_status == review_status.value)
        if mapping_status is not None:
            conditions.append(RulePool.mapping_status == mapping_status.value)

        stmt = select(RulePool)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(RulePool.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_mapping(
        self,
        rule_id: str,
        mapped_condition: dict[str, Any],
        mapped_by: str,
    ) -> bool:
        """更新规则映射状态

        Args:
            rule_id: 规则 ID
            mapped_condition: 映射后的条件字典
            mapped_by: 映射操作人

        Returns:
            是否更新成功
        """
        orm_obj = await self.get_rule_by_id(rule_id)
        if orm_obj is None:
            return False

        orm_obj.mapping_status = MappingStatus.MAPPED.value
        orm_obj.mapped_by = mapped_by
        orm_obj.mapped_at = datetime.now(UTC)

        # 更新 extraction_layer 中的 mapped_condition
        extraction_layer = orm_obj.extraction_layer or {}
        extraction_layer["mapped_condition"] = mapped_condition
        orm_obj.extraction_layer = extraction_layer

        await self.session.flush()
        return True

    async def update_review(
        self,
        rule_id: str,
        review_status: ReviewStatus,
        reviewed_by: str,
        force: bool = False,
    ) -> bool:
        """更新规则审核状态

        Args:
            rule_id: 规则 ID
            review_status: 新的审核状态
            reviewed_by: 审核操作人（auto_review 或 cli_user）
            force: 是否强制覆盖已有审核结果

        Returns:
            是否更新成功
        """
        orm_obj = await self.get_rule_by_id(rule_id)
        if orm_obj is None:
            return False

        # 非强制模式下，已审核通过的规则不允许重复审核
        if not force and orm_obj.review_status != ReviewStatus.PENDING.value:
            return False

        orm_obj.review_status = review_status.value
        orm_obj.reviewed_by = reviewed_by
        orm_obj.reviewed_at = datetime.now(UTC)

        await self.session.flush()
        return True

    async def auto_review_rule(
        self,
        rule_id: str,
        initial_confidence: float,
        has_mapped_condition: bool = False,
        auto_approve_threshold: float = 0.7,
        auto_reject_threshold: float = 0.2,
    ) -> str:
        """自动审核单条规则

        根据初始置信度和映射状态自动决定审核结果：
        - initial_confidence >= auto_approve_threshold 且 has_mapped_condition → APPROVED
        - initial_confidence < auto_reject_threshold → REJECTED
        - 其余 → PENDING

        Args:
            rule_id: 规则 ID
            initial_confidence: 初始置信度
            has_mapped_condition: 是否有 mapped_condition
            auto_approve_threshold: 自动通过阈值（默认 0.7）
            auto_reject_threshold: 自动拒绝阈值（默认 0.2）

        Returns:
            审核结果状态值 (approved/pending/rejected)
        """
        orm_obj = await self.get_rule_by_id(rule_id)
        if orm_obj is None:
            return "not_found"

        # 只对 pending 状态的规则执行自动审核
        if orm_obj.review_status != ReviewStatus.PENDING.value:
            return orm_obj.review_status

        if initial_confidence >= auto_approve_threshold and has_mapped_condition:
            decision = ReviewStatus.APPROVED
            reason = f"auto: confidence({initial_confidence:.3f}) >= {auto_approve_threshold} + has_mapped"
        elif initial_confidence < auto_reject_threshold:
            decision = ReviewStatus.REJECTED
            reason = f"auto: confidence({initial_confidence:.3f}) < {auto_reject_threshold}"
        else:
            # 保持 pending，等待人工审核
            return ReviewStatus.PENDING.value

        orm_obj.review_status = decision.value
        orm_obj.reviewed_by = "auto_review"
        orm_obj.reviewed_at = datetime.now(UTC)

        # 将审核原因写入 extraction_layer 的扩展字段
        extraction = dict(orm_obj.extraction_layer or {})
        extraction["_auto_review"] = {
            "decision": decision.value,
            "reason": reason,
            "reviewed_at": orm_obj.reviewed_at.isoformat(),
        }
        orm_obj.extraction_layer = extraction

        await self.session.flush()
        logger.info(
            "自动审核: rule_id=%s, confidence=%.3f, has_mapped=%s → %s (%s)",
            rule_id, initial_confidence, has_mapped_condition, decision.value, reason,
        )
        return decision.value

    async def update_backtest_result(
        self,
        rule_id: str,
        backtest_result: RuleBacktestResult,
        initial_confidence: float,
    ) -> bool:
        """更新规则回测结果

        Args:
            rule_id: 规则 ID
            backtest_result: 回测结果 schema
            initial_confidence: 初始置信度

        Returns:
            是否更新成功
        """
        orm_obj = await self.get_rule_by_id(rule_id)
        if orm_obj is None:
            return False

        orm_obj.backtest_result = backtest_result.model_dump(mode="json")
        orm_obj.backtest_triggered_at = datetime.now(UTC)
        orm_obj.backtest_hits = backtest_result.hit_trades
        orm_obj.backtest_misses = backtest_result.miss_trades
        orm_obj.backtest_samples = backtest_result.sample_count

        # 回测后更新 validated_confidence：调用多指标综合置信度调整
        from src.rule_backtest.confidence import compute_confidence_adjustment

        orm_obj.validated_confidence = compute_confidence_adjustment(
            initial_confidence=initial_confidence,
            backtest_result=backtest_result,
        )

        await self.session.flush()
        logger.info(
            "回测结果更新: rule_id=%s, hit_rate=%.3f, samples=%d, validated_confidence=%.3f",
            rule_id,
            backtest_result.hit_rate,
            backtest_result.sample_count,
            orm_obj.validated_confidence,
        )
        return True

    async def get_high_confidence_rules(self, threshold: float = 0.7) -> list[RulePool]:
        """获取高置信度规则

        使用 validated_confidence 字段进行过滤，未进行回测的规则不纳入。

        Args:
            threshold: 置信度阈值，默认为 0.7

        Returns:
            置信度高于阈值且已审核通过的 RulePool 对象列表
        """
        stmt = select(RulePool).where(
            and_(
                RulePool.validated_confidence.is_not(None),
                RulePool.validated_confidence >= threshold,
                RulePool.review_status == ReviewStatus.APPROVED.value,
            )
        ).order_by(RulePool.validated_confidence.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ---- ORM <-> Schema 转换 ----

    @staticmethod
    def _to_orm_model(item: RulePoolItem) -> RulePool:
        """将 RulePoolItem schema 转换为 RulePool ORM 对象

        Args:
            item: 规则池条目 schema

        Returns:
            RulePool ORM 对象
        """
        return RulePool(
            rule_id=item.rule_id,
            source_article_ids=item.source_article_ids,
            source_type=item.source_type.value,
            rule_type=item.rule_type,
            instrument_focus=item.instrument_focus,
            extraction_layer=item.extraction_layer.model_dump() if hasattr(item.extraction_layer, 'model_dump') else item.extraction_layer,
            mapping_status=item.mapping_status.value,
            mapped_by=item.mapped_by,
            mapped_at=item.mapped_at,
            initial_confidence=item.initial_confidence,
            validated_confidence=item.validated_confidence,
            review_status=item.review_status.value,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
            backtest_triggered_at=item.backtest_triggered_at,
            backtest_result=item.backtest_result.model_dump(mode="json") if item.backtest_result else None,
            backtest_hits=item.backtest_hits,
            backtest_misses=item.backtest_misses,
            backtest_samples=item.backtest_samples,
            used_in_prediction=item.used_in_prediction,
            prediction_count=item.prediction_count,
            last_used_at=item.last_used_at,
        )

    @staticmethod
    def _from_orm_model(orm_obj: RulePool) -> RulePoolItem:
        """将 RulePool ORM 对象转换为 RulePoolItem schema

        Args:
            orm_obj: RulePool ORM 对象

        Returns:
            RulePoolItem schema
        """
        # 处理 extraction_layer
        extraction_layer_data = orm_obj.extraction_layer or {}

        # 处理 backtest_result
        backtest_result = None
        if orm_obj.backtest_result:
            backtest_result = RuleBacktestResult(**orm_obj.backtest_result)

        return RulePoolItem(
            id=orm_obj.id,
            rule_id=orm_obj.rule_id,
            source_article_ids=orm_obj.source_article_ids or [],
            source_type=RuleSourceType(orm_obj.source_type),
            rule_type=orm_obj.rule_type,
            instrument_focus=orm_obj.instrument_focus,
            extraction_layer=extraction_layer_data,
            mapping_status=MappingStatus(orm_obj.mapping_status),
            mapped_by=orm_obj.mapped_by,
            mapped_at=orm_obj.mapped_at,
            initial_confidence=orm_obj.initial_confidence,
            validated_confidence=orm_obj.validated_confidence,
            review_status=ReviewStatus(orm_obj.review_status),
            reviewed_by=orm_obj.reviewed_by,
            reviewed_at=orm_obj.reviewed_at,
            backtest_triggered_at=orm_obj.backtest_triggered_at,
            backtest_result=backtest_result,
            backtest_hits=orm_obj.backtest_hits,
            backtest_misses=orm_obj.backtest_misses,
            backtest_samples=orm_obj.backtest_samples,
            used_in_prediction=orm_obj.used_in_prediction,
            prediction_count=orm_obj.prediction_count,
            last_used_at=orm_obj.last_used_at,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
