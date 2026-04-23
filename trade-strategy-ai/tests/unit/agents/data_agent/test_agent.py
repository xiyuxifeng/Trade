"""DataAgent capability router 测试。"""

from datetime import date
from src.schemas.contracts import DataRequest


class TestDataAgentRouter:
    """测试 DataAgent 统一路由能力。"""

    def test_data_agent_routes_hot_topics(self):
        """请求 dataset=hot_topics 时路由到 fetch_hot_topics skill。"""
        from src.agents.data_agent.agent import DataAgent

        config = _MockConfig()
        agent = DataAgent(config=config)

        # 用 mock provider 注入
        mock_provider = _MockHotTopicsProvider()
        agent._providers[agent._PROVIDER_KEY] = mock_provider

        req = DataRequest(
            trader_id="test",
            fields=["hot_topics"],
            dataset="hot_topics",
            snapshot_date=date(2026, 4, 23),
        )

        import asyncio
        result = asyncio.run(agent.handle(req))

        assert result.status.value == "ok"
        assert "hot_topics" in result.payload
        assert result.payload["hot_topics"] is not None
        assert result.payload["hot_topics"]["trade_date"] == "2026-04-23"

    def test_data_agent_returns_capability_missing_for_unknown_dataset(self):
        """未知 dataset 返回 capability_missing。"""
        from src.agents.data_agent.agent import DataAgent

        config = _MockConfig()
        agent = DataAgent(config=config)

        req = DataRequest(
            trader_id="test",
            fields=[],
            dataset="unknown_dataset",
        )

        import asyncio
        result = asyncio.run(agent.handle(req))

        assert result.status.value == "capability_missing"
        assert "unknown_dataset" in result.missing_capabilities

    def test_data_agent_routes_topic_constituents(self):
        """dataset=topic_constituents 路由正确。"""
        from src.agents.data_agent.agent import DataAgent

        config = _MockConfig()
        agent = DataAgent(config=config)

        mock_provider = _MockTopicConstituentsProvider()
        agent._providers[agent._PROVIDER_KEY] = mock_provider

        req = DataRequest(
            trader_id="test",
            fields=["topic_constituents"],
            dataset="topic_constituents",
            snapshot_date=date(2026, 4, 23),
        )

        import asyncio
        result = asyncio.run(agent.handle(req))

        assert result.status.value == "ok"
        assert "topic_constituents" in result.payload

    def test_data_agent_routes_strong_symbols(self):
        """dataset=strong_symbols 路由正确。"""
        from src.agents.data_agent.agent import DataAgent

        config = _MockConfig()
        agent = DataAgent(config=config)

        mock_provider = _MockStrongSymbolsProvider()
        agent._providers[agent._PROVIDER_KEY] = mock_provider

        req = DataRequest(
            trader_id="test",
            fields=["strong_symbols"],
            dataset="strong_symbols",
            snapshot_date=date(2026, 4, 23),
        )

        import asyncio
        result = asyncio.run(agent.handle(req))

        assert result.status.value == "ok"
        assert "strong_symbols" in result.payload

    def test_data_agent_fallback_to_fields_without_dataset(self):
        """无 dataset 时按 fields 路由（兼容 Phase 0）。"""
        from src.agents.data_agent.agent import DataAgent

        config = _MockConfig()
        agent = DataAgent(config=config)

        req = DataRequest(
            trader_id="test",
            fields=["last_price"],
            # 无 dataset
        )

        import asyncio
        result = asyncio.run(agent.handle(req))

        # fetch_market skill 存在，应该返回 ok
        assert result.status.value == "ok"

    def test_data_agent_unknown_field_without_dataset_returns_missing(self):
        """无 dataset 但字段不支持时返回 capability_missing。"""
        from src.agents.data_agent.agent import DataAgent

        config = _MockConfig()
        agent = DataAgent(config=config)

        req = DataRequest(
            trader_id="test",
            fields=["hot_topics"],  # 不支持，因为没有 dataset
        )

        import asyncio
        result = asyncio.run(agent.handle(req))

        assert result.status.value == "capability_missing"


class _MockConfig:
    """模拟 AppConfig。"""
    class _Kaipan:
        pass
    class _Data:
        mock_prices = {}
        market_data_cache_dir = None
    kaipan = _Kaipan()
    data = _Data()


class _MockHotTopicsProvider:
    def fetch_hot_topics(self, *, trade_date, slot, **kwargs):
        return {
            "dataset": "hot_topics",
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "topics": [
                {"kind": "concept", "topic_id": "BK0001", "topic_name": "AI", "score": 85.0},
            ],
            "sources": ["board_strength"],
        }


class _MockTopicConstituentsProvider:
    def fetch_topic_constituents(self, *, trade_date, slot, **kwargs):
        return {
            "dataset": "topic_constituents",
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "constituents": [
                {"kind": "stock_sector_v2", "topic_id": "ZS001", "topic_name": "AI"},
            ],
            "sources": ["stock_sector_v2"],
        }


class _MockStrongSymbolsProvider:
    def fetch_strong_symbols(self, *, trade_date, slot, **kwargs):
        return {
            "dataset": "strong_symbols",
            "trade_date": trade_date.isoformat(),
            "slot": slot,
            "symbols": [
                {"kind": "strong_fengkou", "symbol": "000001", "name": "平安银行", "strength_score": 88.0},
            ],
            "sources": ["strong_fengkou"],
        }