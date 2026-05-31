from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from api.dependencies import verify_api_key
from src.common.paths import resolve_project_path
from src.services.config_profile_service import ConfigProfileService
from src.services.setup_service import SetupService

router = APIRouter(prefix="/api/ui/v1", tags=["ui-imports"])

_SUPPORTED_UPLOADS: dict[str, set[str]] = {
    ".csv": {"text/csv", "application/csv", "text/plain"},
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
    ".xlsm": {"application/vnd.ms-excel.sheet.macroEnabled.12", "application/octet-stream"},
    ".html": {"text/html", "application/xhtml+xml", "application/octet-stream"},
    ".htm": {"text/html", "application/xhtml+xml", "application/octet-stream"},
    ".pdf": {"application/pdf", "application/octet-stream"},
}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_UPLOAD_CHUNK_SIZE = 1024 * 1024


class MigrateCrawlStateRequest(BaseModel):
    """crawl state 迁移请求体占位，便于前端保持 JSON 提交。"""


async def _resolve_profile_id(preferred: str | None = None) -> str | None:
    """读取当前 UI BFF 使用的 Profile。"""
    service = ConfigProfileService()
    return service.resolve_runtime_profile_id(preferred)


def get_setup_service() -> SetupService:
    """构建导入与迁移服务。"""
    return SetupService()


def _validate_upload_filename(filename: str | None) -> str:
    """校验上传文件扩展名。"""
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing uploaded filename")
    uploaded_name = Path(filename).name
    if uploaded_name != filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid uploaded filename")
    suffix = Path(uploaded_name).suffix.lower()
    if suffix not in _SUPPORTED_UPLOADS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unsupported file extension: {suffix or '<none>'}")
    return suffix


def _validate_upload_content_type(content_type: str | None, suffix: str) -> None:
    """校验上传文件的 MIME 类型。"""
    if not content_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing content type")
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized not in _SUPPORTED_UPLOADS[suffix]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported content type: {normalized}",
        )


async def _write_upload_to_tempfile(file: UploadFile, target: Path) -> int:
    """把上传文件按块写入临时文件，返回写入字节数。"""
    written = 0
    with target.open("wb") as handle:
        while True:
            chunk = await file.read(_UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if written > _MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="uploaded file too large",
                )
            handle.write(chunk)
    return written


@router.post("/imports/trade-logs", dependencies=[Depends(verify_api_key)])
async def import_trade_logs(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    source: str = Form("csv_import"),
    profile_id: str | None = None,
    service: SetupService = Depends(get_setup_service),
):
    """上传交易日志并在后端临时落盘后交给服务处理。"""
    suffix = _validate_upload_filename(file.filename)
    _validate_upload_content_type(file.content_type, suffix)
    runtime_profile_id = await _resolve_profile_id(profile_id)
    with TemporaryDirectory(prefix="trade-strategy-ai-import-") as tmp_dir:
        target = Path(tmp_dir) / f"trade-log{suffix}"
        await _write_upload_to_tempfile(file, target)
        if runtime_profile_id is not None:
            result = await service.import_trade_logs(
                profile_id=runtime_profile_id,
                csv_path=target,
                source=source,
                dry_run=dry_run,
            )
        else:
            result = await service.import_trade_logs(
                config_path=resolve_project_path("config/app.yaml"),
                csv_path=target,
                source=source,
                dry_run=dry_run,
            )
    payload = dict(result.payload)
    payload.pop("config_path", None)
    return payload


@router.post("/imports/crawl-state/migrate", dependencies=[Depends(verify_api_key)])
async def migrate_crawl_state(
    request: MigrateCrawlStateRequest | None = None,
    profile_id: str | None = None,
    service: SetupService = Depends(get_setup_service),
):
    """迁移 crawl state 到数据库。"""
    del request
    runtime_profile_id = await _resolve_profile_id(profile_id)
    if runtime_profile_id is not None:
        result = await service.migrate_crawl_state(profile_id=runtime_profile_id)
    else:
        result = await service.migrate_crawl_state(config_path=resolve_project_path("config/app.yaml"))
    payload = dict(result.payload)
    payload.pop("config_path", None)
    return payload
