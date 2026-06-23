from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select

from src.db.session import get_session_factory
from src.models.job import Job
from src.models.stage2_canonical import PromptRun
from src.services.base import BaseService, ServiceResult
from src.services.stage3_prompt_retirement import (
    LegacyPromptRetirementItem,
    get_legacy_prompt_retirement_inventory,
)

ROLLOUT_STATES = (
    {
        "state": "legacy_new_comparison",
        "label": "新旧链路对照",
        "description": "新旧链路同时可见，用于逐项核对结果和差异。",
    },
    {
        "state": "new_read_only",
        "label": "新链路只读展示",
        "description": "新链路只用于展示和对照，不承接正式写入。",
    },
    {
        "state": "limited_enablement",
        "label": "小范围启用",
        "description": "新链路仅在受控范围启用，并保留恢复路径。",
    },
    {
        "state": "new_default",
        "label": "新链路成为默认",
        "description": "新链路是默认正式路径，但旧链路仍保留兼容入口。",
    },
    {
        "state": "legacy_read_only",
        "label": "旧入口只读",
        "description": "旧入口只保留兼容或只读访问，不再承接正式写入。",
    },
    {
        "state": "retired",
        "label": "最终退役",
        "description": "旧入口已完成退役，需有单独授权和观察证据。",
    },
)


