from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def init_db(*, project_root: Path) -> None:
	ini_path = project_root / "src" / "db" / "migrations" / "alembic.ini"
	if not ini_path.exists():
		raise FileNotFoundError(f"alembic.ini not found: {ini_path}")
	cfg = Config(str(ini_path))
	command.upgrade(cfg, "head")


if __name__ == "__main__":
	init_db(project_root=Path(__file__).resolve().parents[1])
