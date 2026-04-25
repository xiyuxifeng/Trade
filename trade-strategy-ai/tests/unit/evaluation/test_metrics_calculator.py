"""NTL-S5-010 MFE/MAE 计算器单元测试"""
import pytest
from src.evaluation.metrics_calculator import (
    compute_return_pct,
    _normalize_bar,
    _find_bar_index,
    _extract_rules_hit,
    compute_mfe_mae_return,
)


def test_normalize_bar_lowercase():
    bar = {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}
    result = _normalize_bar(bar)
    assert result == {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}


def test_normalize_bar_uppercase():
    bar = {"Date": "2026-04-01", "Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 103.0}
    result = _normalize_bar(bar)
    assert result == {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}


def test_find_bar_index_found():
    bars = [{"date": "2026-04-01"}, {"date": "2026-04-02"}, {"date": "2026-04-03"}]
    assert _find_bar_index(bars, "2026-04-02") == 1


def test_find_bar_index_not_found():
    bars = [{"date": "2026-04-01"}, {"date": "2026-04-02"}]
    assert _find_bar_index(bars, "2026-04-99") is None


def test_extract_rules_hit_from_snapshot():
    rules_snapshot = [
        {"rule_id": "r1", "condition": "ma_50_200_cross"},
        {"rule_id": "r2", "condition": "rsi_oversold"},
    ]
    result = _extract_rules_hit(rules_snapshot)
    assert result == ["r1", "r2"]  # snapshot 中所有 rule_id 作为 rules_hit


def test_extract_rules_hit_missing_rule_id():
    """rules_snapshot 中某些 rule 没有 rule_id 字段时应跳过"""
    rules_snapshot = [
        {"rule_id": "r1", "condition": "ma_50_200_cross"},
        {"condition": "no_rule_id"},
        {"rule_id": "r2"},
    ]
    result = _extract_rules_hit(rules_snapshot)
    assert result == ["r1", "r2"]


def test_extract_rules_hit_empty():
    rules_snapshot = []
    result = _extract_rules_hit(rules_snapshot)
    assert result == []


# ---- MFE / MAE / return_pct 计算测试 ----


def test_compute_target_hit():
    """止盈触发：价格涨到 target，exit_price 用当日收盘价。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0},  # entry bar
        {"date": "2026-04-02", "open": 103.0, "high": 110.0, "low": 102.0, "close": 109.0},  # target hit
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 10.0      # high=110 - entry=100
    assert mae == 1.0       # entry=100 - low=99
    assert return_pct == pytest.approx(0.09)  # (109/100-1) = 9%
    assert exit_triggered == "target"
    assert exit_date == "2026-04-02"


def test_compute_stop_loss_hit():
    """止损触发：价格跌破 stop_loss。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0},
        {"date": "2026-04-02", "open": 100.0, "high": 101.0, "low": 94.0, "close": 95.0},  # stop hit
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 2.0        # high=102 - entry=100
    assert mae == 6.0        # entry=100 - low=94
    assert return_pct == pytest.approx(-0.05)  # (95/100-1) = -5%
    assert exit_triggered == "stop_loss"
    assert exit_date == "2026-04-02"


def test_compute_no_exit_still_holding():
    """未触发出场（仍持仓），用最后 bar close 作为 exit_price。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
        {"date": "2026-04-02", "open": 102.0, "high": 105.0, "low": 100.0, "close": 104.0},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 5.0        # max(high) - entry = 105 - 100
    assert mae == 2.0        # entry - min(low) = 100 - 98
    assert return_pct == pytest.approx(0.04)  # (104/100-1) = 4%
    assert exit_triggered is None
    assert exit_date == "2026-04-02"


def test_compute_entry_date_only():
    """只有 entry_date 的 bar，没有下一日数据。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 3.0        # high=103 - entry=100
    assert mae == 2.0        # entry=100 - low=98
    assert return_pct == pytest.approx(0.02)  # (102/100-1) = 2%
    assert exit_triggered is None


def test_compute_empty_bars():
    """bars 为空时返回默认值。"""
    result = compute_mfe_mae_return(
        bars=[],
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 0.0
    assert mae == 0.0
    assert return_pct == pytest.approx(0.0)
    assert exit_triggered is None


def test_compute_entry_date_not_in_bars():
    """entry_date 不在 bars 中，从第一条开始计算。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
        {"date": "2026-04-02", "open": 102.0, "high": 105.0, "low": 100.0, "close": 104.0},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-15",  # 不在 bars 中
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    # 从第一条 bar 开始
    assert mfe == 5.0
    assert mae == 2.0
    assert return_pct == pytest.approx(0.04)


def test_compute_zero_entry_price():
    """entry_price 为 0 时返回默认值。"""
    result = compute_mfe_mae_return(
        bars=[{"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}],
        entry_price=0.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date = result
    assert mfe == 0.0
    assert mae == 0.0
    assert return_pct == pytest.approx(0.0)


def test_compute_return_pct_helper():
    """收益率 helper 统一输出比例口径。"""
    assert compute_return_pct(100.0, 104.0) == pytest.approx(0.04)
    assert compute_return_pct(100.0, 95.0) == pytest.approx(-0.05)
    assert compute_return_pct(0.0, 95.0) == 0.0
