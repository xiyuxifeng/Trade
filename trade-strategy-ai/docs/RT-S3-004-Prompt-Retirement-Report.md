# RT-S3-004 Prompt Retirement Report

## Scope

- Task: `RT-S3-004 旧 Prompt 迁移与退役`
- Date: `2026-06-16`
- Parent model session: recovery + continuation
- Scope boundary preserved:
  - `RT-S3-001`～`RT-S3-003` accepted contracts unchanged
  - v1 Prompt registry and Pydantic Schema remain canonical
  - canonical writer remains the sole formal writer
  - no dual-write
  - no DB Schema or Alembic change
  - no Stage 4+ implementation

## Recovered worktree state

Recovery started from a dirty worktree created by the interrupted previous session.

Task-related tracked changes found on recovery:

- `src/agents/data_agent/skills/extract_article_metadata.py`
- `src/evaluation/postmortem_service.py`
- `tests/unit/agents/test_extract_article_metadata.py`
- `tests/unit/agents/test_extract_article_metadata_extended.py`

Task-related untracked files found on recovery:

- `src/services/stage3_prompt_retirement.py`
- `tests/integration/test_stage3_legacy_compatibility.py`

Unsafe partial state found on recovery:

- legacy article extraction had already been redirected to `article_analysis_v1`, but the 5 legacy Prompt files still existed;
- postmortem helpers had already been redirected to v1 Prompt assets;
- retirement inventory existed only as an untracked static stub;
- Stage 3 logs still described `RT-S3-004` as not started.

No unrelated or user-owned changes were found in the recovery diff.

## Legacy inventory and old-to-new mapping

| Legacy Prompt | Replacement Prompt | Replacement Schema | Runtime disposition | Historical read |
| --- | --- | --- | --- | --- |
| `concept_extraction.md` | `article_analysis_v1` / `concept_extraction_v1` | `article_analysis_v1.concept_extraction -> concept_v1` | redirected to v1 compatibility projection | stored `ArticleMetadata` only |
| `rule_extraction.md` | `article_analysis_v1` / `rule_extraction_v1` | `article_analysis_v1.rule_extraction -> rule_v1` | redirected to v1 compatibility projection | stored `ArticleMetadata` / compatibility adapters only |
| `precondition_extraction.md` | `article_analysis_v1` / `explicit_precondition_extraction_v1` | `article_analysis_v1.explicit_preconditions -> explicit_precondition_v1` | redirected to v1 compatibility projection | stored `ArticleMetadata` only |
| `llm_attribution.md` | `llm_attribution_v1` | `llm_attribution_v1` | redirected to v1 asset | stored postmortem results only |
| `llm_postmortem_notes.md` | `llm_postmortem_notes_v1` | `llm_postmortem_notes_v1` | redirected to v1 asset | stored postmortem notes only |

Canonical inventory is implemented in `src/services/stage3_prompt_retirement.py`.

## Fixed-set comparison evidence

Machine-verifiable comparison evidence is provided by:

- `tests/integration/test_stage3_legacy_compatibility.py::test_fixed_set_v1_payload_projects_to_legacy_reader_shape`

The test runs the fixed Stage 3 regression fixtures through the accepted `article_analysis_v1` payload builder and verifies that the compatibility projection still provides the legacy reader shape:

- `extracted_concepts`
- `trading_symbols`
- `strategy_rules`
- `preconditions`
- `comment_insights`
- `sentiment_score`
- `confidence_score`

This comparison is bounded to compatibility readers only. It does not reactivate legacy Prompt files or create a second formal write path.

## Sole writer and active caller cleanup

Verified runtime facts after recovery repair:

- no production `src/api/cli/scripts` caller loads the deleted legacy Prompt filenames;
- legacy article extraction now loads `article_analysis_v1` and projects to legacy read shape only;
- postmortem helpers now load `llm_attribution_v1` and `llm_postmortem_notes_v1`;
- Stage 2 canonical writer contract remains unchanged and still governs formal writes.

Formal-write status:

```text
Application Service
-> canonical repository
-> canonical PostgreSQL database
```

Compatibility-only status:

- legacy article metadata readers keep reading stored historical payloads;
- compatibility projection does not create a second formal writer;
- rollback by restoring deleted Prompt files does not reactivate them because active callers are pinned to v1 Prompt names.

