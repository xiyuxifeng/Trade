from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class _FakeProvider:
    raw_dir: Path

    def fetch_custom(self, **kwargs):
        api_name = kwargs["api_name"]
        if api_name == "ChangeStatistics":
            return {"info": [{"strong": "56", "ztjs": "69"}], "tip": "ok"}
        if api_name == "MarketCapacity":
            return {"info": {"last": "23417", "date": "2026-05-16"}}
        if api_name == "GetZsReal":
            return {"StockList": [{"StockID": "SH000001", "prod_name": "上证指数"}]}
        if api_name == "RefreshStockList":
            return {"StockList": [{"StockID": "SH000001", "prod_name": "上证指数"}]}
        if api_name == "MarketStockZDNum":
            return {"info": {"SJZT": "79", "SJDT": "1"}}
        if api_name == "RealRankingInfo":
            zstype = kwargs.get("ZSType")
            return {"list": [[f"881{zstype}", f"section-{zstype}", 100, 1.2]]}
        if api_name == "DailyLimitIndex":
            return {"info": [71, 5, 1, 1, 1]}
        if api_name == "ZhangTingExpression":
            return {"info": [71, 5, 1, 2, 10.0, 12.0, 66.0, 21.0, 1.0, 3.0, 1.2, "summary"]}
        if api_name == "DailyLimitPerformance2":
            return {"info": [[["000001", "示例", 0]]]}
        if api_name == "GetPMSL_PMLD":
            return {"List": [{"TagName": "T字板"}]}
        if api_name == "MorningBidding":
            return {"info": {"tJJJE": "1亿"}}
        if api_name == "MorningBiddingNum":
            return {"info": [1, 2, 3, 4, 5]}
        if api_name == "MorningBiddingList":
            return {"info": [["000001", "示例", None, 1.2]]}
        if api_name == "GetWPQC":
            return {"List": [["000001", "示例", "量化", 1, "板块", 1.2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.5, 10]]}
        if api_name == "GetBKJJ_W36":
            return {"List1": [["801003", "5G", 6.1, 480121033, 125, 8199256]]}
        if api_name == "GetBKJJBL":
            return {"List": [["000001", "示例", 1.0, 1.2, 8.0]]}
        if api_name == "WeightPerformance":
            return {"info": {"SZ": [["881162", "通信服务", 3.8]], "XD": [["881107", "油气开采及服务", -0.399]]}}
        raise AssertionError(f"unexpected api_name: {api_name}")

    def fetch_board_strength(self, *, trade_date, slot, use_today_url=None):
        return {"list": [["881007", "板块强度", 398, 3.98, -0.07, 100, 10]]}

    def fetch_industry_ranking(self, *, trade_date, slot, use_today_url=None):
        return {"list": [["881267", "行业涨幅", 398, 3.98, -0.07, 100, 10]]}

    def fetch_pre_market_bid(self, *, trade_date, slot):
        return {"info": {"tJJJE": "201.95亿"}}

    def fetch_pre_market_stats(self, *, trade_date, slot):
        return {"info": [189, 196, 50, 61, 2]}

    def fetch_limit_up_info(self, *, trade_date, slot, index=0, st=20):
        return {"info": [71, 5, 1, 2, 10.0]}

    def fetch_limit_up_reason(self, *, trade_date, slot, index=0, st=20):
        return {"nums": {"ZT": 79}, "list": [{"ZSCode": "801807", "num": 2}]}

    def fetch_lhb_list(self, *, trade_date, slot, index=0, st=300):
        return {"info": [["000001", "示例", 0, "", 1, 2, "板块", 3]]}

    def fetch_market_stock_zd_num(self, *, trade_date, slot="17-30", offline=False, **kwargs):
        return {"dataset": "market_stock_zd_num", "trade_date": str(trade_date), "slot": slot, "limit_up_count": 79, "limit_down_count": 1, "panic": 12, "summary": {"SJZT": 79, "SJDT": 1}}

    def fetch_zhang_ting_expression(self, *, trade_date, slot="17-30", offline=False, **kwargs):
        return {"dataset": "zhang_ting_expression", "trade_date": str(trade_date), "slot": slot, "items": [{"total_limit_up": 71, "first_board_count": 5}]}

    def fetch_daily_limit_index(self, *, trade_date, slot="17-30", offline=False, **kwargs):
        return {"dataset": "daily_limit_index", "trade_date": str(trade_date), "slot": slot, "items": [{"one_board_count": 71, "two_board_count": 5}]}

    def fetch_weight_performance(self, *, trade_date, slot="17-30", offline=False, **kwargs):
        return {"dataset": "weight_performance", "trade_date": str(trade_date), "slot": slot, "items": [{"market": "SZ", "symbol": "881162", "name": "通信服务", "change_pct": 3.8}]}

    def fetch_get_feng_k_list(self, *, trade_date, slot="17-30", offline=False, time="", **kwargs):
        return {"dataset": "get_feng_k_list", "trade_date": str(trade_date), "slot": slot, "items": [{"symbol": "000001", "name": "示例"}]}

    def fetch_hot_topics(self, *, trade_date, slot, offline=False):
        return {"topics": [{"kind": "concept", "topic_id": "1", "topic_name": "热点"}], "sources": ["board_strength"]}

    def fetch_topic_constituents(self, *, trade_date, slot, offline=False):
        return {"constituents": [{"kind": "theme_detail", "topic_id": "1", "topic_name": "热点", "symbol": "000001"}], "sources": ["theme_detail"]}

    def fetch_strong_symbols(self, *, trade_date, slot, offline=False):
        return {"symbols": [{"kind": "strong_fengkou", "symbol": "000001", "name": "示例"}], "sources": ["strong_fengkou"]}


