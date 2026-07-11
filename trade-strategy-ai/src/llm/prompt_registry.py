from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from src.schemas.prompt_outputs import (
    ArticleAnalysisOutput,
    ArticleAnalysisRepairOutput,
    ArticleTaxonomyOutput,
    ArticleTaxonomyRepairOutput,
    AuthorMethodProfileBatchOutput,
    AuthorProfileMergeOutput,
    AuthorProfileRevisionOutput,
    AuthorRuleProfileSummaryOutput,
    AuthorValidatedProfileOutput,
    LLMAttributionOutput,
    LLMPostmortemNotesOutput,
    StrategyRevisionProposalOutput,
)


class PromptProductionStatus(StrEnum):
    active = "active"
    conditional = "conditional"
    test_special_only = "test/special_only"
    batch_only = "batch_only"
    asset_validated = "asset_validated"


_PROMPT_VERSION_PATTERN = re.compile(r'"prompt_version"\s*:\s*"([^"]+)"')
_SCHEMA_VERSION_PATTERN = re.compile(r'"schema_version"\s*:\s*"([^"]+)"')


@dataclass(frozen=True, slots=True)
class PromptSpec:
    prompt_name: str
    prompt_version: str
    file_path: Path
    schema_model: type[BaseModel]
    schema_name: str
    schema_version: str
    production_status: PromptProductionStatus
    ownership: str

    def load_prompt_text(self) -> str:
        return (_repo_root() / self.file_path).read_text(encoding="utf-8")

    @property
    def embedded_prompt_version(self) -> str | None:
        match = _PROMPT_VERSION_PATTERN.search(self.load_prompt_text())
        return match.group(1) if match else None

    @property
    def embedded_schema_version(self) -> str | None:
        match = _SCHEMA_VERSION_PATTERN.search(self.load_prompt_text())
        return match.group(1) if match else None

    def export_json_schema(self) -> dict[str, Any]:
        return self.schema_model.model_json_schema()

    def validate_output(self, payload: dict[str, Any]) -> BaseModel:
        return self.schema_model.model_validate(payload)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_registry() -> dict[str, PromptSpec]:
    entries = [
        ("article_taxonomy_v1", "article_taxonomy_v1.md", ArticleTaxonomyOutput, "article_taxonomy_v1", "article_taxonomy_v1", PromptProductionStatus.active),
        ("article_taxonomy_repair_v1", "article_taxonomy_repair_v1.md", ArticleTaxonomyRepairOutput, "article_taxonomy_repair_v1", "article_taxonomy_repair_v1", PromptProductionStatus.conditional),
        ("article_analysis_v1", "article_analysis_v1.md", ArticleAnalysisOutput, "article_analysis_v1", "article_analysis_v1", PromptProductionStatus.test_special_only),
        ("article_analysis_repair_v1", "article_analysis_repair_v1.md", ArticleAnalysisRepairOutput, "article_analysis_repair_v1", "article_analysis_repair_v1", PromptProductionStatus.conditional),
        ("author_method_profile_batch_v1", "author_method_profile_batch_v1.md", AuthorMethodProfileBatchOutput, "author_method_profile_batch_v1", "author_method_profile_batch_v1", PromptProductionStatus.batch_only),
        ("author_rule_profile_summary_v1", "author_rule_profile_summary_v1.md", AuthorRuleProfileSummaryOutput, "author_rule_profile_summary_v1", "author_rule_profile_summary_v1", PromptProductionStatus.asset_validated),
        ("author_validated_profile_v1", "author_validated_profile_v1.md", AuthorValidatedProfileOutput, "author_validated_profile_v1", "author_validated_profile_v1", PromptProductionStatus.asset_validated),
        ("author_profile_merge_v1", "author_profile_merge_v1.md", AuthorProfileMergeOutput, "author_profile_merge_v1", "author_profile_merge_v1", PromptProductionStatus.asset_validated),
        ("author_profile_revision_v1", "author_profile_revision_v1.md", AuthorProfileRevisionOutput, "author_profile_revision_v1", "author_profile_revision_v1", PromptProductionStatus.asset_validated),
        ("llm_attribution_v1", "llm_attribution_v1.md", LLMAttributionOutput, "llm_attribution_v1", "llm_attribution_v1", PromptProductionStatus.asset_validated),
        ("strategy_revision_proposal_v1", "strategy_revision_proposal_v1.md", StrategyRevisionProposalOutput, "strategy_revision_proposal_v1", "strategy_revision_proposal_v1", PromptProductionStatus.asset_validated),
        ("llm_postmortem_notes_v1", "llm_postmortem_notes_v1.md", LLMPostmortemNotesOutput, "llm_postmortem_notes_v1", "llm_postmortem_notes_v1", PromptProductionStatus.asset_validated),
    ]
    return {
        name: PromptSpec(
            prompt_name=name,
            prompt_version=name,
            file_path=Path("prompts") / filename,
            schema_model=schema_model,
            schema_name=schema_name,
            schema_version=schema_version,
            production_status=status,
            ownership="stage3-prompt-suite",
        )
        for name, filename, schema_model, schema_name, schema_version, status in entries
    }


_PROMPT_REGISTRY = _build_registry()


def get_prompt_registry() -> dict[str, PromptSpec]:
    return dict(_PROMPT_REGISTRY)


def get_prompt_spec(prompt_name: str) -> PromptSpec:
    try:
        return _PROMPT_REGISTRY[prompt_name]
    except KeyError as exc:
        raise KeyError(f"unknown prompt: {prompt_name}") from exc


def validate_prompt_fixture(prompt_name: str, payload: str | dict[str, Any]) -> BaseModel:
    spec = get_prompt_spec(prompt_name)
    data = json.loads(payload) if isinstance(payload, str) else payload
    try:
        return spec.validate_output(data)
    except ValidationError as exc:
        raise exc