## Historical-read compatibility evidence

Machine-verifiable evidence:

- `tests/integration/test_stage3_legacy_compatibility.py::test_historical_article_metadata_adapter_does_not_load_legacy_prompt_files`
- `tests/integration/test_stage3_legacy_compatibility.py::test_stage3_prompt_registry_has_no_legacy_prompt_identity_or_path`
- `tests/unit/agents/test_extract_article_metadata.py::test_extract_one_uses_article_analysis_v1_and_compat_projection`

These checks prove:

- historical article metadata can still be adapted without loading deleted Prompt files;
- the canonical Prompt registry does not expose legacy Prompt identities or paths;
- compatibility readers get v1-backed projected data rather than legacy Prompt execution.

## Observation and rollback evidence

Observation evidence used for deletion:

- Stage 3 fixed-set gate remained green after redirecting legacy callers and deleting Prompt files.
- targeted article extraction and postmortem compatibility tests remained green after deletion.
- repo-wide scan confirmed no active production caller still names the deleted Prompt files.

Rollback evidence used for deletion:

- `extract_article_metadata.py` callers are pinned to `get_prompt_spec("article_analysis_v1")`;
- `postmortem_service.py` callers are pinned to `prompts/llm_attribution_v1.md` and `prompts/llm_postmortem_notes_v1.md`;
- `tests/integration/test_stage3_legacy_compatibility.py::test_postmortem_llm_helpers_load_v1_prompt_assets` proves the runtime stays on v1 assets;
- restoring legacy files from Git history would restore text assets only, not the retired routing.

## Reference scan result

Command:

```bash
rg -n "concept_extraction\.md|rule_extraction\.md|precondition_extraction\.md|llm_attribution\.md|llm_postmortem_notes\.md" src api cli scripts tests prompts docs
```

Result classification:

- `src/`: only retirement inventory metadata remains;
- `tests/`: compatibility tests intentionally reference the deleted filenames as retirement gates;
- `docs/`: historical design, task, migration, and retirement records still mention the deleted filenames as historical artifacts and mappings;
- `prompts/`: no deleted legacy Prompt files remain.

No active production runtime reference remains.

## Per-Prompt deletion gates

| Legacy Prompt | Runtime redirected | Historical read works | File deleted | Rollback safe | Gate |
| --- | --- | --- | --- | --- | --- |
| `concept_extraction.md` | yes | yes | yes | yes | passed |
| `rule_extraction.md` | yes | yes | yes | yes | passed |
| `precondition_extraction.md` | yes | yes | yes | yes | passed |
| `llm_attribution.md` | yes | yes | yes | yes | passed |
| `llm_postmortem_notes.md` | yes | yes | yes | yes | passed |

## Files deleted

- `prompts/concept_extraction.md`
- `prompts/rule_extraction.md`
- `prompts/precondition_extraction.md`
- `prompts/llm_attribution.md`
- `prompts/llm_postmortem_notes.md`

## Verification executed

```bash
../.venv/bin/python -m pytest tests/integration/test_stage3_legacy_compatibility.py -q
../.venv/bin/python -m pytest tests/regression/stage3 tests/unit/llm tests/integration/test_stage3_legacy_compatibility.py -q
../.venv/bin/python -m pytest tests/e2e/test_article_pipeline_v1.py tests/unit/agents/test_extract_article_metadata.py tests/unit/agents/test_extract_article_metadata_extended.py -q
git diff --check
```

Results:

- `tests/integration/test_stage3_legacy_compatibility.py`: `6 passed`
- `tests/regression/stage3 tests/unit/llm tests/integration/test_stage3_legacy_compatibility.py`: `14 passed`
- `tests/e2e/test_article_pipeline_v1.py tests/unit/agents/test_extract_article_metadata.py tests/unit/agents/test_extract_article_metadata_extended.py`: `17 passed, 1 skipped`
- `git diff --check`: passed

## Conclusion

- `RT-S3-004` deletion gates passed.
- legacy Prompt files were safely deleted after runtime redirect, fixed-set comparison evidence, historical-read verification, and rollback verification.
- Stage 3 is still not marked complete here.
- Next allowed action: Stage 3 Gate may begin in a separate step.
