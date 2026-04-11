"""FastAPI 应用入口。

整合所有路由：
- /run: 手动触发接口（盘前日报/盘后考核）
- /reports: 报告查询接口
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import run, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时设置配置路径
    config_path = Path("config/app.yaml")
    if config_path.exists():
        run.set_config_path(config_path)
    yield
    # 关闭时清理资源（如有）


app = FastAPI(
    title="Trade Strategy AI API",
    description="交易策略 AI 系统的 HTTP 接口层",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(run.router)
app.include_router(reports.router)


@app.get("/")
async def root():
    """API 根路径。"""
    return {
        "service": "trade-strategy-ai",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "run": {
                "pre_market": "POST /run/pre_market",
                "after_close": "POST /run/after_close",
                "health": "GET /run/health",
            },
            "reports": {
                "list_daily": "GET /reports/daily",
                "get_daily": "GET /reports/daily/{date}",
                "daily_html": "GET /reports/daily/{date}/html",
                "list_evaluation": "GET /reports/evaluation",
                "get_evaluation": "GET /reports/evaluation/{date}",
                "evaluation_html": "GET /reports/evaluation/{date}/html",
            },
        },
    }


@app.get("/health")
async def health():
    """全局健康检查。"""
    return {"status": "ok"}
