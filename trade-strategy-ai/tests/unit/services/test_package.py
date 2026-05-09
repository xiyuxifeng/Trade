from __future__ import annotations


def test_services_package_exposes_web_service_entrypoints() -> None:
    """服务层包应提供 Web 后续要使用的基础导出。"""
    import src.services as services

    assert set(services.__all__) == {
        "BaseService",
        "ArtifactService",
        "BacktestService",
        "DashboardService",
        "ServiceResult",
        "ConfigService",
        "JobService",
        "JobRunner",
        "MarketService",
        "KaipanService",
        "PersonaService",
        "OptimizeService",
        "PipelineService",
        "SignalService",
        "RulePoolService",
        "SetupService",
        "RunService",
        "WorkflowService",
        "SnapshotService",
        "StrategyService",
        "SystemService",
    }
    assert issubclass(services.ConfigService, services.BaseService)
    assert issubclass(services.ArtifactService, services.BaseService)
    assert issubclass(services.BacktestService, services.BaseService)
    assert issubclass(services.DashboardService, services.BaseService)
    assert issubclass(services.JobService, services.BaseService)
    assert issubclass(services.JobRunner, services.BaseService)
    assert issubclass(services.MarketService, services.BaseService)
    assert issubclass(services.KaipanService, services.BaseService)
    assert issubclass(services.PersonaService, services.BaseService)
    assert issubclass(services.OptimizeService, services.BaseService)
    assert issubclass(services.PipelineService, services.BaseService)
    assert issubclass(services.SignalService, services.BaseService)
    assert issubclass(services.RulePoolService, services.BaseService)
    assert issubclass(services.SetupService, services.BaseService)
    assert issubclass(services.RunService, services.BaseService)
    assert issubclass(services.SnapshotService, services.BaseService)
    assert issubclass(services.StrategyService, services.BaseService)
    assert issubclass(services.SystemService, services.BaseService)


def test_service_result_is_structured_and_render_free() -> None:
    """服务返回值应是结构化对象，不直接绑定终端输出。"""
    from src.services import ServiceResult

    result = ServiceResult(message="ok", payload={"count": 1}, warnings=["warn"])

    assert result.status == "ok"
    assert result.message == "ok"
    assert result.payload == {"count": 1}
    assert result.warnings == ["warn"]
