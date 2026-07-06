from __future__ import annotations

import asyncio


class JobScopedModelSelector:
    """Tracks the currently usable model within a single job run."""

    def __init__(self, models: list[str]) -> None:
        normalized = [model.strip() for model in models if isinstance(model, str) and model.strip()]
        if not normalized:
            raise ValueError("at least one model is required")
        self._models = normalized
        self._current_index = 0
        self._unavailable: set[str] = set()
        self._lock = asyncio.Lock()

    async def current_model(self) -> str:
        async with self._lock:
            return self._resolve_current_locked()

    async def mark_success(self, model: str) -> None:
        async with self._lock:
            if model not in self._models:
                return
            self._unavailable.discard(model)
            self._current_index = self._models.index(model)

    async def mark_unavailable(self, model: str) -> str | None:
        async with self._lock:
            if model in self._models:
                self._unavailable.add(model)
            return self._advance_locked()

    def _resolve_current_locked(self) -> str:
        if self._models[self._current_index] not in self._unavailable:
            return self._models[self._current_index]
        next_model = self._advance_locked()
        return next_model or self._models[self._current_index]

    def _advance_locked(self) -> str | None:
        for index, candidate in enumerate(self._models):
            if candidate not in self._unavailable:
                self._current_index = index
                return candidate
        return None
