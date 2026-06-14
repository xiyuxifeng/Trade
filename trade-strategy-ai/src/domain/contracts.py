from __future__ import annotations

from uuid import UUID

from pydantic import Field

from src.domain.enums import (
    ArticleStructureLifecycleState,
    AuthorProfileKind,
    DailyRuleSelectionState,
    DailyStrategyInstanceState,
    DatasetSnapshotState,
    FactSource,
    FormalLifecycleState,
    MarketObservationState,
    MarketSnapshotState,
    PostMarketReviewState,
    ProposalLifecycleState,
    ProposalType,
    QualityStatus,
    RuleCandidateLifecycleState,
    SignalState,
    TradingDayPlanState,
)
from src.domain.references import (
    ArticleReference,
    ArticleStructureReference,
    AuthorMethodProfileReference,
    AuthorRuleProfileReference,
    AuthorValidatedProfileReference,
    DailyRuleSelectionReference,
    DailyStrategyInstanceReference,
    DatasetSnapshotReference,
    MarketSnapshotReference,
    MarketStateReference,
    OptimizationProposalReference,
    PostMarketReviewReference,
    RuleApplicabilityProfileReference,
    RuleCandidateReference,
    RuleFamilyReference,
    RuleVersionReference,
    SignalReference,
    StrategyVersionReference,
    TradingDayPlanReference,
)
from src.domain.value_objects import (
    AuditStamp,
    DomainModel,
    FactSourceRecord,
    QualityRecord,
    SourceProvenance,
)


CORE_OBJECT_TYPES = (
    "Article",
    "ArticleStructure",
    "RuleCandidate",
    "RuleVersion",
    "RuleFamily",
    "DatasetSnapshot",
    "MarketSnapshot",
    "MarketState",
    "RuleApplicabilityProfile",
    "AuthorMethodProfile",
    "AuthorRuleProfile",
    "AuthorValidatedProfile",
    "StrategyVersion",
    "DailyRuleSelection",
    "DailyStrategyInstance",
    "TradingDayPlan",
    "Signal",
    "PostMarketReview",
    "OptimizationProposal",
)

WRITER_OWNERSHIP = {
    "Article": "Article application service",
    "ArticleStructure": "Article analysis application service",
    "RuleCandidate": "Article analysis application service",
    "RuleVersion": "Rule governance application service",
    "RuleFamily": "Rule governance application service",
    "DatasetSnapshot": "Market data application service",
    "MarketSnapshot": "Market data application service",
    "MarketState": "Market data application service",
    "RuleApplicabilityProfile": "Backtest application service",
    "AuthorMethodProfile": "Author profile application service",
    "AuthorRuleProfile": "Author profile application service",
    "AuthorValidatedProfile": "Author profile application service",
    "StrategyVersion": "Strategy application service",
    "DailyRuleSelection": "Daily trading application service",
    "DailyStrategyInstance": "Daily trading application service",
    "TradingDayPlan": "Daily trading application service",
    "Signal": "Daily trading application service",
    "PostMarketReview": "Daily trading application service",
    "OptimizationProposal": "Daily trading application service",
}


class CanonicalContract(DomainModel):
    provenance: SourceProvenance
    quality: QualityRecord
    audit: AuditStamp


class ArticleContract(CanonicalContract):
    reference: ArticleReference
    content_hash: str | None = None


class ArticleStructureContract(CanonicalContract):
    reference: ArticleStructureReference
    article: ArticleReference
    lifecycle_state: ArticleStructureLifecycleState | str
    schema_version: str
    prompt_version: str
    missing_fields: list[str] = Field(default_factory=list)
    inferred_fields: list[str] = Field(default_factory=list)


class RuleCandidateContract(CanonicalContract):
    reference: RuleCandidateReference
    article_structure: ArticleStructureReference
    lifecycle_state: RuleCandidateLifecycleState
    backtestability_status: str = "unknown"


class RuleVersionContract(CanonicalContract):
    reference: RuleVersionReference
    source_candidate: RuleCandidateReference | None = None
    lifecycle_state: FormalLifecycleState
    family: RuleFamilyReference | None = None


class RuleFamilyContract(CanonicalContract):
    reference: RuleFamilyReference
    lifecycle_state: FormalLifecycleState
    members: list[RuleVersionReference] = Field(default_factory=list)


class DatasetSnapshotContract(CanonicalContract):
    reference: DatasetSnapshotReference
    lifecycle_state: DatasetSnapshotState
    market_state_definition_version: str | None = None


class MarketSnapshotContract(CanonicalContract):
    reference: MarketSnapshotReference
    lifecycle_state: MarketSnapshotState


class MarketStateContract(CanonicalContract):
    reference: MarketStateReference
    market_snapshot: MarketSnapshotReference
    lifecycle_state: MarketObservationState
    primary_label: str
    confidence: float
    source_feature_version: str = "legacy"


