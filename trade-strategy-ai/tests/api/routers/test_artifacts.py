"""Artifact UI API 路由测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import verify_api_key
from api.main import app
from api.routers.ui.artifacts import get_artifact_service


@dataclass
class _FakeArtifactService:
    artifact_path: Path

    async def list_artifacts(self, **_: Any) -> Any:
        return _result(
            {
                "count": 1,
                "total": 1,
                "items": [
                    {
                        "artifact_id": "artifact-1",
                        "name": self.artifact_path.name,
                        "path": str(self.artifact_path),
                        "kind": "html",
                        "source": "processed",
                        "exists": True,
                        "size_bytes": self.artifact_path.stat().st_size,
                        "modified_at": "2026-05-09T00:00:00+00:00",
                        "previewable": True,
                        "job_id": None,
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
                "path": str(self.artifact_path),
                "kind": "html",
                "source": "processed",
                "exists": True,
                "size_bytes": self.artifact_path.stat().st_size,
                "modified_at": "2026-05-09T00:00:00+00:00",
                "previewable": True,
                "job_id": None,
                "metadata": {},
                "preview": "<html><body>artifact</body></html>",
                "download_name": self.artifact_path.name,
            }
        )


def _result(payload: dict[str, Any], *, status: str = "ok", message: str = "ok") -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(status=status, message=message, payload=payload)


@pytest.fixture
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

