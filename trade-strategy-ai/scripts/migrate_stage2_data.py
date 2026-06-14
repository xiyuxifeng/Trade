from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.migrations.stage2_data_migration import Stage2MigrationRunner, build_default_store


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RT-S2-003 stage 2 data migration")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="build deterministic migration report without writes")
    mode.add_argument("--apply", action="store_true", help="apply the canonical migration")
    mode.add_argument("--verify", action="store_true", help="verify migrated counts, mappings, and shadow reads")
    mode.add_argument("--resume", action="store_true", help="resume a failed apply run from the saved cursor")
    parser.add_argument("--batch-size", type=int, default=100, help="bounded batch size for apply/resume")
    parser.add_argument("--report-dir", type=Path, required=True, help="directory for migration reports")
    parser.add_argument("--fail-after-items", type=int, default=None, help="test-only injected failure point")
    return parser


def _resolve_mode(args: argparse.Namespace) -> str:
    if args.dry_run:
        return "dry-run"
    if args.apply:
        return "apply"
    if args.verify:
        return "verify"
    if args.resume:
        return "resume"
    raise ValueError("no migration mode selected")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    runner = Stage2MigrationRunner(
        store=build_default_store(),
        report_dir=args.report_dir,
        batch_size=args.batch_size,
        fail_after_items=args.fail_after_items,
    )
    result = runner.run_sync(mode=_resolve_mode(args))
    return 0 if result.status in {"completed", "completed_with_warnings"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