class RuleApplicabilityProfileContract(CanonicalContract):
    reference: RuleApplicabilityProfileReference
    rule_version: RuleVersionReference
    dataset_snapshot: DatasetSnapshotReference
    lifecycle_state: FormalLifecycleState
    market_state_definition_version: str
    result_status: str


class AuthorMethodProfileContract(CanonicalContract):
    reference: AuthorMethodProfileReference
    lifecycle_state: FormalLifecycleState
    profile_kind: AuthorProfileKind = Field(default=AuthorProfileKind.method)


class AuthorRuleProfileContract(CanonicalContract):
    reference: AuthorRuleProfileReference
    lifecycle_state: FormalLifecycleState
    profile_kind: AuthorProfileKind = Field(default=AuthorProfileKind.rule)


class AuthorValidatedProfileContract(CanonicalContract):
    reference: AuthorValidatedProfileReference
    lifecycle_state: FormalLifecycleState
    profile_kind: AuthorProfileKind = Field(default=AuthorProfileKind.validated)


class StrategyVersionContract(CanonicalContract):
    reference: StrategyVersionReference
    lifecycle_state: FormalLifecycleState
    author_method_profile: AuthorMethodProfileReference | None = None
    author_rule_profile: AuthorRuleProfileReference | None = None
    author_validated_profile: AuthorValidatedProfileReference | None = None


class DailyRuleSelectionContract(CanonicalContract):
    reference: DailyRuleSelectionReference
    strategy_version: StrategyVersionReference
    market_state: MarketStateReference
    lifecycle_state: DailyRuleSelectionState


class DailyStrategyInstanceContract(CanonicalContract):
    reference: DailyStrategyInstanceReference
    strategy_version: StrategyVersionReference
    daily_rule_selection: DailyRuleSelectionReference
    market_snapshot: MarketSnapshotReference
    lifecycle_state: DailyStrategyInstanceState


class TradingDayPlanContract(CanonicalContract):
    reference: TradingDayPlanReference
    daily_strategy_instance: DailyStrategyInstanceReference
    lifecycle_state: TradingDayPlanState


class SignalContract(CanonicalContract):
    reference: SignalReference
    lifecycle_state: SignalState
    daily_strategy_instance: DailyStrategyInstanceReference | None = None


class PostMarketReviewContract(CanonicalContract):
    reference: PostMarketReviewReference
    trading_day_plan: TradingDayPlanReference
    market_snapshot: MarketSnapshotReference
    market_state: MarketStateReference
    lifecycle_state: PostMarketReviewState


class CompatibilityTargetReference(DomainModel):
    object_type: str
    canonical_id: UUID | None = None
    canonical_version_id: UUID | None = None
    legacy_id: str | None = None


class OptimizationProposalContract(CanonicalContract):
    reference: OptimizationProposalReference
    post_market_review: PostMarketReviewReference
    lifecycle_state: ProposalLifecycleState
    proposal_type: ProposalType
    target_asset: CompatibilityTargetReference
    base_version: CompatibilityTargetReference | None = None
    accepted_draft_version: CompatibilityTargetReference | None = None


class CoreDomainContractBundle(DomainModel):
    article: ArticleContract
    article_structure: ArticleStructureContract
    rule_candidate: RuleCandidateContract
    rule_version: RuleVersionContract
    rule_family: RuleFamilyContract
    dataset_snapshot: DatasetSnapshotContract
    market_snapshot: MarketSnapshotContract
    market_state: MarketStateContract
    rule_applicability_profile: RuleApplicabilityProfileContract
    author_method_profile: AuthorMethodProfileContract
    author_rule_profile: AuthorRuleProfileContract
    author_validated_profile: AuthorValidatedProfileContract
    strategy_version: StrategyVersionContract
    daily_rule_selection: DailyRuleSelectionContract
    daily_strategy_instance: DailyStrategyInstanceContract
    trading_day_plan: TradingDayPlanContract
    signal: SignalContract
    post_market_review: PostMarketReviewContract
    optimization_proposal: OptimizationProposalContract


__all__ = [
    "CORE_OBJECT_TYPES",
    "WRITER_OWNERSHIP",
    "ArticleContract",
    "ArticleStructureContract",
    "RuleCandidateContract",
    "RuleVersionContract",
    "RuleFamilyContract",
    "DatasetSnapshotContract",
    "MarketSnapshotContract",
    "MarketStateContract",
    "RuleApplicabilityProfileContract",
    "AuthorMethodProfileContract",
    "AuthorRuleProfileContract",
    "AuthorValidatedProfileContract",
    "StrategyVersionContract",
    "DailyRuleSelectionContract",
    "DailyStrategyInstanceContract",
    "TradingDayPlanContract",
    "SignalContract",
    "PostMarketReviewContract",
    "OptimizationProposalContract",
    "CoreDomainContractBundle",
    "AuditStamp",
    "FactSource",
    "FactSourceRecord",
    "QualityRecord",
    "QualityStatus",
    "SourceProvenance",
]
