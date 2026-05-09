from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.dependencies import verify_api_key
from api.routers import alerts, backtest_results, rankings, reports, run, snapshots, strategy_versions
from api.routers.ui import artifacts_router as ui_artifacts_router
from api.routers.ui import jobs_router as ui_jobs_router
from api.routers.ui import legacy_system_router as ui_legacy_system_router
from api.routers.ui import market_router as ui_market_router
from api.routers.ui import snapshots_router as ui_snapshots_router
from api.routers.ui import system_router as ui_system_router
from api.routers.ui.workflows import router as ui_workflows_router
from api.routes import articles_router, market_router, trades_router
from src.common.paths import resolve_project_path
from src.health.routes import health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理，负责初始化运行时配置。"""
    config_path = resolve_project_path("config/app.yaml")
    if config_path.exists():
        run.set_config_path(config_path)
    yield


class RunTriggerRequest(BaseModel):
    """手动触发运行任务的请求体。"""

    config_path: str = "config/app.yaml"
    as_of_date: date | None = None
    force: bool = False
    args: dict[str, Any] = Field(default_factory=dict)


class HostCommandRequest(BaseModel):
    """主机命令请求体。"""

    type: str
    config_path: str = "config/app.yaml"
    as_of_date: date | None = None
    force: bool = False
    args: dict[str, Any] = Field(default_factory=dict)


def _register_legacy_trigger_routes(app: FastAPI) -> None:
    """注册 legacy 运行触发接口。"""

    @app.post("/run/pre_market")
    async def trigger_pre_market(
        request: RunTriggerRequest,
        _: str = Depends(verify_api_key),
    ):
        """触发盘前分析。"""
        from src.host.handler import handle_command_async

        command = {
            "type": "run_pre_market",
            "config_path": request.config_path,
            "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
            "force": request.force,
            "args": request.args,
        }
        return await handle_command_async(command)

    @app.post("/run/after_close")
    async def trigger_after_close(
        request: RunTriggerRequest,
        _: str = Depends(verify_api_key),
    ):
        """触发盘后考核。"""
        from src.host.handler import handle_command_async

        command = {
            "type": "run_after_close",
            "config_path": request.config_path,
            "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
            "force": request.force,
            "args": request.args,
        }
        return await handle_command_async(command)

    @app.post("/host/command")
    async def host_command(
        request: HostCommandRequest,
        _: str = Depends(verify_api_key),
    ):
        """通用 host 命令入口。"""
        from src.host.handler import handle_command_async

        command = {
            "type": request.type,
            "config_path": request.config_path,
            "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
            "force": request.force,
            "args": request.args,
        }
        return await handle_command_async(command)


def create_app() -> FastAPI:
    """构建并返回统一的 FastAPI 应用。"""
    app = FastAPI(
        title="Trade Strategy AI API",
        description="交易策略 AI 系统的 HTTP 接口层",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(run.router)
    app.include_router(reports.router)
    app.include_router(strategy_versions.router)
    app.include_router(snapshots.router)
    app.include_router(rankings.router)
    app.include_router(backtest_results.router)
    app.include_router(alerts.router)
    app.include_router(ui_system_router)
    app.include_router(ui_legacy_system_router)
    app.include_router(ui_workflows_router)
    app.include_router(ui_jobs_router)
    app.include_router(ui_artifacts_router)
    app.include_router(ui_market_router)
    app.include_router(ui_snapshots_router)
    app.include_router(articles_router)
    app.include_router(trades_router)
    app.include_router(market_router)
    app.include_router(health_router)

    _register_legacy_trigger_routes(app)

    @app.get("/")
    async def root():
        """API 根路径。"""
        return {
            "service": "trade-strategy-ai",
            "version": "0.1.0",
            "docs": "/docs",
        }

    @app.get("/health")
    async def health():
        """全局健康检查。"""
        return {"status": "ok"}

    return app


app = create_app()
