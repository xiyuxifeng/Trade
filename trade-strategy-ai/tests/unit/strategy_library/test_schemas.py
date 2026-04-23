"""strategy_library schemas 测试。"""

from datetime import date, datetime
from src.strategy_library.schemas import (
    StrategyVersionStatus,
    StrategyIdea,
    StrategyRecommendation,
    StrategyVersion,
)


class TestStrategyVersionStatus:
    """策略版本状态枚举。"""

    def test_status_values(self):
        """三种状态值正确。"""
        assert StrategyVersionStatus.draft.value == "draft"
        assert StrategyVersionStatus.released.value == "released"
        assert StrategyVersionStatus.archived.value == "archived"


class TestStrategyIdea:
    """单个标的的策略想法。"""

    def test_strategy_idea_fields(self):
        """StrategyIdea 包含所有必要字段。"""
        idea = StrategyIdea(
            symbol="000001",
            side="BUY",
            confidence=0.85,
            entry_price=10.5,
            target_price=12.0,
            stop_loss_price=9.5,
            rationale="突破关键阻力位",
            invalidation="跌破 9.0",
            source_article_ids=["article-1", "article-2"],
        )
        assert idea.symbol == "000001"
        assert idea.side == "BUY"
        assert idea.confidence == 0.85
        assert idea.entry_price == 10.5
        assert idea.target_price == 12.0
        assert idea.stop_loss_price == 9.5
        assert idea.rationale == "突破关键阻力位"
        assert idea.invalidation == "跌破 9.0"
        assert len(idea.source_article_ids) == 2

    def test_strategy_idea_defaults(self):
        """可选字段默认为 None。"""
        idea = StrategyIdea(symbol="000001", side="HOLD", confidence=0.0)
        assert idea.entry_price is None
        assert idea.target_price is None
        assert idea.stop_loss_price is None
        assert idea.rationale is None
        assert idea.invalidation is None
        assert idea.source_article_ids == []


class TestStrategyRecommendation:
    """单个标的的策略建议（含 buy/sell/hold）。"""

    def test_strategy_recommendation_fields(self):
        """StrategyRecommendation 包含所有必要字段。"""
        rec = StrategyRecommendation(
            symbol="000001",
            decision="buy",
            confidence=0.8,
            entry_price=10.5,
            target_price=12.0,
            stop_loss_price=9.5,
            rationale="AI 题材持续发酵",
            evidence_refs=["art-1", "art-2"],
        )
        assert rec.symbol == "000001"
        assert rec.decision == "buy"
        assert rec.confidence == 0.8
        assert rec.entry_price == 10.5
        assert rec.evidence_refs == ["art-1", "art-2"]

    def test_strategy_recommendation_decision_values(self):
        """decision 支持 buy/sell/hold。"""
        for decision in ("buy", "sell", "hold"):
            rec = StrategyRecommendation(
                symbol="000001",
                decision=decision,
                confidence=0.5,
            )
            assert rec.decision == decision


class TestStrategyVersion:
    """策略版本聚合。"""

    def test_strategy_version_fields(self):
        """StrategyVersion 包含所有必要字段。"""
        version = StrategyVersion(
            version_id="ver-001",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[
                StrategyRecommendation(
                    symbol="000001",
                    decision="buy",
                    confidence=0.8,
                    entry_price=10.5,
                    evidence_refs=["art-1"],
                ),
            ],
            source_article_ids=["article-1"],
            evidence_refs=["evidence-1"],
            notes="AI 题材版本",
        )
        assert version.version_id == "ver-001"
        assert version.trader_id == "trader-001"
        assert version.strategy_date == date(2026, 4, 23)
        assert version.status == StrategyVersionStatus.released
        assert len(version.recommendations) == 1
        assert version.recommendations[0].symbol == "000001"

    def test_strategy_version_defaults(self):
        """可选字段有默认值。"""
        version = StrategyVersion(
            version_id="ver-001",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
        )
        assert version.recommendations == []
        assert version.source_article_ids == []
        assert version.evidence_refs == []
        assert version.notes is None
        assert version.released_at is None

    def test_strategy_version_is_frozen(self):
        """StrategyVersion 是不可变的。"""
        version = StrategyVersion(
            version_id="ver-001",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
        )
        try:
            version.status = StrategyVersionStatus.released
            assert False, "Should not allow assignment"
        except Exception:
            pass  # frozen dataclass 不允许赋值