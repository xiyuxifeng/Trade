from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Sequence

from src.services.config_migration_service import ConfigMigrationService


def _build_parser() -> argparse.ArgumentParser:
    """构造内部迁移脚本参数解析器。"""
    parser = argparse.ArgumentParser(description="将旧 config_path 迁移为正式 Profile")
    parser.add_argument("--config", type=Path, default=Path("config/app.yaml"), help="旧 config_path")
    parser.add_argument("--profile-id", dest="profile_id", default=None, help="目标 Profile ID")
    parser.add_argument("--name", default=None, help="目标 Profile 名称")
    parser.add_argument("--environment", default=None, help="目标 Profile 环境标识")
    parser.add_argument("--created-by", dest="created_by", default="system", help="创建者")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不保存")
    return parser


def _print_preview(result_payload: dict[str, object]) -> None:
    """打印迁移预览。"""
    missing_sections = result_payload.get("missing_sections", [])
    compatibility = result_payload.get("compatibility", {})
    print("=== Profile 迁移预览 ===")
    print(f"config_path: {result_payload['config_path']}")
    print(f"profile_id: {result_payload['profile_id']}")
    print(f"profile_name: {result_payload['profile_name']}")
    print(f"environment: {result_payload['environment']}")
    print(f"validation_status: {result_payload['validation_status']}")
    print(f"missing_sections: {', '.join(missing_sections) if missing_sections else '无'}")
    print("=== 脱敏配置预览 ===")
    print(json.dumps(result_payload["masked_preview"], ensure_ascii=False, indent=2))
    print("=== 兼容说明 ===")
    print(f"legacy_entry: {compatibility.get('legacy_entry', 'config_path')}")
    print(f"canonical_target: {compatibility.get('canonical_target', 'profile')}")
    print(f"retired_when: {compatibility.get('retire_condition', '-')}")


def main(argv: Sequence[str] | None = None) -> int:
    """执行内部迁移脚本。"""
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    service = ConfigMigrationService()

    preview = service.preview_migration(
        args.config,
        profile_id=args.profile_id,
        created_by=args.created_by,
        name=args.name,
        environment=args.environment,
    )
    if preview.status != "ok":
        print(preview.message or "profile migration preview failed")
        return 2

    _print_preview(preview.payload)
    if args.dry_run:
        print("dry-run 完成，未保存 Profile")
        return 0

    result = asyncio.run(
        service.migrate_config_path(
            args.config,
            profile_id=args.profile_id,
            created_by=args.created_by,
            name=args.name,
            environment=args.environment,
        )
    )
    if result.status != "ok":
        print(result.message or "profile migration failed")
        return 2

    profile = result.payload["profile"]
    snapshot = result.payload["snapshot"]
    print("=== 迁移完成 ===")
    print(f"profile_id: {profile['profile_id']}")
    print(f"version: {profile['version']}")
    print(f"snapshot_path: {snapshot['snapshot_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
