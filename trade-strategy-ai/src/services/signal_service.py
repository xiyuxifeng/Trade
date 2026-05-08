from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from src.common.config import load_app_config
from src.common.utils import ensure_dir
from src.services.base import BaseService, ServiceResult
from src.strategy.signal_version import SignalVersioning


def _project_base_dir(config_path: Path) -> Path:
	"""根据配置文件路径推导项目根目录。"""
	if config_path.parent.name == "config":
		return config_path.parent.parent
	return config_path.parent


def _to_plain(value: Any) -> Any:
	"""把 dataclass / Pydantic / 容器值转成可序列化结构。"""
	if hasattr(value, "model_dump"):
		return _to_plain(value.model_dump())
	if is_dataclass(value):
		return {k: _to_plain(v) for k, v in asdict(value).items()}
	if isinstance(value, dict):
		return {k: _to_plain(v) for k, v in value.items()}
	if isinstance(value, (list, tuple)):
		return [_to_plain(item) for item in value]
	if isinstance(value, Enum):
		return value.value
	if isinstance(value, (datetime, date)):
		return value.isoformat()
	if isinstance(value, Path):
		return str(value)
	return value


class SignalService(BaseService):
	"""信号版本查询服务。"""

	service_name = "signal"

	def __init__(self, *, versioning: SignalVersioning | None = None) -> None:
		self._versioning = versioning

	def _create_versioning(self, *, config_path: str | Path) -> tuple[SignalVersioning, Path, Path]:
		"""根据配置创建 SignalVersioning。"""
		loaded = load_app_config(config_path)
		base_dir = _project_base_dir(loaded.config_path)
		output_dir = ensure_dir(base_dir / loaded.config.storage.output_dir)
		versioning = self._versioning or SignalVersioning(storage_path=output_dir / "signals")
		return versioning, loaded.config_path, base_dir

	def list_signals(
		self,
		*,
		config_path: str | Path,
		symbol: str | None = None,
		since: str | date | datetime | None = None,
		limit: int = 100,
	) -> ServiceResult:
		"""列出已存储的信号版本。"""
		versioning, loaded_config_path, base_dir = self._create_versioning(config_path=config_path)
		since_dt: datetime | None
		if since is None:
			since_dt = None
		elif isinstance(since, datetime):
			since_dt = since
		elif isinstance(since, date):
			since_dt = datetime.combine(since, datetime.min.time())
		else:
			since_dt = datetime.fromisoformat(since)

		versions = versioning.list_versions(symbol=symbol, since=since_dt, limit=limit)
		signals = [
			{
				"signal_id": item.signal.signal_id,
				"symbol": item.signal.symbol,
				"side": _to_plain(item.signal.side),
				"confidence": item.signal.confidence,
				"timestamp": item.signal.timestamp.isoformat(),
				"trader_id": item.signal.metadata.get("trader_id"),
				"strategy_version_id": item.signal.strategy_version_id,
				"context": _to_plain(item.context),
			}
			for item in versions
		]
		return ServiceResult(
			status="ok",
			message="signals listed" if signals else "no signals found",
			payload={
				"config_path": str(loaded_config_path),
				"base_dir": str(base_dir),
				"count": len(signals),
				"signals": signals,
			},
		)
