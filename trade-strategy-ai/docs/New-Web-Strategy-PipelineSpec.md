# Strategy PipelineSpec

## Canonical Contract

- pipeline_id: `strategy`
- ui_page: `/strategies`
- ui_task_ids: `UI-V2-006`, `UI-V2-007`
- workflow_id: `strategy`
- job_types: `strategy-build`, `run-pre-market`, `run-after-close`
- required_profile_sections: `profile`, `strategy`, `market`, `trader`

## Success Criteria

- The strategy workspace consumes this spec as the single source of truth.
- The UI never hardcodes CLI-specific execution semantics.
- The strategy version, pre-market run, and after-close run can all be traced back to Job and Artifact records.
- The spec stays aligned with existing `job_registry`, `workflow_service`, `StrategyService`, and `RunService` definitions.

## Output And Extension Notes

- `strategy-build` exposes the canonical strategy version result and evidence chain.
- `run-pre-market` and `run-after-close` expose human-readable and machine-readable reports.
- `evidence-pack-json`, `ranking-report-json`, and `memory-update-json` are kept as canonical extension kinds so the pipeline contract can grow without a second spec.

## Current Constraint

- This spec defines the formal Web contract only.
- It does not introduce new CLI surface or new runtime behavior.
