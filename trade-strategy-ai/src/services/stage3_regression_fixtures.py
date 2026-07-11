from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Stage3RegressionCategory = Literal[
    "explicit_and_actionable_rules",
    "pure_conceptual_content",
    "mixed_concept_and_rule_content",
    "concrete_review_case_study_content",
    "explicit_market_state",
    "undeclared_market_state",
    "ambiguous_terminology",
    "kaipan_dependency",
    "duplicate_or_near_duplicate_rules",
    "conflicting_viewpoints",
    "human_review_required",
]

SummarySource = Literal["article_revision_source_payload", "blog_article_current", "unavailable"]
BacktestabilityStatus = Literal["executable", "partially_executable", "not_executable"]

REQUIRED_STAGE3_REGRESSION_CATEGORIES: set[str] = {
    "explicit_and_actionable_rules",
    "pure_conceptual_content",
    "mixed_concept_and_rule_content",
    "concrete_review_case_study_content",
    "explicit_market_state",
    "undeclared_market_state",
    "ambiguous_terminology",
    "kaipan_dependency",
    "duplicate_or_near_duplicate_rules",
    "conflicting_viewpoints",
    "human_review_required",
}

STAGE3_FIXED_SET_GATE_VERSION = "stage3-fixed-set-v1"
STAGE3_FIXED_SET_MODEL = "stage3-fixed-fixture-model"


class RegressionSummaryExpectation(BaseModel):
    available: bool
    aligned: bool
    source: SummarySource
    summary: str | None = None
    contains: str | None = None


class RegressionSemanticAssertions(BaseModel):
    article_structure_provenance_required: bool = True
    method_tags: list[str] = Field(default_factory=list)
    explicit_facts_contains: list[str] = Field(default_factory=list)
    hypotheses_contains: list[str] = Field(default_factory=list)
    missing_fields_contains: list[str] = Field(default_factory=list)
    evidence_required: bool = False
    candidate_rule_count_range: tuple[int, int] = (0, 0)
    data_dependencies_contains: list[str] = Field(default_factory=list)
    backtestability_statuses: list[str] = Field(default_factory=list)
    automatic_review_statuses: list[str] = Field(default_factory=list)
    market_state_status: Literal["explicit", "not_declared"] = "not_declared"
    kaipan_dependency: bool = False


class RegressionRuleFixture(BaseModel):
    rule_key: str
    title: str
    rule_type: str
    timeframe: str
    holding_period: str
    evidence_quotes: list[str] = Field(default_factory=list)
    data_dependencies: list[str] = Field(default_factory=list)
    market_state_status: Literal["explicit", "not_declared"] = "not_declared"
    backtestability_status: Literal["executable", "partially_executable", "not_executable"] = "executable"
    ambiguous_terms: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    manual_review_required: bool = False


