from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import CurrentPrincipal, get_current_principal, verify_api_key
from api.main import app
from api.routers.ui.profiles import get_profile_service
from src.common.config import ConfigError
from src.services.base import ServiceResult


@dataclass
class _FakeProfileService:
    """用于 profile UI 路由测试的替身服务。"""

    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    def serialize_profile(self, profile: Any) -> dict[str, Any]:
        self.calls.append({"method": "serialize_profile", "profile_id": getattr(profile, "profile_id", None)})
        return {
            "profile_id": profile.profile_id,
            "name": profile.name,
            "environment": profile.environment,
            "version": profile.version,
            "sections": profile.sections,
            "secret_refs": profile.secret_refs,
            "validation_status": profile.validation_status,
            "created_by": profile.created_by,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "archived_at": profile.archived_at,
        }

    async def list_profiles(self) -> list[Any]:
        self.calls.append({"method": "list_profiles"})
        return [
            SimpleNamespace(
                profile_id="default",
                name="默认配置",
                environment="production",
                version=2,
                sections={"app": {"timezone": "Asia/Shanghai"}},
                secret_refs={"app.api_key": "masked"},
                validation_status="validated",
                created_by="web",
                created_at="2026-05-16T08:00:00Z",
                updated_at="2026-05-16T08:30:00Z",
                archived_at=None,
            )
        ]

    async def get_profile_detail_payload(self, profile_id: str) -> ServiceResult:
        self.calls.append({"method": "get_profile_detail_payload", "profile_id": profile_id})
        return ServiceResult(
            status="ok",
            message="ok",
            payload={
                "profile": _profile_payload(profile_id),
                "linked_jobs": [_linked_job("job-1")],
                "snapshots": [_snapshot_payload(profile_id, "snapshot-1", job_id="job-1")],
            },
        )

    async def build_profile_edit_payload(self, profile_id: str, draft: dict[str, Any] | None = None) -> ServiceResult:
        self.calls.append({"method": "build_profile_edit_payload", "profile_id": profile_id, "draft": draft})
        return ServiceResult(
            status="ok",
            message="ok",
            payload={
                "profile": _profile_payload(profile_id),
                "draft": {
                    "name": "默认配置",
                    "environment": "production",
                    "sections": {"app": {"timezone": "Asia/Shanghai"}},
                },
                "preview": {
                    **_profile_payload(profile_id),
                    "version": 3,
                    "validation_status": "validated",
                },
                "section_guide": [
                    {
                        "key": "app",
                        "title": "App",
                        "description": "应用分区",
                        "source": "当前 Profile 版本",
                        "default_value": {"timezone": "Asia/Shanghai"},
                        "current_value": {"timezone": "Asia/Shanghai"},
                        "draft_value": {"timezone": "Asia/Shanghai"},
                    }
                ],
                "validation": {
                    "valid": True,
                    "issues": [],
                    "next_version": 3,
                    "validation_status": "validated",
                },
            },
        )

    async def validate_profile_update(self, profile_id: str, draft: dict[str, Any]) -> ServiceResult:
        self.calls.append({"method": "validate_profile_update", "profile_id": profile_id, "draft": draft})
        return ServiceResult(
            status="ok",
            message="ok",
            payload={
                "profile": _profile_payload(profile_id),
                "draft": draft,
                "preview": _profile_payload(profile_id),
                "section_guide": [],
                "validation": {
                    "valid": True,
                    "issues": [],
                    "next_version": 3,
                    "validation_status": "validated",
                },
            },
        )

    async def save_profile_update(self, profile_id: str, draft: dict[str, Any], *, created_by: str) -> ServiceResult:
        self.calls.append({"method": "save_profile_update", "profile_id": profile_id, "draft": draft, "created_by": created_by})
        return ServiceResult(
            status="ok",
            message="ok",
            payload={
                "profile": _profile_payload(profile_id, version=3),
                "snapshot": _snapshot_payload(profile_id, "snapshot-2"),
                "validation": {
                    "valid": True,
                    "issues": [],
                    "next_version": 3,
                    "validation_status": "validated",
                },
            },
        )

    async def archive_profile(self, profile_id: str, *, archived_by: str) -> Any:
        self.calls.append({"method": "archive_profile", "profile_id": profile_id, "archived_by": archived_by})
        return _profile_namespace(profile_id, status="archived")

    async def get_profile(self, profile_id: str) -> Any:
        self.calls.append({"method": "get_profile", "profile_id": profile_id})
        if profile_id == "imported":
            return None
        return _profile_namespace(profile_id)

    async def import_from_config_path(self, config_path, *, profile_id, created_by, name=None, environment=None, validation_status=None):
        del name, environment, validation_status
        self.calls.append({"method": "import_from_config_path", "profile_id": profile_id, "config_path": str(config_path), "created_by": created_by})
        return _profile_namespace(profile_id)

    async def capture_profile_snapshot(self, profile_id: str, *, job_id: str | None = None, source: str | None = None, config_path: str | None = None) -> ServiceResult:
        self.calls.append(
            {
                "method": "capture_profile_snapshot",
                "profile_id": profile_id,
                "job_id": job_id,
                "source": source,
                "config_path": config_path,
            }
        )
        return ServiceResult(
            status="ok",
            message="ok",
            payload=_snapshot_payload(profile_id, job_id or "snapshot-1", job_id=job_id),
        )

    async def list_profile_snapshots(self, profile_id: str) -> list[dict[str, Any]]:
        self.calls.append({"method": "list_profile_snapshots", "profile_id": profile_id})
        return [_snapshot_payload(profile_id, "snapshot-1", job_id="job-1")]

    async def list_profile_linked_jobs(self, profile_id: str) -> list[dict[str, Any]]:
        self.calls.append({"method": "list_profile_linked_jobs", "profile_id": profile_id})
        return [_linked_job("job-1")]


