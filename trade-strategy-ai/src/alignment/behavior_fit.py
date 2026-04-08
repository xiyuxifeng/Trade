"""
行为适配度分析 — P3-009~P3-012。

相似度和距离度量算法：
  - P3-009: 特征向量相似度（余弦、欧几里得）
  - P3-010: 概率分布拟合度（KL 散度、Wasserstein）
  - P3-011: 时间序列相似度（DTW、点互相关）
  - P3-012: 统计量匹配度
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# P3-009: 特征向量相似度
# ---------------------------------------------------------------------------

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算余弦相似度。

    Args:
        a: 特征向量 A
        b: 特征向量 B

    Returns:
        余弦相似度（-1 到 1），1 表示完全相似
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimension")

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """计算欧几里得距离。

    Args:
        a: 特征向量 A
        b: 特征向量 B

    Returns:
        欧几里得距离（>= 0）
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimension")

    return float(np.linalg.norm(a - b))


def manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
    """计算曼哈顿距离。

    Args:
        a: 特征向量 A
        b: 特征向量 B

    Returns:
        曼哈顿距离（>= 0）
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimension")

    return float(np.sum(np.abs(a - b)))


def chebyshev_distance(a: np.ndarray, b: np.ndarray) -> float:
    """计算切比雪夫距离（最大维度差）。

    Args:
        a: 特征向量 A
        b: 特征向量 B

    Returns:
        切比雪夫距离
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have same dimension")

    return float(np.max(np.abs(a - b)))


def cosine_similarity_dict(a: dict[str, float], b: dict[str, float]) -> float:
    """计算两个字典表示的向量的余弦相似度。

    Args:
        a: 稀疏向量（字典形式）
        b: 稀疏向量（字典形式）

    Returns:
        余弦相似度
    """
    # 获取所有键
    all_keys = set(a.keys()) | set(b.keys())
    vec_a = np.array([a.get(k, 0.0) for k in all_keys])
    vec_b = np.array([b.get(k, 0.0) for k in all_keys])

    return cosine_similarity(vec_a, vec_b)


# ---------------------------------------------------------------------------
# P3-010: 概率分布拟合度
# ---------------------------------------------------------------------------

def kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """计算 KL 散度（D_KL(P || Q)）。

    KL 散度衡量分布 P 相对于分布 Q 的信息增益。
    非对称：DKL(P||Q) != DKL(Q||P)

    Args:
        p: 目标分布 P
        q: 参考分布 Q
        epsilon: 防止 log(0) 的小常数

    Returns:
        KL 散度（>= 0），0 表示完全相同
    """
    if len(p) != len(q):
        raise ValueError("Distributions must have same length")

    # 归一化
    p = np.array(p, dtype=np.float64)
    q = np.array(q, dtype=np.float64)
    p = p / (np.sum(p) + epsilon)
    q = q / (np.sum(q) + epsilon)

    # 添加 epsilon 防止 log(0)
    p = p + epsilon
    q = q + epsilon
    p = p / np.sum(p)
    q = q / np.sum(q)

    return float(np.sum(p * np.log(p / q)))


def js_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """计算 Jensen-Shannon 散度。

    对称的散度度量，值域 [0, 1]。

    Args:
        p: 分布 P
        q: 分布 Q
        epsilon: 防止 log(0) 的小常数

    Returns:
        JS 散度（0 到 1）
    """
    if len(p) != len(q):
        raise ValueError("Distributions must have same length")

    m = (p + q) / 2.0
    return (kl_divergence(p, m, epsilon) + kl_divergence(q, m, epsilon)) / 2.0


def wasserstein_distance_1d(
    p: np.ndarray | list[float],
    q: np.ndarray | list[float],
) -> float:
    """计算一维 Wasserstein 距离（EMD 的简化版本）。

    Wasserstein 距离可以理解为将分布 P 转换为分布 Q 所需的最小"工作量"。

    Args:
        p: 一维分布 P
        q: 一维分布 Q

    Returns:
        Wasserstein 距离（>= 0）
    """
    p = np.sort(np.array(p, dtype=np.float64))
    q = np.sort(np.array(q, dtype=np.float64))

    # 累积分布函数的积分差
    p_cdf = np.arange(1, len(p) + 1) / len(p)
    q_cdf = np.arange(1, len(q) + 1) / len(q)

    # 计算所有点的距离
    all_points = np.sort(np.concatenate([p, q]))
    p_interp = np.interp(all_points, p, p_cdf)
    q_interp = np.interp(all_points, q, q_cdf)

    return float(np.sum(np.abs(p_interp - q_interp)) * (all_points[1] - all_points[0]))


