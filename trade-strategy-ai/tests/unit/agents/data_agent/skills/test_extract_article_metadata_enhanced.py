"""extract_article_metadata 增强测试：质量门禁、证据字段、可聚合字段"""

from datetime import datetime
from unittest.mock import MagicMock

from src.agents.data_agent.skills.extract_article_metadata import (
    _quality_gate,
    _validate_rules,
    _validate_preconditions,
    _clamp,
    _safe_float,
)


class TestQualityGate:
    """质量门禁测试：sentiment_score / confidence_score 阈值检查"""

    def test_passes_with_good_scores(self):
        """置信度高、情绪分合理则通过。"""
        raw = {
            "sentiment_score": 0.5,
            "confidence_score": 0.8,
            "strategy_rules": [{"claim_key": "entry.trigger", "rule_type": "entry"}],
        }
        result = _quality_gate(raw)
        assert result["passed"] is True
        assert result["rejected_fields"] == []

    def test_rejects_low_confidence(self):
        """置信度过低则拒绝。"""
        raw = {
            "sentiment_score": 0.5,
            "confidence_score": 0.2,
            "strategy_rules": [],
        }
        result = _quality_gate(raw)
        assert result["passed"] is False
        assert "confidence_score" in result["rejected_fields"]

    def test_rejects_undefined_scores(self):
        """缺失分数视为低质量。"""
        raw = {
            "sentiment_score": None,
            "confidence_score": None,
            "strategy_rules": [],
        }
        result = _quality_gate(raw)
        assert result["passed"] is False

    def test_rejects_out_of_range_sentiment(self):
        """情绪分超出 -1~1 范围则拒绝。"""
        raw = {
            "sentiment_score": 2.0,
            "confidence_score": 0.8,
            "strategy_rules": [],
        }
        result = _quality_gate(raw)
        assert result["passed"] is False

    def test_empty_rules_still_passes_if_confidence_is_high(self):
        """规则为空但置信度高，仍通过（允许纯分析文章）。"""
        raw = {
            "sentiment_score": 0.0,
            "confidence_score": 0.9,
            "strategy_rules": [],
        }
        result = _quality_gate(raw)
        assert result["passed"] is True

    def test_returns_quality_score(self):
        """返回综合质量分。"""
        raw = {
            "sentiment_score": 0.5,
            "confidence_score": 0.6,
            "strategy_rules": [],
        }
        result = _quality_gate(raw)
        assert "quality_score" in result
        assert 0.0 <= result["quality_score"] <= 1.0


class TestValidateRulesEvidenceFields:
    """证据字段测试：source_url / published_at 被正确填充到规则中"""

    def test_enriches_source_url(self):
        """source_url 被填充到规则中。"""
        raw_rules = [
            {"claim_key": "entry.trigger", "rule_type": "entry", "action": {"type": "enter"}},
        ]
        source_url = "https://example.com/article"
        published_at = datetime(2026, 4, 23, 10, 0, 0)
        validated = _validate_rules(raw_rules, source_url=source_url, published_at=published_at)
        assert validated[0]["source_url"] == source_url

    def test_enriches_published_at(self):
        """published_at 被填充到规则中。"""
        raw_rules = [
            {"claim_key": "exit.take_profit", "rule_type": "exit", "action": {"type": "exit"}},
        ]
        published_at = datetime(2026, 4, 23, 10, 0, 0)
        validated = _validate_rules(raw_rules, source_url=None, published_at=published_at)
        # model_dump(mode="json") 将 datetime 转为 ISO 字符串
        assert validated[0]["published_at"] == published_at.isoformat()

    def test_preserves_quoted_text(self):
        """引用原文被保留。"""
        raw_rules = [
            {
                "claim_key": "entry.trigger",
                "rule_type": "entry",
                "action": {"type": "enter"},
                "quoted_text": "放量突破前高，短期看多",
            },
        ]
        validated = _validate_rules(raw_rules, source_url=None, published_at=None)
        assert validated[0]["quoted_text"] == "放量突破前高，短期看多"


class TestAggregatableFields:
    """可聚合字段测试：sentiment_score 和 confidence_score 被正确 clamp"""

    def test_sentiment_clamped_to_valid_range(self):
        """sentiment_score 钳制到 -1~1。"""
        assert _clamp(_safe_float(2.0), -1.0, 1.0) == 1.0
        assert _clamp(_safe_float(-2.0), -1.0, 1.0) == -1.0
        assert _clamp(_safe_float(0.5), -1.0, 1.0) == 0.5
        assert _clamp(_safe_float(None), -1.0, 1.0) is None

    def test_confidence_clamped_to_valid_range(self):
        """confidence_score 钳制到 0~1。"""
        assert _clamp(_safe_float(1.5), 0.0, 1.0) == 1.0
        assert _clamp(_safe_float(-0.5), 0.0, 1.0) == 0.0
        assert _clamp(_safe_float(0.7), 0.0, 1.0) == 0.7
        assert _clamp(_safe_float(None), 0.0, 1.0) is None


class TestValidatePreconditions:
    """Precondition 证据字段测试"""

    def test_enriches_preconditions_with_evidence(self):
        """preconditions 被正确填充证据字段。"""
        raw_preconds = [
            {"claim_key": "filter.market_regime", "condition": {"op": "market_bull"}},
        ]
        source_url = "https://example.com/article"
        published_at = datetime(2026, 4, 23)
        validated = _validate_preconditions(raw_preconds, source_url=source_url, published_at=published_at)
        assert validated[0]["source_url"] == source_url
        # model_dump(mode="json") 将 datetime 转为 ISO 字符串
        assert validated[0]["published_at"] == published_at.isoformat()
        assert validated[0]["schema_version"] == "v0"