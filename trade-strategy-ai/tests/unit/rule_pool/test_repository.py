"""rule_pool repository 单元测试"""
import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.rule_pool.repository import RulePoolRepository
from src.rule_pool.models import RulePool
from src.rule_pool.schemas import (
    MappingStatus,
    ReviewStatus,
    RuleBacktestResult,
    RulePoolItem,
    RuleSourceType,
    ExtractionLayer,
    RawCondition,
)


class TestRulePoolRepository:
    """测试 RulePoolRepository 的 CRUD 方法"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的 AsyncSession"""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def sample_rule_item(self) -> RulePoolItem:
        """创建示例 RulePoolItem"""
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
        return RulePoolItem(
            rule_id="rule_test_001",
            source_article_ids=["article_001", "article_002"],
            source_type=RuleSourceType.STANDALONE,
            rule_type="breakout",
            extraction_layer=layer,
            initial_confidence=0.8,
        )

    @pytest.mark.asyncio
    async def test_create_rule(self, mock_session, sample_rule_item):
        """测试 create_rule 方法"""
        repo = RulePoolRepository(mock_session)

        # 执行创建
        result = await repo.create_rule(sample_rule_item)

        # 验证
        assert result is not None
        assert result.rule_id == sample_rule_item.rule_id
        assert result.source_type == sample_rule_item.source_type.value
        assert result.rule_type == sample_rule_item.rule_type
        assert result.initial_confidence == sample_rule_item.initial_confidence
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_rule_by_id_found(self, mock_session):
        """测试 get_rule_by_id 找到规则的情况"""
        # 模拟查询结果
        mock_rule = MagicMock(spec=RulePool)
        mock_rule.rule_id = "rule_test_001"
        mock_rule.source_type = "standalone"
        mock_rule.mapping_status = "unmapped"
        mock_rule.review_status = "pending"
        mock_rule.extraction_layer = {}
        mock_rule.backtest_result = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.get_rule_by_id("rule_test_001")

        assert result is not None
        assert result.rule_id == "rule_test_001"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_rule_by_id_not_found(self, mock_session):
        """测试 get_rule_by_id 未找到规则的情况"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.get_rule_by_id("non_existent_rule")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_rules_by_status_with_filters(self, mock_session):
        """测试 get_rules_by_status 带过滤条件"""
        mock_rules = [
            MagicMock(spec=RulePool),
            MagicMock(spec=RulePool),
        ]
        mock_rules[0].rule_id = "rule_001"
        mock_rules[1].rule_id = "rule_002"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_rules
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.get_rules_by_status(
            review_status=ReviewStatus.PENDING,
            mapping_status=MappingStatus.UNMAPPED,
            limit=50,
        )

        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_rules_by_status_no_filters(self, mock_session):
        """测试 get_rules_by_status 无过滤条件"""
        mock_rules = [MagicMock(spec=RulePool)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_rules
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.get_rules_by_status()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_update_mapping_success(self, mock_session):
        """测试 update_mapping 成功更新"""
        mock_rule = MagicMock(spec=RulePool)
        mock_rule.rule_id = "rule_test_001"
        mock_rule.mapping_status = "unmapped"
        mock_rule.extraction_layer = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.update_mapping(
            rule_id="rule_test_001",
            mapped_condition={"indicator": "MA20", "period": 20},
            mapped_by="test_user",
        )

        assert result is True
        assert mock_rule.mapping_status == MappingStatus.MAPPED.value
        assert mock_rule.mapped_by == "test_user"
        assert mock_rule.mapped_at is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_mapping_not_found(self, mock_session):
        """测试 update_mapping 规则不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.update_mapping(
            rule_id="non_existent",
            mapped_condition={},
            mapped_by="test_user",
        )

        assert result is False
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_review_success(self, mock_session):
        """测试 update_review 成功更新"""
        mock_rule = MagicMock(spec=RulePool)
        mock_rule.rule_id = "rule_test_001"
        mock_rule.review_status = "pending"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.update_review(
            rule_id="rule_test_001",
            review_status=ReviewStatus.APPROVED,
            reviewed_by="reviewer_001",
        )

        assert result is True
        assert mock_rule.review_status == ReviewStatus.APPROVED.value
        assert mock_rule.reviewed_by == "reviewer_001"
        assert mock_rule.reviewed_at is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_review_not_found(self, mock_session):
        """测试 update_review 规则不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.update_review(
            rule_id="non_existent",
            review_status=ReviewStatus.APPROVED,
            reviewed_by="reviewer_001",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_backtest_result_success(self, mock_session):
        """测试 update_backtest_result 成功更新"""
        mock_rule = MagicMock(spec=RulePool)
        mock_rule.rule_id = "rule_test_001"
        mock_rule.backtest_result = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result

        backtest_result = RuleBacktestResult(
            run_id="run_001",
            run_at=datetime.now(),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            total_trades=100,
            hit_trades=70,
            miss_trades=30,
            hit_rate=0.7,
            avg_return=0.05,
            sample_count=100,
        )

        repo = RulePoolRepository(mock_session)
        result = await repo.update_backtest_result(
            rule_id="rule_test_001",
            backtest_result=backtest_result,
            initial_confidence=0.8,
        )

        assert result is True
        assert mock_rule.backtest_triggered_at is not None
        assert mock_rule.backtest_hits == 70
        assert mock_rule.backtest_misses == 30
        assert mock_rule.backtest_samples == 100
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_backtest_result_not_found(self, mock_session):
        """测试 update_backtest_result 规则不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        backtest_result = RuleBacktestResult(
            run_id="run_001",
            run_at=datetime.now(),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            total_trades=50,
            hit_trades=40,
            miss_trades=10,
            hit_rate=0.8,
            sample_count=50,
        )

        repo = RulePoolRepository(mock_session)
        result = await repo.update_backtest_result(
            rule_id="non_existent",
            backtest_result=backtest_result,
            initial_confidence=0.8,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_high_confidence_rules(self, mock_session):
        """测试 get_high_confidence_rules 方法"""
        mock_rules = [MagicMock(spec=RulePool), MagicMock(spec=RulePool)]
        mock_rules[0].rule_id = "high_conf_001"
        mock_rules[0].validated_confidence = 0.85
        mock_rules[1].rule_id = "high_conf_002"
        mock_rules[1].validated_confidence = 0.75

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_rules
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.get_high_confidence_rules(threshold=0.7)

        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_high_confidence_rules_empty(self, mock_session):
        """测试 get_high_confidence_rules 无结果"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        repo = RulePoolRepository(mock_session)
        result = await repo.get_high_confidence_rules(threshold=0.9)

        assert len(result) == 0


class TestRulePoolRepositoryConversion:
    """测试 RulePoolRepository 的 ORM <-> Schema 转换方法"""

    def test_to_orm_model(self):
        """测试 _to_orm_model 方法"""
        layer = ExtractionLayer(
            rule_type="breakout",
            instrument_focus="stock",
            confidence=0.8,
        )
        item = RulePoolItem(
            rule_id="rule_test_001",
            source_article_ids=["article_001"],
            source_type=RuleSourceType.STANDALONE,
            rule_type="breakout",
            extraction_layer=layer,
            initial_confidence=0.8,
            # RulePoolItem 的 instrument_focus 默认值是 "mixed"
            instrument_focus="mixed",
        )

        orm_obj = RulePoolRepository._to_orm_model(item)

        assert orm_obj.rule_id == "rule_test_001"
        assert orm_obj.source_type == "standalone"
        assert orm_obj.rule_type == "breakout"
        assert orm_obj.instrument_focus == "mixed"  # 来自 RulePoolItem 的默认值
        assert orm_obj.initial_confidence == 0.8
        assert orm_obj.mapping_status == MappingStatus.UNMAPPED.value
        assert orm_obj.review_status == ReviewStatus.PENDING.value

    def test_from_orm_model(self):
        """测试 _from_orm_model 方法"""
        orm_obj = MagicMock(spec=RulePool)
        orm_obj.id = uuid4()
        orm_obj.rule_id = "rule_test_001"
        orm_obj.source_article_ids = ["article_001", "article_002"]
        orm_obj.source_type = "standalone"
        orm_obj.rule_type = "breakout"
        orm_obj.instrument_focus = "stock"
        orm_obj.extraction_layer = {"rule_type": "breakout", "confidence": 0.8}
        orm_obj.mapping_status = "unmapped"
        orm_obj.mapped_by = None
        orm_obj.mapped_at = None
        orm_obj.initial_confidence = 0.8
        orm_obj.validated_confidence = None
        orm_obj.review_status = "pending"
        orm_obj.reviewed_by = None
        orm_obj.reviewed_at = None
        orm_obj.backtest_triggered_at = None
        orm_obj.backtest_result = None
        orm_obj.backtest_hits = 0
        orm_obj.backtest_misses = 0
        orm_obj.backtest_samples = 0
        orm_obj.used_in_prediction = False
        orm_obj.prediction_count = 0
        orm_obj.last_used_at = None
        orm_obj.created_at = datetime.now()
        orm_obj.updated_at = datetime.now()

        item = RulePoolRepository._from_orm_model(orm_obj)

        assert item.rule_id == "rule_test_001"
        assert item.source_type == RuleSourceType.STANDALONE
        assert item.rule_type == "breakout"
        assert item.mapping_status == MappingStatus.UNMAPPED
        assert item.review_status == ReviewStatus.PENDING

    def test_from_orm_model_with_backtest(self):
        """测试 _from_orm_model 方法（带回测结果）"""
        orm_obj = MagicMock(spec=RulePool)
        orm_obj.id = uuid4()
        orm_obj.rule_id = "rule_test_002"
        orm_obj.source_article_ids = ["article_001"]
        orm_obj.source_type = "derived"
        orm_obj.rule_type = "mean_reversion"
        orm_obj.instrument_focus = "mixed"
        orm_obj.extraction_layer = {"rule_type": "mean_reversion"}
        orm_obj.mapping_status = "mapped"
        orm_obj.mapped_by = "user_001"
        orm_obj.mapped_at = datetime.now()
        orm_obj.initial_confidence = 0.7
        orm_obj.validated_confidence = 0.75
        orm_obj.review_status = "approved"
        orm_obj.reviewed_by = "reviewer_001"
        orm_obj.reviewed_at = datetime.now()
        orm_obj.backtest_triggered_at = datetime.now()
        orm_obj.backtest_result = {
            "run_id": "run_001",
            "run_at": datetime.now().isoformat(),
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
            "total_trades": 100,
            "hit_trades": 70,
            "miss_trades": 30,
            "hit_rate": 0.7,
            "avg_return": 0.05,
            "sample_count": 100,
        }
        orm_obj.backtest_hits = 70
        orm_obj.backtest_misses = 30
        orm_obj.backtest_samples = 100
        orm_obj.used_in_prediction = True
        orm_obj.prediction_count = 5
        orm_obj.last_used_at = datetime.now()
        orm_obj.created_at = datetime.now()
        orm_obj.updated_at = datetime.now()

        item = RulePoolRepository._from_orm_model(orm_obj)

        assert item.rule_id == "rule_test_002"
        assert item.source_type == RuleSourceType.DERIVED
        assert item.mapping_status == MappingStatus.MAPPED
        assert item.review_status == ReviewStatus.APPROVED
        assert item.backtest_result is not None
        assert item.backtest_result.hit_rate == 0.7
        assert item.validated_confidence == 0.75