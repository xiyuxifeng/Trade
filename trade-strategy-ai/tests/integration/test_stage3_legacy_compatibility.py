from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from src.agents.data_agent.skills.extract_article_metadata import _legacy_compat_output_from_article_analysis
from src.domain.adapters import adapt_article_metadata_to_structure
from src.llm.prompt_registry import get_prompt_registry
from src.services.stage3_regression_fixtures import get_stage3_fixed_regression_set


LEGACY_PROMPT_FILES = {
    "concept_extraction.md",
    "rule_extraction.md",
    "precondition_extraction.md",
    "llm_attribution.md",
    "llm_postmortem_notes.md",
}


def test_stage3_prompt_registry_has_no_legacy_prompt_identity_or_path() -> None:
    registry = get_prompt_registry()

    assert not (set(registry) & {name.removesuffix(".md") for name in LEGACY_PROMPT_FILES})
    assert not {
        spec.file_path.name
        for spec in registry.values()
        if spec.file_path.name in LEGACY_PROMPT_FILES
    }


def test_deleted_legacy_prompt_files_are_absent_from_prompts_directory() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    assert not {
        path.name
        for path in (repo_root / "prompts").iterdir()
        if path.name in LEGACY_PROMPT_FILES
    }


def test_historical_article_metadata_adapter_does_not_load_legacy_prompt_files(monkeypatch) -> None:
    def fail_if_prompt_file_is_read(self: Path, *args, **kwargs):  # noqa: ANN001
        if self.name in LEGACY_PROMPT_FILES:
            raise AssertionError(f"historical read attempted to load deleted legacy prompt file: {self.name}")
        return original_read_text(self, *args, **kwargs)

    original_read_text = Path.read_text
    monkeypatch.setattr(Path, "read_text", fail_if_prompt_file_is_read)

    contract = adapt_article_metadata_to_structure(
        article_id=UUID("11111111-1111-1111-1111-111111111111"),
        source="blog",
        source_url="https://example.test/article",
        source_article_id="legacy-article-1",
        schema_version="v1",
    )

    assert contract.prompt_version == "legacy_article_metadata"
    assert contract.provenance.fact_sources[0].source_ref == "article_metadata:v1"


def test_fixed_set_v1_payload_projects_to_legacy_reader_shape() -> None:
    for fixture in get_stage3_fixed_regression_set():
        raw = fixture.build_payload(valid=True)

        compat = _legacy_compat_output_from_article_analysis(raw)

        assert compat["stage3_prompt_name"] == "article_analysis_v1"
        assert compat["stage3_schema_version"] == "article_analysis_v1"
        assert set(compat) >= {
            "extracted_concepts",
            "trading_symbols",
            "strategy_rules",
            "preconditions",
            "comment_insights",
            "sentiment_score",
            "confidence_score",
        }
        assert len(compat["strategy_rules"]) == len(fixture.rules)
        assert len(compat["preconditions"]) == len(raw["explicit_preconditions"]["preconditions"])


def test_stage3_legacy_retirement_inventory_maps_every_prompt_and_allows_deletion() -> None:
    from src.services.stage3_prompt_retirement import get_legacy_prompt_retirement_inventory

    inventory = get_legacy_prompt_retirement_inventory()

    assert {item.legacy_filename for item in inventory} == LEGACY_PROMPT_FILES
    for item in inventory:
        assert item.prompt_path == f"prompts/{item.legacy_filename}"
        assert item.replacement_prompt
        assert item.replacement_schema
        assert item.runtime_disposition in {"redirected_to_v1", "inactive_future_stage_v1"}
        assert item.historical_read_disposition == "stored_metadata_only"
        assert item.rollback_disposition == "git_restore_does_not_reactivate"
        assert item.deletion_gate_status == "passed"
        assert item.prompt_file_exists is False


@pytest.mark.asyncio
async def test_postmortem_llm_helpers_do_not_activate_future_stage_prompt_assets(monkeypatch) -> None:
    from src.evaluation.postmortem_service import PostmortemService

    loaded_paths: list[str] = []

    def fake_load_prompt(relative_path: str) -> str:
        loaded_paths.append(relative_path)
        return "symbol={symbol}; side={side}; entry={entry}; target={target}; stop={stop_loss}; bars={bars}; reason={auto_reason}; confidence={auto_confidence}"

    class EnabledClient:
        def is_enabled(self) -> bool:
            return True

        async def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict:
            assert "symbol=" in system_prompt
            assert "000001.SZ" in user_prompt
            return {"reason": "原始原因", "confidence": 0.7}

    monkeypatch.setattr("src.evaluation.postmortem_service._load_prompt", fake_load_prompt)

    service = PostmortemService()
    result = await service.llm_attribution(
        trade_idea={"symbol": "000001.SZ", "side": "buy", "entry": {"price": 10}},
        market_data={"bars": []},
        auto_attribution={"reason": "原始原因", "confidence": 0.5},
        llm_client=EnabledClient(),
    )

    assert result["attribution_source"] == "auto"
    assert loaded_paths == []