class RegressionArticleFixture(BaseModel):
    article_id: UUID
    title: str
    article_revision_id: UUID
    content_hash: str
    article_content: str
    prompt_name: str = "article_taxonomy_v1"
    prompt_version: str = "article_taxonomy_v1"
    schema_name: str = "article_taxonomy_v1"
    schema_version: str = "article_taxonomy_v1"
    model: str = STAGE3_FIXED_SET_MODEL
    covered_categories: set[str]
    selection_reason: str
    expected_outcome_ambiguity: str
    user_confirmation_required: bool = False
    summary_expectation: RegressionSummaryExpectation
    semantic_assertions: RegressionSemanticAssertions
    rules: list[RegressionRuleFixture] = Field(default_factory=list)
    exercise_repair: bool = False
    provider_failures_before_success: int = 0

    @classmethod
    def for_test_case(
        cls,
        *,
        article_id: UUID,
        article_revision_id: UUID,
        content_hash: str,
        title: str,
        article_content: str,
        covered_categories: set[str],
        selection_reason: str,
        expected_outcome_ambiguity: str,
        summary_available: bool,
        method_tags: list[str],
        explicit_facts_contains: list[str],
        candidate_title: str | None,
        data_dependencies_contains: list[str],
        backtestability_statuses: list[BacktestabilityStatus],
        automatic_review_statuses: list[str],
        market_state_status: Literal["explicit", "not_declared"],
        kaipan_dependency: bool,
        hypotheses_contains: list[str] | None = None,
        missing_fields_contains: list[str] | None = None,
        ambiguous_terms: list[str] | None = None,
        missing_fields: list[str] | None = None,
        summary_source: SummarySource | None = None,
        summary_contains: str | None = None,
        exercise_repair: bool = False,
        provider_failures_before_success: int = 0,
    ) -> "RegressionArticleFixture":
        summary_text = f"{title} 摘要" if summary_available else None
        rule = None
        if candidate_title is not None:
            rule = RegressionRuleFixture(
                rule_key=f"rule-{article_revision_id}",
                title=candidate_title,
                rule_type="entry",
                timeframe="5m",
                holding_period="intraday",
                evidence_quotes=[candidate_title],
                data_dependencies=list(data_dependencies_contains),
                market_state_status=market_state_status,
                backtestability_status=backtestability_statuses[0] if backtestability_statuses else "executable",
                ambiguous_terms=list(ambiguous_terms or []),
                missing_fields=list(missing_fields or []),
                manual_review_required=bool(
                    kaipan_dependency
                    or ambiguous_terms
                    or missing_fields
                    or (backtestability_statuses and backtestability_statuses[0] != "executable")
                ),
            )

        return cls(
            article_id=article_id,
            title=title,
            article_revision_id=article_revision_id,
            content_hash=content_hash,
            article_content=article_content,
            covered_categories=covered_categories,
            selection_reason=selection_reason,
            expected_outcome_ambiguity=expected_outcome_ambiguity,
            summary_expectation=RegressionSummaryExpectation(
                available=summary_available,
                aligned=summary_available,
                source=summary_source or ("blog_article_current" if summary_available else "unavailable"),
                summary=summary_text,
                contains=summary_contains,
            ),
            semantic_assertions=RegressionSemanticAssertions(
                method_tags=list(method_tags),
                explicit_facts_contains=list(explicit_facts_contains),
                hypotheses_contains=list(hypotheses_contains or []),
                missing_fields_contains=list(missing_fields_contains or []),
                evidence_required=candidate_title is not None,
                candidate_rule_count_range=(0, 0) if candidate_title is None else (1, 1),
                data_dependencies_contains=list(data_dependencies_contains),
                backtestability_statuses=list(backtestability_statuses),
                automatic_review_statuses=list(automatic_review_statuses),
                market_state_status=market_state_status,
                kaipan_dependency=kaipan_dependency,
            ),
            rules=[] if rule is None else [rule],
            exercise_repair=exercise_repair,
            provider_failures_before_success=provider_failures_before_success,
        )

    def with_semantic_assertions(self, semantic_assertions: RegressionSemanticAssertions) -> "RegressionArticleFixture":
        return self.model_copy(update={"semantic_assertions": semantic_assertions})

    def clone_for_revision(
        self,
        *,
        article_revision_id: UUID,
        content_hash: str,
        article_content: str,
    ) -> "RegressionArticleFixture":
        return self.model_copy(
            update={
                "article_revision_id": article_revision_id,
                "content_hash": content_hash,
                "article_content": article_content,
            }
        )

    def build_payload(self, *, valid: bool) -> dict:
        payload = {
            "prompt_version": "article_taxonomy_v1",
            "schema_version": "article_taxonomy_v1",
            "classification": {
                "article_type": self._article_type(),
                "confidence": 0.91,
                "evidence": self.semantic_assertions.explicit_facts_contains[:1] or [self.title[:12]],
            },
            "concept_extraction": {
                "prompt_version": "concept_extraction_v1",
                "schema_version": "concept_v1",
                "concepts": [],
                "trading_symbols": [],
                "indicators": [],
                "chart_patterns": [],
                "market_themes": [],
                "risk_concepts": [],
                "data_dependencies": list(self.semantic_assertions.data_dependencies_contains),
                "sentiment": {"score": 0.0, "confidence": 0.0},
                "warnings": [],
            },
            "article_structure": {
                "prompt_version": "article_structure_extraction_v1",
                "schema_version": "article_structure_v1",
                "article_id": str(self.article_id),
                "author_id": "author-1",
                "published_at": datetime(2026, 6, 15, 9, 30).isoformat(),
                "article_type": self._article_type(),
                "method_tags": list(self.semantic_assertions.method_tags),
                "analysis_dimensions": ["price", "market_state"],
                "instrument_focus": ["stock"],
                "holding_period": {
                    "value": "intraday" if self.rules else "swing",
                    "source": "explicit",
                    "confidence": 0.88,
                    "evidence": self.semantic_assertions.explicit_facts_contains[:1] or [self.title[:12]],
                },
                "entry_patterns": [rule.title for rule in self.rules],
                "exit_patterns": [],
                "risk_concepts": [],
                "data_dependencies": list(self.semantic_assertions.data_dependencies_contains),
                "market_state": {
                    "status": self.semantic_assertions.market_state_status,
                    "explicit_conditions": (
                        [{"field": "market_state", "operator": "eq", "value": "震荡"}]
                        if self.semantic_assertions.market_state_status == "explicit"
                        else []
                    ),
                    "inferred_hypotheses": [
                        {
                            "market_state": None,
                            "hypothesis": item,
                            "source": "inferred",
                            "confidence": 0.66,
                            "evidence": [item],
                            "validation_status": "unverified",
                        }
                        for item in self.semantic_assertions.hypotheses_contains
                    ],
                },
                "key_claims": [
                    {
                        "claim": item,
                        "claim_type": "fact",
                        "source": "explicit",
                        "confidence": 0.84,
                        "evidence": [item],
                    }
                    for item in self.semantic_assertions.explicit_facts_contains
                ],
                "article_quality": {
                    "information_density": "high",
                    "quantifiability": "medium" if self.rules else "low",
                    "duplicate_risk": "medium" if "duplicate_or_near_duplicate_rules" in self.covered_categories else "low",
                    "needs_manual_review": "human_review_required" in self.covered_categories,
                    "warnings": [],
                },
            },
            "taxonomy_extraction": {
                "taxonomy_version": "extraction_taxonomy_v1",
                "schema_version": "extraction_item_v1",
                "extraction_items": [self._build_taxonomy_item(rule) for rule in self.rules],
            },
            "explicit_preconditions": {
                "prompt_version": "explicit_precondition_extraction_v1",
                "schema_version": "explicit_precondition_v1",
                "status": self.semantic_assertions.market_state_status,
                "preconditions": (
                    [
                        {
                            "condition_type": "market_state",
                            "condition": {
                                "field": "market_state",
                                "operator": "eq",
                                "value": "震荡",
                                "raw_expression": "震荡期",
                            },
                            "confidence": 0.7,
                            "evidence": ["震荡期"],
                        }
                    ]
                    if self.semantic_assertions.market_state_status == "explicit"
                    else []
                ),
                "warnings": [],
            },
            "quality": {
                "needs_repair": self.exercise_repair and not valid,
                "repair_reasons": ["classification confidence type"] if self.exercise_repair and not valid else [],
                "warnings": [],
            },
        }
        if not valid:
            payload["classification"]["confidence"] = "invalid"
        return payload

    def build_repair_payload(self) -> dict:
        return {
            "prompt_version": "article_taxonomy_repair_v1",
            "patched_fields": {"classification.confidence": 0.91},
            "unresolved_errors": [],
            "warnings": [],
        }

    def _article_type(self) -> str:
        if "pure_conceptual_content" in self.covered_categories and not self.rules:
            return "concept"
        if "concrete_review_case_study_content" in self.covered_categories:
            return "review"
        if "mixed_concept_and_rule_content" in self.covered_categories:
            return "mixed"
        return "rule"

    def _build_rule_payload(self, rule: RegressionRuleFixture) -> dict:
        return {
            "rule_key": rule.rule_key,
            "title": rule.title,
            "rule_type": rule.rule_type,
            "instrument_focus": ["stock"],
            "timeframe": rule.timeframe,
            "holding_period": rule.holding_period,
            "condition": {
                "logic": "single",
                "clauses": [
                    {
                        "field": "signal",
                        "operator": "contains",
                        "value": rule.title,
                        "unit": None,
                        "lookback": 1,
                        "raw_expression": rule.title,
                    }
                ],
            },
            "action": {
                "type": "enter",
                "side": "buy",
                "price_reference": "market",
            },
            "risk_controls": [],
            "data_dependencies": list(rule.data_dependencies),
            "market_state_applicability": {
                "status": rule.market_state_status,
                "explicit_conditions": (
                    [{"field": "market_state", "operator": "eq", "value": "震荡"}]
                    if rule.market_state_status == "explicit"
                    else []
                ),
                "inferred_hypotheses": [],
            },
            "quantification": {
                "status": rule.backtestability_status,
                "missing_fields": list(rule.missing_fields),
                "ambiguous_terms": list(rule.ambiguous_terms),
                "manual_review_required": rule.manual_review_required,
            },
            "confidence": 0.83,
            "evidence": [
                {
                    "quote": quote,
                    "supports": "condition",
                }
                for quote in (rule.evidence_quotes or [rule.title])
            ],
            "source_article_id": str(self.article_id),
        }

    def _build_taxonomy_item(self, rule: RegressionRuleFixture) -> dict:
        quote = rule.evidence_quotes[0] if rule.evidence_quotes else rule.title
        if rule.ambiguous_terms:
            primary_type = "semantic_experience"
            payload = {
                "primary_type": primary_type,
                "term_or_phrase": rule.ambiguous_terms[0],
                "source_context": rule.title,
                "plain_language_interpretation": rule.title,
                "related_market_state": None,
                "possible_observable_proxies": list(rule.data_dependencies),
                "semantic_dictionary_action": "clarify",
                "ambiguity_level": "high",
                "not_directly_backtestable": True,
            }
        elif rule.backtestability_status != "executable" or rule.missing_fields:
            primary_type = "rule_candidate"
            missing = list(rule.missing_fields) or ["strict executable mechanics"]
            payload = {
                "primary_type": primary_type,
                "candidate_rule_summary": rule.title,
                "known_components": {"condition": rule.title},
                "missing_fields": missing,
                "repair_tasks": [f"resolve {item}" for item in missing],
                "repair_source": "source_text",
                "repairability": "medium",
                "instrument_universe_status": "complete",
                "entry_exit_status": {"entry": "present", "exit": "partial"},
                "data_dependencies": [{"dataset": item} for item in rule.data_dependencies],
                "timestamp_availability_risk": [],
                "ambiguous_terms": [],
                "not_directly_backtestable": True,
            }
        else:
            # Legacy "executable" fixtures generally contain selection/observation language,
            # not complete entry/exit/risk/sizing mechanics. Preserve them as research claims.
            primary_type = "research_hypothesis"
            payload = {
                "primary_type": primary_type,
                "hypothesis_statement": rule.title,
                "source_experience": quote,
                "dependent_variables": ["forward_return"],
                "independent_variables": ["source_claim_indicator"],
                "candidate_observable_indicators": list(rule.data_dependencies) or ["ohlcv_features"],
                "required_data": list(rule.data_dependencies) or ["ohlcv_1d"],
                "validation_method": "event study before any rule design",
                "timestamp_availability_assumptions": ["all explanatory variables must be frozen before the decision"],
                "research_status": "proposed",
                "not_directly_backtestable": True,
            }
        return {
            "primary_type": primary_type,
            "secondary_tags": ["kaipan"] if any("kaipan" in item.lower() for item in rule.data_dependencies) else [],
            "taxonomy_payload": payload,
            "source_evidence": {
                "quote": quote,
                "span": None,
                "section": None,
                "evidence_kind": "explicit_quote",
                "rationale": "fixed regression fixture evidence",
            },
            "confidence": {
                "score": 0.83,
                "level": "high",
                "rationale": "fixed regression fixture",
                "requires_human_confirmation": rule.manual_review_required or primary_type == "research_hypothesis",
            },
        }


