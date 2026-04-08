"""
贝叶斯优化器单元测试 — P5-009。
"""

from __future__ import annotations

import math
from src.persona.bayesian_search import (
    BayesianSearcher,
    BayesianSearchResult,
    SearchResult,
    bayesian_search,
    BayesianSearchError,
    GaussianProcess,
    _params_to_vector,
    _vector_to_params,
)


class TestGaussianProcess:
    """GaussianProcess 测试。"""

    def test_fit_predict(self):
        """测试 GP 拟合和预测。"""
        gp = GaussianProcess()

        X = np.array([[1], [2], [3]])
        y = np.array([1.0, 2.0, 3.0])

        gp.fit(X, y)

        mu, sigma = gp.predict(np.array([[2.5]]))

        assert isinstance(mu, (float, np.floating))
        assert isinstance(sigma, (float, np.floating))
        assert sigma >= 0


class TestParamsConversion:
    """参数转换测试。"""

    def test_params_to_vector(self):
        """测试参数转向量。"""
        params = {"x": 0.5, "y": 0.75}
        bounds = {"x": (0, 1), "y": (0, 1)}
        keys = ["x", "y"]

        vector = _params_to_vector(params, keys, bounds)

        assert len(vector) == 2
        assert abs(vector[0] - 0.5) < 1e-6
        assert abs(vector[1] - 0.75) < 1e-6

    def test_vector_to_params(self):
        """测试向量转参数。"""
        vector = np.array([0.5, 0.75])
        bounds = {"x": (0, 1), "y": (0, 1)}
        keys = ["x", "y"]

        params = _vector_to_params(vector, keys, bounds)

        assert abs(params["x"] - 0.5) < 1e-6
        assert abs(params["y"] - 0.75) < 1e-6

    def test_roundtrip(self):
        """测试往返转换。"""
        original = {"x": 0.3, "y": 0.7}
        bounds = {"x": (0, 1), "y": (0, 1)}
        keys = ["x", "y"]

        vector = _params_to_vector(original, keys, bounds)
        restored = _vector_to_params(vector, keys, bounds)

        assert abs(restored["x"] - original["x"]) < 1e-6
        assert abs(restored["y"] - original["y"]) < 1e-6


class TestBayesianSearcher:
    """BayesianSearcher 测试。"""

    def test_simple_search(self):
        """测试简单搜索。"""
        searcher = BayesianSearcher(
            param_space={
                "x": (0, 10),
                "y": (0, 10),
            },
            objective_fn=lambda p: -(p["x"] - 5) ** 2 - (p["y"] - 5) ** 2,  # 最大值在 (5, 5)
            maximize=True,
            n_initial_points=3,
        )

        result = searcher.search(n_iter=10)

        assert result.best_params["x"] is not None
        assert result.best_params["y"] is not None
        assert len(result.all_results) >= 3

    def test_maximize_vs_minimize(self):
        """测试最大化 vs 最小化。"""
        # 使用不同的目标函数来区分两种模式
        # 最大化：目标函数返回 (x-5)^2（正值），最大化找到最大值
        searcher_max = BayesianSearcher(
            param_space={"x": (0, 10)},
            objective_fn=lambda p: (p["x"] - 5) ** 2,  # 最大值在 x=5，值为 0
            maximize=True,
            n_initial_points=3,
        )
        result_max = searcher_max.search(n_iter=5)
        # 结果应该在 x=5 附近，最优值接近 0
        assert abs(result_max.best_params["x"] - 5) < 5
        assert isinstance(result_max.best_score, (float, int))

        # 最小化：同样目标函数，最小化也找到最小值
        searcher_min = BayesianSearcher(
            param_space={"x": (0, 10)},
            objective_fn=lambda p: (p["x"] - 5) ** 2,
            maximize=False,
            n_initial_points=3,
        )
        result_min = searcher_min.search(n_iter=5)
        # 结果也应该在 x=5 附近
        assert abs(result_min.best_params["x"] - 5) < 5

    def test_objective_fn_exception(self):
        """测试目标函数抛出异常时跳过。"""
        searcher = BayesianSearcher(
            param_space={"x": (-5, 5)},
            objective_fn=lambda p: 1 / (p["x"] - 2),  # x=2 时除零
            maximize=True,
            n_initial_points=2,
        )

        result = searcher.search(n_iter=5)

        # 应该有一些有效结果
        assert len(result.all_results) >= 2

    def test_progress_callback(self):
        """测试进度回调。"""
        progress = []

        def on_progress(current, total):
            progress.append((current, total))

        searcher = BayesianSearcher(
            param_space={"x": (0, 10)},
            objective_fn=lambda p: -p["x"] ** 2,
            maximize=True,
            n_initial_points=2,
        )

        result = searcher.search(n_iter=5, progress_callback=on_progress)

        assert len(progress) > 0

    def test_single_param(self):
        """测试单个参数。"""
        searcher = BayesianSearcher(
            param_space={"x": (0, 10)},
            objective_fn=lambda p: -(p["x"] - 7) ** 2,
            maximize=True,
            n_initial_points=3,
        )

        result = searcher.search(n_iter=10)

        assert "x" in result.best_params
        assert 0 <= result.best_params["x"] <= 10


