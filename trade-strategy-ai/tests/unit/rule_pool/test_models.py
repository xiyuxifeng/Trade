"""rule_pool models 单元测试"""
import pytest
from datetime import datetime, date
from uuid import uuid4

from src.rule_pool.schemas import (
    RulePoolItem,
    TradeSampleItem,
    ArticleClassificationItem,
    RuleSourceType,
    MappingStatus,
    ReviewStatus,
    ArticleType,
    RuleBacktestResult,
    RawCondition,
    ExtractionLayer,
)
from src.rule_pool.models import RulePool, TradeSample, ArticleClassification


class TestRulePoolSchemas:
    """测试 RulePool 相关 Pydantic schemas"""

    def test_rule_source_type_enum(self):
        """测试规则来源类型枚举"""
        assert RuleSourceType.STANDALONE == "standalone"
        assert RuleSourceType.DERIVED == "derived"
        assert RuleSourceType.EXPERIENCE == "experience"

    def test_mapping_status_enum(self):
        """测试映射状态枚举"""
        assert MappingStatus.UNMAPPED == "unmapped"
        assert MappingStatus.PENDING == "pending"
        assert MappingStatus.MAPPED == "mapped"
        assert MappingStatus.UNMAPPABLE == "unmappable"

    def test_review_status_enum(self):
        """测试审核状态枚举"""
        assert ReviewStatus.PENDING == "pending"
        assert ReviewStatus.APPROVED == "approved"
        assert ReviewStatus.REJECTED == "rejected"

    def test_article_type_enum(self):
        """测试文章类型枚举"""
        assert ArticleType.RULE == "rule"
        assert ArticleType.RECORD == "record"
        assert ArticleType.CONCEPT == "concept"
        assert ArticleType.MIXED == "mixed"
        assert ArticleType.NOISE == "noise"

    def test_raw_condition_default(self):
        """测试 RawCondition 默认值"""
        raw = RawCondition()
        assert raw.raw_text == ""
        assert raw.indicators == []
        assert raw.description == ""

    def test_extraction_layer_default(self):
        """测试 ExtractionLayer 默认值"""
        layer = ExtractionLayer(rule_type="breakout")
        assert layer.rule_type == "breakout"
        assert layer.instrument_focus == "mixed"
        assert isinstance(layer.raw_condition, RawCondition)
        assert layer.mapped_condition is None
        assert layer.action == {}
        assert layer.confidence == 0.5
        assert layer.quoted_text is None

    def test_rule_backtest_result_creation(self):
        """测试 RuleBacktestResult 创建"""
        result = RuleBacktestResult(
            run_id="run_001",
            run_at=datetime.now(),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            total_trades=100,
            hit_trades=70,
            miss_trades=30,
            hit_rate=0.7,
            avg_return=0.05,
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            sample_count=100,
        )
        assert result.run_id == "run_001"
        assert result.total_trades == 100
        assert result.hit_rate == 0.7

    def test_rule_pool_item_creation(self):
        """测试 RulePoolItem 创建"""
        layer = ExtractionLayer(
            rule_type="breakout",
            instrument_focus="stock",
            raw_condition=RawCondition(
                raw_text="price breaks above 20-day high",
                indicators=["MA20"],
                description="突破20日均线",
            ),
            confidence=0.8,
        )
        item = RulePoolItem(
            rule_id="rule_001",
            source_article_ids=["article_001", "article_002"],
            source_type=RuleSourceType.STANDALONE,
            rule_type="breakout",
            extraction_layer=layer,
            initial_confidence=0.8,
        )
        assert item.rule_id == "rule_001"
        assert item.source_type == RuleSourceType.STANDALONE
        assert item.extraction_layer.rule_type == "breakout"
        assert item.mapping_status == MappingStatus.UNMAPPED
        assert item.review_status == ReviewStatus.PENDING

    def test_rule_pool_item_with_backtest(self):
        """测试带回测结果的 RulePoolItem"""
        backtest_result = RuleBacktestResult(
            run_id="run_002",
            run_at=datetime.now(),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            total_trades=50,
            hit_trades=40,
            miss_trades=10,
            hit_rate=0.8,
            avg_return=0.06,
        )
        layer = ExtractionLayer(rule_type="mean_reversion")
        item = RulePoolItem(
            rule_id="rule_002",
            source_article_ids=["article_003"],
            source_type=RuleSourceType.DERIVED,
            rule_type="mean_reversion",
            extraction_layer=layer,
            initial_confidence=0.7,
            backtest_result=backtest_result,
            backtest_hits=40,
            backtest_misses=10,
            backtest_samples=50,
        )
        assert item.backtest_hits == 40
        assert item.backtest_result is not None
        assert item.backtest_result.hit_rate == 0.8

    def test_trade_sample_item_creation(self):
        """测试 TradeSampleItem 创建"""
        sample = TradeSampleItem(
            sample_id="sample_001",
            article_id="article_001",
            symbol="AAPL",
            side="BUY",
            entry_price=150.0,
            quantity=100,
            entry_at=datetime(2026, 1, 15, 10, 0, 0),
            tags=[" earnings", "breakout"],
        )
        assert sample.sample_id == "sample_001"
        assert sample.symbol == "AAPL"
        assert sample.pnl is None
        assert sample.exit_at is None

    def test_article_classification_item_creation(self):
        """测试 ArticleClassificationItem 创建"""
        classification = ArticleClassificationItem(
            article_id="article_001",
            article_type=ArticleType.RULE,
            confidence=0.9,
            classified_by="gpt-4",
            reasons=["contains trading rules", "explicit entry/exit conditions"],
            metadata={"keywords": [" breakout", " MA20"]},
        )
        assert classification.article_id == "article_001"
        assert classification.article_type == ArticleType.RULE
        assert classification.confidence == 0.9


