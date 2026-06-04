from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ArticleMetadataCandidateResponse(BaseModel):
    """单篇文章的候选 metadata 版本摘要。"""

    model_config = ConfigDict(from_attributes=True)

    schema_version: str
    score: float
    score_reasons: list[str] = Field(default_factory=list)
    processed_at: datetime | None = None
    provider: str | None = None
    model: str | None = None
    article_type: str | None = None
    extraction_version: str | None = None
    sentiment_score: float | None = None
    confidence_score: float | None = None
    extracted_concepts_count: int = 0
    trading_symbols_count: int = 0
    strategy_rules_count: int = 0
    preconditions_count: int = 0
    comment_insights_count: int = 0
    raw_llm_output_keys: int = 0


class ArticleMetadataResolutionResponse(BaseModel):
    """单篇文章的 metadata 版本选择结果。"""

    model_config = ConfigDict(from_attributes=True)

    article_id: str
    selected_schema_version: str | None = None
    selected_by: str | None = None
    selected_at: datetime | None = None
    selection_mode: str | None = None
    selection_score: float | None = None
    selection_reason: str | None = None
    recommended_schema_version: str | None = None
    recommended_score: float | None = None
    recommended_reason: str | None = None
    effective_schema_version: str | None = None
    effective_score: float | None = None
    effective_reason: str | None = None
    warning: str | None = None
    candidates: list[ArticleMetadataCandidateResponse] = Field(default_factory=list)


class ArticleMetadataResolutionListResponse(BaseModel):
    """文章 metadata 版本选择的批量响应。"""

    items: list[ArticleMetadataResolutionResponse] = Field(default_factory=list)


class ArticleMetadataListItemResponse(BaseModel):
    """文章 metadata 选择列表项。"""

    model_config = ConfigDict(from_attributes=True)

    article_id: str
    title: str
    author_name: str | None = None
    author_id: str | None = None
    source: str
    source_url: str
    published_at: datetime | None = None
    crawled_at: datetime
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    selection_status: Literal["selected", "unselected"]
    selected_schema_version: str | None = None
    selected_by: str | None = None
    selected_at: datetime | None = None
    selection_mode: str | None = None
    selection_reason: str | None = None
    recommended_schema_version: str | None = None
    effective_schema_version: str | None = None


class ArticleMetadataListResponse(BaseModel):
    """文章 metadata 选择列表分页响应。"""

    items: list[ArticleMetadataListItemResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    pages: int = 0


class ArticleMetadataSelectRequest(BaseModel):
    """手动选择文章 metadata 版本的请求。"""

    selected_schema_version: str
    selected_by: str = "web"
    selection_reason: str | None = None
