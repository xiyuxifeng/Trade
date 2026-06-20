from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.enums import FormalLifecycleState, QualityStatus
from src.models.blog_article import BlogArticle
from src.models.rule_applicability import RuleApplicabilityProfile
from src.models.stage2_canonical import (
    ArticleRevision,
    ArticleStructure,
    Authors,
    AuthorProfileVersion,
    AuthorProfileVersionAudit,
    BacktestResult,
    BacktestRun,
    PromptRun,
    PromptValidationState,
    Rule,
    RuleCandidate,
    RuleVersion,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_element, _compiler, **_kw):  # noqa: ANN001
    return "JSON"


async def _build_session_factory(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'author_validated_profiles.db'}")

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
        await conn.run_sync(BacktestRun.__table__.create)
        await conn.run_sync(BacktestResult.__table__.create)
        await conn.run_sync(RuleApplicabilityProfile.__table__.create)
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


async def _seed_validated_bundle(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    source_author_key: str,
    article_suffix: str,
    title: str,
    rule_type: str,
    recommendation_status: str,
    confidence: float,
    sample_count: int,
    eligible_sample_count: int,
    evaluated_sample_count: int,
    coverage: float | None,
    insufficient_sample_status: str,
    quality_status: str,
    applicable_market_state: str | None,
    blocked_market_state: str | None,
    limitations: list[str],
    warnings: list[str],
    requested_level: str = "level_3",
    effective_level: str = "level_2",
) -> UUID:
    now = datetime(2026, 4, 2, 9, 30, tzinfo=UTC)
    article_id = uuid4()
    revision_id = uuid4()
    prompt_run_id = uuid4()
    structure_id = uuid4()
    candidate_id = uuid4()
    rule_id = uuid4()
    rule_version_id = uuid4()
    run_id = uuid4()
    result_id = uuid4()
    profile_id = uuid4()
    applicability_profile_id = uuid4()

    async with session_factory() as session:
        session.add(
            BlogArticle(
                id=article_id,
                source="tgb",
                source_article_id=f"article-{article_suffix}",
                source_url=f"https://example.com/{article_suffix}",
                title=title,
                author_name="测试作者",
                author_id=source_author_key,
                published_at=now,
                crawled_at=now,
                content_text=title,
                summary=title,
                tags=["验证"],
                content_hash=f"hash-{article_suffix}",
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
                content_hash=f"hash-{article_suffix}",
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
                run_id=f"prompt-{article_suffix}",
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
                input_hash=f"input-{article_suffix}",
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
                candidate_fingerprint=f"candidate-{article_suffix}",
                rule_type=rule_type,
                canonical_payload={},
                evidence_json={},
                explicit_fields={},
                inferred_fields={},
                missing_fields={},
                data_dependencies={"required": ["ohlcv_1d"]},
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
                business_key=f"rule-{article_suffix}",
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
                canonical_fingerprint=f"rv-fp-{article_suffix}",
                schema_version="rule-v1",
                lifecycle_state=FormalLifecycleState.approved,
                title=title,
                description=f"{title} 描述",
                rule_type=rule_type,
                instrument_scope={"instrument_focus": ["stock"]},
                condition_json={},
                action_json={},
                parameter_json={},
                data_dependencies={"required": ["ohlcv_1d"]},
                evidence_json={},
                quality_status=QualityStatus.complete,
                parent_version_id=None,
                published_at=None,
                published_by=None,
                superseded_at=None,
                created_by="stage4",
                updated_by="stage4",
            )
        )
        session.add(
            BacktestRun(
                run_id=run_id,
                rule_version_id=rule_version_id,
                rule_version_fingerprint=f"rv-fp-{article_suffix}",
                rule_version_no=1,
                rule_family_id=None,
                rule_family_fingerprint=None,
                frozen_rule_version_ids=[str(rule_version_id)],
                frozen_rule_version_fingerprints=[f"rv-fp-{article_suffix}"],
                date_from=date(2026, 1, 1),
                date_to=date(2026, 3, 31),
                universe_json={"symbols": ["000001.SZ"]},
                benchmark_symbol="000300.SH",
                mode="historical",
                requested_level=requested_level,
                effective_level=effective_level,
                level_policy_version="stage6-level-policy-v1",
                dataset_snapshot_id=uuid4(),
                dataset_fingerprint=f"dataset-fp-{article_suffix}",
                market_snapshot_ids=[] if requested_level == "level_3" else [],
                market_snapshot_fingerprints=[],
                market_state_model_version="market-state-v1",
                indicator_version="dataset-bound-v1",
                engine_version="stage6-foundation-v1",
                execution_policy_version="stage6-snapshot-only-v1",
                recommendation_policy_version="stage6-recommendation-policy-v1",
                decision_time_policy="cn-a-share-close-plus-availability-v1",
                request_fingerprint=f"request-fp-{article_suffix}",
                reproducibility_fingerprint=f"run-rp-{article_suffix}",
                snapshot_only=True,
                status="completed_valid" if insufficient_sample_status == "sufficient" else "completed_invalid",
                coverage_state="runnable",
                quality_state="complete",
                downgrade_reason="缺失 Kaipan 数据时按 Level 2 解释覆盖限制。" if requested_level == "level_3" else None,
                repair_guidance=[],
                unavailable_reasons=[],
                limitations=limitations,
                progress_json={},
                audit_json={},
                actor_id="operator",
                actor_role="operator",
                reason="stage6",
                source_surface="/rules/results",
                before_state_json=None,
                after_state_json=None,
            )
        )
        session.add(
            BacktestResult(
                result_id=result_id,
                run_id=run_id,
                input_fingerprint=f"input-fp-{article_suffix}",
                result_fingerprint=f"result-fp-{article_suffix}",
                reproducibility_fingerprint=f"result-rp-{article_suffix}",
                status="completed_partial" if insufficient_sample_status != "sufficient" else "completed",
                requested_level=requested_level,
                effective_level=effective_level,
                level_policy_version="stage6-level-policy-v1",
                market_state_model_version="market-state-v1",
                market_state_source_version="features-v1",
                market_state_result_version="market-state-results-v1",
                decision_time_policy="cn-a-share-close-plus-availability-v1",
                overall_metrics={"total_return": 0.12 if recommendation_status == "recommended" else -0.08, "win_rate": 0.62 if recommendation_status == "recommended" else 0.33},
                per_market_state_metrics=[],
                per_rule_metrics=[],
                sample_state_counts={"eligible": eligible_sample_count, "evaluated_true": evaluated_sample_count},
                coverage_json={
                    "market_state": {"state": "ready", "available": True},
                    "samples": {"state": "ready", "count": evaluated_sample_count},
                    "kaipan": {"state": "insufficient_coverage", "available": None, "impact": "缺失 Kaipan 数据只记为覆盖限制。"} if requested_level == "level_3" else {"state": "not_required", "available": None},
                },
                warnings=warnings,
                limitations=limitations,
                provenance_json={},
                audit_json={},
            )
        )
        session.add(
            RuleApplicabilityProfile(
                profile_id=profile_id,
                applicability_profile_id=applicability_profile_id,
                rule_id=str(rule_version_id),
                profile_version="rule-applicability-v1",
                source_backtest_id=str(run_id),
                rule_version_id=rule_version_id,
                rule_version_fingerprint=f"rv-fp-{article_suffix}",
                rule_version_no=1,
                frozen_rule_version_ids=[str(rule_version_id)],
                frozen_rule_version_fingerprints=[f"rv-fp-{article_suffix}"],
                dataset_snapshot_id=uuid4(),
                dataset_fingerprint=f"dataset-fp-{article_suffix}",
                market_state_definition_version="market-state-v1",
                market_state_model_version="market-state-v1",
                market_state_source_version="features-v1",
                lifecycle_state=FormalLifecycleState.draft,
                result_status="ready" if quality_status == "complete" and insufficient_sample_status == "sufficient" else "partial",
                source_backtest_run_ids=[str(run_id)],
                source_backtest_result_ids=[str(result_id)],
                source_result_fingerprints=[f"result-fp-{article_suffix}"],
                market_snapshot_ids=[],
                market_snapshot_fingerprints=[],
                sample_count=sample_count,
                eligible_sample_count=eligible_sample_count,
                evaluated_sample_count=evaluated_sample_count,
                coverage=coverage,
                return_metric=0.12 if recommendation_status == "recommended" else -0.08,
                win_rate=0.62 if recommendation_status == "recommended" else 0.33,
                maximum_drawdown=-0.05 if recommendation_status == "recommended" else -0.12,
                recommendation_status=recommendation_status,
                data_level=effective_level,
                requested_level=requested_level,
                effective_level=effective_level,
                level_policy_version="stage6-level-policy-v1",
                quality_status=quality_status,
                insufficient_sample_status=insufficient_sample_status,
                limitations=limitations,
                warnings=warnings,
                recommendation_policy_version="stage6-recommendation-policy-v1",
                review_status="approved",
                min_sample_count=5,
                confidence=confidence,
                applicable_regimes=[
                    {
                        "regime_label": applicable_market_state,
                        "decision": "recommended",
                        "score": 0.74,
                        "sample_count": sample_count,
                        "confidence": confidence,
                        "low_sample": insufficient_sample_status == "insufficient_sample",
                        "reason": f"{applicable_market_state} 下更稳定" if applicable_market_state else "",
                        "evidence": ["market-state-evidence"],
                    }
                ]
                if applicable_market_state
                else [],
                blocked_regimes=[
                    {
                        "regime_label": blocked_market_state,
                        "decision": "blocked",
                        "score": 0.28,
                        "sample_count": sample_count,
                        "confidence": confidence,
                        "low_sample": insufficient_sample_status == "insufficient_sample",
                        "reason": f"{blocked_market_state} 下回撤更大" if blocked_market_state else "",
                        "evidence": ["market-state-warning"],
                    }
                ]
                if blocked_market_state
                else [],
                neutral_regimes=[],
                best_market_conditions={},
                worst_market_conditions={},
                summary={
                    "profile_version_no": 1,
                    "sample_state_counts": {"eligible": eligible_sample_count, "evaluated_true": evaluated_sample_count},
                    "coverage": {"market_state": "ready"},
                },
                storage_ref={"formal_source": "backtest_runs/backtest_results"},
                created_by="operator",
            )
        )
        await session.commit()
    return profile_id


