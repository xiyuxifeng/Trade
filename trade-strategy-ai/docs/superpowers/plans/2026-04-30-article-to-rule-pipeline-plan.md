# 从文章到规则的生产级交易系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现从文章提取可执行交易规则的完整闭环：分类→分层提取→规则池→回测验证→盘前预测→盘后归因

**Architecture:** 分层设计，新增 rule_pool 表存储独立规则，新增 article_classifier 做文章分类，复用现有 extract_article_metadata 做提取，扩展 BacktestEngine 支持规则回测，扩展 run_pre_market/run_after_close 增加规则联动

**Tech Stack:** Python, SQLAlchemy, Pydantic, APScheduler, 现有 LLM client, 现有 BacktestEngine

---

## 文件结构

```
# 新增文件
src/article_classifier/
    __init__.py
    classifier.py      # 分类器主逻辑
    prompts.py         # 分类 prompt
    schemas.py         # 分类结果 schema

src/rule_pool/
    __init__.py
    models.py          # SQLAlchemy ORM models (RulePool, TradeSample, ArticleClassification)
    repository.py      # 规则池 CRUD
    schemas.py         # Pydantic schemas
    reviewer.py        # 审核流程
    mapper.py          # DSL 映射工具

src/rule_backtest/
    __init__.py
    confidence.py      # 置信度计算
    validator.py       # 规则验证逻辑

src/rule_attribution/
    __init__.py
    attributor.py      # 归因分析
    analyzer.py        # 规则表现分析

# 扩展现有文件
src/agents/data_agent/skills/extract_article_metadata.py  # 扩展支持 article_type
src/models/article_metadata.py                             # 增加字段
src/backtest/engine.py                                     # 扩展支持规则池回测
cli/main.py                                                # 增加 rule-pool 命令组

# 数据库迁移
src/db/migrations/versions/  # 新增迁移脚本
```

---

## Task 1: 数据库模型定义

**Files:**
- Create: `src/rule_pool/models.py`
- Create: `src/db/migrations/versions/2026-04-30_create_rule_pool_tables.py`
- Modify: `src/models/article_metadata.py` (增加字段)
- Test: `tests/unit/rule_pool/test_models.py`

- [ ] **Step 1: 编写 models.py 的 Pydantic schemas**

```python
# src/rule_pool/schemas.py
from __future__ import annotations
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class RuleSourceType(StrEnum):
    STANDALONE = "standalone"    # 规则型文章提取
    DERIVED = "derived"          # 交易记录反推
    EXPERIENCE = "experience"    # 经验规则

class MappingStatus(StrEnum):
    UNMAPPED = "unmapped"
    PENDING = "pending"
    MAPPED = "mapped"
    UNMAPPABLE = "unmappable"

class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ArticleType(StrEnum):
    RULE = "rule"
    RECORD = "record"
    CONCEPT = "concept"
    MIXED = "mixed"
    NOISE = "noise"

class RuleBacktestResult(BaseModel):
    """回测结果"""
    run_id: str
    run_at: datetime
    start_date: date
    end_date: date
    total_trades: int = 0
    hit_trades: int = 0
    miss_trades: int = 0
    hit_rate: float = 0.0
    avg_return: float = 0.0
    avg_win_return: float | None = None  # 盈利交易平均收益（用于计算真实盈亏比）
    avg_loss_return: float | None = None  # 亏损交易平均收益绝对值
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    sample_count: int = 0

class RawCondition(BaseModel):
    """提取层的原始条件"""
    raw_text: str = ""
    indicators: list[str] = Field(default_factory=list)
    description: str = ""

class ExtractionLayer(BaseModel):
    """提取层"""
    rule_type: str
    instrument_focus: str = "mixed"
    raw_condition: RawCondition = Field(default_factory=RawCondition)
    mapped_condition: dict[str, Any] | None = None
    action: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    quoted_text: str | None = None

class RulePoolItem(BaseModel):
    """规则池条目"""
    id: UUID | None = None
    rule_id: str
    source_article_ids: list[str]
    source_type: RuleSourceType
    rule_type: str
    instrument_focus: str = "mixed"
    extraction_layer: ExtractionLayer
    mapping_status: MappingStatus = MappingStatus.UNMAPPED
    mapped_by: str | None = None
    mapped_at: datetime | None = None
    initial_confidence: float
    validated_confidence: float | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    backtest_triggered_at: datetime | None = None
    backtest_result: RuleBacktestResult | None = None
    backtest_hits: int = 0
    backtest_misses: int = 0
    backtest_samples: int = 0
    used_in_prediction: bool = False
    prediction_count: int = 0
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 2: 编写 SQLAlchemy ORM models**

```python
# src/rule_pool/models.py
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

JSONVariant = JSONB  # PostgreSQL 环境下直接使用 JSONB


