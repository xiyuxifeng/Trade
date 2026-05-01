"""置信度计算单元测试"""
import pytest
from datetime import date, datetime

from src.rule_backtest.confidence import compute_confidence_adjustment, get_confidence_level
from src.rule_pool.schemas import RuleBacktestResult


def _make_result(
    total_trades: int = 10,
    hit_trades: int = 6,
    hit_rate: float = 0.6,
    avg_win_return: float = 0.05,
    avg_loss_return: float = -0.03,
    sharpe_ratio: float = 1.0,
    max_drawdown: float = 0.1,
    sample_count: int = 10,
) -> RuleBacktestResult:
    """创建测试用 RuleBacktestResult"""
    return RuleBacktestResult(
        run_id="test_run",
        run_at=datetime(2026, 4, 30),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 4, 30),
        total_trades=total_trades,
        hit_trades=hit_trades,
        miss_trades=total_trades - hit_trades,
        hit_rate=hit_rate,
        avg_return=0.02,
        avg_win_return=avg_win_return,
        avg_loss_return=avg_loss_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        sample_count=sample_count,
    )


class TestComputeConfidenceAdjustment:
    """compute_confidence_adjustment 测试"""

    def test_normal_case(self):
        """正常回测结果，置信度应提升"""
        result = _make_result(
            total_trades=20,
            hit_rate=0.65,
            avg_win_return=0.06,
            avg_loss_return=-0.03,
            sharpe_ratio=1.2,
            max_drawdown=0.08,
            sample_count=20,
        )
        initial = 0.6
        validated = compute_confidence_adjustment(initial, result, prior_weight=20)
        # 回测表现不错，最终置信度应该接近回测证据
        assert 0.5 < validated <= 1.0

    def test_zero_trades(self):
        """零交易时返回保守的初始置信度"""
        result = _make_result(total_trades=0, sample_count=0)
        initial = 0.7
        validated = compute_confidence_adjustment(initial, result)
        assert validated == initial * 0.8  # 降低 20%

    def test_small_sample_protection(self):
        """样本数 < 10 时启用保护机制"""
        result = _make_result(total_trades=5, sample_count=5)
        initial = 0.8
        validated = compute_confidence_adjustment(initial, result, prior_weight=20)
        # 保护因子 = 0.5，分数会降低
        # composite_score 约 0.6，保护后 0.3
        # 后验 = (0.3 * 20 + 0.8 * 5) / (20 + 5) ≈ 0.44
        assert validated < initial

    def test_perfect_backtest(self):
        """完美回测（胜率 100%）应得高分"""
        result = _make_result(
            total_trades=30,
            hit_trades=30,
            hit_rate=1.0,
            avg_win_return=0.05,
            avg_loss_return=-0.01,
            sharpe_ratio=2.0,
            max_drawdown=0.02,
            sample_count=30,
        )
        validated = compute_confidence_adjustment(0.5, result, prior_weight=20)
        assert validated >= 0.69

    def test_poor_backtest(self):
        """糟糕回测（胜率低、回撤大）应降低置信度"""
        result = _make_result(
            total_trades=30,
            hit_rate=0.3,
            avg_win_return=0.02,
            avg_loss_return=-0.05,
            sharpe_ratio=0.3,
            max_drawdown=0.25,
            sample_count=30,
        )
        initial = 0.8
        validated = compute_confidence_adjustment(initial, result, prior_weight=20)
        assert validated < initial

    def test_missing_sharpe(self):
        """缺少夏普比率时使用中性分 0.5"""
        result = _make_result(sharpe_ratio=None)
        validated = compute_confidence_adjustment(0.6, result)
        # 不应报错，且结果合理
        assert 0.0 <= validated <= 1.0

    def test_missing_drawdown(self):
        """缺少最大回撤时使用中性分 0.5"""
        result = _make_result(max_drawdown=None)
        validated = compute_confidence_adjustment(0.6, result)
        assert 0.0 <= validated <= 1.0

    def test_missing_profit_loss_data(self):
        """缺少盈亏数据时使用中性分"""
        result = _make_result(avg_win_return=None, avg_loss_return=None)
        validated = compute_confidence_adjustment(0.6, result)
        assert 0.0 <= validated <= 1.0

    def test_bayesian_weighting(self):
        """贝叶斯式加权：先验权重越大，初始置信度影响越大"""
        # 使用差劲的回测结果，期望高先验权重保护初始置信度
        result = _make_result(
            total_trades=50,
            hit_rate=0.3,  # 差劲的胜率
            avg_win_return=0.02,
            avg_loss_return=-0.08,  # 差劲的盈亏比
            sharpe_ratio=0.2,
            max_drawdown=0.3,
            sample_count=50,
        )
        initial = 0.9

        # 低先验权重：回测证据主导，置信度被拉低
        validated_low_prior = compute_confidence_adjustment(
            initial, result, prior_weight=5
        )
        # 高先验权重：初始置信度保护，回测影响小
        validated_high_prior = compute_confidence_adjustment(
            initial, result, prior_weight=100
        )

        # 高先验权重时，结果应更接近初始值
        diff_low = abs(validated_low_prior - initial)
        diff_high = abs(validated_high_prior - initial)
        assert diff_high < diff_low

    def test_confidence_bounds(self):
        """置信度应在 [0, 1] 范围内"""
        # 极端好结果
        result_good = _make_result(
            total_trades=100,
            hit_rate=0.9,
            avg_win_return=0.1,
            avg_loss_return=-0.01,
            sharpe_ratio=3.0,
            max_drawdown=0.01,
            sample_count=100,
        )
        validated_good = compute_confidence_adjustment(1.0, result_good)
        assert validated_good <= 1.0

        # 极端差结果
        result_bad = _make_result(
            total_trades=100,
            hit_rate=0.1,
            avg_win_return=0.01,
            avg_loss_return=-0.1,
            sharpe_ratio=0.0,
            max_drawdown=0.5,
            sample_count=100,
        )
        validated_bad = compute_confidence_adjustment(0.0, result_bad)
        assert validated_bad >= 0.0


class TestGetConfidenceLevel:
    """get_confidence_level 测试"""

    def test_level_a_high_confidence(self):
        """置信度 >= 0.8 返回 A"""
        assert get_confidence_level(0.8) == "A"
        assert get_confidence_level(0.9) == "A"
        assert get_confidence_level(1.0) == "A"

    def test_level_b(self):
        """置信度 >= 0.6 且 < 0.8 返回 B"""
        assert get_confidence_level(0.6) == "B"
        assert get_confidence_level(0.7) == "B"
        assert get_confidence_level(0.79) == "B"

    def test_level_c(self):
        """置信度 >= 0.4 且 < 0.6 返回 C"""
        assert get_confidence_level(0.4) == "C"
        assert get_confidence_level(0.5) == "C"
        assert get_confidence_level(0.59) == "C"

    def test_level_d_low_confidence(self):
        """置信度 < 0.4 返回 D"""
        assert get_confidence_level(0.0) == "D"
        assert get_confidence_level(0.3) == "D"
        assert get_confidence_level(0.39) == "D"

    @pytest.mark.parametrize("confidence", [0.0, 0.4, 0.6, 0.8, 1.0])
    def test_boundary_values(self, confidence):
        """测试边界值"""
        level = get_confidence_level(confidence)
        assert level in ["A", "B", "C", "D"]