class TestRulePoolModels:
    """测试 RulePool SQLAlchemy ORM 模型"""

    def test_rule_pool_table_name(self):
        """测试 RulePool 表名"""
        assert RulePool.__tablename__ == 'rule_pool'

    def test_trade_sample_table_name(self):
        """测试 TradeSample 表名"""
        assert TradeSample.__tablename__ == 'trade_sample'

    def test_article_classification_table_name(self):
        """测试 ArticleClassification 表名"""
        assert ArticleClassification.__tablename__ == 'article_classification'

    def test_rule_pool_columns(self):
        """测试 RulePool 列定义"""
        columns = [c.name for c in RulePool.__table__.columns]
        assert 'id' in columns
        assert 'rule_id' in columns
        assert 'source_article_ids' in columns
        assert 'source_type' in columns
        assert 'rule_type' in columns
        assert 'extraction_layer' in columns
        assert 'mapping_status' in columns
        assert 'initial_confidence' in columns
        assert 'review_status' in columns
        assert 'backtest_result' in columns
        assert 'used_in_prediction' in columns
        assert 'created_at' in columns
        assert 'updated_at' in columns

    def test_trade_sample_columns(self):
        """测试 TradeSample 列定义"""
        columns = [c.name for c in TradeSample.__table__.columns]
        assert 'id' in columns
        assert 'sample_id' in columns
        assert 'article_id' in columns
        assert 'rule_id' in columns
        assert 'symbol' in columns
        assert 'side' in columns
        assert 'entry_price' in columns
        assert 'exit_price' in columns
        assert 'quantity' in columns
        assert 'entry_at' in columns
        assert 'exit_at' in columns
        assert 'pnl' in columns
        assert 'pnl_pct' in columns
        assert 'holding_period' in columns
        assert 'tags' in columns
        assert 'notes' in columns
        assert 'created_at' in columns
        assert 'updated_at' in columns

    def test_article_classification_columns(self):
        """测试 ArticleClassification 列定义"""
        columns = [c.name for c in ArticleClassification.__table__.columns]
        assert 'id' in columns
        assert 'article_id' in columns
        assert 'article_type' in columns
        assert 'confidence' in columns
        assert 'classified_by' in columns
        assert 'classified_at' in columns
        assert 'reasons' in columns
        # 使用 extra_metadata 而非 metadata，因 metadata 是 SQLAlchemy 保留字
        assert 'extra_metadata' in columns
        assert 'created_at' in columns
        assert 'updated_at' in columns

    def test_rule_pool_indexes(self):
        """测试 RulePool 索引"""
        index_names = [idx.name for idx in RulePool.__table__.indexes]
        assert 'ix_rule_pool_rule_id' in index_names
        assert 'ix_rule_pool_rule_type' in index_names
        assert 'ix_rule_pool_mapping_status' in index_names
        assert 'ix_rule_pool_review_status' in index_names
        assert 'ix_rule_pool_created_at' in index_names

    def test_trade_sample_indexes(self):
        """测试 TradeSample 索引"""
        index_names = [idx.name for idx in TradeSample.__table__.indexes]
        assert 'ix_trade_sample_sample_id' in index_names
        assert 'ix_trade_sample_symbol' in index_names
        assert 'ix_trade_sample_entry_at' in index_names
        assert 'ix_trade_sample_article_id' in index_names
        assert 'ix_trade_sample_rule_id' in index_names

    def test_article_classification_indexes(self):
        """测试 ArticleClassification 索引"""
        index_names = [idx.name for idx in ArticleClassification.__table__.indexes]
        assert 'ix_article_classification_article_id' in index_names
        assert 'ix_article_classification_article_type' in index_names
        assert 'ix_article_classification_confidence' in index_names


class TestSchemaModelConsistency:
    """测试 schemas 和 models 的一致性"""

    def test_rule_pool_item_matches_model(self):
        """验证 RulePoolItem schema 与 RulePool model 字段对应"""
        # Schema 中定义的字段应该能在 model 中找到对应
        schema_fields = [
            'rule_id', 'source_article_ids', 'source_type', 'rule_type',
            'instrument_focus', 'extraction_layer', 'mapping_status',
            'initial_confidence', 'validated_confidence', 'review_status',
            'backtest_result', 'backtest_hits', 'backtest_misses',
            'used_in_prediction', 'prediction_count',
        ]
        model_columns = [c.name for c in RulePool.__table__.columns]

        for field in schema_fields:
            # 验证 schema 字段在 model 中存在（backtest_result 在 model 中是 JSONB）
            if field != 'backtest_result':
                assert field in model_columns, f"Field {field} not found in RulePool model"

    def test_trade_sample_item_matches_model(self):
        """验证 TradeSampleItem schema 与 TradeSample model 字段对应"""
        schema_fields = [
            'sample_id', 'article_id', 'rule_id', 'symbol', 'side',
            'entry_price', 'exit_price', 'quantity', 'entry_at',
            'exit_at', 'pnl', 'pnl_pct', 'holding_period', 'tags', 'notes',
        ]
        model_columns = [c.name for c in TradeSample.__table__.columns]

        for field in schema_fields:
            assert field in model_columns, f"Field {field} not found in TradeSample model"

    def test_article_classification_item_matches_model(self):
        """验证 ArticleClassificationItem schema 与 ArticleClassification model 字段对应"""
        # 注意：schema 中使用 metadata，model 中使用 extra_metadata（因 metadata 是 SQLAlchemy 保留字）
        schema_field = 'metadata'
        model_column = 'extra_metadata'
        model_columns = [c.name for c in ArticleClassification.__table__.columns]
        assert model_column in model_columns, f"Column {model_column} not found in ArticleClassification model"