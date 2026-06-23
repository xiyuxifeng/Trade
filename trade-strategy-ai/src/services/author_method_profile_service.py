from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
import hashlib
import json
from typing import Any, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.author_profile_repository import AuthorProfileRepository
from src.db.session import get_session_factory
from src.domain.enums import AuthorProfileKind, QualityStatus
from src.llm.client import from_env_and_config
from src.llm.prompt_registry import get_prompt_spec
from src.llm.runtime import LLMClientGateway, LLMInvocationTrace, PromptGateway, invoke_with_bounded_retry
from src.models.blog_article import BlogArticle
from src.models.stage2_canonical import ArticleRevision, ArticleStructure, Authors, PromptRun, PromptValidationState
from src.services.author_profile_service import AuthorProfileDraftRequest, AuthorProfileService, AuthorProfileVersionView


AUTHOR_METHOD_PROFILE_SCHEMA_VERSION = "author-profile-v1"
AUTHOR_METHOD_PROFILE_LIMITATION = "画像来自结构化文章表达，不代表作者真实实盘表现。"


class AuthorMethodProfileGenerationRequest(BaseModel):
    author_id: UUID
    article_structure_ids: list[UUID] = Field(min_length=1, max_length=20)
    author_profile_id: UUID | None = None
    parent_version_id: UUID | None = None
    supersedes_version_id: UUID | None = None
    evidence_from: date | None = None
    evidence_to: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    reason: str | None = None
    source_surface: str = "/authors"

    @field_validator("article_structure_ids")
    @classmethod
    def _dedupe_structure_ids(cls, value: list[UUID]) -> list[UUID]:
        deduped = list(dict.fromkeys(value))
        if not deduped:
            raise ValueError("至少需要一个结构化文章结果。")
        return deduped


