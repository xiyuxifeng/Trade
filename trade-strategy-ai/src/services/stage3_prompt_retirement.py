from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LegacyPromptRetirementItem:
    legacy_filename: str
    prompt_path: str
    stem: str
    aliases: tuple[str, ...]
    loader_registry_entry: str
    runtime_callers: tuple[str, ...]
    reference_classes: tuple[str, ...]
    legacy_output_format: str
    replacement_prompt: str
    replacement_schema: str
    runtime_disposition: str
    historical_read_disposition: str
    rollback_disposition: str
    deletion_gate_status: str
    prompt_file_exists: bool


def get_legacy_prompt_retirement_inventory() -> tuple[LegacyPromptRetirementItem, ...]:
    repo_root = Path(__file__).resolve().parents[2]

    def build_item(
        *,
        legacy_filename: str,
        stem: str,
        aliases: tuple[str, ...],
        loader_registry_entry: str,
        runtime_callers: tuple[str, ...],
        reference_classes: tuple[str, ...],
        legacy_output_format: str,
        replacement_prompt: str,
        replacement_schema: str,
        runtime_disposition: str,
        historical_read_disposition: str,
        rollback_disposition: str,
    ) -> LegacyPromptRetirementItem:
        prompt_path = f"prompts/{legacy_filename}"
        prompt_file_exists = (repo_root / prompt_path).exists()
        deletion_gate_status = "pending_file_deletion" if prompt_file_exists else "passed"
        return LegacyPromptRetirementItem(
            legacy_filename=legacy_filename,
            prompt_path=prompt_path,
            stem=stem,
            aliases=aliases,
            loader_registry_entry=loader_registry_entry,
            runtime_callers=runtime_callers,
            reference_classes=reference_classes,
            legacy_output_format=legacy_output_format,
            replacement_prompt=replacement_prompt,
            replacement_schema=replacement_schema,
            runtime_disposition=runtime_disposition,
            historical_read_disposition=historical_read_disposition,
            rollback_disposition=rollback_disposition,
            deletion_gate_status=deletion_gate_status,
            prompt_file_exists=prompt_file_exists,
        )

    return (
        build_item(
            legacy_filename="concept_extraction.md",
            stem="concept_extraction",
            aliases=("extracted_concepts", "trading_symbols", "legacy_article_metadata.concepts"),
            loader_registry_entry="none; retired v0 file path",
            runtime_callers=("legacy extract_article_metadata compatibility path",),
            reference_classes=("active runtime redirected", "historical documentation retained"),
            legacy_output_format="merged v0 JSON fields: extracted_concepts/trading_symbols/comment_insights",
            replacement_prompt="article_analysis_v1",
            replacement_schema="article_analysis_v1.concept_extraction -> concept_v1",
            runtime_disposition="redirected_to_v1",
            historical_read_disposition="stored_metadata_only",
            rollback_disposition="git_restore_does_not_reactivate",
        ),
        build_item(
            legacy_filename="rule_extraction.md",
            stem="rule_extraction",
            aliases=("strategy_rules", "legacy_article_metadata.rules", "rule_pool"),
            loader_registry_entry="none; retired v0 file path",
            runtime_callers=("legacy extract_article_metadata compatibility path",),
            reference_classes=("active runtime redirected", "historical documentation retained"),
            legacy_output_format="merged v0 JSON field: strategy_rules",
            replacement_prompt="article_analysis_v1",
            replacement_schema="article_analysis_v1.rule_extraction -> rule_v1",
            runtime_disposition="redirected_to_v1",
            historical_read_disposition="stored_metadata_only",
            rollback_disposition="git_restore_does_not_reactivate",
        ),
        build_item(
            legacy_filename="precondition_extraction.md",
            stem="precondition_extraction",
            aliases=("preconditions", "market_regime_filter", "legacy_article_metadata.preconditions"),
            loader_registry_entry="none; retired v0 file path",
            runtime_callers=("legacy extract_article_metadata compatibility path",),
            reference_classes=("active runtime redirected", "historical documentation retained"),
            legacy_output_format="merged v0 JSON field: preconditions",
            replacement_prompt="article_analysis_v1",
            replacement_schema="article_analysis_v1.explicit_preconditions -> explicit_precondition_v1",
            runtime_disposition="redirected_to_v1",
            historical_read_disposition="stored_metadata_only",
            rollback_disposition="git_restore_does_not_reactivate",
        ),
        build_item(
            legacy_filename="llm_attribution.md",
            stem="llm_attribution",
            aliases=("postmortem_llm_attribution", "NTL-S5-012"),
            loader_registry_entry="none; retired v0 file path",
            runtime_callers=("PostmortemService.llm_attribution",),
            reference_classes=("future-stage conditional runtime redirected", "historical documentation retained"),
            legacy_output_format="v0 JSON: reason/corrected_reason/confidence",
            replacement_prompt="llm_attribution_v1",
            replacement_schema="llm_attribution_v1",
            runtime_disposition="inactive_future_stage_v1",
            historical_read_disposition="stored_metadata_only",
            rollback_disposition="git_restore_does_not_reactivate",
        ),
        build_item(
            legacy_filename="llm_postmortem_notes.md",
            stem="llm_postmortem_notes",
            aliases=("postmortem_notes", "NTL-S5-013"),
            loader_registry_entry="none; retired v0 file path",
            runtime_callers=("PostmortemService._generate_postmortem_notes",),
            reference_classes=("future-stage conditional runtime redirected", "historical documentation retained"),
            legacy_output_format="v0 JSON: notes",
            replacement_prompt="llm_postmortem_notes_v1",
            replacement_schema="llm_postmortem_notes_v1",
            runtime_disposition="inactive_future_stage_v1",
            historical_read_disposition="stored_metadata_only",
            rollback_disposition="git_restore_does_not_reactivate",
        ),
    )
