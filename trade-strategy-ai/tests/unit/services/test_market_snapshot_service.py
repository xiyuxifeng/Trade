from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class _FakeProvider:
    raw_dir: Path

    def fetch_custom(self, **kwargs):
        api_name = kwargs["api_name"]
        if api_name == "ChangeStatistics":
            return {"info": [{"strong": "56"}]}
        if api_name == "MarketCapacity":
            return {"info": {"last": "23417"}}
        if api_name == "GetZsReal":
            return {"StockList": [{"StockID": "SH000001"}]}
        if api_name == "RefreshStockList":
            return {"StockList": [{"StockID": "SH000001"}]}
        if api_name == "MarketStockZDNum":
            return {"info": {"SJZT": "79", "SJDT": "1"}}
        if api_name == "RealRankingInfo":
            zstype = kwargs.get("ZSType")
            return {"list": [[f"881{zstype}", f"section-{zstype}", 100]]}
        if api_name == "DailyLimitIndex":
            return {"info": [71, 5, 1, 1, 1]}
        if api_name == "ZhangTingExpression":
            return {"info": [71, 5, 1, 2]}
        if api_name == "DailyLimitPerformance2":
            return {"info": [[["000001", "示例"]]]}
        if api_name == "GetPMSL_PMLD":
            return {"List": [{"TagName": "T字板"}]}
        if api_name == "MorningBidding":
            return {"info": {"tJJJE": "1亿"}}
        if api_name == "MorningBiddingNum":
            return {"info": [1, 2, 3, 4, 5]}
        if api_name == "MorningBiddingList":
            return {"info": [["000001", "示例"]]}
        if api_name == "GetWPQC":
            return {"List": [["000001", "示例", "量化", 1, "板块", 1.2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.5, 10]]}
        if api_name == "GetBKJJ_W36":
            return {"List1": [["801003", "5G", 6.1]]}
        if api_name == "GetBKJJBL":
            return {"List": [["000001", "示例"]]}
        if api_name == "WeightPerformance":
            return {"info": {"SZ": [["881162", "通信服务", 3.8]], "XD": [["881107", "油气开采及服务", -0.399]]}}
        raise AssertionError(api_name)

    def fetch_board_strength(self, *, trade_date, slot, use_today_url=None):
        return {"list": [["881007", "板块强度", 398]]}

    def fetch_industry_ranking(self, *, trade_date, slot, use_today_url=None):
        return {"list": [["881267", "行业涨幅", 398]]}

    def fetch_pre_market_bid(self, *, trade_date, slot):
        return {"info": {"tJJJE": "201.95亿"}}

    def fetch_pre_market_stats(self, *, trade_date, slot):
        return {"info": [189, 196, 50, 61, 2]}

    def fetch_limit_up_info(self, *, trade_date, slot, index=0, st=20):
        return {"info": [71, 5, 1, 2, 10.0]}

    def fetch_limit_up_reason(self, *, trade_date, slot, index=0, st=20):
        return {"nums": {"ZT": 79}, "list": [{"ZSCode": "801807", "num": 2}]}

    def fetch_lhb_list(self, *, trade_date, slot, index=0, st=300):
        return {"info": [["000001", "示例"]]}

    def fetch_hot_topics(self, *, trade_date, slot, offline=False):
        return {"topics": [{"kind": "concept", "topic_id": "1", "topic_name": "热点"}], "sources": ["board_strength"]}

    def fetch_topic_constituents(self, *, trade_date, slot, offline=False):
        return {"constituents": [{"kind": "theme_detail", "topic_id": "1", "topic_name": "热点", "symbol": "000001"}], "sources": ["theme_detail"]}

    def fetch_strong_symbols(self, *, trade_date, slot, offline=False):
        return {"symbols": [{"kind": "strong_fengkou", "symbol": "000001", "name": "示例"}], "sources": ["strong_fengkou"]}


