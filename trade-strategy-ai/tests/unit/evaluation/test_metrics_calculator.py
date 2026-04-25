"""NTL-S5-010 MFE/MAE 计算器单元测试"""
import pytest
from src.evaluation.metrics_calculator import (
    compute_return_pct,
    _normalize_bar,
    _find_bar_index,
    _extract_rules_hit,
    compute_mfe_mae_return,
    _is_bar_halted,
    TradeConstraint,
    _infer_board_type,
    _get_limit_pct,
    _resolve_constraint,
)


def test_normalize_bar_lowercase():
    bar = {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000}
    result = _normalize_bar(bar)
    assert result == {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000.0}


def test_normalize_bar_uppercase():
    bar = {"Date": "2026-04-01", "Open": 100.0, "High": 105.0, "Low": 99.0, "Close": 103.0, "Volume": 50000}
    result = _normalize_bar(bar)
    assert result == {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000.0}


def test_normalize_bar_missing_volume():
    """volume 缺失时不添加 volume 字段（避免正常数据被误判为停牌）"""
    bar = {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0}
    result = _normalize_bar(bar)
    assert "volume" not in result


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
        {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000},  # entry bar
        {"date": "2026-04-02", "open": 103.0, "high": 110.0, "low": 102.0, "close": 109.0, "volume": 60000},  # target hit
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert mfe == 10.0      # high=110 - entry=100
    assert mae == 1.0       # entry=100 - low=99
    assert return_pct == pytest.approx(0.09)  # (109/100-1) = 9%
    assert exit_triggered == "target"
    assert exit_date == "2026-04-02"
    assert halted_dates == []
    assert eval_date == "2026-04-02"


def test_compute_stop_loss_hit():
    """止损触发：价格跌破 stop_loss。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 50000},
        {"date": "2026-04-02", "open": 100.0, "high": 101.0, "low": 94.0, "close": 95.0, "volume": 60000},  # stop hit
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert mfe == 2.0        # high=102 - entry=100
    assert mae == 6.0        # entry=100 - low=94
    assert return_pct == pytest.approx(-0.05)  # (95/100-1) = -5%
    assert exit_triggered == "stop_loss"
    assert exit_date == "2026-04-02"
    assert halted_dates == []
    assert eval_date == "2026-04-02"


def test_compute_no_exit_still_holding():
    """未触发出场（仍持仓），用最后 bar close 作为 exit_price。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0, "volume": 50000},
        {"date": "2026-04-02", "open": 102.0, "high": 105.0, "low": 100.0, "close": 104.0, "volume": 60000},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert mfe == 5.0        # max(high) - entry = 105 - 100
    assert mae == 2.0        # entry - min(low) = 100 - 98
    assert return_pct == pytest.approx(0.04)  # (104/100-1) = 4%
    assert exit_triggered is None
    assert exit_date == "2026-04-02"
    assert halted_dates == []
    assert eval_date == "2026-04-02"


def test_compute_entry_date_only():
    """只有 entry_date 的 bar，没有下一日数据。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0, "volume": 50000},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert mfe == 3.0        # high=103 - entry=100
    assert mae == 2.0        # entry=100 - low=98
    assert return_pct == pytest.approx(0.02)  # (102/100-1) = 2%
    assert exit_triggered is None
    assert halted_dates == []
    assert eval_date == "2026-04-01"


def test_compute_empty_bars():
    """bars 为空时返回默认值。"""
    result = compute_mfe_mae_return(
        bars=[],
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert mfe == 0.0
    assert mae == 0.0
    assert return_pct == pytest.approx(0.0)
    assert exit_triggered is None
    assert halted_dates == []
    assert eval_date is None


def test_compute_entry_date_not_in_bars():
    """entry_date 不在 bars 中，从第一条开始计算。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0, "volume": 50000},
        {"date": "2026-04-02", "open": 102.0, "high": 105.0, "low": 100.0, "close": 104.0, "volume": 60000},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-15",  # 不在 bars 中
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    # 从第一条 bar 开始
    assert mfe == 5.0
    assert mae == 2.0
    assert return_pct == pytest.approx(0.04)
    assert halted_dates == []
    assert eval_date == "2026-04-02"


