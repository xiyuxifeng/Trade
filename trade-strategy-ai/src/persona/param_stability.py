"""
参数稳定性分析 — P5-012。

分析参数在不同数据子集上的稳定性，检测参数是否过度依赖特定市场环境。

功能：
1. Bootstrap 分析
2. 参数置信区间估计
3. 参数稳定性评分
4. 敏感性排序
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
import math
import random


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ParamDistribution:
    """单个参数的分布统计。"""
    param: str
    mean: float
    std: float
    min_val: float
    max_val: float
    median: float
    ci_lower: float  # 95% 置信区间下限
    ci_upper: float  # 95% 置信区间上限
    cv: float  # 变异系数


@dataclass
class StabilityAnalysis:
    """参数稳定性分析结果。"""
    param_distributions: list[ParamDistribution]
    overall_stability_score: float  # 0-1
    stable_params: list[str]  # 稳定的参数名
    unstable_params: list[str]  # 不稳定的参数名
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Stability Analyzer
# ---------------------------------------------------------------------------

class ParamStabilityAnalyzer:
    """参数稳定性分析器。

    使用 Bootstrap 方法分析参数在不同数据子集上的稳定性。

    用法：
        analyzer = ParamStabilityAnalyzer(objective_fn)
        result = analyzer.analyze(
            data=price_series,
            param_space={"stop_loss": (0.01, 0.10)},
            n_iterations=50,
        )
        for dist in result.param_distributions:
            print(f"{dist.param}: CV={dist.cv:.2f}, stability={dist.std/dist.mean:.2f}")
    """

    # 稳定性阈值
    STABILITY_CV_THRESHOLD = 0.20  # CV 超过 20% 为不稳定
    HIGH_STABILITY_SCORE = 0.80

    def __init__(
        self,
        objective_fn: Callable[[dict[str, Any]], float],
        *,
        random_seed: int | None = None,
    ):
        """初始化分析器。

        Args:
            objective_fn: 目标函数
            random_seed: 随机种子（用于可重复性）
        """
        self._objective_fn = objective_fn
        if random_seed is not None:
            random.seed(random_seed)

    def analyze(
        self,
        data: list[Any],
        param_space: dict[str, tuple[float, float]],
        best_params: dict[str, Any] | None = None,
        *,
        n_iterations: int = 50,
        sample_ratio: float = 0.8,
    ) -> StabilityAnalysis:
        """执行参数稳定性分析。

        Args:
            data: 数据集
            param_space: 参数空间
            best_params: 基准参数（用于计算相对稳定性）
            n_iterations: Bootstrap 迭代次数
            sample_ratio: 每次采样的数据比例

        Returns:
            StabilityAnalysis
        """
        from src.persona.grid_search import GridSearcher

        # 初始化最佳参数（如果未提供）
        if best_params is None:
            searcher = GridSearcher(
                param_space={k: list(v) for k, v in param_space.items()},
                objective_fn=self._objective_fn,
            )
            best_params = searcher.search().best_params

        # 收集每次迭代的参数值
        param_values: dict[str, list[float]] = {k: [] for k in param_space.keys()}

        for _ in range(n_iterations):
            # Bootstrap 采样
            sample_size = int(len(data) * sample_ratio)
            sample_data = random.sample(data, sample_size) if sample_size < len(data) else data

            # 在采样数据上搜索最优参数
            searcher = GridSearcher(
                param_space={k: list(v) for k, v in param_space.items()},
                objective_fn=lambda p, d=sample_data: self._objective_fn({**p, "data": d}),
            )

            try:
                result = searcher.search()
                for key in param_values.keys():
                    if key in result.best_params:
                        param_values[key].append(result.best_params[key])
            except Exception:
                continue

        if not param_values or all(not v for v in param_values.values()):
            raise ValueError("Not enough valid iterations for stability analysis")

        # 计算分布统计
        distributions = []
        for param, values in param_values.items():
            if not values:
                continue

            dist = self._calculate_distribution(param, values)
            distributions.append(dist)

        # 计算总体稳定性评分
        overall_score = self._calculate_overall_score(distributions)

        # 分类稳定/不稳定参数
        stable_params = [d.param for d in distributions if d.cv <= self.STABILITY_CV_THRESHOLD]
        unstable_params = [d.param for d in distributions if d.cv > self.STABILITY_CV_THRESHOLD]

        # 生成建议
        recommendations = self._generate_recommendations(distributions, overall_score)

        return StabilityAnalysis(
            param_distributions=distributions,
            overall_stability_score=overall_score,
            stable_params=stable_params,
            unstable_params=unstable_params,
            recommendations=recommendations,
        )

    def _calculate_distribution(self, param: str, values: list[float]) -> ParamDistribution:
        """计算参数的分布统计。"""
        if not values:
            raise ValueError(f"No values for param {param}")

        n = len(values)
        mean_val = sum(values) / n
        variance = sum((v - mean_val) ** 2 for v in values) / n
        std_val = math.sqrt(variance) if variance > 0 else 0.0

        sorted_values = sorted(values)
        min_val = sorted_values[0]
        max_val = sorted_values[-1]

        # 中位数
        mid = n // 2
        if n % 2 == 0:
            median = (sorted_values[mid - 1] + sorted_values[mid]) / 2
        else:
            median = sorted_values[mid]

        # 95% 置信区间（使用百分位数）
        ci_lower = sorted_values[max(0, int(n * 0.025))]
        ci_upper = sorted_values[min(n - 1, int(n * 0.975))]

        # 变异系数
        cv = abs(std_val / mean_val) if mean_val != 0 else 0.0

        return ParamDistribution(
            param=param,
            mean=mean_val,
            std=std_val,
            min_val=min_val,
            max_val=max_val,
            median=median,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            cv=cv,
        )

    def _calculate_overall_score(self, distributions: list[ParamDistribution]) -> float:
        """计算总体稳定性评分。"""
        if not distributions:
            return 0.0

        # 基于变异系数的稳定性评分
        scores = []
        for dist in distributions:
            # CV 越低越稳定，0-20% 区间映射到 1-0
            if dist.cv <= self.STABILITY_CV_THRESHOLD:
                score = 1.0
            else:
                # 超过阈值的，评分快速下降
                score = max(0, 1 - (dist.cv - self.STABILITY_CV_THRESHOLD) / self.STABILITY_CV_THRESHOLD)
            scores.append(score)

        return sum(scores) / len(scores)

    def _generate_recommendations(
        self,
        distributions: list[ParamDistribution],
        overall_score: float,
    ) -> list[str]:
        """生成建议。"""
        recommendations = []

        if overall_score < self.HIGH_STABILITY_SCORE:
            recommendations.append("参数稳定性较低，建议简化参数空间或增加数据量")

        for dist in distributions:
            if dist.cv > self.STABILITY_CV_THRESHOLD:
                recommendations.append(
                    f"参数 {dist.param} 变异系数较高 (CV={dist.cv:.2f})，"
                    f"建议检查是否过度依赖特定市场环境"
                )

        if all(d.cv < 0.1 for d in distributions if d.mean != 0):
            recommendations.append("所有参数稳定性良好")

        if not recommendations:
            recommendations.append("参数稳定性处于可接受范围")

        return recommendations


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def analyze_param_stability(
    objective_fn: Callable[[dict[str, Any]], float],
    data: list[Any],
    param_space: dict[str, tuple[float, float]],
    *,
    n_iterations: int = 50,
    random_seed: int | None = None,
) -> StabilityAnalysis:
    """快捷函数：分析参数稳定性。"""
    analyzer = ParamStabilityAnalyzer(
        objective_fn,
        random_seed=random_seed,
    )
    return analyzer.analyze(
        data,
        param_space,
        n_iterations=n_iterations,
    )