class _FakeMarketService:
    async def get_ohlcv(self, symbol: str, start_date, end_date):
        from src.services.base import ServiceResult

        return ServiceResult(
            status="ok",
            message="ok",
            payload={
                "symbol": symbol,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "count": 2,
                "items": [{"time": "2026-05-15"}, {"time": "2026-05-16"}],
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
        Path(dest).write_text(json.dumps({"state": "bull"}), encoding="utf-8")
        return ServiceResult(
            status="ok",
            message="market state written",
            payload={
                "market_state_path": str(dest),
                "source": "cache",
                "benchmark_symbol": benchmark_symbol,
                "market_state": {"state": "bull", "benchmark_symbol": benchmark_symbol},
            },
        )


@pytest.fixture()
async def market_data_session_factory(tmp_path):
    """创建用于 MarketSnapshotService 持久化测试的 sqlite session factory。"""
    from src.models.market_data_quality_report import MarketDataQualityReport
    from src.models.market_dataset import MarketDataset
    from src.models.market_data_snapshot import MarketSnapshot as MarketDataSnapshotRecord
    from src.models.market_data_snapshot_item import MarketSnapshotItem
    from src.models.market_data_snapshot_section import MarketSnapshotSection

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'market_snapshot_service.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(MarketDataSnapshotRecord.__table__.create)
        await conn.run_sync(MarketSnapshotSection.__table__.create)
        await conn.run_sync(MarketDataset.__table__.create)
        await conn.run_sync(MarketSnapshotItem.__table__.create)
        await conn.run_sync(MarketDataQualityReport.__table__.create)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


def test_market_snapshot_service_writes_snapshot_summary_and_quality_reports(tmp_path: Path) -> None:
    """MarketSnapshotService 应输出完整的 snapshot / summary / quality 产物。"""
    from src.services.market_snapshot_service import MarketSnapshotService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    service = MarketSnapshotService(
        provider_factory=lambda **kwargs: _FakeProvider(raw_dir=tmp_path / "raw"),
        market_service=_FakeMarketService(),
        persona_service=_FakePersonaService(),
        snapshot_root=tmp_path / "market_snapshot",
    )

    result = asyncio.run(
        service.build_market_snapshot(
            config_path=config_path,
            benchmark_symbol="000300.SH",
            trade_date="2026-05-16",
            slot="17-30",
            profile_id="default",
            offline=False,
            force=True,
        )
    )

    assert result.status == "ok"
    assert "snapshot_id" in result.payload
    assert Path(result.payload["snapshot_path"]).exists()
    assert Path(result.payload["snapshot_summary_path"]).exists()
    assert Path(result.payload["quality_report_path"]).exists()
    assert result.payload["snapshot"]["sections"]["overview"]["quality_status"] == "ok"
    assert result.payload["snapshot"]["metadata"]["config_ref"] == "config/app.yaml"
    assert result.payload["snapshot_summary"]["metadata"]["config_ref"] == "config/app.yaml"
    assert result.payload["snapshot_summary"]["missing_section_count"] == 0
    assert result.payload["quality_report"]["overall_status"] == "ok"


def test_market_snapshot_service_reports_partial_coverage(tmp_path: Path) -> None:
    """部分 section 缺失时应返回 partial 并记录 warning。"""
    from src.services.market_snapshot_service import MarketSnapshotService

    class _PartialProvider(_FakeProvider):
        def fetch_board_strength(self, *, trade_date, slot, use_today_url=None):
            raise RuntimeError("provider unavailable")

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    service = MarketSnapshotService(
        provider_factory=lambda **kwargs: _PartialProvider(raw_dir=tmp_path / "raw"),
        market_service=_FakeMarketService(),
        persona_service=_FakePersonaService(),
        snapshot_root=tmp_path / "market_snapshot",
    )

    result = asyncio.run(
        service.build_market_snapshot(
            config_path=config_path,
            benchmark_symbol="000300.SH",
            trade_date="2026-05-16",
            slot="17-30",
            profile_id="default",
            offline=False,
            force=True,
        )
    )

    assert result.status == "partial"
    assert any("overview" in warning or "sector_activity" in warning for warning in result.warnings)


@pytest.mark.asyncio()
async def test_market_snapshot_service_persists_snapshot_to_database(tmp_path: Path, market_data_session_factory) -> None:
    """MarketSnapshotService 真实编排路径应把 snapshot 写入 DB。"""
    from src.services.market_data_storage_service import MarketDataStorageService
    from src.services.market_snapshot_service import MarketSnapshotService

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    service = MarketSnapshotService(
        provider_factory=lambda **kwargs: _FakeProvider(raw_dir=tmp_path / "raw"),
        market_service=_FakeMarketService(),
        persona_service=_FakePersonaService(),
        storage_service=MarketDataStorageService(session_factory=market_data_session_factory),
        snapshot_root=tmp_path / "market_snapshot",
    )

    result = await service.build_market_snapshot(
        config_path=config_path,
        benchmark_symbol="000300.SH",
        trade_date="2026-05-16",
        slot="17-30",
        profile_id="default",
        offline=False,
        force=True,
    )

    loaded = await service._storage_service.load_snapshot(result.payload["snapshot_id"])  # noqa: SLF001
    assert result.status == "ok"
    assert result.payload["db_storage"]["snapshot_id"] == result.payload["snapshot_id"]
    assert loaded.status == "ok"
    assert loaded.payload["snapshot"]["snapshot_id"] == result.payload["snapshot_id"]
    assert loaded.payload["dataset"]["dataset_id"] == f"{result.payload['snapshot_id']}:dataset"
