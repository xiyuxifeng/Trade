"""fetch_indicators skill 测试。"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.agents.data_agent.skills.fetch_indicators import (
    to_payload,
    supported_fields,
)


class TestSupportedFields:
    def test_returns_indicators_field(self):
        """supported_fields 包含 indicators。"""
        assert "indicators" in supported_fields()


class TestToPayload:
    def test_returns_empty_when_no_dataset(self):
        """无 dataset 时返回空。"""
        result = to_payload(symbols=["000001.SZ"], dataset=None)
        assert result == {}

    def test_returns_empty_when_wrong_dataset(self):
        """dataset 不是 indicators 时返回空。"""
        result = to_payload(symbols=["000001.SZ"], dataset="hot_topics")
        assert result == {}

    def test_returns_empty_when_no_symbols(self):
        """无 symbols 时返回空 indicators 结构。"""
        result = to_payload(symbols=[], dataset="indicators", provider=MagicMock())
        assert result == {"indicators": {}}

    def test_returns_indicators_for_symbol(self):
        """能返回标的的技术指标。"""
        mock_provider = MagicMock()
        # 模拟 fetch_ohlcv 返回 OHLCV 数据
        mock_provider.fetch_ohlcv.return_value = {
            "000001.SZ": [
                {
                    "open": 10.0,
                    "high": 10.5,
                    "low": 9.8,
                    "close": 10.2,
                    "volume": 1000000,
                    "trade_date": "2026-04-22",
                },
            ]
        }

        result = to_payload(
            symbols=["000001.SZ"],
            dataset="indicators",
            start_date=date(2026, 4, 20),
            end_date=date(2026, 4, 23),
            provider=mock_provider,
        )

        assert "indicators" in result
        assert "000001.SZ" in result["indicators"]
        indicators = result["indicators"]["000001.SZ"]
        # RSI 应有值（至少一Bar无法计算，返回 nan 或 None）
        assert "rsi" in indicators
        assert "macd_histogram" in indicators

    def test_handles_missing_ohlcv_for_symbol(self):
        """provider 没有某标的的 OHLCV 时返回空 dict。"""
        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.return_value = {}  # 无数据

        result = to_payload(
            symbols=["000001.SZ"],
            dataset="indicators",
            provider=mock_provider,
        )

        assert "indicators" in result
        assert result["indicators"] == {}

    def test_dry_run_without_provider(self):
        """无 provider 时返回空 indicators 结构。"""
        result = to_payload(symbols=["000001.SZ"], dataset="indicators", provider=None)
        assert result == {"indicators": {}}
