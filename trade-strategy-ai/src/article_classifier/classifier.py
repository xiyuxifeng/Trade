"""文章分类器核心实现

使用 LLM 对文章进行分类，支持四分类：rule/record/concept/noise
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.article_classifier.prompts import (
    CLASSIFICATION_PROMPT,
    MAX_CONTENT_LENGTH,
)
from src.article_classifier.schemas import ClassificationResult
from src.common.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from src.llm.client import LLMClient


class ArticleClassifier:
    """文章分类器

    使用 LLM 对文章进行分类，输出 ClassificationResult

    Attributes:
        llm_client: LLM 客户端实例
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """初始化文章分类器

        Args:
            llm_client: LLM 客户端实例
        """
        self._llm_client = llm_client

    async def classify(self, title: str, content_text: str) -> ClassificationResult:
        """对文章进行分类

        Args:
            title: 文章标题
            content_text: 文章正文内容

        Returns:
            ClassificationResult: 分类结果，包含类型、置信度和各类型得分

        Raises:
            LLMError: 当 LLM 调用失败或返回格式错误时
        """
        # 截断过长内容，控制输入长度
        truncated_content = content_text[:MAX_CONTENT_LENGTH]

        # 构建用户提示词
        user_prompt = f"文章标题：{title}\n\n文章内容：\n{truncated_content}"

        # 调用 LLM 获取分类结果
        result = await self._llm_client.complete_json(
            system_prompt=CLASSIFICATION_PROMPT,
            user_prompt=user_prompt,
        )

        # 解析并返回分类结果
        classification = ClassificationResult(
            article_type=result.get("article_type", "noise"),
            confidence=result.get("confidence", 0.0),
            type_scores=result.get("type_scores", {}),
            reason=result.get("reason", ""),
        )
        logger.info(
            "文章分类: title=%.50s, type=%s, confidence=%.3f",
            title, classification.article_type, classification.confidence,
        )
        return classification


async def classify_article(
    llm_client: LLMClient,
    title: str,
    content_text: str,
) -> ClassificationResult:
    """对文章进行分类的便捷函数

    Args:
        llm_client: LLM 客户端实例
        title: 文章标题
        content_text: 文章正文内容

    Returns:
        ClassificationResult: 分类结果
    """
    classifier = ArticleClassifier(llm_client)
    return await classifier.classify(title, content_text)