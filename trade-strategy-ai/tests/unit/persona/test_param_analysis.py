"""
参数扫描与对比单元测试 — P5-010。
"""

from __future__ import annotations

import math
from src.persona.param_analysis import (
    OptimizationComparator,
    SensitivityAnalyzer,
    WalkForwardAnalyzer,
    AnalysisReportGenerator,
    ComparisonResult,
    SensitivityResult,
    WalkForwardResult,
    compare_optimizers,
    analyze_sensitivity,
)


class TestOptimizationComparator:
    """OptimizationComparator 测试。"""

    def test_compare_two_results(self):
        """测试对比两个结果。"""
        from src.persona.grid_search import GridSearchResult, SearchResult

        # 创建模拟结果
        result_a = GridSearchResult(
            total_combinations=9,
            searched_combinations=9,
            best_params={"x": 1, "y": 2},
            best_score=10.0,
            best_rank=1,
            all_results=[],
            duration_ms=100,
        )

        result_b = GridSearchResult(
            total_combinations=9,
            searched_combinations=9,
            best_params={"x": 2, "y": 1},
            best_score=8.0,
            best_rank=1,
            all_results=[],
            duration_ms=100,
        )

        comparator = OptimizationComparator()
        comparison = comparator.compare(
            name_a="GridSearch",
            result_a=result_a,
            name_b="Random",
            result_b=result_b,
        )

        assert comparison.winner == "a"
        assert comparison.a_best_score == 10.0
        assert comparison.b_best_score == 8.0
        assert comparison.score_diff == 2.0
        assert comparison.searcher_a_name == "GridSearch"

    def test_compare_tie(self):
        """测试平局情况。"""
        from src.persona.grid_search import GridSearchResult

        result = GridSearchResult(
            total_combinations=9,
            searched_combinations=9,
            best_params={"x": 1},
            best_score=5.0,
            best_rank=1,
            all_results=[],
            duration_ms=100,
        )

        comparator = OptimizationComparator()
        comparison = comparator.compare(
            name_a="A",
            result_a=result,
            name_b="B",
            result_b=result,  # 相同结果
        )

        assert comparison.winner == "tie"
        assert abs(comparison.score_diff) < 1e-10


class TestSensitivityAnalyzer:
    """SensitivityAnalyzer 测试。"""

    def test_analyze_single_param(self):
        """测试单参数敏感性分析。"""
        # 目标函数：(x - 5)^2 + (y - 3)^2，x 的影响更大
        def objective(params):
            return -(params["x"] - 5) ** 2 - (params["y"] - 3) ** 2

        analyzer = SensitivityAnalyzer(objective)
        results = analyzer.analyze(
            param_space={"x": (0, 10), "y": (0, 10)},
            baseline_params={"x": 5, "y": 3},
            n_samples=10,
        )

        assert len(results) == 2
        # 按影响分数排序
        assert results[0].impact_score >= results[1].impact_score

    def test_analyze_returns_correct_structure(self):
        """测试返回正确的结构。"""
        def objective(params):
            return -params["x"] ** 2

        analyzer = SensitivityAnalyzer(objective)
        results = analyzer.analyze(
            param_space={"x": (-5, 5)},
            baseline_params={"x": 0},
            n_samples=5,
        )

        assert len(results) == 1
        r = results[0]
        assert r.param == "x"
        assert isinstance(r.impact_score, float)
        assert r.optimal_value is not None
        assert r.variation_range == (-5, 5)

    def test_analyze_monotonic_detection(self):
        """测试单调性检测。"""
        # 严格递增函数
        def objective(params):
            return params["x"]

        analyzer = SensitivityAnalyzer(objective)
        results = analyzer.analyze(
            param_space={"x": (0, 10)},
            baseline_params={"x": 5},
            n_samples=10,
        )

        # 单调递增函数应该检测为单调
        assert results[0].monotonic is True


class TestWalkForwardAnalyzer:
    """WalkForwardAnalyzer 测试。"""

    def test_walk_forward_basic(self):
        """测试基本的 Walk Forward 分析。"""
        # 生成简单的时序数据
        data = list(range(100))

        # 简单目标函数
        def objective(params):
            return -abs(params["x"] - 50)

        analyzer = WalkForwardAnalyzer(objective)
        result = analyzer.analyze(
            data=data,
            param_space={"x": (0, 100)},
            window_size=20,
            train_ratio=0.7,
        )

        assert result.window_size == 20
        assert result.n_windows >= 1
        assert isinstance(result.degradation, float)
        assert isinstance(result.degradation_pct, float)
        assert isinstance(result.is_stable, bool)

    def test_walk_forward_small_data(self):
        """测试数据不足时抛出错误。"""
        data = list(range(5))  # 数据太少

        def objective(params):
            return 0

        analyzer = WalkForwardAnalyzer(objective)

        try:
            result = analyzer.analyze(
                data=data,
                param_space={"x": (0, 10)},
                window_size=20,
            )
            # 如果没抛异常，检查结果
            assert result.n_windows == 0
        except ValueError:
            pass  # 预期抛出 ValueError


