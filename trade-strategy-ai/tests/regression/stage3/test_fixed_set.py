from __future__ import annotations

from src.services.stage3_regression_fixtures import (
    REQUIRED_STAGE3_REGRESSION_CATEGORIES,
    get_stage3_fixed_regression_set,
)


def test_stage3_fixed_regression_set_has_required_size_and_category_coverage() -> None:
    fixed_set = get_stage3_fixed_regression_set()

    assert 10 <= len(fixed_set) <= 15

    covered = set()
    for item in fixed_set:
        covered.update(item.covered_categories)

    assert covered == REQUIRED_STAGE3_REGRESSION_CATEGORIES


def test_stage3_fixed_regression_set_binds_identity_versions_and_semantic_assertions() -> None:
    fixed_set = get_stage3_fixed_regression_set()

    for item in fixed_set:
        assert item.article_id
        assert item.article_revision_id
        assert item.content_hash
        assert item.prompt_name == "article_taxonomy_v1"
        assert item.prompt_version == "article_taxonomy_v1"
        assert item.schema_name == "article_taxonomy_v1"
        assert item.schema_version == "article_taxonomy_v1"
        assert item.model
        assert item.selection_reason
        assert item.expected_outcome_ambiguity
        assert item.summary_expectation.source in {
            "article_revision_source_payload",
            "blog_article_current",
            "unavailable",
        }
        assert item.summary_expectation.available is item.summary_expectation.aligned
        assert item.semantic_assertions.method_tags
        assert item.semantic_assertions.market_state_status in {"explicit", "not_declared"}
        assert item.semantic_assertions.article_structure_provenance_required is True
        assert item.semantic_assertions.candidate_rule_count_range[0] >= 0
        assert (
            item.semantic_assertions.candidate_rule_count_range[1]
            >= item.semantic_assertions.candidate_rule_count_range[0]
        )
