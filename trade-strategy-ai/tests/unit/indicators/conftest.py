"""共享 fixture：标准 OHLCV 测试数据。"""
import pytest


def make_bar(open_, high, low, close, volume, date_str="2026-04-01"):
    """构造单根 bar（dict）。"""
    return {
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "date": date_str,
    }


@pytest.fixture
def sample_bars():
    """20 根常规日线（上涨趋势），供大多数测试使用。"""
    return [
        make_bar(10, 10.5, 9.8, 10.3, 1000, f"2026-03-{15+i:02d}")
        for i in range(20)
    ]


@pytest.fixture
def flat_bars():
    """价格几乎不变的窄幅震荡 bars（供布林带收口测试）。"""
    base = 10.0
    return [
        make_bar(base, base + 0.05, base - 0.05, base, 100, f"2026-03-{15+i:02d}")
        for i in range(20)
    ]
