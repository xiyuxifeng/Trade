"""规则池盘后归因服务。

负责记录预测命中/失效结果，并回写规则的统计与验证置信度。
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.rule_pool.repository import RulePoolRepository
from src.rule_pool.schemas import RuleBacktestResult
from src.common.stage2_writer_routing import require_legacy_compatibility_write

logger = get_logger(__name__)


class RulePoolAttributionService:
    """规则池盘后归因服务。"""

    def __init__(self, session: AsyncSession, repository: RulePoolRepository | None = None):
        self.session = session
        self.repository = repository or RulePoolRepository(session)

    async def record_prediction_outcome(
        self,
        *,
        rule_id: str,
        hit: bool,
        occurred_at: datetime | None = None,
    ) -> bool:
        """记录一次预测归因结果。"""
        require_legacy_compatibility_write("rule", "RulePoolAttributionService.record_prediction_outcome")
        rule = await self.repository.get_rule_by_id(rule_id)
        if rule is None:
            return False

        now = occurred_at or datetime.now(UTC)
        rule.backtest_hits = int(rule.backtest_hits or 0) + (1 if hit else 0)
        rule.backtest_misses = int(rule.backtest_misses or 0) + (0 if hit else 1)
        rule.backtest_samples = int(rule.backtest_samples or 0) + 1
        rule.backtest_triggered_at = now
        rule.last_used_at = now
        rule.used_in_prediction = True
        rule.prediction_count = int(rule.prediction_count or 0) + 1

        synthetic_result = RuleBacktestResult(
            run_id=f"prediction-{rule_id}",
            run_at=now,
            start_date=now.date(),
            end_date=now.date(),
            total_trades=1,
            hit_trades=1 if hit else 0,
            miss_trades=0 if hit else 1,
            hit_rate=1.0 if hit else 0.0,
            avg_return=0.0,
            avg_win_return=0.0 if hit else None,
            avg_loss_return=0.0 if not hit else None,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            sample_count=1,
        )
        from src.rule_backtest.confidence import compute_confidence_adjustment

        rule.validated_confidence = compute_confidence_adjustment(
            initial_confidence=float(rule.initial_confidence or 0.0),
            backtest_result=synthetic_result,
        )
        rule.backtest_result = {
            "source": "prediction_attribution",
            "hit": hit,
            "occurred_at": now.isoformat(),
        }

        await self.session.flush()
        logger.info(
            "预测归因记录: rule_id=%s, hit=%s, validated_confidence=%.3f",
            rule_id, hit, rule.validated_confidence,
        )
        return True
