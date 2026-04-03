from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
	p = Path(path)
	p.mkdir(parents=True, exist_ok=True)
	return p


def write_json(path: str | Path, payload: Any) -> None:
	p = Path(path)
	ensure_dir(p.parent)
	with p.open("w", encoding="utf-8") as f:
		json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def read_json(path: str | Path) -> Any:
	p = Path(path)
	with p.open("r", encoding="utf-8") as f:
		return json.load(f)


def append_jsonl(path: str | Path, payload: Any) -> None:
	p = Path(path)
	ensure_dir(p.parent)
	with p.open("a", encoding="utf-8") as f:
		f.write(json.dumps(payload, ensure_ascii=False, default=str))
		f.write("\n")
