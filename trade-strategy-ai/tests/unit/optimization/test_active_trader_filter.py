import pytest
from unittest.mock import patch
from src.backtest.schemas import BacktestResult, BacktestSummary, BacktestTradeRecord, RuleValidationResult
from src.optimization.active_trader_filter import ActiveTraderFilter, TraderFilterResult
from src.optimization.config import ActiveTraderFilterConfig


def make_result(trader_id: str, wins: int, total: int) -> BacktestResult:
    """Helper: 创建指定胜率的 BacktestResult"""
    closed = [
        BacktestTradeRecord(
            trade_date=None, trader_id=trader_id, strategy_version_id="v1",
            symbol=f"S{i}", status="closed", entry_price=10.0, exit_price=10.5,
            return_pct=0.05 if i < wins else -0.05,
        )
        for i in range(total)
    ]
    summary = BacktestSummary(
        total_days=10, total_trades=total, valid_trades=total,
        skipped_trades=0, win_rate=wins / total if total else None,
        avg_return_pct=0.0,
    )
    return BacktestResult(
        request_trader_id=trader_id,
        request_date_from=None,
        request_date_to=None,
        records=closed,
        summary=summary,
    )


class TestActiveTraderFilter:
    def test_filter_basic(self):
        """通过筛选的 trader"""
        config = ActiveTraderFilterConfig()
        flt = ActiveTraderFilter(config)
        results = {"T1": make_result("T1", wins=6, total=10)}
        out = flt.filter(results)
        assert len(out) == 1
        assert out[0].filter_passed is True
        assert out[0].composite_score > 0.0

    def test_filter_low_trades(self):
        """交易数不足被折扣"""
        config = ActiveTraderFilterConfig(min_trades=10)
        flt = ActiveTraderFilter(config)
        # T1: 3笔全赢，但样本太少应该被折扣
        results = {"T1": make_result("T1", wins=3, total=3)}
        out = flt.filter(results)
        # sample_confidence = 3/10 = 0.3，adjusted_win_rate = (3+5)/(3+10)=8/13≈0.615
        # composite_score ≈ 0.615 * 0.3 ≈ 0.185 < min_score=0.3 → 不通过
        assert out[0].filter_passed is False

    def test_bayesian_shrinkage(self):
        """贝叶斯收缩效果：5 笔时高胜率被收缩"""
        config = ActiveTraderFilterConfig(bayesian_alpha=10.0, baseline_win_rate=0.50)
        flt = ActiveTraderFilter(config)
        # 5 笔全赢 → 原始胜率 100%
        results = {"T1": make_result("T1", wins=5, total=5)}
        out = flt.filter(results)
        # adjusted = (5 + 10*0.5) / (5 + 10) = 10/15 ≈ 0.667
        assert out[0].adjusted_win_rate == pytest.approx(10 / 15, rel=1e-3)
        assert out[0].raw_win_rate == 1.0  # 原始胜率不变

    def test_composite_score排序(self):
        """结果按 composite_score 降序"""
        config = ActiveTraderFilterConfig()
        flt = ActiveTraderFilter(config)
        results = {
            "T1": make_result("T1", wins=4, total=10),
            "T2": make_result("T2", wins=7, total=10),
            "T3": make_result("T3", wins=2, total=10),
        }
        out = flt.filter(results)
        scores = [r.composite_score for r in out]
        assert scores == sorted(scores, reverse=True)

    def test_no_backtest_result(self):
        """空输入返回空列表"""
        flt = ActiveTraderFilter(ActiveTraderFilterConfig())
        out = flt.filter({})
        assert out == []

    def test_rule_validations_populates_rule_quality(self):
        """rule_validations 提供时 rule_quality 字段被正确填充"""
        config = ActiveTraderFilterConfig()
        flt = ActiveTraderFilter(config)
        results = {"T1": make_result("T1", wins=6, total=10)}
        rvs = {
            "T1": [
                RuleValidationResult(
                    trader_id="T1", strategy_version_id="v1", rule_id="R1",
                    rule_text="规则1", programmable=True,
                    validation_status="validated", hit_count=5, sample_count=10,
                    hit_rate=0.5,
                ),
                RuleValidationResult(
                    trader_id="T1", strategy_version_id="v1", rule_id="R2",
                    rule_text="规则2", programmable=True,
                    validation_status="validated", hit_count=2, sample_count=10,
                    hit_rate=0.2,
                ),
            ]
        }
        out = flt.filter(results, rule_validations=rvs)
        assert out[0].rule_quality == {"R1": 0.5, "R2": 0.2}

    def test_min_rule_hit_rate_filters_low_hit_rules(self):
        """min_rule_hit_rate 设置时，命中率低于门槛的规则会标记到 fail_reasons"""
        config = ActiveTraderFilterConfig(min_rule_hit_rate=0.30)
        flt = ActiveTraderFilter(config)
        results = {"T1": make_result("T1", wins=6, total=10)}
        rvs = {
            "T1": [
                RuleValidationResult(
                    trader_id="T1", strategy_version_id="v1", rule_id="R1",
                    rule_text="规则1", programmable=True,
                    validation_status="validated", hit_count=5, sample_count=10,
                    hit_rate=0.5,
                ),
                RuleValidationResult(
                    trader_id="T1", strategy_version_id="v1", rule_id="R2",
                    rule_text="规则2", programmable=True,
                    validation_status="validated", hit_count=2, sample_count=10,
                    hit_rate=0.2,
                ),
            ]
        }
        out = flt.filter(results, rule_validations=rvs)
        assert any("规则命中率低于门槛" in f for f in out[0].fail_reasons)
        assert "R2" in out[0].fail_reasons[0]

    def test_min_rule_hit_rate_all_pass(self):
        """所有规则命中率都 >= min_rule_hit_rate 时通过规则质量检查"""
        config = ActiveTraderFilterConfig(min_rule_hit_rate=0.10)
        flt = ActiveTraderFilter(config)
        results = {"T1": make_result("T1", wins=6, total=10)}
        rvs = {
            "T1": [
                RuleValidationResult(
                    trader_id="T1", strategy_version_id="v1", rule_id="R1",
                    rule_text="规则1", programmable=True,
                    validation_status="validated", hit_count=5, sample_count=10,
                    hit_rate=0.5,
                ),
            ]
        }
        out = flt.filter(results, rule_validations=rvs)
        assert any("规则命中率" in p for p in out[0].pass_reasons)

    def test_all_zero_valid_trades_emits_warning(self):
        """所有 trader 有效交易数均为 0 时应发出警告日志"""
        import logging
        from src.backtest.schemas import BacktestResult, BacktestSummary

        config = ActiveTraderFilterConfig()
        flt = ActiveTraderFilter(config)

        # 创建 valid_trades=0 的 BacktestResult
        result = BacktestResult(
            request_trader_id="T1",
            request_date_from=None,
            request_date_to=None,
            records=[],
            summary=BacktestSummary(
                total_days=0, total_trades=0, valid_trades=0, skipped_trades=0, win_rate=None,
            ),
        )
        results = {"T1": result}

        # 捕获 logger.warning 输出
        with patch("src.optimization.active_trader_filter.logger") as mock_logger:
            out = flt.filter(results)
            # valid_trades=0 的 trader 仍返回 filter_passed=False 的结果（非空列表）
            assert len(out) == 1
            assert out[0].filter_passed is False
            assert out[0].valid_trades == 0
            # 但应发出警告提示
            mock_logger.warning.assert_called_once()
            assert "有效交易数均为 0" in mock_logger.warning.call_args[0][0]

    def test_mixed_zero_and_nonzero_no_warning(self):
        """部分 trader valid_trades=0 时不触发该警告"""
        from src.backtest.schemas import BacktestResult, BacktestSummary

        flt = ActiveTraderFilter(ActiveTraderFilterConfig())

        results = {
            "T1": BacktestResult(
                request_trader_id="T1",
                request_date_from=None,
                request_date_to=None,
                records=[],
                summary=BacktestSummary(total_days=0, total_trades=0, valid_trades=0, skipped_trades=0, win_rate=None),
            ),
            "T2": make_result("T2", wins=6, total=10),
        }

        with patch("src.optimization.active_trader_filter.logger") as mock_logger:
            out = flt.filter(results)
            assert len(out) == 2
            # 不应触发"均为0"的警告
            warning_calls = [c for c in mock_logger.warning.call_args_list]
            assert not any("有效交易数均为 0" in str(c) for c in warning_calls)
