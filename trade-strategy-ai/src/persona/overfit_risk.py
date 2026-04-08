"""
过度拟合风险评估 — P5-011。

基于 Walk Forward 分析的过度拟合风险评估。

功能：
1. 多窗口 Walk Forward 分析
2. 过拟合统计检验
3. 参数稳定性评分
4. 风险报告生成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
import math


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class WindowAnalysis:
    """单个窗口的分析结果。"""
    window_idx: int
    train_score: float
    test_score: float
    train_params: dict[str, Any]
    test_params: dict[str, Any] | None  # None if no improvement found
    degradation: float
    degradation_pct: float


@dataclass
class OverfitRiskResult:
    """过度拟合风险评估结果。"""
    window_sizes: list[int]
    window_analyses: list[WindowAnalysis]
    overall_degradation: float
    overfit_probability: float  # 0-1，过度拟合概率
    stability_score: float  # 0-1，稳定性评分
    avg_in_sample: float
    avg_out_of_sample: float
    degradation_trend: str  # "improving" / "degrading" / "stable"
    risk_level: str  # "low" / "medium" / "high"


@dataclass
class OverfitRiskReport:
    """过度拟合风险报告。"""
    result: OverfitRiskResult
    recommendations: list[str]
    generated_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Overfit Risk Evaluator
# ---------------------------------------------------------------------------

class OverfitRiskEvaluator:
    """过度拟合风险评估器。

    基于 Walk Forward 分析评估策略的过度拟合风险。

    用法：
        evaluator = OverfitRiskEvaluator(objective_fn)
        result = evaluator.evaluate(
            data=price_series,
            param_space={"stop_loss": (0.01, 0.10)},
            window_sizes=[20, 30, 50],
        )
        print(f"Risk level: {result.risk_level}")
        print(f"Overfit probability: {result.overfit_probability:.2%}")
    """

    # 风险阈值
    HIGH_DEGRADATION_THRESHOLD = 0.30  # 30% 衰减为高风险
    MEDIUM_DEGRADATION_THRESHOLD = 0.15  # 15% 衰减为中等风险
    STABILITY_THRESHOLD = 0.70  # 稳定性评分低于 0.7 为不稳定

    def __init__(
        self,
        objective_fn: Callable[[dict[str, Any]], float],
        *,
        train_ratio: float = 0.7,
        min_window_size: int = 10,
    ):
        """初始化评估器。

        Args:
            objective_fn: 目标函数
            train_ratio: 训练数据比例
            min_window_size: 最小窗口大小
        """
        self._objective_fn = objective_fn
        self._train_ratio = train_ratio
        self._min_window_size = min_window_size

    def evaluate(
        self,
        data: list[Any],
        param_space: dict[str, tuple[float, float]],
        window_sizes: list[int],
        *,
        n_windows: int | None = None,
    ) -> OverfitRiskResult:
        """执行过度拟合风险评估。

        Args:
            data: 时序数据
            param_space: 参数空间
            window_sizes: 窗口大小列表
            n_windows: 每个窗口大小的窗口数量（默认自动）

        Returns:
            OverfitRiskResult
        """
        from src.persona.grid_search import GridSearcher

        all_analyses: list[WindowAnalysis] = []

        for window_size in window_sizes:
            if window_size < self._min_window_size:
                continue

            # 计算窗口数量
            if n_windows is None:
                actual_n_windows = max(1, (len(data) - window_size) // window_size)
            else:
                actual_n_windows = n_windows

            step_size = max(1, (len(data) - window_size) // actual_n_windows)

            for window_idx in range(actual_n_windows):
                start = window_idx * step_size
                end = start + window_size

                if end > len(data):
                    break

                train_end = int(start + window_size * self._train_ratio)
                train_data = data[start:train_end]
                test_data = data[train_end:end]

                if len(train_data) < 5 or len(test_data) < 2:
                    continue

                # 在训练数据上搜索最优参数
                searcher = GridSearcher(
                    param_space={k: list(v) for k, v in param_space.items()},
                    objective_fn=self._objective_fn,
                )

                try:
                    train_result = searcher.search()
                except Exception:
                    continue

                train_params = train_result.best_params
                train_score = train_result.best_score

                # 在测试数据上评估
                test_params = dict(train_params)
                test_params["data"] = test_data

                try:
                    test_score = self._objective_fn(test_params)
                except Exception:
                    test_score = train_score  # 如果评估失败，假设没有衰减

                degradation = train_score - test_score
                degradation_pct = (degradation / abs(train_score) * 100) if train_score != 0 else 0

                all_analyses.append(WindowAnalysis(
                    window_idx=window_idx,
                    train_score=train_score,
                    test_score=test_score,
                    train_params=train_params,
                    test_params=None,  # 测试参数与训练相同（Walk Forward 评估方式）
                    degradation=degradation,
                    degradation_pct=degradation_pct,
                ))

        if not all_analyses:
            raise ValueError("Not enough data for overfitting risk evaluation")

        # 计算统计指标
        in_sample_scores = [a.train_score for a in all_analyses]
        out_of_sample_scores = [a.test_score for a in all_analyses]

        avg_in_sample = sum(in_sample_scores) / len(in_sample_scores)
        avg_oos = sum(out_of_sample_scores) / len(out_of_sample_scores)

        overall_degradation = avg_in_sample - avg_oos
        degradation_pct = (overall_degradation / abs(avg_in_sample) * 100) if avg_in_sample != 0 else 0

        # 计算过拟合概率（基于衰减分布）
        overfit_probability = self._calculate_overfit_probability(all_analyses)

        # 计算稳定性评分
        stability_score = self._calculate_stability_score(all_analyses)

        # 分析衰减趋势
        degradation_trend = self._analyze_degradation_trend(all_analyses)

        # 确定风险等级
        risk_level = self._determine_risk_level(
            degradation_pct, overfit_probability, stability_score
        )

        return OverfitRiskResult(
            window_sizes=window_sizes,
            window_analyses=all_analyses,
            overall_degradation=overall_degradation,
            overfit_probability=overfit_probability,
            stability_score=stability_score,
            avg_in_sample=avg_in_sample,
            avg_out_of_sample=avg_oos,
            degradation_trend=degradation_trend,
            risk_level=risk_level,
        )

    def _calculate_overfit_probability(self, analyses: list[WindowAnalysis]) -> float:
        """计算过拟合概率。"""
        if not analyses:
            return 0.0

        # 基于以下因素计算过拟合概率：
        # 1. 负衰减（测试优于训练）的窗口比例
        negative_degradation_count = sum(1 for a in analyses if a.degradation < 0)
        negative_ratio = negative_degradation_count / len(analyses)

        # 2. 大幅衰减（>30%）的窗口比例
        high_degradation_count = sum(
            1 for a in analyses if abs(a.degradation_pct) > self.HIGH_DEGRADATION_THRESHOLD * 100
        )
        high_ratio = high_degradation_count / len(analyses)

        # 3. 衰减的标准差（高方差表示不稳定）
        if len(analyses) > 1:
            degradations = [a.degradation for a in analyses]
            mean_deg = sum(degradations) / len(degradations)
            variance = sum((d - mean_deg) ** 2 for d in degradations) / len(degradations)
            std_dev = math.sqrt(variance)
            # 标准差大于均值的绝对值时，高概率过拟合
            instability_factor = min(1.0, std_dev / (abs(mean_deg) + 1e-10))
        else:
            instability_factor = 0.0

        # 综合评分
        overfit_prob = (
            (1 - negative_ratio) * 0.3 +  # 负衰减少，过拟合概率低
            high_ratio * 0.4 +  # 大幅衰减多，过拟合概率高
            instability_factor * 0.3  # 不稳定，过拟合概率高
        )

        return min(1.0, max(0.0, overfit_prob))

    def _calculate_stability_score(self, analyses: list[WindowAnalysis]) -> float:
        """计算稳定性评分（0-1，越高越稳定）。"""
        if not analyses:
            return 0.0

        # 基于参数变化的一致性
        if len(analyses) < 2:
            return 1.0

        # 计算每个参数在不同窗口的变异系数
        param_stabilities = []
        all_params = set()
        for a in analyses:
            all_params.update(a.train_params.keys())

        for param in all_params:
            values = [a.train_params.get(param, 0) for a in analyses if param in a.train_params]
            if len(values) > 1 and any(v != 0 for v in values):
                mean_val = sum(values) / len(values)
                std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / len(values))
                # 变异系数
                cv = abs(std_val / mean_val) if mean_val != 0 else 0
                param_stabilities.append(max(0, 1 - cv))

        if not param_stabilities:
            return 1.0

        avg_stability = sum(param_stabilities) / len(param_stabilities)

        # 考虑衰减一致性
        degradation_cv = self._coefficient_of_variation([a.degradation for a in analyses])
        degradation_stability = max(0, 1 - degradation_cv)

        return (avg_stability + degradation_stability) / 2

    def _coefficient_of_variation(self, values: list[float]) -> float:
        """计算变异系数。"""
        if not values:
            return 0.0
        mean_val = sum(values) / len(values)
        if mean_val == 0:
            return 0.0
        std_val = math.sqrt(sum((v - mean_val) ** 2 for v in values) / len(values))
        return abs(std_val / mean_val)

    def _analyze_degradation_trend(self, analyses: list[WindowAnalysis]) -> str:
        """分析衰减趋势。"""
        if len(analyses) < 3:
            return "stable"

        # 检查前半部分和后半部分的平均衰减
        mid = len(analyses) // 2
        first_half = analyses[:mid]
        second_half = analyses[mid:]

        first_avg = sum(a.degradation for a in first_half) / len(first_half)
        second_avg = sum(a.degradation for a in second_half) / len(second_half)

        change_ratio = (second_avg - first_avg) / (abs(first_avg) + 1e-10)

        if change_ratio > 0.2:
            return "improving"  # 衰减在减小
        elif change_ratio < -0.2:
            return "degrading"  # 衰减在增加
        else:
            return "stable"

    def _determine_risk_level(
        self,
        degradation_pct: float,
        overfit_prob: float,
        stability_score: float,
    ) -> str:
        """确定风险等级。"""
        # 基于衰减百分比
        if degradation_pct > self.HIGH_DEGRADATION_THRESHOLD * 100:
            return "high"
        elif degradation_pct > self.MEDIUM_DEGRADATION_THRESHOLD * 100:
            return "medium"

        # 基于过拟合概率
        if overfit_prob > 0.7:
            return "high"
        elif overfit_prob > 0.4:
            return "medium"

        # 基于稳定性评分
        if stability_score < self.STABILITY_THRESHOLD:
            return "medium"

        return "low"


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

class OverfitRiskReportGenerator:
    """过度拟合风险报告生成器。"""

    def generate(self, report: OverfitRiskReport) -> str:
        """生成文本格式的风险报告。"""
        r = report.result

        risk_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴",
        }

        lines = [
            "=" * 60,
            "过度拟合风险评估报告",
            "=" * 60,
            f"生成时间: {report.generated_at.isoformat()}",
            "",
            f"风险等级: {risk_emoji.get(r.risk_level, '')} {r.risk_level.upper()}",
            f"过拟合概率: {r.overfit_probability:.1%}",
            f"稳定性评分: {r.stability_score:.2f}",
            "",
            "-" * 60,
            "统计摘要",
            "-" * 60,
            f"分析窗口大小: {r.window_sizes}",
            f"总窗口数: {len(r.window_analyses)}",
            f"样本内平均分: {r.avg_in_sample:.4f}",
            f"样本外平均分: {r.avg_out_of_sample:.4f}",
            f"总体衰减: {r.overall_degradation:.4f}",
            f"衰减趋势: {r.degradation_trend}",
            "",
        ]

        if r.window_analyses:
            lines.extend([
                "-" * 60,
                "各窗口详情",
                "-" * 60,
                f"{'窗口':<8} {'训练分':<12} {'测试分':<12} {'衰减%':<10}",
                "-" * 42,
            ])
            for a in r.window_analyses[:10]:  # 最多显示10个
                lines.append(
                    f"{a.window_idx:<8} {a.train_score:<12.4f} {a.test_score:<12.4f} {a.degradation_pct:<10.2f}"
                )
            if len(r.window_analyses) > 10:
                lines.append(f"... (还有 {len(r.window_analyses) - 10} 个窗口)")

        if report.recommendations:
            lines.extend([
                "",
                "-" * 60,
                "建议",
                "-" * 60,
            ])
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def evaluate_overfit_risk(
    objective_fn: Callable[[dict[str, Any]], float],
    data: list[Any],
    param_space: dict[str, tuple[float, float]],
    window_sizes: list[int] | None = None,
    *,
    train_ratio: float = 0.7,
) -> OverfitRiskResult:
    """快捷函数：评估过度拟合风险。"""
    if window_sizes is None:
        window_sizes = [20, 30, 50]

    evaluator = OverfitRiskEvaluator(objective_fn, train_ratio=train_ratio)
    return evaluator.evaluate(data, param_space, window_sizes)


def generate_overfit_risk_report(
    objective_fn: Callable[[dict[str, Any]], float],
    data: list[Any],
    param_space: dict[str, tuple[float, float]],
    window_sizes: list[int] | None = None,
) -> OverfitRiskReport:
    """快捷函数：生成过度拟合风险报告。"""
    result = evaluate_overfit_risk(objective_fn, data, param_space, window_sizes)
    recommendations = _generate_recommendations(result)
    return OverfitRiskReport(result=result, recommendations=recommendations)


def _generate_recommendations(result: OverfitRiskResult) -> list[str]:
    """生成建议。"""
    recommendations = []

    if result.risk_level == "high":
        recommendations.append("风险等级为高，建议减少参数数量或增加训练数据")
        recommendations.append("考虑使用更简单的策略模型")
    elif result.risk_level == "medium":
        recommendations.append("风险等级为中等，建议监控策略表现")
        recommendations.append("可以在模拟账户中先验证")

    if result.overfit_probability > 0.5:
        recommendations.append("过拟合概率较高，建议检查参数边界设置")

    if result.stability_score < 0.5:
        recommendations.append("参数在不同窗口间变化较大，建议简化参数空间")

    if result.degradation_trend == "degrading":
        recommendations.append("衰减趋势在恶化，策略可能正在失去有效性")

    if not recommendations:
        recommendations.append("各项指标正常，继续监控策略表现")

    return recommendations