class _FakeMarketService:
    async def get_ohlcv(self, symbol: str, start_date: date, end_date: date):
        from src.services.base import ServiceResult

        del start_date, end_date
        return ServiceResult(
            status="ok",
            message="ok",
            payload={
                "symbol": symbol,
                "start_date": "2026-04-27",
                "end_date": "2026-05-16",
                "count": 2,
                "items": [{"time": "2026-05-15", "close": 10.5}, {"time": "2026-05-16", "close": 10.6}],
            },
        )


class _FakePersonaService:
    def build_market_state(
        self,
        *,
        config_path,
        benchmark_symbol,
        as_of,
        dest,
        from_akshare=False,
        cache_csv=True,
    ):
        from src.services.base import ServiceResult

        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text('{"state":"bull"}', encoding="utf-8")
        del config_path, benchmark_symbol, as_of, from_akshare, cache_csv
        return ServiceResult(
            status="ok",
            message="market state written",
            payload={
                "market_state_path": str(dest),
                "source": "cache",
                "market_state": {"state": "bull"},
            },
        )


def test_first_batch_builders_emit_quality_metadata(tmp_path: Path) -> None:
    """第一批 section builder 应输出质量元数据和结构化 payload。"""
    from src.models.market_snapshot import MarketSnapshotBuildContext
    from src.services.market_snapshot_builders import (
        build_auction_section,
        build_limit_up_down_section,
        build_ohlcv_section,
        build_overview_section,
        build_sector_activity_section,
    )

    provider = _FakeProvider(raw_dir=tmp_path / "raw")
    context = MarketSnapshotBuildContext(
        config_path=str(tmp_path / "config" / "app.yaml"),
        profile_id="default",
        trade_date="2026-05-15",
        slot="17-30",
        offline=False,
    )

    overview = build_overview_section(context, provider=provider)
    limit_up_down = build_limit_up_down_section(context, provider=provider)
    sector = build_sector_activity_section(context, provider=provider)
    auction = build_auction_section(context, provider=provider)
    ohlcv = build_ohlcv_section(context, market_service=_FakeMarketService(), base_dir=tmp_path, benchmark_symbol="SH000001")

    assert overview.section_id == "overview"
    assert overview.quality_status == "ok"
    assert overview.record_count > 0
    assert "sentiment" in overview.payload
    assert limit_up_down.section_id == "limit_up_down"
    assert limit_up_down.quality_status == "ok"
    assert "limit_up_counts" in limit_up_down.payload
    assert sector.section_id == "sector_activity"
    assert sector.quality_status == "ok"
    assert "board_strength" in sector.payload
    assert auction.section_id == "auction"
    assert auction.quality_status == "ok"
    assert "pre_market_bid" in auction.payload
    assert ohlcv.section_id == "ohlcv"
    assert ohlcv.quality_status == "ok"
    assert ohlcv.record_count == 2


