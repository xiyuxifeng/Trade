from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.dependencies import verify_api_key
from api.routers import alerts, backtest_results, rankings, reports, run, snapshots, strategy_versions
from api.routers.ui import artifacts_router as ui_artifacts_router
from api.routers.ui import auth_router as ui_auth_router
from api.routers.ui import imports_router as ui_imports_router
from api.routers.ui import job_audits_router as ui_job_audits_router
from api.routers.ui import jobs_router as ui_jobs_router
from api.routers.ui import data_health_router as ui_data_health_router
from api.routers.ui import kaipan_router as ui_kaipan_router
from api.routers.ui import legacy_system_router as ui_legacy_system_router
from api.routers.ui import market_router as ui_market_router
from api.routers.ui import profiles_router as ui_profiles_router
from api.routers.ui import ops_router as ui_ops_router
from api.routers.ui import optimize_router as ui_optimize_router
from api.routers.ui import pipelines_router as ui_pipelines_router
from api.routers.ui import settings_router as ui_settings_router
from api.routers.ui import persona_router as ui_persona_router
from api.routers.ui import snapshots_router as ui_snapshots_router
from api.routers.ui import rule_pool_router as ui_rule_pool_router
from api.routers.ui import signals_router as ui_signals_router
from api.routers.ui import strategy_studio_router as ui_strategy_studio_router
from api.routers.ui import system_router as ui_system_router
from api.routers.ui.workflows import router as ui_workflows_router
from api.routes import articles_router, market_router, trades_router
from src.common.paths import resolve_project_path
from src.health.routes import health_router


def _resolve_local_web_static_dir() -> Path | None:
    """解析本机静态资源目录。"""
    raw = os.getenv("WEB_STATIC_DIR")
    if not raw:
        return None
    candidate = resolve_project_path(raw)
    index_path = candidate / "index.html"
    if index_path.exists():
        return candidate
    return None


def _is_reserved_local_path(path: str) -> bool:
    """判断路径是否属于 API / docs 等保留入口。"""
    return path in {"docs", "openapi.json", "redoc", "health"} or path.startswith("api/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理，负责初始化运行时配置。"""
    config_path = resolve_project_path("config/app.yaml")
    if config_path.exists():
        run.set_config_path(config_path)
    yield


class HostCommandRequest(BaseModel):
    """主机命令请求体。"""

    type: str
    config_path: str = "config/app.yaml"
    as_of_date: date | None = None
    force: bool = False
    args: dict[str, Any] = Field(default_factory=dict)


def _register_legacy_trigger_routes(app: FastAPI) -> None:
    """注册 legacy 主机命令接口。"""

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
    local_web_static_dir = _resolve_local_web_static_dir()
    local_web_index = local_web_static_dir / "index.html" if local_web_static_dir else None

    app = FastAPI(
        title="Trade Strategy AI API",
        description="交易策略 AI 系统的 HTTP 接口层",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"],
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
    app.include_router(ui_auth_router)
    app.include_router(ui_workflows_router)
    app.include_router(ui_jobs_router)
    app.include_router(ui_pipelines_router)
    app.include_router(ui_artifacts_router)
    app.include_router(ui_market_router)
    app.include_router(ui_profiles_router)
    app.include_router(ui_ops_router)
    app.include_router(ui_optimize_router)
    app.include_router(ui_snapshots_router)
    app.include_router(ui_rule_pool_router)
    app.include_router(ui_strategy_studio_router)
    app.include_router(ui_signals_router)
    app.include_router(ui_persona_router)
    app.include_router(ui_imports_router)
    app.include_router(ui_job_audits_router)
    app.include_router(ui_settings_router)
    app.include_router(ui_kaipan_router)
    app.include_router(ui_data_health_router)
    app.include_router(articles_router)
    app.include_router(trades_router)
    app.include_router(market_router)
    app.include_router(health_router)

    _register_legacy_trigger_routes(app)

    @app.get("/")
    async def root():
        """API 根路径。"""
        if local_web_index is not None:
            return FileResponse(local_web_index)
        return {
            "service": "trade-strategy-ai",
            "version": "0.1.0",
            "docs": "/docs",
        }

    @app.get("/health")
    async def health():
        """全局健康检查。"""
        return {"status": "ok"}

    if local_web_static_dir is not None:

        @app.get("/{path:path}", include_in_schema=False)
        async def web_spa_fallback(path: str):
            """本机静态页面回退入口。"""
            if _is_reserved_local_path(path):
                raise HTTPException(status_code=404, detail="not found")

            candidate = (local_web_static_dir / path).resolve()
            try:
                candidate.relative_to(local_web_static_dir.resolve())
            except ValueError as exc:
                raise HTTPException(status_code=404, detail="not found") from exc

            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate)
            if Path(path).suffix:
                raise HTTPException(status_code=404, detail="not found")
            return FileResponse(local_web_index)

    return app


app = create_app()
