"""S7-003b: Repository version_type / parent_version_id 映射测试"""
from datetime import date

import pytest

from src.strategy_library.repository import StrategyLibraryRepository, _get_version_type
from src.strategy_library.schemas import (
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,
)


class TestGetVersionType:
    """测试 _get_version_type 辅助函数。"""

    def test_valid_manual_string(self):
        """manual 字符串返回 StrategyVersionType.manual。"""
        class FakeOrm:
            version_type = "manual"
        assert _get_version_type(FakeOrm()) == StrategyVersionType.manual

    def test_valid_candidate_string(self):
        """candidate 字符串返回 StrategyVersionType.candidate。"""
        class FakeOrm:
            version_type = "candidate"
        assert _get_version_type(FakeOrm()) == StrategyVersionType.candidate

    def test_none_defaults_to_manual(self):
        """version_type 为 None 时默认 manual。"""
        class FakeOrm:
            version_type = None
        assert _get_version_type(FakeOrm()) == StrategyVersionType.manual

    def test_non_string_defaults_to_manual(self):
        """version_type 为非字符串类型（如 MagicMock）时默认 manual。"""
        from unittest.mock import MagicMock

        class FakeOrm:
            version_type = MagicMock()
        assert _get_version_type(FakeOrm()) == StrategyVersionType.manual


class TestRepositoryVersionTypeMapping:
    """测试 _to_orm_model 和 _from_orm_model 对新列的映射。"""

    def test_to_orm_model_sets_version_type_and_parent(self):
        """验证写入时 version_type 和 parent_version_id 正确映射。"""
        version = StrategyVersion(
            version_id="test_v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 25),
            status=StrategyVersionStatus.draft,
            version_type=StrategyVersionType.candidate,
            parent_version_id="trader_a_2026-04-25_released",
            recommendations=[],
            rules_snapshot=[],
        )
        orm_obj = StrategyLibraryRepository._to_orm_model(version)
        assert orm_obj.version_type == "candidate"
        assert orm_obj.parent_version_id == "trader_a_2026-04-25_released"

    def test_to_orm_model_manual_version(self):
        """manual 类型版本 version_type 为 manual。"""
        version = StrategyVersion(
            version_id="test_v1",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 25),
            status=StrategyVersionStatus.released,
            version_type=StrategyVersionType.manual,
            parent_version_id=None,
            recommendations=[],
            rules_snapshot=[],
        )
        orm_obj = StrategyLibraryRepository._to_orm_model(version)
        assert orm_obj.version_type == "manual"
        assert orm_obj.parent_version_id is None

    def test_from_orm_model_reads_version_type_and_parent(self):
        """验证读取时 version_type 和 parent_version_id 正确映射。"""
        from src.models.trader_strategy_version import TraderStrategyVersion

        orm_obj = TraderStrategyVersion(
            trader_id="trader_a",
            strategy_date=date(2026, 4, 25),
            version_name="test_candidate",
            status="draft",
            version_type="candidate",
            parent_version_id="trader_a_2026-04-25_released",
            source_article_ids=[],
            evidence_refs=[],
            strategy_payload={},
        )
        version = StrategyLibraryRepository._from_orm_model(orm_obj)
        assert version.version_type == StrategyVersionType.candidate
        assert version.parent_version_id == "trader_a_2026-04-25_released"

    def test_from_orm_model_fallback_for_missing_columns(self):
        """验证旧记录（无新列）兼容：默认 manual + None。"""
        from src.models.trader_strategy_version import TraderStrategyVersion

        orm_obj = TraderStrategyVersion(
            trader_id="trader_a",
            strategy_date=date(2026, 4, 25),
            version_name="legacy_v1",
            status="released",
            source_article_ids=[],
            evidence_refs=[],
            strategy_payload={},
        )
        version = StrategyLibraryRepository._from_orm_model(orm_obj)
        assert version.version_type == StrategyVersionType.manual
        assert version.parent_version_id is None
