"""strategy_library repository 测试。"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.strategy_library.repository import StrategyLibraryRepository
from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
)


class TestStrategyLibraryRepository:
    """策略库 repository 测试。"""

    def test_schema_to_orm_converts_all_fields(self):
        """Schema 到 ORM 的转换包含所有字段。"""
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
                    target_price=12.0,
                    stop_loss_price=9.5,
                    rationale="AI题材",
                    evidence_refs=["art-1"],
                ),
            ],
            source_article_ids=["article-1"],
            evidence_refs=["evidence-1"],
            notes="测试版本",
            released_at=datetime(2026, 4, 23, 10, 0, 0),
            rules_snapshot=[{"rule_id": "r1", "condition": "ma5_cross"}],
        )
        orm_obj = StrategyLibraryRepository._to_orm_model(version)
        assert orm_obj.trader_id == "trader-001"
        assert orm_obj.strategy_date == date(2026, 4, 23)
        assert orm_obj.status == "released"
        assert len(orm_obj.strategy_payload["recommendations"]) == 1
        assert orm_obj.strategy_payload["recommendations"][0]["symbol"] == "000001"
        assert orm_obj.strategy_payload["rules_snapshot"] == [{"rule_id": "r1", "condition": "ma5_cross"}]

    def test_orm_to_schema_converts_all_fields(self):
        """ORM 到 Schema 的转换包含所有字段。"""
        orm_obj = MagicMock()
        orm_obj.trader_id = "trader-001"
        orm_obj.strategy_date = date(2026, 4, 23)
        orm_obj.version_name = "ver-001"
        orm_obj.status = "released"
        orm_obj.released_at = datetime(2026, 4, 23, 10, 0, 0)
        orm_obj.source_article_ids = ["article-1"]
        orm_obj.evidence_refs = ["evidence-1"]
        orm_obj.notes = "测试版本"
        orm_obj.strategy_payload = {
            "recommendations": [
                {
                    "symbol": "000001",
                    "decision": "buy",
                    "confidence": 0.8,
                    "entry_price": 10.5,
                    "target_price": 12.0,
                    "stop_loss_price": 9.5,
                    "rationale": "AI题材",
                    "evidence_refs": ["art-1"],
                },
            ],
            "rules_snapshot": [{"rule_id": "r1", "condition": "ma5_cross"}],
        }
        schema_obj = StrategyLibraryRepository._from_orm_model(orm_obj)
        assert schema_obj.trader_id == "trader-001"
        assert schema_obj.strategy_date == date(2026, 4, 23)
        assert schema_obj.status == StrategyVersionStatus.released
        assert len(schema_obj.recommendations) == 1
        assert schema_obj.recommendations[0].symbol == "000001"
        assert schema_obj.notes == "测试版本"
        assert schema_obj.rules_snapshot == [{"rule_id": "r1", "condition": "ma5_cross"}]

    @pytest.mark.asyncio
    async def test_get_by_trader_and_date_returns_versions(self):
        """能按 trader 和日期读取策略版本。"""
        repo = StrategyLibraryRepository()
        mock_session = AsyncMock()
        mock_orm = MagicMock()
        mock_orm.trader_id = "trader-001"
        mock_orm.strategy_date = date(2026, 4, 23)
        mock_orm.version_name = "ver-001"
        mock_orm.status = "draft"
        mock_orm.released_at = None
        mock_orm.source_article_ids = []
        mock_orm.evidence_refs = []
        mock_orm.notes = None
        mock_orm.strategy_payload = {"recommendations": []}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_orm]
        mock_session.execute.return_value = mock_result

        results = await repo.get_by_trader_and_date(mock_session, "trader-001", date(2026, 4, 23))
        assert len(results) == 1
        assert results[0].version_id == "ver-001"
        assert results[0].trader_id == "trader-001"
        assert results[0].strategy_date == date(2026, 4, 23)
        assert results[0].status == StrategyVersionStatus.draft

    @pytest.mark.asyncio
    async def test_get_by_trader_and_date_empty(self):
        """无版本时返回空列表。"""
        repo = StrategyLibraryRepository()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repo.get_by_trader_and_date(mock_session, "trader-999", date(2026, 4, 23))
        assert results == []

    @pytest.mark.asyncio
    async def test_get_released_by_trader_and_date(self):
        """能筛选 released 状态的版本。"""
        repo = StrategyLibraryRepository()
        mock_session = AsyncMock()
        mock_orm = MagicMock()
        mock_orm.trader_id = "trader-001"
        mock_orm.strategy_date = date(2026, 4, 23)
        mock_orm.version_name = "ver-002"
        mock_orm.status = "released"
        mock_orm.released_at = datetime(2026, 4, 23, 10, 0, 0)
        mock_orm.source_article_ids = []
        mock_orm.evidence_refs = []
        mock_orm.notes = None
        mock_orm.strategy_payload = {"recommendations": []}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_orm]
        mock_session.execute.return_value = mock_result

        results = await repo.get_released_by_trader_and_date(mock_session, "trader-001", date(2026, 4, 23))
        assert len(results) == 1
        assert results[0].version_id == "ver-002"
        assert results[0].status == StrategyVersionStatus.released

    @pytest.mark.asyncio
    async def test_save_creates_new_version(self):
        """保存新版本。"""
        repo = StrategyLibraryRepository()
        mock_session = AsyncMock()
        version = StrategyVersion(
            version_id="ver-new",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.draft,
            recommendations=[
                StrategyRecommendation(
                    symbol="000001",
                    decision="buy",
                    confidence=0.8,
                ),
            ],
        )
        # 模拟没有找到现有版本
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.add = MagicMock()

        await repo.save(mock_session, version)
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_updates_existing_version(self):
        """保存已存在的版本（更新）。"""
        repo = StrategyLibraryRepository()
        mock_session = AsyncMock()
        version = StrategyVersion(
            version_id="ver-existing",
            trader_id="trader-001",
            strategy_date=date(2026, 4, 23),
            status=StrategyVersionStatus.released,
            recommendations=[],
        )
        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_session.execute.return_value = mock_result

        await repo.save(mock_session, version)
        mock_session.add.assert_not_called()
        assert mock_existing.status == "released"
