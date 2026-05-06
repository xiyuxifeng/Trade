"""rule_pool prediction / attribution service tests."""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.rule_pool.models import RulePool


@pytest.mark.asyncio
async def test_predict_high_confidence_rules_marks_usage():
    """预测服务会返回高置信度规则并更新使用统计。"""
    from src.rule_pool.prediction import RulePoolPredictionService

    session = AsyncMock()
    session.flush = AsyncMock()

    rule = MagicMock(spec=RulePool)
    rule.rule_id = "rule_001"
    rule.rule_type = "breakout"
    rule.initial_confidence = 0.82
    rule.validated_confidence = 0.91
    rule.source_article_ids = ["article_001"]
    rule.used_in_prediction = False
    rule.prediction_count = 0
    rule.last_used_at = None

    repo = MagicMock()
    repo.get_high_confidence_rules = AsyncMock(return_value=[rule])

    service = RulePoolPredictionService(session=session, repository=repo)
    predictions = await service.predict_high_confidence_rules(threshold=0.8)

    assert len(predictions) == 1
    assert predictions[0].rule_id == "rule_001"
    assert rule.used_in_prediction is True
    assert rule.prediction_count == 1
    assert rule.last_used_at is not None
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_prediction_outcome_updates_counters_and_confidence():
    """归因服务会更新命中统计并重算置信度。"""
    from src.rule_pool.attribution import RulePoolAttributionService

    session = AsyncMock()
    session.flush = AsyncMock()

    rule = MagicMock(spec=RulePool)
    rule.rule_id = "rule_001"
    rule.initial_confidence = 0.75
    rule.validated_confidence = 0.70
    rule.backtest_hits = 2
    rule.backtest_misses = 1
    rule.backtest_samples = 3
    rule.last_used_at = None

    repo = MagicMock()
    repo.get_rule_by_id = AsyncMock(return_value=rule)

    service = RulePoolAttributionService(session=session, repository=repo)
    result = await service.record_prediction_outcome(rule_id="rule_001", hit=True, occurred_at=datetime(2026, 5, 6))

    assert result is True
    assert rule.backtest_hits == 3
    assert rule.backtest_misses == 1
    assert rule.backtest_samples == 4
    assert rule.validated_confidence is not None
    assert rule.last_used_at is not None
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_prediction_outcome_missing_rule_returns_false():
    """归因服务在规则不存在时应返回 False。"""
    from src.rule_pool.attribution import RulePoolAttributionService

    session = AsyncMock()
    session.flush = AsyncMock()
    repo = MagicMock()
    repo.get_rule_by_id = AsyncMock(return_value=None)

    service = RulePoolAttributionService(session=session, repository=repo)
    result = await service.record_prediction_outcome(rule_id="missing", hit=False, occurred_at=datetime(2026, 5, 6))

    assert result is False
    session.flush.assert_not_awaited()
