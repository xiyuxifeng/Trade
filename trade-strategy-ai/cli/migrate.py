from __future__ import annotations

from pathlib import Path

import typer
from alembic import command
from alembic.config import Config


app = typer.Typer(add_completion=False)


def _alembic_config(project_root: Path) -> Config:
	ini_path = project_root / "src" / "db" / "migrations" / "alembic.ini"
	if not ini_path.exists():
		raise FileNotFoundError(f"alembic.ini not found: {ini_path}")
	cfg = Config(str(ini_path))
	return cfg


@app.command("upgrade")
def upgrade(
	revision: str = typer.Argument("head", help="目标版本（默认 head）"),
	project_root: Path = typer.Option(Path("."), help="项目根目录（默认当前目录）"),
) -> None:
	cfg = _alembic_config(project_root.resolve())
	command.upgrade(cfg, revision)


@app.command("downgrade")
def downgrade(
	revision: str = typer.Argument("-1", help="回退版本（默认 -1）"),
	project_root: Path = typer.Option(Path("."), help="项目根目录（默认当前目录）"),
) -> None:
	cfg = _alembic_config(project_root.resolve())
	command.downgrade(cfg, revision)