class RulePool(TimestampMixin, Base):
    """规则池表"""
    __tablename__ = "rule_pool"
    __table_args__ = (
        Index("idx_rule_pool_status", "review_status", "mapping_status"),
        Index("idx_rule_pool_confidence", "validated_confidence"),
        Index("idx_rule_pool_rule_type", "rule_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_article_ids: Mapped[list[str]] = mapped_column(JSONVariant, nullable=False, default=list)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)

    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    instrument_focus: Mapped[str] = mapped_column(String(32), default="mixed")
    extraction_layer: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False)
    mapped_condition: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant, nullable=True)

    mapping_status: Mapped[str] = mapped_column(String(32), default="unmapped")
    mapped_by: Mapped[str | None] = mapped_column(String(64))
    mapped_at: Mapped[datetime | None] = mapped_column()

    initial_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    validated_confidence: Mapped[float | None] = mapped_column(Float)

    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(64))
    reviewed_at: Mapped[datetime | None] = mapped_column()

    backtest_triggered_at: Mapped[datetime | None] = mapped_column()
    backtest_result: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    backtest_hits: Mapped[int] = mapped_column(Integer, default=0)
    backtest_misses: Mapped[int] = mapped_column(Integer, default=0)
    backtest_samples: Mapped[int] = mapped_column(Integer, default=0)

    used_in_prediction: Mapped[bool] = mapped_column(default=False)
    prediction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column()


