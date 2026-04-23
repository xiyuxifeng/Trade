"""strong_symbols_selector 测试。"""

from datetime import datetime
from src.market_universe.schemas import StrongSymbolsPayload, StrongSymbol


class TestStrongSymbolsSelector:
    """Selector 将 provider 原始输出转换为 StrongSymbolsPayload。"""

    def test_build_from_provider_result(self):
        """标准 provider 输出应转换为 StrongSymbolsPayload。"""
        from src.market_universe.strong_symbols_selector import StrongSymbolsSelector

        provider_payload = {
            "dataset": "strong_symbols",
            "trade_date": "2026-04-23",
            "slot": "17-30",
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
                {
                    "kind": "morning_bidding_list",
                    "symbol": "000003",
                    "name": "某股票",
                    "rt_change_pct": 2.1,
                    "bid_net": 5000.0,
                    "bid_turnover": 8000.0,
                    "topic_tags": "新能源",
                },
            ],
            "sources": ["strong_fengkou", "interval_stats_stock", "morning_bidding_list"],
        }

        selector = StrongSymbolsSelector()
        result = selector.build(provider_payload)

        assert isinstance(result, StrongSymbolsPayload)
        assert result.trade_date == "2026-04-23"
        assert result.slot == "17-30"
        assert len(result.symbols) == 3
        assert result.sources == ["strong_fengkou", "interval_stats_stock", "morning_bidding_list"]

        # 验证各类型 StrongSymbol dataclass 实例
        fengkou = result.symbols[0]
        assert isinstance(fengkou, StrongSymbol)
        assert fengkou.kind == "strong_fengkou"
        assert fengkou.symbol == "000001"
        assert fengkou.name == "平安银行"
        assert fengkou.strength_score == 88.0
        assert fengkou.change_pct == 5.2
        assert fengkou.main_force_buy == 15000.0
        assert fengkou.topic_tags == "AI，银行"

        interval = result.symbols[1]
        assert interval.kind == "interval_stats_stock"
        assert interval.symbol == "000002"
        assert interval.return_pct == 8.0
        assert interval.turnover_ratio == 3.5

        morning = result.symbols[2]
        assert morning.kind == "morning_bidding_list"
        assert morning.symbol == "000003"
        assert morning.rt_change_pct == 2.1
        assert morning.bid_net == 5000.0

    def test_build_with_empty_symbols(self):
        """空 symbols 列表应正常返回空 payload。"""
        from src.market_universe.strong_symbols_selector import StrongSymbolsSelector

        provider_payload = {
            "dataset": "strong_symbols",
            "trade_date": "2026-04-23",
            "slot": "09-25",
            "symbols": [],
            "sources": [],
        }

        selector = StrongSymbolsSelector()
        result = selector.build(provider_payload)

        assert isinstance(result, StrongSymbolsPayload)
        assert result.trade_date == "2026-04-23"
        assert result.slot == "09-25"
        assert len(result.symbols) == 0

    def test_build_with_missing_optional_fields(self):
        """provider 输出缺少可选字段时应正常处理。"""
        from src.market_universe.strong_symbols_selector import StrongSymbolsSelector

        provider_payload = {
            "dataset": "strong_symbols",
            "trade_date": "2026-04-23",
            "slot": "15-00",
            "symbols": [
                {"kind": "strong_fengkou", "symbol": "000001", "name": "平安银行"},
            ],
            "sources": ["strong_fengkou"],
        }

        selector = StrongSymbolsSelector()
        result = selector.build(provider_payload)

        assert len(result.symbols) == 1
        s = result.symbols[0]
        assert s.strength_score is None
        assert s.change_pct is None
        assert s.topic_tags is None

    def test_build_includes_fetched_at_timestamp(self):
        """build 应自动填充 fetched_at 时间戳。"""
        from src.market_universe.strong_symbols_selector import StrongSymbolsSelector

        provider_payload = {
            "dataset": "strong_symbols",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "symbols": [],
            "sources": [],
        }

        selector = StrongSymbolsSelector()
        before = datetime.now()
        result = selector.build(provider_payload)
        after = datetime.now()

        assert result.fetched_at is not None
        assert before <= result.fetched_at <= after

    def test_build_preserves_all_sources(self):
        """所有数据源应全部保留在 sources 中。"""
        from src.market_universe.strong_symbols_selector import StrongSymbolsSelector

        provider_payload = {
            "dataset": "strong_symbols",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "symbols": [],
            "sources": ["strong_fengkou", "interval_stats_stock", "morning_bidding_list"],
        }

        selector = StrongSymbolsSelector()
        result = selector.build(provider_payload)

        assert len(result.sources) == 3
        assert "interval_stats_stock" in result.sources

    def test_build_deduplicates_by_symbol_and_kind(self):
        """相同 kind + symbol 的重复标的应去重。"""
        from src.market_universe.strong_symbols_selector import StrongSymbolsSelector

        provider_payload = {
            "dataset": "strong_symbols",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "symbols": [
                {"kind": "strong_fengkou", "symbol": "000001", "name": "股票A"},
                {"kind": "strong_fengkou", "symbol": "000001", "name": "股票A"},  # 重复
                {"kind": "strong_fengkou", "symbol": "000002", "name": "股票B"},  # 不同 symbol
                {"kind": "interval_stats_stock", "symbol": "000001", "name": "股票A"},  # 不同 kind，保留
            ],
            "sources": [],
        }

        selector = StrongSymbolsSelector()
        result = selector.build(provider_payload)

        # 4个输入，3个去重（strong_fengkou/000001 去重保留1个，000002 保留，interval_stats_stock/000001 保留）
        assert len(result.symbols) == 3