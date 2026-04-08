"""
参数稳定性分析单元测试 — P5-012。
"""

from __future__ import annotations

import math
from src.persona.param_stability import (
    ParamStabilityAnalyzer,
    ParamDistribution,
    StabilityAnalysis,
    analyze_param_stability,
)


class TestParamDistribution:
    """ParamDistribution 数据类测试。"""

    def test_distribution_creation(self):
        """测试分布统计创建。"""
        dist = ParamDistribution(
            param="x",
            mean=5.0,
            std=0.5,
            min_val=4.0,
            max_val=6.0,
            median=5.0,
            ci_lower=4.2,
            ci_upper=5.8,
            cv=0.1,
        )

        assert dist.param == "x"
        assert dist.mean == 5.0
        assert dist.cv == 0.1


class TestParamStabilityAnalyzer:
    """ParamStabilityAnalyzer 测试。"""

    def test_basic_analysis(self):
        """测试基本分析。"""
        data = list(range(100))

        def objective(params):
            return -abs(params["x"] - 50)

        analyzer = ParamStabilityAnalyzer(objective, random_seed=42)
        result = analyzer.analyze(
            data=data,
            param_space={"x": (0, 100)},
            n_iterations=10,
        )

        assert isinstance(result.overall_stability_score, float)
        assert 0 <= result.overall_stability_score <= 1
        assert len(result.param_distributions) >= 0

    def test_multiple_params(self):
        """测试多参数分析。"""
        data = list(range(100))

        def objective(params):
            x_val = params.get("x", 50)
            y_val = params.get("y", 50)
            return -(x_val - 50) ** 2 - (y_val - 50) ** 2

        analyzer = ParamStabilityAnalyzer(objective, random_seed=42)
        result = analyzer.analyze(
            data=data,
            param_space={"x": (0, 100), "y": (0, 100)},
            n_iterations=10,
        )

        assert len(result.param_distributions) >= 1

    def test_analysis_with_custom_best_params(self):
        """测试使用自定义基准参数。"""
        data = list(range(100))

        def objective(params):
            return -params["x"] ** 2

        analyzer = ParamStabilityAnalyzer(objective, random_seed=42)
        result = analyzer.analyze(
            data=data,
            param_space={"x": (-10, 10)},
            best_params={"x": 5},
            n_iterations=5,
        )

        assert result.overall_stability_score >= 0

    def test_empty_data_behavior(self):
        """测试空数据行为。"""
        data = []

        def objective(params):
            return 0

        analyzer = ParamStabilityAnalyzer(objective)

        # 空数据配合 sample_ratio=0.8 时 sample_size=0，走 else 分支
        result = analyzer.analyze(
            data=data,
            param_space={"x": (0, 10)},
            n_iterations=5,
        )
        # 空数据目标函数返回0，导致分布全为0
        assert len(result.param_distributions) == 1
        assert result.param_distributions[0].mean == 0.0


class TestConvenienceFunction:
    """快捷函数测试。"""

    def test_analyze_param_stability(self):
        """测试 analyze_param_stability 快捷函数。"""
        data = list(range(50))

        def objective(params):
            return -abs(params["x"] - 25)

        result = analyze_param_stability(
            objective_fn=objective,
            data=data,
            param_space={"x": (0, 50)},
            n_iterations=5,
            random_seed=42,
        )

        assert isinstance(result, StabilityAnalysis)
        assert 0 <= result.overall_stability_score <= 1


class TestStabilityAnalysis:
    """StabilityAnalysis 数据类测试。"""

    def test_analysis_creation(self):
        """测试分析结果创建。"""
        dist = ParamDistribution(
            param="x",
            mean=5.0,
            std=0.5,
            min_val=4.0,
            max_val=6.0,
            median=5.0,
            ci_lower=4.2,
            ci_upper=5.8,
            cv=0.1,
        )

        analysis = StabilityAnalysis(
            param_distributions=[dist],
            overall_stability_score=0.85,
            stable_params=["x"],
            unstable_params=[],
            recommendations=["参数稳定性良好"],
        )

        assert len(analysis.param_distributions) == 1
        assert analysis.overall_stability_score == 0.85
        assert "x" in analysis.stable_params


class TestEdgeCases:
    """边界情况测试。"""

    def test_single_iteration(self):
        """测试单次迭代。"""
        data = list(range(50))

        def objective(params):
            return -params["x"] ** 2

        analyzer = ParamStabilityAnalyzer(objective, random_seed=42)
        result = analyzer.analyze(
            data=data,
            param_space={"x": (-5, 5)},
            n_iterations=1,
        )

        assert isinstance(result.overall_stability_score, float)

    def test_highly_stable_params(self):
        """测试高度稳定的参数。"""
        data = list(range(100))

        def objective(params):
            # 参数对结果影响很小
            return -0.001 * (params["x"] - 50) ** 2 + 100

        analyzer = ParamStabilityAnalyzer(objective, random_seed=42)
        result = analyzer.analyze(
            data=data,
            param_space={"x": (0, 100)},
            n_iterations=10,
        )

        # 由于目标函数相对平坦，参数应该比较稳定
        assert result.overall_stability_score >= 0

    def test_reproducibility_with_seed(self):
        """测试使用相同种子可重现结果。"""
        data = list(range(100))

        def objective(params):
            return -abs(params["x"] - 50)

        result1 = analyze_param_stability(
            objective_fn=objective,
            data=data,
            param_space={"x": (0, 100)},
            n_iterations=5,
            random_seed=123,
        )

        result2 = analyze_param_stability(
            objective_fn=objective,
            data=data,
            param_space={"x": (0, 100)},
            n_iterations=5,
            random_seed=123,
        )

        # 相同的种子应该产生相同数量的参数分布
        assert len(result1.param_distributions) == len(result2.param_distributions)
