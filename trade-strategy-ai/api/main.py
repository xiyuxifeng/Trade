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

from api.routers import run, reports, strategy_versions, snapshots, rankings, backtest_results, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    config_path = Path("config/app.yaml")
    if config_path.exists():
        run.set_config_path(config_path)
    yield


app = FastAPI(
    title="Trade Strategy AI API",
    description="交易策略 AI 系统的 HTTP 接口层",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 中间件
# 注意：allow_credentials=True 时不能使用 allow_origins=["*"]
# 生产环境应配置具体的域名列表
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(run.router)
app.include_router(reports.router)
app.include_router(strategy_versions.router)
app.include_router(snapshots.router)
app.include_router(rankings.router)
app.include_router(backtest_results.router)
app.include_router(alerts.router)


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
            "strategy_versions": {
                "list": "GET /strategy_versions/",
                "get": "GET /strategy_versions/{version_id}",
                "download": "GET /strategy_versions/{version_id}/download",
            },
            "snapshots": {
                "list": "GET /snapshots/",
                "get": "GET /snapshots/{snapshot_id}",
                "download": "GET /snapshots/{snapshot_id}/download",
            },
            "rankings": {
                "list": "GET /rankings/",
                "get": "GET /rankings/{entry_id}",
                "download": "GET /rankings/{entry_id}/download",
            },
            "backtest_results": {
                "list": "GET /backtest_results/",
                "get": "GET /backtest_results/{result_id}",
                "report": "GET /backtest_results/{result_id}/report",
                "validate_rules": "GET /backtest_results/{result_id}/validate_rules",
            },
            "alerts": {
                "list_history": "GET /alerts/history",
                "get_history": "GET /alerts/history/{record_id}",
                "acknowledge": "POST /alerts/{record_id}/acknowledge",
                "resolve": "POST /alerts/{record_id}/resolve",
                "test": "POST /alerts/test",
            },
        },
    }


@app.get("/health")
async def health():
    """全局健康检查。"""
    return {"status": "ok"}