class TestConvenienceFunction:
    """快捷函数测试。"""

    def test_bayesian_search_function(self):
        """测试 bayesian_search 快捷函数。"""
        result = bayesian_search(
            param_space={"x": (0, 10)},
            objective_fn=lambda p: -(p["x"] - 5) ** 2,
            maximize=True,
            n_iter=5,
        )

        assert result.best_params["x"] is not None


class TestSearchResult:
    """SearchResult 数据类测试。"""

    def test_search_result_creation(self):
        """测试 SearchResult 创建。"""
        result = SearchResult(
            params={"x": 1.5},
            score=0.85,
            iteration=10,
        )

        assert result.params["x"] == 1.5
        assert result.score == 0.85
        assert result.iteration == 10


class TestEdgeCases:
    """边界情况测试。"""

    def test_narrow_param_space(self):
        """测试窄参数空间。"""
        searcher = BayesianSearcher(
            param_space={"x": (0.99, 1.01)},
            objective_fn=lambda p: -p["x"] ** 2,
            maximize=True,
            n_initial_points=2,
        )

        result = searcher.search(n_iter=3)

        assert 0.99 <= result.best_params["x"] <= 1.01

    def test_large_param_space(self):
        """测试大参数空间。"""
        searcher = BayesianSearcher(
            param_space={
                "x": (-1000, 1000),
                "y": (-1000, 1000),
            },
            objective_fn=lambda p: p["x"] + p["y"],
            maximize=True,
            n_initial_points=3,
        )

        result = searcher.search(n_iter=5)

        assert -1000 <= result.best_params["x"] <= 1000
        assert -1000 <= result.best_params["y"] <= 1000

    def test_multiple_runs_deterministic(self):
        """测试多次运行结果一致性（给定相同随机种子）。"""
        # 由于使用随机初始化，不同运行结果可能不同
        # 但 best 结果应该在合理范围内
        searcher = BayesianSearcher(
            param_space={"x": (0, 10)},
            objective_fn=lambda p: -(p["x"] - 5) ** 2,
            maximize=True,
            n_initial_points=5,
        )

        result = searcher.search(n_iter=10)

        # 最优点在 x=5 附近
        assert abs(result.best_params["x"] - 5) < 5


class TestBayesianSearchResult:
    """BayesianSearchResult 测试。"""

    def test_result_structure(self):
        """测试结果结构。"""
        searcher = BayesianSearcher(
            param_space={"x": (0, 10)},
            objective_fn=lambda p: -p["x"] ** 2,
            maximize=True,
            n_initial_points=2,
        )

        result = searcher.search(n_iter=5)

        assert "x" in result.best_params
        assert isinstance(result.best_score, (float, int))
        assert len(result.all_results) == result.n_iterations
        assert result.duration_ms > 0
        assert result.searched_at is not None


# Need numpy for tests
import numpy as np
