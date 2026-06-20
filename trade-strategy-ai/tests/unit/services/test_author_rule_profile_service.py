from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from src.domain.enums import FormalLifecycleState, QualityStatus
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    Authors,
    AuthorProfileVersion,
    AuthorProfileVersionAudit,
    PromptRun,
    PromptValidationState,
    Rule,
    RuleCandidate,
    RuleFamily,
    RuleFamilyMembership,
    RuleVersion,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


async def _build_session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'author_rule_profiles.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def _register_char_length(dbapi_connection, _connection_record):  # noqa: ANN001
        dbapi_connection.create_function("char_length", 1, lambda value: len(value) if value is not None else 0)

    async with engine.begin() as conn:
        await conn.run_sync(BlogArticle.__table__.create)
        await conn.run_sync(Authors.__table__.create)
        await conn.run_sync(ArticleRevision.__table__.create)
        await conn.run_sync(PromptRun.__table__.create)
        await conn.run_sync(ArticleStructure.__table__.create)
        await conn.run_sync(RuleCandidate.__table__.create)
        await conn.run_sync(Rule.__table__.create)
        await conn.run_sync(RuleVersion.__table__.create)
        await conn.run_sync(RuleFamily.__table__.create)
        await conn.run_sync(RuleFamilyMembership.__table__.create)
        await conn.run_sync(AuthorProfileVersion.__table__.create)
        await conn.run_sync(AuthorProfileVersionAudit.__table__.create)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _session_scope, session_factory, engine


