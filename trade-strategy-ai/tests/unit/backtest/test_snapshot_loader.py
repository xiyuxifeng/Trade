"""NTL-S6-006: 快照加载器单元测试"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


class TestSnapshotLoaderInterface:
    """SnapshotLoader 接口测试"""

    def test_snapshot_loader_has_load_market_context_method(self):
        """loader 必须有 load_market_context 方法"""
        from src.backtest.snapshot_loader import SnapshotLoader

        loader = SnapshotLoader()
        assert hasattr(loader, "load_market_context")
        assert callable(loader.load_market_context)

    def test_snapshot_loader_has_load_version_for_date_method(self):
        """loader 必须有 load_version_for_date 方法"""
        from src.backtest.snapshot_loader import SnapshotLoader

        loader = SnapshotLoader()
        assert hasattr(loader, "load_version_for_date")
        assert callable(loader.load_version_for_date)

    @pytest.mark.asyncio
    async def test_load_market_context_returns_market_context_dict(self):
        """load_market_context 应返回包含必要 key 的字典"""
        from src.backtest.snapshot_loader import SnapshotLoader

        loader = SnapshotLoader()
        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=["000001.SZ"],
        )
        assert isinstance(result, dict)
        assert "trade_date" in result
        assert "bars_by_symbol" in result
        assert "indicators_by_symbol" in result
        assert "market_universe" in result
        assert "topic_snapshot" in result
        assert "source_refs" in result

    @pytest.mark.asyncio
    async def test_load_market_context_accepts_empty_symbols_list(self):
        """symbols 可以为空列表（表示全部标的）"""
        from src.backtest.snapshot_loader import SnapshotLoader

        loader = SnapshotLoader()
        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=[],
        )
        assert result["bars_by_symbol"] == {}


class TestSnapshotLoaderWithMockedService:
    """使用 mock 服务的 SnapshotLoader 集成测试"""

    @pytest.mark.asyncio
    async def test_load_market_context_with_mocked_snapshot_service(self):
        """当 snapshot_service 返回数据时，loader 应透传"""
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_service = AsyncMock()
        mock_service.load.return_value = {
            "hot_topics": ["AI", "新能源"],
            "strong_symbols": ["000001.SZ"],
        }

        loader = SnapshotLoader(snapshot_service=mock_service)
        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=["000001.SZ"],
        )

        # 应调用 snapshot_service.load
        mock_service.load.assert_called()
        # 返回值应包含 market_universe
        assert result["market_universe"] is not None

    @pytest.mark.asyncio
    async def test_load_market_context_marks_compatibility_fallback(self):
        """当使用 EvidencePack 补洞时，应标记 compatibility_fallback"""
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_service = AsyncMock()
        mock_service.load.return_value = None  # 快照不存在

        loader = SnapshotLoader(
            snapshot_service=mock_service,
            use_evidence_pack_fallback=True,
        )
        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=["000001.SZ"],
        )

        assert result.get("compatibility_fallback") is True

    @pytest.mark.asyncio
    async def test_load_version_for_date_returns_strategy_version(self):
        """load_version_for_date 应返回 StrategyVersion 或 None"""
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_repo = AsyncMock()
        mock_repo.get_released_by_trader_and_date.return_value = []

        loader = SnapshotLoader(strategy_repo=mock_repo)
        result = await loader.load_version_for_date(
            trader_id="trader_a",
            trade_date=date(2026, 4, 1),
        )

        # 返回 None 表示无版本
        assert result is None or hasattr(result, "version_id")

    @pytest.mark.asyncio
    async def test_load_version_for_date_calls_repo(self):
        """loader 应调用 strategy_repo 查询"""
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_repo = AsyncMock()
        mock_repo.get_released_by_trader_and_date.return_value = []

        loader = SnapshotLoader(strategy_repo=mock_repo)
        await loader.load_version_for_date(
            trader_id="trader_a",
            trade_date=date(2026, 4, 1),
        )

        mock_repo.get_released_by_trader_and_date.assert_called_once()


    @pytest.mark.asyncio
    async def test_load_market_context_loads_bars_from_snapshot_service(self):
        """当 snapshot_service 返回 bars 时，loader 应填充 bars_by_symbol"""
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_service = AsyncMock()
        # snapshot_service.load 返回 bars 数据（包含 symbol 字段）
        mock_service.load.side_effect = [
            None,  # market_universe slot
            [  # ohlcv_1d slot
                {
                    "symbol": "000001.SZ",
                    "date": "2026-04-01",
                    "open": 10.0,
                    "high": 10.5,
                    "low": 9.8,
                    "close": 10.2,
                    "volume": 1000000,
                },
                {
                    "symbol": "000001.SZ",
                    "date": "2026-04-02",
                    "open": 10.2,
                    "high": 10.8,
                    "low": 10.1,
                    "close": 10.5,
                    "volume": 1100000,
                },
            ],
        ]

        loader = SnapshotLoader(snapshot_service=mock_service)
        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=["000001.SZ"],
        )

        # snapshot_service.load 应被调用两次：market_universe 和 ohlcv_1d
        assert mock_service.load.call_count == 2
        # 第二次调用应该是 ohlcv_1d slot
        calls = mock_service.load.call_args_list
        assert calls[1][1]["slot"] == "ohlcv_1d"
        # bars_by_symbol 应被正确填充（按 symbol 归类）
        bars = result.get("bars_by_symbol", {})
        assert "000001.SZ" in bars
        assert len(bars["000001.SZ"]) == 2


class TestSnapshotLoaderNoRealTime:
    """验证 SnapshotLoader 不调用实时接口"""

    @pytest.mark.asyncio
    async def test_load_market_context_does_not_call_live_provider(self):
        """use_snapshot_only=True 时不应调用实时 provider"""
        from src.backtest.snapshot_loader import SnapshotLoader

        # 不注入任何 service，只验证 stub 不抛异常
        loader = SnapshotLoader(use_snapshot_only=True)
        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=["000001.SZ"],
        )

        # stub 应返回空结构，不调用实时接口
        assert result["bars_by_symbol"] == {}
        assert result["market_universe"] is None
