"""策略版本构建器：根据 TraderProfile 和文章证据构建 StrategyVersion（增强版）"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Protocol

from src.strategy_library.schemas import (
    StrategyRecommendation,
    StrategyVersion,
    StrategyVersionStatus,
    StrategyVersionType,
)
from src.trader_profile.schemas import (
    PositionBias,
    RiskStyle,
    TraderProfile,
)

if TYPE_CHECKING:
    pass


class ArticleEvidence(Protocol):
    """文章证据协议（duck typing）。

    S10-002: 扩展增加规则相关字段
    """
    article_id: str
    trading_symbols: list[str]
    sentiment_score: float | None
    confidence_score: float | None
    rationale: str | None
    entry_price: float | None  # 入场价（可选，用于计算止损）
    # S10-002 新增规则相关字段
    strategy_rules: list[dict] | None = None  # LLM 提取的策略规则
    preconditions: list[dict] | None = None  # 规则前置条件
    published_at: datetime | None = None  # 文章发布时间


def _base_decision_from_sentiment(sentiment: float | None) -> str:
    """根据情绪分返回基础决策。

    规则：
    - sentiment > 0.2  → buy（正面）
    - sentiment < -0.2  → sell（负面）
    - otherwise         → hold（中性）
    """
    if sentiment is None:
        return "hold"
    if sentiment > 0.2:
        return "buy"
    if sentiment < -0.2:
        return "sell"
    return "hold"


def _adjust_decision_by_bias(base_decision: str, position_bias: PositionBias | None) -> str:
    """根据仓位倾向调整基础决策。

    规则：
    - bias=short 时：buy → sell，sell → buy（反向）
    - bias=neutral 时：所有非 hold → hold（屏蔽方向性信号）
    - bias=long 时：不调整
    """
    if position_bias is None:
        return base_decision

    directional = position_bias.directional.lower() if position_bias.directional else "long"

    if directional == "short":
        if base_decision == "buy":
            return "sell"
        if base_decision == "sell":
            return "buy"
        return "hold"
    elif directional == "neutral":
        return "hold"
    # long：不调整
    return base_decision


def _estimate_stop_loss(
    entry_price: float | None,
    risk_style: RiskStyle | None,
    position_bias: PositionBias | None,
) -> float | None:
    """根据风险风格估算止损价。

    规则：
    - conservative：止损 3%（相对保守）
    - balanced：止损 5%
    - aggressive：不设止损（None）
    - 需要 entry_price 才能计算
    """
    if entry_price is None or risk_style is None:
        return None

    if risk_style == RiskStyle.AGGRESSIVE:
        return None

    stop_pct = 0.03 if risk_style == RiskStyle.CONSERVATIVE else 0.05
    return round(entry_price * (1 - stop_pct), 2)


def _score_article_for_profile(
    article: ArticleEvidence,
    profile: TraderProfile,
) -> float:
    """给文章打分，考虑主题偏好匹配程度（0.0 ~ 1.0）。

    匹配 profile.theme_preference 中任一主题 → 加权提升分数。
    """
    score = 0.5  # 基础分

    # 主题偏好匹配
    if profile.theme_preference:
        rationale_lower = (article.rationale or "").lower()
        for theme_stat in profile.theme_preference:
            if theme_stat.theme.lower() in rationale_lower:
                # 匹配到偏好主题：mention 次数越多加分越多
                score += min(theme_stat.mentions * 0.05, 0.4)
                break

    return min(score, 1.0)


def _collect_article_rules(articles: list[ArticleEvidence]) -> list[dict]:
    """从文章列表中收集策略规则，填充 rules_snapshot。

    每条规则保留原始 rule_id、rule_text、programmatic_indicators，
    并补充来源文章信息和 rule_pool_id 用于后续验真与追溯。

    S10-001: 将 ArticleMetadata.strategy_rules 填充到 StrategyVersion.rules_snapshot
    """
    rules = []
    for article in articles:
        # 获取文章的 strategy_rules（Protocol 支持 duck typing）
        article_rules = getattr(article, "strategy_rules", None) or []
        for rule in article_rules:
            rules.append({
                "rule_id": rule.get("rule_id", f"article_{article.article_id}_{len(rules)}"),
                "rule_text": rule.get("rule_text", ""),
                "programmatic_indicators": rule.get("programmatic_indicators", []),
                "required_fields": rule.get("required_fields", []),
                "source_article_id": str(article.article_id),
                "source_symbols": article.trading_symbols or [],
                **({"rule_pool_id": rule["rule_pool_id"]} if rule.get("rule_pool_id") else {}),
            })
    return rules


def validate_rule_symbol_association(article: ArticleEvidence) -> bool:
    """验证文章是否有有效的规则-标的关联。

    有效条件（满足其一即可）：
    1. 有 trading_symbols + strategy_rules
    2. 有 trading_symbols + preconditions
    3. 有 trading_symbols（用于 sentiment 场景）

    无效条件：
    - 有 strategy_rules 但 trading_symbols 为空/None
    - trading_symbols 和 strategy_rules 和 preconditions 都为空/None

    S10-008: 规则与标的联合验证
    """
    has_symbols = bool(article.trading_symbols)
    has_rules = bool(getattr(article, "strategy_rules", None))
    has_preconditions = bool(getattr(article, "preconditions", None))

    # 有效情况
    if has_symbols and (has_rules or has_preconditions):
        return True

    # 只有 symbols 没有 rules（用于 sentiment 场景）也有效
    if has_symbols and not has_rules and not has_preconditions:
        return True

    # 有 rules 但没有 symbols 关联 - 无效
    if has_rules and not has_symbols:
        return False

    return False


@dataclass
class StrategyVersionBuilder:
    """策略版本构建器（增强版）。

    将 TraderProfile（画像偏好）和 ArticleEvidence（文章证据）
    转换为可执行的 StrategyVersion。
    """

    def build_draft(
        self,
        *,
        trader_id: str,
        strategy_date: date,
        profile: TraderProfile,
        source_articles: list[ArticleEvidence],
    ) -> StrategyVersion:
        """构建草稿状态的策略版本（manual 类型）。"""
        return self._build(
            trader_id=trader_id,
            strategy_date=strategy_date,
            profile=profile,
            source_articles=source_articles,
            status=StrategyVersionStatus.draft,
            version_type=StrategyVersionType.manual,
            parent_version_id=None,
            recommendations=None,
            released_at=None,
        )

    def build_released(
        self,
        *,
        trader_id: str,
        strategy_date: date,
        profile: TraderProfile,
        source_articles: list[ArticleEvidence],
    ) -> StrategyVersion:
        """构建已发布状态的策略版本（manual 类型）。"""
        return self._build(
            trader_id=trader_id,
            strategy_date=strategy_date,
            profile=profile,
            source_articles=source_articles,
            status=StrategyVersionStatus.released,
            version_type=StrategyVersionType.manual,
            parent_version_id=None,
            recommendations=None,
            released_at=datetime.now(UTC),
        )

    def build_candidate(
        self,
        *,
        trader_id: str,
        strategy_date: date,
        parent_version_id: str,
        recommendations: list[StrategyRecommendation],
        notes: str | None = None,
    ) -> StrategyVersion:
        """构建候选优化版本（draft 状态，candidate 类型，S7-003）。

        候选版本：
        - 状态为 draft，不由 Agent 自动发布
        - version_type 为 candidate
        - 引用 parent_version_id 追溯正式版本
        - 由优化流程（S7-001/S7-002）生成
        """
        return StrategyVersion(
            version_id=f"{trader_id}_{strategy_date.isoformat()}_candidate_{parent_version_id[:8]}",
            trader_id=trader_id,
            strategy_date=strategy_date,
            status=StrategyVersionStatus.draft,
            version_type=StrategyVersionType.candidate,
            parent_version_id=parent_version_id,
            recommendations=recommendations,
            source_article_ids=[],
            evidence_refs=[],
            notes=notes,
            released_at=None,
            rules_snapshot=[],
        )

    def _build(
        self,
        *,
        trader_id: str,
        strategy_date: date,
        profile: TraderProfile,
        source_articles: list[ArticleEvidence],
        status: StrategyVersionStatus,
        version_type: StrategyVersionType,
        parent_version_id: str | None,
        recommendations: list[StrategyRecommendation] | None,
        released_at: datetime | None,
    ) -> StrategyVersion:
        """内部构建方法。"""
        # === 1. 按主题偏好过滤和排序文章 ===
        # S10-008: 同时应用规则-标的联合验证
        scored = [
            (article, _score_article_for_profile(article, profile))
            for article in source_articles
            if article.trading_symbols and validate_rule_symbol_association(article)
        ]
        # 按 profile 匹配分数降序排列
        scored.sort(key=lambda x: x[1], reverse=True)

        # === 2. 应用 max_positions 限制 ===
        max_positions = (
            profile.strategy_preference.max_positions
            if profile.strategy_preference and profile.strategy_preference.max_positions
            else None
        )
        if max_positions is not None and len(scored) > max_positions:
            scored = scored[:max_positions]

        # === 3. 生成 recommendations ===
        generated_recommendations: list[StrategyRecommendation] = []
        source_article_ids: list[str] = []
        evidence_refs: list[str] = []

        for article, _ in scored:
            source_article_ids.append(article.article_id)

            sentiment = article.sentiment_score
            confidence = article.confidence_score if article.confidence_score is not None else 0.5

            # 基础决策由情绪分决定
            base_decision = _base_decision_from_sentiment(sentiment)
            # 由仓位倾向调整
            decision = _adjust_decision_by_bias(base_decision, profile.position_bias)

            rationale = article.rationale or None
            if rationale:
                evidence_refs.append(f"{article.article_id}:{rationale}")

            # 估算止损价（conservative / balanced 风格）
            stop_loss = _estimate_stop_loss(article.entry_price, profile.risk_style, profile.position_bias)

            generated_recommendations.append(StrategyRecommendation(
                symbol=article.trading_symbols[0],
                decision=decision,
                confidence=confidence,
                entry_price=None,
                target_price=None,
                stop_loss_price=stop_loss,
                rationale=rationale,
                evidence_refs=[article.article_id],
            ))

        final_recommendations = recommendations if recommendations is not None else generated_recommendations

        # S10-001: 从文章中收集 strategy_rules 填充 rules_snapshot
        # 使用 scored 列表（已过滤无 trading_symbols 的文章）
        rules_snapshot = _collect_article_rules([article for article, _ in scored])

        return StrategyVersion(
            version_id=f"{trader_id}_{strategy_date.isoformat()}_{status.value}",
            trader_id=trader_id,
            strategy_date=strategy_date,
            status=status,
            version_type=version_type,
            parent_version_id=parent_version_id,
            recommendations=final_recommendations,
            source_article_ids=source_article_ids,
            evidence_refs=evidence_refs,
            notes=None,
            released_at=released_at,
            rules_snapshot=rules_snapshot,
        )
