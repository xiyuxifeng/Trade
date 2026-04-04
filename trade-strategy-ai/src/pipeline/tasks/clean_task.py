from __future__ import annotations

import json
from dataclasses import dataclass
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from src.common.utils import ensure_dir, write_json


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
	with path.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			yield json.loads(line)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
	ensure_dir(path.parent)
	with path.open("a", encoding="utf-8") as f:
		f.write(json.dumps(payload, ensure_ascii=False, default=str))
		f.write("\n")


@dataclass(slots=True)
class CleanResult:
	cleaned_paths: list[Path]
	stats_path: Path


def clean_articles_jsonl(*, input_path: Path, output_path: Path) -> dict[str, Any]:
	total = 0
	total_comments = 0
	kept_comments = 0
	filtered_comments = 0

	if output_path.exists():
		output_path.unlink()

	for rec in _iter_jsonl(input_path):
		total += 1
		comments = rec.get("comments") or rec.get("comments_payload") or []
		if not isinstance(comments, list):
			comments = []

		total_comments += len(comments)
		kept = [c for c in comments if not bool(c.get("is_filtered"))]
		kept_comments += len(kept)
		filtered_comments += max(0, len(comments) - len(kept))

		cleaned = {
			**rec,
			"comments_payload": kept,
			"comments_filtered_count": max(0, len(comments) - len(kept)),
			"comments_total_count": len(comments),
		}
		# 兼容下游：统一字段名
		cleaned.pop("comments", None)
		_append_jsonl(output_path, cleaned)

	return {
		"input_path": str(input_path),
		"output_path": str(output_path),
		"records": total,
		"comments_total": total_comments,
		"comments_kept": kept_comments,
		"comments_filtered": filtered_comments,
	}


def run_clean_task(*, base_dir: Path, input_paths: list[Path], force: bool = False) -> CleanResult:
	out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "clean")
	stats: dict[str, Any] = {"files": []}
	cleaned_paths: list[Path] = []

	for p in input_paths:
		if not p.exists():
			continue
		out_path = out_dir / (p.parent.name + ".articles.cleaned.jsonl")
		if out_path.exists() and not force:
			cleaned_paths.append(out_path)
			continue
		file_stats = clean_articles_jsonl(input_path=p, output_path=out_path)
		stats["files"].append(file_stats)
		cleaned_paths.append(out_path)

	stats_path = out_dir / "clean_stats.json"
	write_json(stats_path, stats)
	return CleanResult(cleaned_paths=cleaned_paths, stats_path=stats_path)
