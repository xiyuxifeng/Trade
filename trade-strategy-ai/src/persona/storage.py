from __future__ import annotations

from pathlib import Path

from src.common.utils import read_json, write_json
from src.persona.schemas import PersonaClustersFile


def load_persona_clusters_file(path: str | Path) -> PersonaClustersFile:
	p = Path(path)
	payload = read_json(p)
	return PersonaClustersFile.model_validate(payload)


def write_persona_clusters_file(*, path: str | Path, data: PersonaClustersFile) -> Path:
	p = Path(path)
	p.parent.mkdir(parents=True, exist_ok=True)
	write_json(p, data.model_dump())
	return p
