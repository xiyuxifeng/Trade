from __future__ import annotations

from src.llm.prompt_registry import PromptProductionStatus, get_prompt_registry


def test_prompt_registry_matches_frozen_stage3_contract() -> None:
    registry = get_prompt_registry()

    expected = {
        "article_analysis_v1": (
            "prompts/article_analysis_v1.md",
            "article_analysis_v1",
            PromptProductionStatus.active,
        ),
        "article_analysis_repair_v1": (
            "prompts/article_analysis_repair_v1.md",
            "article_analysis_repair_v1",
            PromptProductionStatus.conditional,
        ),
        "concept_extraction_v1": (
            "prompts/concept_extraction_v1.md",
            "concept_v1",
            PromptProductionStatus.test_special_only,
        ),
        "article_structure_extraction_v1": (
            "prompts/article_structure_extraction_v1.md",
            "article_structure_v1",
            PromptProductionStatus.test_special_only,
        ),
        "rule_extraction_v1": (
            "prompts/rule_extraction_v1.md",
            "rule_v1",
            PromptProductionStatus.test_special_only,
        ),
        "explicit_precondition_extraction_v1": (
            "prompts/explicit_precondition_extraction_v1.md",
            "explicit_precondition_v1",
            PromptProductionStatus.test_special_only,
        ),
        "author_method_profile_batch_v1": (
            "prompts/author_method_profile_batch_v1.md",
            "author_method_profile_batch_v1",
            PromptProductionStatus.batch_only,
        ),
        "author_rule_profile_summary_v1": (
            "prompts/author_rule_profile_summary_v1.md",
            "author_rule_profile_summary_v1",
            PromptProductionStatus.asset_validated,
        ),
        "author_validated_profile_v1": (
            "prompts/author_validated_profile_v1.md",
            "author_validated_profile_v1",
            PromptProductionStatus.asset_validated,
        ),
        "author_profile_merge_v1": (
            "prompts/author_profile_merge_v1.md",
            "author_profile_merge_v1",
            PromptProductionStatus.asset_validated,
        ),
        "author_profile_revision_v1": (
            "prompts/author_profile_revision_v1.md",
            "author_profile_revision_v1",
            PromptProductionStatus.asset_validated,
        ),
        "llm_attribution_v1": (
            "prompts/llm_attribution_v1.md",
            "llm_attribution_v1",
            PromptProductionStatus.asset_validated,
        ),
        "strategy_revision_proposal_v1": (
            "prompts/strategy_revision_proposal_v1.md",
            "strategy_revision_proposal_v1",
            PromptProductionStatus.asset_validated,
        ),
        "llm_postmortem_notes_v1": (
            "prompts/llm_postmortem_notes_v1.md",
            "llm_postmortem_notes_v1",
            PromptProductionStatus.asset_validated,
        ),
    }

    assert set(registry.keys()) == set(expected.keys())
    for prompt_name, (path, schema_version, status) in expected.items():
        spec = registry[prompt_name]
        assert spec.prompt_name == prompt_name
        assert spec.prompt_version == prompt_name
        assert spec.file_path.as_posix() == path
        assert spec.schema_version == schema_version
        assert spec.production_status is status


def test_prompt_registry_loads_prompt_files_and_embedded_versions() -> None:
    for spec in get_prompt_registry().values():
        text = spec.load_prompt_text()
        assert text.startswith("# ")
        assert spec.embedded_prompt_version == spec.prompt_version
        if spec.embedded_schema_version is not None:
            assert spec.embedded_schema_version == spec.schema_version


def test_prompt_registry_exposes_pydantic_schema_exports() -> None:
    for spec in get_prompt_registry().values():
        exported = spec.export_json_schema()
        assert exported["type"] == "object"
        assert spec.schema_name in exported.get("title", "")
