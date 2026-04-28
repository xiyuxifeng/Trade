import pytest
from src.backtest.schemas import BacktestResult, BacktestSummary, BacktestTradeRecord
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
