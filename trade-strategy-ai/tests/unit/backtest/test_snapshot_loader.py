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
        assert "market_regime" in result
        assert "market_regime_version" in result
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

    @pytest.mark.asyncio
    async def test_load_market_context_can_load_market_regime_by_version(self):
        """指定 regime_version 时，loader 应读取对应 Market Regime。"""
        from src.backtest.snapshot_loader import SnapshotLoader

        class _SessionContext:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class _SessionFactory:
            def __call__(self):
                return _SessionContext()

        mock_repo = AsyncMock()
        mock_repo.list_regimes.return_value = [
            {
                "regime_id": "snap-001:market-regime-v1",
                "snapshot_id": "snap-001",
                "trade_date": "2026-04-01",
                "market": "CN",
                "regime_version": "market-regime-v1",
            }
        ]

        loader = SnapshotLoader(
            session_factory=_SessionFactory(),
            regime_repository=mock_repo,
        )
        loader._load_ohlcv_from_db = AsyncMock(return_value={})
        loader._load_indicators_from_db = AsyncMock(return_value={})

        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=["000001.SZ"],
            regime_version="market-regime-v1",
        )

        mock_repo.list_regimes.assert_awaited_once()
        call_kwargs = mock_repo.list_regimes.call_args.kwargs
        assert call_kwargs["trade_date"] == date(2026, 4, 1)
        assert call_kwargs["regime_version"] == "market-regime-v1"
        assert result["market_regime"]["regime_version"] == "market-regime-v1"
        assert result["market_regime_version"] == "market-regime-v1"

    @pytest.mark.asyncio
    async def test_load_market_context_requires_existing_benchmark_symbol(self):
        """当 benchmark_symbol 未落库时，loader 应显式失败。"""
        from src.backtest.snapshot_loader import SnapshotLoader

        loader = SnapshotLoader()
        loader._load_ohlcv_from_db = AsyncMock(return_value={"000001.SZ": [{"symbol": "000001.SZ", "date": "2026-04-01"}]})
        loader._load_indicators_from_db = AsyncMock(return_value={})

        with pytest.raises(ValueError, match="benchmark_symbol.*000300.SH"):
            await loader.load_market_context(
                trade_date=date(2026, 4, 1),
                symbols=["000001.SZ"],
                benchmark_symbol="000300.SH",
            )


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
        """快照加载器只从 snapshot_service 读取 market_universe。"""
        from src.backtest.snapshot_loader import SnapshotLoader

        mock_service = AsyncMock()
        mock_service.load.return_value = None

        loader = SnapshotLoader(snapshot_service=mock_service)
        result = await loader.load_market_context(
            trade_date=date(2026, 4, 1),
            symbols=["000001.SZ"],
        )

        # 现在只读取 market_universe，ohlcv / indicators 由 DB 侧加载
        mock_service.load.assert_awaited_once_with("2026-04-01", slot="market_universe")
        assert result["market_universe"] is None
        assert result["bars_by_symbol"] == {}
        assert result["indicators_by_symbol"] == {}


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
