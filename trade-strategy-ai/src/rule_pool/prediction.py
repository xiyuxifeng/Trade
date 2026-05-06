"""规则池盘前预测服务。

负责从高置信度规则中挑选可用于预测的条目，并更新使用统计。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.rule_pool.repository import RulePoolRepository


@dataclass(slots=True)
class RulePredictionSnapshot:
    """规则盘前预测快照。"""

    rule_id: str
    rule_type: str
    confidence: float
    source_article_ids: list[str]
    predicted_at: datetime


class RulePoolPredictionService:
    """规则池盘前预测服务。"""

    def __init__(self, session: AsyncSession, repository: RulePoolRepository | None = None):
        self.session = session
        self.repository = repository or RulePoolRepository(session)

    async def predict_high_confidence_rules(self, threshold: float = 0.8, limit: int = 20) -> list[RulePredictionSnapshot]:
        """收集高置信度规则并标记为已参与预测。"""
        rules = await self.repository.get_high_confidence_rules(threshold=threshold)
        predicted_at = datetime.now(UTC)
        snapshots: list[RulePredictionSnapshot] = []

        for rule in rules[: max(1, int(limit))]:
            rule.used_in_prediction = True
            rule.prediction_count = int(rule.prediction_count or 0) + 1
            rule.last_used_at = predicted_at
            snapshots.append(
                RulePredictionSnapshot(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    confidence=float(rule.validated_confidence or rule.initial_confidence),
                    source_article_ids=list(rule.source_article_ids or []),
                    predicted_at=predicted_at,
                )
            )

        await self.session.flush()
        return snapshots
