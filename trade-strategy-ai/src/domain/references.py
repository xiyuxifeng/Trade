from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import Field

from src.domain.enums import CanonicalObjectType
from src.domain.value_objects import DomainModel


class ArticleReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.article)
    article_id: UUID
    source: str
    source_article_id: str | None = None
    source_url: str


class ArticleStructureReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.article_structure)
    article_structure_id: UUID
    article_id: UUID
    prompt_run_id: UUID


class RuleCandidateReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.rule_candidate)
    rule_candidate_id: UUID
    article_structure_id: UUID
    source_article_id: UUID


class RuleVersionReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.rule_version)
    rule_id: UUID
    rule_version_id: UUID
    version_no: int


class RuleFamilyReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.rule_family)
    rule_family_id: UUID
    family_key: str


class DatasetSnapshotReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.dataset_snapshot)
    dataset_snapshot_id: UUID
    content_fingerprint: str


class MarketSnapshotReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.market_snapshot)
    market_snapshot_id: UUID
    legacy_snapshot_id: str
    market: str
    trade_date: date
    slot: str
    data_version: str


class MarketStateReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.market_state)
    market_state_id: UUID
    market_snapshot_id: UUID
    definition_version: str
    legacy_regime_id: str | None = None


class RuleApplicabilityProfileReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.rule_applicability_profile)
    applicability_profile_id: UUID
    rule_version_id: UUID
    dataset_snapshot_id: UUID


class AuthorMethodProfileReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.author_method_profile)
    author_profile_id: UUID
    author_profile_version_id: UUID
    version_no: int


class AuthorRuleProfileReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.author_rule_profile)
    author_profile_id: UUID
    author_profile_version_id: UUID
    version_no: int


class AuthorValidatedProfileReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.author_validated_profile)
    author_profile_id: UUID
    author_profile_version_id: UUID
    version_no: int


class StrategyVersionReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.strategy_version)
    strategy_id: UUID
    strategy_version_id: UUID
    version_no: int


class DailyRuleSelectionReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.daily_rule_selection)
    daily_rule_selection_id: UUID
    strategy_version_id: UUID
    market_state_id: UUID
    trade_date: date
    revision_no: int


class DailyStrategyInstanceReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.daily_strategy_instance)
    daily_strategy_instance_id: UUID
    strategy_version_id: UUID
    trade_date: date
    revision_no: int


class TradingDayPlanReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.trading_day_plan)
    trading_day_plan_id: UUID
    daily_strategy_instance_id: UUID
    revision_no: int


class SignalReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.signal)
    signal_id: UUID
    trading_day_plan_id: UUID | None = None


class PostMarketReviewReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.post_market_review)
    post_market_review_id: UUID
    trading_day_plan_id: UUID
    revision_no: int


class OptimizationProposalReference(DomainModel):
    object_type: CanonicalObjectType = Field(default=CanonicalObjectType.optimization_proposal)
    optimization_proposal_id: UUID
    post_market_review_id: UUID
    revision_no: int