def get_stage3_fixed_regression_set() -> list[RegressionArticleFixture]:
    return [
        RegressionArticleFixture.for_test_case(
            article_id=UUID("b7d7be25-31c2-48d2-ab33-8dfbe82c00cf"),
            article_revision_id=UUID("7f5b9637-e475-5c15-97a4-a3338a69eff4"),
            content_hash="2560d2a0ddff568dd8bf8cc362a727d8fda5659de94c3b4bdf889069e9cc9088",
            title="5.21号复盘！市场下跌早有征兆！退潮行情接下来如何应对！",
            article_content="首先今天市场的盘面预判到了！并且也提醒了大家注意风险！降低整体仓位！",
            covered_categories={"concrete_review_case_study_content", "explicit_market_state", "conflicting_viewpoints", "human_review_required"},
            selection_reason="真实复盘文章，明确讨论退潮和仓位风险，适合作为市场状态与人工复核样本。",
            expected_outcome_ambiguity="medium",
            summary_available=False,
            method_tags=["复盘", "仓位"],
            explicit_facts_contains=["降低整体仓位", "市场下跌早有征兆"],
            hypotheses_contains=["退潮延续"],
            candidate_title="退潮期降低仓位",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["partially_executable"],
            automatic_review_statuses=["needs_human_review"],
            market_state_status="explicit",
            kaipan_dependency=False,
            ambiguous_terms=["退潮"],
            missing_fields=["精确减仓阈值"],
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("df2c1dc5-45ec-40fc-afe9-64c9299c5d70"),
            article_revision_id=UUID("a2dfadbd-bdf8-54e6-9b97-6cf154e501a9"),
            content_hash="25cf31e8e457ed40147a3b6f57d9fcb5149df59eb8dcb7c3b900dc8e4923c2a0",
            title="[红包]教你什么是震荡期！淘县九年义务教育！",
            article_content="什么是震荡？震荡是周期的一种象限！周期是一种势能！",
            covered_categories={"pure_conceptual_content", "explicit_market_state", "conflicting_viewpoints"},
            selection_reason="纯概念文章，明确解释震荡期，适合验证无候选规则和显式市场状态。",
            expected_outcome_ambiguity="low",
            summary_available=False,
            method_tags=["周期", "震荡"],
            explicit_facts_contains=["什么是震荡"],
            candidate_title=None,
            data_dependencies_contains=[],
            backtestability_statuses=[],
            automatic_review_statuses=[],
            market_state_status="explicit",
            kaipan_dependency=False,
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("f3d4f639-4bf4-400f-a2d2-a970ccc0bd67"),
            article_revision_id=UUID("1aff1c10-1337-52d7-b54e-512aa88ea3ce"),
            content_hash="e6f55d4bf48bfea57f5c9d1f8e617e03fa046550a101d3b111a58ad32f3193c1",
            title="心态及认知",
            article_content="交易大道，贵在沉淀认知、淬炼心性、严守纪律。",
            covered_categories={"pure_conceptual_content", "undeclared_market_state"},
            selection_reason="纯认知文章，没有可回测规则，适合验证 not_declared 和空规则路径。",
            expected_outcome_ambiguity="low",
            summary_available=False,
            method_tags=["心态", "认知"],
            explicit_facts_contains=["严守纪律"],
            candidate_title=None,
            data_dependencies_contains=[],
            backtestability_statuses=[],
            automatic_review_statuses=[],
            market_state_status="not_declared",
            kaipan_dependency=False,
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("19101ba2-3be8-42d3-919e-489e22666e2c"),
            article_revision_id=UUID("7f9183a4-3611-52d5-ba1d-ec0bb2c07746"),
            content_hash="e29a39c04ada1ce1e5423803a1a894ed55fa30ddc7ca5e82cad054a3fcb15dfb",
            title="复利的本质~选择大于努力！",
            article_content="真正成熟的交易者，早已通过整体仓位管控，把上波不确定性彻底隔绝在风险之外。",
            covered_categories={"pure_conceptual_content", "explicit_market_state", "human_review_required"},
            selection_reason="仓位与复利理念文章，显式依赖市场环境变化，适合验证 sizing 风险类结论需人工复核。",
            expected_outcome_ambiguity="medium",
            summary_available=False,
            method_tags=["仓位", "复利"],
            explicit_facts_contains=["仓位管控"],
            candidate_title="不确定性阶段控制仓位",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["partially_executable"],
            automatic_review_statuses=["needs_human_review"],
            market_state_status="explicit",
            kaipan_dependency=False,
            missing_fields=["具体仓位比例"],
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("17b8567d-c594-4abc-b173-522aeab370fc"),
            article_revision_id=UUID("c389164a-1a43-5916-9974-ba57f3aba1b5"),
            content_hash="d4a2c267d4548461b14af1cd718c41d437a2a03a810df6ea3b5fd677c6c96c58",
            title="教你什么是短线之价值投机",
            article_content="多数人疑惑价值投机：价值偏向趋势，投机主打短线。",
            covered_categories={"mixed_concept_and_rule_content", "conflicting_viewpoints", "ambiguous_terminology", "human_review_required"},
            selection_reason="标题和正文同时包含概念与执行框架，且“价值投机”术语天然模糊。",
            expected_outcome_ambiguity="high",
            summary_available=False,
            method_tags=["价值投机", "趋势"],
            explicit_facts_contains=["价值偏向趋势"],
            hypotheses_contains=["风格轮动"],
            candidate_title="趋势风格下优先价值投机",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["partially_executable"],
            automatic_review_statuses=["needs_human_review"],
            market_state_status="not_declared",
            kaipan_dependency=False,
            ambiguous_terms=["价值投机"],
            missing_fields=["入场阈值"],
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("667cb4be-729d-4019-918b-e40b5bba53b4"),
            article_revision_id=UUID("08edabf5-33da-51d6-b5ff-29bb5464d665"),
            content_hash="db1f694cf966f91b29f308cf8820150575bcc7740e0b7df4b182dad9c4000c9b",
            title="10.21号复盘，市场如期修复，明天怎么看？突破or震荡？",
            article_content="市场今天如期小幅放量普涨，明天正常还会有一个延续向上的过程。",
            covered_categories={"concrete_review_case_study_content", "explicit_market_state", "duplicate_or_near_duplicate_rules"},
            selection_reason="复盘+次日推演文章，明确给出突破/震荡分歧，适合作为案例型规则样本。",
            expected_outcome_ambiguity="medium",
            summary_available=False,
            method_tags=["复盘", "市场状态"],
            explicit_facts_contains=["小幅放量普涨"],
            candidate_title="放量修复后关注突破延续",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["executable"],
            automatic_review_statuses=["pending_backtest"],
            market_state_status="explicit",
            kaipan_dependency=False,
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("36472c6e-13bd-4989-a750-9446e2aff3fd"),
            article_revision_id=UUID("a3d6d2d4-33bd-57d0-9216-fbdbaa43edf8"),
            content_hash="ebd8a98a6fca8f14ded42658ed9b94fa995ccf87e40ede89b84d4b2d648bc36b",
            title="手把手教你如何看竞价~淘县九年义务教育~",
            article_content="我们可以通过集合竞价去排除低于预期的方向，亦或者找到超预期的票。",
            covered_categories={"explicit_and_actionable_rules", "kaipan_dependency", "ambiguous_terminology", "human_review_required"},
            selection_reason="竞价文章强依赖盘前/Kaipan 数据，且“低于预期/超预期”属于需人工确认的模糊术语。",
            expected_outcome_ambiguity="high",
            summary_available=False,
            method_tags=["竞价"],
            explicit_facts_contains=["集合竞价"],
            candidate_title="竞价超预期方向优先观察",
            data_dependencies_contains=["kaipan_tick"],
            backtestability_statuses=["partially_executable"],
            automatic_review_statuses=["needs_human_review"],
            market_state_status="not_declared",
            kaipan_dependency=True,
            ambiguous_terms=["超预期", "低于预期"],
            missing_fields=["竞价量化阈值"],
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("fc461ca7-ff28-4c81-ba58-e4bc69ec8461"),
            article_revision_id=UUID("9dd9e1cd-62ab-5708-8d9d-ca9bad93c739"),
            content_hash="f70d211b1a0c053fb8b392493951e00db1265d72f1620933306f5d4055494f76",
            title="教你什么是短线跨年龙模式~淘县九年义务教育！",
            article_content="临近12.31号的跨年节点，看接下来的跨年龙应该怎么博弈。",
            covered_categories={"mixed_concept_and_rule_content", "duplicate_or_near_duplicate_rules"},
            selection_reason="模式解释和执行思路并存，与一字首开/竞价类样本形成近重复规则覆盖。",
            expected_outcome_ambiguity="medium",
            summary_available=False,
            method_tags=["跨年龙", "模式"],
            explicit_facts_contains=["跨年龙"],
            candidate_title="跨年节点跟踪龙头延续",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["executable"],
            automatic_review_statuses=["pending_backtest"],
            market_state_status="not_declared",
            kaipan_dependency=False,
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("84558067-1ba1-4248-9700-fd4225be8593"),
            article_revision_id=UUID("b64a3c51-bf32-562c-8a86-849eac28ad72"),
            content_hash="02de6880c153fd88f2693ae70f791a32e13b0c52b71a0dd61b93396070aaa0d5",
            title="南方路机，短线逻辑全拆解！",
            article_content="所有时间都是来自临盘，精确到分钟级别！从不做任何模糊的精确！",
            covered_categories={"concrete_review_case_study_content", "explicit_and_actionable_rules", "duplicate_or_near_duplicate_rules"},
            selection_reason="典型单票复盘拆解，和恒宝股份形成近重复案例型规则对。",
            expected_outcome_ambiguity="low",
            summary_available=False,
            method_tags=["个股拆解", "临盘"],
            explicit_facts_contains=["精确到分钟级别"],
            candidate_title="强势股临盘承接后跟随",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["executable"],
            automatic_review_statuses=["pending_backtest"],
            market_state_status="not_declared",
            kaipan_dependency=False,
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("8856f8f8-2441-492a-9292-981f0b3e1672"),
            article_revision_id=UUID("2f2589a2-2689-5b66-a6f1-cb687e0abcc1"),
            content_hash="f6c7f8947f1ac7205a2746c2ff5f5fcc613305c0a5698edf4c0abd849243f140",
            title="教你恒宝股份短线逻辑全拆解！",
            article_content="如何周三早盘竞价参与，全程做T到周五，让波段更大化！",
            covered_categories={"concrete_review_case_study_content", "explicit_and_actionable_rules", "duplicate_or_near_duplicate_rules", "kaipan_dependency"},
            selection_reason="与南方路机构成近重复单票规则，同时多了竞价参与路径和盘中依赖。",
            expected_outcome_ambiguity="medium",
            summary_available=False,
            method_tags=["个股拆解", "竞价"],
            explicit_facts_contains=["早盘竞价参与"],
            candidate_title="强势股临盘承接后跟随",
            data_dependencies_contains=["kaipan_tick"],
            backtestability_statuses=["partially_executable"],
            automatic_review_statuses=["needs_human_review"],
            market_state_status="not_declared",
            kaipan_dependency=True,
            ambiguous_terms=["做T"],
            missing_fields=["具体竞价量能阈值"],
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("fb673d83-bfb7-4a88-a804-c60ad2f8d8a2"),
            article_revision_id=UUID("b351d6e2-c780-5a26-b607-026182a60db4"),
            content_hash="a7828b02a49c197c92cde3a4133afcf133d2c724e4a58e2b1c197f5dde7aab08",
            title="教你短线模式之一字首开！淘县九年义务教育！",
            article_content="上上周分享了短线模式之跨年龙，我们也不负众望成功抓到了东百集团。",
            covered_categories={"explicit_and_actionable_rules", "duplicate_or_near_duplicate_rules"},
            selection_reason="短线模式文章，和跨年龙/竞价文章共同覆盖近重复模式迁移场景。",
            expected_outcome_ambiguity="medium",
            summary_available=False,
            method_tags=["一字首开", "模式"],
            explicit_facts_contains=["一字首开"],
            candidate_title="一字首开后观察回封承接",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["executable"],
            automatic_review_statuses=["pending_backtest"],
            market_state_status="not_declared",
            kaipan_dependency=False,
        ),
        RegressionArticleFixture.for_test_case(
            article_id=UUID("be0d68bd-8fc3-445c-8510-8b01a43185d6"),
            article_revision_id=UUID("7fde0824-b12c-56b5-be39-b4d45c91c49b"),
            content_hash="56ec7a5cdf81c61899ccda0013d629c6bf8e214d4744a33c17effcac90f53722",
            title="量化风格下的轮动行情该如何实战思考，上周总结以及下周应对思路看这里！",
            article_content="本周总体来说参与难度比较大，让我们看看稳健的交易者是如何把握节奏的。",
            covered_categories={"mixed_concept_and_rule_content", "explicit_market_state", "human_review_required"},
            selection_reason="周总结+下周计划，兼具方法论和执行思路，适合作为需要人工复核的混合样本。",
            expected_outcome_ambiguity="medium",
            summary_available=False,
            method_tags=["轮动", "周总结"],
            explicit_facts_contains=["参与难度比较大"],
            candidate_title="轮动行情下控制追高节奏",
            data_dependencies_contains=["ohlcv_1d"],
            backtestability_statuses=["partially_executable"],
            automatic_review_statuses=["needs_human_review"],
            market_state_status="explicit",
            kaipan_dependency=False,
            ambiguous_terms=["把握节奏"],
            missing_fields=["执行节奏量化标准"],
        ),
    ]
