"""
贝叶斯优化器 — P5-009。

基于高斯过程的贝叶斯优化，用于在昂贵评估函数情况下高效找到最优参数。

用法：
    searcher = BayesianSearcher(
        param_space={
            "stop_loss_pct": (0.01, 0.10),
            "take_profit_pct": (0.03, 0.20),
        },
        objective_fn=lambda params: compute_sharpe_ratio(params),
    )
    result = searcher.search(n_iter=30)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

import numpy as np


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """单次搜索结果。"""
    params: dict[str, Any]
    score: float
    iteration: int


@dataclass
class BayesianSearchResult:
    """贝叶斯优化结果。"""
    best_params: dict[str, Any]
    best_score: float
    all_results: list[SearchResult]
    n_iterations: int
    duration_ms: float
    searched_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BayesianSearchError(Exception):
    """贝叶斯优化错误。"""
    pass


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def _params_to_vector(
    params: dict[str, Any],
    keys: list[str],
    bounds: dict[str, tuple[float, float]],
) -> np.ndarray:
    """将参数字典转换为标准化向量 [0, 1]。"""
    vector = []
    for key in keys:
        val = params[key]
        low, high = bounds[key]
        normalized = (val - low) / (high - low) if high > low else 0.5
        vector.append(normalized)
    return np.array(vector)


def _vector_to_params(
    vector: np.ndarray,
    keys: list[str],
    bounds: dict[str, tuple[float, float]],
) -> dict[str, Any]:
    """将标准化向量转换回参数字典。"""
    params = {}
    for i, key in enumerate(keys):
        low, high = bounds[key]
        val = low + vector[i] * (high - low)
        # 如果原始参数是整数，恢复整数
        orig = keys[i]
        if isinstance(bounds[orig], tuple) and bounds[orig][0] != int(bounds[orig][0]):
            params[key] = val
        else:
            params[key] = val
    return params


def _expected_improvement(
    X: np.ndarray,
    y: np.ndarray,
    X_sample: np.ndarray,
    xi: float = 0.01,
) -> np.ndarray:
    """计算期望改进量（Expected Improvement）。"""
    mu = np.mean(y)
    sigma = np.std(y)

    if sigma < 1e-10:
        return np.zeros(len(X_sample))

    # 标准化
    y_normalized = (y - mu) / sigma
    sample_normalized = (X_sample - mu) / sigma

    diff = sample_normalized - y_normalized.max()
    ei = (diff - xi) * _norm_cdf(diff - xi) + sigma * _norm_pdf(diff - xi)
    return ei


def _norm_cdf(x: np.ndarray) -> np.ndarray:
    """标准正态分布 CDF。"""
    return 0.5 * (1 + np.erf(x / np.sqrt(2)))


def _norm_pdf(x: np.ndarray) -> np.ndarray:
    """标准正态分布 PDF。"""
    return np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)


# ---------------------------------------------------------------------------
# Gaussian Process Surrogate
# ---------------------------------------------------------------------------

class GaussianProcess:
    """简易高斯过程替代模型。"""

    def __init__(self, length_scale: float = 1.0, noise: float = 1e-10):
        self.length_scale = length_scale
        self.noise = noise
        self._X_train: np.ndarray | None = None
        self._y_train: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "GaussianProcess":
        """训练 GP 模型。"""
        self._X_train = np.array(X)
        self._y_train = np.array(y)
        return self

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """预测均值和标准差。"""
        if self._X_train is None or self._y_train is None:
            raise BayesianSearchError("Model not fitted")

        X = np.array(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        # RBF 核
        dists = np.linalg.norm(self._X_train - X, axis=1)
        K = np.exp(-0.5 * (dists / self.length_scale) ** 2)

        # 添加噪声
        var = self.noise ** 2
        K_star = K + var

        # 简单预测：使用核函数加权平均
        weights = K / (K.sum() + 1e-10)
        mu = np.dot(weights, self._y_train)

        # 预测方差
        sigma = np.sqrt(np.abs(1 - K.sum() ** 2 / (K_star.sum() + 1e-10)))

        return mu, sigma


# ---------------------------------------------------------------------------
# Bayesian Optimizer
# ---------------------------------------------------------------------------

class BayesianSearcher:
    """贝叶斯优化器。

    基于高斯过程的贝叶斯优化，用于高效搜索最优参数。

    用法：
        searcher = BayesianSearcher(
            param_space={
                "stop_loss_pct": (0.01, 0.10),
                "take_profit_pct": (0.03, 0.20),
            },
            objective_fn=lambda params: compute_sharpe_ratio(params),
        )
        result = searcher.search(n_iter=30)
        print(f"Best params: {result.best_params}")
        print(f"Best score: {result.best_score}")
    """

    def __init__(
        self,
        param_space: dict[str, tuple[float, float]],
        objective_fn: Callable[[dict[str, Any]], float],
        *,
        maximize: bool = True,
        n_initial_points: int = 5,
        xi: float = 0.01,  # 探索/利用平衡参数
        length_scale: float = 1.0,
    ):
        """初始化贝叶斯搜索器。

        Args:
            param_space: 参数空间，值为 (min, max) 元组
            objective_fn: 目标函数，输入参数，返回评分
            maximize: True 为最大化，False 为最小化
            n_initial_points: 初始随机探索点数
            xi: 探索/利用平衡参数（越大越探索）
            length_scale: GP 核函数长度尺度
        """
        self._param_space = param_space
        self._objective_fn = objective_fn
        self._maximize = maximize
        self._n_initial_points = n_initial_points
        self._xi = xi
        self._length_scale = length_scale
        self._keys = list(param_space.keys())
        self._bounds = param_space

    @property
    def param_space(self) -> dict[str, tuple[float, float]]:
        return self._param_space

    def _random_point(self) -> dict[str, Any]:
        """生成随机参数点。"""
        params = {}
        for key, (low, high) in self._param_space.items():
            params[key] = low + np.random.random() * (high - low)
        return params

    def _generate_candidates(
        self,
        n_candidates: int,
        X_sample: np.ndarray | None,
        gp: GaussianProcess | None,
    ) -> np.ndarray:
        """生成候选点（使用期望改进量）。"""
        candidates = []
        for _ in range(n_candidates):
            params = self._random_point()
            candidates.append(_params_to_vector(params, self._keys, self._bounds))
        candidates = np.array(candidates)

        if gp is not None and X_sample is not None:
            # 使用 EI 选择最佳候选点
            y = gp.predict(X_sample)[0]
            ei = _expected_improvement(X_sample, y, candidates, xi=self._xi)
            # 按 EI 排序
            sorted_indices = np.argsort(ei)[::-1]
            candidates = candidates[sorted_indices[:n_candidates]]

        return candidates

    def search(
        self,
        n_iter: int = 30,
        n_candidates: int = 100,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BayesianSearchResult:
        """执行贝叶斯优化。

        Args:
            n_iter: 总迭代次数
            n_candidates: 每轮候选点数量
            progress_callback: 进度回调函数 (current, total)

        Returns:
            BayesianSearchResult
        """
        start_time = datetime.now()
        results: list[SearchResult] = []
        X_train: list[np.ndarray] = []
        y_train: list[float] = []
        gp = GaussianProcess(length_scale=self._length_scale)

        # 初始随机探索
        for _ in range(self._n_initial_points):
            params = self._random_point()
            try:
                score = self._objective_fn(params)
            except Exception:
                continue

            if not self._maximize:
                score = -score

            results.append(SearchResult(params=params, score=score, iteration=len(results)))
            X_train.append(_params_to_vector(params, self._keys, self._bounds))
            y_train.append(score)

        # 贝叶斯优化迭代
        for iteration in range(len(results), n_iter):
            X_train_arr = np.array(X_train)
            y_train_arr = np.array(y_train)

            # 训练 GP
            gp.fit(X_train_arr, y_train_arr)

            # 生成候选点
            candidates = self._generate_candidates(n_candidates, X_train_arr, gp)

            # 选择最佳候选点
            best_candidate = None
            best_score = float('-inf') if self._maximize else float('inf')

            for candidate in candidates[:10]:  # 只评估前 10 个
                params = _vector_to_params(candidate, self._keys, self._bounds)
                try:
                    score = self._objective_fn(params)
                except Exception:
                    continue

                if not self._maximize:
                    score = -score

                if self._maximize:
                    if score > best_score:
                        best_score = score
                        best_candidate = params
                else:
                    if score < best_score:
                        best_score = score
                        best_candidate = params

            if best_candidate is not None:
                results.append(SearchResult(
                    params=best_candidate,
                    score=best_score,
                    iteration=len(results)
                ))
                X_train.append(_params_to_vector(best_candidate, self._keys, self._bounds))
                y_train.append(best_score)

            if progress_callback:
                progress_callback(len(results), n_iter)

        duration = (datetime.now() - start_time).total_seconds() * 1000

        if not results:
            raise BayesianSearchError("No valid results found")

        # 找最优
        if self._maximize:
            best_idx = np.argmax([r.score for r in results])
        else:
            best_idx = np.argmin([r.score for r in results])

        return BayesianSearchResult(
            best_params=results[best_idx].params,
            best_score=results[best_idx].score,
            all_results=results,
            n_iterations=len(results),
            duration_ms=duration,
        )


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def bayesian_search(
    param_space: dict[str, tuple[float, float]],
    objective_fn: Callable[[dict[str, Any]], float],
    *,
    maximize: bool = True,
    n_iter: int = 30,
) -> BayesianSearchResult:
    """快捷函数：执行贝叶斯优化。

    Args:
        param_space: 参数空间
        objective_fn: 目标函数
        maximize: 是否最大化
        n_iter: 迭代次数

    Returns:
        BayesianSearchResult
    """
    searcher = BayesianSearcher(
        param_space=param_space,
        objective_fn=objective_fn,
        maximize=maximize,
    )
    return searcher.search(n_iter=n_iter)
