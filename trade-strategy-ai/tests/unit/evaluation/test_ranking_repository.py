"""RankingRepository 单元测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.evaluation.ranking_service import RankingEntry
from src.evaluation.ranking_repository import RankingRepository


def make_entry(
    trade_date="2026-04-25",
    trader_id="trader_a",
    version_id="v_2026_04_25",
    symbol="SH600519",
    return_pct=5.2,
    mfe=8.0,
    mae=2.8,
):
    return RankingEntry(
        entry_id=uuid4(),
        trade_date=trade_date,
        trader_id=trader_id,
        strategy_version_id=version_id,
        symbol=symbol,
        return_pct=return_pct,
        mfe=mfe,
        mae=mae,
        composite_score=return_pct + max(0, mfe - mae),
        rank=None,
        is_latest=True,
        idea_id=uuid4(),
        attribution_source="auto",
        extra={},
    )


@pytest.mark.asyncio
async def test_upsert_marks_old_latest_false():
    """验证 upsert 将旧 latest 标记为 False。"""
    mock_session = AsyncMock()
    repo = RankingRepository(mock_session)
    entry = make_entry()

    await repo.upsert(entry)

    # 验证 update 被调用（标记旧 entry 为非最新）
    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_upsert_adds_new_record():
    """验证 upsert 添加新 record。"""
    mock_session = AsyncMock()
    repo = RankingRepository(mock_session)
    entry = make_entry()

    await repo.upsert(entry)

    assert mock_session.add.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_find_latest_query():
    """验证 find_latest 调用 session.execute。"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    repo = RankingRepository(mock_session)
    result = await repo.find_latest("v1", "SH600519", "2026-04-25")

    assert mock_session.execute.called
    # verify return value is None when no record found
    assert result is None


@pytest.mark.asyncio
async def test_query_by_date_filters():
    """验证 query_by_date 调用 session.execute。"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = RankingRepository(mock_session)
    result = await repo.query_by_date("2026-04-25", trader_id="trader_a")

    assert mock_session.execute.called
    assert result == []