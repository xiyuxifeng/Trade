"""手动触发接口：盘前日报 / 盘后考核。

P1-032: 实现手动触发接口 /run/pre_market、/run/after_close
"""

from __future__ import annotations

import asyncio
import threading
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.agents.manager_agent.agent import ManagerAgent
from src.common.config import load_app_config
from src.common.paths import resolve_project_path
from src.schemas.contracts import DailyReport, EvaluationResult

router = APIRouter(prefix="/run", tags=["run"])


# ============================================================================
# 线程安全的 ManagerAgent 单例
# ============================================================================

_config_path: Path | None = None
_manager_agent: ManagerAgent | None = None
_manager_lock = threading.Lock()


def get_config_path() -> Path:
    """获取配置文件路径。"""
    global _config_path
    if _config_path is None:
        _config_path = resolve_project_path("config/app.yaml")
    return resolve_project_path(_config_path)


def set_config_path(path: Path) -> None:
    """设置配置文件路径（在应用启动时调用）。"""
    global _config_path
    _config_path = resolve_project_path(path)


def get_base_dir() -> Path:
    """获取项目根目录。"""
    config_path = get_config_path()
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


def get_manager_agent() -> ManagerAgent:
    """获取或创建 ManagerAgent 实例（线程安全）。"""
    global _manager_agent
    if _manager_agent is None:
        with _manager_lock:
            # 双重检查锁定
            if _manager_agent is None:
                config_path = get_config_path()
                base_dir = get_base_dir()
                loaded = load_app_config(config_path)
                _manager_agent = ManagerAgent(config=loaded.config, base_dir=base_dir)
    return _manager_agent


def get_timeout_seconds() -> float:
    """获取运行超时配置。"""
    config_path = get_config_path()
    loaded = load_app_config(config_path)
    return loaded.config.api.timeout_seconds


# ============================================================================
# 请求/响应模型
# ============================================================================

class RunPreMarketRequest(BaseModel):
    """盘前触发请求。"""
    as_of_date: date | None = Field(default=None, description="指定日期，默认今天")
    force: bool = Field(default=False, description="强制重跑并覆盖输出")
    export_html: bool = Field(default=False, description="同时导出 HTML 日报")


class RunAfterCloseRequest(BaseModel):
    """盘后触发请求。"""
    as_of_date: date | None = Field(default=None, description="指定日期，默认今天")
    force: bool = Field(default=False, description="强制重跑并覆盖输出")
    export_html: bool = Field(default=False, description="同时导出 HTML 考核报告")


class RunPreMarketResponse(BaseModel):
    """盘前触发响应。"""
    status: str = "success"
    as_of_date: date
    ideas_count: int = Field(description="生成的交易想法数量")
    output_dir: str = Field(description="输出目录")
    html_path: str | None = Field(default=None, description="HTML 日报路径（如果请求导出）")
    report: DailyReport | None = Field(default=None, description="完整日报数据")


class RunAfterCloseResponse(BaseModel):
    """盘后触发响应。"""
    status: str = "success"
    as_of_date: date
    evaluations_count: int = Field(description="评估数量")
    output_dir: str = Field(description="输出目录")
    html_path: str | None = Field(default=None, description="HTML 考核报告路径（如果请求导出）")
    result: EvaluationResult | None = Field(default=None, description="完整考核数据")


# ============================================================================
# API 端点
# ============================================================================

@router.post(
    "/pre_market",
    response_model=RunPreMarketResponse,
    responses={
        200: {"description": "盘前日报生成成功"},
        400: {"description": "请求参数错误"},
        404: {"description": "配置文件未找到"},
        408: {"description": "请求超时"},
        500: {"description": "服务器内部错误"},
    },
)
async def run_pre_market(
    request: RunPreMarketRequest | None = None,
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> RunPreMarketResponse:
    """触发盘前日报生成。

    收集所有 TraderAgent 的交易想法，生成当日的盘前日报。
    支持指定日期（默认今天）、强制重跑、HTML 导出。
    """
    if request is None:
        request = RunPreMarketRequest()

    as_of_date = request.as_of_date or date.today()
    timeout = get_timeout_seconds()

    try:
        if timeout > 0:
            async with asyncio.timeout(timeout):
                report = await mgr.run_pre_market(as_of_date=as_of_date, force=request.force)
        else:
            report = await mgr.run_pre_market(as_of_date=as_of_date, force=request.force)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"盘前日报生成超时（{timeout}秒）",
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"缺少前置数据: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="盘前日报生成失败",
        )

    html_path = None
    if request.export_html:
        html_path = str(mgr.export_daily_report_html(report=report))

    return RunPreMarketResponse(
        status="success",
        as_of_date=as_of_date,
        ideas_count=len(report.ideas),
        output_dir=str(mgr.output_dir),
        html_path=html_path,
        report=report,
    )


@router.post(
    "/after_close",
    response_model=RunAfterCloseResponse,
    responses={
        200: {"description": "盘后考核生成成功"},
        400: {"description": "请求参数错误"},
        404: {"description": "配置文件未找到或缺少盘前日报"},
        408: {"description": "请求超时"},
        500: {"description": "服务器内部错误"},
    },
)
async def run_after_close(
    request: RunAfterCloseRequest | None = None,
    mgr: ManagerAgent = Depends(get_manager_agent),
) -> RunAfterCloseResponse:
    """触发盘后考核生成。

    基于盘前日报中的交易想法，结合当前价格进行考核评估。
    支持指定日期（默认今天）、强制重跑、HTML 导出。
    """
    if request is None:
        request = RunAfterCloseRequest()

    as_of_date = request.as_of_date or date.today()
    timeout = get_timeout_seconds()

    try:
        if timeout > 0:
            async with asyncio.timeout(timeout):
                result = await mgr.run_after_close(as_of_date=as_of_date, force=request.force)
        else:
            result = await mgr.run_after_close(as_of_date=as_of_date, force=request.force)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"盘后考核生成超时（{timeout}秒）",
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"缺少盘前日报，请先运行盘前流程: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="盘后考核生成失败",
        )

    html_path = None
    if request.export_html:
        html_path = str(mgr.export_evaluation_html(result=result))

    return RunAfterCloseResponse(
        status="success",
        as_of_date=as_of_date,
        evaluations_count=len(result.evaluations),
        output_dir=str(mgr.output_dir),
        html_path=html_path,
        result=result,
    )


@router.get("/health")
async def run_health() -> dict:
    """健康检查端点。"""
    return {"status": "ok", "service": "run"}