class SystemRolloutService(BaseService):
    service_name = "system-rollout"

    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        stage2_report_dir: str | Path | None = None,
        prompt_inventory_provider: Callable[[], tuple[LegacyPromptRetirementItem, ...]] = get_legacy_prompt_retirement_inventory,
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self._stage2_report_dir = Path(stage2_report_dir) if stage2_report_dir is not None else None
        self._prompt_inventory_provider = prompt_inventory_provider

    @staticmethod
    @asynccontextmanager
    async def _default_session_scope_factory():
        session_factory = get_session_factory()
        async with session_factory() as session:
            yield session

    async def get_summary(self, *, actor_role: str) -> ServiceResult:
        async with self._session_scope_factory() as session:
            prompt_runs = list(
                (
                    await session.execute(
                        select(PromptRun)
                        .order_by(PromptRun.created_at.desc(), PromptRun.completed_at.desc())
                        .limit(50)
                    )
                )
                .scalars()
                .all()
            )
            batch_job = (
                await session.execute(
                    select(Job)
                    .where(Job.job_type == "stage3-article-batch")
                    .order_by(Job.updated_at.desc(), Job.created_at.desc())
                    .limit(1)
                )
            ).scalars().first()

        items = [
            self._build_database_item(),
            self._build_prompt_item(prompt_runs),
            self._build_batch_item(batch_job),
            self._build_route_item(),
        ]
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "supported_rollout_states": list(ROLLOUT_STATES),
            "items": items,
        }
        if actor_role not in {"operator", "admin"}:
            payload["items"] = [
                {
                    "migration_id": item["migration_id"],
                    "label": item["label"],
                    "domain": item["domain"],
                    "current_state": item["current_state"],
                    "state_label": item["state_label"],
                    "formal_source": item["formal_source"],
                    "legacy_mode": item["legacy_mode"],
                    "happened": item["happened"],
                    "affected": item["affected"],
                    "repair_guidance": item["repair_guidance"],
                }
                for item in items
            ]
        return ServiceResult(status="ok", message="rollout summary listed", payload=payload)

    def _build_database_item(self) -> dict[str, Any]:
        evidence = self._load_json("apply_report.json")
        verify = self._load_json("verify_report.json")
        preflight = self._load_json("preflight_inventory.json")
        recovery = self._load_json("recovery_export.json")

        categories = evidence.get("categories") if isinstance(evidence.get("categories"), dict) else {}
        rejected_rows = sum(int((value or {}).get("rejected_count") or 0) for value in categories.values())
        conflicted_rows = sum(int((value or {}).get("conflict_count") or 0) for value in categories.values())
        orphan_count = sum(int((value or {}).get("orphan_count") or 0) for value in categories.values())
        hash_mismatch_count = sum(int((value or {}).get("hash_mismatch_count") or 0) for value in categories.values())
        pre_counts = self._extract_inventory_counts(preflight)
        post_counts = self._extract_inventory_counts(verify)
        upgrade_ready = bool(evidence and pre_counts)
        recovery_ready = bool(recovery)
        no_silent_data_loss = False if upgrade_ready and (orphan_count or hash_mismatch_count) else (True if verify else None)

        return {
            "migration_id": "stage2_canonical_database",
            "label": "正式数据库迁移",
            "domain": "database",
            "current_state": "new_default",
            "state_label": "新链路成为默认",
            "formal_source": "Stage 2 canonical 数据库结构",
            "legacy_mode": "compatibility_only",
            "duplicate_formal_source_detected": False,
            "happened": (
                "正式数据库已切到 canonical 结构；旧链路不再作为正式事实源。"
                if upgrade_ready
                else "正式数据库迁移报告尚未完整落档，当前只能显示部分灰度证据。"
            ),
            "affected": "管理员可以核对迁移前后数量、冲突和恢复证据；缺失报告时不能宣称回滚已验证。",
            "repair_guidance": (
                "补齐 Stage 2 preflight/apply/verify/recovery 报告后再执行正式核对。"
                if not (upgrade_ready and recovery_ready)
                else "如需恢复，按 recovery_export 与 verify_report 指引执行，并先对照 preflight/apply 计数。"
            ),
            "comparison": {
                "status": "ready" if upgrade_ready else "partial",
                "pre_counts": pre_counts,
                "post_counts": post_counts,
                "rejected_rows": rejected_rows if evidence else None,
                "conflicted_rows": conflicted_rows if evidence else None,
            },
            "rollback_or_recovery": {
                "status": "ready" if recovery_ready else "partial",
                "mode": "recovery",
                "evidence_file_names": [
                    name
                    for name, value in (
                        ("preflight_inventory.json", preflight),
                        ("apply_report.json", evidence),
                        ("verify_report.json", verify),
                        ("recovery_export.json", recovery),
                    )
                    if value
                ],
                "no_silent_data_loss": no_silent_data_loss,
                "rejected_rows": rejected_rows if evidence else None,
                "conflicted_rows": conflicted_rows if evidence else None,
            },
        }

    def _build_prompt_item(self, prompt_runs: list[PromptRun]) -> dict[str, Any]:
        inventory = self._prompt_inventory_provider()
        raw_output_count = sum(1 for run in prompt_runs if run.raw_output is not None or run.raw_output_text)
        current_contract = next(
            (
                {
                    "prompt_name": run.prompt_name,
                    "prompt_version": run.prompt_version,
                    "schema_version": run.schema_version,
                }
                for run in prompt_runs
            ),
            None,
        )
        previous_contract = self._select_previous_prompt_contract(prompt_runs)
        all_legacy_retired = bool(inventory) and all(not item.prompt_file_exists for item in inventory)

        return {
            "migration_id": "stage3_prompt_contracts",
            "label": "Prompt 合同迁移",
            "domain": "prompt",
            "current_state": "new_default",
            "state_label": "新链路成为默认",
            "formal_source": "PromptRun + v1 Prompt 注册表",
            "legacy_mode": "compatibility_only",
            "duplicate_formal_source_detected": False,
            "happened": (
                "新 Prompt 合同已经是正式默认写入路径，legacy Prompt 文件不会重新激活正式写入。"
                if all_legacy_retired
                else "legacy Prompt 文件仍有残留，当前不能宣称 Prompt 灰度迁移已收口。"
            ),
            "affected": "系统管理会显示当前合同、前一版合同和原始输出保留情况，避免回滚时丢失新证据。",
            "repair_guidance": (
                "如需回滚，先选择上一版 prompt/schema 合同，再复用已保存 raw output 与 validation evidence。"
                if previous_contract
                else "当前未发现上一版 PromptRun 合同，请先保留历史 PromptRun 再进行合同切换。"
            ),
            "comparison": {
                "status": "ready" if all_legacy_retired else "partial",
                "legacy_prompt_count": len(inventory),
                "raw_output_count": raw_output_count,
                "current_contract": current_contract,
            },
            "rollback_or_recovery": {
                "status": "ready" if previous_contract and raw_output_count else "partial",
                "mode": "rollback",
                "current_contract": current_contract,
                "selected_previous_contract": previous_contract,
                "raw_output_preserved": raw_output_count > 0,
                "legacy_runtime_dispositions": sorted({item.runtime_disposition for item in inventory}),
            },
        }

    def _build_batch_item(self, batch_job: Job | None) -> dict[str, Any]:
        runtime_state = batch_job.runtime_state if isinstance(getattr(batch_job, "runtime_state", None), dict) else {}
        checkpoint = runtime_state.get("checkpoint") if isinstance(runtime_state.get("checkpoint"), dict) else {}
        result = batch_job.result if isinstance(getattr(batch_job, "result", None), dict) else {}
        progress = batch_job.progress if isinstance(getattr(batch_job, "progress", None), dict) else {}
        processed_items = checkpoint.get("processed_items") if isinstance(checkpoint.get("processed_items"), list) else []
        resume_point = runtime_state.get("last_safe_point")
        has_recovery_evidence = bool(batch_job and batch_job.idempotency_key and processed_items and resume_point)

        return {
            "migration_id": "stage3_batch_processing",
            "label": "批量文章处理恢复",
            "domain": "batch",
            "current_state": "limited_enablement",
            "state_label": "小范围启用",
            "formal_source": "Stage 3 批处理 Job + PromptRun 证据",
            "legacy_mode": "compatibility_only",
            "duplicate_formal_source_detected": False,
            "happened": (
                "批量文章处理仍按固定样本门禁和受控并发执行，当前属于小范围启用。"
                if batch_job
                else "尚未发现批量文章处理运行证据，当前只能显示受控启用合同。"
            ),
            "affected": "恢复时必须保留幂等键、逐项状态、PromptRun 和继续点，避免重复创建正式对象或丢失失败证据。",
            "repair_guidance": (
                "使用最近安全检查点继续执行；如需重跑，沿用同一幂等键和输入指纹，不要手工跳过校验。"
                if has_recovery_evidence
                else "先执行一次受控批处理，确保写入 processed_items、resume_point 和 validation evidence。"
            ),
            "comparison": {
                "status": "ready" if batch_job else "partial",
                "job_status": batch_job.status if batch_job else None,
                "processed_count": checkpoint.get("processed_count"),
                "quality_stats": progress.get("quality_stats"),
            },
            "rollback_or_recovery": {
                "status": "ready" if has_recovery_evidence else "partial",
                "mode": "recovery",
                "idempotency_key": batch_job.idempotency_key if batch_job else None,
                "resume_point": resume_point,
                "processed_items": processed_items,
                "rejected_or_conflicted_items": result.get("rejected_or_conflicted_items"),
            },
        }

    def _build_route_item(self) -> dict[str, Any]:
        return {
            "migration_id": "legacy_routes",
            "label": "旧入口兼容与只读",
            "domain": "routes",
            "current_state": "legacy_read_only",
            "state_label": "旧入口只读",
            "formal_source": "/system 及正式业务页",
            "legacy_mode": "compatibility_only",
            "duplicate_formal_source_detected": False,
            "happened": "旧路由继续保留兼容深链，但正式默认入口已经切到新的系统管理与业务页面。",
            "affected": "Stage 11 不会删除旧入口，也不会让用户在不知情的情况下被切到未验证的新链路。",
            "repair_guidance": "保持旧入口 compatibility-only；最终退役必须等 Stage 12 或单独授权任务。",
            "comparison": {
                "status": "ready",
                "legacy_routes_retired": False,
                "legacy_write_enabled": False,
            },
            "rollback_or_recovery": {
                "status": "ready",
                "mode": "compatibility",
                "legacy_routes_retired": False,
                "stage12_required_for_retirement": True,
            },
        }

    def _load_json(self, file_name: str) -> dict[str, Any]:
        if self._stage2_report_dir is None:
            return {}
        path = self._stage2_report_dir / file_name
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _extract_inventory_counts(self, payload: dict[str, Any]) -> dict[str, int] | None:
        inventory = payload.get("inventory") if isinstance(payload.get("inventory"), dict) else payload
        database = inventory.get("database") if isinstance(inventory, dict) and isinstance(inventory.get("database"), dict) else None
        if not database:
            return None
        return {str(key): int(value) for key, value in database.items() if isinstance(value, (int, float))}

    def _select_previous_prompt_contract(self, prompt_runs: list[PromptRun]) -> dict[str, str] | None:
        current_identity: tuple[str, str, str] | None = None
        for run in prompt_runs:
            identity = (run.prompt_name, run.prompt_version, run.schema_version)
            if current_identity is None:
                current_identity = identity
                continue
            if identity != current_identity:
                return {
                    "prompt_name": run.prompt_name,
                    "prompt_version": run.prompt_version,
                    "schema_version": run.schema_version,
                }
        return None
