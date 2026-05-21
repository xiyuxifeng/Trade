"""API 目录收敛测试。"""

from __future__ import annotations

from pathlib import Path


def test_api_code_is_consolidated_under_api_package() -> None:
    """API 实现应只保留在 `api/` 目录下。"""
    project_root = Path(__file__).resolve().parents[2]
    legacy_api_dir = project_root / "src" / "api"

    assert (project_root / "api" / "app.py").exists()
    assert (project_root / "api" / "dependencies.py").exists()
    assert (project_root / "api" / "routes").is_dir()
    assert (project_root / "api" / "schemas").is_dir()
    if legacy_api_dir.exists():
        assert not any(path.suffix == ".py" for path in legacy_api_dir.rglob("*.py"))
