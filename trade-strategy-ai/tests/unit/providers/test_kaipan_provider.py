from __future__ import annotations

from datetime import date
from pathlib import Path

from src.providers.base import ProviderStatus
from src.providers.kaipan_provider import KaipanAuth, KaipanProvider


def _build_provider(tmp_path: Path) -> KaipanProvider:
    return KaipanProvider(
        auth=KaipanAuth(token="token", user_id="user"),
        raw_dir=tmp_path / "raw",
        normalized_dir=tmp_path / "normalized",
        snapshots_dir=tmp_path / "snapshots",
        kaipan_config={"token": "token", "user_id": "user"},
    )


def test_kaipan_provider_normalizes_hot_topics(tmp_path: Path) -> None:
    provider = _build_provider(tmp_path)

    provider.fetch_board_strength = lambda *, trade_date, slot, use_today_url=None: {
        "list": [["001", "概念A", 12.3, 1.1, 0.5, 100.0, 200.0]]
    }
    provider.fetch_industry_ranking = lambda *, trade_date, slot, use_today_url=None: {
        "list": [["002", "行业B", 3.4, 2.2, 1.1, 150.0, 250.0]]
    }
    provider.fetch_concept_fengkou = lambda *, trade_date, slot: {"List": [["风口C", 7.8]]}

    result = provider.run("hot_topics", request={"trade_date": "2026-04-22", "slot": "09-25"})

    assert result.status == ProviderStatus.ok
    assert result.payload["dataset"] == "hot_topics"
    assert result.payload["trade_date"] == "2026-04-22"
    assert result.payload["slot"] == "09-25"
    assert len(result.payload["topics"]) == 3
    assert result.payload["topics"][0]["kind"] == "concept"
    assert result.payload["topics"][1]["kind"] == "industry"
    assert result.payload["topics"][2]["kind"] == "concept_fengkou"


def test_kaipan_provider_normalizes_topic_constituents(tmp_path: Path) -> None:
    provider = _build_provider(tmp_path)

    provider.fetch_stock_sector_v2 = lambda *, trade_date, slot, stock_id="": {
        "info": [["T1", "题材A", 12.3, "000001", "龙头A", 9.8]]
    }
    provider.fetch_theme_detail = lambda *, trade_date, slot, theme_id="": {
        "ID": theme_id or "T1",
        "Name": "题材A",
        "BriefIntro": "简介A",
    }
    provider.fetch_limit_up_reason = lambda *, trade_date, slot, index=0, st=20: {
        "list": [{"ZSCode": "T2", "ZSName": "涨停题材B"}]
    }
    provider.fetch_limit_up_info = lambda *, trade_date, slot, index=0, st=20, use_today_url=None: {
        "StockList": [["000002", "股票B", 2]]
    }
    provider.fetch_lhb_list = lambda *, trade_date, slot, index=0, st=300: {
        "list": [{"ID": "000003", "Name": "股票C", "BuyIn": 100.0}]
    }

    result = provider.run(
        "topic_constituents",
        request={"trade_date": "2026-04-22", "slot": "17-30", "stock_id": "000001", "theme_id": "T1"},
    )

    assert result.status == ProviderStatus.ok
    assert result.payload["dataset"] == "topic_constituents"
    assert result.payload["trade_date"] == "2026-04-22"
    assert result.payload["slot"] == "17-30"
    assert len(result.payload["constituents"]) == 5
    assert result.payload["constituents"][0]["kind"] == "stock_sector_v2"
    assert result.payload["constituents"][1]["kind"] == "theme_detail"
    assert result.payload["constituents"][4]["kind"] == "lhb_list"


def test_kaipan_provider_normalizes_strong_symbols(tmp_path: Path) -> None:
    provider = _build_provider(tmp_path)

    provider.fetch_strong_fengkou = lambda *, trade_date, slot, time="", use_today_url=None: {
        "List": [["000001.SZ", "股票A", 88.0, None, 4.5, 1000.0, None, None, 120.0, 80.0, "题材A"]]
    }
    provider.fetch_interval_stats_stock = lambda *, trade_date, slot, start_date=None, end_date=None, use_today_url=None: {
        "List": [["000002.SZ", "股票B", None, 3.8, None, None, 230.0, 0.45, None, None, "题材B"]]
    }
    provider.fetch_morning_bidding_list = lambda *, trade_date, slot, pid_type=0, data_type=4, index=0, order=1, st=20: {
        "info": [["000003.SZ", "股票C", None, 2.1, None, None, 88.0, None, 120.0, None, None, "题材C"]]
    }

    result = provider.run(
        "strong_symbols",
        request={"trade_date": date(2026, 4, 22), "slot": "09-25"},
    )

    assert result.status == ProviderStatus.ok
    assert result.payload["dataset"] == "strong_symbols"
    assert result.payload["trade_date"] == "2026-04-22"
    assert result.payload["slot"] == "09-25"
    assert len(result.payload["symbols"]) == 3
    assert result.payload["symbols"][0]["kind"] == "strong_fengkou"
    assert result.payload["symbols"][1]["kind"] == "interval_stats_stock"
    assert result.payload["symbols"][2]["kind"] == "morning_bidding_list"


def test_kaipan_provider_fetch_hot_topics_wrapper_returns_payload(tmp_path: Path) -> None:
    provider = _build_provider(tmp_path)

    provider.fetch_board_strength = lambda *, trade_date, slot, use_today_url=None: {
        "list": [["001", "概念A", 12.3, 1.1, 0.5, 100.0, 200.0]]
    }
    provider.fetch_industry_ranking = lambda *, trade_date, slot, use_today_url=None: {"list": []}
    provider.fetch_concept_fengkou = lambda *, trade_date, slot: {"List": []}

    payload = provider.fetch_hot_topics(trade_date=date(2026, 4, 22), slot="09-25")

    assert payload["dataset"] == "hot_topics"
    assert payload["topics"][0]["topic_name"] == "概念A"
