"""NTL-S5-010 端到端测试：PostmortemResult.mfe/mae/return_pct 不再是 None"""
import pytest
from datetime import date
from uuid import uuid4

from src.evaluation.postmortem_service import PostmortemService
from src.evaluation.evidence_pack import EvidencePack
from src.schemas.contracts import TradeIdea


def make_trade_idea(symbol: str, entry_price: float, as_of_date: str) -> TradeIdea:
    return TradeIdea(
        idea_id=uuid4(),
        trader_id="test_trader",
        as_of_date=date.fromisoformat(as_of_date),
        symbol=symbol,
        side="buy",
        entry={"type": "limit", "price": entry_price},
        target_price=110.0,
        stop_loss_price=95.0,
    )


def make_evidence_pack(
    trade_idea: TradeIdea,
    bars: list[dict],
    entry_price: float,
    target_price: float | None = None,
    stop_loss_price: float | None = None,
    signal_context=None,
) -> EvidencePack:
    market_data = {
        "bars": bars,
        "entry_price": entry_price,
    }
    if target_price is not None:
        market_data["target_price"] = target_price
    if stop_loss_price is not None:
        market_data["stop_loss_price"] = stop_loss_price
    return EvidencePack(
        idea_id=trade_idea.idea_id,
        trade_date=str(trade_idea.as_of_date),
        trade_idea=trade_idea,
        market_data=market_data,
        signal_context=signal_context,
    )


@pytest.mark.asyncio
async def test_mfe_mae_filled_target_hit():
    """target 触发：mfe/mae/return_pct 全部填入正确值"""
    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0},
        {"date": "2026-04-02", "open": 103.0, "high": 110.0, "low": 102.0, "close": 109.0},
    ]
    pack = make_evidence_pack(
        idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0
    )

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.mfe == 10.0
    assert result.mae == 1.0
    assert result.return_pct == pytest.approx(9.0)
    assert result.extra.get("exit_triggered") == "target"
    assert result.extra.get("exit_date") == "2026-04-02"
    assert result.extra.get("is_final") is True


@pytest.mark.asyncio
async def test_mfe_mae_filled_stop_loss_hit():
    """stop_loss 触发：亏损，mfe/mae 仍正确计算"""
    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0},
        {"date": "2026-04-02", "open": 100.0, "high": 101.0, "low": 94.0, "close": 95.0},
    ]
    pack = make_evidence_pack(
        idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0
    )

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.mfe == 2.0
    assert result.mae == 6.0
    assert result.return_pct == pytest.approx(-5.0)
    assert result.extra.get("exit_triggered") == "stop_loss"


@pytest.mark.asyncio
async def test_still_holding_no_exit():
    """未触发出场（仍持仓），return_pct 用当前 bar close"""
    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
        {"date": "2026-04-02", "open": 102.0, "high": 105.0, "low": 100.0, "close": 104.0},
    ]
    pack = make_evidence_pack(
        idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0
    )

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.mfe == 5.0
    assert result.mae == 2.0
    assert result.return_pct == pytest.approx(4.0)
    assert result.extra.get("exit_triggered") is None
    assert result.extra.get("is_final") is False


@pytest.mark.asyncio
async def test_rules_hit_in_extra():
    """rules_hit 被正确写入 extra"""
    from src.strategy.types import SignalContext
    from datetime import datetime, timezone

    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 103.0, "low": 98.0, "close": 102.0},
    ]
    signal_ctx = SignalContext(
        features_snapshot={},
        market_state={},
        rules_snapshot=[
            {"rule_id": "r1", "condition": "ma_50_200_cross"},
            {"rule_id": "r2", "condition": "rsi_oversold"},
        ],
        timestamp=datetime.now(timezone.utc),
    )
    pack = make_evidence_pack(
        idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0,
        signal_context=signal_ctx,
    )

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.extra.get("rules_hit") == ["r1", "r2"]


@pytest.mark.asyncio
async def test_loss_with_rules_hit_attribution():
    """亏损 + rules_hit 非空 → RULE_PRECONDITION_FAILED"""
    from src.strategy.types import SignalContext
    from datetime import datetime, timezone

    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 85.0, "close": 86.0},
    ]
    signal_ctx = SignalContext(
        features_snapshot={},
        market_state={},
        rules_snapshot=[{"rule_id": "r1", "condition": "ma_50_200_cross"}],
        timestamp=datetime.now(timezone.utc),
    )
    pack = make_evidence_pack(
        idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0,
        signal_context=signal_ctx,
    )

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.return_pct < 0
    assert "rule_precondition_failed" in result.failure_attribution.root_causes


@pytest.mark.asyncio
async def test_loss_without_rules_attribution():
    """亏损 + rules_hit 为空 → ENTRY_TIMING_POOR"""
    idea = make_trade_idea("AAPL", entry_price=100.0, as_of_date="2026-04-01")
    bars = [
        {"date": "2026-04-01", "open": 100.0, "high": 102.0, "low": 85.0, "close": 86.0},
    ]
    # signal_context=None（rules_hit 为空）
    pack = make_evidence_pack(
        idea, bars, entry_price=100.0, target_price=110.0, stop_loss_price=95.0,
        signal_context=None,
    )

    service = PostmortemService()
    result = await service.generate(pack)

    assert result.return_pct < 0
    assert "entry_timing_poor" in result.failure_attribution.root_causes
