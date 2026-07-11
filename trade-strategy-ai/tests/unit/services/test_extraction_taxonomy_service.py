from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.extraction_taxonomy import (
    ExtractionItem,
    ExtractionQualityState,
    ExtractionReviewState,
)
from src.schemas.extraction_taxonomy import (
    PrimaryType,
    REVIEW_DESTINATIONS,
    ExtractionItemDraft,
    validate_taxonomy_payload,
)
from src.services.extraction_taxonomy_service import eligibility_for
from tests.fixtures.taxonomy_samples import PAYLOADS, REPRESENTATIVE_ARTICLES, draft_for


def stored_item(primary_type: str, *, accepted: bool = False) -> ExtractionItem:
    now = datetime.now(UTC)
    item_id = uuid4()
    article_id = uuid4()
    revision_id = uuid4()
    structure_id = uuid4()
    prompt_run_id = uuid4()
    return ExtractionItem(
        extraction_item_id=item_id,
        article_id=article_id,
        article_revision_id=revision_id,
        article_structure_id=structure_id,
        prompt_run_id=prompt_run_id,
        item_index=0,
        item_fingerprint="f" * 64,
        taxonomy_version="extraction_taxonomy_v1",
        schema_version="extraction_item_v1",
        primary_type=PrimaryType(primary_type),
        secondary_tags=[],
        taxonomy_payload={"primary_type": primary_type, **PAYLOADS[primary_type]},
        source_evidence={
            "article_id": str(article_id),
            "article_revision_id": str(revision_id),
            "article_structure_id": str(structure_id),
            "prompt_run_id": str(prompt_run_id),
            **draft_for(primary_type)["source_evidence"],
        },
        confidence=draft_for(primary_type)["confidence"],
        quality_state=ExtractionQualityState.valid,
        review_destination=REVIEW_DESTINATIONS[PrimaryType(primary_type)],
        review_state=ExtractionReviewState.accepted if accepted else ExtractionReviewState.queued,
        provenance={"origin": "fixture"},
        created_by="test",
        updated_by="test",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize("primary_type", [item.value for item in PrimaryType])
def test_all_seven_payload_contracts_validate_and_route(primary_type: str) -> None:
    draft = ExtractionItemDraft.model_validate(draft_for(primary_type))
    assert draft.primary_type.value == primary_type
    assert validate_taxonomy_payload(primary_type, draft.taxonomy_payload.model_dump(mode="json"))
    assert REVIEW_DESTINATIONS[draft.primary_type].value


@pytest.mark.parametrize(
    "primary_type",
    [item.value for item in PrimaryType if item != PrimaryType.executable_rule],
)
def test_every_non_rule_type_is_blocked_from_promotion_and_backtest(primary_type: str) -> None:
    eligibility = eligibility_for(stored_item(primary_type, accepted=True))
    assert eligibility.eligible is False
    assert eligibility.blocked_by == ["non_rule_type"]


def test_rule_candidate_remains_blocked_until_separate_repaired_executable_item() -> None:
    eligibility = eligibility_for(stored_item("rule_candidate", accepted=True))
    assert eligibility.eligible is False
    assert eligibility.required_next_step == "repair"


def test_executable_rule_requires_accepted_strict_validation() -> None:
    assert eligibility_for(stored_item("executable_rule", accepted=False)).eligible is False
    assert eligibility_for(stored_item("executable_rule", accepted=True)).eligible is True


def test_executable_rule_rejects_lookahead_ambiguity_and_missing_timestamps() -> None:
    for mutation in (
        {"lookahead_check": {"passed": False, "rationale": "future confirmation", "risks": ["future"]}},
        {"ambiguous_terms": ["弱转强"]},
        {"timestamp_availability": []},
    ):
        payload = {"primary_type": "executable_rule", **PAYLOADS["executable_rule"], **mutation}
        with pytest.raises(ValidationError):
            validate_taxonomy_payload("executable_rule", payload)


def test_representative_sample_covers_required_categories_and_does_not_force_fuzzy_language() -> None:
    categories = {row["category"] for row in REPRESENTATIVE_ARTICLES}
    assert categories == {
        "情绪周期", "弱转强", "龙头 / 主线", "退潮 / 冰点", "放量 / 共振", "风控纪律", "纯市场复盘"
    }
    assert 10 <= len(REPRESENTATIVE_ARTICLES) <= 20
    fuzzy_terms = ("回暖", "弱转强", "龙头", "主线", "退潮", "冰点")
    for sample in REPRESENTATIVE_ARTICLES:
        if any(term in sample["text"] for term in fuzzy_terms):
            assert "executable_rule" not in sample["expected"]
