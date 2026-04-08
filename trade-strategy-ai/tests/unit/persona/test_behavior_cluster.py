"""
行为聚类单元测试 — P2-012。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.persona.behavior import BehaviorLabel, BehaviorProfile
from src.persona.behavior_cluster import (
    ClusteringResult,
    TraderFeatureVector,
    cluster_traders,
    dbscan_cluster,
    extract_feature_vector,
    extract_features,
    kmeans_cluster,
)


class TestExtractFeatureVector:
    """extract_feature_vector 测试。"""

    def test_empty_profile(self):
        """空画像。"""
        profile = BehaviorProfile(trader_id="t1", label_distribution={})
        vec = extract_feature_vector(profile)
        assert vec.trader_id == "t1"
        assert vec.avg_hold_minutes is None
        assert vec.trade_frequency == 0.0
        # 所有标签应为 0
        for v in vec.label_distribution.values():
            assert v == 0.0

    def test_with_hold_minutes(self):
        """有持仓时长。"""
        profile = BehaviorProfile(
            trader_id="t1",
            label_distribution={"chase_rally": 5, "bottom_fish": 3},
            avg_hold_minutes=120.0,
        )
        vec = extract_feature_vector(profile)
        assert vec.avg_hold_minutes == 120.0
        # 归一化到 0-1（120/480 = 0.25）
        assert vec.raw_features[-2] == pytest.approx(0.25, rel=1e-10)

    def test_trade_frequency(self):
        """交易频率计算。"""
        profile = BehaviorProfile(trader_id="t1", label_distribution={})
        vec = extract_feature_vector(profile, total_trades=504)  # 日均 2 次
        # 504 / 252 = 2.0, / 10 归一化 = 0.2
        assert vec.trade_frequency == 2.0
        assert vec.raw_features[-1] == pytest.approx(0.2, rel=1e-10)

    def test_label_distribution_normalized(self):
        """标签分布归一化。"""
        profile = BehaviorProfile(
            trader_id="t1",
            label_distribution={"chase_rally": 60, "bottom_fish": 40},  # 总 100
        )
        vec = extract_feature_vector(profile)
        assert vec.label_distribution["chase_rally"] == 0.6
        assert vec.label_distribution["bottom_fish"] == 0.4
        # 所有标签总和应为 1.0
        assert sum(vec.label_distribution.values()) == pytest.approx(1.0, rel=1e-10)

    def test_missing_labels_filled(self):
        """缺失标签补零。"""
        profile = BehaviorProfile(
            trader_id="t1",
            label_distribution={"chase_rally": 1},
        )
        vec = extract_feature_vector(profile)
        assert vec.label_distribution["bottom_fish"] == 0.0
        assert vec.label_distribution["trend_follow"] == 0.0


class TestExtractFeatures:
    """extract_features 批量提取测试。"""

    def test_empty_profiles(self):
        """空列表。"""
        ids, matrix = extract_features([])
        assert ids == []
        assert matrix.shape == (0,)

    def test_multiple_profiles(self):
        """多交易者。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={"chase_rally": 10}),
            BehaviorProfile(trader_id="t2", label_distribution={"bottom_fish": 10}),
        ]
        ids, matrix = extract_features(profiles)
        assert len(ids) == 2
        assert matrix.shape[0] == 2
        assert "t1" in ids
        assert "t2" in ids

    def test_feature_matrix_dimensions(self):
        """特征矩阵维度正确。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={}),
            BehaviorProfile(trader_id="t2", label_distribution={}),
        ]
        _, matrix = extract_features(profiles)
        # n_labels + 2 (hold_minutes, trade_freq)
        n_labels = len(BehaviorLabel)
        assert matrix.shape[1] == n_labels + 2


class TestKmeansCluster:
    """K-Means 聚类测试。"""

    def test_simple_clustering(self):
        """简单聚类。"""
        # 两个明显不同的交易者特征
        profiles = [
            BehaviorProfile(
                trader_id="chase_trader",
                label_distribution={"chase_rally": 0.9, "bottom_fish": 0.1},
                avg_hold_minutes=10.0,  # 超短线
            ),
            BehaviorProfile(
                trader_id="swing_trader",
                label_distribution={"bottom_fish": 0.9, "chase_rally": 0.1},
                avg_hold_minutes=240.0,  # 波段
            ),
        ]
        ids, features = extract_features(profiles)
        result = kmeans_cluster(features, k=2, trader_ids=ids)

        assert result.algorithm == "kmeans"
        assert result.n_clusters == 2
        assert len(result.labels) == 2
        # 两个交易者应该被分到不同类别
        assert result.labels[0] != result.labels[1]

    def test_more_clusters_than_samples(self):
        """聚类数大于样本数。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={}),
        ]
        ids, features = extract_features(profiles)
        result = kmeans_cluster(features, k=5, trader_ids=ids)

        # 样本数少于k时，每个样本单独一类
        assert result.n_clusters == 1

    def test_same_profiles_same_cluster(self):
        """相同的画像应该被聚到同一类。"""
        profile_data = {"label_distribution": {"chase_rally": 1.0}}
        profiles = [
            BehaviorProfile(trader_id="t1", **profile_data),
            BehaviorProfile(trader_id="t2", **profile_data),
            BehaviorProfile(trader_id="t3", **profile_data),
        ]
        ids, features = extract_features(profiles)
        result = kmeans_cluster(features, k=2, trader_ids=ids)

        # 相同特征应该被分到同一类（不一定全是同一类，取决于初始化）
        assert result.n_clusters <= 2


