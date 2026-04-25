"""RankingService 核心逻辑单元测试。"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.evaluation.ranking_service import (
    RankingEntry,
    RankingService,
    _compute_composite,
    _sort_key,
)


# -------------------------------------------------
# 辅助函数测试
# -------------------------------------------------

def test_compute_composite_with_return_pct():
    assert _compute_composite(5.0, 8.0, 2.0) == 11.0  # 5 + (8-2)


def test_compute_composite_with_none_return():
    assert _compute_composite(None, 8.0, 2.0) is None


def test_compute_composite_negative_odds():
    """赔率为负时取 0。"""
    assert _compute_composite(5.0, 2.0, 8.0) == 5.0  # max(0, 2-8) = 0


def test_sort_key_with_return_pct():
    """有 return_pct 的 entry 排在前面。"""
    entry = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600519",
        return_pct=5.0, mfe=8.0, mae=2.0,
        composite_score=11.0, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    key = _sort_key(entry)
    assert key[0] == 0  # 有 return_pct


def test_sort_key_without_return_pct():
    """return_pct 为 None 的 entry 排在后面。"""
    entry = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600519",
        return_pct=None, mfe=8.0, mae=2.0,
        composite_score=None, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    key = _sort_key(entry)
    assert key[0] == 1  # None 排在后面


def test_sort_key_odds_sorting():
    """return_pct 相同时，按赔率排序。"""
    entry1 = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600519",
        return_pct=5.0, mfe=10.0, mae=2.0,  # 赔率 8
        composite_score=13.0, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    entry2 = RankingEntry(
        entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
        strategy_version_id="v1", symbol="SH600000",
        return_pct=5.0, mfe=3.0, mae=1.0,  # 赔率 2
        composite_score=7.0, rank=None, is_latest=True,
        idea_id=None, attribution_source="auto",
    )
    key1 = _sort_key(entry1)
    key2 = _sort_key(entry2)
    # 两者 return_pct 相同(5.0)，key[1] 相同，key[2] 为 odds，entry1 的赔率更高，应排前面
    # key: (0, -5.0, -odds)
    assert key1 < key2  # entry1 的 odds(8) > entry2 的 odds(2)，key 更小，排前面


# -------------------------------------------------
# RankingEntry.from_record 测试
# -------------------------------------------------

def test_ranking_entry_from_record():
    """验证从 ORM record 正确构建 RankingEntry。"""
    mock_record = MagicMock()
    mock_record.entry_id = uuid4()
    mock_record.trade_date = "2026-04-25"
    mock_record.trader_id = "trader_a"
    mock_record.strategy_version_id = "v1"
    mock_record.symbol = "SH600519"
    mock_record.return_pct = 5.0
    mock_record.mfe = 8.0
    mock_record.mae = 2.0
    mock_record.composite_score = 11.0
    mock_record.rank = 1
    mock_record.is_latest = True
    mock_record.idea_id = uuid4()
    mock_record.attribution_source = "llm_corrected"
    mock_record.extra = {}

    entry = RankingEntry.from_record(mock_record)

    assert entry.trade_date == "2026-04-25"
    assert entry.trader_id == "trader_a"
    assert entry.return_pct == 5.0
    assert entry.rank == 1
    assert entry.is_latest is True
    assert entry.attribution_source == "llm_corrected"


# -------------------------------------------------
# 排序集成测试（mock ranking service）
# -------------------------------------------------

def test_sorting_integration():
    """验证多级排序逻辑。"""
    entries = [
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S1",
            return_pct=None, mfe=5.0, mae=1.0,  # 赔率 4
            composite_score=None, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S2",
            return_pct=5.0, mfe=8.0, mae=2.0,  # 赔率 6
            composite_score=11.0, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S3",
            return_pct=10.0, mfe=3.0, mae=1.0,  # 赔率 2
            composite_score=12.0, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
        RankingEntry(
            entry_id=uuid4(), trade_date="2026-04-25", trader_id="trader_a",
            strategy_version_id="v1", symbol="S4",
            return_pct=None, mfe=2.0, mae=1.0,  # 赔率 1
            composite_score=None, rank=None, is_latest=True,
            idea_id=None, attribution_source="auto",
        ),
    ]

    sorted_entries = sorted(entries, key=_sort_key)

    # 预期顺序：S3(10.0) > S2(5.0) > S1(赔率4) > S4(赔率1)
    assert sorted_entries[0].symbol == "S3"
    assert sorted_entries[1].symbol == "S2"
    assert sorted_entries[2].symbol == "S1"  # None 排后面，但组内按赔率
    assert sorted_entries[3].symbol == "S4"


# -------------------------------------------------
# RankingService.add_entry 集成测试
# -------------------------------------------------

@pytest.mark.asyncio
async def test_add_entry_creates_entry():
    """验证 add_entry 正确构建并持久化 entry。"""
    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    service = RankingService(mock_session)
    service._repo = mock_repo

    # Mock evidence_pack
    mock_pack = MagicMock()
    mock_pack.trade_date = "2026-04-25"
    mock_pack.strategy_version_id = "v1"
    mock_pack.trade_idea = MagicMock()
    mock_pack.trade_idea.symbol = "SH600519"
    mock_pack.trade_idea.trader_id = "trader_a"
    mock_pack.signal_context = MagicMock()
    mock_pack.signal_context.trader_id = "trader_a"

    # Mock postmortem
    mock_postmortem = MagicMock()
    mock_postmortem.idea_id = uuid4()
    mock_postmortem.return_pct = 5.0
    mock_postmortem.mfe = 8.0
    mock_postmortem.mae = 2.0
    mock_postmortem.attribution_source = "auto"

    # Mock upsert result
    mock_record = MagicMock()
    mock_record.entry_id = uuid4()
    mock_record.trade_date = "2026-04-25"
    mock_record.trader_id = "trader_a"
    mock_record.strategy_version_id = "v1"
    mock_record.symbol = "SH600519"
    mock_record.return_pct = 5.0
    mock_record.mfe = 8.0
    mock_record.mae = 2.0
    mock_record.composite_score = 11.0
    mock_record.rank = None
    mock_record.is_latest = True
    mock_record.idea_id = mock_postmortem.idea_id
    mock_record.attribution_source = "auto"
    mock_record.extra = {}
    mock_repo.upsert.return_value = mock_record

    result = await service.add_entry(mock_postmortem, mock_pack)

    assert mock_repo.upsert.called
    assert result.trade_date == "2026-04-25"
    assert result.trader_id == "trader_a"
    assert result.symbol == "SH600519"
    assert result.return_pct == 5.0


@pytest.mark.asyncio
async def test_add_entry_from_metrics_creates_entry():
    """直接传入 mfe/mae/return_pct，生成 RankingEntry（NTL-S5-011）"""
    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    service = RankingService(mock_session)
    service._repo = mock_repo

    # Mock evidence_pack
    mock_pack = MagicMock()
    mock_pack.trade_date = "2026-04-25"
    mock_pack.strategy_version_id = "v1"
    mock_pack.trade_idea = MagicMock()
    mock_pack.trade_idea.symbol = "AAPL"
    mock_pack.trade_idea.trader_id = "trader_001"
    mock_pack.signal_context = None

    # Mock upsert result
    mock_record = MagicMock()
    mock_record.entry_id = uuid4()
    mock_record.trade_date = "2026-04-25"
    mock_record.trader_id = "trader_001"
    mock_record.strategy_version_id = "v1"
    mock_record.symbol = "AAPL"
    mock_record.return_pct = 3.333
    mock_record.mfe = 10.0
    mock_record.mae = 2.0
    mock_record.composite_score = 11.333
    mock_record.rank = None
    mock_record.is_latest = True
    mock_record.idea_id = None
    mock_record.attribution_source = "auto"
    mock_record.extra = {}
    mock_repo.upsert.return_value = mock_record

    result = await service.add_entry_from_metrics(
        evidence_pack=mock_pack,
        mfe=10.0,
        mae=2.0,
        return_pct=3.333,
    )

    assert mock_repo.upsert.called
    assert result.mfe == 10.0
    assert result.mae == 2.0
    assert result.return_pct == pytest.approx(3.333)
    assert result.trader_id == "trader_001"
    assert result.symbol == "AAPL"
    assert result.attribution_source == "auto"  # 固定为 auto
    assert result.is_latest is True


@pytest.mark.asyncio
async def test_generate_ranking_and_save_creates_file(tmp_path):
    """generate_ranking_and_save 生成 nested + flat 视图并写入文件（NTL-S5-011）"""
    from pathlib import Path
    import json

    mock_session = AsyncMock()
    mock_repo = AsyncMock()
    output_dir = tmp_path / "output"
    service = RankingService(mock_session, output_dir=output_dir)
    service._repo = mock_repo

    # Mock query_by_date 返回空列表（generate_ranking 正常返回空 groups）
    mock_repo.query_by_date = AsyncMock(return_value=[])

    result = await service.generate_ranking_and_save(trade_date="2026-04-25")

    # 验证返回值包含 nested 和 flat
    assert "nested" in result
    assert "flat" in result
    assert result["trade_date"] == "2026-04-25"
    assert "generated_at" in result

    # 验证文件写入
    ranking_file = output_dir / "rankings" / "2026-04-25.json"
    assert ranking_file.exists()
    with open(ranking_file) as f:
        data = json.load(f)
    assert data["trade_date"] == "2026-04-25"
    assert "nested" in data
    assert "flat" in data