from __future__ import annotations

from .artifacts import router as artifacts_router
from .market import router as market_router
from .system import legacy_router as legacy_system_router
from .system import router as system_router
from api.routers.ui.jobs import router as jobs_router

__all__ = [
    "artifacts_router",
    "jobs_router",
    "legacy_system_router",
    "market_router",
    "system_router",
]