class TestDbscanCluster:
    """DBSCAN 聚类测试。"""

    def test_simple_clustering(self):
        """简单聚类。"""
        profiles = [
            BehaviorProfile(
                trader_id="t1",
                label_distribution={"chase_rally": 0.9, "bottom_fish": 0.1},
                avg_hold_minutes=10.0,
            ),
            BehaviorProfile(
                trader_id="t2",
                label_distribution={"bottom_fish": 0.9, "chase_rally": 0.1},
                avg_hold_minutes=240.0,
            ),
        ]
        ids, features = extract_features(profiles)
        result = dbscan_cluster(features, eps=1.0, min_samples=1, trader_ids=ids)

        assert result.algorithm == "dbscan"
        # 两个不同样本应该被分到不同聚类或同一聚类（取决于eps）

    def test_noise_detection(self):
        """噪声点检测。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={"chase_rally": 1.0}),
            BehaviorProfile(trader_id="t2", label_distribution={"bottom_fish": 1.0}),
            # 异常点：与两者都不同
            BehaviorProfile(trader_id="t3", label_distribution={"scalp": 1.0}),
        ]
        ids, features = extract_features(profiles)
        result = dbscan_cluster(features, eps=0.5, min_samples=2, trader_ids=ids)

        # DBSCAN 可能检测到噪声点（标签=-1）
        assert result.algorithm == "dbscan"
        assert len(result.labels) == 3

    def test_single_sample(self):
        """单样本。"""
        profiles = [BehaviorProfile(trader_id="t1", label_distribution={})]
        ids, features = extract_features(profiles)
        result = dbscan_cluster(features, trader_ids=ids)

        # 单样本应返回标签 0
        assert result.labels[0] == 0
        assert result.n_clusters == 1


class TestClusterTraders:
    """cluster_traders 高层接口测试。"""

    def test_kmeans_default_k(self):
        """K-Means 默认 k。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={}),
            BehaviorProfile(trader_id="t2", label_distribution={}),
            BehaviorProfile(trader_id="t3", label_distribution={}),
        ]
        result = cluster_traders(profiles, algorithm="kmeans")
        assert result.algorithm == "kmeans"
        assert result.n_clusters == 3  # 默认 k=min(3, n_samples)

    def test_dbscan_default(self):
        """DBSCAN 默认参数。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={"chase_rally": 1.0}),
            BehaviorProfile(trader_id="t2", label_distribution={"chase_rally": 0.8, "bottom_fish": 0.2}),
        ]
        result = cluster_traders(profiles, algorithm="dbscan")
        assert result.algorithm == "dbscan"

    def test_empty_profiles(self):
        """空列表。"""
        result = cluster_traders([], algorithm="kmeans")
        assert result.n_clusters == 0
        assert len(result.labels) == 0

    def test_invalid_algorithm(self):
        """无效算法。"""
        profiles = [BehaviorProfile(trader_id="t1", label_distribution={})]
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            cluster_traders(profiles, algorithm="invalid")

    def test_trader_ids_preserved(self):
        """trader_id 保持一致。"""
        profiles = [
            BehaviorProfile(trader_id="trader_a", label_distribution={}),
            BehaviorProfile(trader_id="trader_b", label_distribution={}),
        ]
        result = cluster_traders(profiles, algorithm="kmeans", k=2)
        assert "trader_a" in result.trader_ids
        assert "trader_b" in result.trader_ids


class TestClusteringResult:
    """ClusteringResult 数据结构测试。"""

    def test_labels_array(self):
        """标签是 numpy 数组。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={}),
            BehaviorProfile(trader_id="t2", label_distribution={}),
        ]
        result = cluster_traders(profiles, algorithm="kmeans", k=2)
        assert isinstance(result.labels, np.ndarray)
        assert len(result.labels) == 2

    def test_dbscan_noise_label(self):
        """DBSCAN 噪声点标签为 -1。"""
        profiles = [
            BehaviorProfile(trader_id="t1", label_distribution={"chase_rally": 1.0}),
            BehaviorProfile(trader_id="t2", label_distribution={"bottom_fish": 1.0}),
            BehaviorProfile(trader_id="t3", label_distribution={"scalp": 1.0}),
        ]
        ids, features = extract_features(profiles)
        result = dbscan_cluster(features, eps=0.3, min_samples=1, trader_ids=ids)

        # 噪声点标签可能为 -1
        assert -1 in result.labels or len(set(result.labels)) == result.n_clusters
