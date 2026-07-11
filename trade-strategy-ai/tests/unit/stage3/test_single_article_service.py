from __future__ import annotations

from uuid import uuid4

from src.schemas.extraction_taxonomy import PrimaryType, review_destination_for
from src.services.stage3_single_article_service import resolve_summary_provenance


def test_taxonomy_review_routing_replaces_legacy_candidate_auto_review() -> None:
    assert review_destination_for(PrimaryType.executable_rule) == "executable_rule_validation"
    assert review_destination_for(PrimaryType.rule_candidate) == "rule_candidate_repair"
    for primary_type in PrimaryType:
        if primary_type not in {PrimaryType.executable_rule, PrimaryType.rule_candidate}:
            assert review_destination_for(primary_type) not in {
                "executable_rule_validation",
                "rule_candidate_repair",
            }


def test_resolve_summary_provenance_uses_current_article_summary_for_latest_revision() -> None:
    revision_id = uuid4()
    article = type("Article", (), {"summary": "最新摘要", "content_hash": "hash-new"})()
    revision = type(
        "Revision",
        (),
        {"article_revision_id": revision_id, "content_hash": "hash-new", "source_payload": {}},
    )()

    result = resolve_summary_provenance(article=article, revision=revision)

    assert result.summary == "最新摘要"
    assert result.source == "blog_article_current"
    assert result.available is True
    assert result.aligned is True
    assert result.article_revision_id == str(revision_id)
    assert result.content_hash == "hash-new"


def test_resolve_summary_provenance_prefers_revision_source_payload_for_older_revision() -> None:
    revision_id = uuid4()
    article = type("Article", (), {"summary": "当前文章新摘要", "content_hash": "hash-new"})()
    revision = type(
        "Revision",
        (),
        {
            "article_revision_id": revision_id,
            "content_hash": "hash-old",
            "source_payload": {"summary": "旧版本摘要"},
        },
    )()

    result = resolve_summary_provenance(article=article, revision=revision)

    assert result.summary == "旧版本摘要"
    assert result.source == "article_revision_source_payload"
    assert result.available is True
    assert result.aligned is True
    assert result.article_revision_id == str(revision_id)
    assert result.content_hash == "hash-old"


def test_resolve_summary_provenance_marks_unavailable_for_unfrozen_older_summary() -> None:
    revision_id = uuid4()
    article = type("Article", (), {"summary": "当前文章新摘要", "content_hash": "hash-new"})()
    revision = type(
        "Revision",
        (),
        {"article_revision_id": revision_id, "content_hash": "hash-old", "source_payload": {}},
    )()

    result = resolve_summary_provenance(article=article, revision=revision)

    assert result.summary is None
    assert result.source == "unavailable"
    assert result.available is False
    assert result.aligned is False
    assert result.reason == "selected revision has no frozen summary"