async def _seed_author(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    author_id = uuid4()
    async with session_factory() as session:
        session.add(
            Authors(
                author_id=author_id,
                source="tgb",
                source_author_key="author-001",
                display_name="测试作者",
            )
        )
        await session.commit()
    return author_id


async def _seed_rule_version(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    source_author_key: str,
    source_article_suffix: str,
    title: str,
    rule_type: str,
    threshold: float,
    action_side: str = "buy",
    family: str,
    lifecycle_state: FormalLifecycleState = FormalLifecycleState.approved,
    family_name: str | None = None,
) -> tuple[UUID, UUID]:
    now = datetime(2026, 2, 1, 9, 30, tzinfo=UTC)
    article_id = uuid4()
    revision_id = uuid4()
    prompt_run_id = uuid4()
    structure_id = uuid4()
    candidate_id = uuid4()
    rule_id = uuid4()
    rule_version_id = uuid4()
    async with session_factory() as session:
        session.add(
            BlogArticle(
                id=article_id,
                source="tgb",
                source_article_id=f"article-{source_article_suffix}",
                source_url=f"https://example.com/{source_article_suffix}",
                title=title,
                author_name="测试作者",
                author_id=source_author_key,
                published_at=now,
                crawled_at=now,
                content_text=title,
                summary=title,
                tags=["规则"],
                content_hash=f"hash-{source_article_suffix}",
                view_count=0,
                like_count=0,
                bookmark_count=0,
                comment_count=0,
                comments_payload=[],
                raw_payload={},
            )
        )
        session.add(
            ArticleRevision(
                article_revision_id=revision_id,
                article_id=article_id,
                revision_no=1,
                content_hash=f"hash-{source_article_suffix}",
                content_text=title,
                content_html=None,
                source_payload={},
                captured_at=now,
                quality_status=QualityStatus.complete,
            )
        )
        session.add(
            PromptRun(
                prompt_run_id=prompt_run_id,
                run_id=f"prompt-{source_article_suffix}",
                article_id=article_id,
                prompt_name="article_analysis_v1",
                prompt_version="article_analysis_v1",
                schema_name="article_analysis_v1",
                schema_version="article_analysis_v1",
                provider="test-provider",
                model="gpt-5.4",
                input_object_type="article_revision",
                input_object_id=str(article_id),
                input_version_id=str(revision_id),
                input_hash=f"input-{source_article_suffix}",
                request_json={},
                raw_output={},
                raw_output_text="{}",
                validation_state=PromptValidationState.valid,
                validation_errors={},
                retry_count=0,
                token_usage={"total_tokens": 10},
                cost_amount=0.01,
                cost_currency="USD",
                started_at=now,
                completed_at=now,
            )
        )
        session.add(
            ArticleStructure(
                article_structure_id=structure_id,
                article_id=article_id,
                article_revision_id=revision_id,
                prompt_run_id=prompt_run_id,
                schema_version="article_structure_v1",
                payload={"author_id": source_author_key},
                evidence_json={},
                missing_fields={},
                inference_fields={},
                lifecycle_state=FormalLifecycleState.approved,
                quality_status=QualityStatus.complete,
                approved_by="reviewer",
                approved_at=now,
                supersedes_id=None,
                created_by="stage3",
                updated_by="stage3",
            )
        )
        session.add(
            RuleCandidate(
                rule_candidate_id=candidate_id,
                article_structure_id=structure_id,
                source_article_id=article_id,
                candidate_index=1,
                candidate_fingerprint=f"candidate-{source_article_suffix}",
                rule_type=rule_type,
                canonical_payload={
                    "rule_type": rule_type,
                    "instrument_focus": ["stock"],
                    "timeframe": "5m",
                    "holding_period": "intraday",
                    "condition": {"logic": "single", "clauses": [{"field": "volume", "operator": "gt", "value": threshold, "lookback": 5, "unit": "x"}]},
                    "action": {"type": "enter", "side": action_side, "price_reference": "market"},
                    "risk_controls": [],
                    "data_dependencies": ["ohlcv_1d", "volume"],
                    "market_state_applicability": {"status": "not_declared", "explicit_conditions": []},
                    "quantification": {
                        "status": "executable" if threshold <= 1.6 else "partially_executable",
                        "missing_fields": [] if threshold <= 1.6 else ["threshold"],
                        "ambiguous_terms": [] if threshold <= 1.6 else ["放量"],
                        "manual_review_required": threshold > 1.6,
                    },
                },
                evidence_json={"quotes": [title]},
                explicit_fields={},
                inferred_fields={},
                missing_fields={},
                data_dependencies={"required": ["ohlcv_1d", "volume"]},
                backtestability_status="ready",
                review_state="approved",
                quality_status=QualityStatus.complete,
                created_by="stage4",
                updated_by="stage4",
            )
        )
        session.add(
            Rule(
                rule_id=rule_id,
                business_key=f"rule-{source_article_suffix}",
                current_published_version_id=None,
                created_at=now,
                created_by="stage4",
                updated_at=now,
                updated_by="stage4",
            )
        )
        session.add(
            RuleVersion(
                rule_version_id=rule_version_id,
                rule_id=rule_id,
                version_no=1,
                source_candidate_id=candidate_id,
                canonical_fingerprint=f"rv-fp-{source_article_suffix}",
                schema_version="rule-v1",
                lifecycle_state=lifecycle_state,
                title=title,
                description=f"{title} 描述",
                rule_type=rule_type,
                instrument_scope={"instrument_focus": ["stock"]},
                condition_json={"logic": "single", "clauses": [{"field": "volume", "operator": "gt", "value": threshold, "lookback": 5, "unit": "x"}]},
                action_json={"type": "enter", "side": action_side, "price_reference": "market"},
                parameter_json={
                    "timeframe": "5m",
                    "holding_period": "intraday",
                    "market_state_applicability": {"status": "not_declared", "explicit_conditions": []},
                    "quantification": {
                        "status": "executable" if threshold <= 1.6 else "partially_executable",
                        "missing_fields": [] if threshold <= 1.6 else ["threshold"],
                        "ambiguous_terms": [] if threshold <= 1.6 else ["放量"],
                        "manual_review_required": threshold > 1.6,
                    },
                },
                data_dependencies={"required": ["ohlcv_1d", "volume"]},
                evidence_json={"quantification": {"status": "executable"}, "quotes": [title]},
                quality_status=QualityStatus.complete,
                parent_version_id=None,
                published_at=None,
                published_by=None,
                superseded_at=None,
                created_by="stage4",
                updated_by="stage4",
            )
        )
        family_row = (await session.execute(select(RuleFamily).where(RuleFamily.family_key == family))).scalars().first()
        if family_row is None:
            family_row = RuleFamily(
                rule_family_id=uuid4(),
                family_key=family,
                canonical_fingerprint=f"{family}-fp",
                name=family_name or family,
                lifecycle_state=FormalLifecycleState.approved,
                quality_status=QualityStatus.complete,
                created_by="stage4",
                updated_by="stage4",
            )
            session.add(family_row)
            await session.flush()
        session.add(
            RuleFamilyMembership(
                membership_id=uuid4(),
                rule_family_id=family_row.rule_family_id,
                rule_version_id=rule_version_id,
                member_role="representative",
                parameter_distance={"threshold": threshold},
                approved_by="reviewer",
                approved_at=now,
            )
        )
        await session.commit()
    return rule_version_id, family_row.rule_family_id


@pytest.mark.asyncio()
async def test_generate_author_rule_profile_draft_is_deterministic_and_does_not_mutate_rule_governance(tmp_path: Path) -> None:
    from src.services.author_rule_profile_service import AuthorRuleProfileGenerationRequest, AuthorRuleProfileService

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    first_rule_id, first_family_id = await _seed_rule_version(
        session_factory,
        source_author_key="author-001",
        source_article_suffix="001",
        title="放量突破介入",
        rule_type="entry",
        threshold=1.5,
        action_side="buy",
        family="breakout",
        family_name="放量突破族",
    )
    second_rule_id, _second_family_id = await _seed_rule_version(
        session_factory,
        source_author_key="author-001",
        source_article_suffix="002",
        title="放量回踩介入",
        rule_type="entry",
        threshold=1.8,
        action_side="buy",
        family="breakout",
        family_name="放量突破族",
    )
    third_rule_id, third_family_id = await _seed_rule_version(
        session_factory,
        source_author_key="author-001",
        source_article_suffix="003",
        title="放量突破反手离场",
        rule_type="entry",
        threshold=1.5,
        action_side="sell",
        family="reversal",
        family_name="反手离场族",
    )

    async with session_factory() as session:
        before_versions = {
            row.rule_version_id: (row.lifecycle_state, row.updated_at)
            for row in (await session.execute(select(RuleVersion))).scalars().all()
        }
        before_memberships = [
            (row.rule_family_id, row.rule_version_id, row.member_role)
            for row in (await session.execute(select(RuleFamilyMembership))).scalars().all()
        ]

    service = AuthorRuleProfileService(session_scope_factory=session_scope)
    request = AuthorRuleProfileGenerationRequest(
        author_id=author_id,
        rule_version_ids=[first_rule_id, second_rule_id, third_rule_id],
        rule_family_ids=[first_family_id, third_family_id],
        evidence_from=date(2026, 1, 1),
        evidence_to=date(2026, 3, 31),
        effective_from=date(2026, 4, 1),
        reason="生成作者规则画像草稿",
    )

    first = await service.generate_draft(request, actor_id="operator-a", actor_role="operator")
    second = await service.generate_draft(
        request.model_copy(update={"author_profile_id": UUID(first.author_profile_id)}),
        actor_id="operator-a",
        actor_role="operator",
    )

    assert first.profile_kind == "rule"
    assert first.version_no == 1
    assert first.profile_fingerprint == second.profile_fingerprint
    assert first.evidence_fingerprint == second.evidence_fingerprint
    rule_profile = first.payload["rule_profile"]
    assert rule_profile["rule_type_distribution"][0]["rule_type"] == "entry"
    assert rule_profile["quantifiability"]["status_counts"] == {"partial": 1, "quantifiable": 2}
    assert rule_profile["repeat_conflict_summary"]["conflict_pair_count"] == 1
    assert rule_profile["repeat_conflict_summary"]["parameter_variant_pair_count"] == 1
    assert {item["rule_family_id"] for item in rule_profile["rule_families"] if item["rule_family_id"]} == {
        str(first_family_id),
        str(third_family_id),
    }
    assert rule_profile["representative_rules"][0]["reason"]
    assert first.source_bindings["rule_version_ids"]["reviewed_rule_version_ids"] == [
        str(first_rule_id),
        str(second_rule_id),
        str(third_rule_id),
    ]
    assert first.source_bindings["rule_family_ids"]["reviewed_rule_family_ids"]
    assert any(item["lane"] == "rule_statistics" for item in first.payload["conclusions"][0]["evidence"])

    async with session_factory() as session:
        after_versions = {
            row.rule_version_id: (row.lifecycle_state, row.updated_at)
            for row in (await session.execute(select(RuleVersion))).scalars().all()
        }
        after_memberships = [
            (row.rule_family_id, row.rule_version_id, row.member_role)
            for row in (await session.execute(select(RuleFamilyMembership))).scalars().all()
        ]

    assert before_versions == after_versions
    assert before_memberships == after_memberships

    await engine.dispose()


@pytest.mark.asyncio()
async def test_generate_author_rule_profile_draft_marks_missing_unreviewed_and_unaligned_evidence_as_insufficient(tmp_path: Path) -> None:
    from src.services.author_rule_profile_service import AuthorRuleProfileGenerationRequest, AuthorRuleProfileService

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    reviewed_rule_id, family_id = await _seed_rule_version(
        session_factory,
        source_author_key="author-001",
        source_article_suffix="010",
        title="强势股放量介入",
        rule_type="entry",
        threshold=1.5,
        family="breakout",
    )
    unreviewed_rule_id, _ = await _seed_rule_version(
        session_factory,
        source_author_key="author-001",
        source_article_suffix="011",
        title="缩量低吸",
        rule_type="entry",
        threshold=1.4,
        family="dip-buy",
        lifecycle_state=FormalLifecycleState.draft,
    )
    unaligned_rule_id, _ = await _seed_rule_version(
        session_factory,
        source_author_key="other-author",
        source_article_suffix="012",
        title="他人规则",
        rule_type="exit",
        threshold=1.7,
        family="other-family",
    )
    missing_rule_id = uuid4()

    service = AuthorRuleProfileService(session_scope_factory=session_scope)
    draft = await service.generate_draft(
        AuthorRuleProfileGenerationRequest(
            author_id=author_id,
            rule_version_ids=[reviewed_rule_id, unreviewed_rule_id, unaligned_rule_id, missing_rule_id],
            rule_family_ids=[family_id],
            evidence_from=date(2026, 1, 1),
            evidence_to=date(2026, 3, 31),
            effective_from=date(2026, 4, 1),
            reason="证据不完整",
        ),
        actor_id="operator-a",
        actor_role="operator",
    )

    assert draft.profile_kind == "rule"
    assert draft.quality_status == "partial"
    assert draft.status_state == "partial"
    assert any("证据质量不是完整验证状态" in reason for reason in draft.partial_reasons)
    quality = draft.payload["quality"]
    assert quality["status"] == "partial"
    assert "issues" in quality
    issues = quality["issues"]
    assert any(item["reason"] == "部分规则版本未找到。" for item in issues)
    assert any(item["reason"] == "部分规则版本尚未进入已审核状态。" for item in issues)
    assert any(item["reason"] == "部分规则版本来源未对齐当前作者。" for item in issues)
    assert draft.source_bindings["rule_version_ids"]["missing_rule_version_ids"] == [str(missing_rule_id)]

    await engine.dispose()
