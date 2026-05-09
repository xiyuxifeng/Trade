from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.common.paths import resolve_project_path
from src.services.setup_service import SetupService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-imports"])

_SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx", ".xlsm", ".html", ".htm", ".pdf"}


class MigrateCrawlStateRequest(BaseModel):
    """crawl state 迁移请求体占位，便于前端保持 JSON 提交。"""


def _config_path() -> Path:
    """读取当前 UI BFF 使用的配置文件路径。"""
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_setup_service() -> SetupService:
    """构建导入与迁移服务。"""
    return SetupService()


def _validate_upload_filename(filename: str | None) -> str:
    """校验上传文件扩展名。"""
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing uploaded filename")
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unsupported file extension: {suffix or '<none>'}")
    return suffix


@router.post("/imports/trade-logs", dependencies=[Depends(verify_api_key)])
async def import_trade_logs(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    source: str = Form("csv_import"),
    service: SetupService = Depends(get_setup_service),
):
    """上传交易日志并在后端临时落盘后交给服务处理。"""
    suffix = _validate_upload_filename(file.filename)
    with TemporaryDirectory(prefix="trade-strategy-ai-import-") as tmp_dir:
        target = Path(tmp_dir) / f"trade-log{suffix}"
        target.write_bytes(await file.read())
        result = await service.import_trade_logs(
            config_path=_config_path(),
            csv_path=target,
            source=source,
            dry_run=dry_run,
        )
    return result.payload


@router.post("/imports/crawl-state/migrate", dependencies=[Depends(verify_api_key)])
async def migrate_crawl_state(
    request: MigrateCrawlStateRequest | None = None,
    service: SetupService = Depends(get_setup_service),
):
    """迁移 crawl state 到数据库。"""
    del request
    result = await service.migrate_crawl_state(config_path=_config_path())
    return result.payload
