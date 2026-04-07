from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.utils import ensure_dir


@dataclass(slots=True)
class DedupResult:
    deduped_path: Path
    report_path: Path
    duplicates_removed: int


def run_dedup_task(
    *, base_dir: Path, input_paths: list[Path], force: bool = False
) -> DedupResult:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ensure_dir(base_dir / "data" / "processed" / "pipeline" / "dedup")
    deduped_path = out_dir / f"deduped_{timestamp}.jsonl"
    report_path = out_dir / f"dedup_report_{timestamp}.json"

    if deduped_path.exists() and not force:
        return DedupResult(deduped_path=deduped_path, report_path=report_path, duplicates_removed=0)

    seen_keys: set[str] = set()
    duplicates_removed = 0
    total_input = 0
    deduped_records: list[dict[str, Any]] = []

    for input_path in input_paths:
        if not input_path.exists():
            continue
        with open(input_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                total_input += 1
                # Simple dedup by symbol+executed_at+quantity+price
                key = f"{record.get('symbol', '')}:{record.get('executed_at', '')}:{record.get('quantity', '')}:{record.get('price', '')}"
                if key in seen_keys:
                    duplicates_removed += 1
                    continue
                seen_keys.add(key)
                deduped_records.append(record)

    with open(deduped_path, "w", encoding="utf-8") as f:
        for record in deduped_records:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    report = {
        "total_input": total_input,
        "duplicates_removed": duplicates_removed,
        "unique_records": len(deduped_records),
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    return DedupResult(deduped_path=deduped_path, report_path=report_path, duplicates_removed=duplicates_removed)