def _profile_namespace(profile_id: str, *, status: str = "validated") -> Any:
    return SimpleNamespace(
        profile_id=profile_id,
        name="默认配置",
        environment="production",
        version=2 if status != "archived" else 3,
        sections={"app": {"timezone": "Asia/Shanghai"}},
        secret_refs={"app.api_key": "masked"},
        validation_status=status,
        created_by="web",
        created_at="2026-05-16T08:00:00Z",
        updated_at="2026-05-16T08:30:00Z",
        archived_at=None if status != "archived" else "2026-05-16T09:00:00Z",
    )


def _profile_payload(profile_id: str, *, version: int = 2) -> dict[str, Any]:
    return {
        "profile_id": profile_id,
        "name": "默认配置",
        "environment": "production",
        "version": version,
        "sections": {"app": {"timezone": "Asia/Shanghai"}},
        "secret_refs": {"app.api_key": "masked"},
        "validation_status": "validated",
        "created_by": "web",
        "created_at": "2026-05-16T08:00:00Z",
        "updated_at": "2026-05-16T08:30:00Z",
        "archived_at": None,
    }


def _snapshot_payload(profile_id: str, snapshot_id: str, *, job_id: str | None = None) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot_id,
        "profile_id": profile_id,
        "job_id": job_id,
        "source": "job" if job_id else "profile",
        "config_path": "config/app.yaml",
        "config_hash": "hash-1",
        "masked_snapshot": {"app": {"timezone": "Asia/Shanghai"}},
        "masked_sections": ["app"],
        "validation_status": "validated",
        "captured_at": "2026-05-16T08:06:00Z",
        "snapshot_path": "/tmp/profile-snapshot.json",
    }


def _linked_job(job_id: str) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "job_type": "pipeline-run",
        "status": "success",
        "created_at": "2026-05-16T08:05:00Z",
        "updated_at": "2026-05-16T08:10:00Z",
    }


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """创建 profile 路由测试客户端。"""
    app.dependency_overrides.clear()
    app.dependency_overrides[verify_api_key] = lambda: "demo-key"
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="admin",
        api_key_label="Admin",
        authenticated=True,
        source="api_key",
        api_key="admin-key",
    )
    app.dependency_overrides[get_profile_service] = lambda: _FakeProfileService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_profile_routes_cover_list_detail_edit_validate_save_archive_import_and_snapshot(client: AsyncClient) -> None:
    """Profile UI 路由应覆盖正式工作台所需的完整链路。"""
    list_response = await client.get('/api/ui/v1/profiles')
    detail_response = await client.get('/api/ui/v1/profiles/default')
    edit_response = await client.get('/api/ui/v1/profiles/default/edit')
    validate_response = await client.post(
        '/api/ui/v1/profiles/default/validate',
        json={'name': '默认配置', 'environment': 'production', 'sections': {'app': {'timezone': 'Asia/Shanghai'}}},
    )
    save_response = await client.put(
        '/api/ui/v1/profiles/default',
        json={'name': '默认配置', 'environment': 'production', 'sections': {'app': {'timezone': 'Asia/Shanghai'}}, 'confirmed': True},
    )
    archive_response = await client.post('/api/ui/v1/profiles/default/archive', json={'archived_by': 'web'})
    import_response = await client.post(
        '/api/ui/v1/profiles/import',
        json={'profile_id': 'imported', 'config_path': 'config/app.yaml', 'created_by': 'web'},
    )
    snapshot_response = await client.get('/api/ui/v1/profiles/default/snapshots/snapshot-1')

    assert list_response.status_code == 200
    assert list_response.json()['items'][0]['profile_id'] == 'default'
    assert detail_response.status_code == 200
    assert detail_response.json()['profile']['profile_id'] == 'default'
    assert edit_response.status_code == 200
    assert edit_response.json()['validation']['valid'] is True
    assert validate_response.status_code == 200
    assert validate_response.json()['validation']['next_version'] == 3
    assert save_response.status_code == 200
    assert save_response.json()['snapshot']['snapshot_id'] == 'snapshot-2'
    assert archive_response.status_code == 200
    assert archive_response.json()['profile']['validation_status'] == 'archived'
    assert import_response.status_code == 200
    assert import_response.json()['created'] is True
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()['snapshot']['snapshot_id'] == 'snapshot-1'


@pytest.mark.asyncio
async def test_profile_import_returns_400_when_service_raises_config_error() -> None:
    """导入失败时，路由应把 ConfigError 显式映射为 400。"""

    class _FailingImportService(_FakeProfileService):
        async def import_from_config_path(self, config_path, *, profile_id, created_by, name=None, environment=None, validation_status=None):
            del config_path, profile_id, created_by, name, environment, validation_status
            raise ConfigError("snapshot failed")

    app.dependency_overrides.clear()
    app.dependency_overrides[verify_api_key] = lambda: "demo-key"
    app.dependency_overrides[get_current_principal] = lambda: CurrentPrincipal(
        role="operator",
        api_key_label="Operator",
        authenticated=True,
        source="api_key",
        api_key="operator-key",
    )
    app.dependency_overrides[get_profile_service] = lambda: _FailingImportService()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                '/api/ui/v1/profiles/import',
                json={'profile_id': 'imported', 'config_path': 'config/app.yaml', 'created_by': 'web'},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()['detail'] == 'snapshot failed'
