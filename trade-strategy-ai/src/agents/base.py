from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from src.common.logger import get_logger


SkillCallable = Callable[..., Any] | Callable[..., Awaitable[Any]]


class BaseAgent:
	def __init__(self, name: str) -> None:
		self.name = name
		self._skills: dict[str, SkillCallable] = {}
		self.logger = get_logger(f"agent.{name}")

	def register_skill(self, name: str, skill: SkillCallable) -> None:
		self._skills[name] = skill

	def list_skills(self) -> list[str]:
		return sorted(self._skills.keys())

	async def call_skill(self, name: str, **kwargs: Any) -> Any:
		if name not in self._skills:
			raise KeyError(f"Skill not found: {name}")

		fn = self._skills[name]
		if inspect.iscoroutinefunction(fn):
			return await fn(**kwargs)

		result = fn(**kwargs)
		if inspect.isawaitable(result):
			return await result
		return result
