from __future__ import annotations

from .system import router as system_router
from api.routers.ui.jobs import router as jobs_router

__all__ = ["jobs_router", "system_router"]
