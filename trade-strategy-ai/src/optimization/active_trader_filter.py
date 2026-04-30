"""S7-001: 活跃 trader 筛选（ActiveTraderFilter）。

贝叶斯收缩公式：
    adjusted_win_rate = (wins + alpha * baseline) / (valid_trades + alpha)
    sample_confidence = min(valid_trades / min_trades, 1.0)
    composite_score = adjusted_win_rate * sample_confidence

ref: docs/superpowers/specs/2026-04-28-stage7-s7-001-s7-002-design.md
"""

from dataclasses import dataclass, field

from src.backtest.schemas import BacktestResult, BacktestSummary, RuleValidationResult
from src.evaluation.ranking_service import RankingEntry
from src.optimization.config import ActiveTraderFilterConfig

from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TraderFilterResult:
    """单个 trader 的筛选结果。"""
    trader_id: str
    filter_passed: bool
    raw_win_rate: float | None           # 原始胜率（未收缩）
    adjusted_win_rate: float | None     # 贝叶斯收缩后胜率
    valid_trades: int                   # 有效交易笔数
    sample_confidence: float            # 样本置信度（0~1）
    composite_score: float              # 综合得分
    pass_reasons: list[str] = field(default_factory=list)
    fail_reasons: list[str] = field(default_factory=list)
    rule_quality: dict[str, float] = field(default_factory=dict)


class ActiveTraderFilter:
    """活跃 trader 筛选器。

    使用贝叶斯收缩胜率 + 样本置信度综合评估 trader 质量。
    """

    def __init__(self, config: ActiveTraderFilterConfig | None = None):
        self.config = config or ActiveTraderFilterConfig()

    def _compute_score(
        self,
        wins: int,
        valid_trades: int,
    ) -> tuple[float, float, float]:
        """计算综合得分。

        Returns:
            (adjusted_win_rate, sample_confidence, composite_score)
        """
        c = self.config
        if valid_trades == 0:
            return (0.0, 0.0, 0.0)

        # 贝叶斯收缩胜率
        adjusted = (wins + c.bayesian_alpha * c.baseline_win_rate) / (
            valid_trades + c.bayesian_alpha
        )
        # 样本置信度
        confidence = min(valid_trades / c.min_trades, 1.0)
        # 综合得分
        score = adjusted * confidence
        return (adjusted, confidence, score)

    def filter(
        self,
        backtest_results: dict[str, BacktestResult],
        rankings: dict[str, list[RankingEntry]] | None = None,
        rule_validations: dict[str, list[RuleValidationResult]] | None = None,
    ) -> list[TraderFilterResult]:
        """对多个 trader 执行筛选。

        Args:
            backtest_results: {trader_id: BacktestResult}
            rankings: 可选，{trader_id: [RankingEntry]}，暂未使用（为后续 S7-001/S7-004 联动留接口）
            rule_validations: 可选，{trader_id: [RuleValidationResult]}，用于规则质量过滤
                — 若设置 min_rule_hit_rate，则任一规则命中率低于门槛会标记到 fail_reasons

        Returns:
            通过筛选的 TraderFilterResult 列表（按 composite_score 降序）
        """
        c = self.config
        all_results: list[TraderFilterResult] = []

        for trader_id, result in backtest_results.items():
            summary: BacktestSummary | None = result.summary
            valid_trades = summary.valid_trades if summary else 0
            raw_wr = summary.win_rate if summary else None
            wins = int(raw_wr * valid_trades) if raw_wr is not None and valid_trades > 0 else 0

            pass_reasons: list[str] = []
            fail_reasons: list[str] = []
            rule_quality: dict[str, float] = {}

            # 1. 有效交易数检查
            if valid_trades < c.min_trades:
                fail_reasons.append(
                    f"有效交易数 {valid_trades} < 门槛 {c.min_trades}"
                )

            # 2. 原始胜率检查
            if raw_wr is not None and raw_wr < c.min_win_rate:
                fail_reasons.append(
                    f"原始胜率 {raw_wr:.0%} < 门槛 {c.min_win_rate:.0%}"
                )
            elif raw_wr is not None:
                pass_reasons.append(f"原始胜率 {raw_wr:.0%} >= 门槛")

            # 3. 规则质量过滤（可选）
            if rule_validations and trader_id in rule_validations:
                trader_rvs = rule_validations[trader_id]
                for rvr in trader_rvs:
                    if rvr.hit_rate is not None:
                        rule_quality[rvr.rule_id] = rvr.hit_rate

                if c.min_rule_hit_rate is not None:
                    low_hit_rules = [
                        rvr.rule_id for rvr in trader_rvs
                        if rvr.hit_rate is not None
                        and rvr.hit_rate < c.min_rule_hit_rate
                    ]
                    if low_hit_rules:
                        fail_reasons.append(
                            f"规则命中率低于门槛 {c.min_rule_hit_rate:.0%}: {low_hit_rules}"
                        )
                    else:
                        pass_reasons.append("所有规则命中率 >= 门槛")

            # 4. 计算综合得分
            adj_wr, conf, score = self._compute_score(wins, valid_trades)

            # 5. 最终判断
            filter_passed = (
                score >= c.min_score
                and raw_wr is not None
                and raw_wr >= c.min_win_rate
                and valid_trades >= c.min_trades
                and (c.min_rule_hit_rate is None or not any(
                    rule_quality.get(rv.rule_id, 0) < c.min_rule_hit_rate
                    for rv in (rule_validations or {}).get(trader_id, [])
                    if rv.hit_rate is not None
                ))
            )

            if filter_passed:
                pass_reasons.append(f"综合得分 {score:.3f} >= 门槛 {c.min_score:.3f}")
            else:
                fail_reasons.append(f"综合得分 {score:.3f} < 门槛 {c.min_score:.3f}")

            all_results.append(
                TraderFilterResult(
                    trader_id=trader_id,
                    filter_passed=filter_passed,
                    raw_win_rate=raw_wr,
                    adjusted_win_rate=adj_wr,
                    valid_trades=valid_trades,
                    sample_confidence=conf,
                    composite_score=score,
                    pass_reasons=pass_reasons,
                    fail_reasons=fail_reasons,
                    rule_quality=rule_quality,
                )
            )

        # 按 composite_score 降序排列
        all_results.sort(key=lambda r: r.composite_score, reverse=True)

        # 检查是否所有 trader 有效交易数均为 0（静默空结果警告）
        if all_results and all(r.valid_trades == 0 for r in all_results):
            logger.warning(
                "所有 Trader 有效交易数均为 0，请检查 backtest_results 数据是否正确。"
                "返回空结果（无任何 trader 通过筛选）。"
            )

        logger.info("Trader筛选完成: 输入=%d, 通过=%d", len(all_results), sum(1 for r in all_results if r.filter_passed))
        return all_results
