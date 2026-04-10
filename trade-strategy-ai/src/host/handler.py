from __future__ import annotations

import asyncio
import warnings
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


def _handle_persona_init_sample(cmd: HostCommand, mgr: ManagerAgent, base_dir: Path) -> dict[str, Any]:
	"""Handle persona_init_sample command (同步函数，供 sync/async 共同使用)."""
	trader_ids = [t.trader_id for t in mgr.config.traders]
	clusters = build_sample_clusters_file(trader_ids=trader_ids)
	dest = cmd.args.get("dest") or (
		mgr.config.persona.clusters_path
		or "data/processed/persona/clusters.sample.json"
	)
	path = write_persona_clusters_file(
		path=base_dir / dest if not Path(str(dest)).is_absolute() else dest,
		data=clusters,
	)
	return HostResponse(type=cmd.type, payload={"clusters_path": str(path)}).model_dump()


def _dispatch_command(cmd: HostCommand, mgr: ManagerAgent, base_dir: Path) -> dict[str, Any]:
	"""Dispatch a command to the appropriate handler and return a serialized response.

	This is the common dispatch logic used by both async and sync handlers.
	"""
	as_of = cmd.as_of_date or date.today()
	try:
		if cmd.type == "run_pre_market":
			report = mgr.run_pre_market(as_of_date=as_of, force=cmd.force)
			if asyncio.iscoroutine(report):
				report = asyncio.run(report)
			return HostResponse(type=cmd.type, payload=report.model_dump()).model_dump()
		if cmd.type == "run_after_close":
			result = mgr.run_after_close(as_of_date=as_of, force=cmd.force)
			if asyncio.iscoroutine(result):
				result = asyncio.run(result)
			return HostResponse(type=cmd.type, payload=result.model_dump()).model_dump()
		if cmd.type == "persona_init_sample":
			return _handle_persona_init_sample(cmd, mgr, base_dir)
		return HostResponse(
			ok=False, type=cmd.type, errors=[f"Unknown command type: {cmd.type}"]
		).model_dump()
	except Exception as exc:
		return HostResponse(ok=False, type=cmd.type, errors=[str(exc)]).model_dump()


async def handle_command_async(command: dict[str, Any]) -> dict[str, Any]:
	"""Async handler for FastAPI integration.

	This is the preferred entry point for FastAPI routes.
	"""
	cmd = HostCommand.model_validate(command)
	loaded = load_app_config(cmd.config_path)
	base_dir = _project_base_dir(loaded.config_path)
	mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)
	return await _dispatch_command_async(cmd, mgr, base_dir)


async def _dispatch_command_async(cmd: HostCommand, mgr: ManagerAgent, base_dir: Path) -> dict[str, Any]:
	"""Async dispatch logic - awaits async coroutines instead of running them in asyncio.run()."""
	as_of = cmd.as_of_date or date.today()
	try:
		if cmd.type == "run_pre_market":
			report = await mgr.run_pre_market(as_of_date=as_of, force=cmd.force)
			return HostResponse(type=cmd.type, payload=report.model_dump()).model_dump()
		if cmd.type == "run_after_close":
			result = await mgr.run_after_close(as_of_date=as_of, force=cmd.force)
			return HostResponse(type=cmd.type, payload=result.model_dump()).model_dump()
		if cmd.type == "persona_init_sample":
			return _handle_persona_init_sample(cmd, mgr, base_dir)
		return HostResponse(
			ok=False, type=cmd.type, errors=[f"Unknown command type: {cmd.type}"]
		).model_dump()
	except Exception as exc:
		return HostResponse(ok=False, type=cmd.type, errors=[str(exc)]).model_dump()


def handle_command(command: dict[str, Any]) -> dict[str, Any]:
	"""Handle a thin-shell JSON command.

	.. deprecated::
		Use :func:`handle_command_async` instead. This synchronous version
		will be removed once all callers migrate to the async interface.
	"""
	warnings.warn(
		"handle_command is deprecated, use handle_command_async instead",
		DeprecationWarning,
		stacklevel=2,
	)

	cmd = HostCommand.model_validate(command)
	loaded = load_app_config(cmd.config_path)
	base_dir = _project_base_dir(loaded.config_path)
	mgr = ManagerAgent(config=loaded.config, base_dir=base_dir)
	return _dispatch_command(cmd, mgr, base_dir)