def test_compute_zero_entry_price():
    """entry_price 为 0 时返回默认值。"""
    result = compute_mfe_mae_return(
        bars=[{"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000}],
        entry_price=0.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert mfe == 0.0
    assert mae == 0.0
    assert return_pct == pytest.approx(0.0)
    assert halted_dates == []
    assert eval_date == "2026-04-01"


def test_compute_return_pct_helper():
    """收益率 helper 统一输出比例口径。"""
    assert compute_return_pct(100.0, 104.0) == pytest.approx(0.04)
    assert compute_return_pct(100.0, 95.0) == pytest.approx(-0.05)
    assert compute_return_pct(0.0, 95.0) == 0.0


# ---- 停牌/无成交识别测试 ----


def test_is_bar_halted_explicit_flag():
    """显式 is_halted=True 应判定为停牌。"""
    bar = {"date": "2026-04-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 0, "is_halted": True}
    assert _is_bar_halted(bar) is True


def test_is_bar_halted_volume_zero_no_price_move():
    """volume==0 且价格无波动 → 停牌。"""
    bar = {"date": "2026-04-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 0}
    assert _is_bar_halted(bar) is True


def test_is_bar_halted_volume_zero_but_price_move():
    """volume==0 但价格有波动 → 不判定为停牌（可能有竞价/盘前盘后价格）。"""
    bar = {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 0}
    assert _is_bar_halted(bar) is False


def test_is_bar_halted_normal_trade():
    """正常交易 bar 不应被判定为停牌。"""
    bar = {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 50000}
    assert _is_bar_halted(bar) is False


def test_compute_skip_halted_bars():
    """停牌 bar 应被跳过，不参与 MFE/MAE 计算。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0, "volume": 50000},  # entry
        {"date": "2026-04-02", "open": 102.0, "high": 102.0, "low": 102.0, "close": 102.0, "volume": 0},      # halted
        {"date": "2026-04-03", "open": 102.0, "high": 110.0, "low": 101.0, "close": 109.0, "volume": 60000},  # target hit
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert halted_dates == ["2026-04-02"]
    assert mfe == 10.0       # high=110 - entry=100（跳过停牌日）
    assert mae == 2.0        # entry=100 - low=98（跳过停牌日）
    assert return_pct == pytest.approx(0.09)  # (109/100-1) = 9%
    assert exit_triggered == "target"
    assert exit_date == "2026-04-03"
    assert eval_date == "2026-04-03"


def test_compute_all_bars_halted():
    """所有 bar 均为停牌时，exit_price 保持 entry_price，return_pct=0，exit_date 为 None。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 0},
        {"date": "2026-04-02", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 0},
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert halted_dates == ["2026-04-01", "2026-04-02"]
    assert mfe == 0.0
    assert mae == 0.0
    assert return_pct == pytest.approx(0.0)
    assert exit_triggered is None
    assert exit_date is None  # 未实际出场
    assert eval_date == "2026-04-02"  # 评估截止日为最后一条 bar 日期


# ---- A股交易规则约束测试 ----


def test_infer_board_type_main():
    """主板股票代码推断。"""
    assert _infer_board_type("600000.SH") == "main"
    assert _infer_board_type("601318") == "main"
    assert _infer_board_type("000001.SZ") == "main"
    assert _infer_board_type("002415") == "main"


def test_infer_board_type_chinext():
    """创业板股票代码推断。"""
    assert _infer_board_type("300750.SZ") == "chinext"
    assert _infer_board_type("301000") == "chinext"


def test_infer_board_type_star():
    """科创板股票代码推断。"""
    assert _infer_board_type("688981.SH") == "star"
    assert _infer_board_type("688000") == "star"


def test_infer_board_type_st():
    """ST 股票代码推断。"""
    assert _infer_board_type("ST0001") == "st"
    # 数字开头的代码即使包含 ST 后缀也不应被识别为 ST（如 600000.ST 是格式错误）
    assert _infer_board_type("ST凯乐") == "st"


def test_infer_board_type_etf():
    """ETF 等非股票代码默认主板。"""
    assert _infer_board_type("510300.SH") == "main"
    assert _infer_board_type("ETF500") == "main"


def test_get_limit_pct():
    """涨跌停幅度查询。"""
    assert _get_limit_pct("main") == (0.10, 0.10)
    assert _get_limit_pct("chinext") == (0.20, 0.20)
    assert _get_limit_pct("star") == (0.20, 0.20)
    assert _get_limit_pct("st") == (0.05, 0.05)
    assert _get_limit_pct("bse") == (0.30, 0.30)
    assert _get_limit_pct("unknown") == (0.10, 0.10)  # 默认值


def test_resolve_constraint_auto():
    """自动推断板块类型和涨跌停幅度。"""
    c = TradeConstraint(board_type="auto")
    resolved = _resolve_constraint(c, "600000.SH")
    assert resolved.board_type == "main"
    assert resolved.limit_up_pct == 0.10
    assert resolved.limit_down_pct == 0.10


def test_resolve_constraint_explicit():
    """显式指定涨跌停幅度。"""
    c = TradeConstraint(limit_up_pct=0.15, limit_down_pct=0.15, board_type="main")
    resolved = _resolve_constraint(c, "600000.SH")
    assert resolved.limit_up_pct == 0.15
    assert resolved.limit_down_pct == 0.15


def test_t_plus_one_constraint():
    """T+1 约束：entry_date 当日不能卖出，止盈/止损不触发。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 115.0, "low": 99.0, "close": 110.0, "volume": 50000},  # entry，high 超过 target
        {"date": "2026-04-02", "open": 110.0, "high": 109.0, "low": 100.0, "close": 105.0, "volume": 50000},  # 第二天未达 target
    ]
    # 启用 T+1：4月1日不能卖出，target 不触发
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
        symbol="600000.SH",
        constraint=TradeConstraint(t_plus_one=True),
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert exit_triggered is None  # 未触发出场（T+1 阻止了当日卖出，第二天也没触发）
    assert exit_date == "2026-04-02"  # 最后持仓日

    # 禁用 T+1：4月1日可以卖出，target 触发
    result2 = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=95.0,
        symbol="600000.SH",
        constraint=TradeConstraint(t_plus_one=False),
    )
    mfe2, mae2, return_pct2, exit_triggered2, exit_date2, _, _ = result2
    assert exit_triggered2 == "target"  # 触发出场
    assert exit_date2 == "2026-04-01"


def test_limit_up_constraint():
    """涨停约束：止盈价不能超过涨停价。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 50000},  # entry
        {"date": "2026-04-02", "open": 100.0, "high": 112.0, "low": 100.0, "close": 110.0, "volume": 50000},  # 主板涨停价 110
    ]
    # 主板 10% 涨停：涨停价 = 100 * 1.10 = 110
    # target = 111，但 effective_high = min(112, 110) = 110，无法触发 target
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=111.0,  # 高于涨停价
        stop_loss_price=95.0,
        symbol="600000.SH",
        constraint=TradeConstraint(t_plus_one=False),
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert exit_triggered is None  # 未触发（被涨停限制）
    assert mfe == pytest.approx(10.0)  # MFE 受涨停限制：110 - 100 = 10


def test_limit_down_constraint():
    """跌停约束：止损价不能低于跌停价。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 50000},  # entry
        {"date": "2026-04-02", "open": 100.0, "high": 100.0, "low": 85.0, "close": 90.0, "volume": 50000},  # 主板跌停价 90
    ]
    # 主板 10% 跌停：跌停价 = 100 * 0.90 = 90
    # stop_loss = 92，但 effective_low = max(85, 90) = 90，触发 stop_loss
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=110.0,
        stop_loss_price=92.0,  # 高于跌停价
        symbol="600000.SH",
        constraint=TradeConstraint(t_plus_one=False),
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert exit_triggered == "stop_loss"  # 触发（effective_low = 90 <= 92）
    assert mae == 10.0  # MAE 受跌停限制：100 - 90 = 10


def test_chinext_limit_up():
    """创业板 20% 涨停约束。"""
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "volume": 50000},
        {"date": "2026-04-02", "open": 100.0, "high": 125.0, "low": 100.0, "close": 120.0, "volume": 50000},  # 创业板涨停价 120
    ]
    result = compute_mfe_mae_return(
        bars=bars,
        entry_price=100.0,
        entry_date="2026-04-01",
        target_price=122.0,  # 高于涨停价 120
        stop_loss_price=95.0,
        symbol="300750.SZ",
        constraint=TradeConstraint(t_plus_one=False),
    )
    mfe, mae, return_pct, exit_triggered, exit_date, halted_dates, eval_date = result
    assert exit_triggered is None  # 未触发（被 20% 涨停限制）
    assert mfe == 20.0  # MFE 受涨停限制：120 - 100 = 20
