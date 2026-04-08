"""
网格搜索优化器单元测试 — P5-008。
"""

from __future__ import annotations

import math
from src.persona.grid_search import (
    GridSearcher,
    GridSearchResult,
    SearchResult,
    grid_search,
    GridSearchError,
)


class TestGridSearcher:
    """GridSearcher 测试。"""

    def test_simple_grid_search(self):
        """测试简单的网格搜索。"""
        searcher = GridSearcher(
            param_space={
                "x": [1, 2, 3],
                "y": [10, 20],
            },
            objective_fn=lambda p: p["x"] + p["y"],
        )

        result = searcher.search()

        assert result.total_combinations == 6
        assert result.searched_combinations == 6
        assert result.best_params["x"] == 3
        assert result.best_params["y"] == 20
        assert result.best_score == 23

    def test_maximize_vs_minimize(self):
        """测试最大化 vs 最小化。"""
        # 最大化
        searcher_max = GridSearcher(
            param_space={"x": [1, 2, 3]},
            objective_fn=lambda p: p["x"],
            maximize=True,
        )
        result_max = searcher_max.search()
        assert result_max.best_score == 3

        # 最小化
        searcher_min = GridSearcher(
            param_space={"x": [1, 2, 3]},
            objective_fn=lambda p: p["x"],
            maximize=False,
        )
        result_min = searcher_min.search()
        assert result_min.best_score == 1

    def test_skip_fn(self):
        """测试跳过函数。"""
        searcher = GridSearcher(
            param_space={
                "x": [1, 2, 3],
                "y": [1, 2, 3],
            },
            objective_fn=lambda p: p["x"] + p["y"],
            skip_fn=lambda p: p["x"] == p["y"],  # 跳过 x == y 的组合
        )

        result = searcher.search()

        # 总共 9 个组合，跳过 3 个（x==y），剩下 6 个
        assert result.searched_combinations == 6
        # 检查没有 x == y 的结果
        for r in result.all_results:
            assert r.params["x"] != r.params["y"]

    def test_max_combinations(self):
        """测试最大组合数限制。"""
        searcher = GridSearcher(
            param_space={
                "x": list(range(10)),
                "y": list(range(10)),
            },
            objective_fn=lambda p: p["x"] + p["y"],
            max_combinations=5,
        )

        assert searcher.total_combinations() == 100

        result = searcher.search()

        # 应该只搜索 5 个组合
        assert result.searched_combinations == 5
        assert result.total_combinations == 100

    def test_objective_fn_exception(self):
        """测试目标函数抛出异常时跳过。"""
        searcher = GridSearcher(
            param_space={"x": [1, 2, 3]},
            objective_fn=lambda p: 1 / (p["x"] - 2),  # x=2 时除零
        )

        result = searcher.search()

        # x=2 时会抛出异常被跳过，剩下 2 个有效结果
        assert result.searched_combinations == 2

    def test_ranking(self):
        """测试结果排名。"""
        searcher = GridSearcher(
            param_space={"x": [1, 2, 3]},
            objective_fn=lambda p: p["x"],
        )

        result = searcher.search()

        # 按 x 降序排列
        assert result.all_results[0].rank == 1
        assert result.all_results[0].score == 3
        assert result.all_results[1].rank == 2
        assert result.all_results[1].score == 2
        assert result.all_results[2].rank == 3
        assert result.all_results[2].score == 1

    def test_progress_callback(self):
        """测试进度回调。"""
        progress = []

        def on_progress(current, total):
            progress.append((current, total))

        searcher = GridSearcher(
            param_space={"x": [1, 2, 3], "y": [1, 2]},
            objective_fn=lambda p: p["x"] + p["y"],
        )

        result = searcher.search(progress_callback=on_progress)

        # 总共 6 个组合
        assert result.searched_combinations == 6
        assert len(progress) == 6

    def test_empty_result_raises_error(self):
        """测试全部失败时抛出错误。"""
        import pytest
        searcher = GridSearcher(
            param_space={"x": [1]},
            objective_fn=lambda p: 1 / 0,  # 总是抛出异常
        )

        with pytest.raises(GridSearchError):
            searcher.search()


class TestConvenienceFunction:
    """快捷函数测试。"""

    def test_grid_search_function(self):
        """测试 grid_search 快捷函数。"""
        result = grid_search(
            param_space={"x": [1, 2, 3]},
            objective_fn=lambda p: p["x"],
        )

        assert result.best_score == 3
        assert result.best_params["x"] == 3


class TestSearchResult:
    """SearchResult 数据类测试。"""

    def test_search_result_creation(self):
        """测试 SearchResult 创建。"""
        result = SearchResult(
            params={"x": 1, "y": 2},
            score=0.85,
            rank=1,
            metadata={"sharpe": 1.2},
        )

        assert result.params["x"] == 1
        assert result.score == 0.85
        assert result.rank == 1
        assert result.metadata["sharpe"] == 1.2


class TestEdgeCases:
    """边界情况测试。"""

    def test_single_param(self):
        """测试单个参数。"""
        searcher = GridSearcher(
            param_space={"x": [1, 2, 3]},
            objective_fn=lambda p: p["x"] * 2,
        )

        result = searcher.search()

        assert result.best_params["x"] == 3
        assert result.best_score == 6

    def test_empty_param_space(self):
        """测试空参数空间（应该返回 0 个组合）。"""
        searcher = GridSearcher(
            param_space={},
            objective_fn=lambda p: 0,
        )

        result = searcher.search()

        assert result.total_combinations == 1  # 空 product 返回一个空元组
        assert result.searched_combinations == 1
        assert result.best_params == {}

    def test_all_same_score(self):
        """测试所有参数组合得分相同。"""
        searcher = GridSearcher(
            param_space={"x": [1, 2, 3]},
            objective_fn=lambda p: 1.0,  # 总是返回 1.0
        )

        result = searcher.search()

        # 所有结果的分数都是 1.0，第一个是最好的
        assert result.best_score == 1.0
        assert len(result.all_results) == 3

    def test_float_values(self):
        """测试浮点数值。"""
        searcher = GridSearcher(
            param_space={
                "lr": [0.001, 0.01, 0.1],
                "gamma": [0.9, 0.95, 0.99],
            },
            objective_fn=lambda p: p["lr"] * p["gamma"],
        )

        result = searcher.search()

        # 最佳应该是 0.1 * 0.99 = 0.099
        assert result.best_params["lr"] == 0.1
        assert result.best_params["gamma"] == 0.99
        assert math.isclose(result.best_score, 0.099)


class TestPerformance:
    """性能测试。"""

    def test_large_search_space(self):
        """测试较大搜索空间（带限制）。"""
        searcher = GridSearcher(
            param_space={
                "x": list(range(20)),
                "y": list(range(20)),
            },
            objective_fn=lambda p: p["x"] + p["y"],
            max_combinations=100,
        )

        assert searcher.total_combinations() == 400

        result = searcher.search()

        assert result.searched_combinations == 100
        assert result.total_combinations == 400
        # 检查结果已排序
        for i in range(len(result.all_results) - 1):
            assert result.all_results[i].score >= result.all_results[i + 1].score
