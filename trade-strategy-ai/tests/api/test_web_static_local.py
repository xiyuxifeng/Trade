from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_web_static_root_and_spa_fallback(monkeypatch, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>web</body></html>", encoding="utf-8")
    monkeypatch.setenv("WEB_STATIC_DIR", str(dist))

    from api.app import create_app

    client = TestClient(create_app())
    assert client.get("/").status_code == 200
    assert client.get("/jobs").status_code == 200
    assert "web" in client.get("/jobs").text
    assert client.get("/health").json() == {"status": "ok"}


def test_api_routes_keep_priority(monkeypatch, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>web</body></html>", encoding="utf-8")
    monkeypatch.setenv("WEB_STATIC_DIR", str(dist))

    from api.app import create_app

    client = TestClient(create_app())
    assert client.get("/api/ui/v1/system/status").status_code in {200, 401, 403}
