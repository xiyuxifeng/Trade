from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.evaluation.evidence_pack import EvidencePack
from src.evaluation.evaluation_context_service import EvaluationContextService
from src.schemas.contracts import DailyReport, DataResponseStatus, TradeEntry, TradeIdea
from src.strategy_library.schemas import StrategyVersion, StrategyVersionStatus, StrategyVersionType


@dataclass
class _FakeSignalVersion:
    context: object


class _FakeSignalVersioning:
    def __init__(self, context: object) -> None:
        self._context = context
        self.requests: list[str] = []

    def get_version(self, version_id: str) -> _FakeSignalVersion | None:
        self.requests.append(version_id)
        return _FakeSignalVersion(context=self._context)


class _FakeDataAgent:
    def __init__(self) -> None:
        self.requests: list[tuple[list[str], str]] = []

    async def handle(self, req: object) -> object:
        self.requests.append((list(req.symbols), req.dataset))
        if req.dataset == "ohlcv_1d":
            return SimpleNamespace(
                status=DataResponseStatus.ok,
                payload={
                    "ohlcv_1d": {
                        req.symbols[0]: [
                            {"date": "2026-04-06", "open": 10.0, "high": 10.2, "low": 9.9, "close": 10.1},
                        ]
                    }
                },
            )
        return SimpleNamespace(
            status=DataResponseStatus.ok,
            payload={"indicators": {req.symbols[0]: {"rsi": 55.0}}},
        )


class _FakeStrategyLibraryService:
    def __init__(self, version: StrategyVersion) -> None:
        self.version = version
        self.requests: list[tuple[str, str]] = []

    async def get_version(self, session: object, version_id: str) -> StrategyVersion | None:
        self.requests.append(("get_version", version_id))
        return self.version


@asynccontextmanager
async def _fake_session_scope():
    yield SimpleNamespace()


def _make_trade_idea() -> TradeIdea:
    day = date(2026, 4, 6)
    return TradeIdea(
        trader_id="trader_a",
        as_of_date=day,
        symbol="000001.SZ",
        entry=TradeEntry(type="limit", price=10.0),
        target_price=10.5,
        stop_loss_price=9.7,
        strategy_version_id="sv_001",
    )


@pytest.mark.asyncio
async def test_generate_evidence_pack_uses_signal_context_market_data_and_strategy_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    """证据打包应由独立 service 完成，而不是散落在 ManagerAgent 里。"""
    from src.evaluation import evaluation_context_service as mod

    signal_context = SimpleNamespace(triggered_rules=["rule-1"], confidence=0.8)
    strategy_version = StrategyVersion(
        version_id="sv_001",
        trader_id="trader_a",
        strategy_date=date(2026, 4, 6),
        status=StrategyVersionStatus.released,
        version_type=StrategyVersionType.manual,
        recommendations=[],
        source_article_ids=[],
        evidence_refs=[],
        rules_snapshot=[{"rule_id": "r1"}],
    )

    data_agent = _FakeDataAgent()
    strategy_service = _FakeStrategyLibraryService(strategy_version)
    signal_versioning = _FakeSignalVersioning(signal_context)
    service = EvaluationContextService(
        data_agent=data_agent,
        strategy_library_service=strategy_service,
        signal_versioning=signal_versioning,
    )

    monkeypatch.setattr(mod, "session_scope", _fake_session_scope)

    idea = _make_trade_idea()
    report = DailyReport(as_of_date=idea.as_of_date, ideas=[idea], highlights=["seed"])

    pack = await service.generate_evidence_pack(
        idea=idea,
        daily_report=report,
        last_prices={"000001.SZ": 10.6},
    )

    assert isinstance(pack, EvidencePack)
    assert pack.signal_context is not None
    assert pack.strategy_version_id == "sv_001"
    assert pack.strategy_version_snapshot == [{"rule_id": "r1"}]
    assert pack.market_data.entry_price == 10.0
    assert pack.market_data.current_price == 10.6
    assert pack.market_data.bars and pack.market_data.bars[0]["close"] == 10.1


@pytest.mark.asyncio
async def test_get_account_snapshot_uses_trade_idea_trader_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """账户快照 service 应优先使用 trade_idea 的 trader_id 作为 account_id。"""
    from src.evaluation import evaluation_context_service as mod

    captured: dict[str, str] = {}

    async def fake_build_account_snapshot(*, session: object, account_id: str, initial_cash: float = 100000.0, as_of: datetime | None = None) -> SimpleNamespace:
        captured["account_id"] = account_id
        return SimpleNamespace(account_id=account_id, net_value=100000.0)

    monkeypatch.setattr(mod, "session_scope", _fake_session_scope)
    monkeypatch.setattr(mod, "build_account_snapshot", fake_build_account_snapshot)

    service = EvaluationContextService(
        data_agent=_FakeDataAgent(),
        strategy_library_service=_FakeStrategyLibraryService(
            StrategyVersion(
                version_id="sv_001",
                trader_id="trader_a",
                strategy_date=date(2026, 4, 6),
                status=StrategyVersionStatus.released,
                version_type=StrategyVersionType.manual,
                recommendations=[],
                source_article_ids=[],
                evidence_refs=[],
                rules_snapshot=[],
            )
        ),
        signal_versioning=_FakeSignalVersioning(SimpleNamespace()),
    )

    snapshot = await service.get_account_snapshot(trade_idea=_make_trade_idea())

    assert captured["account_id"] == "trader_a"
    assert snapshot.account_id == "trader_a"