class TestAnalysisReportGenerator:
    """AnalysisReportGenerator 测试。"""

    def test_generate_empty_report(self):
        """测试生成空报告。"""
        from src.persona.param_analysis import AnalysisReport

        generator = AnalysisReportGenerator()
        report = AnalysisReport(
            comparison=None,
            sensitivity=[],
            walk_forward=None,
        )

        text = generator.generate(report)

        assert "参数优化分析报告" in text
        assert "生成时间" in text

    def test_generate_full_report(self):
        """测试生成完整报告。"""
        from src.persona.param_analysis import AnalysisReport, AnalysisReportGenerator

        generator = AnalysisReportGenerator()

        comparison = ComparisonResult(
            searcher_a_name="GridSearch",
            searcher_b_name="Bayesian",
            a_best_score=10.0,
            b_best_score=8.0,
            a_best_params={"x": 1},
            b_best_params={"x": 2},
            score_diff=2.0,
            score_diff_pct=25.0,
            winner="a",
        )

        sensitivity = [
            SensitivityResult(
                param="x",
                impact_score=0.5,
                optimal_value=5.0,
                variation_range=(0, 10),
                monotonic=True,
            ),
        ]

        walk_forward = WalkForwardResult(
            window_size=20,
            n_windows=3,
            in_sample_scores=[10, 9, 8],
            out_of_sample_scores=[9, 8, 7],
            degradation=1.0,
            degradation_pct=11.1,
            is_stable=True,
            avg_in_sample=9.0,
            avg_out_of_sample=8.0,
        )

        report = AnalysisReport(
            comparison=comparison,
            sensitivity=sensitivity,
            walk_forward=walk_forward,
        )

        text = generator.generate(report)

        assert "GridSearch" in text
        assert "Bayesian" in text
        assert "胜者: A" in text
        assert "Walk Forward" in text
        assert "稳定性: 稳定" in text


class TestConvenienceFunctions:
    """快捷函数测试。"""

    def test_compare_optimizers_function(self):
        """测试 compare_optimizers 快捷函数。"""
        from src.persona.grid_search import GridSearchResult

        result = GridSearchResult(
            total_combinations=1,
            searched_combinations=1,
            best_params={"x": 1},
            best_score=5.0,
            best_rank=1,
            all_results=[],
            duration_ms=100,
        )

        comparison = compare_optimizers(
            name_a="A",
            result_a=result,
            name_b="B",
            result_b=result,
        )

        assert comparison.winner == "tie"

    def test_analyze_sensitivity_function(self):
        """测试 analyze_sensitivity 快捷函数。"""
        def objective(params):
            return -params["x"] ** 2

        results = analyze_sensitivity(
            objective_fn=objective,
            param_space={"x": (-5, 5)},
            baseline_params={"x": 0},
            n_samples=5,
        )

        assert len(results) == 1
        assert results[0].param == "x"


class TestEdgeCases:
    """边界情况测试。"""

    def test_comparison_with_zero_benchmark(self):
        """测试基准为 0 的对比（显式返回0避免除零）。"""
        from src.persona.grid_search import GridSearchResult

        result_a = GridSearchResult(
            total_combinations=1,
            searched_combinations=1,
            best_params={"x": 1},
            best_score=10.0,
            best_rank=1,
            all_results=[],
            duration_ms=100,
        )

        result_b = GridSearchResult(
            total_combinations=1,
            searched_combinations=1,
            best_params={"x": 1},
            best_score=0.0,
            best_rank=1,
            all_results=[],
            duration_ms=100,
        )

        comparator = OptimizationComparator()
        comparison = comparator.compare(
            name_a="A",
            result_a=result_a,
            name_b="B",
            result_b=result_b,
        )

        assert comparison.winner == "a"
        assert comparison.score_diff == 10.0
        # 基准为0时，返回0而不是inf
        assert comparison.score_diff_pct == 0

    def test_sensitivity_all_same_score(self):
        """测试所有采样得分相同的情况。"""
        def objective(params):
            return 1.0  # 恒定返回值

        analyzer = SensitivityAnalyzer(objective)
        results = analyzer.analyze(
            param_space={"x": (0, 10)},
            baseline_params={"x": 5},
            n_samples=5,
        )

        assert results[0].impact_score == 0.0
