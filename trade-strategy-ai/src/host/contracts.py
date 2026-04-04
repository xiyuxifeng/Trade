from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class HostCommand(BaseModel):
	"""Thin-shell command contract.

	This is designed for future Claude Code/Openclaw adapters.
	The host should pass JSON to this contract and receive JSON results.
	"""

	type: Literal[
		"run_pre_market",
		"run_after_close",
		"persona_init_sample",
	]
	config_path: str = "config/app.yaml"
	as_of_date: date | None = None
	force: bool = False
	args: dict[str, Any] = Field(default_factory=dict)


class HostResponse(BaseModel):
	ok: bool = True
	type: str
	payload: dict[str, Any] = Field(default_factory=dict)
	errors: list[str] = Field(default_factory=list)
