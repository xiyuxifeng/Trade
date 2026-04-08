"""
行为聚类模块 — P2-012。

基于交易者的行为特征（BehaviorProfile）进行无监督聚类。
支持 K-Means 和 DBSCAN 两种算法。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler

from src.persona.behavior import BehaviorLabel, BehaviorProfile


@dataclass
class TraderFeatureVector:
    """交易者特征向量。"""
    trader_id: str
    # 行为标签频率分布（归一化）
    label_distribution: dict[str, float]
    # 平均持仓时长（分钟），None 表示无数据
    avg_hold_minutes: float | None
    # 日均交易次数
    trade_frequency: float
    # 特征向量原始值（用于调试）
    raw_features: np.ndarray = field(default_factory=lambda: np.array([]))


# ---------------------------------------------------------------------------
# 特征提取
# ---------------------------------------------------------------------------

# 所有行为标签（用于构建固定维度的特征向量）
_ALL_LABELS = [label.value for label in BehaviorLabel]


def extract_feature_vector(profile: BehaviorProfile, total_trades: int | None = None) -> TraderFeatureVector:
    """从 BehaviorProfile 提取特征向量。

    Args:
        profile: 交易者行为画像
        total_trades: 总交易次数（用于计算频率），若为 None 则用 label_distribution 总和估算

    Returns:
        TraderFeatureVector
    """
    # 1. 行为标签频率分布（归一化到 0-1）
    label_freq = profile.label_distribution.copy()
    total = sum(label_freq.values()) or 1.0
    label_dist_normalized = {k: v / total for k, v in label_freq.items()}

    # 补充缺失的标签为 0
    for label in _ALL_LABELS:
        if label not in label_dist_normalized:
            label_dist_normalized[label] = 0.0

    # 2. 平均持仓时长（归一化：假设最大 480 分钟 = 8 小时）
    avg_hold = profile.avg_hold_minutes
    if avg_hold is None:
        avg_hold_normalized = 0.0
    else:
        avg_hold_normalized = min(avg_hold / 480.0, 1.0)

    # 3. 交易频率（日均次数，假设每年 252 交易日）
    trade_freq = 0.0
    if total_trades is not None and total_trades > 0:
        trade_freq = total_trades / 252.0
    trade_freq_normalized = min(trade_freq, 10.0) / 10.0  # 归一化到 0-1（假设日均最多10次）

    # 构建特征向量
    label_features = [label_dist_normalized[label] for label in _ALL_LABELS]
    other_features = [avg_hold_normalized, trade_freq_normalized]
    raw_features = np.array(label_features + other_features, dtype=np.float64)

    return TraderFeatureVector(
        trader_id=profile.trader_id,
        label_distribution=label_dist_normalized,
        avg_hold_minutes=avg_hold,
        trade_frequency=trade_freq,
        raw_features=raw_features,
    )


def extract_features(profiles: list[BehaviorProfile], total_trades: dict[str, int] | None = None) -> tuple[list[str], np.ndarray]:
    """从多个 BehaviorProfile 批量提取特征矩阵。

    Args:
        profiles: 交易者行为画像列表
        total_trades: trader_id -> 总交易次数映射

    Returns:
        (trader_ids, feature_matrix)
        feature_matrix 形状: (n_samples, n_features)
    """
    if not profiles:
        return [], np.array([])

    vectors = []
    trader_ids = []

    for profile in profiles:
        trades = total_trades.get(profile.trader_id) if total_trades else None
        vec = extract_feature_vector(profile, trades)
        vectors.append(vec)
        trader_ids.append(vec.trader_id)

    # 特征矩阵
    feature_matrix = np.array([v.raw_features for v in vectors], dtype=np.float64)

    return trader_ids, feature_matrix


# ---------------------------------------------------------------------------
# 聚类算法
# ---------------------------------------------------------------------------

@dataclass
class ClusteringResult:
    """聚类结果。"""
    # 聚类标签，-1 表示噪声点（DBSCAN）
    labels: np.ndarray
    # 算法名称
    algorithm: str
    # 聚类数量（不含噪声）
    n_clusters: int
    # 原始 trader_ids
    trader_ids: list[str]


def _standardize(features: np.ndarray) -> np.ndarray:
    """标准化特征矩阵（Z-score）。"""
    if features.ndim == 1:
        features = features.reshape(-1, 1)
    scaler = StandardScaler()
    return scaler.fit_transform(features)


def kmeans_cluster(
    features: np.ndarray,
    k: int,
    trader_ids: list[str] | None = None,
    random_state: int = 42,
) -> ClusteringResult:
    """K-Means 聚类。

    Args:
        features: 特征矩阵 (n_samples, n_features)
        k: 聚类数量
        trader_ids: 可选的 trader_id 列表
        random_state: 随机种子

    Returns:
        ClusteringResult
    """
    if len(features) < k:
        # 样本数少于 k，返回每个样本单独一类
        labels = np.arange(len(features))
        return ClusteringResult(
            labels=labels,
            algorithm="kmeans",
            n_clusters=len(features),
            trader_ids=trader_ids or [f"sample_{i}" for i in range(len(features))],
        )

    standardized = _standardize(features)
    model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    labels = model.fit_predict(standardized)

    return ClusteringResult(
        labels=labels,
        algorithm="kmeans",
        n_clusters=k,
        trader_ids=trader_ids or [f"sample_{i}" for i in range(len(features))],
    )


def dbscan_cluster(
    features: np.ndarray,
    eps: float = 0.5,
    min_samples: int = 2,
    trader_ids: list[str] | None = None,
) -> ClusteringResult:
    """DBSCAN 聚类。

    Args:
        features: 特征矩阵 (n_samples, n_features)
        eps: 邻域半径
        min_samples: 核心点的最小邻居数
        trader_ids: 可选的 trader_id 列表

    Returns:
        ClusteringResult
    """
    if len(features) < 2:
        labels = np.zeros(len(features), dtype=int)
        return ClusteringResult(
            labels=labels,
            algorithm="dbscan",
            n_clusters=1,
            trader_ids=trader_ids or [f"sample_{i}" for i in range(len(features))],
        )

    standardized = _standardize(features)
    model = DBSCAN(eps=eps, min_samples=min_samples)
    labels = model.fit_predict(standardized)

    # 噪声点标签为 -1，实际聚类数从非负标签计算
    n_clusters = len(set(labels) - {-1})

    return ClusteringResult(
        labels=labels,
        algorithm="dbscan",
        n_clusters=n_clusters,
        trader_ids=trader_ids or [f"sample_{i}" for i in range(len(features))],
    )


def cluster_traders(
    profiles: list[BehaviorProfile],
    total_trades: dict[str, int] | None = None,
    *,
    algorithm: str = "kmeans",
    k: int | None = None,
    eps: float = 0.5,
    min_samples: int = 2,
    random_state: int = 42,
) -> ClusteringResult:
    """对交易者进行行为聚类（高层接口）。

    Args:
        profiles: 交易者行为画像列表
        total_trades: trader_id -> 总交易次数映射
        algorithm: 算法选择 "kmeans" 或 "dbscan"
        k: K-Means 聚类数（仅 kmeans 模式）
        eps: DBSCAN 邻域半径（仅 dbscan 模式）
        min_samples: DBSCAN 最小样本数（仅 dbscan 模式）
        random_state: 随机种子

    Returns:
        ClusteringResult
    """
    if not profiles:
        return ClusteringResult(
            labels=np.array([], dtype=int),
            algorithm=algorithm,
            n_clusters=0,
            trader_ids=[],
        )

    trader_ids, features = extract_features(profiles, total_trades)

    if algorithm == "kmeans":
        if k is None:
            k = min(3, len(profiles))  # 默认 k=3
        return kmeans_cluster(features, k=k, trader_ids=trader_ids, random_state=random_state)
    elif algorithm == "dbscan":
        return dbscan_cluster(features, eps=eps, min_samples=min_samples, trader_ids=trader_ids)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
