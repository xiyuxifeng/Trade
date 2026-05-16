from __future__ import annotations

from .artifacts import router as artifacts_router
from .auth import router as auth_router
from .imports import router as imports_router
from .kaipan import router as kaipan_router
from .data_health import router as data_health_router
from .persona import router as persona_router
from .pipelines import router as pipelines_router
from .signals import router as signals_router
from .market import router as market_router
from .profiles import router as profiles_router
from .snapshots import router as snapshots_router
from .settings import router as settings_router
from .ops import router as ops_router
from .strategy_studio import router as strategy_studio_router
from .system import legacy_router as legacy_system_router
from .system import router as system_router
from api.routers.ui.jobs import router as jobs_router

__all__ = [
    "artifacts_router",
    "auth_router",
    "imports_router",
    "jobs_router",
    "kaipan_router",
    "data_health_router",
    "legacy_system_router",
    "market_router",
    "profiles_router",
    "persona_router",
    "pipelines_router",
    "settings_router",
    "ops_router",
    "snapshots_router",
    "signals_router",
    "strategy_studio_router",
    "system_router",
]
