"""Web 管理后台和 CLI 共用的服务层入口。

本阶段只建立基础约定：
- 服务不依赖 Typer
- 服务不直接输出终端文本
- 服务返回结构化结果
"""

from src.services.artifact_service import ArtifactService
from src.services.base import BaseService, ServiceResult
from src.services.backtest_service import BacktestService
from src.services.config_edit_service import ConfigEditService
from src.services.config_migration_service import ConfigMigrationService
from src.services.config_profile_service import ConfigProfileService
from src.services.config_snapshot_service import ConfigSnapshotService
from src.services.dashboard_service import DashboardService
from src.services.data_audit_query_service import DataAuditQueryService
from src.services.config_service import ConfigService
from src.services.job_service import JobService
from src.services.job_audit_query_service import JobAuditQueryService
from src.services.job_runner import JobRunner
from src.services.kaipan_service import KaipanService
from src.services.market_service import MarketService
from src.services.market_data_storage_service import MarketDataStorageService
from src.services.market_snapshot_service import MarketSnapshotService
from src.services.market_snapshot_query_service import MarketSnapshotQueryService
from src.services.market_regime_service import MarketRegimeService
from src.services.market_regime_feature_service import MarketRegimeFeatureService
from src.services.rule_applicability_service import RuleApplicabilityService
from src.services.regime_rule_selection_service import RegimeRuleSelectionService
from src.services.optimize_service import OptimizeService
from src.services.pipeline_application_service import PipelineApplicationService
from src.services.persona_service import PersonaService
from src.services.pipeline_service import PipelineService
from src.services.signal_service import SignalService
from src.services.security_audit_query_service import SecurityAuditQueryService
from src.services.rule_pool_service import RulePoolService
from src.services.setup_service import SetupService
from src.services.step_timeline_service import StepTimelineService
from src.services.run_service import RunService
from src.services.workflow_run_service import WorkflowRunService
from src.services.workflow_runner import WorkflowRunner
from src.services.workflow_service import WorkflowService
from src.services.snapshot_service import SnapshotService
from src.services.strategy_service import StrategyService
from src.services.system_service import SystemService

__all__ = [
    "BaseService",
    "ServiceResult",
    "ArtifactService",
    "BacktestService",
    "ConfigEditService",
    "ConfigMigrationService",
    "ConfigProfileService",
    "ConfigSnapshotService",
    "DashboardService",
    "DataAuditQueryService",
    "ConfigService",
    "JobService",
    "JobAuditQueryService",
    "JobRunner",
    "SystemService",
    "RunService",
    "WorkflowRunner",
    "WorkflowRunService",
    "WorkflowService",
    "PipelineService",
    "SnapshotService",
    "MarketService",
    "MarketDataStorageService",
    "MarketSnapshotService",
    "MarketSnapshotQueryService",
    "MarketRegimeService",
    "MarketRegimeFeatureService",
    "RegimeRuleSelectionService",
    "RuleApplicabilityService",
    "StrategyService",
    "PersonaService",
    "SignalService",
    "KaipanService",
    "SecurityAuditQueryService",
    "OptimizeService",
    "PipelineApplicationService",
    "RulePoolService",
    "SetupService",
    "StepTimelineService",
]