class _StructuredArticleBundle(BaseModel):
    article: BlogArticle
    revision: ArticleRevision
    structure: ArticleStructure
    prompt_run: PromptRun

    model_config = {"arbitrary_types_allowed": True}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _extract_display(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if "name" in item:
            return str(item["name"])
        if "market_state" in item:
            return str(item["market_state"])
    return json.dumps(_jsonable(item), ensure_ascii=False, sort_keys=True)


class AuthorMethodProfileService:
    def __init__(
        self,
        *,
        session_scope_factory: Callable[[], Any] | None = None,
        gateway: PromptGateway | None = None,
        repository: AuthorProfileRepository | None = None,
        profile_service: AuthorProfileService | None = None,
        model: str = "gpt-5.4",
    ) -> None:
        self._session_scope_factory = session_scope_factory or self._default_session_scope_factory
        self._gateway = gateway or LLMClientGateway.from_config(
            from_env_and_config(provider=None, model=model, url=None, api_key=None)
        )
        self._repository = repository or AuthorProfileRepository()
        self._profile_service = profile_service or AuthorProfileService(
            repository=self._repository,
            session_scope_factory=self._session_scope_factory,
        )
        self._model = model

    @staticmethod
    @asynccontextmanager
    async def _default_session_scope_factory():
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def generate_draft(
        self,
        request: AuthorMethodProfileGenerationRequest,
        *,
        actor_id: str,
        actor_role: str,
    ) -> AuthorProfileVersionView:
        if actor_role not in {"operator", "admin"}:
            raise PermissionError("operator permission is required to create an author method profile draft")

        async with self._session_scope_factory() as session:
            author = await session.get(Authors, request.author_id)
            if author is None:
                raise LookupError("author not found")

            bundles = await self._load_bundles(session, structure_ids=request.article_structure_ids)
            aligned, issues = self._partition_bundles(author=author, requested_ids=request.article_structure_ids, bundles=bundles)
            if not aligned:
                draft_request = self._build_insufficient_draft_request(request, issues)
                return await self._profile_service.create_draft(draft_request, actor_id=actor_id, actor_role=actor_role)

            prompt_spec = get_prompt_spec("author_method_profile_batch_v1")
            batch_input = self._build_batch_input(author=author, request=request, bundles=aligned)
            identity = _fingerprint(
                {
                    "author_id": request.author_id,
                    "article_structure_ids": request.article_structure_ids,
                    "evidence_from": request.evidence_from,
                    "evidence_to": request.evidence_to,
                    "effective_from": request.effective_from,
                    "effective_to": request.effective_to,
                    "prompt_version": prompt_spec.prompt_version,
                    "schema_version": prompt_spec.schema_version,
                    "model": self._model,
                }
            )
            prompt_run = await self._find_cached_prompt_run(session, identity=identity)
            if prompt_run is None:
                trace, retry_count = await invoke_with_bounded_retry(
                    self._gateway,
                    prompt_name=prompt_spec.prompt_name,
                    system_prompt=prompt_spec.load_prompt_text(),
                    user_prompt=json.dumps(batch_input, ensure_ascii=False, sort_keys=True),
                    model=self._model,
                )
                validated = prompt_spec.validate_output(trace.data).model_dump(mode="json")
                prompt_run = await self._save_prompt_run(
                    session,
                    author_id=request.author_id,
                    identity=identity,
                    prompt_name=prompt_spec.prompt_name,
                    schema_name=prompt_spec.schema_name,
                    batch_id=str(batch_input["batch_id"]),
                    batch_input=batch_input,
                    trace=trace,
                    retry_count=retry_count,
                )
            else:
                validated = prompt_spec.validate_output(prompt_run.raw_output or {}).model_dump(mode="json")

        warnings = list((validated.get("quality") or {}).get("warnings", []))
        if len(aligned) < 10:
            warnings.append("当前批次少于 10 篇结构化文章，结果只能作为部分证据草稿。")
        draft_request = self._build_draft_request(
            request=request,
            bundles=aligned,
            prompt_run=prompt_run,
            validated=validated,
            warnings=warnings,
        )
        return await self._profile_service.create_draft(draft_request, actor_id=actor_id, actor_role=actor_role)

    async def _load_bundles(self, session: AsyncSession, *, structure_ids: list[UUID]) -> list[_StructuredArticleBundle]:
        stmt = (
            select(ArticleStructure, PromptRun, ArticleRevision, BlogArticle)
            .join(PromptRun, PromptRun.prompt_run_id == ArticleStructure.prompt_run_id)
            .join(ArticleRevision, ArticleRevision.article_revision_id == ArticleStructure.article_revision_id)
            .join(BlogArticle, BlogArticle.id == ArticleStructure.article_id)
            .where(ArticleStructure.article_structure_id.in_(structure_ids))
        )
        rows = (await session.execute(stmt)).all()
        return [
            _StructuredArticleBundle(structure=structure, prompt_run=prompt_run, revision=revision, article=article)
            for structure, prompt_run, revision, article in rows
        ]

    def _partition_bundles(
        self,
        *,
        author: Authors,
        requested_ids: list[UUID],
        bundles: list[_StructuredArticleBundle],
    ) -> tuple[list[_StructuredArticleBundle], list[dict[str, Any]]]:
        bundle_by_id = {bundle.structure.article_structure_id: bundle for bundle in bundles}
        aligned: list[_StructuredArticleBundle] = []
        issues: list[dict[str, Any]] = []
        for structure_id in requested_ids:
            bundle = bundle_by_id.get(structure_id)
            if bundle is None:
                issues.append({"article_structure_id": str(structure_id), "reason": "未找到结构化文章结果。"})
                continue
            article_matches = bundle.article.source == author.source and bundle.article.author_id == author.source_author_key
            payload_matches = (bundle.structure.payload or {}).get("author_id") == author.source_author_key
            revision_matches = bundle.prompt_run.input_version_id == str(bundle.revision.article_revision_id)
            valid_prompt = bundle.prompt_run.validation_state in {PromptValidationState.valid, PromptValidationState.repaired}
            if article_matches and payload_matches and revision_matches and valid_prompt:
                aligned.append(bundle)
                continue
            reasons: list[str] = []
            if not article_matches or not payload_matches:
                reasons.append("证据来源未对齐作者映射。")
            if not revision_matches:
                reasons.append("文章内容版本与结构化结果的 PromptRun 版本不一致。")
            if not valid_prompt:
                reasons.append("结构化文章结果未处于有效校验状态。")
            issues.append(
                {
                    "article_structure_id": str(structure_id),
                    "article_revision_id": str(bundle.revision.article_revision_id),
                    "reason": " ".join(reasons),
                }
            )
        return aligned, issues

    def _build_batch_input(
        self,
        *,
        author: Authors,
        request: AuthorMethodProfileGenerationRequest,
        bundles: list[_StructuredArticleBundle],
    ) -> dict[str, Any]:
        batch_id = _fingerprint(
            {
                "author_id": request.author_id,
                "article_structure_ids": [bundle.structure.article_structure_id for bundle in bundles],
                "effective_from": request.effective_from,
                "effective_to": request.effective_to,
            }
        )[:16]
        return {
            "author_id": str(request.author_id),
            "batch_id": batch_id,
            "date_range": {
                "start": request.evidence_from.isoformat() if request.evidence_from else None,
                "end": request.evidence_to.isoformat() if request.evidence_to else None,
            },
            "article_count": len(bundles),
            "article_structures": [
                {
                    "article_id": str(bundle.article.id),
                    "article_revision_id": str(bundle.revision.article_revision_id),
                    "article_structure_id": str(bundle.structure.article_structure_id),
                    "published_at": bundle.article.published_at.isoformat() if bundle.article.published_at else None,
                    "content_hash": bundle.revision.content_hash,
                    "payload": _jsonable(bundle.structure.payload),
                    "evidence": _jsonable(bundle.structure.evidence_json),
                    "prompt_provenance": {
                        "prompt_run_id": str(bundle.prompt_run.prompt_run_id),
                        "run_id": bundle.prompt_run.run_id,
                        "prompt_version": bundle.prompt_run.prompt_version,
                        "schema_version": bundle.prompt_run.schema_version,
                    },
                }
                for bundle in bundles
            ],
            "optional_cluster_label": author.display_name,
        }

    async def _find_cached_prompt_run(self, session: AsyncSession, *, identity: str) -> PromptRun | None:
        stmt = (
            select(PromptRun)
            .where(PromptRun.prompt_name == "author_method_profile_batch_v1")
            .where(PromptRun.prompt_version == "author_method_profile_batch_v1")
            .where(PromptRun.schema_version == "author_method_profile_batch_v1")
            .where(PromptRun.model == self._model)
            .where(PromptRun.input_hash == identity)
            .where(PromptRun.validation_state.in_([PromptValidationState.valid, PromptValidationState.repaired]))
            .order_by(PromptRun.completed_at.desc().nullslast(), PromptRun.created_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalars().first()

    async def _save_prompt_run(
        self,
        session: AsyncSession,
        *,
        author_id: UUID,
        identity: str,
        prompt_name: str,
        schema_name: str,
        batch_id: str,
        batch_input: dict[str, Any],
        trace: LLMInvocationTrace,
        retry_count: int,
    ) -> PromptRun:
        now = datetime.now(UTC)
        prompt_run = PromptRun(
            prompt_run_id=uuid4(),
            run_id=uuid4().hex,
            article_id=None,
            prompt_name=prompt_name,
            prompt_version=prompt_name,
            schema_name=schema_name,
            schema_version=prompt_name,
            provider=trace.provider,
            model=trace.model,
            input_object_type="author_method_profile_batch",
            input_object_id=str(author_id),
            input_version_id=batch_id,
            input_hash=identity,
            request_json=_jsonable(batch_input),
            raw_output=_jsonable(trace.raw_output if trace.raw_output is not None else trace.data),
            raw_output_text=trace.raw_output_text,
            validation_state=PromptValidationState.valid,
            validation_errors={},
            retry_count=retry_count,
            token_usage=_jsonable(trace.token_usage),
            cost_amount=trace.cost_amount,
            cost_currency=trace.cost_currency,
            started_at=now,
            completed_at=datetime.now(UTC),
        )
        session.add(prompt_run)
        await session.flush()
        return prompt_run

    def _build_draft_request(
        self,
        *,
        request: AuthorMethodProfileGenerationRequest,
        bundles: list[_StructuredArticleBundle],
        prompt_run: PromptRun,
        validated: dict[str, Any],
        warnings: list[str],
    ) -> AuthorProfileDraftRequest:
        method_profile = {
            "trading_style": validated.get("dominant_methods", []),
            "analysis_framework": validated.get("analysis_framework", []),
            "stock_selection_preference": validated.get("instrument_preferences", []),
            "entry_preferences": validated.get("entry_preferences", []),
            "exit_preferences": validated.get("exit_preferences", []),
            "risk_expressions": validated.get("risk_expressions", []),
            "holding_period_preferences": validated.get("holding_period_preferences", []),
            "data_dependency_preferences": validated.get("data_dependency_preferences", []),
            "market_state_assumptions": validated.get("market_state_hypotheses", []),
            "stable_traits": validated.get("stable_traits", []),
            "stage_specific_traits": validated.get("stage_specific_traits", []),
            "conflicts": validated.get("conflicts", []),
            "representative_articles": validated.get("representative_articles", []),
        }
        quality_status = QualityStatus.complete
        if warnings:
            quality_status = QualityStatus.partial
        elif (validated.get("quality") or {}).get("consistency") == "low":
            quality_status = QualityStatus.ambiguous
        article_ids = [str(bundle.article.id) for bundle in bundles]
        article_revision_ids = [str(bundle.revision.article_revision_id) for bundle in bundles]
        article_structure_ids = [str(bundle.structure.article_structure_id) for bundle in bundles]
        evidence = {
            "article_expression": [
                {
                    "article_id": str(bundle.article.id),
                    "article_revision_id": str(bundle.revision.article_revision_id),
                    "article_structure_id": str(bundle.structure.article_structure_id),
                    "content_hash": bundle.revision.content_hash,
                    "prompt_run_id": str(bundle.prompt_run.prompt_run_id),
                    "method_tags": (bundle.structure.payload or {}).get("method_tags", []),
                    "key_claims": (bundle.structure.payload or {}).get("key_claims", []),
                }
                for bundle in bundles
            ]
        }
        source_versions = {
            "article_structure_schema_versions": sorted({bundle.structure.schema_version for bundle in bundles}),
            "article_analysis_prompt_versions": sorted({bundle.prompt_run.prompt_version for bundle in bundles}),
            "article_analysis_schema_versions": sorted({bundle.prompt_run.schema_version for bundle in bundles}),
            "article_revision_content_hashes": {
                str(bundle.revision.article_revision_id): bundle.revision.content_hash for bundle in bundles
            },
            "incremental_update_scope": "changed_article_revision_group",
            "method_profile_prompt_version": prompt_run.prompt_version,
            "method_profile_prompt_schema_version": prompt_run.schema_version,
            "prompt_run_id": str(prompt_run.prompt_run_id),
            "run_id": prompt_run.run_id,
            "model": prompt_run.model,
            "token_usage": _jsonable(prompt_run.token_usage),
            "cost": {
                "amount": float(prompt_run.cost_amount) if prompt_run.cost_amount is not None else None,
                "currency": prompt_run.cost_currency,
            },
            "input_hash": prompt_run.input_hash,
        }
        payload = {
            "method_profile": method_profile,
            "quality": {
                "status": "partial" if quality_status == QualityStatus.partial else "ready",
                "coverage": (validated.get("quality") or {}).get("coverage"),
                "consistency": (validated.get("quality") or {}).get("consistency"),
                "confidence": (validated.get("quality") or {}).get("confidence"),
                "warnings": warnings,
            },
            "conclusions": self._build_conclusions(method_profile=method_profile, bundles=bundles, prompt_run=prompt_run),
            "limitations": [AUTHOR_METHOD_PROFILE_LIMITATION, *warnings],
        }
        return AuthorProfileDraftRequest(
            author_id=request.author_id,
            author_profile_id=request.author_profile_id,
            parent_version_id=request.parent_version_id,
            supersedes_version_id=request.supersedes_version_id,
            profile_kind=AuthorProfileKind.method,
            schema_version=AUTHOR_METHOD_PROFILE_SCHEMA_VERSION,
            prompt_version=prompt_run.prompt_version,
            prompt_run_id=prompt_run.prompt_run_id,
            payload=payload,
            evidence=evidence,
            source_article_ids={
                "article_ids": article_ids,
                "article_revision_ids": article_revision_ids,
                "article_structure_ids": article_structure_ids,
            },
            source_versions=source_versions,
            evidence_from=request.evidence_from,
            evidence_to=request.evidence_to,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            quality_status=quality_status,
            reason=request.reason,
            source_surface=request.source_surface,
        )

    def _build_insufficient_draft_request(
        self,
        request: AuthorMethodProfileGenerationRequest,
        issues: list[dict[str, Any]],
    ) -> AuthorProfileDraftRequest:
        return AuthorProfileDraftRequest(
            author_id=request.author_id,
            author_profile_id=request.author_profile_id,
            parent_version_id=request.parent_version_id,
            supersedes_version_id=request.supersedes_version_id,
            profile_kind=AuthorProfileKind.method,
            schema_version=AUTHOR_METHOD_PROFILE_SCHEMA_VERSION,
            payload={
                "method_profile": {
                    "trading_style": [],
                    "analysis_framework": [],
                    "stock_selection_preference": [],
                    "entry_preferences": [],
                    "exit_preferences": [],
                    "risk_expressions": [],
                    "holding_period_preferences": [],
                    "data_dependency_preferences": [],
                    "market_state_assumptions": [],
                    "stable_traits": [],
                    "stage_specific_traits": [],
                    "conflicts": [],
                    "representative_articles": [],
                },
                "quality": {
                    "status": "insufficient_evidence",
                    "warnings": ["证据来源未对齐，当前只能生成部分草稿。"],
                    "issues": issues,
                },
                "conclusions": [],
                "limitations": [AUTHOR_METHOD_PROFILE_LIMITATION, "证据来源未对齐，当前只能生成部分草稿。"],
            },
            evidence={"article_expression": [], "issues": issues},
            source_article_ids={
                "article_structure_ids": [str(item) for item in request.article_structure_ids],
                "article_revision_ids": [],
            },
            source_versions={
                "alignment_status": "insufficient_evidence",
                "incremental_update_scope": "changed_article_revision_group",
                "issues": issues,
            },
            evidence_from=request.evidence_from,
            evidence_to=request.evidence_to,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            quality_status=QualityStatus.unresolved,
            reason=request.reason,
            source_surface=request.source_surface,
        )

    def _build_conclusions(
        self,
        *,
        method_profile: dict[str, Any],
        bundles: list[_StructuredArticleBundle],
        prompt_run: PromptRun,
    ) -> list[dict[str, Any]]:
        article_refs = [
            {
                "article_id": str(bundle.article.id),
                "article_revision_id": str(bundle.revision.article_revision_id),
                "article_structure_id": str(bundle.structure.article_structure_id),
                "content_hash": bundle.revision.content_hash,
                "prompt_run_id": str(bundle.prompt_run.prompt_run_id),
            }
            for bundle in bundles
        ]
        conclusions: list[dict[str, Any]] = []
        for field, label in (
            ("trading_style", "交易风格"),
            ("analysis_framework", "分析框架"),
            ("stock_selection_preference", "选股偏好"),
            ("entry_preferences", "入场偏好"),
            ("exit_preferences", "退出偏好"),
            ("risk_expressions", "风险表达"),
            ("holding_period_preferences", "持有周期"),
            ("data_dependency_preferences", "数据依赖"),
            ("market_state_assumptions", "市场状态假设"),
        ):
            items = method_profile.get(field) or []
            if not items:
                continue
            confidence_values = [float(item.get("confidence", 0.0) or 0.0) for item in items if isinstance(item, dict)]
            evidence_texts: list[str] = []
            for item in items:
                if isinstance(item, dict):
                    evidence_texts.extend(str(value) for value in item.get("evidence", []))
            conclusions.append(
                {
                    "text": f"{label}：{'; '.join(_extract_display(item) for item in items[:3])}",
                    "evidence": [
                        {
                            **ref,
                            "quote": evidence_texts[index] if index < len(evidence_texts) else None,
                        }
                        for index, ref in enumerate(article_refs[: max(1, min(3, len(article_refs)))])
                    ],
                    "confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
                    "provenance": {
                        "lane": "article_expression",
                        "source": "llm_summary",
                        "prompt_run_id": str(prompt_run.prompt_run_id),
                        "run_id": prompt_run.run_id,
                    },
                    "version_binding": {
                        "schema_version": AUTHOR_METHOD_PROFILE_SCHEMA_VERSION,
                        "prompt_version": prompt_run.prompt_version,
                        "prompt_schema_version": prompt_run.schema_version,
                        "prompt_run_id": str(prompt_run.prompt_run_id),
                    },
                }
            )
        return conclusions
