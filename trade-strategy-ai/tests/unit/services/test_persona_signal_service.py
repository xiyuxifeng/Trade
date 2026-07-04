from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@dataclass
class _FakeDbSignal:
	signal_id: str
	symbol: str
	side: str
	confidence: float
	created_at: datetime
	trader_id: str | None
	strategy_version_id: str | None
	signal_metadata: dict[str, object]


class _FakeDbRepo:
	def __init__(self, rows: list[_FakeDbSignal]) -> None:
		self.rows = rows
		self.calls: list[dict[str, object]] = []

	async def list_signals(self, session, *, symbol=None, since=None, limit=100, offset=0):
		self.calls.append(
			{
				"session": session,
				"symbol": symbol,
				"since": since,
				"limit": limit,
				"offset": offset,
			}
		)
		return self.rows


class _FakeDbSessionScope:
	async def __aenter__(self):
		return object()

	async def __aexit__(self, exc_type, exc, tb):
		return None


def _write_basic_config(config_path: Path) -> None:
	config_path.parent.mkdir(parents=True, exist_ok=True)
	config_path.write_text(
		"""
timezone: Asia/Shanghai
runtime:
  output_dir: data/processed/phase0
persona:
  clusters_path: data/processed/persona/clusters.sample.json
traders:
  - trader_id: trader_a
    display_name: Trader A
  - trader_id: trader_b
    display_name: Trader B
""",
		encoding="utf-8",
	)


def test_signal_service_list_signals(tmp_path: Path) -> None:
	"""SignalService 应支持信号列表查询。"""
	from src.services.signal_service import SignalService

	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)
	service = SignalService(
		session_factory=lambda: _FakeDbSessionScope(),
		signal_repository=_FakeDbRepo(
			[
				_FakeDbSignal(
					signal_id="signal-db-1",
					symbol="000001.SZ",
					side="buy",
					confidence=0.88,
					created_at=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
					trader_id="trader_a",
					strategy_version_id="version-1",
					signal_metadata={
						"trader_id": "trader_a",
						"context": {"trend": "up", "score": 0.88},
						"summary": "trend up",
					},
				)
			]
		),
	)

	result = service.list_signals(config_path=config_path, symbol="000001.SZ", since=date(2026, 4, 22), limit=20)

	assert result.status == "ok"
	assert result.payload["source"] == "database"
	assert result.payload["count"] == 1
	assert result.payload["signals"][0]["signal_id"] == "signal-db-1"
	assert result.payload["signals"][0]["trader_id"] == "trader_a"
	assert result.payload["signals"][0]["context"]["trend"] == "up"


def test_signal_service_list_signals_prefers_database(tmp_path: Path) -> None:
	"""SignalService 应优先读取数据库中的信号。"""
	from src.services.signal_service import SignalService

	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)

	service = SignalService(
		session_factory=lambda: _FakeDbSessionScope(),
		signal_repository=_FakeDbRepo(
			[
				_FakeDbSignal(
					signal_id="signal-db-1",
					symbol="000001.SZ",
					side="BUY",
					confidence=0.77,
					created_at=datetime(2026, 4, 23, 9, 30, tzinfo=UTC),
					trader_id="trader_db",
					strategy_version_id="version-db",
					signal_metadata={
						"trader_id": "trader_db",
						"summary": "db trend up",
						"context": {"trend": "up", "score": 0.77},
					},
				)
			]
		),
	)

	result = service.list_signals(config_path=config_path, symbol="000001.SZ", since=date(2026, 4, 22), limit=20)

	assert result.status == "ok"
	assert result.payload["source"] == "database"
	assert result.payload["count"] == 1
	assert result.payload["signals"][0]["signal_id"] == "signal-db-1"
	assert result.payload["signals"][0]["trader_id"] == "trader_db"
	assert result.payload["signals"][0]["context"]["trend"] == "up"


@pytest.mark.asyncio
async def test_persona_service_build_sample_clusters(tmp_path: Path) -> None:
	"""PersonaService 应支持生成样例 clusters 文件。"""
	from src.services.persona_service import PersonaService

	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)

	service = PersonaService()
	result = await service.build_sample_clusters(config_path=config_path)

	assert result.status == "ok"
	assert Path(result.payload["clusters_path"]).exists()
	assert result.payload["trader_count"] == 2
	assert result.payload["clusters_count"] == 6


@pytest.mark.asyncio
async def test_persona_service_build_market_state_from_csv(tmp_path: Path) -> None:
	"""PersonaService 应支持从 benchmark CSV 构建 MarketState。"""
	from src.services.persona_service import PersonaService

	config_path = tmp_path / "config" / "app.yaml"
	_write_basic_config(config_path)
	csv_path = tmp_path / "data" / "processed" / "market_data" / "510300_SH_daily.csv"
	csv_path.parent.mkdir(parents=True, exist_ok=True)
	rows = ["date,close"]
	start = date(2026, 2, 1)
	for i in range(80):
		rows.append(f"{(start + timedelta(days=i)).isoformat()},{3.0 + i * 0.02}")
	csv_path.write_text("\n".join(rows), encoding="utf-8")

	service = PersonaService()
	result = await service.build_market_state(
		config_path=config_path,
		benchmark_symbol="510300.SH",
		as_of="2026-04-15",
		dest=tmp_path / "market_state.json",
	)

	assert result.status == "ok"
	assert result.payload["source"] == "cache"
	assert result.payload["benchmark_symbol"] == "510300.SH"
	assert Path(result.payload["market_state_path"]).exists()
	assert result.payload["market_state"]["as_of_date"] == "2026-04-15"
