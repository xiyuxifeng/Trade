"""
参数扫描与对比 — P5-010。

对比不同优化器的结果，分析参数敏感性和性能差异。

功能：
1. 优化结果对比（网格搜索 vs 贝叶斯）
2. 参数敏感性分析（Sobol 指数、单因素分析）
3. Walk Forward 分析（时序数据上的过拟合风险）
4. 对比报告生成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from src.persona.grid_search import GridSearchResult
    from src.persona.bayesian_search import BayesianSearchResult


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ComparisonResult:
    """两个优化结果的对比。"""
    searcher_a_name: str
    searcher_b_name: str
    a_best_score: float
    b_best_score: float
    a_best_params: dict[str, Any]
    b_best_params: dict[str, Any]
    score_diff: float  # a - b
    score_diff_pct: float  # (a - b) / b * 100
    winner: str  # "a" / "b" / "tie"


@dataclass
class SensitivityResult:
    """参数敏感性分析结果。"""
    param: str
    impact_score: float  # 参数变化对输出的影响程度
    optimal_value: Any
    variation_range: tuple[Any, Any]
    monotonic: bool | None  # 是否单调


@dataclass
class WalkForwardResult:
    """Walk Forward 分析结果。"""
    window_size: int
    n_windows: int
    in_sample_scores: list[float]
    out_of_sample_scores: list[float]
    degradation: float  # OOS 相对 IIS 的性能衰减
    degradation_pct: float
    is_stable: bool  # 衰减在容忍范围内
    avg_in_sample: float
    avg_out_of_sample: float


@dataclass
class AnalysisReport:
    """完整分析报告。"""
    comparison: ComparisonResult | None
    sensitivity: list[SensitivityResult]
    walk_forward: WalkForwardResult | None
    generated_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Optimization Comparator
# ---------------------------------------------------------------------------

class OptimizationComparator:
    """优化器结果对比器。

    对比不同优化器的最优结果，分析参数差异和性能差异。

    用法：
        comparator = OptimizationComparator()
        comparison = comparator.compare(
            name_a="GridSearch",
            result_a=grid_result,
            name_b="Bayesian",
            result_b=bayesian_result,
        )
        print(f"Winner: {comparison.winner}")
    """

    def compare(
        self,
        name_a: str,
        result_a: GridSearchResult | BayesianSearchResult,
        name_b: str,
        result_b: GridSearchResult | BayesianSearchResult,
    ) -> ComparisonResult:
        """对比两个优化结果。

        Args:
            name_a: 优化器 A 名称
            result_a: 优化器 A 结果
            name_b: 优化器 B 名称
            result_b: 优化器 B 结果

        Returns:
            ComparisonResult
        """
        a_best_score = self._get_best_score(result_a)
        b_best_score = self._get_best_score(result_b)

        a_best_params = self._get_best_params(result_a)
        b_best_params = self._get_best_params(result_b)

        score_diff = a_best_score - b_best_score
        score_diff_pct = (score_diff / abs(b_best_score) * 100) if b_best_score != 0 else 0

        if abs(score_diff) < 1e-10:
            winner = "tie"
        elif score_diff > 0:
            winner = "a"
        else:
            winner = "b"

        return ComparisonResult(
            searcher_a_name=name_a,
            searcher_b_name=name_b,
            a_best_score=a_best_score,
            b_best_score=b_best_score,
            a_best_params=a_best_params,
            b_best_params=b_best_params,
            score_diff=score_diff,
            score_diff_pct=score_diff_pct,
            winner=winner,
        )

    def _get_best_score(self, result: "GridSearchResult | BayesianSearchResult") -> float:
        # 两种结果类型都有 best_score 属性
        return result.best_score

    def _get_best_params(self, result: "GridSearchResult | BayesianSearchResult") -> dict[str, Any]:
        # 两种结果类型都有 best_params 属性
        return result.best_params


# ---------------------------------------------------------------------------
# Sensitivity Analyzer
# ---------------------------------------------------------------------------

class SensitivityAnalyzer:
    """参数敏感性分析器。

    分析每个参数对目标函数的影响程度。

    用法：
        analyzer = SensitivityAnalyzer(objective_fn)
        results = analyzer.analyze(param_space, best_params, n_samples=20)
        for r in results:
            print(f"{r.param}: impact={r.impact_score:.3f}")
    """

    def __init__(self, objective_fn: Callable[[dict[str, Any]], float]):
        self._objective_fn = objective_fn

    def analyze(
        self,
        param_space: dict[str, tuple[float, float]],
        baseline_params: dict[str, Any],
        *,
        n_samples: int = 20,
    ) -> list[SensitivityResult]:
        """分析每个参数的敏感性。

        Args:
            param_space: 参数空间
            baseline_params: 基准参数（通常是最佳参数）
            n_samples: 采样点数

        Returns:
            敏感性分析结果列表
        """
        results = []

        for param_name, (low, high) in param_space.items():
            result = self._analyze_single_param(
                param_name, low, high, baseline_params, n_samples
            )
            results.append(result)

        # 按影响程度排序
        results.sort(key=lambda r: r.impact_score, reverse=True)
        return results

    def _analyze_single_param(
        self,
        param_name: str,
        low: float,
        high: float,
        baseline_params: dict[str, Any],
        n_samples: int,
    ) -> SensitivityResult:
        """分析单个参数的敏感性。"""
        baseline_score = self._objective_fn(baseline_params)

        scores = []
        values = []
        for i in range(n_samples):
            t = i / (n_samples - 1) if n_samples > 1 else 0
            value = low + t * (high - low)
            values.append(value)

            test_params = dict(baseline_params)
            test_params[param_name] = value
            try:
                score = self._objective_fn(test_params)
                scores.append(score)
            except Exception:
                scores.append(float('-inf'))

        # 计算影响分数（标准差）
        if scores:
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            impact_score = math.sqrt(variance)
        else:
            impact_score = 0.0

        # 检查单调性
        monotonic = None
        if len(scores) >= 3:
            increasing = all(scores[i] <= scores[i + 1] for i in range(len(scores) - 1))
            decreasing = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
            if increasing or decreasing:
                monotonic = increasing

        # 找到最优值
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        optimal_value = values[best_idx]

        return SensitivityResult(
            param=param_name,
            impact_score=impact_score,
            optimal_value=optimal_value,
            variation_range=(values[0], values[-1]),
            monotonic=monotonic,
        )


# ---------------------------------------------------------------------------
# Walk Forward Analyzer
# ---------------------------------------------------------------------------

class WalkForwardAnalyzer:
    """Walk Forward 分析器。

    用于检测时序数据上的过拟合风险。

    用法：
        analyzer = WalkForwardAnalyzer(objective_fn)
        result = analyzer.analyze(
            time_series_data,
            window_size=30,
            train_ratio=0.7,
        )
        print(f"Degradation: {result.degradation_pct:.1f}%")
    """

    def __init__(self, objective_fn: Callable[[dict[str, Any]], float]):
        self._objective_fn = objective_fn

    def analyze(
        self,
        data: list[Any],
        param_space: dict[str, tuple[float, float]],
        window_size: int,
        *,
        train_ratio: float = 0.7,
        step_size: int | None = None,
    ) -> WalkForwardResult:
        """执行 Walk Forward 分析。

        Args:
            data: 时序数据
            param_space: 参数空间
            window_size: 窗口大小
            train_ratio: 训练数据比例
            step_size: 步长（默认 window_size）

        Returns:
            WalkForwardResult
        """
        if step_size is None:
            step_size = window_size

        in_sample_scores = []
        out_of_sample_scores = []

        n_windows = 0
        for start in range(0, len(data) - window_size, step_size):
            end = start + window_size
            train_data = data[start:int(start + window_size * train_ratio)]
            test_data = data[int(start + window_size * train_ratio):end]

            if len(train_data) < 5 or len(test_data) < 2:
                continue

            # 在训练数据上搜索最优参数
            searcher = _create_grid_searcher(param_space, self._objective_fn)
            train_result = searcher.search()

            # 评估在测试数据上的表现
            test_params = train_result.best_params
            try:
                oos_score = self._objective_fn({**test_params, "data": test_data})
                out_of_sample_scores.append(oos_score)
            except Exception:
                pass

            in_sample_scores.append(train_result.best_score)
            n_windows += 1

        if not in_sample_scores:
            raise ValueError("Not enough data for Walk Forward analysis")

        avg_in_sample = sum(in_sample_scores) / len(in_sample_scores)
        avg_oos = sum(out_of_sample_scores) / len(out_of_sample_scores) if out_of_sample_scores else 0

        degradation = avg_in_sample - avg_oos
        degradation_pct = (degradation / abs(avg_in_sample) * 100) if avg_in_sample != 0 else 0

        # 稳定性判断：衰减在 20% 以内视为稳定
        is_stable = abs(degradation_pct) < 20

        return WalkForwardResult(
            window_size=window_size,
            n_windows=n_windows,
            in_sample_scores=in_sample_scores,
            out_of_sample_scores=out_of_sample_scores,
            degradation=degradation,
            degradation_pct=degradation_pct,
            is_stable=is_stable,
            avg_in_sample=avg_in_sample,
            avg_out_of_sample=avg_oos,
        )


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

class AnalysisReportGenerator:
    """分析报告生成器。"""

    def generate(self, report: AnalysisReport) -> str:
        """生成文本格式的分析报告。"""
        lines = [
            "=" * 60,
            "参数优化分析报告",
            "=" * 60,
            f"生成时间: {report.generated_at.isoformat()}",
            "",
        ]

        # 对比结果
        if report.comparison:
            c = report.comparison
            lines.extend([
                "-" * 60,
                "优化器对比",
                "-" * 60,
                f"优化器 A: {c.searcher_a_name}",
                f"  最优分数: {c.a_best_score:.4f}",
                f"  最优参数: {c.a_best_params}",
                f"优化器 B: {c.searcher_b_name}",
                f"  最优分数: {c.b_best_score:.4f}",
                f"  最优参数: {c.b_best_params}",
                f"胜者: {c.winner.upper()}",
                f"分数差异: {c.score_diff:.4f} ({c.score_diff_pct:.2f}%)",
                "",
            ])

        # 敏感性分析
        if report.sensitivity:
            lines.extend([
                "-" * 60,
                "参数敏感性分析",
                "-" * 60,
                f"{'参数':<20} {'影响分数':<12} {'最优值':<12} {'单调性':<8}",
                "-" * 52,
            ])
            for r in report.sensitivity:
                mono = "是" if r.monotonic else ("否" if r.monotonic is False else "-")
                lines.append(
                    f"{r.param:<20} {r.impact_score:<12.4f} {str(r.optimal_value):<12} {mono:<8}"
                )
            lines.append("")

        # Walk Forward 分析
        if report.walk_forward:
            wf = report.walk_forward
            lines.extend([
                "-" * 60,
                "Walk Forward 分析",
                "-" * 60,
                f"窗口大小: {wf.window_size}",
                f"窗口数量: {wf.n_windows}",
                f"样本内平均分: {wf.avg_in_sample:.4f}",
                f"样本外平均分: {wf.avg_out_of_sample:.4f}",
                f"性能衰减: {wf.degradation:.4f} ({wf.degradation_pct:.2f}%)",
                f"稳定性: {'稳定' if wf.is_stable else '不稳定'}",
                "",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def _create_grid_searcher(
    param_space: dict[str, list[Any]],
    objective_fn: Callable[[dict[str, Any]], float],
) -> "GridSearcher":
    """创建网格搜索器（避免循环导入）。"""
    from src.persona.grid_search import GridSearcher
    return GridSearcher(param_space=param_space, objective_fn=objective_fn)


def compare_optimizers(
    name_a: str,
    result_a: GridSearchResult | BayesianSearchResult,
    name_b: str,
    result_b: GridSearchResult | BayesianSearchResult,
) -> ComparisonResult:
    """快捷函数：对比两个优化结果。"""
    comparator = OptimizationComparator()
    return comparator.compare(name_a, result_a, name_b, result_b)


def analyze_sensitivity(
    objective_fn: Callable[[dict[str, Any]], float],
    param_space: dict[str, tuple[float, float]],
    baseline_params: dict[str, Any],
    *,
    n_samples: int = 20,
) -> list[SensitivityResult]:
    """快捷函数：分析参数敏感性。"""
    analyzer = SensitivityAnalyzer(objective_fn)
    return analyzer.analyze(param_space, baseline_params, n_samples=n_samples)