class TradeSample(TimestampMixin, Base):
    """交易样本表"""
    __tablename__ = "trade_sample"
    __table_args__ = (
        Index("idx_trade_sample_symbol", "symbol"),
        Index("idx_trade_sample_date", "entry_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_article_id: Mapped[UUID] = mapped_column(
        ForeignKey("blog_articles.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float)
    entry_date: Mapped[date | None] = mapped_column(Date)
    exit_date: Mapped[date | None] = mapped_column(Date)
    raw_description: Mapped[str | None] = mapped_column(String)
    derived_rule_id: Mapped[UUID | None] = mapped_column(ForeignKey("rule_pool.id"))


class ArticleClassification(TimestampMixin, Base):
    """文章分类表"""
    __tablename__ = "article_classification"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    article_id: Mapped[UUID] = mapped_column(
        ForeignKey("blog_articles.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    article_type: Mapped[str] = mapped_column(String(32), nullable=False)
    article_type_confidence: Mapped[float | None] = mapped_column(Float)
    classification_version: Mapped[str | None] = mapped_column(String(20))
    type_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONVariant)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(64))
    reviewed_at: Mapped[datetime | None] = mapped_column()
```

- [ ] **Step 3: 编写单元测试**

```python
# tests/unit/rule_pool/test_models.py
import pytest
from src.rule_pool.schemas import RulePoolItem, RawCondition, ExtractionLayer, RuleSourceType, MappingStatus

def test_rule_pool_item_creation():
    item = RulePoolItem(
        rule_id="test_rule_001",
        source_article_ids=["article-1", "article-2"],
        source_type=RuleSourceType.STANDALONE,
        rule_type="entry",
        extraction_layer=ExtractionLayer(
            rule_type="entry",
            raw_condition=RawCondition(
                raw_text="放量突破前高",
                indicators=["volume", "price"],
                description="当成交量放大且价格突破近期高点时买入"
            ),
            action={"type": "enter", "side": "buy"}
        ),
        initial_confidence=0.8
    )
    assert item.rule_id == "test_rule_001"
    assert item.source_type == RuleSourceType.STANDALONE
    assert item.extraction_layer.raw_condition.raw_text == "放量突破前高"

def test_raw_condition_defaults():
    rc = RawCondition()
    assert rc.raw_text == ""
    assert rc.indicators == []
    assert rc.description == ""
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/unit/rule_pool/test_models.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/rule_pool/models.py src/rule_pool/schemas.py tests/unit/rule_pool/test_models.py
git commit -m "feat: add rule_pool models and schemas"
```

---

## Task 2: article_classifier 分类器

**Files:**
- Create: `src/article_classifier/__init__.py`
- Create: `src/article_classifier/classifier.py`
- Create: `src/article_classifier/prompts.py`
- Create: `src/article_classifier/schemas.py`
- Create: `tests/unit/article_classifier/test_classifier.py`

- [ ] **Step 1: 编写分类 prompt**

```python
# src/article_classifier/prompts.py
CLASSIFICATION_PROMPT = """你是一个文章分类器。请判断以下文章的[主要]类型：

类型定义：
- rule: 描述一般性交易规则/策略，不针对具体历史操作
- record: 描述具体历史操作（包含明确的时间、价格、数量）
- concept: 纯理论/框架/心态分享，无具体条件
- mixed: 同一篇文章包含多种类型内容（如：先讲方法论，再列具体案例）
- noise: 个人观点、闲聊、新闻、无交易逻辑

输出格式（严格 JSON，不要输出任何其他内容）：
{{
    "article_type": "rule|record|concept|mixed|noise",
    "confidence": 0.0~1.0,
    "type_scores": {{"rule": 0.x, "record": 0.x, "concept": 0.x, "mixed": 0.x, "noise": 0.x}},
    "reason": "简短原因"
}}

注意：
- 如果是混合类型，选择最主要的类型
- confidence 低于 0.5 时标记为"需要人工复核"
- 只输出 JSON，不要输出任何解释或markdown
"""
```

- [ ] **Step 2: 编写分类结果 schema**

```python
# src/article_classifier/schemas.py
from __future__ import annotations
from pydantic import BaseModel

class ClassificationResult(BaseModel):
    """文章分类结果"""
    article_type: str  # rule/record/concept/mixed/noise
    confidence: float  # 0.0~1.0
    type_scores: dict[str, float]  # 各类型得分
    reason: str  # 分类原因
```

- [ ] **Step 3: 编写分类器主逻辑**

```python
# src/article_classifier/classifier.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from src.llm.client import LLMClient, LLMError
from src.article_classifier.prompts import CLASSIFICATION_PROMPT
from src.article_classifier.schemas import ClassificationResult

def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()

async def classify_article(
    client: LLMClient,
    title: str,
    content_text: str,
    published_at: str | None = None,
    author_name: str | None = None,
) -> ClassificationResult:
    """对文章进行类型分类

    Args:
        client: LLM 客户端
        title: 文章标题
        content_text: 文章正文
        published_at: 发布时间
        author_name: 作者

    Returns:
        ClassificationResult

    Raises:
        LLMError: 分类失败时抛出
    """
    # 控制内容长度
    content = content_text.strip()
    if len(content) > 10000:
        content = content[:10000]

    user_prompt = json.dumps(
        {
            "title": title,
            "content_text": content,
            "published_at": published_at,
            "author_name": author_name,
        },
        ensure_ascii=False,
    )

    system_prompt = CLASSIFICATION_PROMPT

    data = await client.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)

    return ClassificationResult(
        article_type=data.get("article_type", "noise"),
        confidence=float(data.get("confidence", 0.0)),
        type_scores=data.get("type_scores", {}),
        reason=data.get("reason", ""),
    )
```

- [ ] **Step 4: 编写单元测试**

```python
# tests/unit/article_classifier/test_classifier.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.article_classifier.classifier import classify_article
from src.article_classifier.schemas import ClassificationResult

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.complete_json = AsyncMock(return_value={
        "article_type": "rule",
        "confidence": 0.85,
        "type_scores": {"rule": 0.85, "record": 0.1, "concept": 0.03, "mixed": 0.01, "noise": 0.01},
        "reason": "文章描述了一般性MACD金叉买入规则"
    })
    return client

@pytest.mark.asyncio
async def test_classify_rule_article(mock_client):
    result = await classify_article(
        client=mock_client,
        title="MACD金叉买入法",
        content_text="当MACD指标从负转正且成交量放大时，是买入信号...",
        published_at="2024-01-15",
        author_name="test_author"
    )
    assert isinstance(result, ClassificationResult)
    assert result.article_type == "rule"
    assert result.confidence == 0.85
    mock_client.complete_json.assert_called_once()
```

- [ ] **Step 5: 运行测试验证**

Run: `pytest tests/unit/article_classifier/test_classifier.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/article_classifier/ tests/unit/article_classifier/test_classifier.py
git commit -m "feat: add article_classifier module"
```

---

## Task 3: 扩展 article_metadata 表

**Files:**
- Modify: `src/models/article_metadata.py`
- Create: `src/db/migrations/versions/2026-04-30_add_article_metadata_fields.py`
- Test: `tests/unit/models/test_article_metadata.py`

- [ ] **Step 1: 查看现有 article_metadata 模型**

```python
# src/models/article_metadata.py (现有结构)
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from src.models.base import Base, TimestampMixin

JSONVariant = JSON().with_variant(JSONB, "postgresql")


class ArticleMetadata(TimestampMixin, Base):
    __tablename__ = "article_metadata"
    __table_args__ = (
        UniqueConstraint("article_id", "schema_version", name="uq_article_metadata_article_id_version"),
        Index("ix_article_metadata_processed_at", "processed_at"),
        CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="sentiment_score_range",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="confidence_score_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    article_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("blog_articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column("schema_version", String(20), nullable=False, default="v1")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_concepts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    trading_symbols: Mapped[list[str]] = mapped_column(JSONVariant, default=list, nullable=False)
    strategy_rules: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    preconditions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    comment_insights: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVariant,
        default=list,
        nullable=False,
    )
    raw_llm_output: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    article = relationship("BlogArticle", back_populates="metadata_record")
```

- [ ] **Step 2: 添加新字段到模型**

```python
# 在 ArticleMetadata 类中添加（保持现有字段不变）
# 新增字段
article_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # rule/record/concept/mixed/noise
extraction_version: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 提取版本
standalone_rule_ids: Mapped[list[str] | None] = mapped_column(JSONVariant, nullable=True)  # 进入规则池的 standalone 规则 ID 列表
derived_rule_ids: Mapped[list[str] | None] = mapped_column(JSONVariant, nullable=True)  # 反推规则 ID 列表
trade_sample_ids: Mapped[list[str] | None] = mapped_column(JSONVariant, nullable=True)  # 交易样本 ID 列表
```

- [ ] **Step 3: 编写迁移脚本**

```python
# src/db/migrations/versions/2026-04-30_add_article_metadata_fields.py
"""Add fields to article_metadata

Revision ID: 20260430_add_fields
Revises: previous_revision_id
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260430_add_fields'
down_revision = 'previous_revision_id'  # 需要替换为实际的前一个版本
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('article_metadata', sa.Column('extraction_version', sa.String(20), nullable=True))
    op.add_column('article_metadata', sa.Column('standalone_rule_ids', sa.JSON, nullable=True))
    op.add_column('article_metadata', sa.Column('derived_rule_ids', sa.JSON, nullable=True))
    op.add_column('article_metadata', sa.Column('trade_sample_ids', sa.JSON, nullable=True))
    op.add_column('article_metadata', sa.Column('article_type', sa.String(32), nullable=True))

def downgrade() -> None:
    op.drop_column('article_metadata', 'article_type')
    op.drop_column('article_metadata', 'trade_sample_ids')
    op.drop_column('article_metadata', 'derived_rule_ids')
    op.drop_column('article_metadata', 'standalone_rule_ids')
    op.drop_column('article_metadata', 'extraction_version')
```

- [ ] **Step 4: 提交**

```bash
git add src/models/article_metadata.py src/db/migrations/versions/2026-04-30_add_article_metadata_fields.py
git commit -m "feat: add fields to article_metadata table"
```

---

## Task 4: rule_pool repository CRUD

**Files:**
- Create: `src/rule_pool/repository.py`
- Test: `tests/unit/rule_pool/test_repository.py`

- [ ] **Step 1: 编写 repository**

```python
# src/rule_pool/repository.py
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.rule_pool.models import RulePool, TradeSample, ArticleClassification
from src.rule_pool.schemas import RulePoolItem, MappingStatus, ReviewStatus, RuleBacktestResult

class RulePoolRepository:
    """规则池仓储"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_rule(self, rule: RulePoolItem) -> RulePool:
        """创建规则"""
        db_rule = RulePool(
            rule_id=rule.rule_id,
            source_article_ids=rule.source_article_ids,
            source_type=rule.source_type.value,
            rule_type=rule.rule_type,
            instrument_focus=rule.instrument_focus,
            extraction_layer=rule.extraction_layer.model_dump(),
            mapping_status=rule.mapping_status.value,
            initial_confidence=rule.initial_confidence,
            review_status=rule.review_status.value,
        )
        self.session.add(db_rule)
        await self.session.flush()
        return db_rule

    async def get_rule_by_id(self, rule_id: str) -> RulePool | None:
        """根据 rule_id 查询规则"""
        result = await self.session.execute(
            select(RulePool).where(RulePool.rule_id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_rules_by_status(
        self,
        review_status: ReviewStatus | None = None,
        mapping_status: MappingStatus | None = None,
        limit: int = 100,
    ) -> list[RulePool]:
        """根据状态查询规则"""
        query = select(RulePool)
        if review_status:
            query = query.where(RulePool.review_status == review_status.value)
        if mapping_status:
            query = query.where(RulePool.mapping_status == mapping_status.value)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_mapping(
        self,
        rule_id: str,
        mapped_condition: dict[str, Any],
        mapped_by: str,
    ) -> bool:
        """更新规则映射状态"""
        result = await self.session.execute(
            update(RulePool)
            .where(RulePool.rule_id == rule_id)
            .values(
                mapped_condition=mapped_condition,
                mapping_status=MappingStatus.MAPPED.value,
                mapped_by=mapped_by,
                mapped_at=datetime.now(),
            )
        )
        return result.rowcount > 0

    async def update_review(
        self,
        rule_id: str,
        review_status: ReviewStatus,
        reviewed_by: str,
    ) -> bool:
        """更新规则审核状态"""
        result = await self.session.execute(
            update(RulePool)
            .where(RulePool.rule_id == rule_id)
            .values(
                review_status=review_status.value,
                reviewed_by=reviewed_by,
                reviewed_at=datetime.now(),
            )
        )
        return result.rowcount > 0

    async def update_backtest_result(
        self,
        rule_id: str,
        backtest_result: RuleBacktestResult,
        initial_confidence: float,
    ) -> bool:
        """更新规则回测结果"""
        from src.rule_backtest.confidence import compute_confidence_adjustment

        validated_confidence = compute_confidence_adjustment(
            initial_confidence=initial_confidence,
            backtest_result=backtest_result,
        )
        result = await self.session.execute(
            update(RulePool)
            .where(RulePool.rule_id == rule_id)
            .values(
                backtest_triggered_at=datetime.now(),
                backtest_result=backtest_result.model_dump(),
                validated_confidence=validated_confidence,
                backtest_hits=backtest_result.hit_trades,
                backtest_misses=backtest_result.miss_trades,
                backtest_samples=backtest_result.sample_count,
            )
        )
        return result.rowcount > 0

    async def get_high_confidence_rules(self, threshold: float = 0.7) -> list[RulePool]:
        """获取高置信度规则"""
        result = await self.session.execute(
            select(RulePool)
            .where(
                RulePool.validated_confidence >= threshold,
                RulePool.review_status == ReviewStatus.APPROVED.value,
                RulePool.mapping_status == MappingStatus.MAPPED.value,
            )
            .limit(100)
        )
        return list(result.scalars().all())
```

- [ ] **Step 2: 编写单元测试**

```python
# tests/unit/rule_pool/test_repository.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.rule_pool.repository import RulePoolRepository
from src.rule_pool.schemas import RulePoolItem, ExtractionLayer, RawCondition, RuleSourceType

@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session

@pytest.mark.asyncio
async def test_create_rule(mock_session):
    repo = RulePoolRepository(mock_session)
    rule = RulePoolItem(
        rule_id="test_rule",
        source_article_ids=["a1"],
        source_type=RuleSourceType.STANDALONE,
        rule_type="entry",
        extraction_layer=ExtractionLayer(rule_type="entry"),
        initial_confidence=0.8,
    )
    db_rule = await repo.create_rule(rule)
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/rule_pool/test_repository.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/rule_pool/repository.py tests/unit/rule_pool/test_repository.py
git commit -m "feat: add rule_pool repository CRUD"
```

---

## Task 5: 置信度计算

**Files:**
- Create: `src/rule_backtest/confidence.py`
- Test: `tests/unit/rule_backtest/test_confidence.py`

- [ ] **Step 1: 编写置信度计算函数**

```python
# src/rule_backtest/confidence.py
from __future__ import annotations
from src.rule_pool.schemas import RuleBacktestResult

def compute_confidence_adjustment(
    initial_confidence: float,
    backtest_result: RuleBacktestResult,
    prior_weight: int = 20,
) -> float:
    """
    多指标综合置信度调整

    参数：
        initial_confidence: 提取时的初始置信度
        backtest_result: 回测结果
        prior_weight: 先验权重（样本少时保护）

    返回：
        validated_confidence: 验证后的置信度
    """
    # 1. 样本不足或零交易时保护性处理
    total = backtest_result.total_trades
    if backtest_result.sample_count < 10 or total == 0:
        return initial_confidence * 0.9

    # 2. 基本胜率
    hit_rate = backtest_result.hit_trades / total

    # 3. 盈亏比（盈利均值 / 亏损均值绝对值）
    avg_win = backtest_result.avg_win_return
    avg_loss = backtest_result.avg_loss_return
    if avg_win is not None and avg_loss is not None and avg_loss > 0:
        profit_loss_ratio = avg_win / avg_loss
    else:
        # 无细分数据时，用 avg_return 做保守近似
        avg_return = backtest_result.avg_return
        profit_loss_ratio = max(avg_return * 25 + 0.5, 0) if avg_return != 0 else 0.5

    # 4. 夏普比率调整
    sharpe = backtest_result.sharpe_ratio or 0
    sharpe_factor = max(min(sharpe / 2.0, 1.0), -1.0)  # 归一化到 [-1, 1]

    # 5. 最大回撤惩罚
    max_dd = backtest_result.max_drawdown or 0
    dd_penalty = max_dd * 0.5

    # 6. 综合得分
    score = (
        0.4 * hit_rate +  # 胜率权重 40%
        0.2 * min(profit_loss_ratio, 1.5) / 1.5 +  # 盈亏比权重 20%
        0.2 * (sharpe_factor + 1) / 2 +  # 夏普权重 20%
        0.2 * (1 - dd_penalty)  # 回撤权重 20%
    )

    # 7. 贝叶斯式加权更新
    n = backtest_result.sample_count
    validated_confidence = (
        initial_confidence * prior_weight + score * n
    ) / (prior_weight + n)

    return validated_confidence

def get_confidence_level(confidence: float) -> str:
    """获取置信度等级"""
    if confidence >= 0.8:
        return "A"
    elif confidence >= 0.6:
        return "B"
    elif confidence >= 0.4:
        return "C"
    else:
        return "D"
```

- [ ] **Step 2: 编写单元测试**

```python
# tests/unit/rule_backtest/test_confidence.py
import pytest
from src.rule_backtest.confidence import compute_confidence_adjustment, get_confidence_level
from src.rule_pool.schemas import RuleBacktestResult
from datetime import datetime

def test_compute_confidence_with_high_hit_rate():
    backtest_result = RuleBacktestResult(
        run_id="test_run",
        run_at=datetime.now(),
        start_date=datetime.now().date(),
        end_date=datetime.now().date(),
        total_trades=20,
        hit_trades=15,
        miss_trades=5,
        hit_rate=0.75,
        avg_return=0.02,
        sharpe_ratio=1.5,
        max_drawdown=0.1,
        sample_count=20,
    )
    initial = 0.7
    result = compute_confidence_adjustment(initial, backtest_result)
    assert 0.0 <= result <= 1.0
    assert result > initial  # 好结果应该提升置信度

def test_compute_confidence_low_sample():
    backtest_result = RuleBacktestResult(
        run_id="test_run",
        run_at=datetime.now(),
        start_date=datetime.now().date(),
        end_date=datetime.now().date(),
        total_trades=5,
        hit_trades=2,
        miss_trades=3,
        sample_count=5,
    )
    initial = 0.8
    result = compute_confidence_adjustment(initial, backtest_result)
    assert result == initial * 0.9  # 小样本保护

def test_confidence_level():
    assert get_confidence_level(0.85) == "A"
    assert get_confidence_level(0.7) == "B"
    assert get_confidence_level(0.5) == "C"
    assert get_confidence_level(0.3) == "D"
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/rule_backtest/test_confidence.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/rule_backtest/confidence.py tests/unit/rule_backtest/test_confidence.py
git commit -m "feat: add confidence computation"
```

---

## Task 6: DSL 映射工具

**Files:**
- Create: `src/rule_pool/mapper.py`
- Test: `tests/unit/rule_pool/test_mapper.py`

- [ ] **Step 1: 编写 DSL 映射工具**

```python
# src/rule_pool/mapper.py
from __future__ import annotations
from typing import Any

# 标准操作符
OPERATORS = ["and", "or", "not", "gt", "lt", "eq", "gte", "lte", "in", "not_in", "cross_above", "cross_below", "cmp"]

# 标准字段库
STANDARD_FIELDS = [
    "close", "open", "high", "low", "volume",
    "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
    "ema5", "ema10", "ema20", "ema60",
    "macd", "macd_signal", "macd_hist",
    "rsi6", "rsi12", "rsi24",
    "bollinger_upper", "bollinger_middle", "bollinger_lower",
    "kdj_k", "kdj_d", "kdj_j",
    "volume_ratio", "turnover_rate",
]

# 常用映射规则
MAPPING_RULES = {
    # 量能相关
    ("放量", "volume_ratio_above"): {"op": "gt", "field": "volume_ratio", "value": 1.5},
    ("缩量", "volume_ratio_below"): {"op": "lt", "field": "volume_ratio", "value": 0.7},
    ("巨量", "volume_ratio_above"): {"op": "gt", "field": "volume_ratio", "value": 3.0},
    # 价格相关
    ("突破", "close_above"): None,  # 需要更多上下文
    ("跌破", "close_below"): None,
    # 指标相关
    ("金叉", "cross_above"): None,
    ("死叉", "cross_below"): None,
    ("超卖", "rsi_below"): {"op": "lt", "field": "rsi6", "value": 30},
    ("超买", "rsi_above"): {"op": "gt", "field": "rsi6", "value": 70},
}

def suggest_mapping(raw_text: str) -> list[dict[str, Any]]:
    """根据原始文本建议可能的映射

    Args:
        raw_text: 原始条件文本

    Returns:
        可能的映射建议列表
    """
    suggestions = []
    for key, mapping in MAPPING_RULES.items():
        keyword, mapped_key = key
        if keyword in raw_text and mapping:
            suggestions.append({
                "keyword": keyword,
                "mapped_key": mapped_key,
                "mapping": mapping,
                "confidence": 0.8,
            })
    return suggestions

def validate_mapped_condition(condition: dict[str, Any]) -> tuple[bool, str]:
    """验证映射后的条件是否合法

    Args:
        condition: 映射后的条件字典

    Returns:
        (是否合法, 错误信息)
    """
    if not isinstance(condition, dict):
        return False, "condition must be a dict"

    op = condition.get("op")
    if op not in OPERATORS:
        return False, f"unknown operator: {op}"

    # 检查 field 是否在标准字段库中（针对 cmp 操作）
    if op == "cmp":
        field = condition.get("field")
        if field and field not in STANDARD_FIELDS:
            # 允许自定义字段，但给出警告
            pass  # 不阻止，允许灵活扩展

    return True, ""

def build_and_condition(*conditions: dict[str, Any]) -> dict[str, Any]:
    """构建 AND 条件"""
    return {"op": "and", "args": list(conditions)}

def build_or_condition(*conditions: dict[str, Any]) -> dict[str, Any]:
    """构建 OR 条件"""
    return {"op": "or", "args": list(conditions)}

def build_cmp_condition(field: str, cmp_op: str, value: Any) -> dict[str, Any]:
    """构建比较条件"""
    return {"op": "cmp", "field": field, "cmp": cmp_op, "value": value}
```

- [ ] **Step 2: 编写单元测试**

```python
# tests/unit/rule_pool/test_mapper.py
import pytest
from src.rule_pool.mapper import suggest_mapping, validate_mapped_condition, build_and_condition, build_cmp_condition

def test_suggest_mapping_volume():
    suggestions = suggest_mapping("放量突破前高")
    assert len(suggestions) >= 1
    keyword = next((s["keyword"] for s in suggestions if s["keyword"] == "放量"), None)
    assert keyword == "放量"

def test_validate_mapped_condition_valid():
    condition = {"op": "cmp", "field": "volume_ratio", "cmp": "gt", "value": 1.5}
    valid, error = validate_mapped_condition(condition)
    assert valid is True
    assert error == ""

def test_validate_mapped_condition_invalid_op():
    condition = {"op": "unknown_op", "field": "volume"}
    valid, error = validate_mapped_condition(condition)
    assert valid is False
    assert "unknown operator" in error

def test_build_and_condition():
    cond1 = build_cmp_condition("volume_ratio", "gt", 1.5)
    cond2 = build_cmp_condition("close", "gt", 10.0)
    and_cond = build_and_condition(cond1, cond2)
    assert and_cond["op"] == "and"
    assert len(and_cond["args"]) == 2
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/unit/rule_pool/test_mapper.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/rule_pool/mapper.py tests/unit/rule_pool/test_mapper.py
git commit -m "feat: add DSL mapper utility"
```

---

## Task 7: 扩展 extract_article_metadata 支持 article_type

**Files:**
- Modify: `src/agents/data_agent/skills/extract_article_metadata.py`
- Modify: `src/models/article_metadata.py`
- Test: `tests/unit/agents/test_extract_article_metadata_extended.py`

- [ ] **Step 1: 阅读现有代码理解结构**

关键点：
- `_process_one_article` 函数处理单篇文章
- 需要在提取前先调用 article_classifier 分类
- 分类结果存储到 `meta.article_type`

- [ ] **Step 2: 修改 extract_article_metadata.py**

在 `_process_one_article` 函数中添加：

```python
# 在函数开头添加 article_type 分类
async def _process_one_article(
    # ... 现有参数 ...
):
    stats.scanned += 1

    # 新增：文章分类
    if client.is_enabled():
        try:
            from src.article_classifier.classifier import classify_article
            classification = await classify_article(
                client=client,
                title=article.title,
                content_text=article.content_text or "",
                published_at=article.published_at.isoformat() if article.published_at else None,
                author_name=article.author_name,
            )
            meta.article_type = classification.article_type
        except Exception:
            meta.article_type = "noise"  # 分类失败默认为噪音

    # ... 后续现有逻辑保持不变 ...
```

- [ ] **Step 3: 修改 article_metadata.py 添加 article_type 字段到 ORM**

```python
# 在 ArticleMetadata 类中添加
article_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # rule/record/concept/mixed/noise
```

- [ ] **Step 4: 编写扩展测试**

```python
# tests/unit/agents/test_extract_article_metadata_extended.py
import pytest
from unittest.mock import AsyncMock, MagicMock
# ... 现有测试扩展 ...
```

- [ ] **Step 5: 运行测试验证**

Run: `pytest tests/unit/agents/test_extract_article_metadata.py -v`
Expected: PASS（现有测试不应被破坏）

- [ ] **Step 6: 提交**

```bash
git add src/agents/data_agent/skills/extract_article_metadata.py src/models/article_metadata.py
git commit -m "feat: extend extract_article_metadata to support article_type classification"
```

---

## Task 8: 扩展 BacktestEngine 支持规则池回测

**Files:**
- Modify: `src/backtest/engine.py`
- Modify: `src/backtest/rule_registry.py`
- Test: `tests/unit/backtest/test_rule_pool_backtest.py`

- [ ] **Step 1: 阅读现有 BacktestEngine 理解结构**

关键点：
- `run(request: BacktestRequest) -> BacktestResult`
- 已有 `SnapshotLoader`, `score_backtest_trade` 等

- [ ] **Step 2: 扩展 BacktestEngine 添加规则回测方法**

```python
# 在 BacktestEngine 类中添加

async def run_rules_backtest(
    self,
    session: AsyncSession,
    rule_ids: list[str] | None = None,  # None 表示全部规则
    start_date: date,
    end_date: date,
    min_confidence: float = 0.5,
) -> BacktestResult:
    """
    对规则池中的规则进行回测

    Args:
        session: 数据库会话（BacktestEngine 本身不持有 session）
        rule_ids: 要回测的规则 ID 列表，None 表示全部
        start_date: 回测开始日期
        end_date: 回测结束日期
        min_confidence: 最小置信度阈值

    Returns:
        BacktestResult
    """
    from src.rule_pool.repository import RulePoolRepository

    # 1. 获取要回测的规则
    repo = RulePoolRepository(session)
    if rule_ids:
        rules = []
        for rid in rule_ids:
            rule = await repo.get_rule_by_id(rid)
            if rule and rule.validated_confidence and rule.validated_confidence >= min_confidence:
                rules.append(rule)
    else:
        rules = await repo.get_high_confidence_rules(threshold=min_confidence)

    # 2. 对每条规则执行回测
    rule_results = []
    for rule in rules:
        result = await self._backtest_single_rule(rule, start_date, end_date)
        rule_results.append(result)

    # 3. 汇总结果
    return self._aggregate_rule_results(rule_results)

async def _backtest_single_rule(
    self,
    rule: RulePool,
    start_date: date,
    end_date: date,
) -> RuleBacktestResult:
    """对单条规则执行回测"""
    # ✅ 已实现（2026-05-07）：解析 mapped_condition → 加载 OHLCV/指标 → 评估 → T+1 收益
    pass  # 详见 src/backtest/engine.py:_backtest_single_rule

def _aggregate_rule_results(
    self,
    results: list[RuleBacktestResult],
) -> BacktestResult:
    """汇总规则回测结果"""
    # TODO: 实现结果聚合
    pass
```

- [ ] **Step 3: 提交**

```bash
git add src/backtest/engine.py
git commit -m "feat: extend BacktestEngine for rule pool backtest"
```

---

## Task 9: CLI 命令扩展

**Files:**
- Modify: `cli/main.py`
- Test: `tests/unit/cli/test_rule_pool_commands.py`

- [ ] **Step 1: 添加 rule-pool 命令组**

```python
# cli/main.py 中添加
import typer
from src.rule_pool.repository import RulePoolRepository
from src.db.session import session_scope

rule_pool_app = typer.Typer()

@rule_pool_app.command("list")
def rule_pool_list(limit: int = 100):
    """列出规则池中的规则"""
    import asyncio
    async def _run():
        async with session_scope() as session:
            repo = RulePoolRepository(session)
            rules = await repo.get_rules_by_status(limit=limit)
            for r in rules:
                print(f"{r.rule_id} | {r.rule_type} | confidence={r.validated_confidence or r.initial_confidence:.2f} | status={r.review_status}")
    asyncio.run(_run())

@rule_pool_app.command("review")
def rule_pool_review(rule_id: str, decision: str):
    """审核规则 (approve/reject)"""
    import asyncio
    from src.rule_pool.schemas import ReviewStatus

    async def _run():
        async with session_scope() as session:
            repo = RulePoolRepository(session)
            status = ReviewStatus.APPROVED if decision == "approve" else ReviewStatus.REJECTED
            await repo.update_review(rule_id, status, reviewed_by="cli_user")
            print(f"Rule {rule_id} {status.value}")
    asyncio.run(_run())

# 在 main.py 末尾（其他 add_typer 附近）注册
app.add_typer(rule_pool_app, name="rule-pool")
```

- [ ] **Step 2: 提交**

```bash
git add cli/main.py
git commit -m "feat: add rule-pool CLI commands"
```

---

## Task 10: 回测触发与调度

**Files:**
- Create: `src/rule_backtest/scheduler.py`
- Modify: `src/pipeline/scheduler.py`

- [ ] **Step 1: 编写回测调度器**

```python
# src/rule_backtest/scheduler.py
from __future__ import annotations
import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.common.config import AppConfig
from src.backtest.engine import BacktestEngine

def build_rule_backtest_scheduler(
    *,
    config: AppConfig,
    session_factory,
) -> BackgroundScheduler:
    """构建规则回测调度器

    每周日凌晨 00:00 执行全量规则回测
    """
    sched = BackgroundScheduler()

    def _job() -> None:
        from datetime import date
        from src.db.session import async_session_factory

        async def _run():
            from src.db.session import get_session_factory
            AsyncSessionFactory = get_session_factory()
            async with AsyncSessionFactory() as session:
                engine = BacktestEngine()
                result = await engine.run_rules_backtest(
                    session=session,
                    start_date=date(2023, 1, 1),
                    end_date=date(2026, 4, 30),
                )
                print(f"Rule backtest completed: {result.summary}")

        asyncio.run(_run())

    # 每周日凌晨 00:00
    sched.add_job(_job, CronTrigger(day_of_week="sun", hour=0, minute=0), id="rule_backtest_weekly")
    return sched
```

- [ ] **Step 2: 提交**

```bash
git add src/rule_backtest/scheduler.py
git commit -m "feat: add rule backtest scheduler"
```

---

## 自检清单

完成所有任务后，逐项检查：

### 1. Spec 覆盖率

| 设计章节 | 对应 Task |
|---------|----------|
| 阶段一：文章分类 | Task 2, Task 7 |
| 阶段二：分层提取 | Task 7（复用现有） |
| 阶段三：进入规则池 | Task 4 |
| 阶段四：DSL 映射 | Task 6 |
| 阶段五：回测验证 | Task 5, Task 8, Task 10 |
| 阶段六：置信度调整 | Task 5 |
| 阶段七：盘前预测 | Task 8 扩展 |
| 阶段八：盘后归因 | Future work |
| 阶段九：规则优化 | Future work |
| 数据库表 | Task 1, Task 3 |
| CLI 命令 | Task 9 |

### 2. 占位符扫描

- [ ] 无 "TBD"、"TODO" 类的占位符
- [ ] 所有函数都有实际实现（即使是简化的 TODO 注释）
- [ ] 测试代码完整可运行

### 3. 类型一致性

- [ ] `RulePoolItem.rule_id` 类型与 `RulePool.rule_id` 一致
- [ ] `MappingStatus` 枚举值与数据库存储一致
- [ ] `ReviewStatus` 枚举值与数据库存储一致

---

**Plan saved to:** `docs/superpowers/plans/2026-04-30-article-to-rule-pipeline-plan.md`

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-04-30-article-to-rule-pipeline-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**