@pytest.mark.asyncio()
async def test_generate_validated_profile_draft_uses_formal_sources_only_and_preserves_traceability(tmp_path: Path) -> None:
    from src.services.author_validated_profile_service import (
        AuthorValidatedProfileGenerationRequest,
        AuthorValidatedProfileService,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    strong_profile_id = await _seed_validated_bundle(
        session_factory,
        source_author_key="author-001",
        article_suffix="strong",
        title="放量突破介入",
        rule_type="entry",
        recommendation_status="recommended",
        confidence=0.82,
        sample_count=12,
        eligible_sample_count=12,
        evaluated_sample_count=11,
        coverage=0.91,
        insufficient_sample_status="sufficient",
        quality_status="complete",
        applicable_market_state="强势上行",
        blocked_market_state="缩量震荡",
        limitations=["画像来自正式回测与规则适用性证据，不代表作者真实实盘表现。"],
        warnings=[],
    )
    weak_profile_id = await _seed_validated_bundle(
        session_factory,
        source_author_key="author-001",
        article_suffix="weak",
        title="高开追涨",
        rule_type="entry",
        recommendation_status="not_recommended",
        confidence=0.7,
        sample_count=9,
        eligible_sample_count=9,
        evaluated_sample_count=8,
        coverage=0.76,
        insufficient_sample_status="sufficient",
        quality_status="partial",
        applicable_market_state=None,
        blocked_market_state="情绪退潮",
        limitations=["部分交易日缺少市场状态，当前结果只能作为部分验证证据。"],
        warnings=["部分交易日缺少可证明当时可用的市场状态。"],
        requested_level="level_2",
        effective_level="level_2",
    )
    service = AuthorValidatedProfileService(session_scope_factory=session_scope)

    draft = await service.generate_draft(
        AuthorValidatedProfileGenerationRequest(
            author_id=author_id,
            applicability_profile_ids=[strong_profile_id, weak_profile_id],
            evidence_from=date(2026, 1, 1),
            evidence_to=date(2026, 3, 31),
            effective_from=date(2026, 4, 1),
            reason="根据正式回测与适用性证据生成作者验证画像草稿",
        ),
        actor_id="operator-a",
        actor_role="operator",
    )

    assert draft.profile_kind == "validated"
    assert draft.lifecycle_state == "draft"
    validated_profile = draft.payload["validated_profile"]
    assert validated_profile["strong_rule_types"][0]["rule_type"] == "entry"
    assert validated_profile["weak_rule_types"][0]["rule_type"] == "entry"
    assert validated_profile["strong_market_states"][0]["market_state"] == "强势上行"
    assert validated_profile["weak_market_states"][0]["market_state"] in {"缩量震荡", "情绪退潮"}
    assert validated_profile["data_coverage"]["total_applicability_profiles"] == 2
    assert validated_profile["sample_count"]["total"] == 21
    assert validated_profile["confidence"]["overall"] > 0
    assert draft.source_bindings["rule_applicability_profile_ids"]["requested_profile_ids"] == [str(strong_profile_id), str(weak_profile_id)]
    assert len(draft.source_bindings["backtest_run_ids"]["resolved_run_ids"]) == 2
    assert len(draft.source_bindings["backtest_result_ids"]["resolved_result_ids"]) == 2
    assert draft.source_versions["aggregation_version"] == "author_validated_profile_summary_deterministic_v1"
    assert "真实实盘" in draft.limitations[0]
    assert all("胜率" not in conclusion["text"] for conclusion in draft.payload["conclusions"])

    await engine.dispose()


@pytest.mark.asyncio()
async def test_generate_validated_profile_draft_keeps_insufficient_sample_and_missing_kaipan_as_limitations(tmp_path: Path) -> None:
    from src.services.author_validated_profile_service import (
        AuthorValidatedProfileGenerationRequest,
        AuthorValidatedProfileService,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    profile_id = await _seed_validated_bundle(
        session_factory,
        source_author_key="author-001",
        article_suffix="limited",
        title="竞价强追",
        rule_type="entry",
        recommendation_status="limited",
        confidence=0.24,
        sample_count=3,
        eligible_sample_count=3,
        evaluated_sample_count=0,
        coverage=0.41,
        insufficient_sample_status="insufficient_sample",
        quality_status="partial",
        applicable_market_state=None,
        blocked_market_state=None,
        limitations=[
            "缺失 Kaipan 数据只会记为覆盖限制，不会被当成规则失败。",
            "样本不足时只能标记为 insufficient_sample。",
        ],
        warnings=["缺失 Kaipan 数据的样本不会计入条件不成立、亏损或成功覆盖。"],
    )
    service = AuthorValidatedProfileService(session_scope_factory=session_scope)

    draft = await service.generate_draft(
        AuthorValidatedProfileGenerationRequest(
            author_id=author_id,
            applicability_profile_ids=[profile_id],
            evidence_from=date(2026, 1, 1),
            evidence_to=date(2026, 3, 31),
            effective_from=date(2026, 4, 1),
            reason="生成低样本验证画像草稿",
        ),
        actor_id="operator-a",
        actor_role="operator",
    )

    validated_profile = draft.payload["validated_profile"]
    assert draft.quality_status == "partial"
    assert validated_profile["sample_count"]["insufficient_sample_profiles"] == 1
    assert validated_profile["data_coverage"]["kaipan_limitation_profiles"] == 1
    assert validated_profile["weak_rule_types"] == []
    assert any("insufficient_sample" in item for item in draft.limitations)
    assert any("Kaipan" in item for item in draft.limitations)
    assert draft.partial_reasons

    await engine.dispose()


@pytest.mark.asyncio()
async def test_generate_validated_profile_draft_does_not_overwrite_reviewed_or_published_profiles(tmp_path: Path) -> None:
    from src.services.author_profile_service import AuthorProfileTransitionRequest
    from src.services.author_validated_profile_service import (
        AuthorValidatedProfileGenerationRequest,
        AuthorValidatedProfileService,
    )

    session_scope, session_factory, engine = await _build_session_factory(tmp_path)
    author_id = await _seed_author(session_factory)
    profile_id = await _seed_validated_bundle(
        session_factory,
        source_author_key="author-001",
        article_suffix="stable",
        title="趋势低吸",
        rule_type="entry",
        recommendation_status="recommended",
        confidence=0.8,
        sample_count=10,
        eligible_sample_count=10,
        evaluated_sample_count=9,
        coverage=0.88,
        insufficient_sample_status="sufficient",
        quality_status="complete",
        applicable_market_state="强趋势",
        blocked_market_state="弱趋势",
        limitations=["画像来自正式回测与规则适用性证据，不代表作者真实实盘表现。"],
        warnings=[],
    )
    service = AuthorValidatedProfileService(session_scope_factory=session_scope)

    first = await service.generate_draft(
        AuthorValidatedProfileGenerationRequest(
            author_id=author_id,
            applicability_profile_ids=[profile_id],
            evidence_from=date(2026, 1, 1),
            evidence_to=date(2026, 3, 31),
            effective_from=date(2026, 4, 1),
            effective_to=date(2026, 6, 30),
        ),
        actor_id="operator-a",
        actor_role="operator",
    )
    first = await service._profile_service.submit_for_review(  # noqa: SLF001
        first.author_profile_version_id,
        AuthorProfileTransitionRequest(reason="提交审核"),
        actor_id="operator-a",
        actor_role="operator",
    )
    published = await service._profile_service.publish(  # noqa: SLF001
        first.author_profile_version_id,
        AuthorProfileTransitionRequest(reason="人工发布"),
        actor_id="reviewer-a",
        actor_role="operator",
    )

    revision = await service.generate_draft(
        AuthorValidatedProfileGenerationRequest(
            author_id=author_id,
            author_profile_id=UUID(published.author_profile_id),
            applicability_profile_ids=[profile_id],
            evidence_from=date(2026, 1, 1),
            evidence_to=date(2026, 3, 31),
            effective_from=date(2026, 4, 1),
            effective_to=date(2026, 6, 30),
            reason="新验证证据只生成草稿",
        ),
        actor_id="operator-a",
        actor_role="operator",
    )

    assert revision.lifecycle_state == "draft"
    assert revision.version_no == 2
    still_published = await service._profile_service.get_version(  # noqa: SLF001
        published.author_profile_version_id,
        actor_id="viewer",
        actor_role="viewer",
    )
    assert still_published.lifecycle_state == "published"

    await engine.dispose()
