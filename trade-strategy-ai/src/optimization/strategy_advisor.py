"""S7-002: 策略调整建议（StrategyAdvisor）。

生成规则：
  1. 命中率 < 10% + 后验收益负 → 建议删除
  2. 命中率 > 70% + 后验收益负 → 建议复核止盈止损
  3. 命中率 < 30% + 后验收益正 → 建议升级为程序化
  4. missing_snapshot → 建议检查快照覆盖
  5. 程序化 + 命中率 < 5% → 建议删除或修改条件

ref: docs/superpowers/specs/2026-04-28-stage7-s7-001-s7-002-design.md
"""

from dataclasses import dataclass, field
from datetime import date

from src.backtest.schemas import RuleValidationResult
from src.common.logger import get_logger

logger = get_logger(__name__)


def _format_return_mean(value: float) -> str:
    """格式化收益率，负数显示为「亏损 X%」，正数显示为「+X%」。"""
    if value < 0:
        return f"亏损 {abs(value) * 100:.2f}%"
    return f"+{value * 100:.2f}%"


@dataclass
class RuleAdjustment:
    """单条规则调整建议（S7-002 输出）。"""
    trader_id: str
    rule_id: str
    rule_text: str
    current_status: str
    suggestion: str
    confidence: float
    hit_rate: float | None
    posterior_return_mean: float | None
    posterior_return_median: float | None
    trade_date: date | None = None  # 规则验真的交易日期，用于 RollingEvaluator 窗口计算


@dataclass
class AdvisorResult:
    """S7-002 完整输出。"""
    trader_id: str
    adjustments: list[RuleAdjustment] = field(default_factory=list)
    skipped_rules: list[str] = field(default_factory=list)


# -------------------------------------------------
# 调整规则定义
# -------------------------------------------------
_ADJUSTMENT_RULES = [
    {
        # 规则1：命中率极低 + 后验收益负 → 建议删除
        "condition": lambda r: (
            r.hit_rate is not None and r.hit_rate < 0.10
            and r.posterior_return_mean is not None
            and r.posterior_return_mean < 0
        ),
        "current_status": "hit_rate_too_low_and_return_negative",
        "suggestion": (
            "建议删除该规则：命中率 {hit_rate:.0%} 且后验收益 {return_mean}，"
            "该规则当前净亏损，建议移除避免误导交易决策。"
        ),
    },
    {
        # 规则2：命中率高但收益负 → 建议复核止盈止损
        "condition": lambda r: (
            r.hit_rate is not None and r.hit_rate > 0.70
            and r.posterior_return_mean is not None
            and r.posterior_return_mean < 0
        ),
        "current_status": "high_hit_rate_but_negative_return",
        "suggestion": (
            "建议复核止盈/止损参数：规则命中率 {hit_rate:.0%}，"
            "但后验收益 {return_mean}，可能是止盈过紧或止损过宽。"
        ),
    },
    {
        # 规则3：规则未命中但后验收益为正 → 建议升级为程序化
        "condition": lambda r: (
            r.hit_rate is not None and r.hit_rate < 0.30
            and r.posterior_return_mean is not None
            and r.posterior_return_mean > 0
        ),
        "current_status": "missed_opportunity",
        "suggestion": (
            "规则未充分触发（命中率 {hit_rate:.0%}），"
            "但后验收益 {return_mean}，建议升级为可程序化执行。"
        ),
    },
    {
        # 规则4：规则长期 missing_snapshot → 建议检查快照覆盖
        "condition": lambda r: r.validation_status == "missing_snapshot",
        "current_status": "missing_snapshot",
        "suggestion": (
            "规则所需快照数据长期缺失，无法验真。"
            "建议检查 data/market_universe/snapshots 目录覆盖情况。"
        ),
    },
    {
        # 规则5：程序化但命中率极低 → 建议删除或修改条件
        "condition": lambda r: (
            r.programmable is True
            and r.hit_rate is not None
            and r.hit_rate < 0.05
        ),
        "current_status": "programmable_but_rarely_hit",
        "suggestion": (
            "规则声明为可程序化但命中率仅 {hit_rate:.0%}，"
            "建议重新审视规则条件或删除。"
        ),
    },
]


class StrategyAdvisor:
    """策略调整建议生成器。"""

    def advise(
        self,
        rule_validations: list[RuleValidationResult],
    ) -> AdvisorResult:
        """基于规则验真结果生成策略调整建议。

        Args:
            rule_validations: 单个 trader 的规则验真结果列表

        Returns:
            AdvisorResult — 包含 adjustments 和 skipped_rules
        """
        if not rule_validations:
            return AdvisorResult(trader_id="", adjustments=[], skipped_rules=[])

        trader_id = rule_validations[0].trader_id
        adjustments: list[RuleAdjustment] = []
        skipped: list[str] = []

        for rvr in rule_validations:
            matched = False
            for rule in _ADJUSTMENT_RULES:
                if rule["condition"](rvr):
                    matched = True
                    suggestion = rule["suggestion"].format(
                        hit_rate=rvr.hit_rate or 0.0,
                        return_mean=_format_return_mean(rvr.posterior_return_mean or 0.0),
                    )
                    # 置信度与 hit_rate 相关
                    confidence = min((rvr.hit_rate or 0.0) + 0.3, 1.0)

                    adjustments.append(
                        RuleAdjustment(
                            trader_id=rvr.trader_id,
                            rule_id=rvr.rule_id,
                            rule_text=rvr.rule_text,
                            current_status=rule["current_status"],
                            suggestion=suggestion,
                            confidence=confidence,
                            hit_rate=rvr.hit_rate,
                            posterior_return_mean=rvr.posterior_return_mean,
                            posterior_return_median=rvr.posterior_return_median,
                        )
                    )
                    logger.debug(
                        "规则调整建议: trader=%s rule=%s status=%s",
                        rvr.trader_id, rvr.rule_id, rule["current_status"],
                    )
                    break  # 每条规则最多匹配一条建议

            if not matched:
                skipped.append(rvr.rule_id)

        logger.info(
            "策略调整建议生成完成: trader=%s, 建议数=%d, 跳过数=%d",
            trader_id, len(adjustments), len(skipped),
        )
        return AdvisorResult(trader_id=trader_id, adjustments=adjustments, skipped_rules=skipped)
