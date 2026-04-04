from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import load_app_config
from src.host.contracts import HostCommand, HostResponse
from src.persona.sample import build_sample_clusters_file
from src.persona.storage import write_persona_clusters_file


def _project_base_dir(config_path: Path) -> Path:
	if config_path.parent.name == "config":
		return config_path.parent.parent
	return config_path.parent


def handle_command(command: dict[str, Any]) -> dict[str, Any]:
	"""Handle a thin-shell JSON command.

	This function intentionally keeps a stable JSON IO surface for host integration.
	"""

	cmd = HostCommand.model_validate(command)
	loaded = load_app_config(cmd.config_path)
	base_dir = _project_base_dir(loaded.config_path)
	mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)
	as_of = cmd.as_of_date or date.today()

	try:
		if cmd.type == "run_pre_market":
			report = asyncio.run(mgr.run_pre_market(as_of_date=as_of, force=cmd.force))
			return HostResponse(type=cmd.type, payload=report.model_dump()).model_dump()
		if cmd.type == "run_after_close":
			result = asyncio.run(mgr.run_after_close(as_of_date=as_of, force=cmd.force))
			return HostResponse(type=cmd.type, payload=result.model_dump()).model_dump()
		if cmd.type == "persona_init_sample":
			trader_ids = [t.trader_id for t in loaded.config.traders]
			clusters = build_sample_clusters_file(trader_ids=trader_ids)
			dest = cmd.args.get("dest") or (loaded.config.persona.clusters_path or "data/processed/persona/clusters.sample.json")
			path = write_persona_clusters_file(path=base_dir / dest if not Path(str(dest)).is_absolute() else dest, data=clusters)
			return HostResponse(type=cmd.type, payload={"clusters_path": str(path)}).model_dump()
		return HostResponse(ok=False, type=cmd.type, errors=[f"Unknown command type: {cmd.type}"]).model_dump()
	except Exception as exc:  # noqa: BLE001
		return HostResponse(ok=False, type=cmd.type, errors=[str(exc)]).model_dump()
