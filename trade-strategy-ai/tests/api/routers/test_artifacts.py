"""Artifact UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.artifacts import get_artifact_service


@dataclass
class _FakeArtifactService:
    artifact_path: Path

    async def list_artifacts(self, **kwargs: Any) -> Any:
        self.last_list_kwargs = kwargs
        return _result(
            {
                "count": 1,
                "total": 1,
                "items": [
                    {
                        "artifact_id": "artifact-1",
                        "name": self.artifact_path.name,
                        "title": self.artifact_path.name,
                        "kind": "html",
                        "source": "processed",
                        "exists": True,
                        "size_bytes": self.artifact_path.stat().st_size,
                        "modified_at": "2026-05-09T00:00:00+00:00",
                        "previewable": True,
                        "job_id": None,
                        "job_type": None,
                        "safe_download_url": "/api/ui/v1/artifacts/artifact-1/download",
                        "download_name": self.artifact_path.name,
                        "storage_ref": {
                            "source": "file",
                            "logical_id": self.artifact_path.name,
                            "relative_path": self.artifact_path.name,
                            "uri": None,
                            "metadata": {},
                        },
                        "metadata": {},
                    }
                ],
            }
        )

    async def get_artifact(self, artifact_id: str) -> Any:
        if artifact_id != "artifact-1":
            return _result({"artifact_id": artifact_id}, status="partial", message="artifact not found")
        return _result(
            {
                "artifact_id": "artifact-1",
                "name": self.artifact_path.name,
                "title": self.artifact_path.name,
                "kind": "html",
                "source": "processed",
                "exists": True,
                "size_bytes": self.artifact_path.stat().st_size,
                "modified_at": "2026-05-09T00:00:00+00:00",
                "previewable": True,
                "job_id": None,
                "job_type": None,
                "safe_download_url": "/api/ui/v1/artifacts/artifact-1/download",
                "download_name": self.artifact_path.name,
                "storage_ref": {
                    "source": "file",
                    "logical_id": self.artifact_path.name,
                    "relative_path": self.artifact_path.name,
                    "uri": None,
                    "metadata": {},
                },
                "metadata": {},
                "preview": "<html><body>artifact</body></html>",
            }
        )

    async def list_filter_options(self) -> Any:
        self.filter_options_called = True
        return _result(
            {
                "kinds": ["html", "json"],
                "sources": ["jobs", "processed"],
                "job_types": ["run-pre-market", "strategy-build"],
                "job_ids": ["job-2", "job-1"],
            }
        )

    def is_download_path_allowed(self, path: Path) -> bool:
        return path.resolve().is_relative_to(self.artifact_path.parent.resolve())

    def resolve_download_path(self, artifact_id: str) -> Path | None:
        if artifact_id == "artifact-1":
            return self.artifact_path
        return None


@dataclass
class _UnsafeArtifactService:
    artifact_path: Path

    async def list_artifacts(self, **_: Any) -> Any:
        return _result(
            {
                "count": 1,
                "total": 1,
                "items": [],
            }
        )

    async def get_artifact(self, artifact_id: str) -> Any:
        return _result(
            {
                "artifact_id": artifact_id,
                "name": "escape.html",
                "title": "escape.html",
                "kind": "html",
                "source": "processed",
                "exists": True,
                "size_bytes": 1,
                "modified_at": "2026-05-09T00:00:00+00:00",
                "previewable": True,
                "job_id": None,
                "job_type": None,
                "safe_download_url": "/api/ui/v1/artifacts/artifact-escape/download",
                "download_name": "escape.html",
                "storage_ref": {
                    "source": "file",
                    "logical_id": "escape.html",
                    "relative_path": "escape.html",
                    "uri": None,
                    "metadata": {},
                },
                "metadata": {},
                "preview": "<html><body>escape</body></html>",
            }
        )

    def is_download_path_allowed(self, path: Path) -> bool:
        return False

    def resolve_download_path(self, artifact_id: str) -> Path | None:
        return self.artifact_path


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """创建带认证覆盖的测试客户端。"""
    artifact_path = tmp_path / "artifact.html"
    artifact_path.write_text("<html><body>artifact</body></html>", encoding="utf-8")
    fake_service = _FakeArtifactService(artifact_path=artifact_path)
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_artifact_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_get_and_download_artifacts(client: AsyncClient) -> None:
    """Artifact UI API 应支持列表、详情和下载。"""
    listed = await client.get("/api/ui/v1/artifacts")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["name"] == "artifact.html"

    detail = await client.get("/api/ui/v1/artifacts/artifact-1")
    assert detail.status_code == 200
    assert detail.json()["preview"].startswith("<html>")

    downloaded = await client.get("/api/ui/v1/artifacts/artifact-1/download")
    assert downloaded.status_code == 200
    assert downloaded.text.startswith("<html>")


@pytest.mark.asyncio
async def test_list_artifact_filter_options(tmp_path: Path) -> None:
    """Artifact UI API 应支持筛选选项。"""
    artifact_path = tmp_path / "artifact.html"
    artifact_path.write_text("<html><body>artifact</body></html>", encoding="utf-8")
    fake_service = _FakeArtifactService(artifact_path=artifact_path)

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_artifact_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/ui/v1/artifacts/filter-options")
        assert response.status_code == 200
        assert response.json()["job_ids"] == ["job-2", "job-1"]
        assert fake_service.filter_options_called is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_artifacts_accepts_job_type_and_date(tmp_path: Path) -> None:
    """Artifact UI API 应暴露 job_type 和 date 筛选。"""
    artifact_path = tmp_path / "artifact.html"
    artifact_path.write_text("<html><body>artifact</body></html>", encoding="utf-8")
    fake_service = _FakeArtifactService(artifact_path=artifact_path)

    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_artifact_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/ui/v1/artifacts?job_type=strategy-build&date=2026-05-16")
        assert response.status_code == 200
        assert fake_service.last_list_kwargs == {"kind": None, "source": None, "job_type": "strategy-build", "date": "2026-05-16", "job_id": None, "q": None, "skip": 0, "limit": 50}
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_download_artifact_rejects_paths_outside_allowed_roots(tmp_path: Path) -> None:
    """Artifact 下载接口应拒绝允许目录之外的路径。"""
    fake_service = _UnsafeArtifactService(artifact_path=tmp_path / "escape.html")
    app.dependency_overrides.clear()
    try:
        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_artifact_service] = lambda: fake_service
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/ui/v1/artifacts/artifact-escape/download")
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
