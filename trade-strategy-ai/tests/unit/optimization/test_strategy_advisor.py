import pytest
from src.backtest.schemas import RuleValidationResult
from src.optimization.strategy_advisor import StrategyAdvisor, RuleAdjustment, AdvisorResult, _format_return_mean


def make_rvr(
    rule_id: str,
    hit_rate: float | None,
    posterior_return_mean: float | None,
    validation_status: str = "validated",
    programmable: bool = True,
) -> RuleValidationResult:
    return RuleValidationResult(
        trader_id="T1",
        strategy_version_id="v1",
        rule_id=rule_id,
        rule_text=f"规则 {rule_id}",
        programmable=programmable,
        validation_status=validation_status,
        hit_count=0, sample_count=0,
        hit_rate=hit_rate,
        posterior_return_mean=posterior_return_mean,
        posterior_return_median=None,
        notes=[],
    )


class TestStrategyAdvisor:
    def test_delete_rule_on_low_hit_and_negative_return(self):
        """命中率<10% + 后验收益负 → 建议删除"""
        advisor = StrategyAdvisor()
        validations = [
            make_rvr("R1", hit_rate=0.05, posterior_return_mean=-0.02),
        ]
        result = advisor.advise(validations)
        assert len(result.adjustments) == 1
        assert result.adjustments[0].current_status == "hit_rate_too_low_and_return_negative"
        assert "建议删除" in result.adjustments[0].suggestion

    def test_review_stop_loss_on_high_hit_negative_return(self):
        """命中率>70% + 后验收益负 → 建议复核止盈止损"""
        advisor = StrategyAdvisor()
        validations = [
            make_rvr("R2", hit_rate=0.75, posterior_return_mean=-0.01),
        ]
        result = advisor.advise(validations)
        assert len(result.adjustments) == 1
        assert result.adjustments[0].current_status == "high_hit_rate_but_negative_return"
        assert "止盈" in result.adjustments[0].suggestion or "止损" in result.adjustments[0].suggestion

    def test_missing_snapshot(self):
        """missing_snapshot → 建议检查快照"""
        advisor = StrategyAdvisor()
        validations = [
            make_rvr("R3", hit_rate=None, posterior_return_mean=None,
                     validation_status="missing_snapshot"),
        ]
        result = advisor.advise(validations)
        assert len(result.adjustments) == 1
        assert result.adjustments[0].current_status == "missing_snapshot"

    def test_skipped_rules(self):
        """不满足任何 condition 的规则落入 skipped_rules"""
        advisor = StrategyAdvisor()
        validations = [
            make_rvr("R_good", hit_rate=0.60, posterior_return_mean=0.05),
        ]
        result = advisor.advise(validations)
        assert len(result.adjustments) == 0
        assert "R_good" in result.skipped_rules

    def test_multiple_rules(self):
        """多条规则同时匹配"""
        advisor = StrategyAdvisor()
        validations = [
            make_rvr("R1", hit_rate=0.05, posterior_return_mean=-0.02),
            make_rvr("R2", hit_rate=0.75, posterior_return_mean=-0.01),
            make_rvr("R3", hit_rate=None, posterior_return_mean=None,
                     validation_status="missing_snapshot"),
            make_rvr("R4", hit_rate=0.60, posterior_return_mean=0.05),
        ]
        result = advisor.advise(validations)
        assert len(result.adjustments) == 3
        assert "R4" in result.skipped_rules

    def test_format_return_mean_negative(self):
        """负收益率显示为「亏损 X%」"""
        assert _format_return_mean(-0.05) == "亏损 5.00%"
        assert _format_return_mean(-0.1234) == "亏损 12.34%"

    def test_format_return_mean_positive(self):
        """正收益率显示为「+X%」"""
        assert _format_return_mean(0.12) == "+12.00%"
        assert _format_return_mean(0.05) == "+5.00%"

    def test_negative_return_in_suggestion(self):
        """负收益率在建议文本中正确格式化"""
        advisor = StrategyAdvisor()
        validations = [
            make_rvr("R1", hit_rate=0.05, posterior_return_mean=-0.02),
        ]
        result = advisor.advise(validations)
        assert "亏损" in result.adjustments[0].suggestion
        assert "-2.00%" not in result.adjustments[0].suggestion

    def test_positive_return_in_suggestion(self):
        """正收益率在建议文本中正确格式化"""
        advisor = StrategyAdvisor()
        validations = [
            make_rvr("R1", hit_rate=0.20, posterior_return_mean=0.08),
        ]
        result = advisor.advise(validations)
        assert "+" in result.adjustments[0].suggestion
        assert "8.00%" in result.adjustments[0].suggestion
