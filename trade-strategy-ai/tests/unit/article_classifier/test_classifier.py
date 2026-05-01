"""ArticleClassifier 单元测试"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.article_classifier.classifier import ArticleClassifier, classify_article
from src.article_classifier.schemas import ClassificationResult
from src.llm.client import LLMClient


class TestClassificationResult:
    """ClassificationResult 数据模型测试。"""

    def test_basic_result(self):
        """基本结果测试。"""
        result = ClassificationResult(
            article_type="rule",
            confidence=0.8,
            type_scores={"rule": 0.8, "record": 0.1, "concept": 0.05, "mixed": 0.03, "noise": 0.02},
            reason="描述了一般性交易规则",
        )

        assert result.article_type == "rule"
        assert result.confidence == 0.8
        assert result.type_scores["rule"] == 0.8
        assert result.reason == "描述了一般性交易规则"

    def test_default_values(self):
        """默认值测试。"""
        result = ClassificationResult(article_type="noise")

        assert result.confidence == 0.0
        assert result.type_scores == {}
        assert result.reason == ""

    def test_confidence_range(self):
        """置信度范围测试。"""
        # 有效范围
        result = ClassificationResult(article_type="rule", confidence=0.0)
        assert result.confidence == 0.0

        result = ClassificationResult(article_type="rule", confidence=1.0)
        assert result.confidence == 1.0


class TestArticleClassifier:
    """ArticleClassifier 测试。"""

    @pytest.fixture
    def mock_llm_client(self):
        """创建模拟的 LLM 客户端。"""
        client = MagicMock(spec=LLMClient)
        client.complete_json = AsyncMock()
        return client

    @pytest.fixture
    def classifier(self, mock_llm_client):
        """创建分类器实例。"""
        return ArticleClassifier(mock_llm_client)

    @pytest.mark.asyncio
    async def test_classify_rule_article(self, classifier, mock_llm_client):
        """分类 rule 类型文章。"""
        mock_llm_client.complete_json.return_value = {
            "article_type": "rule",
            "confidence": 0.85,
            "type_scores": {"rule": 0.85, "record": 0.1, "concept": 0.03, "mixed": 0.01, "noise": 0.01},
            "reason": "描述了一般性交易规则",
        }

        result = await classifier.classify(
            title="交易策略分享",
            content_text="当股价突破20日均线时，应该考虑买入。这是趋势跟踪的基本策略。",
        )

        assert result.article_type == "rule"
        assert result.confidence == 0.85
        assert result.type_scores["rule"] == 0.85

        # 验证 LLM 调用参数
        mock_llm_client.complete_json.assert_called_once()
        call_kwargs = mock_llm_client.complete_json.call_args.kwargs
        assert "system_prompt" in call_kwargs
        assert "user_prompt" in call_kwargs
        assert "交易策略分享" in call_kwargs["user_prompt"]

    @pytest.mark.asyncio
    async def test_classify_record_article(self, classifier, mock_llm_client):
        """分类 record 类型文章。"""
        mock_llm_client.complete_json.return_value = {
            "article_type": "record",
            "confidence": 0.9,
            "type_scores": {"rule": 0.05, "record": 0.9, "concept": 0.03, "mixed": 0.01, "noise": 0.01},
            "reason": "包含具体历史交易记录",
        }

        result = await classifier.classify(
            title="今日操作记录",
            content_text="今天在 10:30 以 25.5 元买入 1000 股，随后在 14:00 以 26.2 元卖出。",
        )

        assert result.article_type == "record"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_classify_concept_article(self, classifier, mock_llm_client):
        """分类 concept 类型文章。"""
        mock_llm_client.complete_json.return_value = {
            "article_type": "concept",
            "confidence": 0.78,
            "type_scores": {"rule": 0.1, "record": 0.05, "concept": 0.78, "mixed": 0.05, "noise": 0.02},
            "reason": "纯理论框架分享",
        }

        result = await classifier.classify(
            title="投资心态探讨",
            content_text="投资成功的关键在于保持耐心和纪律。不要被短期波动影响情绪。",
        )

        assert result.article_type == "concept"
        assert result.confidence == 0.78

    @pytest.mark.asyncio
    async def test_classify_noise_article(self, classifier, mock_llm_client):
        """分类 noise 类型文章。"""
        mock_llm_client.complete_json.return_value = {
            "article_type": "noise",
            "confidence": 0.65,
            "type_scores": {"rule": 0.05, "record": 0.05, "concept": 0.1, "mixed": 0.1, "noise": 0.7},
            "reason": "闲聊内容无交易逻辑",
        }

        result = await classifier.classify(
            title="今日天气",
            content_text="今天天气真好，阳光明媚，适合出去走走。",
        )

        assert result.article_type == "noise"
        assert result.confidence == 0.65

    @pytest.mark.asyncio
    async def test_classify_mixed_article(self, classifier, mock_llm_client):
        """分类 mixed 类型文章。"""
        mock_llm_client.complete_json.return_value = {
            "article_type": "mixed",
            "confidence": 0.72,
            "type_scores": {"rule": 0.4, "record": 0.35, "concept": 0.1, "mixed": 0.72, "noise": 0.05},
            "reason": "既讲方法论又举具体案例",
        }

        result = await classifier.classify(
            title="我的交易方法",
            content_text="我一般会在股价突破均线时买入，比如上周五就以 15.2 元买入了某股票，策略是趋势跟踪。",
        )

        assert result.article_type == "mixed"
        assert result.confidence == 0.72

    @pytest.mark.asyncio
    async def test_content_truncation(self, classifier, mock_llm_client):
        """测试内容截断功能。"""
        mock_llm_client.complete_json.return_value = {
            "article_type": "rule",
            "confidence": 0.8,
            "type_scores": {},
            "reason": "测试",
        }

        # 创建一个超长内容
        long_content = "a" * 15000

        await classifier.classify(title="测试", content_text=long_content)

        # 验证调用参数
        call_kwargs = mock_llm_client.complete_json.call_args.kwargs
        user_prompt = call_kwargs["user_prompt"]
        # 内容应该被截断到 10000 字符
        assert len(user_prompt) <= 10000 + len("文章标题：测试\n\n文章内容：\n")

    @pytest.mark.asyncio
    async def test_handle_missing_fields(self, classifier, mock_llm_client):
        """测试处理 LLM 返回缺失字段的情况。"""
        # LLM 只返回部分字段
        mock_llm_client.complete_json.return_value = {
            "article_type": "rule",
            # 缺少 confidence, type_scores, reason
        }

        result = await classifier.classify(
            title="测试",
            content_text="测试内容",
        )

        # 使用默认值
        assert result.article_type == "rule"
        assert result.confidence == 0.0
        assert result.type_scores == {}
        assert result.reason == ""


class TestClassifyArticleFunction:
    """classify_article 便捷函数测试。"""

    @pytest.mark.asyncio
    async def test_classify_article_function(self):
        """测试便捷函数。"""
        mock_client = MagicMock(spec=LLMClient)
        mock_client.complete_json = AsyncMock(return_value={
            "article_type": "rule",
            "confidence": 0.85,
            "type_scores": {"rule": 0.85},
            "reason": "测试",
        })

        result = await classify_article(
            llm_client=mock_client,
            title="测试文章",
            content_text="这是一个测试内容",
        )

        assert result.article_type == "rule"
        assert result.confidence == 0.85
        mock_client.complete_json.assert_called_once()