from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass
class _FakeStrategyVersion:
    version_id: str
    trader_id: str
    strategy_date: date
    status: str
    version_type: str = "manual"
    released_at: datetime | None = None
    rules_snapshot: list[dict] | None = None
    recommendations: list[dict] | None = None
    notes: str | None = None
    parent_version_id: str | None = None
    source_article_ids: list[str] | None = None
    evidence_refs: list[str] | None = None


class _FakeResult:
    def __init__(self, rows: list[_FakeStrategyVersion], total: int | None = None) -> None:
        self._rows = rows
        self._total = total if total is not None else len(rows)

    def scalar(self):
        return self._total

    def scalars(self):
        class _Scalars:
            def __init__(self, rows):
                self._rows = rows

            def all(self):
                return self._rows

        return _Scalars(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, rows_by_query: list[_FakeStrategyVersion] | None = None) -> None:
        self.rows_by_query = rows_by_query or []
        self.executed = []

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _FakeResult(self.rows_by_query)


class _FakeSessionScope:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return None


def test_strategy_service_builds_strategy_version(tmp_path: Path) -> None:
    """StrategyService 应通过构建入口触发策略版本生成。"""
    from src.services.strategy_service import StrategyService

    calls: dict[str, object] = {}

    async def fake_build(details, *, config):
        calls["build"] = (details, config)
        return None

    config_path = tmp_path / "config" / "app.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("timezone: Asia/Shanghai\ntraders: []\n", encoding="utf-8")

    service = StrategyService(build_handler=fake_build)
    result = asyncio.run(
        service.build_strategy_version(
            config_path=config_path,
            trader_id="trader_a",
            strategy_date="2026-04-23",
            force=True,
        )
    )

    assert result.status == "ok"
    assert result.payload["trader_id"] == "trader_a"
    assert result.payload["strategy_date"] == "2026-04-23"
    assert result.payload["force"] is True
    assert calls["build"][0]["trader_id"] == "trader_a"


def test_strategy_service_lists_versions_and_loads_detail(tmp_path: Path) -> None:
    """StrategyService 应支持列表和详情查询。"""
    from src.services.strategy_service import StrategyService

    rows = [
        _FakeStrategyVersion(
            version_id="trader_a_2026-04-23_draft",
            trader_id="trader_a",
            strategy_date=date(2026, 4, 23),
            status="draft",
            released_at=None,
            recommendations=[{"symbol": "000001.SZ"}],
            rules_snapshot=[{"rule_id": "r1"}],
            notes="note",
        ),
    ]
    session = _FakeSession(rows)

    service = StrategyService(session_scope_factory=lambda: _FakeSessionScope(session))

    listed = asyncio.run(
        service.list_strategy_versions(
            trader_id="trader_a",
            status="draft",
            date_from="2026-04-01",
            date_to="2026-04-30",
            skip=0,
            limit=10,
        )
    )
    detail = asyncio.run(service.get_strategy_version("trader_a_2026-04-23_draft"))
    download = asyncio.run(service.download_strategy_version("trader_a_2026-04-23_draft"))

    assert listed.payload["count"] == 1
    assert listed.payload["items"][0]["version_id"] == "trader_a_2026-04-23_draft"
    assert detail.payload["item"]["version_id"] == "trader_a_2026-04-23_draft"
    assert detail.payload["item"]["rules_snapshot"] == [{"rule_id": "r1"}]
    assert download.payload["file_name"] == "strategy_version_trader_a_2026-04-23_draft.json"
    assert download.payload["item"]["notes"] == "note"


def test_strategy_service_returns_none_detail_when_missing(tmp_path: Path) -> None:
    """不存在的策略版本应返回错误状态。"""
    from src.services.strategy_service import StrategyService

    session = _FakeSession([])
    service = StrategyService(session_scope_factory=lambda: _FakeSessionScope(session))

    result = asyncio.run(service.get_strategy_version("missing"))

    assert result.status == "error"
    assert result.payload["item"] is None
