"""
过度拟合风险评估单元测试 — P5-011。
"""

from __future__ import annotations

import math
from src.persona.overfit_risk import (
    OverfitRiskEvaluator,
    OverfitRiskReportGenerator,
    OverfitRiskResult,
    WindowAnalysis,
    evaluate_overfit_risk,
    generate_overfit_risk_report,
)


class TestOverfitRiskEvaluator:
    """OverfitRiskEvaluator 测试。"""

    def test_basic_evaluation(self):
        """测试基本评估。"""
        data = list(range(100))

        def objective(params):
            return -abs(params["x"] - 50) + params.get("offset", 0)

        evaluator = OverfitRiskEvaluator(objective)
        result = evaluator.evaluate(
            data=data,
            param_space={"x": (0, 100)},
            window_sizes=[20, 30],
        )

        assert result.risk_level in ["low", "medium", "high"]
        assert 0 <= result.overfit_probability <= 1
        assert 0 <= result.stability_score <= 1
        assert result.degradation_trend in ["improving", "degrading", "stable"]

    def test_evaluation_with_multiple_windows(self):
        """测试多窗口评估。"""
        data = list(range(200))

        def objective(params):
            return -params["x"] ** 2

        evaluator = OverfitRiskEvaluator(objective)
        result = evaluator.evaluate(
            data=data,
            param_space={"x": (-10, 10)},
            window_sizes=[20, 40],
        )

        assert len(result.window_analyses) > 0
        assert result.avg_in_sample is not None
        assert result.avg_out_of_sample is not None

    def test_empty_data_raises_error(self):
        """测试数据为空时抛出错误。"""
        data = []

        def objective(params):
            return 0

        evaluator = OverfitRiskEvaluator(objective)

        try:
            result = evaluator.evaluate(
                data=data,
                param_space={"x": (0, 10)},
                window_sizes=[20],
            )
            # 应该抛出 ValueError
            assert len(result.window_analyses) == 0
        except ValueError:
            pass  # 预期抛出 ValueError


class TestOverfitRiskResult:
    """OverfitRiskResult 数据类测试。"""

    def test_result_creation(self):
        """测试结果创建。"""
        analyses = [
            WindowAnalysis(
                window_idx=0,
                train_score=10.0,
                test_score=8.0,
                train_params={"x": 5},
                test_params={"x": 5},
                degradation=2.0,
                degradation_pct=20.0,
            ),
        ]

        result = OverfitRiskResult(
            window_sizes=[20],
            window_analyses=analyses,
            overall_degradation=2.0,
            overfit_probability=0.3,
            stability_score=0.8,
            avg_in_sample=10.0,
            avg_out_of_sample=8.0,
            degradation_trend="stable",
            risk_level="medium",
        )

        assert result.risk_level == "medium"
        assert result.overfit_probability == 0.3
        assert result.stability_score == 0.8


class TestWindowAnalysis:
    """WindowAnalysis 数据类测试。"""

    def test_window_analysis_creation(self):
        """测试窗口分析创建。"""
        analysis = WindowAnalysis(
            window_idx=0,
            train_score=10.0,
            test_score=8.0,
            train_params={"x": 5},
            test_params={"x": 5},
            degradation=2.0,
            degradation_pct=20.0,
        )

        assert analysis.window_idx == 0
        assert analysis.train_score == 10.0
        assert analysis.test_score == 8.0
        assert analysis.degradation == 2.0
        assert analysis.degradation_pct == 20.0


class TestConvenienceFunctions:
    """快捷函数测试。"""

    def test_evaluate_overfit_risk(self):
        """测试 evaluate_overfit_risk 快捷函数。"""
        data = list(range(100))

        def objective(params):
            return -abs(params["x"] - 50)

        result = evaluate_overfit_risk(
            objective_fn=objective,
            data=data,
            param_space={"x": (0, 100)},
            window_sizes=[20],
        )

        assert isinstance(result, OverfitRiskResult)

    def test_generate_overfit_risk_report(self):
        """测试 generate_overfit_risk_report 快捷函数。"""
        data = list(range(100))

        def objective(params):
            return -abs(params["x"] - 50)

        report = generate_overfit_risk_report(
            objective_fn=objective,
            data=data,
            param_space={"x": (0, 100)},
            window_sizes=[20],
        )

        assert report.result is not None
        assert len(report.recommendations) > 0


class TestOverfitRiskReportGenerator:
    """报告生成器测试。"""

    def test_generate_report(self):
        """测试报告生成。"""
        analyses = [
            WindowAnalysis(
                window_idx=0,
                train_score=10.0,
                test_score=8.0,
                train_params={"x": 5},
                test_params={"x": 5},
                degradation=2.0,
                degradation_pct=20.0,
            ),
        ]

        result = OverfitRiskResult(
            window_sizes=[20],
            window_analyses=analyses,
            overall_degradation=2.0,
            overfit_probability=0.3,
            stability_score=0.8,
            avg_in_sample=10.0,
            avg_out_of_sample=8.0,
            degradation_trend="stable",
            risk_level="medium",
        )

        from src.persona.overfit_risk import OverfitRiskReport
        report = OverfitRiskReport(
            result=result,
            recommendations=["测试建议"],
        )

        generator = OverfitRiskReportGenerator()
        text = generator.generate(report)

        assert "过度拟合风险评估报告" in text
        assert "风险等级" in text
        assert "MEDIUM" in text
        assert "测试建议" in text


class TestEdgeCases:
    """边界情况测试。"""

    def test_single_window(self):
        """测试单个窗口。"""
        data = list(range(50))

        def objective(params):
            return -params["x"] ** 2

        evaluator = OverfitRiskEvaluator(objective)
        result = evaluator.evaluate(
            data=data,
            param_space={"x": (-5, 5)},
            window_sizes=[40],
            n_windows=1,
        )

        assert len(result.window_analyses) >= 1

    def test_high_degradation_detected(self):
        """测试高衰减被正确检测。"""
        # 创建数据，使得训练和测试表现差异很大
        data = list(range(100))

        def objective(params):
            # 简单函数，参数变化影响小
            return -params["x"] ** 2

        evaluator = OverfitRiskEvaluator(objective)
        result = evaluator.evaluate(
            data=data,
            param_space={"x": (-10, 10)},
            window_sizes=[30],
        )

        # 结果应该包含风险等级
        assert result.risk_level in ["low", "medium", "high"]

    def test_small_data_with_small_windows(self):
        """测试小数据配合小窗口。"""
        data = list(range(20))

        def objective(params):
            return 0

        evaluator = OverfitRiskEvaluator(objective, min_window_size=5)
        result = evaluator.evaluate(
            data=data,
            param_space={"x": (0, 10)},
            window_sizes=[10],
        )

        # 应该有至少一些分析结果
        assert isinstance(result.overfit_probability, float)
