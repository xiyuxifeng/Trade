# Strategy PipelineSpec

## Canonical Contract

- pipeline_id: `strategy`
- ui_page: `/strategies`
- ui_task_ids: `UI-V2-006`, `UI-V2-007`
- workflow_id: `strategy`
- job_types: `strategy-build`, `run-pre-market`, `run-after-close`
- required_profile_sections: `top_symbols`, `style_cluster_ids`, `concept_tags`, `strategy_preference`, `risk_style`, `theme_preference`, `position_bias`

## Success Criteria

- The strategy workspace consumes this spec as the single source of truth.
- The UI never hardcodes CLI-specific execution semantics.
- The strategy version, pre-market run, and after-close run can all be traced back to Job and Artifact records.
- The spec stays aligned with existing `job_registry`, `workflow_service`, `StrategyService`, and `RunService` definitions.

## Output And Extension Notes

- `strategy-build` exposes the canonical `result-json` output used by Job Detail and the strategy workspace.
- `run-pre-market` and `run-after-close` expose `result-json` plus a human-readable `html` report.
- `evidence-pack-json`, `ranking-report-json`, and `memory-update-json` are reserved as future extension kinds so the pipeline contract can grow without a second spec.

## Current Constraint

- This spec defines the formal Web contract only.
- It does not introduce new CLI surface or new runtime behavior.