def kolmogorov_smirnov_statistic(
    p: np.ndarray | list[float],
    q: np.ndarray | list[float],
) -> float:
    """计算 Kolmogorov-Smirnov 统计量。

    两个累积分布之间的最大差距。

    Args:
        p: 一维分布 P
        q: 一维分布 Q

    Returns:
        KS 统计量（0 到 1）
    """
    p = np.sort(np.array(p, dtype=np.float64))
    q = np.sort(np.array(q, dtype=np.float64))

    p_cdf = np.arange(1, len(p) + 1) / len(p)
    q_cdf = np.arange(1, len(q) + 1) / len(q)

    # 在所有数据点上计算 CDF 差
    all_points = np.sort(np.concatenate([p, q]))
    p_interp = np.interp(all_points, p, p_cdf)
    q_interp = np.interp(all_points, q, q_cdf)

    return float(np.max(np.abs(p_interp - q_interp)))


# ---------------------------------------------------------------------------
# P3-011: 时间序列相似度
# ---------------------------------------------------------------------------

def dtw_distance(
    s1: np.ndarray,
    s2: np.ndarray,
    window: int | None = None,
) -> float:
    """计算动态时间规整（DTW）距离。

    DTW 可以衡量两个时间序列的相似性，允许时间轴上的伸缩。

    Args:
        s1: 时间序列 1
        s2: 时间序列 2
        window: 约束窗口大小（可选）

    Returns:
        DTW 距离
    """
    s1 = np.array(s1, dtype=np.float64)
    s2 = np.array(s2, dtype=np.float64)

    n, m = len(s1), len(s2)

    if window is None:
        window = max(n, m)

    # 初始化距离矩阵
    dtw_matrix = np.full((n + 1, m + 1), np.inf)
    dtw_matrix[0, 0] = 0.0

    # 填充距离矩阵
    for i in range(1, n + 1):
        j_start = max(1, i - window)
        j_end = min(m, i + window) + 1
        for j in range(j_start, j_end):
            cost = abs(s1[i - 1] - s2[j - 1])
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i - 1, j],    # 插入
                dtw_matrix[i, j - 1],  # 删除
                dtw_matrix[i - 1, j - 1]  # 匹配
            )

    return float(dtw_matrix[n, m])


def cross_correlation(
    s1: np.ndarray,
    s2: np.ndarray,
    max_lag: int | None = None,
    normalize: bool = True,
) -> dict[int, float]:
    """计算点互相关（Cross-correlation）。

    衡量两个时间序列在不同滞后位置的相关性。

    Args:
        s1: 时间序列 1
        s2: 时间序列 2
        max_lag: 最大滞后阶数
        normalize: 是否归一化

    Returns:
        {lag: correlation} 字典，lag 从 -max_lag 到 max_lag
    """
    s1 = np.array(s1, dtype=np.float64)
    s2 = np.array(s2, dtype=np.float64)

    if max_lag is None:
        max_lag = min(len(s1), len(s2)) - 1

    n = len(s1)
    m = len(s2)
    max_lag = min(max_lag, n - 1, m - 1)

    correlations: dict[int, float] = {}

    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            # s1 滞后于 s2
            s1_shifted = s1[lag:]
            s2_shifted = s2[:len(s1_shifted)]
        else:
            # s2 滞后于 s1
            s1_shifted = s1[:m + lag]
            s2_shifted = s2[-lag:-lag + len(s1_shifted)]

        if len(s1_shifted) < 2 or len(s2_shifted) < 2:
            correlations[lag] = 0.0
            continue

        if normalize:
            # 归一化互相关
            mean1 = np.mean(s1_shifted)
            mean2 = np.mean(s2_shifted)
            std1 = np.std(s1_shifted)
            std2 = np.std(s2_shifted)

            if std1 == 0 or std2 == 0:
                correlations[lag] = 0.0
            else:
                correlations[lag] = float(np.mean(
                    (s1_shifted - mean1) * (s2_shifted - mean2)
                ) / (std1 * std2))
        else:
            correlations[lag] = float(np.mean((s1_shifted - s2_shifted) ** 2))

    return correlations


