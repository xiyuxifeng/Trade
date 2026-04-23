"""fetch_ohlcv skill 测试。"""

from datetime import date
from src.agents.data_agent.skills.fetch_ohlcv import supported_fields, to_payload


class TestFetchOhlcvSkill:
    """测试 ohlcv 拉取 skill。"""

    def test_supported_fields_returns_ohlcv(self):
        """supported_fields 应返回包含 ohlcv_1d 的列表。"""
        fields = supported_fields()
        assert "ohlcv_1d" in fields

    def test_to_payload_returns_empty_when_no_dataset(self):
        """dataset 不是 ohlcv_1d 时返回空 dict。"""
        result = to_payload(symbols=[], dataset=None)
        assert result == {}

        result = to_payload(symbols=[], dataset="hot_topics")
        assert result == {}

    def test_to_payload_returns_empty_list_when_no_provider(self):
        """没有 provider 时返回空列表。"""
        result = to_payload(symbols=["000001"], dataset="ohlcv_1d", provider=None)
        assert result == {"ohlcv_1d": {}}

    def test_to_payload_with_mock_provider(self):
        """有 provider 时返回 ohlcv 数据。"""
        from src.agents.data_agent.skills.fetch_ohlcv import to_payload

        mock_provider = _MockMarketDataProvider()

        result = to_payload(
            symbols=["000001"],
            dataset="ohlcv_1d",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 23),
            provider=mock_provider,
        )

        assert "ohlcv_1d" in result
        assert result["ohlcv_1d"] is not None
        ohlcv = result["ohlcv_1d"]
        assert "000001" in ohlcv
        bars = ohlcv["000001"]["bars"]
        assert len(bars) == 2
        assert bars[0]["close"] == 10.5

    def test_to_payload_handles_provider_exception(self):
        """provider 抛出异常时返回空。"""
        bad_provider = _BadProvider()

        result = to_payload(
            symbols=["000001"],
            dataset="ohlcv_1d",
            provider=bad_provider,
        )

        assert result == {"ohlcv_1d": {}}

    def test_to_payload_multiple_symbols(self):
        """支持多个 symbol 一起返回。"""
        from src.agents.data_agent.skills.fetch_ohlcv import to_payload

        mock_provider = _MockMarketDataProvider()

        result = to_payload(
            symbols=["000001", "000002"],
            dataset="ohlcv_1d",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 23),
            provider=mock_provider,
        )

        ohlcv = result["ohlcv_1d"]
        assert "000001" in ohlcv
        assert "000002" in ohlcv


class _MockMarketDataProvider:
    """模拟 MarketDataProvider，用于测试。"""

    def fetch_ohlcv(self, *, symbols, start_date, end_date, **kwargs):
        return {
            "000001": {
                "symbol": "000001",
                "market_kind": "stock",
                "timeframe": "1d",
                "bars": [
                    {"date": "2026-04-01", "open": 10.0, "high": 10.8, "low": 9.9, "close": 10.5, "volume": 1000000, "turnover": 10500000},
                    {"date": "2026-04-02", "open": 10.5, "high": 11.0, "low": 10.3, "close": 10.8, "volume": 1200000, "turnover": 12960000},
                ],
            },
            "000002": {
                "symbol": "000002",
                "market_kind": "stock",
                "timeframe": "1d",
                "bars": [
                    {"date": "2026-04-01", "open": 20.0, "high": 21.0, "low": 19.8, "close": 20.5, "volume": 800000, "turnover": 16400000},
                ],
            },
        }


class _BadProvider:
    """模拟抛出异常的 provider。"""

    def fetch_ohlcv(self, **kwargs):
        raise RuntimeError("provider error")