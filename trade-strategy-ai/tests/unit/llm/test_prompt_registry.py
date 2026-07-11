from __future__ import annotations

from src.llm.prompt_registry import PromptProductionStatus, get_prompt_registry


def test_prompt_registry_matches_frozen_stage3_contract() -> None:
    registry = get_prompt_registry()

    expected = {
        "article_taxonomy_v1": (
            "prompts/article_taxonomy_v1.md",
            "article_taxonomy_v1",
            PromptProductionStatus.active,
        ),
        "article_taxonomy_repair_v1": (
            "prompts/article_taxonomy_repair_v1.md",
            "article_taxonomy_repair_v1",
            PromptProductionStatus.conditional,
        ),
        "article_analysis_v1": (
            "prompts/article_analysis_v1.md",
            "article_analysis_v1",
            PromptProductionStatus.test_special_only,
        ),
        "article_analysis_repair_v1": (
            "prompts/article_analysis_repair_v1.md",
            "article_analysis_repair_v1",
            PromptProductionStatus.conditional,
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


def test_article_analysis_prompt_is_self_contained_without_runtime_prompt_concatenation() -> None:
    text = get_prompt_registry()["article_analysis_v1"].load_prompt_text()

    assert "# Concept Extraction v1" not in text
    assert "# Article Structure Extraction v1" not in text
    assert "# Rule Extraction v1" not in text
    assert "# Explicit Precondition Extraction v1" not in text
    assert "子 Prompt 详细规范" not in text
    assert '"classification": {' in text
    assert '"concept_extraction": {' in text
    assert '"article_structure": {' in text
    assert '"rule_extraction": {' in text
    assert '"explicit_preconditions": {' in text
    assert '"market_state": {' in text
    assert '"quantification": {' in text
    assert "不得编造止盈、止损、持有周期、仓位和参数" in text


def test_prompt_registry_exposes_pydantic_schema_exports() -> None:
    for spec in get_prompt_registry().values():
        exported = spec.export_json_schema()
        assert exported["type"] == "object"
        assert spec.schema_name in exported.get("title", "")
