from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse

from api.dependencies import describe_api_key
from api.routers import alerts, backtest_results, rankings, reports, snapshots, strategy_versions
from api.routers.ui import artifacts_router as ui_artifacts_router
from api.routers.ui import auth_router as ui_auth_router
from api.routers.ui import imports_router as ui_imports_router
from api.routers.ui import job_audits_router as ui_job_audits_router
from api.routers.ui import jobs_router as ui_jobs_router
from api.routers.ui import data_health_router as ui_data_health_router
from api.routers.ui import data_audits_router as ui_data_audits_router
from api.routers.ui import article_metadata_router as ui_article_metadata_router
from api.routers.ui import kaipan_router as ui_kaipan_router
from api.routers.ui import legacy_system_router as ui_legacy_system_router
from api.routers.ui import market_router as ui_market_router
from api.routers.ui import profiles_router as ui_profiles_router
from api.routers.ui import ops_router as ui_ops_router
from api.routers.ui import optimize_router as ui_optimize_router
from api.routers.ui import security_audit_router as ui_security_audit_router
from api.routers.ui import pipelines_router as ui_pipelines_router
from api.routers.ui import traders_router as ui_traders_router
from api.routers.ui import persona_router as ui_persona_router
from api.routers.ui import snapshots_router as ui_snapshots_router
from api.routers.ui import rule_pool_router as ui_rule_pool_router
from api.routers.ui import signals_router as ui_signals_router
from api.routers.ui import strategy_studio_router as ui_strategy_studio_router
from api.routers.ui import system_router as ui_system_router
from api.routers.ui.workflows import router as ui_workflows_router
from api.routes import articles_router, market_router, trades_router
from src.common.paths import resolve_project_path
from src.common.config import ConfigError
from src.common.logger import bind_log_context, configure_logging, get_logger
from src.audit.service import AuditService
from src.health.routes import health_router

logger = get_logger(__name__)


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
    configure_logging()
    yield


def get_audit_service() -> AuditService:
    """返回用于记录安全审计的服务实例。"""
    return AuditService()


def _permission_denied_actor(request: Request) -> dict[str, Any]:
    """把 403 请求整理成可审计的公开身份信息。"""
    api_key = request.headers.get("X-API-Key")
    principal = describe_api_key(api_key)
    if principal is not None:
        return principal

    return {
        "role": "anonymous" if not api_key else "api_key",
        "api_key_label": None,
        "authenticated": False,
        "source": "anonymous" if not api_key else "api_key",
    }


async def _record_permission_denied(request: Request, exc: HTTPException) -> None:
    """把 403 请求记录为只读安全日志。"""
    if exc.status_code != 403:
        return

    actor = _permission_denied_actor(request)
    payload = {
        "request": {
            "method": request.method,
            "path": request.url.path,
        },
        "response": {
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
        "principal": actor,
    }
    source = "ui" if request.url.path.startswith("/api/ui/") else "api"
    try:
        await get_audit_service().record(
            event_type="permission_denied",
            actor=str(actor.get("api_key_label") or actor.get("role") or "anonymous"),
            entity_type="http_request",
            entity_id=f"{request.method} {request.url.path}",
            dataset_version=None,
            payload=payload,
            source=source,
        )
    except Exception:
        return


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

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        """给每个请求注入 request_id，并记录简要请求日志。"""
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()
        with bind_log_context(request_id=request_id):
            try:
                response = await call_next(request)
            except Exception:
                duration_ms = (time.perf_counter() - started_at) * 1000.0
                logger.exception(
                    "request failed method=%s path=%s duration_ms=%.2f",
                    request.method,
                    request.url.path,
                    duration_ms,
                )
                raise
            duration_ms = (time.perf_counter() - started_at) * 1000.0
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request completed method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
        return response

    app.include_router(reports.router)
    app.include_router(strategy_versions.router)
    app.include_router(snapshots.router)
    app.include_router(rankings.router)
    app.include_router(backtest_results.router)
    app.include_router(alerts.router)
    app.include_router(ui_system_router)
    app.include_router(ui_legacy_system_router)
    app.include_router(ui_auth_router)
    app.include_router(ui_imports_router)
    app.include_router(ui_workflows_router)
    app.include_router(ui_jobs_router)
    app.include_router(ui_pipelines_router)
    app.include_router(ui_artifacts_router)
    app.include_router(ui_market_router)
    app.include_router(ui_profiles_router)
    app.include_router(ui_ops_router)
    app.include_router(ui_optimize_router)
    app.include_router(ui_traders_router)
    app.include_router(ui_security_audit_router)
    app.include_router(ui_snapshots_router)
    app.include_router(ui_rule_pool_router)
    app.include_router(ui_strategy_studio_router)
    app.include_router(ui_signals_router)
    app.include_router(ui_persona_router)
    app.include_router(ui_job_audits_router)
    app.include_router(ui_kaipan_router)
    app.include_router(ui_data_health_router)
    app.include_router(ui_data_audits_router)
    app.include_router(ui_article_metadata_router)
    app.include_router(articles_router)
    app.include_router(trades_router)
    app.include_router(market_router)
    app.include_router(health_router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """统一处理 HTTPException，并记录 403 访问拒绝日志。"""
        await _record_permission_denied(request, exc)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(ConfigError)
    async def config_error_handler(_request: Request, exc: ConfigError):
        """把可配置项缺失转成 400，提示用户补配置而不是 500。"""
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc) or "configuration error"},
        )

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
                raise HTTPException(status_code=404, detail="未找到页面")

            candidate = (local_web_static_dir / path).resolve()
            try:
                candidate.relative_to(local_web_static_dir.resolve())
            except ValueError as exc:
                raise HTTPException(status_code=404, detail="未找到页面") from exc

            if candidate.exists() and candidate.is_file():
                return FileResponse(candidate)
            if Path(path).suffix:
                raise HTTPException(status_code=404, detail="未找到页面")
            return FileResponse(local_web_index)

    return app


app = create_app()
