from __future__ import annotations

import json
from pathlib import Path

from src.providers.kaipan_normalizer import KaipanNormalizer


def _build_normalizer(tmp_path: Path) -> KaipanNormalizer:
    return KaipanNormalizer(
        schema_dir=Path("src/providers/kaipan_schema"),
        snapshots_dir=tmp_path / "snapshots",
    )


def _write_raw(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"meta": {"trade_date": "2026-05-18", "slot": "17-30"}, "data": payload}, ensure_ascii=False), encoding="utf-8")
    return path


def test_kaipan_normalizer_supports_10_5_schemas(tmp_path: Path) -> None:
    normalizer = _build_normalizer(tmp_path)

    market_stock = normalizer.normalize_market_stock_zd_num(
        _write_raw(tmp_path / "market_stock_zd_num.json", {"info": {"SJZT": 79, "SJDT": 1, "panic": 12}}),
        slot="17-30",
    )
    zhang_ting = normalizer.normalize_zhang_ting_expression(
        _write_raw(tmp_path / "zhang_ting_expression.json", {"info": [71, 5, 1, 2, 10.0, 12.0, 66.0, 21.0, 1.0, 3.0, 1.2, "summary"]}),
        slot="17-30",
    )
    daily_limit = normalizer.normalize_daily_limit_index(
        _write_raw(tmp_path / "daily_limit_index.json", {"info": [71, 5, 1, 1, 1]}),
        slot="17-30",
    )
    weight = normalizer.normalize_weight_performance(
        _write_raw(tmp_path / "weight_performance.json", {"info": {"SZ": [["881162", "通信服务", 3.8]]}}),
        slot="17-30",
    )
    feng_k = normalizer.normalize_get_feng_k_list(
        _write_raw(tmp_path / "get_feng_k_list.json", {"List": [["000001", "示例", 88.0, None, 4.5, 1000.0, None, None, 120.0, 80.0, "题材A"]]}),
        slot="17-30",
    )

    assert market_stock["summary"][0]["limit_up_count"] == 79
    assert market_stock["summary"][0]["limit_down_count"] == 1
    assert zhang_ting["summary"][0]["total_limit_up"] == 71
    assert daily_limit["summary"][0]["one_board_count"] == 71
    assert weight["summary"][0]["markets"]["SZ"][0][1] == "通信服务"
    assert feng_k["items"][0]["symbol"] == "000001"
