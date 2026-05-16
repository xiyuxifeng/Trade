# Market Data PipelineSpec

## Canonical Contract

- pipeline_id: `market_data`
- ui_page: `/market`
- ui_task_ids: `UI-V2-005`, `UI-V2-007`
- workflow_id: `scheduler`
- job_types: `kaipan-fetch`, `kaipan-normalize`, `kaipan-run`, `ohlcv-crawl`, `market-state-build`, `snapshot-build`
- required_profile_sections: `market`, `profile`, `provider`

## Success Criteria

- The market workspace consumes this spec as the single source of truth.
- The UI never hardcodes provider-private fields or filesystem paths.
- The spec stays aligned with existing `job_registry` and `workflow_service` definitions.

## Permissions And Error Modes

- `kaipan-fetch` / `kaipan-normalize` / `kaipan-run` use `admin` permission.
- `ohlcv-crawl` / `market-state-build` / `snapshot-build` use `operator` permission.
- Error modes are declared per job type so the market workspace can show structured failure reasons instead of free-form exceptions.
- The UI should treat `provider unavailable`, `config missing`, `data empty`, `data invalid`, `partial snapshot`, and `system error` as canonical user-facing categories.
