"""文章分类结果的数据模型定义"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    """文章分类结果

    Attributes:
        article_type: 文章类型 (rule/record/concept/mixed/noise)
        confidence: 分类置信度 (0.0~1.0)
        type_scores: 各类型得分字典
        reason: 分类原因说明
    """
    article_type: str = Field(
        description="文章类型：rule/record/concept/mixed/noise"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="分类置信度，范围 0.0~1.0"
    )
    type_scores: dict[str, float] = Field(
        default_factory=dict,
        description="各类型得分，键为类型名，值为 0.0~1.0 的分数"
    )
    reason: str = Field(
        default="",
        description="简短分类原因"
    )