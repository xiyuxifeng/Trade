"""
网格搜索优化器 — P5-008。

在参数空间中进行网格搜索，找到最优参数组合。

用法：
    searcher = GridSearcher(
        param_space={
            "stop_loss_pct": [0.02, 0.03, 0.05],
            "take_profit_pct": [0.05, 0.08, 0.10],
        },
        objective_fn=lambda params: compute_sharpe_ratio(params),
    )
    results = searcher.search()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import reduce
from typing import Any, Callable

import itertools


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ParameterSpace:
    """参数空间定义。"""
    name: str
    values: list[Any]

    def __len__(self) -> int:
        return len(self.values)


@dataclass
class SearchResult:
    """单次搜索结果。"""
    params: dict[str, Any]
    score: float
    rank: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GridSearchResult:
    """网格搜索结果。"""
    total_combinations: int
    searched_combinations: int
    best_params: dict[str, Any]
    best_score: float
    best_rank: int
    all_results: list[SearchResult]
    duration_ms: float
    searched_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GridSearchError(Exception):
    """网格搜索错误。"""
    pass


# ---------------------------------------------------------------------------
# Grid Searcher
# ---------------------------------------------------------------------------

class GridSearcher:
    """网格搜索优化器。

    在给定的参数空间中进行穷举搜索，找到最优参数组合。

    用法：
        searcher = GridSearcher(
            param_space={
                "stop_loss_pct": [0.02, 0.03, 0.05],
                "take_profit_pct": [0.05, 0.08, 0.10],
            },
            objective_fn=lambda params: compute_sharpe_ratio(params),
            maximize=True,  # 默认最大化
        )
        result = searcher.search()
        print(f"Best params: {result.best_params}")
        print(f"Best score: {result.best_score}")
    """

    def __init__(
        self,
        param_space: dict[str, list[Any]],
        objective_fn: Callable[[dict[str, Any]], float],
        *,
        maximize: bool = True,
        max_combinations: int | None = None,
        skip_fn: Callable[[dict[str, Any]], bool] | None = None,
    ):
        """初始化网格搜索器。

        Args:
            param_space: 参数空间，如 {"stop_loss_pct": [0.02, 0.03]}
            objective_fn: 目标函数，输入参数，返回评分
            maximize: True 为最大化，False 为最小化
            max_combinations: 最大搜索组合数（用于限制搜索空间）
            skip_fn: 跳过某些参数组合的函数（如某些组合无意义）
        """
        self._param_space = param_space
        self._objective_fn = objective_fn
        self._maximize = maximize
        self._max_combinations = max_combinations
        self._skip_fn = skip_fn

    @property
    def param_space(self) -> dict[str, list[Any]]:
        return self._param_space

    def total_combinations(self) -> int:
        """计算总组合数。"""
        if not self._param_space:
            return 1
        return int(reduce(
            lambda a, b: a * len(b),
            self._param_space.values(),
            1
        ))

    def _generate_combinations(self):
        """生成所有参数组合。"""
        keys = list(self._param_space.keys())
        for values in itertools.product(*self._param_space.values()):
            yield dict(zip(keys, values))

    def search(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> GridSearchResult:
        """执行网格搜索。

        Args:
            progress_callback: 进度回调函数 (current, total)

        Returns:
            GridSearchResult
        """
        start_time = datetime.now()
        total = self.total_combinations()

        # 如果设置了 max_combinations，随机采样
        if self._max_combinations and total > self._max_combinations:
            return self._search_sampled(total, progress_callback, start_time)

        results: list[SearchResult] = []
        searched = 0

        for params in self._generate_combinations():
            # 跳过无效组合
            if self._skip_fn and self._skip_fn(params):
                continue

            try:
                score = self._objective_fn(params)
            except Exception:
                # 目标函数计算失败，跳过
                continue

            searched += 1
            results.append(SearchResult(
                params=params,
                score=score,
                rank=0,  # 稍后计算
            ))

            if progress_callback:
                progress_callback(searched, total)

        # 排序并计算排名
        results.sort(key=lambda r: r.score, reverse=self._maximize)
        for i, r in enumerate(results):
            r.rank = i + 1

        duration = (datetime.now() - start_time).total_seconds() * 1000

        if not results:
            raise GridSearchError("No valid results found")

        return GridSearchResult(
            total_combinations=total,
            searched_combinations=searched,
            best_params=results[0].params,
            best_score=results[0].score,
            best_rank=results[0].rank,
            all_results=results,
            duration_ms=duration,
        )

    def _search_sampled(
        self,
        total: int,
        progress_callback: Callable[[int, int], None] | None,
        start_time: datetime,
    ) -> GridSearchResult:
        """随机采样搜索（当组合数超过限制时）。"""
        import random

        results: list[SearchResult] = []
        all_combinations = list(self._generate_combinations())
        sampled = random.sample(all_combinations, self._max_combinations)

        searched = 0
        for params in sampled:
            if self._skip_fn and self._skip_fn(params):
                continue

            try:
                score = self._objective_fn(params)
            except Exception:
                continue

            searched += 1
            results.append(SearchResult(
                params=params,
                score=score,
                rank=0,
            ))

            if progress_callback:
                progress_callback(searched, self._max_combinations)

        results.sort(key=lambda r: r.score, reverse=self._maximize)
        for i, r in enumerate(results):
            r.rank = i + 1

        duration = (datetime.now() - start_time).total_seconds() * 1000

        if not results:
            raise GridSearchError("No valid results found")

        return GridSearchResult(
            total_combinations=total,
            searched_combinations=searched,
            best_params=results[0].params,
            best_score=results[0].score,
            best_rank=results[0].rank,
            all_results=results,
            duration_ms=duration,
        )


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def grid_search(
    param_space: dict[str, list[Any]],
    objective_fn: Callable[[dict[str, Any]], float],
    *,
    maximize: bool = True,
) -> GridSearchResult:
    """快捷函数：执行网格搜索。

    Args:
        param_space: 参数空间
        objective_fn: 目标函数
        maximize: 是否最大化

    Returns:
        GridSearchResult
    """
    searcher = GridSearcher(
        param_space=param_space,
        objective_fn=objective_fn,
        maximize=maximize,
    )
    return searcher.search()