def test_market_state_and_legacy_sections_share_section_shape(tmp_path: Path) -> None:
    """旧 MarketUniverse 相关 section 应统一输出为 MarketSnapshotSection。"""
    from src.models.market_snapshot import MarketSnapshotBuildContext
    from src.services.market_snapshot_builders import (
        build_hot_topics_section,
        build_market_state_section,
        build_strong_symbols_section,
        build_topic_constituents_section,
    )

    provider = _FakeProvider(raw_dir=tmp_path / "raw")
    context = MarketSnapshotBuildContext(
        config_path=str(tmp_path / "config" / "app.yaml"),
        profile_id="default",
        trade_date="2026-05-15",
        slot="17-30",
        offline=False,
    )

    hot_topics = build_hot_topics_section(context, provider=provider)
    constituents = build_topic_constituents_section(context, provider=provider)
    strong_symbols = build_strong_symbols_section(context, provider=provider)
    market_state = build_market_state_section(
        context,
        persona_service=_FakePersonaService(),
        config_path=str(tmp_path / "config" / "app.yaml"),
        output_dir=tmp_path / "data" / "processed" / "market_snapshot",
        benchmark_symbol="000300.SH",
    )

    assert hot_topics.quality_status == "ok"
    assert constituents.quality_status == "ok"
    assert strong_symbols.quality_status == "ok"
    assert market_state.quality_status == "ok"


def test_get_feng_k_list_section_passes_required_params(tmp_path: Path) -> None:
    """收盘强势标的构建时应传入文档要求的参数。"""
    from src.models.market_snapshot import MarketSnapshotBuildContext
    from src.services.market_snapshot_builders import build_get_feng_k_list_section

    provider = _FakeProvider(raw_dir=tmp_path / "raw")
    captured: list[dict[str, object]] = []

    def _fetch_get_feng_k_list(**kwargs):
        captured.append(kwargs)
        return {"dataset": "get_feng_k_list", "trade_date": "2026-05-15", "slot": "17-30", "items": [{"symbol": "000001"}]}

    provider.fetch_get_feng_k_list = _fetch_get_feng_k_list  # type: ignore[method-assign]

    context = MarketSnapshotBuildContext(
        config_path=str(tmp_path / "config" / "app.yaml"),
        profile_id="default",
        trade_date="2026-05-15",
        slot="17-30",
        offline=False,
    )

    section = build_get_feng_k_list_section(context, provider=provider)

    assert section.quality_status == "ok"
    assert captured[0]["time"] == "1500"
    assert captured[0]["index"] == 0
    assert captured[0]["order"] == 17
    assert captured[0]["st"] == 500


def test_market_snapshot_registry_includes_10_5_sections(tmp_path: Path) -> None:
    """默认 registry 应包含 10.5 Kaipan sections。"""
    from src.services.market_snapshot_builders import build_default_market_snapshot_registry

    registry = build_default_market_snapshot_registry(
        provider=_FakeProvider(raw_dir=tmp_path / "raw"),
        market_service=_FakeMarketService(),
        persona_service=_FakePersonaService(),
        base_dir=tmp_path,
        benchmark_symbol="SH000001",
        config_path=tmp_path / "config" / "app.yaml",
    )

    section_ids = registry.section_ids()
    assert "market_stock_zd_num" in section_ids
    assert "zhang_ting_expression" in section_ids
    assert "daily_limit_index" in section_ids
    assert "weight_performance" in section_ids
    assert "get_feng_k_list" in section_ids
