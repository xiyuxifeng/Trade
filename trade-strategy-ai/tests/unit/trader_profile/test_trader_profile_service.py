from __future__ import annotations

from src.persona.schemas import PersonaClustersFile, StyleCluster
from src.trader_profile.service import _aggregate_profile


def test_aggregate_profile_counts_top_symbols() -> None:
    profile = _aggregate_profile(
        trader_id="trader_a",
        symbols_by_article=[
            ["000001.SZ", "510300.SH"],
            ["000001.SZ"],
            ["000002.SZ", "000001.SZ"],
        ],
        concepts_by_article=[[], [], []],
        rules_by_article=[],
        clusters_file=None,
    )

    assert profile.trader_id == "trader_a"
    assert [s.symbol for s in profile.top_symbols[:2]] == ["000001.SZ", "000002.SZ"]
    assert profile.top_symbols[0].mentions == 3


def test_aggregate_profile_includes_cluster_ids() -> None:
    clusters_file = PersonaClustersFile(
        clusters_by_trader={
            "trader_a": [
                StyleCluster(cluster_id="trader_a:stock:v0", label="Stock"),
                StyleCluster(cluster_id="trader_a:etf:v0", label="ETF"),
            ]
        }
    )

    profile = _aggregate_profile(
        trader_id="trader_a",
        symbols_by_article=[["000001.SZ"]],
        concepts_by_article=[[]],
        rules_by_article=[],
        clusters_file=clusters_file,
    )

    assert profile.style_cluster_ids == ["trader_a:stock:v0", "trader_a:etf:v0"]

