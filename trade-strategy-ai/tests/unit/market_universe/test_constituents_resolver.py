"""constituents_resolver 测试。"""

from datetime import datetime
from src.market_universe.schemas import TopicConstituentsPayload, TopicConstituent


class TestConstituentsResolver:
    """Resolver 将 provider 原始输出转换为 TopicConstituentsPayload。"""

    def test_build_from_provider_result(self):
        """标准 provider 输出应转换为 TopicConstituentsPayload。"""
        from src.market_universe.constituents_resolver import ConstituentsResolver

        provider_payload = {
            "dataset": "topic_constituents",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "constituents": [
                {
                    "kind": "stock_sector_v2",
                    "topic_id": "ZS001",
                    "topic_name": "人工智能",
                    "topic_change_pct": 2.5,
                    "leader_symbol": "000001",
                    "leader_name": "平安银行",
                    "leader_change_pct": 3.1,
                },
                {
                    "kind": "limit_up_reason",
                    "topic_id": "ZS002",
                    "topic_name": "芯片",
                },
                {
                    "kind": "limit_up_info",
                    "symbol": "000002",
                    "name": "万科A",
                    "board_num": 5,
                },
                {
                    "kind": "lhb_list",
                    "symbol": "000003",
                    "name": "某股票",
                    "net_buy": 1000.5,
                },
                {
                    "kind": "theme_detail",
                    "topic_id": "TH001",
                    "topic_name": "新能源车",
                    "brief_intro": "新能源汽车主题",
                },
            ],
            "sources": ["stock_sector_v2", "limit_up_reason", "limit_up_info", "lhb_list", "theme_detail"],
        }

        resolver = ConstituentsResolver()
        result = resolver.build(provider_payload)

        assert isinstance(result, TopicConstituentsPayload)
        assert result.trade_date == "2026-04-23"
        assert result.slot == "17-30"
        assert len(result.constituents) == 5
        assert result.sources == ["stock_sector_v2", "limit_up_reason", "limit_up_info", "lhb_list", "theme_detail"]

        # 验证各类型 dataclass 实例
        stock_sector = result.constituents[0]
        assert isinstance(stock_sector, TopicConstituent)
        assert stock_sector.kind == "stock_sector_v2"
        assert stock_sector.topic_id == "ZS001"
        assert stock_sector.topic_change_pct == 2.5
        assert stock_sector.leader_symbol == "000001"
        assert stock_sector.leader_change_pct == 3.1

        limit_up = result.constituents[1]
        assert limit_up.kind == "limit_up_reason"

        limit_info = result.constituents[2]
        assert limit_info.kind == "limit_up_info"
        assert limit_info.symbol == "000002"
        assert limit_info.board_num == 5

        lhb = result.constituents[3]
        assert lhb.kind == "lhb_list"
        assert lhb.net_buy == 1000.5

        theme = result.constituents[4]
        assert theme.kind == "theme_detail"
        assert theme.brief_intro == "新能源汽车主题"

    def test_build_with_empty_constituents(self):
        """空 constituents 列表应正常返回空 payload。"""
        from src.market_universe.constituents_resolver import ConstituentsResolver

        provider_payload = {
            "dataset": "topic_constituents",
            "trade_date": "2026-04-23",
            "slot": "09-25",
            "constituents": [],
            "sources": [],
        }

        resolver = ConstituentsResolver()
        result = resolver.build(provider_payload)

        assert isinstance(result, TopicConstituentsPayload)
        assert result.trade_date == "2026-04-23"
        assert result.slot == "09-25"
        assert len(result.constituents) == 0

    def test_build_with_missing_optional_fields(self):
        """provider 输出缺少可选字段时应正常处理。"""
        from src.market_universe.constituents_resolver import ConstituentsResolver

        provider_payload = {
            "dataset": "topic_constituents",
            "trade_date": "2026-04-23",
            "slot": "15-00",
            "constituents": [
                {"kind": "limit_up_reason", "topic_id": "ZS001", "topic_name": "芯片"},
            ],
            "sources": ["limit_up_reason"],
        }

        resolver = ConstituentsResolver()
        result = resolver.build(provider_payload)

        assert len(result.constituents) == 1
        c = result.constituents[0]
        assert c.topic_change_pct is None
        assert c.leader_symbol is None
        assert c.board_num is None

    def test_build_includes_fetched_at_timestamp(self):
        """build 应自动填充 fetched_at 时间戳。"""
        from src.market_universe.constituents_resolver import ConstituentsResolver

        provider_payload = {
            "dataset": "topic_constituents",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "constituents": [],
            "sources": [],
        }

        resolver = ConstituentsResolver()
        before = datetime.now()
        result = resolver.build(provider_payload)
        after = datetime.now()

        assert result.fetched_at is not None
        assert before <= result.fetched_at <= after

    def test_build_preserves_all_sources(self):
        """所有数据源应全部保留在 sources 中。"""
        from src.market_universe.constituents_resolver import ConstituentsResolver

        provider_payload = {
            "dataset": "topic_constituents",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "constituents": [],
            "sources": ["stock_sector_v2", "theme_detail", "limit_up_reason", "limit_up_info", "lhb_list"],
        }

        resolver = ConstituentsResolver()
        result = resolver.build(provider_payload)

        assert len(result.sources) == 5
        assert "limit_up_reason" in result.sources
        assert "lhb_list" in result.sources

    def test_build_deduplicates_by_symbol_and_kind(self):
        """相同 kind + symbol 的重复成分应去重。"""
        from src.market_universe.constituents_resolver import ConstituentsResolver

        provider_payload = {
            "dataset": "topic_constituents",
            "trade_date": "2026-04-23",
            "slot": "17-30",
            "constituents": [
                {"kind": "limit_up_info", "symbol": "000001", "name": "股票A"},
                {"kind": "limit_up_info", "symbol": "000001", "name": "股票A"},  # 重复
                {"kind": "limit_up_info", "symbol": "000002", "name": "股票B"},  # 不同 symbol
                {"kind": "lhb_list", "symbol": "000001", "name": "股票A"},  # 不同 kind，保留
            ],
            "sources": [],
        }

        resolver = ConstituentsResolver()
        result = resolver.build(provider_payload)

        # 4个输入，3个去重（limit_up_info/000001 去重保留1个，000002 保留，lhb_list/000001 保留）
        assert len(result.constituents) == 3

    def test_build_merges_partial_payloads(self):
        """NTL-S4-TD002: FallbackProvider 返回 partial=True 时，合并多个 partial_payloads。"""
        from src.market_universe.constituents_resolver import ConstituentsResolver

        provider_payload = {
            "partial": True,
            "errors": ["provider2 timeout"],
            "partial_payloads": [
                {
                    "trade_date": "2026-04-23",
                    "slot": "17-30",
                    "constituents": [
                        {"kind": "stock_sector_v2", "topic_id": "ZS001", "topic_name": "AI"},
                    ],
                    "sources": ["kaipan"],
                },
                {
                    "trade_date": "2026-04-23",
                    "slot": "17-30",
                    "constituents": [
                        {"kind": "limit_up_info", "symbol": "000001", "name": "股票A", "board_num": 5},
                        {"kind": "stock_sector_v2", "topic_id": "ZS001", "topic_name": "AI"},  # 重复，去重
                    ],
                    "sources": ["akshare"],
                },
            ],
        }

        resolver = ConstituentsResolver()
        result = resolver.build(provider_payload)

        # 3个输入，1个重复 → 2个
        assert len(result.constituents) == 2
        # stock_sector_v2 用 topic_name，limit_up_info 用 name
        topic_names = {c.topic_name for c in result.constituents}
        names = {c.name for c in result.constituents}
        assert "AI" in topic_names
        assert "股票A" in names
        # sources 合并
        assert "kaipan" in result.sources
        assert "akshare" in result.sources