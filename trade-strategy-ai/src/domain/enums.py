from __future__ import annotations

from enum import StrEnum


class CanonicalObjectType(StrEnum):
    article = "Article"
    article_structure = "ArticleStructure"
    rule_candidate = "RuleCandidate"
    rule_version = "RuleVersion"
    rule_family = "RuleFamily"
    dataset_snapshot = "DatasetSnapshot"
    market_snapshot = "MarketSnapshot"
    market_state = "MarketState"
    rule_applicability_profile = "RuleApplicabilityProfile"
    author_method_profile = "AuthorMethodProfile"
    author_rule_profile = "AuthorRuleProfile"
    author_validated_profile = "AuthorValidatedProfile"
    strategy_version = "StrategyVersion"
    daily_rule_selection = "DailyRuleSelection"
    daily_strategy_instance = "DailyStrategyInstance"
    trading_day_plan = "TradingDayPlan"
    signal = "Signal"
    post_market_review = "PostMarketReview"
    optimization_proposal = "OptimizationProposal"


class FactSource(StrEnum):
    explicit_article = "explicit_article"
    llm_inference = "llm_inference"
    program_observation = "program_observation"
    backtest_observation = "backtest_observation"
    human_approval = "human_approval"
    legacy_import = "legacy_import"


class QualityStatus(StrEnum):
    verified = "verified"
    complete = "complete"
    partial = "partial"
    ambiguous = "ambiguous"
    unresolved = "unresolved"
    rejected = "rejected"
    legacy_only = "legacy_only"


class FormalLifecycleState(StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    published = "published"
    archived = "archived"
    rejected = "rejected"
    superseded = "superseded"


class ArticleStructureLifecycleState(StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class RuleCandidateLifecycleState(StrEnum):
    extracted = "extracted"
    auto_review = "auto_review"
    manual_review = "manual_review"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class DatasetSnapshotState(StrEnum):
    ready = "ready"
    partial = "partial"
    invalid = "invalid"
    archived = "archived"


class MarketSnapshotState(StrEnum):
    building = "building"
    ready = "ready"
    partial = "partial"
    invalid = "invalid"
    archived = "archived"


class MarketObservationState(StrEnum):
    valid = "valid"
    partial = "partial"
    invalid = "invalid"
    superseded = "superseded"


class DailyRuleSelectionState(StrEnum):
    generated = "generated"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"
    cancelled = "cancelled"


class DailyStrategyInstanceState(StrEnum):
    generated = "generated"
    approved = "approved"
    superseded = "superseded"
    cancelled = "cancelled"


class TradingDayPlanState(StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"
    cancelled = "cancelled"


class SignalState(StrEnum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    expired = "expired"
    executed = "executed"


class PostMarketReviewState(StrEnum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    archived = "archived"


class ProposalLifecycleState(StrEnum):
    draft = "draft"
    in_review = "in_review"
    accepted = "accepted"
    rejected = "rejected"
    archived = "archived"
    superseded = "superseded"


class ProposalType(StrEnum):
    rule_optimization = "rule_optimization"
    author_profile_revision = "author_profile_revision"
    strategy_revision = "strategy_revision"


class AuthorProfileKind(StrEnum):
    method = "method"
    rule = "rule"
    validated = "validated"
