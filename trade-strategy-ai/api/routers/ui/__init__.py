from __future__ import annotations

from .artifacts import router as artifacts_router
from .authors import router as authors_router
from .auth import router as auth_router
from .daily_pre_market import router as daily_pre_market_router
from .imports import router as imports_router
from .kaipan import router as kaipan_router
from .data_health import router as data_health_router
from .data_audits import router as data_audits_router
from .article_metadata import router as article_metadata_router
from .persona import router as persona_router
from .pipelines import router as pipelines_router
from .signals import router as signals_router
from .market import router as market_router
from .profiles import router as profiles_router
from .snapshots import router as snapshots_router
from .settings import router as settings_router
from .ops import router as ops_router
from .optimize import router as optimize_router
from .traders import router as traders_router
from .security_audit import router as security_audit_router
from .strategies import router as strategies_router
from .strategy_studio import router as strategy_studio_router
from .job_audits import router as job_audits_router
from .rule_pool import router as rule_pool_router
from .rule_lifecycle import router as rule_lifecycle_router
from .rule_review import router as rule_review_router
from .formal_backtests import router as formal_backtests_router
from .system import legacy_router as legacy_system_router
from .system import router as system_router
from api.routers.ui.jobs import router as jobs_router

__all__ = [
    "artifacts_router",
    "authors_router",
    "auth_router",
    "daily_pre_market_router",
    "imports_router",
    "job_audits_router",
    "jobs_router",
    "kaipan_router",
    "data_health_router",
    "data_audits_router",
    "article_metadata_router",
    "legacy_system_router",
    "market_router",
    "profiles_router",
    "persona_router",
    "pipelines_router",
    "settings_router",
    "ops_router",
    "optimize_router",
    "traders_router",
    "security_audit_router",
    "strategies_router",
    "snapshots_router",
    "signals_router",
    "rule_pool_router",
    "rule_lifecycle_router",
    "rule_review_router",
    "formal_backtests_router",
    "strategy_studio_router",
    "system_router",
]
