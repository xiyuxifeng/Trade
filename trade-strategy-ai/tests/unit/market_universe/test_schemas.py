def test_market_universe_package_importable():
    """market_universe 包应可导入。"""
    from src.market_universe import schemas
    assert hasattr(schemas, "HotTopic")


def test_hot_topic_fields():
    """HotTopic 应包含所有热点字段。"""
    from src.market_universe.schemas import HotTopic

    t = HotTopic(
        kind="concept",
        topic_id="001",
        topic_name="人工智能",
        score=85.5,
        increase_pct=3.2,
        speed_pct=1.1,
        turnover=5000.0,
        net_inflow=2000.0,
    )
    assert t.kind == "concept"
    assert t.topic_id == "001"
    assert t.topic_name == "人工智能"
    assert t.score == 85.5
    assert t.increase_pct == 3.2
    assert t.speed_pct == 1.1
    assert t.turnover == 5000.0
    assert t.net_inflow == 2000.0


def test_hot_topic_defaults():
    """HotTopic 可缺省字段应默认 None。"""
    from src.market_universe.schemas import HotTopic

    t = HotTopic(kind="concept", topic_id="001", topic_name="人工智能")
    assert t.score is None
    assert t.increase_pct is None
    assert t.speed_pct is None


def test_topic_constituent_fields():
    """TopicConstituent 应包含所有成分字段。"""
    from src.market_universe.schemas import TopicConstituent

    c = TopicConstituent(
        kind="stock_sector_v2",
        topic_id="ZS001",
        topic_name="人工智能",
        symbol="000001",
        name="平安银行",
        topic_change_pct=2.5,
        leader_symbol="000001",
        leader_name="平安银行",
        leader_change_pct=3.1,
    )
    assert c.kind == "stock_sector_v2"
    assert c.topic_id == "ZS001"
    assert c.topic_name == "人工智能"
    assert c.symbol == "000001"
    assert c.leader_change_pct == 3.1


def test_topic_constituent_optional():
    """TopicConstituent 大部分字段可缺省。"""
    from src.market_universe.schemas import TopicConstituent

    c = TopicConstituent(kind="limit_up_reason", topic_id="ZS001", topic_name="人工智能")
    assert c.symbol is None
    assert c.leader_change_pct is None


def test_strong_symbol_fields():
    """StrongSymbol 应包含所有强势标的的字段。"""
    from src.market_universe.schemas import StrongSymbol

    s = StrongSymbol(
        kind="strong_fengkou",
        symbol="000001",
        name="平安银行",
        strength_score=88.0,
        change_pct=5.2,
        turnover=30000.0,
        turnover_ratio=2.5,
        return_pct=8.0,
        net_inflow=15000.0,
        topic_tags="AI，银行",
    )
    assert s.kind == "strong_fengkou"
    assert s.strength_score == 88.0
    assert s.turnover_ratio == 2.5


def test_strong_symbol_optional():
    """StrongSymbol 可缺省字段应默认 None。"""
    from src.market_universe.schemas import StrongSymbol

    s = StrongSymbol(kind="morning_bidding_list", symbol="000001", name="平安银行")
    assert s.strength_score is None
    assert s.return_pct is None


def test_market_universe_aggregates_all():
    """MarketUniverse 应聚合三类 payload。"""
    from datetime import datetime
    from src.market_universe.schemas import (
        MarketUniverse,
        HotTopicsPayload,
        TopicConstituentsPayload,
        StrongSymbolsPayload,
        HotTopic,
        TopicConstituent,
        StrongSymbol,
    )

    mu = MarketUniverse(
        trade_date="2026-04-23",
        slot="17-30",
        hot_topics=HotTopicsPayload(
            trade_date="2026-04-23",
            slot="17-30",
            topics=[HotTopic(kind="concept", topic_id="001", topic_name="AI")],
            sources=["board_strength"],
            fetched_at=datetime.now(),
        ),
        topic_constituents=TopicConstituentsPayload(
            trade_date="2026-04-23",
            slot="17-30",
            constituents=[TopicConstituent(kind="limit_up_reason", topic_id="ZS001", topic_name="AI")],
            sources=["limit_up_reason"],
        ),
        strong_symbols=StrongSymbolsPayload(
            trade_date="2026-04-23",
            slot="17-30",
            symbols=[StrongSymbol(kind="strong_fengkou", symbol="000001", name="平安银行", strength_score=85.0)],
            sources=["strong_fengkou"],
        ),
        metadata={"source": "kaipan"},
    )

    assert mu.trade_date == "2026-04-23"
    assert mu.hot_topics is not None
    assert len(mu.hot_topics.topics) == 1
    assert mu.topic_constituents is not None
    assert mu.strong_symbols is not None
    assert mu.strong_symbols.symbols[0].strength_score == 85.0


def test_market_universe_optional_payloads():
    """MarketUniverse 的三类 payload 均可为 None。"""
    from src.market_universe.schemas import MarketUniverse

    mu = MarketUniverse(trade_date="2026-04-23", slot="09-25")
    assert mu.hot_topics is None
    assert mu.topic_constituents is None
    assert mu.strong_symbols is None