def pearson_correlation(s1: np.ndarray, s2: np.ndarray) -> float:
    """计算皮尔逊相关系数。

    Args:
        s1: 时间序列 1
        s2: 时间序列 2

    Returns:
        相关系数（-1 到 1）
    """
    s1 = np.array(s1, dtype=np.float64)
    s2 = np.array(s2, dtype=np.float64)

    if len(s1) != len(s2):
        raise ValueError("Series must have same length")

    if len(s1) < 2:
        return 0.0

    mean1 = np.mean(s1)
    mean2 = np.mean(s2)
    std1 = np.std(s1, ddof=0)
    std2 = np.std(s2, ddof=0)

    if std1 == 0 or std2 == 0:
        return 0.0

    return float(np.mean((s1 - mean1) * (s2 - mean2)) / (std1 * std2))


def similarity_from_distance(distance: float, scale: float = 1.0) -> float:
    """将距离转换为相似度。

    使用指数衰减：similarity = exp(-distance / scale)

    Args:
        distance: 距离值
        scale: 尺度参数

    Returns:
        相似度（0 到 1）
    """
    return float(np.exp(-distance / scale) if scale > 0 else 0.0)


# ---------------------------------------------------------------------------
# P3-012: 统计量匹配度
# ---------------------------------------------------------------------------

@dataclass
class StatsMatchScore:
    """统计量匹配结果。"""
    win_rate_score: float = 0.0
    expected_value_score: float = 0.0
    overall_score: float = 0.0


def compute_win_rate_score(
    actual_win_rate: float,
    expected_win_rate: float,
    tolerance: float = 0.2,
) -> float:
    """计算胜率匹配分数。

    Args:
        actual_win_rate: 实际胜率
        expected_win_rate: 期望胜率
        tolerance: 容许偏差

    Returns:
        匹配分数（0 到 1）
    """
    diff = abs(actual_win_rate - expected_win_rate)
    score = max(0.0, 1.0 - diff / tolerance)
    return float(score)


def compute_expected_value_score(
    actual_ev: float,
    expected_ev: float,
    tolerance: float = 0.05,
) -> float:
    """计算期望值匹配分数。

    Args:
        actual_ev: 实际期望值
        expected_ev: 期望期望值
        tolerance: 容许偏差（按绝对值）

    Returns:
        匹配分数（0 到 1）
    """
    if expected_ev == 0:
        if actual_ev == 0:
            return 1.0
        return max(0.0, 1.0 - abs(actual_ev) / tolerance)

    diff = abs(actual_ev - expected_ev)
    score = max(0.0, 1.0 - diff / (abs(expected_ev) * tolerance + tolerance))
    return float(score)


def compute_stats_match_score(
    actual_stats: dict[str, float],
    expected_stats: dict[str, float],
    weights: dict[str, float] | None = None,
) -> StatsMatchScore:
    """计算统计量综合匹配度。

    Args:
        actual_stats: 实际统计量字典
        expected_stats: 期望统计量字典
        weights: 各统计量的权重

    Returns:
        StatsMatchScore
    """
    if weights is None:
        weights = {"win_rate": 0.5, "expected_value": 0.5}

    win_rate_score = 0.0
    expected_value_score = 0.0

    if "win_rate" in actual_stats and "win_rate" in expected_stats:
        win_rate_score = compute_win_rate_score(
            actual_stats["win_rate"],
            expected_stats["win_rate"],
        )

    if "expected_value" in actual_stats and "expected_value" in expected_stats:
        expected_value_score = compute_expected_value_score(
            actual_stats["expected_value"],
            expected_stats["expected_value"],
        )

    overall_score = (
        win_rate_score * weights.get("win_rate", 0.5)
        + expected_value_score * weights.get("expected_value", 0.5)
    )

    return StatsMatchScore(
        win_rate_score=win_rate_score,
        expected_value_score=expected_value_score,
        overall_score=overall_score,
    )
