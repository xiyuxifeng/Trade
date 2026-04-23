"""fetch_strong_symbols skill 测试。"""

from datetime import date
from src.agents.data_agent.skills.fetch_strong_symbols import supported_fields, to_payload


class TestFetchStrongSymbolsSkill:
    """测试强势池拉取 skill。"""

    def test_supported_fields_returns_strong_symbols(self):
        """supported_fields 应返回包含 strong_symbols 的列表。"""
        fields = supported_fields()
        assert "strong_symbols" in fields

    def test_to_payload_returns_empty_when_no_dataset(self):
        """dataset 不是 strong_symbols 时返回空 dict。"""
        result = to_payload(dataset=None)
        assert result == {}

        result = to_payload(dataset="last_price")
        assert result == {}

    def test_to_payload_returns_empty_when_no_provider(self):
        """没有 provider 时返回 None 的 strong_symbols。"""
        result = to_payload(dataset="strong_symbols", provider=None)
        assert result == {"strong_symbols": None}

    def test_to_payload_with_mock_provider(self):
        """有 provider 时返回构建后的强势池数据。"""
        from src.agents.data_agent.skills.fetch_strong_symbols import to_payload

        mock_provider = _MockStrongSymbolsProvider()

        result = to_payload(
            dataset="strong_symbols",
            snapshot_date=date(2026, 4, 23),
            slot="17-30",
            provider=mock_provider,
        )

        assert "strong_symbols" in result
        assert result["strong_symbols"] is not None
        ss = result["strong_symbols"]
        assert ss["trade_date"] == "2026-04-23"
        assert ss["slot"] == "17-30"
        assert len(ss["symbols"]) == 2
        assert ss["symbols"][0]["name"] == "平安银行"
        assert ss["symbols"][0]["kind"] == "strong_fengkou"
        assert "strong_fengkou" in ss["sources"]

    def test_to_payload_handles_provider_exception(self):
        """provider 抛出异常时返回 None。"""
        bad_provider = _BadProvider()

        result = to_payload(
            dataset="strong_symbols",
            snapshot_date=date(2026, 4, 23),
            provider=bad_provider,
        )

        assert result == {"strong_symbols": None}


class _MockStrongSymbolsProvider:
    """模拟 StrongSymbolsProvider，用于测试。"""

    def fetch_strong_symbols(self, *, trade_date, slot, **kwargs):
        return {
            "dataset": "strong_symbols",
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "symbols": [
                {
                    "kind": "strong_fengkou",
                    "symbol": "000001",
                    "name": "平安银行",
                    "strength_score": 88.0,
                    "change_pct": 5.2,
                    "turnover": 30000.0,
                    "main_force_buy": 15000.0,
                    "main_force_sell": 10000.0,
                    "topic_tags": "AI，银行",
                },
                {
                    "kind": "interval_stats_stock",
                    "symbol": "000002",
                    "name": "万科A",
                    "return_pct": 8.0,
                    "net_inflow": 20000.0,
                    "turnover_ratio": 3.5,
                    "topic_tags": "房地产",
                },
            ],
            "sources": ["strong_fengkou", "interval_stats_stock", "morning_bidding_list"],
        }


class _BadProvider:
    """模拟抛出异常的 provider。"""

    def fetch_strong_symbols(self, **kwargs):
        raise RuntimeError("provider error")