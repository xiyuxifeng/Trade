from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.trader_option_service import TraderOptionService


class _FakeScalarResult:
    def __init__(self, items: list[str]) -> None:
        self._items = items

    def scalars(self) -> _FakeScalarResult:
        return self

    def all(self) -> list[str]:
        return self._items


class _FakeSession:
    def __init__(self, items: list[str]) -> None:
        self._items = items

    async def execute(self, stmt):  # noqa: ANN001
        return _FakeScalarResult(self._items)


class _FakeSessionScope:
    def __init__(self, items: list[str]) -> None:
        self._session = _FakeSession(items)

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


@pytest.mark.asyncio
async def test_list_trader_options_merges_strategy_and_backtest_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    strategy_scope_factory = lambda: _FakeSessionScope(["trader_b", "trader_a", "trader_a"])  # noqa: E731
    service = TraderOptionService(session_scope_factory=strategy_scope_factory)

    backtest_root = tmp_path / "backtest"
    backtest_root.mkdir()
    (backtest_root / "result-a.json").write_text(json.dumps({"request_trader_id": "trader_c"}), encoding="utf-8")
    (backtest_root / "result-b.json").write_text(json.dumps({"trader_id": "trader_a"}), encoding="utf-8")

    monkeypatch.setattr(
        "src.services.trader_option_service._get_backtest_result_dirs",
        lambda: [backtest_root],
    )

    strategy_result = await service.list_trader_options(source="strategy")
    backtest_result = await service.list_trader_options(source="backtest")
    all_result = await service.list_trader_options(source="all")

    assert strategy_result.status == "ok"
    assert strategy_result.payload["items"] == ["trader_a", "trader_b"]

    assert backtest_result.status == "ok"
    assert backtest_result.payload["items"] == ["trader_a", "trader_c"]

    assert all_result.status == "ok"
    assert all_result.payload["items"] == ["trader_a", "trader_b", "trader_c"]
