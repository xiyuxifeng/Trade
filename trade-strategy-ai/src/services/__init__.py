"""Web 管理后台和 CLI 共用的服务层入口。

说明：
- 这里只提供统一命名空间，不在包导入阶段 eager 加载整棵服务树。
- 这样可以避免 ManagerAgent / JobRunner / PipelineApplicationService
  等互相依赖的模块在 import 阶段形成循环引用。
- 需要具体服务时，使用 `from src.services import FooService`，
  由本模块按需加载并缓存到全局命名空间。
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from src.services.base import BaseService, ServiceResult

_LAZY_EXPORTS: dict[str, str] = {
    "ArtifactService": "src.services.artifact_service",
    "BacktestService": "src.services.backtest_service",
    "ConfigEditService": "src.services.config_edit_service",
    "ConfigMigrationService": "src.services.config_migration_service",
    "ConfigProfileService": "src.services.config_profile_service",
    "ConfigSnapshotService": "src.services.config_snapshot_service",
    "DashboardService": "src.services.dashboard_service",
    "DataAuditQueryService": "src.services.data_audit_query_service",
    "ConfigService": "src.services.config_service",
    "JobService": "src.services.job_service",
    "JobAuditQueryService": "src.services.job_audit_query_service",
    "JobRunner": "src.services.job_runner",
    "SystemService": "src.services.system_service",
    "RunService": "src.services.run_service",
    "WorkflowRunner": "src.services.workflow_runner",
    "WorkflowRunService": "src.services.workflow_run_service",
    "WorkflowService": "src.services.workflow_service",
    "PipelineService": "src.services.pipeline_service",
    "PipelineApplicationService": "src.services.pipeline_application_service",
    "SnapshotService": "src.services.snapshot_service",
    "MarketService": "src.services.market_service",
    "MarketDataStorageService": "src.services.market_data_storage_service",
    "MarketSnapshotService": "src.services.market_snapshot_service",
    "MarketSnapshotQueryService": "src.services.market_snapshot_query_service",
    "MarketRegimeService": "src.services.market_regime_service",
    "MarketRegimeFeatureService": "src.services.market_regime_feature_service",
    "RegimeRuleSelectionService": "src.services.regime_rule_selection_service",
    "RuleApplicabilityService": "src.services.rule_applicability_service",
    "StrategyService": "src.services.strategy_service",
    "PersonaService": "src.services.persona_service",
    "SignalService": "src.services.signal_service",
    "KaipanService": "src.services.kaipan_service",
    "SecurityAuditQueryService": "src.services.security_audit_query_service",
    "OptimizeService": "src.services.optimize_service",
    "RulePoolService": "src.services.rule_pool_service",
    "SetupService": "src.services.setup_service",
    "StepTimelineService": "src.services.step_timeline_service",
}

__all__ = [
    "BaseService",
    "ServiceResult",
    *sorted(_LAZY_EXPORTS.keys()),
]


def __getattr__(name: str) -> Any:
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_path)
    value = getattr(module, name)
    globals()[name] = value
    return value
