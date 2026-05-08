from __future__ import annotations

from pathlib import Path

# trade-strategy-ai 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_root() -> Path:
    """返回 trade-strategy-ai 的项目根目录。"""
    return PROJECT_ROOT


def resolve_project_path(path: str | Path | None, *, root: Path | None = None) -> Path:
    """将相对路径解析到项目根目录下。

    Args:
        path: 待解析路径，None 时返回项目根目录
        root: 可选的根目录，默认使用项目根目录
    """
    base = root or PROJECT_ROOT
    if path is None:
        return base

    p = Path(path).expanduser()
    if p.is_absolute():
        return p
    return base / p
